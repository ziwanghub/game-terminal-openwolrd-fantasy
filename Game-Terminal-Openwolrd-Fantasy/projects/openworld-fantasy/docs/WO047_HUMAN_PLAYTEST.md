# WO-047 — Human Feedback Round หลัง Synergy + Feel Polish

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-047 |
| **ขึ้นกับ** | WO-035–046 (Stat · Anima · Moments · Relic · Chorus · Foresight · **Synergy**) |
| **เวอร์ชัน** | `1.94.0-alpha`+ |
| **หลัก** | รู้สึกผู้เล่นจริง · polish โทน/ความถี่ · **ไม่ feature ใหญ่** · Auto ต้องไม่พัง |

**เอกสารระบบ:** [`STAT_ARCHITECTURE.md`](STAT_ARCHITECTURE.md) · §0.14–0.15  
**คู่มือก่อนหน้า:** [`WO045_HUMAN_PLAYTEST.md`](WO045_HUMAN_PLAYTEST.md)  
**Harness:** `python3 scripts/wo047_human_feedback_polish.py`  
**ผล:** `exports/WO047_PLAYTEST_LOG.md` · แบบฟอร์ม `exports/WO047_HUMAN_FEEDBACK.md`

---

## 0. DNA ล็อก (อย่าพัง)

| ใช่ | ไม่ใช่ |
|-----|--------|
| Soft Alert · Moment · Foresight · **Relic×Area Synergy** | dump ตัวเลข anima |
| Anima ≠ ขวัญ | resource ใหม่ · upgrade tree |
| Bond 2 / Chorus 3+ / Soft Cap 4+ | เควส storyline ยาว |
| Auto ถอดภาระ · area tension · cold moment | rewrite architecture |

---

## 1. เป้า playtest มือ ~90–120 นาที (H0–H10 + S-blocks)

### แกนเดิม (สั้น)

| Block | ทำ | ผ่านเมื่อ |
|-------|-----|----------|
| **H0 Bootstrap** | เซฟใหม่ · บทเรียน · รู้ V/P/G/B | เมนูหลักรู้ |
| **H1 Needs** | สำรวจ 6–10 · กิน/พัก | soft warn ไหล |
| **H2 Soft P + V** | ลงแต้ม · กด V | แยกขวัญ vs จิต |

### โฟกัส WO-047 (สำคัญ)

| Block | ทำ | โฟกัส Feel |
|-------|-----|------------|
| **H3 Foresight + Synergy** | ใส่ divine เรลิก → เดินเขา/ผลึก/เมือง · ใส่ hell → เดินพื้นที่ divine | ใบ้ **สะท้อน vs ขัด lean** ชัดไหม · ซ้ำไหม |
| **H4 Moment × Relic** | เข้าหา Mini-Moment ≥3 (ตรง lean อย่างน้อย 1 · ขัด lean อย่างน้อย 1) | Anima ชัดขึ้นตอน help ตรง lean ไหม |
| **H5 Relic single** | 1 ชิ้น · สำรวจ 5 ติก | จิตอุ่น/แผ่วรู้สึกได้ |
| **H6 Bond 2** | 2 lean เดียวกัน | Resonance ≠ ชิ้นเดียว |
| **H7 Chorus 3** | ชิ้นที่ 3 | Chorus ชัด · Soft Cap ถ้า 4 ไม่แรงเกิน |
| **H8 Chamber + location** | spar 2–3 ตอนอยู่พื้นที่ lean ตรง | spar ลึกขึ้นไหม |
| **H9 Auto + Synergy** | Auto 5–15 ติก · ขวัญต่ำ + เรลิกขัดพื้นที่ | ถอดสมเหตุสมผลไหม |
| **H10 Dungeon foresight** | แผงก่อนดัน | world + synergy ใบ้ |

**เส้นทางเร็ว (harness/admin ได้):**  
1) G ยืม storm หรือให้ `relic_storm_fang`+`relic_aegis_sky` → เขา/ผลึก  
2) ใส่ hell → ผลึก/เมือง (tension)  
3) void gear → `void_rift`

---

## 2. แบบบันทึกมือ → `exports/WO047_HUMAN_FEEDBACK.md`

```markdown
### รอบ WO-047 · วันที่: ____ · เวอร์ชัน: ____

| Block | ผ่าน | โน้ต | ปัญหา (ซ้ำ/เบา/แรง/ไม่รู้สึก/Auto) |
|-------|:----:|------|-------------------------------------|
| H0 Bootstrap | ☐ | | |
| H1 Needs | ☐ | | |
| H2 Soft P + V | ☐ | | |
| H3 Foresight×Synergy | ☐ | | |
| H4 Moment×Relic | ☐ | | |
| H5 Relic single | ☐ | | |
| H6 Bond 2 | ☐ | | |
| H7 Chorus 3 | ☐ | | |
| H8 Chamber+loc | ☐ | | |
| H9 Auto+Synergy | ☐ | | |
| H10 Dungeon FS | ☐ | | |

### Feel 1–5 (บังคับ)
| หัวข้อ | คะแนน | โน้ต |
|--------|:------:|------|
| Needs | __/5 | |
| Soft P / V | __/5 | |
| Anima รู้สึกได้ | __/5 | |
| Bond / Chorus | __/5 | |
| Mini-Moments | __/5 | |
| Soft Foresight | __/5 | |
| **Relic×Area Synergy** | __/5 | |
| Auto + Synergy | __/5 | |
| โลกมีชีวิตโดยรวม | __/5 | |

### คำถามบังคับ (WO-047)
1. ใส่เรลิก **ตรง** พื้นที่ vs **ขัด** พื้นที่ รู้สึกต่างชัดไหม?  
2. Foresight ใบ้ synergy ช่วยตัดสินใจไหม หรือซ้ำ?  
3. Moment ตอน lean ตรง ทำให้ Anima “มีชีวิต” ขึ้นไหม?  
4. Auto ถอดเมื่อขัดโลก + ขวัญต่ำ สมเหตุสมผลไหม?  
5. Hotfix ทันที 1–3 ข้อ:

1. …
2. …
3. …
```

---

## 3. Harness

```bash
cd projects/openworld-fantasy
python3 scripts/wo047_human_feedback_polish.py
# → exports/WO047_PLAYTEST_LOG.md · exports/wo047_playtest.json
```

---

## 4. เฟสงาน

| เฟส | งาน | ผล |
|-----|-----|-----|
| **1** | คู่มือ + แบบฟอร์ม | docs นี้ · feedback stub |
| **2** | Feel polish (synergy/anima/foresight/cap) | โค้ด |
| **3** | Harness + DNA lock + สรุป WO-048 | log · version |

---

## 5. Acceptance

- [x] คู่มือ H0–H10 โฟกัส synergy  
- [x] แบบฟอร์ม Feel 1–5  
- [x] Hotfix feel (ไม่ feature ใหญ่)  
- [x] Harness + unit ผ่าน  
- [x] STAT_ARCHITECTURE DNA note  
- [x] สรุป + แนะนำ WO-048  

---

## 6. Changelog

| วันที่ | เหตุการณ์ |
|--------|-----------|
| 2026-07-16 | สร้าง WO-047 guide · harness · feel polish |
