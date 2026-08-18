import { Badge } from "./Badge";

interface DelayBadgeProps {
  delayed: boolean;
  delayMinutes: number;
}

/** Small inline flag for delayed feeds (e.g. equities at 15-min delay). */
export function DelayBadge({ delayed, delayMinutes }: DelayBadgeProps) {
  return delayed ? <Badge variant="accent">{delayMinutes}-min delayed</Badge> : null;
}
