# แผนพัฒนา / คิวงาน

**เกมปัจจุบัน:** `1.54.0-alpha` (`party-relationship-assist`) — ดู `game/config.py`  
**แผนหลัก (Wave A–F):** [`ROADMAP.md`](ROADMAP.md) ← อ่านภาพรวมก่อน  
**Work Order Backlog (เอกสารกลาง WO):** [`WO_BACKLOG.md`](WO_BACKLOG.md) ← งานที่แตกเป็น WO แล้ว (เริ่มสะสม 2026-07-15)  
**Needs 3 เฟส / Phase 1 design:** [`NEEDS_PHASE1_DESIGN.md`](NEEDS_PHASE1_DESIGN.md) · **WO-004** (ready — รอ implement)

### ทิศล็อก (product) — 2026-07-14

> **เล่นคนเดียวให้ระบบนิ่งก่อน · online ไว้ท้ายสุด**  
> - โฟกัส: playtest · hotfix · บาลานซ์ · เนื้อหา solo · polish ระบบที่มีแล้ว  
> - **ระงับ / อย่าเริ่ม:** W4 online · H5 live room จริง · realtime MP · netcode ใหม่  
> - ของ async ที่มีอยู่แล้ว (echo · อันดับ · ขอแรง · host ไฟล์) = ใช้ได้ แต่**ไม่ขยายเป็น online** จนกว่า solo นิ่ง  

### Sprint ล่าสุด (ตามแผนพัฒนา)

| งาน | สถานะ |
|-----|--------|
| Soft feedback เกียร์/อัป/Unit affinity | **done** (`soft_feel.py`) |
| ข้อเสนออาชีพ รับ/ปฏิเสธ + nudge เลเวลอัป/HUD | **done** |
| อาชีพลับ Unit 33 + affinity แต้ม | **done** |
| IC1 pack B (เกียร์/mat) + MC thin areas | **done** |
| **IC2** การ์ดผูกมอนเฉพาะ | **done** |
| **MC2** มอนเต็มแพ็ก + pool ≥6 | **done** |
| **IC3** คราฟสายมอน | **done** |
| **MC3** บทบาท mid plant/undead/bird/insect | **done** |
| **IC4** เกียร์บอส + การ์ดบอส + เซ็ต | **done** |
| **MC4** elite ทุกพื้นที่ | **done** |
| **IC5** หีบ/ร้าน/เศรษฐกิจ | **done** |
| **MC5** หนา late | **done** |
| **IC6** polish หีบ/ร้าน/sink/คราฟเบา | **done** |
| **MC6** pool elite cap · rebalance น้ำหนัก · health tests | **done** |
| **คอนเทนต์ IC1–IC6 / MC1–MC6** | **closed** |
| **Unit HSR** joke↔โหด / broken↔แผ่ว + soft path | **done** (1.35) |
| **Skill tree** T3 +1/สาย | **done** (1.35) |
| **HSR balance** joke cap · broken gutter · soft หลังลงแต้ม | **done** (1.36) |
| **Soft path มาตรฐาน** เกียร์/อัป/เรียนสกิล · smoke loop | **done** (1.37) |
| **Onboarding** บทเรียน 8 หน้า + ใบ้ C/K/P/อัป/Unit | **done** (1.38) |
| **MI1–MI2** มอนฉลาด: เลือกท่าตามบริบท + หนี soft (elite) | **done** (1.39) |
| **MI3** คุย/เจรจา soft (เข้าหา · elite) | **done** (1.40) |
| **Solo polish MI** ใบ้ · situation · ไฟต์ 7 เจรจา · ปาร์ตี้ finish | **done** (1.41) |
| **W1/W0 polish** echo freshness · ร่องรอยตัวเอง · เงาสู้ MI · area mood | **done** (1.42) |
| **SK-R0–R2** (+R3 lite) slot · rank scale · learn roll · buff gate · counter/reflect | **done** (1.43) |
| **SK-R4** แพ็ก debuff/buff 5 สาย + status slow/weak | **done** (1.44) |
| **SK-R5 lite** essence กระซิบท่า (nudge rank) | **done** (1.44) |
| **CM1–CM2** สมาธิ→ขั้นคอมโบ · ฉลาด/เวท→ภาษี/ลดมานาโซ่ | **done** (1.45) |
| **CM3** ฉลาดโชว์แบนด์ · เลิกลง P ตรง + migrate | **done** (1.46) |
| **CM4 lite** mind growth ตอนเรียนสกิล | **done** (1.46) |
| **CM5** เพดานสมาธิตามเลเวล · soft msg · ห้องสมุด/fusion mind | **done** (1.47) |
| **Post-CM polish** smoke · UI mind · soft MP fail | **done** (1.48) |
| ถัดไป | playtest มือยาว · hotfix จาก feedback · online รอ |

