import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchHealth, getEngineInfo } from "./engine";

const info = { port: 8123, token: "tok-1" };

afterEach(() => {
  vi.unstubAllGlobals();
  delete (window as { aiview?: unknown }).aiview;
});

describe("fetchHealth", () => {
  it("calls /health on the engine port with the session token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "ok", version: "0.1.0" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const health = await fetchHealth(info);

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8123/health", {
      headers: { "X-Engine-Token": "tok-1" },
    });
    expect(health).toEqual({ status: "ok", version: "0.1.0" });
  });

  it("throws on non-2xx response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));
    await expect(fetchHealth(info)).rejects.toThrow("HTTP 503");
  });
});

describe("getEngineInfo", () => {
  it("returns null without the Electron bridge", async () => {
    expect(await getEngineInfo()).toBeNull();
  });

  it("delegates to window.aiview when present", async () => {
    (window as { aiview?: unknown }).aiview = {
      engineInfo: vi.fn().mockResolvedValue(info),
    };
    expect(await getEngineInfo()).toEqual(info);
  });
});
