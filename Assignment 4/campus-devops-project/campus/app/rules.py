"""Pure business rules (no I/O) - unit-test targets."""
from datetime import datetime, timedelta

DEFAULT_MAX_MINUTES = 120
DEFAULT_SENSOR_THRESHOLD = 75.0
SLA_HOURS = {"P1": 4, "P2": 24, "P3": 72}
TRANSITIONS = {
    "OPEN": {"ASSIGNED"},
    "ASSIGNED": {"IN_PROGRESS", "OPEN"},
    "IN_PROGRESS": {"RESOLVED"},
    "RESOLVED": {"CLOSED", "IN_PROGRESS"},
    "CLOSED": set(),
}
STAFF = {"admin", "manager", "technician"}
APPROVERS = {"admin", "approver"}


def parse_ts(value):
    return datetime.fromisoformat(value)


def overlaps(a_start, a_end, b_start, b_end):
    """Half-open intervals: back-to-back bookings do not overlap."""
    return a_start < b_end and b_start < a_end


def validate_window(start, end, max_minutes=DEFAULT_MAX_MINUTES):
    """Return error string or None."""
    if end <= start:
        return "end must be after start"
    if (end - start) > timedelta(minutes=max_minutes):
        return "duration exceeds %d minutes" % max_minutes
    return None


def sensor_alert(value, threshold=DEFAULT_SENSOR_THRESHOLD):
    """Alert when value reaches the threshold (inclusive)."""
    return value >= threshold


def priority(impact, urgency):
    if impact not in (1, 2, 3) or urgency not in (1, 2, 3):
        raise ValueError("impact and urgency must be 1..3")
    score = impact * urgency
    if score >= 6:
        return "P1"
    if score >= 3:
        return "P2"
    return "P3"


def sla_deadline(created, prio):
    return created + timedelta(hours=SLA_HOURS[prio])


def can_transition(current, target):
    return target in TRANSITIONS.get(current, set())


def can_approve(role):
    return role in APPROVERS
