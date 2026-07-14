# core — ผู้คุมกฎการพัฒนามืออาชีพ

โฟลเดอร์นี้คือ **Professional Development Governance** ไม่ใช่ที่สร้างฟีเจอร์เกม

## สิ่งที่อยู่ที่นี่

| รายการ | รายละเอียด |
|--------|------------|
| `zmos-gen4-v0.4.0/` | Z-MOS Gen4 — Controlled Trial Foundation |
| เครื่องมือ | CLI `zcl` (session, doctor, preflight, truth, intent, trace) |
| โปรโตคอล | `zmos-core.md` — execution loop, trust tiers, DoD |

## สิ่งที่ core เป็น

- ชั้นกำกับ AI/คนพัฒนาให้ทำงานมีหลักฐาน  
- Session entry ก่อนงาน (`zcl start`)  
- Preflight → Execute → Validate → Verify → Document  
- Truth-first / intent / append-only trace  

## สิ่งที่ core ไม่เป็น

- ❌ ไม่ใช่เกม open world  
- ❌ ไม่เก็บ data พื้นที่/สกิล/เซฟผู้เล่น  
- ❌ ไม่ใช่ที่ commit feature combat / UI เกม  
- ❌ EVO ไม่ถือ project runtime memory แทนโปรเจกต์ลูก  

โค้ดเกมอยู่ที่: `../projects/openworld-fantasy/`

## การใช้งานย่อ

ดูคู่มือเต็มใน `zmos-gen4-v0.4.0/README.md`

```text
zcl sync | start | doctor | preflight | status
```

เมื่อฝัง governance เข้าโปรเจกต์เกม — สร้าง `.z-mos/` ที่ **root โปรเจกต์เกม** ไม่แก้ EVO เป็นที่เก็บ state เกม
