import { useEffect, useMemo, useRef, useState } from "react";

import { buildWsUrl } from "../lib/api";
import type { ScanHit } from "../lib/scannerTypes";
import { parseScanHitFrame } from "../lib/wsFrames";
import { useAccessToken } from "./useAccessToken";
import { useWebSocket } from "./useWebSocket";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
const MAX_HITS = 50;
// Bound the dedup memory: over a long-lived session the `seen` set would grow
// without limit. Keep well above MAX_HITS so recent replays still dedup.
const SEEN_CAP = 500;

/**
 * Subscribes to the live scanner-hits WebSocket and returns the most recent
 * hits (newest first, bounded to `MAX_HITS`, deduped by rule/instrument/ts).
 * Carries the real Supabase access token as `?token=`; stays disconnected
 * until a token is available (i.e. the user is signed in).
 */
export function useScanHits(): ScanHit[] {
  const [hits, setHits] = useState<ScanHit[]>([]);
  const seen = useRef(new Set<string>());

  const onMessage = useMemo(
    () => (data: string) => {
      const hit = parseScanHitFrame(data);
      if (hit === null) return;
      const key = `${hit.rule_id}-${hit.instrument_id}-${hit.ts}`;
      if (seen.current.has(key)) return;
      seen.current.add(key);
      // Evict the oldest key (Set preserves insertion order) to cap memory.
      if (seen.current.size > SEEN_CAP) {
        const oldest = seen.current.values().next().value;
        if (oldest !== undefined) seen.current.delete(oldest);
      }
      setHits((prev) => [hit, ...prev].slice(0, MAX_HITS));
    },
    [],
  );

  const token = useAccessToken();
  // A token change means a different user (or a fresh sign-in) — drop the
  // previous user's buffered hits and dedup memory so nothing bleeds across.
  useEffect(() => {
    setHits([]);
    seen.current.clear();
  }, [token]);

  const wsUrl = token ? buildWsUrl(`${WS_BASE}/ws/scanner/hits`, token) : "";
  useWebSocket(wsUrl, { onMessage });

  return hits;
}
