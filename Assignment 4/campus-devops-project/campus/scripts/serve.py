"""Start the service. Config only from environment (no secrets in source)."""
import logging, os, sys
sys.path.insert(0, os.getcwd())
from werkzeug.serving import make_server
from app import db, migrate
from app.main import create_app

path = os.environ.get("DB_PATH", "campus.db")
if not os.path.exists(path):
    c = db.init_v1(path); db.seed(c); c.close()
if os.environ.get("MIGRATE") == "1":
    migrate.migrate_to_v2(path, fail_after_alter=os.environ.get("FAIL_MIGRATION") == "1")
logging.getLogger("werkzeug").setLevel(logging.ERROR)
make_server("127.0.0.1", int(os.environ.get("PORT", 5000)), create_app(path), threaded=True).serve_forever()