| Vision / สาย | เอกสาร | สถานะย่อ |
|--------------|--------|----------|
| แผนหลัก Wave | [`ROADMAP.md`](ROADMAP.md) | A playtest → E echo → F online |
| **อัปเดตไอเทมทั้งก้อน (แบ่งเฟส)** | [`ITEM_CONTENT_PLAN.md`](ITEM_CONTENT_PLAN.md) | **IC0–IC6 วางแผนแล้ว** · อัปครบแต่ค่อยเป็นค่อยไป |
| **เพิ่มมอนสเตอร์ (แบ่งเฟส)** | [`MONSTER_CONTENT_PLAN.md`](MONSTER_CONTENT_PLAN.md) | **MC0–MC6 วางแผนแล้ว** · เติมครบแต่ไม่ dump RO ทั้งก้อน |
| หีบรางวัล L0–L5 | [`CHEST_LOOT_VISION.md`](CHEST_LOOT_VISION.md) | **L0–L5 done** (L5 คลังหีบ UX) |
| ดรอปมอน (runtime) | [`MONSTER_DROPS.md`](MONSTER_DROPS.md) | **D1–D2 + world + hotfix 1.27** |
| คราฟ K0–K4 | [`CRAFT_SYSTEM.md`](CRAFT_SYSTEM.md) | **K0–K4 done** · ขยายตาม IC3 |
| โลก-เซิร์ฟ W0–W4 | [`WORLD_SERVER_VISION.md`](WORLD_SERVER_VISION.md) | **W0–W3 lite done** · W4 รอ |
| UX-Tama T0–T3 | [`UX_TAMA_VISION.md`](UX_TAMA_VISION.md) | **T0–T3 done** |
| Needs N1–N5 | [`NEEDS_COMBAT_FOOD_VISION.md`](NEEDS_COMBAT_FOOD_VISION.md) | **N1–N5 done** |
| โจมตี/ป้องกัน/ธาตุ DD0–DD5 | [`DAMAGE_DEFENSE_VISION.md`](DAMAGE_DEFENSE_VISION.md) | **DD0–DD5 lite done** |
| โหลดเอาต์หลายช่อง · grip · soft diversity EL0–EL5 | [`EQUIP_LOADOUT_VISION.md`](EQUIP_LOADOUT_VISION.md) | **EL0–EL5 + EQ-W/G/A done** |
| ขอแรง H0–H5 | [`HELP_SITUATION_VISION.md`](HELP_SITUATION_VISION.md) | **H0–H5 lite done** (H5 = presence soft) |

**แดชบอร์ดประเมินระบบ:** `python3 -m game.admin.dashboard`  
คะแนน/แผนใน `data/meta/system_dashboard.yaml` · แสดง text · export `exports/dashboard_latest.{txt,md}` · เมนูเกม **8 → 8**

---

## สถานะเฟส

