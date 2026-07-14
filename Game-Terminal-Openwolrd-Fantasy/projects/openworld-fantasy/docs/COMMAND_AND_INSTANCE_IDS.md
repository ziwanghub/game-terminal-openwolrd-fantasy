# ระบบคำสั่งแบบ Prefix + รหัส Instance / เจ้าของ

**สถานะ:** Design v1 + **implement บางส่วน 1.11.0** (`commands.py` · `item_instances.py` · sight handles)  
**แรงจูงใจ:** ป้องกันระบบและผู้เล่นสับสนระหว่าง *ชนิดของ* · *ชิ้นที่มีเจ้าของ* · *แอคชัน*  
**อ้างอิง play:** `sw001` ดาบเหล็ก · กระเป๋า hub · สนาม sights หลายเป้า  

---

## 1. ปัญหาปัจจุบัน

| อาการ | ทำไมงง |
|--------|--------|
| พิมพ์ `sw001` | หมายถึง *ชนิดดาบ* หรือ *ชิ้นที่สวมอยู่* หรือ *ชิ้นในคลัง*? |
| เลข `1` | เมนูกระเป๋า / เป้าสายตา / ตัวเลือกไฟต์ ซ้อนกันตาม context |
| หลายมอนในสายตา | `3` แล้ว `2` จำลำดับ — สลับรอบแล้วเป้าเลื่อน |
| อัปเกรด | ช่อง `weapon` กับรหัสดาบคนละชั้นความหมาย |
| หลายผู้เล่น / trade (อนาคต) | ดาบเหล็กเหมือนกัน แยกเจ้าของไม่ได้ |

**หลักที่ผู้ใช้เสนอ (ยอมรับเป็นแกนออกแบบ):**

1. **คำสั่ง = prefix + รหัส** เช่น `f`+รหัสมอน · `upgrade_`+รหัสดาบ  
2. **ชนิด ≠ ชิ้นที่มีเจ้าของ**  
   - `sw001` = แบบ/เทมเพลต ดาบเหล็ก (ยังไม่ผูกใคร)  
   - `sw001_<ownerId>` หรือ instance เต็ม = ดาบของใคร + สถานะสวม/คลัง  

พิมพ์ยาวขึ้นนิดหน่อย แลกกับ **parser ไม่เดา context ผิด**

---

## 2. โมเดลรหัส 3 ชั้น

```text
┌─────────────────────────────────────────────────────────┐
│  L1 TEMPLATE (ชนิดของ)                                   │
│  sw001 · ar001 · mn_wolf · pt_hp                         │
│  = นิยามใน data · ไม่มีเจ้าของ · ใช้ในร้าน/คราฟ/ดรอป table   │
└───────────────────────────┬─────────────────────────────┘
                            │ spawn / ซื้อ / ดรอป
                            ▼
┌─────────────────────────────────────────────────────────┐
│  L2 INSTANCE (ชิ้นของจริงในโลก)                            │
│  i_a7f3c2  หรือ  sw001#a7f3c2                            │
│  เก็บ: template, rarity, upgrade, sockets, bound flags   │
└───────────────────────────┬─────────────────────────────┘
                            │ own / equip / trade
                            ▼
┌─────────────────────────────────────────────────────────┐
│  L3 BINDING (ความสัมพันธ์กับตัวละคร)                       │
│  owner_id · location: bag | equip:weapon | ground | mail │
│  แสดงสั้น: sw001_u9k2  (= template + owner short)        │
└─────────────────────────────────────────────────────────┘
```

### 2.1 กฎความหมาย (สำคัญ)

| รหัสที่ผู้เล่นเห็น | ความหมาย | ใช้ทำอะไรได้ |
|-------------------|----------|----------------|
| **`sw001`** | ชนิดดาบเหล็กเท่านั้น | ดู data ทั่วไป · ร้านโชว์สินค้า · คราฟ recipe · *ไม่* ถอด/อัป/ขายชิ้นจริง |
| **`sw001_u9k2`** | ชิ้นที่ผูก owner `u9k2` (ย่อ) | รู้ว่าของใคร · ถ้า owner = ตัวเอง → จัดการได้ |
| **`sw001#a7f3`** | instance เต็ม (แนะนำใน UI ละเอียด) | แยกดาบเหล็ก 2 เล่มของคนเดียวกัน (rarity/อัปต่างกัน) |
| **`@self.sw001`** | shortcut: ชิ้นของฉันที่เป็น template นี้ (ถ้ามีชิ้นเดียว) | สะดวก · ถ้ามีหลายชิ้นระบบถามให้ระบุ `#…` |

