import urllib.request
import json
import time
from fastapi import HTTPException

_CG_BASE = "https://api.coingecko.com/api/v3"

_SYMBOL_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "XRP": "ripple", "ADA": "cardano", "AVAX": "avalanche-2",
    "LINK": "chainlink", "DOT": "polkadot", "DOGE": "dogecoin",
    "HBAR": "hedera-hashgraph", "LTC": "litecoin", "BCH": "bitcoin-cash",
    "XLM": "stellar", "XTZ": "tezos", "APT": "aptos", "SHIB": "shiba-inu"
}

def _fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "AIServices/1.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise HTTPException(status_code=429, detail="Rate limited by upstream data provider. Please retry in a moment.")
        raise HTTPException(status_code=502, detail=f"Upstream error: {e.code}")

def get_price(symbol):
    coin_id = _SYMBOL_MAP.get(symbol.upper(), symbol.lower())
    url = _CG_BASE + "/simple/price?ids=" + coin_id + "&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
    data = _fetch(url)
    if coin_id not in data:
        raise HTTPException(status_code=404, detail="Symbol not found: " + symbol)
    info = data[coin_id]
    return {"symbol": symbol.upper(), "price_usd": info.get("usd", 0), "change_24h_pct": info.get("usd_24h_change", 0), "volume_24h_usd": info.get("usd_24h_vol", 0), "market_cap_usd": info.get("usd_market_cap", 0), "timestamp": int(time.time())}

def get_multi_price(symbols):
    coin_ids = []
    id_map = {}
    for s in symbols:
        cid = _SYMBOL_MAP.get(s.strip().upper(), s.strip().lower())
        coin_ids.append(cid)
        id_map[cid] = s.strip().upper()
    url = _CG_BASE + "/simple/price?ids=" + ",".join(coin_ids) + "&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
    data = _fetch(url)
    result = {}
    for cid, info in data.items():
        sym = id_map.get(cid, cid.upper())
        result[sym] = {"price_usd": info.get("usd", 0), "change_24h_pct": info.get("usd_24h_change", 0), "volume_24h_usd": info.get("usd_24h_vol", 0), "market_cap_usd": info.get("usd_market_cap", 0)}
    return {"prices": result, "timestamp": int(time.time())}

def get_indicators(symbol):
    coin_id = _SYMBOL_MAP.get(symbol.upper(), symbol.lower())
    ohlc = _fetch(_CG_BASE + "/coins/" + coin_id + "/ohlc?vs_currency=usd&days=7")
    if not ohlc or len(ohlc) < 20:
        raise HTTPException(status_code=404, detail="Insufficient data")
    closes = [c[4] for c in ohlc]
    gains = [max(0, closes[i]-closes[i-1]) for i in range(1, min(len(closes), 15))]
    losses = [max(0, closes[i-1]-closes[i]) for i in range(1, min(len(closes), 15))]
    avg_gain = sum(gains)/len(gains) if gains else 0
    avg_loss = sum(losses)/len(losses) if losses else 0
    rsi = 100 - (100 / (1 + (avg_gain/avg_loss if avg_loss > 0 else 100))) if avg_loss > 0 else 100
    sma = sum(closes[-20:])/20 if len(closes) >= 20 else sum(closes)/len(closes)
    variance = sum((c-sma)**2 for c in closes[-20:])/20 if len(closes) >= 20 else 0
    std = variance ** 0.5
    ranges = [c[2]-c[3] for c in ohlc[-14:]]
    atr = sum(ranges)/len(ranges) if ranges else 0
    return {"symbol": symbol.upper(), "rsi_14": round(rsi, 2), "bollinger_bands": {"upper": round(sma+2*std, 4), "middle": round(sma, 4), "lower": round(sma-2*std, 4)}, "atr_14": round(atr, 4), "support_24h": round(min(c[3] for c in ohlc[-24:]), 4), "resistance_24h": round(max(c[2] for c in ohlc[-24:]), 4), "current_price": closes[-1], "timestamp": int(time.time())}

def get_fear_greed():
    data = _fetch("https://api.alternative.me/fng/?limit=1")
    item = data["data"][0]
    return {"index": int(item["value"]), "label": item["value_classification"]}

def get_defi_yields():
    data = _fetch("https://yields.llama.fi/pools", timeout=15)
    pools = [p for p in data.get("data", []) if p.get("tvlUsd", 0) > 10000000 and p.get("apy", 0) > 0]
    pools.sort(key=lambda x: x.get("tvlUsd", 0), reverse=True)
    top = [{"project": p.get("project"), "chain": p.get("chain"), "symbol": p.get("symbol"), "tvl_usd": p.get("tvlUsd", 0), "apy": p.get("apy", 0)} for p in pools[:20]]
    return {"top_pools": top, "count": len(top), "timestamp": int(time.time())}
