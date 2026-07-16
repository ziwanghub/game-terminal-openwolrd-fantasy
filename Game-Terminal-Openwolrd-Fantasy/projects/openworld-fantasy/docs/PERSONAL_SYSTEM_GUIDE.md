# Personal System Guide — เรื่องของฉัน (WO-053)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-053 |
| **สถานะ** | shipped @ `2.00.0-alpha` |
| **โมดูล** | `game/domain/personal_system.py` |
| **UX** | ตัวละคร → **V** = 「เรื่องของฉัน」 |
| **หลัก** | Soft Feel · Mystery · Narrative · ไม่โชว์ตัวเลขดิบ |

---

## 1. บทบาท

Personal System = จุดรวมตัวตนผู้เล่น

| ระบบ | ใน panel |
|------|----------|
| Grade 048/049 | ① เกรดรวม + แกน soft |
| Appraisal 051 | ② ชั้นอ่าน S–SSS |
| Anima 037+ | ③ ชีพ + จิตวิญญาณ |
| Relic / Bond 040–043 | ④ พันธะ · ภาระ |
| Faction 038+ | ⑤ สายตาโลก |
| Auto Growth 052 | ⑥ โหมดโต + แหล่งล่าสุด |
| Soft Journal | ⑦ บันทึกจังหวะ |

---

## 2. UX

| คีย์ | ผล |
|------|-----|
| **V** | เปิด panel 「เรื่องของฉัน」 |
| **d** (หลัง V) | อ่านชั้นลึก (appraisal paid) |
| **a** (หลัง V) | ประเมิน soft เดิม (V legacy) |
| Hub | บรรทัด compact + ใบ้ V |

ครั้งแรกที่เปิด: seed prologue journal  
“เริ่มต้นเส้นทาง — ยังไม่รู้ว่าตัวเองเป็นใคร”

---

## 3. Soft Journal

| kind | ตัวอย่างเหตุการณ์ |
|------|-------------------|
| temple | วิหารปลดเกรด |
| growth | เข้าโหมดไหลเอง · pulse สำคัญ |
| anima | สั่นกับเรลิก · ห้อง G |
| bond | เรโซแนนซ์ / คอรัส / ตึง |
| faction | สายตาเทพ/มาร/echo |
| appraisal | ตาคมขึ้น SS/SSS |
| milestone | prologue ฯลฯ |

- เก็บสูงสุด ~24 รายการ  
- `unique_key` กัน spam เหตุการณ์ซ้ำ  
- โชว์ newest-first · ติด Lv.

---

## 4. Hooks (อัตโนมัติ)

| แหล่ง | ฟังก์ชัน |
|--------|----------|
| วิหาร | `note_temple_story` |
| Phase-out P@30 | `note_auto_growth_story` |
| Growth pulse | `note_growth_pulse_story` (ทุก 3 pulse / เลื่อนชั้น) |
| Anima moment | `note_anima_story` |
| Bond sync | `note_bond_story` |
| Faction adjust | `note_faction_story` |
| Appraisal tier up | `note_appraisal_story` |

---

## 5. นอกขอบเขต WO-053

- Weakness recipes เต็มใน combat  
- Appraisal เฉลยสูตร SSS  
- Resource ใหม่ · Online · Bank/FX · Upgrade Tree  

---

## 6. ทดสอบ

| | |
|--|--|
| Unit | `tests/unit/test_wo053_personal_system.py` |
| Harness | `scripts/wo053_personal_system_playtest.py` |

---

## Changelog

| วันที่ | |
|--------|--|
| 2026-07-16 | WO-053 Personal System full surface + journal |
