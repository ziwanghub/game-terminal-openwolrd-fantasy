# TLS Rules — Admission, Usage, and Category
**Version:** 1.0
**System:** Z-MOS v1.4.0 — TLS

---

## Part 1: Admission Rules

A template or module may enter TLS **only when ALL** conditions are met:

### ✅ Required (ALL must be true)
1. **Used in production** — deployed and used by a real client
2. **No P1 bugs** — zero Priority 1 issues at time of admission
3. **QA V1 passed** — completed 3-layer audit (UI + Structure + Console)
4. **End-to-end functional** — full flow works, not partial implementation
5. **Not custom-only** — logic is generalizable, not one-client-specific
6. **Reusable ≥ 2 use cases** — proven or applicable to at least 2 different clients

### ❌ Prohibited
- Dumping an entire project into TLS without extraction
- Storing client data (names, bookings, transactions)
- Storing secrets, API keys, or environment-specific config
- Storing config for a specific shop (belongs in project, not TLS)
- Adding "draft" templates that were never built or tested

---

## Part 2: Category Structure

### Template Categories

Template ต้องอยู่ใน category ใดหนึ่ง:

Canonical template type enum:
`landing | booking | admin | member | bundle`

| Category | คืออะไร | ตัวอย่าง |
|----------|---------|---------|
| `landing` | Landing page / หน้าร้านหลัก | premium-massage-v1 |
| `booking` | Booking flow / จองคิว | booking-standard-v1 |
| `admin` | Admin dashboard / หลังบ้าน | admin-spa-v1 |
| `member` | Member area / หน้าสมาชิก | member-basic-v1 |
| `bundle` | ชุดรวมหลาย template | spa-complete-v1 |

### Directory Rule

```
tls/templates/
├── landing/         ← landing category only
├── booking/         ← booking category only
├── admin/           ← admin category only
├── member/          ← member category only
└── bundles/         ← bundle category only
```

Canonical mapping:
- Template `type: "bundle"` ต้องเก็บใน folder `tls/templates/bundles/`

ห้ามสร้าง subdirectory นอก 5 categories นี้

### Project Instance Rule

| สิ่งนี้ | TLS? | Project? |
|---------|:----:|:--------:|
| Template blueprint | ✅ | copied from TLS |
| Client data | ❌ | ✅ |
| shop-config.json (real) | ❌ | ✅ |
| config.default.json (example) | ✅ | ❌ |
| .z-mos/ runtime state | ❌ | ✅ |
| Source code (template) | ✅ | copied from TLS |
| Source code (customization) | ❌ | ✅ |

---

## 🚨 Template Usage Rule

การเลือกใช้ template ใน production ต้องอิงตาม `status` ใน manifest:

| Status | Usage Policy |
|--------|--------------|
| `draft` / `tested` | ❌ **ห้ามใช้** deploy production เด็ดขาด |
| `proven` | ⚠️ ใช้ได้แบบ **controlled** (ต้องมี agent ดูแลใกล้ชิด) |
| `stable` | ✅ ใช้ production ได้ตามปกติ |
| `deployable` | ✅ ใช้ผ่าน `zcl tls create` ได้ทันที (Auto-pilot) |
| `deprecated` | ❌ **ห้ามใช้** สำหรับ project ใหม่ |

---

## Part 3: Usage Rules

เมื่อ Z-MOS ใช้ TLS template สำหรับ project ใหม่:

1. **ห้ามแก้ template โดยตรง** — `tls/templates/` เป็น read-only blueprint
2. **ต้อง copy → project runtime** — template ถูก copy เข้า project, TLS original ไม่เปลี่ยน
3. **Config override ผ่าน config file เท่านั้น** — ทุกความแตกต่างอยู่ใน `shop-config.json`
4. **Feature toggle ต้องมาจาก config** — ห้าม hardcode on/off ใน source code
5. **Schema validation ก่อนใช้** — `template.json` + `shop-config.json` ต้องผ่าน validation

---

## Part 4: Registry Rules

1. ทุก template ที่ admitted ต้อง registry ใน `template-registry.json`
2. ทุก module ที่ admitted ต้อง registry ใน `module-registry.json`
3. Registry ในเฟสปัจจุบันทำหน้าที่เป็น **governance index/catalog** ของสิ่งที่ admitted ใน TLS
4. Deprecated items คงอยู่ใน registry ด้วย `status: "deprecated"`
5. Runtime ปัจจุบัน (`zcl tls create`) ยังไม่ enforce registry เป็น operational source of truth

---

## Part 5: Modification Rules

### Template Update
- Update ต้องขึ้น version (semver)
- ห้ามแก้ in-place โดยไม่ขึ้น version
- ทุก update ต้องผ่าน admission criteria ใหม่

### Breaking Change
- ถ้าเปลี่ยน config structure → major version bump
- ต้องมี migration guide
- Project ที่ใช้ version เดิม ไม่ถูกบังคับอัปเดต
