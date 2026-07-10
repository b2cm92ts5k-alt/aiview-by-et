# spec.md — AIView by ET (save point)

> อ่านไฟล์นี้ก่อนเริ่มทุก session. อัพเดท "Current State / Next" ทุกครั้งที่ทำ task เสร็จ.

## Vision
แอพ AI ช่วยวิเคราะห์ตลาด (หุ้น/คริปโต/ทองคำ/น้ำมัน/ค่าเงิน) หาจังหวะเข้าเทรด buy/sell แบบ futures,
จำลองการเทรดของ AI เก็บสถิติ + history แพ้ชนะเป็น dashboard, ให้ผู้ใช้ copy รูปแบบ/การตั้งค่าไปเทรดจริงได้.
หน้าตาคล้าย TradingView, สร้าง indicator AI เอง, เลือกสมอง AI ได้ทั้ง Local (Ollama) และ Cloud API.
PC ก่อน แล้วเผื่อ Mobile. Open-source MIT.

## Current State
**🟢 M2 AI Signals — เสร็จ + ปิด gate แล้ว [2026-07-10] (CI GitHub เขียวที่ 6bbc41e — M0/M1/M2 ปิดครบ)**

**M2 ที่ทำแล้ว (verify จริงทุกข้อ):**
- **Indicator engine** (`app/indicators/`) — basic (SMA/EMA/RSI Wilder/MACD/ATR), Zero-Lag EMA (Ehlers public formula), SMC (swing fractals, BOS/CHoCH, FVG, Order Block — public methodology, ทุกไฟล์มี comment อ้าง source ตามกฎ) + registry set "core" + `GET /indicators` — เทสเทียบค่าคำนวณมือครบ
- **AI layer** (`app/ai/`) — `AIProvider` ABC + `OllamaProvider` (list_models จาก /api/tags = key-gate เทียบเท่า, complete ผ่าน /api/chat format=json), prompt template `ai/prompts/analyze.md`, orchestrator (context: candles+indicators+MTF summary → parse Signal + repair retry 1 ครั้ง + NoSetup → null), signals table (migration v2) + `POST /analyze` + `GET /signals` + `GET /ai/models` → **pytest 63/63 ✓ ruff ✓ mypy ✓**
- **Renderer** — SignalPanel (model selector จาก /ai/models, ปุ่มวิเคราะห์, signal card entry/SL/TP/RR/confidence/เหตุผล, ปุ่ม Copy + Copy settings + disclaimer), MtfTable (confluence 5m/15m/60m/4h/1D จาก zlema trend + RSI), เส้น entry/SL/TP บน chart → **vitest 17/17 ✓ tsc ✓ eslint ✓**
- **Live smoke ผ่านจริง**: Ollama qwen3:8b (RTX 2060S 8GB, 100% GPU) → `POST /analyze` BTC/USDT [15m,60m,4h] ได้ Signal จริง (LONG entry 64152.55 SL 63266.6 conf 85% เหตุผลอ้าง ZLEMA/RSI/MACD/OB/ATR) + persist ลง SQLite + `GET /signals` เจอ · UI wiring: `/ai/models` + `/indicators`×5tf + `/markets` + `/candles` = 200 หมดจาก renderer จริง

**M1 (ก่อนหน้า):** data layer Binance/ccxt (ThreadedResolver) + TwelveData (BYOK env), resample 10m/45m/1Y (batch+streaming), `/markets` `/candles` + WS subscribe→candle.update, Lightweight Charts v5 UI + Zustand + watchlist/TF selector — smoke จริงผ่าน (candle.update 15m + 10m resampled)
**M0 (ก่อนหน้า):** engine `/health` `/settings` `/ws` + token auth + SQLite versioned migrations · Electron sidecar lifecycle + vault (safeStorage, ไม่มี getKey IPC) · React health card · CI (ruff+mypy+pytest / eslint+tsc+vitest+build) · Electron ^43, audit 0 vuln

เอกสาร: ราก (`CLAUDE.md`, `MEMORY.md`, `spec.md`, `README.md` + dev quickstart, `LICENSE`) + `docs/` ครบ 6 ไฟล์ · shared-types ยังเขียนมือ (รอ openapi-typescript)

## Architecture ที่ตกลงไว้ (สรุป — รายละเอียดใน docs/)
- **Frontend**: Electron + React + TypeScript + Vite + Tailwind + TradingView Lightweight Charts
- **Engine**: Python + FastAPI sidecar (spawn โดย Electron main) — คุยผ่าน local REST + WebSocket
- **Modules ใน engine**: data-provider adapters → indicator engine → AI orchestration (signal) → simulator/backtest → stats
- **Storage**: SQLite (trades, stats, settings) + encrypted key vault (OS keychain / Electron safeStorage)
- **AI providers**: Ollama (local) + Anthropic/OpenAI/Google/OpenRouter/GitHub Models (cloud, key-gated)
- **Data providers**: Binance/ccxt (crypto), Twelve Data/Finnhub/Polygon (stocks/gold/oil/FX)

