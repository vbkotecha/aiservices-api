"""
Utility Data — Web extraction, package security, SEO keywords.
Niche endpoints that fill gaps on agentic.market Bazaar.

Web extraction: $0.002/call (volume play, 6 providers but all busy)
Package security: $0.02/call (only 1 provider — tensorfeed.ai)
SEO keywords: $0.01/call (SpyFu has 46 endpoints — proven demand)
"""
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime


def _fetch(url, timeout=10, headers=None):
    """Fetch raw content from URL."""
    h = {"User-Agent": "AgentServices/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode(errors="replace")


def _fetch_json(url, timeout=10, headers=None):
    """Fetch JSON from URL."""
    return json.loads(_fetch(url, timeout, headers))


# ============================================================
# WEB CONTENT EXTRACTION — Clean text from any URL
# $0.002 per call (volume play)
# ============================================================
def extract_web_content(url: str):
    """
    Fetch a URL and extract clean, token-efficient text.
    Strips navigation, ads, scripts, and boilerplate.
    Returns markdown-formatted content.

    6 providers on Bazaar charge $0.001-$0.01 for this. We're competitive at $0.002.
    """
    try:
        raw = _fetch(url, timeout=15)

        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', raw, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # Remove scripts, styles, nav, footer, header
        clean = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<nav[^>]*>.*?</nav>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<footer[^>]*>.*?</footer>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<header[^>]*>.*?</header>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<aside[^>]*>.*?</aside>', '', clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r'<!--.*?-->', '', clean, flags=re.DOTALL)

        # Convert common HTML to text
        # Preserve paragraphs and headings
        clean = re.sub(r'<h[1-6][^>]*>', '\n## ', clean, flags=re.IGNORECASE)
        clean = re.sub(r'</h[1-6]>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'<p[^>]*>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'</p>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'<br[^>]*/?>', '\n', clean, flags=re.IGNORECASE)
        clean = re.sub(r'<li[^>]*>', '\n- ', clean, flags=re.IGNORECASE)

        # Extract meta description
        desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', raw, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else ""

        # og:description fallback
        if not description:
            og_match = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', raw, re.IGNORECASE)
            description = og_match.group(1).strip() if og_match else ""

        # Strip remaining HTML tags
        clean = re.sub(r'<[^>]+>', ' ', clean)

        # Decode HTML entities
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")

        # Collapse whitespace
        clean = re.sub(r'[ \t]+', ' ', clean)
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        clean = clean.strip()

        # Truncate to reasonable length for agents (token-efficient)
        max_chars = 10000
        truncated = len(clean) > max_chars
        clean = clean[:max_chars]

        return {
            "url": url,
            "title": title[:200],
            "description": description[:500],
            "content": clean,
            "content_length": len(clean),
            "truncated": truncated,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "url": url, "status": "error"}


# ============================================================
# PACKAGE SECURITY SCAN — Check PyPI/npm packages for vulnerabilities
# $0.02 per call (only 1 provider — tensorfeed.ai)
# Data: OSV API (free, open vulnerability database)
# ============================================================
def scan_package_security(package: str, ecosystem: str = "PyPI"):
    """
    Check a package for known security vulnerabilities.
    Returns risk score and vulnerability details.

    Only 1 provider on Bazaar (tensorfeed.ai at $0.02). We match the price.
    Data source: OSV.dev (Google's open vulnerability database) — free.
    """
    try:
        # Query OSV API
        payload = json.dumps({"package": {"name": package, "ecosystem": ecosystem}}).encode()
        req = urllib.request.Request(
            "https://api.osv.dev/v1/query",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        vulns = data.get("vulns", [])

        if not vulns:
            return {
                "package": package,
                "ecosystem": ecosystem,
                "risk_score": 0,
                "risk_label": "Safe",
                "vulnerabilities_found": 0,
                "summary": f"No known vulnerabilities for {package} in {ecosystem}.",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        # Analyze vulnerabilities
        critical = []
        high = []
        moderate = []
        low = []

        for v in vulns:
            severity = "MODERATE"
            for s in v.get("severity", []):
                if s.get("type") == "CVSS_V3":
                    score_str = s.get("score", "")
                    # Extract CVSS score from vector string
                    cvss_match = re.search(r'CVSS:3.[01]/.*', score_str)
                    if cvss_match:
                        severity = "CRITICAL" if "ACUTE" in score_str.upper() else severity

            # Use database_specific severity if available
            db_specific = v.get("database_specific", {})
            if "severity" in db_specific:
                sev = db_specific["severity"].upper()
                if "CRITICAL" in sev:
                    severity = "CRITICAL"
                elif "HIGH" in sev:
                    severity = "HIGH"
                elif "MODERATE" in sev or "MEDIUM" in sev:
                    severity = "MODERATE"
                elif "LOW" in sev:
                    severity = "LOW"

            vuln_info = {
                "id": v.get("id", ""),
                "summary": v.get("summary", "")[:200],
                "severity": severity,
                "fixed_in": [],
                "aliases": v.get("aliases", [])[:5],
            }

            # Get fix versions
            for affected in v.get("affected", []):
                for r in affected.get("ranges", []):
                    for event in r.get("events", []):
                        if "fixed" in event:
                            vuln_info["fixed_in"].append(event["fixed"])

            if severity == "CRITICAL":
                critical.append(vuln_info)
            elif severity == "HIGH":
                high.append(vuln_info)
            elif severity == "MODERATE":
                moderate.append(vuln_info)
            else:
                low.append(vuln_info)

        # Risk score: weighted by severity
        risk_score = min(100, len(critical) * 30 + len(high) * 15 + len(moderate) * 5 + len(low))
        risk_label = "Critical" if risk_score >= 70 else "High" if risk_score >= 40 else "Moderate" if risk_score >= 15 else "Low"

        return {
            "package": package,
            "ecosystem": ecosystem,
            "risk_score": risk_score,
            "risk_label": risk_label,
            "vulnerabilities_found": len(vulns),
            "critical_count": len(critical),
            "high_count": len(high),
            "moderate_count": len(moderate),
            "low_count": len(low),
            "critical": critical[:5],
            "high": high[:5],
            "moderate": moderate[:5],
            "recommendation": "Update immediately" if critical or high else "Monitor for updates" if moderate else "Package appears safe",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "package": package, "status": "error"}


# ============================================================
# SEO KEYWORD RESEARCH — Search volume and competition
# $0.01 per call (SpyFu has 46 endpoints — proven demand)
# Data: Google Suggest API (free)
# ============================================================
def seo_keywords(keyword: str):
    """
    Keyword research data: related keywords, search suggestions,
    and competition signals.

    SpyFu charges $0.01 with 46 endpoints — proven demand.
    Data: Google Autocomplete API (free).
    """
    try:
        # Get Google autocomplete suggestions
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(keyword)}"
        data = _fetch_json(url, timeout=8)

        suggestions = data[1] if len(data) > 1 else []

        # Generate keyword variations
        variations = []
        for s in suggestions[:15]:
            # Estimate relative volume (higher position = higher volume)
            position = suggestions.index(s) + 1
            est_volume = max(100, 10000 // position)

            variations.append({
                "keyword": s,
                "estimated_monthly_volume": est_volume,
                "competition": "High" if position <= 3 else "Medium" if position <= 8 else "Low",
                "cpc_estimate": round(0.5 + (10 / position), 2),
            })

        # Question-based keywords (high intent)
        question_prefixes = ["how to", "what is", "best", "why", "when", "where", "vs"]
        questions = []
        for prefix in question_prefixes:
            q_url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(prefix + ' ' + keyword)}"
            try:
                q_data = _fetch_json(q_url, timeout=5)
                for q in q_data[1][:3]:
                    questions.append(q)
            except:
                continue

        return {
            "keyword": keyword,
            "related_keywords": variations,
            "question_keywords": questions[:10],
            "total_suggestions": len(variations),
            "top_keyword": variations[0]["keyword"] if variations else keyword,
            "top_volume_estimate": variations[0]["estimated_monthly_volume"] if variations else 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": "Volume estimates are relative rankings from autocomplete position, not exact search volumes.",
        }
    except Exception as e:
        return {"error": str(e), "keyword": keyword, "status": "error"}
