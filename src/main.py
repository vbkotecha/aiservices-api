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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto_data import get_price, get_multi_price, get_indicators, get_fear_greed, get_defi_yields
from geo_data import get_ip_geo
from web_data import get_url_metadata

WALLET = os.environ.get("WALLET_ADDRESS", "0x9863aB6242663FCc84c33632741711dB78f8Fd15")

app = FastAPI(
    title="AIServices",
    version="1.0.0",
    description="""Paid data APIs for AI agents — crypto prices, technical indicators, DeFi yields, IP geolocation, URL metadata.

All paid endpoints use x402 protocol with USDC on Base.
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
X402_NETWORK = "eip155:8453"

X402_ENABLED = False
try:
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption, CreateHeadersAuthProvider
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.http.types import RouteConfig
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.server import x402ResourceServer
    from x402_payment import create_cdp_auth_headers, CDP_FACILITATOR_URL

    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(
            url=CDP_FACILITATOR_URL,
            auth_provider=CreateHeadersAuthProvider(create_cdp_auth_headers),
        )
    )
    payment_server = x402ResourceServer(facilitator)
    payment_server.register(X402_NETWORK, ExactEvmServerScheme())
    payment_server.initialize()

    payment_routes = {
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
    print(f"[x402] Payment middleware enabled — indicators/yields ($0.02), metadata ($0.01)", flush=True)
    X402_ENABLED = True
except Exception as e:
    print(f"[x402] NOT loaded — running in free mode. Error: {e}", flush=True)
    X402_ENABLED = False


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
         responses={200: {"content": {"application/json": {"schema": {"type": "object", "properties": {"pools": {"type": "array"}}}}}}})
async def defi_yields():
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


# --- Health & Discovery ---

@app.get("/")
async def root():
    return {
        "name": "AIServices",
        "tagline": "Paid data APIs for AI agents",
        "version": "1.0.0",
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
        },
        "live": True,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "x402_enabled": X402_ENABLED,
        "services": ["crypto_prices", "indicators", "defi_yields", "fear_greed", "geo", "metadata"],
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


@app.get("/api-docs", response_class=HTMLResponse)
async def api_docs_page():
    return HTMLResponse(content="<h1>AIServices</h1><p>Visit <a href='/docs'>/docs</a> for Swagger.</p>")
