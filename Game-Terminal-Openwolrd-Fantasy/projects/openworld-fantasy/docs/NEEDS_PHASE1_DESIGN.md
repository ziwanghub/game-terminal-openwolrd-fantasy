# Needs Phase 1 — Core Stabilization (Design)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | [WO-004](WO_BACKLOG.md#wo-004-core-needs-stabilization--phase-1) |
| **สถานะเอกสาร** | **Phase 1 implemented** @ 1.56.0-alpha |
| **เวอร์ชันฐาน** | ~1.55.0-alpha |
| **วัตถุประสงค์เฟส** | Auto กลัวหิว / ล้า / ขวัญพัง **สมมาตร** กับมือ |

**นอกสcope เฟส 1:** sickness, แยก thirst, proactive planner ลึก, collapse ครบ 3 แกน, chronicle/dashboard (เฟส 2–3)

**แผน 3 เฟสรวม:** ดูท้ายเอกสาร §9

---

## 1. ปัญหาปัจจุบัน (สั้น)

| ช่องว่าง | มือ | auto ตอนนี้ |
|----------|-----|-------------|
| Needs ระหว่างไฟต์ | win/loss + mults + skill fail + ATB ล้า | `auto_fight` เกือบไม่ใช้ |
| ขวัญ | fail/block สกิล | ไม่มี threshold / policy |
| ล้า | ATB ช้า | ไม่มี rest action ใน auto |
| หิว/ล้า care | R/E มือ | ดัน: กินตาม threshold เท่านั้น |
| log เหตุผล | soft notes บางส่วน | ใช้ของแล้วไม่บอก “ทำไม” ชัด |

---

## 2. หลักการออกแบบ

1. **กฎเดียว** — domain `needs.py` เป็น source of truth; auto **เรียก** ไม่คัดลอกสูตรใหม่  
2. **ขยายของเดิม** — `auto_prefs`, `use_items_by_thresholds`, `apply_needs_event`, `combat_needs_mults`, `skill_fail_chance`, `atb_fatigue_mult`  
3. **ไม่รื้อ combat_session** — ดึง helper ที่ใช้ซ้ำได้ ไปให้ auto ใช้  
4. **Soft / anti-spoiler** — log เหตุผลเป็นภาษาผู้เล่น ไม่โชว์ %  
5. **ทำทีละชิ้น** — ลำดับ implement §8  

---

## 3. โครงสร้างเป้าหมาย (เฟส 1)

```text
                    ┌─────────────────────────┐
                    │  domain/needs.py         │
                    │  apply_needs_event       │
                    │  combat_needs_mults      │
                    │  skill_fail / ATB ล้า    │
                    │  rest / food relief      │
                    │  needs_care_decision *NEW soft API
                    └───────────┬─────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
 combat_session          auto_fight              dungeon_auto /
 (มือ — คงพฤติกรรม)      (ใช้กฎ needs เดียว)      field auto shell
         │                      │                      │
         │                      │              auto_prefs + thresholds
         │                      │              + rest option
         │                      │              + care log lines
         ▼                      ▼                      ▼
              player["needs"]  ·  player["auto_prefs"]
              optional: player["_needs_care_log"] session
```

\* `needs_care_decision` = ฟังก์ชัน domain บาง ๆ คืน **action intent**  
`eat | rest | use_hp | use_mp | avoid_fight | continue` + soft reason  
ไม่ใช่ AI ใหญ่ — แค่รวม threshold/policy ไว้ที่เดียวให้ auto เรียก

---

## 4. ชิ้นงานออกแบบรายข้อ WO

### 4.1 auto_fight ใช้กฎเดียวกับ combat_session

