# วิสัยทัศน์: โจมตี 4 แบบ · ป้องกัน · ธาตุ · ต้านสถานะ

**สถานะ:** **DD0–DD5 ทำแล้ว** (`1.17.1-alpha`) · polish ภายหลัง  
**เกมปัจจุบัน:** `1.17.x`  
**แผนรวม:** [`ROADMAP.md`](ROADMAP.md) · [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md)  
**เกี่ยว:** combat · ATB · ป้องกัน · AoE · status_fx · soft / anti-spoiler

---

## 0. เป้าหมายหนึ่งประโยค

ให้การโจมตี/ป้องกันมี**ชั้นชัด** (กายภาพ · เวท · แสง · มืด + ธาตุย่อย)  
ผู้เล่น**รู้สึก**ว่าต้องเลือกกัน/สกิลให้ถูก — **ไม่โชว์ตาราง %** หรือตัวเลขต้านดิบ

---

## 1. สถานะปัจจุบัน (baseline)

| ชั้น | ตอนนี้ | ช่องว่าง |
|------|--------|---------|
| ธาตุสกิล | `elements: [physical, fire, water, shadow, holy, …]` | ไม่มีชั้น **damage_class** ชัด 4 แบบ |
| แมตช์ธาตุ | `data/elements/matchups.yaml` บางคู่ | ยังไม่ครบ · ใช้เบาใน combat |
| ป้องกัน | `guard_*` + `strong_vs` / `weak_vs` tags | ยังไม่แยก **กายภาพ / เวท / ธาตุ** เป็นสเตตัส |
| ลดดาเมจถาวร | `power_def` อย่างเดียว | ไม่มี **magic_def** แยก |
| สถานะ | `status_fx.resist_chance` | ยังไม่ผูก **ธาตุ AoE → ต้านสถานะ** ชัด |
| UI | soft กัน strong/weak | ยังไม่อธิบายชั้นโจมตี 4 แบบ |

**หลักที่รักษา:** data-driven YAML · soft UI · ซ่อนสูตร · domain บริสุทธิ์ + pytest

---

## 2. โมเดลที่ล็อก (ออกแบบ)

### 2.1 ชั้นโจมตี — **Damage Class** (4 แบบ)

ทุกสกิล/การโจมตีมี `damage_class` หนึ่งค่าหลัก:

| # | id | ชื่อ UI soft | ความหมาย |
|---|-----|--------------|----------|
| 1 | `physical` | กายภาพ | ดาบ ธนู กระแทก · กันด้วยเกราะกาย |
| 2 | `arcane` | เวทมนต์ | เวทบริสุทธิ์/arcane · กันด้วยเกราะเวท |
| 3 | `light` | แสง | holy / ศักดิ์สิทธิ์ · ซ้อนธาตุ light |
| 4 | `dark` | มืด | shadow / เงา · ซ้อนธาตุ dark |

**แมปจากของเดิม (migrate soft):**

| elements เดิม | damage_class แนะนำ |
|---------------|-------------------|
| `physical` | physical |
| `arcane`, `magic` | arcane |
| `holy`, `light` | light |
| `shadow`, `dark` | dark |
| `fire`, `water`, `wind`, `earth`, `lightning`, `ice` | **ยัง physical หรือ arcane ตามสกิล** + **element** แยก |

กฎ:  
- **damage_class** = ช่องทางหลัก (4 แบบ)  
- **elements[]** = ธาตุย่อย (ไฟ น้ำ ดิน ลม แข็ง ไฟฟ้า แสง มืด …) สำหรับ matchup + สถานะ

```text
ดาเมจสุดท้าย ≈ raw
  × class_mitigation(physical_def / magic_def / light_dark soft)
  × element_matchup(attacker_el, defender_el)
  × guard_skill_mult(strong_vs / weak_vs)
  × status_mods
```

### 2.2 ชั้นป้องกัน — 4 แกน

| # | แกน | id ภายใน | ลดอะไร |
|---|-----|----------|--------|
| 1 | ป้องกันกายภาพ | `def_physical` / power_def | damage_class = physical |
| 2 | ป้องกันเวท | `def_arcane` / power_mdef | damage_class = arcane |
| 3 | ป้องกันธาตุ | `elem_resist[el]` | ธาตุย่อย: light, dark, fire, water, wind, earth, ice, lightning, … |
| 4 | ต้านสถานะ | `status_resist` / per-status | โอกาส shrug สถานะ — **บูสต์เมื่อโดนธาตุ/AoE ที่เกี่ยวข้อง** |

**แสง/มืด:**  
- เป็นทั้ง **damage_class** (light/dark) และ **element**  
- ป้องกันธาตุ light/dark ใช้ `elem_resist`  
- กันสกิล: guard strong_vs ยังใช้ได้ (เช่น กันเงา)

