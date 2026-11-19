"""Bounded load experiment: 200 requests, 10 concurrent clients, local HTTP server."""
import logging, os, sys, tempfile, threading, time, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
from werkzeug.serving import make_server
sys.path.insert(0, os.getcwd())
from app import db
from app.main import create_app

logging.getLogger('werkzeug').setLevel(logging.ERROR)
fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd)
c = db.init_v1(path); db.seed(c); c.close()
srv = make_server("127.0.0.1", 5055, create_app(path), threaded=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.5)


def call(i):
    body = json.dumps({"facility_id": 1, "start": "2026-12-%02dT%02d:00" % (1 + i // 20, 8 + i % 20 // 2 * 1),
                       "end": "2026-12-%02dT%02d:30" % (1 + i // 20, 8 + i % 20 // 2 * 1)}).encode()
    req = urllib.request.Request("http://127.0.0.1:5055/bookings", body,
                                 {"X-Token": "tok-stu1", "Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        code = urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        code = e.code
    return code, (time.perf_counter() - t) * 1000


t0 = time.perf_counter()
with ThreadPoolExecutor(10) as ex:
    res = list(ex.map(call, range(200)))
wall = time.perf_counter() - t0
lat = sorted(r[1] for r in res)
codes = {}
for r in res:
    codes[r[0]] = codes.get(r[0], 0) + 1
conn = db.connect(path)
n = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
print("requests=200 concurrency=10 wall=%.2fs throughput=%.0f req/s" % (wall, 200 / wall))
dups = conn.execute("SELECT COUNT(*) FROM (SELECT start_ts FROM bookings GROUP BY facility_id,start_ts HAVING COUNT(*)>1)").fetchone()[0]
print("status_codes=%s rows_in_db=%d double_booked_slots=%d" % (codes, n, dups))
print("latency_ms p50=%.1f p95=%.1f max=%.1f" % (lat[99], lat[189], lat[-1]))
os.remove(path)
sys.exit(1 if dups else 0)
