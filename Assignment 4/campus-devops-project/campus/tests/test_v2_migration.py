import os
from app import db, migrate
from tests.helpers import *


class V2Tests(ApiCase):
    def test_m1_migration_preserves_existing_rows(self):
        self.book(STU1, 1, "2026-11-20T10:00", "2026-11-20T11:00")
        self.client.post("/tickets", headers=H(STU1), json={"title": "a", "impact": 2, "urgency": 2})
        before = (len(self.rows("SELECT * FROM bookings")), len(self.rows("SELECT * FROM tickets")),
                  len(self.rows("SELECT * FROM audit_log")))
        self.assertEqual(migrate.migrate_to_v2(self.path), 2)
        after = (len(self.rows("SELECT * FROM bookings")), len(self.rows("SELECT * FROM tickets")),
                 len(self.rows("SELECT * FROM audit_log")))
        self.assertEqual(before, after)

    def test_m2_migration_is_idempotent(self):
        migrate.migrate_to_v2(self.path)
        self.assertEqual(migrate.migrate_to_v2(self.path), 2)

    def test_m3_failed_migration_rolls_back(self):
        self.book(STU1, 1, "2026-11-20T10:00", "2026-11-20T11:00")
        with self.assertRaises(RuntimeError):
            migrate.migrate_to_v2(self.path, fail_after_alter=True)
        c = db.connect(self.path)
        self.assertEqual(migrate.current_version(c), 1)
        cols = [r[1] for r in c.execute("PRAGMA table_info(facilities)")]
        c.close()
        self.assertNotIn("max_duration_min", cols)
        self.assertEqual(len(self.rows("SELECT * FROM bookings")), 1)

    def test_m4_campus_lab_limit_90_after_migration(self):
        migrate.migrate_to_v2(self.path)
        ok = self.book(STU1, 2, "2026-11-20T10:00", "2026-11-20T11:30")
        bad = self.book(STU2, 2, "2026-11-21T10:00", "2026-11-21T11:31")
        self.assertEqual((ok.status_code, bad.status_code), (201, 422))
        self.assertEqual(ok.get_json()["max_minutes"], 90)

    def test_m5_lab_sensor_threshold_60_after_migration(self):
        migrate.migrate_to_v2(self.path)
        r = self.client.post("/sensor-events", headers=H(TECH), json={
            "event_id": "m5", "sensor_id": "s", "facility_id": 2, "value": 60})
        self.assertTrue(r.get_json()["alert"])

    def test_m6_old_v1_clients_still_work_on_v2(self):
        migrate.migrate_to_v2(self.path)
        self.assertEqual(self.book(STU1, 1, "2026-11-20T10:00", "2026-11-20T11:00").status_code, 201)

    def test_m7_revised_api_purpose_stored(self):
        migrate.migrate_to_v2(self.path)
        self.book(STU1, 1, "2026-11-20T10:00", "2026-11-20T11:00", purpose="Project review")
        self.assertEqual(self.rows("SELECT purpose FROM bookings")[0]["purpose"], "Project review")