### 2.3 ธาตุย่อย (Element catalog)

| กลุ่ม | ids |
|-------|-----|
| แสง–มืด | `light`/`holy`, `dark`/`shadow` |
| ธรรมชาติ/เวท | `fire`, `water`, `wind`, `earth` |
| พายุ/หนาว | `lightning`, `ice` (แข็ง) |
| กาย | `physical` (แท็กเสริม ไม่ใช่ธาตุเสมอ) |

`matchups.yaml` ขยายคู่: ไฟ↔น้ำ, ดิน↔สายฟ้า, แสง↔มืด, น้ำ→ไฟฟ้า ฯลฯ  
**UI:** soft เท่านั้น — 「แสงแผด」, 「เงากลืน」, 「เปียกทำให้ไฟแผ่ว」

### 2.4 ต้านสถานะ (แกน 4) + AoE ธาตุ

```text
P_resist = clamp(
    base_resist(status)
  + gear_status_resist
  + elem_status_bonus(attack_elements, status)   # ใหม่
  + aoe_status_soft                               # ใหม่: AoE เบาลง/ต้านขึ้นเล็ก
, 0, resist_cap)
```

| แนวคิด | รายละเอียด |
|--------|------------|
| โดนไฟ AoE | ต้าน `burn` สูงขึ้นเล็ก (เคยชิน/ระวัง) **หรือ** ต้านลดถ้าเปียก — เลือกทิศหนึ่งใน D2 |
| เกียร์/ลงทุน | DEF/INT soft → ต้านสถานะ (มีบางส่วนใน needs/status แล้ว) |
| Soft UI | 「ร่างกายชินกับเปลว」 / 「จิตยังไม่เคยชินเงา」 — ไม่โชว์ % |

**ข้อเสนอ default (ล็อกง่าย):**  
- AoE ธาตุ: **chance สถานะต่ำกว่า single** อยู่แล้ว → เพิ่ม **elem_resist ชั่วคราว soft** หลังโดนสถานะชนิดนั้น (stack ซ่อน)  
- อย่าให้ “ฟาร์มต้านถาวร” ง่ายเกิน

---

## 3. สูตร runtime (ซ่อน — implement)

### 3.1 ลำดับลดดาเมจ (ขาเข้า)

```text
1. raw (มอน/สกิล)
2. dodge / miss soft (ถ้ามี)
3. damage_class mitigation
     physical → power_def
     arcane   → power_mdef (ใหม่)
     light/dark → lerp(def, mdef) หรือ elem_resist soft
4. element matchup mult (matchups.yaml)
5. active guard skill (strong/weak/neutral)
6. status dmg_taken_mult
7. floor ≥ 0
```

### 3.2 ขาออก (ผู้เล่นโจมตี)

```text
1. base power + ATK/MAG ตาม damage_class
2. element matchup vs mon.elements
3. mon.elem_resist / mon.def_physical / def_arcane
4. crit / cards / needs mult
```

### 3.3 ข้อมูลบนสกิล (YAML)

```yaml
- id: fire_ball
  damage_class: arcane      # ใหม่ (default จาก elements ถ้าไม่มี)
  elements: [fire]
  power: 22
  # status apply เหมือนเดิม
```

```yaml
- id: guard_basic
  slot: defense
  guard_class: physical     # ใหม่: physical | arcane | elemental | universal
  strong_vs: [physical]
  weak_vs: [arcane, fire, lightning]
```

### 3.4 ข้อมูลบนผู้เล่น / มอน

```yaml
# player (computed / alloc later)
power_def: …      # กาย
power_mdef: …     # เวท (ใหม่)
elem_resist:
  fire: 0.0       # -0.3..0.5 soft clamp
  shadow: 0.0
status_resist: { burn: 0.05, … }
```

ลงทุนแต้ม: **defense → def กาย**, **magic/intelligence → mdef** (soft, ไม่โชว์)

---

## 4. UI soft (anti-spoiler)

| สถานการณ์ | แสดง |
|-----------|------|
| กันถูกชั้น | 「★ เกราะรับแรงกระแทก」 / 「ม่านกลืนเวท」 |
| กันผิดชั้น | 「✗ เกราะไม่ช่วยต่อแสงนั้น」 |
| ธาตุดี/แย่ | flavor เดิม + soft |
| ต้านสถานะ | 「เปลวไม่ติด」 / 「เงายังเกาะ」 |
| แผงสถานะ | soft band เท่านั้น — ไม่โชว์ `def_fire: 12%` |

เมนูป้องกันในไฟต์: จัดกลุ่ม soft  
`1 กันกาย · 2 กันเวท · 3 กันธาตุ · 0 ไม่กัน`  
(สกิลจริง map เข้ากลุ่ม — ผู้เล่นไม่เห็น id)

---

