# AIView by ET — v0.1.0 Release Notes

> วันที่: 2026-07-10 · สถานะ: ครบ roadmap M0–M5 · License: MIT
> ⚠️ เครื่องมือวิเคราะห์เพื่อการศึกษา **ไม่ใช่คำแนะนำการลงทุน** — ผลจำลอง/backtest ไม่รับประกันผลในอนาคต

## ✅ ทำอะไรได้ (ทดสอบจริงแล้ว)

**Chart & Data**
- กราฟแท่งเทียน realtime สไตล์ TradingView (Lightweight Charts) — คริปโตผ่าน Binance **ฟรี ไม่ต้องมี key**
- Timeframe 11 ระดับ (5m–1Y) รวม 10m/45m/1Y ที่ engine resample ให้เอง
- Symbol search + watchlist แยกตาม asset class
- หุ้น/ทอง/น้ำมัน/FX ผ่าน Twelve Data — ใส่ key ฟรีของตัวเองในแท็บ Models (BYOK)

**AI Signals**
- กดวิเคราะห์ → AI คืน signal ครบ: LONG/SHORT, entry, SL, TP1-3, RR, confidence, เหตุผล
- Copy signal / Copy settings ไปใช้ต่อได้ทันที · เส้น entry/SL/TP ขึ้นบน chart
- MTF confluence table (trend + RSI ของ 5m/15m/1h/4h/1D)
- AI ใช้ได้ทั้ง **Local (Ollama — ฟรี 100%)** และ **Cloud** (Anthropic/OpenAI/Google/OpenRouter/GitHub Models — ใส่ key เอง โชว์ model เมื่อ key valid เท่านั้น)

**Simulator & Dashboard**
- ทุก signal จาก AI เปิด **ไม้จำลองอัตโนมัติ** ตามจนชน SL/TP/timeout (paper trading)
- **Backtest** บนข้อมูลย้อนหลังจริง (rule strategy หรือ indicator ที่สร้างเอง) — fee/slippage/risk ปรับได้
- Dashboard: winrate, Avg R, expectancy, profit factor, max drawdown, equity curve, breakdown ตาม model/TF/side
- History รายไม้ + Export CSV / JSON / Markdown report

**Indicator AI (จุดขายหลัก)**
- อธิบาย indicator ที่อยากได้เป็นภาษาไทย/อังกฤษ → AI สร้างเป็น DSL config → ระบบ **validate โดยรันจริง + quick backtest** → บันทึกแล้วใช้เป็น overlay บน chart หรือ strategy backtest ได้เหมือน built-in
- ปลอดภัย: AI ออก config ไม่ใช่โค้ด — ไม่มีทางรันโค้ดแปลกปลอมบนเครื่อง
- มี guardrail ปฏิเสธการ copy indicator ที่มีลิขสิทธิ์ (ต้อง public methodology + อ้าง source)

**Model Manager & Benchmark**
- เช็ค VRAM เครื่องอัตโนมัติ — model ที่ VRAM ไม่พอถูกล็อกพร้อมบอกเหตุผล
- ติดตั้ง local model จากในแอพ (pull พร้อม progress, มีทีละตัวประหยัดดิสก์)
- **Benchmark**: ให้หลาย model วิเคราะห์ข้อมูลชุดเดียวกันแล้วเทียบ winrate/PF จริง

**อื่นๆ**: desktop notification เมื่อมี signal/ไม้ปิด · workspaces · disclaimer ครั้งแรก · API key เก็บเข้ารหัสด้วย OS keychain ไม่ออกนอกเครื่อง

## ⚠️ ยังทำไม่ได้ / ข้อจำกัดที่ควรรู้ก่อนใช้

| เรื่อง | สถานะ |
|---|---|
| ยิงออเดอร์จริงเข้า exchange | **ไม่ทำโดยเจตนา** (นโยบายเฟสแรก) — ผู้ใช้ copy signal ไปวางเอง |
| ความเร็ว AI local | ขึ้นกับ GPU — RTX 2060S + qwen3:8b ใช้เวลาวิเคราะห์ ~1-3 นาที/ครั้ง |
| คุณภาพ signal | ยังไม่ผ่านการ tune — rule strategy backtest บน BTC ให้ winrate ~37% (แสดงตามจริง ไม่แต่งตัวเลข) ให้ใช้ dashboard/benchmark ตัดสินเอง |
| ข้อมูล non-crypto บน free tier | Twelve Data free = delayed + จำกัด request/วัน |
| Ollama | ต้องติดตั้งเองครั้งแรก (แอพเปิดหน้า download ให้) — auto-install เต็มรูปแบบยังไม่มา |
| Paper trades | หายเมื่อปิดแอพระหว่างไม้ยังเปิด (ไม้ค้างสถานะ open ไม่ resume) |
| ประวัติ/DB | เก็บในเครื่องเท่านั้น (`%APPDATA%/aiview`) — ไม่มี sync |
| Mobile / หลายจอ / drawing tools | ยังไม่มี (future) |
| Cloud provider | โค้ดพร้อม+เทสด้วย mock แล้ว แต่ยังไม่ได้ทดสอบกับ key จริง |

## การติดตั้ง

1. ดาวน์โหลด `AIView by ET Setup 0.1.0.exe` → ติดตั้ง (เลือกโฟลเดอร์ได้)
2. เปิดแอพ → ยอมรับ disclaimer → เห็นกราฟ BTC/USDT ได้ทันที (ไม่ต้องตั้งค่าอะไร)
3. อยากใช้ AI: ติดตั้ง [Ollama](https://ollama.com) แล้วไปแท็บ **Models** → เลือกรุ่นตาม VRAM → ติดตั้ง → กลับมาแท็บ Chart กด "วิเคราะห์"

## สำหรับนักพัฒนา

Dev setup + กติกา contribution: [CONTRIBUTING.md](../CONTRIBUTING.md) · สถาปัตยกรรม: [docs/](../docs)
