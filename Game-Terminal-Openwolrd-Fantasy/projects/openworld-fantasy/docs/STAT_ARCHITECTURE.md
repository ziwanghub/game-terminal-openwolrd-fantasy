# Stat & Relationship Architecture (WO-035)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-035 |
| **สถานะ** | … · WO-046 Synergy · **WO-047 Human Feedback + Feel Polish · DNA lock** @ 1.94 |
| **หลัก** | 3 Layer · map ของเดิม · ไม่ rewrite ครั้งเดียว · soft DNA |

---

## เฟส 0 — Glossary & Mapping (ล็อก)

### 0.1 Glossary (ชื่อห้ามสับสน)

| คำ (UI/เอกสาร) | โค้ดหลัก | Layer | ความหมายล็อก |
|----------------|----------|-------|----------------|
| **หิว** | `needs.hunger` | L1 Needs | สะสมทางกาย · สูง = แย่ |
| **ล้า** | `needs.fatigue` | L1 Needs | ความเหนื่อยสะสม · สูง = แย่ · กระทบ ATB |
| **ขวัญ** | `needs.morale` | L1 Needs | กำลังใจ · สูง = ดี · ภาระเรลิกกินชั้นนี้ |
| **HP / ชีพ** | `hp` / `max_hp` | Vitals | ชีวิต · soft อาการได้ |
| **MP / มานา** | `mana` / `max_mana` | Vitals | พลังเวทใช้ได้ |
| **กายภาพ (Physical)** | facet `physical` | L2 Core | รวม atk/def/speed powers soft |
| **เวท (Magical)** | facet `magical` | L2 Core | รวม magic/mdef/mana soft |
| **จิตวิญญาณ (Anima)** | **`anima`** | L2 Core | Core เสาที่ 3 ซ่อน — **ไม่ใช่ขวัญ** |
| **สติ** | `intel_current` / `intel_max` | Spendable | ใช้เร่งจังหวะ / ทางเลือก |
| **โฟกัสจิต** | `focus_latent` | Hidden | คอมโบ — ไม่โชว์ตัวเลข |
| **โชค** | `luck_score` | Multiplier bus | ตัวคูณโอกาส · ไม่ลง P |
| **คริ / หลบ** | `crit_chance` / `dodge_chance` | L3 Derivative | ซ่อน % · flavor อย่างเดียว |
| **power_*** | `power_atk` ฯลฯ | L3 | ซ่อนเสมอ |
| **ลงทุน P** | `stats_alloc` | Invest | โจม/กัน/เวท/เร็ว · soft UI |
| **ภาระเรลิก** | burden band | Soft state | กินขวัญ · แจ้ง `relic.*` |
| **relic.spirit_*** | Soft Alert codes | Alert only | **= ขวัญตอนมีเรลิก** · **ห้าม** ใช้เป็น Anima |
| **สัมพันธ์** | `party_bonds` / `world_relations` | Social axis | 0–100 ราย actor |

### 0.2 Spirit naming lock

| ห้ามใช้ | เหตุ |
|---------|------|
| `spirit` เปล่า | ชน alert / คลุมเครือ |
| `relic.spirit_*` เป็น resource | ล็อก WO-034 = morale display |
| `needs.spirit` | ปน Needs |

| ใช้ | |
|-----|--|
| **โค้ด** | `anima` (float soft 0–100 ภายใน) |
| **UI soft** | จิตวิญญาณ · แบนด์ (แผ่ว / มั่น / ลึก…) |
| **facet id** | `spirit` ในตาราง Core **เฉพาะ facet กลุ่ม** · ค่าจริงเก็บที่ `anima` |

### 0.3 Map ฟิลด์เดิม → Layer