## 5. แผนเฟส implement (Dmg/Def)

| เฟส | ชื่อ | งาน | ผลผู้เล่น | เป้าเวอร์ชัน |
|-----|------|-----|----------|-------------|
| **DD0** | แคตตาล็อก | `damage_classes` · `elements` catalog · แมป skill เดิม | — | 1.16.x |
| **DD1** | ลดดาเมจชั้น | power_mdef · class mitigation ขาเข้า/ออก | เวท vs กายรู้สึกต่าง | 1.16.x |
| **DD2** | กันสกิลกลุ่ม | guard_class · UI ป้องกัน 3 กลุ่ม | เลือกกันถูก/ผิดชัด | 1.16–1.17 |
| **DD3** | ธาตุ matchup เต็ม | ขยาย matchups · mon resists | ไฟ/น้ำ/แสง/มืดมีน้ำหนัก | 1.17 |
| **DD4** | ต้านสถานะ + AoE | elem_status_bonus · aoe soft | AoE ธาตุไม่ spam debuff โหด | 1.17–1.18 |
| **DD5** | เกียร์/ลงทุน | เกียร์ให้ mdef/elem_resist · soft panel | build หลากหลาย | 1.18+ |

**ลำดับแนะนำ:** DD0 → DD1 → DD2 → DD3 → DD4 → DD5  

**อย่าทำพร้อม:** W1 echo / H5 — คนละสาย (ขนานได้หลัง DD1 นิ่ง)

---

## 6. แผนภาพ

```text
[ตอนนี้ 1.15 · combat เดิม]
        │
        ▼
 DD0  catalog + migrate skills
        │
        ▼
 DD1  physical vs arcane def (mdef)
        │
        ├─► DD2  guard groups UI
        │
        ▼
 DD3  element matchups full
        │
        ▼
 DD4  status resist + AoE soft
        │
        ▼
 DD5  gear / invest hooks
```

---

## 7. เกณฑ์จบแต่ละเฟส

| เฟส | เกณฑ์ |
|-----|--------|
| DD0 | ทุกสกิล combat มี damage_class · เทส data integrity |
| DD1 | ดาเมจเวทกับกายไม่ใช้ power_def อย่างเดียว · pytest |
| DD2 | เมนูกันแยกกลุ่ม · strong/weak ยังทำงาน |
| DD3 | อย่างน้อย 8 คู่ matchup · มอนมี elements |
| DD4 | fire AoE burn chance/resist soft ต่าง single · เทส |
| DD5 | อย่างน้อย 3 เกียร์ให้ mdef หรือ elem_resist |

---

## 8. ความเสี่ยง

| ความเสี่ยง | กัน |
|------------|-----|
| ผู้เล่นงง 4 ชั้น + ธาตุ | soft label · ค่อยๆ ปลด DD1 ก่อนธาตุเต็ม |
| balance พัง | clamp mult 0.4–1.8 · อย่า stacking ซ้อนเกิน |
| data บวม | migrate อัตโนมัติจาก elements เดิม |
| spoiler wiki | ไม่โชว์ตารางใน UI · matchups ซ่อน |

---

## 9. ไฟล์ที่แตะ (เมื่อ implement)

| ไฟล์ | บทบาท |
|------|--------|
| `data/elements/classes.yaml` | 4 damage_class |
| `data/elements/matchups.yaml` | ขยายคู่ |
| `data/skills/*.yaml` | damage_class + elements |
| `game/domain/combat.py` | mitigation pipeline |
| `game/domain/combo.py` | apply_defense + guard_class |
| `game/domain/status_fx.py` | elem/AoE resist soft |
| `game/services/combat_session.py` | UI กันกลุ่ม |
| `tests/unit/test_damage_defense.py` | ใหม่ |

---

## 10. ความสัมพันธ์กับระบบอื่น

| ระบบ | เกี่ยว |
|------|--------|
| ลงทุน DEF / MAG / INT | DEF→กาย · MAG/INT→เวท |
| needs | หิว/ล้า soft บน ATK — คงไว้ |
| AoE balance | splash mult คง · ซ้อน status soft |
| หีบ / เกียร์ | ทีหลัง DD5 |
| soft / anti-spoiler | ทุกเฟส |

---

## 11. คำสั่งทีม (เมื่อเริ่มโค้ด)

1. อย่า rewrite ทั้ง combat ใน PR เดียว — DD0–DD1 ก่อน  
2. ทุกเฟส: pytest + ScriptedIO ไฟต์สั้น  
3. อัป `PHASES.md` / `IMPROVEMENT_PLAN` เมื่อปิดเฟส  
4. UI กล่องสัดส่วนเดียวกับไฟต์ 1.15  

**คำสั่งถัดไป:** พิมพ์ **พัฒนา DD0–DD1** เมื่อพร้อมลงมือโค้ด  
