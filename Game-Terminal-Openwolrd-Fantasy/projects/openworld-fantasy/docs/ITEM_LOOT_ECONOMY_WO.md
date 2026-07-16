# WO-ITEM-1–5 — Loot Identity · Mid Gear · Economy · Gear Identity · Playtest Hotfix

**เวอร์ชัน:** `2.10.1-alpha` (`wo-item-5-playtest-hotfix`)  
**สถานะ:** ITEM-1…4 implement · ITEM-5 harness + hot-fix เบา · unit ผ่าน  
**Playtest มือ:** ดู `docs/WO_ITEM5_PLAYTEST.md`

## WO-ITEM-1 Loot Identity
- ตารางมอนหนา (`drops` ≥3–4) → `gen_scale` soft (WO-ITEM-5: ≥4 → **0.08** · ≥3 → **0.11** · thin → **0.22**)
- ยังมีสำรอง mat/ยาเบา · soft floor กัน loot ว่าง
- soft source ใน note: `จากมอน` · `ชิ้นส่วนมอน` · `สำรองสนาม` · `จากบอส` (ไม่โชว์ %)
- โค้ด: `build_combat_loot_table` ใน `game/domain/inventory_sys.py`

## WO-ITEM-2 Mid Gear Pack
- เกียร์ mid ~15 ชิ้น (prefix `mid_*`) · 5 โทนพื้นที่ (ดง/ถ้ำ/ทะเลทราย/หนอง/เขา)
- ใส่ drops มอน mid (very_rare) · คราฟ 2 สูตร (`craft_mid_forest_blade`, `craft_mid_cave_fang`)
- ข้อมูล: `data/items/items.yaml` · `data/sets/gear_sets.yaml` · `data/craft/recipes.yaml`

## WO-ITEM-3 Economy Soft
- ขาย mat common/uncommon ×0.72 ของ sell_ratio · rare mat ×0.88
- floor ขาย mat เพดาน 0.18 (ไม่ให้ประกันราคายก sink)
- ค่าอัปเกียร์เงินขั้นแรก +sink เล็ก (`upgrade_cost`)
- เส้นทางขายส่ง `item_kind`/`item_id`: shop · `bag_sell` · junk auto-sell · equip sell
- โค้ด: `game/domain/balance.py` · `bag_sell.py` · `inventory_auto.py`

## WO-ITEM-4 Gear Identity Lite
- เซ็ตใหม่ 5 ชุด: forest_thorn · cave_shade · desert_sun · marsh_mist · ridge_stone
- `element_bias` บนเกียร์ + soft tag / `gear_primary_element` ใน `recompute_stats`
- เซ็ตเต็ม: atk/hp/def/mdef + ธาตุเอน (ไม่ใช่ full weakness recipes)

## WO-ITEM-5 Playtest + Hotfix
- Full-loop harness: loot → bag → sell → equip → party soft · auto farm metrics
- Hotfix: ลด generic หนาขึ้นอีกนิด · โทน desc mid gear ชัด · sink mat คง ×0.72 (ไม่แรงเกิน)
- เอกสาร checklist: `docs/WO_ITEM5_PLAYTEST.md`

## ทดสอบ
- `tests/unit/test_wo_item1_4_loot_economy.py`
- `tests/unit/test_wo_item5_full_loop.py`
- Harness: mon > generic · generic share < 35% · empty floor · mid set · economy soft

## นอกขอบเขต (ยังไม่ทำ)
- Full weakness recipes (มอน → WO-Mon)
- Divine gear dump
- ธนาคาร / % ดรอป UI
- Full set bonus ซับซ้อน
