# TLS Status Lifecycle
**Version:** 1.0
**System:** Z-MOS v1.4.0 — TLS
**Purpose:** กำหนดสถานะ template อย่างเป็นทางการ เพื่อให้ตัดสินใจได้ว่า "ใช้ได้ / ยังใช้ไม่ได้"

---

## Status List

```
draft → tested → proven → stable → deployable → deprecated
```

---

## Status Definitions

### `draft`
| | |
|---|---|
| **ความหมาย** | ออกแบบแล้ว ยังไม่ได้ build หรือมี code จริง |
| **ใช้เมื่อ** | เพิ่งสร้าง scaffold / มีแค่ manifest + README |
| **ห้ามใช้เมื่อ** | มี source code จริงและ test ผ่านแล้ว |
| **Deploy ได้?** | ❌ ห้ามเด็ดขาด |

### `tested`
| | |
|---|---|
| **ความหมาย** | Build แล้ว + test ใน dev environment ผ่าน |
| **ใช้เมื่อ** | มี source code จริง + run ได้ใน dev + ไม่มี crash |
| **ห้ามใช้เมื่อ** | ยังไม่เคย build หรือ test |
| **Deploy ได้?** | ❌ ห้ามใช้ production |

### `proven`
| | |
|---|---|
| **ความหมาย** | ใช้งานจริงกับลูกค้า ≥1 ราย + QA ผ่าน |
| **ใช้เมื่อ** | ลูกค้าใช้จริง + flow หลักทำงานได้ + ไม่มี P1 bug |
| **ห้ามใช้เมื่อ** | ยังไม่เคยมีลูกค้าจริงใช้ |
| **Deploy ได้?** | ⚠️ ใช้ได้แบบ controlled (ต้องมีคนดูแล) |

### `stable`
| | |
|---|---|
| **ความหมาย** | ใช้งานจริงต่อเนื่อง + ผ่าน feedback cycle + ไม่มี critical issue ใหม่ |
| **ใช้เมื่อ** | production ≥1 เดือน + ไม่มี P1/P2 issue ใหม่ |
| **ห้ามใช้เมื่อ** | เพิ่ง deploy ยังไม่ผ่าน feedback |
| **Deploy ได้?** | ✅ ใช้ production ได้ |

### `deployable`
| | |
|---|---|
| **ความหมาย** | ใช้ซ้ำได้ ≥2 use cases + `zcl tls create` run ได้โดยไม่ต้องแก้ code |
| **ใช้เมื่อ** | ทุก step ของ `zcl tls create` ผ่าน + config-only customization |
| **ห้ามใช้เมื่อ** | ยังต้องแก้ code หลัง create |
| **Deploy ได้?** | ✅ ใช้ผ่าน `zcl tls create` ได้ทันที |

### `deprecated`
| | |
|---|---|
| **ความหมาย** | ถูกแทนที่แล้ว ห้ามใช้ project ใหม่ |
| **ใช้เมื่อ** | มี version ใหม่แทนแล้ว |
| **ห้ามใช้เมื่อ** | ยังไม่มี replacement |
| **Deploy ได้?** | ❌ ห้ามใช้ project ใหม่ (project เก่าที่ใช้อยู่ไม่ถูกบังคับอัปเดต) |

---

## Promotion Criteria

### `draft` → `tested`
- [ ] มี source code จริงใน `src/`
- [ ] Build ผ่าน (ไม่มี error)
- [ ] Run ได้ใน dev environment
- [ ] มี `package.json` ที่ install ได้

### `tested` → `proven`
- [ ] ลูกค้าจริงใช้งาน ≥1 ราย
- [ ] Flow หลัก (core user journey) ใช้งานได้ end-to-end
- [ ] ไม่มี P1 bug
- [ ] ผ่าน QA V1 (UI + Structure + Console)
- [ ] `customer_live_status` = `"live"`

### `proven` → `stable`
- [ ] ใช้งานจริงต่อเนื่อง ≥1 เดือน
- [ ] ผ่าน feedback cycle ≥1 รอบ (ลูกค้า feedback → แก้ → ลูกค้า confirm)
- [ ] ไม่มี P1/P2 issue ใหม่หลัง feedback
- [ ] Performance acceptable ในสภาพ production จริง

### `stable` → `deployable`
- [ ] ใช้ซ้ำได้ ≥2 use cases (ลูกค้าหรือ project ต่างกัน)
- [ ] `zcl tls create` run ได้โดยไม่ต้องแก้ code
- [ ] Config-only customization (ทุกความแตกต่างอยู่ใน config)
- [ ] มี `entry_point` ใน template.json
- [ ] `install_command` + `build_command` ทำงานได้

### Any → `deprecated`
- [ ] มี template version ใหม่แทนที่แล้ว
- [ ] ไม่มี project ที่ใช้ template นี้ (หรือมีแผนย้าย)

---

## Demotion Rules

สถานะอาจถูกลดลงเมื่อ:
- พบ P1 bug ที่ยังไม่ได้แก้ → ลดจาก `deployable`/`stable` → `proven`
- ลูกค้าหยุดใช้งาน / ยกเลิก → ลดจาก `proven` → `tested`
- Source code หายหรือ build พัง → ลดจาก `tested` → `draft`

---

## Summary Table

| Status | Definition | Deploy? | `zcl tls create`? |
|--------|------------|:-------:|:------------------:|
| draft | ออกแบบแล้ว ยังไม่มี code | ❌ | ❌ block |
| tested | Build + test ผ่าน | ❌ | ⚠️ warn |
| proven | ลูกค้าใช้จริง + QA ผ่าน | ⚠️ controlled | ⚠️ warn |
| stable | ใช้ต่อเนื่อง + ไม่มี issue | ✅ | ✅ |
| deployable | ใช้ซ้ำได้ + auto-create | ✅ | ✅ |
| deprecated | ถูกแทนที่ | ❌ ห้าม project ใหม่ | ❌ block |
