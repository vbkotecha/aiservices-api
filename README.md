# AIServices

> Paid APIs for AI agents — crypto data, DeFi yields, dispute resolution with built-in x402 payments on Base

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![Network](https://img.shields.io/badge/network-Base%20Mainnet-blue)](https://base.org)
[![Payment](https://img.shields.io/badge/payment-x402%20%2F%20USDC-purple)](https://x402.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange)](https://modelcontextprotocol.io)

**Live at:** [api.aiservices.to](https://api.aiservices.to) | **MCP Server:** `npx aiservices-mcp`

## What is this?

AIServices is the monetized API layer for AI agents. No API keys, no subscriptions — agents pay per-request with USDC on Base using the [x402 payment protocol](https://x402.org).

**The thesis:** As AI agents become autonomous actors, they need their own financial infrastructure. AIServices provides the data and trust APIs they need, with payments baked into the HTTP layer itself.

## Endpoints

### Free (no payment required)
| Endpoint | Description |
|----------|-------------|
| `GET /v1/prices?symbols=BTC,ETH` | Current crypto prices |
| `GET /v1/fear-greed` | Crypto Fear & Greed sentiment index |
| `GET /v1/geo?ip=1.2.3.4` | IP geolocation lookup |
| `GET /v1/policies` | List dispute resolution policy templates |

### Paid (x402 USDC micropayments)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /v1/indicators?symbol=BTC` | $0.02 | Technical indicators (RSI, MACD, Bollinger Bands) |
| `GET /v1/defi/yields` | $0.02 | Top DeFi yield pools by TVL |
| `GET /v1/metadata?url=` | $0.01 | URL metadata extraction and unfurling |
| `POST /v1/disputes` | $0.05 | AI-powered dispute resolution (7 policy templates) |

## Quick Start

### Using curl
```bash
# Free — no payment needed
curl https://api.aiservices.to/v1/prices?symbols=BTC,ETH

# Paid — returns 402 with payment instructions
curl https://api.aiservices.to/v1/indicators?symbol=BTC
```

### Using the Python SDK
```bash
pip install aiservices
```

```python
from aiservices import AIServicesClient

client = AIServicesClient()

# Free endpoints
prices = client.get_prices("BTC,ETH,XRP")
sentiment = client.get_fear_greed()

# Paid endpoints (x402 payment handled automatically by x402 client)
indicators = client.get_indicators("BTC")
```

### Using with LangChain
```python
from aiservices import create_aiservices_tools
from langchain.agents import create_react_agent

tools = create_aiservices_tools()
# 8 tools: crypto_prices, technical_indicators, defi_yields, fear_greed,
# ip_geolocation, url_metadata, resolve_dispute, list_policies
agent = create_react_agent(llm, tools)
```

### Using as MCP Server (Claude Desktop, Cursor, etc.)
```json
{
  "mcpServers": {
    "aiservices": {
      "command": "npx",
      "args": ["aiservices-mcp"]
    }
  }
}
```

## Dispute Resolution Engine

AIServices includes an AI-powered dispute resolution system with 7 policy templates:

| Policy | Use Case |
|--------|----------|
| `freelance-delivery` | Freelancer vs client delivery disputes |
| `milestone-payment` | Milestone-based project payment disputes |
| `sla-monitoring` | Service level agreement violations |
| `api-quality` | API response quality / uptime disputes |
| `bug-bounty` | Bug bounty validity disputes |
| `scope-dispute` | Project scope creep disputes |
| `physical-commerce` | Physical goods transaction disputes |

```python
# Resolve a dispute
result = client.resolve_dispute(
    policy="milestone-payment",
    dispute={
        "freelancer": "Delivered all 5 milestones on time",
        "client": "Milestone 3 was late and incomplete",
        "evidence": ["git_commits", "slack_logs"]
    }
)
```

## Discovery & Listings

- [x402scan](https://x402scan.com) — Listed
- [CDP Bazaar](https://bazaar.coinbase.com) — Extension enabled
- [agent-tools.cloud](https://agent-tools.cloud) — Listed
- [MCPize](https://mcpize.com) — Config ready
- [Smithery](https://smithery.ai) — Config ready
- [mcp.so](https://mcp.so) — Submitted

## Tech Stack

- **FastAPI** (Python 3.11+)
- **x402 v2** payment middleware (Coinbase CDP)
- **USDC** on **Base Mainnet**
- Deployed on Railway with custom domain + TLS

## Testing

```bash
python3 -m pytest tests/
```

## Architecture

```
Agent → x402-enabled HTTP client → AIServices API
                                      ├── Free endpoints (no payment)
                                      ├── Paid endpoints (402 → pay → 200)
                                      └── Dispute engine (LLM-powered, 7 policies)
```

## License

MIT — Build on it, fork it, integrate it.

## Links

- **API:** [api.aiservices.to](https://api.aiservices.to)
- **GitHub:** [github.com/vbkotecha/aiservices-api](https://github.com/vbkotecha/aiservices-api)
- **x402 Protocol:** [x402.org](https://x402.org)
- **Base:** [base.org](https://base.org)
