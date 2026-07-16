# Soft Alert Bus — Vision (WO-033)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-033 |
| **โมดูล** | `game/domain/alerts.py` |
| **สถานะ** | `done` @ 1.77–1.78 · **Relic catalog** WO-034 @ 1.79 |
| **โทน** | soft text · terminal · ไม่ sound/GUI หนัก |

---

## เป้าหมาย

รวมศูนย์การแจ้งเตือน soft ของเกม — เริ่มจาก **Divine Burden**  
API เดียวให้ domain อื่นเรียกในอนาคต

---

## API

```text
build_alert(code, **ctx) -> Alert
collect_alert / emit_alert_lines(player, code, **ctx) -> List[str]
emit_alert(player, code, io=..., force=..., **ctx) -> List[str]
```

### Severity

| ระดับ | Visual |
|-------|--------|
| info | `  · …` |
| warn | `  ⚠ …` |
| crit | `render_box` หัวข้อวิกฤต |

### Throttle

เก็บ `player["_alert_throttle"]` ตาม `throttle_key` + tick (`auto_ticks` / `time_units`)

---

## Catalog

### relic.* (WO-034 — canonical)

ดูตารางเต็มใน [`RELIC_ALERT_PLAN.md`](RELIC_ALERT_PLAN.md)

| กลุ่ม | codes |
|-------|--------|
| ใส่/ถอด | equip · equip_warning · unequip |
| สู้ | aura_active · mana_drain · spirit_low/critical · morale_debuff |
| วิกฤต | critical · auto_blocked · auto_unequip |
| ใบ้ | aura_resisted · aura_strong |
| continuity | pre_fight · pre_dungeon |

`burden.*` = **alias** → `relic.*` (`resolve_alert_code`)  
`relic.spirit_*` = **ชื่อแสดง** ของขวัญ (morale) — ไม่มี Spirit แยก

### needs.* (WO-033.4)

| code | ใช้เมื่อ |
|------|----------|
| needs.hunger/fatigue/morale.* | soft warn กายใจ (WO-005 vocab) |
| needs.pressure.* | one-liner priority hint |

---

## ผูกแล้ว

- `divine_burden` equip · tick · unequip · pre_fight helper  
- `combat_session._run_combat` pre-fight + **needs record**  
- `auto_farm.auto_fight` pre-fight + **needs record**  
- `auto_farm` stop morale → auto_blocked  
- `soft_foresight` pre_dungeon  
- God auto-run summary · Soft Alert ล่าสุด  
- `combat_needs_soft_warnings` / `needs_pressure_hint` → catalog (033.4)  

---

## กฎ vitals vs history

| path | throttle | เหตุผล |
|------|----------|--------|
| `combat_needs_soft_warnings` | **ไม่** | แผง vitals ต้องโชว์สถานะปัจจุบันทุกเฟรม |
| `record_needs_soft_alerts` | **ใช่** | เข้าไฟต์/care · เก็บ history ให้ God ไม่ spam |

---

## Acceptance

- [x] equip relic → soft alert (fit/strain/crush)  
- [x] morale_crit + burden → crit alert (throttle ไม่ spam)  
- [x] auto blocked เมื่อ morale stop + burden  
- [x] pre-fight / pre-dungeon  
- [x] catalog ขยายได้ (`register_alert_def`)  
- [x] unit tests ผ่าน  
- [x] needs soft-warn ผ่าน bus · คำศัพท์ WO-005 เดิม  
- [x] record needs ตอนเข้าไฟต์ (throttle)  

---

## Changelog

| วันที่ | เหตุการณ์ |
|--------|-----------|
| 2026-07-15 | design + implement WO-033.1–.3 |
| 2026-07-15 | ship `1.77.0-alpha` · backlog/phases · God recent alerts |
| 2026-07-15 | **033.4** @ `1.78.0-alpha` · needs catalog · inline · record on fight |
| 2026-07-15 | **WO-034.0–1** @ `1.79.0-alpha` · relic.* catalog · burden alias |
