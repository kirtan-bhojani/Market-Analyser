import { useQuery } from "@tanstack/react-query";

import { getNews } from "../lib/api";

/** Recent news + sentiment, optionally filtered by ticker. Refreshes each minute. */
export function useNews(symbol?: string) {
  return useQuery({
    queryKey: ["news", symbol ?? "all"],
    queryFn: () => getNews(symbol),
    refetchInterval: 60_000,
  });
}
