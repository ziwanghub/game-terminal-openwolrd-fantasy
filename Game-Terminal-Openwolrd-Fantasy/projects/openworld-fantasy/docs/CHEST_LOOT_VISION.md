# วิสัยทัศน์: หีบรางวัลหลายระดับ · Unit unique · ดรอปไร้รูปแบบคาดเดา

**สถานะ:** **L0–L5 implement แล้ว** (`1.22.0-alpha` L5 bag UX · L0–L4 ตั้งแต่ 1.14)  
**เกมอ้างอิง:** `1.22.0-alpha` (`solo-k3-l5`)  
**แผนรวม:** [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md) · [`ROADMAP.md`](ROADMAP.md)  
**โค้ด:** `game/domain/chest_loot.py` · `data/chests/` · เควส/กระดาน reward · unit claims  
**เกี่ยวข้อง:** [`RARITY.md`](RARITY.md) · soft / anti-spoiler · บอส · เควส · unit

---

## 0. เป้าหมายหนึ่งประโยค

มี**หีบรางวัล**หลายแรงก์ (ธรรมดา → SSS) และ**หีบ unit** ที่ให้ของเฉพาะตัวละคร/unit  
แหล่งได้ (บอส เควส ฯลฯ) ใช้ logic **ไร้รูปแบบตายตัว** — ผู้เล่นเดา “ฟาร์มตรงไหนแน่นอน” ไม่ได้  
ของในหีบสุ่มตามแรงก์หีบ แต่**หีบสูงก็ยังมีโอกาสได้ของทั่วไป** (โอกาสดีขึ้น ไม่การันตี)

---

## 1. หลักการออกแบบ (ล็อก)

| # | หลัก | ความหมาย |
|---|------|----------|
| C-P1 | **หีบ ≠ ไอเทมสำเร็จรูป** | ได้ “กล่อง” ก่อน แล้วเปิด (หรือ auto-open แบบ soft) |
| C-P2 | **แรงก์หีบ ≠ การันตีของใน** | SSS แค่**ตารางโอกาสดีขึ้น** ยังดรอป common ได้ |
| C-P3 | **Unit unique = ชิ้นเดียวในโลก/เซฟ** | flag ครอบครอง · ดรอปซ้ำไม่ได้ (หรือได้เศษแทน) |
| C-P4 | **Anti-spoiler แหล่ง** | ไม่บอก “บอส X = หีบ SS” ใน UI · เห็นแค่ flavor |
| C-P5 | **ไร้รูปแบบคาดเดา** | หลายชั้นสุ่ม + noise + เงื่อนไขซ่อน + anti-pity-public |
| C-P6 | **มอนธรรมดาหายากมาก** | ส่วนใหญ่ไม่ดรอปหีบ · บอส/เหตุการณ์พิเศษมีน้ำหนัก |
| C-P7 | **ผูก rarity เดิม** | ของในหีบใช้ tier ○◇◆★… ที่มีอยู่ |
| C-P8 | **Soft death / ไม่พังเซฟ** | หีบไม่หายเพราะตายง่ายเกิน (optional lock ถึงเมือง) |

---

## 2. ระดับหีบ (Chest rank)

แมปกับภาษาผู้เล่น + ภายใน:

| แรงก์หีบ (UI soft) | id ภายใน | สัญลักษณ์แนะนำ | น้ำหนักตาราง “ดี” |
|--------------------|----------|----------------|-------------------|
| **ธรรมดา** | `chest_common` | □ / กล่องไม้ | ต่ำ |
| **สูง** | `chest_uncommon` | ▢ กล่องเหล็ก | ปานกลาง |
| **หายาก** | `chest_rare` | ■ กล่องเงิน | สูงขึ้น |
| **S** | `chest_s` | ◆ กล่องทอง | สูง |
| **SS** | `chest_ss` | ★ กล่องผลึก | สูงมาก |
| **SSS** | `chest_sss` | ✦ กล่องสุญญะ | สูงสุด (ยังไม่การันตี) |
| **Unit** | `chest_unit` | ◈ หีบพันธะ | **ของ unit เท่านั้น** (กฎพิเศษ) |

**หมายเหตุ:** S/SS/SSS **ไม่** เท่ากับ sacred/legendary ของ rarity อุปกรณ์แบบ 1:1  
หีบคือ “ซองสุ่ม” · ของข้างในยังมี rarity ของตัวเอง

### 2.1 แสดงผล soft

```text
คุณพบ「หีบ · หายาก」
 1 เปิดทันที  2 เก็บเข้าคลัง  0 ทิ้ง (soft confirm)
```

ไม่โชว์ % ดรอป · ไม่โชว์ “ตาราง SSS”

---

## 3. ของในหีบ — ตารางโอกาส (แนวคิด)

