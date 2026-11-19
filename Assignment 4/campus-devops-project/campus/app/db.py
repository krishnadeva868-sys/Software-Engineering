import sqlite3

SCHEMA_V1 = """
CREATE TABLE users(id TEXT PRIMARY KEY, token TEXT UNIQUE, role TEXT);
CREATE TABLE facilities(id INTEGER PRIMARY KEY, name TEXT, restricted INTEGER DEFAULT 0);
CREATE TABLE bookings(id INTEGER PRIMARY KEY AUTOINCREMENT, facility_id INTEGER, user_id TEXT,
  start_ts TEXT, end_ts TEXT, status TEXT);
CREATE TABLE tickets(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, impact INTEGER, urgency INTEGER,
  priority TEXT, status TEXT, owner_id TEXT, booking_id INTEGER, idem_key TEXT UNIQUE,
  sla_due TEXT, sync_status TEXT DEFAULT 'NONE', external_id TEXT);
CREATE TABLE sensor_events(event_id TEXT PRIMARY KEY, sensor_id TEXT, facility_id INTEGER,
  value REAL, ticket_id INTEGER);
CREATE TABLE audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, action TEXT, detail TEXT);
CREATE TABLE schema_version(v INTEGER);
INSERT INTO schema_version VALUES(1);
"""


def connect(path):
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_v1(path):
    conn = connect(path)
    conn.executescript(SCHEMA_V1)
    conn.commit()
    return conn


def seed(conn):
    conn.executemany("INSERT INTO users VALUES(?,?,?)", [
        ("admin1", "tok-admin", "admin"), ("mgr1", "tok-mgr", "manager"),
        ("tech1", "tok-tech", "technician"), ("appr1", "tok-appr", "approver"),
        ("fac1", "tok-fac", "faculty"), ("stu1", "tok-stu1", "student"),
        ("stu2", "tok-stu2", "student"), ("sensor1", "tok-sensor", "technician")])
    conn.executemany("INSERT INTO facilities(id,name,restricted) VALUES(?,?,?)",
                     [(1, "Seminar Hall", 0), (2, "Chemistry Lab", 1)])
    conn.commit()
