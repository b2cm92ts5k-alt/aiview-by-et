import type {
  Candle,
  EngineInfo,
  HealthResponse,
  MarketsResponse,
  Timeframe,
} from "@aiview/shared-types";

export async function getEngineInfo(): Promise<EngineInfo | null> {
  if (window.aiview) return window.aiview.engineInfo();
  // dev fallback: renderer opened in a plain browser (vite preview) against a
  // manually started engine — not used inside Electron
  const port = import.meta.env.VITE_ENGINE_PORT;
  if (port) {
    return { port: Number(port), token: import.meta.env.VITE_ENGINE_TOKEN ?? "" };
  }
  return null;
}

function base(info: EngineInfo): string {
  return `http://127.0.0.1:${info.port}`;
}

function headers(info: EngineInfo): Record<string, string> {
  return { "X-Engine-Token": info.token };
}

async function get<T>(info: EngineInfo, path: string): Promise<T> {
  const res = await fetch(`${base(info)}${path}`, { headers: headers(info) });
  if (!res.ok) throw new Error(`${path} failed: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export function fetchHealth(info: EngineInfo): Promise<HealthResponse> {
  return get<HealthResponse>(info, "/health");
}

export function fetchMarkets(info: EngineInfo): Promise<MarketsResponse> {
  return get<MarketsResponse>(info, "/markets");
}

export function fetchCandles(
  info: EngineInfo,
  symbol: string,
  tf: Timeframe,
  limit = 500,
): Promise<Candle[]> {
  const params = new URLSearchParams({ symbol, tf, limit: String(limit) });
  return get<Candle[]>(info, `/candles?${params}`);
}

export function wsUrl(info: EngineInfo): string {
  return `ws://127.0.0.1:${info.port}/ws?token=${encodeURIComponent(info.token)}`;
}
