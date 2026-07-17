# WO-Worthiness-1 — Path of Worthiness (Lite)

| ฟิลด์ | ค่า |
|--------|-----|
| **สถานะ** | Design Lock · implement 2.21.0-alpha |
| **หลัก** | เข้าถึงได้ ≠ สมควรได้ · ฟาร์มซื้อเวลาไม่ได้ซื้อความสมควร |

## ล็อก

| รายการ | ค่า |
|--------|-----|
| Gate แมพ | ป่า (`dark_forest`) เต็ม → หนอง (`mist_marsh`) Whisper จน T1 → เขา (`mountain_rock`) Whisper จน T2 |
| Cap ฟาร์ม | rarity rank ≤ **5 legendary** (ฟาร์ม/หีบ/บอสปกติ) |
| T1 | `boss_forest_king` + flag · รางวัล `relic_divine_laurel` · 1 ครั้ง/ตัว · **มือ** |
| T2 | `boss_mist_hydra` + flag · รางวัล `relic_god_eye` (ดวงตาพระเจ้า) · 1 ครั้ง/ตัว · **มือ** |
| Soft wall | Whisper / Trial / Reward Lock |
| Auto | ห้าม first-trial · ห้ามดรอป/grant ของเทพจาก auto |

## Soft wall

| ระดับ | ความหมาย |
|-------|----------|
| **Whisper** | เข้าพื้นที่ได้ · soft “ยังไม่พร้อม” · ของเทพไม่โผล่ |
| **Trial** | บอสโหมดพิสูจน์ · มือเคลียร์ครั้งแรก = flag + grant |
| **Reward Lock** | divine+ / trial exclusive ไม่จากฟาร์มปกติ |

## นอกขอบเขต

Gate 8 แมพ · trial ทุกของเทพ · auto policy ใหญ่ · content pack ใหญ่

## โค้ดหลัก

`game/domain/worthiness.py` · ผูก travel / combat boss / loot / chest / auto
