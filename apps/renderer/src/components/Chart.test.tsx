import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeWebSocket } from "../test/mocks";

const { series } = vi.hoisted(() => ({
  series: { setData: vi.fn(), update: vi.fn() },
}));

vi.mock("lightweight-charts", () => {
  const chart = {
    addSeries: vi.fn(() => series),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    remove: vi.fn(),
  };
  return { createChart: vi.fn(() => chart), CandlestickSeries: Symbol("cs") };
});

import Chart from "./Chart";

const info = { port: 8123, token: "tok" };
const candle = {
  symbol: "BTC/USDT", tf: "15m" as const, ts: 1_700_000_100_000,
  o: 1, h: 2, l: 0.5, c: 1.5, v: 10,
};

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeWebSocket);
  FakeWebSocket.instances = [];
  series.setData.mockClear();
  series.update.mockClear();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve([candle]) }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Chart", () => {
  it("loads history into the candlestick series", async () => {
    render(<Chart info={info} symbol="BTC/USDT" tf="15m" />);
    await waitFor(() => {
      expect(series.setData).toHaveBeenCalledWith([
        { time: candle.ts / 1000, open: 1, high: 2, low: 0.5, close: 1.5 },
      ]);
    });
  });

  it("applies realtime candle.update to the series", async () => {
    render(<Chart info={info} symbol="BTC/USDT" tf="15m" />);
    await waitFor(() => expect(FakeWebSocket.instances.length).toBe(1));
    const ws = FakeWebSocket.instances[0];
    ws.open();
    ws.push({
      type: "candle.update",
      ts: Date.now(),
      payload: { ...candle, c: 1.9 },
    });
    expect(series.update).toHaveBeenCalledWith(
      expect.objectContaining({ close: 1.9 }),
    );
  });

  it("ignores updates for a different symbol", async () => {
    render(<Chart info={info} symbol="BTC/USDT" tf="15m" />);
    await waitFor(() => expect(FakeWebSocket.instances.length).toBe(1));
    const ws = FakeWebSocket.instances[0];
    ws.open();
    ws.push({
      type: "candle.update",
      ts: Date.now(),
      payload: { ...candle, symbol: "ETH/USDT" },
    });
    expect(series.update).not.toHaveBeenCalled();
  });
});
