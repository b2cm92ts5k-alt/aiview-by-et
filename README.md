# AIView by ET

> **AI-powered market analysis** — ผู้ช่วย AI หาจังหวะเข้าเทรด buy/sell (futures) สำหรับ หุ้น · คริปโต · ทองคำ · น้ำมัน · ค่าเงิน · จำลองการเทรด เก็บสถิติ และ copy รูปแบบไปใช้ได้จริง

Desktop app หน้าตาคล้าย TradingView · **Electron + React** frontend · **Python/FastAPI** engine · AI ได้ทั้ง **Local (Ollama)** และ **Cloud API** · PC ก่อน แล้วเผื่อ Mobile

**License:** [PolyForm Noncommercial 1.0.0](LICENSE) — ใช้ฟรีเพื่อ non-commercial, **ห้ามใช้/ขายเชิงพาณิชย์** · **Version:** v0.1.1 (Windows) · **Status:** 🟢 M0–M5 ครบตาม roadmap — chart realtime · AI signals · simulator/backtest · Indicator-AI builder · model manager + benchmark

> ⚠️ **Disclaimer:** เครื่องมือนี้ใช้เพื่อการวิเคราะห์และการศึกษาเท่านั้น **ไม่ใช่คำแนะนำการลงทุน** การเทรดมีความเสี่ยง ผลจากอดีต/การจำลองไม่รับประกันผลในอนาคต

---

## ⬇️ ดาวน์โหลด & ติดตั้ง (ผู้ใช้ทั่วไป — Windows)

1. โหลด `AIView by ET Setup 0.1.1.exe` จากหน้า [**Releases**](../../releases) → ติดตั้ง (เลือกโฟลเดอร์ได้)
   > ยังไม่ได้ code-sign — Windows SmartScreen อาจเตือน กด **More info → Run anyway**
