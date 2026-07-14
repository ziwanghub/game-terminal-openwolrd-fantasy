# TLS Config System
**Version:** 1.0
**System:** Z-MOS v1.4.0 — TLS
**Purpose:** กำหนดว่าอะไรเป็น config อะไรเป็น code และ config structure เป็นยังไง

---

## shop-config.json Structure

```json
{
  "shop": {
    "name": "ชื่อร้าน",
    "slug": "kebab-case-id",
    "tagline": "คำอธิบายสั้น",
    "logo": "logo.png",
    "phone": "091-xxx-xxxx",
    "line_id": "@shop-id",
    "address": "ที่อยู่",
    "map_url": "https://maps.google.com/...",
    "social": {
      "facebook": "url",
      "instagram": "url"
    }
  },

  "branding": {
    "primary_color": "#HEX",
    "secondary_color": "#HEX",
    "font": "Google Font name"
  },

  "services": [
    {
      "name": "ชื่อบริการ",
      "duration": "60 min",
      "price": 500,
      "description": "คำอธิบาย"
    }
  ],

  "staff": [
    {
      "name": "ชื่อ",
      "role": "ตำแหน่ง",
      "photo": "staff.jpg"
    }
  ],

  "hours": {
    "mon-fri": "10:00-21:00",
    "sat-sun": "09:00-22:00"
  },

  "features": {
    "booking":    { "visible": true,  "enabled": true },
    "staff":      { "visible": true,  "enabled": true },
    "gallery":    { "visible": false, "enabled": false },
    "promotions": { "visible": false, "enabled": false },
    "admin":      { "visible": true,  "enabled": true },
    "payments":   { "visible": false, "enabled": false }
  },

  "package": "pro"
}
```

---

## Config vs Code Boundary

| สิ่งนี้ | Config | Code | เหตุผล |
|---------|:------:|:----:|--------|
| ชื่อร้าน / โลโก้ / สี | ✅ | | ต่างกันทุกร้าน |
| รายการบริการ + ราคา | ✅ | | ข้อมูลธุรกิจ |
| เวลาเปิด-ปิด | ✅ | | เปลี่ยนได้ |
| Feature on/off | ✅ | | toggle ตาม package |
| Package tier | ✅ | | ระดับบริการ |
| Booking flow logic | | ✅ | ระบบซับซ้อน |
| Payment processing | | ✅ | ต้อง secure |
| Auth/Session | | ✅ | security logic |
| Template layout | | ✅ | โครงสร้างหน้า |
| Hash chain integrity | | ✅ | enforcement system |

**กฎ:** ถ้าเปลี่ยนค่าแล้วต้องแก้ code → ข้อมูลนั้นอยู่ผิดที่

---

## Config Ownership

| ที่อยู่ | เจ้าของ | เปลี่ยนได้เมื่อ |
|---------|---------|----------------|
| `tls/templates/*/config.default.json` | TLS (blueprint) | เมื่อ update template version |
| `project/shop-config.json` | Project (runtime) | เมื่อลูกค้าเปลี่ยนข้อมูลร้าน |

**Rule:** project config override TLS default  
TLS default เป็นตัวอย่าง project config เป็นของจริง

---

## Validation

ทุก `shop-config.json` ต้องผ่าน `schemas/config.schema.json` ก่อน deploy

ถ้าไม่ผ่าน → **deploy blocked**

Validation ตรวจ:
- required fields ครบ
- color format ถูก (#HEX)
- slug เป็น kebab-case
- price ≥ 0
- features มี visible + enabled ทุก entry
- package เป็น basic / pro / premium
