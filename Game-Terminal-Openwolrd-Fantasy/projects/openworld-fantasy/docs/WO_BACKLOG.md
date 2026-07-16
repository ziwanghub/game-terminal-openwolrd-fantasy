# WO Backlog — Pixel Fantasy Open Skill Improvement

| ฟิลด์ | ค่า |
|--------|-----|
| **ชื่อเต็ม** | Work Order Backlog · Pixel Fantasy Open Skill / Open World Fantasy |
| **สถานะเอกสาร** | **เริ่มสะสม** |
| **วันที่เริ่ม** | 15 ก.ค. 2569 (2026-07-15) |
| **เวอร์ชันอ้างอิงเกม** | `1.58.0-alpha` (`ux-field-character-auto`) · source: `game/config.py` |
| **หมายเหตุ UX** | WO-002 **Deferred / Simplified** — `WORLD_THEME_UX_ENABLED=False` (เล่นแบบเลือกโลกง่าย) |
| **เจ้าของ** | ทีม openworld-fantasy |
| **ความสัมพันธ์** | คิวเชิง product ยาว → [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md) · ภาพรวม → [`ROADMAP.md`](ROADMAP.md) · สถาปัตย์ → [`ARCHITECTURE.md`](ARCHITECTURE.md) |

---

## 0. เอกสารนี้คืออะไร

| ใช่ | ไม่ใช่ |
|-----|--------|
| **Backlog กลางของ Work Order (WO)** ที่จะทำ/กำลังทำ/ทำแล้ว | Changelog รายเวอร์ชัน (`PHASES.md`) |
| สเปกสั้น + Acceptance Criteria ต่อ WO | Design doc เต็มระบบ (ลิงก์ไป docs รายระบบ) |
| จุดเดียวที่ engineer / AI / SA ดึงงานไป implement | แทนที่ IMPROVEMENT_PLAN ทั้งก้อน |

### สถานะ WO ที่ใช้

| สถานะ | ความหมาย |
|--------|----------|
| `backlog` | รับเข้าคิวแล้ว ยังไม่เริ่ม |
| `ready` | สเปกชัด พร้อมหยิบ |
| `in_progress` | กำลังทำ |
| `blocked` | ติด dependency / ตัดสินใจ |
| `deferred` | พักไว้ · โค้ดอาจมีแต่ปิดใช้งาน / รอ UX |
| `done` | ปิดแล้ว (ใส่เวอร์ชันที่ ship) |
| `cancelled` | ยกเลิก พร้อมเหตุผลสั้นๆ |

### กฎสั้นๆ

1. **WO ใหม่** เพิ่มท้าย §2 ด้วยเลขรัน `WO-00N` (ไม่ reuse เลขที่ยกเลิก)  
2. เปลี่ยนสถานะในตาราง §1 และในหัวการ์ด §2 ให้ตรงกัน  
3. เมื่อ `done` → ใส่ `Shipped in:` version + วันที่  
4. งานใหญ่ที่ยังไม่เป็น WO → อยู่ IMPROVEMENT_PLAN จนกว่าจะแตกเป็น WO  
5. อย่าทำ online/web ก่อน solo นิ่ง (ทิศ product ล็อกแล้ว)

---

## 1. ดัชนี WO (สแกนเร็ว)

