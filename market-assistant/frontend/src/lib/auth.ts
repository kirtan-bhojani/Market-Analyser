import { supabase } from "./supabase";

/**
 * Single source of truth for "what's the current bearer token" — used by the
 * authed fetch/WS transport layer. Returns `null` when there's no active
 * Supabase session (e.g. signed out).
 */
export async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
