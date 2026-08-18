import { useQuery } from "@tanstack/react-query";

import { getSeasonality } from "../lib/api";

export function useSeasonality(symbol: string, tf: string, bucket: "dow" | "month" | "hour") {
  return useQuery({
    queryKey: ["seasonality", symbol, tf, bucket],
    queryFn: () => getSeasonality(symbol, tf, bucket),
  });
}
