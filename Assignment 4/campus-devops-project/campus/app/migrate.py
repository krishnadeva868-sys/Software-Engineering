"""Schema v1 -> v2: per-facility policy columns. Idempotent, data-preserving."""
import shutil
from . import db


def current_version(conn):
    return conn.execute("SELECT v FROM schema_version").fetchone()[0]


def migrate_to_v2(path, fail_after_alter=False):
    """Backup first; on any error restore backup. Returns final version."""
    backup = path + ".bak"
    shutil.copyfile(path, backup)
    conn = db.connect(path)
    try:
        if current_version(conn) >= 2:
            return 2
        conn.execute("ALTER TABLE facilities ADD COLUMN max_duration_min INTEGER")
        conn.execute("ALTER TABLE facilities ADD COLUMN sensor_threshold REAL")
        conn.execute("ALTER TABLE bookings ADD COLUMN purpose TEXT DEFAULT 'unspecified'")
        if fail_after_alter:
            raise RuntimeError("simulated migration failure")
        conn.execute("UPDATE facilities SET max_duration_min=90, sensor_threshold=60 WHERE restricted=1")
        conn.execute("UPDATE schema_version SET v=2")
        conn.commit()
        return 2
    except Exception:
        conn.close()
        shutil.copyfile(backup, path)  # rollback
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def rollback(path):
    shutil.copyfile(path + ".bak", path)
