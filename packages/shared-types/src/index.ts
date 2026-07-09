/**
 * Shared FE/BE contract types.
 *
 * M0: hand-written to mirror the pydantic models in engine/app.
 * Later milestones generate these from the engine's OpenAPI schema
 * (openapi-typescript) per TDD.md §3 — keep this file the single import point.
 */

/** GET /health */
export interface HealthResponse {
  status: "ok";
  version: string;
}

/** Handed from Electron main to renderer via IPC `engine:info` */
export interface EngineInfo {
  port: number;
  token: string;
}

/** Every WebSocket message uses this envelope (TDD.md §3.3) */
export interface WsEnvelope<T = unknown> {
  type: string;
  ts: number;
  payload: T;
}

/** ARCHITECTURE.md §6 — 11 supported timeframes */
export type Timeframe =
  | "5m" | "10m" | "15m" | "30m" | "45m" | "60m"
  | "4h" | "1D" | "1W" | "1M" | "1Y";

export const TIMEFRAMES: readonly Timeframe[] = [
  "5m", "10m", "15m", "30m", "45m", "60m", "4h", "1D", "1W", "1M", "1Y",
] as const;

export type AssetClass = "crypto" | "stock" | "gold" | "oil" | "fx";

/** ARCHITECTURE.md §5 — central candle schema (ts = bar open, UTC ms) */
export interface Candle {
  symbol: string;
  tf: Timeframe;
  ts: number;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

export interface SymbolInfo {
  symbol: string;
  name: string | null;
  asset_class: AssetClass;
  provider: string;
}

/** GET /markets */
export interface MarketsResponse {
  asset_classes: AssetClass[];
  symbols: SymbolInfo[];
}

/** Engine lifecycle status pushed from Electron main to renderer */
export type EngineStatus =
  | { state: "starting" }
  | { state: "ready"; info: EngineInfo }
  | { state: "crashed"; restarts: number }
  | { state: "failed" };
