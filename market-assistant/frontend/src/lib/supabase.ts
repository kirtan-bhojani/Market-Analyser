import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing Supabase config: set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY (see .env.example).",
  );
}

/**
 * Shared Supabase client. Tests mock this module (`vi.mock("../../src/lib/supabase")`)
 * so they never depend on real env vars or network access.
 */
export const supabase = createClient(supabaseUrl ?? "", supabaseAnonKey ?? "");