| เฟส | สถานะ |
|-----|--------|
| Mode Shell · multi-ATB · multi-target · AoE balance | **1.13.5–1.13.10** (เสร็จหลัก) |
| แดชบอร์ดระบบเกม (ประเมิน + แผนเฟส · text) | **1.13.11** |
| Help Situation **H0–H4** | **1.13.12–1.13.14** |
| **T0** needs tick · **W0** rank soft | **1.13.15** |
| **N1–N4** needs combat/ATB/อาหาร | **1.13.16** |
| **L0–L2** หีบ data/เปิด/ดรอป | **1.13.18** |
| **L3–L4** เควส/กระดานหีบ · unit unique | **1.14.0** |
| **T1–T2** load delta · Tama panel | **1.15.0** |
| playtest (หิว/ล้า/อาหารร้าน/หีบ/tama) | คิวสั้น |
| **DD0–DD5** โจมตี 4 แบบ · กัน · ธาตุ · ต้านสถานะ | **DD0–DD5 done** (DD5 lite gear resist) |
| **EL0–EL5** ช่องเกียร์ · 1H/2H/โล่/dual · เกราะ 4 ส่วน · soft diversity | **EL0–EL5 done** |
| **N5** unit soft titles | **done** (หิว/ขวัญ) |
| **W0–W2** rank · echo · challenge | **done lite** |
| **T3** live Tama · **H5** presence soft | **done lite** |
| **W3** world host file + locks | **done lite** |
| **W4** online lite · true H5 room | **ระงับ** — solo นิ่งก่อน · online ท้ายสุด |
| V Later (LLM / Web / realtime MP) | **ระงับ** — ท้ายสุด |
| **Solo focus** playtest · hotfix · เนื้อหา · polish | **คิวหลักตอนนี้** |
| **IC0–IC6** อัปเดตไอเทม/การ์ดทั้งก้อน (แบ่งเฟส) | **แผนล็อก** — [`ITEM_CONTENT_PLAN.md`](ITEM_CONTENT_PLAN.md) · **ยังไม่เททั้งก้อน** |
| **MC0–MC6** เพิ่มมอนสเตอร์ (แบ่งเฟส) | **แผนล็อก** — [`MONSTER_CONTENT_PLAN.md`](MONSTER_CONTENT_PLAN.md) · **ไม่ dump RO ทั้งก้อน** |

---

## แผนเฟสอัปเดตไอเทม (IC) — สรุปในคิว

> **เป้าหมายสุดท้าย:** อัปไอเทม/การ์ด/ดรอป/คราฟ/ร้าน/หีบ **ให้ครบ**  
> **วิธีทำ:** แบ่งเฟส **IC0→IC6** อัปทีละชุด · เทส + playtest ได้ทุกระยะ · ห้าม dump ทั้งคลังทีเดียว  
> **รายละเอียดเต็ม:** [`ITEM_CONTENT_PLAN.md`](ITEM_CONTENT_PLAN.md)

| เฟส | ชื่อ | งานหลัก | สถานะ |
|-----|------|---------|--------|
| **IC0** | กฎ + map ชนิด | rename · ช่อง EL · กฎการ์ด soft | โครงพร้อม (doc) |
| **IC1** | เกียร์ pack A | หัว/ขา/เท้า/อาวุธชนิด · ร้าน | **บางส่วน 1.28** (pack เขา–ทะเลทราย) |
| **IC2** | การ์ด pack A | การ์ดผูกมอน ~15–25 · compatible EL | **เริ่ม 1.28** (3 ใบใหม่) |
| **IC3** | Mat + คราฟ | สายล่า→คราฟ ต่อพื้นที่ | รอคิว (มีฐานบาง) |
| **IC4** | Mid–late | เกียร์/การ์ด/บอส ลึก | รอคิว |
| **IC5** | เศรษฐกิจปิด | หีบ pool · ร้าน · เซ็ต | รอคิว |
| **IC6** | ปิดงานทั้งก้อน | บาลานซ์ + doc + playtest ยาว | รอคิว |

