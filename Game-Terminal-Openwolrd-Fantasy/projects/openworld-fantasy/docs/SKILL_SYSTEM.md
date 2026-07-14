# ระบบสกิล · Skill Tree (S1 ใช้งานแล้ว)

## สถานะ implement
| คลื่น | สถานะ | เนื้อหา |
|------|--------|---------|
| **S1** | ✅ | tree อาชีพ · prereq · เงิน 3 สกุล · ไอเทม · charge/lease · อาจารย์ · เมนู K |
| **SK-R0–R2** | ✅ **1.43** | Rank N–SSS · scale power/MP · เรียน roll · slot buff/debuff · counter/reflect |
| **SK-R3** | ✅ lite | mastery ซ่อน + โอกาสเปลี่ยนโทน |
| **SK-R4** | ✅ **1.44** | pack 15 สกิล debuff/buff · status slow/weak · `pack_skr4.yaml` |
| **SK-R5** | ✅ lite | `essence_skill_whisper` / echo · ใช้จากกระเป๋า nudge rank |
| S2 | บางส่วน | Combo length by level มีแล้ว |
| S3–S4 | บางส่วน | Unit exclusive + HSR มีแล้ว |

## Skill Rank (ผู้เล่น)
- ป้าย soft: ธรรมดา / สูง / หายาก / S / SS / SSS — **ไม่โชว์สูตร**
- เรียนครั้งแรก roll rank (SSS หายาก · ต้นเกม SS/SSS ภาษี MP/charge)
- ใช้บ่อย → mastery ซ่อน อาจ「เปลี่ยนโทน」
- โค้ด: `game/domain/skill_rank.py` · `data/skills/rank_rules.yaml`

## Slot
| slot | บทบาท |
|------|--------|
| combat | ดาเมจ (+ apply_status ได้) |
| debuff | เน้นสถานะ (รองรับ) |
| buff | บัฟตัว · **1 ครั้ง/แอคชัน** · category exclusive |
| defense | guard · **counter** · **reflect** |
| support | ฮีล / utility |

รายละเอียดออกแบบ: [`SKILL_SLOT_RANK_VISION.md`](SKILL_SLOT_RANK_VISION.md)

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
- **Slot ขยาย + Skill Rank (ออกแบบแล้ว):** [`SKILL_SLOT_RANK_VISION.md`](SKILL_SLOT_RANK_VISION.md) · เฟส **SK-R0→R6**
- Combo 2.0 · Unit exclusive (HSR มีแล้วบางส่วน) · อย่า bulk ร้อยสกิลทีเดียว
