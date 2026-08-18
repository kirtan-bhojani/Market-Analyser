import { useQuery } from "@tanstack/react-query";

import { authedFetch } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface BacktestStats {
  sharpe: number;
  max_dd: number;
  win_rate: number;
  net_return: number;
  trade_count: number;
}

export interface EquityPoint {
  ts: string;
  value: number;
}

export interface BacktestResponse {
  id: string;
  status: string;
  stats: BacktestStats | null;
  equity_curve: EquityPoint[] | null;
}

async function fetchBacktest(id: string): Promise<BacktestResponse> {
  const res = await authedFetch(`${API_BASE}/backtests/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch backtest ${id} (${res.status})`);
  }
  return res.json();
}

/** Max consecutive fetch failures before we stop polling a backtest. */
export const MAX_POLL_FAILURES = 3;
const POLL_MS = 2000;

/**
 * Poll cadence given the current query state: stop (`false`) on a terminal
 * status OR after too many consecutive failures; otherwise poll every 2s.
 */
export function backtestRefetchInterval(
  status: string | undefined,
  failureCount: number,
): number | false {
  if (failureCount >= MAX_POLL_FAILURES) return false;
  return status === "done" || status === "failed" ? false : POLL_MS;
}

/**
 * TanStack Query wrapper over `GET /backtests/{id}`. Polls every 2s while the
 * backtest is still running, and stops once it reaches a terminal state
 * (`status === "done"` / `"failed"`) or the endpoint fails repeatedly.
 */
export function useBacktest(id: string) {
  return useQuery({
    queryKey: ["backtest", id],
    queryFn: () => fetchBacktest(id),
    refetchInterval: (query) =>
      backtestRefetchInterval(query.state.data?.status, query.state.fetchFailureCount),
  });
}
