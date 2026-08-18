import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createInstrument, getInstruments, seedNifty50, updateInstrument } from "../lib/api";

export function useInstruments(assetClass?: string) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["instruments", assetClass],
    queryFn: () => getInstruments(assetClass),
  });

  const create = useMutation({
    mutationFn: createInstrument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instruments"] }),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateInstrument(id, active),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instruments"] }),
  });

  const seedNifty50Preset = useMutation({
    mutationFn: seedNifty50,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instruments"] }),
  });

  return { ...query, create, toggleActive, seedNifty50: seedNifty50Preset };
}
