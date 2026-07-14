# แผนพัฒนา / คิวงาน

**เกมปัจจุบัน:** `1.13.15-alpha` (`t0-needs-w0-rank`)

| Vision (ยังไม่ทำ) | เอกสาร |
|-------------------|--------|
| โลก-เซิร์ฟ · echo · อันดับท้าสู้ | [`WORLD_SERVER_VISION.md`](WORLD_SERVER_VISION.md) · เฟส **W0–W4** |
| UX-Tama · needs · เวลา hybrid | [`UX_TAMA_VISION.md`](UX_TAMA_VISION.md) · เฟส **T0–T3** |
| ขอแรง · สถานการณ์บนเซฟ · ร่วมทีมช่วย | [`HELP_SITUATION_VISION.md`](HELP_SITUATION_VISION.md) · เฟส **H0–H5** |

**แดชบอร์ดประเมินระบบ:** `python3 -m game.admin.dashboard`  
คะแนน/แผนใน `data/meta/system_dashboard.yaml` · แสดง text · export `exports/dashboard_latest.{txt,md}` · เมนูเกม **8 → 8**

---

## สถานะเฟส

| เฟส | สถานะ |
|-----|--------|
| Mode Shell · multi-ATB · multi-target · AoE balance | **1.13.5–1.13.10** (เสร็จหลัก) |
| แดชบอร์ดระบบเกม (ประเมิน + แผนเฟส · text) | **1.13.11** |
| Help Situation **H0–H4** | **1.13.12–1.13.14** |
| **T0** needs tick · **W0** rank soft | **1.13.15** |
| playtest (ขอแรง + needs + อันดับ) | คิวสั้น |
| **T1–T3** · **W1–W4** · **H5** | แผนแล้ว · ยังไม่เริ่ม |
| V Later (LLM / Web / realtime MP) | รอ |

### ปิดล่าสุด (1.13.15)

- **T0:** `needs` hunger/fatigue/morale · tick จากพัก/สำรวจ/เดินทาง/ไฟต์/กิน · soft บน PERSONAL  
- **W0:** อันดับ soft band · help title · คะแนนซ่อนรวมช่วยเหลือ · เขียน `rank_board.json`  

### ปิดก่อนหน้า (1.13.14)

- **H4:** policy เพื่อน · ชื่อเสียงผู้ช่วย · world_signals · เควสยื่นมือ  

### ปิดก่อนหน้า (1.13.13)

- **H1–H3:** กระดาน **G** · escrow · assist · inbox/chronicle  

### ปิดก่อนหน้า (1.13.12)

- **H0:** `situation` + consent ในดัน (เมนู 6) · บันทึกพักรอแรง  

### ปิดก่อนหน้า (1.13.11)

- แดชบอร์ดประเมินระบบ: YAML scores · เมตริก registry · roadmap · export text (txt/md)  

### ปิดก่อนหน้า (1.13.10)

- บาลานซ์ AoE/กลุ่ม · splash diminishing · soft splash XP · spawn กลุ่มตามเลเวล  

---

## คิวใกล้

| รายการ | หมายเหตุ |
|--------|----------|
| playtest 1–2 ชม. | ตรวจ AoE · Mode Shell · เมืองเริ่ม |
| เนื้อหา / เป้าเล่น (optional) | เติมเมื่อ playtest ชี้ |

---

## เฟส UX-Tama (วิสัยทัศน์ — ยังไม่ implement)

รายละเอียดเต็ม: **`docs/UX_TAMA_VISION.md`**

| เฟส | ชื่อ | สรุป | สถานะ |
|-----|------|------|--------|
| **T0** | Needs + tick | ท้อง/ล้า/ขวัญ · rest/explore/travel/combat/eat | **1.13.15** |
| **T1** | Load delta + แถบ | เวลาตอนโหลดเซฟ · แถบ soft ใน PERSONAL + ย่อสนาม | **รอ** |
| **T2** | Tama panel เต็ม | ASCII กลางจอ · เมนูกิน/พัก · mood soft | **รอ** |
| **T3** | Live optional | refresh/animation เบาตอนเปิด panel | **รอ** |

### หลักการล็อก (ย่อ)

1. RPG โลกเปิดเป็นหลัก — Tama อยู่จอสถานะ/เพื่อน ไม่กลืนทั้งเกม  
2. Soft bars เท่านั้น (ไม่สปอยล์สูตร)  
3. เวลา = **tick จาก action** + **delta ตอนโหลดเซฟ** (ไม่บังคับ process ค้าง 24 ชม.)  
4. Realtime ค้างจอ = optional ทีหลัง  
5. `needs = f(สถานการณ์เกม, เวลาที่ผ่าน)`  

