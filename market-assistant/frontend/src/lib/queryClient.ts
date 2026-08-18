import { QueryClient } from "@tanstack/react-query";

// retry:false — fail fast to a deterministic error state instead of silently
// retrying a down backend 3× (which also left panels stuck in a loading state
// for seconds). Live data has its own WS reconnect; REST refetches on mount.
export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});
