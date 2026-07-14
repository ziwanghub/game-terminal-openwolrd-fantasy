# ระบบสกิล · Skill Tree (S1 ใช้งานแล้ว)

## สถานะ implement
| คลื่น | สถานะ | เนื้อหา |
|------|--------|---------|
| **S1** | ✅ | tree อาชีพ · prereq · เงิน 3 สกุล · ไอเทม · charge/lease · อาจารย์ · เมนู K |
| S2 | รอ | Combo 2.0 ตามเลเวล · fusion เพิ่ม |
| S3 | รอ | Unit claim 1/โลก · mastery |
| S4 | รอ | content ร้อยสกิล / ร้อย unit |

## วิธีเล่น
- **K** — ต้นไม้อาชีพ: ดูโหนดที่เปิด/ใกล้, เรียนด้วยเงิน/ไอเทม
- ต้องมี **สกิลพื้นฐาน** (`requires`) ก่อนเรียนโหนดถัดไป
- โหนดไกลมาก **ไม่แสดง**
- **อาจารย์** (ผล encounter master) — เมนูสอนสกิล · บางท่า **ใช้ได้จำกัดครั้ง** แล้วเติมเงิน

## เครื่องหมายในเมนู K
| สัญลักษณ์ | ความหมาย |
|-----------|----------|
| ✓ | มีแล้ว |
| ○ | เรียนได้ (จ่ายต้นทุน) |
| ? | ใกล้แล้ว / ต้องอาจารย์ |
| × | หมดครั้งใช้ — เลือกเพื่อเติม |

## ไฟล์ data
```
data/skills/
  skills.yaml           # core + unit skills
  tree_warrior.yaml
  tree_mage.yaml
  tree_archer.yaml
  tree_rogue.yaml
  tree_priest.yaml
  master_taught.yaml    # lease skills
  masters.yaml          # อาจารย์ + ค่าเรียน
```

## โค้ดหลัก
- `game/domain/skill_tree.py` — learn / prereq / tree UI helpers / master teach
- `game/domain/skill_charges.py` — lease spend/renew
- `game/services/field_loop.py` — เมนู K · เมนูอาจารย์ · spend หลังโจมตี

## Schema ย่อ
```yaml
- id: warrior_cleave
  tree: warrior
  tier: 2
  requires: [basic_strike]
  learn:
    method: [self]
    require_level: 6
    cost_world: 55
    cost_heaven: 0
    cost_hell: 0
    cost_items: {upgrade_mat: 1}
  charge:
    mode: none | master_lease | fixed
    max_uses: 10   # ถ้า lease
```

## ตัวเลขปัจจุบัน (S1)
- สกิลใน registry ≈ **60**
- อาจารย์ **4** คน (steel / tide / arcane / shade)
- Unit skill ยัง 3 ตัว (ขยาย S3–S4)

## แผนต่อ
ดูแผนเต็มใน session plan — Combo 2.0, Unit ร้อยแบบ exclusive, gen content
