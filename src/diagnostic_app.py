"""Diagnostic app - import modules one by one to find the crash."""
import os
import sys
import traceback

print("[DIAG] Starting diagnostic...", flush=True)

# Step 1: Basic FastAPI
try:
    from fastapi import FastAPI
    print("[DIAG] fastapi: OK", flush=True)
except Exception as e:
    print(f"[DIAG] fastapi: FAILED - {e}", flush=True)

# Step 2: Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
print(f"[DIAG] sys.path: {sys.path[:3]}", flush=True)

# Step 3: Import each module one by one
modules = [
    ("crypto_data", "from crypto_data import get_price"),
    ("geo_data", "from geo_data import get_ip_geo"),
    ("web_data", "from web_data import get_url_metadata"),
    ("search_data", "from search_data import web_search"),
    ("dex_data", "from dex_data import get_swap_quote"),
    ("prediction_data", "from prediction_data import get_polymarket_markets"),
    ("news_data", "from news_data import get_crypto_news"),
    ("engine.policy_engine", "from engine.policy_engine import evaluate_dispute"),
    ("mcp_endpoint", "from mcp_endpoint import router"),
    ("marketing_data", "from marketing_data import get_brand_sentiment"),
    ("onchain_data", "from onchain_data import get_whales"),
    ("synthesis_data", "from synthesis_data import get_token_risk"),
    ("inference_gateway", "from inference_gateway import list_models"),
    ("tradfi_data", "from tradfi_data import get_stock_quote"),
    ("utility_data", "from utility_data import extract_web_content"),
    ("agent_memory", "from agent_memory import store"),
    ("skill_packs", "from skill_packs import crypto_dossier"),
    ("media_gateway", "from media_gateway import generate_image"),
    ("voice_gateway", "from voice_gateway import get_phone_number"),
]

failed_modules = []
for name, imp_stmt in modules:
    try:
        exec(imp_statement)
        print(f"[DIAG] {name}: OK", flush=True)
    except Exception as e:
        print(f"[DIAG] {name}: FAILED - {e}", flush=True)
        traceback.print_exc()
        failed_modules.append(name)

# Step 4: Try x402
try:
    from x402.http import FacilitatorConfig
    print("[DIAG] x402: OK", flush=True)
except Exception as e:
    print(f"[DIAG] x402: FAILED - {e}", flush=True)

# Step 5: Try importing full main
try:
    from main import app
    print("[DIAG] main.app: OK", flush=True)
except Exception as e:
    print(f"[DIAG] main.app: FAILED - {e}", flush=True)
    traceback.print_exc()

print(f"[DIAG] Failed modules: {failed_modules}", flush=True)
print("[DIAG] Done. Starting minimal server.", flush=True)

# Start a minimal server so the deploy doesn't crash
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "OK", "mode": "diagnostic", "failed_modules": failed_modules}

@app.get("/")
async def root():
    return {"status": "OK", "mode": "diagnostic", "failed_modules": failed_modules}
