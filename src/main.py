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
from mcp_endpoint import router as mcp_router

WALLET = os.environ.get("WALLET_ADDRESS", "0x1830DAdb0A16eb569B5f8526AADDF47ce85aC8e0")

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

# --- x402 Payment Protocol (Base Mainnet) ---
X402_WALLET = os.environ.get("WALLET_ADDRESS", WALLET)
X402_NETWORK = "eip155:84532"  # Base Sepolia testnet (default facilitator supports this)
X402_FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "https://x402.org/facilitator")

X402_ENABLED = False
X402_ERROR = "Not initialized"
try:
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption, CreateHeadersAuthProvider
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.http.types import RouteConfig
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.server import x402ResourceServer
    from x402.extensions.bazaar import bazaar_resource_server_extension
    from x402_payment import create_cdp_auth_headers, CDP_FACILITATOR_URL

    auth_provider = CreateHeadersAuthProvider(create_cdp_auth_headers)

    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(
            url=CDP_FACILITATOR_URL,
            auth_provider=auth_provider,
        )
    )
    payment_server = x402ResourceServer(facilitator)
    payment_server.register(X402_NETWORK, ExactEvmServerScheme())
    payment_server.register_extension(bazaar_resource_server_extension)

    payment_routes = {
        "POST /v1/disputes": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=X402_WALLET,
                    price="$0.05",
                    network=X402_NETWORK,
                ),
            ],
            mime_type="application/json",
            description="Submit a dispute for policy-driven ruling (AgentCourt engine)",
        ),
        "GET /v1/indicators/*": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=X402_WALLET,
                    price="$0.02",
                    network=X402_NETWORK,
                ),
            ],
            mime_type="application/json",
            description="Technical indicators: RSI, Bollinger Bands, ATR, Support/Resistance",
        ),
        "GET /v1/yields": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=X402_WALLET,
                    price="$0.02",
                    network=X402_NETWORK,
                ),
            ],
            mime_type="application/json",
            description="Top DeFi yield pools by TVL",
        ),
        "GET /v1/metadata": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=X402_WALLET,
                    price="$0.01",
                    network=X402_NETWORK,
                ),
            ],
            mime_type="application/json",
            description="URL metadata extraction and unfurling",
        ),
    }

    app.add_middleware(
        PaymentMiddlewareASGI,
        routes=payment_routes,
        server=payment_server,
    )
    print(f"[x402] Payment middleware enabled — disputes ($0.05), indicators/yields ($0.02), metadata ($0.01)", flush=True)
    X402_ENABLED = True
except ImportError as e:
    print(f"[x402] NOT installed — running in free mode. Error: {e}", flush=True)
    X402_ENABLED = False
    X402_ERROR = f"ImportError: {e}"
X402_ERROR = "Not initialized"
except Exception as e:
    import traceback
    print(f"[x402] Failed to initialize — running in free mode. Error: {e}", flush=True)
    traceback.print_exc()
    X402_ENABLED = False
    X402_ERROR = f"{type(e).__name__}: {e}"
X402_ERROR = "Not initialized"

# --- MCP Remote Transport ---
app.include_router(mcp_router)
print(f"[mcp] Remote MCP endpoint mounted at /mcp — 8 tools available", flush=True)


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
        "x402_error": X402_ERROR,
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


