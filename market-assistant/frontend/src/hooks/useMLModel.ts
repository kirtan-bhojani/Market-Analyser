import { useQuery } from "@tanstack/react-query";

import { authedFetch } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface FoldMetric {
  fold: number;
  n_train: number;
  n_test: number;
  accuracy: number;
}

export interface MLModelResponse {
  id: string;
  instrument_group: string;
  version: string;
  published: boolean;
  fold_metrics: FoldMetric[];
  feature_importances: Record<string, number>;
  model_net_return: number;
  buy_hold_return: number;
  random_return: number;
  threshold: number;
}

async function fetchMLModel(id: string): Promise<MLModelResponse> {
  const res = await authedFetch(`${API_BASE}/ml/models/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch ML model ${id} (${res.status})`);
  }
  return res.json();
}

/** TanStack Query wrapper over `GET /ml/models/{id}`. */
export function useMLModel(id: string) {
  return useQuery({ queryKey: ["ml-model", id], queryFn: () => fetchMLModel(id) });
}
