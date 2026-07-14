# Vision: Skill Slot ขยาย + Skill Rank

**สถานะ:** **SK-R0–R5 lite ship แล้ว (1.43–1.44)** · polish/balance คิว  
**เกมปัจจุบันอ้างอิง:** `1.44.0-alpha` · สกิล ~116 · rank + pack R4  
**หลัก soft:** ผู้เล่นไม่เห็นสูตร % · Rank อัปวิธีซ่อน · anti-spoiler  
**คู่กับ:** [`SKILL_SYSTEM.md`](SKILL_SYSTEM.md) · [`STATUS.md`](STATUS.md) · DD status · combo  

---

## 0. สิ่งที่มีอยู่แล้ว (ฐาน)

| ชั้น | ปัจจุบัน |
|------|----------|
| **slot** | `combat` (~75) · `support` (~13 ฮีล/บัฟเบา) · `defense` (~12 กันกลุ่ม) |
| **status catalog** | debuff: poison/burn/freeze/stun/shock · buff: regen/might/ward/focus |
| **apply** | มอน `attack_profiles.status` · การ์ด on-hit · ยังเกือบไม่มีสกิลผู้เล่นชนิด debuff ชัด |
| **charge** | master_lease / fixed บางตัว |
| **combo** | เรียง combat skills · defense แยกตอนโดนตี |
| **Unit / HSR** | skill t5 แรง/joke ตามสไตล์ |

**ช่องว่างที่คุณชี้:**  
debuff เป็นสายสกิลยังบาง · defense ยังไม่มีสะท้อน/counter ชัด · buff ซ้อนร่ายพร้อมกันอาจพังบาลานซ์ · ยังไม่มี **Skill Rank** (F→SSS)

---

## 1. ออกแบบ Slot ใหม่ (taxonomy)

### 1.1 ตาราง slot เป้าหมาย

| slot | บทบาท | ตัวอย่างผล | จำกัดหลัก |
|------|--------|-----------|-----------|
| **combat** | ดาเมจตรง · AoE · ธาตุ | fire_ball · cleave | ดาเมจ + MP · rank scale power |
| **debuff** | ใส่สถานะผิดปกติให้เป้า | poison cloud · ลด ATK soft | chance ซ่อน · resist · 1 status/hit soft · CD/charge |
| **buff** | บัฟตัวเอง (หรือปาร์ตี้เบา) | might · focus · haste soft | **stack rule** · ร่ายซ้อนจำกัด · MP สะสม |
| **defense** | กัน · **สะท้อน** · **counter** | guard · reflect veil · riposte | ใช้ตอนโดนตี / ตั้งท่าล่วงหน้า 1 รอบ |
| **support** | ฮีล · ล้าง · utility ไม่ใช่บัฟโจมตี | heal · cleanse · mist | แยกจาก buff ชัด (อย่าปน might กับ heal) |

> **migrate soft:**  
> - ฮีล/cleanse อยู่ `support` ต่อ  
> - might/ward/focus ถ้าเป็นสกิล → ย้ายหรือ tag `buff`  
> - กันเดิม = `defense.guard` · ใหม่ = `defense.reflect` / `defense.counter`

### 1.2 Debuff — ระบบควรมีอะไร

ยึด catalog ที่มี + เติมทีละชุด (อย่า dump RO):

| กลุ่ม | status ที่มี/ควร | สกิลตัวอย่าง (concept) |
|-------|------------------|------------------------|
| **DoT** | poison · burn | เมฆพิษ · เปลวติด |
| **Control** | freeze · stun · shock | น้ำแข็งเท้า · ฟ้าผ่ามึน |
| **Weaken** (เพิ่มทีหลัง) | weak / slow / silence (ยังไม่มีครบ) | ลดแรง/ช้า/ปิดร่าย soft |
| **Mark** | soft mark (ใหม่ optional) | เป้าถูก mark → ดาเมจถัดไปนิด |

