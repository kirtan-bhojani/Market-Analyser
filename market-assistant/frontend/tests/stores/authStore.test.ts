import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Session, User } from "@supabase/supabase-js";

vi.mock("../../src/lib/supabase", () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn(),
      getSession: vi.fn(),
    },
  },
}));

import { supabase } from "../../src/lib/supabase";
import { useAuthStore } from "../../src/stores/authStore";

const fakeUser = { id: "user-1", email: "a@b.com" } as unknown as User;
const fakeSession = { access_token: "fake-token", user: fakeUser } as unknown as Session;

const mockedSignIn = vi.mocked(supabase.auth.signInWithPassword);
const mockedSignOut = vi.mocked(supabase.auth.signOut);

describe("authStore", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({ user: null, session: null, isAuthenticated: false });
    vi.clearAllMocks();
  });

  it("starts signed out", () => {
    const state = useAuthStore.getState();
    expect(state.session).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it("signIn sets session/user and isAuthenticated on success", async () => {
    mockedSignIn.mockResolvedValue({
      data: { session: fakeSession, user: fakeUser },
      error: null,
    } as Awaited<ReturnType<typeof supabase.auth.signInWithPassword>>);

    await useAuthStore.getState().signIn("a@b.com", "password123");

    const state = useAuthStore.getState();
    expect(state.session).toEqual(fakeSession);
    expect(state.user).toEqual(fakeUser);
    expect(state.isAuthenticated).toBe(true);
  });

  it("signIn surfaces the Supabase error and leaves state signed out", async () => {
    mockedSignIn.mockResolvedValue({
      data: { session: null, user: null },
      error: { message: "Invalid credentials" },
    } as unknown as Awaited<ReturnType<typeof supabase.auth.signInWithPassword>>);

    await expect(useAuthStore.getState().signIn("a@b.com", "wrong")).rejects.toBeTruthy();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("does not persist the access_token/session to localStorage", async () => {
    mockedSignIn.mockResolvedValue({
      data: { session: fakeSession, user: fakeUser },
      error: null,
    } as Awaited<ReturnType<typeof supabase.auth.signInWithPassword>>);

    await useAuthStore.getState().signIn("a@b.com", "password123");

    const persisted = localStorage.getItem("market-assistant-auth");
    expect(persisted).not.toBeNull();
    // The full session (incl. access_token) must never be duplicated here;
    // only `user` is persisted for a fast first-paint.
    expect(persisted).not.toContain("fake-token");
    expect(persisted).not.toContain("access_token");
    const parsed = JSON.parse(persisted as string);
    expect(parsed.state.user).toEqual(fakeUser);
    expect(parsed.state.session).toBeUndefined();
  });

  it("signOut clears session/user", async () => {
    useAuthStore.setState({
      session: fakeSession,
      user: fakeUser,
      isAuthenticated: true,
    });
    mockedSignOut.mockResolvedValue({ error: null });

    await useAuthStore.getState().signOut();

    const state = useAuthStore.getState();
    expect(state.session).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });
});