### เงื่อนไขเริ่ม T0 (โดยประมาณ)

- PERSONAL hub ใช้งานได้ (มีแล้ว)  
- ตกลง needs ขั้นต่ำ (ท้อง / ล้า / จิต)  
- ไม่ชนคิว playtest ร้อน — หรือทำขนานได้  

---

## เฟส World Server (วิสัยทัศน์ — ยังไม่ implement)

รายละเอียดเต็ม: **`docs/WORLD_SERVER_VISION.md`**

| เฟส | ชื่อ | สรุป | สถานะ |
|-----|------|------|--------|
| **W0** | Rank board soft | อันดับ soft band · help title · rank_board.json | **1.13.15** |
| **W1** | Player echo | เงา snapshot จริง · สู้/คุย/ทีม · ไม่ทำร้ายเซฟเจ้าของ | **รอ** |
| **W2** | Rank challenge | ท้าอันดับ · จ่ายค่าหัว · ชนะได้ที่นั่งโชว์ | **รอ** |
| **W3** | World host | process โลกรันค้าง · client ต่อ | **รอ** |
| **W4** | Online lite | auth/anti-cheat เบา | **รอ** |

### เงื่อนไขเริ่ม W0 (โดยประมาณ)

- playtest หลัง 1.13.x ผ่านรอบหนึ่ง  
- ตลาด/เซฟโลกเสถียรพอ  
- ตกลงกฎค่าหัว + สิ่งที่โชว์บนบอร์ด  

**ลำดับแนะนำโดยรวม:** playtest → (T0–T1 หรือ เนื้อหา) → W0/H0 → W1 → H1–H3 → H4/W2 → …  
อย่ากระโดด W3–W4 / H5 ก่อน echo + assist async นิ่ง

---

## เฟส Help Situation / ขอแรงสังคม (วิสัยทัศน์ — ยังไม่ implement)

รายละเอียดเต็ม: **`docs/HELP_SITUATION_VISION.md`**

| เฟส | ชื่อ | สรุป | สถานะ |
|-----|------|------|--------|
| **H0** | Situation + consent | ดัน/วิกฤตบนเซฟ · เปิด/ปิดยินยอมแทรก | **1.13.12** |
| **H1** | กระดานสัญญาณ | รายการ `help.open` · เมนู **G** | **1.13.13** |
| **H2** | Offer + escrow | เงิน/ของตอบแทนล็อก · จ่าย/คืน | **1.13.13** |
| **H3** | Assist + chronicle | ยื่นมือ · สู้ · เขียนผลเซฟ P1 · inbox | **1.13.13** |
| **H4** | สังคมลึก | เพื่อน/ชื่อเสียงผู้ช่วย · เควสยื่นมือ · บันทึกโลก | **1.13.14** |
| **H5** | Live co-op | online พร้อมกันใน situation | **รอ** |

### หลักการล็อก (ย่อ)

1. สถานการณ์อยู่บน**เซฟเจ้าของ** — ไม่ใช่ใครก็เข้าได้  
2. ต้อง**ยินยอม (consent)** ก่อนแทรกเซฟแบบจำกัด  
3. ของตอบแทน **optional** · ใช้ escrow  
4. ร่วมทีมช่วย · async ก่อน realtime  
5. แยก echo ทั่วไป (ไม่แก้เซฟ) กับ assist (แก้ได้จำกัด)  

### เงื่อนไขเริ่ม H0 (โดยประมาณ)

- playtest แกน 1.13.x ผ่านรอบหนึ่ง  
- ดัน solo นิ่ง  
- ตกลง consent + escrow + ขอบเขตสิทธิ์ผู้ช่วย  

---

## V Later (คนละสาย)

| รายการ | หมายเหตุ |
|--------|----------|
| LLM local | NarrativePort หลัง field นิ่ง |
| Web IO | หลัง IO นิ่ง |
| Z-MOS เต็ม | multi-agent/ops — **ไม่** คุม logic เกม |
| Realtime MP + มอนโลก | หลัง H3/H5 foundation + W3+ — **ไม่ทำตอน solo** |

---

```bash
cd projects/openworld-fantasy
python3 -m game
python3 -m pytest -q
```
