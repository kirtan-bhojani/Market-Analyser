import { Panel } from "../components/common/Panel";
import { EmptyState } from "../components/common/EmptyState";
import { AlertSubscriptionForm } from "../components/settings/AlertSubscriptionForm";
import { useAlertSubscriptions } from "../hooks/useAlertSubscriptions";
import { useScanRules } from "../hooks/useScanRules";

export function Settings() {
  const { subscriptions, remove } = useAlertSubscriptions();
  const { rules } = useScanRules();

  const ruleName = (ruleId: number) => rules.find((r) => r.id === ruleId)?.name ?? `Rule #${ruleId}`;

  return (
    <>
      <h1 className="page-title">Settings</h1>
      <p className="page-sub">Alert subscriptions here · universe, profile, and theme live elsewhere</p>

      <Panel title="Alert subscriptions" tag={subscriptions.length > 0 ? `${subscriptions.length}` : undefined}>
        <AlertSubscriptionForm />

        {subscriptions.length === 0 ? (
          <EmptyState
            glyph="🔔"
            title="No alert subscriptions yet"
            message="Pick a scan rule and a telegram chat id above — you'll get a message every time that rule fires."
          />
        ) : (
          <ul className="as-list" data-testid="subscription-list">
            {subscriptions.map((sub) => (
              <li className="as-row" key={sub.id} data-testid={`subscription-${sub.id}`}>
                <div className="as-row-info">
                  <span className="as-row-rule">{ruleName(sub.rule_id)}</span>
                  <span className="as-row-target num">{sub.channel} → {sub.target}</span>
                </div>
                <button
                  type="button"
                  className="as-remove"
                  data-testid={`remove-${sub.id}`}
                  onClick={() => remove.mutate(sub.id)}
                  disabled={remove.isPending}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  );
}
