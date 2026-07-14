# Workspace map (สั้น)

แผนที่ monorepo แม่ + วินัย Z-MOS อยู่ที่:

| แหล่ง | ใช้เมื่อ |
|--------|---------|
| [`../../README.md`](../../README.md) | บทบาท `core/` · `projects/` · `design/` · คำสั่ง `zcl` |
| [`../../core/README.md`](../../core/README.md) | ทางเข้า Z-MOS Gen4 |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | **แผนที่ระบบเกม** + Doc Policy (อ่านก่อน) |

## แยก 1 บรรทัด

- **`core/`** = governance พัฒนา (session / preflight / truth) — **ไม่ใช่เกม**
- **`projects/openworld-fantasy/`** = โค้ดเกม · data · tests · docs เกม
- เกมถูกไหม = **pytest + domain** · ทำงาน session ใหญ่ยังไง = **Z-MOS**

อย่า copy โปรโตคอล Z-MOS ลง docs เกม — ดู Doc Policy ใน `ARCHITECTURE.md`
