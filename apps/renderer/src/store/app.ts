import type { EngineInfo, Timeframe } from "@aiview/shared-types";
import { create } from "zustand";

interface AppState {
  engineInfo: EngineInfo | null;
  symbol: string;
  tf: Timeframe;
  setEngineInfo: (info: EngineInfo | null) => void;
  setSymbol: (symbol: string) => void;
  setTf: (tf: Timeframe) => void;
}

export const useAppStore = create<AppState>((set) => ({
  engineInfo: null,
  symbol: "BTC/USDT",
  tf: "15m",
  setEngineInfo: (engineInfo) => set({ engineInfo }),
  setSymbol: (symbol) => set({ symbol }),
  setTf: (tf) => set({ tf }),
}));