**กฎ balanace debuff (ล็อกแนว):**
1. ติดผ่าน `apply_status` + resist ที่มีแล้ว (DD4)  
2. **ไม่การันตีติด** — soft text เท่านั้น  
3. **1 status ต่อสกิล/ต่อเป้า** (anti stack spam เหมือน on-hit cards)  
4. Rank สูง → duration/chance soft ขึ้น **และ** MP/charge แพง  
5. Elite/บอส `intel_tier` สูง → ต้าน/หนี debuff บ่อยขึ้น soft  
6. ห้าม debuff ถาวร · max duration cap ซ่อน  

### 1.3 Defense — กัน + สะท้อน + Counter

| subtype | พฤติกรรม | ตัวอย่าง |
|---------|----------|----------|
| **guard** (มีแล้ว) | ลดดาเมจตามกลุ่มกาย/เวท/ธาตุ | guard_basic · ม่านน้ำ |
| **reflect** | คืน % ดาเมจที่ได้รับ (หลังกัน) กลับศัตรู · cap ซ่อน | โล่เงา · เกราะหนาม |
| **counter** | ถ้าโดนและยังมี HP → โต้กลับ 1 ครั้ง (power soft) | เกราะสวน · คมรอ |

**กฎ:**
- Reflect **ไม่** คริซ้อน · **ไม่** ติด status จาก reflect (anti loop)  
- Counter ใช้ **1 ครั้งต่อการตั้งท่า** · ศัตรูหลาย hit อาจ counter แค่ hit แรก  
- Rank สูง: reflect_pct / counter power สูง แต่ MP ตั้งท่าแพง + อาจ “แตก” ถ้าโดนเกินเกณฑ์  
- บอส phase ที่มี reflect อยู่แล้ว → อย่าซ้อน player reflect ให้ OP เกิน  

### 1.4 Buff — เพิ่มสถานะตัวเอง (และปัญหา “ร่ายพร้อมกัน”)

**ความเสี่ยงที่คุณชี้ถูกต้อง:**  
ถ้าผู้เล่นมี MP พอ + ร่าย buff หลายตัวต่อรอบ/ต่อคอมโบ → might+ward+focus+… = โกง

**กฎ anti multi-buff (ล็อกแนว):**

| กฎ | รายละเอียด |
|----|------------|
| **Buff budget / เทิร์น** | ร่าย buff ได้ **1 ครั้งต่อ action** (ไม่ใส่ในคอมโบยาวเป็น spree) |
| **Category exclusive** | กลุ่ม atk / def / tempo / resource — **กลุ่มละ 1 active** (might ทับ might, ห้าม might+berserk ซ้อนถ้าหมวดเดียวกัน) |
| **Soft diminishing** | บัฟชิ้นที่ 2–3 ในไฟต์เดียวกัน ผลลด (ซ่อน) |
| **Rank tax** | Rank S+ บัฟแรง แต่ **MP สูง + ระยะสั้น + charge** |
| **Combo gate** | คอมโบอนุญาต combat+combat · **buff ไม่ผสมคอมโบดาเมจ** (หรือได้แค่ท้ายโซ่ 1) |
| **Focus resource** | optional: ใช้สติ (`intelligence` current) เปิด buff ชั้นสูง |

ผลลัพธ์: ยังรู้สึกโหดถ้า build บัฟ + จังหวะดี แต่ไม่ “กด 5 บัฟแล้วลบแมพ”

---

## 2. Skill Rank — ออกแบบ

### 2.1 แถบ Rank (ผู้เล่นเห็น soft / ระบบเก็บ id)