**ลำดับแนะนำกับ solo:** playtest ดรอป 1.27 → **IC1** → **IC2** → **IC3** → (playtest) → **IC4–IC5** → **IC6**  
**อย่ากระโดด IC6 / bulk RO dump** ก่อน IC1–IC2 นิ่ง

---

## แผนเฟสเพิ่มมอนสเตอร์ (MC) — สรุปในคิว

> **เป้าหมายสุดท้าย:** เติมมอนให้ครบสายเนื้อหา (pool หนา · บทบาทครบ · บอส/elite · ดรอป+การ์ด)  
> **วิธีทำ:** แบ่งเฟส **MC0→MC6** เพิ่มทีละชุด · **มอนใหม่ต้องมี drops + pool** · ห้าม dump mob_db / ชื่อ RO ทั้งก้อน  
> **รายละเอียดเต็ม:** [`MONSTER_CONTENT_PLAN.md`](MONSTER_CONTENT_PLAN.md)

| เฟส | ชื่อ | งานหลัก | สถานะ |
|-----|------|---------|--------|
| **MC0** | กฎ + แผนที่บทบาท | บทบาท RO-like → เรา · กฎแพ็กมอน | โครง doc |
| **MC1** | เติมพื้นที่บาง | เขา·ทะเลทราย pool 3→5+ | **done 1.28** (pool 6–7 + elite) |
| **MC2** | บทบาทที่ขาด | plant/skeleton/insect/นก ฯลฯ ชุดละ 6–10 | รอคิว |
| **MC3** | Elite / profiles | ไฟต์หลาก · status soft | รอคิว |
| **MC4** | Mid–late + mini-boss | late เฉพาะ · mini 2–4 | รอคิว |
| **MC5** | ผูก IC | card_id เฉพาะ · mat/คราฟ | รอคิว (คู่ IC2–IC3) |
| **MC6** | ปิดงานมอน | บาลานซ์ pool/HP · playtest ยาว | รอคิว |

**ลำดับแนะนำ:** playtest → **MC1 ∥ IC1** → **MC2 ∥ IC2** → MC3 → MC4 → **MC5 กับ IC** → MC6  
**ฐานตอนนี้:** มอน 41 · บอส 8 · drops ครบ — เติมทีละเฟสไม่เริ่มจากศูนย์

### ปิดล่าสุด (1.28.0)

- **MC1:** เขา/ทะเลทราย pool หนา (นกผา ตุ่นหิน โจรผา งูทราย วิญญาณฝุ่น หมาจิ้งจอก เงาเนิน) + elite soft ◆
- **IC1:** เกียร์หัว/ขา/เท้า/หอก/ดาบโค้ง/โล่กลาง · mat ใหม่ · คราฟ 4 สูตร · ร้าน armory
- **IC2 เริ่ม:** การ์ดผูกมอน 3 ใบ (นกผา งูทราย ฝุ่น)
- **S1:** elite scale + soft class บนดาเมจออก

### ปิดก่อน (1.27.0)

- Hotfix drops runtime บน pick_monster/spawn_boss

### ปิดก่อน (1.26.0)

- ดรอปต่อมอน **ครบ 41 ตัว** · mat ทั่วแผนที่ · บอส table

### ปิดก่อน (1.25.0)

- D1–D2 ป่า/ถ้ำ · G1 เกียร์/อาวุธ · mat แรก · card_id early

### ปิดก่อน (1.24.0)

- ร้านไม่ขายการ์ด · การ์ดดรอปไฟต์ · เก็บของ A / เลข,comma / 0

### ปิดก่อน (1.23.0)

- **K4:** อาหาร/ยา camp · เควส cook

### ปิดก่อน (1.22.0)

- **K3** station↔area · **L5** คลังหีบ UX

### ปิดก่อน (1.21.0)

