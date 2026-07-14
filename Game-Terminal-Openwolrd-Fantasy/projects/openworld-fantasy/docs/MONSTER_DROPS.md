# ดรอปมอนสเตอร์ (per-monster table)

**สถานะ:** D1–D2 **done** · world pack **1.26** · runtime hotfix **1.27**  
**โค้ด:** `game/domain/monster_drops.py` · `build_combat_loot_table` · `pick_monster` / `spawn_boss`  
**หลัก:** โครงแบบ RO · **soft rate ไม่โชว์ %** · ชื่อของโลกเรา (ไม่ copy RO)  
**แผนเติมมอนใหม่ (แบ่งเฟส):** [`MONSTER_CONTENT_PLAN.md`](MONSTER_CONTENT_PLAN.md) · **MC0–MC6**

**1.27:** ตารางดรอปต้องถูก copy จาก YAML ตอน spawn — มิฉะนั้น loot หลังชนะไม่เห็น `drops`  
**มอนใหม่ทุกตัว (MC1+):** ต้องมี `drops` (+ `card_id` ตามแผน) ตั้งแต่เพิ่ม — ดูกฎแพ็กใน MONSTER_CONTENT_PLAN

---

## YAML

```yaml
- id: forest_wolf
  # ... stats ...
  card_id: card_wind          # optional การ์ดพันธะ
  card_rate: very_rare        # default very_rare
  drops:
    - item: wolf_fang
      rate: common            # common|uncommon|rare|very_rare|boss|always
      qty: [1, 2]
      note: ชิ้นส่วนมอน
```

## ชั้น rate (ซ่อน)

| rate | แนวภายใน |
|------|----------|
| common | ~0.48 |
| uncommon | ~0.20 |
| rare | ~0.07 |
| very_rare | ~0.018 |
| boss | ~0.52 |
| always | 1.0 |

บอส × soft บน rare/very_rare · ฟาร์มซ้ำ mon เดิม → anti_farm

## หลังชนะ

1. ตารางมอน  
2. generic mat/ยา (ลดถ้ามีตาราง)  
3. การ์ด: `card_id` ในตารางก่อน · ไม่งั้น pool ธาตุ  
4. ผู้เล่นเลือก **A / เลข, / 0**

## ความครอบคลุม (1.26)

| พื้นที่ | มอน (ตัวอย่าง mat) |
|---------|---------------------|
| ป่ามืด | ก็อบลิน/หมาป่า/เอนท์ · scrap/fang/bark |
| ถ้ำเงา | ค้างคาว/สไลม์/wraith · wing/core/dust |
| ภูเขาหิน | โกเล็ม/โทรล/drake · stone_chip/troll_hide |
| เมืองโบราณ | หนู/นักเลง/อัศวิน · rat_tail/thug_badge |
| ทะเลทราย | แมงป่อง/ราเดอร์ · stinger/sand_cloak_mat |
| หนองหมอก | ปลิง/วิสป์/โทรล · leech_sac/mist_dew |
| ยอดผลึก | ไร/โกเล็ม/drake · crystal_dust |
| รอยแยก | ละออง/คลาน/เวทย์ · void_ash |
| บอสทั้ง 8 | table หนา + sealed chest soft |

**ทุกตัว (41)** มี `drops` และ/หรือ `card_id`