| Rank id (ภายใน) | ป้ายผู้เล่น (soft) | ความหมายคร่าว |
|-----------------|-------------------|---------------|
| `N` | ธรรมดา | พื้นฐาน · MP ถูก · แรงพอใช้ |
| `H` | สูง | ชัดขึ้น · MP กลาง |
| `R` | หายาก | เด่น · ต้นทุนเริ่มเจ็บ |
| `S` | **S** | แรงชัด · MP/charge จริงจัง |
| `SS` | **SS** | โหด · ต้นทุนสูง / จำกัดครั้ง |
| `SSS` | **SSS** | เกือบโกง · **ภาษีหนัก** (ด้านล่าง) |

> หลีกเลี่ยงป้าย “F E D C B A” ปนกับกระดานภารกิจ F–SSS — ใช้ **N/H/R/S/SS/SSS** หรือ soft ไทยอย่างเดียวใน UI  
> ถ้าอยากโทนเกมเก่า: โชว์แค่「ลูกไฟ · แรงรู้สึก: ธรรมดา/คม/ดุ」ไม่โชว์ตัวอักษร rank ดิบทุกจอ

**ตัวอย่าง:** `fire_ball`  
- Rank N: ลูกไฟ · รู้สึกอุ่น  
- Rank R: ลูกไฟ · รู้สึกร้อนจัด  
- Rank SSS: ลูกไฟ · ท้องฟ้าร้อน — แต่ MP โหด / ใช้ได้น้อย

### 2.2 Rank กระทบอะไร (ซ่อนตัวเลข)

| มิติ | N → SSS (แนว) |
|------|----------------|
| power / heal | ↑ |
| status chance / duration | ↑ เบา |
| reflect_pct / counter | ↑ เบา |
| **cost_mana** | ↑↑ (โค้งชันหลัง S) |
| **charge / cooldown soft** | จำกัดขึ้นหลัง SS |
| learn / upgrade ต้นทุน | ↑ |
| ล้มเหลวอัป rank | โอกาสพลาด soft (คล้ายอัปเกียร์) |

**SSS ตั้งแต่ต้นเกม (โชค):** อนุญาตได้ แต่บังคับอย่างน้อย 2 จาก 3:
1. MP แพงมาก (อาจ > max_mana เริ่ม → ใช้ไม่ได้จนกว่าลงแต้ม/เลเวล)  
2. `charge.mode: fixed` ใช้ได้น้อย แล้วเติมยาก  
3. Soft drawback: หิว/ล้า/ขวัญ หรือ self_chip เมื่อร่าย  

→ “แทบโกง” แต่**เปิดไม่ทัน/ใช้ไม่บ่อย** = fantasy jackpot ที่ไม่พัง early forever

### 2.3 เก็บข้อมูล (instance ต่อสกิล)

```yaml
# บน player (แนว)
skill_ranks:
  fire_ball: S          # rank ปัจจุบัน
skill_rank_xp:          # ซ่อน — ไม่โชว์
  fire_ball: 0
# หรือ instance ถ้าอนาคตสกิลเป็นชิ้น:
# skill_instances: [{id: fire_ball, rank: S, uid: ...}]
```

Data skill base เก็บ `rank_default: N` · `rank_cap` (unit อาจถึง SSS ง่ายกว่า / joke ถึง SSS แต่ power แผ่วตาม HSR)

### 2.4 วิธีอัป Rank — **ผู้เล่นไม่รู้สูตร** (ออกแบบระบบ)

ช่องทางซ่อน (หลายทาง · ไม่บอกใน UI ตรงๆ):

| ช่อง (ซ่อน) | แนวคิด | soft ใบ้ |
|------------|--------|----------|
| **A. ใช้จริง** | ร่ายสกิลในไฟต์สะสม mastery ซ่อน | 「ท่านี้คุ้นมือขึ้น」 |
| **B. ชนะใต้เงื่อนไข** | ชนะมอนธาตุตรง / elite / บอสด้วยสกิลนั้น | 「เปลวตอบสนอง」 |
| **C. ครู/อาจารย์** | master สอน “ลึก” โอกาสอัปรูปแบบ | เมนูอาจารย์มีทางเลือกลึกลับ |
| **D. ไอเทมหายาก** | scroll / essence ธาตุ · ไม่การันตี | ของชื่อคลุมเครือ |
| **E. หีบ / เควส** | reward rank-up token soft | เควสไม่บอกว่าเป็น rank |
| **F. โชคแรกพบ** | ตอนเรียนครั้งแรก roll rank (N บ่อย · SSS หายากมาก) | 「ได้ท่าที่… หนักมือผิดปกติ」 |
| **G. Unit / path** | อาชีพลับ/สไตล์ตรง เร่ง mastery บางสาย | soft เข้าทาง |

