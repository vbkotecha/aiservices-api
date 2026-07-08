"""
AgentServices — Paid APIs for AI agents
Crypto market data, IP geolocation, URL metadata, marketing intelligence
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

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto_data import get_price, get_multi_price, get_indicators, get_fear_greed, get_defi_yields
from geo_data import get_ip_geo
from web_data import get_url_metadata
from search_data import web_search
from dex_data import get_swap_quote, get_trending_tokens, get_gas_tracker
from prediction_data import get_polymarket_markets, get_polymarket_market, get_prediction_summary
from news_data import get_crypto_news, get_social_trending, get_global_market
from engine.policy_engine import evaluate_dispute, list_policies
from mcp_endpoint import router as mcp_router
from marketing_data import (
    SentimentRequest, TrendRequest, CompetitorRequest, ContentGapRequest, AdCopyRequest,
    analyze_sentiment, detect_trends, analyze_competitors, find_content_gaps, generate_ad_copy,
)
from onchain_data import (
    get_whales, get_exchange_flows, get_correlation_matrix,
    get_defi_tvl, get_stablecoin_flows, get_github_velocity, get_agent_context, get_macro,
)
from synthesis_data import (
    get_token_risk, get_crypto_signal, get_hn_sentiment, get_npm_stats,
    get_github_trending, get_yield_comparison, deep_research, portfolio_intelligence,
    defi_strategy_report, market_pulse, onchain_overview, arbitrage_scanner,
)
from inference_gateway import list_models as list_inference_models, inference, quick_complete
from tradfi_data import get_stock_quote, get_stock_history, get_sec_filings, get_commodities, get_economic_indicators, get_fx_rates
from utility_data import extract_web_content, scan_package_security, seo_keywords
from agent_memory import store as mem_store, retrieve as mem_retrieve, list_keys as mem_list, delete as mem_delete, search as mem_search
from skill_packs import crypto_dossier, stock_dossier, market_overview, available_skills

AISERVICES_PAY_TO = "0x9863aB6242663FCc84c33632741711dB78f8Fd15"
WALLET = os.environ.get("WALLET_ADDRESS", AISERVICES_PAY_TO)

app = FastAPI(
    title="AgentServices",
    version="5.3.0",
    description="""Paid APIs for AI agents — data, intelligence, inference, and more.
Crypto market data, DeFi yields, DEX quotes, prediction markets, news, search, IP geolocation,
URL metadata, on-chain analytics, whale tracking, correlation matrix, DeFi TVL, stablecoin flows,
GitHub trending, npm stats, Hacker News sentiment, token risk scoring, crypto signals,
LLM inference gateway, marketing intelligence, and more.

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

# --- Security Headers + Bazaar Discovery Enrichment ---
# x402 indexers (CDP Bazaar / agentic.market) validate resources by GETting
# the live 402 response and checking for extensions.bazaar and
# resource.serviceName/tags. Without these, resources stay stuck in
# "processing" and never get indexed. This middleware enriches all 402
# responses with the required bazaar discovery metadata.
_BAZAAR_TAGS = ["data", "crypto", "defi", "search", "inference", "marketing-intelligence", "onchain", "analytics"]

@app.middleware("http")
async def enrich_402_bazaar(request, call_next):
    response = await call_next(request)
    # Security headers on all responses
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:;"
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Window"] = "60s"

    # Enrich 402 Payment Required responses with Bazaar discovery data
    if response.status_code == 402:
        # Get the payment-required header
        pr_header = response.headers.get("payment-required", "")
        if pr_header:
            try:
                import base64 as _b64
                import json as _json
                # Decode the base64 payment-required payload
                try:
                    decoded = _b64.b64decode(pr_header).decode()
                except Exception:
                    decoded = pr_header  # might already be raw JSON

                payload = _json.loads(decoded)

                # Fix resource URL: http -> https
                resource = payload.get("resource", {})
                if "url" in resource and resource["url"].startswith("http://"):
                    resource["url"] = resource["url"].replace("http://", "https://", 1)

                # Add serviceName and tags to resource (required by Bazaar indexers)
                resource["serviceName"] = "AgentServices"
                resource["tags"] = _BAZAAR_TAGS
                payload["resource"] = resource

                # Add extensions.bazaar to each accept entry
                route_path = resource.get("url", "").split("aiservices.to", 1)[-1] if "aiservices.to" in resource.get("url", "") else resource.get("url", "")
                route_desc = resource.get("description", "AgentServices API")

                for accept in payload.get("accepts", []):
                    # Fix payTo: ensure 0x prefix
                    pay_to = accept.get("payTo", "")
                    if pay_to and not pay_to.startswith("0x"):
                        accept["payTo"] = "0x" + pay_to

                    # Add bazaar extension if not present
                    if "extensions" not in accept:
                        accept["extensions"] = {}
                    if "bazaar" not in accept["extensions"]:
                        accept["extensions"]["bazaar"] = {
                            "name": "AgentServices",
                            "description": route_desc,
                        }

                # Re-encode and update header
                updated_json = _json.dumps(payload, separators=(',', ':'))
                updated_b64 = _b64.b64encode(updated_json.encode()).decode()
                response.headers["payment-required"] = updated_b64

            except Exception as e:
                # Don't break the response if enrichment fails
                print(f"[bazaar-enrich] Warning: failed to enrich 402: {e}", flush=True)

    return response

# --- x402 Payment Protocol (Base Mainnet) ---
# Payment receiver is intentionally separated from WALLET_ADDRESS so an agent
# consumer wallet cannot accidentally become the API revenue wallet in prod.
X402_WALLET = os.environ.get("X402_PAY_TO", os.environ.get("X402_WALLET_ADDRESS", AISERVICES_PAY_TO))
X402_BASE_NETWORK = "eip155:8453"
X402_BSC_NETWORK = "eip155:56"
X402_SVM_NETWORK = "solana:5eychk4D"  # Solana mainnet
X402_FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "https://api.cdp.coinbase.com/platform/v2/x402")

# Multi-chain: Dexter facilitator (x402.dexter.cash) supports Base + BSC + more.
# CDP facilitator supports Base + Solana. We detect and register accordingly.
X402_IS_MULTICHAIN = any(d in X402_FACILITATOR_URL.lower() for d in ("dexter", "infra402", "aeon"))

# Build network list: Always Base, add Solana (CDP supports it), add BSC if multichain facilitator
X402_NETWORKS = [X402_BASE_NETWORK, X402_SVM_NETWORK] + ([X402_BSC_NETWORK] if X402_IS_MULTICHAIN else [])
X402_NETWORK_LABEL = "Base + Solana" + (" + BSC" if X402_IS_MULTICHAIN else "")

X402_ENABLED = False
X402_ERROR = "Not initialized"
try:
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption, CreateHeadersAuthProvider
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.http.types import RouteConfig
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.server import x402ResourceServer
    from x402.extensions.bazaar import bazaar_resource_server_extension

    # Build facilitator — CDP needs JWT auth headers, others (Dexter) are open
    facilitator_config_kwargs = {"url": X402_FACILITATOR_URL}
    if not X402_IS_MULTICHAIN:
        from x402_payment import create_cdp_auth_headers, CDP_FACILITATOR_URL
        facilitator_config_kwargs["url"] = CDP_FACILITATOR_URL
        facilitator_config_kwargs["auth_provider"] = CreateHeadersAuthProvider(create_cdp_auth_headers)

    facilitator = HTTPFacilitatorClient(FacilitatorConfig(**facilitator_config_kwargs))
    payment_server = x402ResourceServer(facilitator)
    # Register EVM networks (Base, BSC)
    payment_server.register(X402_BASE_NETWORK, ExactEvmServerScheme())
    if X402_IS_MULTICHAIN:
        payment_server.register(X402_BSC_NETWORK, ExactEvmServerScheme())
    # Register Solana (SVM) — CDP facilitator supports Solana mainnet
    try:
        from x402.mechanisms.svm.exact import ExactSvmServerScheme
        payment_server.register(X402_SVM_NETWORK, ExactSvmServerScheme())
        print(f"[x402] Solana (SVM) support registered on {X402_SVM_NETWORK}", flush=True)
    except Exception as svm_err:
        print(f"[x402] WARNING: SVM scheme registration failed: {svm_err}", flush=True)
        X402_NETWORKS = [n for n in X402_NETWORKS if n != X402_SVM_NETWORK]
        X402_NETWORK_LABEL = "Base" + (" + BSC" if X402_IS_MULTICHAIN else "")
    payment_server.register_extension(bazaar_resource_server_extension)

    def _payment_options(wallet: str, price: str) -> list:
        """Generate PaymentOption for every supported network (multi-chain)."""
        options = []
        for net in X402_NETWORKS:
            if net.startswith("solana:"):
                # Solana needs a separate SPL wallet address
                svm_wallet = os.environ.get("X402_SVM_PAY_TO", "")
                if svm_wallet:
                    options.append(PaymentOption(scheme="exact", pay_to=svm_wallet, price=price, network=net))
            else:
                options.append(PaymentOption(scheme="exact", pay_to=wallet, price=price, network=net))
        return options

    payment_routes = {
        "POST /v1/disputes": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Submit a dispute for policy-driven ruling (AgentCourt engine)",
        ),
        "GET /v1/indicators/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Technical indicators: RSI, Bollinger Bands, ATR, Support/Resistance",
        ),
        "GET /v1/yields": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Top DeFi yield pools by TVL",
        ),
        "GET /v1/metadata": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="URL metadata extraction and unfurling",
        ),
        "GET /v1/search": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="AI-powered web search with structured results",
        ),
        "POST /v1/marketing/sentiment": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="AI brand sentiment analysis across platforms",
        ),
        "POST /v1/marketing/trends": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Industry trend detection with velocity scores",
        ),
        "POST /v1/marketing/competitors": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Competitive intelligence — keywords, channels, strategy",
        ),
        "POST /v1/marketing/content-gaps": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.04"),
            mime_type="application/json",
            description="SEO content gap analysis",
        ),
        "POST /v1/marketing/ad-copy": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="AI ad copy generator for Google/Meta/TikTok/Taboola",
        ),
        "GET /v1/whales": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Large whale transactions on BTC and ETH chains",
        ),
        "GET /v1/exchange-flows": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="CEX reserve flows and 24h changes",
        ),
        "GET /v1/correlation": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="30-day cross-asset correlation matrix",
        ),
        "GET /v1/defi-tvl": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="DeFi protocol TVL rankings from DeFi Llama",
        ),
        "GET /v1/stablecoin-flows": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Stablecoin market caps and supply data",
        ),
        "GET /v1/github-velocity": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="GitHub crypto repo velocity scores",
        ),
        "GET /v1/macro": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Macro economic and crypto indicators",
        ),
        # --- NEW: Inference Gateway (BlockRun competitor) ---
        "POST /v1/inference": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="LLM inference gateway — chat completions via gpt-5.4/5.4-mini/5.5",
        ),
        "POST /v1/complete": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Quick text completion — send a prompt, get a response",
        ),
        # --- NEW: Synthesis Endpoints ---
        "GET /v1/token-risk/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Token risk scoring — volatility, liquidity, market cap analysis",
        ),
        "GET /v1/signals/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.04"),
            mime_type="application/json",
            description="Crypto buy/sell signals synthesized from technical indicators",
        ),
        "GET /v1/hn-sentiment": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Hacker News tech sentiment analysis",
        ),
        "GET /v1/npm-stats/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="NPM package download statistics and trend analysis",
        ),
        "GET /v1/github-trending": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="GitHub trending repositories",
        ),
        "GET /v1/yield-comparison": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="DeFi yield comparison with risk-adjusted analysis",
        ),
        # --- NEW: Traditional Finance (gap fillers) ---
        "GET /v1/stocks/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Real-time stock quotes from Yahoo Finance",
        ),
        "GET /v1/stocks/*/history": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Historical OHLCV stock data",
        ),
        "GET /v1/sec/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="SEC filings parser — 10-K, 10-Q, 8-K, Form 4 from EDGAR",
        ),
        "GET /v1/commodities": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Commodity prices — oil, gold, silver, copper, wheat, more",
        ),
        "GET /v1/economic": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="US economic indicators — CPI, GDP, unemployment, Fed rate",
        ),
        "GET /v1/fx": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.003"),
            mime_type="application/json",
            description="Real-time FX/forex rates for 30+ currencies",
        ),
        # --- NEW: Utility (gap fillers) ---
        "GET /v1/extract": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.002"),
            mime_type="application/json",
            description="Web content extraction — clean text from any URL",
        ),
        "GET /v1/security/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Package security scan — check PyPI/npm for vulnerabilities",
        ),
        "GET /v1/seo/keywords": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="SEO keyword research — volume estimates and competition",
        ),
        # --- NEW: Deep Research (flagship bundled endpoint) ---
        "GET /v1/research": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Deep research — search + extract + synthesize in one call",
        ),
        # --- NEW: Portfolio Intelligence (bundled endpoint) ---
        "GET /v1/portfolio": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.10"),
            mime_type="application/json",
            description="Portfolio intelligence — price + signal + risk + sentiment in one call",
        ),
        # --- NEW: DeFi Strategy Report (high-value bundled) ---
        "GET /v1/defi-strategy": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.25"),
            mime_type="application/json",
            description="DeFi strategy report — yields + TVL + comparison + risk in one call",
        ),
        # --- NEW: Market Pulse (rapid snapshot) ---
        "GET /v1/market-pulse": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Market pulse — sentiment + trending + news + social + whales + global in one call",
        ),
        "GET /v1/onchain-overview": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.15"),
            mime_type="application/json",
            description="On-chain overview — whales + exchange flows + stablecoin flows + correlation + DeFi TVL",
        ),
        "GET /v1/arbitrage": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.08"),
            mime_type="application/json",
            description="Cross-DEX arbitrage scanner — price discrepancies, gas-adjusted profitability, slippage modeling",
        ),
        # --- Agent Memory (retention hook) ---
        "POST /v1/memory/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="Store agent memory — persistent wallet-keyed KV",
        ),
        "GET /v1/memory/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="Retrieve agent memory",
        ),
        "DELETE /v1/memory/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="Delete agent memory entry",
        ),
        "POST /v1/memory/search": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Semantic search across agent memory",
        ),
        # --- Skill Packs (bundled intelligence) ---
        "POST /v1/skills/crypto-dossier": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.10"),
            mime_type="application/json",
            description="Crypto dossier — price + indicators + risk + signal + fear/greed + whales in one call",
        ),
        "POST /v1/skills/stock-dossier": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Stock dossier — quote + FX rates + sentiment in one call",
        ),
        "GET /v1/skills/market-overview": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Market pulse — fear/greed + BTC signal + whales + regime classification",
        ),
    }

    app.add_middleware(
        PaymentMiddlewareASGI,
        routes=payment_routes,
        server=payment_server,
    )
    print(f"[x402] Payment middleware enabled on {X402_NETWORK_LABEL} — disputes ($0.05), indicators/yields/correlation ($0.02–$0.03), metadata/search ($0.01), marketing ($0.03–$0.05), on-chain data ($0.02–$0.03)", flush=True)
    X402_ENABLED = True
    X402_ERROR = None

    # CRITICAL: Bazaar discovery enrichment middleware — must be added AFTER
    # PaymentMiddlewareASGI so it's the outermost layer and can intercept 402
    # responses from the x402 middleware. Without this, CDP Bazaar indexers
    # never see extensions.bazaar in the live 402 and resources stay stuck
    # in "processing" — never appearing on agentic.market.
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response as StarletteResponse
    import base64 as _b64_enrich
    import json as _json_enrich

    _ENRICH_TAGS = ["data", "crypto", "defi", "search", "inference", "marketing-intelligence", "onchain", "analytics"]

    class BazaarEnrichmentMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if response.status_code == 402:
                pr_header = response.headers.get("payment-required", "")
                if pr_header:
                    try:
                        # Try base64 decode first, then raw JSON
                        try:
                            decoded = _b64_enrich.b64decode(pr_header).decode()
                        except Exception:
                            decoded = pr_header

                        payload = _json_enrich.loads(decoded)

                        # Fix resource URL: http -> https
                        resource = payload.get("resource", {})
                        if "url" in resource and resource["url"].startswith("http://"):
                            resource["url"] = resource["url"].replace("http://", "https://", 1)

                        # Add serviceName and tags to resource (Bazaar indexer requirement)
                        resource["serviceName"] = "AgentServices"
                        resource["tags"] = _ENRICH_TAGS
                        payload["resource"] = resource

                        route_desc = resource.get("description", "AgentServices API")

                        # Enrich accepts with bazaar extension + fix payTo
                        for accept in payload.get("accepts", []):
                            # Fix payTo: ensure 0x prefix
                            pay_to = accept.get("payTo", "")
                            if pay_to and not pay_to.startswith("0x"):
                                accept["payTo"] = "0x" + pay_to

                            # Add bazaar extension
                            if "extensions" not in accept:
                                accept["extensions"] = {}
                            if "bazaar" not in accept["extensions"]:
                                accept["extensions"]["bazaar"] = {
                                    "name": "AgentServices",
                                    "description": route_desc,
                                }

                        # Re-encode and update header
                        updated_json = _json_enrich.dumps(payload, separators=(',', ':'))
                        updated_b64 = _b64_enrich.b64encode(updated_json.encode()).decode()
                        response.headers["payment-required"] = updated_b64
                        print(f"[bazaar-enrich] Enriched 402 for {resource.get('url', 'unknown')}", flush=True)

                    except Exception as e:
                        print(f"[bazaar-enrich] Warning: failed to enrich 402: {e}", flush=True)

            return response

    app.add_middleware(BazaarEnrichmentMiddleware)
    print("[bazaar-enrich] Bazaar discovery enrichment middleware enabled", flush=True)