@app.get("/docs-page", response_class=HTMLResponse)
async def api_docs_page():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AIServices — Paid APIs for AI Agents</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;line-height:1.6}
.container{max-width:900px;margin:0 auto;padding:40px 20px}
header{text-align:center;margin-bottom:50px}
h1{font-size:2.5em;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px}
.tagline{font-size:1.1em;color:#888}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.85em;font-weight:600;margin:5px}
.badge-free{background:#1a3a1a;color:#4ade80;border:1px solid #4ade80}
.badge-paid{background:#3a2a1a;color:#fbbf24;border:1px solid #fbbf24}
.badge-x402{background:#2a1a3a;color:#a78bfa;border:1px solid #a78bfa}
section{background:#111;border-radius:12px;padding:25px;margin-bottom:20px;border:1px solid #222}
h2{font-size:1.4em;color:#60a5fa;margin-bottom:15px}
.endpoint{display:flex;align-items:flex-start;justify-content:space-between;padding:12px 0;border-bottom:1px solid #1a1a1a}
.endpoint:last-child{border-bottom:none}
.method{font-weight:700;font-family:monospace;font-size:0.9em;min-width:200px}
.GET{color:#4ade80}.POST{color:#fbbf24}
.price{font-weight:600;font-size:0.85em}
.desc{color:#999;font-size:0.9em;margin-top:4px}
code{background:#1a1a1a;padding:2px 6px;border-radius:4px;font-size:0.9em;color:#a78bfa}
pre{background:#1a1a1a;padding:15px;border-radius:8px;overflow-x:auto;margin:10px 0}
pre code{background:none;padding:0;color:#e0e0e0}
a{color:#60a5fa;text-decoration:none}
a:hover{text-decoration:underline}
.footer{text-align:center;padding:30px;color:#555;font-size:0.85em}
.wallet{font-family:monospace;font-size:0.85em;color:#666}
</style>
</head>
<body>
<div class="container">
<header>
<h1>AIServices</h1>
<p class="tagline">Paid APIs for AI Agents — Market Data + Dispute Resolution</p>
<div style="margin-top:10px">
<span class="badge badge-x402">x402 / USDC on Base</span>
<span class="badge badge-free">4 Free Endpoints</span>
<span class="badge badge-paid">4 Paid Endpoints</span>
</div>
</header>

<section>
<h2>Quick Start</h2>
<p>No signup. No API keys. Free endpoints work immediately. Paid endpoints use x402 micropayments.</p>
<pre><code># Free: Get BTC price
curl https://api.aiservices.to/v1/price/BTC

# Free: Batch prices
curl "https://api.aiservices.to/v1/prices?symbols=BTC,ETH,SOL"

# Free: Fear & Greed Index
curl https://api.aiservices.to/v1/fear-greed

# MCP: Connect your AI tool
# URL: https://api.aiservices.to/mcp (Streamable HTTP)</code></pre>
</section>

<section>
<h2>Market Data</h2>
<div class="endpoint">
<div><div class="method GET">GET /v1/price/{symbol}</div><div class="desc">Current crypto price (BTC, ETH, SOL, XRP...)</div></div>
<span class="badge badge-free">FREE</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/prices?symbols=BTC,ETH</div><div class="desc">Batch crypto prices</div></div>
<span class="badge badge-free">FREE</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/indicators/{symbol}</div><div class="desc">RSI, Bollinger Bands, ATR, Support/Resistance</div></div>
<span class="price">$0.02</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/yields</div><div class="desc">Top DeFi yield pools by TVL</div></div>
<span class="price">$0.02</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/fear-greed</div><div class="desc">Crypto Fear & Greed Index (0-100)</div></div>
<span class="badge badge-free">FREE</span>
</div>
</section>

<section>
<h2>Location & Web</h2>
<div class="endpoint">
<div><div class="method GET">GET /v1/geo/{ip}</div><div class="desc">IP geolocation lookup (country, city, ISP)</div></div>
<span class="badge badge-free">FREE</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/metadata?url=...</div><div class="desc">URL metadata extraction and unfurling</div></div>
<span class="price">$0.01</span>
</div>
</section>

<section>
<h2>Dispute Resolution (AgentCourt Engine)</h2>
<div class="endpoint">
<div><div class="method POST">POST /v1/disputes</div><div class="desc">Submit dispute for policy-driven ruling. 7 policies: freelance, milestone, SLA, API quality, bug bounty, scope, physical commerce.</div></div>
<span class="price">$0.05</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/policies</div><div class="desc">List dispute policy templates</div></div>
<span class="badge badge-free">FREE</span>
</div>
</section>

<section>
<h2>MCP Integration</h2>
<p>Connect AIServices directly to Claude, Cursor, or any MCP client:</p>
<pre><code>MCP Server URL: https://api.aiservices.to/mcp
Transport: Streamable HTTP</code></pre>
<p>8 tools available immediately. No installation required.</p>
</section>

<section>
<h2>Payments (x402)</h2>
<p>Paid endpoints use the <a href="https://x402.org" target="_blank">x402 protocol</a>. No API keys, no subscriptions.</p>
<ol style="padding-left:20px;color:#999">
<li>Agent requests a paid endpoint</li>
<li>Server returns HTTP 402 with payment details</li>
<li>Agent pays in USDC on Base Mainnet</li>
<li>Server verifies and returns data</li>
</ol>
<p class="wallet">Wallet: 0x1830DAdb0A16eb569B5f8526AADDF47ce85aC8e0</p>
</section>

<section>
<h2>Links</h2>
<p><a href="/docs">Swagger/OpenAPI Docs</a> · <a href="/llms.txt">llms.txt</a> · <a href="/health">Health Check</a> · <a href="https://github.com/vbkotecha/aiservices-api">GitHub</a></p>
</section>

<div class="footer">
<p>AIServices v2.0.0 — MIT License</p>
</div>
</div>
</body>
</html>
""")
