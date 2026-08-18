import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

/** Stamp the active theme onto <html> so tokens.css can react to it. */
function stampTheme(theme: Theme) {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = theme;
  }
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme) => {
        stampTheme(theme);
        set({ theme });
      },
      toggleTheme: () => get().setTheme(get().theme === "dark" ? "light" : "dark"),
    }),
    {
      name: "market-assistant-theme",
      onRehydrateStorage: () => (state) => {
        stampTheme(state?.theme ?? "dark");
      },
    }
  )
);

// Stamp once at module load so the first paint matches the stored theme.
stampTheme(useThemeStore.getState().theme);
