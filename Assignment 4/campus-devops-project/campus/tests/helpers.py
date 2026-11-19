import os, tempfile, unittest
from app import db
from app.main import create_app

H = lambda tok: {"X-Token": tok}
ADMIN, MGR, TECH, APPR, FAC, STU1, STU2 = ("tok-admin", "tok-mgr", "tok-tech", "tok-appr",
                                             "tok-fac", "tok-stu1", "tok-stu2")


class ApiCase(unittest.TestCase):
    tracker = None

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        c = db.init_v1(self.path)
        db.seed(c)
        c.close()
        self.app = create_app(self.path, tracker=self.tracker)
        self.client = self.app.test_client()

    def tearDown(self):
        for suffix in ("", ".bak"):
            if os.path.exists(self.path + suffix):
                os.remove(self.path + suffix)

    def book(self, tok, fid, s, e, **extra):
        body = {"facility_id": fid, "start": s, "end": e}
        body.update(extra)
        return self.client.post("/bookings", json=body, headers=H(tok))

    def rows(self, sql, *a):
        c = db.connect(self.path)
        r = [dict(x) for x in c.execute(sql, a)]
        c.close()
        return r
