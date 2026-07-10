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

export type Side = "long" | "short";

/** FEATURES.md §F1 — signal schema (mirror of engine app/models.py Signal) */
export interface Signal {
  id: string;
  symbol: string;
  tf: Timeframe;
  side: Side;
  entry: number;
  sl: number;
  tp: number[];
  rr: number;
  confidence: number;
  reason: string;
  indicators_used: Record<string, string>;
  model: string;
  position_size_hint: string | null;
  leverage_hint: string | null;
  created_at: number;
  valid_until: number | null;
}

/** POST /analyze body */
export interface AnalyzeRequest {
  symbol: string;
  tfs: Timeframe[];
  provider: string;
  model: string;
}

export interface IndicatorMarker {
  ts: number;
  kind: string;
  price: number;
  price2: number | null;
  label: string | null;
}

/** GET /indicators element */
export interface IndicatorResult {
  name: string;
  lines: Record<string, (number | null)[]>;
  markers: IndicatorMarker[];
}

export type TradeStatus = "open" | "win" | "loss" | "be" | "timeout";

/** ARCHITECTURE.md §5 Trade schema (mirror of engine Trade) */
export interface Trade {
  id: string;
  signal_id: string;
  symbol: string;
  tf: Timeframe;
  side: Side;
  entry: number;
  exit: number | null;
  sl: number;
  tp: number;
  qty: number;
  pnl: number | null;
  r_multiple: number | null;
  status: TradeStatus;
  model: string;
  opened_at: number;
  closed_at: number | null;
}

export interface SimConfig {
  initial_capital: number;
  risk_per_trade_pct: number;
  fee_pct: number;
  slippage_pct: number;
  timeout_bars: number;
}

export interface EquityPoint {
  ts: number;
  equity: number;
}

export interface StatsBreakdownRow {
  key: string;
  trades: number;
  winrate: number;
  avg_r: number;
  pnl: number;
}

/** ARCHITECTURE.md §5 Stats schema */
export interface Stats {
  scope: string;
  trades: number;
  wins: number;
  losses: number;
  winrate: number;
  avg_r: number;
  expectancy: number;
  profit_factor: number;
  max_drawdown_pct: number;
  total_pnl: number;
  equity_curve: EquityPoint[];
  by_symbol: StatsBreakdownRow[];
  by_tf: StatsBreakdownRow[];
  by_model: StatsBreakdownRow[];
  by_side: StatsBreakdownRow[];
}

export interface BacktestRequest {
  symbol: string;
  tf: Timeframe;
  limit: number;
  strategy: string;
  config?: Partial<SimConfig>;
}

export interface BacktestRun {
  run_id: string;
  status: "running" | "done" | "error";
  progress: number;
  detail: string | null;
  trades: Trade[] | null;
  stats: Stats | null;
}

/** Engine lifecycle status pushed from Electron main to renderer */
export type EngineStatus =
  | { state: "starting" }
  | { state: "ready"; info: EngineInfo }
  | { state: "crashed"; restarts: number }
  | { state: "failed" };
