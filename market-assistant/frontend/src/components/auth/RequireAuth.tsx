import { Navigate, Outlet } from "react-router-dom";

import { useAuthStore } from "../../stores/authStore";

/** Route guard: renders its children via `<Outlet/>` when signed in, else
 * redirects to `/login`. Mounted as the parent element of every app route.
 *
 * Authorization keys off the LIVE Supabase `session`, not the persisted
 * fast-paint flag — and it waits for `resolved` so a reload can't briefly admit
 * (or briefly bounce) a visitor before the real session is known. */
export function RequireAuth() {
  const resolved = useAuthStore((s) => s.resolved);
  const authed = useAuthStore((s) => s.session != null);

  // Live session not yet known — hold the route rather than deciding on stale
  // persisted state. AppShell renders a neutral shell; keep this minimal.
  if (!resolved) return <div className="route-resolving" aria-busy="true" />;

  return authed ? <Outlet /> : <Navigate to="/login" replace />;
}
