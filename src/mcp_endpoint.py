"""
Remote MCP transport endpoint for AIServices.
Allows AI tools (Claude, Cursor, etc.) to connect directly without installing anything.
Uses Streamable HTTP transport per MCP spec.
"""
import json
import asyncio
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse

router = APIRouter()

# MCP tool definitions matching our API endpoints
MCP_TOOLS = [
    {
        "name": "crypto_prices",
        "description": "Get current crypto prices for one or more symbols (FREE)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "string",
                    "description": "Comma-separated crypto symbols (e.g. BTC,ETH,SOL)",
                    "default": "BTC,ETH,SOL,XRP"
                }
            }
        }
    },
    {
        "name": "technical_indicators",
        "description": "Get technical indicators (RSI, MACD, Bollinger Bands) for a crypto symbol ($0.02 x402)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Crypto symbol (e.g. BTC)"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "defi_yields",
        "description": "Get top DeFi yield pools ranked by TVL ($0.02 x402)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results", "default": 20}
            }
        }
    },
    {
        "name": "fear_greed",
        "description": "Get crypto Fear & Greed sentiment index (FREE)",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ip_geolocation",
        "description": "Get geolocation data for an IP address (FREE)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP address (e.g. 1.2.3.4)"}
            },
            "required": ["ip"]
        }
    },
    {
        "name": "url_metadata",
        "description": "Extract metadata from a URL — title, description, images ($0.01 x402)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to extract metadata from"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "resolve_dispute",
        "description": "Submit a dispute for AI-powered policy-driven ruling. 7 policy templates available ($0.05 x402)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy": {
                    "type": "string",
                    "description": "Policy template: freelance-delivery, milestone-payment, sla-monitoring, api-quality, bug-bounty, scope-dispute, physical-commerce",
                    "enum": [
                        "freelance-delivery", "milestone-payment", "sla-monitoring",
                        "api-quality", "bug-bounty", "scope-dispute", "physical-commerce"
                    ]
                },
                "claimant": {"type": "string", "description": "Plaintiff address or agent ID"},
                "respondent": {"type": "string", "description": "Respondent address or agent ID"},
                "claim": {"type": "string", "description": "What happened"},
                "desired_remedy": {"type": "string", "description": "What the claimant wants"},
                "evidence": {"type": "array", "items": {"type": "string"}, "description": "Evidence items"}
            },
            "required": ["policy", "claimant", "respondent"]
        }
    },
    {
        "name": "list_policies",
        "description": "List all available dispute resolution policy templates (FREE)",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

MCP_RESOURCES = [
    {
        "uri": "aiservices://prices",
        "name": "Live Crypto Prices",
        "description": "Current crypto prices (BTC, ETH, SOL, XRP)",
        "mimeType": "application/json"
    },
    {
        "uri": "aiservices://policies",
        "name": "Dispute Policy Templates",
        "description": "Available dispute resolution policies",
        "mimeType": "application/json"
    }
]


@router.post("/mcp")
async def mcp_handler(request: Request):
    """
    MCP Streamable HTTP endpoint.
    Handles initialize, tools/list, tools/call, resources/list.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}},
            status_code=400
        )

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    # --- initialize ---
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "AIServices",
                    "version": "2.0.0",
                }
            }
        }

    # --- tools/list ---
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS}
        }

    # --- resources/list ---
    if method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": MCP_RESOURCES}
        }

    # --- tools/call ---
    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        result = await _execute_tool(tool_name, args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    }
                ]
            }
        }

    # --- notifications/initialized (acknowledge silently) ---
    if method == "notifications/initialized":
        return Response(status_code=204)

    # --- ping ---
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # Unknown method
    return JSONResponse(
        {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}},
        status_code=400
    )


async def _execute_tool(tool_name: str, args: dict):
    """Execute a tool call and return the result."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        if tool_name == "crypto_prices":
            from crypto_data import get_multi_price
            symbols = args.get("symbols", "BTC,ETH,SOL,XRP")
            return get_multi_price(symbols.split(","))

        elif tool_name == "technical_indicators":
            from crypto_data import get_indicators
            symbol = args.get("symbol", "BTC")
            # Note: This is a paid endpoint — MCP caller needs x402 payment
            return get_indicators(symbol)

        elif tool_name == "defi_yields":
            from crypto_data import get_defi_yields
            return get_defi_yields()

        elif tool_name == "fear_greed":
            from crypto_data import get_fear_greed
            return get_fear_greed()

        elif tool_name == "ip_geolocation":
            from geo_data import get_ip_geo
            ip = args.get("ip", "")
            return get_ip_geo(ip)

        elif tool_name == "url_metadata":
            from web_data import get_url_metadata
            url = args.get("url", "")
            return get_url_metadata(url)

        elif tool_name == "resolve_dispute":
            from engine.policy_engine import evaluate_dispute
            ruling = evaluate_dispute(
                dispute={
                    "claimant": args.get("claimant", ""),
                    "respondent": args.get("respondent", ""),
                    "claim": args.get("claim", ""),
                    "desired_remedy": args.get("desired_remedy", ""),
                },
                evidence=args.get("evidence", []),
                policy_name=args.get("policy", "freelance-delivery"),
            )
            return ruling

        elif tool_name == "list_policies":
            from engine.policy_engine import list_policies
            return list_policies()

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}


@router.get("/mcp/tools")
async def mcp_tools_summary():
    """Human-readable summary of MCP tools for discovery."""
    return {
        "server": "AIServices MCP Server",
        "endpoint": "https://api.aiservices.to/mcp",
        "transport": "streamable-http",
        "protocol_version": "2024-11-05",
        "tools": [
            {"name": t["name"], "description": t["description"]}
            for t in MCP_TOOLS
        ],
        "free_tools": ["crypto_prices", "fear_greed", "ip_geolocation", "list_policies"],
        "paid_tools": ["technical_indicators", "defi_yields", "url_metadata", "resolve_dispute"],
        "setup": {
            "claude_desktop": {
                "mcpServers": {
                    "aiservices": {"url": "https://api.aiservices.to/mcp"}
                }
            },
            "cursor": "Add https://api.aiservices.to/mcp as MCP server in Cursor settings",
        }
    }
