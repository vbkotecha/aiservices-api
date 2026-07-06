# AgentServices

> 37-endpoint crypto, market intelligence, and AI inference API for AI agents — with x402 micropayments on Base

[![Version](https://img.shields.io/badge/version-5.0.0-brightgreen)](https://github.com/vbkotecha/aiservices-api)
[![Network](https://img.shields.io/badge/network-Base%20Mainnet-blue)](https://base.org)
[![Payment](https://img.shields.io/badge/payment-x402%20%2F%20USDC-purple)](https://x402.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange)](https://modelcontextprotocol.io)
[![Status](https://img.shields.io/badge/status-live-success)](https://api.aiservices.to/health)

**Live at:** [api.aiservices.to](https://api.aiservices.to) | **MCP Server:** `https://api.aiservices.to/mcp` (SSE) | **Discovery:** `/.well-known/x402`

## What is this?

AgentServices is the monetized API layer for AI agents. No API keys, no subscriptions — agents pay per-request with USDC on Base using the [x402 payment protocol](https://x402.org).

**37 endpoints** across crypto data, market intelligence, DeFi analytics, AI inference, and dispute resolution. 12 are free. 25 are paid via x402 (from $0.01 to $0.05 per call).

## Endpoints

### Free (no payment required)
| Endpoint | Description |
|----------|-------------|
| `GET /v1/prices?symbols=BTC,ETH` | Current crypto prices (CoinGecko) |
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
| `GET /health` | API health check |

### Paid — Data APIs (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /v1/indicators/BTC` | $0.02 | Technical indicators (RSI, MACD, Bollinger Bands, ATR, Support/Resistance) |
| `GET /v1/yields` | $0.02 | Top DeFi yield pools by TVL |
| `GET /v1/metadata?url=` | $0.01 | URL metadata extraction and unfurling |
| `GET /v1/search?q=` | $0.01 | Web search for crypto/market information |
| `GET /v1/onchain/:address` | $0.02 | On-chain analytics for any address |
| `GET /v1/onchain/:address/tokens` | $0.03 | Token holdings for any address |

### Paid — Synthesis APIs (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /v1/token-risk/:symbol` | $0.03 | Risk assessment for any token (rug pull, liquidity, contract audit) |
| `GET /v1/crypto-signals` | $0.04 | Aggregated buy/sell signals across multiple indicators |
| `GET /v1/yield-comparison` | $0.03 | Compare yields across protocols with risk-adjusted returns |
| `GET /v1/hn-sentiment` | $0.02 | Hacker News sentiment analysis for tech topics |
| `GET /v1/npm-stats/:package` | $0.02 | NPM package download stats and trends |
| `GET /v1/github-trending` | $0.02 | Trending GitHub repos by language/topic |
| `GET /v1/marketing-intel` | $0.05 | Marketing intelligence: competitors, content gaps, ad copy |

### Paid — AI Inference (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `POST /v1/inference` | $0.03 | LLM inference (gpt-5.4/5.4-mini/5.5) — chat completions |
| `POST /v1/complete` | $0.03 | Text completion (CodexSale proxy) |

### Paid — Dispute Resolution (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `POST /v1/disputes` | $0.05 | AI-powered dispute resolution (7 policy templates) |

---

## Use Cases — What Agents Can Build

### Portfolio Monitor
```bash
# Get current prices (FREE)
curl https://api.aiservices.to/v1/prices?symbols=BTC,ETH,SOL

# Get technical signals for entry/exit ($0.04)
curl https://api.aiservices.to/v1/crypto-signals

# Check token risk before buying ($0.03)
curl https://api.aiservices.to/v1/token-risk/PEPE
```

### DeFi Yield Optimizer
```bash
# Get all yield pools ranked by TVL ($0.02)
curl https://api.aiservices.to/v1/yields

# Compare yields with risk-adjusted returns ($0.03)
curl https://api.aiservices.to/v1/yield-comparison

# Check on-chain position for any wallet ($0.02)
curl https://api.aiservices.to/v1/onchain/0x9863aB6242663FCc84c33632741711dB78f8Fd15
```

### Market Intelligence Agent
```bash
# Get market sentiment (FREE)
curl https://api.aiservices.to/v1/fear-greed

# Search for latest news on any topic ($0.01)
curl "https://api.aiservices.to/v1/search?q=base+chain+ecosystem"

# Get trending tokens (FREE)
curl https://api.aiservices.to/v1/trending

# Get marketing intelligence report ($0.05)
curl "https://api.aiservices.to/v1/marketing-intel?competitor=blockrun&topic=x402"
```

### Technical Analysis Bot
```bash
# Full technical indicator suite ($0.02)
curl https://api.aiservices.to/v1/indicators/BTC
# Returns: RSI, MACD, Bollinger Bands, ATR, Support/Resistance levels

# AI-generated market predictions (FREE)
curl https://api.aiservices.to/v1/predictions

# Combine with on-chain analytics ($0.03)
curl https://api.aiservices.to/v1/onchain/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045/tokens
```

### Developer Research Agent
```bash
# GitHub trending repos ($0.02)
curl "https://api.aiservices.to/v1/github-trending?language=python&since=weekly"

# NPM package stats ($0.02)
curl https://api.aiservices.to/v1/npm-stats/react

# Hacker News sentiment ($0.02)
curl "https://api.aiservices.to/v1/hn-sentiment?q=AI+agents"
```

### AI Chat / Inference
```bash
# Chat completions via x402 ($0.03)
curl -X POST https://api.aiservices.to/v1/inference \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.4-mini","messages":[{"role":"user","content":"Explain x402 in 3 sentences"}]}'
```

---

## Quick Start

### Using curl
```bash
# Free — no payment needed
curl https://api.aiservices.to/v1/prices?symbols=BTC,ETH

# Paid — returns HTTP 402 with payment instructions in the header
curl -i https://api.aiservices.to/v1/indicators/BTC
# Response includes x402 payment envelope: network, amount, payTo address
# Agent pays via x402 client, retries with X-Payment header, gets data
```

### Using as MCP Server (Claude Desktop, Cursor, etc.)
```json
{
  "mcpServers": {
    "agentservices": {
      "url": "https://api.aiservices.to/mcp",
      "transport": "sse"
    }
  }
}
```

13+ MCP tools available: `crypto_prices`, `trending_tokens`, `global_market`, `gas_prices`, `market_predictions`, `crypto_news`, `social_trending`, `technical_indicators`, `defi_yields`, `search_web`, `token_risk`, `crypto_signals`, `onchain_analytics`

### Using with Python
```python
import httpx

# Free endpoints
resp = httpx.get("https://api.aiservices.to/v1/prices?symbols=BTC,ETH")
prices = resp.json()

# Paid endpoints — use x402 client to handle payment
from x402.client import x402Client
client = x402Client()
result = client.get("https://api.aiservices.to/v1/indicators/BTC")
# Client handles 402 → pays USDC → retries with payment proof → returns data
```

### Using with JavaScript/TypeScript
```typescript
// Free endpoints
const prices = await fetch("https://api.aiservices.to/v1/prices?symbols=BTC,ETH").then(r => r.json());

// Paid endpoints — use @x402/facilitator
import { wrapFetchWithPayment } from "@x402/facilitator";
const paidFetch = wrapFetchWithPayment(fetch);
const indicators = await paidFetch("https://api.aiservices.to/v1/indicators/BTC").then(r => r.json());
```

## Dispute Resolution Engine

AgentServices includes an AI-powered dispute resolution system with 7 policy templates:

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
