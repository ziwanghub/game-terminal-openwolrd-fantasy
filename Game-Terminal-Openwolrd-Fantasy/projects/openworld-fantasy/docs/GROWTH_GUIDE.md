# Growth Guide — เติบโตอัตโนมัติ (WO-052)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-052 |
| **สถานะ** | shipped @ `1.99.0-alpha` |
| **โมดูล** | `game/domain/auto_growth.py` |
| **เกต** | `AUTO_GROWTH_LEVEL = 30` |
| **หลัก** | Soft Feel · เกรดมีน้ำหนัก · ไม่ farm แต้มซ้ำ |

---

## 1. สองยุคการเติบโต

| ช่วง | โหมด | พฤติกรรม |
|------|------|----------|
| **Lv 1–27** | Manual Soft P | ลงแต้ม P ได้ · soft feedback |
| **Lv 28–29** | Soft foreshadow | ยังลง P ได้ · ใบ้ “พลังอั้น” |
| **Lv 30+** | **Automatic Growth** | ไม่รับแต้ม P ใหม่ · เมนู P = “พลังไหลเวียนเอง” |

---

## 2. Phase-out แต้มคงเหลือ

เมื่อเข้าโหมดอัตโนมัติครั้งแรก:

1. ตั้ง `auto_growth_active = True`
2. แปลง `stat_points` คงเหลือ → growth pulse (source `residual`)
3. เคลียร์แต้มเป็น 0
4. ข้อความ soft: “แต้มเก่าไหลเข้าตัว…”

ทำครั้งเดียว (`_p_phase_out_done`)

---

## 3. Automatic Growth

### อัตรา (ซ่อน)

```
effective_rate ≈ player_grade growth_mult × anima soft × relic soft
```

| เกรด | อัตราประมาณ (เทียบ C=1) |
|------|-------------------------|
| F | 0.55 |
| C | 1.00 |
| S | 1.40 |
| SSS | 1.70 |

`growth_profile` (สมดุล / เฉพาะ / ผสม) กำหนด **ทิศทางแกน** (atk/def/magic/speed)

### แหล่ง pulse

| source | ตัวอย่าง | น้ำหนักฐาน |
|--------|----------|------------|
| `level` | เลเวลอัพ | สูง |
| `quest` | เควสสำเร็จ | สูง |
| `combat` | ชนะไฟต์ | กลาง |
| `anima` | Anima moment | กลาง |
| `relic` | bond (hook) | เบา |
| `faction` | สายตาโลก (hook) | เบา |
| `residual` | phase-out แต้ม | ครั้งเดียว |

ผล: เพิ่ม `axis_progress` + soft `stats_alloc` ticks → recompute powers  
UI: “พลังของคุณกำลังพัฒนาเอง…” · ชั้นเกรดเลื่อนเมื่อถึง

---

## 4. UX

| ที่ | หลัง Lv30 |
|----|-----------|
| เมนู **P** | panel auto growth (ไม่เลือก 1–4 ลงแต้ม) |
| `allocate_stat` | ปฏิเสธ soft |
| Personal hub | “พลังไหลเอง → P” |
| เลเวลอัพ | ไม่มี “ได้แต้ม +N” — มี soft growth |

**ห้ามโชว์:** สูตร · `power_*` · growth_mult ดิบ

---

## 5. ผูกระบบ

| ระบบ | |
|------|--|
| Grade 048/049 | rate + profile tilt |
| Damage 050 | โตแล้ว damge soft เปลี่ยนตาม |
| Appraisal 051 | อ่านชั้นหลังโต |
| Anima | moment เติม pulse |
| Quest / Combat | pulse หลัก |

---

## 6. นอกขอบเขต WO-052

- Weakness recipes / damage volatility
- Resource ใหม่
- เปลี่ยนสถาปัตยกรรมหลัก
- Rewrite combat

---

## 7. ทดสอบ

| | |
|--|--|
| Unit | `tests/unit/test_wo052_auto_growth.py` |
| Harness | `scripts/wo052_auto_growth_playtest.py` |

---

## Changelog

| วันที่ | |
|--------|--|
| 2026-07-16 | WO-052 Auto Growth + cut P @30 |
