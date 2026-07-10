import type { EngineInfo, Workspace } from "@aiview/shared-types";
import { useEffect, useState } from "react";
import { fetchSettings, putSettings } from "../api/engine";
import { useAppStore } from "../store/app";

/** F10 — save/restore workspace (symbol/tf/overlay) เก็บใน engine settings */
export default function WorkspaceBar({ info }: { info: EngineInfo | null }) {
  const { symbol, tf, overlaySet, setSymbol, setTf, setOverlaySet } = useAppStore();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [name, setName] = useState("");

  useEffect(() => {
    if (!info) return;
    let cancelled = false;
    fetchSettings(info)
      .then((s) => {
        if (!cancelled && Array.isArray(s["workspaces"])) {
          setWorkspaces(s["workspaces"] as Workspace[]);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [info]);

  const save = async () => {
    if (!info || !name.trim()) return;
    const ws: Workspace = { name: name.trim(), symbol, tf, overlaySet };
    const next = [...workspaces.filter((w) => w.name !== ws.name), ws];
    await putSettings(info, { workspaces: next });
    setWorkspaces(next);
    setName("");
  };

  const load = (wsName: string) => {
    const ws = workspaces.find((w) => w.name === wsName);
    if (!ws) return;
    setSymbol(ws.symbol);
    setTf(ws.tf);
    setOverlaySet(ws.overlaySet);
  };

  return (
    <div className="flex items-center gap-1" data-testid="workspace-bar">
      <select
        value=""
        onChange={(e) => load(e.target.value)}
        className="rounded border border-slate-700 bg-slate-900 px-1.5 py-1 text-xs text-slate-300"
        title="โหลด workspace"
      >
        <option value="">Workspace…</option>
        {workspaces.map((w) => (
          <option key={w.name} value={w.name}>
            {w.name}
          </option>
        ))}
      </select>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="ชื่อ workspace"
        className="w-28 rounded border border-slate-700 bg-slate-900 px-1.5 py-1 text-xs text-slate-200 placeholder:text-slate-600"
      />
      <button
        onClick={save}
        disabled={!info || !name.trim()}
        className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-40"
        title="บันทึก workspace ปัจจุบัน"
      >
        💾
      </button>
    </div>
  );
}