| หัวข้อ | ออกแบบ |
|--------|--------|
| **ระหว่างไฟต์** | ทุก N เทิร์นฝั่งผู้เล่น (แนะนำทุกเทิร์นหรือทุก 2 เทิร์น): `apply_needs_event(player, "combat", silent=True)` — ใช้ event ที่มีในตารางแล้วแต่ caller หาย |
| **จบชนะ/แพ้** | เรียก `combat_win` / `combat_loss` เหมือน session (auto แพ้ถ้ายัง soft-revive อยู่: ยัง revive ได้ แต่ **ต้อง** apply combat_loss ก่อน revive เพื่อสมมาตร needs) |
| **ดาเมจออก** | คูณ `combat_needs_mults()["atk_mult"]` (มือมีแล้วใน `player_attack_damage` — ตรวจว่า auto ใช้ path เดียวกันหรือต้องส่งผ่าน) |
| **ดาเมจเข้า + หลบ** | ใช้ `incoming_mult` / `dodge_mult` กับ raw มอน (auto ตอนนี้แค่ครึ่งดาเมจเมื่อ HP ต่ำ) |
| **ขวัญ → สกิล** | ก่อนใช้สกิลจาก plan: `skill_blocked_by_morale` → ตกเป็นโจมตีปกติ; `skill_fail_chance` → miss/อ่อน soft |
| **ล้า → จังหวะ** | auto ไม่มี ATB จริง — **จำลอง**: โอกาส “ช้าหนึ่งจังหวะ” / มอนโจมตีก่อนในเทิร์น ตาม `atb_fatigue_mult` (map เบา: ถ้า mult < 0.9 มี chance มอนตีก่อนหรือผู้เล่นข้ามโจมตี) |
| **guard** | คง crude HP guard + soft จาก fatigue/morale (ขวัญต่ำ guard บ่อยขึ้นเล็กน้อย — optional เฟส 1) |

**ห้าม:** ย้าย auto ทั้งก้อนไป `combat_session` interactive ในเฟส 1 (ช้า/ซับซ้อนเกิน)

### 4.2 auto_prefs + Morale

ขยาย defaults (ชื่อฟิลด์ร่าง):

```text
auto_prefs:
  hp_pct, mp_pct, hunger, fatigue     # มีอยู่
  morale: 35                          # NEW — ทำ care เมื่อ morale ≤ ค่านี้
  skill_plan, item_mode               # มีอยู่
  low_morale_policy: "caution"        # NEW — see below
```

| `low_morale_policy` | พฤติกรรมเฟส 1 |
|---------------------|----------------|
| `ignore` | ไม่ใช้ (debug) |
| `caution` (default) | เลี่ยงไฟต์เสริม / ไม่ท้าบอสออโต้ / ชอบ rest หรือ eat ถ้าช่วย morale |
| `retreat` | หยุด auto run เมื่อ morale ≤ threshold (soft stop) |

`item_mode` thrift/safe ขยับ morale threshold คล้าย hunger (safe → เกณฑ์สูงขึ้น = ระวังเร็ว)

### 4.3 Rest ใน Auto Agent

| จุด | พฤติกรรม |
|-----|----------|
| **เงื่อนไข rest** | `fatigue >= auto_prefs.fatigue` **หรือ** (morale ≤ morale thr และ policy ≠ ignore) และไม่ได้อยู่กลางไฟต์ |
| **ผล rest** | เรียก `apply_needs_event(..., "rest")` เดียวกับมือ — **ไม่** ประดิษฐ์ delta ใหม่ |
| **ที่รัน** | `dungeon_auto` tick (ก่อน explore/combat); field auto ถ้ามี shell รอบนอก |
| **ราคา soft** | rest ใช้ 1 “action slot” ของ tick (ไม่ explore ใน tick นั้น) — กัน rest spam ไร้ต้นทุนเวลา |
| **อาหาร vs rest** | ถ้าหิวถึงเกณฑ์ → กินก่อน; ถ้าล้าถึงเกณฑ์และหิวยังไม่วิกฤต → rest; ถ้าทั้งคู่ → กินก่อนแล้ว rest ถ้ายังล้า (ลำดับ care) |

ลำดับ care ต่อ tick (ร่าง):

```text
1. needs_care_decision()
2. if eat → use_items food
3. if rest → apply rest event + log
4. if use_hp/mp → potions (threshold เดิม)
5. if avoid_fight → skip combat spawn this tick / stop boss auto
6. else continue explore/fight
```

### 4.4 Logging / Visibility

| ชนิด | ตัวอย่าง soft line |
|------|---------------------|
| กิน | `ออโต้: กินเพราะท้องขึ้นเกณฑ์ (หิว)` |
| พัก | `ออโต้: พักเพราะล้า — ร่างยังไม่พร้อม` |
| เลี่ยงไฟต์ | `ออโต้: ขวัญไม่นิ่ง — เลี่ยงเงาเพิ่ม` |
| สกิล fail | `ออโต้: มือสั่น — ท่าไม่เต็ม` (ขวัญ) |
| วิกฤต | `ออโต้: ท้อง/ล้า/ขวัญ วิกฤต` |
| หยุดรัน | `ออโต้หยุด: ขวัญต่ำเกินนโยบาย` / อาหารหมด (ของเดิม) |

