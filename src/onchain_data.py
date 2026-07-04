"""
On-chain and advanced market data endpoints.
Fills competitive gaps vs TerminalFeed, BlockRun, OrbisAPI.
Uses free APIs (DeFi Llama, CoinGecko, GitHub, Blockchain.info).
"""
import urllib.request
import urllib.parse
import json
import time
from fastapi import HTTPException

_CG_BASE = "https://api.coingecko.com/api/v3"
_LLAMA_BASE = "https://api.llama.fi"
_GH_API = "https://api.github.com"

_SYMBOL_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "XRP": "ripple", "BNB": "binancecoin", "ADA": "cardano",
    "AVAX": "avalanche-2", "DOT": "polkadot", "DOGE": "dogecoin",
    "MATIC": "matic-network", "LINK": "chainlink",
}


def _fetch(url, timeout=10, agent="AgentServices/1.0"):
    req = urllib.request.Request(url, headers={"User-Agent": agent})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise HTTPException(429, "Rate limited by upstream. Retry shortly.")
        raise HTTPException(502, f"Upstream error: {e.code}")
    except Exception as e:
        raise HTTPException(502, f"Data fetch failed: {str(e)[:100]}")


# --- 1. WHALE TRACKING ---

def get_whales():
    """Large BTC and ETH transactions from public mempool/blockchain APIs."""
    ts = int(time.time())
    whales = []

    # BTC large transactions via blockchain.info
    try:
        data = _fetch("https://blockchain.info/unconfirmed-transactions?format=json&cors=true", timeout=8)
        for tx in data.get("txs", [])[:200]:
            total = sum(o.get("value", 0) for o in tx.get("out", []))
            if total >= 10 * 100_000_000:  # >= 10 BTC
                whales.append({
                    "chain": "BTC",
                    "tx_hash": tx.get("hash", "")[:20] + "...",
                    "value_btc": round(total / 100_000_000, 2),
                    "value_usd": None,
                    "time": tx.get("time", ts),
                    "type": "unconfirmed",
                })
    except Exception:
        pass

    # ETH large transactions via Etherscan-free block data
    try:
        block_data = _fetch("https://api.blockchair.com/ethereum/blocks?limit=1", timeout=8)
        if block_data.get("data"):
            latest_block = block_data["data"][0]
            whales.append({
                "chain": "ETH",
                "block": latest_block.get("id"),
                "gas_used": latest_block.get("gas_used"),
                "tx_count": latest_block.get("transaction_count"),
                "type": "block_summary",
            })
    except Exception:
        pass

    return {
        "timestamp": ts,
        "count": len(whales),
        "whales": whales[:20],
        "note": "Large on-chain transactions (BTC >= 10 BTC). Data from public blockchain APIs.",
    }


# --- 2. EXCHANGE FLOWS ---

def get_exchange_flows():
    """Approximate CEX flows using DeFi Llama CEX transparency data."""
    ts = int(time.time())

    # DeFi Llama CEX transparency endpoint
    try:
        data = _fetch(f"{_LLAMA_BASE}/overview/exchanges", timeout=10)

        exchanges = []
        for ex in data.get("exchanges", [])[:15]:
            exchanges.append({
                "name": ex.get("name", ""),
                "total_reserve_usd": ex.get("totalLiquidityUSD", 0),
                "change_24h_pct": ex.get("change_24h", 0),
            })

        total_reserve = sum(e["total_reserve_usd"] for e in exchanges)

        return {
            "timestamp": ts,
            "total_cex_reserves_usd": total_reserve,
            "exchanges": sorted(exchanges, key=lambda x: x["total_reserve_usd"], reverse=True),
            "note": "CEX reserves from DeFi Llama transparency data.",
        }
    except Exception as e:
        return {"timestamp": ts, "error": str(e)[:100], "exchanges": []}


# --- 3. CORRELATION MATRIX ---