- **W3 lite:** `file_lock` · `world_meta.json` · player index soft · host heartbeat
- **Host process:** `python -m game.host <world>` · `python -m game.host status`
- **Client:** เมนู 6 โลก-host · `client_pointer.json` · ตลาด/rank/echo เขียนใต้ lock
- ยัง**ไม่ใช่** HTTP MMO — โหมดไฟล์ร่วมเครื่อง

### ปิดก่อนหน้า (1.20.0)

- **T3:** แอนิเมชันเข้า PERSONAL · live drip บนจอ (cap ต่อรอบ) · ui_prefs `live_tama` / `tama_enter_anim`
- **H5 lite:** กระดานขอแรงแสดง 〔ร่องรอยสด/เพิ่งผ่าน/เงาเก่า〕 · ช่วยตอนสด +rep soft
- **ไม่ใช่** realtime multiplayer — async presence จาก saved_at

### ปิดก่อนหน้า (1.19.0)

- **W1:** `echoes/{id}.json` snapshot ตอนเซฟ · sanitize · สู้/คุยไม่แก้เซฟเจ้าของ · soft 「เงา·」
- **W2 lite:** สำรวจ **A** อันดับ/ท้า · จ่ายค่าหัว · สู้เงาอันดับ · อัปบอร์ด soft
- `build_echo_snapshot` / `write_echo_snapshot` / `try_rank_challenge`

### ปิดก่อนหน้า (1.18.0)

- **EQ-W:** weight_class light/medium/heavy soft · แผงเกียร์「ตัวเบา/ก้าวหนัก」
- **EQ-G:** stance_meters ซ่อน · ชนะไฟต์ฝึกท่า · ยังไม่ชิน = mult แผ่ว
- **EQ-A:** พื้นที่ `climate` × วัสดุเกียร์ · soft 「สนิมในใจ」「โลหะร้อนแผด」
- **EQ-N:** ชุดหนัก + หิว/ล้า → ATB/ดาเมจรับแย่ชัด
- **N5:** 「ร่างจำความอดอยาก」「ใจไม่แตก」soft flags
- โมดูล `game/domain/loadout_context.py`

### ปิดก่อนหน้า (1.17.1)

- **DD4:** ต้านสถานะ soft · familiarity ซ่อน · AoE ลดโอกาสติดสถานะ · flavor 「ร่างกายชินกับเปลว」
- **DD5 lite:** `gear_status_resist` จากโล่/หมวก/bias · ลงทุน def/intel soft
- **EL5:** เศษเซ็ต (partial) ข้ามหลายช่อง · โบนัสแผ่ว + soft note · เซ็ตเต็มยังครบ
- พัก (rest) ลด familiarity

### ปิดก่อนหน้า (1.17.0)

- **DD2:** เมนูกัน soft 3 กลุ่ม (กันกาย / กันเวท / กันธาตุ) · `guard_class` บนสกิล · class match soft
- **DD3:** ขยาย `matchups.yaml` (ไฟ/น้ำ/แสง-มืด/สายฟ้า/น้ำแข็ง/ดิน-ลม)
- **EL4:** เลือกมือหลัก/รองตอน dual · ยืนยันถอด off ก่อนใส่ 2H · ป้าย grip ในเมนูสวม
- โมดูล `game/domain/guard_groups.py`

### ปิดก่อนหน้า (1.16.1)

- **DD0:** `data/elements/damage_classes.yaml` · `game/domain/damage_class.py` · แมป skill `damage_class`
- **DD1:** `power_mdef` · class mitigation ขาเข้า (physical→def / arcane→mdef / light·dark blend) · soft flavor
- **EL3:** loadout soft bias (โล่/dual/2H/robe/parts) → `gear_*_bias` → `power_def`/`power_mdef`/`power_spd`
- outbound: เวทใช้ power_mag · กายใช้ power_atk (ซ่อน)

### ปิดก่อนหน้า (1.16.0)

