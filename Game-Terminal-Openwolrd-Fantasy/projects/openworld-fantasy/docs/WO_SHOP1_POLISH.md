# WO-Shop-1 — Shop Polish + Price Balance

**เวอร์ชัน:** `2.11.0-alpha` (`wo-shop-1-polish`)  
**สถานะ:** implement แล้ว · unit ผ่าน

## ขอบเขตที่ทำ
- จูนราคา junk / specialty mat
- แยกโทน stock ร้าน (ลดซ้ำ merchant↔armory)
- UI หมวด + เรียงราคา + แบ่งหน้า
- การ์ดยังไม่ขายทุกร้าน

## เฟส 1 — Price
| กฎ | ค่า |
|----|-----|
| Junk sell | **~22%** ของ buy (band 20–25) |
| Mat sink | ×0.72 common (ITEM-3) |
| Mat cap | **≤0.34** ทุก shop (specialty ลดแล้ว) |
| rare_exchange | sell_ratio 0.40 · mat_sell_cap 0.32 |
| legend_pavilion | stock ว่าง · buy_stock false · รับซื้อ rank สูง · tax สูง |

โค้ด: `game/domain/balance.py` (`is_junk_item`, `MAT_SELL_RATIO_CAP`, `JUNK_SELL_RATIO`)

## เฟส 2 — Identity stock
| ร้าน | โทน |
|------|-----|
| traveling_merchant | ยา · อาหาร · mat พื้นฐาน · เกียร์ต้น |
| city_armory | **เกียร์อย่างเดียว** |
| rare_exchange | **mat + scroll** (ตัดเกียร์) |
| celestial_bazaar | charm / sink สวรรค์ |
| infernal_market | sink นรก |
| legend_pavilion | ไม่ขายระบบ · รับซื้อแรงก์สูง |

## เฟส 3 — UI
- ซื้อ: เลือกหมวดก่อน · เรียงราคาถูก→แพง
- รายการยาว: แบ่งหน้า `SHOP_BUY_PAGE=10` (N/P)
- hub แสดงนับต่อหมวด

## Acceptance
1. Junk ถูกกว่า mat ชัด  
2. Specialty mat ≤34%  
3. UI หมวดก่อน + แบ่งหน้า  
4. การ์ด 0 ใน stock  
5. Unit + harness ผ่าน  

## ทดสอบ
```bash
python3 -m pytest tests/unit/test_wo_shop1_polish.py tests/unit/test_loot_pick_and_shop_cards.py -q
```

## นอกขอบเขต
- แลกการ์ด · P2P market · ธนาคาร · % ดรอป UI
