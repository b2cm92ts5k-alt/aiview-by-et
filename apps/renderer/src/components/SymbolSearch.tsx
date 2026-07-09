import type { SymbolInfo } from "@aiview/shared-types";
import { useEffect, useMemo, useRef, useState } from "react";

export default function SymbolSearch({
  symbols,
  value,
  onSelect,
}: {
  symbols: SymbolInfo[];
  value: string;
  onSelect: (symbol: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  const matches = useMemo(() => {
    const q = query.trim().toUpperCase();
    if (!q) return symbols.slice(0, 30);
    return symbols
      .filter(
        (s) =>
          s.symbol.toUpperCase().includes(q) ||
          (s.name ?? "").toUpperCase().includes(q),
      )
      .slice(0, 30);
  }, [symbols, query]);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  return (
    <div ref={wrapRef} className="relative" data-testid="symbol-search">
      <input
        value={open ? query : value}
        placeholder="ค้นหา symbol…"
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => setQuery(e.target.value)}
        className="w-56 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-cyan-500"
      />
      {open && (
        <ul className="absolute z-20 mt-1 max-h-80 w-72 overflow-y-auto rounded-md border border-slate-700 bg-slate-900 shadow-2xl">
          {matches.map((s) => (
            <li key={`${s.provider}:${s.symbol}`}>
              <button
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-800"
                onClick={() => {
                  onSelect(s.symbol);
                  setOpen(false);
                }}
              >
                <span className="font-medium text-slate-100">{s.symbol}</span>
                <span className="ml-3 truncate text-xs text-slate-500">
                  {s.name ?? ""} · {s.asset_class}
                </span>
              </button>
            </li>
          ))}
          {matches.length === 0 && (
            <li className="px-3 py-2 text-sm text-slate-500">ไม่พบ symbol</li>
          )}
        </ul>
      )}
    </div>
  );
}
