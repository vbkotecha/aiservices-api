"""Minimal test - if this runs, the container is fine."""
import os
import sys

print(f"[TEST] Python: {sys.version}", flush=True)
print(f"[TEST] PORT: {os.environ.get('PORT', 'NOT SET')}", flush=True)
print(f"[TEST] CWD: {os.getcwd()}", flush=True)
print(f"[TEST] PWD contents: {os.listdir('.')}", flush=True)
print(f"[TEST] src/ contents: {os.listdir('src') if os.path.exists('src') else 'NO src/'}", flush=True)

# Test imports one by one
modules = [
    ("fastapi", "from fastapi import FastAPI"),
    ("uvicorn", "import uvicorn"),
    ("pydantic", "from pydantic import BaseModel"),
    ("requests", "import requests"),
    ("x402", "from x402.http import FacilitatorConfig"),
    ("cryptography", "import cryptography"),
]

for name, imp in modules:
    try:
        exec(imp)
        print(f"[TEST] {name}: OK", flush=True)
    except Exception as e:
        print(f"[TEST] {name}: FAILED - {e}", flush=True)

# Try importing the actual app
try:
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    from src.main import app
    print(f"[TEST] src.main: OK", flush=True)
except Exception as e:
    import traceback
    print(f"[TEST] src.main: CRASHED - {e}", flush=True)
    traceback.print_exc()
