# AI_MODELS.md — โมเดล AI สำหรับวิเคราะห์ตลาด (AIView by ET)

> **รายการนี้เป็น anchor รอผู้ใช้ review/เคาะ** — model landscape เปลี่ยนเร็ว, tag "⭐ แนะนำ" และตัวเลขปรับได้
> อ้างอิงกฎ: จะเปลี่ยน tag แนะนำ/ตัวเลข = ถามก่อน (ดู [MEMORY.md](../MEMORY.md))
> เกณฑ์ที่ให้น้ำหนักสำหรับงานนี้: **reasoning เชิงตัวเลข/หลาย timeframe**, ความเสถียรของ **structured JSON output**, context length, ต้นทุน, ความเร็ว, (bonus) **vision** อ่านภาพชาร์ต

---

## A. Cloud models (key-gated — โชว์เมื่อใส่ API key แล้วเท่านั้น, ข้อ 7)

### Anthropic — Claude
| Model | Tag | จุดเด่นสำหรับตลาด | หมายเหตุ |
|-------|-----|------------------|----------|
| Claude Opus 4.x | ⭐ แนะนำ | reasoning ลึก, วิเคราะห์ confluence หลาย TF + อธิบายเหตุผลดี, JSON เสถียร | ต้นทุน/ไม้สูงสุด — เหมาะ signal สำคัญ/สรุป |
| Claude Sonnet | ⭐ แนะนำ | สมดุล reasoning/speed/cost, vision อ่านชาร์ตได้ | ตัวหลักสำหรับใช้งานประจำ |
| Claude Haiku | — | เร็ว/ถูก | เหมาะ pre-filter / MTF table เร็วๆ |

### OpenAI
| Model | Tag | จุดเด่น | หมายเหตุ |
|-------|-----|---------|----------|
| GPT-5 / o-series (reasoning) | ⭐ แนะนำ | reasoning เข้ม, tool-use ดี, JSON เสถียร | ตัวเลือกหลักฝั่ง OpenAI |
| GPT-5 mini / นน. เล็ก | — | เร็ว/ถูกกว่า | งาน bulk / MTF scan |

### Google — Gemini
| Model | Tag | จุดเด่น | หมายเหตุ |
|-------|-----|---------|----------|
| Gemini 2.x/3 Pro | ⭐ แนะนำ (vision) | context ยาวมาก + multimodal อ่านภาพชาร์ตเก่ง | ดีเวลาต้องดู pattern จากภาพ |
| Gemini Flash | — | เร็ว/ถูก, context ยาว | scan หลาย symbol พร้อมกัน |

### Gateways (รวมหลาย provider)
| Provider | Tag | จุดเด่น | หมายเหตุ |
|----------|-----|---------|----------|
| OpenRouter | — | key เดียวเข้าถึงหลายโมเดล (รวม open models), เทียบราคา/สลับง่าย | ดีสำหรับทดลองหา model ที่แม่นสุด |
| GitHub Models | — | ลองโมเดลหลายเจ้าได้ (มี free/quota) | เหมาะ prototype |

## B. Local models ผ่าน Ollama (ติดตั้งอัตโนมัติเมื่อผู้ใช้เลือก, ข้อ 7)

| Model (Ollama) | Tag | ขนาด | VRAM แนะนำ | จุดเด่นสำหรับตลาด |
|----------------|-----|------|-----------|------------------|
| Qwen2.5 / Qwen3 Instruct 14B | ⭐ แนะนำ | 14B | ~12 GB | reasoning ตัวเลข/JSON ดีสุดในกลุ่มฟรีขนาดกลาง |
| Qwen2.5 / Qwen3 Instruct 32B | ⭐ แนะนำ (ถ้าเครื่องไหว) | 32B | ~24 GB | คุณภาพใกล้ cloud tier กลาง |
| DeepSeek-R1 (distill 7B/14B/32B) | ⭐ แนะนำ (reasoning) | 7–32B | 8–24 GB | chain-of-thought แรง เหมาะ signal reasoning |
| Llama 3.x Instruct 8B | — | 8B | ~8 GB | สมดุล, community/tooling ใหญ่ |
| Llama 3.x 70B | — | 70B | ~40 GB+ | คุณภาพสูง แต่กินเครื่องหนัก |
| Qwen2.5 7B / Mistral 7B | — | 7B | ~8 GB | เบาสุด สำหรับเครื่อง entry-level / MTF scan |

**หมายเหตุ VRAM** (โดยประมาณ, quantized Q4): 7–8B ≈ 8 GB · 14B ≈ 12 GB · 32B ≈ 24 GB · 70B ≈ 40 GB+

### VRAM-gated install (นโยบายที่เคาะแล้ว)
1. **เช็ค VRAM/RAM ก่อนเสมอ** ก่อนลง default model
2. default model เลือกอัตโนมัติตาม VRAM: `<8GB → 7B` · `~12GB → 14B` · `~24GB → 32B` (+40GB → 70B)
3. รุ่นที่ VRAM **ถึง = เลือกลงได้**; รุ่นที่ **ไม่ถึง = lock + ขึ้นข้อความ** บอกความต้องการ vs ที่เครื่องมี
4. **single active local model**: เลือกลงรุ่นใหม่ → **uninstall รุ่นเก่าออกก่อน** แล้ว pull รุ่นใหม่ (มีทีละตัว ประหยัดดิสก์)
5. โชว์ VRAM + พื้นที่ดิสก์ที่ต้องใช้ก่อนยืนยัน
> รายละเอียด UX ดู [FEATURES.md](FEATURES.md) §F7

## C. คำแนะนำการเลือก (default policy)
- **เริ่มต้น/ฟรี 100%**: Ollama + **Qwen 14B** (หรือ DeepSeek-R1 distill ถ้าอยากได้ reasoning เข้ม)
- **คุณภาพสูงสุด**: Cloud — **Claude Opus/Sonnet** หรือ **GPT-5/o-series** สำหรับ signal สำคัญ + สรุป
- **ต้องอ่านภาพชาร์ต**: **Gemini Pro** หรือ Claude Sonnet (vision)
- **อยากทดลองหลายตัวถูกๆ**: **OpenRouter**
- **แพทเทิร์นแนะนำ**: ใช้ model เล็ก/เร็ว pre-scan หลาย symbol → ยกเฉพาะตัวน่าสนใจให้ model ใหญ่ยืนยัน (ลดต้นทุน)

## D. สิ่งที่ยังต้องเคาะ
- [ ] ยืนยัน tag "⭐ แนะนำ" ชุดนี้ (หรือปรับ)
- [x] **default model = เลือกตาม VRAM อัตโนมัติ** (VRAM-gated install ด้านบน) — เคาะแล้ว
- [ ] จะทำ **benchmark ในแอพ** (ให้แต่ละ model วิเคราะห์ชุดเดียวกันแล้วเทียบ winrate ใน simulator) เป็นฟีเจอร์เลยไหม — จะทำให้ "แนะนำ" มีข้อมูลจริงรองรับ แทนความเห็น