except ImportError as e:
    print(f"[x402] NOT installed — running in free mode. Error: {e}", flush=True)
    X402_ENABLED = False
    X402_ERROR = f"ImportError: {e}"
except Exception as e:
    import traceback
    print(f"[x402] Failed to initialize — running in free mode. Error: {e}", flush=True)
    traceback.print_exc()
    X402_ENABLED = False
    X402_ERROR = f"{type(e).__name__}: {e}"

# --- MCP Remote Transport ---
app.include_router(mcp_router)
print(f"[mcp] Remote MCP endpoint mounted at /mcp — 21 tools available", flush=True)


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


# --- Web Search ---

@app.get("/v1/search", tags=["Search"],
         summary="Web Search",
         description="AI-powered web search. Returns structured results with titles, URLs, and snippets. Uses Exa if API key available, otherwise DuckDuckGo.")
async def search_web(q: str, num: int = 5):
    """Web search — structured results ($0.01 via x402)"""
    return web_search(q, num)


# --- DEX / Trading ---

@app.get("/v1/swap/quote", tags=["DEX"],
         summary="DEX Swap Quote",
         description="Get a swap quote from 0x API across Ethereum, Base, Polygon, Arbitrum, Optimism, BSC.")
async def swap_quote(
    chain: str = "ethereum",
    sellToken: str = "WETH",
    buyToken: str = "USDC",
    sellAmount: str = "1000000000000000000",
):
    """Get DEX swap quote from 0x API (FREE)"""
    return get_swap_quote(chain, sellToken, buyToken, sell_amount=sellAmount)


@app.get("/v1/trending", tags=["Market Data"],
         summary="Trending Tokens",
         description="Get trending tokens and coins being searched right now on CoinGecko.")
async def trending_tokens():
    """Trending tokens — most searched right now (FREE)"""
    return get_trending_tokens()


@app.get("/v1/gas", tags=["Market Data"],
         summary="Gas Tracker",
         description="Current gas prices for Ethereum (slow, standard, fast) in Gwei.")
async def gas_tracker():
    """Current gas prices (FREE)"""
    return get_gas_tracker()


# --- Prediction Markets ---

@app.get("/v1/predictions", tags=["Prediction Markets"],
         summary="Prediction Markets",
         description="Get active prediction markets from Polymarket ranked by 24h volume.")
async def prediction_markets(limit: int = 20):
    """Active prediction markets from Polymarket (FREE)"""
    return get_polymarket_markets(limit=limit)


@app.get("/v1/predictions/{slug}", tags=["Prediction Markets"],
         summary="Prediction Market Details",
         description="Get details for a specific Polymarket prediction market.")
async def prediction_market_detail(slug: str):
    """Specific prediction market details (FREE)"""
    return get_polymarket_market(slug)


# --- News & Social ---

@app.get("/v1/news", tags=["News"],
         summary="Crypto News",
         description="Latest crypto and blockchain news from multiple sources.")
async def crypto_news(limit: int = 20):
    """Latest crypto news (FREE)"""
    return get_crypto_news(limit=limit)


@app.get("/v1/social", tags=["News"],
         summary="Social Trending",
         description="Trending crypto topics: coins, categories, and NFTs being discussed.")
async def social_trending():
    """Social trending — coins, categories, NFTs (FREE)"""
    return get_social_trending()


@app.get("/v1/global", tags=["Market Data"],
         summary="Global Market Stats",
         description="Global crypto market data: total market cap, volume, BTC dominance.")
async def global_market():
    """Global market stats (FREE)"""
    return get_global_market()


# --- Marketing Intelligence (AI-Powered) ---

@app.post("/v1/marketing/sentiment", tags=["Marketing Intelligence"],
          summary="Brand Sentiment Analysis",
          description="AI-powered brand sentiment analysis across platforms. Uses GPT-4o-mini for real-time analysis.")
async def marketing_sentiment(req: SentimentRequest):
    """Brand sentiment analysis (FREE during beta)"""
    return analyze_sentiment(req.brand, req.platforms)

@app.post("/v1/marketing/trends", tags=["Marketing Intelligence"],
          summary="Industry Trend Detection",
          description="Detect trending marketing topics in any industry with velocity scores and content recommendations.")
async def marketing_trends(req: TrendRequest):
    """Industry trend detection (FREE during beta)"""
    return detect_trends(req.industry, req.limit)

@app.post("/v1/marketing/competitors", tags=["Marketing Intelligence"],
          summary="Competitive Intelligence",
          description="AI-powered competitor analysis: keywords, channels, content strategy, and actionable recommendations.")
async def marketing_competitors(req: CompetitorRequest):
    """Competitive intelligence (FREE during beta)"""
    return analyze_competitors(req.competitor_url, req.your_url)

@app.post("/v1/marketing/content-gaps", tags=["Marketing Intelligence"],
          summary="Content Gap Analysis",
          description="Find SEO content gaps between you and competitors. Includes keyword opportunities with difficulty scores.")
async def marketing_content_gaps(req: ContentGapRequest):
    """Content gap analysis (FREE during beta)"""
    return find_content_gaps(req.your_domain, req.competitor_domains)

@app.post("/v1/marketing/ad-copy", tags=["Marketing Intelligence"],
          summary="AI Ad Copy Generator",
          description="Generate ad copy variations for Google, Meta, TikTok, or Taboola. Platform-specific constraints and tone control.")
async def marketing_ad_copy(req: AdCopyRequest):
    """AI ad copy generation (FREE during beta)"""
    return generate_ad_copy(req.product, req.platform, req.tone, req.count)



# --- On-Chain & Advanced Data (Gap Fillers) ---

@app.get("/v1/whales", tags=["On-Chain Data"],
         summary="Large Transaction Tracking",
         description="Whale transactions: large BTC (>=10 BTC) and ETH movements from public blockchain APIs. ($0.02)")
async def whale_tracking(limit: int = 50, min_btc: float = 10.0):
    """Large on-chain whale transactions ($0.02)"""
    return get_whales()

@app.get("/v1/exchange-flows", tags=["On-Chain Data"],
         summary="CEX Reserve Flows",
         description="Centralized exchange reserves and 24h changes from DeFi Llama transparency data. ($0.02)")
async def exchange_flows(limit: int = 20):
    """CEX inflow/outflow tracking ($0.02)"""
    return get_exchange_flows()

@app.get("/v1/correlation", tags=["Market Data"],
         summary="Cross-Asset Correlation Matrix",
         description="30-day Pearson correlations across top crypto assets (BTC, ETH, SOL, XRP, BNB, etc.). ($0.03)")
async def correlation_matrix(days: int = 30):
    """Cross-asset correlation matrix ($0.03)"""
    return get_correlation_matrix()

@app.get("/v1/defi-tvl", tags=["DeFi"],
         summary="DeFi Protocol TVL Rankings",
         description="Top DeFi protocols ranked by Total Value Locked from DeFi Llama. ($0.02)")
async def defi_tvl(limit: int = 20, chain: str = "all"):
    """DeFi protocol TVL rankings ($0.02)"""
    return get_defi_tvl(limit, chain)

@app.get("/v1/stablecoin-flows", tags=["On-Chain Data"],
         summary="Stablecoin Market Caps & Flows",
         description="Top stablecoins by market cap with supply data from DeFi Llama. ($0.02)")
