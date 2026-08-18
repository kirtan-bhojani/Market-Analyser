import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authedFetch } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const SUBSCRIPTIONS_KEY = ["alert-subscriptions"] as const;

export interface AlertSubscription {
  id: number;
  user_id: string;
  rule_id: number;
  channel: string;
  target: string;
}

export interface CreateAlertSubscriptionInput {
  rule_id: number;
  channel: string;
  target: string;
}

async function fetchSubscriptions(): Promise<AlertSubscription[]> {
  const res = await authedFetch(`${API_BASE}/api/alert-subscriptions`);
  if (!res.ok) throw new Error(`Failed to load alert subscriptions (${res.status})`);
  return res.json();
}

async function postSubscription(
  input: CreateAlertSubscriptionInput,
): Promise<AlertSubscription> {
  const res = await authedFetch(`${API_BASE}/api/alert-subscriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Failed to create alert subscription (${res.status})`);
  return res.json();
}

async function deleteSubscriptionReq(id: number): Promise<void> {
  const res = await authedFetch(`${API_BASE}/api/alert-subscriptions/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete alert subscription (${res.status})`);
}

/**
 * TanStack Query wrapper over the alert-subscriptions CRUD endpoints
 * (T8), mirroring `useScanRules`. All requests ride the authed transport
 * so they're scoped to the signed-in user.
 */
export function useAlertSubscriptions() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: SUBSCRIPTIONS_KEY });

  const subscriptionsQuery = useQuery({
    queryKey: SUBSCRIPTIONS_KEY,
    queryFn: fetchSubscriptions,
  });

  const create = useMutation({ mutationFn: postSubscription, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: deleteSubscriptionReq, onSuccess: invalidate });

  return {
    subscriptions: subscriptionsQuery.data ?? [],
    isLoading: subscriptionsQuery.isLoading,
    isError: subscriptionsQuery.isError,
    create,
    remove,
  };
}
