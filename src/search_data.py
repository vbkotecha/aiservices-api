"""
Web search data module — Exa-style search passthrough
Also supports DuckDuckGo Instant Answers as a free fallback.
"""
import urllib.request
import urllib.parse
import json
import time
from fastapi import HTTPException

# Exa API key (optional — enables premium search)
EXA_API_KEY = None
import os
_env_key = os.environ.get("EXA_API_KEY")
if _env_key:
    EXA_API_KEY = _env_key

def _fetch_json(url, headers=None, timeout=10, data=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "AgentServices/2.0"})
    if data:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise HTTPException(status_code=429, detail="Rate limited by upstream. Retry shortly.")
        raise HTTPException(status_code=502, detail=f"Upstream error: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search error: {str(e)}")


def web_search(query: str, num_results: int = 5):
    """
    Web search using Exa API if key available, otherwise DuckDuckGo Instant Answers.
    Returns structured search results with title, URL, and snippet.
    """
    if EXA_API_KEY:
        # Use Exa for high-quality AI-powered search
        results = _fetch_json(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": EXA_API_KEY,
                "Content-Type": "application/json",
            },
            data={
                "query": query,
                "num_results": min(num_results, 10),
                "type": "auto",
            },
        )
        hits = []
        for r in results.get("results", []):
            hits.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("text", "")[:300] if r.get("text") else "",
                "author": r.get("author"),
                "published_date": r.get("published_date"),
            })
        return {
            "query": query,
            "engine": "exa",
            "results": hits,
            "count": len(hits),
            "timestamp": int(time.time()),
        }
    
    # Fallback: DuckDuckGo Instant Answers API (free, no key)
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    })
    data = _fetch_json(f"https://api.duckduckgo.com/?{params}")
    
    results = []
    # Abstract (main answer)
    if data.get("AbstractText"):
        results.append({
            "title": data.get("Heading", ""),
            "url": data.get("AbstractURL", ""),
            "snippet": data.get("AbstractText", ""),
            "source": data.get("AbstractSource", ""),
        })
    # Related topics
    for topic in data.get("RelatedTopics", [])[:num_results]:
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({
                "title": topic.get("Text", "").split(" - ")[0] if " - " in topic.get("Text", "") else topic.get("Text", "")[:80],
                "url": topic.get("FirstURL", ""),
                "snippet": topic.get("Text", ""),
            })
    
    return {
        "query": query,
        "engine": "duckduckgo",
        "results": results[:num_results],
        "count": len(results[:num_results]),
        "timestamp": int(time.time()),
    }