async def stablecoin_flows(limit: int = 20):
    """Stablecoin supply and flows ($0.02)"""
    return get_stablecoin_flows()

@app.get("/v1/github-velocity", tags=["Developer Activity"],
         summary="GitHub Repo Velocity Scores",
         description="Trending crypto/web3 GitHub repos with computed velocity scores. ($0.02)")
async def github_velocity(language: str = "", limit: int = 15):
    """GitHub repo activity with velocity scoring ($0.02)"""
    return get_github_velocity(language, limit)

@app.get("/v1/agent-context", tags=["AI Agent Tools"],
         summary="Paste-Ready Agent Context",
         description="Composed multi-source market context in a single paste-ready payload for LLM system prompts. (FREE)")
async def agent_context():
    """Composed context for AI agents (FREE)"""
    return get_agent_context()

@app.get("/v1/macro", tags=["Market Data"],
         summary="Macro Economic Indicators",
         description="Crypto-macro indicators: global market cap, dominance, derivatives data. ($0.02)")
async def macro_indicators(currency: str = "usd"):
    """Macro economic indicators ($0.02)"""
    return get_macro()


# --- Health & Discovery ---

_landing_html = None
def _get_landing():
    global _landing_html
    if _landing_html is None:
        landing_path = Path(__file__).parent / "landing.html"
        if landing_path.exists():
            _landing_html = landing_path.read_text()
        else:
            _landing_html = "<h1>AgentServices</h1>"
    return _landing_html


@app.get("/")
async def root(request: Request):
    """Route based on domain: agentservices.to serves website HTML, all paths serve API."""
    host = request.headers.get("host", "").split(":")[0].lower()
    if host.startswith("api."):
        return {
            "name": "AgentServices",
            "tagline": "Paid APIs for AI agents — data, inference, and market intelligence",
            "version": "5.3.0",
            "payment": "x402 / USDC on Base",
            "wallet": X402_WALLET,
            "services": {
                "market_data": {
                    "price": {"endpoint": "GET /v1/price/{symbol}", "price": "free", "desc": "Current crypto price"},
                    "batch_prices": {"endpoint": "GET /v1/prices?symbols=BTC,ETH", "price": "free", "desc": "Batch crypto prices"},
                    "indicators": {"endpoint": "GET /v1/indicators/{symbol}", "price": "$0.02", "desc": "RSI, Bollinger Bands, ATR, Support/Resistance"},
                    "yields": {"endpoint": "GET /v1/yields", "price": "$0.02", "desc": "Top DeFi yield pools by TVL"},
                    "fear_greed": {"endpoint": "GET /v1/fear-greed", "price": "free", "desc": "Crypto Fear & Greed Index"},
                    "global": {"endpoint": "GET /v1/global", "price": "free", "desc": "Global market cap, volume, BTC dominance"},
                    "trending": {"endpoint": "GET /v1/trending", "price": "free", "desc": "Trending tokens right now"},
                    "gas": {"endpoint": "GET /v1/gas", "price": "free", "desc": "Current ETH gas prices"},
                },
                "search": {
                    "web_search": {"endpoint": "GET /v1/search?q=...", "price": "$0.01", "desc": "AI-powered web search"},
                },
                "dex": {
                    "swap_quote": {"endpoint": "GET /v1/swap/quote", "price": "free", "desc": "DEX swap quote (0x API, 6 chains)"},
                },
                "prediction_markets": {
                    "markets": {"endpoint": "GET /v1/predictions", "price": "free", "desc": "Active Polymarket prediction markets"},
                    "detail": {"endpoint": "GET /v1/predictions/{slug}", "price": "free", "desc": "Specific market details"},
                },
                "news_social": {
                    "news": {"endpoint": "GET /v1/news", "price": "free", "desc": "Latest crypto news"},
                    "social_trending": {"endpoint": "GET /v1/social", "price": "free", "desc": "Trending coins, categories, NFTs"},
                },
                "dispute_resolution": {
                    "file_dispute": {"endpoint": "POST /v1/disputes", "price": "$0.05", "desc": "Submit dispute for policy-driven ruling (AgentCourt engine)"},
                    "policies": {"endpoint": "GET /v1/policies", "price": "free", "desc": "List dispute policy templates"},
                },
            },
            "live": True,
        }
    return HTMLResponse(content=_get_landing())


@app.get("/api")
async def api_discovery():
    """API discovery JSON for agents and crawlers."""
    return {
        "name": "AgentServices",
        "tagline": "Paid APIs for AI agents — data, inference, and market intelligence",
        "version": "3.0.0",
        "payment": "x402 / USDC on Base",
        "wallet": X402_WALLET,
        "services": {
            "market_data": {
                "price": {"endpoint": "GET /v1/price/{symbol}", "price": "free", "desc": "Current crypto price"},
                "batch_prices": {"endpoint": "GET /v1/prices?symbols=BTC,ETH", "price": "free", "desc": "Batch crypto prices"},
                "indicators": {"endpoint": "GET /v1/indicators/{symbol}", "price": "$0.02", "desc": "RSI, Bollinger Bands, ATR, Support/Resistance"},
                "yields": {"endpoint": "GET /v1/yields", "price": "$0.02", "desc": "Top DeFi yield pools by TVL"},
                "fear_greed": {"endpoint": "GET /v1/fear-greed", "price": "free", "desc": "Crypto Fear & Greed Index"},
                "global": {"endpoint": "GET /v1/global", "price": "free", "desc": "Global market cap, volume, BTC dominance"},
                "trending": {"endpoint": "GET /v1/trending", "price": "free", "desc": "Trending tokens right now"},
                "gas": {"endpoint": "GET /v1/gas", "price": "free", "desc": "Current ETH gas prices"},
            },
            "search": {
                "web_search": {"endpoint": "GET /v1/search?q=...", "price": "$0.01", "desc": "AI-powered web search"},
                "deep_research": {"endpoint": "GET /v1/research?q=...", "price": "$0.05", "desc": "Search + extract + synthesize in one call"},
                "portfolio_intelligence": {"endpoint": "GET /v1/portfolio?symbol=...", "price": "$0.10", "desc": "Price + signal + risk + sentiment in one call"},
                "defi_strategy": {"endpoint": "GET /v1/defi-strategy?chain=...", "price": "$0.25", "desc": "DeFi yields + TVL + comparison + risk analysis"},
                "market_pulse": {"endpoint": "GET /v1/market-pulse", "price": "$0.05", "desc": "Sentiment + trending + news + whales + global in one call"},
                "onchain_overview": {"endpoint": "GET /v1/onchain-overview", "price": "$0.15", "desc": "Whales + exchange flows + stablecoin flows + correlation + DeFi TVL"},
                "arbitrage_scanner": {"endpoint": "GET /v1/arbitrage?symbols=BTC,ETH,SOL", "price": "$0.08", "desc": "Cross-DEX price discrepancies + gas-adjusted profitability modeling"},
            },
            "dex": {
                "swap_quote": {"endpoint": "GET /v1/swap/quote", "price": "free", "desc": "DEX swap quote (0x API, 6 chains)"},
            },
            "prediction_markets": {
                "markets": {"endpoint": "GET /v1/predictions", "price": "free", "desc": "Active Polymarket prediction markets"},
                "detail": {"endpoint": "GET /v1/predictions/{slug}", "price": "free", "desc": "Specific market details"},
            },
            "news_social": {
                "news": {"endpoint": "GET /v1/news", "price": "free", "desc": "Latest crypto news"},
                "social_trending": {"endpoint": "GET /v1/social", "price": "free", "desc": "Trending coins, categories, NFTs"},
            },
            "dispute_resolution": {
                "file_dispute": {"endpoint": "POST /v1/disputes", "price": "$0.05", "desc": "Submit dispute for policy-driven ruling (AgentCourt engine)"},
                "policies": {"endpoint": "GET /v1/policies", "price": "free", "desc": "List dispute policy templates"},
            },
            "marketing_intelligence": {
                "sentiment": {"endpoint": "POST /v1/marketing/sentiment", "price": "$0.03", "desc": "Brand sentiment analysis (AI-powered)"},
                "trends": {"endpoint": "POST /v1/marketing/trends", "price": "$0.03", "desc": "Industry trend detection"},
                "competitors": {"endpoint": "POST /v1/marketing/competitors", "price": "$0.05", "desc": "Competitive intelligence"},
                "content_gaps": {"endpoint": "POST /v1/marketing/content-gaps", "price": "$0.04", "desc": "SEO content gap analysis"},
                "ad_copy": {"endpoint": "POST /v1/marketing/ad-copy", "price": "$0.05", "desc": "AI ad copy generation"},
            },
            "onchain_data": {
                "whales": {"endpoint": "GET /v1/whales", "price": "$0.02", "desc": "Large whale transactions on BTC/ETH"},
                "exchange_flows": {"endpoint": "GET /v1/exchange-flows", "price": "$0.02", "desc": "CEX reserve flows"},
                "stablecoin_flows": {"endpoint": "GET /v1/stablecoin-flows", "price": "$0.02", "desc": "Stablecoin market caps and supply"},
            },
            "advanced_market_data": {
                "correlation": {"endpoint": "GET /v1/correlation", "price": "$0.03", "desc": "30-day cross-asset correlation matrix"},
                "defi_tvl": {"endpoint": "GET /v1/defi-tvl", "price": "$0.02", "desc": "DeFi protocol TVL rankings"},
                "macro": {"endpoint": "GET /v1/macro", "price": "$0.02", "desc": "Macro economic indicators"},
            },
            "developer_activity": {
                "github_velocity": {"endpoint": "GET /v1/github-velocity", "price": "$0.02", "desc": "GitHub crypto repo velocity scores"},
            },
            "agent_tools": {
                "agent_context": {"endpoint": "GET /v1/agent-context", "price": "free", "desc": "Paste-ready market context for LLMs"},
            },
        },
        "live": True,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "5.3.0",
        "x402_enabled": X402_ENABLED,
        "x402_error": X402_ERROR,
        "x402_networks": X402_NETWORKS,
        "x402_facilitator": X402_FACILITATOR_URL,
        "services": ["crypto_prices", "indicators", "defi_yields", "fear_greed", "geo", "metadata", "search", "swap_quote", "trending", "gas", "predictions", "news", "social_trending", "global", "disputes", "policies", "marketing_sentiment", "marketing_trends", "marketing_competitors", "marketing_content_gaps", "marketing_ad_copy", "whales", "exchange_flows", "correlation", "defi_tvl", "stablecoin_flows", "github_velocity", "agent_context", "macro", "inference", "quick_complete", "token_risk", "crypto_signals", "hn_sentiment", "npm_stats", "github_trending", "yield_comparison", "stock_quote", "stock_history", "sec_filings", "commodities", "economic_indicators", "fx_rates", "web_extract", "package_security", "seo_keywords", "deep_research", "portfolio_intelligence", "defi_strategy", "market_pulse", "onchain_overview", "arbitrage_scanner"],
    }


