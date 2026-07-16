# Relic Alert Catalog — Plan (WO-034)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-034 |
| **โมดูล** | `game/domain/alerts.py` |
| **ขึ้นกับ** | Soft Alert Bus (WO-033) · Divine Burden |
| **สถานะ** | **done** เฟส 0–5 @ 1.79–1.81.0-alpha |

---

## ล็อกเฟส 0 (rule lock)

1. **namespace หลัก = `relic.*`**
2. **`relic.spirit_*` = ชื่อแสดงผลของขวัญ (morale)** — ไม่สร้าง Spirit resource ใหม่
3. **`burden.*` → alias ไป `relic.*`** (call site เก่ายังใช้ได้ · history เก็บ canonical)
4. Soft DNA: ข้อความ · throttle · ไม่ hard lock · ไม่ธนาคาร/FX/online
5. `needs.*` แยก namespace — ไม่ปน relic

---

## Catalog (canonical)

### 1 ใส่ / ถอด

| code | sev | throttle | หมายเหตุ |
|------|-----|----------|----------|
| `relic.equip` | info | 0 | ใส่สำเร็จ ภาระเบา |
| `relic.equip_warning` | warn | 0 | ภาระสูง (strain/crush) |
| `relic.unequip` | info | 0 | ถอดมือ/auto (wire เฟส 2) |

### 2 สู้

| code | sev | throttle | หมายเหตุ |
|------|-----|----------|----------|
| `relic.aura_active` | info | once_session | เทิร์นแรก (wire เฟส 3) |
| `relic.mana_drain` | warn | 3 | ดูด/บางมานา |
| `relic.spirit_low` | warn | 4 | morale low + relic |
| `relic.spirit_critical` | crit | 5 | morale crit + relic |
| `relic.morale_debuff` | warn | 4 | optional ขณะ drain |

### 3 วิกฤต / Auto

| code | sev | throttle | หมายเหตุ |
|------|-----|----------|----------|
| `relic.critical` | crit | 5 | umbrella ใกล้พัง (wire เฟส 4) |
| `relic.auto_blocked` | crit | 3 | alias จาก burden |
| `relic.auto_unequip` | warn | 0 | alias จาก burden |

### 4 ใบ้ (เฟส 5)

| code | sev | throttle | หมายเหตุ |
|------|-----|----------|----------|
| `relic.aura_resisted` | info | 5 | catalog only · ยังไม่มี rule ต้าน |
| `relic.aura_strong` | warn | 4 · once | catalog only |

### Continuity

| code | sev | หมายเหตุ |
|------|-----|----------|
| `relic.pre_fight` | warn | จาก burden.pre_fight |
| `relic.pre_dungeon` | warn | จาก burden.pre_dungeon |

---

## Alias map (burden → relic)

| legacy | canonical |
|--------|-----------|
| `burden.equip.fit` | `relic.equip` |
| `burden.equip.strain` | `relic.equip_warning` |
| `burden.equip.crush` | `relic.equip_warning` |
| `burden.morale_low` | `relic.spirit_low` |
| `burden.morale_crit` | `relic.spirit_critical` |
| `burden.mana_thin` | `relic.mana_drain` |
| `burden.auto_unequip` | `relic.auto_unequip` |
| `burden.auto_blocked` | `relic.auto_blocked` |
| `burden.pre_fight` | `relic.pre_fight` |
| `burden.pre_dungeon` | `relic.pre_dungeon` |

API: `resolve_alert_code(code)` · `ALERT_CODE_ALIASES`

---

## เฟส implement

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **0** | ล็อกแผน + spirit=morale | **done** |
| **1** | catalog relic.* + alias + sev/throttle | **done** |
| **2** | equip / equip_warning / unequip wire | **done** @ 1.80 |
| **3** | aura_active · mana_drain · spirit_* tick | **done** @ 1.80 |
| **4** | critical · auto_* ใช้ relic code ชัด | **done** @ 1.80 |
| **5** | aura_resisted · polish โทน | **done** @ 1.81 |

### Wire map (เฟส 2–4)

| code | ผูกที่ |
|------|--------|
| `relic.equip` / `equip_warning` | `on_equip_burden_note` |
| `relic.unequip` | `on_unequip_burden_note` ← `unequip_slot` (manual) |
| `relic.auto_unequip` | `try_auto_unequip_burden` (skip plain unequip) |
| `relic.auto_blocked` | `auto_farm` morale stop |
| `relic.pre_fight` + `aura_active` | `pre_fight_burden_alerts` |
| `relic.pre_dungeon` | `soft_foresight` |
| `relic.spirit_*` / `morale_debuff` / `mana_drain` / `critical` | `apply_burden_tick` |
| `relic.aura_strong` | equip crush · pre_fight · aura crush press |
| `relic.aura_resisted` | `apply_relic_aura` เมื่อ soft resist สำเร็จ |

### เฟส 5 soft resist (ไม่สร้าง resource ใหม่)

ใช้ affinity · intelligence · gear_status_resist · morale · blessing tag  
chance cap ~0.55 · crush ยากกว่า strain

### โทน

- `{band_th}` แทน strain/crush ดิบ (ร้อนมือ / หนักเกินตัว)
- ตัด meta ในข้อความ player (ไม่โชว์ `spirit=ขวัญ` / `band=`)

---

## Acceptance

- [x] catalog มี `relic.*` ครบตามแผน  
- [x] alias burden → relic  
- [x] severity/throttle ต่อ code  
- [x] `build_alert("burden…")` ได้ code canonical  
- [x] history เก็บ `relic.*`  
- [x] tests ผ่าน  
- [x] equip / unequip / auto / pre-fight wire  
- [x] spirit + mana_drain + critical tick  
- [x] aura_resisted soft + polish โทน  

---

## Changelog

| วันที่ | เหตุการณ์ |
|--------|-----------|
| 2026-07-15 | ล็อกแผน · implement เฟส 0–1 @ 1.79.0-alpha |
| 2026-07-15 | เฟส 2–4 wire @ 1.80.0-alpha |
| 2026-07-15 | เฟส 5 polish @ 1.81.0-alpha |
