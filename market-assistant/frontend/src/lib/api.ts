import type { CorrelationVM } from "../components/analytics/CorrelationMatrix";
import type { SeasonalityVM } from "../components/analytics/SeasonalityHeatmap";
import type { NewsItemVM } from "../components/news/NewsPanel";
import { getAccessToken } from "./auth";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

interface NewsItemApiShape {
  id: number;
  source: string | null;
  title: string | null;
  url: string | null;
  published_at: string | null;
  sentiment: number | null;
  tickers: string[] | null;
}

/**
 * Bearer-authed transport wrapper around `fetch`. Every backend API call goes
 * through this so the Supabase access token (if any) rides along as
 * `Authorization: Bearer <token>`. Delegates straight to `fetch` when there's
 * no active session — the backend's dev/test stub covers that path.
 */
export async function authedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const token = await getAccessToken();
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return fetch(input, { ...init, headers });
}

/**
 * Appends the Supabase access token to a WebSocket URL as `?token=<jwt>`,
 * matching the backend's WS auth contract. Returns the base URL unchanged
 * when there's no token (caller decides whether to still connect).
 */
export function buildWsUrl(baseUrl: string, token: string | null): string {
  if (!token) return baseUrl;
  const separator = baseUrl.includes("?") ? "&" : "?";
  return `${baseUrl}${separator}token=${encodeURIComponent(token)}`;
}

export interface InstrumentDto {
  id: number;
  symbol: string;
  assetClass: string;
  exchange: string;
  active: boolean;
  delayed: boolean;
  delayMinutes: number;
}

interface InstrumentApiShape {
  id: number;
  symbol: string;
  asset_class: string;
  exchange: string;
  active: boolean;
  delayed: boolean;
  delay_minutes: number;
}

function fromApi(raw: InstrumentApiShape): InstrumentDto {
  return {
    id: raw.id,
    symbol: raw.symbol,
    assetClass: raw.asset_class,
    exchange: raw.exchange,
    active: raw.active,
    delayed: raw.delayed,
    delayMinutes: raw.delay_minutes,
  };
}

export async function getInstruments(assetClass?: string): Promise<InstrumentDto[]> {
  const params = assetClass ? `?asset_class=${encodeURIComponent(assetClass)}` : "";
  const res = await authedFetch(`${API_BASE}/api/instruments${params}`);
  if (!res.ok) throw new Error(`getInstruments failed: ${res.status}`);
  const body: InstrumentApiShape[] = await res.json();
  return body.map(fromApi);
}

export async function createInstrument(payload: {
  symbol: string;
  assetClass: string;
  exchange: string;
}): Promise<InstrumentDto> {
  const res = await authedFetch(`${API_BASE}/api/instruments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbol: payload.symbol,
      asset_class: payload.assetClass,
      exchange: payload.exchange,
    }),
  });
  if (!res.ok) throw new Error(`createInstrument failed: ${res.status}`);
  const body: InstrumentApiShape = await res.json();
  return fromApi(body);
}

export async function updateInstrument(id: number, active: boolean): Promise<InstrumentDto> {
  const res = await authedFetch(`${API_BASE}/api/instruments/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });
  if (!res.ok) throw new Error(`updateInstrument failed: ${res.status}`);
  const body: InstrumentApiShape = await res.json();
  return fromApi(body);
}

export async function seedNifty50(): Promise<InstrumentDto[]> {
  const res = await authedFetch(`${API_BASE}/api/instruments/seed-nifty50`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`seedNifty50 failed: ${res.status}`);
  const body: InstrumentApiShape[] = await res.json();
  return body.map(fromApi);
}

export interface SignalDto {
  id: number;
  instrument_id: number | null;
  strategy: string;
  direction: string;
  ts: string;
  confidence: number | null;
  ref_entry: number | null;
  ref_sl: number | null;
  ref_tp: number | null;
  backtest_ref: string | null;
  meta: Record<string, unknown> | null;
}