@app.get("/.well-known/x402")
async def x402_manifest():
    """x402 payment manifest for agent discovery."""
    endpoints = [
        {"path": "/v1/price/{symbol}", "method": "GET", "price": "$0.00", "description": "Current crypto price (FREE)"},
        {"path": "/v1/prices", "method": "GET", "price": "$0.00", "description": "Batch crypto prices (FREE)"},
        {"path": "/v1/fear-greed", "method": "GET", "price": "$0.00", "description": "Crypto Fear and Greed Index (FREE)"},
        {"path": "/v1/global", "method": "GET", "price": "$0.00", "description": "Global market cap, volume, dominance (FREE)"},
        {"path": "/v1/trending", "method": "GET", "price": "$0.00", "description": "Trending tokens (FREE)"},
        {"path": "/v1/gas", "method": "GET", "price": "$0.00", "description": "Current ETH gas prices (FREE)"},
        {"path": "/v1/geo/{ip}", "method": "GET", "price": "$0.00", "description": "IP geolocation lookup (FREE)"},
        {"path": "/v1/swap/quote", "method": "GET", "price": "$0.00", "description": "DEX swap quote across 6 chains (FREE)"},
        {"path": "/v1/predictions", "method": "GET", "price": "$0.00", "description": "Active prediction markets (FREE)"},
        {"path": "/v1/news", "method": "GET", "price": "$0.00", "description": "Latest crypto news (FREE)"},
        {"path": "/v1/social", "method": "GET", "price": "$0.00", "description": "Trending coins, categories, NFTs (FREE)"},
        {"path": "/v1/policies", "method": "GET", "price": "$0.00", "description": "List dispute resolution policy templates (FREE)"},
        {"path": "/mcp", "method": "POST", "price": "$0.00", "description": "Remote MCP server for AI agent integration (FREE)"},
        {"path": "/v1/indicators/{symbol}", "method": "GET", "price": "$0.02", "description": "Technical indicators: RSI, BB, ATR, S/R"},
        {"path": "/v1/yields", "method": "GET", "price": "$0.02", "description": "Top DeFi yield pools by TVL"},
        {"path": "/v1/metadata", "method": "GET", "price": "$0.01", "description": "URL metadata extraction and unfurling"},
        {"path": "/v1/search", "method": "GET", "price": "$0.01", "description": "AI-powered web search with structured results"},
        {"path": "/v1/disputes", "method": "POST", "price": "$0.05", "description": "Policy-driven dispute resolution (7 policy templates)"},
        {"path": "/v1/marketing/sentiment", "method": "POST", "price": "$0.03", "description": "AI brand sentiment analysis across platforms"},
        {"path": "/v1/marketing/trends", "method": "POST", "price": "$0.03", "description": "Industry trend detection with velocity scores"},
        {"path": "/v1/marketing/competitors", "method": "POST", "price": "$0.05", "description": "Competitive intelligence: keywords, channels, strategy"},
        {"path": "/v1/marketing/content-gaps", "method": "POST", "price": "$0.04", "description": "SEO content gap analysis"},
        {"path": "/v1/marketing/ad-copy", "method": "POST", "price": "$0.05", "description": "AI ad copy generator for paid channels"},
        {"path": "/v1/whales", "method": "GET", "price": "$0.02", "description": "Large whale transactions on BTC and ETH chains"},
        {"path": "/v1/exchange-flows", "method": "GET", "price": "$0.02", "description": "CEX reserve flows and 24h changes"},
        {"path": "/v1/correlation", "method": "GET", "price": "$0.03", "description": "30-day cross-asset correlation matrix"},
        {"path": "/v1/defi-tvl", "method": "GET", "price": "$0.02", "description": "DeFi protocol TVL rankings from DeFi Llama"},
        {"path": "/v1/stablecoin-flows", "method": "GET", "price": "$0.02", "description": "Stablecoin market caps and supply data"},
        {"path": "/v1/github-velocity", "method": "GET", "price": "$0.02", "description": "GitHub crypto repo velocity scores"},
        {"path": "/v1/macro", "method": "GET", "price": "$0.02", "description": "Macro economic and crypto indicators"},
        {"path": "/v1/research", "method": "GET", "price": "$0.05", "description": "Deep research — search + extract + synthesize in one call"},
        {"path": "/v1/portfolio", "method": "GET", "price": "$0.10", "description": "Portfolio intelligence — price + signal + risk + sentiment in one call"},
        {"path": "/v1/defi-strategy", "method": "GET", "price": "$0.25", "description": "DeFi strategy report — yields + TVL + comparison + risk analysis"},
        {"path": "/v1/market-pulse", "method": "GET", "price": "$0.05", "description": "Market pulse — sentiment + trending + news + whales + global snapshot"},
        {"path": "/v1/onchain-overview", "method": "GET", "price": "$0.15", "description": "On-chain overview — whales + exchange flows + stablecoin flows + correlation + DeFi TVL"},
    ]
    paid_endpoints = [endpoint for endpoint in endpoints if endpoint["price"] != "$0.00"]
    return {
        "version": "1.0",
        "name": "AgentServices",
        "description": "Paid data APIs for AI agents — crypto, DeFi, on-chain analytics, search, marketing intelligence, and dispute resolution",
        "networks": X402_NETWORKS,
        "chain_id": X402_NETWORKS[0] if X402_NETWORKS else "eip155:8453",
        "currency": "USDC",
        "endpoints": endpoints,
        "paid_endpoints": paid_endpoints,
        "paid_endpoint_count": len(paid_endpoints),
        "categories": ["Data", "Market Data", "On-chain Analytics", "Geolocation", "DEX", "Prediction Markets", "Search", "News", "Governance", "Dispute Resolution", "MCP", "Marketing Intelligence"],
        "payTo": X402_WALLET,
        "contact": "https://github.com/vbkotecha",
        "website": "https://agentservices.to",
        "repository": "https://github.com/vbkotecha/aiservices-api",
        "homepage": "https://agentservices.to",
        "license": "MIT",
        "spec": "x402-service-manifest/1",
    }


@app.get("/.well-known/agent.json")
async def agent_json():
    """Agent discovery manifest for AI agent platforms and crawlers."""
    return {
        "name": "AgentServices",
        "version": "5.3.0",
        "description": "Paid data APIs for AI agents — crypto, DeFi, DEX, prediction markets, news, search, geolocation, metadata, on-chain analytics, whale tracking, DeFi TVL, correlation matrix, stablecoin flows, GitHub velocity, macro indicators",
        "url": "https://agentservices.to",
        "capabilities": [
            "crypto-market-data",
            "technical-indicators",
            "defi-yields",
            "ip-geolocation",
            "url-metadata",
            "web-search",
            "dex-swap-quotes",
            "prediction-markets",
            "crypto-news",
            "social-trending",
            "global-market-stats",
            "marketing-sentiment",
            "marketing-trends",
            "marketing-competitors",
            "marketing-content-gaps",
            "marketing-ad-copy",
            "whale-tracking",
            "exchange-flows",
            "correlation-matrix",
            "defi-tvl",
            "stablecoin-flows",
            "github-velocity",
            "agent-context",
            "macro-indicators",
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
                "GET /v1/global",
                "GET /v1/trending",
                "GET /v1/gas",
                "GET /v1/swap/quote",
                "GET /v1/predictions",
                "GET /v1/news",
                "GET /v1/social",
            ],
            "paid": [
                {"path": "GET /v1/indicators/{symbol}", "price": "$0.02"},
                {"path": "GET /v1/yields", "price": "$0.02"},
                {"path": "GET /v1/metadata", "price": "$0.01"},
                {"path": "GET /v1/search", "price": "$0.01"},
                {"path": "POST /v1/disputes", "price": "$0.05"},
                {"path": "POST /v1/marketing/sentiment", "price": "$0.03"},
                {"path": "POST /v1/marketing/trends", "price": "$0.03"},
                {"path": "POST /v1/marketing/competitors", "price": "$0.05"},
                {"path": "POST /v1/marketing/content-gaps", "price": "$0.04"},
                {"path": "POST /v1/marketing/ad-copy", "price": "$0.05"},
                {"path": "GET /v1/whales", "price": "$0.02"},
                {"path": "GET /v1/exchange-flows", "price": "$0.02"},
                {"path": "GET /v1/correlation", "price": "$0.03"},
                {"path": "GET /v1/defi-tvl", "price": "$0.02"},
                {"path": "GET /v1/stablecoin-flows", "price": "$0.02"},
                {"path": "GET /v1/github-velocity", "price": "$0.02"},
                {"path": "GET /v1/macro", "price": "$0.02"},
            ],
        },
        "docs": "https://agentservices.to/docs",
        "github": "https://github.com/vbkotecha/aiservices-api",
        "wallet": X402_WALLET,
    }


@app.get("/.well-known/x402.json")
async def x402_json_manifest():
    """x402 v2 discovery manifest — what AgentGrade, Open 402 Directory, and x402.direct crawlers look for."""
    paid_services = [
        {"method": "GET", "path": "/v1/indicators/{symbol}", "price": "$0.02"},
        {"method": "GET", "path": "/v1/yields", "price": "$0.02"},
        {"method": "GET", "path": "/v1/metadata", "price": "$0.01"},
        {"method": "GET", "path": "/v1/search", "price": "$0.01"},
        {"method": "POST", "path": "/v1/disputes", "price": "$0.05"},
        {"method": "POST", "path": "/v1/marketing/sentiment", "price": "$0.03"},
        {"method": "POST", "path": "/v1/marketing/trends", "price": "$0.03"},
        {"method": "POST", "path": "/v1/marketing/competitors", "price": "$0.05"},
        {"method": "POST", "path": "/v1/marketing/content-gaps", "price": "$0.04"},
        {"method": "POST", "path": "/v1/marketing/ad-copy", "price": "$0.05"},
        {"method": "GET", "path": "/v1/whales", "price": "$0.02"},
        {"method": "GET", "path": "/v1/exchange-flows", "price": "$0.02"},
        {"method": "GET", "path": "/v1/correlation", "price": "$0.03"},
        {"method": "GET", "path": "/v1/defi-tvl", "price": "$0.02"},
        {"method": "GET", "path": "/v1/stablecoin-flows", "price": "$0.02"},
        {"method": "GET", "path": "/v1/github-velocity", "price": "$0.02"},
        {"method": "GET", "path": "/v1/macro", "price": "$0.02"},
        {"method": "POST", "path": "/v1/inference", "price": "$0.03"},
        {"method": "POST", "path": "/v1/complete", "price": "$0.03"},
        {"method": "GET", "path": "/v1/token-risk/{token}", "price": "$0.03"},
        {"method": "GET", "path": "/v1/signals/{symbol}", "price": "$0.04"},
        {"method": "GET", "path": "/v1/hn-sentiment", "price": "$0.02"},
        {"method": "GET", "path": "/v1/npm-stats/{package}", "price": "$0.02"},
        {"method": "GET", "path": "/v1/github-trending", "price": "$0.02"},
        {"method": "GET", "path": "/v1/yield-comparison", "price": "$0.03"},
        # Traditional Finance (v5.1.0)
        {"method": "GET", "path": "/v1/stocks/{ticker}", "price": "$0.02"},
        {"method": "GET", "path": "/v1/stocks/{ticker}/history", "price": "$0.03"},
        {"method": "GET", "path": "/v1/sec/{ticker}", "price": "$0.03"},
        {"method": "GET", "path": "/v1/commodities", "price": "$0.03"},
        {"method": "GET", "path": "/v1/economic", "price": "$0.03"},
        {"method": "GET", "path": "/v1/fx", "price": "$0.003"},
        # Utility (v5.1.0)
        {"method": "GET", "path": "/v1/extract", "price": "$0.002"},
        {"method": "GET", "path": "/v1/security/{package}", "price": "$0.02"},
        {"method": "GET", "path": "/v1/seo/keywords", "price": "$0.01"},
        # Intelligence (bundled high-value)
        {"method": "GET", "path": "/v1/research", "price": "$0.05"},
        {"method": "GET", "path": "/v1/portfolio/{symbol}", "price": "$0.10"},
        {"method": "GET", "path": "/v1/defi-strategy", "price": "$0.25"},
        {"method": "GET", "path": "/v1/market-pulse", "price": "$0.05"},
        {"method": "GET", "path": "/v1/onchain-overview", "price": "$0.15"},
        {"method": "GET", "path": "/v1/arbitrage", "price": "$0.08"},
    ]
    free_services = [
        {"method": "GET", "path": "/v1/price/{symbol}", "price": "$0.00"},
        {"method": "GET", "path": "/v1/prices", "price": "$0.00"},
        {"method": "GET", "path": "/v1/fear-greed", "price": "$0.00"},
        {"method": "GET", "path": "/v1/global", "price": "$0.00"},
        {"method": "GET", "path": "/v1/trending", "price": "$0.00"},
        {"method": "GET", "path": "/v1/gas", "price": "$0.00"},
        {"method": "GET", "path": "/v1/geo/{ip}", "price": "$0.00"},
        {"method": "GET", "path": "/v1/swap/quote", "price": "$0.00"},
        {"method": "GET", "path": "/v1/predictions", "price": "$0.00"},
        {"method": "GET", "path": "/v1/news", "price": "$0.00"},
        {"method": "GET", "path": "/v1/social", "price": "$0.00"},
        {"method": "GET", "path": "/v1/policies", "price": "$0.00"},
        {"method": "POST", "path": "/mcp", "price": "$0.00"},
    ]
    return {
        "x402Version": 2,
        "name": "AgentServices",
        "description": "Paid APIs for AI agents — crypto data, stocks, SEC filings, commodities, FX, inference gateway, market signals, web extraction, security scanning, MCP integration, cross-DEX arbitrage scanning. 52 services, 40 paid.",
        "network": "eip155:8453",
        "facilitator": "coinbase",
        "payTo": X402_WALLET,
        "currency": "USDC",
        "website": "https://agentservices.to",
        "apiBaseUrl": "https://agentservices.to",
        "repository": "https://github.com/vbkotecha/aiservices-api",
        "documentation": "https://agentservices.to/docs",
        "services": paid_services + free_services,
        "extensions": {
            "bazaar": {"discoverable": True}
        },
    }


