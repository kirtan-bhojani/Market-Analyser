import { useQuery } from "@tanstack/react-query";

import { getCorrelation } from "../lib/api";

export function useCorrelation(assetClass: "crypto" | "equity", tf = "1h", limit = 200) {
  return useQuery({
    queryKey: ["correlation", assetClass, tf, limit],
    queryFn: () => getCorrelation(assetClass, tf, limit),
  });
}
