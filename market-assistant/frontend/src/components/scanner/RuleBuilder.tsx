import { useState } from "react";

import {
  INDICATORS,
  OPERATORS,
  TIMEFRAMES,
  type Condition,
  type Indicator,
  type Operator,
  type RuleDefinition,
  type Timeframe,
} from "../../lib/scannerTypes";

const emptyRow = (): Condition => ({ ind: "rsi", tf: "5m", op: "<", value: 0 });

interface RuleBuilderProps {
  onSubmit: (definition: RuleDefinition, name: string) => void;
  /** Optional: disable the save button (e.g. while a create request is in flight). */
  pending?: boolean;
}

/**
 * Visual AND-condition builder. Emits a `RuleDefinition` DSL object of the
 * shape `{ all: Condition[] }` and the rule name via `onSubmit`.
 */
export function RuleBuilder({ onSubmit, pending = false }: RuleBuilderProps) {
  const [name, setName] = useState("");
  const [rows, setRows] = useState<Condition[]>([emptyRow()]);

  const updateRow = (index: number, patch: Partial<Condition>) => {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  // The worker only evaluates the closing timeframe's snapshot, so a rule that
  // mixes timeframes silently never fires. Keep the tf shared across all rows:
  // changing any row's tf rewrites every row's tf, so the builder can only emit
  // a uniform-tf rule.
  const updateTimeframe = (tf: Timeframe) => {
    setRows((prev) => prev.map((row) => ({ ...row, tf })));
  };

  const removeRow = (index: number) => {
    setRows((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev));
  };

  const handleSave = () => {
    onSubmit({ all: rows }, name);
  };

  return (
    <div className="rule-builder">
      <label className="rb-field">
        <span className="rb-label">Rule name</span>
        <input
          data-testid="rule-name-input"
          className="rb-name"
          value={name}
          placeholder="e.g. RSI dip"
          onChange={(e) => setName(e.target.value)}
        />
      </label>

      <div className="rb-rows">
        {rows.map((row, i) => (
          <div className="rb-row" key={i}>
            {i > 0 && <span className="rb-conj">AND</span>}
            <select
              data-testid={`row-${i}-indicator`}
              className="rb-select"
              value={row.ind}
              onChange={(e) => updateRow(i, { ind: e.target.value as Indicator })}
            >
              {INDICATORS.map((ind) => (
                <option key={ind} value={ind}>
                  {ind}
                </option>
              ))}
            </select>
            <select
              data-testid={`row-${i}-tf`}
              className="rb-select"
              value={row.tf}
              onChange={(e) => updateTimeframe(e.target.value as Timeframe)}
            >
              {TIMEFRAMES.map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </select>
            <select
              data-testid={`row-${i}-operator`}
              className="rb-select rb-op"
              value={row.op}
              onChange={(e) => updateRow(i, { op: e.target.value as Operator })}
            >
              {OPERATORS.map((op) => (
                <option key={op} value={op}>
                  {op}
                </option>
              ))}
            </select>
            <input
              data-testid={`row-${i}-value`}
              className="rb-value num"
              type="number"
              value={row.value}
              onChange={(e) => updateRow(i, { value: Number(e.target.value) })}
            />
            <button
              type="button"
              className="rb-remove"
              aria-label={`Remove condition ${i + 1}`}
              disabled={rows.length === 1}
              onClick={() => removeRow(i)}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <div className="rb-actions">
        <button
          type="button"
          className="rb-add"
          data-testid="add-row"
          onClick={() =>
            // Inherit the current (shared) timeframe so adding a condition can't
            // silently create a mixed-tf rule that the worker never fires.
            setRows((prev) => [
              ...prev,
              { ...emptyRow(), tf: prev[0]?.tf ?? emptyRow().tf },
            ])
          }
        >
          + Add condition
        </button>
        <button
          type="button"
          className="cta rb-save"
          data-testid="save-rule"
          disabled={pending || !name.trim()}
          onClick={handleSave}
        >
          Save rule
        </button>
      </div>
    </div>
  );
}
