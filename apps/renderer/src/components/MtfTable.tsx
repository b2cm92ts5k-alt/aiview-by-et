import type { EngineInfo, Timeframe } from "@aiview/shared-types";
import { useEffect, useState } from "react";
import { fetchIndicators } from "../api/engine";

// FEATURES.md §F3 — ตาราง confluence 5/15/60/240(4h)/1D ตามภาพต้นแบบ
const MTF_TFS: Timeframe[] = ["5m", "15m", "60m", "4h", "1D"];

type Row = { tf: Timeframe; trend: 1 | 0 | -1 | null; rsi: number | null };

export default function MtfTable({
  info,
  symbol,
}: {
  info: EngineInfo | null;
  symbol: string;
}) {
  const [rows, setRows] = useState<Row[]>(MTF_TFS.map((tf) => ({ tf, trend: null, rsi: null })));

  useEffect(() => {
    if (!info) return;
    let cancelled = false;
    setRows(MTF_TFS.map((tf) => ({ tf, trend: null, rsi: null })));
    for (const tf of MTF_TFS) {
      fetchIndicators(info, symbol, tf, "core", 120)
        .then((results) => {
          if (cancelled) return;
          const zl = results.find((r) => r.name === "zero_lag");
          const rsi = results.find((r) => r.name === "rsi");
          const trendVals = zl?.lines["trend"] ?? [];
          const rsiVals = rsi?.lines["rsi14"] ?? [];
          const trend = (trendVals[trendVals.length - 1] ?? null) as 1 | 0 | -1 | null;
          const rsiLast = rsiVals[rsiVals.length - 1] ?? null;
          setRows((prev) =>
            prev.map((row) => (row.tf === tf ? { tf, trend, rsi: rsiLast } : row)),
          );
        })
        .catch(() => {
          /* แถวนั้นคงสถานะ "—" — engine ปัญหาใหญ่จะโชว์ที่ HealthBadge */
        });
    }
    return () => {
      cancelled = true;
    };
  }, [info, symbol]);

  return (
    <div className="border-b border-slate-800 p-3" data-testid="mtf-table">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        MTF Confluence
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-500">
            <th className="pb-1 text-left font-medium">TF</th>
            <th className="pb-1 text-left font-medium">Trend</th>
            <th className="pb-1 text-right font-medium">RSI14</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ tf, trend, rsi }) => (
            <tr key={tf} className="border-t border-slate-800/60">
              <td className="py-1 text-slate-300">{tf}</td>
              <td className="py-1">
                {trend === 1 && <span className="text-emerald-400">▲ Bullish</span>}
                {trend === -1 && <span className="text-rose-400">▼ Bearish</span>}
                {trend === 0 && <span className="text-slate-400">— Neutral</span>}
                {trend === null && <span className="text-slate-600">…</span>}
              </td>
              <td className="py-1 text-right text-slate-300">
                {rsi === null ? "…" : rsi.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