@app.get("/.well-known/ai-catalog.json")
async def ai_catalog():
    """Agentic Resource Discovery (ARD) catalog — Google Cloud Agent Registry + federated discovery.
    Spec: github.com/ards-project/ard-spec — makes AgentServices discoverable by Gemini Enterprise agents."""
    return {
        "specVersion": "1.0",
        "host": {
            "displayName": "AgentServices",
            "identifier": "urn:ai:::agentservices.to",
            "documentationUrl": "https://agentservices.to",
        },
        "entries": [
            {
                "identifier": "urn:ai:::agentservices.to/mcp",
                "displayName": "AgentServices MCP Server",
                "type": "application/mcp-server-card+json",
                "url": "https://agentservices.to/mcp",
                "description": "52 paid APIs for AI agents — crypto data, market intelligence, on-chain analytics, cross-DEX arbitrage, AI inference, DeFi strategy, portfolio intelligence. 37 MCP tools. x402 payments (USDC on Base).",
                "tags": ["crypto", "defi", "market-data", "x402", "payments", "analytics", "inference", "mcp", "agents", "blockchain"],
                "capabilities": [
                    "crypto_prices", "technical_indicators", "defi_yields", "fear_greed",
                    "market_intelligence", "portfolio_analysis", "defi_strategy",
                    "cross_dex_arbitrage", "onchain_analytics", "ai_inference",
                    "web_search", "web_extraction", "token_risk_scoring",
                    "crypto_signals", "whale_tracking", "exchange_flows",
                ],
                "representativeQueries": [
                    "get Bitcoin price and technical indicators",
                    "find the best DeFi yield opportunities",
                    "analyze my crypto portfolio risk",
                    "scan for cross-DEX arbitrage opportunities",
                    "run AI inference with GPT or Gemini models",
                ],
                "version": "5.3.0",
                "updatedAt": "2026-07-08T07:00:00Z",
                "metadata": {
                    "pricing": "freemium ($0.01-$0.25 per call, USDC on Base)",
                    "paymentProtocol": "x402",
                    "chain": "base",
                    "endpointCount": "52",
                    "freeEndpoints": "12",
                    "paidEndpoints": "40",
                    "openapiSpec": "https://agentservices.to/openapi.json",
                    "skillCard": "https://agentservices.to/.well-known/agentskills/agentservices/SKILL.md",
                    "x402Manifest": "https://agentservices.to/.well-known/x402.json",
                },
            },
            {
                "identifier": "urn:ai:::agentservices.to/api",
                "displayName": "AgentServices REST API",
                "type": "application/vnd.oai.openapi+json",
                "url": "https://agentservices.to/openapi.json",
                "description": "REST API with 52 endpoints for crypto data, stocks, SEC filings, commodities, FX rates, web search, extraction, SEO analysis, package security, GitHub trending, HN sentiment, npm stats, and more.",
                "tags": ["api", "rest", "crypto", "finance", "data", "analytics"],
                "capabilities": ["rest_api", "data_endpoints", "synthesis", "market_data"],
                "representativeQueries": [
                    "get crypto prices and market data",
                    "analyze stock fundamentals and SEC filings",
                    "extract content from web pages",
                    "check npm package security",
                ],
                "version": "5.3.0",
                "updatedAt": "2026-07-08T07:00:00Z",
            },
        ],
    }


@app.get("/llms.txt")
async def llms_txt():
    """LLM-friendly API description for agent crawlers and AI discovery."""
    lines = [
        "# AgentServices",
        "",
        "> Paid APIs for AI agents. 51 services, 39 paid. Crypto data, stocks, SEC filings, commodities, FX, inference gateway (gpt-5.4/5.5), token risk scoring, crypto signals, cross-DEX arbitrage scanner, web extraction, package security, SEO research, and more. All via x402 (USDC on Base).",
        "",
        "## Base URL",
        "https://agentservices.to",
        "",
        "## Authentication",
        "Paid endpoints use x402 protocol (USDC on Base Mainnet). Free endpoints require no auth.",
        "",
        "## Free Endpoints",
        "- GET /v1/price/{symbol} — Current crypto price (e.g., BTC, ETH)",
        "- GET /v1/prices?symbols=BTC,ETH,SOL — Batch crypto prices",
        "- GET /v1/fear-greed — Crypto Fear & Greed Index (0-100)",
        "- GET /v1/geo/{ip} — IP geolocation lookup",
        "- GET /v1/global — Global market cap, volume, BTC dominance",
        "- GET /v1/trending — Trending tokens being searched right now",
        "- GET /v1/gas — Current Ethereum gas prices (slow/standard/fast)",
        "- GET /v1/swap/quote — DEX swap quote (0x API, 6 chains)",
        "- GET /v1/predictions — Active Polymarket prediction markets",
        "- GET /v1/predictions/{slug} — Specific prediction market details",
        "- GET /v1/news — Latest crypto and blockchain news",
        "- GET /v1/social — Trending coins, categories, NFTs",
        "",
        "## Paid Endpoints (x402 / USDC on Base)",
        "- GET /v1/indicators/{symbol} — RSI, Bollinger Bands, ATR, Support/Resistance ($0.02)",
        "- GET /v1/yields — Top DeFi yield pools by TVL ($0.02)",
        "- GET /v1/metadata?url=... — URL metadata extraction and unfurling ($0.01)",
        "- GET /v1/search?q=... — AI-powered web search ($0.01)",
        "- POST /v1/marketing/sentiment — AI brand sentiment analysis ($0.03)",
        "- POST /v1/marketing/trends — Industry trend detection with velocity ($0.03)",
        "- POST /v1/marketing/competitors — Competitive intelligence ($0.05)",
        "- POST /v1/marketing/content-gaps — SEO content gap analysis ($0.04)",
        "- POST /v1/marketing/ad-copy — AI ad copy generator ($0.05)",
        "- GET /v1/whales — Large whale transactions BTC/ETH ($0.02)",
        "- GET /v1/exchange-flows — CEX reserve flows ($0.02)",
        "- GET /v1/correlation — 30-day cross-asset correlation matrix ($0.03)",
        "- GET /v1/defi-tvl — DeFi protocol TVL rankings ($0.02)",
        "- GET /v1/stablecoin-flows — Stablecoin market caps and supply ($0.02)",
        "- GET /v1/github-velocity — GitHub crypto repo velocity scores ($0.02)",
        "- GET /v1/macro — Macro economic indicators ($0.02)",
        "- POST /v1/inference — LLM inference gateway, gpt-5.4/5.4-mini/5.5 ($0.03)",
        "- POST /v1/complete?prompt=... — Quick text completion ($0.03)",
        "- GET /v1/token-risk/{token} — Token risk scoring ($0.03)",
        "- GET /v1/signals/{symbol} — Crypto buy/sell signals ($0.04)",
        "- GET /v1/hn-sentiment — Hacker News tech sentiment ($0.02)",
        "- GET /v1/npm-stats/{package} — NPM download trends ($0.02)",
        "- GET /v1/github-trending — GitHub trending repos ($0.02)",
        "- GET /v1/yield-comparison — DeFi yield comparison with risk ($0.03)",
        "- GET /v1/stocks/{ticker} — Real-time stock quote ($0.02)",
        "- GET /v1/stocks/{ticker}/history — Historical OHLCV ($0.03)",
        "- GET /v1/sec/{ticker} — SEC filings parser, 10-K/10-Q/Form 4 ($0.03)",
        "- GET /v1/commodities — Oil, gold, silver, wheat prices ($0.03)",
        "- GET /v1/economic — CPI, GDP, Fed rate (FRED) ($0.03)",
        "- GET /v1/fx?base=USD — 30+ currency exchange rates ($0.003)",
        "- GET /v1/extract?url=... — Web content extraction ($0.002)",
        "- GET /v1/security/{package} — Package vulnerability scan ($0.02)",
        "- GET /v1/seo/keywords?keyword=... — SEO keyword research ($0.01)",
        "- GET /v1/research?q=... — Deep research: search + extract + synthesize ($0.05)",
        "- GET /v1/portfolio?symbol=... — Portfolio intelligence: price + signal + risk + sentiment ($0.10)",
        "- GET /v1/defi-strategy?chain=... — DeFi strategy: yields + TVL + comparison + risk ($0.25)",
        "- GET /v1/market-pulse — Market pulse: sentiment + trending + news + whales ($0.05)",
        "- GET /v1/onchain-overview — On-chain intelligence: whales + flows + correlation + DeFi TVL ($0.15)",
        "",
        "## Free Agent Tools",
        "- GET /v1/agent-context — Paste-ready market context for LLM prompts",
        "",
        "## Example Usage",
        "```",
        "# Free: Get BTC price",
        "curl https://agentservices.to/v1/price/BTC",
        "",
        "# Paid: Get BTC indicators (requires x402 payment)",
        "curl https://agentservices.to/v1/indicators/BTC",
        "```",
        "",
        f"## Payment Wallet\n{X402_WALLET}",
        "",
        "## Links",
        "- API Docs: https://agentservices.to/docs",
        "- Examples: https://agentservices.to/examples",
        "- GitHub: https://github.com/vbkotecha/aiservices-api",
    ]
    from starlette.responses import PlainTextResponse
    return PlainTextResponse(content="\n".join(lines), media_type="text/plain")


@app.get("/robots.txt")
async def robots_txt():
    """Robots.txt with explicit AI crawler rules for agent discovery."""
    from starlette.responses import PlainTextResponse
    lines = [
        "# AgentServices — robots.txt",
        "# AI agents and crawlers are explicitly allowed",
        "",
        "User-agent: GPTBot",
        "Allow: /",
        "",
        "User-agent: ClaudeBot",
        "Allow: /",
        "",
        "User-agent: ChatGPT-User",
        "Allow: /",
        "",
        "User-agent: anthropic-ai",
        "Allow: /",
        "",
        "User-agent: Google-Extended",
        "Allow: /",
        "",
        "User-agent: PerplexityBot",
        "Allow: /",
        "",
        "User-agent: Amazonbot",
        "Allow: /",
        "",
        "User-agent: *",
        "Allow: /",
        "",
        "# Key endpoints for AI agents",
        "# /llms.txt — Machine-readable service description",
        "# /openapi.json — OpenAPI 3.1 specification",
        "# /mcp — MCP server (SSE)",
        "# /.well-known/x402 — x402 payment discovery",
        "# /.well-known/mcp/server-card.json — MCP server card",
    ]
    return PlainTextResponse(content="\n".join(lines), media_type="text/plain")


@app.get("/schema.json")
async def openapi_schema():
    """Explicit OpenAPI schema endpoint for crawlers that prefer /schema.json over /openapi.json."""
    return app.openapi()


