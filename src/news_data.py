"""
News and social data module — crypto news, trending social, and whale tracking.
Uses free public APIs and RSS feeds.
"""
import urllib.request
import json
import time
import xml.etree.ElementTree as ET
from fastapi import HTTPException

def _fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={
        "User-Agent": "AgentServices/2.0",
        "Accept": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"News API error: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error: {str(e)}")


def _fetch_rss(url, source_name, limit=10, timeout=10):
    """Fetch and parse an RSS feed into structured news items."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "AgentServices/2.0",
        "Accept": "application/rss+xml, application/xml, text/xml",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        xml_data = resp.read().decode("utf-8", errors="ignore")
        root = ET.fromstring(xml_data)
        items = []
        # RSS 2.0 format
        for item in root.iter("item"):
            title = item.findtext("title", default="")
            link = item.findtext("link", default="")
            pub_date = item.findtext("pubDate", default="")
            desc_el = item.find("description")
            desc = desc_el.text if desc_el is not None and desc_el.text else ""
            items.append({
                "title": title,
                "url": link,
                "source": source_name,
                "body": desc[:200] if desc else "",
                "published_at": pub_date,
            })
            if len(items) >= limit:
                break
        return items
    except Exception:
        return []


def get_crypto_news(limit: int = 20, category: str = ""):
    """
    Get latest crypto news.
    Tries CryptoPanics (if API key), then RSS feeds from multiple sources.
    """
    import os
    api_key = os.environ.get("CRYPTOPANICS_TOKEN", "")

    if api_key:
        params = f"auth_token={api_key}&public=true"
        if category:
            params += f"&currencies={category}"
        params += f"&kind=news"
        try:
            data = _fetch(f"https://cryptopanic.com/api/v1/posts/?{params}")
            results = data.get("results", [])[:limit]
            news = []
            for item in results:
                news.append({
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source": item.get("source", {}).get("title", "") if isinstance(item.get("source"), dict) else item.get("source", ""),
                    "published_at": item.get("published_at"),
                    "votes": item.get("votes"),
                    "categories": item.get("categories"),
                })
            return {
                "news": news,
                "count": len(news),
                "source": "cryptopanic",
                "timestamp": int(time.time()),
            }
        except Exception:
            pass  # Fall through to RSS

    # RSS fallback — multiple feeds for redundancy
    feeds = [
        ("https://cointelegraph.com/rss", "CoinTelegraph"),
        ("https://bitcoinist.com/feed/", "Bitcoinist"),
        ("https://news.bitcoin.com/feed/", "Bitcoin.com"),
        ("https://www.newsbtc.com/feed/", "NewsBTC"),
    ]
    all_news = []
    per_feed = max(limit // len(feeds) + 2, 5)  # Distribute limit across feeds
    for feed_url, source in feeds:
        items = _fetch_rss(feed_url, source, limit=per_feed)
        all_news.extend(items)

    # Sort by position (feeds are already chronological)
    all_news = all_news[:limit]
    return {
        "news": all_news,
        "count": len(all_news),
        "source": "rss-multi",
        "timestamp": int(time.time()),
    }


def get_social_trending():
    """
    Get trending crypto topics and social sentiment indicators.
    Combines CoinGecko trending search + social mentions.
    """
    # Trending searches on CoinGecko
    trending_data = _fetch("https://api.coingecko.com/api/v3/search/trending")
    
    trending_coins = []
    for item in trending_data.get("coins", []):
        coin = item.get("item", {})
        trending_coins.append({
            "name": coin.get("name"),
            "symbol": coin.get("symbol"),
            "rank": coin.get("market_cap_rank"),
            "score": coin.get("score"),
        })
    
    # Trending categories
    trending_cats = []
    for cat in trending_data.get("categories", [])[:5]:
        trending_cats.append(cat.get("name", str(cat)))
    
    # Trending NFTs
    trending_nfts = []
    for nft in trending_data.get("nfts", [])[:5]:
        n = nft.get("data") if isinstance(nft, dict) else {}
        trending_nfts.append({
            "name": n.get("name") if isinstance(n, dict) else str(nft),
            "symbol": n.get("symbol") if isinstance(n, dict) else None,
        })
    
    return {
        "trending_coins": trending_coins,
        "trending_categories": trending_cats,
        "trending_nfts": trending_nfts,
        "timestamp": int(time.time()),
    }


def get_global_market():
    """Get global crypto market cap, volume, BTC dominance."""
    data = _fetch("https://api.coingecko.com/api/v3/global")
    gd = data.get("data", {})
    
    return {
        "total_market_cap_usd": gd.get("total_market_cap", {}).get("usd", 0),
        "total_volume_24h_usd": gd.get("total_volume", {}).get("usd", 0),
        "market_cap_change_24h_pct": gd.get("market_cap_change_percentage_24h_usd", 0),
        "active_cryptos": gd.get("active_cryptocurrencies", 0),
        "markets": gd.get("markets", 0),
        "btc_dominance": gd.get("market_cap_percentage", {}).get("btc", 0),
        "eth_dominance": gd.get("market_cap_percentage", {}).get("eth", 0),
        "timestamp": int(time.time()),
    }
