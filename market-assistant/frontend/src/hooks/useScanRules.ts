import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authedFetch } from "../lib/api";
import type { RuleDefinition, ScanRule } from "../lib/scannerTypes";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const RULES_KEY = ["scanner", "rules"] as const;

async function fetchRules(): Promise<ScanRule[]> {
  const res = await authedFetch(`${API_BASE}/api/scanner/rules`);
  if (!res.ok) throw new Error(`Failed to load rules (${res.status})`);
  return res.json();
}

async function postRule(input: { name: string; definition: RuleDefinition }): Promise<ScanRule> {
  const res = await authedFetch(`${API_BASE}/api/scanner/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: input.name, definition: input.definition, enabled: true }),
  });
  if (!res.ok) throw new Error(`Failed to create rule (${res.status})`);
  return res.json();
}

async function patchRule(input: { id: number; enabled: boolean }): Promise<ScanRule> {
  const res = await authedFetch(`${API_BASE}/api/scanner/rules/${input.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: input.enabled }),
  });
  if (!res.ok) throw new Error(`Failed to update rule (${res.status})`);
  return res.json();
}

async function deleteRuleReq(id: number): Promise<void> {
  const res = await authedFetch(`${API_BASE}/api/scanner/rules/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete rule (${res.status})`);
}

/**
 * TanStack Query wrapper over the scanner rules CRUD endpoints. Returns the
 * rules list plus create/update/delete mutations that invalidate the cache.
 */
export function useScanRules() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: RULES_KEY });

  const rulesQuery = useQuery({ queryKey: RULES_KEY, queryFn: fetchRules });

  const createRule = useMutation({ mutationFn: postRule, onSuccess: invalidate });
  const updateRule = useMutation({ mutationFn: patchRule, onSuccess: invalidate });
  const deleteRule = useMutation({ mutationFn: deleteRuleReq, onSuccess: invalidate });

  return {
    rules: rulesQuery.data ?? [],
    isLoading: rulesQuery.isLoading,
    isError: rulesQuery.isError,
    createRule,
    updateRule,
    deleteRule,
  };
}
