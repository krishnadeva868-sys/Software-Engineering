import unittest
from datetime import datetime
from app import rules

D = lambda h, m=0: datetime(2026, 11, 20, h, m)


class UnitTests(unittest.TestCase):
    def test_u1_overlap_partial(self):
        self.assertTrue(rules.overlaps(D(9, 30), D(10, 30), D(10), D(11)))

    def test_u2_back_to_back_allowed(self):
        self.assertFalse(rules.overlaps(D(9), D(10), D(10), D(11)))

    def test_u3_duration_boundary(self):
        self.assertIsNone(rules.validate_window(D(9), D(11), 120))
        self.assertIn("exceeds", rules.validate_window(D(9), D(11, 1), 120))

    def test_u4_end_before_start_rejected(self):
        self.assertIsNotNone(rules.validate_window(D(10), D(10)))
        self.assertIsNotNone(rules.validate_window(D(11), D(10)))

    def test_u5_sensor_threshold_boundary(self):
        self.assertFalse(rules.sensor_alert(74.9))
        self.assertTrue(rules.sensor_alert(75.0))
        self.assertTrue(rules.sensor_alert(75.1))

    def test_u6_priority_matrix(self):
        self.assertEqual(rules.priority(3, 3), "P1")
        self.assertEqual(rules.priority(3, 2), "P1")
        self.assertEqual(rules.priority(2, 2), "P2")
        self.assertEqual(rules.priority(1, 3), "P2")
        self.assertEqual(rules.priority(1, 2), "P3")

    def test_u7_priority_invalid_values(self):
        for bad in ((0, 1), (4, 1), (1, 0)):
            with self.assertRaises(ValueError):
                rules.priority(*bad)

    def test_u8_sla_deadlines(self):
        self.assertEqual(rules.sla_deadline(D(8), "P1"), D(12))
        self.assertEqual(rules.sla_deadline(D(8), "P3").day, 23)

    def test_u9_transitions(self):
        self.assertTrue(rules.can_transition("OPEN", "ASSIGNED"))
        self.assertFalse(rules.can_transition("OPEN", "CLOSED"))
        self.assertFalse(rules.can_transition("CLOSED", "OPEN"))

    def test_u10_approval_roles(self):
        self.assertTrue(rules.can_approve("approver"))
        self.assertFalse(rules.can_approve("student"))
        self.assertFalse(rules.can_approve("faculty"))


if __name__ == "__main__":
    unittest.main()