2. เปิดแอพ → ยอมรับ disclaimer → **เห็นกราฟ BTC/USDT realtime ได้ทันที** (ไม่ต้องตั้งค่าอะไร Binance ฟรี)
3. อยากใช้ AI: ติดตั้ง [Ollama](https://ollama.com) → แท็บ **Models** เลือกรุ่นตาม VRAM แล้วติดตั้ง → กลับแท็บ Chart กด "วิเคราะห์"

ไม่ต้องมี Python/Node — engine ถูก bundle มาในตัวแล้ว · ดูรายละเอียดทำอะไรได้/ไม่ได้ที่ [RELEASE_NOTES_v0.1.0.md](docs/RELEASE_NOTES_v0.1.0.md) · การเปลี่ยนแปลง v0.1.1 ดู [CHANGELOG](docs/RELEASE_NOTES_v0.1.1.md)

---

## 🚀 Dev Quickstart

ต้องมี: Node 20+ · Python 3.11+

```bash
# 1) engine (ครั้งแรก)
cd engine
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"   # Windows
cd ..

# 2) frontend
npm install

# 3) รันแอพ (Vite + Electron + spawn engine อัตโนมัติ)
npm run dev
```

Tests: `npm test` (vitest) · `npm run test:engine` (pytest) · `npm run lint` · `npm run typecheck`
Build installer: `npm run package` (PyInstaller engine + electron-builder NSIS → `apps/desktop/release/`)

โครง repo: `apps/desktop` (Electron main/preload) · `apps/renderer` (React UI) · `engine/` (Python FastAPI) · `packages/shared-types` (FE/BE contract)

**AI**: Local ผ่าน [Ollama](https://ollama.com) (แอพจัดการ pull/VRAM gate ให้จากแท็บ Models) หรือ Cloud — ใส่ API key ของคุณเอง (BYOK, เก็บเข้ารหัสในเครื่อง) · **Data**: Binance ฟรีไม่ต้องมี key, ตลาดอื่นใส่ key Twelve Data

อยากช่วยพัฒนา? อ่าน [CONTRIBUTING.md](CONTRIBUTING.md)

## 📖 Design Documentation

เอกสารทั้งหมดอยู่ใน [`docs/`](docs/):

| Doc | คำอธิบาย |
|-----|----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | ภาพรวมสถาปัตยกรรม — layer/module, process (Electron ⇄ FastAPI ⇄ AI), data flow |
| [TDD.md](docs/TDD.md) | Technical Design — IPC, sidecar lifecycle, API contract, engine, storage, security, test strategy |
| [FEATURES.md](docs/FEATURES.md) | Feature spec ละเอียด แตกจาก concept ข้อ 1–7 |
| [AI_MODELS.md](docs/AI_MODELS.md) | รายชื่อ AI model แนะนำสำหรับวิเคราะห์ตลาด (Cloud + Local) |
| [DATA_SOURCES.md](docs/DATA_SOURCES.md) | เทียบ market data provider ต่อ asset class + แผน fallback |
| [ROADMAP.md](docs/ROADMAP.md) | แผนพัฒนา M0–M5 + future Mobile |

ไฟล์กำกับการทำงาน: [CLAUDE.md](CLAUDE.md) (กฎ AI) · [MEMORY.md](MEMORY.md) (บทเรียน) · [spec.md](spec.md) (save point / สถานะปัจจุบัน)

## 🎯 Core Pillars
1. **Actionable Signals** — บอกจังหวะเข้า พร้อม entry/SL/TP/RR ที่ copy ไปใช้ได้ทันที ไม่ใช่แค่ลูกศรลอยๆ
2. **Prove It, Don't Promise It** — ทุก signal มีสถิติจาก simulator/backtest รองรับ โปร่งใส แพ้ชนะเห็นหมด
3. **TradingView-familiar** — ผู้ใช้ที่คุ้น TradingView หยิบใช้ได้ทันทีใน 1 นาที
4. **Your Brain, Your Choice** — เลือกสมอง AI ได้ ทั้งฟรี (Local) และ Cloud, ข้อมูล/คีย์อยู่ในเครื่องผู้ใช้

## 🔑 Key Specs
- **Markets:** หุ้น · คริปโต · ทองคำ (XAU) · น้ำมัน (WTI/Brent) · ค่าเงิน (FX)
- **Timeframes:** 5m · 10m · 15m · 30m · 45m · 60m · 4h · 1D · 1W · 1M · 1Y
- **Output:** signal schema มาตรฐาน (symbol, TF, side, entry, SL, TP1–3, R:R, confidence, เหตุผล)
- **Simulator:** backtest ย้อนหลัง + paper live-sim → dashboard สถิติ + history แพ้ชนะรายไม้
- **AI:** Local ผ่าน Ollama (ติดตั้งอัตโนมัติ) หรือ Cloud (Anthropic/OpenAI/Google/OpenRouter/GitHub Models — โชว์ model เมื่อใส่ key แล้วเท่านั้น)
- **Data:** provider ของเราเอง (ไม่ดึงจาก TradingView) — chart ใช้ Lightweight Charts

## 🗺️ Roadmap (สรุป)
`M0` Foundations → `M1` Chart + Realtime Data → `M2` AI Signals → `M3` Simulator + Dashboard → `M4` Indicator-AI Builder → `M5` Model Manager + Polish → *(future)* Mobile

ดูรายละเอียด + tasks ใน [ROADMAP.html/md](docs/ROADMAP.md)

## 📄 License
[**PolyForm Noncommercial 1.0.0**](LICENSE) — ใช้/แก้ไข/แจกจ่ายต่อได้ฟรี **เพื่อวัตถุประสงค์ที่ไม่ใช่เชิงพาณิชย์เท่านั้น** · ห้ามนำไปใช้หรือขายในเชิงพาณิชย์
(v0.1.0 ปล่อยเป็น MIT ไปแล้วยังเป็น MIT ถาวร — เปลี่ยนเป็น noncommercial ตั้งแต่ v0.1.1)

---
*ET Office · ทุกค่าตัวเลข/รายชื่อโมเดลเป็น anchor รอ review + tuning*
