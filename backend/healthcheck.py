"""Container health probe — exits 0 if /health answers, 1 otherwise. (No curl needed in the image.)"""
import os
import sys
import urllib.request

port = os.environ.get("PORT", "8000")
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=4) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
