# WO-ITEM-5 — Full Loop Playtest + Hotfix

**เวอร์ชัน:** `2.10.1-alpha` (`wo-item-5-playtest-hotfix`)  
**สถานะ:** harness + hot-fix เบา · **playtest มือยังแนะนำ**

## ขอบเขต
- ยืนยันวงจร: loot → กระเป๋า → ขาย → คราฟ → equip → party → มอน
- Hotfix เฉพาะจุดจาก harness (ไม่ dump content)
- นอกขอบ: Divine pack · full weakness recipes · % ดรอป UI · ธนาคาร

## เฟส 1 — Playtest Checklist (มือ)

| ขั้น | ทำ | บันทึก soft |
|------|-----|-------------|
| A | Farm 2–3 พื้นที่ (ดง early · ถ้ำ/เขา mid) | ของส่วนใหญ่มาจากมอนหรือสำรอง? |
| B | Loot → organize/stack → ขาย mat | กระเป๋าตัน? ขาย mat ถูก/แพง? |
| C | คราฟ mid 1–2 + equip เซ็ตโทน | โทนพื้นที่ชัดไหม |
| D | Party assist + อ่านสหาย | ซุ่มช่วยตอนวิกฤต? |
| E | Appraisal mon S+ | ใบ้ธาตุโดยไม่ % |
| F | Auto 15–20 นาที | เงิน/ยา ล้นหรือแห้ง |

## เฟส 2 — Hotfix ที่ลงแล้ว (จาก harness)

| หัวข้อ | ก่อน | หลัง (2.10.1) |
|--------|------|----------------|
| gen_scale thick ≥4 | 0.10 | **0.08** |
| gen_scale ≥3 | 0.15 | **0.11** |
| gen_scale thin | 0.28 | **0.22** |
| boss generic | 0.18 | **0.14** |
| soft floor bump | 0.22 | **0.20** |
| soft source note | สำรอง | ชัดว่า **สำรองสนาม** / คราฟได้ |
| mid gear desc | `mid ดง/ถ้ำ…` | โทนพื้นที่ + ชื่อเซ็ต soft |
| mat sell sink | ×0.72 | **คงไว้** (อย่าแรงเกิน · harness mat≈0.7× equip path) |

## เฟส 3 — ปิดรอบ
- docs: ไฟล์นี้ · `ITEM_LOOT_ECONOMY_WO.md` · `PHASES.md`
- tests: `tests/unit/test_wo_item5_full_loop.py` + `test_wo_item1_4_loot_economy.py`

## Acceptance
1. ของมอนมีเอกลักษณ์ (mon lines > generic · ratio generic < 35%)
2. เงินไม่ล้นเร็ว · farm ยังคุ้ม (sink นุ่ม)
3. กระเป๋า + ปาร์ตี้ + มอนไหลใน harness
4. Unit + harness ผ่าน

## รัน harness
```bash
python3 -m pytest tests/unit/test_wo_item5_full_loop.py tests/unit/test_wo_item1_4_loot_economy.py -q
```
