"""Post-deployment smoke checks against a running instance."""
import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timedelta
base = sys.argv[1]
# unique slot per run so the smoke test is repeatable against a persistent database
T0 = datetime(2040, 1, 1) + timedelta(hours=2 * (int(time.time()) % 200000))
S, E, O = T0.isoformat(timespec='minutes'), (T0 + timedelta(hours=1)).isoformat(timespec='minutes'), (T0 + timedelta(minutes=30)).isoformat(timespec='minutes')


def version():
    try:
        return json.loads(urllib.request.urlopen(base + "/health", timeout=5).read()).get("version")
    except Exception:
        return None


def call(method, path, body=None, tok="tok-stu1"):
    req = urllib.request.Request(base + path, json.dumps(body).encode() if body else None,
                                 {"X-Token": tok, "Content-Type": "application/json"}, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0  # service unreachable

checks = [
    ("health", call("GET", "/health"), 200),
    ("booking created", call("POST", "/bookings", {"facility_id": 1, "start": S, "end": E}), 201),
    ("overlap rejected", call("POST", "/bookings", {"facility_id": 1, "start": O, "end": E}), 409),
    ("no token rejected", call("POST", "/bookings", {}, tok=""), 401),
]
bad = 0
for name, got, want in checks:
    ok = got == want
    bad += not ok
    print("SMOKE %-18s expected=%d got=%d %s" % (name, want, got, "PASS" if ok else "FAIL"))
if len(sys.argv) > 2:
    got = version()
    ok = got == sys.argv[2]
    bad += not ok
    print("SMOKE %-18s expected=%s got=%s %s" % ("version served", sys.argv[2], got, "PASS" if ok else "FAIL"))
sys.exit(1 if bad else 0)
