# spec.md — AIView by ET (save point)

> อ่านไฟล์นี้ก่อนเริ่มทุก session. อัพเดท "Current State / Next" ทุกครั้งที่ทำ task เสร็จ.

## Vision
แอพ AI ช่วยวิเคราะห์ตลาด (หุ้น/คริปโต/ทองคำ/น้ำมัน/ค่าเงิน) หาจังหวะเข้าเทรด buy/sell แบบ futures,
จำลองการเทรดของ AI เก็บสถิติ + history แพ้ชนะเป็น dashboard, ให้ผู้ใช้ copy รูปแบบ/การตั้งค่าไปเทรดจริงได้.
หน้าตาคล้าย TradingView, สร้าง indicator AI เอง, เลือกสมอง AI ได้ทั้ง Local (Ollama) และ Cloud API.
PC ก่อน แล้วเผื่อ Mobile. Open-source MIT.

## Current State
**🟢 M1 Chart + Realtime Data — เสร็จ + verify ผ่านแล้ว [2026-07-10] (M0 ปิด gate: CI GitHub เขียว run 29048809008)**

**M1 ที่ทำแล้ว (verify จริงทุกข้อ):**
- **Engine data layer** — `models.py` (Candle/SymbolInfo/11 tf ตาม ARCHITECTURE §5–6), `DataProvider` interface, `BinanceProvider` (ccxt.pro REST+WS, ฟรีไม่ต้อง key), `TwelveDataProvider` (BYOK ผ่าน env `TWELVEDATA_API_KEY`, realtime = poll, test ด้วย MockTransport), resample 10m/45m/1Y (pandas batch + `StreamAggregator` streaming), `DataService` route symbol→provider + ซ่อน resample
- **Endpoints ใหม่**: `GET /markets`, `GET /candles?symbol&tf&since&limit`, WS protocol `subscribe/unsubscribe` → push `candle.update` (envelope เดิม) → **pytest 35/35 ✓ ruff ✓ mypy ✓**
- **Renderer** — Lightweight Charts v5 candlestick + Zustand store, layout สไตล์ TradingView (symbol search + TF selector 11 ตัว บน / toolbar ซ้าย placeholder / chart กลาง / watchlist ขวา grouped ตาม asset class), WS hook re-subscribe เมื่อเปลี่ยน symbol/tf + auto-reconnect → **vitest 12/12 ✓ tsc ✓ eslint ✓**
- **Smoke จริง**: `npm run dev` → `/markets` 200 (Binance load_markets), `/candles` BTC/USDT 15m 200 (500 แท่ง), WS accepted · สคริปต์ ws_smoke: subscribe 15m ได้ 3 candle.update จริง (close 63373.99) + 10m resampled ts align bucket ✓

**M0 (ก่อนหน้า):** engine `/health` `/settings` `/ws` + token auth + SQLite versioned migrations · Electron sidecar lifecycle + vault (safeStorage) · React health card · CI เขียวบน GitHub

ที่ทำแล้ว (verify จริงทุกข้อ):
- **engine/** — Python FastAPI: `/health`, `/settings` (GET/PUT), `/ws` (envelope `{type,ts,payload}` + `engine.hello`), token auth (X-Engine-Token / `?token=`), SQLite + versioned SQL migrations → **pytest 16/16 ✓ · ruff ✓ · mypy ✓**
- **apps/desktop/** — Electron main+preload: spawn sidecar บน port ว่าง + token ต่อ session, poll `/health` (backoff), graceful shutdown, restart จำกัด 3 ครั้ง, vault (safeStorage → `vault.json` encrypted blobs, ไม่มี getKey IPC), IPC: `engine:info`, `vault:setKey/hasKey`, `app:notify`, push `engine:status`
- **apps/renderer/** — React+Vite+Tailwind v4: health card (เขียว/เหลือง/แดง poll ทุก 3s) → **vitest 6/6 ✓ · tsc ✓ · vite build ✓**
- **packages/shared-types/** — contract types เขียนมือ (M0) รอเปลี่ยนเป็น openapi-typescript ภายหลัง
- **CI**: `.github/workflows/ci.yml` (engine: ruff+mypy+pytest · frontend: eslint+tsc+vitest+build)
- **Smoke test ผ่าน**: `npm run dev` → vite ✓ → electron ✓ → engine spawn ✓ → main poll `/health` 200 ✓ → renderer CORS+poll `/health` 200 ต่อเนื่อง ✓ (= health เขียวใน UI)
- `npm audit` = 0 vulnerabilities (bump Electron 33→43 เพราะ advisory)

เอกสาร: ราก (`CLAUDE.md`, `MEMORY.md`, `spec.md`, `README.md` + dev quickstart, `LICENSE`) + `docs/` ครบ 6 ไฟล์

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
1. commit M1 + push → CI เขียว (M1 gate)
2. ผู้ใช้เคาะ open questions (AI_MODELS แนะนำ / in-app benchmark) — บล็อก M2 บางส่วน (ต้องรู้ default model)
3. M1 ค้าง (ไม่บล็อก M2): ทดสอบ TwelveData กับ key จริง (BYOK UI), OHLCV cache ใน SQLite (`candles_cache`), rate-limit token bucket, MTF confluence table (F3 — ROADMAP วางไว้ M2)
4. เข้าเฟส **M2 AI Signals**: indicator engine ชุดแรก (Zero-Lag EMA, SMC, EMA/RSI/ATR — public methodology + comment อ้าง source), AIProvider abstraction + Ollama, `/analyze` → Signal JSON, signal panel + markers บน chart
