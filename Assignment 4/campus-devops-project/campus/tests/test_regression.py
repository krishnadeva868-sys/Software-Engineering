from tests.helpers import *


class RegressionTests(ApiCase):
    """Previously correct critical behaviour that every release must keep."""

    def test_r1_back_to_back_booking_still_allowed(self):
        self.book(STU1, 1, "2026-11-20T10:00", "2026-11-20T11:00")
        self.assertEqual(self.book(STU2, 1, "2026-11-20T11:00", "2026-11-20T12:00").status_code, 201)

    def test_r2_contained_booking_still_rejected(self):
        self.book(STU1, 1, "2026-11-20T10:00", "2026-11-20T12:00")
        self.assertEqual(self.book(STU2, 1, "2026-11-20T10:30", "2026-11-20T11:00").status_code, 409)

    def test_r3_sensor_value_at_threshold_alerts(self):
        r = self.client.post("/sensor-events", headers=H(TECH), json={
            "event_id": "e2", "sensor_id": "s1", "facility_id": 1, "value": 75})
        self.assertTrue(r.get_json()["alert"])

    def test_r4_duplicate_sensor_event_makes_one_ticket(self):
        body = {"event_id": "e3", "sensor_id": "s1", "facility_id": 1, "value": 90}
        self.client.post("/sensor-events", headers=H(TECH), json=body)
        r = self.client.post("/sensor-events", headers=H(TECH), json=body)
        self.assertTrue(r.get_json()["duplicate"])
        self.assertEqual(len(self.rows("SELECT * FROM tickets")), 1)

    def test_r5_student_cannot_approve_lab_booking(self):
        bid = self.book(STU1, 2, "2026-11-20T10:00", "2026-11-20T11:00").get_json()["id"]
        r = self.client.post("/bookings/%d/approve" % bid, headers=H(STU1))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.rows("SELECT status FROM bookings")[0]["status"], "PENDING")


class ConcurrencyRegression(ApiCase):
    def test_r6_concurrent_same_slot_only_one_wins(self):
        import threading
        codes = []

        def go(tok):
            codes.append(self.app.test_client().post(
                "/bookings", headers=H(tok),
                json={"facility_id": 1, "start": "2026-12-01T10:00", "end": "2026-12-01T11:00"}).status_code)
        ts = [threading.Thread(target=go, args=(STU1 if i % 2 else STU2,)) for i in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(codes.count(201), 1, codes)
        self.assertEqual(len(self.rows("SELECT * FROM bookings")), 1)
