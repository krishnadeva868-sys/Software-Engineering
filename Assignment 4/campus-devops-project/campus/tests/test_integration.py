from tests.helpers import *

S1, E1 = "2026-11-20T10:00", "2026-11-20T11:00"


class IntegrationTests(ApiCase):
    def test_i1_booking_persisted_and_audited(self):
        r = self.book(STU1, 1, S1, E1)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.rows("SELECT * FROM bookings")), 1)
        self.assertEqual(self.rows("SELECT action FROM audit_log")[0]["action"], "booking_created")

    def test_i2_overlap_rejected_with_409(self):
        self.book(STU1, 1, S1, E1)
        r = self.book(STU2, 1, "2026-11-20T09:30", "2026-11-20T10:30")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(len(self.rows("SELECT * FROM bookings")), 1)

    def test_i3_restricted_lab_needs_approval(self):
        bid = self.book(STU1, 2, S1, E1).get_json()["id"]
        self.assertEqual(self.rows("SELECT status FROM bookings")[0]["status"], "PENDING")
        r = self.client.post("/bookings/%d/approve" % bid, headers=H(APPR))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.rows("SELECT status FROM bookings")[0]["status"], "APPROVED")

    def test_i4_sensor_alert_creates_p1_ticket_and_syncs(self):
        r = self.client.post("/sensor-events", headers=H(TECH), json={
            "event_id": "e1", "sensor_id": "s1", "facility_id": 1, "value": 80})
        self.assertEqual(r.status_code, 201)
        t = self.rows("SELECT * FROM tickets")[0]
        self.assertEqual((t["priority"], t["sync_status"]), ("P1", "SYNCED"))

    def test_i5_ticket_lifecycle_and_audit(self):
        tid = self.client.post("/tickets", headers=H(STU1), json={
            "title": "Projector broken", "impact": 2, "urgency": 2}).get_json()["id"]
        for to in ("ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"):
            r = self.client.post("/tickets/%d/transition" % tid, headers=H(TECH), json={"to": to})
            self.assertEqual(r.status_code, 200)
        bad = self.client.post("/tickets/%d/transition" % tid, headers=H(TECH), json={"to": "OPEN"})
        self.assertEqual(bad.status_code, 409)
        self.assertEqual(len(self.rows("SELECT * FROM audit_log WHERE action='ticket_transition'")), 4)

    def test_i6_missing_fields_rejected(self):
        self.assertEqual(self.client.post("/bookings", headers=H(STU1), json={"facility_id": 1}).status_code, 422)
        self.assertEqual(self.client.post("/tickets", headers=H(STU1), json={"title": "x"}).status_code, 422)
