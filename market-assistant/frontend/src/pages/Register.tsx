import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Panel } from "../components/common/Panel";
import { DEMO_ID, DEMO_PASSKEY } from "../lib/demoCreds";
import { useAuthStore } from "../stores/authStore";

/** Supabase-backed sign-up. Navigates to the app home if a session comes back
 * immediately; otherwise (email confirmation required) shows a hint instead.
 * Fields are prefilled with demo access so an interviewer can sign in directly. */
export function Register() {
  const signUp = useAuthStore((s) => s.signUp);
  const navigate = useNavigate();
  const [email, setEmail] = useState(DEMO_ID);
  const [password, setPassword] = useState(DEMO_PASSKEY);
  const [error, setError] = useState<string | null>(null);
  const [needsConfirmation, setNeedsConfirmation] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setNeedsConfirmation(false);
    setSubmitting(true);
    try {
      await signUp(email, password);
      if (useAuthStore.getState().isAuthenticated) {
        navigate("/");
      } else {
        setNeedsConfirmation(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="brand-mark" aria-hidden="true">
            M
          </div>
          <div className="brand-name">Market Assistant</div>
        </div>

        <Panel title="Create account">
          <form className="auth-form" onSubmit={handleSubmit}>
            <label className="auth-field" htmlFor="register-email">
              <span className="auth-label">ID</span>
              <input
                id="register-email"
                className="auth-input"
                type="text"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="auth-field" htmlFor="register-password">
              <span className="auth-label">Passkey</span>
              <input
                id="register-password"
                className="auth-input"
                type="password"
                autoComplete="new-password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            <p className="auth-hint">Demo access prefilled — continue to explore.</p>
            {error !== null && <p className="auth-error" role="alert">{error}</p>}
            {needsConfirmation && (
              <p className="auth-hint">Check your email to confirm your account, then sign in.</p>
            )}

            <button type="submit" className="auth-submit" disabled={submitting}>
              {submitting ? "Creating account…" : "Create account"}
            </button>
          </form>
        </Panel>

        <p className="auth-alt">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
