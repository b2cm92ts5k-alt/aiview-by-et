import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ModelsView from "./ModelsView";

const info = { port: 8123, token: "tok" };

const benchDone = {
  run_id: "b1", status: "done", progress: 1, detail: null,
  results: [{
    provider: "ollama", model: "qwen3:8b", signals: 3, no_setup: 1, errors: 0,
    stats: {
      scope: "benchmark:ollama:qwen3:8b", trades: 3, wins: 2, losses: 1,
      winrate: 66.7, avg_r: 0.5, expectancy: 0.5, profit_factor: 1.8,
      max_drawdown_pct: 5, total_pnl: 90, equity_curve: [],
      by_symbol: [], by_tf: [], by_model: [], by_side: [],
    },
  }],
};

function stubFetch() {
  return vi.fn((url: string, init?: RequestInit) => {
    const path = new URL(url).pathname;
    let body: unknown = {};
    if (path === "/ai/models") {
      body = { ollama: [{ id: "qwen3:8b", recommended: false },
                        { id: "qwen3:14b", recommended: true }] };
    } else if (path === "/benchmark") {
      expect(init?.method).toBe("POST");
      const req = JSON.parse(String(init?.body));
      expect(req.models).toEqual([{ provider: "ollama", model: "qwen3:8b" }]);
      body = { run_id: "b1" };
    } else if (path.startsWith("/benchmark/runs/")) {
      body = benchDone;
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  delete (window as { aiview?: unknown }).aiview;
});

describe("ModelsView", () => {
  it("shows local catalog with recommended tags and engine models", async () => {
    vi.stubGlobal("fetch", stubFetch());
    render(<ModelsView info={info} symbol="BTC/USDT" tf="15m" />);
    expect(screen.getByTestId("local-catalog")).toHaveTextContent("⭐ qwen3:14b");
    expect(screen.getByTestId("local-catalog")).toHaveTextContent("~12 GB VRAM");
    await waitFor(() => {
      expect(screen.getByTestId("bench-models")).toHaveTextContent("ollama·qwen3:8b");
    });
  });

  it("runs benchmark and shows result table", async () => {
    vi.stubGlobal("fetch", stubFetch());
    render(<ModelsView info={info} symbol="BTC/USDT" tf="15m" />);
    await waitFor(() => screen.getByText(/ollama·qwen3:8b/));

    fireEvent.click(screen.getByText(/ollama·qwen3:8b/));
    fireEvent.click(screen.getByRole("button", { name: "รัน Benchmark" }));
    await waitFor(() => {
      expect(screen.getByTestId("bench-results")).toHaveTextContent("66.7%");
    }, { timeout: 3000 });
    expect(screen.getByTestId("bench-results")).toHaveTextContent("1.80");
  });

  it("locks local models above available VRAM (bridge present)", async () => {
    (window as { aiview?: unknown }).aiview = {
      systemSpecs: vi.fn().mockResolvedValue({ ram_mb: 32768, vram_mb: 8192, gpu_name: "RTX 2060S" }),
      ollamaStatus: vi.fn().mockResolvedValue({
        installed: true, running: true, models: ["qwen3:8b"], downloadUrl: "x",
      }),
      vaultListProviders: vi.fn().mockResolvedValue([]),
      onOllamaProgress: vi.fn().mockReturnValue(() => {}),
    };
    vi.stubGlobal("fetch", stubFetch());
    render(<ModelsView info={info} symbol="BTC/USDT" tf="15m" />);
    await waitFor(() => {
      expect(screen.getByTestId("specs")).toHaveTextContent("RTX 2060S");
    });
    // 14b ต้องการ 12GB > 8GB → lock
    expect(screen.getByTestId("local-catalog")).toHaveTextContent("VRAM ไม่พอ (8/12 GB)");
  });
});