**ข้อเสนอผู้ใช้ `sw001_id_user`:** ใช้รูปแบบมาตรฐาน

```text
{template}_{ownerShort}           # sw001_u9k2
{template}_{ownerShort}#{inst}    # sw001_u9k2#a7f3   เมื่อมีหลายเล่ม
```

- `ownerShort` = 6 ตัวอักษรจาก `player.id` (หรือ hash)  
- ถ้ายังไม่มี owner (บนพื้น / ในหีบยังไม่ claim): แสดงแค่ `sw001#a7f3` หรือ `sw001@ground`

### 2.2 แสดงผลที่แนะนำ

**ชนิด (ร้าน / สารานุกรม):**
```text
sw001  ดาบเหล็ก  [○] ธรรมดา   ← ยังไม่ใช่ของใคร
```

**ชิ้นของฉันที่สวม:**
```text
อาวุธ: sw001_u9k2#a7f3  ดาบเหล็ก [○] ธรรมดา  · สวมอยู่
```

**ชิ้นในคลัง (ยังไม่สวม):**
```text
1. sw001_u9k2#b91c  ดาบเหล็ก [✦] ตำนาน  · ในกระเป๋า
```

**ของคนอื่น (ดูอย่างเดียว / trade):**
```text
sw001_v3xm#c012  ดาบเหล็ก · เจ้าของ: อัศวินเมฆ (ไม่ใช่ของคุณ)
```

ผู้เล่น **อ่านได้ทันที**: มี `_owner` = มีเจ้าของ · ไม่มี = แค่ชนิดหรือยังไม่ผูก

---

## 3. ไวยากรณ์คำสั่ง (Command Grammar)

### 3.1 รูปแบบสากล

```text
<verb>_<target>
<verb> <target>          # อนุญาตช่องว่างถ้า parser ชัด
<verb><target>           # แบบสั้นเฉพาะ verb 1 ตัวอักษร: f, t, x
```

**กฎ parse:**

1. แยก `verb` จากตารางคำสั่งที่ลงทะเบียน (ยาวก่อนสั้น — `upgrade` ก่อน `u`)  
2. ส่วนที่เหลือ = `target` (รหัส entity)  
3. ถ้าว่างหรือไม่รู้จัก → soft error + ใบ้ตัวอย่าง  
4. **ห้าม** ใช้เลขล้วนเป็น target หลักในโหมด multi-entity (ยกเว้นเมนู wizard ที่ lock context)

### 3.2 ตาราง Verb (สนาม + กระเป๋า + ไฟต์)

| Verb | ชื่อเต็ม (พิมพ์ได้) | สั้น | เป้า | ตัวอย่าง |
|------|---------------------|-----|------|----------|
| **fight** | `f_` / `fight_` | `f` | มอนสเตอร์ในสายตา | `f_mn02` · `fmn02` |
| **talk** | `talk_` | `t` | NPC / ผู้เล่น | `t_np01` |
| **open** | `open_` | `o` | หีบ | `o_ch01` |
| **inspect** | `inspect_` / `i_` | `i` | ใดๆ | `i_sw001_u9k2` |
| **equip** | `equip_` | — | instance ของฉัน | `equip_sw001_u9k2#a7f3` |
| **unequip** | `unequip_` | — | instance ที่สวม | `unequip_sw001_u9k2#a7f3` |
| **upgrade** | `upgrade_` | — | instance ที่สวม/คลัง | `upgrade_sw001_u9k2#a7f3` |
| **sell** | `sell_` | — | instance ของฉัน | `sell_sw001_u9k2#b91c` |
| **drop** | `drop_` / `discard_` | — | instance | `drop_sw001_u9k2#b91c` |
| **use** | `use_` | — | consumable instance/stack | `use_pt_hp` |
| **socket** | `socket_` | — | card + gear (2 เป้า) | `socket_cd_fire>sw001_…` |
| **go** | `go_` | — | area id | `go_dark_forest` (อนาคต) |

**เมนูเลข 0–9 คงไว้** สำหรับมือใหม่ / ทางลัด context-bound  
**Prefix command** สำหรับกรณี dual-target, multi-mob, automation, co-op

### 3.3 ตัวอย่างสายตาสนาม (หลายเป้า — แก้ความงง)

**เดิม (งง):**
```text
1. [chest] หีบ
2. [monster] ???
3. [monster] ???
เลือก: 3 → 2   # เข้าหา แล้วเลขในเมนูย่อย?
```

