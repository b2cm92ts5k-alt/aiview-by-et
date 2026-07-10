# AIView by ET — v0.1.1 Release Notes

> วันที่: 2026-07-10 · ต่อจาก [v0.1.0](RELEASE_NOTES_v0.1.0.md)
> ⚠️ เครื่องมือวิเคราะห์เพื่อการศึกษา **ไม่ใช่คำแนะนำการลงทุน**

## 🔻 เปลี่ยนแปลงสำคัญ

### 1. License เปลี่ยนเป็น PolyForm Noncommercial 1.0.0
- **v0.1.1 เป็นต้นไป**: source-available — ใช้/แก้ไข/แจกจ่ายต่อได้ **เพื่อวัตถุประสงค์ที่ไม่ใช่เชิงพาณิชย์เท่านั้น** · **ห้ามนำไปใช้หรือขายในเชิงพาณิชย์** (ดู [LICENSE](../LICENSE))
- ใช้ส่วนตัว/ศึกษา/วิจัย/องค์กรไม่แสวงกำไร = ได้เต็มที่
- หมายเหตุ: **v0.1.0 ที่ปล่อยเป็น MIT ไปแล้วยังคงเป็น MIT ถาวร** (เพิกถอนย้อนหลังไม่ได้) — การเปลี่ยนมีผลกับ v0.1.1 เป็นต้นไป
- dependency ภายนอก (Electron/React/ccxt/FastAPI ฯลฯ) ยังอยู่ภายใต้สัญญาของตัวเอง ไม่เปลี่ยนตาม

### 2. ปิดแอพแล้ว Ollama / local model ทำงานต่อ (bug fix)
- **เดิม**: บน Windows แอพ Electron ผูก `ollama serve` ที่แอพเป็นคนสตาร์ท ไว้กับ job object ของตัวเอง → ปิดแอพแล้ว Ollama + โมเดลที่โหลดอยู่ถูก kill ตาม
- **แก้แล้ว**: สตาร์ท `ollama serve` ผ่าน `Start-Process` ให้เป็น process อิสระคนละ job → **ปิดแอพแล้ว Ollama และโมเดลที่กำลังรันอยู่ทำงานต่อ** ไม่ถูกดับ
- ยืนยันเพิ่มเติม: การปิดแอพจัดการเฉพาะ engine (Python sidecar) ของตัวเองเท่านั้น ไม่ยุ่งกับ Ollama

## ✅ ฟีเจอร์ (เท่าเดิมกับ v0.1.0)
Chart realtime · AI signals (Local/Cloud) · simulator + dashboard + backtest · Indicator-AI builder · model manager + benchmark — รายละเอียดเต็มดู [RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md)

## การติดตั้ง
โหลด `AIView by ET Setup 0.1.1.exe` จากหน้า Releases → ติดตั้งทับตัวเก่าได้เลย

**Verified**: engine pytest 137/137 · frontend vitest 29/29 · packaged app spawn engine + health 200