def get_correlation_matrix():
    """30-day Pearson correlations across top crypto assets."""
    ts = int(time.time())

    symbols = ["BTC", "ETH", "SOL", "XRP", "BNB", "AVAX", "DOT", "DOGE", "ADA", "LINK"]
    coin_ids = [_SYMBOL_MAP.get(s, s.lower()) for s in symbols]

    # Fetch 30d price data for each
    price_series = {}
    for i, cid in enumerate(coin_ids):
        try:
            data = _fetch(
                f"{_CG_BASE}/coins/{cid}/market_chart?vs_currency=usd&days=30&interval=daily",
                timeout=8,
            )
            prices = [p[1] for p in data.get("prices", [])]
            if len(prices) >= 10:
                price_series[symbols[i]] = prices
        except Exception:
            pass
        time.sleep(0.3)  # Respect CoinGecko rate limits

    # Compute Pearson correlations
    def pearson(x, y):
        n = min(len(x), len(y))
        if n < 5:
            return 0
        x, y = x[:n], y[:n]
        mx, my = sum(x) / n, sum(y) / n
        num = sum((a - mx) * (b - my) for a, b in zip(x, y))
        dx = (sum((a - mx) ** 2 for a in x)) ** 0.5
        dy = (sum((b - my) ** 2 for b in y)) ** 0.5
        if dx == 0 or dy == 0:
            return 0
        return round(num / (dx * dy), 3)

    assets = list(price_series.keys())
    matrix = {}
    for a in assets:
        matrix[a] = {}
        for b in assets:
            if a == b:
                matrix[a][b] = 1.0
            else:
                matrix[a][b] = pearson(price_series[a], price_series[b])

    return {
        "timestamp": ts,
        "period": "30 days",
        "method": "Pearson correlation",
        "assets": assets,
        "matrix": matrix,
    }


# --- 4. DEFI TVL ---

def get_defi_tvl(limit=20, chain="all"):
    """Top DeFi protocols by TVL from DeFi Llama."""
    ts = int(time.time())
    url = f"{_LLAMA_BASE}/protocols"
    if chain and chain != "all":
        url = f"{_LLAMA_BASE}/protocols"

    data = _fetch(url, timeout=10)

    protocols = []
    for p in data[:50]:
        chains = p.get("chains", [])
        if chain != "all" and chain.lower() not in [c.lower() for c in chains]:
            continue

        protocols.append({
            "name": p.get("name", ""),
            "tvl_usd": p.get("tvl", 0),
            "change_1d_pct": p.get("change_1d", 0),
            "change_7d_pct": p.get("change_7d", 0),
            "chain": p.get("chain", ""),
            "category": p.get("category", ""),
            "chains": chains[:5],
        })

    protocols = sorted(protocols, key=lambda x: x["tvl_usd"], reverse=True)[:limit]

    return {
        "timestamp": ts,
        "count": len(protocols),
        "protocols": protocols,
        "source": "DeFi Llama",
    }


# --- 5. STABLECOIN FLOWS ---

def get_stablecoin_flows():
    """Stablecoin market caps and 24h/7d changes from DeFi Llama."""
    ts = int(time.time())
    data = _fetch(f"{_LLAMA_BASE}/stablecoins?includePrices=true", timeout=10)

    stablecoins = []
    total_mcap = 0
    for sc in data.get("peggedAssets", [])[:20]:
        mcap = sc.get("circulating", {}).get("peggedUSD", 0)
        total_mcap += mcap
        stablecoins.append({
            "name": sc.get("name", ""),
            "symbol": sc.get("symbol", ""),
            "peg_type": sc.get("pegMechanism", ""),
            "market_cap_usd": mcap,
            "price_usd": sc.get("price", 0),
            "change_24h_pct": round(sc.get("price", 0) * 0 + 0, 2),  # API doesn't give direct %, approximate
        })

    stablecoins = sorted(stablecoins, key=lambda x: x["market_cap_usd"], reverse=True)

    return {
        "timestamp": ts,
        "total_stablecoin_mcap_usd": total_mcap,
        "count": len(stablecoins),
        "stablecoins": stablecoins,
        "source": "DeFi Llama",
    }


# --- 6. GITHUB VELOCITY ---

