import type {
  BenchmarkRun,
  EngineInfo,
  ModelEntry,
  OllamaStatus,
  PullProgress,
  SystemSpecs,
  Timeframe,
} from "@aiview/shared-types";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAiModels, fetchBenchmarkRun, postBenchmark } from "../api/engine";

// Local catalog ตาม docs/AI_MODELS.md §B (เคาะแล้ว 2026-07-10) — VRAM โดยประมาณ Q4
const LOCAL_CATALOG: { id: string; vramGb: number; recommended: boolean; note: string }[] = [
  { id: "qwen3:14b", vramGb: 12, recommended: true, note: "reasoning ตัวเลข/JSON ดีสุดกลุ่มกลาง" },
  { id: "qwen3:32b", vramGb: 24, recommended: true, note: "คุณภาพใกล้ cloud tier กลาง" },
  { id: "deepseek-r1:14b", vramGb: 12, recommended: true, note: "reasoning เข้ม" },
  { id: "deepseek-r1:7b", vramGb: 8, recommended: true, note: "reasoning เข้ม (เครื่องเบา)" },
  { id: "llama3.1:8b", vramGb: 8, recommended: false, note: "สมดุล, tooling ใหญ่" },
  { id: "qwen2.5:7b", vramGb: 8, recommended: false, note: "เบาสุด / MTF scan" },
];

const CLOUD_PROVIDERS = ["anthropic", "openai", "google", "openrouter", "github", "twelvedata"];

const BENCH_POLL_MS = 1000;

