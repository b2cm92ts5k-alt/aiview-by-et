import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

afterEach(() => {
  vi.unstubAllGlobals();
  delete (window as { aiview?: unknown }).aiview;
});

describe("App", () => {
  it("shows offline when no Electron bridge is available", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId("engine-status")).toHaveTextContent("Engine ออฟไลน์");
    });
  });

  it("shows engine online after successful health check", async () => {
    (window as { aiview?: unknown }).aiview = {
      engineInfo: vi.fn().mockResolvedValue({ port: 8123, token: "tok" }),
      onEngineStatus: vi.fn().mockReturnValue(() => {}),
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: "ok", version: "0.1.0" }),
      }),
    );

    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId("engine-status")).toHaveTextContent("Engine ทำงานปกติ · v0.1.0");
    });
  });
});
