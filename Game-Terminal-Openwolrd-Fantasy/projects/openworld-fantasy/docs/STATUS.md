# ระบบสถานะผิดปกติ (Abnormal Status)

**เวอร์ชัน:** 1.9.3-alpha  
**โมดูล:** `game/domain/status_fx.py`  
**ข้อมูล:** `data/statuses/statuses.yaml`

---

## หลักการ

- สถานะเป็น **debuff/ailment** ติดบนผู้เล่นหรือมอน
- **data-driven** — เพิ่ม id ใหม่ใน YAML โดยไม่ต้อง hard-code ทุกจุด
- UI โชว์ **ชื่อ + รอบเหลือ** มากกว่าสูตรเต็ม (ปรัชญา soft)
- on-hit จากการ์ด: **สูงสุด 1 สถานะ/ครั้ง** · chance แคปจาก `defaults.on_hit_chance_cap` (0.35)
- **ต้านทาน (resist)** หลัง proc — gear / map / blessing นิดหน่อย (soft)

---

## แคตตาล็อกเริ่มต้น

| id | ชื่อ | ผลหลัก |
|----|------|--------|
| poison | พิษ | DoT ต่อเทิร์น/สนาม |
| burn | ไหม้ | DoT (ไฟ) |
| freeze | แช่แข็ง | ข้ามแอคชัน · ไฟ/สายฟ้าแรงขึ้น (combat) |
| stun | มึนงง | ข้ามแอคชัน (สั้น) |
| shock | ช็อก | DoT + โอกาสข้ามแอคชัน |
| **regen** | ฟื้นฟู | บัฟ · tick ฮีล |
| **might** | พลังขึ้น | บัฟ · +atk ชั่วคราว |
| **ward** | เกราะอ่อน | บัฟ · ลดดาเมจเข้า |
| **focus** | สมาธิ | บัฟ · tick มานา |

บัฟ **ไม่ถูกล้าง** ด้วย panacea / cleanse debuffs

---

## API หลัก

```python
from game.domain.status_fx import (
    apply_status,
    cleanse,
    clear_statuses,
    process_status_turn,
    resist_chance,
    try_apply_attack_status,
    should_skip_action,
    tick_field_statuses,
)

apply_status(entity, "poison", reg, rng, chance=1.0)
cleanse(player, reg, mode="all_debuffs")           # ยาถอนสถานะ
clear_statuses(player, reg, item_id="antidote", clear_spec="poison")
try_apply_attack_status(player, mon, reg, rng, profile=profile)
```

โครงสร้าง entry:

```text
{"id": "poison", "name": "พิษ", "remaining": 3, "tick_hp": 4, ...}
```

Resistance บนตัวละคร (optional):

```text
player["status_resist"] = {"poison": 0.3, "all": 0.05, "ailment": 0.1}
```

---

## แหล่งที่มา

| แหล่ง | ตัวอย่าง |
|--------|----------|
| การ์ด on_hit | burn, shock |
| คอมโบ / fusion | freeze, burn |
| กับดักหีบ / ดัน | poison |
| **มอนโจมตี** | `apply_status` บนมอน · `attack_profiles[].status` · fallback ธาตุ |

ลำดับ resolve สถานะมอน: **profile → mon.apply_status → element fallback** (~12%)

## การล้าง (cleanse)

| ไอเทม | ผล |
|--------|-----|
| antidote | poison / ailment ที่ระบุ cleansed_by |
| panacea (ยาถอนสถานะ) | **ทุก debuff** (`clear_all_debuffs`) ไม่ล้างบัฟ |
| balm_regen / tonic_might / oil_ward / tea_focus | ใส่บัฟ |
| blessed_charm | ฟื้น + ล้าง ailment ที่ระบุ |

ในไฟต์: เมนู **3 ยา/ล้าง/บัฟ** → ใช้ของ หรือ **ล้างเร็ว** (กิน panacea/antidote อัตโนมัติ)

```python
cleanse(player, reg, mode="all_debuffs")
cleanse(player, reg, mode="ailment")
clear_statuses(..., clear_spec="all")  # เท่ากับ all debuffs
active_status_mods(player, reg)  # {atk_flat, dmg_taken_mult}
```

---

## วงจรในไฟต์

1. ผู้เล่นโจมตี → on-hit / fusion อาจ `apply_status` ศัตรู  
2. ผู้เล่นเมนู 3 → ยา/บัฟ/ล้าง (ใช้ 1 เทิร์น)  
3. เทิร์นศัตรู: `should_skip_action` → ข้ามโจมตีถ้า freeze/stun/shock  
4. หลังดาเมจมอนโดนผู้เล่น → `apply_monster_hit_status` (resist ได้ → `[ต้าน]`)  
5. `process_status_turn` ทั้งสองฝ่าย: DoT / buff tick + ลด remaining  

สนาม: `apply_field_regen` เรียก `tick_field_statuses`

---

## ขยายสถานะใหม่

1. เพิ่มบล็อกใน `data/statuses/statuses.yaml`  
2. (ถ้าต้องการ) บรรทัด narrative ใน `combat_flavor.yaml`  
3. อ้าง id จากการ์ด/สกิล/fusion/มอน  
4. รัน `pytest tests/unit/test_status_fx.py`
