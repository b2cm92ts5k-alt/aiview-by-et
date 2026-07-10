import type { EquityPoint } from "@aiview/shared-types";
import {
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  createChart,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

const DARK = {
  layout: { background: { color: "#0b0e14" }, textColor: "#8b94a7" },
  grid: { vertLines: { color: "#151a25" }, horzLines: { color: "#151a25" } },
  timeScale: { borderColor: "#1e2536", timeVisible: true },
  rightPriceScale: { borderColor: "#1e2536" },
};

export default function EquityCurve({ points }: { points: EquityPoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, { ...DARK, autoSize: true });
    seriesRef.current = chart.addSeries(LineSeries, { color: "#22d3ee", lineWidth: 2 });
    chartRef.current = chart;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    // lightweight-charts ต้องการ time ไม่ซ้ำ — ไม้ที่ปิด ms เดียวกันให้ขยับ 1s
    const seen = new Set<number>();
    const data = points.map((p) => {
      let t = Math.floor(p.ts / 1000);
      while (seen.has(t)) t += 1;
      seen.add(t);
      return { time: t as UTCTimestamp, value: p.equity };
    });
    seriesRef.current?.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [points]);

  return <div ref={containerRef} className="h-48 w-full" data-testid="equity-curve" />;
}