| ID | ชื่อ | Priority | หมวด | สถานะ |
|----|------|----------|------|--------|
| [WO-001](#wo-001-enhance-game-start-launcher) | Enhance game-start Launcher | Medium | Infrastructure / DX | `backlog` |
| [WO-002](#wo-002-improve-world-selection--new-world-creation-flow) | Improve World Selection & New World Creation Flow | High | UX / Onboarding / Open Progression | `deferred` (simplified) |
| [WO-004](#wo-004-core-needs-stabilization--phase-1) | Core Needs Stabilization — Phase 1 | High | Survival / Auto / Needs | `done` @ 1.56.0-alpha |
| [WO-005](#wo-005-needs-visibility--integration-p15) | Needs Visibility & Integration (P1.5) | High | Combat UI / Needs | `done` @ 1.58.0-alpha |
| [WO-010](#wo-010-add-auto-play-into-combat-screen) | Add Auto Play into Combat Screen | High | Combat / Auto / UX | `done` @ 1.60.0-alpha |
| [WO-011](#wo-011-playtest-preparation--auto-run-summary-system) | Playtest Preparation & Auto Run Summary | High | Playtest / Auto / DX | `done` @ 1.61.0-alpha |
| [WO-012](#wo-012-soft-death--defeat-experience-polish) | Soft Death & Defeat Experience Polish | High | Combat / Feedback | `done` @ 1.62.0-alpha |
| [WO-013](#wo-013-continuous-auto-combat--structured-fight-log) | Continuous Auto Combat + Fight Log | High | Combat / Auto / UX | `done` @ 1.62.0-alpha |
| [WO-015](#wo-015-needs-parity--playtest-foundation) | Needs Parity & Playtest Foundation | High | Needs / Parity | `done` @ 1.63.0-alpha |
| [WO-016](#wo-016-god-measurement--log) | God Measurement & Log | High | Playtest / DX | `done` @ 1.63.0-alpha |
| [WO-021](#wo-021-economy-balance--needs-connection) | Economy Balance & Needs Connection | High | Economy / Auto / Needs | `done` @ 1.66.0-alpha |
| [WO-022](#wo-022-economy-follow-up-polish--playtest) | Economy Follow-up Polish & Playtest | High | Economy / Auto / Playtest | `done` @ 1.67.0-alpha |
| [WO-023](#wo-023-divine-burden-system--full-phase) | Divine Burden System — Full Phase | High | Gear / Needs / God-sim | `done` @ 1.68.0-alpha |
| [WO-024](#wo-024-divine-burden-polish--world-hooks) | Divine Burden Polish & World Hooks | High | Gear / Echo / Content | `done` @ 1.69.0-alpha |
| [WO-025](#wo-025-relic-quests--auto-echo-avoid) | Relic Quests & Auto Echo Avoid | Medium | Quest / Auto / Burden | `done` @ 1.70.0-alpha |
| [WO-026](#wo-026-playtest-stabilize--polish-round) | Playtest Stabilize & Polish Round | High | Playtest / Burden / UX | `done` @ 1.71.0-alpha |
| [WO-027](#wo-027-relic-depth--chamber-polish) | Relic Depth & Chamber Polish | High | Relic / Chamber / Economy | `done` @ 1.72.0-alpha |
| [WO-028](#wo-028-human-playtest-round) | Human Playtest Round | High | Playtest / God / Relic | `done` @ 1.73.0-alpha |
| [WO-029](#wo-029-area-loop-polish-forest--marsh) | Area Loop Polish (Forest & Marsh) | High | Content / Quest / Flavor | `done` @ 1.73.0-alpha |
| [WO-030](#wo-030-human-feedback--polish-round) | Human Feedback & Polish Round | High | Playtest / Balance / UX | `done` @ 1.74.0-alpha |
| [WO-031](#wo-031-area-loop-polish-cave--desert) | Area Loop Polish (Cave & Desert) | High | Content / Quest / Flavor | `done` @ 1.75.0-alpha |
| [WO-032](#wo-032-area-loops-complete-map) | Area Loops Complete Map | High | Content / Quest / Flavor | `done` @ 1.76.0-alpha |
| [WO-033](#wo-033-soft-alert-bus) | Soft Alert Bus | High | UX / Burden / Domain | `done` @ 1.77–1.78.0-alpha |
| [WO-034](#wo-034-relic-alert-catalog) | Relic Alert Catalog | High | UX / Relic / Soft Alert | `done` @ 1.79–1.81.0-alpha |
| [WO-035](#wo-035-stat--relationship-architecture) | Stat & Relationship Architecture | High | Stats / UI / Social | `done` lite @ 1.82.0-alpha |
| [WO-036](#wo-036-stat-architecture-polish--playtest) | Stat Architecture Polish & Playtest | High | Playtest / UX / Soft | `done` @ 1.83.0-alpha |
| [WO-037](#wo-037-anima-presence--soft-moments) | Anima Presence & Soft Moments | High | Spirit / Soft Alert / Feel | `done` @ 1.84.0-alpha |
| [WO-038](#wo-038-world-relations-lite) | World Relations Lite (Divine/Infernal) | High | Social / Soft Alert / World | `done` @ 1.85.0-alpha |
| [WO-039](#wo-039-faction-mini-moments) | Faction Mini-Moments | High | Content / Soft / World | `done` @ 1.86.0-alpha |
| [WO-040](#wo-040-anima--relic-depth) | Anima × Relic Depth | High | Spirit / Relic / Soft | `done` @ 1.87.0-alpha |
| [WO-041](#wo-041-relic-soft-bonds) | Relic Soft Bonds | High | Spirit / Relic / Soft | `done` @ 1.88.0-alpha |
| [WO-042](#wo-042-area-mini-moments--relic-content) | Area Mini-Moments + Relic Content | High | Content / Soft / Relic | `done` @ 1.89.0-alpha |
| [WO-043](#wo-043-bond-soft-cap--3-piece-chorus) | Bond Soft Cap + Soft Chorus | High | Spirit / Relic / Soft | `done` @ 1.90.0-alpha |
| [WO-044](#wo-044-area-loop-flavor--soft-foresight) | Area Loop Flavor + Soft Foresight | High | Content / Soft / World | `done` @ 1.91.0-alpha |
| [WO-045](#wo-045-playtest-polish-รอบใหญ่) | Playtest Polish รอบใหญ่ | High | Playtest / Soft / DNA | `done` @ 1.92.0-alpha |
| [WO-046](#wo-046-relic--moment-soft-synergy-lite) | Relic × Moment Soft Synergy | High | Relic / World / Soft | `done` @ 1.93.0-alpha |
| [WO-047](#wo-047-human-feedback-round--feel-polish) | Human Feedback + Feel Polish | High | Playtest / Soft / DNA | `done` @ 1.94.0-alpha |

*อัปเดตตารางนี้ทุกครั้งที่มี WO ใหม่หรือเปลี่ยนสถานะ*  
*WO-003: เลขเว้นว่าง — ใช้ WO-004 ตามคิว Needs Phase 1*

---

## 2. รายละเอียด WO

### WO-001 Enhance game-start Launcher

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-001 |
| **ชื่อ** | Enhance game-start Launcher |
| **Priority** | Medium |
| **หมวด** | Infrastructure / Developer Experience |
| **สถานะ** | `backlog` |
| **เวอร์ชันอ้างอิงตอนรับ** | 1.54.0-alpha |
| **ไฟล์หลัก** | `scripts/game-start` · (ทางลัด) `game-start` ที่ root โปรเจกต์ |
| **Shipped in** | — |

#### รายละเอียด

- ปรับ **error message + help** ให้ user-friendly มากขึ้น (ไทย/อังกฤษ)
- เพิ่ม **auto venv detection** + แนะนำ `pip install -e ".[dev]"` เมื่อสภาพแวดล้อมไม่พร้อม
- เพิ่ม flag: `--clean` · `--update-deps` · `--debug`
- **รักษา** path resolution (symlink) และ `exec` เดิมไว้

#### Acceptance Criteria

- [ ] รัน `game-start` ได้จากทุกที่
- [ ] help ชัด (ไทย + อังกฤษสั้น)
- [ ] error ชี้นำ setup
- [ ] flag เดิม + ใหม่ทำงาน

---

### WO-002 Improve World Selection & New World Creation Flow

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-002 |
| **ชื่อ** | Improve World Selection & New World Creation Flow |
| **Priority** | High |
| **หมวด** | UX / Onboarding / Open Progression |
| **สถานะ** | **`deferred` / Simplified** (ผู้ใช้ชอบแบบเดิม — ง่าย ไม่สับสน) |
| **เวอร์ชันอ้างอิงตอนรับ** | 1.54.0-alpha |
| **ไฟล์หลัก** | `game/domain/world_creation.py` · `game/services/world_service.py` · `game/app.py` · `data/worlds/themes.yaml` · `game/config.py` (`WORLD_THEME_UX_ENABLED`) |
| **Shipped in** | code @ `1.55.0-alpha` · **runtime default = simple (off)** |

#### รายละเอียด (สเปกเดิม — พัก)

- Soft Flavor + Area Theme เมื่อเลือกโลก
- ตั้งชื่อโลก + เลือกธีมเริ่มต้น (mastery / open skill)
- รู้สึกสร้างโลกของตัวเอง · Open Skill Emergence

#### สถานะปัจจุบัน (Simplified)

- **เล่นจริง:** รายการโลก catalog + สร้างตัวในโลก (แบบเดิม) — **ไม่มี** เมนูสร้างโลก/ธีม
- โค้ด WO-002 **ยังอยู่** ปิดด้วย `WORLD_THEME_UX_ENABLED = False` ใน `game/config.py`
- เปิดใหม่ทีหลัง: ตั้ง `True` แล้วรันเทสต์ที่ mark `enable_theme_ux`

#### Acceptance Criteria (เมื่อ reopen)

- [ ] ธีม/flavor ไม่ทำให้ onboarding สับสน (UX ผ่าน playtest)
- [ ] มีโหมด simple เป็น default เสมอ
- [ ] custom world optional ชัดเจน

#### บันทึก

- 2026-07-15 implement full path @ 1.55.0-alpha  
- 2026-07-15 **defer:** กลับ simple picker · เก็บโค้ด · flag off

---

### WO-004 Core Needs Stabilization — Phase 1

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-004 |
| **ชื่อ** | Core Needs Stabilization — Phase 1 |
| **Priority** | High |
| **หมวด** | Survival / Auto Agent / Needs |
| **สถานะ** | `done` |
| **เวอร์ชันอ้างอิงตอนรับ** | 1.55.0-alpha |
| **เอกสารออกแบบ** | [`NEEDS_PHASE1_DESIGN.md`](NEEDS_PHASE1_DESIGN.md) |
| **ไฟล์หลัก** | `game/domain/needs.py` · `game/runtime/auto_farm.py` · `game/runtime/dungeon_auto.py` |
| **Shipped in** | `1.56.0-alpha` (2026-07-15) |

#### วัตถุประสงค์

ทำให้ระบบ Needs เป็นฐานเอาชีวิตรอดที่ **สมมาตรระหว่างมือและออโต้**  
เป้าหมายเฟส: **Auto ต้องกลัวหิว กลัวล้า และกลัวขวัญพังเหมือนมือ**

#### งานในเฟสนี้

1. **auto_fight ใช้กฎเดียวกับ combat_session (เท่าที่สมเหตุสมผล)**  
   - เรียก `apply_needs_event` ระหว่าง/จบไฟต์ออโต้  
   - morale → skill fail / block ใน auto  
   - fatigue → จังหวะโจมตีใน auto (จำลอง ไม่บังคับ ATB เต็ม)  
   - ใช้ `combat_needs_mults` กับดาเมจ  
2. **ขยาย auto_prefs รองรับ Morale**  
   - threshold + policy เมื่อขวัญต่ำ (caution / retreat)  
3. **Rest เป็นตัวเลือก Auto Agent**  
   - dungeon_auto / field auto เมื่อ fatigue (และ morale ตาม policy)  
4. **Logging / visibility**  
   - soft reason: ทำไมกิน พัก เลี่ยงไฟต์ หยุด  

#### หลักการ

- ไม่เพิ่ม sickness / แยก thirst  
- ใช้ของเดิม: `auto_prefs`, `use_items_by_thresholds`, `apply_needs_event`  
- เน้นสมมาตร manual ↔ auto  
- **ออกแบบก่อน → implement ทีละส่วน** (P1.1–P1.5 ใน design doc)

#### นอกสcope (เฟส 2–3)

- Proactive planner ลึก · near-collapse ล้า/ขวัญเต็มรูป  
- Collapse ครบ · chronicle · party link · God dashboard  

#### Acceptance Criteria

- [x] auto_fight ใช้ needs เดียวกับมือ (tick/win-loss/mults/morale/fatigue)  
- [x] auto_prefs morale + low_morale_policy  
- [x] Rest ใน dungeon/field auto  
- [x] soft log เหตุผลการ care  
- [x] เทสต์ unit path หลักผ่าน  

#### บันทึก

- 2026-07-15: รับ WO-004 · เขียน design  
- 2026-07-15: **P1.1** auto_fight needs  
- 2026-07-15: **Phase 1 complete** @ 1.56.0-alpha — prefs/rest/log/field+dungeon care  
- 2026-07-15: **P1.3 enhanced** — morale bands high/mid/low/crit · eat_morale · rest_long · aggression · block boss auto  
- 2026-07-15: **P1.4 Auto Inventory** — `game/runtime/inventory_auto.py` · drop junk · stock warn · wire dungeon/field  





#### คำสั่ง implement (เมื่อพร้อม)

```text
Implement WO-004 from docs/WO_BACKLOG.md
Follow docs/NEEDS_PHASE1_DESIGN.md order P1.1 → P1.5
Do not expand into Phase 2–3 scope.
Keep soft anti-spoiler logs. Reuse domain needs APIs.
```

---


### WO-005 Needs Visibility & Integration (P1.5)

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-005 |
| **ชื่อ** | Needs Visibility & Integration (P1.5) |
| **Priority** | High |
| **หมวด** | Combat UI / Needs / Soft feedback |
| **สถานะ** | `done` |
| **Shipped in** | `1.58.0-alpha` |

#### งานที่ทำ

- [x] แสดง หิว / ล้า / ขวัญ ใน `render_combat_vitals` (บรรทัด `กายใจ`)
- [x] soft warning เมื่อ bad/low/crit (+ แท่งจังหวะเมื่อล้า)
- [x] ศัพท์ **ขวัญ** มาตรฐาน · แยกจากจิต/ฉลาด
- [x] feedback มือใกล้เคียงออโต้ (fail สกิล · situation strip)

#### ไฟล์หลัก

`game/domain/needs.py` · `game/ui_terminal/status.py` · `game/services/combat_session.py` · `game/domain/narrative.py`

---


### WO-006 Field Status Layout

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-006 |
| **สถานะ** | `done` @ 1.58.0-alpha |
| **สรุป** | หน้าสำรวจ: ตัวตน → กายใจ (หิว/ล้า/ขวัญ) เด่น → ที่/เงิน · soft warn · sights แยก |

### WO-007 Character Menu Index

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-007 |
| **สถานะ** | `done` @ 1.58.0-alpha |
| **สรุป** | เมนู 5 = index 1–6 + ดูแล R/E/H/M + A Auto Policy |

### WO-008 Auto Policy Hub

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-008 |
| **สถานะ** | `done` @ 1.58.0-alpha |
| **สรุป** | `auto_policy_hub.py` · สรุป agent soft · ตั้ง prefs/inv/ขวัญ |

### WO-010 Add Auto Play into Combat Screen

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-010 |
| **ชื่อ** | Add Auto Play into Combat Screen |
| **Priority** | High |
| **หมวด** | Combat / Auto / UX |
| **สถานะ** | `done` @ 1.60.0-alpha |
| **ไฟล์หลัก** | `game/services/combat_session.py` · `game/domain/mode_shell.py` |
| **Shipped in** | 1.60.0-alpha |

#### สรุป
- เมนูไฟต์: **8 / A** → Auto Play (ไม่รื้อ 1–7)
- ยืนยัน + สรุป policy (`care_auto_oneliner` · ขวัญ · ก้าวร้าว · แผนสกิล)
- ลูป ATB: ใช้ `_auto_pick_skill` + thresholds ยา/ขวัญ จาก P1
- หยุด: **0 / Space** หลังจังหวะ → Manual
- Soft hint เมื่อขวัญต่ำ / ล้าสูง

### WO-011 Playtest Preparation & Auto Run Summary System

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-011 |
| **ชื่อ** | Playtest Preparation & Auto Run Summary System |
| **Priority** | High |
| **หมวด** | Playtest / Auto / DX |
| **สถานะ** | `done` @ 1.61.0-alpha |
| **ไฟล์หลัก** | `game/runtime/auto_run_log.py` · `auto_farm.py` · `dungeon_auto.py` · `personal_hub.py` |
| **Shipped in** | 1.61.0-alpha |

#### สรุป
- End-of-Run Summary หลัง Field/Dungeon Auto
- Auto Run Logger (กิน/พัก/สู้/ขวัญ/หยุด) · God-readable
- เมนูตัวละคร **X = Test Run** (ติก / 60s wall clock · ดูสรุป · God Compact)
- God Compact: กายใจ + Policy เด่นทุกติก Auto

### WO-012 Soft Death & Defeat Experience Polish

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-012 |
| **สถานะ** | `done` @ 1.62.0-alpha |
| **สรุป** | `defeat.py` · soft death สมมาตรมือ/ออโต้ · near-death · สาเหตุแพ้ |

### WO-013 Continuous Auto Combat + Structured Fight Log

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-013 |
| **สถานะ** | `done` @ 1.62.0-alpha |
| **สรุป** | Continuous/Step Auto · `fight_log.py` T# ▸/◂ · Fight Report ท้ายไฟต์ |

### WO-015 Needs Parity & Playtest Foundation

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-015 |
| **สถานะ** | `done` @ 1.63.0-alpha |
| **สรุป** | combat needs tick มือ=ออโต้ · prefs playtest · soft foresight ก่อนดัน · fight log มือ |

### WO-016 God Measurement & Log

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-016 |
| **สถานะ** | `done` @ 1.63.0-alpha |
| **สรุป** | archive Auto Run history (12) · Test Run menu 9 · format_playtest_history |

---
### WO-021 Economy Balance & Needs Connection

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-021 |
| **ชื่อ** | Economy Balance & Needs Connection |
| **Priority** | High |
| **หมวด** | Economy / Auto / Needs |
| **สถานะ** | `done` |
| **Shipped in** | `1.66.0-alpha` (2026-07-15) |
| **ไฟล์หลัก** | `balance.grant_combat_money` · `auto_farm` · `inventory_auto` · `auto_policy_hub` · `items.yaml` · `dungeons.yaml` · `quests.yaml` |

#### สิ่งที่ ship

1. **รายได้สมมาตรมือ/ออโต้** — ชนะไฟต์ได้ `money_world` เสมอ; heaven/hell เป็นโบนัสเสริม  
2. **Auto ซื้อเสบียง (optional)** — `auto_buy_supplies` ใน Auto Policy Hub (A)  
3. **ราคา early อาหาร/ยาลง** · Heaven/Hell จากดัน/เควส/ชั้น  
4. **ขายขยะอัตโนมัติ** — `inv_sell_junk` (default เปิด) แทนทิ้งล้วน

#### หลักการ

- ไม่เพิ่มธนาคาร / inflation / แลกสกุล  
- โครงสร้างเดิม: shops / market / resolve_victory / auto_farm  

---

### WO-022 Economy Follow-up Polish & Playtest

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-022 |
| **ชื่อ** | Economy Follow-up Polish & Playtest |
| **Priority** | High |
| **หมวด** | Economy / Auto / Playtest |
| **สถานะ** | `done` |
| **Shipped in** | `1.67.0-alpha` (2026-07-15) |
| **ไฟล์หลัก** | `auto_farm` · `inventory_auto` · `auto_run_log` · `soft_foresight` · `auto_policy_hub` |
| **ขึ้นกับ** | WO-021 |

#### สิ่งที่ ship (ตามคำแนะนำหลัง WO-021 + Wave A)

1. **field auto money_factor 0.85 → 0.90** — ใกล้มือขึ้น  
2. **`auto_buy_supplies` default เปิด** · reserve 50 · item_mode thrift/safe คุมการใช้จ่าย  
3. **ซื้อฉุกเฉิน** เมื่ออาหาร=0 + หิว bad/crit (แม้ปิดซื้อปกติ)  
4. **สรุป Auto Run แสดงเงิน Δ / ซื้อ / ขายขยะ**  
5. **Soft Foresight** โชว์เงิน + สถานะซื้อเสบียง  
6. **Playtest Field30** → `exports/WO022_ECONOMY_PLAYTEST.md`

---

### WO-023 Divine Burden System — Full Phase

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-023 |
| **ชื่อ** | Divine Burden System — Full Phase |
| **Priority** | High |
| **หมวด** | Gear / Needs / God-sim / Playtest |
| **สถานะ** | `done` |
| **Shipped in** | `1.68.0-alpha` (2026-07-15) |
| **Vision** | [`DIVINE_BURDEN_VISION.md`](DIVINE_BURDEN_VISION.md) |
| **ขึ้นกับ** | WO-021/022 (economy อย่า regress) · Needs stable |

#### เฟส

| เฟส | รหัส | สถานะ |
|-----|------|--------|
| Vision & Rule | **023.1** | **done** |
| Divine Burden Lite | **023.2** | **done** |
| Godforge Chamber Lite | **023.3** | **done** |
| Relic Aura + Social Lite | **023.4** | **done** |
| Content + Economy Check | **023.5** | **done** |

#### ชื่อล็อก

- **Divine Burden** · **Relic Aura** · **Godforge Chamber / ห้องทดสอบเรลิก**

#### หลัก

- ใส่ได้เสมอ · โทษขวัญ soft · Chamber = sandbox · Auto ถอดภาระได้  
- ห้าม: PvP ฆ่า · ธนาคาร · permadeath · online aura  

---

### WO-024 Divine Burden Polish & World Hooks

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-024 |
| **ชื่อ** | Divine Burden Polish & World Hooks |
| **Priority** | High |
| **หมวด** | Gear / Echo / Content / UX |
| **สถานะ** | `done` |
| **Shipped in** | `1.69.0-alpha` (2026-07-15) |
| **ขึ้นกับ** | WO-023 |

#### สิ่งที่ ship (ตามคำแนะนำหลัง WO-023)

1. **Echo UI + Relic Aura menu** — ถอย / นอบน้อม / ก้าวร้าว ก่อนเข้าหาเงา  
2. **echo snapshot** เก็บ `equip_rarity_summary` + `relic_presence`  
3. **ดรอปเรลิกเบา** บนบอส/ดัน (very_rare / chance ต่ำ)  
4. **Soft Foresight + Personal hub** โชว์ภาระเรลิก  

---

### WO-025 Relic Quests & Auto Echo Avoid

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-025 |
| **ชื่อ** | Relic Quests & Auto Echo Avoid |
| **Priority** | Medium |
| **หมวด** | Quest / Auto / Divine Burden |
| **สถานะ** | `done` |
| **Shipped in** | `1.70.0-alpha` (2026-07-15) |
| **ขึ้นกับ** | WO-023 · WO-024 |

#### สิ่งที่ ship (ตามคำแนะนำหลัง WO-024)

1. **เควสเรลิก 2 สาย** — `weight_of_storm` → `relic_storm_fang` · `whisper_of_void_ring` → แหวนสุญญะ  
2. **Auto เลี่ยงเงาออร่าเรลิก** — `auto_avoid_relic_echo` (default เปิด) ไม่ pause ลูป  
3. **Policy Hub B** — เปิด/ปิด ถอดภาระ + เลี่ยงเงาออร่า  

---

### WO-026 Playtest Stabilize & Polish Round

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-026 |
| **ชื่อ** | Playtest Stabilize & Polish Round |
| **Priority** | High |
| **หมวด** | Playtest / Burden / Economy / UX |
| **สถานะ** | `done` |
| **Shipped in** | `1.71.0-alpha` (2026-07-15) |
| **คู่มือ** | [`WO026_PLAYTEST_GUIDE.md`](WO026_PLAYTEST_GUIDE.md) |
| **บันทึก** | [`exports/WO026_PLAYTEST_LOG.md`](../exports/WO026_PLAYTEST_LOG.md) |
| **ขึ้นกับ** | WO-023–025 |

#### สิ่งที่ ship

1. คู่มือ playtest + แบบบันทึก + harness `scripts/wo026_playtest_harness.py`  
2. Balance burden ปานกลางค่อนเบา (ไม่ −2/tick crush)  
3. บทเรียน 9/9 เรลิก + ใบ้ onboard  
4. God summary ภาระ/ถอด/ขวัญ · Chamber tips  

---

### WO-027 Relic Depth & Chamber Polish

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-027 |
| **ชื่อ** | Relic Depth & Chamber Polish |
| **Priority** | High |
| **หมวด** | Relic / Chamber / Economy / Flavor |
| **สถานะ** | `done` |
| **Shipped in** | `1.72.0-alpha` (2026-07-15) |
| **บันทึกสั้น** | [`exports/WO027_PLAYTEST_SHORT.md`](../exports/WO027_PLAYTEST_SHORT.md) |
| **ขึ้นกับ** | WO-026 |

#### สิ่งที่ ship

1. เควส mid: เถ้าโลกันตร์ · หักปริซึม · เกราะท้องฟ้า + ดรอปบอส/ดัน  
2. Chamber: spar หลายรอบแรงขึ้น · เมนู 7 สรุป · สรุปตอนออก  
3. Burden feel ชัดขึ้นเล็กน้อย · ยัง playable  
4. Economy soft dampen ตอน strain/crush  
5. Flavor / onboard เพิ่ม  

---

### WO-028 Human Playtest Round

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-028 |
| **ชื่อ** | Human Playtest Round |
| **Priority** | High |
| **หมวด** | Playtest / God / Relic path |
| **สถานะ** | `done` |
| **Shipped in** | `1.73.0-alpha` |
| **คู่มือ** | [`WO028_HUMAN_PLAYTEST.md`](WO028_HUMAN_PLAYTEST.md) |
| **Log** | [`exports/WO028_PLAYTEST_LOG.md`](../exports/WO028_PLAYTEST_LOG.md) |

#### สิ่งที่ ship

1. คู่มือ playtest มือ mid-relic + checklist  
2. Harness `scripts/wo028_playtest_harness.py`  
3. Test Run → **H** checklist God  

---

### WO-029 Area Loop Polish (Forest & Marsh)

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-029 |
| **ชื่อ** | Area Loop Polish — ป่ามืด & หนองหมอก |
| **Priority** | High |
| **หมวด** | Content / Quest / Flavor |
| **สถานะ** | `done` |
| **Shipped in** | `1.73.0-alpha` |
| **ขึ้นกับ** | WO-028 |

#### สิ่งที่ ship

1. เควสป่า: `forest_echoes_hunt` · `forest_night_watch`  
2. เควสหนอง: `marsh_leech_cull` · `marsh_reed_path` (hydra ผูก reed)  
3. `loop_soft` บน area yaml + ใบ้ตอนเดินทางเข้าพื้นที่  
4. area_mood ขยาย flavor ป่า/หนอง  

---

### WO-030 Human Feedback & Polish Round

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-030 |
| **ชื่อ** | Human Feedback & Polish Round |
| **Priority** | High |
| **หมวด** | Playtest / Balance / UX |
| **สถานะ** | `done` |
| **Shipped in** | `1.74.0-alpha` |
| **Log** | [`exports/WO030_PLAYTEST_LOG.md`](../exports/WO030_PLAYTEST_LOG.md) |
| **Harness** | `scripts/wo030_human_playtest.py` |
| **ขึ้นกับ** | WO-028 · WO-029 |

#### สิ่งที่ ship

1. Human-like playtest session (P1–P7) + บันทึก scores/metrics  
2. Hotfix: burden medium + soft floor · chamber แนะนำ · God ถอดชัด  
3. Quest soft_hint ในรายการ · first-relic tip · hub banner  
4. รางวัลเควสป่า/หนอง ชวนกลับเล็กน้อย  

---

### WO-031 Area Loop Polish (Cave & Desert)

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-031 |
| **ชื่อ** | Area Loop Polish — ถ้ำเงา & ทะเลทรายร้อน |
| **Priority** | High |
| **หมวด** | Content / Quest / Flavor |
| **สถานะ** | `done` |
| **Shipped in** | `1.75.0-alpha` |
| **Check** | `scripts/wo031_area_loop_check.py` · `exports/WO031_AREA_LOOPS.md` |
| **ขึ้นกับ** | WO-029 · WO-030 |

#### สิ่งที่ ship

1. **ถ้ำเงา:** `cave_bat_cull` → `cave_lantern_path` → `shadow_slayer` (ผูก lantern)  
2. **ทะเลทราย:** `desert_dune_walk` → `desert_scorpion_cull` → `desert_sun_ready` → `sun_end` (ผูก sun ready)  
3. `loop_soft` + area_mood ขยาย · ใบ้ onboard  

---

### WO-032 Area Loops Complete Map

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-032 |
| **ชื่อ** | Area Loops Complete Map (เขา·ผลึก·เมือง·รอยแยก) |
| **Priority** | High |
| **หมวด** | Content / Quest / Flavor |
| **สถานะ** | `done` |
| **Shipped in** | `1.76.0-alpha` |
| **Check** | `scripts/wo032_area_loop_check.py` |
| **ขึ้นกับ** | WO-029 · WO-031 |

#### สิ่งที่ ship

1. **เขา:** ridge → golem → titan ready → `titan_fall`  
2. **ผลึก:** shard cull → peak watch → `prism_sovereign_fall`  
3. **เมือง:** alley patrol → market echo (soft return)  
4. **รอยแยก:** edge walk → whisper cull (หลัง void_initiate)  
5. **loop_soft ครบ 8 พื้นที่**  

---

### WO-033 Soft Alert Bus

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-033 |
| **ชื่อ** | Soft Alert Bus |
| **Priority** | High |
| **หมวด** | UX / Divine Burden / Domain |
| **สถานะ** | `done` |
| **Shipped in** | `1.77.0-alpha` (+ **033.4** @ `1.78.0-alpha`) |
| **Vision** | [`SOFT_ALERT_VISION.md`](SOFT_ALERT_VISION.md) |
| **ขึ้นกับ** | WO-023+ (burden) · Needs stable |

#### สิ่งที่ ship

1. **`game/domain/alerts.py`** — `Alert` · catalog · throttle · `collect`/`emit`/`format`  
2. **catalog `burden.*`** — equip fit/strain/crush · morale · auto · pre-fight/dungeon · mana_thin  
3. **ผูก Divine Burden** — equip note · tick morale/mana · auto unequip  
4. **pre-fight** — `combat_session._run_combat` · `auto_farm.auto_fight`  
5. **auto stop** — morale + burden → `burden.auto_blocked`  
6. **soft foresight** — `burden.pre_dungeon`  
7. **God log** — Soft Alert ล่าสุดจาก `_alert_history`  
8. **tests** — `tests/unit/test_wo033_alerts.py`  

#### 033.4 Needs soft-warn เข้า bus (`1.78.0-alpha`)

1. **catalog `needs.*`** — hunger/fatigue/morale · pressure one-liners  
2. **`combat_needs_soft_warnings` / `needs_pressure_hint`** — อ่านจาก catalog (live, ไม่ throttle)  
3. **`record_needs_soft_alerts`** — เขียน history ตอนเข้าไฟต์ (มือ+ออโต้, throttle)  
4. **`format_alert_inline`** — โทน `…หิว/ล้า/ขวัญ` เดิม WO-005 

---

### WO-034 Relic Alert Catalog

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-034 |
| **ชื่อ** | Relic Alert Catalog |
| **Priority** | High |
| **หมวด** | UX / Relic / Soft Alert |
| **สถานะ** | `done` (เฟส 0–5) |
| **Shipped in** | `1.79` catalog · `1.80` wire · `1.81` polish |
| **Plan** | [`RELIC_ALERT_PLAN.md`](RELIC_ALERT_PLAN.md) |
| **ขึ้นกับ** | WO-033 Soft Alert Bus |

#### เฟส

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **0** | ล็อก `relic.*` · spirit=morale · alias | **done** |
| **1** | catalog ครบ · severity/throttle · resolve | **done** |
| **2** | equip / equip_warning / unequip wire | **done** |
| **3** | combat tick aura/mana/spirit | **done** |
| **4** | critical + auto_* | **done** |
| **5** | aura_resisted · polish โทน | **done** |

#### สิ่งที่ ship

1. **catalog `relic.*` + alias `burden.*`**  
2. **equip / equip_warning / unequip** (`on_unequip_burden_note`)  
3. **tick:** spirit_low/critical · morale_debuff · mana_drain · aura_active  
4. **pre_fight / pre_dungeon / auto_blocked / auto_unequip** ใช้ `relic.*`  
5. **critical** umbrella เมื่อ crush + morale crit  
6. **034.5** soft aura resist · `{band_th}` · โทนข้อความ  

---

### WO-035 Stat & Relationship Architecture

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-035 |
| **ชื่อ** | Stat & Relationship Architecture (3 Layer) |
| **สถานะ** | `done` lite (เฟส 0–3) |
| **Shipped in** | `1.82.0-alpha` |
| **Doc** | [`STAT_ARCHITECTURE.md`](STAT_ARCHITECTURE.md) |

#### เฟส

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **0** | Glossary · map · `anima` name · UI rules | done |
| **1** | Visible shell · soft P · ประเมินตัวเอง (V) | done |
| **2** | Core facets · anima · needs soft links | done |
| **3** | Luck→upgrade · world_relations · assist+luck | done lite |

#### สิ่งที่ ship

1. **`anima`** = Spirit core (ซ่อน) · ห้ามปน morale / `relic.spirit_*`  
2. **soft invest UI** · ข้อความลงแต้ม soft  
3. **self_assess** · hub **V**  
4. **HP soft condition** บน hub/field/combat  
5. **luck** soft bias upgrade + assist  
6. **`world_relations`** axis npc/divine/infernal (API)  

---

### WO-036 Stat Architecture Polish & Playtest

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-036 |
| **ชื่อ** | Stat Architecture Polish & Playtest Round |
| **สถานะ** | `done` |
| **Shipped in** | `1.83.0-alpha` |
| **Guide** | [`WO036_HUMAN_PLAYTEST.md`](WO036_HUMAN_PLAYTEST.md) |
| **Log** | `exports/WO036_PLAYTEST_LOG.md` |
| **Harness** | `scripts/wo036_stat_playtest.py` |
| **ขึ้นกับ** | WO-035 · WO-028 |

#### เฟส

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **1** | Playtest harness + feedback doc | done |
| **2** | Hotfix soft P/V · anima แยกขวัญ · luck/assist cap | done |
| **3** | ประเมินศัตรู (I) · UI assess · economy smoke | done |

#### สิ่งที่ ship

1. คู่มือ + harness + export log  
2. ประเมินตัวเอง แบ่ง ①②③ + ใบ้ขวัญ≠จิตวิญญาณ  
3. soft P ข้อความชี้ V  
4. luck upgrade/assist เพดานแคบลง  
5. ประเมินศัตรู soft ในไฟต์ **I** / **?**  
6. Anima บน status หลังกด V ครั้ง  

---

### WO-037 Anima Presence & Soft Moments

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-037 |
| **ชื่อ** | Anima Presence & Soft Moments |
| **สถานะ** | `done` |
| **Shipped in** | `1.84.0-alpha` |
| **ขึ้นกับ** | WO-035 · WO-036 · Soft Alert |
| **Harness** | `scripts/wo037_anima_playtest.py` |
| **Log** | `exports/WO037_ANIMA_PLAYTEST.md` |

#### เฟส

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **1** | Soft moments เรลิก/ห้อง/เรียน/คอมโบเวท | done |
| **2** | ขวัญ drain · ต้านจิต · soft fail ท่า | done |
| **3** | Harness + polish + docs | done |

#### สิ่งที่ ship

1. Soft Alert `anima.*` (ไม่ปน `relic.spirit_*`)  
2. `anima_presence_lines` · nudge เล็ก · `_anima_presence_felt`  
3. ผูก equip · chamber spar · library · learn_skill · magic combo  
4. ขวัญ drain ตาม anima · mental resist · skill waver (frail)  
5. Status โชว์จิตวิญญาณหลัง presence  

#### ห้าม (คงตาม scope)

- ลง P สำหรับ Anima · resource ใหม่ · relations เทพเต็ม  

---

### WO-038 World Relations Lite

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-038 |
| **ชื่อ** | World Relations Lite (Divine / Infernal / Echo) |
| **สถานะ** | `done` |
| **Shipped in** | `1.85.0-alpha` |
| **Harness** | `scripts/wo038_world_relations_playtest.py` |
| **ขึ้นกับ** | WO-035/037 · Soft Alert |

#### สิ่งที่ ship

1. `world_relations.py` · faction divine/infernal/ancient_echo  
2. Soft Alert `world.*`  
3. ผูก NPC outcome · echo · chamber · เรลิกธีม  
4. ขวัญ drain soft จาก faction  
5. hub บรรทัดโลก · V แสดง ④ ความสัมพันธ์โลก  
6. harness + unit tests  

---

### WO-039 Faction Mini-Moments

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-039 |
| **ชื่อ** | Faction Mini-Moments (Divine / Infernal / Echo) |
| **สถานะ** | `done` |
| **Shipped in** | `1.86.0-alpha` |
| **Harness** | `scripts/wo039_faction_moments_playtest.py` |
| **ขึ้นกับ** | WO-038 |

#### สิ่งที่ ship

1. 3 moments: วายุ · เงามาร · กระซิบป่า  
2. ทางเลือก ช่วย/ไม่ช่วย/หลบ → faction + Anima + ขวัญ  
3. sight `faction_moment` · เข้าหาจาก field  
4. Auto soft-resolve / เลี่ยง cold faction  
5. Soft Alert `world.moment_*`  

---

### WO-040 Anima × Relic Depth

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-040 |
| **ชื่อ** | Anima × Relic Depth |
| **สถานะ** | `done` |
| **Shipped in** | `1.87.0-alpha` |
| **Harness** | `scripts/wo040_relic_anima_playtest.py` · `exports/WO040_RELIC_ANIMA.md` |
| **ขึ้นกับ** | WO-037 · WO-038 · WO-039 · Divine Burden |

#### สิ่งที่ ship

1. Relic faction lean: storm/sky=divine · hell=infernal · void/ancient=echo  
2. Equip depth → Anima อุ่น/แผ่ว/สั่น + Soft Alert `anima.relic_*` + faction soft  
3. Morale mult ขณะใส่ (divine ช้า · infernal เร็ว) · burden tick + needs  
4. Chamber spar depth `anima.spar_*` · explore whisper `world.relic_*`  
5. Auto ถอดเมื่อ Anima แผ่ว + ขวัญกด  
6. Docs §0.9 STAT_ARCHITECTURE · unit `test_wo040_relic_anima.py`

#### ขอบเขตห้าม (ทำแล้วไม่เกิน)

- ไม่เพิ่ม resource · ไม่ upgrade tree · ไม่เควสใหญ่ · ไม่เปลี่ยน UI หลัก

---

### WO-041 Relic Soft Bonds

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-041 |
| **ชื่อ** | Relic Soft Bonds |
| **สถานะ** | `done` |
| **Shipped in** | `1.88.0-alpha` |
| **Harness** | `scripts/wo041_relic_bonds_playtest.py` · `exports/WO041_RELIC_BONDS.md` |
| **ขึ้นกับ** | WO-040 · WO-037 · WO-038 |

#### สิ่งที่ ship

1. 2+ lean เดียวกัน → Resonance (`anima.bond_divine/infernal/echo`) · Anima + ขวัญ mult  
2. lean ผสม → Soft Tension · ขวัญลดเร็ว · Anima แผ่ว  
3. Chamber spar ลึก bond · world explore bond gaze/haze/chorus  
4. world_relations เพิ่มตาม bond faction  
5. Auto ถอดเมื่อ Tension + ขวัญกด · เลือก minority lean ก่อน  
6. Docs §0.10 · unit `test_wo041_relic_bonds.py`

#### ขอบเขตห้าม

- ไม่ resource ใหม่ · ไม่ upgrade tree · ไม่เควสใหญ่ · ไม่ UI ใหม่

---

### WO-042 Area Mini-Moments + Relic Content

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-042 |
| **ชื่อ** | Area Mini-Moments Expansion + Relic Content |
| **สถานะ** | `done` |
| **Shipped in** | `1.89.0-alpha` |
| **Harness** | `scripts/wo042_moments_relics_playtest.py` · `exports/WO042_MOMENTS_RELICS.md` |
| **ขึ้นกับ** | WO-039 · WO-041 |

#### สิ่งที่ ship

1. Mini-Moments ใหม่: `infernal_cave_coal` · `echo_desert_mirage` · `divine_crystal_prayer`  
2. Soft Alert `world.moment_cave_*` / `desert_*` / `crystal_*`  
3. เรลิก: `relic_hell_brand_charm` (acc · infernal) · `relic_echo_shroud` (body · echo)  
4. Infernal Bond / Echo Bond ใช้งานได้จริง · Divine Bond คงเดิม  
5. ดรอปบอส + เควส soft (ไม่ร้าน)  
6. Docs §0.11 · unit `test_wo042_moments_relics.py`

#### ขอบเขตห้าม

- ไม่ resource ใหม่ · ไม่ upgrade tree · ไม่ storyline ยาว · ไม่ UI ใหม่

---

### WO-043 Bond Soft Cap + 3-piece Chorus

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-043 |
| **ชื่อ** | Bond Soft Cap + 3-piece Soft Chorus (lite) |
| **สถานะ** | `done` |
| **Shipped in** | `1.90.0-alpha` |
| **Harness** | `scripts/wo043_chorus_playtest.py` · `exports/WO043_CHORUS.md` |
| **ขึ้นกับ** | WO-041 · WO-042 |

#### สิ่งที่ ship

1. 2 ชิ้น = Resonance · **3+ = Soft Chorus** · 4+ = Chorus + Soft Cap  
2. Soft Alert `anima.chorus_*` · `anima.bond_soft_cap` · `world.chorus_*`  
3. Chamber spar / explore / world_relations ลึกขึ้นตาม Chorus  
4. Auto บางคณะเมื่อ Soft Cap + ขวัญกด  
5. ชิ้นที่ 3: laurel · ash greaves · echo sandals  
6. Docs §0.12 · unit `test_wo043_chorus.py`

#### ขอบเขตห้าม

- ไม่ resource ใหม่ · ไม่ upgrade tree · ไม่เควสใหญ่ · ไม่ UI ใหม่

---

### WO-044 Area Loop Flavor + Soft Foresight

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-044 |
| **ชื่อ** | Area Loop Flavor Polish + Soft Foresight (Moment Hint) |
| **สถานะ** | `done` |
| **Shipped in** | `1.91.0-alpha` |
| **Harness** | `scripts/wo044_area_foresight_playtest.py` · `exports/WO044_AREA_FORESIGHT.md` |
| **ขึ้นกับ** | WO-039 · WO-042 · soft_foresight |

#### สิ่งที่ ship

1. Moments ใหม่: `divine_mountain_gaze` · `divine_city_bell` · `echo_void_pull`  
2. ทุก 8 พื้นที่มี ≥1 Mini-Moment · AREA_FACTION_HINT ครบ  
3. Soft Foresight: `area_world_gaze_lines` · ใบ้ Mini-Moment · Soft Alert foresight  
4. Wire: travel (ซ้ำก็ใบ้) · explore tick · dungeon foresight panel  
5. Docs §0.13 · unit `test_wo044_area_foresight.py`

#### ขอบเขตห้าม

- ไม่ resource ใหม่ · ไม่ upgrade · ไม่เควสใหญ่ · ไม่ UI ใหม่

---

### WO-045 Playtest Polish รอบใหญ่

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-045 |
| **ชื่อ** | Playtest Polish รอบใหญ่ (Human + Harness) |
| **สถานะ** | `done` |
| **Shipped in** | `1.92.0-alpha` |
| **คู่มือ** | [`WO045_HUMAN_PLAYTEST.md`](WO045_HUMAN_PLAYTEST.md) |
| **Harness** | `scripts/wo045_playtest_polish.py` · `exports/WO045_PLAYTEST_LOG.md` |
| **ขึ้นกับ** | WO-035–044 |

#### สิ่งที่ ship

1. คู่มือมือ 90–120 นาที + แบบฟอร์ม Feel 1–5  
2. Harness รวม smoke Needs/Relic/Bond/Chorus/Moment/Foresight/Auto  
3. Hotfix: brief re-visit gaze · moment chance curve · equip multi less spam · throttle  
4. STAT_ARCHITECTURE §0.14 DNA lock lite  
5. unit `test_wo045_playtest_polish.py`

#### ขอบเขตห้าม

- ไม่ feature ใหญ่ · ไม่ resource ใหม่ · ไม่ rewrite architecture

---

### WO-046 Relic × Moment Soft Synergy Lite

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-046 |
| **ชื่อ** | Relic × Moment Soft Synergy Lite |
| **สถานะ** | `done` |
| **Shipped in** | `1.93.0-alpha` |
| **Harness** | `scripts/wo046_relic_moment_synergy_playtest.py` · `exports/WO046_RELIC_MOMENT_SYNERGY.md` |
| **ขึ้นกับ** | WO-040–045 · faction_moments · soft_foresight |

#### สิ่งที่ ship

1. Resonate / Area Tension จาก relic lean vs area lean  
2. Moment chance mult + bias faction · Anima scale ตอน resolve  
3. Foresight ใบ้ synergy · explore presence pulse · chamber spar deepen  
4. Auto ถอดเมื่อ area tension + ขวัญกด  
5. Soft Alert `world.synergy_*` / `anima.synergy_*`  
6. Docs §0.15 · unit `test_wo046_relic_moment_synergy.py`

#### ขอบเขตห้าม

- ไม่ resource ใหม่ · ไม่ upgrade · ไม่เควสใหญ่ · ไม่ UI ใหม่

---

### WO-047 Human Feedback Round + Feel Polish

| ฟิลด์ | ค่า |
|--------|-----|
| **ID** | WO-047 |
| **ชื่อ** | Human Feedback Round หลัง Synergy + Feel Polish |
| **สถานะ** | `done` |
| **Shipped in** | `1.94.0-alpha` |
| **คู่มือ** | [`WO047_HUMAN_PLAYTEST.md`](WO047_HUMAN_PLAYTEST.md) |
| **Harness** | `scripts/wo047_human_feedback_polish.py` · `exports/WO047_PLAYTEST_LOG.md` |
| **ขึ้นกับ** | WO-045 · WO-046 |

#### สิ่งที่ ship

1. คู่มือ H0–H10 โฟกัส synergy ตรง/ขัดพื้นที่  
2. Feel polish: foresight tone · presence pulse · tension morale · soft cap  
3. DNA lock note §0.16 · unit `test_wo047_feel_polish.py`  
4. แบบฟอร์ม `exports/WO047_HUMAN_FEEDBACK.md` (รอกรอกมือ)

#### ขอบเขตห้าม

- ไม่ feature ใหญ่ · ไม่ resource · ไม่ rewrite architecture

---

### WO-00N … (แม่แบบ)

```markdown
### WO-00N ชื่อสั้น
...
```

---

## 3. คำสั่งสั้นสำหรับ Grok CLI

```markdown
เอกสารกลาง: docs/WO_BACKLOG.md
**WO-001** Enhance game-start — backlog
**WO-002** World theme/custom — deferred/simplified @ 1.55.0-alpha
**WO-004** Core Needs Stabilization Phase 1 — done @ 1.56
**WO-005** Needs Visibility combat (P1.5) — done @ 1.57
```

---

## 4. Changelog เอกสารนี้

| วันที่ | เหตุการณ์ |
|--------|-----------|
| 2026-07-15 | สร้าง backlog · รับ **WO-001** |
| 2026-07-15 | implement **WO-002** @ 1.55.0-alpha |
| 2026-07-15 | **Defer WO-002:** simple world picker default · `WORLD_THEME_UX_ENABLED=False` · เก็บโค้ด |
| 2026-07-15 | รับ **WO-004** Needs Phase 1 · design `NEEDS_PHASE1_DESIGN.md` |
| 2026-07-15 | **WO-004 done** @ 1.56.0-alpha (`needs-core-stabilization`) |
| 2026-07-15 | **WO-005 done** @ 1.58.0-alpha — combat needs visibility (P1.5) |
| 2026-07-15 | **WO-006/007/008 done** @ 1.58.0-alpha |
| 2026-07-15 | **WO-010 done** @ 1.60.0-alpha — Auto Play บนหน้า Combat |
| 2026-07-15 | **WO-011 done** @ 1.61.0-alpha — Playtest summary / logger / Test Run |
| 2026-07-15 | **WO-012/013 done** @ 1.62.0-alpha — Soft death polish + Continuous combat log |
| 2026-07-15 | **WO-015/016 done** @ 1.63.0-alpha — combat tick parity · foresight · run history |
| 2026-07-15 | **WO-017 R2** @ 1.64.0-alpha — threshold tune · less eat_morale/rest spam · playtest log |
| 2026-07-15 | **WO-017 R3** @ 1.65.0-alpha — fatigue 67 · 1-action counters · Field30 rest 17→4 |
| 2026-07-15 | **WO-021 done** @ 1.66.0-alpha — economy parity · auto buy/sell · early prices · H/H sources |
| 2026-07-15 | **WO-022 done** @ 1.67.0-alpha — money_factor 0.9 · auto_buy default · economy playtest |
| 2026-07-15 | **WO-023.1 done** — `DIVINE_BURDEN_VISION.md` rule lock · เฟส 2–5 AC |
| 2026-07-15 | **WO-023 done** @ 1.68.0-alpha — Burden · Chamber · Aura · content 4 relics |
| 2026-07-15 | **WO-024 done** @ 1.69.0-alpha — echo aura UI · relic drops · foresight/hub |
| 2026-07-15 | **WO-025 done** @ 1.70.0-alpha — relic quests · auto avoid relic echo |
| 2026-07-15 | **WO-026 done** @ 1.71.0-alpha — playtest guide · burden soft · tutorial 9 · god log |
| 2026-07-15 | **WO-027 done** @ 1.72.0-alpha — mid relic quests · chamber spar/summary · economy dampen |
| 2026-07-15 | **WO-028/029 done** @ 1.73.0-alpha — human playtest pack · forest/marsh loops |
| 2026-07-15 | **WO-030 done** @ 1.74.0-alpha — human feedback · burden/chamber/UX polish |
| 2026-07-15 | **WO-031 done** @ 1.75.0-alpha — cave/desert area loops · boss chain depth |
| 2026-07-15 | **WO-032 done** @ 1.76.0-alpha — mountain/crystal/city/void loops · full map |
| 2026-07-15 | **WO-033 done** @ 1.77.0-alpha — Soft Alert Bus · burden catalog · throttle · pre-fight/auto |
| 2026-07-15 | **WO-033.4 done** @ 1.78.0-alpha — needs soft-warn เข้า Soft Alert Bus · record on combat enter |
| 2026-07-15 | **WO-034.0–1** @ 1.79.0-alpha — Relic Alert catalog `relic.*` · burden alias · spirit=morale lock |
| 2026-07-15 | **WO-034.2–4** @ 1.80.0-alpha — wire equip/unequip/tick/auto · critical umbrella |
| 2026-07-15 | **WO-034.5 done** @ 1.81.0-alpha — aura_resisted soft · band_th · tone polish |
| 2026-07-15 | **WO-035** @ 1.82.0-alpha — 3-layer stats · anima · soft P · assess · luck/relations |
| 2026-07-15 | **WO-036 done** @ 1.83.0-alpha — stat playtest · soft polish · enemy assess · luck cap |
| 2026-07-15 | **WO-037 done** @ 1.84.0-alpha — Anima presence soft moments · morale/combat · Soft Alert |
| 2026-07-15 | **WO-038 done** @ 1.85.0-alpha — World Relations Lite · divine/infernal/echo soft |
| 2026-07-15 | **WO-039 done** @ 1.86.0-alpha — Faction Mini-Moments · 3 soft encounters · Auto |
| 2026-07-16 | **WO-040 done** @ 1.87.0-alpha — Anima × Relic Depth · lean · spar · whisper · auto frail |
| 2026-07-16 | **WO-041 done** @ 1.88.0-alpha — Relic Soft Bonds · resonance · tension · spar/auto |
| 2026-07-16 | **WO-042 done** @ 1.89.0-alpha — Area Moments ถ้ำ/ทะเลทราย/ผลึก · hell charm + echo shroud |
| 2026-07-16 | **WO-043 done** @ 1.90.0-alpha — Soft Chorus 3+ · Soft Cap 4+ · third lean pieces |
| 2026-07-16 | **WO-044 done** @ 1.91.0-alpha — Area moments ครบแผนที่ · Soft Foresight moment hint |
| 2026-07-16 | **WO-045 done** @ 1.92.0-alpha — Playtest Polish · DNA lock lite · foresight/moment tone |
| 2026-07-16 | **WO-046 done** @ 1.93.0-alpha — Relic × Moment/Area Soft Synergy lite |
| 2026-07-16 | **WO-047 done** @ 1.94.0-alpha — Human Feedback + Feel Polish · DNA lock |
