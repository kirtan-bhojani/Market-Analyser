import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { RequireAuth } from "../../src/components/auth/RequireAuth";
import { useAuthStore } from "../../src/stores/authStore";

function renderGuard() {
  return render(
    <MemoryRouter initialEntries={["/app"]}>
      <Routes>
        <Route element={<RequireAuth />}>
          <Route path="/app" element={<h1>Guarded</h1>} />
        </Route>
        <Route path="/login" element={<h1>Sign in</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  useAuthStore.setState({ user: null, session: null, isAuthenticated: false, resolved: false });
});

describe("RequireAuth (T3-20)", () => {
  it("holds the route (neither guarded nor login) until auth is resolved", () => {
    // Persisted fast-paint could set isAuthenticated=true — must NOT admit yet.
    useAuthStore.setState({ isAuthenticated: true, resolved: false, session: null });
    renderGuard();
    expect(screen.queryByRole("heading", { name: "Guarded" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("redirects to /login once resolved with no live session", () => {
    useAuthStore.setState({ isAuthenticated: true, resolved: true, session: null });
    renderGuard();
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("renders the guarded route once resolved with a live session", () => {
    useAuthStore.setState({
      isAuthenticated: true,
      resolved: true,
      session: { user: { email: "a@b.com" } } as never,
    });
    renderGuard();
    expect(screen.getByRole("heading", { name: "Guarded" })).toBeInTheDocument();
  });
});
