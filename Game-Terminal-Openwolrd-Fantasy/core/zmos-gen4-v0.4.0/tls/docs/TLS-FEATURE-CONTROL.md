# TLS Feature Control Model
**Version:** 1.0
**System:** Z-MOS v1.4.0 — TLS
**Purpose:** กำหนดกลไก เปิด/ปิด feature ด้วย config ไม่ใช่ code

---

## Feature Types

| Type | ควบคุมอะไร | ตัวอย่าง |
|------|-----------|---------|
| **UI Visibility** | แสดง/ซ่อน section บน UI | ปุ่ม "จอง" โผล่หรือไม่ |
| **Logic Access** | logic ทำงานหรือไม่ | Booking engine รับ request ได้ไหม |

---

## Dual Flag System

ทุก feature มี **2 flags** ควบคุมพร้อมกัน:

```json
{
  "booking": { "visible": true, "enabled": true }
}
```

| Flag | ความหมาย |
|------|----------|
| `visible` | UI render section นี้หรือไม่ |
| `enabled` | Backend logic ทำงานหรือไม่ |

---

## State Matrix

| visible | enabled | ผลลัพธ์ | Use Case |
|---------|---------|---------|----------|
| `true` | `true` | ✅ ทำงานเต็มที่ | Feature ที่ซื้อแล้ว |
| `true` | `false` | ⚠️ แสดงแต่ disabled | Upsell — แสดง "อัปเกรดเพื่อใช้งาน" |
| `false` | `true` | 🔒 Logic พร้อมแต่ซ่อน | Pre-activation / A-B test |
| `false` | `false` | ❌ ไม่มีอะไร | Feature ที่ไม่ได้ซื้อ |

---

## Safety Rules

1. **Toggle ต้องไม่ทำให้พัง**  
   `visible: false` → section ไม่ render ไม่ใช่ error  
   `enabled: false` → API return graceful rejection ไม่ใช่ crash

2. **ห้าม hardcode feature on/off ใน source code**  
   ทุก toggle ต้องมาจาก config เท่านั้น

3. **Package validates features**  
   System ต้องเช็ค features กับ package tier  
   ลูกค้าเปิด feature เกิน package ไม่ได้  
   Validation เป็น server-side

---

## Implementation Pattern

```
// Component-level rendering (recommended)
// Parent decides — child renders

function ServicePage({ config }) {
  return (
    <Layout>
      <Hero />           {/* CORE — always */}
      <Services />       {/* CORE — always */}
      
      {config.features.staff.visible && <Staff />}
      {config.features.gallery.visible && <Gallery />}
      {config.features.booking.visible && (
        <BookingCTA enabled={config.features.booking.enabled} />
      )}
      
      <Map />            {/* CORE — always */}
      <Footer />         {/* CORE — always */}
    </Layout>
  );
}
```

**Pattern rule:** ตรวจ flag ที่ parent level เท่านั้น  
ห้าม scatter `if (feature.xxx)` ทั่ว codebase
