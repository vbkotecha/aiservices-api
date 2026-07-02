"""
LangChain Tool Wrappers for AIServices
======================================
Drop-in tools for LangChain agents.

Usage:
    from aiservices import create_aiservices_tools
    tools = create_aiservices_tools()
    agent = create_react_agent(llm, tools)
"""
from typing import Optional
from langchain.tools import Tool
from .client import AIServicesClient

_client = AIServicesClient()

def _get_prices(symbols: str = "") -> str:
    import json
    return json.dumps(_client.get_prices(symbols or None))

def _get_indicators(symbol: str) -> str:
    import json
    return json.dumps(_client.get_indicators(symbol))

def _get_defi_yields(chain: str = "") -> str:
    import json
    return json.dumps(_client.get_defi_yields(chain or None))

def _get_fear_greed() -> str:
    import json
    return json.dumps(_client.get_fear_greed())

def _get_geo(ip: str = "") -> str:
    import json
    return json.dumps(_client.get_geo(ip or None))

def _get_url_metadata(url: str) -> str:
    import json
    return json.dumps(_client.get_url_metadata(url))

def _resolve_dispute(policy_and_dispute: str) -> str:
    import json
    parts = policy_and_dispute.split("|", 1)
    policy = parts[0].strip()
    dispute = json.loads(parts[1]) if len(parts) > 1 else {}
    return json.dumps(_client.resolve_dispute(policy, dispute))

def _list_policies() -> str:
    import json
    return json.dumps(_client.list_policies())

def create_aiservices_tools() -> list:
    """Create LangChain Tool objects for all AIServices endpoints."""
    return [
        Tool(name="crypto_prices", func=_get_prices,
             description="Get current crypto prices. Input: comma-separated symbols like 'BTC,ETH'. FREE."),
        Tool(name="technical_indicators", func=_get_indicators,
             description="Get technical indicators (RSI, MACD) for a crypto symbol. Input: 'BTC'. $0.02."),
        Tool(name="defi_yields", func=_get_defi_yields,
             description="Get DeFi yield rates. Input: chain name or empty for all. $0.02."),
        Tool(name="fear_greed", func=_get_fear_greed,
             description="Get crypto Fear & Greed sentiment index. No input needed. FREE."),
        Tool(name="ip_geolocation", func=_get_geo,
             description="Get geolocation for an IP address. Input: IP or empty. FREE."),
        Tool(name="url_metadata", func=_get_url_metadata,
             description="Extract metadata from a URL. Input: full URL. $0.01."),
        Tool(name="resolve_dispute", func=_resolve_dispute,
             description="Resolve a dispute using AI. Input: 'policy_id|{\"key\":\"value\"}'. $0.05."),
        Tool(name="list_policies", func=_list_policies,
             description="List available dispute resolution policies. No input. FREE."),
    ]