@app.get("/.well-known/agentskills/agentservices/SKILL.md")
async def agentskills_manifest():
    """AgentSkills.io SKILL.md — discoverable skill for agent platforms (AIsa, etc)."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content='''---
name: agentservices
description: >-
  Access paid data APIs for AI agents including crypto prices, technical indicators,
  DeFi yields, on-chain analytics (whale tracking, exchange flows, stablecoin flows),
  market intelligence (sentiment, trends, competitor analysis, content gaps, ad copy),
  portfolio intelligence, DeFi strategy optimization, web search and extraction,
  URL metadata, IP geolocation, AI inference (GPT models), fear-greed index, and
  MCP integration. Use when the agent needs real-time financial data, crypto market
  data, on-chain analysis, marketing intelligence, research, or AI inference.
  Payments via x402 protocol (USDC on Base). Free endpoints available for prices,
  trending, news, and social data.
license: MIT
compatibility: >-
  Network access required. Supports x402 micropayments (USDC on Base) for paid
  endpoints. Works with any HTTP client or MCP-compatible agent. No SDK installation
  required -- standard REST API with optional MCP transport.
metadata:
  author: AgentServices
  version: "5.3.0"
  website: "https://agentservices.to"
  api_base_url: "https://agentservices.to"
  repository: "https://github.com/vbkotecha/aiservices-api"
  documentation: "https://agentservices.to/docs"
  payment_protocol: "x402"
  payment_currency: "USDC"
  payment_network: "Base (eip155:8453)"
  payment_facilitator: "Coinbase CDP"
  total_services: "50"
  paid_services: "38"
  free_services: "12"
  mcp_tools: "36"
  mcp_endpoint: "https://agentservices.to/mcp"
---

# AgentServices -- Paid Data APIs for AI Agents

## Overview

AgentServices provides 50 API endpoints for AI agents, covering crypto data,
on-chain analytics, market intelligence, web research, and AI inference.
Paid endpoints use x402 micropayments ($0.01-$0.25 per call in USDC on Base).
12 endpoints are completely free -- no payment, no signup, no API key.

## Quick Start

### Free Endpoints (no payment, no key)

    curl https://agentservices.to/v1/prices
    curl https://agentservices.to/v1/price/BTC
    curl https://agentservices.to/v1/fear-greed
    curl https://agentservices.to/v1/trending
    curl https://agentservices.to/v1/news
    curl https://agentservices.to/v1/global

### Paid Endpoints (x402 micropayment)

When you call a paid endpoint, the server returns HTTP 402 with payment
instructions in the response body. Pay with USDC on Base, then retry
with the payment proof.

## Payment Setup

### Option 1: Coinbase Agentic Wallet (recommended)

Install the agentic wallet CLI and fund with USDC on Base:

    npx awal@latest wallet generate
    npx awal@latest wallet fund --amount 5    # $5 USDC

Then pay for any endpoint:

    npx awal@latest x402 pay 'https://agentservices.to/v1/indicators/BTC'

### Option 2: Any x402-compatible wallet

Use @x402/fetch or any x402 client library. The server's 402 response
includes a complete payment descriptor (amount, payTo address, network,
and facilitator URL).

CDP Paymaster makes payments gasless -- no ETH needed, only USDC.

## MCP Integration

Connect AgentServices to any MCP-compatible client (Claude Desktop,
Cursor, Cline, Windsurf, VS Code):

### Claude Desktop

Add to claude_desktop_config.json:

    {
      "mcpServers": {
        "agentservices": {
          "url": "https://agentservices.to/mcp"
        }
      }
    }

### Cursor / Cline / Generic MCP Client

    Server URL: https://agentservices.to/mcp
    Transport: SSE (Server-Sent Events)

36 tools available covering all endpoints.

## Endpoint Reference

### Free Endpoints (no payment)

| Endpoint | Description |
|---|---|
| GET /v1/prices | All crypto prices |
| GET /v1/price/{symbol} | Single crypto price |
| GET /v1/fear-greed | Fear & Greed Index |
| GET /v1/trending | Trending tokens |
| GET /v1/news | Latest crypto news |
| GET /v1/global | Global market stats |
| GET /v1/social-trending | Social media trends |
| GET /v1/gas | Gas prices |
| GET /v1/predictions | Price predictions |
| GET /v1/swap-quote | DEX swap quotes |
| GET /v1/geo | IP geolocation |
| GET /v1/policies | Dispute templates |

### Paid Endpoints (x402)

| Endpoint | Price | Description |
|---|---|---|
| GET /v1/indicators/{symbol} | $0.02 | Technical indicators (RSI, MACD, etc.) |
| GET /v1/yields | $0.02 | DeFi yield rates across protocols |
| GET /v1/whales | $0.02 | Whale transaction tracking |
| GET /v1/exchange-flows | $0.02 | Exchange inflow/outflow data |
| GET /v1/correlation | $0.03 | Token correlation matrix |
| GET /v1/stablecoin-flows | $0.02 | Stablecoin flow analysis |
| GET /v1/defi-tvl | $0.02 | DeFi TVL by protocol |
| GET /v1/search | $0.01 | Web search |
| GET /v1/metadata | $0.01 | URL metadata extraction |
| GET /v1/sentiment | $0.03 | Market sentiment analysis |
| GET /v1/trends | $0.03 | Market trend analysis |
| GET /v1/competitors | $0.05 | Competitor analysis |
| GET /v1/token-risk/{symbol} | $0.03 | Token risk assessment |
| GET /v1/crypto-signals/{symbol} | $0.04 | Crypto trading signals |
| GET /v1/portfolio?symbol=BTC | $0.10 | Portfolio intelligence report |
| GET /v1/defi-strategy | $0.25 | DeFi investment strategy report |
| GET /v1/market-pulse | $0.05 | Market overview (6 modules) |
| GET /v1/onchain-overview | $0.15 | On-chain analytics (5 modules) |
| GET /v1/research | $0.05 | Deep research (search+extract+synthesize) |
| POST /v1/inference | $0.03 | AI inference (GPT models) |
| POST /v1/complete | $0.03 | AI text completion |

Full list at https://agentservices.to/docs

## Use Cases

- **Portfolio Monitor**: /v1/portfolio + /v1/indicators + /v1/token-risk
- **DeFi Yield Optimizer**: /v1/defi-strategy + /v1/yields + /v1/defi-tvl
- **Market Intelligence Agent**: /v1/market-pulse + /v1/sentiment + /v1/trends
- **Trading Bot**: /v1/crypto-signals + /v1/whales + /v1/exchange-flows
- **Research Agent**: /v1/research + /v1/search + /v1/metadata

## Discovery

- x402 Manifest: https://agentservices.to/.well-known/x402.json
- OpenAPI Spec: https://agentservices.to/openapi.json
- Agent Skill Card: https://agentservices.to/.well-known/mcp/server-card.json
- ARD Catalog: https://agentservices.to/.well-known/ai-catalog.json
- MCP Registry: to.agentservices/agentservices
- Network: Base (eip155:8453)
- Facilitator: Coinbase CDP (https://api.cdp.coinbase.com/platform/v2/x402)
''',
        media_type="text/markdown",
        headers={"Cache-Control": "public, max-age=3600"}
    )


@app.get("/manifest.json")
async def web_manifest():
    """Web app manifest for browser/agent discovery."""
    return {
        "name": "AgentServices",
        "short_name": "AgentServices",
        "description": "Paid data APIs for AI agents — crypto, DeFi, geo, web metadata, marketing intelligence, dispute resolution",
        "start_url": "https://agentservices.to",
        "scope": "/",
        "display": "standalone",
        "categories": ["developer", "finance", "data"],
        "icons": [],
    }


@app.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest():
    """OpenAI plugin manifest for ChatGPT plugin discovery."""
    return {
        "schema_version": "v1",
        "name_for_human": "AgentServices",
        "name_for_model": "agentservices",
        "description_for_human": "Paid APIs for AI agents — crypto data, market intelligence, DeFi analytics, on-chain analytics, search, and AI inference. Pay per request with USDC on Base.",
        "description_for_model": "Access 50+ API endpoints for crypto prices, technical indicators, DeFi yields, on-chain analytics, whale tracking, market sentiment, web search, LLM inference, portfolio intelligence, and dispute resolution. Free endpoints need no payment. Paid endpoints use x402 protocol (USDC on Base).",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": "https://agentservices.to/openapi.json"},
        "logo_url": "https://agentservices.to/logo.png",
        "contact_email": "vbkotecha@gmail.com",
        "legal_info_url": "https://agentservices.to",
        "url": "https://agentservices.to",
    }


@app.get("/docs-page", response_class=HTMLResponse)
async def api_docs_page():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentServices — Premium APIs for AI Agents</title>
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
<h1>AgentServices</h1>
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
curl https://agentservices.to/v1/price/BTC

# Free: Batch prices
curl "https://agentservices.to/v1/prices?symbols=BTC,ETH,SOL"

# Free: Fear & Greed Index
curl https://agentservices.to/v1/fear-greed

# MCP: Connect your AI tool
# URL: https://agentservices.to/mcp (Streamable HTTP)</code></pre>
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
<p>Connect AgentServices directly to Claude, Cursor, or any MCP client:</p>
<pre><code>MCP Server URL: https://agentservices.to/mcp
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
<p class="wallet">Wallet: 0x9863aB6242663FCc84c33632741711dB78f8Fd15</p>
</section>

<section>
<h2>Links</h2>
<p><a href="/docs">Swagger/OpenAPI Docs</a> · <a href="/llms.txt">llms.txt</a> · <a href="/health">Health Check</a> · <a href="https://github.com/vbkotecha/aiservices-api">GitHub</a></p>
</section>

<div class="footer">
<p>AgentServices — MIT License</p>
</div>
</div>
</body>
</html>
""")


# ============================================================
# NEW v5.0.0 ENDPOINTS — Synthesis + Inference Gateway
# ============================================================

# --- Inference Gateway (BlockRun competitor) ---

class InferenceRequest(BaseModel):
    model: str = Field(default="gpt-5.4-mini", description="gpt-5.4, gpt-5.4-mini, or gpt-5.5")
    messages: List[dict] = Field(description="Chat messages in OpenAI format [{role, content}]")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=16000)

@app.get("/v1/models", tags=["Inference"])
async def list_models():
    """List available inference models (FREE)"""
    return list_inference_models()

@app.post("/v1/inference", tags=["Inference"],
          summary="LLM Inference — Chat Completion",
          description="Send a chat completion request. Models: gpt-5.4, gpt-5.4-mini, gpt-5.5. Costs $0.03 USDC via x402.")
async def llm_inference(req: InferenceRequest):
    """LLM inference gateway ($0.03 per call via x402)"""
    return inference(
        model=req.model,
        messages=req.messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )

@app.post("/v1/complete", tags=["Inference"],
          summary="Quick Text Completion",
          description="Send a prompt, get a completion. Simpler than /v1/inference. Costs $0.03 USDC via x402.")
async def quick_completion(prompt: str, model: str = "gpt-5.4-mini", max_tokens: int = 500):
    """Quick text completion ($0.03 per call via x402)"""
    return quick_complete(prompt=prompt, model=model, max_tokens=max_tokens)


# --- Synthesis Endpoints ---

@app.get("/v1/token-risk/{token}", tags=["Synthesis"],
         summary="Token Risk Scoring",
         description="Risk score (0-100) for any crypto token. Analyzes volatility, liquidity, and market cap. Costs $0.03 USDC via x402.")
async def token_risk(token: str):
    """Token risk scoring ($0.03 per call via x402)"""
    return get_token_risk(token)

@app.get("/v1/signals/{symbol}", tags=["Synthesis"],
         summary="Crypto Buy/Sell Signals",
         description="Synthesized trading signal from RSI, moving averages, and Bollinger Bands. Costs $0.04 USDC via x402.")
async def crypto_signals(symbol: str):
    """Crypto signal feed ($0.04 per call via x402)"""
    return get_crypto_signal(symbol)

@app.get("/v1/hn-sentiment", tags=["Synthesis"],
         summary="Hacker News Sentiment",
         description="Tech sentiment from top HN stories. Optionally filter by query. Costs $0.02 USDC via x402.")
async def hn_sentiment(query: str = ""):
    """Hacker News sentiment ($0.02 per call via x402)"""
    return get_hn_sentiment(query)

@app.get("/v1/npm-stats/{package}", tags=["Synthesis"],
         summary="NPM Download Stats",
         description="Package download statistics and trend analysis. Costs $0.02 USDC via x402.")
async def npm_stats(package: str):
    """NPM package stats ($0.02 per call via x402)"""
    return get_npm_stats(package)

@app.get("/v1/github-trending", tags=["Synthesis"],
         summary="GitHub Trending Repos",
         description="Hot repositories created in the last 7 days. Filter by language. Costs $0.02 USDC via x402.")
async def github_trending(language: str = "", since: str = "daily"):
    """GitHub trending ($0.02 per call via x402)"""
    return get_github_trending(language, since)

@app.get("/v1/yield-comparison", tags=["Synthesis"],
         summary="DeFi Yield Comparison with Risk",
         description="Compare DeFi yields with risk-adjusted analysis. Not just raw APY. Costs $0.03 USDC via x402.")
async def yield_comparison(chain: str = ""):
    """Risk-adjusted yield comparison ($0.03 per call via x402)"""
    return get_yield_comparison(chain)


# ============================================================
# TRADITIONAL FINANCE ENDPOINTS (v5.1.0 — Gap Fillers)
# ============================================================

@app.get("/v1/stocks/{ticker}", tags=["Traditional Finance"],
         summary="Stock Market Quote",
         description="Real-time stock quote from Yahoo Finance. Only 2 providers on Bazaar. $0.02 USDC via x402.")
async def stock_quote(ticker: str):
    """Stock quote ($0.02 per call via x402)"""
    return get_stock_quote(ticker)

@app.get("/v1/stocks/{ticker}/history", tags=["Traditional Finance"],
         summary="Historical Stock Data",
         description="Historical OHLCV data. Range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 5y. $0.03 USDC via x402.")
