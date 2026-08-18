import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { App } from "../../src/App";
import { DISCLAIMER_TEXT } from "../../src/components/Disclaimer";
import { createTestRouter } from "../../src/router";
import { useAuthStore } from "../../src/stores/authStore";

const NAV_LINKS = [
  "Home",
  "Charts",
  "Scanner",
  "Strategies",
  "Trends",
  "Analytics",
  "ML",
  "Chat",
  "Settings",
];

const ROUTES = ["/", "/charts", "/scanner", "/strategies", "/trends", "/analytics", "/ml", "/chat", "/settings"];

describe("AppShell", () => {
  beforeEach(() => {
    document.documentElement.removeAttribute("data-theme");
    // AppShell now sits behind RequireAuth (Phase 11) — sign in for these specs.
    useAuthStore.setState({
      isAuthenticated: true,
      resolved: true,
      session: { user: { email: "a@b.com" } } as never,
      user: { email: "a@b.com" } as never,
    });
  });

  it("renders all 9 nav links", () => {
    render(<App router={createTestRouter("/")} />);
    const nav = screen.getByRole("navigation", { name: "Primary" });

    for (const label of NAV_LINKS) {
      expect(within(nav).getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it.each(ROUTES)("shows nav and disclaimer footer on %s", (path) => {
    render(<App router={createTestRouter(path)} />);

    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeInTheDocument();
  });

  it("marks the active route's nav link with aria-current", () => {
    render(<App router={createTestRouter("/scanner")} />);
    const nav = screen.getByRole("navigation", { name: "Primary" });

    expect(within(nav).getByRole("link", { name: "Scanner" })).toHaveClass("active");
  });

  it("renders a theme toggle", () => {
    render(<App router={createTestRouter("/")} />);

    expect(screen.getByRole("button", { name: /switch to (light|dark) theme/i })).toBeInTheDocument();
  });
});