**อัปไม่การันตี:** คล้ายอัปเกียร์ — สำเร็จ / คงที่ / (SS→SSS) เสี่ยง soft ล้ม  
**ห้ามเมนู “อัป rank ตรงๆ + %”**

### 2.5 UI soft (anti-spoiler)

- เมนูสกิล: ชื่อ · รู้สึกแรง (`ธรรมดา` / `คม` / `ดุ` / `น่ากลัว`) · MP soft  
- **ไม่โชว์** rank letter ทุกจอถ้า immersion ต้องการ — หรือโชว์แค่ S+ เป็นสัญลักษณ์ ◆◆◆  
- ตอนอัป: 「ท่านี้… เปลี่ยนโทน」ไม่ใช่「F→E 55%」

---

## 3. ผลกระทบระบบอื่น

| ระบบ | ผลกระทบ |
|------|---------|
| **Combo** | combat เท่านั้นในโซ่หลัก · debuff ได้ท้ายโซ่ 1 (optional) · buff แยกรอบ |
| **ATB / สติ** | buff แรง / rank S+ อาจกินสติ |
| **Unit HSR** | rank สูง × style match = โหด · mismatch = แผ่วแม้ SSS |
| **มอน MI** | debuff ใส่ elite ยาก · หนี/เลือกท่าตอบ |
| **Economy** | essence rank-up = sink · master lease คู่ rank |
| **Save** | `skill_ranks` + hidden xp |

---

## 4. ความเสี่ยงและ mitigation

| ความเสี่ยง | แก้ |
|------------|-----|
| Buff stacking OP | budget 1/turn · category exclusive · diminishing |
| SSS early | MP/charge/self cost gate |
| Debuff lock boss | resist + duration cap + boss cleanse phase |
| Reflect loop | no status on reflect · cap · 1 counter |
| Rank grind toxic | multi-path ซ่อน · ไม่ต้องฟาร์มอย่างเดียว · soft ceiling ต่อเลเวล |
| UI รก | soft band · ไม่ dump ตัวเลข |

---

## 5. แผนเฟสพัฒนา (SK-R)

> แบ่งเฟส · เทสได้ทุกระยะ · **ห้าม implement rank+slot+content ทั้งก้อนทีเดียว**

| เฟส | ชื่อ | งานหลัก | เกณฑ์จบ | พึ่งพา |
|-----|------|---------|---------|--------|
| **SK-R0** | กฎ + schema | doc นี้ · `slot` enum · `skill_rank` schema · soft labels | schema ล็อกใน doc + test fixture | — |
| **SK-R1** | Slot แยก logic | engine: buff/debuff/defense subtype · migrate tag เบา | ร่าย heal≠buff stack rule · defense reflect stub | status_fx |
| **SK-R2** | Rank runtime | `skill_ranks` บน player · scale power/MP · roll ตอนเรียน | เรียน fire_ball ได้ rank ต่าง · SSS แพง MP | SK-R0 |
| **SK-R3** | อัป rank ซ่อน | mastery จากใช้สกิล · soft note · ล้ม/สำเร็จ soft | ใช้บ่อยมี chance อัป · ไม่มีเมนู % | SK-R2 |
| **SK-R4** | เนื้อหา debuff/buff/reflect | 2–4 สกิล/สาย · tree node เบา · YAML | ไฟต์รู้สึกมี DoT/บัฟ/สะท้อน | SK-R1–3 |
| **SK-R5** | อาจารย์ · ไอเทม · sink | essence · master deep teach · chest noise | sink ทำงาน · playtest | SK-R3–4 |
| **SK-R6** | บาลานซ์ + Unit/HSR | cap combo+buff · unit rank · dashboard | ไม่พัง early · smoke tests | playtest |