- **EL0:** ช่อง `main_hand/off_hand/head/body/legs/feet/acc_1` · migrate เซฟ `weapon→main_hand` `armor→body` `accessory→acc_1` · `SAVE_VERSION=4`
- **EL1:** grip `one_hand/two_hand/shield/focus` · dual auto off · two_hand ล็อก/ถอด off · โล่ off · off-hand ATK ×0.55
- **EL2 content ขั้นต่ำ:** โล่ · ดาบสองมือ · หมวก/ขา/เท้า · ร้าน city_armory สต็อก
- UI เกียร์หลายช่อง · แผงกระเป๋า · soft notes โหลดเอาต์

### ปิดก่อนหน้า (1.15.0)

- **T1:** `saved_at` / unix · `apply_load_delta` ตอนโหลด (cap 48 ชม. · soft ไม่ฆ่า)  
- **T2:** ASCII Tama + แถบ needs · PERSONAL **R พัก / E กิน**  

### ปิดก่อนหน้า (1.14.1)

- **คราฟ K1–K2:** `data/craft/rules.yaml` · success roll · soft/hard fail + คืน mat/เงินบางส่วน · โบนัสวัตถุดิบเกรดเกิน min · UI ป้ายโอกาส (ไม่โชว์ %)  

### ปิดก่อนหน้า (1.14.0)

- **L3:** `reward_chest` บนเควส/กระดาน · `set_flags` ซ่อน · soft chance กระดานแรงก์สูง  
- **L4:** `unit_uniques.yaml` 3 ชิ้น · scope save/world · `unique_claims.json` · SSS→unit หาง  

### ปิดก่อนหน้า (1.13.18)

- **L0–L2 หีบ:** `data/chests/` ranks/pools/sources · `chest_loot.py` · เปิดจากกระเป๋าหมวด 4 · ดรอปบอส (noise+anti_farm) · unit unique 1 ชิ้น/เซฟ (echo_shard แทน)  

### ปิดก่อนหน้า (1.13.17)

- ร้าน **B → เลือกหมวด** แล้วค่อยซื้อ · ขายแยกหมวด · กระเป๋าเน้นเลือกหมวดก่อน (อาหาร/ยา/ฯลฯ)  

### ปิดก่อนหน้า (1.13.16)

- **N1–N4:** แถบ −/−− · soft death หิว · combat/ATB · อาหาร tier แยกยา  

### ปิดก่อนหน้า (1.13.15)

- **T0** needs tick · **W0** rank soft + rank_board.json  

### ปิดก่อนหน้า (1.13.14)

- **H4:** policy เพื่อน · ชื่อเสียงผู้ช่วย · world_signals · เควสยื่นมือ  

### ปิดก่อนหน้า (1.13.13)

- **H1–H3:** กระดาน **G** · escrow · assist · inbox/chronicle  

### ปิดก่อนหน้า (1.13.12)

- **H0:** `situation` + consent ในดัน (เมนู 6) · บันทึกพักรอแรง  

### ปิดก่อนหน้า (1.13.11)

- แดชบอร์ดประเมินระบบ: YAML scores · เมตริก registry · roadmap · export text (txt/md)  

### ปิดก่อนหน้า (1.13.10)

- บาลานซ์ AoE/กลุ่ม · splash diminishing · soft splash XP · spawn กลุ่มตามเลเวล  

---

## คิวใกล้ (ตาม ROADMAP Wave A → B)

| ลำดับ | รายการ | Wave |
|------:|--------|------|
| 1 | **Playtest มือ** หิว/อาหาร/ร้านหมวด · ขอแรง 2 เซฟ · ไฟต์กลุ่ม | A |
| 2 | Hotfix จาก playtest | A |
| 3 | **L0** data หีบ (ranks/pools) | B |
| 4 | **L1** เปิดหีบ + ให้ของ | B |
| 5 | **L2** ดรอปหีบจากบอส (มอนธรรมดาเกือบไม่ตก) | B |

