import type { Session, User } from "@supabase/supabase-js";
import { create } from "zustand";
import { persist } from "zustand/middleware";

import { supabase } from "../lib/supabase";

interface AuthState {
  user: User | null;
  session: Session | null;
  isAuthenticated: boolean;
  /**
   * True once the live Supabase session has been resolved at least once
   * (initial `getSession`/`onAuthStateChange`, or an explicit auth action).
   * Route guards must wait for this before redirecting, so a persisted
   * fast-paint `user` can't briefly admit a signed-out visitor.
   */
  resolved: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  setSession: (session: Session | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      session: null,
      isAuthenticated: false,
      resolved: false,
      setSession: (session) =>
        set({
          session,
          user: session?.user ?? null,
          isAuthenticated: session != null,
          resolved: true,
        }),
      signIn: async (email, password) => {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        set({
          session: data.session,
          user: data.user,
          isAuthenticated: data.session != null,
          resolved: true,
        });
      },
      signUp: async (email, password) => {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        set({
          session: data.session,
          user: data.user,
          isAuthenticated: data.session != null,
          resolved: true,
        });
      },
      signOut: async () => {
        const { error } = await supabase.auth.signOut();
        if (error) throw error;
        set({ session: null, user: null, isAuthenticated: false, resolved: true });
      },
    }),
    {
      // Persist ONLY `user` for a fast first-paint after reload — never the
      // session/access_token. supabase-js persists its own session, so
      // duplicating the JWT under a second localStorage key only widens the
      // token-theft surface. initAuth()/onAuthStateChange (wired in main.tsx)
      // rehydrates the live session + token on load.
      name: "market-assistant-auth",
      partialize: (state) => ({ user: state.user }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isAuthenticated = state.user != null;
        }
      },
    },
  ),
);

let authInitialized = false;

/**
 * Registers the Supabase auth-state listener once so sign-in/refresh/sign-out
 * events (including those from another tab) keep the store in sync. Safe to
 * call multiple times — only the first call subscribes.
 */
export function initAuth(): void {
  if (authInitialized) return;
  authInitialized = true;
  supabase.auth.onAuthStateChange((_event, session) => {
    useAuthStore.getState().setSession(session);
  });
}
