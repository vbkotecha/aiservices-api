"""
AIServices — Paid data APIs for AI agents
Crypto market data, IP geolocation, URL metadata
"""
import os
from pathlib import Path

# Load .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().strip().splitlines():
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto_data import get_price, get_multi_price, get_indicators, get_fear_greed, get_defi_yields
from geo_data import get_ip_geo
from web_data import get_url_metadata
from engine.policy_engine import evaluate_dispute, list_policies

WALLET = os.environ.get("WALLET_ADDRESS", "0x9863aB6242663FCc84c33632741711dB78f8Fd15")

app = FastAPI(
    title="AIServices",
    version="2.0.0",
    description="""Paid APIs for AI agents — crypto market data, DeFi yields, IP geolocation, URL metadata, AND dispute resolution.

All paid endpoints use x402 protocol with USDC on Base. Powered by AgentCourt policy engine.
""",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- x402 Payment Protocol (Base Mainnet) ---\nX402_WALLET = os.environ.get("WALLET_ADDRESS", WALLET)\nX402_NETWORK = "eip155:8453"\n\nX402_ENABLED = False\ntry:\n    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption\n    from x402.http.middleware.fastapi import PaymentMiddlewareASGI\n    from x402.http.types import RouteConfig\n    from x402.mechanisms.evm.exact import ExactEvmServerScheme\n    from x402.server import x402ResourceServer\n\n    # Use CDP facilitator if credentials available, otherwise community facilitator\n    _facilitator_url = "https://x402.org/facilitator"\n    _facilitator_kwargs = {}\n    try:\n        from x402.http import CreateHeadersAuthProvider\n        from x402_payment import create_cdp_auth_headers, CDP_FACILITATOR_URL\n        if os.environ.get("CDP_API_KEY_ID") and os.environ.get("CDP_API_KEY_SECRET"):\n            _facilitator_url = CDP_FACILITATOR_URL\n            _facilitator_kwargs["auth_provider"] = CreateHeadersAuthProvider(create_cdp_auth_headers)\n            print("[x402] Using CDP facilitator with auth headers", flush=True)\n    except ImportError:\n        print("[x402] CDP auth not available, using community facilitator", flush=True)\n\n    facilitator = HTTPFacilitatorClient(\n        FacilitatorConfig(url=_facilitator_url, **_facilitator_kwargs)\n    )\n    payment_server = x402ResourceServer(facilitator)\n    payment_server.register(X402_NETWORK, ExactEvmServerScheme())\n\n    # Optional: register bazaar extension for discovery\n    try:\n        from x402.extensions.bazaar import bazaar_resource_server_extension\n        payment_server.register_extension(bazaar_resource_server_extension)\n        print("[x402] Bazaar discovery extension registered", flush=True)\n    except ImportError:\n        print("[x402] Bazaar extension not available (OK, continuing)", flush=True)\n\n    payment_server.initialize()\n\n    payment_routes = {\n        "POST /v1/disputes": RouteConfig(\n            accepts=[\n                PaymentOption(\n                    scheme="exact",\n                    pay_to=X402_WALLET,\n                    price="$0.05",\n                    network=X402_NETWORK,\n                ),\n            ],\n            mime_type="application/json",\n            description="Submit a dispute for policy-driven ruling (AgentCourt engine)",\n        ),\n        "GET /v1/indicators/*": RouteConfig(\n            accepts=[\n                PaymentOption(\n                    scheme="exact",\n                    pay_to=X402_WALLET,\n                    price="$0.02",\n                    network=X402_NETWORK,\n                ),\n            ],\n            mime_type="application/json",\n            description="Technical indicators: RSI, Bollinger Bands, ATR, Support/Resistance",\n        ),\n        "GET /v1/yields": RouteConfig(\n            accepts=[\n                PaymentOption(\n                    scheme="exact",\n                    pay_to=X402_WALLET,\n                    price="$0.02",\n                    network=X402_NETWORK,\n                ),\n            ],\n            mime_type="application/json",\n            description="Top DeFi yield pools by TVL",\n        ),\n        "GET /v1/metadata": RouteConfig(\n            accepts=[\n                PaymentOption(\n                    scheme="exact",\n                    pay_to=X402_WALLET,\n                    price="$0.01",\n                    network=X402_NETWORK,\n                ),\n            ],\n            mime_type="application/json",\n            description="URL metadata extraction and unfurling",\n        ),\n    }\n\n    app.add_middleware(\n        PaymentMiddlewareASGI,\n        routes=payment_routes,\n        server=payment_server,\n    )\n    print(f"[x402] Payment middleware enabled — disputes ($0.05), indicators/yields ($0.02), metadata ($0.01)", flush=True)\n    X402_ENABLED = True\nexcept Exception as e:\n    import traceback\n    print(f"[x402] NOT loaded — running in free mode. Error: {e}", flush=True)\n    traceback.print_exc()\n    X402_ENABLED = False


# --- Market Data ---

@app.get("/v1/price/{symbol}", tags=["Market Data"])
async def crypto_price(symbol: str):
    """Current crypto price (FREE)"""
    return get_price(symbol)

@app.get("/v1/prices", tags=["Market Data"])
async def crypto_prices(symbols: str = "BTC,ETH,SOL,XRP"):
    """Batch crypto prices (FREE)"""
    return get_multi_price(symbols.split(","))

@app.get("/v1/indicators/{symbol}", tags=["Market Data"])
async def crypto_indicators(symbol: str):
    """Technical indicators: RSI, BB, ATR, S/R ($0.02)"""
    return get_indicators(symbol)

@app.get("/v1/yields", tags=["Market Data"],
         response_model=dict,
         responses={
             200: {
                 "content": {
                     "application/json": {
                         "schema": {
                             "type": "object",
                             "properties": {
                                 "pools": {
                                     "type": "array",
                                     "items": {
                                         "type": "object",
                                         "properties": {
                                             "protocol": {"type": "string"},
                                             "pool": {"type": "string"},
                                             "apy": {"type": "number"},
                                             "tvl_usd": {"type": "number"},
                                             "chain": {"type": "string"},
                                         }
                                     }
                                 }
                             }
                         }
                     }
                 },
                 "description": "Top DeFi yield pools ranked by TVL"
             },
             402: {"description": "Payment required — $0.02 USDC on Base"}
         },
         summary="Top DeFi Yield Pools",
         description="Returns top DeFi yield farming pools ranked by TVL across major protocols. Costs $0.02 USDC via x402.")
async def defi_yields(
    limit: int = 20,
    chain: str = "all"
):
    """Top DeFi yield pools by TVL ($0.02)"""
    return get_defi_yields()

@app.get("/v1/fear-greed", tags=["Market Data"])
async def fear_greed():
    """Crypto Fear & Greed Index (FREE)"""
    return get_fear_greed()


# --- Geolocation ---

@app.get("/v1/geo/{ip}", tags=["Location"])
async def ip_geo(ip: str):
    """IP geolocation lookup (FREE)"""
    return get_ip_geo(ip)


# --- Web Data ---

@app.get("/v1/metadata", tags=["Web Data"])
async def url_metadata(url: str):
    """URL metadata extraction and unfurling ($0.01)"""
    return get_url_metadata(url)


# --- Dispute Resolution (AgentCourt engine) ---

class DisputeRequest(BaseModel):
    policy: str = Field(description="Policy template name (e.g. freelance-delivery)")
    claimant: str = Field(description="Plaintiff address or agent ID")
    respondent: str = Field(description="Respondent address or agent ID")
    claim: str = Field("", description="What happened")
    desired_remedy: str = Field("", description="What the claimant wants")
    evidence: list = Field(default_factory=list, description="Evidence items")

@app.post("/v1/disputes", tags=["Dispute Resolution"])
async def resolve_dispute(req: DisputeRequest):
    """Submit a dispute for policy-driven ruling ($0.05 via x402)"""
    dispute_dict = {
        "claimant": req.claimant,
        "respondent": req.respondent,
        "claim": req.claim,
        "desired_remedy": req.desired_remedy,
    }
    ruling = evaluate_dispute(
        dispute=dispute_dict,
        evidence=req.evidence,
        policy_name=req.policy,
    )
    return ruling

@app.get("/v1/policies", tags=["Dispute Resolution"])
async def get_policies():
    """List available dispute policy templates (FREE)"""
    return list_policies()


# --- Health & Discovery ---

@app.get("/")
async def root():
    return {
        "name": "AIServices",
        "tagline": "Paid APIs for AI agents — market data + dispute resolution",
        "version": "2.0.0",
        "payment": "x402 / USDC on Base",
        "wallet": WALLET,
        "services": {
            "market_data": {
                "price": {"endpoint": "GET /v1/price/{symbol}", "price": "free", "desc": "Current crypto price"},
                "batch_prices": {"endpoint": "GET /v1/prices?symbols=BTC,ETH", "price": "free", "desc": "Batch crypto prices"},
                "indicators": {"endpoint": "GET /v1/indicators/{symbol}", "price": "$0.02", "desc": "RSI, Bollinger Bands, ATR, Support/Resistance"},
                "yields": {"endpoint": "GET /v1/yields", "price": "$0.02", "desc": "Top DeFi yield pools by TVL"},
                "fear_greed": {"endpoint": "GET /v1/fear-greed", "price": "free", "desc": "Crypto Fear & Greed Index"},
            },
            "dispute_resolution": {
                "file_dispute": {"endpoint": "POST /v1/disputes", "price": "$0.05", "desc": "Submit dispute for policy-driven ruling (AgentCourt engine)"},
                "policies": {"endpoint": "GET /v1/policies", "price": "free", "desc": "List dispute policy templates"},
            },
        },
        "live": True,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "x402_enabled": X402_ENABLED,
        "services": ["crypto_prices", "indicators", "defi_yields", "fear_greed", "geo", "metadata", "disputes", "policies"],
    }


@app.get("/.well-known/x402")
async def x402_manifest():
    """x402 payment manifest for agent discovery."""
    return {
        "version": "1.0",
        "name": "AIServices",
        "description": "Paid data APIs for AI agents — crypto prices, indicators, DeFi yields, geolocation, URL metadata",
        "network": "base-mainnet",
        "chain_id": "eip155:8453",
        "currency": "USDC",
        "endpoints": [
            {"path": "/v1/price/{symbol}", "method": "GET", "price": "$0.00", "description": "Current crypto price (FREE)"},
            {"path": "/v1/prices", "method": "GET", "price": "$0.00", "description": "Batch crypto prices (FREE)"},
            {"path": "/v1/indicators/{symbol}", "method": "GET", "price": "$0.02", "description": "Technical indicators: RSI, BB, ATR, S/R"},
            {"path": "/v1/yields", "method": "GET", "price": "$0.02", "description": "Top DeFi yield pools by TVL"},
            {"path": "/v1/fear-greed", "method": "GET", "price": "$0.00", "description": "Crypto Fear and Greed Index (FREE)"},
            {"path": "/v1/geo/{ip}", "method": "GET", "price": "$0.00", "description": "IP geolocation lookup (FREE)"},
            {"path": "/v1/metadata", "method": "GET", "price": "$0.01", "description": "URL metadata extraction and unfurling"},
        ],
        "categories": ["Data", "Market Data", "Geolocation"],
        "payTo": WALLET,
        "contact": "https://github.com/vbkotecha",
        "website": "https://api.aiservices.to",
        "license": "MIT",
    }


@app.get("/.well-known/agent.json")
async def agent_json():
    """Agent discovery manifest for AI agent platforms and crawlers."""
    return {
        "name": "AIServices",
        "version": "1.0.0",
        "description": "Paid data APIs for AI agents — crypto prices, indicators, DeFi yields, geolocation, URL metadata",
        "url": "https://api.aiservices.to",
        "capabilities": [
            "crypto-market-data",
            "technical-indicators",
            "defi-yields",
            "ip-geolocation",
            "url-metadata",
        ],
        "payment": {
            "protocol": "x402",
            "currency": "USDC",
            "network": "base-mainnet",
            "chain_id": 8453,
        },
        "endpoints": {
            "free": [
                "GET /v1/price/{symbol}",
                "GET /v1/prices?symbols=BTC,ETH",
                "GET /v1/fear-greed",
                "GET /v1/geo/{ip}",
            ],
            "paid": [
                {"path": "GET /v1/indicators/{symbol}", "price": "$0.02"},
                {"path": "GET /v1/yields", "price": "$0.02"},
                {"path": "GET /v1/metadata", "price": "$0.01"},
            ],
        },
        "docs": "https://api.aiservices.to/docs",
        "github": "https://github.com/vbkotecha/aiservices-api",
        "wallet": WALLET,
    }


@app.get("/llms.txt")
async def llms_txt():
    """LLM-friendly API description for agent crawlers and AI discovery."""
    lines = [
        "# AIServices",
        "",
        "> Paid data APIs for AI agents. Crypto prices, technical indicators, DeFi yields, IP geolocation, URL metadata.",
        "",
        "## Base URL",
        "https://api.aiservices.to",
        "",
        "## Authentication",
        "Paid endpoints use x402 protocol (USDC on Base Mainnet). Free endpoints require no auth.",
        "",
        "## Free Endpoints",
        "- GET /v1/price/{symbol} — Current crypto price (e.g., BTC, ETH)",
        "- GET /v1/prices?symbols=BTC,ETH,SOL — Batch crypto prices",
        "- GET /v1/fear-greed — Crypto Fear & Greed Index (0-100)",
        "- GET /v1/geo/{ip} — IP geolocation lookup",
        "",
        "## Paid Endpoints (x402 / USDC on Base)",
        "- GET /v1/indicators/{symbol} — RSI, Bollinger Bands, ATR, Support/Resistance ($0.02)",
        "- GET /v1/yields — Top DeFi yield pools by TVL ($0.02)",
        "- GET /v1/metadata?url=... — URL metadata extraction and unfurling ($0.01)",
        "",
        "## Example Usage",
        "```",
        "# Free: Get BTC price",
        "curl https://api.aiservices.to/v1/price/BTC",
        "",
        "# Paid: Get BTC indicators (requires x402 payment)",
        "curl https://api.aiservices.to/v1/indicators/BTC",
        "```",
        "",
        f"## Payment Wallet\n{WALLET}",
        "",
        "## Links",
        "- API Docs: https://api.aiservices.to/docs",
        "- GitHub: https://github.com/vbkotecha/aiservices-api",
    ]
    from starlette.responses import PlainTextResponse
    return PlainTextResponse(content="\n".join(lines), media_type="text/plain")


@app.get("/schema.json")
async def openapi_schema():
    """Explicit OpenAPI schema endpoint for crawlers that prefer /schema.json over /openapi.json."""
    return app.openapi()


@app.get("/manifest.json")
async def web_manifest():
    """Web app manifest for browser/agent discovery."""
    return {
        "name": "AIServices",
        "short_name": "AIServices",
        "description": "Paid data APIs for AI agents — crypto, DeFi, geo, web metadata",
        "start_url": "https://api.aiservices.to",
        "scope": "/",
        "display": "standalone",
        "categories": ["developer", "finance", "data"],
        "icons": [],
    }


@app.get("/api-docs", response_class=HTMLResponse)
async def api_docs_page():
    return HTMLResponse(content="<h1>AIServices</h1><p>Visit <a href='/docs'>/docs</a> for Swagger.</p>")
