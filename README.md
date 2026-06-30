# AIServices API

> Paid data APIs for AI agents — crypto, geo, web metadata via x402 micropayments on Base

[![Tests](https://img.shields.io/badge/tests-58%2F58%20passing-brightgreen)](tests/test_api.py)
[![Network](https://img.shields.io/badge/network-Base%20Mainnet-blue)](https://base.org)
[![Payment](https://img.shields.io/badge/payment-x402%20%2F%20USDC-purple)](https://x402.org)

## What is this?

AIServices provides pay-per-request data APIs for autonomous AI agents. No API keys, no subscriptions — agents pay with USDC on Base mainnet using the [x402 payment protocol](https://x402.org).

**Live at:** [api.aiservices.to](https://api.aiservices.to)

## Endpoints

### Paid (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /v1/indicators/{symbol}` | $0.02 | Technical indicators (RSI, Bollinger Bands, ATR, Support/Resistance) |
| `GET /v1/yields` | $0.02 | Top DeFi yield pools by TVL |
| `GET /v1/metadata?url=` | $0.01 | URL metadata extraction and unfurling |

### Free
| Endpoint | Description |
|----------|-------------|
| `GET /v1/price/{symbol}` | Current crypto price |
| `GET /v1/prices?symbols=` | Batch crypto prices |
| `GET /v1/fear-greed` | Crypto Fear & Greed Index |
| `GET /v1/geo/{ip}` | IP geolocation |

## Quick Start

```bash
# Free endpoint — no payment needed
curl https://api.aiservices.to/v1/price/BTC

# Paid endpoint — returns 402 with payment instructions
curl https://api.aiservices.to/v1/yields
```

The `402 Payment Required` response includes a `payment-required` header (base64-encoded JSON) with payment details. Pay using any x402-compatible client.

## Discovery

- [x402scan](https://x402scan.com) — Listed ✅
- CDP Bazaar — Bazaar extension enabled (auto-indexes after first settlement)
- [x402 manifest](https://api.aiservices.to/.well-known/x402)

## Tech Stack

- **FastAPI** (Python 3.11+)
- **x402 v2** payment middleware
- **CDP Facilitator** for verify/settle
- Deployed on **Railway**
- USDC on **Base Mainnet**

## Testing

```bash
python3 tests/test_api.py
# 58 tests covering health, discovery, x402 manifest, paid endpoints, free endpoints, error handling
```

## License

MIT