เก็บ optional: `player.setdefault("auto_care_notes", [])` จำกัดความยาว (เช่น 20 บรรทัดล่าสุด) สำหรับสรุปรอบ — ไม่บังคับ UI ใหญ่

---

## 5. ไฟล์ที่คาดว่าแตะ (ตอน implement)

| ไฟล์ | บทบาท |
|------|--------|
| `game/domain/needs.py` | care decision helper · crit log helpers (บาง) |
| `game/runtime/auto_farm.py` | `auto_fight` ผูก needs/combat mults/fail |
| `game/runtime/dungeon_auto.py` | prefs morale · rest · order care · logs |
| `game/runtime/auto_farm.py` (field) | เรียก care ก่อน fight ถ้าง่าย |
| `tests/unit/test_needs_*.py` / ใหม่ | สมมาตร win-loss · threshold morale · rest |

ไม่แตะ: multiplayer, permadeath, WO-002 theme UX

---

## 6. Acceptance Criteria (เฟส 1)

- [ ] `auto_fight` ใช้ `combat_needs_mults` / morale skill gate-fail / fatigue pacing soft  
- [ ] ชนะ/แพ้ออโต้เรียก `combat_win` / `combat_loss` needs  
- [ ] ระหว่างไฟต์ออโต้มี `combat` needs tick (หรือเทียบเท่าที่สมเหตุสมผล)  
- [ ] `auto_prefs` มี `morale` (+ policy อย่างน้อย caution/retreat)  
- [ ] dungeon_auto (และ field auto ถ้ารองรับ) **rest** ได้เมื่อล้าสูง  
- [ ] log soft อธิบาย กิน / พัก / เลี่ยง / หยุด  
- [ ] มือ (`combat_session`) พฤติกรรม needs เดิมไม่พัง  
- [ ] เทสต์ unit ครอบคลุม path หลัก  
- [ ] ไม่เพิ่มระบบโรค/กระหายแยก  

---

## 7. ความเสี่ยงออกแบบ

| ความเสี่ยง | แนวกัน |
|------------|--------|
| auto ช้า / ตายบ่อยหลังผูก needs | soft fail + rest; อย่าเพิ่ง hard death |
| rest spam | 1 rest ต่อ tick · fatigue ต้องถึงเกณฑ์ |
| combat event ทุกเทิร์นโหดเกิน | เริ่มทุก 2 เทิร์นหรือ delta เดิมของตาราง `combat` ที่มีอยู่ |
| สูตรซ้ำใน auto_fight | บังคับเรียก domain เท่านั้น |

---

## 8. ลำดับ implement (ทีละส่วน — หลังอนุมัติ design)

| ขั้น | งาน | ตรวจ |
|------|-----|------|
| **P1.1** | auto_fight needs parity | **done** |
| **P1.2** | morale/fatigue in fight | **done** (in P1.1) |
| **P1.3** | auto_prefs morale + **band policy** (high/mid/low/crit) + eat_morale + rest_long | **done** (enhanced) |
| **P1.4** | dungeon rest + care logs | **done** |
| **P1.4b** | **Auto Inventory Management** (`runtime/inventory_auto.py`) | **done** |
| **P1.5** | field auto care | **done** |
| **P1.5b / WO-005** | Needs Visibility in combat UI + soft feedback | **done** @ 1.57 |

---

## 9. แผน Needs 3 เฟส (อ้างอิง — นอก WO-004)

| เฟส | ชื่อ | เป้าหมาย |
|-----|------|----------|
| **1** | Core Needs Stabilization | สมมาตรมือ–ออโต้ · morale/rest/log (เอกสารนี้ + WO-004) |
| **2** | Needs-Driven Decision | proactive policy · foresight ก่อนดัน · near-collapse ล้า/ขวัญ |
| **3** | Survival Foundation | collapse ครบ · chronicle · party link · God dashboard เตรียม |

---

## 10. สถานะถัดไป

- Design นี้ = พร้อมให้ review  
- **ยังไม่เขียนโค้ด** จนกว่าจะสั่ง `Implement WO-004`  
- หลัง ship: อัป WO-004 → done + version ใน `WO_BACKLOG.md` / `PHASES.md`
