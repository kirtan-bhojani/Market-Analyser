import type { ReactNode } from "react";

interface EmptyStateProps {
  glyph?: ReactNode;
  title: string;
  message: string;
  action?: string;
}

/** Designed empty state used by placeholder pages until Phases 3–13 fill content. */
export function EmptyState({ glyph = "◔", title, message, action }: EmptyStateProps) {
  return (
    <div className="empty">
      <div className="glyph" aria-hidden="true">
        {glyph}
      </div>
      <h3>{title}</h3>
      <p>{message}</p>
      {action !== undefined && (
        <button className="cta" type="button">
          {action}
        </button>
      )}
    </div>
  );
}
