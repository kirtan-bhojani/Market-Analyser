import type { ReactNode } from "react";

type BadgeVariant = "neutral" | "long" | "short" | "accent";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
}

/** Small status label. `long`/`short` carry direction semantics (never buy/sell). */
export function Badge({ variant = "neutral", children }: BadgeProps) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}
