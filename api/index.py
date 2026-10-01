import sys
import os
import shutil

# Ensure project root is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# On Vercel Serverless environment, copy pre-seeded DB to /tmp so writes succeed
if os.environ.get("VERCEL"):
    tmp_db = "/tmp/fraudlens.db"
    root_db = os.path.join(root_dir, "fraudlens.db")
    if not os.path.exists(tmp_db) and os.path.exists(root_db):
        try:
            shutil.copy2(root_db, tmp_db)
        except Exception:
            pass
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db}"

from backend.app.main import app
