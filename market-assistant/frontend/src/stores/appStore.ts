import { create } from "zustand";

interface AppState {
  selectedSymbol: string | null;
  setSelectedSymbol: (symbol: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedSymbol: null,
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
}));
