# WO-Shop-4 — Shop Economy & Reputation

**เวอร์ชัน:** `2.14.0-alpha` (`wo-shop-4-reputation`)  
**สถานะ:** implement แล้ว · unit ผ่าน

## ขอบเขต
- `shop_rep` ต่อร้าน **0–100** (เริ่ม 20–30)
- ราคา/ stock / dialogue ผูก rep
- ไม่โชว์ % หรือเลข rep ดิบใน UI

## เฟส 1 — Reputation
| แหล่ง | ผล |
|--------|-----|
| ซื้อ | +2 (`reason=buy`) |
| ขาย mat | +2 (`sell_mat`) |
| ขายทั่วไป | +1 |
| bulk sell | +1–5 soft |
| เควสที่เกี่ยวข้อง | `grant_shop_rep_quest` +3–8 |

ฟังก์ชัน: `ensure_shop_rep` · `get_shop_rep` · `bump_shop_rep` · `shop_rep_soft_label`

## เฟส 2 — Dynamic Economy
| ด้าน | ผลเมื่อ rep สูง |
|------|------------------|
| ซื้อ | ถูกลงสูงสุด **−12%** |
| ขาย | ร้านจ่ายดีขึ้นสูงสุด **+8%** |
| uncommon stock | เปิดที่ rep ≥ **35** |
| rare+ stock | เปิดที่ rep ≥ **60** |
| วัน + bias | เบา · clamp แยก buy/sell |

## เฟส 3 — Flavor
- cold / cool / known / warm / friend
- dialogue เปลี่ยนตาม band
- ใบ้: 「รับซื้อ/ราคาดีขึ้นถ้าคุณมาบ่อย…」
- hub: ความคุ้น 〔คำ soft〕 — ไม่โชว์ตัวเลข

## ทดสอบ
```bash
python3 -m pytest tests/unit/test_wo_shop4_reputation.py tests/unit/test_wo_shop3_experience.py -q
```

## นอกขอบเขต
แลกการ์ด · P2P · ธนาคาร · Divine dump · % UI · ร้านใหม่
