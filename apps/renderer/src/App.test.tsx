import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeWebSocket } from "./test/mocks";

vi.mock("lightweight-charts", () => {
  const series = { setData: vi.fn(), update: vi.fn() };
  const chart = {
    addSeries: vi.fn(() => series),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    remove: vi.fn(),
  };
  return { createChart: vi.fn(() => chart), CandlestickSeries: Symbol("cs") };
});

import App from "./App";
import { useAppStore } from "./store/app";

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeWebSocket);
  FakeWebSocket.instances = [];
  useAppStore.setState({ engineInfo: null, symbol: "BTC/USDT", tf: "15m" });
});

afterEach(() => {
  vi.unstubAllGlobals();
  delete (window as { aiview?: unknown }).aiview;
});

const health = { status: "ok", version: "0.1.1" };
const markets = {
  asset_classes: ["crypto"],
  symbols: [
    { symbol: "BTC/USDT", name: "BTC", asset_class: "crypto", provider: "binance" },
    { symbol: "ETH/USDT", name: "ETH", asset_class: "crypto", provider: "binance" },
  ],
};

function stubEngineFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      const path = new URL(url).pathname;
      const body =
        path === "/health" ? health
        : path === "/markets" ? markets
        : path === "/settings" ? { disclaimer_accepted: true }
        : path === "/ai/models" ? {}
        : [];
      return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
    }),
  );
}

function stubBridge() {
  (window as { aiview?: unknown }).aiview = {
    engineInfo: vi.fn().mockResolvedValue({ port: 8123, token: "tok" }),
    onEngineStatus: vi.fn().mockReturnValue(() => {}),
  };
}

describe("App", () => {
  it("shows offline when no Electron bridge is available", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId("engine-status")).toHaveTextContent("Engine ออฟไลน์");
    });
  });

  it("shows engine online and loads watchlist symbols", async () => {
    stubBridge();
    stubEngineFetch();

    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId("engine-status")).toHaveTextContent("Engine ทำงานปกติ · v0.1.1");
    });
    await waitFor(() => {
      expect(screen.getByTestId("watchlist")).toHaveTextContent("ETH/USDT");
    });
  });

  it("subscribes over WS for the active symbol/tf", async () => {
    stubBridge();
    stubEngineFetch();

    render(<App />);
    // 2 connections: chart stream + alerts hook (F8)
    await waitFor(() => expect(FakeWebSocket.instances.length).toBeGreaterThanOrEqual(1));
    for (const ws of FakeWebSocket.instances) ws.open();
    await waitFor(() => {
      const sent = FakeWebSocket.instances.flatMap((w) => w.sent).map((s) => JSON.parse(s));
      expect(sent).toContainEqual({
        type: "subscribe",
        payload: { symbol: "BTC/USDT", tf: "15m" },
      });
    });
    expect(FakeWebSocket.instances[0].url).toContain("token=tok");
  });
});
