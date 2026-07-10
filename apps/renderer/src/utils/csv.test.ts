import type { Trade } from "@aiview/shared-types";
import { describe, expect, it } from "vitest";
import { tradesToCsv } from "./csv";

const trade: Trade = {
  id: "t1",
  signal_id: "s1",
  symbol: "BTC/USDT",
  tf: "15m",
  side: "long",
  entry: 100,
  exit: 110,
  sl: 95,
  tp: 110,
  qty: 20,
  pnl: 200,
  r_multiple: 2,
  status: "win",
  model: "qwen3:8b",
  opened_at: 1000,
  closed_at: 2000,
};

describe("tradesToCsv", () => {
  it("produces header + one row per trade", () => {
    const csv = tradesToCsv([trade]);
    const lines = csv.split("\n");
    expect(lines).toHaveLength(2);
    expect(lines[0]).toContain("id,signal_id,symbol");
    expect(lines[1]).toContain("BTC/USDT");
    expect(lines[1]).toContain("win");
  });

  it("escapes commas and quotes", () => {
    const tricky = { ...trade, model: 'weird,"model"' };
    const csv = tradesToCsv([tricky]);
    expect(csv).toContain('"weird,""model"""');
  });

  it("empty exit/pnl become empty cells", () => {
    const open = { ...trade, exit: null, pnl: null, r_multiple: null, closed_at: null };
    const row = tradesToCsv([open]).split("\n")[1];
    expect(row.split(",")[6]).toBe(""); // exit column
  });
});
