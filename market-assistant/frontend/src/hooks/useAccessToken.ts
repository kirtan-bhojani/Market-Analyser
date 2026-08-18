import { useEffect, useState } from "react";

import { getAccessToken } from "../lib/auth";
import { useAuthStore } from "../stores/authStore";

/**
 * Live Supabase access token for WS hooks: re-fetches whenever the auth
 * store's session changes (sign in/out, token refresh) so a socket url can
 * be rebuilt with `buildWsUrl`. `null` while unauthenticated or not yet
 * resolved — callers should hold off connecting in that case.
 */
export function useAccessToken(): string | null {
  const session = useAuthStore((s) => s.session);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAccessToken().then((t) => {
      if (!cancelled) setToken(t);
    });
    return () => {
      cancelled = true;
    };
  }, [session]);

  return token;
}