export async function getSignals(
  instrumentId: number,
  strategy?: string,
): Promise<SignalDto[]> {
  const params = new URLSearchParams({ instrument_id: String(instrumentId) });
  if (strategy) params.set("strategy", strategy);
  const res = await authedFetch(`${API_BASE}/api/signals?${params.toString()}`);
  if (!res.ok) throw new Error(`getSignals failed: ${res.status}`);
  return res.json();
}

// --- Chat (Phase 10) ---

export interface ChatSessionDto {
  id: string;
  createdAt: string;
}

interface ChatSessionApiShape {
  id: string;
  user_id: string;
  created_at: string;
}

export interface ChatMessageDto {
  role: "user" | "assistant" | "tool";
  content: string;
}

interface ChatMessageApiShape {
  role: "user" | "assistant" | "tool";
  content: string | null;
}

export function chatTurnUrl(sessionId: string): string {
  return `${API_BASE}/api/chat/sessions/${sessionId}/turns`;
}

export async function createSession(): Promise<ChatSessionDto> {
  const res = await authedFetch(`${API_BASE}/api/chat/sessions`, { method: "POST" });
  if (!res.ok) throw new Error(`createSession failed: ${res.status}`);
  const body: ChatSessionApiShape = await res.json();
  return { id: body.id, createdAt: body.created_at };
}

export async function listSessions(): Promise<ChatSessionDto[]> {
  const res = await authedFetch(`${API_BASE}/api/chat/sessions`);
  if (!res.ok) throw new Error(`listSessions failed: ${res.status}`);
  const body: ChatSessionApiShape[] = await res.json();
  return body.map((s) => ({ id: s.id, createdAt: s.created_at }));
}

export async function getSessionMessages(sessionId: string): Promise<ChatMessageDto[]> {
  const res = await authedFetch(`${API_BASE}/api/chat/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error(`getSessionMessages failed: ${res.status}`);
  const body: ChatMessageApiShape[] = await res.json();
  return body
    .filter((m) => m.role !== "tool" && m.content)
    .map((m) => ({ role: m.role, content: m.content ?? "" }));
}

// --- Phase 13: dashboard news + analytics feeds ---

export async function getNews(symbol?: string): Promise<NewsItemVM[]> {
  const qs = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  const res = await authedFetch(`${API_BASE}/api/news${qs}`);
  if (!res.ok) throw new Error(`getNews failed: ${res.status}`);
  const body: NewsItemApiShape[] = await res.json();
  return body.map((n) => ({
    id: n.id,
    source: n.source,
    title: n.title,
    url: n.url,
    published_at: n.published_at,
    sentiment: n.sentiment,
    tickers: n.tickers ?? [],
  }));
}

export async function getCorrelation(
  assetClass: "crypto" | "equity",
  tf = "1h",
  limit = 200,
): Promise<CorrelationVM> {
  const res = await authedFetch(
    `${API_BASE}/api/analytics/correlation?asset_class=${assetClass}&tf=${tf}&limit=${limit}`,
  );
  if (!res.ok) throw new Error(`getCorrelation failed: ${res.status}`);
  return res.json();
}

export async function getSeasonality(
  symbol: string,
  tf: string,
  bucket: "dow" | "month" | "hour",
): Promise<SeasonalityVM> {
  const res = await authedFetch(
    `${API_BASE}/api/analytics/seasonality?symbol=${encodeURIComponent(symbol)}&tf=${tf}&bucket=${bucket}`,
  );
  if (!res.ok) throw new Error(`getSeasonality failed: ${res.status}`);
  return res.json();
}

export interface BacktestDetailVM {
  id: string;
  status: string;
  strategy?: string;
  equity_curve: { ts: string; value: number }[] | null;
}

export async function getBacktest(id: string): Promise<BacktestDetailVM> {
  const res = await authedFetch(`${API_BASE}/backtests/${id}`);
  if (!res.ok) throw new Error(`getBacktest failed: ${res.status}`);
  return res.json();
}
