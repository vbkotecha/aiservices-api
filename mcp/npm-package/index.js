#!/usr/bin/env node
/**
 * AgentServices MCP Server — Pure JavaScript (zero dependencies)
 * 
 * 50+ paid APIs for AI agents: crypto data, DeFi yields, on-chain analytics,
 * portfolio intelligence, deep research, market intelligence, and more.
 * x402 micropayments via USDC on Base.
 * 
 * Usage in Claude Desktop / Cursor / Windsurf:
 *   npx agentservices-mcp
 * 
 * Or add to MCP config:
 *   {
 *     "mcpServers": {
 *       "agentservices": {
 *         "command": "npx",
 *         "args": ["agentservices-mcp"]
 *       }
 *     }
 *   }
 * 
 * No Python required. No API key required for free endpoints.
 * Paid endpoints return 402 — agents pay via x402 (USDC on Base).
 */

const https = require('https');
const readline = require('readline');

const BASE_URL = 'agentservices.to';
const API_BASE = `https://${BASE_URL}`;

// ============================================================
// ENDPOINT DEFINITIONS — all 50+ services
// ============================================================
const TOOLS = [
  // === FREE ENDPOINTS ===
  {
    name: 'crypto_prices',
    description: 'Get current cryptocurrency prices. FREE. Returns prices for BTC, ETH, SOL, XRP and more.',
    method: 'GET', path: '/v1/crypto/prices',
    params: { symbols: { type: 'string', description: 'Comma-separated crypto symbols (e.g. BTC,ETH,SOL)' } }
  },
  {
    name: 'fear_greed',
    description: 'Get the crypto Fear & Greed Index. FREE. Market sentiment indicator (0=extreme fear, 100=extreme greed).',
    method: 'GET', path: '/v1/fear-greed',
    params: {}
  },
  {
    name: 'ip_geolocation',
    description: 'Get geolocation data for an IP address. FREE.',
    method: 'GET', path: '/v1/geo',
    params: { ip: { type: 'string', description: 'IP address to look up' } }
  },
  {
    name: 'trending_crypto',
    description: 'Get trending cryptocurrencies. FREE.',
    method: 'GET', path: '/v1/trending',
    params: {}
  },
  {
    name: 'global_market',
    description: 'Get global crypto market stats (total market cap, volume, BTC dominance). FREE.',
    method: 'GET', path: '/v1/global',
    params: {}
  },
  {
    name: 'gas_prices',
    description: 'Get current gas prices for major chains (Ethereum, Base, Polygon). FREE.',
    method: 'GET', path: '/v1/gas',
    params: {}
  },
  {
    name: 'swap_quote',
    description: 'Get a DEX swap quote. FREE. Find the best rate for token swaps.',
    method: 'GET', path: '/v1/swap/quote',
    params: {
      chain: { type: 'string', description: 'Blockchain (e.g. ethereum, base)' },
      token_in: { type: 'string', description: 'Input token address' },
      token_out: { type: 'string', description: 'Output token address' },
      amount: { type: 'string', description: 'Amount to swap' }
    }
  },
  {
    name: 'crypto_news',
    description: 'Get latest crypto and blockchain news. FREE.',
    method: 'GET', path: '/v1/news',
    params: { category: { type: 'string', description: 'News category (optional)' } }
  },
  {
    name: 'social_trending',
    description: 'Get trending topics on crypto social media. FREE.',
    method: 'GET', path: '/v1/social/trending',
    params: {}
  },
  {
    name: 'list_policies',
    description: 'List all available dispute resolution policy templates. FREE.',
    method: 'GET', path: '/v1/policies',
    params: {}
  },
  {
    name: 'crypto_predictions',
    description: 'Get crowd-sourced crypto price predictions. FREE.',
    method: 'GET', path: '/v1/predictions',
    params: { symbol: { type: 'string', description: 'Crypto symbol' } }
  },

  // === PAID ENDPOINTS (x402 — USDC on Base) ===
  {
    name: 'technical_indicators',
    description: 'Get technical indicators (RSI, MACD, Bollinger Bands, etc.) for any crypto. $0.02/call via x402.',
    method: 'GET', path: '/v1/indicators',
    params: {
      symbol: { type: 'string', description: 'Crypto symbol (e.g. BTC, ETH)' },
      interval: { type: 'string', description: 'Timeframe: 1h, 4h, 1d' }
    }
  },
  {
    name: 'defi_yields',
    description: 'Get DeFi yield rates across protocols and chains. $0.02/call via x402.',
    method: 'GET', path: '/v1/defi/yields',
    params: {
      chain: { type: 'string', description: 'Blockchain name (optional)' },
      protocol: { type: 'string', description: 'Protocol name (optional)' }
    }
  },
  {
    name: 'url_metadata',
    description: 'Extract rich metadata from any URL (title, description, images, OpenGraph). $0.01/call via x402.',
    method: 'GET', path: '/v1/metadata',
    params: { url: { type: 'string', description: 'URL to extract metadata from' } }
  },
  {
    name: 'search_web',
    description: 'AI-powered web search optimized for agents. Returns clean, relevant results. $0.01/call via x402.',
    method: 'GET', path: '/v1/search',
    params: { q: { type: 'string', description: 'Search query' } }
  },
  {
    name: 'whale_tracker',
    description: 'Track large crypto transactions (whale movements). $0.02/call via x402.',
    method: 'GET', path: '/v1/whales',
    params: {
      symbol: { type: 'string', description: 'Crypto symbol' },
      min_value: { type: 'string', description: 'Minimum USD value (optional)' }
    }
  },
  {
    name: 'exchange_flows',
    description: 'Track exchange inflows/outflows for crypto. $0.02/call via x402.',
    method: 'GET', path: '/v1/exchange-flows',
    params: { symbol: { type: 'string', description: 'Crypto symbol' } }
  },
  {
    name: 'correlation_matrix',
    description: 'Get correlation matrix between major cryptocurrencies. $0.02/call via x402.',
    method: 'GET', path: '/v1/correlation',
    params: { symbols: { type: 'string', description: 'Comma-separated symbols' } }
  },
  {
    name: 'stablecoin_flows',
    description: 'Track stablecoin flows across chains and bridges. $0.02/call via x402.',
    method: 'GET', path: '/v1/stablecoin-flows',
    params: {}
  },
  {
    name: 'defi_tvl',
    description: 'Get Total Value Locked across DeFi protocols. $0.02/call via x402.',
    method: 'GET', path: '/v1/defi/tvl',
    params: { chain: { type: 'string', description: 'Blockchain (optional)' } }
  },
  {
    name: 'github_velocity',
    description: 'Measure GitHub commit velocity for any repo. $0.02/call via x402.',
    method: 'GET', path: '/v1/github/velocity',
    params: { repo: { type: 'string', description: 'GitHub repo (owner/name)' } }
  },
  {
    name: 'macro_indicators',
    description: 'Get macro economic indicators (CPI, GDP, unemployment, etc.). $0.02/call via x402.',
    method: 'GET', path: '/v1/macro',
    params: { indicator: { type: 'string', description: 'Indicator name (optional)' } }
  },
  {
    name: 'token_risk_score',
    description: 'Get a comprehensive risk assessment for any crypto token. $0.03/call via x402.',
    method: 'GET', path: '/v1/token-risk',
    params: { symbol: { type: 'string', description: 'Token symbol or contract address' } }
  },
  {
    name: 'crypto_signals',
    description: 'Get aggregated trading signals (technical + on-chain + sentiment). $0.04/call via x402.',
    method: 'GET', path: '/v1/crypto-signals',
    params: { symbol: { type: 'string', description: 'Crypto symbol' } }
  },
  {
    name: 'yield_comparison',
    description: 'Compare DeFi yields across protocols with risk-adjusted returns. $0.03/call via x402.',
    method: 'GET', path: '/v1/yield-comparison',
    params: { asset: { type: 'string', description: 'Asset to compare yields for' } }
  },
  {
    name: 'hn_sentiment',
    description: 'Get Hacker News sentiment analysis for any topic. $0.02/call via x402.',
    method: 'GET', path: '/v1/hn-sentiment',
    params: { topic: { type: 'string', description: 'Topic to analyze' } }
  },
  {
    name: 'npm_stats',
    description: 'Get npm package download statistics and trends. $0.02/call via x402.',
    method: 'GET', path: '/v1/npm-stats',
    params: { package: { type: 'string', description: 'npm package name' } }
  },
  {
    name: 'github_trending',
    description: 'Get trending GitHub repositories by language/topic. $0.02/call via x402.',
    method: 'GET', path: '/v1/github/trending',
    params: {
      language: { type: 'string', description: 'Programming language (optional)' },
      since: { type: 'string', description: 'Time range: daily, weekly, monthly' }
    }
  },
  {
    name: 'stock_quote',
    description: 'Get real-time stock price quotes. $0.02/call via x402.',
    method: 'GET', path: '/v1/stock/quote',
    params: { symbol: { type: 'string', description: 'Stock ticker symbol' } }
  },
  {
    name: 'stock_history',
    description: 'Get historical stock price data. $0.02/call via x402.',
    method: 'GET', path: '/v1/stock/history',
    params: {
      symbol: { type: 'string', description: 'Stock ticker symbol' },
      period: { type: 'string', description: 'Time period: 1d, 1w, 1m, 3m, 1y' }
    }
  },
  {
    name: 'sec_filings',
    description: 'Search SEC EDGAR filings (10-K, 10-Q, 8-K, etc.). $0.02/call via x402.',
    method: 'GET', path: '/v1/sec/filings',
    params: {
      company: { type: 'string', description: 'Company name or CIK' },
      type: { type: 'string', description: 'Filing type (optional)' }
    }
  },
  {
    name: 'commodities',
    description: 'Get commodity prices (gold, silver, oil, wheat, etc.). $0.02/call via x402.',
    method: 'GET', path: '/v1/commodities',
    params: {}
  },
  {
    name: 'economic_indicators',
    description: 'Get key economic indicators (interest rates, inflation, GDP). $0.02/call via x402.',
    method: 'GET', path: '/v1/economic',
    params: {}
  },
  {
    name: 'fx_rates',
    description: 'Get foreign exchange rates. $0.01/call via x402.',
    method: 'GET', path: '/v1/fx-rates',
    params: { base: { type: 'string', description: 'Base currency (default: USD)' } }
  },
  {
    name: 'web_extract',
    description: 'Extract clean text content from any web page. $0.02/call via x402.',
    method: 'GET', path: '/v1/web/extract',
    params: { url: { type: 'string', description: 'URL to extract content from' } }
  },
  {
    name: 'package_security',
    description: 'Get security audit for npm/pip packages. $0.02/call via x402.',
    method: 'GET', path: '/v1/package-security',
    params: {
      ecosystem: { type: 'string', description: 'npm or pip' },
      package: { type: 'string', description: 'Package name' }
    }
  },
  {
    name: 'seo_keywords',
    description: 'Get SEO keyword suggestions and search volume data. $0.03/call via x402.',
    method: 'GET', path: '/v1/seo/keywords',
    params: { keyword: { type: 'string', description: 'Seed keyword' } }
  },
  {
    name: 'marketing_sentiment',
    description: 'Analyze market sentiment for a brand or product. $0.03/call via x402.',
    method: 'GET', path: '/v1/marketing/sentiment',
    params: { brand: { type: 'string', description: 'Brand or product name' } }
  },
  {
    name: 'marketing_trends',
    description: 'Get marketing trend analysis for an industry. $0.03/call via x402.',
    method: 'GET', path: '/v1/marketing/trends',
    params: { industry: { type: 'string', description: 'Industry name' } }
  },
  {
    name: 'marketing_competitors',
    description: 'Get competitor analysis for a brand. $0.04/call via x402.',
    method: 'GET', path: '/v1/marketing/competitors',
    params: { brand: { type: 'string', description: 'Brand name' } }
  },
  {
    name: 'marketing_content_gaps',
    description: 'Identify content gaps in a niche. $0.03/call via x402.',
    method: 'GET', path: '/v1/marketing/content-gaps',
    params: { niche: { type: 'string', description: 'Niche or topic' } }
  },
  {
    name: 'marketing_ad_copy',
    description: 'Generate AI-powered ad copy variations. $0.04/call via x402.',
    method: 'GET', path: '/v1/marketing/ad-copy',
    params: {
      product: { type: 'string', description: 'Product name' },
      audience: { type: 'string', description: 'Target audience' }
    }
  },

  // === BUNDLED INTELLIGENCE ENDPOINTS ===
  {
    name: 'deep_research',
    description: 'Deep research endpoint: search + extract + synthesize in one call. Returns a comprehensive research report. $0.05/call via x402.',
    method: 'GET', path: '/v1/research',
    params: { q: { type: 'string', description: 'Research query' } }
  },
  {
    name: 'portfolio_intelligence',
    description: 'Portfolio intelligence: price + technical signal + risk score + market sentiment + synthesized verdict. $0.10/call via x402.',
    method: 'GET', path: '/v1/portfolio',
    params: { symbol: { type: 'string', description: 'Crypto symbol (e.g. BTC)' } }
  },
  {
    name: 'defi_strategy',
    description: 'DeFi investment strategy: top yields + protocol TVL + cross-chain comparison + risk assessment. $0.25/call via x402.',
    method: 'GET', path: '/v1/defi-strategy',
    params: {}
  },
  {
    name: 'market_pulse',
    description: 'Market pulse: Fear & Greed + trending + news + social + whales + global market. Synthesized market direction signal. $0.05/call via x402.',
    method: 'GET', path: '/v1/market-pulse',
    params: {}
  },
  {
    name: 'onchain_overview',
    description: 'On-chain overview: whale movements + exchange flows + stablecoin flows + correlation + DeFi TVL. $0.15/call via x402.',
    method: 'GET', path: '/v1/onchain-overview',
    params: {}
  },

  // === AI INFERENCE ===
  {
    name: 'ai_inference',
    description: 'Run AI model inference (GPT-5.4, GPT-5.5). POST with messages. $0.03/call via x402.',
    method: 'POST', path: '/v1/inference',
    params: {
      messages: { type: 'string', description: 'JSON array of message objects' },
      model: { type: 'string', description: 'Model name (gpt-5.4, gpt-5.4-mini, gpt-5.5)' }
    }
  },
  {
    name: 'ai_complete',
    description: 'Quick AI text completion. $0.03/call via x402.',
    method: 'POST', path: '/v1/complete',
    params: {
      prompt: { type: 'string', description: 'Text prompt' },
      model: { type: 'string', description: 'Model name (optional)' }
    }
  },

  // === DISPUTE RESOLUTION ===
  {
    name: 'resolve_dispute',
    description: 'AI-powered dispute resolution using policy templates. $0.05/call via x402. Policies: mileage_payment, physical_commerce, freelance_delivery, bug_bounty, api_quality, sla_monitoring, scope_dispute.',
    method: 'POST', path: '/v1/disputes',
    params: {
      policy: { type: 'string', description: 'Policy ID' },
      dispute: { type: 'string', description: 'Dispute details as JSON' }
    }
  },
];

