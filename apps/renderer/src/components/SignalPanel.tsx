import type { EngineInfo, Signal, Timeframe } from "@aiview/shared-types";
import { useEffect, useState } from "react";
import { fetchAiModels, postAnalyze } from "../api/engine";

type PanelState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "signal"; signal: Signal }
  | { kind: "no-setup" }
  | { kind: "error"; detail: string };

function signalToText(s: Signal): string {
  const tps = s.tp.map((t, i) => `TP${i + 1}: ${t}`).join(" · ");
  return [
    `${s.symbol} ${s.tf} — ${s.side.toUpperCase()}`,
    `Entry: ${s.entry} · SL: ${s.sl} · ${tps}`,
    `RR(TP1): ${s.rr} · Confidence: ${s.confidence}%`,
    `เหตุผล: ${s.reason}`,
    `Model: ${s.model}`,
    `⚠️ เพื่อการศึกษา ไม่ใช่คำแนะนำการลงทุน`,
  ].join("\n");
}

function settingsToText(s: Signal): string {
  return JSON.stringify(
    { symbol: s.symbol, tf: s.tf, indicators: s.indicators_used, model: s.model },
    null,
    2,
  );
}

export default function SignalPanel({
  info,
  symbol,
  tf,
  onSignal,
}: {
  info: EngineInfo | null;
  symbol: string;
  tf: Timeframe;
  onSignal: (signal: Signal | null) => void;
}) {
  const [models, setModels] = useState<
    { provider: string; model: string; recommended: boolean }[]
  >([]);
  const [selected, setSelected] = useState<string>("");
  const [state, setState] = useState<PanelState>({ kind: "idle" });
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!info) return;
    let cancelled = false;
    fetchAiModels(info)
      .then((byProvider) => {
        if (cancelled) return;
        const flat = Object.entries(byProvider).flatMap(([provider, list]) =>
          list.map((entry) => ({
            provider,
            model: entry.id,
            recommended: entry.recommended,
          })),
        );
        // เรียงตัวแนะนำขึ้นก่อน (F7)
        flat.sort((a, b) => Number(b.recommended) - Number(a.recommended));
        setModels(flat);
        if (flat.length > 0) setSelected(`${flat[0].provider}:${flat[0].model}`);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [info]);

  const analyze = async () => {
    if (!info || !selected) return;
    const [provider, ...rest] = selected.split(":");
    const model = rest.join(":");
    setState({ kind: "loading" });
    onSignal(null);
    try {
      const signal = await postAnalyze(info, { symbol, tfs: [tf, "60m", "4h"], provider, model });
      if (signal) {
        setState({ kind: "signal", signal });
        onSignal(signal);
      } else {
        setState({ kind: "no-setup" });
      }
    } catch (e) {
      setState({ kind: "error", detail: String(e) });
    }
  };

  const copy = async (label: string, text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <div className="border-b border-slate-800 p-3" data-testid="signal-panel">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        AI Signal
      </div>

      <div className="flex items-center gap-2">
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
          data-testid="model-select"
        >
          {models.length === 0 && <option value="">ไม่พบ model (เปิด Ollama ก่อน)</option>}
          {models.map(({ provider, model, recommended }) => (
            <option key={`${provider}:${model}`} value={`${provider}:${model}`}>
              {recommended ? "⭐ " : ""}{provider} · {model}
            </option>
          ))}
        </select>
        <button
          onClick={analyze}
          disabled={!info || !selected || state.kind === "loading"}
          className="rounded bg-cyan-600 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-40"
        >
          {state.kind === "loading" ? "กำลังวิเคราะห์…" : "วิเคราะห์"}
        </button>
      </div>

      <div className="mt-3 text-sm" data-testid="signal-result">
        {state.kind === "idle" && (
          <p className="text-xs text-slate-500">เลือก model แล้วกดวิเคราะห์เพื่อหา setup</p>
        )}
        {state.kind === "no-setup" && (
          <p className="text-xs text-amber-300">AI ไม่เห็น setup ที่สมเหตุสมผลตอนนี้</p>
        )}
        {state.kind === "error" && (
          <p className="text-xs text-rose-300">วิเคราะห์ไม่สำเร็จ — {state.detail}</p>
        )}
        {state.kind === "signal" && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span
                className={`rounded px-2 py-0.5 text-xs font-bold ${
                  state.signal.side === "long"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-rose-500/20 text-rose-300"
                }`}
              >
                {state.signal.side.toUpperCase()}
              </span>
              <span className="text-xs text-slate-400">
                มั่นใจ {state.signal.confidence}% · RR {state.signal.rr}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
              <span className="text-slate-500">Entry</span>
              <span className="text-right text-slate-200">{state.signal.entry}</span>
              <span className="text-slate-500">Stop Loss</span>
              <span className="text-right text-rose-300">{state.signal.sl}</span>
              {state.signal.tp.map((tp, i) => (
                <span key={i} className="contents">
                  <span className="text-slate-500">TP{i + 1}</span>
                  <span className="text-right text-emerald-300">{tp}</span>
                </span>
              ))}
            </div>
            <p className="text-xs leading-relaxed text-slate-400">{state.signal.reason}</p>
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => copy("signal", signalToText(state.signal))}
                className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
              >
                {copied === "signal" ? "คัดลอกแล้ว ✓" : "Copy"}
              </button>
              <button
                onClick={() => copy("settings", settingsToText(state.signal))}
                className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
              >
                {copied === "settings" ? "คัดลอกแล้ว ✓" : "Copy settings"}
              </button>
            </div>
            <p className="pt-1 text-[10px] text-slate-600">
              ⚠️ เครื่องมือวิเคราะห์เพื่อการศึกษา ไม่ใช่คำแนะนำการลงทุน
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
