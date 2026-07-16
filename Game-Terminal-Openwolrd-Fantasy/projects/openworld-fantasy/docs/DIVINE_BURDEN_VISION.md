# Divine Burden System — Vision & Rule Lock

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | [WO-023](WO_BACKLOG.md#wo-023-divine-burden-system--full-phase) |
| **สถานะเอกสาร** | **Implemented** เฟส 1–5 @ `1.68.0-alpha` |
| **เวอร์ชันฐาน** | `1.67.0-alpha` → ship `1.68.0-alpha` |
| **อัปเดต** | 2026-07-15 |
| **วัตถุประสงค์** | ของระดับสูงใช้ได้ แต่ต้องแลกภาระจิตใจ · มีห้องทดสอบปลอดภัย |

**เอกสารเกี่ยวข้อง:** [`NEEDS_PHASE1_DESIGN.md`](NEEDS_PHASE1_DESIGN.md) · [`EQUIP_LOADOUT_VISION.md`](EQUIP_LOADOUT_VISION.md) · [`ITEM_ECONOMY.md`](ITEM_ECONOMY.md) · [`WO_BACKLOG.md`](WO_BACKLOG.md)

---

## 0. เป้าหมายหนึ่งประโยค

ให้ **ของเทพมีราคา** — ผู้เล่นใส่ได้เสมอ แต่รู้สึก “ไม่ใช่ของเรา” ผ่าน **ขวัญ / soft flavor / drain เบา** และมี **Godforge Chamber** สำหรับลองของโดยไม่พังเซฟโลก

---

## 1. ชื่อระบบ (ล็อก)

| ชั้น | ชื่อ EN | ชื่อ soft ไทย | บทบาท |
|------|---------|---------------|--------|
| ระบบหลัก | **Divine Burden** | ภาระแห่งเรลิก | โทษเมื่อสวมของเกินความเหมาะสม |
| ออร่า | **Relic Aura** | ออร่าเรลิก | แผ่ผลต่อผู้ใกล้ / companion / echo |
| สถานที่ | **Godforge Chamber** | ห้องทดสอบเรลิก | sandbox ยืมของ · วัดพลัง/ภาระ |

**อย่าใช้ชื่อคลุมเครือ:** Legacy System, Bank, Artifact Shop (คนละเรื่อง)

---

## 2. หลักการออกแบบ (ล็อก)

| # | หลัก | ความหมาย |
|---|------|----------|
| **DB-P1** | ใส่ได้เสมอ | ไม่ hard gate · ไม่ “เลเวลไม่ถึงใส่ไม่ได้” |
| **DB-P2** | โทษหลัก = ขวัญ (Needs) | soft drain · soft label · ไม่โชว์ % สูตร |
| **DB-P3** | Soft ก่อนตัวเลข | flavor line · band ขวัญ · ไม่ DPS meter |
| **DB-P4** | ห้อง ≠ โลกจริง | ยืมของ · ออกแล้วคืน · ไม่ฟาร์มเงิน/ของจริง |
| **DB-P5** | Auto จัดการภาระได้ | ถอดเมื่อขวัญต่ำ · ไม่ auto-equip divine/legendary เกินตัว |
| **DB-P6** | ไม่ชน economy | ไม่เพิ่มธนาคาร/แลกสกุล · chamber ไม่เป็น gold farm |
| **DB-P7** | ทีละเฟส | 023.1 doc → 023.2 burden → 023.3 chamber → 023.4 aura → 023.5 content |
| **DB-P8** | Soft death เท่านั้น | ไม่ permadeath จาก burden |

---

## 3. ขอบเขต Burden vs Chamber vs Aura

```text
┌─────────────────────────────────────────────────────────┐
│  Divine Burden (ทุกที่ · ของจริงในเซฟ)                    │
│  สวม legendary+ เกิน appropriateness → drain ขวัญ/เบา MP │
└───────────────────────────┬─────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                                     ▼
┌─────────────────────┐              ┌─────────────────────┐
│ Relic Aura (ทีหลัง)  │              │ Godforge Chamber    │
│ companion / echo    │              │ sandbox ยืมเรลิก     │
│ soft social menu    │              │ วัดพลัง vs วัดภาระ   │
└─────────────────────┘              │ ออก = คืนของทั้งหมด │
                                     └─────────────────────┘
```

| คำถาม | คำตอบล็อก |
|--------|-----------|
| Burden เกิดที่ไหน? | **ทุกที่** เมื่อสวมของจริงที่ติด burden |
| Chamber ทำอะไร? | ลองของยืม + sparring · เปิด/ปิด burden ในห้องได้ |
| Aura เกิดเมื่อไหร่? | เฟส 023.4 — ผู้สวม burden สูงแผ่ soft ไป companion/echo |
| ของยืมออกห้องได้ไหม? | **ไม่ได้** — คืนทั้งหมด |

---

## 4. Rarity ที่เริ่มมี Burden

อ้างอิง `data/rarity/tiers.yaml`:

| rank | id | Burden เฟสแรก? | หมายเหตุ |
|-----:|----|:--------------:|----------|
| 1–3 | common–rare | ไม่ | ของใช้ทั่วไป |
| 4 | sacred | **เบา / optional** | ถ้า appropriateness ต่ำมากเท่านั้น (023.2 อาจข้าม) |
| 5 | **legendary** | **ใช่** | เริ่ม burden มาตรฐาน |
| 6+ | **divine / archdivine / mythic** | **ใช่ · แรงกว่า** | คอนเทนต์ยังบาง — เฟส 023.5 เติม |

**กฎ:** burden active เมื่อ  
`rarity_rank(item) >= LEGENDARY_RANK (5)`  
และ `appropriateness(player, item) < threshold` (soft ซ่อน)

---

## 5. ความเหมาะสม (Appropriateness) — soft ซ่อน

**ผู้เล่นไม่เห็นสูตร** — เห็นแค่ soft line / แถบขวัญ

ปัจจัยภายใน (ลำดับความสำคัญ):

1. **เลเวลตัวละคร** vs soft “น้ำหนักเรลิก” (rarity rank)  
2. **Latent / occupation soft** (มีอยู่แล้วใน progression)  
3. **Unit / class path affinity** (ถ้ามี)  
4. (ทีหลัง) heaven/hell affinity · rank soft · library

**ระดับ appropriateness ภายใน (ไม่โชว์ชื่อดิบ):**

| แบนด์ซ่อน | ความหมาย soft | โทษ |
|-----------|----------------|------|
| `fit` | มือคุ้น / ของรับเรา | ไม่ drain (หรือ flavor เบา) |
| `strain` | หนักมือ | drain ขวัญช้า |
| `crush` | เกินตัวชัด | drain ขวัญ + MP ช้า + combat soft โทษเล็ก |

**เฟส 023.2 ใช้สูตรง่าย (ล็อก implement):**

```text
burden_gap = rarity_rank - clamp(1 + level//5 + soft_affinity_bonus, 1, 8)
if gap <= 0 → fit
if gap == 1 → strain
if gap >= 2 → crush
```

(ตัวเลขจูนได้ใน balance helper — ไม่โชว์ผู้เล่น)

---

## 6. ระดับโทษ (เฟสแรก = ปานกลางค่อนเบา)

| แบนด์ | ขวัญ / ติก (field soft) | ระหว่างไฟต์ | combat soft |
|-------|-------------------------|-------------|-------------|
| fit | — | — | — |
| strain | morale −1 ทุก ~2–3 care tick | MP −1 ช้า ๆ (optional) | เล็กน้อย skill wobble ถ้าขวัญต่ำอยู่แล้ว |
| crush | morale −1~2 ต่อ care tick | MP −1~2 ช้า | ขวัญต่ำเร็ว → Auto ควรถอด |

**ห้ามเฟสแรก:** skill lock ถาวร · ห้ามถอด · ฆ่าอัตโนมัติ · ลบของ  

**ถอดของ:** drain หยุดทันที (เหลือขวัญที่ลดไปแล้ว — ฟื้นด้วย care ปกติ)

---

## 7. Soft flavor (ตัวอย่าง — ห้ามสูตร)

- 「ของนี้ร้อนมือ…」  
- 「ภาระแห่งเรลิกกดอก」  
- 「ลมจากดาบไม่ใช่ของคนธรรมดา」  
- 「จิตสั่น — ยังไม่ใช่เจ้าของที่แท้」  

Aura (023.4):  
- companion: 「เพื่อนสีหน้าเปลี่ยน…」  
- echo: 「ออร่าจากเงาคนแปลกหน้ากดขวัญ」  

---

## 8. Auto Policy (ล็อก)

| พฤติกรรม | กฎ |
|----------|-----|
| Auto-equip | **ไม่** auto-equip legendary+ ถ้าจะทำให้ strain/crush (default) |
| ขณะรัน auto | ถ้าขวัญ ≤ morale threshold (policy) **และ** สวม burden → **ถอด** ชิ้นที่ gap สูงสุด 1 ชิ้น/รอบ care |
| prefs | `auto_unequip_burden: true` (default) · `auto_equip_relics: false` (default) |
| thrift/safe | thrift ถอดเร็วขึ้น · safe ระวังขวัญมากกว่า |

---

## 9. Godforge Chamber — กฎ sandbox

| กฎ | รายละเอียด |
|----|------------|
| เข้า | เมือง soft / Personal hub / Test Run (God) |
| ของยืม | 2–4 เรลิกทดลอง (template chamber-only) |
| sparring | มอนจำลอง / dummy · soft death เบากว่าโลก |
| โหมด A | **วัดพลัง** — ปิด/ลด burden (จูนตัวเลข) |
| โหมด B | **วัดภาระ** — burden เต็มเหมือนโลก |
| ออก | คืนของยืม · ล้าง chamber flags · **ไม่** โอน rarity สูงเข้ากระเป๋าโลก |
| รางวัล | ไม่เงินโลกหนัก · ไม่ดรอปของจริง (XP เบา optional ≤ โลกจริงมาก) |

**Anti-farm:** chamber ไม่เติม money_world / tax_fund / market listing  

---

## 10. Relic Aura + Social Lite (023.4)

| แหล่ง | ผล soft |
|-------|---------|
| Companion ในปาร์ตี้ | ขวัญ companion หรือ player soft note · ไม่บังคับแตกทีม |
| Echo เกียร์แรง | เมนู: ถอย · นอบน้อม (ลดโทษ aura ชั่วคราว) · ก้าวร้าว (เสี่ยง soft ต่อสู้ / ขวัญพัง) |

**ห้าม:** บังคับฆ่า · online realtime aura · PvP ลงโทษถาวร  

---

## 11. เศรษฐกิจ (ไม่ชน WO-021/022)

| กฎ | เหตุผล |
|----|--------|
| Chamber ไม่ให้เงิน | กันฟาร์ม |
| Burden ไม่ buff ดรอปเงิน | กัน “ใส่เทพ = รวย” |
| เรลิกจริง (023.5) หายาก | drop/quest/boss เท่านั้น · ไม่ร้านระบบ bulk |
| Sink เบา optional | พิธีดูแลเรลิก / heaven–hell เล็ก — ไม่ธนาคาร |
| Sell junk / auto buy | คงตาม WO-021/022 — burden ไม่แตะ |

**เช็คหลัง 023.5:** Field30 economy เงินไม่ระเบิดจาก relic; auto ยังซื้อเสบียงได้  

---

## 12. ลำดับเฟส implement (WO-023)

| เฟส | รหัส | งาน | โค้ด |
|-----|------|-----|:----:|
| 1 | **023.1** | Vision & Rule (เอกสารนี้) | ไม่ |
| 2 | **023.2** | Divine Burden Lite ทุกที่ | ใช่ |
| 3 | **023.3** | Godforge Chamber Lite | ใช่ |
| 4 | **023.4** | Relic Aura + Social Lite | ใช่ (optional ถ้าเวลา) |
| 5 | **023.5** | Content 2–4 เรลิก + economy/UI log | ใช่ |

แต่ละเฟส: **รายงาน + Acceptance ก่อนไปต่อ**

---

## 13. Acceptance Criteria ต่อเฟส

### 023.1 — Vision (เอกสาร)

- [x] ชื่อระบบล็อก 3 ชั้น  
- [x] Burden ทุกที่ · Chamber sandbox · Aura ทีหลัง  
- [x] Legendary+ เริ่ม burden  
- [x] โทษปานกลางค่อนเบา · ใส่ได้เสมอ  
- [x] Auto / economy / ห้ามทำ ชัด  
- [x] AC เฟส 2–5 ด้านล่าง  

### 023.2 — Burden Lite

- [x] สวม legendary+ ที่ gap>0 → soft morale drain บน field care / combat tick เบา  
- [x] soft flavor อย่างน้อย 1 บรรทัดเมื่อเริ่ม burden / ต่อช่วง  
- [x] ถอดแล้ว drain หยุด  
- [x] Auto: ไม่ equip relic เกินตัว · ถอดเมื่อขวัญต่ำ (prefs)  
- [x] unit test: fit/strain/crush · unequip clears burden  
- [x] ไม่แตะ money grant formulas ของ WO-021  

### 023.3 — Chamber Lite

- [x] เข้า–ออก chamber ได้จาก hub อย่างน้อย 1 จุด  
- [x] ยืม 2–4 เรลิก · ออกแล้ว inventory โลกไม่มีของยืม  
- [x] sparring อย่างน้อย 1 โหมด  
- [x] สลับ/โหมด วัดพลัง vs วัดภาระ  
- [x] ไม่ +money_world หนักจาก chamber  

### 023.4 — Aura Lite

- [x] สวม burden crush → companion soft note หรือ morale soft  
- [x] (optional) echo path เมนู ถอย/นอบน้อม/ก้าวร้าว soft  
- [x] ไม่มี PvP kill อัตโนมัติ  

### 023.5 — Content + Economy

- [x] เรลิก legendary/divine ใหม่ 2–4 ชิ้น ธีมชัด  
- [x] God log / summary อ่าน burden ได้  
- [x] smoke: economy helpers เดิมยังผ่าน · ไม่ regress grant_combat_money  

---

## 14. ไฟล์เป้าหมาย (เฟสโค้ด — ยังไม่แตะใน 023.1)

| เฟส | ไฟล์แนว |
|-----|---------|
| 023.2 | `game/domain/divine_burden.py` (ใหม่) · equipment recompute · needs tick · dungeon_auto / auto prefs · soft_feel |
| 023.3 | `game/services/godforge_chamber.py` (ใหม่) · personal_hub / field_menus / test run · data items chamber-only |
| 023.4 | divine_burden aura · party soft · situation/echo soft |
| 023.5 | `data/items/items.yaml` · flavor · auto_run_log summary bit |

---

## 15. สิ่งที่ห้ามใน WO-023 ทั้งก้อน

- PvP ฆ่าจากออร่า  
- แลกสกุล / ธนาคาร / inflation overhaul  
- Permadeath จาก Burden  
- Online realtime aura  
- Hard level gate ห้ามใส่  
- Chamber เป็นฟาร์มเงิน/ของจริง  

---

## 16. Changelog เอกสาร

| วันที่ | เหตุการณ์ |
|--------|-----------|
| 2026-07-15 | **023.1** สร้าง vision + rule lock · AC เฟส 2–5 |
| 2026-07-15 | **023.2–023.5** implement @ 1.68.0-alpha · chamber · aura · content |
| 2026-07-15 | **WO-024** polish @ 1.69.0 — echo UI · drops · foresight/hub |
| 2026-07-15 | **WO-025** @ 1.70.0 — quest rewards · auto avoid relic echo |
| 2026-07-15 | **WO-027** @ 1.72.0 — mid relic depth · chamber polish · economy dampen |

---

## 17. สรุปหนึ่งบล็อก

```text
Divine Burden  = ใส่ของเทพได้ · จ่ายขวัญ (ทุกที่)
Relic Aura     = แผ่ soft ไปคนใกล้ (ทีหลัง)
Godforge       = ห้องยืมของ · ไม่ออกโลก · วัดระบบ

เริ่ม legendary+ · โทษเบา–ปานกลาง · Auto ถอดได้
economy WO-021/022 ไม่พัง · ไม่ธนาคาร · ไม่ PvP
```
