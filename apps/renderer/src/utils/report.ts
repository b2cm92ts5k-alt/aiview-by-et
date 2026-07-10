import type { Stats, StatsBreakdownRow, Trade } from "@aiview/shared-types";

function breakdownTable(title: string, rows: StatsBreakdownRow[]): string {
  if (rows.length === 0) return "";
  const body = rows
    .map((r) => `| ${r.key} | ${r.trades} | ${r.winrate.toFixed(1)}% | ${r.avg_r.toFixed(2)} | ${r.pnl.toFixed(2)} |`)
    .join("\n");
  return `\n### ${title}\n\n| Key | ไม้ | Winrate | Avg R | PnL |\n|---|---|---|---|---|\n${body}\n`;
}

/** F11 — สรุปผลเป็น Markdown report */
export function statsToMarkdown(stats: Stats, trades: Trade[], scopeLabel: string): string {
  return `# AIView by ET — รายงานผลการจำลอง (${scopeLabel})

> สร้างเมื่อ ${new Date().toLocaleString("th-TH", { hour12: false })}
> ⚠️ เครื่องมือวิเคราะห์เพื่อการศึกษา ไม่ใช่คำแนะนำการลงทุน — ผลจำลองไม่รับประกันผลในอนาคต

## สรุป

| ตัวชี้วัด | ค่า |
|---|---|
| จำนวนไม้ (ปิดแล้ว) | ${stats.trades} |
| ชนะ / แพ้ | ${stats.wins} / ${stats.losses} |
| Winrate | ${stats.winrate.toFixed(2)}% |
| Avg R / Expectancy | ${stats.avg_r.toFixed(3)} |
| Profit Factor | ${stats.profit_factor.toFixed(3)} |
| Max Drawdown | ${stats.max_drawdown_pct.toFixed(2)}% |
| PnL รวม | ${stats.total_pnl.toFixed(2)} |
${breakdownTable("ตาม Model", stats.by_model)}${breakdownTable("ตาม Symbol", stats.by_symbol)}${breakdownTable("ตาม Timeframe", stats.by_tf)}${breakdownTable("ตาม Side", stats.by_side)}
## รายไม้ (${trades.length})

| เวลาเข้า | Symbol | TF | Side | Entry | Exit | R | PnL | ผล | Model |
|---|---|---|---|---|---|---|---|---|---|
${trades
  .map(
    (t) =>
      `| ${new Date(t.opened_at).toISOString()} | ${t.symbol} | ${t.tf} | ${t.side} | ${t.entry} | ${t.exit ?? "—"} | ${t.r_multiple?.toFixed(2) ?? "—"} | ${t.pnl?.toFixed(2) ?? "—"} | ${t.status} | ${t.model} |`,
  )
  .join("\n")}
`;
}
