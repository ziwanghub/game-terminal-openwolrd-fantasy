# WO-Shop-3 — Shop Experience Polish

**เวอร์ชัน:** `2.13.0-alpha` (`wo-shop-3-experience`)  
**สถานะ:** implement แล้ว · unit ผ่าน

## ขอบเขต
- flavor / dialogue ต่อร้าน
- dynamic price เบา (วัน · rep · bias ร้าน)
- UI ใบ้โทน · best-buyer · หมวดเรียงตามโทน
- ไม่เพิ่มร้านใหม่ · ไม่แลกการ์ด · ไม่ P2P

## เฟส 1 — Flavor
- `greetings[]` + `specialty_hint` ใน `shops.yaml`
- `pick_greeting` · `specialty_hint` ใน `shop_experience.py`
- hub แสดงทักทาย + โทน + เด่น + วันตลาด soft

## เฟส 2 — Dynamic price
| ปัจจัย | ผล (clamp 0.94–1.06) |
|--------|----------------------|
| วัน (`time_units//20`) | คลื่น sin เบา ±~3% |
| rep (`help_rep` + `shop_rep`) | ซื้อถูกขึ้นเล็ก / ขายดีขึ้นเล็ก |
| shop bias | armory ซื้อเกียร์แพงนิด · rare รับ mat ดีขึ้นนิด |
| junk floor | ≥ ~18% ของ buy-ref |
| mat floor | ≥ ~22% ของ buy-ref (min 2) |

## เฟส 3 — UI
- หมวดเรียงตามโทน (★ = หมวดเด่น)
- ขาย mat: ใบ้「รับซื้อดีที่สุดที่…」
- ใบ้ชัด: **การ์ดไม่ขายที่นี่**

## ทดสอบ
```bash
python3 -m pytest tests/unit/test_wo_shop3_experience.py tests/unit/test_wo_shop2_identity.py tests/unit/test_wo_shop1_polish.py -q
```

## นอกขอบเขต
แลกการ์ด · P2P · ธนาคาร · Divine dump · % ดรอป UI · ร้านใหม่
