import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("lightweight-charts", () => {
  const series = { setData: vi.fn(), update: vi.fn() };
  const chart = {
    addSeries: vi.fn(() => series),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    remove: vi.fn(),
  };
  return {
    createChart: vi.fn(() => chart),
    CandlestickSeries: Symbol("cs"),
    LineSeries: Symbol("ls"),
  };
});

import Dashboard from "./Dashboard";

const info = { port: 8123, token: "tok" };

const stats = {
  scope: "backtest", trades: 3, wins: 2, losses: 1, winrate: 66.67,
  avg_r: 0.8, expectancy: 0.8, profit_factor: 2.1, max_drawdown_pct: 12.5,
  total_pnl: 350.5,
  equity_curve: [{ ts: 1000, equity: 10100 }, { ts: 2000, equity: 10350.5 }],
  by_symbol: [], by_tf: [],
  by_model: [{ key: "rule:zlema-smc", trades: 3, winrate: 66.67, avg_r: 0.8, pnl: 350.5 }],
  by_side: [],
};

const trades = [{
  id: "t1", signal_id: "s1", symbol: "BTC/USDT", tf: "15m", side: "long",
  entry: 100, exit: 110, sl: 95, tp: 110, qty: 20, pnl: 200, r_multiple: 2,
  status: "win", model: "rule:zlema-smc", opened_at: 1_700_000_000_000,
  closed_at: 1_700_000_900_000,
}];

function stubFetch(runStatus = "done") {
  return vi.fn((url: string, init?: RequestInit) => {
    const path = new URL(url).pathname;
    let body: unknown = [];
    if (path === "/stats") body = stats;
    else if (path === "/trades") body = trades;
    else if (path === "/sim/backtest") {
      expect(init?.method).toBe("POST");
      body = { run_id: "r1" };
    } else if (path.startsWith("/sim/runs/")) {
      body = { run_id: "r1", status: runStatus, progress: 1, detail: null,
               trades: null, stats: null };
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
  });
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("Dashboard", () => {
  it("loads stats cards and history table", async () => {
    vi.stubGlobal("fetch", stubFetch());
    render(<Dashboard info={info} symbol="BTC/USDT" tf="15m" />);
    await waitFor(() => {
      expect(screen.getByTestId("stats-cards")).toHaveTextContent("66.7%");
    });
    expect(screen.getByTestId("stats-cards")).toHaveTextContent("350.50");
    expect(screen.getByTestId("history-table")).toHaveTextContent("BTC/USDT");
    expect(screen.getByTestId("history-table")).toHaveTextContent("win");
    expect(screen.getByTestId("dashboard")).toHaveTextContent("rule:zlema-smc");
  });

  it("run backtest posts request and reloads when done", async () => {
    const fetchMock = stubFetch("done");
    vi.stubGlobal("fetch", fetchMock);
    render(<Dashboard info={info} symbol="BTC/USDT" tf="15m" />);
    await waitFor(() => screen.getByRole("button", { name: "รัน Backtest" }));

    fireEvent.click(screen.getByRole("button", { name: "รัน Backtest" }));
    await waitFor(() => {
      const paths = fetchMock.mock.calls.map((c) => new URL(c[0] as string).pathname);
      expect(paths).toContain("/sim/backtest");
      expect(paths.some((p) => p.startsWith("/sim/runs/"))).toBe(true);
    });
  });

  it("renders equity curve container when stats have points", async () => {
    vi.stubGlobal("fetch", stubFetch());
    render(<Dashboard info={info} symbol="BTC/USDT" tf="15m" />);
    await waitFor(() => {
      expect(screen.getByTestId("equity-curve")).toBeInTheDocument();
    });
  });
});
