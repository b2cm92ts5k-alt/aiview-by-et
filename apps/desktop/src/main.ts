import { BrowserWindow, Notification, app, ipcMain } from "electron";
import * as path from "path";
import { type SidecarHandle, startSidecar } from "./sidecar";
import { hasKey, setKey } from "./vault";

let sidecar: SidecarHandle | null = null;
let win: BrowserWindow | null = null;

// dev: apps/desktop → repo root is two levels up
const repoRoot = path.resolve(__dirname, "..", "..", "..");
const engineDir = path.join(repoRoot, "engine");

function sendEngineStatus(status: unknown): void {
  win?.webContents.send("engine:status", status);
}

function createWindow(): void {
  win = new BrowserWindow({
    width: 1400,
    height: 900,
    title: "AIView by ET",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    void win.loadURL(devUrl);
  } else {
    void win.loadFile(path.join(repoRoot, "apps", "renderer", "dist", "index.html"));
  }
  win.on("closed", () => {
    win = null;
  });
}

function registerIpc(): void {
  ipcMain.handle("engine:info", () =>
    sidecar ? { port: sidecar.port, token: sidecar.token } : null,
  );
  ipcMain.handle("vault:setKey", (_e, provider: string, key: string) => setKey(provider, key));
  ipcMain.handle("vault:hasKey", (_e, provider: string) => hasKey(provider));
  ipcMain.handle("app:notify", (_e, payload: { title: string; body: string }) => {
    new Notification({ title: payload.title, body: payload.body }).show();
  });
}

app.whenReady().then(async () => {
  registerIpc();
  createWindow();
  try {
    sidecar = await startSidecar(engineDir, path.join(app.getPath("userData"), "aiview.sqlite3"), {
      onCrash: (restarts) => sendEngineStatus({ state: "crashed", restarts }),
      onFailed: () => sendEngineStatus({ state: "failed" }),
    });
    sendEngineStatus({ state: "ready", info: { port: sidecar.port, token: sidecar.token } });
  } catch (err) {
    console.error("[main] engine failed to start:", err);
    sendEngineStatus({ state: "failed" });
  }
});

app.on("window-all-closed", () => {
  app.quit();
});

app.on("before-quit", (event) => {
  if (sidecar) {
    event.preventDefault();
    const s = sidecar;
    sidecar = null;
    void s.stop().finally(() => app.quit());
  }
});
