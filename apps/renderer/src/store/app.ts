import type { EngineInfo, Timeframe } from "@aiview/shared-types";
import { create } from "zustand";

interface AppState {
  engineInfo: EngineInfo | null;
  symbol: string;
  tf: Timeframe;
  /** ชื่อ custom indicator (F6) ที่ overlay อยู่บน chart — null = ไม่มี */
  overlaySet: string | null;
  setEngineInfo: (info: EngineInfo | null) => void;
  setSymbol: (symbol: string) => void;
  setTf: (tf: Timeframe) => void;
  setOverlaySet: (name: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  engineInfo: null,
  symbol: "BTC/USDT",
  tf: "15m",
  overlaySet: null,
  setEngineInfo: (engineInfo) => set({ engineInfo }),
  setSymbol: (symbol) => set({ symbol }),
  setTf: (tf) => set({ tf }),
  setOverlaySet: (overlaySet) => set({ overlaySet }),
}));