| ฟิลด์เดิม | Layer | Core facet (ถ้ามี) |
|-----------|-------|---------------------|
| `needs.hunger` | L1 | — |
| `needs.fatigue` | L1 | ← soft จาก Physical สูง (ล้าช้า/ทน) แผ่ว |
| `needs.morale` | L1 | ← soft จาก Anima (ขวัญนิ่งกว่า) แผ่ว |
| `stats_alloc.atk/defense/speed` | Invest → L2 Physical | physical |
| `stats_alloc.magic` | Invest → L2 Magical | magical |
| `power_atk/def/spd` | L3 | physical |
| `power_mag/mdef` | L3 | magical |
| `power_intel` · `mind_growth` · `focus_latent` | L3 / hidden | spirit (ป้อน anima soft) |
| `crit_chance` · `dodge_chance` | L3 | — |
| `luck_score` | Luck bus | — |
| `intel_*` | Spendable | magical/spirit edge |
| `party_bonds[id]` | Relationship | companion |
| `world_relations[axis:id]` | Relationship | npc/divine/infernal |
| gear latent_* | L3 | ตามชิ้น |

### 0.4 UI visibility rules (ล็อก)

| จอ | โชว์ | ซ่อน |
|----|------|------|
| **Field L0 / L1c / hub หลัก** | ชื่อ·เลเวล·อาชีพ · HP soft/แถบ · กายใจ 3 · เงินย่อ · ภาระ soft | power_* · crit% · luck · anima ดิบ · invest ×N |
| **Combat vitals** | HP/MP แถบ · กายใจ compact · ATB · สถานะ | invest · anima ดิบ · luck |
| **เมนู P** | soft bar / soft feel · แต้มคงเหลือ · สติ soft | ตัวเลข ×N invest (เฟส 1+) · luck · anima |
| **สถานะเต็ม S** | ตัวตน · ชีพ · soft ลงทุน · soft Anima band (หลังประเมิน/เบา) | power ดิบ · % |
| **ประเมินตัวเอง** | soft band Physical/Magical/Anima · อาการ HP | ตัวเลข power |
| **God compact** | เหมือน field + needs · อาจโชว์ debug ทีหลัง | — |

### 0.5 กฎ Needs ↔ Core (เฟส 2 + WO-037)

| Core | ป้อน Needs soft |
|------|-----------------|
| Physical สูง | ล้าสะสมช้าเล็ก / ทนหิวแผ่ว |
| Magical สูง | สติ max / ฟื้นสติ soft |
| Anima (Spirit facet) สูง | ขวัญ **drain ช้า** · ต้านสถานะจิต · ภาระ/ออร่า soft |
| Anima ต่ำ | ขวัญ drain เร็ว · soft fail ท่าโฟกัส (หายาก) |

### 0.6 Anima Presence (WO-037) — soft moments

| เหตุการณ์ | Soft Alert | รู้สึก |
|-----------|------------|--------|
| ใส่เรลิก | `anima.relic_touch` | จิตสั่นไหว · ลึกกว่าขวัญ |
| Chamber spar | `anima.chamber_echo` | หนักแต่ลึกซึ้ง |
| ห้องสมุด / เรียนสกิล | `anima.learn_glow` | สมาธิไหล |
| คอมโบเวท ≥2 | `anima.mana_flow` | มานาคล่อง |
| แผ่ว / ลึก | `anima.thin` / `anima.deep` | ใบ้แบนด์ |
| ท่าสั่น | `anima.skill_waver` | soft fail (frail only) |

**ห้าม:** โชว์ตัวเลข `anima` · ลง P · ปน `relic.spirit_*` (ขวัญ)

### 0.7 World Relations Lite (WO-038)

| Faction | รหัส | ตัวอย่างแหล่ง soft |
|---------|------|---------------------|
| สายสวรรค์/เทพ | `faction:divine` | NPC priest/sage · ห้อง G · เรลิก holy/storm |
| สายมาร/นรก | `faction:infernal` | NPC cultist · หนอง · เรลิก hell/void |
| เงาโบราณ/echo | `faction:ancient_echo` | echo approach · ป่ามืด |

| ผล soft | |
|---------|--|
| divine สูง | ขวัญ drain ช้า · anima อุ่น (นิด) |
| infernal ต่ำ (เป็นศัตรู) | ขวัญ drain เร็วเล็กน้อย |
| Soft Alert | `world.divine_*` · `world.infernal_*` · `world.echo_*` |

โมดูล: `game/domain/world_relations.py`  
UI: บรรทัด “โลก · …” บน hub · ④ ในประเมินตัวเอง (V)

### 0.8 Faction Mini-Moments (WO-039)