## Decisions log
- [2026-07-03] เลือก Electron+React (frontend) + Python/FastAPI (engine) แทน Tauri/Rust — เหตุผล: ecosystem quant ของ Python (pandas, ccxt, backtesting) + community Electron ใหญ่
- [2026-07-03] Data: multi-provider เอง **ไม่ดึงจาก TradingView** (ToS) — chart ใช้ Lightweight Charts (Apache-2.0)
- [2026-07-03] Indicator AI: reimplement จาก public methodology เท่านั้น ห้าม copy Pine proprietary
- [2026-07-03] เฟสแรกไม่ต่อ broker ยิงออเดอร์จริง — ผู้ใช้ copy signal ไปเทรดเอง (financial disclaimer)
- [2026-07-03] **Local model = VRAM-gated install**: เช็ค VRAM ก่อนเสมอ → default ตาม VRAM, รุ่นที่ VRAM ไม่ถึง lock+แจ้ง, single active model (ลงใหม่ = uninstall ตัวเก่า) — ดู FEATURES §F7
- [2026-07-03] ลำดับ milestone ใน ROADMAP.md = ยืนยันแล้ว (M0→M5 + future Mobile)
- [2026-07-03] **Data provider**: crypto = Binance/ccxt · non-crypto = **Twelve Data (หลัก)** + Finnhub/Polygon สำรอง · **BYOK ไม่ bundle key กลาง** — ดู DATA_SOURCES §5
- [2026-07-10] **Migration = versioned SQL** (ไม่ใช้ alembic) — schema ยังเล็ก, dependency น้อยกว่า, list `MIGRATIONS` + `PRAGMA user_version` ใน `engine/app/store/db.py` (TDD §8 เคาะแล้ว)
- [2026-07-10] Dev server ล็อก **IPv4 `127.0.0.1`** ทั้ง vite/wait-on/Electron — `localhost` บน Windows resolve เป็น `::1` ทำให้ wait-on ค้าง
- [2026-07-10] Electron pin `^43` — ต่ำกว่านั้นมี security advisory (npm audit high)
- [2026-07-10] **State lib (FE) = Zustand** (TDD §1 เคาะแล้ว) — เบากว่า RTK, state หลักอยู่ engine อยู่แล้ว UI store เล็ก
- [2026-07-10] **aiohttp ใช้ ThreadedResolver** ใน BinanceProvider — aiodns/c-ares ยิง UDP DNS ตรง พังบนบาง Windows/network ("Could not contact DNS servers") · getaddrinfo ของ OS ชัวร์กว่า
- [2026-07-10] engine ต้องใช้ `uvicorn[standard]` — ตัว plain ไม่มี WS library (TestClient จับไม่ได้เพราะรัน in-process)
- [2026-07-10] Symbol canonical = ccxt style (`BTC/USDT`) · TwelveData symbol ทอง/น้ำมัน เริ่มที่ `XAU/USD`, `WTI/USD`, `BRN/USD` (DATA_SOURCES §6 — ยัง verify กับ key จริงไม่ได้ รอผู้ใช้ใส่ BYOK)

## Open questions (รอผู้ใช้เคาะก่อนเข้าเฟสโค้ด)
- [ ] ยืนยันรายชื่อ model "⭐ แนะนำ" ใน `docs/AI_MODELS.md` (default model = เคาะแล้ว: VRAM-gated)
- [ ] จะทำ in-app model benchmark (แข่ง winrate จริง) เป็นฟีเจอร์เลยไหม (option, ไม่บล็อก M0)

## Next
1. ผู้ใช้เคาะ open questions (AI_MODELS แนะนำ / in-app benchmark)
2. งานค้างไม่บล็อก M3: TwelveData ทดสอบกับ key จริง (BYOK UI), OHLCV cache SQLite (`candles_cache`), rate-limit token bucket, SMC markers วาดบน chart (ตอนนี้มีแต่เส้น signal), signal history UI
4. เข้าเฟส **M3 Simulator + Dashboard + History**: backtest engine (เคาะ lib: backtesting.py vs vectorbt — TDD §1), paper live-sim, stats (winrate/R/expectancy/PF/DD/equity curve), dashboard UI + history table + export CSV/JSON