async def stock_history(ticker: str, range: str = "3mo"):
    """Historical stock OHLCV ($0.03 per call via x402)"""
    return get_stock_history(ticker, range)

@app.get("/v1/sec/{ticker}", tags=["Traditional Finance"],
         summary="SEC Filings Parser",
         description="Recent SEC filings (10-K, 10-Q, 8-K, Form 4) from EDGAR. Only 2 providers on Bazaar. $0.03 USDC via x402.")
async def sec_filings(ticker: str, filing_type: str = "10-K"):
    """SEC filings ($0.03 per call via x402)"""
    return get_sec_filings(ticker, filing_type)

@app.get("/v1/commodities", tags=["Traditional Finance"],
         summary="Commodity Prices",
         description="Oil, gold, silver, copper, wheat, corn, coffee, and more. Undercuts LoneStar ($0.05). $0.03 USDC via x402.")
async def commodities(category: str = "all"):
    """Commodity prices ($0.03 per call via x402)"""
    return get_commodities()

@app.get("/v1/economic", tags=["Traditional Finance"],
         summary="Economic Indicators",
         description="CPI, GDP, unemployment, Fed funds rate, Treasury yields. From FRED. $0.03 USDC via x402.")
async def economic_indicators(indicator: str = "all"):
    """US economic indicators ($0.03 per call via x402)"""
    return get_economic_indicators()

@app.get("/v1/fx", tags=["Traditional Finance"],
         summary="FX / Forex Rates",
         description="Real-time exchange rates for 30+ currencies. Only 1 provider on Bazaar. $0.003 USDC via x402.")
async def fx_rates(base: str = "USD"):
    """FX rates ($0.003 per call via x402)"""
    return get_fx_rates(base)


# ============================================================
# UTILITY ENDPOINTS (v5.1.0 — Gap Fillers)
# ============================================================

@app.get("/v1/extract", tags=["Utility"],
         summary="Web Content Extraction",
         description="Fetch any URL and get clean, token-efficient text. Strips ads, nav, scripts. $0.002 USDC via x402.")
async def web_extract(url: str):
    """Web content extraction ($0.002 per call via x402)"""
    return extract_web_content(url)

@app.get("/v1/security/{package}", tags=["Utility"],
         summary="Package Security Scan",
         description="Check PyPI/npm packages for known vulnerabilities. Only 1 provider on Bazaar. $0.02 USDC via x402.")
async def package_security(package: str, ecosystem: str = "PyPI"):
    """Package security scan ($0.02 per call via x402)"""
    return scan_package_security(package, ecosystem)

@app.get("/v1/seo/keywords", tags=["Utility"],
         summary="SEO Keyword Research",
         description="Keyword research with volume estimates and competition data. SpyFu has 46 endpoints — proven demand. $0.01 USDC via x402.")
async def keyword_research(keyword: str):
    """SEO keyword research ($0.01 per call via x402)"""
    return seo_keywords(keyword)


# --- Deep Research (Flagship Bundled Endpoint) ---

@app.get("/v1/research", tags=["Research"],
         summary="Deep Research — Search + Extract + Synthesize",
         description="One-call deep research: searches the web, extracts content from top sources, and synthesizes an intelligence brief with key findings, themes, and sentiment. Replaces 3+ separate API calls. $0.05 USDC via x402.")
async def research_endpoint(q: str, sources: int = 3):
    """
    Deep Research ($0.05 per call via x402)

    Bundles: web search + content extraction + synthesis analysis.
    Returns a structured intelligence brief with key findings, themes, and sentiment.
    """
    return deep_research(q, max_sources=min(sources, 5))


# --- Portfolio Intelligence (High-Value Bundled Endpoint) ---

@app.get("/v1/portfolio", tags=["Intelligence"],
         summary="Portfolio Intelligence — Price + Signal + Risk + Sentiment",
         description="Comprehensive asset analysis in one call: market data, technical signals (RSI, MA, Bollinger), risk scoring, and market sentiment (Fear & Greed). Replaces 4+ separate API calls. $0.10 USDC via x402.")
async def portfolio_endpoint(symbol: str):
    """
    Portfolio Intelligence ($0.10 per call via x402)

    Bundles: price + technical signal + risk score + market sentiment.
    Returns a synthesized verdict combining all modules.
    """
    return portfolio_intelligence(symbol)


# --- DeFi Strategy Report (High-Value Bundled Endpoint) ---

@app.get("/v1/defi-strategy", tags=["Intelligence"],
         summary="DeFi Strategy — Yields + TVL + Comparison + Risk",
         description="Comprehensive DeFi investment analysis: top yield opportunities, protocol TVL rankings, cross-chain yield comparison, and risk assessment with high-APY flags. Replaces 4+ API calls. $0.25 USDC via x402.")
async def defi_strategy_endpoint(chain: str = ""):
    """
    DeFi Strategy Report ($0.25 per call via x402)

    Bundles: yield opportunities + protocol TVL + yield comparison + risk flags.
    Returns synthesized investment strategy with risk-adjusted recommendations.
    """
    return defi_strategy_report(chain)


# --- Market Pulse (Rapid Market Snapshot) ---

@app.get("/v1/market-pulse", tags=["Intelligence"],
         summary="Market Pulse — Sentiment + Trending + News + Whales",
         description="Real-time crypto market snapshot: Fear & Greed index, trending tokens, latest news, social signals, whale movements, and global market stats. Replaces 6+ API calls. $0.05 USDC via x402.")
async def market_pulse_endpoint():
    """
    Market Pulse ($0.05 per call via x402)

    Bundles: sentiment + trending + news + social + whales + global market.
    Returns synthesized market direction signal for rapid agent decision-making.
    """
    return market_pulse()


@app.get("/v1/onchain-overview", tags=["Intelligence"],
         summary="On-Chain Overview — Whales + Flows + Correlation + TVL",
         description="Comprehensive on-chain intelligence: whale movements, exchange flows, stablecoin flows, correlation matrix, and DeFi TVL in one call. Replaces 5+ API calls. $0.15 USDC via x402.")
async def onchain_overview_endpoint():
    """
    On-Chain Overview ($0.15 per call via x402)

    Bundles: whale activity + exchange flows + stablecoin flows + correlation matrix + DeFi TVL.
    Returns synthesized on-chain assessment for smart money tracking and liquidity flow analysis.
    """
    return onchain_overview()


# --- Cross-DEX Arbitrage Scanner ---

@app.get("/v1/arbitrage", tags=["Intelligence"],
         summary="Arbitrage Scanner — Cross-DEX Price Discrepancies + Profitability",
         description="Cross-DEX arbitrage scanner: compares token prices across exchanges, calculates gas-adjusted profitability, models slippage, and flags actionable opportunities. Unique computation — no free API provides this. $0.08 USDC via x402.")
async def arbitrage_scanner_endpoint(symbols: str = "BTC,ETH,SOL,USDC,WETH,WBTC"):
    """
    Cross-DEX Arbitrage Scanner ($0.08 per call via x402)

    Scans for price discrepancies across exchanges. For each symbol:
    - Compares prices from CoinGecko (aggregated) vs Coinbase spot
    - Calculates spread percentage and absolute
    - Models profitability at $100/$1K/$10K/$100K trade sizes
    - Factors in gas costs (Base L2) and slippage proportional to volume
    - Flags opportunities where net ROI > 0.5% after costs

    This is COMPUTATION, not data fetching. Addresses competitive feedback
    that raw data endpoints are commoditized.
    """
    return arbitrage_scanner(symbols)


# --- Agent-Friendly Examples Page ---

_examples_html = None
def _get_examples():
    global _examples_html
    if _examples_html is None:
        _examples_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentServices — Agent Integration Examples</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'SF Mono','Fira Code',monospace;background:#0a0a0a;color:#e0e0e0;line-height:1.6;padding:20px}
