import { Panel } from "../components/common/Panel";
import { HitsFeed } from "../components/scanner/HitsFeed";
import { RuleBuilder } from "../components/scanner/RuleBuilder";
import { RuleList } from "../components/scanner/RuleList";
import { useScanHits } from "../hooks/useScanHits";
import { useScanRules } from "../hooks/useScanRules";
import type { RuleDefinition } from "../lib/scannerTypes";

export function Scanner() {
  const { rules, isLoading, createRule, updateRule, deleteRule } = useScanRules();
  const hits = useScanHits();

  const handleSubmit = (definition: RuleDefinition, name: string) => {
    if (!name.trim()) return;
    createRule.mutate({ name: name.trim(), definition });
  };

  return (
    <>
      <h1 className="page-title">Scanner</h1>
      <p className="page-sub">Build indicator rules · watch live hits across your universe</p>

      <div className="scanner-grid">
        <div className="scanner-col">
          <Panel title="Rule builder">
            <RuleBuilder onSubmit={handleSubmit} pending={createRule.isPending} />
            {createRule.isError && (
              <p className="scanner-err">Could not save the rule. Is the backend running?</p>
            )}
          </Panel>

          <Panel title="Saved rules" tag={rules.length > 0 ? `${rules.length}` : undefined}>
            <RuleList
              rules={rules}
              isLoading={isLoading}
              onToggle={(id, enabled) => updateRule.mutate({ id, enabled })}
              onDelete={(id) => deleteRule.mutate(id)}
            />
          </Panel>
        </div>

        <div className="scanner-col">
          <Panel title="Live hits" tag={hits.length > 0 ? `${hits.length}` : "last 30 min"}>
            <HitsFeed hits={hits} />
          </Panel>
        </div>
      </div>
    </>
  );
}