**ลำดับแนะนำกับ solo ปัจจุบัน:**  
`SK-R0 → R1 → R2 → R3` (ระบบ) แล้ว `R4` เนื้อหาทีละ pack · `R5–R6` ปิด  

**อย่าทำพร้อม:** W4 online · dump ร้อยสกิล rank ทุกตัว  

### 5.1 แพ็กเนื้อหา R4 (ตัวอย่างแบ่ง)

| pack | สาย | เพิ่ม |
|------|-----|------|
| A | mage/rogue | debuff burn/poison 2 · buff focus 1 |
| B | warrior | counter + reflect เบา 2 |
| C | priest/archer | support cleanse แยก · debuff slow soft |
| D | unit | rank_default ต่างกันตาม joke/OP |

---

## 6. Schema ร่าง (data)

```yaml
# skills.yaml (ขยาย)
- id: fire_ball
  slot: combat          # combat | debuff | buff | defense | support
  defense_mode: null    # guard | reflect | counter (defense only)
  elements: [fire]
  power: 28
  cost_mana: 12
  rank_default: N
  rank_cap: SS          # SSS เฉพาะโชค/unit/event
  rank_curve: fire_std  # ตาราง scale ใน rules
  apply_status:         # debuff/combat optional
    id: burn
    chance: 0.22        # ซ่อนจาก UI
  buff_status: might    # buff slot
  buff_category: atk    # exclusive group
  reflect_pct: 0.0
  counter_power: 0
```

```yaml
# data/skills/rank_rules.yaml (ใหม่ R0–R2)
ranks: [N, H, R, S, SS, SSS]
soft_label:
  N: ธรรมดา
  H: สูง
  R: หายาก
  S: S
  SS: SS
  SSS: SSS
power_mult:  [1.00, 1.08, 1.18, 1.32, 1.50, 1.72]
mana_mult:   [1.00, 1.10, 1.25, 1.48, 1.85, 2.40]
# SSS เพิ่ม charge บังคับถ้า roll ตอน level 1–5
early_sss_tax:
  max_level: 5
  force_charge_max: 3
  mana_mult_extra: 1.35
```

---

## 7. เกณฑ์สำเร็จผลิตภัณฑ์

- ผู้เล่นแยกบทบาทสกิลได้: ตี / ติดสถานะ / บัฟตัว / กัน·สะท้อน·สวน / ฮีล  
- Rank ทำให้ `fire_ball` คนละตัวรู้สึกคนละน้ำหนัก โดย**ไม่โชว์สูตร**  
- SSS โชคยังสนุก แต่ early ไม่ลบเกม  
- Buff ซ้อนไม่พัง · Debuff ไม่ล็อกบอสตายตัว  
- เทส unit: scale rank · tax SSS · buff exclusive · reflect no-loop  

---

## 8. คิว implement ถัดไป (เมื่อเริ่มโค้ด)

1. **SK-R0** ล็อก schema + `rank_rules.yaml` + อัป `SKILL_SYSTEM.md`  
2. **SK-R1** `skill_slots` resolve ใน combat_session / guard  
3. **SK-R2** rank บน player + scale  
4. เทส `tests/unit/test_skill_rank_r2.py`  
5. ยังไม่ bulk เนื้อหาจนกว่า R2–R3 นิ่ง  

---

*เอกสารนี้เป็นแผนออกแบบ — ยังไม่ bump APP_VERSION จนกว่าจะ ship เฟสแรก*
