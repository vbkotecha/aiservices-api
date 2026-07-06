"""
Prediction market data module — Polymarket and other prediction markets.
Uses free public APIs.
"""
import urllib.request
import json
import time
from fastapi import HTTPException

# Polymarket API base
POLYMARKET_API = "https://gamma-api.polymarket.com"
POLYMARKET_DATA = "https://data-api.polymarket.com"

# Kalshi API
KALSHI_API = "https://api.elections.kalshi.com"

def _fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={
        "User-Agent": "AgentServices/2.0",
        "Accept": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Prediction market API error: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error: {str(e)}")


def get_polymarket_markets(limit: int = 20, active_only: bool = True):
    """Get active prediction markets from Polymarket."""
    params = []
    if active_only:
        params.append("active=true")
    params.append("closed=false")
    params.append("order=volume24hr")
    params.append("ascending=false")
    params.append(f"limit={min(limit, 50)}")
    
    url = f"{POLYMARKET_API}/markets?{'&'.join(params)}"
    data = _fetch(url)
    
    markets = []
    for m in data if isinstance(data, list) else data.get("markets", data.get("data", [])):
        markets.append({
            "id": m.get("id") or m.get("condition_id"),
            "question": m.get("question"),
            "slug": m.get("slug"),
            "category": m.get("category"),
            "outcome_yes": m.get("outcomePrices", ["", ""])[0] if isinstance(m.get("outcomePrices"), list) else None,
            "outcome_no": m.get("outcomePrices", ["", ""])[1] if isinstance(m.get("outcomePrices"), list) else None,
            "volume_24h": m.get("volume24hr") or m.get("volume24hrClob"),
            "volume_total": m.get("volumeNum") or m.get("volumeClob"),
            "liquidity": m.get("liquidityNum") or m.get("liquidityClob"),
            "end_date": m.get("endDate"),
            "image": m.get("image") or m.get("icon"),
        })
    
    return {
        "platform": "polymarket",
        "markets": markets[:limit],
        "count": len(markets[:limit]),
        "timestamp": int(time.time()),
    }


def get_polymarket_market(slug_or_id: str):
    """Get details for a specific Polymarket market."""
    url = f"{POLYMARKET_API}/markets?slug={slug_or_id}"
    data = _fetch(url)
    markets = data if isinstance(data, list) else data.get("markets", data.get("data", []))
    if not markets:
        # Try by ID
        url = f"{POLYMARKET_API}/markets/{slug_or_id}"
        data = _fetch(url)
        markets = [data] if data else []
    
    if not markets:
        raise HTTPException(status_code=404, detail="Market not found")
    
    m = markets[0]
    return {
        "platform": "polymarket",
        "id": m.get("id") or m.get("condition_id"),
        "question": m.get("question"),
        "description": m.get("description"),
        "category": m.get("category"),
        "outcome_prices": m.get("outcomePrices"),
        "volume_24h": m.get("volume24hr") or m.get("volume24hrClob"),
        "volume_total": m.get("volumeNum") or m.get("volumeClob"),
        "liquidity": m.get("liquidityNum") or m.get("liquidityClob"),
        "end_date": m.get("endDate"),
        "active": m.get("active"),
        "closed": m.get("closed"),
        "image": m.get("image") or m.get("icon"),
        "timestamp": int(time.time()),
    }


def get_prediction_summary():
    """Get a summary of top prediction markets across platforms."""
    poly = get_polymarket_markets(limit=10)
    
    return {
        "top_markets": poly["markets"],
        "platforms": ["polymarket"],
        "total_markets_shown": poly["count"],
        "timestamp": int(time.time()),
    }
