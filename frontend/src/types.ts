export interface ETFInfo {
  ticker: string;
  name: string;
}

export interface OverlappingHolding {
  name: string;
  cusip: string | null;
  weight_etf1: number;
  weight_etf2: number;
  overlap_contribution: number;
}

export interface OverlapResult {
  etf1_ticker: string;
  etf2_ticker: string;
  etf1_name: string;
  etf2_name: string;
  overlap_percentage: number;
  common_holdings_count: number;
  etf1_total_holdings: number;
  etf2_total_holdings: number;
  top_overlapping: OverlappingHolding[];
}
