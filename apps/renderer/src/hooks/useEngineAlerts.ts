import type { EngineInfo, Signal, Trade, WsEnvelope } from "@aiview/shared-types";
import { useEffect } from "react";
import { wsUrl } from "../api/engine";

/** F8 — desktop notification เมื่อมี signal ใหม่ / ไม้จำลองปิด (ชน SL/TP) */
export function useEngineAlerts(info: EngineInfo | null): void {
  useEffect(() => {
    if (!info || !window.aiview) return;
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      ws = new WebSocket(wsUrl(info));
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data) as WsEnvelope;
        if (msg.type === "signal.new") {
          const s = msg.payload as Signal;
          void window.aiview?.notify({
            title: `จังหวะเข้า ${s.side.toUpperCase()} · ${s.symbol}`,
            body: `entry ${s.entry} · SL ${s.sl} · TP1 ${s.tp[0]} · มั่นใจ ${s.confidence}%`,
          });
        }
        if (msg.type === "trade.update") {
          const t = msg.payload as Trade;
          if (t.status !== "open") {
            void window.aiview?.notify({
              title: `ปิดไม้จำลอง ${t.symbol} — ${t.status.toUpperCase()}`,
              body: `PnL ${t.pnl?.toFixed(2) ?? "?"} · R ${t.r_multiple?.toFixed(2) ?? "?"}`,
            });
          }
        }
      };
      ws.onclose = () => {
        if (!closed) retry = setTimeout(connect, 3000);
      };
    };
    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [info]);
}
