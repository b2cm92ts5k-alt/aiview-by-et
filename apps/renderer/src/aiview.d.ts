import type { EngineInfo, EngineStatus } from "@aiview/shared-types";

declare global {
  interface Window {
    /** Bridge from Electron preload — undefined when running in a plain browser */
    aiview?: {
      engineInfo: () => Promise<EngineInfo | null>;
      vaultSetKey: (provider: string, key: string) => Promise<void>;
      vaultHasKey: (provider: string) => Promise<boolean>;
      notify: (payload: { title: string; body: string }) => Promise<void>;
      onEngineStatus: (cb: (status: EngineStatus) => void) => () => void;
    };
  }
}

export {};
