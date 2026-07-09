import type { SymbolInfo } from "@aiview/shared-types";

const CLASS_LABEL: Record<string, string> = {
  crypto: "คริปโต",
  stock: "หุ้น",
  gold: "ทองคำ",
  oil: "น้ำมัน",
  fx: "ค่าเงิน",
};

export default function Watchlist({
  symbols,
  active,
  onSelect,
}: {
  symbols: SymbolInfo[];
  active: string;
  onSelect: (symbol: string) => void;
}) {
  const groups = new Map<string, SymbolInfo[]>();
  for (const s of symbols) {
    const list = groups.get(s.asset_class) ?? [];
    list.push(s);
    groups.set(s.asset_class, list);
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto" data-testid="watchlist">
      <div className="border-b border-slate-800 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Watchlist
      </div>
      {[...groups.entries()].map(([cls, list]) => (
        <div key={cls}>
          <div className="px-3 pb-1 pt-3 text-[11px] font-medium text-slate-500">
            {CLASS_LABEL[cls] ?? cls}
          </div>
          {list.slice(0, 12).map((s) => (
            <button
              key={`${s.provider}:${s.symbol}`}
              onClick={() => onSelect(s.symbol)}
              className={`flex w-full items-center justify-between px-3 py-1.5 text-left text-sm ${
                s.symbol === active
                  ? "bg-cyan-500/10 text-cyan-300"
                  : "text-slate-300 hover:bg-slate-800/60"
              }`}
            >
              <span>{s.symbol}</span>
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