**ใหม่:**
```text
── สิ่งที่สังเกต ──
  ch01  [หีบ] หีบเก่า — อุ่นผิดปกติ
  mn02  [มอน] เงาร่าง A  เสี่ยง:?
  mn03  [มอน] เงาร่าง B  เสี่ยง:?

คำสั่ง: f_mn02 | o_ch01 | i_mn03 | หรือเมนู 3 แบบเดิม
เลือก: f_mn02
→ เข้าสู้กับเป้า mn02 โดยไม่สลับกับ mn03
```

รหัส `mn02` **ผูกกับ entity ใน sights รอบนี้** (รีเซ็ตเมื่อสำรวจใหม่ / เปลี่ยนพื้นที่) — เป็น *session handle* ไม่ใช่ species id ถาวร  
Species ภายใน: `wolf` · แสดง: `mn02 · ???` จนกว่าจะรู้จัก

### 3.4 ตัวอย่างอัปเกรด / ถอด

```text
upgrade_sw001_u9k2#a7f3
→ ชัดว่าอัป “เล่มนี้” ของฉัน ไม่ใช่ template sw001 ทั้งเซิร์ฟ

unequip_sw001_u9k2#a7f3
→ ถอดเล่มที่สวม ถ้า # ไม่ตรงของที่สวม → error ชัด

inspect_sw001
→ เปิดสารานุกรมชนิด (ไม่มีปุ่มถอด/ขาย)

inspect_sw001_u9k2#a7f3
→ เปิดแผงชิ้นจริง + เมนูจัดการ (ถ้า owner = self)
```

---

## 4. กรรมสิทธิ์และสิทธิ์ (AuthZ เบา)

```text
can(player, verb, target):
  template only     → inspect_public เท่านั้น
  instance.owner == player.id → full bag verbs
  instance.owner != player    → inspect_other (ไม่มี ถอด/อัป/ขาย/ทิ้ง)
  sight handle mn##           → f/i เฉพาะรอบที่ handle ยัง valid
  ground loot                 → take_ หลัง claim
```

**Soft UI:** ถ้าพิมพ์ `upgrade_sw001` (ไม่มี owner/instance):

```text
sw001 คือชนิดของ — ยังไม่ชี้ชิ้นจริง
 ของคุณที่ตรงชนิด:
  1. sw001_u9k2#a7f3  [สวม] ธรรมดา +0
  2. sw001_u9k2#b91c  [คลัง] ตำนาน +2
พิมพ์: upgrade_sw001_u9k2#a7f3
```

ระบบ **ไม่เดา** เล่มแรกเงียบๆ

---

## 5. โครงสร้างข้อมูล (สำหรับ implement)

### 5.1 Template (มีแล้ว + ขยาย)

```yaml
# items.yaml
- id: iron_sword
  code: sw001          # L1 public template code
  kind: equipment
  ...
```

### 5.2 Instance (ใหม่ — inventory เก็บ list of objects)

```json
{
  "inst_id": "a7f3c2",
  "template_id": "iron_sword",
  "code": "sw001",
  "owner_id": "player_uuid_…",
  "rarity": "common",
  "upgrade": 0,
  "sockets": [null],
  "bound": false,
  "location": "equip:weapon"
}
```

**Migration จาก list ขนานปัจจุบัน:**

| เดิม | ใหม่ |
|------|------|
| `inventory_ids[]` | `inventory_items[]` ของ instance |
| `inventory_rarities[]` | field ใน instance |
| `equip_ids.weapon = "iron_sword"` | `equip.weapon = inst_id` + instance store |
| `equip_rarities` | ใน instance |

แสดงผลยัง derive: `format_ref(inst) → "sw001_u9k2#a7f3"`

### 5.3 Sight handles (สนาม)

```json
{
  "handle": "mn02",
  "kind": "monster",
  "ref": "encounter_token_…",
  "expires_turn": 12
}
```

---

## 6. Parser pipeline

```text
raw input
  → trim / lower
  → if in {0-9, S, P, K, …} and length≤2 → legacy menu key
  → match longest verb prefix from registry
  → target = remainder (strip leading _ )
  → resolve target:
       sight_handle? → entity
       instance_ref? → item instance
       template_code? → template (verbs จำกัด)
       area / npc code?
  → authz
  → execute verb handler
  → soft error with examples
```

**Verb registry ไฟล์เดียว** (`data/commands/verbs.yaml` หรือ hardcode เฟสแรก):

```yaml
verbs:
  - id: fight
    prefixes: ["f_", "f", "fight_"]
    target: sight_monster
  - id: upgrade
    prefixes: ["upgrade_"]
    target: item_instance_self
  - id: inspect
    prefixes: ["i_", "inspect_", "i"]
    target: any
```

---

## 7. UX ข้อความ (หลักการ)

