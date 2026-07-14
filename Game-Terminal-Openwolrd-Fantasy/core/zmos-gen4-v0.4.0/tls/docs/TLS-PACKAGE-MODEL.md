# TLS Package Model
**Version:** 1.0
**System:** Z-MOS v1.4.0 — TLS
**Purpose:** กำหนด package tiers และ feature mapping

---

## Package Tiers

| Feature | Basic | Pro | Premium |
|---------|:-----:|:---:|:-------:|
| Landing Page (CORE) | ✅ | ✅ | ✅ |
| Services List (CORE) | ✅ | ✅ | ✅ |
| Map/Contact (CORE) | ✅ | ✅ | ✅ |
| Staff Section | ❌ | ✅ | ✅ |
| Gallery | ❌ | ✅ | ✅ |
| Booking System | ❌ | ✅ | ✅ |
| Admin Dashboard | ❌ | ✅ | ✅ |
| Promotions | ❌ | ❌ | ✅ |
| Payment Integration | ❌ | ❌ | ✅ |
| Reviews | ❌ | ❌ | ✅ |

---

## Package Definitions

```json
{
  "basic": [
    "landing", "services", "map", "contact"
  ],
  "pro": [
    "landing", "services", "map", "contact",
    "staff", "gallery", "booking", "admin"
  ],
  "premium": [
    "landing", "services", "map", "contact",
    "staff", "gallery", "booking", "admin",
    "promotions", "payments", "reviews"
  ]
}
```

---

## Activation Rules

### เมื่อ deploy ร้านใหม่:

1. อ่าน `package` จาก `shop-config.json`
2. Lookup package definition → ได้ list features ที่อนุญาต
3. ตั้ง feature flags ทุกตัวตาม package
4. Feature ที่ไม่อยู่ใน package → `{ visible: false, enabled: false }`

### Validation:

```
for each feature in config.features:
  if feature NOT in package_definition[config.package]:
    if feature.visible == true OR feature.enabled == true:
      → BLOCK deployment
      → Error: "feature X not included in package Y"
```

### Rules:

1. ลูกค้าห้ามเปิด feature เกิน package แม้จะแก้ config เอง
2. Validation เป็น **server-side** ไม่ใช่ client-side only
3. อัปเกรด package → features เปิดเพิ่มเติมอัตโนมัติจาก definition
4. ดาวน์เกรด package → features ถูกปิดทันที

---

## Package Upgrade Path

```
Basic → Pro      : +staff, +gallery, +booking, +admin
Pro   → Premium  : +promotions, +payments, +reviews
```

เมื่ออัปเกรด:
- ไม่ต้องแก้ code
- เปลี่ยน `"package": "pro"` → `"package": "premium"` ใน config
- System เปิด features ที่เพิ่มขึ้นอัตโนมัติ
