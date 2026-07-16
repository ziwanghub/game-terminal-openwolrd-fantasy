# WO-Shop-2 — Shop Content + Identity Polish

**เวอร์ชัน:** `2.12.0-alpha` (`wo-shop-2-identity`)  
**สถานะ:** implement แล้ว · unit ผ่าน

## ขอบเขต
- เพิ่มโทน/เอกลักษณ์แต่ละร้าน (ไม่เพิ่มร้านใหม่)
- content pack เบา 2–4 ชิ้นต่อโทน
- UI ใบ้โทน · การ์ดยังไม่ขาย

## โทนร้าน

| ร้าน | โทน | stock หลัก |
|------|-----|------------|
| traveling_merchant | รถเร่ — ยา อาหาร เดินทาง | potions · rations · `shop_merchant_*` |
| city_armory | โรงตี — เกียร์ + อัปเกรด | gear · `upgrade_mat` · `shop_armory_*` |
| rare_exchange | ผลึก/ม้วน/mat | crystal · scrolls · mon mats · `shop_rare_*` |
| celestial_bazaar | พรแผ่ว / charm | blessed · incense · `shop_celestial_*` |
| infernal_market | สัญญา / เถ้า | hell_contract · void_ash · `shop_infernal_*` |
| legend_pavilion | รับซื้อแรงก์สูง + ตำนานเบา | `shop_legend_*` (≤3 · legendary) |

## Content pack ใหม่
- merchant: road_tea · mixed_ration  
- armory: whetstone · temper_oil · rivet_pack  
- rare: crystal_lens · prism_vial · bound_scroll  
- celestial: prayer_bead · soft_laurel · light_vial  
- infernal: ember_vial · void_token · smoke_oil  
- legend: memory_fragment · soft_seal · echo_thread  

## UI
- ฟิลด์ `tone` ใน `shops.yaml`
- hub แสดง `โทน  …` + ใบ้การ์ดไม่ขาย
- `shop_tone_line()` fallback defaults

## Acceptance
1. แต่ละร้านโทนชัด ไม่ซ้ำหนัก  
2. UI ใบ้โทน  
3. การ์ด 0 ใน stock  
4. Unit + harness ผ่าน  

## ทดสอบ
```bash
python3 -m pytest tests/unit/test_wo_shop2_identity.py tests/unit/test_wo_shop1_polish.py -q
```

## นอกขอบเขต
- แลกการ์ด · P2P · ธนาคาร · Divine pack ใหญ่ · % ดรอป UI
