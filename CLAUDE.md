# CLAUDE.md — กฎการทำงานในโปรเจกต์นี้ (AIView by ET)

@MEMORY.md

---

## ชั้น 1 · Guardrails (กฎหยุดพฤติกรรมพัง)

- **NO MAGIC**: ไม่รู้ห้ามเดา — ไม่รู้ path/schema/ชื่อ endpoint ให้เปิดดู `spec.md`/docs หรือถาม ไม่ใช่แต่งขึ้นมา
- **VERIFY BEFORE DONE**: ห้ามบอก "เสร็จ" ถ้ายังไม่รัน ไม่มีหลักฐาน — engine ต้องผ่าน `pytest`, frontend ต้องผ่าน `vitest`/build จริง (กฎสำคัญสุด)
- **DISSENT**: ก่อนทำของใหญ่ ให้เถียงก่อน — พังแล้วกระทบแค่ไหน, ถอยกลับได้มั้ย ถ้าไม่ชัวร์ ให้ถามก่อนลงมือ
- **SCOPE DRIFT**: สั่งแก้ bug 1 ตัว ห้ามดันไป refactor ทั้ง module เอง ถ้าจะทำเกินสโคป ให้เตือนก่อน
- **NO LICENSE THEFT** (เฉพาะโปรเจกต์นี้): ห้าม copy โค้ด indicator ที่มีลิขสิทธิ์ (Pine Script ของ AlgoAlpha/LuxAlgo ฯลฯ) ห้ามดึง/redistribute ข้อมูลราคาจาก TradingView — reimplement จาก *public methodology* เท่านั้น (ดู [[dont-copy-proprietary-pine]], [[tv-data-not-redistributable]])
- **FINANCIAL DISCLAIMER** (เฉพาะโปรเจกต์นี้): แอพนี้เป็นเครื่องมือวิเคราะห์/การศึกษา **ไม่ใช่คำแนะนำการลงทุน** — ห้ามเขียนข้อความในแอพที่การันตีกำไร/ชักชวนลงทุน, ห้ามต่อ broker ยิงออเดอร์จริงอัตโนมัติในเฟสแรกโดยไม่ถาม
- **SECRETS**: API key ของผู้ใช้เก็บเข้ารหัสในเครื่อง (OS keychain / safeStorage) — ห้าม log, ห้าม commit, ห้ามส่งขึ้น server ใด
- **R0/R1/R2**: แบ่ง decision ตามการถอยกลับได้
  - R0 (ถอยไม่ได้ เช่น force-push, delete, ลบไฟล์, drop schema/DB) = หยุดถามก่อนทำ
  - R1 (ถอยยาก เช่น refactor ใหญ่, แก้ DB schema, เปลี่ยน API contract) = ทำแล้วบอกผลให้รู้
  - R2 (ถอยง่าย เช่น แก้ bug เล็ก, เพิ่ม comment/test) = ทำเลยได้

## ชั้น 2 · Memory (ไม่ลืมบทเรียน)

- ไฟล์ [MEMORY.md](MEMORY.md) ถูก import ไว้ด้านบนแล้ว (`@MEMORY.md`) — โหลดทุก session อัตโนมัติ
- ทุกครั้งที่ AI ทำพลาดแบบที่ไม่ควรเกิดซ้ำ **ต้องเพิ่ม entry ใหม่ลงใน MEMORY.md** ก่อนจบงาน
- entry ต้องมี 3 ช่อง: เกิดอะไร / root cause / ครั้งหน้าทำยังไง — ห้ามเขียนแบบบอกแค่ว่าพลาดเรื่องอะไรโดยไม่มี root cause

## ชั้น 3 · Spec-driven ([spec.md](spec.md) = save point)

- **เริ่ม session**: อ่าน [spec.md](spec.md) ก่อนทำอะไรทั้งหมด เพื่อรู้ว่าทำอะไรอยู่ ถึงไหนแล้ว ตกลง architecture ไว้ยังไง
- **ทำ task เสร็จ**: ต้องอัพเดท spec.md (Current State, ตัดสินใจอะไรไป, ต่อไปทำอะไร) ก่อนถึงจะถือว่าจบงาน
- ห้ามบอกว่า "เสร็จ" ถ้ายังไม่อัพเดท spec.md
- กฎนี้ทำให้ `/clear` หรือ compact ได้โดยไม่ต้องเล่าใหม่ — context อยู่ในไฟล์ ไม่ได้อยู่ใน session
- เอกสารออกแบบอยู่ใน [`docs/`](docs/) — ยึดตามนั้น ห้ามแต่งกลไก/endpoint/ฟีเจอร์ที่ไม่มีในเอกสาร (ดู [ARCHITECTURE.md](docs/ARCHITECTURE.md), [TDD.md](docs/TDD.md), [FEATURES.md](docs/FEATURES.md))

## ชั้น 4 · Work Pattern ของผู้ใช้

**ตัดสินใจยังไง / ชอบ-ไม่ชอบอะไร**
- ต้องการ "confirm ก่อนสร้าง" — เสนอแนวคิด/แผนก่อนแล้วให้ยืนยัน ไม่ใช่ลงมือทำทันทีกับงานที่มีหลายทางเลือก
- ยึดตาม design docs ที่มีอยู่จริง (`docs/`) ห้ามแต่งกลไก/ตัวเลข/endpoint ที่ไม่มีในเอกสาร
- ชอบงานที่ทำเสร็จแล้วมีหลักฐานชัดเจนว่า "ใช้ได้จริง" ไม่ใช่แค่ "เขียนโค้ดแล้ว"
- ตัวเลข balance/perf/model ที่ "ล็อกแล้ว" → ห้ามเปลี่ยนเองโดยไม่ถาม อ้างอิงจาก docs/memory เสมอ

**น้ำเสียง**
- สื่อสารแบบไทย ตรงประเด็น กระชับ — คำถามง่ายไม่ต้องมี section เยอะ
- UI ของแอพเป็นภาษาไทยเป็นหลัก, โค้ด/identifier/commit เป็นอังกฤษ

## เทคโนโลยีหลัก (อ้างอิงเร็ว)

- **Frontend**: Electron + React + TypeScript + Vite + Tailwind + TradingView Lightweight Charts
- **Engine**: Python + FastAPI (sidecar process) — market data, indicators, simulator/backtest, AI orchestration
- **Storage**: SQLite (trade history / stats)
- **AI**: provider abstraction — Ollama (local) + Anthropic/OpenAI/Google/OpenRouter/GitHub Models (cloud, key-gated)
- **Data**: multi-provider — Binance/ccxt (crypto), Twelve Data/Finnhub/Polygon (stocks/gold/oil/FX)
- **Tests**: `pytest` (engine), `vitest` + Playwright (frontend)
- **License**: MIT · open-source บน GitHub
