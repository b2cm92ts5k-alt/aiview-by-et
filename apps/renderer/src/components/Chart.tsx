import type { Candle, EngineInfo, Signal, Timeframe } from "@aiview/shared-types";
import {
  CandlestickSeries,
  LineSeries,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
  createChart,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { fetchCandles, fetchIndicators } from "../api/engine";
import { useCandleStream } from "../hooks/useCandleStream";

const OVERLAY_COLORS = ["#f59e0b", "#a78bfa", "#34d399", "#f472b6", "#60a5fa"];

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
  signal = null,
  overlaySet = null,
}: {
  info: EngineInfo | null;
  symbol: string;
  tf: Timeframe;
  signal?: Signal | null;
  overlaySet?: string | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const overlaySeriesRef = useRef<ISeriesApi<"Line">[]>([]);
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

  // custom indicator overlay (F6): วาด line ทุกเส้นของ def (ข้าม signal_*)
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    for (const s of overlaySeriesRef.current) chart.removeSeries(s);
    overlaySeriesRef.current = [];
    if (!info || !overlaySet) return;

    let cancelled = false;
    Promise.all([
      fetchIndicators(info, symbol, tf, overlaySet),
      fetchCandles(info, symbol, tf),
    ])
      .then(([results, candles]) => {
        if (cancelled || !chartRef.current) return;
        const lines = results[0]?.lines ?? {};
        let color = 0;
        for (const [name, values] of Object.entries(lines)) {
          if (name.startsWith("signal_")) continue;
          const series = chartRef.current.addSeries(LineSeries, {
            color: OVERLAY_COLORS[color % OVERLAY_COLORS.length],
            lineWidth: 1,
            title: name,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          series.setData(
            candles
              .map((candle, i) => ({ time: (candle.ts / 1000) as UTCTimestamp, value: values[i] }))
              .filter((p): p is { time: UTCTimestamp; value: number } => p.value !== null),
          );
          overlaySeriesRef.current.push(series);
          color += 1;
        }
      })
      .catch(() => {
        /* overlay ล้มเหลวไม่บล็อก chart หลัก */
      });
    return () => {
      cancelled = true;
    };
  }, [info, symbol, tf, overlaySet]);

  // signal overlay: เส้น entry/SL/TP (F1)
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    for (const line of priceLinesRef.current) series.removePriceLine(line);
    priceLinesRef.current = [];
    if (!signal || signal.symbol !== symbol) return;
    const mk = (price: number, color: string, title: string) =>
      priceLinesRef.current.push(
        series.createPriceLine({ price, color, title, lineWidth: 1, lineStyle: 2 }),
      );
    mk(signal.entry, "#22d3ee", `entry ${signal.side}`);
    mk(signal.sl, "#f43f5e", "SL");
    signal.tp.forEach((tp, i) => mk(tp, "#22d3a5", `TP${i + 1}`));
  }, [signal, symbol]);

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
