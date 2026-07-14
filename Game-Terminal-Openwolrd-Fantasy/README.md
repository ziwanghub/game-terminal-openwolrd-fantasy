# Game-Terminal-Openwolrd-Fantasy

Workspace พัฒนาเกม terminal fantasy แบบมี **ผู้คุมกฎอาชีพ** แยกจาก **โค้ดเกม**

## บทบาทโฟลเดอร์ (ล็อกไว้)

| โฟลเดอร์ | บทบาท | ทำอะไร / ไม่ทำอะไร |
|----------|--------|---------------------|
| **`core/`** | **ผู้คุมกฎการพัฒนา (Professional Governance)** | Z-MOS Gen4 / `zcl` — กำกับ session, preflight, truth, intent, trace, trust tier · **ไม่ใช่เกม** · ไม่ใส่ feature เกมที่นี่ |
| **`projects/`** | **พื้นที่สร้างเกม** | โค้ดเกม, data, saves, tests · เปลี่ยน logic / คอนเทนต์ที่นี่ |
| **`design/`** | เอกสารความต้องการ (RD) | สเปค / roadmap · ไม่ใช่ runtime เกม |
| **`archive/`** | สำรองของเก่า | เก็บของเลิกใช้ |

```text
core/          ← กฎ · วินัย · หลักฐานการทำงาน (Z-MOS)
   │
   │  กำกับ (ไม่แทนที่ build ของเกม)
   ▼
projects/      ← ผลิตเกมจริง (openworld-fantasy)
design/        ← ความต้องการ / ออกแบบเป็นเอกสาร
archive/       ← ของเก่า
```

## core = ผู้คุมกฎมืออาชีพ

ใช้ **Z-MOS Gen4 v0.4.0** (`core/zmos-gen4-v0.4.0`)

| หลักการ | ความหมาย |
|---------|----------|
| **ไม่ใช่โปรเจกต์ลูกค้า** | EVO/core เป็น engine กำกับ — ไม่เก็บ state เกมใน core |
| **Session entry** | ก่อนงานใหญ่: `zcl start` (อ่านอย่างเดียวก่อน mutate) |
| **Execution loop** | Preflight → Execute → Validate → Verify → Document |
| **Truth-first** | authority อยู่ที่ truth / intent ของ **โปรเจกต์ที่กำลังทำ** |
| **Definition of Done** | ทำเสร็จ + verify ผ่าน + เอกสารครบ + จัดระดับ risk ที่เหลือ |

คำสั่งหลัก (รันจาก tree ของ zmos-core ตามคู่มือ Z-MOS):

```text
zcl sync | start | doctor | preflight | status | trace verify
```

รายละเอียดโปรโตคอล: `core/zmos-gen4-v0.4.0/zmos-core.md`  
คู่มือ: `core/zmos-gen4-v0.4.0/README.md`

**กฎสำคัญจาก core เอง**

- อย่าแก้ JSON state ตรงๆ — ใช้ CLI  
- Project runtime memory (`.z-mos/` ของโปรเจกต์) อยู่ที่ **project root** ไม่ฝังใน EVO  
- เกม build/test ยังเป็นของ `projects/*` — Z-MOS **เสริม governance** ไม่แทนที่ Python/pytest  

## projects = สร้างเกมที่นี่

```bash
cd projects/openworld-fantasy
python3 pixel_fantasy_openskill.py
# หรือ
python3 -m game
```

ดู: `projects/README.md` และ `projects/openworld-fantasy/README.md`

## วินัยเมื่อ AI / คนพัฒนาใน workspace นี้

1. **อ่านบทบาทโฟลเดอร์** — โค้ดเกม → `projects/` เท่านั้น  
2. **งานเฟสเกม** — ทำใน `projects/openworld-fantasy` ตาม P0–P11  
3. **งานกำกับ / ตรวจสุขภาพ session** — ใช้ `core` (Z-MOS)  
4. **เอกสารความต้องการ** — อัป `design/RD` เมื่อสเปคเปลี่ยน  
5. **ห้าม** ย้าย logic เกมเข้า `core/` หรือใช้ `core` เป็นโฟลเดอร์ feature  

## เกมปัจจุบัน

| รายการ | ค่า |
|--------|-----|
| โปรเจกต์ | `projects/openworld-fantasy` |
| โหมด | Terminal text RPG (ยังไม่มีกราฟิก) |
| เวอร์ชัน | `1.13.10-alpha` (`aoe-pack-balance`) |
| แผนที่ระบบเกม | `projects/openworld-fantasy/docs/ARCHITECTURE.md` (+ Doc Policy) |
| คุมเกม / คุม session | pytest + ARCHITECTURE · Z-MOS **lite** (ยังไม่เต็ม) |