| id | พื้นที่ | Faction | ทางเลือก |
|----|---------|---------|----------|
| `divine_wind_gaze` | เมือง · ผลึก | divine | ช่วย / ผ่าน / หลบ |
| `infernal_haze_echo` | หนอง · ถ้ำ | infernal | จ้อง / ปฏิเสธ / หลบ |
| `echo_forest_whisper` | ป่ามืด | ancient_echo | ฟัง / ไล่ / เงียบ |

| ผล soft | |
|---------|--|
| ช่วย/ฟัง | faction ↑ · Anima อุ่น · Soft Alert |
| จ้องมาร | faction infernal ↑ แบบเสี่ยง · ขวัญ↓ · Anima แผ่ว |
| Auto | soft resolve หรือเลี่ยงถ้า faction เย็น (`auto_avoid_cold_faction`) |

โมดูล: `game/domain/faction_moments.py` · sight kind `faction_moment`

### 0.9 Anima × Relic Depth (WO-040)

ปิดลูป **เรลิก ↔ จิตวิญญาณ ↔ สายตาโลก** โดยไม่เพิ่ม resource / ระบบอัปเกรด / เควสใหญ่

| Relic lean | ตัวอย่าง | ใส่แล้ว (Anima) | ขวัญ drain (equipped) |
|------------|----------|-----------------|------------------------|
| **divine** | storm · sky · holy | อุ่น (+anima) · Soft `anima.relic_divine` | ช้า (`×0.88`) |
| **infernal** | hell · fire · dark | แผ่ว (−anima) · Soft `anima.relic_infernal` | เร็ว (`×1.12`) |
| **ancient_echo** | void · shadow · arcane | สั่นไหว · Soft `anima.relic_echo` | ไม่เสถียรเล็ก (`×1.03`) |

| ช่วง | Soft / ผล |
|------|-----------|
| **Equip** | WO-037 presence + WO-040 lean depth · faction soft ↑ · `_relic_faction_lean` |
| **Chamber spar** | Anima swing ชัด · `anima.spar_*` · faction pulse |
| **สำรวจ** | โอกาสกระซิบ/สายตา · `world.relic_*_whisper` · world_relations เล็กน้อย |
| **Auto** | ถอดเมื่อ Anima แผ่ว + ขวัญกด (`should_auto_unequip_for_anima`) |

**ห้าม:** โชว์ตัวเลข anima · resource ใหม่ · relic upgrade tree · เปลี่ยน UI หลัก

โมดูล: `game/domain/relic_anima.py`  
Wire: `divine_burden` (equip / tick / auto) · `needs` morale mult · `godforge_chamber` spar · `field_actions` explore

### 0.10 Relic Soft Bonds (WO-041)

เมื่อใส่เรลิก **2+ ชิ้น** พร้อมกัน — lean โต้ตอบกัน (ไม่ใช่ upgrade tree)

| สถานะ | เงื่อนไข | Anima | ขวัญ drain | Soft Alert |
|--------|----------|-------|------------|------------|
| **Resonance (เรโซแนนซ์)** | 2+ lean เดียวกัน | Divine อุ่น / Infernal แผ่วเบา / Echo สั่น | Divine ช้ากว่า · Infernal ปานกลาง · Echo ไม่เสถียรเบา | `anima.bond_*` |
| **Soft Tension** | lean ผสม (เช่น divine+infernal) | แผ่ว | เร็วขึ้น (`×1.16`) | `anima.bond_tension` |

| ช่วง | ผล soft |
|------|---------|
| **Equip** | หลัง lean depth → `on_relic_bond_pulse` · faction ของ bond ↑ |
| **Chamber spar** | Bond ลึกขึ้น · `anima.spar_bond_*` · faction pulse แรงขึ้น |
| **สำรวจ** | Bond gaze/haze/chorus · Tension ลมขัด lean |
| **Auto** | Tension + ขวัญกด → ถอดชิ้น minority lean ก่อน |

**ตัวอย่าง content ปัจจุบัน:** storm+aegis = Divine Bond · hell+aegis = Tension · void ring = echo lean เดี่ยว (รอคู่)

**ห้าม:** resource ใหม่ · upgrade tree · เควสใหญ่ · UI ใหม่

API: `evaluate_relic_bonds` · `on_relic_bond_pulse` · `tension_unequip_preference`

