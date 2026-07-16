# Appraisal Guide — อ่านชั้น (WO-051)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-051 |
| **สถานะ** | shipped @ `1.98.0-alpha` |
| **โมดูล** | `game/domain/appraisal.py` |
| **สกิล** | `soft_appraise` / 「อ่านชั้น」 |
| **หลัก** | Soft Feel · Mystery · ไม่โชว์ตัวเลขดิบ |

---

## 1. บทบาทใน DNA

Appraisal = ทางหลักในการ **รู้ตัวเองและศัตรู** หลังวิหารปลดเกรด

| ทาง | ใช้ |
|-----|-----|
| **V** (ตัวละคร) | ประเมินตัวเอง + ชั้นลึกเมื่อ tier ≥ S |
| **I / ?** (ไฟต์) | อ่านศัตรู soft · ไม่เสียเทิร์น |
| **วิหาร W** | ปลดเกรด + seed ชั้น S + สกิลอ่านชั้น |

---

## 2. ชั้น S – SS – SSS

| ชั้น | ศัตรู | ตัวเอง |
|------|--------|--------|
| **base** | soft band เดิม (อาการ/ภัย/คม) | soft ชีพ/จิต · ยังไม่ตัวอักษร |
| **S** | + ระดับประมาณ 〔ตัวอักษร〕 + ขั้น soft | + Grade Surface (ตัวอักษร + tier) |
| **SS** | + จุดอ่อน soft (ธาตุ/แนวทาง) | + แกนเด่น/บาง · เรลิกภาระ |
| **SSS** | + Soft Recipe 1–2 สาย (เช่น น้ำ+ลม → น้ำแข็ง) | + สายเล่นที่เหมาะ · soft mult feel |

**ห้ามโชว์:** HP/ATK ดิบ · mult % · `power_*` · สูตรดาเมจ

---

## 3. ค่าใช้จ่าย (soft)

| | S | SS | SSS |
|--|---|----|-----|
| มานา | 6 | 10 | 14 |
| คูลดาวน์ (tick) | 2 | 3 | 4 |

- base glance ฟรี (ไฟต์ I ยังอ่านได้)
- ถ้ามานา/CD ไม่พร้อม → ยังอ่านแบบแผ่วได้ แต่ไม่โต XP

---

## 4. การโตของชั้น

| แหล่ง | ผล |
|--------|-----|
| วิหารปลด | seed **S** + สกิล |
| ใช้ประเมิน | `appraisal_xp` +1–3 |
| Lv / Anima สูง | soft gate ขึ้น SS / SSS |
| skill_ranks[soft_appraise] | ถ้ามี ใช้ max กับ stored tier |

---

## 5. ผูกระบบอื่น

| ระบบ | |
|------|--|
| **Grade (048/049)** | surface หลังปลด · ตัวอักษร+tier |
| **Damage Pipeline (050)** | หลัง appraise มอน → soft combat hint แผ่ว |
| **Anima** | จิตมั่น = อ่านชัดขึ้น · จิตแผ่ว = พร่า |
| **Relic burden** | crush/strain ใบ้ใน self SS+ |
| **Soft Alert** | `appraisal.read` · `appraisal.grow` |

---

## 6. Soft Recipe (SSS)

ดึงจาก `data/elements/fusions.yaml` + matchups  
แสดงเป็นสาย เช่น:

```
· สาย 〔น้ำ + ลม → น้ำแข็ง〕 — ไอน้ำเย็นจัดกลายเป็นน้ำแข็ง
```

**ไม่ใช่** weakness recipes เต็มใน combat (ยังไม่ auto apply mult จาก appraisal)

---

## 7. นอกขอบเขต WO-051

- ตัด P @30 → **WO-052**
- Damage volatility / weakness recipes เต็มใน pipeline
- Resource ใหม่
- UI ใหญ่ (ใช้ V / I / Soft Alert ที่มี)

---

## 8. ทดสอบ

| | |
|--|--|
| Unit | `tests/unit/test_wo051_appraisal.py` |
| Harness | `scripts/wo051_appraisal_playtest.py` |

---

## Changelog

| วันที่ | |
|--------|--|
| 2026-07-16 | WO-051 Appraisal S–SSS soft |
