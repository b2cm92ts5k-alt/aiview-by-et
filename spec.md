# spec.md — AIView by ET (save point)

> อ่านไฟล์นี้ก่อนเริ่มทุก session. อัพเดท "Current State / Next" ทุกครั้งที่ทำ task เสร็จ.

## Vision
แอพ AI ช่วยวิเคราะห์ตลาด (หุ้น/คริปโต/ทองคำ/น้ำมัน/ค่าเงิน) หาจังหวะเข้าเทรด buy/sell แบบ futures,
จำลองการเทรดของ AI เก็บสถิติ + history แพ้ชนะเป็น dashboard, ให้ผู้ใช้ copy รูปแบบ/การตั้งค่าไปเทรดจริงได้.
หน้าตาคล้าย TradingView, สร้าง indicator AI เอง, เลือกสมอง AI ได้ทั้ง Local (Ollama) และ Cloud API.
PC ก่อน แล้วเผื่อ Mobile. Open-source MIT.

## Current State
**🟢 M3 Simulator + Dashboard + History — โค้ด+เทสเสร็จ [2026-07-10] (รอ CI เขียวเพื่อปิด gate)**

**M3 ที่ทำแล้ว (verify จริงทุกข้อ):**
- **Sim core** (`app/sim/`) — `fill.py` (fill model ตาม Decisions: slippage/fee ต่อขา, SL-first เมื่อชนทั้งคู่, TP1 เต็มไม้, timeout, BE epsilon 0.05R, sizing risk% ของทุนตั้งต้น), `stats.py` (winrate/avgR/expectancy/PF/maxDD/equity curve + breakdown symbol/tf/model/side), `strategy.py` (rule "zlema-smc" — proxy เชิงกติกาไว้ backtest โดยไม่ยิง LLM รายแท่ง), `backtest.py` (replay signals หรือ rule + `RunRegistry` async)
- **Paper live-sim** (`sim/paper.py`) — signal จาก `/analyze` เปิดไม้จำลองอัตโนมัติ (ARCHITECTURE flow 6b) ติดตาม stream จนชน SL/TP/timeout + WS broadcast `signal.new`/`trade.update`
- **Storage v3**: ตาราง `trades` (source backtest/paper + run_id) + `sim_runs` · **Endpoints**: `POST /sim/backtest` (async), `GET /sim/runs/{id}`, `GET /trades?scope&run_id`, `GET /stats?scope` → **pytest 86/86 ✓ ruff ✓ mypy ✓**
- **Dashboard UI** — view switcher Chart/Dashboard, stats cards 6 ใบ, equity curve (lightweight-charts line), breakdown ตาม model/tf/side, History table รายไม้ + Export CSV/JSON, ปุ่มรัน backtest + poll run → **vitest 23/23 ✓ tsc ✓ eslint ✓**
- **Live smoke ผ่านจริง**: backtest BTC/USDT 15m 1000 แท่ง (data Binance จริง) → 86 ไม้ปิด, winrate 37.21%, PF 0.61, maxDD 29.9%, equity curve 86 จุด, persist + query กลับได้ครบ (ตัวเลขติดลบ = rule proxy ยังไม่ tune — สอดคล้อง pillar "Prove It")
- หมายเหตุ: ยังไม่ได้คลิก UI Dashboard ในแอพจริง (ไม่มี interactive driver) — data flow ครอบด้วย vitest + endpoint live ครบ

**M2 (ก่อนหน้า):** indicator engine (basic + Zero-Lag Ehlers + SMC — public methodology มี comment อ้าง source) + `GET /indicators` · AI layer: OllamaProvider + orchestrator + repair retry + `POST /analyze`/`GET /signals`/`GET /ai/models` (key-gated) · UI: SignalPanel + Copy/Copy settings + MtfTable + เส้น entry/SL/TP — live smoke qwen3:8b ได้ Signal จริง persist ครบ

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
- [2026-07-10] **in-app model benchmark = ทำ** (ผู้ใช้เคาะ) — อยู่ M5
- [2026-07-10] **Backtest = custom event simulator** (ไม่ใช้ vectorbt/backtesting.py — TDD §1 เคาะแล้ว): fill model ของเรา (entry ราคา signal + SL/TP หลายเป้า + timeout รายไม้) ไม่ map กับ API ของทั้งสอง lib, เขียนเอง ~เล็กกว่า + เลี่ยง dep numba · ถ้าอนาคตต้อง vectorized mass-run ค่อย revisit
- [2026-07-10] **Sim fill model v1**: exit เต็มไม้ที่ TP1/SL/timeout (ยังไม่ partial scale-out), แท่งเดียวแตะทั้ง SL+TP → นับ SL ก่อน (conservative), sizing = risk% ของทุนตั้งต้น (ไม่ compound) — ค่า fee/slippage/ทุน/risk อยู่ใน `SimConfig` ผู้ใช้ปรับได้ ไม่ hardcode

## Open questions (รอผู้ใช้เคาะก่อนเข้าเฟสโค้ด)
- [ ] ยืนยันรายชื่อ model "⭐ แนะนำ" ใน `docs/AI_MODELS.md` (default model = เคาะแล้ว: VRAM-gated)
- [x] in-app model benchmark (แข่ง winrate จริง) — **เคาะแล้ว [2026-07-10]: เอา** → เข้า M5 ตาม ROADMAP

## Next
1. commit M3 + push → CI เขียว (M3 gate)
2. ผู้ใช้เคาะ open question ที่เหลือ: รายชื่อ model "⭐ แนะนำ" ใน AI_MODELS.md
3. งานค้างไม่บล็อก M4: BYOK UI (TwelveData/cloud keys ผ่าน vault→engine), OHLCV cache SQLite, rate-limit token bucket, SMC markers บน chart, signal history UI, backtest ด้วย AI signals ย้อนหลัง (replay mode รองรับแล้วใน engine), คลิกทดสอบ Dashboard ในแอพจริง
4. เข้าเฟส **M4 Indicator-AI Builder** (F6): pipeline describe → AI generate → validate บน sample → backtest → save, ใช้ indicator ที่สร้างเหมือน built-in, legal guardrail public methodology เท่านั้น