// ============================================================
// JSON-RPC OVER STDIO — MCP PROTOCOL IMPLEMENTATION
// ============================================================

const rl = readline.createInterface({ input: process.stdin, terminal: false });

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + '\n');
}

function makeToolDefs() {
  return TOOLS.map(t => {
    const properties = {};
    for (const [key, val] of Object.entries(t.params)) {
      properties[key] = val;
    }
    return {
      name: t.name,
      description: t.description,
      inputSchema: {
        type: 'object',
        properties,
        required: Object.keys(t.params).filter(k => !t.params[k].description?.includes('optional'))
      }
    };
  });
}

async function callAPI(tool, args) {
  return new Promise((resolve) => {
    let urlPath = tool.path;
    let body = null;

    if (tool.method === 'GET') {
      const qs = Object.entries(args)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
      if (qs) urlPath += `?${qs}`;
    } else {
      body = JSON.stringify(args);
    }

    const options = {
      hostname: BASE_URL,
      path: urlPath,
      method: tool.method,
      headers: { 'Accept': 'application/json' },
      timeout: 30000,
    };
    if (body) {
      options.headers['Content-Type'] = 'application/json';
      options.headers['Content-Length'] = Buffer.byteLength(body);
    }

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 402) {
          // x402 payment required
          let payInfo = {};
          try { payInfo = JSON.parse(data); } catch {}
          resolve({
            status: 402,
            payment_required: true,
            message: `This endpoint requires x402 payment (${tool.description.match(/\$[\d.]+/)?.[0] || '$0.01-0.25'}). The agent must send USDC on Base network to complete this call.`,
            payment_details: payInfo,
            endpoint: `${API_BASE}${tool.path}`,
          });
        } else {
          let parsed;
          try { parsed = JSON.parse(data); } catch { parsed = data.substring(0, 5000); }
          resolve({ status: res.statusCode, data: parsed });
        }
      });
    });

    req.on('error', (err) => {
      resolve({ status: 0, error: err.message });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({ status: 0, error: 'Request timed out (30s)' });
    });

    if (body) req.write(body);
    req.end();
  });
}

