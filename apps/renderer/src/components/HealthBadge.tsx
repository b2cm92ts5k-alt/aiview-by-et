import type { EngineInfo, HealthResponse } from "@aiview/shared-types";
import { useEffect, useState } from "react";
import { fetchHealth } from "../api/engine";

const POLL_MS = 3000;

type EngineUiState =
  | { kind: "connecting" }
  | { kind: "online"; health: HealthResponse }
  | { kind: "offline"; detail: string };

export default function HealthBadge({ info }: { info: EngineInfo | null }) {
  const [state, setState] = useState<EngineUiState>({ kind: "connecting" });

  useEffect(() => {
    if (!info) {
      setState({ kind: "offline", detail: "ไม่พบ Electron bridge (เปิดผ่าน npm run dev)" });
      return;
    }
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
    <div className="flex items-center gap-2" data-testid="engine-status" title={
      state.kind === "offline" ? state.detail : undefined
    }>
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${
          state.kind === "online"
            ? "bg-emerald-400"
            : state.kind === "connecting"
              ? "bg-amber-400 animate-pulse"
              : "bg-rose-500"
        }`}
      />
      <span className="text-xs text-slate-400">
        {state.kind === "online" && `Engine ทำงานปกติ · v${state.health.version}`}
        {state.kind === "connecting" && "กำลังเชื่อมต่อ engine…"}
        {state.kind === "offline" && <span className="text-rose-300">Engine ออฟไลน์ — {state.detail}</span>}
      </span>
    </div>
  );
}
