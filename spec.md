# spec.md — AIView by ET (save point)

> อ่านไฟล์นี้ก่อนเริ่มทุก session. อัพเดท "Current State / Next" ทุกครั้งที่ทำ task เสร็จ.

## Vision
แอพ AI ช่วยวิเคราะห์ตลาด (หุ้น/คริปโต/ทองคำ/น้ำมัน/ค่าเงิน) หาจังหวะเข้าเทรด buy/sell แบบ futures,
จำลองการเทรดของ AI เก็บสถิติ + history แพ้ชนะเป็น dashboard, ให้ผู้ใช้ copy รูปแบบ/การตั้งค่าไปเทรดจริงได้.
หน้าตาคล้าย TradingView, สร้าง indicator AI เอง, เลือกสมอง AI ได้ทั้ง Local (Ollama) และ Cloud API.
PC ก่อน แล้วเผื่อ Mobile. Open-source MIT.

## Current State
**🟢 M5 Model Manager + Cloud providers + Polish — โค้ด+เทสเสร็จ [2026-07-10] (รอ CI ปิด gate — จบ roadmap M0–M5)**

**M5 ที่ทำแล้ว (verify จริง):**
- **Cloud AI providers** (`ai/cloud.py`) — Anthropic / OpenAI / Google / OpenRouter / GitHub Models (OpenAI-compat base) ทั้งหมด key-gated: key ไม่ valid → list ว่าง (F7) · **key handoff** `POST/GET/DELETE /providers/keys` — main อ่าน vault → ส่งเข้า engine in-memory ต่อ session (TDD §9, ไม่ log/ไม่ลงดิสก์) รวม `twelvedata` (BYOK data → /markets โผล่ทันที)
- **Tag ⭐ แนะนำ** (`ai/recommended.py`) — mapping ตาม AI_MODELS.md ที่ผู้ใช้เคาะ · `/ai/models` shape ใหม่ `{id, recommended}`
- **Benchmark** (`sim/benchmark.py`) — walk-forward K จุดตัด ทุก model เห็นข้อมูลชุดเดียวกัน → sim ด้วย fill model เดิม → stats ต่อ model · `POST /benchmark` + `GET /benchmark/runs/{id}` + WS progress → **pytest 137/137 ✓ ruff ✓ mypy ✓**
- **Desktop**: Ollama manager (detect/serve/pull พร้อม progress, single-active = rm ตัวเก่าก่อน pull, เปิดหน้า download ถ้ายังไม่ติดตั้ง), `system:specs` (VRAM ผ่าน nvidia-smi + RAM), push vault keys → engine เมื่อ ready + เมื่อ setKey
- **UI**: แท็บ **Models** (specs เครื่อง, local catalog ตาม AI_MODELS §B + VRAM-gated lock 🔒, cloud BYOK key manager, benchmark UI + ตารางผล) · **Disclaimer ครั้งแรก** (F9) · **Desktop alerts** signal.new/ไม้ปิด (F8) · **Workspaces** save/load (F10) · **Export Report MD** (F11) → **vitest 29/29 ✓ tsc ✓ eslint ✓**
- **Docs**: CONTRIBUTING.md + README (สถานะ+AI/BYOK guide) · **Live smoke ผ่าน**: `/ai/models` กับ ollama จริง (qwen3:8b → recommended=false ถูกต้อง), key register/list/remove roundtrip, key ปลอม → list ว่าง (key-gate จริง)

**M4 (ก่อนหน้า):** DSL safe evaluator (ast whitelist — AI ออก config ไม่ใช่โค้ด, source citation บังคับ) + pipeline generate→validate จริง→repair→quick backtest→save (`indicator_defs` v4) + ใช้เป็น set/strategy ได้ + UI Indicator AI + overlay — live smoke qwen3:8b สร้าง `zlema_sma_rsi` ครบลูป F6

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

## Open questions — เคาะครบแล้ว
- [x] รายชื่อ model "⭐ แนะนำ" ใน `docs/AI_MODELS.md` — **เคาะแล้ว [2026-07-10]: ตามที่เขียนไว้** (mapping อยู่ใน `engine/app/ai/recommended.py` — จะแก้ต้องถามก่อน)
- [x] in-app model benchmark (แข่ง winrate จริง) — **เคาะแล้ว [2026-07-10]: เอา** → ทำแล้วใน M5

## Next
1. commit M5 + push → CI เขียว (M5 gate = **จบ roadmap M0–M5**)
2. ตัดสินใจ release: tag v0.1.0 + GitHub Release (รอผู้ใช้สั่ง — outward-facing) · repo public + CI พร้อมแล้ว
3. Backlog หลัง release: ทดสอบ cloud provider กับ key จริง, Ollama auto-install ตัว installer (ตอนนี้เปิดหน้า download), default model auto-select ตาม VRAM ตอน first-run, OHLCV cache SQLite, rate-limit token bucket, SMC markers บน chart, signal history UI, Playwright E2E, คลิกทดสอบ UI จริงทุก view, max-risk warning (F9 ส่วนที่เหลือ), openapi-typescript แทน shared-types มือ
4. Future: Mobile (ROADMAP) — reuse engine API
