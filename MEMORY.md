# MEMORY.md — บันทึกความผิดพลาด/บทเรียนของ AI ในโปรเจกต์นี้

> ไฟล์นี้คือ "ห้ามลืม" — ทุกครั้งที่ AI ทำพลาดแบบที่ไม่ควรเกิดซ้ำ ให้เพิ่ม entry ใหม่ที่นี่
> ทุก entry ต้องมี 3 ช่องเสมอ: **เกิดอะไร** / **ทำไม (root cause)** / **ครั้งหน้าทำยังไง**
> ห้ามเขียนแบบ "AI พลาดเรื่อง X" เฉยๆ — ต้องสั่งงานต่อได้จากบรรทัดเดียว
> entry ที่ยังไม่เกิดจริงแต่กันไว้ก่อน (seed) ระบุ `[SEED]` นำหน้า

---

## [2026-07-10] electron-builder ต้องการ electronVersion แบบ fixed ใน npm workspace {#electron-builder-fixed-version}
- **เกิดอะไร**: `electron-builder --win` fail ทันที `Electron version "^43.0.0" is a range, not a fixed version` — build installer ไม่ได้ ทั้งที่ `npm run dev` (electron รันปกติ) ผ่านหมด
- **ทำไม (root cause)**: repo เป็น npm workspaces → electron ถูก hoist ไป `node_modules` ราก ไม่ได้อยู่ใต้ `apps/desktop/node_modules` → electron-builder resolve เวอร์ชันจาก dependency range ใน package.json ของ desktop ไม่ได้ (ปกติมันอ่านจาก installed module)
- **ครั้งหน้าทำยังไง**: ใส่ `"electronVersion": "<fixed>"` ใน `build` config ของ electron-builder ตรงๆ (เช่น `43.1.0` — ดูจาก `npx electron --version`) · กฎนี้ใช้กับทุก monorepo/workspace ที่ hoist electron

## [SEED] ห้าม copy โค้ด indicator ที่มีลิขสิทธิ์ (Pine Script proprietary) — reimplement จาก public methodology เท่านั้น {#dont-copy-proprietary-pine}
- **เกิดอะไร**: ฟีเจอร์ "Indicator AI" (ข้อ 6) เรียนรู้จากต้นแบบ indicator ที่ใช้งานจริง — ต้นแบบในภาพคือ AlgoAlpha *Zero Lag Signals* และ LuxAlgo *Smart Money Concepts* ซึ่งเป็น Pine Script **มีลิขสิทธิ์/closed-source**
- **ทำไม (root cause)**: การ copy/แปลโค้ด Pine ที่มีลิขสิทธิ์มาเป็น Python = ละเมิดลิขสิทธิ์ + ขัด MIT ของเราเอง (open-source แต่มีโค้ดขโมยมา = ปนเปื้อน)
- **ครั้งหน้าทำยังไง**: implement indicator จาก **แนวคิดสาธารณะ** เท่านั้น — Zero-Lag EMA (Ehlers, public formula), SMC concepts (BOS/CHoCH/Order Block/FVG/Liquidity = methodology สาธารณะ อธิบายในตำรา/บทความ) → เขียนเป็นโค้ดเราเองจากสูตร ไม่เปิดไฟล์ Pine ต้นฉบับมาแปลบรรทัดต่อบรรทัด · ทุก indicator ในrepo ต้องมี comment อ้าง public source ของสูตร

## [2026-07-10] .gitignore pattern แบบ generic (`data/`) กลืน source dir จน CI แดง — และห้ามปิด milestone ก่อนเห็น CI เขียว {#gitignore-ate-source-dir}
- **เกิดอะไร**: commit M1 แล้ว CI พังด้วย `ModuleNotFoundError: No module named 'app.data'` — `.gitignore` มี `data/` (ตั้งใจ ignore runtime data) แต่มัน match ทุก dir ชื่อ data รวมถึง `engine/app/data/` ที่เป็น source ทั้งชุด → `git add -A` ข้ามเงียบๆ · local test ผ่านหมดเพราะไฟล์อยู่บนดิสก์ · ซ้ำร้ายคือประกาศ "M1 เสร็จ" แล้วเดินหน้า M2 ทั้งที่ CI ยังไม่เขียว
- **ทำไม (root cause)**: (1) pattern ignore แบบไม่ระบุ root (`data/`, `cache/`, `vault/`) match ได้ทุกความลึก (2) กฎ milestone gate บอกให้รอ CI เขียวแต่ไม่รอ — เชื่อ local เขียวแทน
- **ครั้งหน้าทำยังไง**: (1) dir ignore ประเภท runtime ให้ขึ้นต้น `/` เสมอ (root-relative) (2) หลัง commit ไฟล์ใหม่ ให้เช็ค `git status` ว่าไม่มี dir ที่ควร track โผล่เป็น `??` และถ้าตั้ง dir ชื่อสามัญ (data/cache/vault) ให้ `git check-ignore -v <ไฟล์>` ก่อน (3) milestone ปิดได้เมื่อ **CI บน GitHub เขียวจริงเท่านั้น** — local เขียวไม่นับ

## [SEED] ห้ามดึง/redistribute ข้อมูลราคาจาก TradingView — ใช้ provider เอง {#tv-data-not-redistributable}
- **เกิดอะไร**: ข้อ 4 อยาก "ดึงกราฟจริงจาก TradingView realtime" — แต่ TradingView ToS ห้าม scrape/redistribute ข้อมูลราคาของเขา และไม่มี public data API
- **ทำไม (root cause)**: สับสนระหว่าง "หน้าตาเหมือน TradingView" (ทำได้ด้วย Lightweight Charts) กับ "ใช้ data ของ TradingView" (ผิด ToS) — ถ้าดึง data เขามาใส่แอพ + simulator = เสี่ยงถูกแบน/ฟ้อง
- **ครั้งหน้าทำยังไง**: chart ใช้ **TradingView Lightweight Charts** (Apache-2.0, ฟรี, แค่ library วาดกราฟ ไม่มี data มาด้วย) + feed ข้อมูลจาก provider ของเราเอง (Binance/ccxt, Twelve Data, Finnhub, Polygon) · ห้ามใช้ Advanced Charts/Charting Library ใน public MIT repo (redistribution จำกัด ต้องขอ agreement) · ดู [DATA_SOURCES.md](docs/DATA_SOURCES.md)

## [SEED] ตัวเลข/รุ่นโมเดลใน AI_MODELS.md เป็น anchor รอผู้ใช้ยืนยัน — ห้ามเปลี่ยนเอง
- **เกิดอะไร**: รายชื่อ model "แนะนำ" + ตัวเลข VRAM/ราคาใน [AI_MODELS.md](docs/AI_MODELS.md) เป็นค่าตั้งต้นที่ผู้ใช้จะไปรีวิว/เคาะเอง
- **ทำไม (root cause)**: model landscape เปลี่ยนเร็ว (รุ่นใหม่ออกตลอด) — ถ้า AI ไปแก้ tag "แนะนำ" หรือตัวเลขเองโดยไม่ถาม อาจขัดกับที่ผู้ใช้ตัดสินใจไว้
- **ครั้งหน้าทำยังไง**: จะเพิ่ม/ถอด/เปลี่ยน tag แนะนำหรือตัวเลขในลิสต์โมเดล = ถามผู้ใช้ก่อนเสมอ อ้างอิงเหตุผล (benchmark/cost) ประกอบ
