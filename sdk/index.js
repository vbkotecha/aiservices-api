/**
 * AIServices Client SDK
 * 
 * Paid data APIs for AI agents — crypto market data, DeFi yields, 
 * IP geolocation, URL metadata, and dispute resolution (AgentCourt).
 * 
 * Free endpoints: prices, fear-greed, geo
 * Paid endpoints (x402/USDC): indicators ($0.02), yields ($0.02), metadata ($0.01), disputes ($0.05)
 * 
 * @module aiservices-client
 */

const DEFAULT_BASE_URL = "https://api.aiservices.to";

class AIServicesClient {
  /**
   * Create an AIServices client.
   * @param {Object} options
   * @param {string} [options.baseUrl] - API base URL (default: https://api.aiservices.to)
   * @param {string} [options.walletAddress] - Wallet for x402 payments (required for paid endpoints)
   * @param {string} [options.privateKey] - Private key for signing x402 payments
   */
  constructor(options = {}) {
    this.baseUrl = (options.baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
    this.walletAddress = options.walletAddress || null;
    this.privateKey = options.privateKey || null;
    this._fetch = options.fetch || globalThis.fetch;
  }

  /**
   * Make an HTTP request to the API.
   * @private
   */
  async _request(method, path, body = null) {
    const url = `${this.baseUrl}${path}`;
    const opts = {
      method,
      headers: { "Content-Type": "application/json" },
    };
    if (body) opts.body = JSON.stringify(body);

    const response = await this._fetch(url, opts);
    
    // Handle x402 payment required
    if (response.status === 402) {
      const error = new Error("Payment required. This endpoint requires x402 payment (USDC on Base).");
      error.status = 402;
      error.needsPayment = true;
      
      // If x402 header present, try to extract payment requirements
      const wwwAuth = response.headers.get("www-authenticate") || response.headers.get("WWW-Authenticate");
      if (wwwAuth) {
        try {
          error.paymentRequirements = JSON.parse(wwwAuth.startsWith("x402 ") ? wwwAuth.slice(5) : wwwAuth);
        } catch {
          error.paymentRequirements = wwwAuth;
        }
      }
      throw error;
    }

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`API error ${response.status}: ${text}`);
    }

    return response.json();
  }

  // ─── FREE ENDPOINTS ──────────────────────────────────────────────

  /**
   * Get current crypto price (FREE).
   * @param {string} symbol - Crypto symbol (e.g., "BTC", "ETH")
   * @returns {Promise<Object>} Price data
   */
  async getPrice(symbol) {
    return this._request("GET", `/v1/price/${encodeURIComponent(symbol)}`);
  }

  /**
   * Get batch crypto prices (FREE).
   * @param {string[]} symbols - Array of symbols (e.g., ["BTC", "ETH"])
   * @returns {Promise<Object>} Batch price data
   */
  async getPrices(symbols = ["BTC", "ETH", "SOL", "XRP"]) {
    return this._request("GET", `/v1/prices?symbols=${symbols.join(",")}`);
  }

  /**
   * Get Crypto Fear & Greed Index (FREE).
   * @returns {Promise<Object>} Fear & Greed data
   */
  async getFearGreed() {
    return this._request("GET", `/v1/fear-greed`);
  }

  /**
   * Get IP geolocation (FREE).
   * @param {string} ip - IP address
   * @returns {Promise<Object>} Geolocation data
   */
  async getGeo(ip) {
    return this._request("GET", `/v1/geo/${encodeURIComponent(ip)}`);
  }

  /**
   * List dispute policy templates (FREE).
   * @returns {Promise<Array>} Available policies
   */
  async listPolicies() {
    return this._request("GET", `/v1/policies`);
  }

  // ─── PAID ENDPOINTS (x402 / USDC on Base) ────────────────────────

  /**
   * Get technical indicators: RSI, Bollinger Bands, ATR, Support/Resistance ($0.02).
   * @param {string} symbol - Crypto symbol
   * @returns {Promise<Object>} Technical indicators
   */
  async getIndicators(symbol) {
    return this._request("GET", `/v1/indicators/${encodeURIComponent(symbol)}`);
  }

  /**
   * Get top DeFi yield pools by TVL ($0.02).
   * @param {Object} [opts]
   * @param {number} [opts.limit=20] - Max results
   * @param {string} [opts.chain="all"] - Filter by chain
   * @returns {Promise<Object>} Yield pool data
   */
  async getYields({ limit = 20, chain = "all" } = {}) {
    return this._request("GET", `/v1/yields?limit=${limit}&chain=${encodeURIComponent(chain)}`);
  }

  /**
   * Get URL metadata / unfurling ($0.01).
   * @param {string} url - URL to extract metadata from
   * @returns {Promise<Object>} Metadata (title, description, image, etc.)
   */
  async getMetadata(url) {
    return this._request("GET", `/v1/metadata?url=${encodeURIComponent(url)}`);
  }

  /**
   * Submit a dispute for policy-driven ruling ($0.05).
   * Uses the AgentCourt engine for deterministic, policy-first dispute resolution.
   * 
   * @param {Object} dispute
   * @param {string} dispute.policy - Policy template name (e.g., "freelance-delivery", "bug-bounty")
   * @param {string} dispute.claimant - Plaintiff address or agent ID
   * @param {string} dispute.respondent - Respondent address or agent ID
   * @param {string} [dispute.claim] - What happened
   * @param {string} [dispute.desiredRemedy] - What the claimant wants
   * @param {Array} [dispute.evidence] - Evidence items
   * @returns {Promise<Object>} Ruling with confidence, facts, and remedy
   */
  async fileDispute({ policy, claimant, respondent, claim = "", desiredRemedy = "", evidence = [] }) {
    return this._request("POST", `/v1/disputes`, {
      policy,
      claimant,
      respondent,
      claim,
      desired_remedy: desiredRemedy,
      evidence,
    });
  }

  // ─── HEALTH ──────────────────────────────────────────────────────

  /**
   * Check API health and x402 status.
   * @returns {Promise<Object>} Health status
   */
  async health() {
    return this._request("GET", `/health`);
  }
}

// CommonJS export
module.exports = { AIServicesClient };

// Also export as default for require
module.exports.default = AIServicesClient;

// Named export for the client class
module.exports.AIServicesClient = AIServicesClient;
