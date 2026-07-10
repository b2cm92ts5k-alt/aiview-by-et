import type {
  EngineInfo,
  GenerateIndicatorResponse,
  IndicatorDef,
} from "@aiview/shared-types";
import { useCallback, useEffect, useState } from "react";
import {
  deleteIndicatorDef,
  fetchAiModels,
  generateIndicator,
  listIndicatorDefs,
  saveIndicatorDef,
} from "../api/engine";
import { useAppStore } from "../store/app";

type BuilderState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "result"; result: GenerateIndicatorResponse; saved: boolean }
  | { kind: "error"; detail: string };

export default function IndicatorBuilder({ info }: { info: EngineInfo | null }) {
  const { symbol, tf, overlaySet, setOverlaySet } = useAppStore();
  const [description, setDescription] = useState("");
  const [models, setModels] = useState<{ provider: string; model: string }[]>([]);
  const [selected, setSelected] = useState("");
  const [state, setState] = useState<BuilderState>({ kind: "idle" });
  const [saved, setSaved] = useState<IndicatorDef[]>([]);

  const reloadSaved = useCallback(async () => {
    if (!info) return;
    try {
      setSaved(await listIndicatorDefs(info));
    } catch {
      /* engine down — HealthBadge ฟ้องอยู่แล้ว */
    }
  }, [info]);

  useEffect(() => {
    if (!info) return;
    let cancelled = false;
    fetchAiModels(info)
      .then((byProvider) => {
        if (cancelled) return;
        const flat = Object.entries(byProvider).flatMap(([provider, list]) =>
          list.map((entry) => ({ provider, model: entry.id })),
        );
        setModels(flat);
        if (flat.length > 0) setSelected(`${flat[0].provider}:${flat[0].model}`);
      })
      .catch(() => {});
    void reloadSaved();
    return () => {
      cancelled = true;
    };
  }, [info, reloadSaved]);

  const generate = async () => {
    if (!info || !selected || !description.trim()) return;
    const [provider, ...rest] = selected.split(":");
    setState({ kind: "loading" });
    try {
      const result = await generateIndicator(info, {
        description, provider, model: rest.join(":"), symbol, tf,
      });
      setState({ kind: "result", result, saved: false });
    } catch (e) {
      setState({ kind: "error", detail: String(e) });
    }
  };

  const save = async () => {
    if (!info || state.kind !== "result") return;
    try {
      await saveIndicatorDef(info, state.result.definition);
      setState({ ...state, saved: true });
      await reloadSaved();
    } catch (e) {
      setState({ kind: "error", detail: String(e) });
    }
  };

  const remove = async (name: string) => {
    if (!info) return;
    await deleteIndicatorDef(info, name);
    if (overlaySet === name) setOverlaySet(null);
    await reloadSaved();
  };

  return (
    <div className="grid h-full grid-cols-2 gap-4 overflow-y-auto p-4" data-testid="indicator-builder">
      {/* left: describe + generate */}
      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          สร้าง Indicator ด้วย AI (F6)
        </div>
        <p className="mb-2 text-xs text-slate-500">
          อธิบาย methodology ที่ต้องการ (public methodology เท่านั้น — AI จะปฏิเสธ
          การ copy indicator ที่มีลิขสิทธิ์)
        </p>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="เช่น: เส้น zero-lag EMA 21 เทียบกับ SMA 50 แล้วให้สัญญาณ long เมื่อตัดขึ้นและ RSI ยังไม่ overbought…"
          className="h-32 w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-500"
          data-testid="describe-input"
        />
        <div className="mt-2 flex items-center gap-2">
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
          >
            {models.length === 0 && <option value="">ไม่พบ model (เปิด Ollama ก่อน)</option>}
            {models.map(({ provider, model }) => (
              <option key={`${provider}:${model}`} value={`${provider}:${model}`}>
                {provider} · {model}
              </option>
            ))}
          </select>
          <button
            onClick={generate}
            disabled={!info || !selected || !description.trim() || state.kind === "loading"}
            className="rounded bg-cyan-600 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-40"
          >
            {state.kind === "loading" ? "กำลังสร้าง…" : "Generate"}
          </button>
        </div>

        <div className="mt-3" data-testid="builder-result">
          {state.kind === "error" && (
            <p className="text-xs text-rose-300">ไม่สำเร็จ — {state.detail}</p>
          )}
          {state.kind === "result" && (
            <div className="rounded border border-slate-800 bg-slate-900/60 p-3 text-xs">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-semibold text-slate-100">
                  {state.result.definition.title}
                  <span className="ml-2 text-slate-500">({state.result.definition.name})</span>
                </span>
                <button
                  onClick={save}
                  disabled={state.saved}
                  className="rounded bg-emerald-600 px-2 py-1 font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
                >
                  {state.saved ? "บันทึกแล้ว ✓" : "บันทึก"}
                </button>
              </div>
              <p className="text-slate-400">{state.result.definition.description}</p>
              <p className="mt-1 text-slate-500">Source: {state.result.definition.source}</p>
              <div className="mt-2 space-y-0.5 font-mono text-[11px] text-cyan-200/80">
                {Object.entries(state.result.definition.lines).map(([name, expr]) => (
                  <div key={name}>
                    {name} = {expr}
                  </div>
                ))}
                {state.result.definition.long_when && (
                  <div className="text-emerald-300/80">
                    long: {state.result.definition.long_when}
                  </div>
                )}
                {state.result.definition.short_when && (
                  <div className="text-rose-300/80">
                    short: {state.result.definition.short_when}
                  </div>
                )}
              </div>
              {state.result.backtest && (
                <div className="mt-2 border-t border-slate-800 pt-2 text-slate-300">
                  Quick backtest ({symbol} {tf}): {state.result.backtest.trades} ไม้ · winrate{" "}
                  {state.result.backtest.winrate.toFixed(1)}% · PF{" "}
                  {state.result.backtest.profit_factor.toFixed(2)} · maxDD{" "}
                  {state.result.backtest.max_drawdown_pct.toFixed(1)}%
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* right: saved list */}
      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Indicator ที่บันทึกไว้
        </div>
        <ul className="space-y-2" data-testid="saved-list">
          {saved.map((d) => (
            <li key={d.name} className="rounded border border-slate-800 bg-slate-900/60 p-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-100">{d.title}</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setOverlaySet(overlaySet === d.name ? null : d.name)}
                    className={`rounded border px-2 py-0.5 ${
                      overlaySet === d.name
                        ? "border-cyan-500 text-cyan-300"
                        : "border-slate-700 text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    {overlaySet === d.name ? "Overlay อยู่ ✓" : "Overlay บน Chart"}
                  </button>
                  <button
                    onClick={() => remove(d.name)}
                    className="rounded border border-slate-700 px-2 py-0.5 text-rose-300 hover:bg-slate-800"
                  >
                    ลบ
                  </button>
                </div>
              </div>
              <p className="mt-1 text-slate-500">{d.source}</p>
            </li>
          ))}
          {saved.length === 0 && (
            <li className="text-xs text-slate-600">ยังไม่มี — generate แล้วกดบันทึก</li>
          )}
        </ul>
      </div>
    </div>
  );
}
