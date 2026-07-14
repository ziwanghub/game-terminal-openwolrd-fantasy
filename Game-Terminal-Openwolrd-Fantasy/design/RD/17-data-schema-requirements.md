# RD-17: Data & Save Schema Requirements

**สถานะ:** Draft  

---

## 1. วัตถุประสงค์

กำหนดว่าคอนเทนต์และเซฟ **แยกจากโค้ด** อย่างไร และฟิลด์ขั้นต่ำที่ต้องมี

## 2. หลักการ

| หลัก | ค่า |
|------|-----|
| ฟอร์แมตคอนเทนต์ | YAML (แนะนำ) |
| Validate | Schema ตอนโหลด (เช่น Pydantic) — พังตอนบูตไม่กลางเกม |
| เซฟผู้เล่น | JSON + `save_version` |
| Art | ไฟล์ข้อความ `.txt` อ้างด้วย `art_id` |
| id | snake_case ภาษาอังกฤษ; ชื่อแสดงผลแยก field `name` |

## 3. โครงสร้างโฟลเดอร์ data (เป้าหมาย)

```text
data/
  areas/
  monsters/
  skills/          # attack, support, defense
  items/
  cards/
  shops/
  elements/        # matchups, fusions
  encounters/      # approach, chest tables
  statuses/
  occupations/
  worlds/
  art/
    monsters/ items/ cards/ ui/
```

## 4. เอนทิตีขั้นต่ำ

### Area
`id, name, world_tier, unlock, connections[], spawn/monster_pools, ambient(regen), chest_table_ref`

### Monster
`id, name, level_range, pools tags, attack_profiles[], resists?, art_id, art_unknown_id, rarity`

### Skill
`id, name, slot(combat|support|defense), cost_mana, power?, elements[], applies_status[], combo tags, defense strong_vs/weak_vs (ถ้า defense)`

### Item / Equipment
`id, name, slot, stats, sockets, tags, rarity, art_id, spotlight_on_obtain?`

### Card
`id, name, compatible[], bonuses, grant_tags[], grant_skills[], art_id, rarity`

### Status
`id, name, duration, tick, modifiers, cleanse`

### Elements
matchups[], fusions[] — **ไม่โชว์ใน UI ตรงๆ**

### Encounter tables
weights → ambush | combat | friend | master | loot | trap

## 5. เซฟตัวละคร (ขั้นต่ำ)

```text
save_version, world_id, character_id
identity (name, occupation, zodiac, …)
level, xp_percent
vitals, stats, currencies
inventory, equipment, socketed_cards
skills[], statuses[]
area_mastery{}, location
knowledge { monsters, reactions, notes }
ui_prefs
disciple/blessings (ถ้ามี)
```

## 6. ข้อกำหนดคุณภาพข้อมูล

| ID | ข้อกำหนด |
|----|----------|
| DATA-01 | ทุก id อ้างอิงข้ามไฟล์ต้องมีอยู่จริง (validate) |
| DATA-02 | art_id ชี้ไฟล์ที่มีหรือมี fallback |
| DATA-03 | เซฟระบุ save_version เสมอ |
| DATA-04 | เปลี่ยน schema มี migrator หรือประกาศ breaking |
| DATA-05 | คอนเทนต์บาลานซ์อยู่ใน data ไม่ hardcode ใน UI |

## 7. นอกขอบเขต v1

- Mod marketplace  
- Binary packed assets บังคับ (ทำทีหลังได้ถ้าไฟล์เยอะ)  

## 8. ประวัติ

| วันที่ | หมายเหตุ |
|--------|----------|
| 2026-07-14 | Draft schema ระดับ requirement |
