import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { initAuth } from "./stores/authStore";
import "./styles/tokens.css";
import "./styles/app.css";

// Register the Supabase auth-state listener once so the store stays in sync on
// refresh, token-refresh, and cross-tab sign in/out.
initAuth();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
