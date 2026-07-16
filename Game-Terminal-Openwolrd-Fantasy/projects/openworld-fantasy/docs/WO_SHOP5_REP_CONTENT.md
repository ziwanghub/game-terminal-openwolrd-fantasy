# WO-Shop-5 — Shop Reputation Content

**เวอร์ชัน:** `2.15.0-alpha` (`wo-shop-5-rep-content`)  
**สถานะ:** implement แล้ว · unit ผ่าน

## ขอบเขต
- soft field events ที่ช่วยเพิ่ม shop_rep (+5–15)
- เควสร้าน (explore + deliver_item)
- flavor ลูกค้าประจำ (rep 80+)
- ไม่โชว์ % / เลข rep ดิบ

## เฟส 1 — Events
| event | ร้าน | พื้นที่ตัวอย่าง | rep |
|-------|------|-----------------|-----|
| merchant_road_aid | พ่อค้าเร่ | ป่า/ทะเลทราย/เขา/เมือง | +8 |
| armory_shadow_raid | อาวุธเมือง | เมือง/ป่า | +12 |
| rare_crystal_errand | ตลาดวัสดุ | ผลึก/ถ้ำ/เมือง | +10 |
| celestial_lantern_lift | ตลาดสวรรค์ | เมือง/ผลึก | +9 |
| infernal_ash_scatter | ตลาดนรก | หนอง/ถ้ำ/void | +11 |
| legend_echo_quiet | ศาลาตำนาน | เมือง/void/ผลึก | +10 |

เข้า field sights เป็น `kind: shop_rep_event` · เมนูช่วย/เดินจาก

## เฟส 2 — Quests
| quest | type | ร้าน | rep reward |
|-------|------|------|------------|
| shop_merchant_road_favor | explore | traveling_merchant | +10 |
| shop_armory_rare_mats | deliver rare_mat×3 | city_armory | +14 |
| shop_rare_crystal_run | deliver crystal_dust×4 | rare_exchange | +12 |
| shop_celestial_blessing_walk | explore city | celestial | +9 |
| shop_infernal_ash_favor | deliver void_ash×2 | infernal | +11 |
| shop_legend_listen | explore city | legend | +10 |

ส่งของ: เข้า hub ร้าน → `try_deliver_shop_quests` หักของอัตโนมัติเมื่อครบ

## เฟส 3 — Friend band
- hub แสดง 〔ลูกค้าใจดี〕 + บรรทัด VIP soft
- ราคา/stock ยังตาม Shop-4

## ทดสอบ
```bash
python3 -m pytest tests/unit/test_wo_shop5_rep_content.py tests/unit/test_wo_shop4_reputation.py -q
```

## นอกขอบเขต
แลกการ์ด · P2P · ธนาคาร · Divine dump · ร้านใหม่ · % UI