### 3.1 ชั้นสุ่ม 2 ชั้น

```text
ชั้น A: เลือก "bucket" ของรางวัล
  junk | material | consumable_food | consumable_heal | equipment | special | unit_unique

ชั้น B: เลือก item_id จาก bucket + roll rarity ของชิ้น
```

### 3.2 น้ำหนัก bucket ตามแรงก์หีบ (ตัวอย่าง — ซ่อนใน YAML)

| bucket | ธรรมดา | สูง | หายาก | S | SS | SSS |
|--------|-------:|----:|------:|--:|---:|----:|
| junk/mat ต่ำ | 45 | 30 | 18 | 12 | 8 | 5 |
| food / heal | 30 | 28 | 22 | 18 | 14 | 10 |
| equipment common–uncommon | 20 | 28 | 30 | 28 | 22 | 15 |
| equipment rare+ | 4 | 10 | 20 | 28 | 32 | 35 |
| special / key / thread | 1 | 3 | 7 | 10 | 14 | 18 |
| **empty soft** (ได้ของน้อยมาก) | 0 | 1 | 3 | 4 | 5 | 7 |

- SSS: โอกาส equipment rare+ **สูงขึ้น** แต่ยังมีแถว mat/food  
- “empty soft” = ได้ของถูกชิ้นเดียว + ข้อความ flavor ไม่ใช่กล่องว่างโหด

### 3.3 Rarity ของชิ้น (ชั้น B)

ใช้ `data/rarity/tiers.yaml` drop_weight **บิดด้วย chest_rank_bias**:

```text
effective_weight(tier) = base_drop_weight(tier) * chest_bias[chest_rank][tier]
```

| แรงก์หีบ | bias common | uncommon | rare | sacred+ |
|----------|------------:|---------:|-----:|--------:|
| ธรรมดา | 1.4 | 0.8 | 0.3 | 0.05 |
| สูง | 1.1 | 1.0 | 0.5 | 0.1 |
| หายาก | 0.9 | 1.1 | 0.9 | 0.25 |
| S | 0.7 | 1.0 | 1.2 | 0.5 |
| SS | 0.5 | 0.9 | 1.3 | 0.9 |
| SSS | 0.4 | 0.8 | 1.2 | 1.3 |

→ **SSS ยังออก ○ ธรรมดาได้** แค่ถี่น้อยลง

### 3.4 จำนวนชิ้นต่อหีบ

| แรงก์ | จำนวนม้วน (ซ่อน) |
|-------|------------------|
| ธรรมดา–สูง | 1 |
| หายาก–S | 1–2 (roll) |
| SS–SSS | 2–3 (roll) |
| Unit | 1 (unique) เสมอ |

---

## 4. หีบ Unit · ไอเทมชิ้นเดียวในระบบ

### 4.1 นิยาม

```yaml
# data/chests/unit_uniques.yaml (แผน)
- id: unit_blade_of_ash
  name: ดาบเถ้าพันธะ
  kind: equipment
  slot: weapon
  unique_scope: world   # world | save | account
  unit_bind: true       # ผูก unit_class / ธง unit
  chest_only: chest_unit
  # ไม่เข้าตารางหีบธรรมดา
```

| ขอบเขต unique | ความหมาย |
|---------------|----------|
| **save** | หนึ่งชิ้นต่อเซฟผู้เล่น |
| **world** | หนึ่งชิ้นต่อ `world_id` (ทุกเซฟในโลกร่วม) — หายากสุด |
| **account** | ทีหลัง online |

### 4.2 กฎดรอป

1. ตรวจ `unique_owned(world|save, item_id)`  
2. ถ้ามีแล้ว → **ไม่** roll ชิ้นนั้น · แทนด้วย `echo_shard` / วัสดุ / หีบต่ำกว่า  
3. ครั้งแรกได้ → ตั้ง flag · soft text  
   `「ของชิ้นนี้… เหมือนมีเพียงหนึ่งในเส้นทางนี้」`

### 4.3 หีบ unit มาจากไหน (anti-spoiler)

ไม่โชว์เงื่อนไข — ตัวอย่าง**ภายใน**:

| แหล่งซ่อน (logic) | soft ที่ผู้เล่นเห็น |
|-------------------|---------------------|
| เคลียร์บอส + unit ปลดแล้ว + luck noise | หีบพันธะผุดหลังเงาหาย |
| เควส campaign บทซ่อน | กล่องไม่มีป้าย |
| ช่วย H3 ครบ + อาหาร tier สูง (ผูก needs) | รางวัลเงียบ |
| หีบ SSS เปิดแล้ว roll bucket unit (หายากมาก) | ได้หีบ unit แทนของ |

ผู้เล่น**ไม่มีทางรู้สูตร** — แค่เล่นแล้วบังเอิญเจอ

