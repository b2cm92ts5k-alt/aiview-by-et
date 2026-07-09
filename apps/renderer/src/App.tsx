import type { SymbolInfo } from "@aiview/shared-types";
import { useEffect, useState } from "react";
import { fetchMarkets, getEngineInfo } from "./api/engine";
import Chart from "./components/Chart";
import HealthBadge from "./components/HealthBadge";
import SymbolSearch from "./components/SymbolSearch";
import TimeframeSelector from "./components/TimeframeSelector";
import Watchlist from "./components/Watchlist";
import { useAppStore } from "./store/app";

// left toolbar: M1 placeholder — drawing tools มาเฟสหลัง (FEATURES §F5)
const TOOLBAR_ICONS = ["✛", "─", "▭", "⟋", "𝑓", "⚙"];

export default function App() {
  const { engineInfo, symbol, tf, setEngineInfo, setSymbol, setTf } = useAppStore();
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);

  useEffect(() => {
    let cancelled = false;
    const acquire = async () => {
      const info = await getEngineInfo();
      if (!cancelled) setEngineInfo(info);
    };
    void acquire();
    const off = window.aiview?.onEngineStatus((status) => {
      if (status.state === "ready") setEngineInfo(status.info);
      if (status.state === "failed") setEngineInfo(null);
    });
    return () => {
      cancelled = true;
      off?.();
    };
  }, [setEngineInfo]);

  useEffect(() => {
    if (!engineInfo) return;
    let cancelled = false;
    fetchMarkets(engineInfo)
      .then((m) => {
        if (!cancelled) setSymbols(m.symbols);
      })
      .catch(() => {
        /* markets ล้มเหลวไม่บล็อก chart — HealthBadge จะฟ้องปัญหา engine อยู่แล้ว */
      });
    return () => {
      cancelled = true;
    };
  }, [engineInfo]);

  return (
    <div className="flex h-screen flex-col bg-[#0b0e14] text-slate-100">
      {/* top bar */}
      <header className="flex items-center gap-4 border-b border-slate-800 px-3 py-2">
        <div className="text-sm font-bold tracking-wide text-cyan-400">
          AIView <span className="font-normal text-slate-500">by ET</span>
        </div>
        <SymbolSearch symbols={symbols} value={symbol} onSelect={setSymbol} />
        <TimeframeSelector value={tf} onChange={setTf} />
        <div className="ml-auto flex items-center gap-4">
          <span className="text-sm font-semibold text-slate-200">{symbol}</span>
          <HealthBadge info={engineInfo} />
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* left toolbar (placeholder M1) */}
        <aside className="flex w-11 flex-col items-center gap-1 border-r border-slate-800 py-2">
          {TOOLBAR_ICONS.map((icon, i) => (
            <button
              key={i}
              className="flex h-8 w-8 items-center justify-center rounded text-sm text-slate-500 hover:bg-slate-800 hover:text-slate-200"
              title="เครื่องมือ (เฟสถัดไป)"
            >
              {icon}
            </button>
          ))}
        </aside>

        {/* chart */}
        <main className="min-w-0 flex-1">
          <Chart info={engineInfo} symbol={symbol} tf={tf} />
        </main>

        {/* right panel */}
        <aside className="w-60 border-l border-slate-800">
          <Watchlist symbols={symbols} active={symbol} onSelect={setSymbol} />
        </aside>
      </div>
    </div>
  );
}
