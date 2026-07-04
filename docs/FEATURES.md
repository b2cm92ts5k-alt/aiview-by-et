# FEATURES.md — AIView by ET

> แตก concept ข้อ 1–7 (+ ของแถม) เป็น feature spec. อ้างอิงกับ [ARCHITECTURE.md](ARCHITECTURE.md) / [TDD.md](TDD.md).
> สถานะทั้งหมด = 📋 planned (ยังไม่เขียนโค้ด)

---

## F1 · Signal & Copy-to-Trade (concept ข้อ 1)
**ทำอะไร**: AI แจ้งจังหวะเข้า buy/sell แบบ futures ผู้ใช้ copy รูปแบบ + การตั้งค่าไม้ไปเทรดในแอพจริงได้

**Signal schema มาตรฐาน** (ใช้ร่วมทั้งแอพ):
```
Signal = {
  symbol, timeframe, side (long/short),
  entry, stopLoss, takeProfit[1..3],
  riskReward, positionSizeHint, leverageHint,
  confidence (0-100), reason (ข้อความอธิบาย),
  indicatorsUsed{}, model, createdAt, validUntil
}
```
**UI**:
- Signal card บน chart + panel ข้างขวา (entry/SL/TP/RR/confidence)
- ปุ่ม **Copy**: คัดลอกเป็นข้อความ/JSON พร้อม preset (ไม้, ขนาด, leverage) เอาไปวางในแอพเทรดจริง
- ปุ่ม **Copy settings**: คัดลอกการตั้งค่าที่ AI ใช้ (indicator set, timeframe, risk params)
- (เฟสหลัง) template สำหรับ exchange ยอดนิยม
> ⚠️ ไม่ยิงออเดอร์จริงอัตโนมัติในเฟสแรก — ผู้ใช้เป็นคนวางเอง (financial disclaimer)

## F2 · Simulator + Data Dashboard + History (concept ข้อ 2)
**ทำอะไร**: จำลองการเทรดจริงของ AI, เก็บสถิติทั้งหมดเป็น dashboard + ประวัติรายไม้ แพ้ชนะ

**Simulator**:
- **Backtest** ย้อนหลังบน historical (เร็ว, ได้สถิติทันที)
- **Paper live-sim** เดินตาม signal realtime, ปิดไม้เมื่อชน SL/TP/timeout
- config: fee, slippage, ทุนเริ่มต้น, risk ต่อไม้

**Dashboard** (สถิติ):
- Winrate, Avg R-multiple, Expectancy, Profit Factor, Max Drawdown
- Equity curve, PnL รายวัน/สัปดาห์/เดือน
- Breakdown ต่อ symbol / timeframe / model / side
- ตารางเทียบ "AI model ไหน / indicator set ไหน แม่นสุด"

**History**:
- ตารางรายไม้: entry/exit, ผล (win/loss/BE), R-multiple, เหตุผล, model ที่ใช้
- filter/sort/search + export CSV/JSON เพื่อวิเคราะห์ต่อ

## F3 · Timeframes (concept ข้อ 3)
รองรับ: **5m · 10m · 15m · 30m · 45m · 60m · 4h · 1D · 1W · 1M · 1Y**
- tf ที่ provider ไม่มีตรงๆ → engine resample จาก base เล็กกว่า
- ผู้ใช้ตั้งค่า timeframe ที่จะให้ AI วิเคราะห์/ trade ได้อิสระต่อ workspace
- **MTF confluence table** (เหมือนตาราง 5/15/60/240/1D ในภาพต้นแบบ): โชว์ทิศ Bullish/Bearish แต่ละ TF พร้อมกัน

## F4 · Realtime Chart & Data (concept ข้อ 4)
**ทำอะไร**: ดึงกราฟจริง realtime มาแสดงในแอพ
- **Chart engine**: TradingView **Lightweight Charts** (Apache-2.0) — วาด candlestick + overlay indicator + signal markers
- **Data**: provider ของเราเอง (Binance/ccxt, Twelve Data, Finnhub, Polygon) — **ไม่ดึงจาก TradingView** (ToS)
- realtime ผ่าน WebSocket ของ provider ถ้ามี ไม่งั้น polling
- ดูรายละเอียด provider ต่อ asset class ใน [DATA_SOURCES.md](DATA_SOURCES.md)
> หมายเหตุ: "หน้าตาเหมือน TradingView" ทำได้ด้วย Lightweight Charts + UI; "data ของ TradingView" ใช้ไม่ได้ (ดู [MEMORY.md](../MEMORY.md) `tv-data-not-redistributable`)