// ============================================================
// REQUEST HANDLERS
// ============================================================

rl.on('line', (line) => {
  let msg;
  try { msg = JSON.parse(line); } catch { return; }

  const { id, method, params } = msg;

  switch (method) {
    case 'initialize':
      send({
        jsonrpc: '2.0', id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: { tools: {} },
          serverInfo: { name: 'agentservices', version: '5.3.0' }
        }
      });
      break;

    case 'notifications/initialized':
      // No response needed for notifications
      break;

    case 'tools/list':
      send({
        jsonrpc: '2.0', id,
        result: { tools: makeToolDefs() }
      });
      break;

    case 'tools/call': {
      const toolName = params?.name;
      const args = params?.arguments || {};
      const tool = TOOLS.find(t => t.name === toolName);

      if (!tool) {
        send({
          jsonrpc: '2.0', id,
          result: {
            content: [{ type: 'text', text: `Unknown tool: ${toolName}. Available: ${TOOLS.map(t => t.name).join(', ')}` }],
            isError: true,
          }
        });
        break;
      }

      callAPI(tool, args).then((result) => {
        let text;
        if (result.payment_required) {
          text = JSON.stringify(result, null, 2);
        } else if (result.status >= 200 && result.status < 300) {
          text = typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2);
        } else {
          text = `HTTP ${result.status}: ${JSON.stringify(result.data || result.error, null, 2)}`;
        }
        send({
          jsonrpc: '2.0', id,
          result: {
            content: [{ type: 'text', text }],
            isError: result.status === 402 || result.status === 0,
          }
        });
      });
      break;
    }

    case 'ping':
      send({ jsonrpc: '2.0', id, result: {} });
      break;

    default:
      if (id) {
        send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } });
      }
  }
});

rl.on('close', () => process.exit(0));

// Log to stderr so it doesn't interfere with stdio protocol
process.stderr.write('AgentServices MCP Server v5.3.0 started. 50 tools available (11 free, 39 paid via x402).\n');
