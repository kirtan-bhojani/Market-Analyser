import type { ReactNode } from "react";

interface PanelProps {
  title?: string;
  tag?: ReactNode;
  children: ReactNode;
  bodyClassName?: string;
}

/** Bordered content card with an optional titled header. */
export function Panel({ title, tag, children, bodyClassName }: PanelProps) {
  return (
    <section className="panel">
      {title !== undefined && (
        <header className="panel-h">
          <h3>{title}</h3>
          {tag !== undefined && <span className="tag">{tag}</span>}
        </header>
      )}
      <div className={bodyClassName ?? "panel-b"}>{children}</div>
    </section>
  );
}
