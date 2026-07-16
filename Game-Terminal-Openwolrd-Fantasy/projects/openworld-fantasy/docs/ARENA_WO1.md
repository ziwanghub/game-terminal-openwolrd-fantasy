# WO-Arena-1 — Arena System (First Version)

**เวอร์ชัน:** `2.17.0-alpha` (`wo-arena-1`)  
**สถานะ:** implement แล้ว · unit ผ่าน

## เข้าเล่น
- สนาม: **เมืองโบราณ / ยอดผลึก** (location)
- คีย์สนาม: **U** (ลานอารีน่า)
- ทีม: ผู้เล่น + ซุ่ม 0–3 = **1–4 คน** (เลือก lineup)

## กติกา session
1. รับใบเชิญ **Mystery** (เงา ??? · ไม่โชว์ stat/%)
2. เลือกซุ่ม (เว้นว่าง = คนเดียว)
3. **3 รอบ** ไฟต์ (จำลอง + คะแนนกลยุทธ์)
4. แพ้รอบยังได้คะแนน · รวม 3 รอบ → แบนด์
5. แบนด์สูงพอ → **ไขชั้นลึก** แม้ชนะ 0 รอบ
6. รางวัลตามแบนด์×ชั้น · **dim = ไม่มีรางวัลหลัก** · F ยังได้ถ้าแบนด์ดี

## ชั้น NPC
`normal` → `elite` → `legendary` → `divine`  
ศัตรูต่อจอ **≤3** · scale ตามขนาดทีมผู้เล่น

## คะแนน (ภายใน · ไม่โชว์สูตร)
Pressure · Craft · Team · Poise · Tempo · Resolve  
UI: แบนด์ 〔เลือน/จาง/คม/เฉียบ/ตำนานแผ่ว〕 + แต้มรวม soft ปัด

## Mystery weight (ไม่สุ่มล้วน)
rep ร้าน · Anima · เควส · บอส · คะแนนอารีน่าเก่า · grade

## โค้ด
- `game/domain/arena.py`
- `game/services/arena_session.py`
- field: `U` / `arena`

## ทดสอบ
```bash
python3 -m pytest tests/unit/test_wo_arena1.py -q
```

## นอกขอบเขต
PvP · Online · Divine pack dump · % ดรอป UI · คุมซุ่มเต็มสกิล