.container{max-width:900px;margin:0 auto}
h1{color:#fff;font-size:1.8em;margin-bottom:10px}
h1 a{color:#4A90D9;text-decoration:none}
.subtitle{color:#888;margin-bottom:30px;font-size:0.95em}
h2{color:#4A90D9;font-size:1.2em;margin:30px 0 12px;border-bottom:1px solid #222;padding-bottom:6px}
h3{color:#e8e8e8;font-size:1em;margin:20px 0 8px}
.section{background:#111;border-radius:8px;padding:20px;margin-bottom:20px;border:1px solid #1a1a1a}
.code-block{background:#0d0d0d;border:1px solid #1a1a1a;border-radius:6px;padding:14px;overflow-x:auto;margin:8px 0;font-size:0.85em;color:#a8ffa8}
.code-block .comment{color:#666}
.code-block .var{color:#4A90D9}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.75em;font-weight:bold;margin-left:8px}
.badge-free{background:#1a3a1a;color:#4ade80}
.badge-paid{background:#3a2a1a;color:#fbbf24}
.badge-bundle{background:#2a1a3a;color:#a78bfa}
.tag{display:inline-block;background:#1a1a2e;color:#6b7afe;padding:2px 8px;border-radius:3px;font-size:0.75em;margin:2px}
.note{color:#888;font-size:0.85em;font-style:italic;margin:5px 0}
a{color:#4A90D9}
</style>
</head>
<body>
<div class="container">
<h1>🔗 <a href="/">AgentServices</a> — Agent Integration Examples</h1>
<p class="subtitle">Ready-to-use prompts and commands for AI agents. Copy, paste, execute.</p>

<div class="section">
<h2>Quick Start for AI Agents</h2>
<p>AgentServices provides 50+ APIs for AI agents. Free endpoints work immediately. Paid endpoints use x402 (USDC micropayments on Base).</p>
<p style="margin-top:8px">
<span class="tag">x402</span>
<span class="tag">USDC</span>
<span class="tag">Base Mainnet</span>
<span class="tag">MCP</span>
<span class="tag">OpenAPI 3.1</span>
</p>
</div>

<div class="section">
<h2>1. Free Endpoints — No Payment Needed</h2>
<h3>Crypto Prices</h3>
<div class="code-block"><span class="comment"># Get current price for any crypto</span>
curl https://agentservices.to/v1/prices?symbols=BTC,ETH,SOL

<span class="comment"># Single asset</span>
curl https://agentservices.to/v1/price/BTC</div>

<h3>Market Overview</h3>
<div class="code-block"><span class="comment"># Global market stats</span>
curl https://agentservices.to/v1/global

<span class="comment"># Fear & Greed Index</span>
curl https://agentservices.to/v1/fear-greed

<span class="comment"># Trending tokens</span>
curl https://agentservices.to/v1/trending

<span class="comment"># Latest crypto news</span>
curl https://agentservices.to/v1/news</div>

<h3>Agent-Ready Context</h3>
<div class="code-block"><span class="comment"># Paste-ready market context for LLMs</span>
curl https://agentservices.to/v1/agent-context</div>
</div>

<div class="section">
<h2>2. MCP Integration — Connect to Claude, Cursor, or Any MCP Client</h2>
<p>AgentServices exposes a remote MCP server at <code>/mcp</code>. No installation required.</p>
<div class="code-block"><span class="comment"># Claude Desktop / Cursor config (add to mcp.json)</span>
{
  "mcpServers": {
    "agentservices": {
      "url": "https://agentservices.to/mcp"
    }
  }
}

<span class="comment"># List available MCP tools</span>
curl https://agentservices.to/mcp/tools</div>
<p class="note">36 MCP tools available — crypto data, market intelligence, search, DeFi, on-chain analytics, and more.</p>
</div>

<div class="section">
<h2>3. Paid Endpoints — x402 Payments <span class="badge badge-paid">$0.01-$0.25</span></h2>
<p>Paid endpoints return HTTP 402 with payment instructions. Use any x402-compatible wallet.</p>

<h3>Web Search <span class="badge badge-paid">$0.01</span></h3>
<div class="code-block"><span class="comment"># AI-powered web search</span>
curl https://agentservices.to/v1/search?q=latest+AI+agent+frameworks

<span class="comment"># Returns 402 → pay with x402 wallet → get results</span></div>

<h3>Technical Indicators <span class="badge badge-paid">$0.02</span></h3>
<div class="code-block">curl https://agentservices.to/v1/indicators/BTC
<span class="comment"># RSI, Bollinger Bands, ATR, Support/Resistance</span></div>

<h3>DeFi Yields <span class="badge badge-paid">$0.02</span></h3>
<div class="code-block">curl https://agentservices.to/v1/yields
<span class="comment"># Top yield pools by TVL across chains</span></div>
</div>

<div class="section">
<h2>4. Bundled Intelligence — One Call, Full Analysis <span class="badge badge-bundle">BEST VALUE</span></h2>
<p>Aggregated endpoints that replace multiple API calls. Higher value, lower total cost.</p>

<h3>Deep Research <span class="badge badge-bundle">$0.05</span></h3>
<div class="code-block"><span class="comment"># Search + Extract + Synthesize in one call</span>
curl "https://agentservices.to/v1/research?q=ethereum+merge+impact+on+defi"</div>

<h3>Portfolio Intelligence <span class="badge badge-bundle">$0.10</span></h3>
<div class="code-block"><span class="comment"># Price + Signal + Risk + Sentiment + Verdict</span>
curl "https://agentservices.to/v1/portfolio?symbol=BTC"</div>

<h3>Market Pulse <span class="badge badge-bundle">$0.05</span></h3>
<div class="code-block"><span class="comment"># Sentiment + Trending + News + Whales + Global snapshot</span>
curl https://agentservices.to/v1/market-pulse</div>

<h3>DeFi Strategy Report <span class="badge badge-bundle">$0.25</span></h3>
<div class="code-block"><span class="comment"># Yields + TVL + Cross-chain comparison + Risk assessment</span>
curl "https://agentservices.to/v1/defi-strategy?chain=ethereum"</div>

<h3>On-Chain Overview <span class="badge badge-bundle">$0.15</span></h3>
<div class="code-block"><span class="comment"># Whales + Exchange flows + Stablecoin flows + Correlation + DeFi TVL</span>
curl https://agentservices.to/v1/onchain-overview</div>
</div>

<div class="section">
<h2>5. LLM Inference Gateway <span class="badge badge-paid">$0.03</span></h3>
<div class="code-block"><span class="comment"># List models</span>
curl https://agentservices.to/v1/models

<span class="comment"># Chat completion (OpenAI-compatible)</span>
curl -X POST https://agentservices.to/v1/inference \\
  -H "Content-Type: application/json" \\
  -d '{"model":"gpt-5.4-mini","messages":[{"role":"user","content":"What is DeFi?"}]}'</div>
</div>

<div class="section">
<h2>6. Use-Case: Portfolio Monitoring Agent</h2>
<div class="code-block"><span class="comment"># Step 1: Get free prices</span>
curl "https://agentservices.to/v1/prices?symbols=BTC,ETH,LINK"

<span class="comment"># Step 2: Get technical signals ($0.02)</span>
curl https://agentservices.to/v1/indicators/BTC

<span class="comment"># Step 3: Get full portfolio intelligence ($0.10)</span>
curl "https://agentservices.to/v1/portfolio?symbol=ETH"

<span class="comment"># Total cost for full portfolio check: ~$0.14</span></div>
</div>

<div class="section">
<h2>7. Use-Case: Market Intelligence Agent</h2>
<div class="code-block"><span class="comment"># Step 1: Market pulse ($0.05) — full snapshot</span>
curl https://agentservices.to/v1/market-pulse

<span class="comment"># Step 2: Deep research on a topic ($0.05)</span>
curl "https://agentservices.to/v1/research?q=base+chain+ecosystem+growth+2026"

<span class="comment"># Step 3: On-chain overview ($0.15) — smart money flows</span>
curl https://agentservices.to/v1/onchain-overview

<span class="comment"># Total cost for full market intelligence: ~$0.25</span></div>
</div>

<div class="section">
<h2>8. Discovery Manifests</h2>
<div class="code-block"><span class="comment"># x402 payment manifest</span>
curl https://agentservices.to/.well-known/x402

<span class="comment"># OpenAPI 3.1 spec</span>
curl https://agentservices.to/openapi.json

<span class="comment"># Agent skills manifest</span>
curl https://agentservices.to/.well-known/agentskills/agentservices/SKILL.md

<span class="comment"># MCP server card</span>
curl https://agentservices.to/.well-known/mcp/server-card.json

<span class="comment"># llms.txt for LLM crawlers</span>
curl https://agentservices.to/llms.txt</div>
</div>

<div class="section">
<h2>9. x402 Payment Flow</h2>
<p>All paid endpoints use the x402 protocol. When you hit a paid endpoint:</p>
<div class="code-block"><span class="comment"># 1. Agent sends GET request</span>
curl https://agentservices.to/v1/search?q=base+chain

<span class="comment"># 2. Server responds with 402 Payment Required:</span>
<span class="comment"># {</span>
<span class="comment">#   "x402Version": 2,</span>
<span class="comment">#   "accepts": {</span>
<span class="comment">#     "url": "https://agentservices.to/v1/search?q=base+chain",</span>
<span class="comment">#     "maxAmountRequired": 1000,</span>
<span class="comment">#     "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",</span>
<span class="comment">#     "network": "eip155:8453"</span>
<span class="comment">#   }</span>
<span class="comment"># }</span>

<span class="comment"># 3. Agent pays via x402 wallet (CDP, Coinbase Smart Wallet, etc.)</span>
<span class="comment"># 4. Server returns data with payment receipt</span></div>
<p class="note">Network: Base Mainnet (Chain ID 8453). Asset: USDC. Facilitator: CDP.</p>
</div>

<div class="section" style="text-align:center">
<p>
<a href="/">← Back to AgentServices</a> | 
<a href="/docs">API Docs</a> | 
<a href="/openapi.json">OpenAPI Spec</a> | 
<a href="https://github.com/vbkotecha/aiservices-api">GitHub</a>
</p>
<p style="margin-top:8px;color:#555;font-size:0.8em">
AgentServices — Paid APIs for AI agents. 51 services. x402/USDC on Base.
</p>
</div>

</div>
</body>
</html>"""
    return _examples_html


@app.get("/examples", tags=["Developer"], response_class=HTMLResponse)
async def examples_page():
    """Agent-friendly examples page with ready-to-use prompts and curl commands."""
    return HTMLResponse(content=_get_examples())


# ============================================================
# AGENT MEMORY (v5.2.0 — Retention Hook)
# ============================================================

class MemoryRequest(BaseModel):
    value: str = Field(description="Value to store")
    ttl_seconds: int = Field(default=0, description="TTL in seconds (0 = permanent)")

@app.post("/v1/memory/{key}", tags=["Agent Memory"],
          summary="Store Agent Memory",
          description="Store a value keyed to the caller's wallet. Persistent across sessions. $0.01 via x402.")
async def memory_store(key: str, req: MemoryRequest, request: Request):
    """Store agent memory ($0.01 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_store(wallet, key, req.value, req.ttl_seconds)

@app.get("/v1/memory/{key}", tags=["Agent Memory"],
          summary="Retrieve Agent Memory",
          description="Retrieve a stored value by key. $0.01 via x402.")
async def memory_get(key: str, request: Request):
    """Retrieve agent memory ($0.01 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_retrieve(wallet, key)

@app.delete("/v1/memory/{key}", tags=["Agent Memory"],
          summary="Delete Agent Memory",
          description="Delete a stored value. $0.01 via x402.")
async def memory_del(key: str, request: Request):
    """Delete agent memory ($0.01 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_delete(wallet, key)

@app.get("/v1/memory", tags=["Agent Memory"],
          summary="List Agent Memory Keys",
          description="List all stored keys for the caller's wallet. $0.01 via x402.")
async def memory_list(request: Request):
    """List agent memory keys ($0.01 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_list(wallet)

class MemorySearchRequest(BaseModel):
    query: str = Field(description="Search query")

@app.post("/v1/memory/search", tags=["Agent Memory"],
          summary="Search Agent Memory",
          description="Semantic search across all stored values. $0.02 via x402.")
async def memory_search_endpoint(req: MemorySearchRequest, request: Request):
    """Search agent memory ($0.02 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_search(wallet, req.query)


# ============================================================
# SKILL PACKS (v5.2.0 — Bundled Intelligence)
# ============================================================

class SkillRequest(BaseModel):
    symbol: str = Field(default="", description="Crypto symbol or stock ticker")

@app.get("/v1/skills", tags=["Skill Packs"],
          summary="List Available Skills",
          description="List all available skill packs (bundled multi-endpoint intelligence). FREE.")
async def skills_list():
    """List available skills (FREE)"""
    return available_skills()

@app.post("/v1/skills/crypto-dossier", tags=["Skill Packs"],
          summary="Crypto Dossier",
          description="Full crypto intelligence in one call: price + indicators + risk + signal + fear/greed + whales. $0.10 via x402.")
async def skill_crypto(req: SkillRequest):
    """Crypto dossier ($0.10 via x402)"""
    return crypto_dossier(req.symbol)

@app.post("/v1/skills/stock-dossier", tags=["Skill Packs"],
          summary="Stock Dossier",
          description="Full stock intelligence: quote + FX + sentiment. $0.05 via x402.")
async def skill_stock(req: SkillRequest):
    """Stock dossier ($0.05 via x402)"""
    return stock_dossier(req.symbol)

@app.get("/v1/skills/market-overview", tags=["Skill Packs"],
          summary="Market Overview",
          description="Full market pulse: fear/greed + BTC signal + whales + regime classification. $0.05 via x402.")
async def skill_market():
    """Market overview ($0.05 via x402)"""
    return market_overview()


# --- Privacy Policy (required for Anthropic Connector Directory) ---
@app.get("/privacy", tags=["Legal"], summary="Privacy Policy")
async def privacy_policy():
    """AgentServices Privacy Policy — required for MCP directory submissions."""
    return {
        "policy_version": "1.0",
        "last_updated": "2026-07-08",
        "data_collection": {
            "what_we_collect": [
                "API request parameters (e.g., crypto symbols, URLs, IP addresses provided by caller)",
                "Payment metadata from x402 protocol (transaction hashes, wallet addresses)",
                "Standard HTTP request headers (User-Agent, Accept, Content-Type)",
                "Timestamp and endpoint path for rate limiting and analytics"
            ],
            "what_we_do_not_collect": [
                "Personal names, emails, phone numbers",
                "Browser cookies or tracking pixels",
                "Location data beyond what the caller explicitly provides",
                "Biometric or identity data"
            ]
        },
        "data_usage": {
            "purpose": "All collected data is used solely for processing API requests and returning responses. Payment metadata is used for x402 protocol verification only.",
            "retention": "Request logs are retained for 30 days for debugging and rate limiting, then automatically purged. Payment metadata is retained per on-chain immutability (we do not store it separately).",
            "sharing": "We do not sell, share, or transfer data to third parties. Data is processed in-memory for request fulfillment and discarded."
        },
        "security": {
            "transport": "All communication uses HTTPS/TLS 1.2+",
            "authentication": "Free endpoints require no authentication. Paid endpoints use x402 (HTTP 402) payment protocol with USDC on Base blockchain. No passwords or OAuth tokens are collected.",
            "infrastructure": "Hosted on Railway (SOC 2 Type II certified infrastructure provider). No on-disk persistent storage of request data."
        },
        "user_rights": {
            "data_access": "Users can access their request history via API logs (available on request)",
            "data_deletion": "Request data is automatically purged after 30 days. Users can request immediate deletion by contacting support.",
            "opt_out": "Users can stop using the service at any time. No accounts or subscriptions to cancel."
        },
        "contact": "For privacy inquiries: hustlemode@agentmail.to",
        "mcp_specific": {
            "origin_validation": "The MCP server validates Origin headers for enhanced security in Claude environments.",
            "no_user_data_modification": "All tools are read-only (readOnlyHint: true). AgentServices does not modify files, settings, or data on the user's system.",
            "external_calls": "Tools call AgentServices' own first-party APIs. No third-party API calls are made on behalf of the user."
        }
    }


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    """OAuth Protected Resource metadata (RFC 9728).
    Declares that our MCP server uses no authentication for free tools.
    Required for Anthropic Connector Directory compliance."""
    return {
        "resource": "https://agentservices.to/mcp",
        "authorization_servers": [],
        "bearer_methods_supported": [],
        "resource_documentation": "https://agentservices.to/docs",
        "resource_name": "AgentServices MCP Server",
        "resource_description": "Free tools require no auth. Paid tools use x402 (HTTP 402) payment. No OAuth required for discovery or free tool access.",
    }


@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    """OAuth Authorization Server metadata.
    AgentServices does not operate an OAuth server — free tools are public, paid tools use x402."""
    return {
        "issuer": "https://agentservices.to",
        "authorization_endpoint": None,
        "token_endpoint": None,
        "response_types_supported": [],
        "grant_types_supported": [],
        "note": "AgentServices does not use OAuth. Free tools are publicly accessible. Paid tools use x402 micropayments (HTTP 402).",
    }


