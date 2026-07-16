# WO-Mon-1–4 — Diversity · Weakness · Balance · Content

**เวอร์ชัน:** `2.09.0-alpha` (`wo-mon-1-4-diversity`)

## WO-Mon-1 Pool Diversity + Profiles Soft
- ปรับ `weight` ทุกพื้นที่ — early top-2 normal < 50% ของ pool
- เพิ่มน้ำหนัก elite ช่วงต้น (เช่น forest/cave ~7%)
- `attack_profiles` + `telegraph` **ครบทุกมอนใน catalog** (เดิม 17 → ทั้งหมด)

## WO-Mon-2 Weakness Lite Playable
- ฟิลด์ `weak_to` บนมอน (ธาตุอ่อน soft)
- Appraisal **S+** ใบ้ soft (S บรรทัดเดียว · SS+/SSS ลึกขึ้น)
- `weakness_lite_mult`: S +3% · SS+ สูงสุด ~+6%

## WO-Mon-3 Balance Pass
- Elite rarity ceiling (สุ่ม uncommon/rare)
- Early area rarity soft-cap
- `_clamp_spawn_stats` จำกัดสเกล elite+rarity
- World difficulty mult clamp สำหรับ non-boss

## WO-Mon-4 Content Pack
- เพิ่มมอน **+15** (รวม elite ใหม่ 2)
- `role_tag` ครบ catalog
- ใส่ pool พื้นที่ที่เกี่ยวข้อง

## นอกขอบเขต (ยังไม่ทำ)
- Full weakness recipes
- Mon skill charge เต็มรูป
- Rewrite AI
