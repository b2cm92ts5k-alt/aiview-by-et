/**
 * Ollama manager (F7): detect install, ensure serve, pull with progress,
 * single-active-model policy (rm old before pull new).
 */
import { type ChildProcess, execFile, spawn } from "child_process";
import { existsSync } from "fs";
import * as os from "os";
import * as path from "path";

const OLLAMA_URL = "http://127.0.0.1:11434";
const DOWNLOAD_URL = "https://ollama.com/download";

export interface OllamaStatus {
  installed: boolean;
  running: boolean;
  models: string[];
  downloadUrl: string;
}

export interface PullProgress {
  model: string;
  status: string; // e.g. "pulling manifest", "downloading", "success", "error"
  percent: number | null;
  detail?: string;
}

export function findOllama(): string | null {
  const candidates = [
    path.join(os.homedir(), "AppData", "Local", "Programs", "Ollama", "ollama.exe"),
    "C:\\Program Files\\Ollama\\ollama.exe",
  ];
  for (const c of candidates) if (existsSync(c)) return c;
  return null; // PATH fallback handled by callers using "ollama"
}

async function isRunning(): Promise<boolean> {
  try {
    const res = await fetch(`${OLLAMA_URL}/api/tags`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function ollamaStatus(): Promise<OllamaStatus> {
  const bin = findOllama();
  const running = await isRunning();
  let models: string[] = [];
  if (running) {
    try {
      const res = await fetch(`${OLLAMA_URL}/api/tags`);
      const body = (await res.json()) as { models?: { name: string }[] };
      models = (body.models ?? []).map((m) => m.name);
    } catch {
      /* engine ยังใช้ /ai/models ได้อยู่ดี */
    }
  }
  return { installed: bin !== null, running, models, downloadUrl: DOWNLOAD_URL };
}

export async function ensureServe(): Promise<boolean> {
  if (await isRunning()) return true;
  const bin = findOllama();
  if (!bin) return false;
  const child = spawn(bin, ["serve"], { detached: true, stdio: "ignore", windowsHide: true });
  child.unref();
  for (let i = 0; i < 20; i++) {
    await new Promise((r) => setTimeout(r, 500));
    if (await isRunning()) return true;
  }
  return false;
}

function rmModel(bin: string, model: string): Promise<void> {
  return new Promise((resolve) => {
    execFile(bin, ["rm", model], () => resolve()); // ไม่มี model อยู่แล้วก็ถือว่าจบ
  });
}

/**
 * Pull model พร้อม progress (single-active: ลบ removeModel ก่อนถ้าระบุ).
 * ollama pull เขียน progress ลง stderr เช่น "pulling abc... 42%"
 */
export async function ensureModel(
  model: string,
  removeModel: string | null,
  onProgress: (p: PullProgress) => void,
): Promise<void> {
  const bin = findOllama();
  if (!bin) {
    onProgress({ model, status: "error", percent: null,
                 detail: `Ollama ยังไม่ติดตั้ง — ดาวน์โหลดที่ ${DOWNLOAD_URL}` });
    return;
  }
  if (!(await ensureServe())) {
    onProgress({ model, status: "error", percent: null, detail: "start ollama serve ไม่สำเร็จ" });
    return;
  }
  if (removeModel && removeModel !== model) {
    onProgress({ model, status: `removing ${removeModel}`, percent: null });
    await rmModel(bin, removeModel);
  }

  await new Promise<void>((resolve) => {
    const child: ChildProcess = spawn(bin, ["pull", model], { windowsHide: true });
    const handleChunk = (chunk: Buffer) => {
      const text = chunk.toString();
      for (const line of text.split(/\r|\n/)) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        const pct = /(\d{1,3})%/.exec(trimmed);
        onProgress({
          model,
          status: trimmed.slice(0, 80),
          percent: pct ? Math.min(100, Number(pct[1])) : null,
        });
      }
    };
    child.stdout?.on("data", handleChunk);
    child.stderr?.on("data", handleChunk);
    child.on("exit", (code) => {
      onProgress(code === 0
        ? { model, status: "success", percent: 100 }
        : { model, status: "error", percent: null, detail: `ollama pull exited ${code}` });
      resolve();
    });
  });
}