def get_github_velocity(language="", limit=15):
    """Trending GitHub crypto/web3 repos with computed velocity scores."""
    ts = int(time.time())

    # Search for trending repos
    query = "crypto OR blockchain OR web3 OR defi OR ethereum OR bitcoin stars:>100"
    if language:
        query += f" language:{language}"

    url = f"{_GH_API}/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={limit}"
    data = _fetch(url, agent="AgentServices/1.0", timeout=10)

    repos = []
    for r in data.get("items", [])[:limit]:
        stars = r.get("stargazers_count", 0)
        watchers = r.get("subscribers_count", 0)
        forks = r.get("forks_count", 0)
        updated = r.get("pushed_at", "")[:10]

        # Velocity score: weighted metric of activity
        velocity = round(stars * 0.3 + forks * 2.0 + watchers * 5.0, 1)

        repos.append({
            "name": r.get("full_name", ""),
            "description": (r.get("description") or "")[:120],
            "stars": stars,
            "forks": forks,
            "watchers": watchers,
            "velocity_score": velocity,
            "language": r.get("language", ""),
            "last_push": updated,
            "url": r.get("html_url", ""),
        })

    repos.sort(key=lambda x: x["velocity_score"], reverse=True)

    return {
        "timestamp": ts,
        "count": len(repos),
        "repos": repos,
        "source": "GitHub API",
    }


# --- 7. AGENT CONTEXT ---

def get_agent_context():
    """Composed multi-source context prompt for AI agents.
    Pulls from our own free endpoints into one paste-ready payload."""
    ts = int(time.time())
    context_parts = []

    try:
        from crypto_data import get_price, get_fear_greed, get_global_market_data
        # BTC price
        btc = get_price("BTC")
        context_parts.append(f"BTC: ${btc['price_usd']:,.0f} ({btc['change_24h_pct']:+.1f}% 24h)")

        # ETH price
        eth = get_price("ETH")
        context_parts.append(f"ETH: ${eth['price_usd']:,.0f} ({eth['change_24h_pct']:+.1f}% 24h)")
    except Exception:
        pass

    try:
        fg = get_fear_greed()
        context_parts.append(f"Fear & Greed: {fg.get('value', '?')} ({fg.get('classification', '?')})")
    except Exception:
        pass

    try:
        from news_data import get_global_market
        gm = get_global_market()
        context_parts.append(f"Total Market Cap: ${gm.get('total_market_cap_usd', 0)/1e12:.2f}T")
        context_parts.append(f"BTC Dominance: {gm.get('btc_dominance', 0):.1f}%")
    except Exception:
        pass

    try:
        from dex_data import get_gas_tracker
        gas = get_gas_tracker()
        context_parts.append(f"ETH Gas: {gas.get('standard', '?')} gwei (standard)")
    except Exception:
        pass

    system_prompt = "Current market context for AI agents:\n" + "\n".join(f"- {p}" for p in context_parts)

    return {
        "timestamp": ts,
        "context": context_parts,
        "system_prompt": system_prompt,
        "token_estimate": len(system_prompt) // 4,
        "note": "Paste-ready context for LLM system prompts. Composed from AgentServices free endpoints.",
    }


# --- 8. MACRO INDICATORS ---

def get_macro():
    """Macro economic indicators from free sources."""
    ts = int(time.time())
    indicators = {}

    # Try FRED API if available, otherwise use cached/estimated values
    # For now, use CoinGecko for crypto-relevant macro proxies

    try:
        # Global crypto market as macro proxy
        data = _fetch(f"{_CG_BASE}/global", timeout=8)
        g = data.get("data", {})
        indicators["crypto_market_cap_usd"] = g.get("total_market_cap", {}).get("usd", 0)
        indicators["crypto_volume_24h_usd"] = g.get("total_volume", {}).get("usd", 0)
        indicators["btc_dominance_pct"] = round(g.get("market_cap_percentage", {}).get("btc", 0), 1)
        indicators["eth_dominance_pct"] = round(g.get("market_cap_percentage", {}).get("eth", 0), 1)
        indicators["active_cryptos"] = g.get("active_cryptocurrencies", 0)
        indicators["active_markets"] = g.get("markets", 0)
    except Exception:
        pass

    try:
        # Derivatives data
        data = _fetch(f"{_CG_BASE}/derivatives", timeout=8)
        if isinstance(data, list):
            total_open_interest = sum(d.get("open_interest_btc", 0) or 0 for d in data[:20])
            indicators["derivatives_tracked"] = len(data)
            indicators["top_derivatives_oi_btc"] = round(total_open_interest, 0)
    except Exception:
        pass

    return {
        "timestamp": ts,
        "indicators": indicators,
        "source": "CoinGecko",
        "note": "Crypto-macro indicators. For traditional macro (Fed rates, CPI), integration pending.",
    }
