import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SignalPanel from "./SignalPanel";

const info = { port: 8123, token: "tok" };

const signal = {
  id: "sig-1",
  symbol: "BTC/USDT",
  tf: "15m",
  side: "long",
  entry: 63000,
  sl: 62000,
  tp: [64000, 65000],
  rr: 1.0,
  confidence: 70,
  reason: "zlema trend up",
  indicators_used: { zero_lag: "up" },
  model: "llama3.1:8b",
  position_size_hint: null,
  leverage_hint: null,
  created_at: 1,
  valid_until: null,
};

function stubFetch(analyzeBody: unknown, analyzeOk = true) {
  return vi.fn((url: string, init?: RequestInit) => {
    const path = new URL(url).pathname;
    if (path === "/ai/models") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ollama: ["llama3.1:8b"] }),
      });
    }
    if (path === "/analyze") {
      expect(init?.method).toBe("POST");
      return Promise.resolve({
        ok: analyzeOk,
        status: analyzeOk ? 200 : 502,
        json: () => Promise.resolve(analyzeBody),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });
}

beforeEach(() => {
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SignalPanel", () => {
  it("loads models and shows them in the selector", async () => {
    vi.stubGlobal("fetch", stubFetch(signal));
    render(<SignalPanel info={info} symbol="BTC/USDT" tf="15m" onSignal={() => {}} />);
    await waitFor(() => {
      expect(screen.getByTestId("model-select")).toHaveTextContent("ollama · llama3.1:8b");
    });
  });

  it("analyze shows the signal card and notifies parent", async () => {
    vi.stubGlobal("fetch", stubFetch(signal));
    const onSignal = vi.fn();
    render(<SignalPanel info={info} symbol="BTC/USDT" tf="15m" onSignal={onSignal} />);
    await waitFor(() => expect(screen.getByTestId("model-select")).toHaveTextContent("llama3.1"));

    fireEvent.click(screen.getByRole("button", { name: "วิเคราะห์" }));
    await waitFor(() => {
      expect(screen.getByTestId("signal-result")).toHaveTextContent("LONG");
    });
    expect(screen.getByTestId("signal-result")).toHaveTextContent("63000");
    expect(onSignal).toHaveBeenLastCalledWith(expect.objectContaining({ id: "sig-1" }));
  });

  it("shows no-setup state when analyze returns null", async () => {
    vi.stubGlobal("fetch", stubFetch(null));
    render(<SignalPanel info={info} symbol="BTC/USDT" tf="15m" onSignal={() => {}} />);
    await waitFor(() => expect(screen.getByTestId("model-select")).toHaveTextContent("llama3.1"));

    fireEvent.click(screen.getByRole("button", { name: "วิเคราะห์" }));
    await waitFor(() => {
      expect(screen.getByTestId("signal-result")).toHaveTextContent("ไม่เห็น setup");
    });
  });

  it("copy button writes signal text with disclaimer to clipboard", async () => {
    vi.stubGlobal("fetch", stubFetch(signal));
    render(<SignalPanel info={info} symbol="BTC/USDT" tf="15m" onSignal={() => {}} />);
    await waitFor(() => expect(screen.getByTestId("model-select")).toHaveTextContent("llama3.1"));
    fireEvent.click(screen.getByRole("button", { name: "วิเคราะห์" }));
    await waitFor(() => screen.getByRole("button", { name: "Copy" }));

    fireEvent.click(screen.getByRole("button", { name: "Copy" }));
    await waitFor(() => {
      const written = vi.mocked(navigator.clipboard.writeText).mock.calls[0][0];
      expect(written).toContain("BTC/USDT 15m — LONG");
      expect(written).toContain("ไม่ใช่คำแนะนำการลงทุน");
    });
  });
});