### 0.11 Area Mini-Moments + Relic Content (WO-042)

ขยาย content เบา ๆ — ไม่เควสใหญ่ / ไม่ upgrade

#### Mini-Moments ต่อพื้นที่

| id | พื้นที่ | Faction | ทางเลือกหลัก |
|----|---------|---------|--------------|
| `divine_wind_gaze` | เมือง · ผลึก | divine | ช่วยอธิษฐาน |
| `infernal_haze_echo` | หนอง · ถ้ำ | infernal | จ้อง / ปฏิเสธ |
| `echo_forest_whisper` | ป่ามืด | echo | ฟัง / ไล่ |
| **`infernal_cave_coal`** | **ถ้ำเงา** | infernal | รับเถ้า / ปัด |
| **`echo_desert_mirage`** | **ทะเลทราย** | echo | ฟังภาพลวง / ไล่ |
| **`divine_crystal_prayer`** | **ยอดผลึก** | divine | ร่วมอธิษฐาน / ผ่าน |

#### Relic pack (6 ชิ้น) + Bond pairs

| Relic | Slot | Lean | คู่ Bond |
|-------|------|------|----------|
| `relic_storm_fang` | main | divine | + `relic_aegis_sky` → **Divine Bond** |
| `relic_aegis_sky` | body | divine | ↑ |
| `relic_hell_ember_blade` | main | infernal | + `relic_hell_brand_charm` → **Infernal Bond** |
| **`relic_hell_brand_charm`** | acc | infernal | ↑ (WO-042) |
| `relic_void_whisper_ring` | acc | echo | + `relic_echo_shroud` → **Echo Bond** |
| **`relic_echo_shroud`** | body | echo | ↑ (WO-042) |

แหล่ง: บอส rare/very_rare · เควส soft (`brand_of_hell_charm` · `echo_shroud_burden`) — **ไม่ขายร้าน**

### 0.12 Bond Soft Cap & Soft Chorus (WO-043)

| ชิ้น lean เดียวกัน | โหมด | รู้สึก |
|-------------------|------|--------|
| **1** | single (WO-040) | lean เดี่ยว · Anima อุ่น/แผ่ว/สั่น |
| **2** | **Resonance** (WO-041) | เรโซแนนซ์ · Soft Alert `anima.bond_*` |
| **3+** | **Soft Chorus** (WO-043) | คณะเรลิก · แรงกว่า 2 ชิ้น · `anima.chorus_*` |
| **4+** | Chorus + **Soft Cap** | หนักเกิน · จิตสั่น · ขวัญกดแผ่ว · ไม่ล็อกเกม |

| Chorus lean | Anima | ขวัญ | World / Explore |
|-------------|-------|------|-----------------|
| Divine | อุ่นแรง | ลดช้า (`~×0.82`) | สายตาเทพลึก · faction ↑ |
| Infernal | แผ่วแต่แข็ง | กดปานกลาง | หมอกมารมั่นคง |
| Echo | สั่นแต่เชื่อม | ไม่เสถียรเบา | คณะกระซิบ · chance สูง |

| Soft Cap | |
|----------|--|
| เงื่อนไข | count ≥ 4 lean เดียวกัน |
| ผล | Anima ดึงกลาง · ขวัญ −1 แผ่ว · Soft Alert `anima.bond_soft_cap` · faction boost จำกัด |
| Auto | Cap + ขวัญกด → ถอดชิ้น non-weapon ก่อน (บางคณะ) |

| Chamber spar | Chorus ลึกกว่า Resonance · Soft Cap แผ่วตอนซ้อม |
| World | `world.chorus_*` · adjust_faction แรงขึ้น (cap ที่ 4+) |

ชิ้นที่ 3 (เปิด Chorus จริง): `relic_divine_laurel` (head) · `relic_hell_ash_greaves` (legs) · `relic_echo_sandals` (feet)

**ห้าม:** resource ใหม่ · upgrade tree · UI ใหม่

### 0.13 Area Moments Full Map + Soft Foresight (WO-044)

ปิดลูป “ทุกพื้นที่มีสายตา” — Mini-Moment + Soft Foresight ใบ้ lean

#### Mini-Moments ครบ 8 พื้นที่ (9 moments)

