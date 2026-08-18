import { create } from "zustand";

export interface WatchlistTileData {
  symbol: string;
  last: number;
  changePct: number;
}

interface WatchlistState {
  tiles: Record<string, WatchlistTileData>;
  upsertTile: (tile: WatchlistTileData) => void;
}

export const useWatchlistStore = create<WatchlistState>((set) => ({
  tiles: {},
  upsertTile: (tile) =>
    set((state) => ({ tiles: { ...state.tiles, [tile.symbol]: tile } })),
}));
