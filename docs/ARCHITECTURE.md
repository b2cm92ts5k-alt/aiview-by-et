# ARCHITECTURE.md — AIView by ET

> ภาพรวมสถาปัตยกรรม. รายละเอียดระดับ implementation ดู [TDD.md](TDD.md).

## 1. หลักการออกแบบ
1. **แยกสมองออกจากหน้าจอ** — UI (Electron/React) โง่ๆ วาดอย่างเดียว; logic ตลาด/AI/simulator อยู่ใน Python engine ทั้งหมด → ย้าย engine ไป cloud/mobile ทีหลังได้โดยไม่แตะ UI มาก
2. **Provider เป็น plugin** — ทั้ง data provider และ AI provider ซ่อนหลัง interface เดียว เพิ่ม/ถอดได้โดยไม่กระทบ core
3. **ทุกอย่างเป็น data** — signal, trade, stat มี schema มาตรฐานตัวเดียว ใช้ร่วมกันทั้ง copy-trade / simulator / dashboard
4. **Local-first + privacy** — data ราคา, ประวัติเทรด, API key อยู่ในเครื่องผู้ใช้ทั้งหมด

## 2. Process / Runtime diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Electron App (Desktop)                                      │
│                                                              │
│  ┌────────────────┐  IPC   ┌──────────────────────────────┐ │
│  │ Main process   │◄──────►│ Renderer (React + TS)        │ │
│  │ - window/menu  │        │ - Chart (Lightweight Charts) │ │
│  │ - sidecar mgr  │        │ - Signal panel / MTF table   │ │
│  │ - key vault    │        │ - Dashboard / History        │ │
│  │ - Ollama mgr   │        │ - Settings / Model manager   │ │
│  └───────┬────────┘        └──────────────┬───────────────┘ │
│          │ spawn/health                   │ REST + WebSocket │
└──────────┼────────────────────────────────┼─────────────────┘
           │                                 │
           ▼                                 ▼
   ┌───────────────────────────────────────────────────────┐
   │  Python Engine (FastAPI sidecar, localhost)           │
   │                                                       │
   │  API layer (REST + WS)                                │
   │   │                                                   │
   │   ├─ Data layer ──► DataProvider adapters             │
   │   │                  (Binance/ccxt, TwelveData,       │
   │   │                   Finnhub, Polygon)               │
   │   ├─ Indicator engine (Zero-Lag EMA, SMC, ...)        │
   │   ├─ AI orchestration ──► AIProvider adapters         │
   │   │                        (Ollama / Anthropic /      │
   │   │                         OpenAI / Google / ...)     │
   │   ├─ Simulator / Backtest engine                      │
   │   └─ Storage (SQLite) + stats                         │
   └───────────────────────────────────────────────────────┘
           │                         │
           ▼                         ▼
   ┌───────────────┐        ┌────────────────────┐
   │ Market APIs   │        │ Ollama (local) /   │
   │ (exchanges,   │        │ Cloud LLM APIs     │
   │  data vendors)│        └────────────────────┘
   └───────────────┘
```

## 3. Layers (ใน Python engine)

| Layer | หน้าที่ | ตัวอย่าง module |
|-------|---------|-----------------|
| **API** | REST + WebSocket endpoint, validate request/response (pydantic) | `api/routes/*`, `api/ws.py` |
| **Data** | ดึง OHLCV + realtime tick ต่อ symbol/timeframe, normalize เป็น schema กลาง, cache | `data/providers/*`, `data/cache.py` |
| **Indicator** | คำนวณ indicator จาก OHLCV (public methodology) | `indicators/zero_lag.py`, `indicators/smc.py` |
| **AI orchestration** | ประกอบ context (ราคา+indicator+MTF) → เรียก LLM → parse เป็น Signal | `ai/orchestrator.py`, `ai/providers/*`, `ai/prompts/*` |
| **Simulator** | รัน signal บน historical (backtest) / realtime (paper) → trades + สถิติ | `sim/backtest.py`, `sim/paper.py`, `sim/stats.py` |
| **Storage** | persist trades/stats/settings ใน SQLite | `store/db.py`, `store/models.py` |

## 4. Data flow หลัก (signal → dashboard)

```
1. ผู้ใช้เลือก symbol + timeframe (เช่น BTCUSDT, 15m)
2. Data layer ดึง OHLCV (history) + subscribe realtime tick
3. Indicator engine คำนวณ indicator ทุก timeframe ที่เกี่ยว (MTF)
4. AI orchestrator ประกอบ context → เรียก AI provider ที่ผู้ใช้เลือก
5. AI คืน Signal (side, entry, SL, TP1-3, RR, confidence, เหตุผล)
6. Signal ส่งเข้า: (a) Renderer แสดงบน chart + panel  (b) Simulator เปิดไม้จำลอง
7. Simulator ติดตามผลจนปิดไม้ → บันทึก Trade ลง SQLite
8. Stats aggregate → Dashboard (winrate, PnL, RR เฉลี่ย, drawdown, ฯลฯ)
```

## 5. Core domain models (ย่อ — ดู schema เต็มใน TDD.md)
- **Candle** `{ symbol, tf, ts, o, h, l, c, v }`
- **Signal** `{ id, symbol, tf, side, entry, sl, tp[], rr, confidence, reason, indicators{}, model, createdAt }`
- **Trade** `{ id, signalId, side, entry, exit, sl, tp, qty, pnl, rMultiple, status(open/win/loss/be), openedAt, closedAt }`
- **Stats** `{ scope, trades, winrate, avgR, expectancy, profitFactor, maxDrawdown, equityCurve[] }`

## 6. Timeframe model
รองรับ 5m · 10m · 15m · 30m · 45m · 60m · 4h · 1D · 1W · 1M · 1Y.
timeframe ที่ provider ไม่มีตรงๆ (เช่น 10m/45m) → engine **resample** จาก base ที่เล็กกว่า (เช่น 5m/15m).
Multi-timeframe (MTF) confluence table (เหมือนตาราง 5/15/60/240/1D ในภาพต้นแบบ) เป็นหนึ่งใน core view.

## 7. Extensibility points
- **เพิ่ม data provider**: implement `DataProvider` interface (`fetch_ohlcv`, `subscribe`, `capabilities`)
- **เพิ่ม AI provider**: implement `AIProvider` interface (`list_models`, `complete`) — key-gated
- **เพิ่ม indicator**: subclass `Indicator` (`compute(df) -> series/markers`) — ต้องมาจาก public methodology
- **Indicator AI (ข้อ 6)**: pipeline ที่ AI สังเคราะห์ indicator ใหม่จากคำอธิบาย methodology → ออกเป็น config/โค้ดที่ validate + backtest ได้ (ดู [FEATURES.md](FEATURES.md) §6)

## 8. Future: Mobile
เพราะ logic อยู่ใน Python engine หลัง REST/WS — Mobile (React Native / Expo) reuse API เดิมได้
โดยรัน engine เป็น cloud service หรือ bundle engine แบบ lightweight. UI layer เขียนใหม่ แต่ domain/contract เดิม.
