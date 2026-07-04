# TDD.md — Technical Design Document · AIView by ET

> รายละเอียดระดับ implementation. ภาพรวมดู [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Tech stack (locked)

| ชั้น | เทคโนโลยี |
|------|-----------|
| Desktop shell | Electron (latest LTS) |
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Chart | TradingView **Lightweight Charts** (Apache-2.0) |
| State (FE) | Zustand หรือ Redux Toolkit (เคาะตอน M1) |
| Engine | Python 3.11+ + FastAPI + Uvicorn |
| Data (crypto) | ccxt / Binance API |
| Data (stocks/gold/oil/FX) | Twelve Data / Finnhub / Polygon (ดู [DATA_SOURCES.md](DATA_SOURCES.md)) |
| Indicators | pandas + numpy (+ pandas-ta เป็น reference, ไม่ผูกขาด) |
| Backtest | backtesting.py หรือ vectorbt (เคาะตอน M3) |
| AI (local) | Ollama (HTTP `localhost:11434`) |
| AI (cloud) | Anthropic / OpenAI / Google / OpenRouter / GitHub Models SDK |
| Storage | SQLite (via SQLAlchemy หรือ sqlite3) |
| Tests | `pytest` (engine), `vitest` + Playwright (frontend) |
| Packaging | electron-builder + PyInstaller (bundle engine) |

## 2. Process model & sidecar lifecycle

Electron **main** เป็นผู้จัดการวงจรชีวิตของ Python engine:

```
app.whenReady()
  → หา engine binary (dev: python -m app.main | prod: PyInstaller exe)
  → spawn sidecar บน port ว่าง (ephemeral), ส่ง port ให้ renderer
  → poll GET /health จน 200 (timeout + retry, มี backoff)
  → เปิด BrowserWindow
app 'before-quit' / window closed
  → ส่ง SIGTERM ให้ sidecar → รอ graceful → SIGKILL ถ้าเกิน timeout
crash ของ sidecar → main ตรวจจับ exit → restart (จำกัดจำนวนครั้ง) + แจ้ง renderer
```

หลักการ: **renderer ไม่เคยรู้จัก Python ตรงๆ** — เรียกผ่าน main (สำหรับ secret/lifecycle) หรือเรียก REST/WS ตรงไป `localhost:<port>` (สำหรับ data ปกติ). port ผูก loopback เท่านั้น + token ต่อ session กัน process อื่นแอบยิง.

## 3. IPC & API contract

### 3.1 Electron IPC (renderer ⇄ main) — เฉพาะงาน privileged
- `vault:setKey(provider, key)` / `vault:hasKey(provider)` — เก็บ/เช็ค API key (ไม่มี getKey ออกมา plain)
- `ollama:ensure(model)` — ติดตั้ง Ollama + pull model (stream progress)
- `engine:info()` — port + session token
- `app:notify(payload)` — desktop notification

### 3.2 REST (renderer ⇄ engine) — ตัวอย่าง endpoint
```
GET  /health                         → { status, version }
GET  /markets                        → asset classes + symbols ที่รองรับ
GET  /candles?symbol&tf&from&to      → Candle[]
GET  /indicators?symbol&tf&set       → indicator series/markers
POST /analyze  { symbol, tf[], model } → Signal            (เรียก AI)
GET  /signals?symbol&status          → Signal[]
POST /sim/backtest { config }        → { runId }           (async)
GET  /sim/runs/{runId}               → progress/result
GET  /trades?scope                   → Trade[]
GET  /stats?scope                    → Stats
GET  /ai/models?provider             → model[] (เฉพาะที่มี key/พร้อมใช้)
GET  /settings / PUT /settings
```

### 3.3 WebSocket (`/ws`)
push realtime: `candle.update`, `signal.new`, `trade.update`, `sim.progress`, `engine.log`.
ทุก message มี envelope `{ type, ts, payload }`.

**Contract เป็น source of truth**: กำหนดด้วย pydantic (engine) + สร้าง TS types อัตโนมัติ (เช่น openapi-typescript) → FE/BE ไม่หลุดกัน.

## 4. Data layer
- **DataProvider interface**: `fetch_ohlcv(symbol, tf, from, to)`, `subscribe(symbol, tf) -> stream`, `capabilities()`
- **Normalization**: ทุก provider แปลงเป็น `Candle` schema กลาง (UTC ms timestamp)
- **Timeframe resample**: tf ที่ provider ไม่มี (10m/45m/บาง 1Y) → resample จาก base ที่เล็กกว่า ด้วย pandas `resample`
- **Cache**: OHLCV cache ใน SQLite/parquet ลด rate-limit hit; realtime ผ่าน WS ของ provider ถ้ามี ไม่งั้น poll
- **Rate-limit guard**: token-bucket ต่อ provider, fallback provider เมื่อ quota หมด (ดู DATA_SOURCES.md)

## 5. Indicator engine
- `Indicator.compute(df: DataFrame) -> IndicatorResult` (line series / bands / markers)
- ชุดเริ่มต้น (จาก public methodology, มี comment อ้าง source):
  - **Zero-Lag EMA / trend signal** (Ehlers zero-lag concept)
  - **SMC**: BOS, CHoCH, Order Block, FVG, liquidity zones (methodology สาธารณะ)
  - พื้นฐาน: EMA/SMA, RSI, MACD, ATR, volume profile
- ⚠️ ห้าม copy โค้ด Pine ที่มีลิขสิทธิ์ (ดู [MEMORY.md](../MEMORY.md) `dont-copy-proprietary-pine`)
- ทุก indicator มี unit test เทียบ output กับค่า reference ที่คำนวณมือ/known-good

## 6. AI orchestration
- **AIProvider interface**: `list_models()`, `complete(messages, tools?) -> text/json`
- Providers: `OllamaProvider`, `AnthropicProvider`, `OpenAIProvider`, `GoogleProvider`, `OpenRouterProvider`, `GitHubModelsProvider`
- **model list = key-gated**: `GET /ai/models?provider=X` คืน model ก็ต่อเมื่อมี key ที่ valid (cloud) หรือ Ollama พร้อม (local) — ตรงตามข้อ 7
- **Analysis pipeline** (`POST /analyze`):
  1. รวบ context: OHLCV ล่าสุด + indicator values + MTF summary (ย่อเป็นตัวเลข/ข้อความ ไม่ยัด candle ดิบเยอะ)
  2. เติม prompt template (`ai/prompts/analyze.md`) ที่บังคับ output เป็น **Signal JSON schema**
  3. เรียก provider → parse + validate (pydantic) → retry/repair ถ้า JSON เพี้ยน
  4. คืน Signal + เก็บ log (prompt/response) แบบ opt-in debug
- **Vision (optional)**: provider ที่รับภาพได้ (Gemini/GPT/Claude) ส่ง snapshot chart ประกอบได้ (เฟสหลัง)
- ต้นทุน/ความเร็ว/รุ่นแนะนำ ดู [AI_MODELS.md](AI_MODELS.md)

## 7. Simulator / Backtest engine
- **Backtest** (`sim/backtest.py`): รัน strategy/signal บน historical OHLCV → Trade[] เร็ว ไม่ต้องรอ realtime (ทำ **ก่อน** live-sim เสมอเพื่อได้สถิติไว)
- **Paper live-sim** (`sim/paper.py`): เปิดไม้จำลองตาม signal ใหม่ ติดตาม tick realtime จนชน SL/TP/timeout
- **Fill model**: entry ที่ราคา signal, SL/TP ตาม level, รองรับ slippage + fee config
- **Stats** (`sim/stats.py`): winrate, avg R, expectancy, profit factor, max drawdown, equity curve, per-symbol/per-TF/per-model breakdown → เข้า Dashboard
- ทุก Trade เก็บ SQLite → History หน้า UI (ดูรายไม้ แพ้ชนะ เหตุผล)

## 8. Storage & schema
- SQLite ไฟล์เดียวใน userData dir. ตารางหลัก: `candles_cache`, `signals`, `trades`, `sim_runs`, `settings`, `indicator_defs`
- Migration: alembic หรือ versioned SQL (เคาะตอน M0)
- Export: ผู้ใช้ export trades/stats เป็น CSV/JSON ได้ (เพื่อ copy ไปวิเคราะห์ต่อ)

## 9. Security
- **API keys**: เก็บผ่าน Electron `safeStorage` (เข้ารหัสด้วย OS keychain: DPAPI/Keychain/libsecret). engine รับ key ผ่าน main แบบ in-memory ต่อ session — ไม่เขียน plaintext ลงดิสก์, ไม่ log
- **Engine bind**: loopback + session token; ไม่เปิด port ออก network
- **`.env.example`** ให้ dev; จริงๆ key มาจาก vault ไม่ใช่ env ใน prod
- **No telemetry** ของ data ตลาด/คีย์ออกนอกเครื่อง

## 10. Test strategy
- **Engine (`pytest`)**: unit — indicator correctness (เทียบ known values), provider adapters (mock HTTP), signal parsing/repair, simulator fill logic + stats math; integration — `/analyze` ด้วย fake AIProvider (deterministic)
- **Frontend (`vitest`)**: component/logic, store reducers, API client
- **E2E (Playwright)**: launch Electron, health-check engine, render chart + signal panel, run backtest flow
- **CI**: GitHub Actions — lint (ruff/eslint) + typecheck (mypy/tsc) + `pytest` + `vitest` ก่อน merge
- กฎ VERIFY BEFORE DONE (CLAUDE.md): ห้ามบอกเสร็จก่อนเทสผ่านจริง

## 11. Repo layout (เป้าหมายตอน scaffold M0)
```
/                     ← root docs (CLAUDE/MEMORY/spec/README/LICENSE)
  docs/               ← เอกสารออกแบบ
  apps/
    desktop/          ← Electron main + preload
    renderer/         ← React app
  engine/             ← Python FastAPI
    app/ (api, data, indicators, ai, sim, store)
    tests/
  packages/
    shared-types/     ← TS types generated จาก OpenAPI
  .github/workflows/  ← CI
```
> โครงนี้เป็น target — ยังไม่สร้างในเฟสเอกสาร (ดู [spec.md](../spec.md) Current State).
