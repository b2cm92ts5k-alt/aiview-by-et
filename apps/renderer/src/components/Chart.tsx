import type { Candle, EngineInfo, Timeframe } from "@aiview/shared-types";
import {
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  createChart,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { fetchCandles } from "../api/engine";
import { useCandleStream } from "../hooks/useCandleStream";

const DARK = {
  layout: { background: { color: "#0b0e14" }, textColor: "#8b94a7" },
  grid: {
    vertLines: { color: "#151a25" },
    horzLines: { color: "#151a25" },
  },
  crosshair: { mode: 0 },
  timeScale: { borderColor: "#1e2536", timeVisible: true },
  rightPriceScale: { borderColor: "#1e2536" },
};

const SERIES = {
  upColor: "#22d3a5",
  downColor: "#f43f5e",
  borderUpColor: "#22d3a5",
  borderDownColor: "#f43f5e",
  wickUpColor: "#22d3a5",
  wickDownColor: "#f43f5e",
};

function toBar(c: Candle) {
  return {
    time: (c.ts / 1000) as UTCTimestamp,
    open: c.o,
    high: c.h,
    low: c.l,
    close: c.c,
  };
}

export default function Chart({
  info,
  symbol,
  tf,
}: {
  info: EngineInfo | null;
  symbol: string;
  tf: Timeframe;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, { ...DARK, autoSize: true });
    const series = chart.addSeries(CandlestickSeries, SERIES);
    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // history load on symbol/tf change
  useEffect(() => {
    if (!info) return;
    let cancelled = false;
    setError(null);
    fetchCandles(info, symbol, tf)
      .then((candles) => {
        if (cancelled || !seriesRef.current) return;
        seriesRef.current.setData(candles.map(toBar));
        chartRef.current?.timeScale().fitContent();
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [info, symbol, tf]);

  useCandleStream(info, symbol, tf, (candle) => {
    if (candle.symbol === symbol && candle.tf === tf) {
      seriesRef.current?.update(toBar(candle));
    }
  });

  return (
    <div className="relative h-full w-full" data-testid="chart-container">
      <div ref={containerRef} className="h-full w-full" />
      {error && (
        <div className="absolute inset-x-0 top-2 mx-auto w-fit rounded bg-rose-950/80 px-3 py-1 text-xs text-rose-300">
          โหลดข้อมูลไม่สำเร็จ — {error}
        </div>
      )}
    </div>
  );
}
