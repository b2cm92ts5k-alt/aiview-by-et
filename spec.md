# spec.md — AIView by ET (save point)

> อ่านไฟล์นี้ก่อนเริ่มทุก session. อัพเดท "Current State / Next" ทุกครั้งที่ทำ task เสร็จ.

## Vision
แอพ AI ช่วยวิเคราะห์ตลาด (หุ้น/คริปโต/ทองคำ/น้ำมัน/ค่าเงิน) หาจังหวะเข้าเทรด buy/sell แบบ futures,
จำลองการเทรดของ AI เก็บสถิติ + history แพ้ชนะเป็น dashboard, ให้ผู้ใช้ copy รูปแบบ/การตั้งค่าไปเทรดจริงได้.
หน้าตาคล้าย TradingView, สร้าง indicator AI เอง, เลือกสมอง AI ได้ทั้ง Local (Ollama) และ Cloud API.
PC ก่อน แล้วเผื่อ Mobile. Open-source MIT.

## Current State
**🟢 M4 Indicator-AI Builder — เสร็จ [2026-07-10] (live smoke ผ่าน — รอ CI เขียวปิด gate)**

**M4 ที่ทำแล้ว:**
- **DSL** (`app/indicators/dsl.py`) — safe expression evaluator (ast whitelist, ไม่มี attribute/subscript/import, ฟังก์ชันเฉพาะ whitelist, cap ความยาว/จำนวน lines) + `IndicatorDef` (name/title/description/**source บังคับ** ตาม legal guardrail/params/lines/long_when/short_when) + `compute_def` → security tests (reject `__import__`, attr access, lambda, subscript ฯลฯ) + correctness tests เทียบ builtin
- **Pipeline** (`ai/indicator_gen.py` + `prompts/indicator.md`) — describe → AI generate JSON → parse → **validate ด้วยการรันจริงบนแท่งจริง** → repair retry 1 ครั้ง · AI ปฏิเสธ proprietary → 422 · prompt มี DSL reference + กฎห้าม copy AlgoAlpha/LuxAlgo
- **Endpoints**: `POST /indicators/ai/generate` (+quick backtest ถ้ามี long/short), `POST/GET /indicators/defs`, `DELETE /indicators/defs/{name}`, `GET /indicators?set=<ชื่อ custom>` ใช้เหมือน built-in, `/sim/backtest strategy=custom:<ชื่อ>` · migration v4 `indicator_defs` → **pytest 112/112 ✓ ruff ✓ mypy ✓**
- **UI**: แท็บ "Indicator AI" — describe → generate → เห็น def + expressions + quick backtest → บันทึก → list + ลบ + **Overlay บน Chart** (วาดทุก line ของ def เป็น line series) → **vitest 26/26 ✓ tsc ✓ eslint ✓**
- **Live smoke ผ่านจริง (Done criteria F6 ครบ)**: qwen3:8b สร้าง def `zlema_sma_rsi` จากคำอธิบายไทย (อ้าง public source) → validate บนแท่ง Binance จริง → quick backtest 430 ไม้ → save → ใช้เป็น indicator set (`GET /indicators?set=zlema_sma_rsi` ได้ 5 lines) → ใช้เป็น strategy `custom:zlema_sma_rsi` backtest 530 ไม้ wr 39.4%

**M3 (ก่อนหน้า):** sim core (fill SL-first/fee/slippage/risk% + stats ครบ + rule strategy + RunRegistry) · paper live-sim เปิดไม้อัตโนมัติจาก /analyze + WS trade.update · storage v3 (trades/sim_runs) + `/sim/backtest` `/sim/runs/{id}` `/trades` `/stats` · Dashboard UI (stats cards/equity curve/breakdowns/history/export) — live smoke BTC/USDT 1000 แท่ง 86 ไม้ persist ครบ (ยังไม่ได้คลิก UI จริง — ครอบด้วย vitest)

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
- [2026-07-10] **Indicator-AI (F6) = DSL config ไม่ใช่โค้ด**: AI ออก JSON definition (expressions บน whitelist: ema/sma/rma/rsi/zlema/atr/shift/highest/lowest/abs/crossover/crossunder + เลขคณิต/เปรียบเทียบ/& |) → engine ตีความผ่าน ast whitelist เอง **ไม่ exec Python จาก LLM** (กัน arbitrary code execution — docs เขียน "config/โค้ด" เลือกฝั่ง config ด้วยเหตุผล security) · validate = รันจริงบนแท่งจริงก่อนรับ + repair retry 1 ครั้ง

## Open questions (รอผู้ใช้เคาะก่อนเข้าเฟสโค้ด)
- [ ] ยืนยันรายชื่อ model "⭐ แนะนำ" ใน `docs/AI_MODELS.md` (default model = เคาะแล้ว: VRAM-gated)
- [x] in-app model benchmark (แข่ง winrate จริง) — **เคาะแล้ว [2026-07-10]: เอา** → เข้า M5 ตาม ROADMAP

## Next
1. commit M4 + push → CI เขียว (M4 gate)
2. ผู้ใช้เคาะ open question ที่เหลือ: รายชื่อ model "⭐ แนะนำ" ใน AI_MODELS.md — **จำเป็นก่อนเข้า M5** (M5 = model manager + tag แนะนำ key-gated)
3. งานค้างไม่บล็อก: BYOK UI (TwelveData/cloud keys ผ่าน vault→engine), OHLCV cache SQLite, rate-limit token bucket, SMC markers บน chart, signal history UI, replay-backtest ด้วย AI signals ย้อนหลัง, คลิกทดสอบ UI ในแอพจริง
4. เข้าเฟส **M5 Model Manager + Cloud providers + Polish**: cloud AI providers (Anthropic/OpenAI/Google/OpenRouter/GitHub Models, key-gated ผ่าน vault), Ollama auto-install + VRAM gate + pull progress (F7), in-app model benchmark (เคาะแล้ว: ทำ), alerts/notifications, risk gate/disclaimer, workspaces, export report, docs contributor + GitHub release
