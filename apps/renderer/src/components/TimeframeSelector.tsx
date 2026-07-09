import { TIMEFRAMES, type Timeframe } from "@aiview/shared-types";

export default function TimeframeSelector({
  value,
  onChange,
}: {
  value: Timeframe;
  onChange: (tf: Timeframe) => void;
}) {
  return (
    <div className="flex items-center gap-0.5" data-testid="tf-selector">
      {TIMEFRAMES.map((tf) => (
        <button
          key={tf}
          onClick={() => onChange(tf)}
          className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
            tf === value
              ? "bg-cyan-500/20 text-cyan-300"
              : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          }`}
        >
          {tf}
        </button>
      ))}
    </div>
  );
}
