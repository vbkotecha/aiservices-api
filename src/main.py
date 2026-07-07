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
    defi_strategy_report, market_pulse,
)
from inference_gateway import list_models as list_inference_models, inference, quick_complete
from tradfi_data import get_stock_quote, get_stock_history, get_sec_filings, get_commodities, get_economic_indicators, get_fx_rates
from utility_data import extract_web_content, scan_package_security, seo_keywords

AISERVICES_PAY_TO = "0x9863aB6242663FCc84c33632741711dB78f8Fd15"
WALLET = os.environ.get("WALLET_ADDRESS", AISERVICES_PAY_TO)

app = FastAPI(
    title="AgentServices",
    version="5.2.0",
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
X402_FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "https://api.cdp.coinbase.com/platform/v2/x402")

# Multi-chain: Dexter facilitator (x402.dexter.cash) supports Base + BSC + more.
# CDP facilitator supports Base only. We detect and register accordingly.
X402_IS_MULTICHAIN = any(d in X402_FACILITATOR_URL.lower() for d in ("dexter", "infra402", "aeon"))
X402_NETWORKS = [X402_BASE_NETWORK] + ([X402_BSC_NETWORK] if X402_IS_MULTICHAIN else [])
X402_NETWORK_LABEL = "Base + BSC" if X402_IS_MULTICHAIN else "Base"

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
    for net in X402_NETWORKS:
        payment_server.register(net, ExactEvmServerScheme())
    payment_server.register_extension(bazaar_resource_server_extension)

    def _payment_options(wallet: str, price: str) -> list:
        """Generate PaymentOption for every supported network (multi-chain)."""
        return [
            PaymentOption(scheme="exact", pay_to=wallet, price=price, network=net)
            for net in X402_NETWORKS
        ]

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
    """Route based on domain: aiservices.to = website, api.aiservices.to = API JSON."""
    host = request.headers.get("host", "").split(":")[0].lower()
    if host.startswith("api."):
        return {
            "name": "AgentServices",
            "tagline": "Paid APIs for AI agents — data, inference, and market intelligence",
            "version": "4.1.0",
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
        "version": "4.0.0",
        "x402_enabled": X402_ENABLED,
        "x402_error": X402_ERROR,
        "x402_networks": X402_NETWORKS,
        "x402_facilitator": X402_FACILITATOR_URL,
        "services": ["crypto_prices", "indicators", "defi_yields", "fear_greed", "geo", "metadata", "search", "swap_quote", "trending", "gas", "predictions", "news", "social_trending", "global", "disputes", "policies", "marketing_sentiment", "marketing_trends", "marketing_competitors", "marketing_content_gaps", "marketing_ad_copy", "whales", "exchange_flows", "correlation", "defi_tvl", "stablecoin_flows", "github_velocity", "agent_context", "macro", "inference", "quick_complete", "token_risk", "crypto_signals", "hn_sentiment", "npm_stats", "github_trending", "yield_comparison", "stock_quote", "stock_history", "sec_filings", "commodities", "economic_indicators", "fx_rates", "web_extract", "package_security", "seo_keywords", "deep_research", "portfolio_intelligence", "defi_strategy", "market_pulse"],
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
        "website": "https://api.aiservices.to",
        "repository": "https://github.com/vbkotecha/aiservices-api",
        "homepage": "https://api.aiservices.to",
        "license": "MIT",
        "spec": "x402-service-manifest/1",
    }


@app.get("/.well-known/agent.json")
async def agent_json():
    """Agent discovery manifest for AI agent platforms and crawlers."""
    return {
        "name": "AgentServices",
        "version": "4.1.0",
        "description": "Paid data APIs for AI agents — crypto, DeFi, DEX, prediction markets, news, search, geolocation, metadata, on-chain analytics, whale tracking, DeFi TVL, correlation matrix, stablecoin flows, GitHub velocity, macro indicators",
        "url": "https://api.aiservices.to",
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
        "docs": "https://api.aiservices.to/docs",
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
        "description": "Paid APIs for AI agents — crypto data, stocks, SEC filings, commodities, FX, inference gateway, market signals, web extraction, security scanning, and MCP integration. 47 services, 35 paid.",
        "network": "eip155:8453",
        "facilitator": "coinbase",
        "payTo": X402_WALLET,
        "currency": "USDC",
        "website": "https://aiservices.to",
        "apiBaseUrl": "https://api.aiservices.to",
        "repository": "https://github.com/vbkotecha/aiservices-api",
        "documentation": "https://api.aiservices.to/docs",
        "services": paid_services + free_services,
        "extensions": {
            "bazaar": {"discoverable": True}
        },
    }


@app.get("/llms.txt")
async def llms_txt():
    """LLM-friendly API description for agent crawlers and AI discovery."""
    lines = [
        "# AgentServices",
        "",
        "> Paid APIs for AI agents. 47 services, 35 paid. Crypto data, stocks, SEC filings, commodities, FX, inference gateway (gpt-5.4/5.5), token risk scoring, crypto signals, web extraction, package security, SEO research, and more. All via x402 (USDC on Base).",
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
        "",
        "## Free Agent Tools",
        "- GET /v1/agent-context — Paste-ready market context for LLM prompts",
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
        "name": "AgentServices",
        "short_name": "AgentServices",
        "description": "Paid data APIs for AI agents — crypto, DeFi, geo, web metadata, marketing intelligence, dispute resolution",
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
<p>Connect AgentServices directly to Claude, Cursor, or any MCP client:</p>
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

