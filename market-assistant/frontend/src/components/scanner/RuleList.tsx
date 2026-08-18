import { Badge } from "../common/Badge";
import { EmptyState } from "../common/EmptyState";
import type { Condition, ScanRule } from "../../lib/scannerTypes";

function conditionText(c: Condition): string {
  return `${c.ind}(${c.tf}) ${c.op} ${c.value}`;
}

interface RuleListProps {
  rules: ScanRule[];
  isLoading?: boolean;
  onToggle: (id: number, enabled: boolean) => void;
  onDelete: (id: number) => void;
}

/** Lists saved scan rules with enable/disable toggle and delete controls. */
export function RuleList({ rules, isLoading = false, onToggle, onDelete }: RuleListProps) {
  if (isLoading) {
    return <p className="rl-empty">Loading rules…</p>;
  }

  if (rules.length === 0) {
    return (
      <EmptyState
        glyph="⊞"
        title="No rules yet"
        message="Build a rule above — pick an indicator, timeframe, operator, and value, then combine rows with AND. Saved rules appear here and stream matches into the hits feed."
      />
    );
  }

  return (
    <ul className="rule-list" data-testid="rule-list">
      {rules.map((rule) => (
        <li className="rule-item" key={rule.id} data-testid={`rule-${rule.id}`}>
          <div className="ri-head">
            <span className="ri-name">{rule.name}</span>
            <Badge variant={rule.enabled ? "accent" : "neutral"}>
              {rule.enabled ? "Enabled" : "Disabled"}
            </Badge>
          </div>
          <div className="ri-conds">
            {(rule.definition.all ?? []).length > 0 ? (
              (rule.definition.all ?? []).map((c, i) => (
                <span className="ri-cond num" key={i}>
                  {i > 0 && <span className="ri-and">AND</span>}
                  {conditionText(c)}
                </span>
              ))
            ) : (
              <span className="ri-cond">Custom rule</span>
            )}
          </div>
          <div className="ri-actions">
            <button
              type="button"
              className="ri-btn"
              data-testid={`toggle-${rule.id}`}
              onClick={() => onToggle(rule.id, !rule.enabled)}
            >
              {rule.enabled ? "Disable" : "Enable"}
            </button>
            <button
              type="button"
              className="ri-btn ri-del"
              data-testid={`delete-${rule.id}`}
              onClick={() => onDelete(rule.id)}
            >
              Delete
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
