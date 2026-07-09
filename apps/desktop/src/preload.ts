import { contextBridge, ipcRenderer } from "electron";

/**
 * Renderer-facing bridge (`window.aiview`) — privileged calls only (TDD.md §3.1).
 * Market data flows over REST/WS straight to the engine, not through here.
 */
contextBridge.exposeInMainWorld("aiview", {
  engineInfo: () => ipcRenderer.invoke("engine:info"),
  vaultSetKey: (provider: string, key: string) =>
    ipcRenderer.invoke("vault:setKey", provider, key),
  vaultHasKey: (provider: string) => ipcRenderer.invoke("vault:hasKey", provider),
  notify: (payload: { title: string; body: string }) => ipcRenderer.invoke("app:notify", payload),
  onEngineStatus: (cb: (status: unknown) => void) => {
    const listener = (_e: unknown, status: unknown) => cb(status);
    ipcRenderer.on("engine:status", listener);
    return () => ipcRenderer.removeListener("engine:status", listener);
  },
});