---

## 5. แหล่งดรอปหีบ — ไร้รูปแบบคาดเดา

### 5.1 ชั้นตัดสิน “ได้หีบไหม” (ไม่ใช่ % คงที่)

```text
P(chest) = clamp(
    base_source
  * area_mood          # เปลี่ยนตาม time_units / mastery
  * player_noise       # hash(player_id, day_seed, kill_count) → 0.7–1.3
  * anti_farm          # ฆ่าซ้ำชนิดเดิมในหน้าต่างเวลา → ลด
  * pity_hidden        # เพิ่มช้ามากหลังแล้งนาน (ไม่โชว์, ไม่ reset ชัด)
  * quest_flag_boost   # ธงเควสซ่อน
  * boss_mult
)
```

**ห้าม** ตาราง “บอสป่า = 15% SS เสมอ” แบบ dig แล้ว farm

### 5.2 น้ำหนักแหล่ง (แนวทาง)

| แหล่ง | base ได้หีบ | แรงก์หีบที่โน้ม |
|--------|------------:|----------------|
| มอนธรรมดา | **~0–2%** (เกือบไม่ตก) | ธรรมดา–สูง ถ้าตก |
| มอน elite / ชื่อพิเศษ | ต่ำ–กลาง | สูง–หายาก |
| **บอสพื้นที่** | กลาง–สูง | หายาก–S (หาง SS) |
| **บอสดัน** | สูงกว่าบอสป่า | S–SS (หาง SSS) |
| หีบสนาม (sight chest) | กลาง | ตาม area |
| เควส/กระดาน รางวัล | กำหนดหรือ roll ซ่อน | ตามแรงก์เควส |
| เหตุการณ์โลก / rank | หายาก | สูง |
| ช่วยเหลือ / social | ต่ำมาก | special / unit ทางอ้อม |

### 5.3 มอนธรรมดา “อาจไม่ตกเลย”

```text
if mon.tier == normal:
    if rng() > very_low_threshold * noise:
        return no_chest
```

ส่วนใหญ่ loot เดิม (ยา/mat ตรงๆ) ยังมีได้ — **หีบ** หายาก

### 5.4 บอส

```text
roll_chest_rank(boss) ใช้ multi-die:
  d1 = threat / phase
  d2 = player luck_score (เล็ก)
  d3 = daily_seed xor boss_id
  d4 = first_clear_bonus (ครั้งแรกดีกว่า ซ่อน)
→ map เป็น chest_common … chest_sss
```

ครั้งแรกเคลียร์บอส: soft ข้อความดีขึ้น · โอกาสแรงก์สูงขึ้นเล็กน้อย  
เคลียร์ซ้ำ: ลด first_clear · anti_farm

### 5.5 เควส — ผู้เล่นไม่รู้ทางได้

| แบบ | ภายใน | ผู้เล่นเห็น |
|-----|--------|-------------|
| รางวัลหีบตรง | `reward_chest: chest_rare` | 「หีบปิดผนึก」 |
| ธงปลดตาราง | `flags.chest_table_void=1` | ไม่บอก |
| เงื่อนไข OR ซ่อน | kill+explore+help แบบ soft | ไม่ checklist |
| หีบ unit | เควสจบ + unit | ของผูกชะตา |

**Logic ไร้รูปแบบ:** ใช้ `seed = hash(world_id, quest_id, player_secret, week_bucket)`  
คนละเซปดาห์/คนละตัว โอกาสต่างกันเล็กน้อย — **ขุด wiki ยาก**

---

## 6. ขั้นตอน runtime (แผนโค้ด)

```text
1. kill / clear / quest complete
2. decide_chest_drop(source, ctx) → None | chest_rank
3. if chest: grant_chest_item หรือ open_now
4. open_chest(rank):
     for i in rolls:
       bucket = weighted(rank, noise)
       if bucket == unit_unique:
         pick unique available or fallback
       else:
         item = pick_from_pool(bucket, area)
         rarity = roll_rarity(rank bias)
       grant item
5. soft narrative lines
```

### 6.1 โครงสร้าง data (แผน)

```text
data/chests/
  ranks.yaml          # chest_common … chest_sss weights
  pools.yaml          # bucket → item_ids
  unit_uniques.yaml   # unique items + scope
  sources.yaml        # base rates by source type (ไม่โชว์ในเกม)
```

### 6.2 เซฟ

```text
player["chests_inventory"] = [{rank, sealed, source_soft}]  # optional เก็บก่อนเปิด
player["unique_owned"] = ["unit_blade_of_ash", ...]
world: saves/{world}/unique_claims.json   # ถ้า scope=world
```

---

## 7. UI/UX

### 7.1 ได้หีบ

