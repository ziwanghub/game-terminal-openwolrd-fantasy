# Damage Pipeline v1 (WO-050)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-050 |
| **สถานะ** | shipped @ `1.97.0-alpha` |
| **โมดูล** | `game/domain/damage_pipeline.py` |
| **หลัก** | Adapter ทางเดียว · เกรด soft mult · ไม่โชว์สูตร · ไม่ volatility เต็ม |

---

## 1. เป้าหมาย

- รวมทางคำนวณดาเมจแบบค่อยเป็นค่อยไป (ไม่ rewrite combat ทั้งก้อน)
- ผูก `player_grade` + `axis_grades` เป็น soft multiplier
- Soft combat log — ผู้เล่นรู้สึกได้ ไม่เห็นตัวเลขดิบ
- รองรับอนาคต (ธาตุ / จุดอ่อน / คอมโบ) ผ่าน adapter hooks

---

## 2. ทางเข้า (Adapter API)

| ฟังก์ชัน | ทิศ | ใช้เมื่อ |
|----------|-----|---------|
| `resolve_player_outbound(...)` | ผู้เล่น → มอน | physical / arcane / light / dark |
| `resolve_player_inbound(...)` | มอน → ผู้เล่น | dodge + def soft + grade defense |
| `resolve_monster_outbound(...)` | raw มอน | backend power; grade อยู่ฝั่ง inbound |

**Compatibility wrappers** (legacy import ยังใช้ได้):

- `combat.player_attack_damage` → `resolve_player_outbound`
- `combat.apply_incoming_damage` → `resolve_player_inbound`
- `combat.monster_raw_damage` → `resolve_monster_outbound`

ผลลัพธ์: `DamageResult(amount, flavor, soft_notes, damage_class, meta)`  
`meta` ใช้ใน test/debug เท่านั้น — **ห้ามโชว์ผู้เล่น**

---

## 3. Soft Grade Mult (ล็อกเบา)

### Outbound (โจมตี)

| ส่วน | ผล |
|------|-----|
| `player_grade` (หลังวิหาร) | F≈0.90 … C=1.00 … S≈1.12 … SSS≈1.15 (soft cap) |
| axis (atk / magic ตาม class) | F≈0.92 … C=1.00 … S≈1.09 … SSS≈1.12 |
| tier | early −0.01 · mid 0 · late +0.015 · special +0.025 |
| blend | revealed: 55% player + 45% axis · pre-temple: axis เบา ๆ |
| clamp | **0.85 – 1.18** |

### Inbound (รับดาเมจ)

| ส่วน | ผล |
|------|-----|
| defense axis | F รับมากขึ้น · S+ รับน้อยลง |
| player_grade | เหนียวขึ้นเล็กน้อยเมื่อเกรดสูง |
| clamp | **0.82 – 1.12** |

### Presence (เบา)

| แหล่ง | soft |
|--------|------|
| Anima สูง/ต่ำ | ±1–3% + soft log |
| Burden strain/crush | ลดแผ่ว |
| Bond resonance flag | +2% แผ่ว |

**ไม่มี** SSS volatility 80–150 · **ไม่มี** weakness recipes เต็ม

---

## 4. Soft Combat Log (ตัวอย่าง)

| สถานการณ์ | โทน |
|-----------|-----|
| mult สูง กาย | ·พลังกายภาพไหลเวียนแรง |
| mult สูง เวท | ·เวทไหลคมชัด |
| mult ต่ำ | ·แรงแผ่ว / ·เวทพร่า |
| รับได้ดี | ·เกราะในตนรับได้ |
| Anima แผ่ว | ·จิตแผ่ว |

ความถี่: ไม่ทุกฮิต (rng throttle) · ไม่มีตัวเลข / %

---

## 5. Backend

สูตรเดิมยังเป็น core:

- skill power + bonus + damage_class outbound_power
- element mult · mastery · needs · crit
- dodge / incoming needs · alloc_def_bonus

Pipeline **ห่อ** แล้วคูณ soft grade — ไม่ลบสูตรเก่า

Class mitigation (`damage_class.apply_class_mitigation`) ยังอยู่ combo path แยก  
Inbound เปิด `use_class_mitigation=True` ได้เมื่อต้องการรวมทางเดียวในอนาคต

---

## 6. นอกขอบเขต WO-050

- Weakness recipes + ธาตุ fusion เต็ม → WO-051+
- SSS volatility สูง
- Appraisal Skill S–SSS เต็ม → WO-051
- ตัด P @30 → WO-052
- Resource ใหม่

---

## 7. ทดสอบ

| | |
|--|--|
| Unit | `tests/unit/test_wo050_damage_pipeline.py` |
| Harness | `scripts/wo050_damage_pipeline_playtest.py` |

---

## Changelog

| วันที่ | |
|--------|--|
| 2026-07-16 | WO-050 v1 adapter + grade soft mult |