## F5 · TradingView-like UX/UI (concept ข้อ 5)
**เป้าหมาย**: ผู้ใช้ที่คุ้น TradingView ใช้เป็นทันที
- Layout: symbol search bar บน, toolbar เครื่องมือซ้าย, chart กลาง, panel indicator/signal ขวา, timeframe selector, watchlist
- Dark theme neon (อิงภาพต้นแบบ), MTF signal table มุมขวาบน
- Interaction: crosshair, drawing tools (เฟสหลัง), หลาย layout/workspace
- ⚠️ เลียน "ความคุ้นเคย/patterns" ได้ แต่ไม่ copy asset/โลโก้/โค้ดของ TradingView

## F6 · Indicator AI Builder (concept ข้อ 6)
**ทำอะไร**: สร้าง indicator AI ของเราเอง โดยเรียนรู้จากต้นแบบ indicator ที่ใช้งานได้จริง
- ผู้ใช้อธิบาย methodology / logic ที่ต้องการ (ภาษาไทย/อังกฤษ) → AI สังเคราะห์เป็น indicator config/โค้ด
- Pipeline: describe → AI generate → **validate (compile/run บน sample data)** → **backtest** → เก็บถ้าผ่าน
- indicator ที่ได้ใช้ใน F1 (signal) และ F2 (simulator) ได้เหมือน built-in
- ⚠️ **legal guardrail**: เรียนจาก *public methodology* เท่านั้น (Zero-Lag EMA, SMC ฯลฯ) — ห้าม import/copy Pine Script ที่มีลิขสิทธิ์ (ดู [MEMORY.md](../MEMORY.md) `dont-copy-proprietary-pine`)

## F7 · AI Model Selector (concept ข้อ 7)
**ทำอะไร**: เลือกสมอง AI ได้ทั้ง Local และ Cloud

**Local (Ollama) — VRAM-gated install flow** (ตามที่พี่เคาะ):
1. เปิดแอพ/เข้าหน้า model ครั้งแรก → **เช็ค VRAM (+ RAM) ของเครื่องก่อนเสมอ**
2. เลือก **default model อัตโนมัติตาม VRAM ที่มี** (เช่น <8GB→7B, ~12GB→14B, ~24GB→32B) แล้วติดตั้ง Ollama + pull ให้ (stream progress)
3. รายการ model ที่เลือกลงใหม่ได้: **รุ่นที่ VRAM ถึง = เลือกได้; รุ่นที่ VRAM ไม่ถึง = lock + ขึ้นข้อความบอก** (เช่น "ต้องการ ~24GB, เครื่องมี 12GB")
4. **นโยบาย single active local model**: เลือกลงรุ่นใหม่ → ระบบ **uninstall รุ่นเก่าออกก่อน** แล้วค่อย pull รุ่นใหม่ (ประหยัดดิสก์, มีทีละตัว)
5. แสดงพื้นที่ดิสก์/VRAM ที่ต้องใช้ก่อนยืนยันทุกครั้ง

**Cloud**:
- ใส่ API key ของ provider (Anthropic/OpenAI/Google/OpenRouter/GitHub Models) → **โชว์ list model เฉพาะเมื่อ key valid เท่านั้น**

**ทั่วไป**:
- **Tag "แนะนำ"** ติดที่ model ที่วิเคราะห์ตลาดได้ดี (ดู [AI_MODELS.md](AI_MODELS.md))
- สลับ model ต่อ workspace ได้ + เทียบผลแต่ละ model ใน dashboard (F2)

---

## ของแถม (จากคำแนะนำเพิ่มเติม — รอผู้ใช้เคาะว่าเอาเฟสไหน)
- **F8 Alerts/Notifications**: desktop toast + เสียง เมื่อมีจังหวะเข้า / ชน SL-TP
- **F9 Risk gate & Disclaimer**: หน้ายอมรับ disclaimer ตอนเปิดครั้งแรก + ตั้ง max risk เตือนเมื่อเกิน
- **F10 Workspaces/Layouts**: หลาย layout เหมือน TradingView, save/restore
- **F11 Export/Report**: สรุปผลเป็น PDF/CSV
- **F12 (future) Mobile**: reuse engine API, UI ใหม่ (React Native/Expo)
