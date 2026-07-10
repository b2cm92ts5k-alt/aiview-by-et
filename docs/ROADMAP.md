# ROADMAP.md — AIView by ET

> แผนพัฒนา. สถานะปัจจุบัน: 🟡 Pre-production (เอกสารเสร็จ ยังไม่มีโค้ด — ดู [spec.md](../spec.md))
> ลำดับ/ขอบเขตเป็น anchor รอผู้ใช้เคาะ

---

## M0 · Foundations (โครงกระดูก)
**เป้าหมาย**: แอพเปล่ารันได้ end-to-end, มี test harness + CI
- Scaffold Electron + React + Vite + TS + Tailwind
- Python FastAPI sidecar + `/health`, spawn/shutdown จาก Electron main
- IPC + REST/WS ต่อกันได้ (renderer อ่าน `/health` จาก engine)
- SQLite + settings, vault (safeStorage) เก็บ key
- CI (GitHub Actions): lint + typecheck + `pytest` + `vitest`
- **Done เมื่อ**: `npm run dev` เปิดแอพ, engine health เขียว, test เขียวใน CI

## M1 · Chart + Realtime Data (F4, F3, F5 บางส่วน)
**เป้าหมาย**: เห็นกราฟจริง realtime หน้าตาคล้าย TradingView
- DataProvider adapters: Binance/ccxt (crypto) + Twelve Data/Finnhub (อื่นๆ)
- OHLCV + WS realtime → Lightweight Charts (candlestick)
- Symbol search, timeframe selector (11 tf), resample 10m/45m
- Layout พื้นฐานสไตล์ TradingView (toolbar/panel/watchlist)
- **Done เมื่อ**: เลือก symbol+tf เห็นแท่งเทียน update realtime

## M2 · AI Signals (F1, F7 บางส่วน)
**เป้าหมาย**: AI ออก signal พร้อม copy ได้
- Indicator engine ชุดแรก (Zero-Lag, SMC BOS/CHoCH/OB/FVG, EMA/RSI/ATR — public methodology)
- AIProvider abstraction + Ollama local (ก่อน) → `/analyze` คืน Signal JSON
- Signal panel + markers บน chart + ปุ่ม Copy / Copy settings
- MTF confluence table (F3)
- **Done เมื่อ**: กดวิเคราะห์ได้ signal จริง (entry/SL/TP/RR/เหตุผล) copy ออกไปได้

## M3 · Simulator + Dashboard + History (F2)
**เป้าหมาย**: พิสูจน์ว่า signal ดีแค่ไหน
- Backtest engine (historical) → Trade[]
- Paper live-sim (realtime)
- Stats (winrate, R, expectancy, PF, drawdown, equity curve) + breakdown
- Dashboard UI + History table + export CSV/JSON
- **Done เมื่อ**: รัน backtest ได้สถิติ + history รายไม้ครบ แสดงใน dashboard

## M4 · Indicator-AI Builder (F6)
**เป้าหมาย**: สร้าง indicator เองด้วย AI
- Pipeline: describe → AI generate → validate (run บน sample) → backtest → save
- ใช้ indicator ที่สร้างใน signal/sim ได้เหมือน built-in
- legal guardrail: public methodology เท่านั้น
- **Done เมื่อ**: สร้าง indicator ใหม่จากคำอธิบาย, ผ่าน backtest, เอาไปใช้ได้

## M5 · Model Manager + Cloud providers + Polish (F7 เต็ม, F8–F11)
**เป้าหมาย**: พร้อม release open-source
- Cloud providers ครบ (Anthropic/OpenAI/Google/OpenRouter/GitHub Models), model list key-gated + tag แนะนำ
- Ollama auto-install + spec check + pull progress
- Alerts/notifications, risk gate/disclaimer, workspaces, export report
- in-app model benchmark เทียบ winrate (เคาะแล้ว 2026-07-10: ทำ)
- docs สำหรับ contributor, GitHub release, MIT
- **Done เมื่อ**: ผู้ใช้ใหม่ติดตั้ง ใช้ได้ครบลูป, repo public พร้อม CI

## Future · Mobile
- reuse engine API (REST/WS), UI ใหม่ (React Native / Expo)
- engine เป็น cloud service หรือ lightweight bundle

---
## Milestone gates
แต่ละ M ต้อง: (1) test เขียว (`pytest`+`vitest`) (2) อัพเดท [spec.md](../spec.md) (3) demo ใช้ได้จริง ก่อนขึ้น M ถัดไป (กฎ VERIFY BEFORE DONE ใน [CLAUDE.md](../CLAUDE.md))
