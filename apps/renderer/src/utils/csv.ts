import type { Trade } from "@aiview/shared-types";

const COLUMNS: (keyof Trade)[] = [
  "id", "signal_id", "symbol", "tf", "side", "entry", "exit", "sl", "tp",
  "qty", "pnl", "r_multiple", "status", "model", "opened_at", "closed_at",
];

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

export function tradesToCsv(trades: Trade[]): string {
  const header = COLUMNS.join(",");
  const rows = trades.map((t) => COLUMNS.map((c) => cell(t[c])).join(","));
  return [header, ...rows].join("\n");
}

export function downloadText(filename: string, mime: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
