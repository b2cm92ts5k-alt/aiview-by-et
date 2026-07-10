import type {
  EngineInfo,
  EngineStatus,
  OllamaStatus,
  PullProgress,
  SystemSpecs,
} from "@aiview/shared-types";

declare global {
  interface Window {
    /** Bridge from Electron preload — undefined when running in a plain browser */
    aiview?: {
      engineInfo: () => Promise<EngineInfo | null>;
      vaultSetKey: (provider: string, key: string) => Promise<void>;
      vaultHasKey: (provider: string) => Promise<boolean>;
      vaultDeleteKey: (provider: string) => Promise<void>;
      vaultListProviders: () => Promise<string[]>;
      systemSpecs: () => Promise<SystemSpecs>;
      ollamaStatus: () => Promise<OllamaStatus>;
      ollamaOpenDownload: () => Promise<void>;
      ollamaEnsure: (model: string, removeModel: string | null) => Promise<void>;
      onOllamaProgress: (cb: (p: PullProgress) => void) => () => void;
      notify: (payload: { title: string; body: string }) => Promise<void>;
      onEngineStatus: (cb: (status: EngineStatus) => void) => () => void;
    };
  }
}

export {};
