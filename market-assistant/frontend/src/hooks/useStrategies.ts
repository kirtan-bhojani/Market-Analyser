import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authedFetch } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** JSON-schema fragment the backend emits for a preset's tunable params. */
export interface ParamSpec {
  type: "integer" | "number";
  minimum?: number;
  maximum?: number;
  default?: number;
}

export interface ParamSchema {
  type: string;
  properties: Record<string, ParamSpec>;
  required: string[];
}

/** Shape of one preset from `GET /api/strategies`. */
export interface StrategyMeta {
  name: string;
  label: string;
  regime_mode: string; // "trend" | "range" | "any"
  param_schema: ParamSchema;
  default_params: Record<string, number>;
}

/** Honest mini-backtest stats — mirrors the backend `BacktestStats` shape.
 * `trade_count` serializes as a float (e.g. 9.0); round it in the UI. */
export interface MiniBacktestStats {
  sharpe: number;
  max_dd: number;
  win_rate: number;
  net_return: number;
  trade_count: number;
}

export interface MiniBacktestResult {
  stats: MiniBacktestStats;
  n_candles: number;
}

export interface StrategyConfigInput {
  strategy: string;
  instrument_id: number;
  tf: string;
  params: Record<string, number>;
  enabled: boolean;
}

/** A saved config from `GET /api/strategy-configs`. */
export interface StrategyConfig extends StrategyConfigInput {
  id: number;
  user_id: string;
}

export interface MiniBacktestInput {
  name: string;
  instrument_id: number;
  tf: string;
  params: Record<string, number>;
  fees_bps?: number;
  slippage_bps?: number;
}

async function fetchStrategies(): Promise<StrategyMeta[]> {
  const res = await authedFetch(`${API_BASE}/api/strategies`);
  if (!res.ok) throw new Error(`Failed to load strategies (${res.status})`);
  return res.json();
}

async function fetchStrategyConfigs(): Promise<StrategyConfig[]> {
  const res = await authedFetch(`${API_BASE}/api/strategy-configs`);
  if (!res.ok) throw new Error(`Failed to load strategy configs (${res.status})`);
  return res.json();
}

/** Upsert a config. The backend keys on (user, strategy, instrument, tf), so a
 * repeat POST (e.g. toggling Off) flips the existing row instead of adding a
 * duplicate that would leave the strategy still enabled for the worker. */
async function postStrategyConfig(input: StrategyConfigInput): Promise<unknown> {
  const res = await authedFetch(`${API_BASE}/api/strategy-configs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Failed to save strategy config (${res.status})`);
  return res.json();
}

/** Honest, synchronous mini-backtest via `POST /api/strategies/{name}/backtest`. */
export async function runMiniBacktest({
  name,
  fees_bps = 10,
  slippage_bps = 5,
  ...rest
}: MiniBacktestInput): Promise<MiniBacktestResult> {
  const res = await authedFetch(`${API_BASE}/api/strategies/${name}/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...rest, fees_bps, slippage_bps }),
  });
  if (!res.ok) throw new Error(`Mini-backtest failed (${res.status})`);
  return res.json();
}

/** TanStack Query wrapper over the strategies API. */
export function useStrategies() {
  const queryClient = useQueryClient();
  const strategiesQuery = useQuery({
    queryKey: ["strategies"],
    queryFn: fetchStrategies,
  });
  const configsQuery = useQuery({
    queryKey: ["strategy-configs"],
    queryFn: fetchStrategyConfigs,
  });

  const upsertStrategyConfig = useMutation({
    mutationFn: postStrategyConfig,
    // Refetch persisted configs so every card reflects the saved truth (an Off
    // toggle actually reads Off) rather than trusting the optimistic flip.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategy-configs"] }),
  });

  return {
    strategies: strategiesQuery.data ?? [],
    // Guard the shape: the page does `configs.filter(...)`, so a non-array
    // payload must degrade to [] rather than throw and blank the whole page.
    configs: Array.isArray(configsQuery.data) ? configsQuery.data : [],
    isLoading: strategiesQuery.isLoading,
    isError: strategiesQuery.isError,
    upsertStrategyConfig,
  };
}
