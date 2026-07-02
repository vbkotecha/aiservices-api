/**
 * AIServices Client SDK — TypeScript definitions
 */

export interface PriceResponse {
  symbol: string;
  price: number;
  currency: string;
  timestamp: string;
  [key: string]: any;
}

export interface BatchPriceResponse {
  [symbol: string]: PriceResponse;
}

export interface FearGreedResponse {
  value: number;
  classification: string;
  timestamp: string;
  [key: string]: any;
}

export interface GeoResponse {
  ip: string;
  country: string;
  countryCode: string;
  region: string;
  city: string;
  lat: number;
  lon: number;
  [key: string]: any;
}

export interface IndicatorsResponse {
  symbol: string;
  rsi: number;
  bollinger_bands: { upper: number; middle: number; lower: number };
  atr: number;
  support: number;
  resistance: number;
  [key: string]: any;
}

export interface YieldPool {
  protocol: string;
  pool: string;
  apy: number;
  tvl_usd: number;
  chain: string;
}

export interface YieldsResponse {
  pools: YieldPool[];
}

export interface MetadataResponse {
  title: string;
  description: string;
  image: string;
  url: string;
  [key: string]: any;
}

export interface PolicyInfo {
  name: string;
  version: string;
  description: string;
  rules_count: number;
}

export interface DisputeRequest {
  policy: string;
  claimant: string;
  respondent: string;
  claim?: string;
  desiredRemedy?: string;
  evidence?: Array<Record<string, any>>;
}

export interface DisputeRuling {
  ruling: string;
  reasoning: string;
  remedy: string;
  confidence: "high" | "medium" | "low";
  status: "ruled" | "needs_more_info";
  facts_established: Array<{ fact: string; value: string }>;
  facts_disputed: Array<{ fact: string; value: string }>;
  facts_unknown: Array<{ fact: string; reason: string }>;
  matched_rule_id: string;
  policy_name: string;
  policy_version: string;
  case_id: string;
  ruled_at: string;
  engine_version: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  x402_enabled: boolean;
  services: string[];
}

export interface ClientOptions {
  baseUrl?: string;
  walletAddress?: string;
  privateKey?: string;
  fetch?: typeof fetch;
}

export declare class AIServicesClient {
  constructor(options?: ClientOptions);
  
  // Free endpoints
  getPrice(symbol: string): Promise<PriceResponse>;
  getPrices(symbols?: string[]): Promise<BatchPriceResponse>;
  getFearGreed(): Promise<FearGreedResponse>;
  getGeo(ip: string): Promise<GeoResponse>;
  listPolicies(): Promise<PolicyInfo[]>;
  
  // Paid endpoints (x402/USDC)
  getIndicators(symbol: string): Promise<IndicatorsResponse>;
  getYields(opts?: { limit?: number; chain?: string }): Promise<YieldsResponse>;
  getMetadata(url: string): Promise<MetadataResponse>;
  fileDispute(dispute: DisputeRequest): Promise<DisputeRuling>;
  
  // Health
  health(): Promise<HealthResponse>;
}

export default AIServicesClient;
