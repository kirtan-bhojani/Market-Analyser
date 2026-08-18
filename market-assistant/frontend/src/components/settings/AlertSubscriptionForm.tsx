import { useState } from "react";
import type { FormEvent } from "react";

import { useAlertSubscriptions } from "../../hooks/useAlertSubscriptions";
import { useScanRules } from "../../hooks/useScanRules";

/**
 * Creates a telegram alert subscription: pick one of the user's scan rules
 * and enter the telegram chat id to notify. Channel is fixed to "telegram" —
 * the worker only delivers that channel today.
 */
export function AlertSubscriptionForm() {
  const { rules } = useScanRules();
  const { create } = useAlertSubscriptions();

  const [ruleId, setRuleId] = useState<string>("");
  const [target, setTarget] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const selectedRuleId = ruleId || (rules.length > 0 ? String(rules[0].id) : "");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmedTarget = target.trim();

    if (!selectedRuleId || !trimmedTarget) {
      setValidationError("Pick a rule and enter a telegram target.");
      return;
    }

    setValidationError(null);
    create.mutate(
      { rule_id: Number(selectedRuleId), channel: "telegram", target: trimmedTarget },
      { onSuccess: () => setTarget("") },
    );
  };

  return (
    <form className="as-form" onSubmit={handleSubmit}>
      <label className="as-field" htmlFor="as-rule">
        <span className="as-label">Scan rule</span>
        <select
          id="as-rule"
          className="as-select"
          value={selectedRuleId}
          onChange={(e) => setRuleId(e.target.value)}
        >
          {rules.length === 0 && <option value="">No rules yet</option>}
          {rules.map((rule) => (
            <option key={rule.id} value={rule.id}>
              {rule.name}
            </option>
          ))}
        </select>
      </label>

      <label className="as-field" htmlFor="as-target">
        <span className="as-label">Telegram chat id</span>
        <input
          id="as-target"
          className="as-input"
          value={target}
          placeholder="e.g. 123456789"
          onChange={(e) => setTarget(e.target.value)}
        />
      </label>

      {validationError !== null && (
        <p className="as-error" role="alert">
          {validationError}
        </p>
      )}
      {create.isError && (
        <p className="as-error" role="alert">
          {create.error instanceof Error ? create.error.message : "Could not create subscription."}
        </p>
      )}

      <button type="submit" className="cta as-submit" disabled={create.isPending}>
        {create.isPending ? "Adding…" : "Add subscription"}
      </button>
    </form>
  );
}
