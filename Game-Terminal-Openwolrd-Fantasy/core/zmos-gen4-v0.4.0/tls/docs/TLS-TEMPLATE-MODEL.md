# TLS Template Model
**Version:** 1.0
**System:** Z-MOS v1.4.0 — TLS
**Purpose:** กำหนดว่า Template คืออะไร มีกี่ layer แต่ละ layer ทำอะไร

---

## Definition

Template = พิมพ์เขียวที่พิสูจน์แล้วว่าใช้งานได้  
ไม่ใช่ mockup ไม่ใช่ prototype  
ต้องผ่านการใช้งานจริงก่อนเข้า TLS

---

## Template Layers

### CORE (Lock)
ส่วนที่ **ห้ามเปลี่ยน** โครงสร้าง — อยู่ทุก project ทุก package

| Section | Description |
|---------|-------------|
| Header/Nav | Logo + ชื่อร้าน + navigation |
| Hero | Banner หลัก + CTA หลัก |
| Services | รายการบริการ + ราคา |
| Map/Location | แผนที่ + ข้อมูลติดต่อ |
| Footer | ข้อมูลร้าน + social links |

**Rule:** เปลี่ยนได้แค่ content (ข้อความ, รูป, สี) ผ่าน config  
ห้ามเปลี่ยน layout หรือลบออก

### FEATURE (Toggle)
ส่วนที่ **เปิด/ปิดได้** จาก config โดยไม่แก้ code

| Section | Description |
|---------|-------------|
| Staff/Therapist | แสดงทีมงาน |
| Gallery | รูปภาพผลงาน |
| Booking CTA | ปุ่มจอง + booking flow |
| Promotions | โปรโมชันพิเศษ |
| Admin Dashboard | หลังบ้านจัดการข้อมูล |

**Rule:** ซ่อนไม่ render ≠ code พัง  
Feature ปิดแล้วระบบต้องทำงานปกติ

### EXTENSION (Future)
ส่วนที่ **ยังไม่มีใน codebase** ต้องพัฒนาก่อนใช้

| Section | Description |
|---------|-------------|
| Reviews/Testimonials | รีวิวลูกค้า |
| Loyalty Program | สะสมแต้ม |
| LINE OA Automation | Messaging อัตโนมัติ |
| Multi-branch | หลายสาขา |

**Rule:** ไม่ render จนกว่าจะ build + enable  
ไม่เปิดจาก config ได้ถ้า code ยังไม่มี

---

## Template File Standard

ทุก template directory ต้องมี:

```
template-name/
├── template.json        ← Manifest (REQUIRED)
├── config.default.json  ← Default config values
├── README.md            ← Usage documentation
├── preview.png          ← Visual preview
└── src/                 ← Reusable source code (canonical)
```

Legacy compatibility:
- template ที่ extract มาจากระบบเก่า อนุญาตให้ใช้ `app/` ชั่วคราวในช่วง transition
- มาตรฐานสำหรับ template ใหม่/ที่อัปเดต ต้องใช้ `src/`

**Validation:** `template.json` ต้องผ่าน `schemas/template.schema.json`

---

## Status Lifecycle

```
draft → tested → proven → stable → deployable → deprecated
```

| Status | เงื่อนไข |
|--------|----------|
| draft | ออกแบบแล้ว ยังไม่ได้ build |
| tested | Build + test ใน dev |
| proven | ใช้กับลูกค้าจริง 1 ราย + QA ผ่าน |
| stable | ใช้กับ ≥2 ลูกค้า ไม่มี P1 |
| deployable | ใช้ผ่าน `zcl tls create` ได้ทันทีโดยไม่ต้องแก้ code |
| deprecated | ถูกแทนที่ ห้ามใช้กับ project ใหม่ |
