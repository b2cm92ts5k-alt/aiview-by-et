/**
 * Python engine sidecar lifecycle (TDD.md §2):
 * spawn on a free loopback port → poll /health until ready →
 * graceful kill on quit → limited auto-restart on crash.
 */
import { type ChildProcess, spawn } from "child_process";
import { randomUUID } from "crypto";
import { existsSync } from "fs";
import * as net from "net";
import * as path from "path";

export interface SidecarHandle {
  port: number;
  token: string;
  stop: () => Promise<void>;
}

export interface SidecarEvents {
  onCrash: (restarts: number) => void;
  onFailed: () => void;
}

const MAX_RESTARTS = 3;
const HEALTH_TIMEOUT_MS = 30_000;

export function getFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.listen(0, "127.0.0.1", () => {
      const address = srv.address();
      if (address && typeof address === "object") {
        const port = address.port;
        srv.close(() => resolve(port));
      } else {
        srv.close(() => reject(new Error("no port")));
      }
    });
    srv.on("error", reject);
  });
}

function resolvePython(engineDir: string): string {
  if (process.env.AIVIEW_PYTHON) return process.env.AIVIEW_PYTHON;
  const venvPython =
    process.platform === "win32"
      ? path.join(engineDir, ".venv", "Scripts", "python.exe")
      : path.join(engineDir, ".venv", "bin", "python");
  return existsSync(venvPython) ? venvPython : "python";
}

export async function waitForHealth(port: number, timeoutMs = HEALTH_TIMEOUT_MS): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let delay = 200;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/health`);
      if (res.ok) return;
    } catch {
      // engine not up yet
    }
    await new Promise((r) => setTimeout(r, delay));
    delay = Math.min(delay * 1.5, 1_000);
  }
  throw new Error(`engine /health not ready within ${timeoutMs}ms`);
}

export async function startSidecar(
  engineDir: string,
  dbPath: string,
  events: SidecarEvents,
): Promise<SidecarHandle> {
  const token = randomUUID();
  const port = await getFreePort();
  let child: ChildProcess | null = null;
  let stopping = false;
  let restarts = 0;

  const spawnEngine = () => {
    child = spawn(resolvePython(engineDir), ["-m", "app.main", "--port", String(port)], {
      cwd: engineDir,
      env: { ...process.env, ENGINE_TOKEN: token, AIVIEW_DB: dbPath },
      stdio: ["ignore", "pipe", "pipe"],
    });
    child.stdout?.on("data", (d: Buffer) => console.log(`[engine] ${d.toString().trimEnd()}`));
    child.stderr?.on("data", (d: Buffer) => console.log(`[engine] ${d.toString().trimEnd()}`));
    child.on("exit", (code) => {
      if (stopping) return;
      restarts += 1;
      console.error(`[engine] exited (code=${code}), restart ${restarts}/${MAX_RESTARTS}`);
      if (restarts <= MAX_RESTARTS) {
        events.onCrash(restarts);
        spawnEngine();
      } else {
        events.onFailed();
      }
    });
  };

  spawnEngine();
  await waitForHealth(port);

  const stop = () =>
    new Promise<void>((resolve) => {
      stopping = true;
      if (!child || child.exitCode !== null) return resolve();
      const killTimer = setTimeout(() => {
        child?.kill("SIGKILL");
        resolve();
      }, 5_000);
      child.once("exit", () => {
        clearTimeout(killTimer);
        resolve();
      });
      child.kill(); // SIGTERM (Windows: TerminateProcess)
    });

  return { port, token, stop };
}
