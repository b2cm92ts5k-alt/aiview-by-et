/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ENGINE_PORT?: string;
  readonly VITE_ENGINE_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
