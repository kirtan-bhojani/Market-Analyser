export type Operator = "<" | "<=" | ">" | ">=" | "==" | "!=";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "1d";
export type Indicator =
  | "rsi"
  | "ema"
  | "sma"
  | "vwap"
  | "atr"
  | "adx"
  | "rel_volume"
  | "gap_pct";

export interface Condition {
  ind: Indicator;
  tf: Timeframe;
  op: Operator;
  value: number;
  params?: Record<string, number>;
}

export interface RuleDefinition {
  all: Condition[];
}

export interface ScanRule {
  id: number;
  name: string;
  definition: RuleDefinition;
  enabled: boolean;
}

export interface ScanHit {
  rule_id: number;
  rule_name: string;
  instrument_id: number;
  tf: Timeframe;
  ts: string;
  payload: Record<string, number | null>;
}

export const INDICATORS: Indicator[] = [
  "rsi",
  "ema",
  "sma",
  "vwap",
  "atr",
  "adx",
  "rel_volume",
  "gap_pct",
];

export const TIMEFRAMES: Timeframe[] = ["1m", "5m", "15m", "1h", "1d"];

export const OPERATORS: Operator[] = ["<", "<=", ">", ">=", "==", "!="];

/**
 * Dev-only user id used both for rule ownership (backend default) and the
 * scanner-hits WebSocket token, so the feed receives the hits produced by
 * rules created through the REST hook. Replaced by real auth in Phase 11.
 */
export const DEV_USER_ID = "00000000-0000-0000-0000-000000000001";
