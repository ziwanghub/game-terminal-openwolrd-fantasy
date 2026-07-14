# แผนพัฒนา / คิวงาน

**เกมปัจจุบัน:** `1.13.10-alpha` (`aoe-pack-balance`)

---

## สถานะ

| เฟส | สถานะ |
|-----|--------|
| Mode Shell · multi-ATB · multi-target · bulk | **1.13.5–1.13.9** |
| **บาลานซ์ AoE / กลุ่ม** | **1.13.10** |
| V Later | LLM / Web / Z-MOS เต็ม |

### ปิดใน 1.13.10

| | |
|--|--|
| `domain/aoe_balance.py` | splash diminishing · pack spawn · soft splash XP |
| กระแสฝูงใหญ่ | ยิ่งหลายตัว ดาเมจกระแสยิ่งแผ่ว |
| ล้มจากกระแส | XP ~42% · ข้อความรางวัลแผ่ว |
| spawn กลุ่ม | ต้นเกมหายาก · ปลายเกมมี 3 ตัวได้บ้าง |
| สกิล AoE | มานาขึ้นเล็กน้อย · power ลงเล็กน้อย |

---

## คิวค้าง

| รายการ | หมายเหตุ |
|--------|----------|
| playtest รอบใหม่ | ตรวจ AoE หลังบาลานซ์ |
| V Later | LLM / Web / Z-MOS |

```bash
python3 -m game && python3 -m pytest -q
```
