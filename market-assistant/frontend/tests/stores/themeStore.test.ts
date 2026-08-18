import { beforeEach, describe, expect, it } from "vitest";

import { useThemeStore } from "../../src/stores/themeStore";

describe("themeStore", () => {
  beforeEach(() => {
    localStorage.clear();
    useThemeStore.setState({ theme: "dark" });
    document.documentElement.removeAttribute("data-theme");
  });

  it("defaults to dark", () => {
    expect(useThemeStore.getState().theme).toBe("dark");
  });

  it("toggle flips dark -> light and stamps data-theme", () => {
    useThemeStore.getState().toggleTheme();

    expect(useThemeStore.getState().theme).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("toggle flips light -> dark", () => {
    useThemeStore.getState().setTheme("light");
    useThemeStore.getState().toggleTheme();

    expect(useThemeStore.getState().theme).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("persists the theme to localStorage", () => {
    useThemeStore.getState().setTheme("light");

    expect(localStorage.getItem("market-assistant-theme")).toContain("light");
  });
});
