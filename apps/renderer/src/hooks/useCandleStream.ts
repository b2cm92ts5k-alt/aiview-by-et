import type { Candle, EngineInfo, Timeframe, WsEnvelope } from "@aiview/shared-types";
import { useEffect, useRef } from "react";
import { wsUrl } from "../api/engine";

const RECONNECT_MS = 2000;

/**
 * One engine WS connection; re-subscribes when symbol/tf changes and calls
 * onCandle for every candle.update (TDD §3.3 envelope).
 */
export function useCandleStream(
  info: EngineInfo | null,
  symbol: string,
  tf: Timeframe,
  onCandle: (candle: Candle) => void,
): void {
  const onCandleRef = useRef(onCandle);
  onCandleRef.current = onCandle;

  useEffect(() => {
    if (!info) return;
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      ws = new WebSocket(wsUrl(info));
      ws.onopen = () => {
        ws?.send(JSON.stringify({ type: "subscribe", payload: { symbol, tf } }));
      };
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data) as WsEnvelope;
        if (msg.type === "candle.update") {
          onCandleRef.current(msg.payload as Candle);
        }
      };
      ws.onclose = () => {
        if (!closed) retry = setTimeout(connect, RECONNECT_MS);
      };
    };
    connect();

    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [info, symbol, tf]);
}