**ถัดไปหลัง B:** L3–L4 · T1 · W1 (ดู `ROADMAP.md`)

---

## เฟส UX-Tama (วิสัยทัศน์ — ยังไม่ implement)

รายละเอียดเต็ม: **`docs/UX_TAMA_VISION.md`**

| เฟส | ชื่อ | สรุป | สถานะ |
|-----|------|------|--------|
| **T0** | Needs + tick | ท้อง/ล้า/ขวัญ · rest/explore/travel/combat/eat | **1.13.15** |
| **T1** | Load delta + แถบ | เวลาตอนโหลดเซฟ · แถบ soft ใน PERSONAL + ย่อสนาม | **รอ** |
| **T2** | Tama panel เต็ม | ASCII กลางจอ · เมนูกิน/พัก · mood soft | **รอ** |
| **T3** | Live optional | refresh/animation เบาตอนเปิด panel | **รอ** |

### หลักการล็อก (ย่อ)

1. RPG โลกเปิดเป็นหลัก — Tama อยู่จอสถานะ/เพื่อน ไม่กลืนทั้งเกม  
2. Soft bars เท่านั้น (ไม่สปอยล์สูตร)  
3. เวลา = **tick จาก action** + **delta ตอนโหลดเซฟ** (ไม่บังคับ process ค้าง 24 ชม.)  
4. Realtime ค้างจอ = optional ทีหลัง  
5. `needs = f(สถานการณ์เกม, เวลาที่ผ่าน)`  

### เงื่อนไขเริ่ม T0 (โดยประมาณ)

- PERSONAL hub ใช้งานได้ (มีแล้ว)  
- ตกลง needs ขั้นต่ำ (ท้อง / ล้า / จิต)  
- ไม่ชนคิว playtest ร้อน — หรือทำขนานได้  

---

## เฟส Needs → Combat / อาหาร (วิสัยทัศน์ — ยังไม่ implement)

รายละเอียดเต็ม: **`docs/NEEDS_COMBAT_FOOD_VISION.md`**

| เฟส | ชื่อ | สรุป | สถานะ |
|-----|------|------|--------|
| **N1** | UI ภาวะ − / crit | เครื่องหมาย − · soft death หิว | **1.13.16** |
| **N2** | Combat + ATB | หิว→ATK/DEF/dodge · ล้า→ATB · ขวัญ→สกิล | **1.13.16** |
| **N3** | ต้านทานสเตตัส | DEF/SPD/INT/ATK ชะลอโทษ needs | **1.13.16** |
| **N4** | อาหารเต็มระบบ | tier · ร้าน · แยกยา · บัฟ | **1.13.16** |
| **N5** | Unit soft | ปลดพลังโดยไม่รู้วิธีชัด | **รอ** |

**ลำดับแนะนำ:** N1 → (N4 อาหารร้าน ขนานได้) → N2 → N3 → N5  

---

## เฟสหีบรางวัล

รายละเอียดเต็ม: **`docs/CHEST_LOOT_VISION.md`**

| เฟส | ชื่อ | สรุป | สถานะ |
|-----|------|------|--------|
| **L0** | Data skeleton | ranks · pools · unit_uniques | **1.13.18** |
| **L1** | เปิดหีบ + ให้ของ | open_chest · soft text · หมวดหีบ | **1.13.18** |
| **L2** | ดรอปบอส/มอน | บอสโน้ม · มอนธรรมดาเกือบไม่ตก · noise | **1.13.18** |
| **L3** | เควสรางวัลหีบ | reward_chest · flags ซ่อน · กระดาน | **1.14.0** |
| **L4** | Unit unique | save/world · 3 ชิ้น · claims | **1.14.0** |
| **L5** | คลังหีบในกระเป๋า | สรุปแรงก์ · เรียงสูงก่อน · เปิดทั้งหมด A | **1.22.0** |

**หลัก:** แรงก์หีบ ≠ การันตีของ · ดรอปไร้รูปแบบตายตัว · unit ชิ้นเดียว  

