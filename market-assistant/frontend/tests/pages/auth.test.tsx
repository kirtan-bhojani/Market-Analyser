import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../../src/App";
import { createTestRouter } from "../../src/router";

const authState = vi.hoisted(() => ({
  isAuthenticated: false,
  resolved: true,
  session: null as { user: { email: string } } | null,
  user: null as { email: string } | null,
  signIn: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("../../src/stores/authStore", () => ({
  useAuthStore: Object.assign(
    (selector: (s: typeof authState) => unknown) => selector(authState),
    { getState: () => authState },
  ),
}));

describe("auth routing", () => {
  beforeEach(() => {
    authState.isAuthenticated = false;
    authState.resolved = true;
    authState.session = null;
    authState.user = null;
    authState.signIn.mockReset();
    authState.signUp.mockReset();
    authState.signOut.mockReset();
  });

  it("redirects an unauthenticated visitor to /login instead of the guarded route", () => {
    render(<App router={createTestRouter("/")} />);

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Home" })).not.toBeInTheDocument();
  });

  it("lets an authenticated visitor reach a guarded app route", () => {
    authState.isAuthenticated = true;
    authState.session = { user: { email: "a@b.com" } };
    authState.user = { email: "a@b.com" };

    render(<App router={createTestRouter("/")} />);

    expect(screen.getByRole("heading", { name: "Home" })).toBeInTheDocument();
  });

  it("submits the login form via signIn and navigates on success", async () => {
    authState.signIn.mockImplementation(async () => {
      authState.isAuthenticated = true;
    });

    render(<App router={createTestRouter("/login")} />);

    fireEvent.change(screen.getByLabelText("ID"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Passkey"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(authState.signIn).toHaveBeenCalledWith("a@b.com", "secret123"));
  });

  it("shows the Supabase error when signIn rejects", async () => {
    authState.signIn.mockRejectedValue(new Error("Invalid credentials"));

    render(<App router={createTestRouter("/login")} />);

    fireEvent.change(screen.getByLabelText("ID"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Passkey"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
  });
});
