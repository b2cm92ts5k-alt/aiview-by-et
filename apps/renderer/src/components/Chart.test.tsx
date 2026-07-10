import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeWebSocket } from "../test/mocks";

const { series } = vi.hoisted(() => ({
  series: {
    setData: vi.fn(),
    update: vi.fn(),
    createPriceLine: vi.fn((_opts: { price: number }) => ({})),
    removePriceLine: vi.fn(),
  },
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
  series.createPriceLine.mockClear();
  series.removePriceLine.mockClear();
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

  it("draws entry/SL/TP price lines for an active signal", async () => {
    const signal = {
      id: "s1", symbol: "BTC/USDT", tf: "15m" as const, side: "long" as const,
      entry: 1.2, sl: 0.9, tp: [1.5, 1.8], rr: 1, confidence: 60, reason: "",
      indicators_used: {}, model: "m", position_size_hint: null,
      leverage_hint: null, created_at: 1, valid_until: null,
    };
    render(<Chart info={info} symbol="BTC/USDT" tf="15m" signal={signal} />);
    await waitFor(() => {
      expect(series.createPriceLine).toHaveBeenCalledTimes(4); // entry + SL + TP1 + TP2
    });
    const prices = series.createPriceLine.mock.calls.map((c) => c[0].price);
    expect(prices).toEqual([1.2, 0.9, 1.5, 1.8]);
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
