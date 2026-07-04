# spec.md — AIView by ET (save point)

> อ่านไฟล์นี้ก่อนเริ่มทุก session. อัพเดท "Current State / Next" ทุกครั้งที่ทำ task เสร็จ.

## Vision
แอพ AI ช่วยวิเคราะห์ตลาด (หุ้น/คริปโต/ทองคำ/น้ำมัน/ค่าเงิน) หาจังหวะเข้าเทรด buy/sell แบบ futures,
จำลองการเทรดของ AI เก็บสถิติ + history แพ้ชนะเป็น dashboard, ให้ผู้ใช้ copy รูปแบบ/การตั้งค่าไปเทรดจริงได้.
หน้าตาคล้าย TradingView, สร้าง indicator AI เอง, เลือกสมอง AI ได้ทั้ง Local (Ollama) และ Cloud API.
PC ก่อน แล้วเผื่อ Mobile. Open-source MIT.

## Current State
**🟡 Pre-production — เอกสารกำกับการพัฒนาเสร็จ ยังไม่มีโค้ด**

เอกสารที่มีแล้ว:
- ราก: `CLAUDE.md`, `MEMORY.md`, `spec.md` (ไฟล์นี้), `README.md`, `LICENSE (MIT)`
- `docs/`: `ARCHITECTURE.md`, `TDD.md`, `FEATURES.md`, `AI_MODELS.md`, `DATA_SOURCES.md`, `ROADMAP.md`

ยังไม่มี: source code, `package.json`, Python engine, scaffold ใดๆ

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

## Open questions (รอผู้ใช้เคาะก่อนเข้าเฟสโค้ด)
- [ ] ยืนยันรายชื่อ model "⭐ แนะนำ" ใน `docs/AI_MODELS.md` (default model = เคาะแล้ว: VRAM-gated)
- [ ] จะทำ in-app model benchmark (แข่ง winrate จริง) เป็นฟีเจอร์เลยไหม (option, ไม่บล็อก M0)

## Next
1. ผู้ใช้ review เอกสาร (โดยเฉพาะ AI_MODELS + DATA_SOURCES + ROADMAP) แล้วเคาะ open questions
2. เข้าเฟส **M0 Foundations** (แยก session): scaffold Electron+React+Vite, Python FastAPI sidecar, health-check IPC, CI + test harness (`pytest` + `vitest`)
3. อัพเดท Current State ไฟล์นี้เมื่อ M0 เริ่ม