```text
「เงาแตก — กล่องตกลงมา」
〔หีบ · S〕
 1 เปิด  2 เก็บ  0 ปล่อยไว้
```

### 7.2 เปิด

```text
เปิดหีบ…
 · เสบียงนักเดินทาง [○]
 · ดาบเหล็ก · สูง [◇]
「ยังไม่ใช่สิ่งที่เงาสัญญา — แต่ก็ใช้ได้」
```

SSS เปิดแล้วได้ของธรรมดา → flavor รับได้ ไม่โมโห:

```text
「กล่องใหญ่… ของข้างในเรียบง่าย — โชคยังไม่ถึง」
```

### 7.3 Unit

```text
「สิ่งนี้อยู่ในมือคุณเพียงหนึ่งเดียวบนเส้นทางนี้」
 (ไม่โชว์ unit id / เงื่อนไข)
```

### 7.4 กระเป๋า

หมวดใหม่ optional: **หีบ** (ยังไม่เปิด)  
หรือเก็บใน other จนกว่า implement

---

## 8. กำหนดไอเทม ↔ ระดับได้รับ (ตารางออกแบบ)

| กลุ่มของ | หีบที่**เข้า pool** | หมายเหตุ |
|----------|---------------------|----------|
| ยาเล็ก / ขนมปัง / mat ถูก | ทุกแรงก์ | หีบสูงยังออกได้ |
| ยา/เสบียง tier กลาง | สูง+ | |
| เกียร์ common–uncommon | ธรรมดา+ | |
| เกียร์ rare | หายาก+ (น้ำหนัก) | |
| ด้ายดัน / key shard | S+ หาง | |
| ของ sacred–legend | SS–SSS หางยาว | |
| **unit unique** | หีบ unit เท่านั้น | ชิ้นเดียว |

**โอกาส “ของดี”** = f(แรงก์หีบ) × noise — ไม่ใช่ if rank>=SS then legendary

---

## 9. แผนเฟส implement (L0–L4)

| เฟส | ชื่อ | ขอบเขต | สถานะ |
|-----|------|--------|--------|
| **L0** | Data skeleton | ranks.yaml · pools · unit_uniques โครง | **1.13.18** |
| **L1** | เปิดหีบ + ให้ของ | API open_chest · ใส่กระเป๋า · soft text | **1.13.18** |
| **L2** | ดรอปจากบอส/มอน | decide_chest_drop · anti_farm · noise | **1.13.18** |
| **L3** | เควส/กระดาน รางวัลหีบ | reward_chest · ธงซ่อน | **1.14.0** |
| **L4** | Unit unique + world claim | scope save/world · fallback shard | **1.14.0** |
| **L5** | เก็บหีบในคลัง · หมวดกระเป๋า | สรุปแรงก์ · เรียง · เปิดทั้งหมด A | **1.22.0** |

**ลำดับแนะนำ:** L0 → L1 → L2 (บอสก่อน) → L3 → L4  

อย่าเปิด SSS/unit ก่อนตาราง common นิ่ง

---

## 10. ความเสี่ยง

| ความเสี่ยง | กัน |
|------------|-----|
| ฟาร์มบอสวน | anti_farm + first_clear ซ่อน + noise รายวัน |
| SSS = ต้อง legendary | ตารางยังมี common · flavor รับได้ |
| unit ซ้ำ | unique_owned + world claim |
| ผู้เล่นงงหีบ | ข้อความ soft ชัด · เปิดง่าย 1 ปุ่ม |
| data บวม | pool อ้าง item id ที่มีอยู่ก่อน เพิ่มของใหม่ทีหลัง |

---

## 11. สิ่งของเดิมใช้ต่อ

| ของเดิม | ใช้ |
|---------|-----|
| `rarity` tiers + roll | rarity ในหีบ |
| boss kill / dungeon clear | L2 source |
| quests reward | L3 |
| unit_class / flags | L4 bind |
| soft / anti-spoiler | ทั้งระบบ |
| bag categories | L5 หมวดหีบ |

---

## 12. เกณฑ์พร้อมเริ่ม L0–L1

1. แคตตาล็อกไอเทมนิ่งพอ (มีแล้ว ~50)  
2. ตกลง 6+1 แรงก์หีบ (ธรรมดา…SSS + unit)  
3. ตกลง unique scope = save ก่อน (world ทีหลัง)  

---

## 13. Changelog

| วันที่ | |
|--------|--|
| 2026-07-14 | ออกแบบหีบหลายแรงก์ · unit unique · ดรอปไร้รูปแบบ · ตารางโอกาส · เฟส L0–L5 |
| 2026-07-14 | **L5:** คลังหีบในกระเป๋า — สรุปแรงก์ soft · เรียงสูงก่อน · เปิดทั้งหมด (A + confirm) |
