import type { EngineInfo, HealthResponse } from "@aiview/shared-types";
import { useEffect, useState } from "react";
import { fetchHealth, getEngineInfo } from "./api/engine";

const POLL_MS = 3000;

type EngineUiState =
  | { kind: "connecting" }
  | { kind: "online"; health: HealthResponse }
  | { kind: "offline"; detail: string };

export default function App() {
  const [state, setState] = useState<EngineUiState>({ kind: "connecting" });
  const [info, setInfo] = useState<EngineInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    const acquire = async () => {
      const engineInfo = await getEngineInfo();
      if (!cancelled) setInfo(engineInfo);
      if (!engineInfo && !cancelled) {
        setState({ kind: "offline", detail: "ไม่พบ Electron bridge (เปิดผ่าน npm run dev)" });
      }
    };
    void acquire();
    // main pushes engine:status when sidecar becomes ready/crashes
    const off = window.aiview?.onEngineStatus((status) => {
      if (status.state === "ready") setInfo(status.info);
      if (status.state === "failed") {
        setState({ kind: "offline", detail: "engine start ไม่สำเร็จ (ดู log ของ main)" });
      }
    });
    return () => {
      cancelled = true;
      off?.();
    };
  }, []);

  useEffect(() => {
    if (!info) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const health = await fetchHealth(info);
        if (!cancelled) setState({ kind: "online", health });
      } catch (err) {
        if (!cancelled) setState({ kind: "offline", detail: String(err) });
      }
    };
    void poll();
    const timer = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [info]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="w-[420px] rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <h1 className="text-xl font-semibold">AIView by ET</h1>
        <p className="mt-1 text-sm text-slate-400">M0 Foundations — engine health check</p>

        <div className="mt-5 flex items-center gap-3" data-testid="engine-status">
          <span
            className={`inline-block h-3 w-3 rounded-full ${
              state.kind === "online"
                ? "bg-emerald-400"
                : state.kind === "connecting"
                  ? "bg-amber-400 animate-pulse"
                  : "bg-rose-500"
            }`}
          />
          <span className="text-sm">
            {state.kind === "online" && (
              <>
                Engine ทำงานปกติ · v{state.health.version}
                {info ? ` · port ${info.port}` : ""}
              </>
            )}
            {state.kind === "connecting" && "กำลังเชื่อมต่อ engine…"}
            {state.kind === "offline" && (
              <span className="text-rose-300">Engine ออฟไลน์ — {state.detail}</span>
            )}
          </span>
        </div>
      </div>
    </div>
  );
}
