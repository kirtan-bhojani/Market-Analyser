/// <reference types="vite/client" />

// Explicit augmentation so `import.meta.env` typechecks regardless of the
// tsconfig `types` allowlist (which otherwise excludes vite/client's globals).
interface ImportMetaEnv {
  readonly VITE_WS_URL?: string;
  readonly VITE_API_URL?: string;
  readonly VITE_SUPABASE_URL?: string;
  readonly VITE_SUPABASE_ANON_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
