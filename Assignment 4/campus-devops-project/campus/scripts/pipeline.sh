#!/bin/bash
# Local runner mirroring .github/workflows/ci.yml stage by stage (used where GitHub/Docker are unavailable).
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd); cd "$ROOT"
ENVDIR=${ENVDIR:-/tmp/campus_env}; PORT=${PORT:-5100}
SHA=$(git rev-parse --short HEAD); VER="1.${SHA}"
start_server() { (cd "$ENVDIR/current"; env DB_PATH="$ENVDIR/data/campus.db" PORT=$PORT APP_VERSION=${RUN_VER:-$VER} "$@" python3 scripts/serve.py </dev/null >"$ENVDIR/serve.log" 2>&1 & echo $! > "$ENVDIR/server.pid"); }
stop_server() { [ -f "$ENVDIR/server.pid" ] && kill $(cat "$ENVDIR/server.pid") 2>/dev/null; rm -f "$ENVDIR/server.pid"; for i in 1 2 3 4 5 6 7 8 9 10; do python3 -c "import socket,sys; s=socket.socket(); sys.exit(0 if s.connect_ex(('127.0.0.1',$PORT)) else 1)" && break; sleep 0.5; done; }
gate() { echo "GATE [$1] $2"; if [ "$2" != PASS ]; then echo "PIPELINE BLOCKED at '$1' - no build, no deploy (version $VER)"; exit 1; fi; }
echo "== stage 1 checkout: commit $SHA, version $VER"
python3 -c "import flask" && echo "== stage 2 dependencies: flask available"
echo "== stage 3 security: secret scan (tracked source)"
if git grep -nEi "(password|secret|api_key)[[:space:]]*=[[:space:]]*['\"][^'\"]+" -- app scripts >/dev/null; then gate secret-scan FAIL; else gate secret-scan PASS; fi
echo "== stage 4 tests (unit + integration + regression + security + migration)"
python3 -W ignore -m unittest discover -s tests -t . 2>&1 | tail -25 > /tmp/test_out.txt; RC=${PIPESTATUS[0]}
cat /tmp/test_out.txt
[ $RC -eq 0 ] && gate tests PASS || gate tests FAIL
echo "== stage 5 build: artifact campus-$VER.tar.gz"
mkdir -p "$ENVDIR/artifacts"; tar czf "$ENVDIR/artifacts/campus-$VER.tar.gz" app scripts requirements.txt Dockerfile
sha256sum "$ENVDIR/artifacts/campus-$VER.tar.gz" | cut -c1-24
if command -v docker >/dev/null; then docker build --build-arg VERSION=$VER -t campus:$VER . ; else echo "docker build SKIPPED (docker not installed in this sandbox)"; fi
echo "== stage 6 deploy to isolated environment $ENVDIR"
REL="$ENVDIR/releases/$VER"; mkdir -p "$REL" "$ENVDIR/data"; tar xzf "$ENVDIR/artifacts/campus-$VER.tar.gz" -C "$REL"
PREV=$(readlink "$ENVDIR/current" 2>/dev/null || true)
[ -f "$ENVDIR/data/campus.db" ] && cp "$ENVDIR/data/campus.db" "$ENVDIR/data/campus.db.pre-$VER"
ln -sfn "$REL" "$ENVDIR/current"
stop_server; sleep 0.5
start_server MIGRATE=${MIGRATE:-0} FAIL_MIGRATION=${FAIL_MIGRATION:-0}
sleep 1.5
echo "== stage 7 smoke checks"
if python3 scripts/smoke.py "http://127.0.0.1:$PORT" "$VER"; then echo "DEPLOYED $VER (smoke PASS)"; exit 0; fi
echo "SMOKE FAILED - rolling back"
tail -3 "$ENVDIR/serve.log"
stop_server
[ -f "$ENVDIR/data/campus.db.pre-$VER" ] && cp "$ENVDIR/data/campus.db.pre-$VER" "$ENVDIR/data/campus.db" && echo "database restored from backup"
if [ -n "$PREV" ]; then ln -sfn "$PREV" "$ENVDIR/current"; RUN_VER=$(basename $PREV); start_server MIGRATE=0 FAIL_MIGRATION=0; sleep 1.5
  python3 scripts/smoke.py "http://127.0.0.1:$PORT" "$RUN_VER" && echo "ROLLBACK OK: previous release $(basename $PREV) serving again"; fi
exit 1
