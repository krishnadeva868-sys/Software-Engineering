import os
from datetime import datetime
from flask import Flask, request, jsonify
from . import db, rules


def default_tracker(ticket):
    """Stub for the external issue tracker (always available in dev)."""
    return "EXT-%d" % ticket["id"]


def create_app(db_path=None, tracker=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH", "campus.db")
    app.config["TRACKER"] = tracker or default_tracker

    def conn():
        return db.connect(app.config["DB_PATH"])

    def audit(c, actor, action, detail=""):
        c.execute("INSERT INTO audit_log(ts,actor,action,detail) VALUES(?,?,?,?)",
                  (datetime.utcnow().isoformat(), actor, action, detail))

    def current_user(c):
        # Role always comes from the database via token; client-supplied role headers are ignored.
        tok = request.headers.get("X-Token", "")
        return c.execute("SELECT * FROM users WHERE token=?", (tok,)).fetchone()

    def facility(c, fid):
        row = c.execute("SELECT * FROM facilities WHERE id=?", (fid,)).fetchone()
        return dict(row) if row else None

    def limits(fac):
        return (fac.get("max_duration_min") or rules.DEFAULT_MAX_MINUTES,
                fac.get("sensor_threshold") or rules.DEFAULT_SENSOR_THRESHOLD)

    def sync(c, tid):
        t = dict(c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone())
        try:
            ext = app.config["TRACKER"](t)
            c.execute("UPDATE tickets SET sync_status='SYNCED', external_id=? WHERE id=?", (ext, tid))
        except Exception:
            c.execute("UPDATE tickets SET sync_status='PENDING' WHERE id=?", (tid,))
        c.commit()

    def new_ticket(c, title, impact, urgency, owner, booking_id=None, key=None):
        prio = rules.priority(impact, urgency)
        now = datetime.utcnow()
        cur = c.execute(
            "INSERT INTO tickets(title,impact,urgency,priority,status,owner_id,booking_id,idem_key,sla_due)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (title, impact, urgency, prio, "OPEN", owner, booking_id, key,
             rules.sla_deadline(now, prio).isoformat()))
        audit(c, owner, "ticket_created", "id=%d prio=%s" % (cur.lastrowid, prio))
        c.commit()
        return cur.lastrowid

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=os.environ.get("APP_VERSION", "dev"))

    @app.post("/bookings")
    def book():
        c = conn()
        u = current_user(c)
        if not u:
            return jsonify(error="unauthenticated"), 401
        d = request.get_json(silent=True) or {}
        for f in ("facility_id", "start", "end"):
            if f not in d:
                return jsonify(error="missing field: %s" % f), 422
        fac = facility(c, d["facility_id"])
        if not fac:
            return jsonify(error="unknown facility"), 404
        try:
            s, e = rules.parse_ts(d["start"]), rules.parse_ts(d["end"])
        except ValueError:
            return jsonify(error="bad timestamp"), 422
        err = rules.validate_window(s, e, limits(fac)[0])
        if err:
            return jsonify(error=err), 422
        c.execute("BEGIN IMMEDIATE")  # serialise check+insert so concurrent requests cannot double-book
        for row in c.execute("SELECT start_ts,end_ts FROM bookings WHERE facility_id=? AND status!='CANCELLED'",
                             (fac["id"],)).fetchall():
            if rules.overlaps(s, e, rules.parse_ts(row["start_ts"]), rules.parse_ts(row["end_ts"])):
                c.rollback()
                return jsonify(error="overlaps existing booking"), 409
        status = "PENDING" if fac["restricted"] else "APPROVED"
        cur = c.execute("INSERT INTO bookings(facility_id,user_id,start_ts,end_ts,status) VALUES(?,?,?,?,?)",
                        (fac["id"], u["id"], d["start"], d["end"], status))
        if "purpose" in d and "purpose" in [r[1] for r in c.execute("PRAGMA table_info(bookings)")]:
            c.execute("UPDATE bookings SET purpose=? WHERE id=?", (d["purpose"], cur.lastrowid))
        audit(c, u["id"], "booking_created", "id=%d status=%s" % (cur.lastrowid, status))
        c.commit()
        return jsonify(id=cur.lastrowid, status=status, max_minutes=limits(fac)[0]), 201

    @app.post("/bookings/<int:bid>/approve")
    def approve(bid):
        c = conn()
        u = current_user(c)
        if not u:
            return jsonify(error="unauthenticated"), 401
        if not rules.can_approve(u["role"]):
            audit(c, u["id"], "approve_denied", "booking=%d" % bid)
            c.commit()
            return jsonify(error="forbidden"), 403
        b = c.execute("SELECT * FROM bookings WHERE id=?", (bid,)).fetchone()
        if not b:
            return jsonify(error="not found"), 404
        if b["status"] != "PENDING":
            return jsonify(error="booking not pending"), 409
        c.execute("UPDATE bookings SET status='APPROVED' WHERE id=?", (bid,))
        audit(c, u["id"], "booking_approved", "id=%d" % bid)
        c.commit()
        return jsonify(id=bid, status="APPROVED")

    @app.post("/tickets")
    def create_ticket():
        c = conn()
        u = current_user(c)
        if not u:
            return jsonify(error="unauthenticated"), 401
        d = request.get_json(silent=True) or {}
        for f in ("title", "impact", "urgency"):
            if f not in d:
                return jsonify(error="missing field: %s" % f), 422
        key = d.get("idempotency_key")
        if key:
            old = c.execute("SELECT id FROM tickets WHERE idem_key=?", (key,)).fetchone()
            if old:
                return jsonify(id=old["id"], duplicate=True), 200
        try:
            tid = new_ticket(c, d["title"], d["impact"], d["urgency"], u["id"], d.get("booking_id"), key)
        except ValueError as ex:
            return jsonify(error=str(ex)), 422
        sync(c, tid)
        t = c.execute("SELECT priority,sla_due,sync_status FROM tickets WHERE id=?", (tid,)).fetchone()
        return jsonify(id=tid, priority=t["priority"], sla_due=t["sla_due"], sync_status=t["sync_status"]), 201

    @app.get("/tickets/<int:tid>")
    def get_ticket(tid):
        c = conn()
        u = current_user(c)
        if not u:
            return jsonify(error="unauthenticated"), 401
        t = c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
        if not t:
            return jsonify(error="not found"), 404
        if u["role"] not in rules.STAFF and t["owner_id"] != u["id"]:
            return jsonify(error="forbidden"), 403
        return jsonify(dict(t))

    @app.post("/tickets/<int:tid>/transition")
    def transition(tid):
        c = conn()
        u = current_user(c)
        if not u:
            return jsonify(error="unauthenticated"), 401
        if u["role"] not in rules.STAFF:
            return jsonify(error="forbidden"), 403
        t = c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
        if not t:
            return jsonify(error="not found"), 404
        target = (request.get_json(silent=True) or {}).get("to")
        if not rules.can_transition(t["status"], target):
            return jsonify(error="illegal transition %s->%s" % (t["status"], target)), 409
        c.execute("UPDATE tickets SET status=? WHERE id=?", (target, tid))
        audit(c, u["id"], "ticket_transition", "id=%d %s->%s" % (tid, t["status"], target))
        c.commit()
        return jsonify(id=tid, status=target)

    @app.post("/sensor-events")
    def sensor_event():
        c = conn()
        u = current_user(c)
        if not u or u["role"] not in rules.STAFF:
            return jsonify(error="forbidden"), 403
        d = request.get_json(silent=True) or {}
        for f in ("event_id", "sensor_id", "facility_id", "value"):
            if f not in d:
                return jsonify(error="missing field: %s" % f), 422
        if c.execute("SELECT 1 FROM sensor_events WHERE event_id=?", (d["event_id"],)).fetchone():
            return jsonify(duplicate=True), 200
        fac = facility(c, d["facility_id"])
        if not fac:
            return jsonify(error="unknown facility"), 404
        tid = None
        if rules.sensor_alert(d["value"], limits(fac)[1]):
            tid = new_ticket(c, "Sensor alert %s" % d["sensor_id"], 3, 2, u["id"],
                             key="sensor-" + d["event_id"])
        c.execute("INSERT INTO sensor_events VALUES(?,?,?,?,?)",
                  (d["event_id"], d["sensor_id"], d["facility_id"], d["value"], tid))
        c.commit()
        if tid:
            sync(c, tid)
        return jsonify(alert=tid is not None, ticket_id=tid), 201

    @app.post("/sync/retry")
    def sync_retry():
        c = conn()
        u = current_user(c)
        if not u or u["role"] not in rules.STAFF:
            return jsonify(error="forbidden"), 403
        ids = [r["id"] for r in c.execute("SELECT id FROM tickets WHERE sync_status='PENDING'")]
        for i in ids:
            sync(c, i)
        left = c.execute("SELECT COUNT(*) FROM tickets WHERE sync_status='PENDING'").fetchone()[0]
        return jsonify(retried=len(ids), still_pending=left)

    return app
