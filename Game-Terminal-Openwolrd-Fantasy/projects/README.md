# projects — พื้นที่สร้างเกม

โฟลเดอร์นี้เท่านั้นที่ใช้ **เขียน/รัน/ทดสอบเกม**

ผู้คุมกฎการพัฒนาอยู่ที่ `../core/` (Z-MOS) — ไม่ใส่โค้ดเกมใน core

| โปรเจกต์ | คำอธิบาย |
|----------|----------|
| `openworld-fantasy/` | Terminal Open World Fantasy · ดู `openworld-fantasy/docs/ARCHITECTURE.md` |

```bash
cd openworld-fantasy
python3 -m game
python3 -m pytest -q
```

- แผนที่เกม / **Doc Policy** → `openworld-fantasy/docs/ARCHITECTURE.md`  
- Session ใหญ่ → Z-MOS lite (`core`, เช่น `zcl start`) แล้วค่อย mutate ใต้ `projects/`  
- **อย่า** ใช้ Z-MOS แทน pytest สำหรับความถูกต้องของเกม  
