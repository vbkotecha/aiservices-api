"""
Synthesis Data — High-value analyzed intelligence endpoints.
Not raw data (commoditized at $0.001). These are SYNTHESIZED signals that
command $0.03-$0.05 per call because they analyze raw data into actionable intelligence.

Categories (from x402 market research July 2026):
- Token risk scoring (synthesis)
- Crypto signal feed (buy/sell signals, not just prices)
- DeFi yield comparison with risk
- GitHub trending repos
- NPM download stats
- Hacker News sentiment
- Deep research (search + extract + synthesize)
"""
import urllib.request
import urllib.parse
import json
import re
import time
from datetime import datetime, timedelta


def _fetch_json(url, timeout=10):
    """Fetch JSON from URL with timeout."""
    req = urllib.request.Request(url, headers={"User-Agent": "AgentServices/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ============================================================
# TOKEN RISK SCORING — Analyzes a token across multiple risk dimensions
# $0.03 per call
# ============================================================
def get_token_risk(token: str):
    """
    Synthesize a risk score for any crypto token.
    Combines volatility, liquidity, holder concentration, and market cap
    into a single 0-100 risk score with category breakdown.

    THIS IS SYNTHESIS, not raw data. Agents pay for the analysis, not the numbers.
    """
    try:
        # Get base price data
        price_data = _fetch_json(f"https://api.coingecko.com/api/v3/simple/price?ids={token}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true", timeout=8)

        if token not in price_data:
            return {"error": f"Token '{token}' not found", "status": "not_found"}

        data = price_data[token]
        price = data.get("usd", 0)
        change_24h = data.get("usd_24h_change", 0)
        volume_24h = data.get("usd_24h_vol", 0)
        market_cap = data.get("usd_market_cap", 0)

        # Calculate risk dimensions
        # 1. Liquidity risk (volume to market cap ratio)
        vol_to_mcap = (volume_24h / market_cap) if market_cap > 0 else 0
        liquidity_score = min(100, max(0, vol_to_mcap * 100))  # Higher ratio = higher liquidity = lower risk

        # 2. Volatility risk (based on 24h change magnitude)
        volatility_score = min(100, abs(change_24h) * 3)  # Scale up for sensitivity

        # 3. Market cap risk (smaller cap = higher risk)
        if market_cap > 10_000_000_000:
            mcap_risk = 10  # Very safe
        elif market_cap > 1_000_000_000:
            mcap_risk = 30
        elif market_cap > 100_000_000:
            mcap_risk = 50
        elif market_cap > 10_000_000:
            mcap_risk = 70
        else:
            mcap_risk = 90  # Very risky

        # 4. Momentum (direction of change)
        momentum = "bullish" if change_24h > 2 else "bearish" if change_24h < -2 else "neutral"

        # Composite risk score (0 = safe, 100 = very risky)
        composite = round(
            (volatility_score * 0.3) +
            (mcap_risk * 0.4) +
            ((100 - liquidity_score) * 0.3)
        )

        risk_label = "Low" if composite < 30 else "Moderate" if composite < 55 else "High" if composite < 75 else "Extreme"

        return {
            "token": token,
            "risk_score": composite,
            "risk_label": risk_label,
            "dimensions": {
                "volatility": round(volatility_score, 1),
                "market_cap_risk": mcap_risk,
                "liquidity_risk": round(100 - liquidity_score, 1),
            },
            "market_data": {
                "price_usd": price,
                "change_24h_pct": round(change_24h, 2),
                "volume_24h_usd": volume_24h,
                "market_cap_usd": market_cap,
            },
            "momentum": momentum,
            "recommendation": "Caution" if composite > 60 else "Monitor" if composite > 40 else "Stable",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# CRYPTO SIGNAL FEED — Buy/sell signals from technical analysis
# $0.04 per call
# ============================================================
def get_crypto_signal(symbol: str):
    """
    Generate a synthesized buy/sell signal from multiple indicators.
    RSI, moving averages, Bollinger Band position, and momentum.

    THIS IS SYNTHESIS. Raw price data is free. The analysis is what agents pay for.
    """
    try:
        # Fetch OHLC data from CoinGecko
        cg_id_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple",
                     "ADA": "cardano", "AVAX": "avalanche-2", "DOT": "polkadot", "LINK": "chainlink",
                     "MATIC": "matic-network", "ATOM": "cosmos", "ARB": "arbitrum", "OP": "optimism"}

        cg_id = cg_id_map.get(symbol.upper(), symbol.lower())

        ohlc = _fetch_json(f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days=7", timeout=8)

        if not ohlc or len(ohlc) < 10:
            return {"error": f"Could not fetch data for {symbol}", "status": "error"}

        closes = [c[4] for c in ohlc]  # Close prices
        current_price = closes[-1]

        # Simple RSI calculation
        gains = []
        losses = []
        for i in range(1, min(len(closes), 15)):
            diff = closes[i] - closes[i-1]
            gains.append(max(0, diff))
            losses.append(max(0, -diff))

        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss > 0 else 100

        # Moving averages
        ma_short = sum(closes[-7:]) / len(closes[-7:]) if len(closes) >= 7 else current_price
        ma_long = sum(closes[-14:]) / len(closes[-14:]) if len(closes) >= 14 else current_price

        # Bollinger Band position (simple)
        sma = sum(closes[-14:]) / 14 if len(closes) >= 14 else current_price
        variance = sum((c - sma) ** 2 for c in closes[-14:]) / 14 if len(closes) >= 14 else 0
        std = variance ** 0.5
        upper = sma + 2 * std
        lower = sma - 2 * std
        bb_position = "upper" if current_price > upper * 0.98 else "lower" if current_price < lower * 1.02 else "middle"

        # Synthesize signal
        signals = []
        score = 0  # -100 (strong sell) to +100 (strong buy)

        # RSI signal
        if rsi < 30:
            signals.append({"indicator": "RSI", "value": round(rsi, 1), "signal": "oversold_buy"})
            score += 30
        elif rsi > 70:
            signals.append({"indicator": "RSI", "value": round(rsi, 1), "signal": "overbought_sell"})
            score -= 30
        else:
            signals.append({"indicator": "RSI", "value": round(rsi, 1), "signal": "neutral"})
            score += (50 - rsi) * 0.2

        # MA crossover signal
        if ma_short > ma_long:
            signals.append({"indicator": "MA_Cross", "short": round(ma_short, 2), "long": round(ma_long, 2), "signal": "golden_cross_bullish"})
            score += 25
        else:
            signals.append({"indicator": "MA_Cross", "short": round(ma_short, 2), "long": round(ma_long, 2), "signal": "death_cross_bearish"})
            score -= 25

        # Bollinger signal
        if bb_position == "lower":
            signals.append({"indicator": "Bollinger", "position": "lower_band", "signal": "bounce_buy"})
            score += 20
        elif bb_position == "upper":
            signals.append({"indicator": "Bollinger", "position": "upper_band", "signal": "resistance_sell"})
            score -= 20

        score = max(-100, min(100, round(score)))

        if score > 40:
            action = "STRONG BUY"
            confidence = "high"
        elif score > 15:
            action = "BUY"
            confidence = "moderate"
        elif score > -15:
            action = "HOLD"
            confidence = "low"
        elif score > -40:
            action = "SELL"
            confidence = "moderate"
        else:
            action = "STRONG SELL"
            confidence = "high"

        return {
            "symbol": symbol.upper(),
            "price_usd": round(current_price, 4),
            "action": action,
            "confidence": confidence,
            "signal_score": score,
            "indicators": signals,
            "rsi": round(rsi, 1),
            "ma_7": round(ma_short, 2),
            "ma_14": round(ma_long, 2),
            "bollinger_position": bb_position,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "disclaimer": "Synthesized from public market data. Not financial advice.",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# HACKER NEWS SENTIMENT — Tech sentiment from HN
# $0.02 per call
# ============================================================
def get_hn_sentiment(query: str = ""):
    """
    Fetch top Hacker News stories and analyze tech sentiment.
    Useful for agents tracking developer sentiment, tech trends, and startup buzz.

    Niche feed — "barely represented" on x402 Bazaar per market research.
    """
    try:
        # Get top stories
        top_ids = _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=8)

        stories = []
        for story_id in top_ids[:20]:
            story = _fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5)
            if story and story.get("title"):
                # Filter by query if provided
                if query and query.lower() not in story.get("title", "").lower():
                    continue
                stories.append({
                    "title": story["title"],
                    "score": story.get("score", 0),
                    "comments": story.get("descendants", 0),
                    "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                    "time": story.get("time", 0),
                })

        # Synthesize sentiment
        total_score = sum(s["score"] for s in stories)
        total_comments = sum(s["comments"] for s in stories)
        avg_score = total_score / len(stories) if stories else 0

        # Simple keyword-based sentiment
        positive_keywords = ["launch", "new", "breakthrough", "success", "funding", "growth", "open source", "free"]
        negative_keywords = ["breach", "hack", "vulnerability", "layoff", "shutdown", "crash", "bug", "deprecated"]

        positive_count = 0
        negative_count = 0
        for s in stories:
            title_lower = s["title"].lower()
            if any(kw in title_lower for kw in positive_keywords):
                positive_count += 1
            if any(kw in title_lower for kw in negative_keywords):
                negative_count += 1

        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "query": query or "top stories",
            "sentiment": sentiment,
            "signal_strength": round(abs(positive_count - negative_count) / max(len(stories), 1), 2),
            "stories_analyzed": len(stories),
            "aggregate_score": total_score,
            "avg_story_score": round(avg_score, 1),
            "total_comments": total_comments,
            "trending_topics": [s["title"][:80] for s in stories[:5]],
            "stories": stories[:10],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# NPM DOWNLOAD STATS — Package popularity trends
# $0.02 per call
# ============================================================
def get_npm_stats(package: str):
    """
    NPM package download statistics and trend analysis.
    Useful for agents tracking developer tool adoption and ecosystem health.

    Niche feed — underserved on x402 Bazaar.
    """
    try:
        # Get last 6 months of downloads
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=180)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        dl_data = _fetch_json(
            f"https://api.npmjs.org/downloads/point/{start_str}:{end_str}/{package}",
            timeout=8
        )

        # Get last week for trend
        week_start = (end_date - timedelta(days=7)).strftime("%Y-%m-%d")
        week_data = _fetch_json(
            f"https://api.npmjs.org/downloads/point/{week_start}:{end_str}/{package}",
            timeout=8
        )

        # Get package metadata
        try:
            pkg_data = _fetch_json(f"https://registry.npmjs.org/{package}/latest", timeout=5)
            description = pkg_data.get("description", "")
            version = pkg_data.get("version", "unknown")
            license = pkg_data.get("license", "unknown")
        except:
            description = ""
            version = "unknown"
            license = "unknown"

        daily_avg_6mo = dl_data.get("downloads", 0) / 180
        daily_avg_week = week_data.get("downloads", 0) / 7

        # Trend: is adoption accelerating or decelerating?
        if daily_avg_6mo > 0:
            trend_ratio = daily_avg_week / daily_avg_6mo
            if trend_ratio > 1.2:
                trend = "accelerating"
            elif trend_ratio > 1.0:
                trend = "growing"
            elif trend_ratio > 0.8:
                trend = "stable"
            else:
                trend = "declining"
        else:
            trend_ratio = 0
            trend = "unknown"

        return {
            "package": package,
            "version": version,
            "description": description,
            "license": license,
            "downloads_6mo": dl_data.get("downloads", 0),
            "downloads_last_week": week_data.get("downloads", 0),
            "daily_average_6mo": round(daily_avg_6mo, 1),
            "daily_average_week": round(daily_avg_week, 1),
            "trend": trend,
            "trend_ratio": round(trend_ratio, 2),
            "adoption_signal": f"{package} is {trend} — {round(daily_avg_week):,}/day this week vs {round(daily_avg_6mo):,}/day avg",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# GITHUB TRENDING — Hot repos in a language/topic
# $0.02 per call
# ============================================================
def get_github_trending(language: str = "", since: str = "daily"):
    """
    GitHub trending repositories — what's hot right now.
    Synthesized ranking from GitHub's trending page.

    Niche feed — underserved on x402 Bazaar per market research.
    """
    try:
        # Use GitHub search API for recent trending repos
        params = {
            "sort": "stars",
            "order": "desc",
            "q": f"created:>{(datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')}"
        }
        if language:
            params["q"] += f" language:{language}"

        query_string = urllib.parse.urlencode(params)
        headers = {"Accept": "application/vnd.github.v3+json"}

        gh_token = ""  # No token = rate limited but works for basic
        if gh_token:
            headers["Authorization"] = f"token {gh_token}"

        url = f"https://api.github.com/search/repositories?{query_string}&per_page=15"
        req = urllib.request.Request(url, headers={**headers, "User-Agent": "AgentServices/1.0"})

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        repos = []
        for repo in data.get("items", [])[:15]:
            repos.append({
                "name": repo["full_name"],
                "description": repo.get("description", ""),
                "stars": repo["stargazers_count"],
                "language": repo.get("language", "Unknown"),
                "forks": repo["forks_count"],
                "url": repo["html_url"],
                "open_issues": repo["open_issues_count"],
                "created_at": repo["created_at"],
                "topics": repo.get("topics", [])[:5],
            })

        # Synthesize trending insights
        top_stars = repos[0]["stars"] if repos else 0
        languages = {}
        for r in repos:
            lang = r["language"]
            languages[lang] = languages.get(lang, 0) + 1

        dominant_language = max(languages, key=languages.get) if languages else "N/A"

        return {
            "language_filter": language or "all",
            "period": f"Last 7 days",
            "total_new_repos_found": data.get("total_count", 0),
            "repos_returned": len(repos),
            "top_repo": repos[0]["name"] if repos else "none",
            "top_repo_stars": top_stars,
            "dominant_language": dominant_language,
            "language_distribution": dict(sorted(languages.items(), key=lambda x: -x[1])[:5]),
            "repositories": repos,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# DEFI YIELD COMPARISON — Analyze yield pools with risk context
# $0.03 per call
# ============================================================
def get_yield_comparison(chain: str = ""):
    """
    Compare DeFi yields across protocols WITH risk context.
    Not just raw APY (commoditized) — this adds risk-adjusted yield analysis.

    SYNTHESIS: Raw yield data is $0.02. Risk-adjusted analysis is $0.03.
    """
    try:
        # Get yield data from DeFi Llama
        url = "https://yields.llama.fi/pools"
        if chain:
            url += f"?chain={chain}"

        data = _fetch_json(url, timeout=12)
        pools = data.get("data", [])

        # Filter and rank pools
        analyzed = []
        for pool in pools[:200]:
            apy = pool.get("apy", 0) or 0
            tvl = pool.get("tvlUsd", 0) or 0
            pool_symbol = pool.get("symbol", "UNKNOWN")
            project = pool.get("project", "unknown")
            pool_chain = pool.get("chain", "unknown")

            # Skip tiny pools
            if tvl < 100_000:
                continue

            # Risk-adjusted scoring
            # Higher TVL = lower risk
            tvl_risk = min(100, max(0, 100 - (tvl / 1_000_000) * 2))

            # APY sanity check: >100% APY = high risk
            apy_risk = min(100, max(0, apy / 2))

            # Risk-adjusted yield = APY minus risk penalty
            risk_penalty = (tvl_risk + apy_risk) / 4
            risk_adjusted_apy = max(0, apy - risk_penalty)

            risk_category = "Low" if (tvl > 500_000_000 and apy < 15) else "Medium" if (tvl > 50_000_000 and apy < 30) else "High"

            analyzed.append({
                "project": project,
                "symbol": pool_symbol,
                "chain": pool_chain,
                "apy": round(apy, 2),
                "tvl_usd": round(tvl),
                "risk_category": risk_category,
                "risk_adjusted_apy": round(risk_adjusted_apy, 2),
                "verdict": "safe_yield" if risk_category == "Low" and apy > 5 else "caution" if risk_category == "High" else "watch",
            })

        # Sort by risk-adjusted APY (best opportunities first)
        analyzed.sort(key=lambda x: x["risk_adjusted_apy"], reverse=True)

        # Synthesize summary
        top_opportunity = analyzed[0] if analyzed else None
        avg_apy = sum(a["apy"] for a in analyzed) / len(analyzed) if analyzed else 0
        safe_pools = [a for a in analyzed if a["risk_category"] == "Low"]
        high_risk_pools = [a for a in analyzed if a["risk_category"] == "High"]

        return {
            "chain_filter": chain or "all chains",
            "pools_analyzed": len(analyzed),
            "avg_apy": round(avg_apy, 2),
            "safe_pools_count": len(safe_pools),
            "high_risk_pools_count": len(high_risk_pools),
            "top_opportunity": top_opportunity,
            "best_safe_yield": safe_pools[0] if safe_pools else None,
            "pools": analyzed[:20],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "methodology": "Risk-adjusted yield = APY minus penalty for low TVL and unsustainably high APY. Low risk requires TVL > $500M and APY < 15%.",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# DEEP RESEARCH — Search + Extract + Synthesize in ONE call
# $0.05 per call — Premium bundled endpoint
# ============================================================

def _fetch_html(url: str, timeout: int = 10) -> str:
    """Fetch raw HTML from a URL."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AgentServices/5.1; +https://agentservices.to)",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    """Extract readable text from HTML (lightweight, no dependencies)."""
    # Remove scripts, styles, and comments
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    # Convert common tags to whitespace
    html = re.sub(r'<(p|div|br|h[1-6]|li|tr|td)[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</(p|div|h[1-6]|li|tr|td)>', '\n', html, flags=re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r'<[^>]+>', '', html)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#39;', "'").replace('&quot;', '"').replace('&#x27;', "'")
    # Clean whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()[:5000]  # Cap at 5K chars per source


def deep_research(query: str, max_sources: int = 3):
    """
    SYNTHESIZED RESEARCH — Search the web, extract content from top results,
    and produce an intelligence brief with key findings.

    This is the flagship bundled endpoint. Raw search is $0.01. This is $0.05
    because it does search + extraction + synthesis in one call. Agents pay for
    the time saved (3 calls → 1 call) and the synthesized analysis.

    Competitive positioning: Superhighway charges $0.005 for search+scrape.
    We charge $0.05 for search+extract+SYNTHESIS (actual intelligence brief).
    """
    from search_data import web_search

    # Step 1: Search the web
    search_result = web_search(query, num_results=max_sources + 2)
    results = search_result.get("results", [])

    if not results:
        return {
            "query": query,
            "status": "no_results",
            "findings": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    # Step 2: Extract content from top sources
    sources = []
    for i, result in enumerate(results[:max_sources]):
        url = result.get("url", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")

        source_data = {
            "title": title,
            "url": url,
            "snippet": snippet,
            "extracted_content": "",
            "extraction_status": "skipped",
        }

        if url and url.startswith("http"):
            try:
                html = _fetch_html(url, timeout=8)
                content = _html_to_text(html)
                source_data["extracted_content"] = content[:3000]  # 3K chars for synthesis
                source_data["extraction_status"] = "extracted"
            except Exception as e:
                source_data["extraction_status"] = f"error: {str(e)[:100]}"

        sources.append(source_data)

    # Step 3: Synthesize findings
    all_snippets = [s.get("snippet", "") + " " + s.get("extracted_content", "")[:1500] for s in sources if s.get("snippet") or s.get("extracted_content")]
    combined_text = " ".join(all_snippets).lower()

    # Keyword-based entity extraction and theme detection
    key_phrases = []
    # Extract dollar amounts, percentages, numbers
    dollar_amounts = re.findall(r'\$[\d,.]+[BbMmKk]?', " ".join(all_snippets))
    if dollar_amounts:
        key_phrases.extend([f"Financial: {d}" for d in list(set(dollar_amounts))[:5]])

    percentages = re.findall(r'\d+\.?\d*%', " ".join(all_snippets))
    if percentages:
        key_phrases.extend([f"Metric: {p}" for p in list(set(percentages))[:5]])

    # Detect themes
    themes = []
    theme_keywords = {
        "funding/investment": ["funding", "raised", "investment", "series", "valuation", "investors"],
        "product launch": ["launch", "released", "announces", "ships", "available"],
        "partnership": ["partnership", "collaboration", "partners with", "joins"],
        "regulation": ["regulation", "sec", "compliance", "law", "bill", "act"],
        "market data": ["market", "revenue", "growth", "users", "adoption"],
        "technology": ["ai", "model", "infrastructure", "protocol", "blockchain", "agent"],
        "competition": ["competes", "rival", "vs", "alternative", "competitor"],
    }

    for theme, keywords in theme_keywords.items():
        count = sum(1 for kw in keywords if kw in combined_text)
        if count >= 2:
            themes.append(f"{theme} ({count} mentions)")

    # Sentiment
    positive_words = ["growth", "surge", "breakthrough", "success", "bullish", "record", "high", "beat", "exceed"]
    negative_words = ["decline", "crash", "bearish", "loss", "fail", "layoff", "shutdown", "breach", "hack"]
    pos_count = sum(1 for w in positive_words if w in combined_text)
    neg_count = sum(1 for w in negative_words if w in combined_text)
    sentiment = "positive" if pos_count > neg_count else "negative" if neg_count > pos_count else "neutral"

    # Build the research brief
    brief_sections = []
    for s in sources:
        snippet_text = (s.get("extracted_content") or s.get("snippet", ""))[:500]
        if snippet_text:
            # Take first 2 sentences
            sentences = re.split(r'(?<=[.!?])\s+', snippet_text)
            brief_sections.append(f"[{s['title']}] {' '.join(sentences[:3])}")

    return {
        "query": query,
        "research_type": "deep_research",
        "sources_analyzed": len(sources),
        "sources_successfully_extracted": sum(1 for s in sources if s["extraction_status"] == "extracted"),
        "synthesis": {
            "brief": "\n\n".join(brief_sections[:3]) if brief_sections else "Limited content available for synthesis.",
            "key_findings": key_phrases[:10] if key_phrases else ["No specific metrics detected"],
            "themes_detected": themes[:5] if themes else ["General topic coverage"],
            "sentiment": sentiment,
            "sentiment_drivers": {
                "positive_signals": pos_count,
                "negative_signals": neg_count,
            },
        },
        "sources": [
            {
                "title": s["title"],
                "url": s["url"],
                "snippet": s.get("snippet", ""),
                "extraction_status": s["extraction_status"],
                "content_preview": s.get("extracted_content", "")[:500] if s.get("extracted_content") else "",
            }
            for s in sources
        ],
        "pricing_advantage": "This call replaced 3+ separate API calls (search + extract + analyze). Cost: $0.05 vs $0.04+ separately.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