export default function ModelsView({
  info,
  symbol,
  tf,
}: {
  info: EngineInfo | null;
  symbol: string;
  tf: Timeframe;
}) {
  const [specs, setSpecs] = useState<SystemSpecs | null>(null);
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);
  const [pull, setPull] = useState<PullProgress | null>(null);
  const [keyed, setKeyed] = useState<string[]>([]);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [models, setModels] = useState<Record<string, ModelEntry[]>>({});
  const [benchSelected, setBenchSelected] = useState<Set<string>>(new Set());
  const [bench, setBench] = useState<BenchmarkRun | null>(null);
  const benchTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const reload = useCallback(async () => {
    if (window.aiview) {
      setSpecs(await window.aiview.systemSpecs());
      setOllama(await window.aiview.ollamaStatus());
      setKeyed(await window.aiview.vaultListProviders());
    }
    if (info) {
      try {
        setModels(await fetchAiModels(info));
      } catch {
        /* engine down — HealthBadge ฟ้อง */
      }
    }
  }, [info]);

  useEffect(() => {
    void reload();
    const off = window.aiview?.onOllamaProgress((p) => {
      setPull(p);
      if (p.status === "success") void reload();
    });
    return () => {
      off?.();
      if (benchTimer.current) clearInterval(benchTimer.current);
    };
  }, [reload]);

  const installedLocal = ollama?.models ?? [];

  const install = async (model: string) => {
    // single active local model (F7): ลบตัวเก่าก่อน pull ตัวใหม่
    const removeModel = installedLocal.length > 0 ? installedLocal[0] : null;
    setPull({ model, status: "เริ่มติดตั้ง…", percent: null });
    await window.aiview?.ollamaEnsure(model, removeModel);
  };

  const saveKey = async (provider: string) => {
    const key = keyInputs[provider]?.trim();
    if (!key || !window.aiview) return;
    await window.aiview.vaultSetKey(provider, key);
    setKeyInputs((prev) => ({ ...prev, [provider]: "" }));
    await reload();
  };

  const deleteKey = async (provider: string) => {
    await window.aiview?.vaultDeleteKey(provider);
    await reload();
  };

  const runBenchmark = async () => {
    if (!info || benchSelected.size === 0) return;
    const refs = [...benchSelected].map((k) => {
      const [provider, ...rest] = k.split(":");
      return { provider, model: rest.join(":") };
    });
    const { run_id } = await postBenchmark(info, { models: refs, symbol, tf });
    setBench({ run_id, status: "running", progress: 0, detail: null, results: [] });
    benchTimer.current = setInterval(async () => {
      const run = await fetchBenchmarkRun(info, run_id);
      setBench(run);
      if (run.status !== "running" && benchTimer.current) {
        clearInterval(benchTimer.current);
        benchTimer.current = null;
      }
    }, BENCH_POLL_MS);
  };

  const vramGb = specs?.vram_mb ? specs.vram_mb / 1024 : null;

  return (
    <div className="h-full space-y-6 overflow-y-auto p-4" data-testid="models-view">
      {/* specs */}
      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          เครื่องของคุณ
        </h2>
        <div className="text-sm text-slate-300" data-testid="specs">
          {specs ? (
            <>
              GPU: {specs.gpu_name ?? "ไม่พบ NVIDIA GPU"} · VRAM:{" "}
              {vramGb ? `${vramGb.toFixed(0)} GB` : "—"} · RAM:{" "}
              {(specs.ram_mb / 1024).toFixed(0)} GB
            </>
          ) : (
            <span className="text-slate-500">อ่าน specs ได้เฉพาะในแอพ Electron</span>
          )}
        </div>
      </section>

      {/* local models */}
      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Local (Ollama) — ติดตั้งได้ทีละรุ่น (single active)
        </h2>
        {ollama && !ollama.installed && (
          <p className="mb-2 text-xs text-amber-300">
            ยังไม่ได้ติดตั้ง Ollama —{" "}
            <button className="underline" onClick={() => window.aiview?.ollamaOpenDownload()}>
              ดาวน์โหลดที่ ollama.com
            </button>
          </p>
        )}
        <ul className="space-y-1.5" data-testid="local-catalog">
          {LOCAL_CATALOG.map((m) => {
            const locked = vramGb !== null && vramGb < m.vramGb;
            const installed = installedLocal.some((x) => x.startsWith(m.id.split(":")[0]) && x === m.id);
            return (
              <li
                key={m.id}
                className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs"
              >
                <div>
                  <span className="font-semibold text-slate-100">
                    {m.recommended ? "⭐ " : ""}{m.id}
                  </span>
                  <span className="ml-2 text-slate-500">
                    ต้องการ ~{m.vramGb} GB VRAM · {m.note}
                  </span>
                </div>
                {installed ? (
                  <span className="text-emerald-300">ติดตั้งแล้ว ✓</span>
                ) : locked ? (
                  <span className="text-slate-500" title={`ต้องการ ~${m.vramGb}GB, เครื่องมี ${vramGb?.toFixed(0)}GB`}>
                    🔒 VRAM ไม่พอ ({vramGb?.toFixed(0)}/{m.vramGb} GB)
                  </span>
                ) : (
                  <button
                    onClick={() => install(m.id)}
                    disabled={!ollama?.installed}
                    className="rounded bg-cyan-600 px-2 py-1 font-semibold text-white hover:bg-cyan-500 disabled:opacity-40"
                  >
                    ติดตั้ง
                  </button>
                )}
              </li>
            );
          })}
        </ul>
        {pull && pull.status !== "success" && (
          <div className="mt-2 text-xs text-slate-400" data-testid="pull-progress">
            {pull.model}: {pull.status}
            {pull.percent !== null && ` (${pull.percent}%)`}
            {pull.detail && <span className="text-rose-300"> — {pull.detail}</span>}
          </div>
        )}
      </section>

      {/* cloud keys */}
      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Cloud API Keys (BYOK — เก็บเข้ารหัสในเครื่อง ไม่ส่งขึ้น server ใด)
        </h2>
        <ul className="space-y-1.5" data-testid="cloud-keys">
          {CLOUD_PROVIDERS.map((provider) => {
            const has = keyed.includes(provider);
            const ready = provider in models;
            return (
              <li
                key={provider}
                className="flex items-center gap-2 rounded border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs"
              >
                <span className="w-24 font-semibold text-slate-100">{provider}</span>
                {has ? (
                  <>
                    <span className={ready || provider === "twelvedata" ? "text-emerald-300" : "text-amber-300"}>
                      มี key แล้ว ✓{ready && ` · ${models[provider].length} models`}
                    </span>
                    <button
                      onClick={() => deleteKey(provider)}
                      className="ml-auto rounded border border-slate-700 px-2 py-0.5 text-rose-300 hover:bg-slate-800"
                    >
                      ลบ key
                    </button>
                  </>
                ) : (
                  <>
                    <input
                      type="password"
                      placeholder="วาง API key…"
                      value={keyInputs[provider] ?? ""}
                      onChange={(e) =>
                        setKeyInputs((prev) => ({ ...prev, [provider]: e.target.value }))
                      }
                      className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200"
                    />
                    <button
                      onClick={() => saveKey(provider)}
                      disabled={!keyInputs[provider]?.trim() || !window.aiview}
                      className="rounded bg-cyan-600 px-2 py-1 font-semibold text-white hover:bg-cyan-500 disabled:opacity-40"
                    >
                      บันทึก
                    </button>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      {/* benchmark */}
      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Model Benchmark — เทียบ winrate บนข้อมูลชุดเดียวกัน ({symbol} {tf})
        </h2>
        <div className="mb-2 flex flex-wrap gap-2" data-testid="bench-models">
          {Object.entries(models).flatMap(([provider, list]) =>
            list.map((entry) => {
              const key = `${provider}:${entry.id}`;
              const checked = benchSelected.has(key);
              return (
                <label
                  key={key}
                  className={`flex cursor-pointer items-center gap-1 rounded border px-2 py-1 text-xs ${
                    checked ? "border-cyan-500 text-cyan-300" : "border-slate-700 text-slate-300"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() =>
                      setBenchSelected((prev) => {
                        const next = new Set(prev);
                        if (next.has(key)) next.delete(key);
                        else next.add(key);
                        return next;
                      })
                    }
                    className="accent-cyan-500"
                  />
                  {entry.recommended ? "⭐ " : ""}{provider}·{entry.id}
                </label>
              );
            }),
          )}
          {Object.keys(models).length === 0 && (
            <span className="text-xs text-slate-600">ยังไม่มี model พร้อมใช้</span>
          )}
        </div>
        <button
          onClick={runBenchmark}
          disabled={!info || benchSelected.size === 0 || bench?.status === "running"}
          className="rounded bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-40"
        >
          {bench?.status === "running"
            ? `กำลังรัน… ${(bench.progress * 100).toFixed(0)}%`
            : "รัน Benchmark"}
        </button>
        {bench?.status === "error" && (
          <p className="mt-2 text-xs text-rose-300">benchmark ล้มเหลว — {bench.detail}</p>
        )}
        {bench?.status === "done" && (
          <table className="mt-3 w-full text-xs" data-testid="bench-results">
            <thead>
              <tr className="text-slate-500">
                <th className="pb-1 text-left font-medium">Model</th>
                <th className="pb-1 text-right font-medium">Signals</th>
                <th className="pb-1 text-right font-medium">No-setup</th>
                <th className="pb-1 text-right font-medium">Winrate</th>
                <th className="pb-1 text-right font-medium">PF</th>
                <th className="pb-1 text-right font-medium">Avg R</th>
              </tr>
            </thead>
            <tbody>
              {bench.results.map((r) => (
                <tr key={`${r.provider}:${r.model}`} className="border-t border-slate-800/60">
                  <td className="py-1 text-slate-200">{r.provider}·{r.model}</td>
                  <td className="py-1 text-right text-slate-300">{r.signals}</td>
                  <td className="py-1 text-right text-slate-500">{r.no_setup}</td>
                  <td className="py-1 text-right text-slate-300">
                    {r.stats.winrate.toFixed(1)}%
                  </td>
                  <td className="py-1 text-right text-slate-300">
                    {r.stats.profit_factor.toFixed(2)}
                  </td>
                  <td className="py-1 text-right text-slate-300">{r.stats.avg_r.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
