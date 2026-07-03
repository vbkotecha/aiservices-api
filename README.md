# AIServices

> 16-endpoint crypto and market intelligence API for AI agents — with x402 micropayments on Base

[![Version](https://img.shields.io/badge/version-3.0.0-brightgreen)](https://github.com/vbkotecha/aiservices-api)
[![Network](https://img.shields.io/badge/network-Base%20Mainnet-blue)](https://base.org)
[![Payment](https://img.shields.io/badge/payment-x402%20%2F%20USDC-purple)](https://x402.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange)](https://modelcontextprotocol.io)

**Live at:** [api.aiservices.to](https://api.aiservices.to) | **MCP Server:** `https://api.aiservices.to/mcp` (SSE)

## What is this?

AIServices is the monetized API layer for AI agents. No API keys, no subscriptions — agents pay per-request with USDC on Base using the [x402 payment protocol](https://x402.org).

**16 endpoints** across crypto data, market intelligence, DeFi, and dispute resolution. 11 are free. 4 are paid via x402. One is AI-powered dispute resolution.

## Endpoints

### Free (no payment required)
| Endpoint | Description |
|----------|-------------|
| `GET /v1/prices?symbols=BTC,ETH` | Current crypto prices |
| `GET /v1/trending` | Trending tokens by market activity |
| `GET /v1/global` | Global market cap, volume, BTC dominance |
| `GET /v1/fear-greed` | Crypto Fear & Greed sentiment index |
| `GET /v1/gas` | Current gas prices on Base/Ethereum |
| `GET /v1/predictions` | AI-generated market predictions |
| `GET /v1/news` | Latest crypto news headlines |
| `GET /v1/social/trending` | Trending social sentiment topics |
| `GET /v1/geo?ip=1.2.3.4` | IP geolocation lookup |
| `GET /v1/swap/quote?from=&to=&amount=` | DEX swap quote (0x integration) |
| `GET /v1/policies` | List dispute resolution policy templates |

### Paid (x402 USDC micropayments)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /v1/indicators?symbol=BTC` | $0.02 | Technical indicators (RSI, MACD, Bollinger Bands, ATR, Support/Resistance) |
| `GET /v1/yields` | $0.02 | Top DeFi yield pools by TVL |
| `GET /v1/metadata?url=` | $0.01 | URL metadata extraction and unfurling |
| `GET /v1/search?q=` | $0.01 | Web search for crypto/market information |
| `POST /v1/disputes` | $0.05 | AI-powered dispute resolution (7 policy templates) |

## Quick Start

### Using curl
```bash
# Free — no payment needed
curl https://api.aiservices.to/v1/prices?symbols=BTC,ETH

# Paid — returns 402 with payment instructions
curl https://api.aiservices.to/v1/indicators?symbol=BTC
```

### Using as MCP Server (Claude Desktop, Cursor, etc.)
```json
{
  "mcpServers": {
    "aiservices": {
      "url": "https://api.aiservices.to/mcp",
      "transport": "sse"
    }
  }
}
```

8 MCP tools: `crypto_prices`, `trending_tokens`, `global_market`, `gas_prices`, `market_predictions`, `crypto_news`, `social_trending`, `technical_indicators`, `defi_yields`, `search_web`

### Using with Python
```python
import httpx

# Free endpoints
resp = httpx.get("https://api.aiservices.to/v1/prices?symbols=BTC,ETH")
prices = resp.json()

# Paid endpoints — use x402 client to handle payment
from x402 import X402Client
client = X402Client()
result = client.get("https://api.aiservices.to/v1/indicators?symbol=BTC")
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

## Discovery & Listings

- [x402 Discovery](https://api.aiservices.to/.well-known/x402) — Live
- [MCP Registry](https://registry.modelcontextprotocol.io) — Listed as `to.aiservices/aiservices`
- [CDP Bazaar](https://bazaar.coinbase.com) — Extension enabled
- [awesome-x402](https://github.com/xpaysh/awesome-x402) — PR submitted

## Tech Stack

- **FastAPI** (Python 3.11+)
- **x402 v2** payment middleware (Coinbase CDP facilitator)
- **USDC** on **Base Mainnet** (EIP-3009 gasless transfers)
- Deployed on Railway with custom domain + TLS

## License

MIT — Build on it, fork it, integrate it.

## Links

- **API:** [api.aiservices.to](https://api.aiservices.to)
- **MCP:** [api.aiservices.to/mcp](https://api.aiservices.to/mcp)
- **Discovery:** [api.aiservices.to/.well-known/x402](https://api.aiservices.to/.well-known/x402)
- **GitHub:** [github.com/vbkotecha/aiservices-api](https://github.com/vbkotecha/aiservices-api)
- **x402 Protocol:** [x402.org](https://x402.org)
- **Base:** [base.org](https://base.org)
