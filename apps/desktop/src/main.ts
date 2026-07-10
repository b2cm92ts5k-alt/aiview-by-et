import { BrowserWindow, Notification, app, ipcMain, shell } from "electron";
import * as path from "path";
import { ensureModel, ollamaStatus } from "./ollama";
import { type SidecarHandle, startSidecar } from "./sidecar";
import { getSystemSpecs } from "./specs";
import { deleteKey, getKeyForEngine, hasKey, listKeyProviders, setKey } from "./vault";

// provider ที่รองรับ BYOK — key ถูกส่งเข้า engine แบบ in-memory ต่อ session (TDD §9)
const KEY_PROVIDERS = ["anthropic", "openai", "google", "openrouter", "github", "twelvedata"];

let sidecar: SidecarHandle | null = null;
let win: BrowserWindow | null = null;

// dev: apps/desktop → repo root is two levels up · prod: engine อยู่ใน resources
const repoRoot = path.resolve(__dirname, "..", "..", "..");
const engineDir = app.isPackaged
  ? path.join(process.resourcesPath, "engine")
  : path.join(repoRoot, "engine");
const engineExe = app.isPackaged ? path.join(engineDir, "aiview-engine.exe") : null;

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
  } else if (app.isPackaged) {
    // renderer-dist ถูก copy เข้า app package ตอน build (ดู scripts "package")
    void win.loadFile(path.join(__dirname, "..", "renderer-dist", "index.html"));
  } else {
    void win.loadFile(path.join(repoRoot, "apps", "renderer", "dist", "index.html"));
  }
  win.on("closed", () => {
    win = null;
  });
}

/** ส่ง key เข้า engine — in-memory เท่านั้น ห้าม log ตัว key (TDD §9) */
async function pushKeyToEngine(provider: string, key: string): Promise<void> {
  if (!sidecar) return;
  try {
    await fetch(`http://127.0.0.1:${sidecar.port}/providers/keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Engine-Token": sidecar.token },
      body: JSON.stringify({ provider, key }),
    });
  } catch (err) {
    console.error(`[main] push key for ${provider} failed:`, err);
  }
}

async function pushAllVaultKeys(): Promise<void> {
  for (const provider of await listKeyProviders()) {
    if (!KEY_PROVIDERS.includes(provider)) continue;
    const key = await getKeyForEngine(provider);
    if (key) await pushKeyToEngine(provider, key);
  }
}

function registerIpc(): void {
  ipcMain.handle("engine:info", () =>
    sidecar ? { port: sidecar.port, token: sidecar.token } : null,
  );
  ipcMain.handle("vault:setKey", async (_e, provider: string, key: string) => {
    await setKey(provider, key);
    await pushKeyToEngine(provider, key); // มีผลทันทีโดย key ไม่ผ่าน renderer กลับ
  });
  ipcMain.handle("vault:hasKey", (_e, provider: string) => hasKey(provider));
  ipcMain.handle("vault:deleteKey", async (_e, provider: string) => {
    await deleteKey(provider);
    if (sidecar) {
      await fetch(`http://127.0.0.1:${sidecar.port}/providers/keys/${provider}`, {
        method: "DELETE",
        headers: { "X-Engine-Token": sidecar.token },
      }).catch(() => {});
    }
  });
  ipcMain.handle("vault:listProviders", () => listKeyProviders());
  ipcMain.handle("system:specs", () => getSystemSpecs());
  ipcMain.handle("ollama:status", () => ollamaStatus());
  ipcMain.handle("ollama:openDownload", () => shell.openExternal("https://ollama.com/download"));
  ipcMain.handle(
    "ollama:ensure",
    (e, model: string, removeModel: string | null) =>
      ensureModel(model, removeModel, (p) => {
        e.sender.send("ollama:progress", p);
      }),
  );
  ipcMain.handle("app:notify", (_e, payload: { title: string; body: string }) => {
    new Notification({ title: payload.title, body: payload.body }).show();
  });
}

app.whenReady().then(async () => {
  registerIpc();
  createWindow();
  try {
    sidecar = await startSidecar(
      engineDir,
      path.join(app.getPath("userData"), "aiview.sqlite3"),
      {
        onCrash: (restarts) => sendEngineStatus({ state: "crashed", restarts }),
        onFailed: () => sendEngineStatus({ state: "failed" }),
      },
      engineExe,
    );
    sendEngineStatus({ state: "ready", info: { port: sidecar.port, token: sidecar.token } });
    await pushAllVaultKeys(); // BYOK: key จาก vault → engine ทันทีที่พร้อม
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
