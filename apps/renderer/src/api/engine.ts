import type {
  AnalyzeRequest,
  BacktestRequest,
  BacktestRun,
  Candle,
  EngineInfo,
  GenerateIndicatorResponse,
  HealthResponse,
  IndicatorDef,
  IndicatorResult,
  MarketsResponse,
  Signal,
  Stats,
  Timeframe,
  Trade,
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

export function fetchIndicators(
  info: EngineInfo,
  symbol: string,
  tf: Timeframe,
  set = "core",
  limit = 300,
): Promise<IndicatorResult[]> {
  const params = new URLSearchParams({ symbol, tf, set, limit: String(limit) });
  return get<IndicatorResult[]>(info, `/indicators?${params}`);
}

export function fetchAiModels(info: EngineInfo): Promise<Record<string, string[]>> {
  return get<Record<string, string[]>>(info, "/ai/models");
}

export async function postBacktest(
  info: EngineInfo,
  req: BacktestRequest,
): Promise<{ run_id: string }> {
  const res = await fetch(`${base(info)}/sim/backtest`, {
    method: "POST",
    headers: { ...headers(info), "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`backtest failed: HTTP ${res.status}`);
  return (await res.json()) as { run_id: string };
}

export function fetchRun(info: EngineInfo, runId: string): Promise<BacktestRun> {
  return get<BacktestRun>(info, `/sim/runs/${runId}`);
}

export function fetchTrades(
  info: EngineInfo,
  scope?: "backtest" | "paper",
  runId?: string,
): Promise<Trade[]> {
  const params = new URLSearchParams();
  if (scope) params.set("scope", scope);
  if (runId) params.set("run_id", runId);
  return get<Trade[]>(info, `/trades?${params}`);
}

export function fetchStats(
  info: EngineInfo,
  scope?: "backtest" | "paper",
  runId?: string,
): Promise<Stats> {
  const params = new URLSearchParams();
  if (scope) params.set("scope", scope);
  if (runId) params.set("run_id", runId);
  return get<Stats>(info, `/stats?${params}`);
}

async function post<T>(info: EngineInfo, path: string, body: unknown): Promise<T> {
  const res = await fetch(`${base(info)}${path}`, {
    method: "POST",
    headers: { ...headers(info), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* keep http status */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export function generateIndicator(
  info: EngineInfo,
  req: { description: string; provider: string; model: string; symbol?: string; tf?: Timeframe },
): Promise<GenerateIndicatorResponse> {
  return post<GenerateIndicatorResponse>(info, "/indicators/ai/generate", req);
}

export function saveIndicatorDef(
  info: EngineInfo,
  def: IndicatorDef,
): Promise<{ name: string }> {
  return post<{ name: string }>(info, "/indicators/defs", def);
}

export function listIndicatorDefs(info: EngineInfo): Promise<IndicatorDef[]> {
  return get<IndicatorDef[]>(info, "/indicators/defs");
}

export async function deleteIndicatorDef(info: EngineInfo, name: string): Promise<void> {
  const res = await fetch(`${base(info)}/indicators/defs/${encodeURIComponent(name)}`, {
    method: "DELETE",
    headers: headers(info),
  });
  if (!res.ok) throw new Error(`delete failed: HTTP ${res.status}`);
}

/** null = AI เห็นว่าไม่มี setup ตอนนี้ */
export async function postAnalyze(
  info: EngineInfo,
  req: AnalyzeRequest,
): Promise<Signal | null> {
  const res = await fetch(`${base(info)}/analyze`, {
    method: "POST",
    headers: { ...headers(info), "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* keep http status */
    }
    throw new Error(detail);
  }
  return (await res.json()) as Signal | null;
}