| พื้นที่ | lean | Moments |
|---------|------|---------|
| dark_forest | echo | `echo_forest_whisper` |
| mist_marsh | infernal | `infernal_haze_echo` |
| cave_shadow | infernal | `infernal_haze_echo` · `infernal_cave_coal` |
| desert_heat | echo | `echo_desert_mirage` |
| crystal_peak | divine | `divine_wind_gaze` · `divine_crystal_prayer` |
| **mountain_rock** | divine | **`divine_mountain_gaze`** |
| **ancient_city** | divine | `divine_wind_gaze` · **`divine_city_bell`** |
| **void_rift** | echo | **`echo_void_pull`** |

#### Soft Foresight · Moment Hint

| จุด | ผล soft |
|-----|---------|
| เดินทางเข้าพื้นที่ | สายตา lean + ใบ้ Mini-Moment ที่เป็นไปได้ |
| ก่อนลงดัน (Foresight) | + world gaze ในแผง foresight เดิม |
| สำรวจ | chance ต่ำ (~12%) ถ้ายังไม่เคยเห็นในรอบ visit |
| Soft Alert | `world.foresight_divine_gaze` / `infernal_haze` / `echo_whisper` |

ตัวอย่างข้อความ:  
「คุณรู้สึกสายตาจากเทพวายุ…」·「เงามารแผ่ซ่านเบา ๆ…」·「เสียงกระซิบจาก echo…」  
+ 「ใบ้สายตาโลก อาจเจอ Mini-Moment 〔…〕」

โมดูล: `soft_foresight.area_world_gaze_lines` · `explore_soft_gaze_tick`  
Wire: `field_actions` travel/explore · `soft_dungeon_entry_warnings`

**ห้าม:** resource ใหม่ · เควสใหญ่ · UI ใหม่

### 0.14 DNA Lock Lite (WO-045 Playtest Polish)

หลังโซ่ WO-035–044 ระบบ soft หลัก **ล็อกแนวทาง** (ปรับโทน/ความถี่ได้ · อย่า rewrite):

| ชั้น | ล็อก |
|------|------|
| **Needs** | หิว · ล้า · ขวัญ · soft warn บน Soft Alert Bus |
| **Anima** | Core ซ่อน · ≠ ขวัญ · Soft Presence / band เท่านั้น |
| **Relic lean** | divine / infernal / echo · equip depth |
| **Bond** | 2 = Resonance · 3+ = Chorus · 4+ = Soft Cap |
| **Moments** | ครบ 8 พื้นที่ · ช่วย/ปฏิเสธ/หลบ · Auto soft |
| **Foresight** | เสบียง/ภาระ + world gaze · re-visit = **brief** (WO-045) |
| **Auto** | ถอดภาระ · anima frail · tension/cap · เลี่ยง moment เย็น |

#### WO-045 polish ที่ ship

- Travel ซ้ำ → brief gaze (ไม่ dump ใบ้เต็มทุกครั้ง)  
- Moment chance: แรกสูง · หลังเงียบ · cool-down พื้นที่เดิม  
- ใส่เรลิกหลายชิ้น → ลดข้อความ lean ซ้อน bond/chorus  
- Soft Cap / Foresight Soft Alert throttle ยาวขึ้น  

**คู่มือมือ:** [`WO045_HUMAN_PLAYTEST.md`](WO045_HUMAN_PLAYTEST.md)  
**Harness:** `scripts/wo045_playtest_polish.py`

### 0.15 Relic × Moment Soft Synergy (WO-046)

เชื่อม **เรลิก lean** กับ **lean พื้นที่ / Mini-Moment** — soft เท่านั้น

| สถานะ | เงื่อนไข | ผล soft |
|--------|----------|---------|
| **Resonate** | relic primary lean = area lean | Moment chance ×1.28–1.42 · Anima ชัดขึ้น · ขวัญ drain เบา · bias moment ตรง faction |
| **Area Tension** | relic lean ≠ area lean | Moment chance แผ่ว · ขวัญ drain เร็วเล็กน้อย · Soft Alert ขัด lean · Auto ถอดเมื่อขวัญกด |

