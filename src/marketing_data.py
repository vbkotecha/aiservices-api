"""
AgentServices — Marketing Intelligence Module
AI-powered marketing tools for media buying teams.
Powered by OpenAI GPT-4o-mini.
"""
import os
import re
import json
import urllib.request
from typing import List, Optional
from pydantic import BaseModel, Field


# --- OpenAI Helper ---

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _ai_analyze(prompt: str, system: str = "You are a marketing intelligence analyst. Return ONLY raw JSON. No markdown, no code blocks, no explanations.") -> str:
    """Call OpenAI for analysis."""
    if not OPENAI_API_KEY:
        return _heuristic_response(prompt, str(e))

    try:
        body = json.dumps({
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1500,
        }).encode()

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            # Strip markdown code blocks
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            return content
    except Exception:
        return _heuristic_response(prompt, str(e))


def _heuristic_response(prompt: str, error: str = "") -> str:
    """Fallback when no OpenAI key or API call fails."""
    return json.dumps({
        "note": f"AI analysis unavailable — {error or 'configure OPENAI_API_KEY'}",
        "prompt_used": prompt[:200],
        "openai_key_present": bool(OPENAI_API_KEY),
        "openai_key_len": len(OPENAI_API_KEY),
    })


def _parse_json_response(text: str):
    """Parse JSON from AI response, handling edge cases."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'[\[\{].*[\]\}]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_analysis": text}


# --- Request Models ---

class SentimentRequest(BaseModel):
    brand: str = Field(description="Brand name to analyze")
    platforms: List[str] = Field(default=["twitter", "reddit", "tiktok"], description="Platforms to check")


class TrendRequest(BaseModel):
    industry: str = Field(description="Industry (e.g. fintech, ecommerce)")
    limit: int = Field(default=5, ge=1, le=20)


class CompetitorRequest(BaseModel):
    competitor_url: str = Field(description="Competitor website")
    your_url: str = Field(description="Your website")


class ContentGapRequest(BaseModel):
    your_domain: str = Field(description="Your domain")
    competitor_domains: List[str] = Field(description="Competitor domains")


class AdCopyRequest(BaseModel):
    product: str = Field(description="Product/service name")
    platform: str = Field(default="google", description="Ad platform: google, meta, tiktok, taboola")
    tone: str = Field(default="professional", description="Tone: professional, casual, urgent, luxury")
    count: int = Field(default=3, ge=1, le=10)


# --- Endpoint Functions ---

def analyze_sentiment(brand: str, platforms: List[str]) -> dict:
    analysis = _ai_analyze(
        f"Analyze brand sentiment for '{brand}' across {', '.join(platforms)}. "
        f"Provide: overall_sentiment_score (0-1), sentiment_breakdown (positive/negative/neutral percentages), "
        f"top_positive_themes (array of 3), top_negative_themes (array of 3), "
        f"trend_direction (rising/stable/declining), key_influencers (array). Return as JSON object."
    )
    data = _parse_json_response(analysis)
    return {"brand": brand, "platforms": platforms, "analysis": data}


def detect_trends(industry: str, limit: int) -> dict:
    analysis = _ai_analyze(
        f"Identify the top {limit} trending topics in {industry} marketing right now. "
        f"For each: topic_name, velocity_score (1-10), estimated_reach, why_its_trending (1 sentence), "
        f"recommended_content_angle. Return as JSON array."
    )
    trends = _parse_json_response(analysis)
    return {"industry": industry, "trends": trends if isinstance(trends, list) else [trends]}


def analyze_competitors(competitor_url: str, your_url: str) -> dict:
    analysis = _ai_analyze(
        f"Analyze the marketing strategy of {competitor_url} compared to {your_url}. "
        f"For each competitor provide: likely_target_keywords (8 keywords), "
        f"primary_marketing_channels (array), content_strategy_summary, "
        f"estimated_ad_budget_tier (low/medium/high), actionable_recommendations for {your_url} (5 items). Return as JSON."
    )
    intel = _parse_json_response(analysis)
    return {"your_url": your_url, "competitor_url": competitor_url, "intelligence": intel}


def find_content_gaps(your_domain: str, competitor_domains: List[str]) -> dict:
    analysis = _ai_analyze(
        f"Compare content coverage between {your_domain} and {', '.join(competitor_domains)}. "
        f"Find content gaps: topics competitors rank for but {your_domain} doesn't. "
        f"For each gap: topic, keyword, estimated_search_volume, difficulty (1-10), "
        f"recommended_format (blog/video/infographic/tool), priority_score (1-10). Return as JSON array."
    )
    gaps = _parse_json_response(analysis)
    return {"your_domain": your_domain, "gaps": gaps if isinstance(gaps, list) else [gaps]}


PLATFORM_SPECS = {
    "google": {"max_headline": 30, "max_description": 90, "format": "text ad"},
    "meta": {"max_headline": 40, "max_description": 125, "format": "feed ad"},
    "tiktok": {"max_headline": 50, "max_description": 100, "format": "video hook + caption"},
    "taboola": {"max_headline": 60, "max_description": 100, "format": "native ad"},
}


def generate_ad_copy(product: str, platform: str, tone: str, count: int) -> dict:
    specs = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["google"])
    analysis = _ai_analyze(
        f"Generate {count} ad copy variations for '{product}' on {platform} with a {tone} tone. "
        f"Constraints: headline max {specs['max_headline']} chars, description max {specs['max_description']} chars. "
        f"Format: {specs['format']}. "
        f"For each variation provide: headline, description, call_to_action, "
        f"target_keyword, and expected_appeal (emotional/rational/urgency/curiosity). "
        f"Return as JSON array.",
        system=f"You are an expert copywriter for {platform} ads. Return ONLY raw JSON array. No markdown, no code blocks, no explanations."
    )
    copies = _parse_json_response(analysis)
    return {
        "product": product,
        "platform": platform,
        "tone": tone,
        "platform_specs": specs,
        "variations": copies if isinstance(copies, list) else [copies],
    }