---

## เฟส World Server (วิสัยทัศน์ — ยังไม่ implement)

รายละเอียดเต็ม: **`docs/WORLD_SERVER_VISION.md`**

| เฟส | ชื่อ | สรุป | สถานะ |
|-----|------|------|--------|
| **W0** | Rank board soft | อันดับ soft band · help title · rank_board.json | **1.13.15** |
| **W1** | Player echo | เงา snapshot จริง · สู้/คุย/ทีม · ไม่ทำร้ายเซฟเจ้าของ | **รอ** |
| **W2** | Rank challenge | ท้าอันดับ · จ่ายค่าหัว · ชนะได้ที่นั่งโชว์ | **รอ** |
| **W3** | World host | process โลกรันค้าง · client ต่อ | **รอ** |
| **W4** | Online lite | auth/anti-cheat เบา | **รอ** |

### เงื่อนไขเริ่ม W0 (โดยประมาณ)

- playtest หลัง 1.13.x ผ่านรอบหนึ่ง  
- ตลาด/เซฟโลกเสถียรพอ  
- ตกลงกฎค่าหัว + สิ่งที่โชว์บนบอร์ด  

**ลำดับแนะนำโดยรวม:** playtest → (T0–T1 หรือ เนื้อหา) → W0/H0 → W1 → H1–H3 → H4/W2 → …  
อย่ากระโดด W3–W4 / H5 ก่อน echo + assist async นิ่ง

---

## เฟส Help Situation / ขอแรงสังคม (วิสัยทัศน์ — ยังไม่ implement)

รายละเอียดเต็ม: **`docs/HELP_SITUATION_VISION.md`**

| เฟส | ชื่อ | สรุป | สถานะ |
|-----|------|------|--------|
| **H0** | Situation + consent | ดัน/วิกฤตบนเซฟ · เปิด/ปิดยินยอมแทรก | **1.13.12** |
| **H1** | กระดานสัญญาณ | รายการ `help.open` · เมนู **G** | **1.13.13** |
| **H2** | Offer + escrow | เงิน/ของตอบแทนล็อก · จ่าย/คืน | **1.13.13** |
| **H3** | Assist + chronicle | ยื่นมือ · สู้ · เขียนผลเซฟ P1 · inbox | **1.13.13** |
| **H4** | สังคมลึก | เพื่อน/ชื่อเสียงผู้ช่วย · เควสยื่นมือ · บันทึกโลก | **1.13.14** |
| **H5** | Live co-op | online พร้อมกันใน situation | **รอ** |

### หลักการล็อก (ย่อ)

1. สถานการณ์อยู่บน**เซฟเจ้าของ** — ไม่ใช่ใครก็เข้าได้  
2. ต้อง**ยินยอม (consent)** ก่อนแทรกเซฟแบบจำกัด  
3. ของตอบแทน **optional** · ใช้ escrow  
4. ร่วมทีมช่วย · async ก่อน realtime  
5. แยก echo ทั่วไป (ไม่แก้เซฟ) กับ assist (แก้ได้จำกัด)  

### เงื่อนไขเริ่ม H0 (โดยประมาณ)

- playtest แกน 1.13.x ผ่านรอบหนึ่ง  
- ดัน solo นิ่ง  
- ตกลง consent + escrow + ขอบเขตสิทธิ์ผู้ช่วย  

---

## V Later (คนละสาย)

| รายการ | หมายเหตุ |
|--------|----------|
| LLM local | NarrativePort หลัง field นิ่ง |
| Web IO | หลัง IO นิ่ง |
| Z-MOS เต็ม | multi-agent/ops — **ไม่** คุม logic เกม |
| Realtime MP + มอนโลก | หลัง H3/H5 foundation + W3+ — **ไม่ทำตอน solo** |

---

```bash
cd projects/openworld-fantasy
python3 -m game
python3 -m pytest -q
```
