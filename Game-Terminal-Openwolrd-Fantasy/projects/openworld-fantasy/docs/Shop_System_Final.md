# Shop System Final — WO-Shop-1…6

**เวอร์ชัน:** `2.16.0-alpha` (`wo-shop-6-final`)  
**สถานะ:** **ปิดสายร้านค้า** · unit ผ่าน · ไม่เปิด WO-Shop-7

## สรุปทั้งสาย

| WO | โฟกัส | เวอร์ชัน |
|----|--------|----------|
| **1** | Price · identity stock · UI หมวด/หน้า | 2.11 |
| **2** | Content pack · โทนร้าน · legend stock เบา | 2.12 |
| **3** | Dialogue · dynamic day/rep · best-buyer | 2.13 |
| **4** | shop_rep 0–100 · ราคา±rep · stock gate | 2.14 |
| **5** | Events · deliver quests · friend flavor | 2.15 |
| **6** | Final polish + Anima/Grade/Relic/Spar | **2.16** |

## ร้าน (6 ร้าน · ไม่เพิ่มใหม่)

| id | โทน |
|----|-----|
| traveling_merchant | ยา·อาหาร·เดินทาง |
| city_armory | เกียร์ + วัสดุอัป |
| rare_exchange | mat·scroll·crystal |
| celestial_bazaar | charm·blessing (สวรรค์) |
| infernal_market | สัญญา·เถ้า (นรก) |
| legend_pavilion | รับ rank สูง · stock ตำนานเบา · **รับเรลิกเบา** |

## Reputation
- 0–100 ต่อร้าน · เริ่ม 20–30  
- ซื้อ/ขาย/เควส/event/spar → เพิ่ม  
- UI: คำ soft เท่านั้น (ไม่โชว์เลข / %)  
- ซื้อ −12% / ขาย +8% ที่ rep สูง · clamp ชัด  

## Integration (WO-Shop-6)
| ระบบ | ผล |
|------|-----|
| **Anima** | rep≥60 เข้า shop → จิตอุ่นแผ่ว (throttle) |
| **Grade** | เกรดสูงซื้อถูกขึ้น · เปิด stock เร็วขึ้น soft |
| **Relic** | legend รับซื้อเรลิกทีละชิ้น (ratio เบา ~14%) |
| **Spar/Arena** | spar ห้องเรลิก → rep โรงตี + พ่อค้าเร่ (+10 soft, throttle) |

## DNA ที่ล็อก
- การ์ด **ไม่ขาย** ในร้าน  
- ไม่ P2P / ธนาคาร / % ดรอป UI  
- ไม่ Divine pack dump  
- Soft feel ตลอด  

## ทดสอบ
```bash
python3 -m pytest tests/unit/test_wo_shop6_final.py \
  tests/unit/test_wo_shop5_rep_content.py \
  tests/unit/test_wo_shop4_reputation.py \
  tests/unit/test_wo_shop3_experience.py \
  tests/unit/test_wo_shop2_identity.py \
  tests/unit/test_wo_shop1_polish.py -q
```

## เอกสารย่อย
- `WO_SHOP1_POLISH.md` … `WO_SHOP5_REP_CONTENT.md`  
- ไฟล์นี้ = **สรุปปิดระบบ**
