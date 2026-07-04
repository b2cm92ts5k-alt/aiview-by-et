# DATA_SOURCES.md — แหล่งข้อมูลตลาด (AIView by ET)

> **รายการนี้เป็น anchor รอผู้ใช้เคาะ** — เลือก provider หลักต่อ asset class ตาม budget/free-tier
> หลักการ: **ไม่ดึง/redistribute ข้อมูลจาก TradingView** (ToS) — ใช้ provider ของเราเอง + วาดด้วย Lightweight Charts

---

## 1. ทำไมไม่ใช้ TradingView เป็นแหล่งข้อมูล
- TradingView ToS **ห้าม** scrape/redistribute ราคาของเขา + ไม่มี public data API สำหรับ 3rd-party app
- **Advanced Charts / Charting Library** ของ TV ฟรีแต่ต้องขอ agreement + redistribution จำกัด → ใส่ใน public MIT repo ไม่ได้
- ✅ สิ่งที่ใช้ได้: **Lightweight Charts** (Apache-2.0) = แค่ library วาดกราฟ ไม่มี data มาด้วย → เรา feed data เอง
- ดู [MEMORY.md](../MEMORY.md) `tv-data-not-redistributable`

## 2. Provider ต่อ asset class

### คริปโต (Crypto)
| Provider | Realtime | ฟรี | หมายเหตุ |
|----------|----------|-----|----------|
| **Binance API** ⭐ | WebSocket | ✅ ฟรี, generous limit | ตัวหลักคริปโต, OHLCV + WS ครบ |
| **ccxt** (lib) ⭐ | ขึ้นกับ exchange | ✅ | รวมหลาย exchange ใน interface เดียว (Binance/Bybit/OKX/…) |
| Bybit / OKX | WebSocket | ✅ | fallback / ตลาด futures อื่น |

### หุ้น / ทองคำ / น้ำมัน / ค่าเงิน (Stocks / Gold / Oil / FX)
| Provider | ครอบคลุม | Realtime (free) | Free tier | หมายเหตุ |
|----------|----------|-----------------|-----------|----------|
| **Twelve Data** ⭐ | หุ้น, FX, ทอง/น้ำมัน (commodities), crypto | บาง (delayed บน free) | มี free tier (จำกัด req/วัน + WS จำกัด) | ครอบคลุมกว้างสุดใน 1 ที่ = ตัวหลักที่ไม่ใช่คริปโต |
| **Finnhub** ⭐ | หุ้น (US เด่น), FX, crypto | WebSocket (บางส่วน free) | free tier ใช้ได้ | ข่าว + fundamentals แถม |
| **Polygon.io** | หุ้น, FX, options | realtime = เสียเงิน; free = delayed/EOD | free tier delayed | คุณภาพดี แต่ realtime ต้องจ่าย |
| Alpha Vantage | หุ้น, FX, commodities | delayed | free (rate limit ต่ำมาก) | สำรอง/backfill history |
| Yahoo Finance (unofficial) | กว้าง | delayed | "ฟรี" แต่ไม่เป็นทางการ | ใช้เป็น fallback อย่างระวัง ToS |

> **ทอง/น้ำมัน**: เข้าถึงผ่าน symbol ของ Twelve Data (เช่น `XAU/USD`, `WTI`/`BRENT`) หรือ futures/CFD proxy ของ provider นั้นๆ — เคาะ symbol mapping ตอน M1

## 3. สถาปัตยกรรม provider (สรุป — เต็มใน TDD §4)
- ทุก provider หลัง `DataProvider` interface เดียว (`fetch_ohlcv`, `subscribe`, `capabilities`)
- **normalize** → `Candle` schema กลาง (UTC ms)
- **resample** tf ที่ provider ไม่มี (10m/45m) จาก base เล็กกว่า
- **cache** OHLCV ลด rate-limit hit
- **fallback chain** ต่อ asset class: ลอง provider หลัก → ถ้า quota หมด/ล่ม → provider สำรอง

## 4. Rate-limit & cost strategy
- token-bucket ต่อ provider (กัน ban)
- cache history เชิงรุก, subscribe realtime เฉพาะ symbol ที่เปิดดู/มี signal ค้าง
- free tier พอสำหรับ dev + ผู้ใช้เดี่ยว; ผู้ใช้ใส่ key ของตัวเอง (BYOK) → ไม่ชน quota รวม
- key ทั้งหมดเก็บใน vault เข้ารหัส (ดู TDD §9)

## 5. Decision (เคาะแล้ว 2026-07-03)
- **Crypto**: Binance / ccxt (ฟรี realtime)
- **Non-crypto (หุ้น/ทอง/น้ำมัน/FX)**: **Twelve Data เป็น provider หลัก** (กว้างสุด จบในที่เดียว) · Finnhub/Polygon = สำรอง/fallback
- **BYOK (Bring Your Own Key)**: ผู้ใช้ใส่ free API key ของตัวเอง — ตอนเปิดแอพครั้งแรก guide ไปขอ key ฟรี. **ไม่ bundle key กลาง** (กัน quota รวมหมดเมื่อคนใช้เยอะ + ปลอดภัยกว่า)

## 6. ยังต้องเคาะตอน implement (M1)
- [ ] symbol mapping ทอง/น้ำมัน/ดัชนี ต่อ provider (เช่น `XAU/USD`, `WTI`)
- [ ] ระดับ realtime ที่ยอมรับได้บน free tier (บาง asset เป็น delayed) — กระทบ live-sim
