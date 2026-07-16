# WO-036 — Stat Architecture Polish & Playtest Round

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-036 |
| **ขึ้นกับ** | WO-035 Stat Architecture · WO-028 playtest pack |
| **เวอร์ชันเป้า** | `1.83.0-alpha`+ |
| **หลัก** | ความรู้สึกผู้เล่น · ไม่เพิ่ม resource ใหม่ · Auto ต้องไม่พัง |

**คู่มือร่วม:** [`WO028_HUMAN_PLAYTEST.md`](WO028_HUMAN_PLAYTEST.md) · [`STAT_ARCHITECTURE.md`](STAT_ARCHITECTURE.md)  
**Harness:** `python3 scripts/wo036_stat_playtest.py`  
**ผล:** `exports/WO036_PLAYTEST_LOG.md`

---

## 1. เป้า playtest มือ ~60–90 นาที

| Block | ทำ | โฟกัส WO-036 |
|-------|-----|----------------|
| **S0 Bootstrap** | เซฟใหม่ · hub · บทเรียน | รู้ **V=ประเมิน** · **P=soft** |
| **S1 Soft P** | ลงแต้มโจม/กัน 2–3 แต้ม | ข้อความ soft ชัดไหม · รู้สึก “หนาขึ้น” ไหม |
| **S2 Assess self** | กด **V** 2 ครั้ง (ครั้ง 2 ควร) | อ่านง่ายไหม · แยกขวัญ vs จิตวิญญาณ |
| **S3 Field Needs** | สำรวจ/กิน/พัก | หิว·ล้า·ขวัญ สมดุลไหม |
| **S4 Combat** | ไฟต์ 3–5 รอบมือ/ออโต้ | ชีพ soft + กายใจ · Auto ไม่พัง |
| **S5 Relic + Anima** | ใส่ legendary · เดิน 10 ติก · V อีกครั้ง | Anima รู้สึกได้ไหม · ภาระกดขวัญ |
| **S6 Chamber G** | ยืม · spar · ออก | เงินไม่เฟ้อ · สรุปภาระ |
| **S7 Dungeon soft** | foresight ก่อนดัน | soft ขวัญ/เรลิก |
| **S8 Economy** | 3–5 ไฟต์มี/ไม่มี crush | เงินไม่ระเบิด |

---

## 2. แบบบันทึกมือ (คัดลอก)

```markdown
### รอบ WO-036 · วันที่ · เวอร์ชัน

| Block | ผ่าน | โน้ต | P1/P2/P3 |
|-------|:----:|------|----------|
| S0 Bootstrap | ☐ | | |
| S1 Soft P | ☐ | | |
| S2 Assess V | ☐ | | |
| S3 Needs | ☐ | | |
| S4 Combat/Auto | ☐ | | |
| S5 Relic/Anima | ☐ | | |
| S6 Chamber | ☐ | | |
| S7 Dungeon | ☐ | | |
| S8 Economy | ☐ | | |

Feel 1–5:
 Soft P __/5 · ประเมิน V __/5 · Anima รู้สึก __/5 · Needs __/5 · Auto __/5

Hotfix ต้องการ:
1. …
2. …
```

### คำถามบังคับ (จากคำสั่ง WO)

1. ลงแต้ม P แบบ soft รู้สึกอย่างไร?  
2. ประเมินตัวเอง (V) ใช้ได้จริงไหม?  
3. Spirit / Anima รู้สึกได้หรือยัง?  
4. Needs 3 ตัวสมดุลไหม?

---

## 3. เฟสงาน

| เฟส | งาน | ผล |
|-----|-----|-----|
| **1** | Human / harness playtest + feedback log | `exports/WO036_PLAYTEST_LOG.md` |
| **2** | Hotfix soft text · Anima · assist · luck upgrade | โค้ด + เทส |
| **3** | ประเมินศัตรู lite · UI assess · economy check | โค้ด + เทส |

---

## 4. Acceptance

- [x] คู่มือ + harness  
- [x] Feedback เอกสารชัด  
- [x] Hotfix จากผลเทส  
- [x] ประเมินศัตรู soft  
- [x] Auto smoke ผ่าน  
- [x] สรุปจุดแข็ง/อ่อน + แนะนำ WO-037  

---

## 5. Changelog

| วันที่ | เหตุการณ์ |
|--------|-----------|
| 2026-07-15 | สร้าง WO-036 guide + harness + polish round |
