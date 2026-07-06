"""
DEX aggregation module — 0x API passthrough for token swaps and pricing.
Revenue model: 0x swap fees can be routed to our address.
Also includes trending tokens and gas data from free APIs.
"""
import os
import urllib.request
import json
import time
from fastapi import HTTPException

# 0x API requires an API key now (free tier: 100K calls/month)
ZEROX_API_KEY = os.environ.get("ZEROX_API_KEY", "")

# 0x API base URLs per chain (new unified API format)
ZEROX_BASE = {
    "ethereum": "https://api.0x.org/swap",
    "base": "https://base-api.0x.org/swap",
    "polygon": "https://polygon-api.0x.org/swap",
    "arbitrum": "https://arbitrum-api.0x.org/swap",
    "optimism": "https://optimism-api.0x.org/swap",
    "bsc": "https://bsc-api.0x.org/swap",
}

# Optional: affiliate address for fee routing
AFFILIATE_ADDRESS = os.environ.get("AFFILIATE_ADDRESS", "")


def _fetch(url, timeout=10):
    headers = {"User-Agent": "AIServices/2.0"}
    if ZEROX_API_KEY:
        headers["0x-api-key"] = ZEROX_API_KEY
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise HTTPException(status_code=503, detail="DEX API requires ZEROX_API_KEY — not configured. Set ZEROX_API_KEY env var.")
        raise HTTPException(status_code=502, detail=f"DEX API error: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"DEX error: {str(e)}")


def get_swap_quote(chain: str, sell_token: str, buy_token: str, sell_amount: str = None, buy_amount: str = None):
    """
    Get a DEX swap quote from 0x API.
    Pass either sell_amount (in token units) or buy_amount.
    """
    if not ZEROX_API_KEY:
        raise HTTPException(status_code=503, detail="DEX swap quotes require ZEROX_API_KEY configuration. Free endpoints: /v1/trending, /v1/gas, /v1/price/{symbol}")

    base = ZEROX_BASE.get(chain.lower(), ZEROX_BASE["ethereum"])
    chain_lower = chain.lower()
    
    # 0x v2 uses permit2 endpoint
    params_list = [
        f"chain={chain_lower}",
        f"sellToken={sell_token}",
        f"buyToken={buy_token}",
    ]
    if sell_amount:
        params_list.append(f"sellAmount={sell_amount}")
    if buy_amount:
        params_list.append(f"buyAmount={buy_amount}")
    if AFFILIATE_ADDRESS:
        params_list.append(f"affiliateAddress={AFFILIATE_ADDRESS}")
        params_list.append("swapFeeRecipientBps=100")  # 1% fee
    
    query_string = "&".join(params_list)
    
    # Try /permit2/quote endpoint
    endpoint = f"{base}/permit2/quote?{query_string}"
    try:
        data = _fetch(endpoint)
    except Exception:
        # Fallback to /v1/quote
        endpoint = f"{base}/v1/quote?{query_string}"
        data = _fetch(endpoint)
    
    return {
        "chain": chain_lower,
        "sell_token": sell_token,
        "buy_token": buy_token,
        "price": data.get("price"),
        "sell_amount": data.get("sellAmount"),
        "buy_amount": data.get("buyAmount"),
        "sources": data.get("sources", []),
        "gas_estimate": data.get("gas"),
        "timestamp": int(time.time()),
        "raw": data,  # Full quote data for execution
    }


def get_token_price_0x(chain: str, token: str):
    """Get token price via 0x API."""
    base = ZEROX_BASE.get(chain.lower(), ZEROX_BASE["ethereum"])
    # Use WETH as reference for price
    data = _fetch(f"{base}/v1/price?sellToken={token}&buyToken=WETH&sellAmount=1000000000000000000")
    return {
        "chain": chain.lower(),
        "token": token,
        "price_in_weth": data.get("price"),
        "timestamp": int(time.time()),
    }


def get_trending_tokens():
    """Get trending tokens from CoinGecko (free API)."""
    data = _fetch("https://api.coingecko.com/api/v3/search/trending")
    coins = []
    for item in data.get("coins", []):
        coin = item.get("item", {})
        coins.append({
            "id": coin.get("id"),
            "name": coin.get("name"),
            "symbol": coin.get("symbol"),
            "market_cap_rank": coin.get("market_cap_rank"),
            "score": coin.get("score"),
            "thumb": coin.get("thumb"),
            "price_btc": coin.get("price_btc"),
        })
    return {
        "trending": coins,
        "count": len(coins),
        "timestamp": int(time.time()),
    }


def get_gas_tracker():
    """Get gas prices for Ethereum from multiple sources."""
    # Try Etherscan-compatible gas oracle
    try:
        data = _fetch("https://api.etherscan.io/v2/api?chainid=1&module=gastracker&action=gasoracle")
        result = data.get("result", {})
        return {
            "chain": "ethereum",
            "slow_gwei": int(float(result.get("SafeGasPrice", 0))),
            "standard_gwei": int(float(result.get("ProposeGasPrice", 0))),
            "fast_gwei": int(float(result.get("FastGasPrice", 0))),
            "eth_price_usd": float(result.get("ethUsdPrice", 0)),
            "timestamp": int(time.time()),
        }
    except Exception:
        # Fallback to a block native estimate
        data = _fetch("https://gasstation.polygon.technology/api/v2")
        return {
            "chain": "polygon",
            "safe_low": data.get("safeLow"),
            "standard": data.get("standard"),
            "fast": data.get("fast"),
            "timestamp": int(time.time()),
        }