1. **Template เรียบ · Instance บอกเจ้าของ**  
2. **Legend คงที่** ใต้กระเป๋า: `_xxxx` = เจ้าของ · `#yyyy` = ชิ้นย่อย  
3. **เมนูเลขไม่ทิ้ง** — prefix เป็นช่องทาง “ไม่สับสน”  
4. **พิมพ์ยาวได้ ถูกชัวร์** ดีกว่าพิมพ์สั้นแล้วระบบเดาผิด  
5. **Error สอน:** บอกว่าขาดอะไร (`#instance` / owner) ไม่ใช่แค่ “นอกช่วง”

### Wireframe กระเป๋า (เป้าหมาย)

```text
── กระเป๋า ──
 สวมอยู่:
   อาวุธ: sw001_u9k2#a7f3  ดาบเหล็ก [○] ธรรมดา
          ↑template ↑owner ↑ชิ้น
  ชนิดอย่างเดียว (sw001) = ยังไม่ใช่ของใคร — ใช้อัป/ถอดไม่ได้

คำสั่งตัวอย่าง:
  i_sw001_u9k2#a7f3     ดูชิ้นนี้
  upgrade_sw001_u9k2#a7f3
  unequip_sw001_u9k2#a7f3
  sell_sw001_u9k2#a7f3
```

### Wireframe ไฟต์หลายตัว

```text
  mn02 หมาป่า  HP ██░░
  mn03 หมาป่า  HP ████
คำสั่ง: f_mn02 / skill_slash>mn03 / เมนู 1 โจมตีแล้วเลือกเป้า
```

---

## 8. ขอบเขตที่ไม่ทำในดีไซน์นี้

- PvP แย่งของ / steal verb (ไว้เฟส social)  
- Economy audit log เต็มรูปแบบ  
- GUI drag-drop  
- LLM แปลงภาษาธรรมชาติ → command (เฟส V ทีหลัง — map ลง grammar นี้ได้)

---

## 9. แผน implement (PR แยก)

| ขั้น | งาน | เสี่ยง |
|------|-----|--------|
| **A** | Verb registry + parser กลาง (`game/domain/commands.py`) · เมนูเลขยังทำงาน | ต่ำ |
| **B** | Sight handles `mn##` / `ch##` · `f_` `o_` `t_` ใน field | กลาง |
| **C** | Instance model ขนาน inventory (migrate save) · แสดง `sw001_owner#inst` | กลาง–สูง |
| **D** | bag verbs: `upgrade_` `unequip_` `sell_` `drop_` `equip_` | กลาง |
| **E** | ปฏิเสธ verb บน template-only + ใบ้รายการ instance ของผู้เล่น | ต่ำ |
| **F** | เทส ScriptedIO + docs UIUX/BAG | ต่ำ |

** sav compatibility:** โหลดเซฟเก่า → generate `inst_id` + `owner_id` จาก player ตอน sanitize  

---

## 10. ตัวอย่างจับคู่ความเข้าใจผู้ใช้

| ผู้ใช้คิด | ระบบตีความ |
|-----------|------------|
| `sw001` | ดาบเหล็ก *ชนิด* — ไม่มีเจ้าของ |
| `sw001_u9k2` | ดาบเหล็กของ user สั้น u9k2 (ถ้าชิ้นเดียว) |
| `sw001_u9k2#a7f3` | เล่มเฉพาะ · รู้ว่าใครถือ/สวมจาก `location` |
| `f_mn02` | ไฟต์มอน handle 02 ในสายตานี้ |
| `upgrade_sw001` | **ไม่รัน** — ใบ้ให้ใส่ instance |
| `upgrade_sw001_u9k2#a7f3` | อัปเล่มนั้น ถ้าเป็นของฉันและเงื่อนไขครบ |

---

## 11. สรุปตัดสินใจออกแบบ

1. แยก **Template / Instance / Binding** ชัด  
2. คำสั่ง **verb + target** เป็น primary สำหรับ multi-entity และ gear manage  
3. เมนูเลขเป็น secondary / onboarding  
4. รหัสที่ “มี `_owner`” = มีเจ้าของ; ล้วนๆ `sw001` = ชนิด  
5. ระบบ **ไม่ auto-pick** เมื่อกำกวม — ถามหรือ list ตัวเลือก  

**ขั้นถัดไปเมื่ออนุมัติ:** เริ่ม **ขั้น A+B** (parser + sight handles) โดยยังไม่พัง inventory เดิม แล้วค่อย **C** instance migrate  

---

*เอกสารนี้สะท้อนข้อเสนอ: `f`+รหัสมอน · `upgrade_`+รหัสดาบ · `sw001` vs `sw001_owner` — ขยายเป็น grammar ทั้งเกม*
