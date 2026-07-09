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

/** Engine lifecycle status pushed from Electron main to renderer */
export type EngineStatus =
  | { state: "starting" }
  | { state: "ready"; info: EngineInfo }
  | { state: "crashed"; restarts: number }
  | { state: "failed" };
