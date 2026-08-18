import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  /** Optional 0–100 gauge under the value. */
  gauge?: number;
}

/** Labelled metric tile with an optional gauge bar. */
export function StatCard({ label, value, gauge }: StatCardProps) {
  return (
    <div className="stat">
      <div className="lbl">{label}</div>
      <div className="big num">{value}</div>
      {gauge !== undefined && (
        <div className="gauge">
          <span style={{ width: `${Math.max(0, Math.min(100, gauge))}%` }} />
        </div>
      )}
    </div>
  );
}