| จุด | Integration |
|-----|-------------|
| **Foresight** | ใบ้ “เรลิกสะท้อนโลก” / “เรลิกขัด lean โลก” |
| **Moment resolve** | Anima nudge scale (resonate ×1.35) |
| **Explore** | presence pulse โอกาสต่ำ (throttled) |
| **Chamber spar** | ซ้อมตอน resonate → จิต/พันธะชัดขึ้น |
| **Auto** | area tension + ขวัญกด → ถอดเรลิก |

API: `evaluate_relic_area_synergy` · `moment_chance_factor` · `synergy_foresight_lines`  
Soft Alert: `world.synergy_*` · `anima.synergy_*`

**ตัวอย่าง:** storm/aegis บนเขา/ผลึก/เมือง → resonate · hell บนเขา → area tension

**ห้าม:** resource ใหม่ · upgrade · เควสใหญ่ · UI ใหม่

### 0.16 Human Feedback + Feel Polish (WO-047)

หลัง synergy (WO-046) — **ล็อก DNA + ปรับ feel** ไม่เพิ่ม feature

| ปรับ (feel) | รายละเอียด |
|-------------|------------|
| Foresight synergy | โทนภาษาธรรมชาติขึ้น (น้อย jargon lean〔〕) · ใบ้ถอด/ย้ายเมื่อ tension |
| Presence pulse | explore ~24% · throttle 3 · Anima nudge ชัดขึ้น · soft band thin/deep |
| Area tension morale | ×1.09 (รู้สึกกด) · resonate ×0.96 |
| Soft Cap | กลาง · ขวัญ pinch เฉพาะ morale>28 · ข้อความ “ถอดชิ้นหนึ่งแล้วนิ่ม” |
| Soft Alert synergy | throttle 2–3 · เน้น “จังหวะเดียวกัน / ดึงคนละทาง” |

**คู่มือมือ:** [`WO047_HUMAN_PLAYTEST.md`](WO047_HUMAN_PLAYTEST.md)  
**Harness:** `scripts/wo047_human_feedback_polish.py`  
**แบบฟอร์ม:** `exports/WO047_HUMAN_FEEDBACK.md`

DNA หลัก (Needs · Anima · Bond/Chorus · Moments · Foresight · Synergy · Auto) **ถือว่าล็อกแนวทาง** — ขยาย content/ soft layer ถัดไปได้โดยไม่ rewrite

---

## เฟส implement

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **0** | Glossary · map · anima name · UI rules | done |
| **1** | Visible shell · soft P · ประเมินตัวเอง | done lite |
| **2** | Core facets · anima hidden · needs links | done lite |
| **3** | Luck→upgrade · world_relations · assist luck soft | done lite |

---

## โมดูล

| ไฟล์ | บทบาท |
|------|--------|
| `game/domain/stat_arch.py` | facets · anima · soft assess · HP soft · UI helpers |
| `game/domain/relic_anima.py` | WO-040–046 lean · Bonds · Chorus · Cap · **area synergy** · spar · auto |
| `docs/STAT_ARCHITECTURE.md` | เอกสารนี้ |

---

## Changelog

| วันที่ | |
|--------|--|
| 2026-07-15 | WO-035 เฟส 0–3 lite ship |
| 2026-07-15 | WO-037 Anima Presence · soft moments · morale/combat link |
| 2026-07-15 | WO-038 World Relations Lite · divine/infernal/echo |
| 2026-07-15 | WO-039 Faction Mini-Moments · 3 soft encounters |
| 2026-07-16 | WO-040 Anima × Relic Depth · lean · spar · explore whisper · auto |
| 2026-07-16 | WO-041 Relic Soft Bonds · resonance · tension · spar/auto |
| 2026-07-16 | WO-042 Area Moments (ถ้ำ/ทะเลทราย/ผลึก) + hell charm / echo shroud |
| 2026-07-16 | WO-043 Soft Chorus (3+) · Soft Cap (4+) · third lean pieces |
| 2026-07-16 | WO-044 Area moments ครบแผนที่ · Soft Foresight moment hint |
| 2026-07-16 | WO-045 Playtest Polish · DNA lock lite · foresight/moment/equip tone |
| 2026-07-16 | WO-046 Relic × Moment/Area Soft Synergy lite |
| 2026-07-16 | WO-047 Human Feedback round · feel polish · DNA lock |
