import type { EngineInfo, HealthResponse } from "@aiview/shared-types";

export async function getEngineInfo(): Promise<EngineInfo | null> {
  if (!window.aiview) return null;
  return window.aiview.engineInfo();
}

export async function fetchHealth(info: EngineInfo): Promise<HealthResponse> {
  const res = await fetch(`http://127.0.0.1:${info.port}/health`, {
    headers: { "X-Engine-Token": info.token },
  });
  if (!res.ok) throw new Error(`health check failed: HTTP ${res.status}`);
  return (await res.json()) as HealthResponse;
}
