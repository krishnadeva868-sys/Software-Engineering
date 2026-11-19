from tests.helpers import *


def down(_ticket):
    raise ConnectionError("tracker unavailable")


class SecurityTests(ApiCase):
    def test_s1_student_cannot_read_others_ticket(self):
        tid = self.client.post("/tickets", headers=H(STU1), json={"title": "a", "impact": 1, "urgency": 1}).get_json()["id"]
        self.assertEqual(self.client.get("/tickets/%d" % tid, headers=H(STU2)).status_code, 403)
        self.assertEqual(self.client.get("/tickets/%d" % tid, headers=H(STU1)).status_code, 200)

    def test_s2_role_header_cannot_impersonate(self):
        bid = self.book(STU1, 2, "2026-11-20T10:00", "2026-11-20T11:00").get_json()["id"]
        h = {"X-Token": STU1, "X-Role": "admin"}
        self.assertEqual(self.client.post("/bookings/%d/approve" % bid, headers=h).status_code, 403)

    def test_s3_no_token_and_bad_token_rejected(self):
        self.assertEqual(self.client.post("/bookings", json={}).status_code, 401)
        self.assertEqual(self.client.post("/bookings", json={}, headers=H("bogus")).status_code, 401)

    def test_s4_student_cannot_transition_or_post_sensor_events(self):
        tid = self.client.post("/tickets", headers=H(STU1), json={"title": "a", "impact": 1, "urgency": 1}).get_json()["id"]
        self.assertEqual(self.client.post("/tickets/%d/transition" % tid, headers=H(STU1), json={"to": "ASSIGNED"}).status_code, 403)
        r = self.client.post("/sensor-events", headers=H(STU1), json={"event_id": "x", "sensor_id": "s", "facility_id": 1, "value": 99})
        self.assertEqual(r.status_code, 403)

    def test_s5_denied_approval_is_audited(self):
        bid = self.book(STU1, 2, "2026-11-20T10:00", "2026-11-20T11:00").get_json()["id"]
        self.client.post("/bookings/%d/approve" % bid, headers=H(STU2))
        self.assertEqual(len(self.rows("SELECT * FROM audit_log WHERE action='approve_denied'")), 1)

    def test_s6_repeated_submission_is_idempotent(self):
        body = {"title": "Leak", "impact": 2, "urgency": 3, "idempotency_key": "k1"}
        a = self.client.post("/tickets", headers=H(STU1), json=body)
        b = self.client.post("/tickets", headers=H(STU1), json=body)
        self.assertEqual((a.status_code, b.status_code), (201, 200))
        self.assertEqual(len(self.rows("SELECT * FROM tickets")), 1)


class DependencyFailureTests(ApiCase):
    tracker = staticmethod(down)

    def test_d1_tracker_down_keeps_local_ticket_pending(self):
        r = self.client.post("/tickets", headers=H(STU1), json={"title": "a", "impact": 2, "urgency": 2})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["sync_status"], "PENDING")
        self.assertEqual(len(self.rows("SELECT * FROM tickets")), 1)

    def test_d2_retry_after_recovery_syncs_once(self):
        self.client.post("/tickets", headers=H(STU1), json={"title": "a", "impact": 2, "urgency": 2})
        self.app.config["TRACKER"] = lambda t: "EXT-%d" % t["id"]
        r = self.client.post("/sync/retry", headers=H(TECH)).get_json()
        self.assertEqual((r["retried"], r["still_pending"]), (1, 0))
        r2 = self.client.post("/sync/retry", headers=H(TECH)).get_json()
        self.assertEqual(r2["retried"], 0)
