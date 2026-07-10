import type {
  EngineInfo,
  Stats,
  StatsBreakdownRow,
  Timeframe,
  Trade,
} from "@aiview/shared-types";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchRun, fetchStats, fetchTrades, postBacktest } from "../api/engine";
import { downloadText, tradesToCsv } from "../utils/csv";
import EquityCurve from "./EquityCurve";

type Scope = "backtest" | "paper";

const POLL_MS = 500;

function StatCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className={`text-lg font-semibold ${accent ?? "text-slate-100"}`}>{value}</div>
    </div>
  );
}

function BreakdownTable({ title, rows }: { title: string; rows: StatsBreakdownRow[] }) {
  if (rows.length === 0) return null;
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-500">
            <th className="pb-1 text-left font-medium">Key</th>
            <th className="pb-1 text-right font-medium">ไม้</th>
            <th className="pb-1 text-right font-medium">Winrate</th>
            <th className="pb-1 text-right font-medium">Avg R</th>
            <th className="pb-1 text-right font-medium">PnL</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-t border-slate-800/60">
              <td className="py-1 text-slate-300">{r.key}</td>
              <td className="py-1 text-right text-slate-300">{r.trades}</td>
              <td className="py-1 text-right text-slate-300">{r.winrate.toFixed(1)}%</td>
              <td className="py-1 text-right text-slate-300">{r.avg_r.toFixed(2)}</td>
              <td className={`py-1 text-right ${r.pnl >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                {r.pnl.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const STATUS_COLOR: Record<string, string> = {
  win: "text-emerald-300",
  loss: "text-rose-300",
  be: "text-slate-400",
  timeout: "text-amber-300",
  open: "text-cyan-300",
};

export default function Dashboard({
  info,
  symbol,
  tf,
}: {
  info: EngineInfo | null;
  symbol: string;
  tf: Timeframe;
}) {
  const [scope, setScope] = useState<Scope>("backtest");
  const [stats, setStats] = useState<Stats | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bars, setBars] = useState(1000);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const reload = useCallback(async () => {
    if (!info) return;
    try {
      const [s, t] = await Promise.all([fetchStats(info, scope), fetchTrades(info, scope)]);
      setStats(s);
      setTrades(t);
    } catch (e) {
      setError(String(e));
    }
  }, [info, scope]);

  useEffect(() => {
    void reload();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [reload]);

  const runBacktest = async () => {
    if (!info) return;
    setRunning(true);
    setError(null);
    try {
      const { run_id } = await postBacktest(info, {
        symbol, tf, limit: bars, strategy: "zlema-smc",
      });
      pollRef.current = setInterval(async () => {
        const run = await fetchRun(info, run_id);
        if (run.status !== "running") {
          if (pollRef.current) clearInterval(pollRef.current);
          setRunning(false);
          if (run.status === "error") setError(run.detail ?? "backtest error");
          await reload();
        }
      }, POLL_MS);
    } catch (e) {
      setRunning(false);
      setError(String(e));
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4" data-testid="dashboard">
      {/* controls */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex rounded border border-slate-700 text-xs">
          {(["backtest", "paper"] as Scope[]).map((s) => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={`px-3 py-1.5 ${
                scope === s ? "bg-cyan-500/20 text-cyan-300" : "text-slate-400 hover:bg-slate-800"
              }`}
            >
              {s === "backtest" ? "Backtest" : "Paper (live)"}
            </button>
          ))}
        </div>
        {scope === "backtest" && (
          <>
            <span className="text-xs text-slate-500">
              {symbol} · {tf} · ย้อนหลัง
            </span>
            <input
              type="number"
              value={bars}
              min={100}
              max={5000}
              onChange={(e) => setBars(Number(e.target.value))}
              className="w-20 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
            />
            <span className="text-xs text-slate-500">แท่ง (rule: zlema-smc)</span>
            <button
              onClick={runBacktest}
              disabled={!info || running}
              className="rounded bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-40"
            >
              {running ? "กำลังรัน…" : "รัน Backtest"}
            </button>
          </>
        )}
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => downloadText("trades.csv", "text/csv", tradesToCsv(trades))}
            disabled={trades.length === 0}
            className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-40"
          >
            Export CSV
          </button>
          <button
            onClick={() =>
              downloadText("trades.json", "application/json", JSON.stringify(trades, null, 2))
            }
            disabled={trades.length === 0}
            className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-40"
          >
            Export JSON
          </button>
        </div>
      </div>

      {error && <p className="mb-3 text-xs text-rose-300">เกิดข้อผิดพลาด — {error}</p>}

      {/* stats cards */}
      {stats && (
        <div className="mb-4 grid grid-cols-3 gap-2 lg:grid-cols-6" data-testid="stats-cards">
          <StatCard label="ไม้ทั้งหมด" value={String(stats.trades)} />
          <StatCard
            label="Winrate"
            value={`${stats.winrate.toFixed(1)}%`}
            accent={stats.winrate >= 50 ? "text-emerald-300" : "text-rose-300"}
          />
          <StatCard label="Avg R / Expectancy" value={stats.avg_r.toFixed(2)} />
          <StatCard label="Profit Factor" value={stats.profit_factor.toFixed(2)} />
          <StatCard label="Max Drawdown" value={`${stats.max_drawdown_pct.toFixed(1)}%`} />
          <StatCard
            label="PnL รวม"
            value={stats.total_pnl.toFixed(2)}
            accent={stats.total_pnl >= 0 ? "text-emerald-300" : "text-rose-300"}
          />
        </div>
      )}

      {/* equity curve */}
      {stats && stats.equity_curve.length > 0 && (
        <div className="mb-4 rounded-lg border border-slate-800 p-2">
          <div className="mb-1 px-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Equity Curve
          </div>
          <EquityCurve points={stats.equity_curve} />
        </div>
      )}

      {/* breakdowns */}
      {stats && (
        <div className="mb-4 grid gap-4 lg:grid-cols-3">
          <BreakdownTable title="ตาม Model" rows={stats.by_model} />
          <BreakdownTable title="ตาม Timeframe" rows={stats.by_tf} />
          <BreakdownTable title="ตาม Side" rows={stats.by_side} />
        </div>
      )}

      {/* history */}
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
        History ({trades.length} ไม้)
      </div>
      <table className="w-full text-xs" data-testid="history-table">
        <thead>
          <tr className="text-slate-500">
            <th className="pb-1 text-left font-medium">เวลาเข้า</th>
            <th className="pb-1 text-left font-medium">Symbol</th>
            <th className="pb-1 text-left font-medium">TF</th>
            <th className="pb-1 text-left font-medium">Side</th>
            <th className="pb-1 text-right font-medium">Entry</th>
            <th className="pb-1 text-right font-medium">Exit</th>
            <th className="pb-1 text-right font-medium">R</th>
            <th className="pb-1 text-right font-medium">PnL</th>
            <th className="pb-1 text-left font-medium">ผล</th>
            <th className="pb-1 text-left font-medium">Model</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-t border-slate-800/60">
              <td className="py-1 text-slate-400">
                {new Date(t.opened_at).toLocaleString("th-TH", { hour12: false })}
              </td>
              <td className="py-1 text-slate-300">{t.symbol}</td>
              <td className="py-1 text-slate-300">{t.tf}</td>
              <td className={`py-1 ${t.side === "long" ? "text-emerald-300" : "text-rose-300"}`}>
                {t.side}
              </td>
              <td className="py-1 text-right text-slate-300">{t.entry.toFixed(2)}</td>
              <td className="py-1 text-right text-slate-300">{t.exit?.toFixed(2) ?? "—"}</td>
              <td className="py-1 text-right text-slate-300">
                {t.r_multiple?.toFixed(2) ?? "—"}
              </td>
              <td
                className={`py-1 text-right ${
                  (t.pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300"
                }`}
              >
                {t.pnl?.toFixed(2) ?? "—"}
              </td>
              <td className={`py-1 ${STATUS_COLOR[t.status]}`}>{t.status}</td>
              <td className="py-1 text-slate-500">{t.model}</td>
            </tr>
          ))}
          {trades.length === 0 && (
            <tr>
              <td colSpan={10} className="py-4 text-center text-slate-600">
                ยังไม่มีไม้ใน scope นี้ — รัน backtest หรือปล่อยให้ AI เปิดไม้จำลองจากหน้า Chart
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
