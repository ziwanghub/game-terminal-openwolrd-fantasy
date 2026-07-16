# WO-045 — Playtest Polish รอบใหญ่ (Human + Harness)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-045 |
| **ขึ้นกับ** | WO-035–044 (Stat · Anima · Relations · Moments · Relic · Chorus · Foresight) |
| **เวอร์ชัน** | `1.92.0-alpha`+ |
| **หลัก** | รู้สึกผู้เล่น · สมดุล · **ไม่เพิ่ม feature ใหญ่** · Auto ต้องไม่พัง |

**เอกสารระบบ:** [`STAT_ARCHITECTURE.md`](STAT_ARCHITECTURE.md)  
**Harness รวม:** `python3 scripts/wo045_playtest_polish.py`  
**ผล:** `exports/WO045_PLAYTEST_LOG.md` · แบบฟอร์มมือด้านล่าง

---

## 0. DNA ล็อกชั่วคราว (อย่าพัง)

| ใช่ | ไม่ใช่ |
|-----|--------|
| Soft Alert · Soft Moment · Soft Foresight | dump ตัวเลข anima / power |
| Anima ≠ ขวัญ · ≠ `relic.spirit_*` | resource ใหม่ · upgrade tree |
| Relic lean → Bond → Chorus → Soft Cap | เควส storyline ยาว |
| Mini-Moment ครบ 8 พื้นที่ | UI ใหม่ใหญ่ |
| Auto ถอดภาระ / เลี่ยง moment เย็น | rewrite สถาปัตย์ |

---

## 1. เป้า playtest มือ ~90–120 นาที

| Block | ทำ | โฟกัส WO-045 |
|-------|-----|----------------|
| **H0 Bootstrap** | เซฟใหม่ · บทเรียน · Hub | รู้ **V / P / G / B / Auto** |
| **H1 Needs** | สำรวจ 8–12 รอบ · กิน/พัก | หิว·ล้า·ขวัญ ไหลไหม · soft warn |
| **H2 Soft P + V** | ลงแต้ม 2–3 · กด V | soft ชัด · แยกขวัญ vs จิตวิญญาณ |
| **H3 Foresight travel** | เดินทาง 4–6 พื้นที่ (ซ้ำ 1 พื้นที่) | ใบ้สายตา **ไม่ซ้ำรำคาญ** · รู้ lean |
| **H4 Mini-Moments** | เข้าหา sight 〔โลก〕 ≥3 ครั้ง · ช่วย/ปฏิเสธ/หลบ | รู้สึกโลก · faction เปลี่ยน soft |
| **H5 Relic single** | ใส่ 1 เรลิก · เดิน 5–8 ติก | Anima อุ่น/แผ่ว · ภาระขวัญ |
| **H6 Bond 2** | ใส่ 2 lean เดียวกัน (เช่น storm+aegis) | Resonance ชัด vs ชิ้นเดียว |
| **H7 Chorus 3** | ใส่ชิ้นที่ 3 (laurel/greaves/sandals) | Chorus ≠ Resonance · Soft Cap ถ้า 4 |
| **H8 Chamber G** | ยืม · spar 2–3 · สรุป · ออก | เงินไม่เฟ้อ · จิตสั่น spar |
| **H9 Combat + Auto** | มือ 3 ไฟต์ · Auto 5–10 ติก | Auto ถอดเรลิกเมื่อขวัญ/Anima แย่ |
| **H10 Dungeon soft** | เปิด foresight ก่อนดัน | แผง foresight มี world gaze + เสบียง |

**เส้นทางเรลิกแนะนำ (ไม่บังคับเคลียร์บอส):** ห้อง **G** ยืม storm/hell/void · หรือให้ไอเทมจาก harness/admin ถ้าเทสเร็ว

---

## 2. แบบบันทึกมือ (คัดลอกไป `exports/WO045_HUMAN_FEEDBACK.md`)

```markdown
### รอบ WO-045 · วันที่: ____ · เวอร์ชัน: ____

| Block | ผ่าน | โน้ตสั้น | ปัญหา (ซ้ำ/เบา/แรง/ไม่รู้สึก) |
|-------|:----:|----------|-------------------------------|
| H0 Bootstrap | ☐ | | |
| H1 Needs | ☐ | | |
| H2 Soft P + V | ☐ | | |
| H3 Foresight travel | ☐ | | |
| H4 Mini-Moments | ☐ | | |
| H5 Relic single | ☐ | | |
| H6 Bond 2 | ☐ | | |
| H7 Chorus 3 | ☐ | | |
| H8 Chamber | ☐ | | |
| H9 Combat/Auto | ☐ | | |
| H10 Dungeon foresight | ☐ | | |

### Feel 1–5 (บังคับ)
| หัวข้อ | คะแนน | โน้ต |
|--------|:------:|------|
| Needs (หิว/ล้า/ขวัญ) | __/5 | |
| Soft P / ประเมิน V | __/5 | |
| Anima รู้สึกได้ | __/5 | |
| Relic Bond / Chorus | __/5 | |
| Mini-Moments | __/5 | |
| Soft Foresight ใบ้โลก | __/5 | |
| Auto สมเหตุสมผล | __/5 | |
| โลกมีชีวิตโดยรวม | __/5 | |

### คำถามบังคับ
1. Anima ต่างจากขวัญชัดไหม?  
2. ใส่เรลิก 2 ชิ้น vs 3 ชิ้น รู้สึกต่างไหม?  
3. Foresight / ใบ้ moment ซ้ำหรือเงียบเกินไหม?  
4. Auto ช่วยหรือขัดใจ?  
5. จุดที่อยาก hotfix ทันที 1–3 ข้อ:

Hotfix ต้องการ:
1. …
2. …
3. …
```

---

## 3. Harness (อัตโนมัติ)

```bash
cd projects/openworld-fantasy
python3 scripts/wo045_playtest_polish.py
# ผล: exports/WO045_PLAYTEST_LOG.md · exports/wo045_playtest.json
```

ครอบคลุม smoke: Needs · Anima equip · Bond/Chorus · Moments ครบพื้นที่ · Foresight · Chamber spar · Auto unequip · Auto fight

---

## 4. เฟสงาน WO-045

| เฟส | งาน | ผล |
|-----|-----|-----|
| **1** | คู่มือมือ + แบบฟอร์ม + harness รวม | docs นี้ · script |
| **2** | Hotfix จากจุดอ่อนสะสม + ผล harness | foresight · moment · soft tone · auto |
| **3** | Verify · ล็อก DNA ใน STAT_ARCHITECTURE · สรุป WO-046 | log + version |

---

## 5. Acceptance

- [x] คู่มือ Human 90–120 นาที + แบบฟอร์ม  
- [x] Harness รวม + export log  
- [x] Hotfix polish (ไม่ feature ใหญ่)  
- [x] Unit/smoke ผ่าน  
- [x] STAT_ARCHITECTURE DNA lock โน้ต  
- [x] สรุปจุดแข็ง/อ่อน + แนะนำ WO-046  

---

## 6. Changelog

| วันที่ | เหตุการณ์ |
|--------|-----------|
| 2026-07-16 | สร้าง WO-045 guide · harness · polish round |
