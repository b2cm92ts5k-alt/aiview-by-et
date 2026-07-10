# Contributing to AIView by ET

ยินดีรับ contribution! โปรเจกต์นี้เป็น MIT open-source — โปรดอ่านกติกาสำคัญก่อนส่ง PR

## ⚠️ กติกาที่ต่อรองไม่ได้

1. **NO LICENSE THEFT** — ห้าม copy/แปลโค้ด indicator ที่มีลิขสิทธิ์ (Pine Script ของ
   AlgoAlpha/LuxAlgo ฯลฯ) ทุก indicator ต้อง reimplement จาก *public methodology*
   และมี comment อ้างแหล่งที่มาของสูตรในไฟล์
2. **ห้ามดึง/redistribute ข้อมูลราคาจาก TradingView** — ใช้ data provider ของโปรเจกต์
   (Binance/ccxt, Twelve Data ฯลฯ) เท่านั้น
3. **SECRETS** — API key ต้องผ่าน vault (safeStorage) หรือ env เท่านั้น
   ห้าม log, ห้าม commit, ห้าม hardcode
4. **Financial disclaimer** — ห้ามเพิ่มข้อความการันตีกำไร/ชักชวนลงทุน
   และห้ามต่อ broker ยิงออเดอร์จริงอัตโนมัติ

## Dev setup

ดู Quickstart ใน [README.md](README.md) — สรุป: Node 20+, Python 3.11+,
`engine/.venv` + `pip install -e ".[dev]"`, `npm install`, `npm run dev`

## ก่อนส่ง PR ทุกครั้ง

```bash
# engine
cd engine
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m mypy app
.venv/Scripts/python -m pytest

# frontend (จาก root)
npm run lint
npm run typecheck
npm test
```

CI (GitHub Actions) รันชุดเดียวกัน — PR ต้องเขียวทั้งหมดก่อน merge

## โครงสร้าง

- `engine/` — Python FastAPI sidecar: data providers → indicators → AI → simulator → stats
- `apps/desktop/` — Electron main/preload (sidecar lifecycle, vault, Ollama manager)
- `apps/renderer/` — React UI (Lightweight Charts, Zustand, Tailwind)
- `packages/shared-types/` — FE/BE contract types
- `docs/` — design docs (ARCHITECTURE, TDD, FEATURES, ROADMAP ฯลฯ) — ยึดตามนี้
- `spec.md` — สถานะปัจจุบัน + decisions log · `MEMORY.md` — บทเรียนที่ห้ามพลาดซ้ำ

## แนวทางเขียนโค้ด

- เทสมาก่อน merge: indicator ใหม่ต้องมีเทสเทียบค่าคำนวณมือ/known-good
- ทุก timeframe/fill model/ค่า config ที่กระทบผลลัพธ์ → อยู่ใน config ไม่ hardcode
- UI ภาษาไทยเป็นหลัก · โค้ด/identifier/commit เป็นอังกฤษ
