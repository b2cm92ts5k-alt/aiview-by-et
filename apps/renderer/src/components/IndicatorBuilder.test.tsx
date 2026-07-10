import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAppStore } from "../store/app";
import IndicatorBuilder from "./IndicatorBuilder";

const info = { port: 8123, token: "tok" };

const definition = {
  name: "zl_cross",
  title: "ZLEMA Cross",
  description: "momentum shift",
  source: "Ehlers zero-lag EMA (public)",
  params: { fast: 9 },
  lines: { zl: "zlema(c, fast)" },
  long_when: "crossover(zl, sma(c, 30))",
  short_when: null,
};

const backtest = {
  scope: "backtest", trades: 12, wins: 7, losses: 5, winrate: 58.3,
  avg_r: 0.4, expectancy: 0.4, profit_factor: 1.6, max_drawdown_pct: 8.2,
  total_pnl: 120, equity_curve: [], by_symbol: [], by_tf: [], by_model: [], by_side: [],
};

function stubFetch(savedList: unknown[] = []) {
  return vi.fn((url: string, init?: RequestInit) => {
    const path = new URL(url).pathname;
    let body: unknown = [];
    if (path === "/ai/models") body = { ollama: [{ id: "qwen3:8b", recommended: false }] };
    else if (path === "/indicators/ai/generate") body = { definition, backtest };
    else if (path === "/indicators/defs" && init?.method === "POST") body = { name: "zl_cross" };
    else if (path === "/indicators/defs") body = savedList;
    return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
  });
}

beforeEach(() => {
  useAppStore.setState({ overlaySet: null, symbol: "BTC/USDT", tf: "15m" });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("IndicatorBuilder", () => {
  it("generates a definition and shows quick backtest", async () => {
    vi.stubGlobal("fetch", stubFetch());
    render(<IndicatorBuilder info={info} />);
    await waitFor(() => screen.getByText("ollama · qwen3:8b"));

    fireEvent.change(screen.getByTestId("describe-input"), {
      target: { value: "zlema ตัด sma" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() => {
      expect(screen.getByTestId("builder-result")).toHaveTextContent("ZLEMA Cross");
    });
    expect(screen.getByTestId("builder-result")).toHaveTextContent("zl = zlema(c, fast)");
    expect(screen.getByTestId("builder-result")).toHaveTextContent("winrate 58.3%");
  });

  it("save posts the definition and refreshes saved list", async () => {
    const fetchMock = stubFetch();
    vi.stubGlobal("fetch", fetchMock);
    render(<IndicatorBuilder info={info} />);
    await waitFor(() => screen.getByText("ollama · qwen3:8b"));
    fireEvent.change(screen.getByTestId("describe-input"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));
    await waitFor(() => screen.getByRole("button", { name: "บันทึก" }));

    fireEvent.click(screen.getByRole("button", { name: "บันทึก" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "บันทึกแล้ว ✓" })).toBeDisabled();
    });
    const posts = fetchMock.mock.calls.filter(
      (c) => (c[1] as RequestInit | undefined)?.method === "POST"
        && new URL(c[0] as string).pathname === "/indicators/defs",
    );
    expect(posts).toHaveLength(1);
  });

  it("overlay button toggles store overlaySet", async () => {
    vi.stubGlobal("fetch", stubFetch([definition]));
    render(<IndicatorBuilder info={info} />);
    await waitFor(() => screen.getByRole("button", { name: "Overlay บน Chart" }));

    fireEvent.click(screen.getByRole("button", { name: "Overlay บน Chart" }));
    expect(useAppStore.getState().overlaySet).toBe("zl_cross");

    fireEvent.click(screen.getByRole("button", { name: "Overlay อยู่ ✓" }));
    expect(useAppStore.getState().overlaySet).toBeNull();
  });
});
