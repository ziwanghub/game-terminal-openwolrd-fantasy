# แผนพัฒนาหลัก (Roadmap)

**เกมปัจจุบัน:** `1.15.0-alpha` (`tama-t1-t2`)  
**อัปเดต:** 2026-07-14  
**คิวงานรายวัน:** [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md)  
**แผนเฟสไอเทม (อัปครบแต่แบ่งเฟส):** [`ITEM_CONTENT_PLAN.md`](ITEM_CONTENT_PLAN.md) · **IC0–IC6**  
**แผนเฟสมอน (เติมครบแต่แบ่งเฟส · ไม่ dump RO):** [`MONSTER_CONTENT_PLAN.md`](MONSTER_CONTENT_PLAN.md) · **MC0–MC6**  
**สถาปัตย์:** [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## 0. เป้าหมายผลิตภัณฑ์ (ล็อกทิศ)

| ระยะ | เป้าหมาย |
|------|----------|
| **ตอนนี้ (ล็อก)** | **Solo บนเครื่อง · ระบบนิ่ง · playtest จริง** — ห้ามเปิด online ใหญ่ |
| **กลาง** | โลกร่วม **async ที่มีแล้ว** ใช้/polish เบา (อันดับ · echo · ขอแรง · หีบ) — ยังไม่ net |
| **ยาว / ท้ายสุด** | Online realtime หลายคน + มอนหลากหลาย (คนละ architecture) |

**UI:** text + soft bars + Tama ที่จอสถานะ — ความสนุกที่ระบบ / เรื่อง / กิจกรรม / เควส  

**ทิศล็อก (2026-07-14):** เล่นคนเดียวให้นิ่งก่อน · **online ไว้สุดท้าย**  
**ห้ามกระโดด:** W4 / H5 live room / realtime MP / netcode ก่อน solo playtest + hotfix นิ่ง  

---

## 1. สิ่งที่ทำแล้ว (ฐาน alpha)

| ช่วงเวอร์ชัน | สาระ |
|--------------|------|
| ≤1.13.10 | โลกเปิด · ATB กลุ่ม · AoE · ตลาด · กระดาน · Mode Shell · ดัน |
| 1.13.11 | แดชบอร์ดประเมินระบบ (text) |
| 1.13.12–14 | Help H0–H4 (ขอแรง · escrow · assist · เพื่อน · ชื่อเสียง) |
| 1.13.15 | T0 needs tick · W0 rank soft |
| 1.13.16 | N1–N4 needs→combat/ATB · อาหาร tier |
| 1.13.17 | ร้าน/กระเป๋า **เลือกหมวดก่อน** |
| 1.13.18 | หีบ **L0–L2** (data · เปิด · ดรอปบอส/มอน · unit skeleton) |
| 1.14.0 | หีบ **L3–L4** (เควส/กระดาน · unit unique save/world) |

**เล่นได้ครบวงจร alpha** — โฟกัสถัดไป = playtest + T1–T2 / W1

---

## 2. ลำดับพัฒนาแนะนำ (Wave)

### Wave A — เสถียรจาก playtest (คิวสั้น · ตอนนี้)

| # | งาน | หมายเหตุ |
|---|-----|----------|
| A1 | Playtest มือ 1–2 ชม. | หิว/อาหาร/ร้านหมวด · ดรอปมอน · ขอแรง 2 เซฟ · ไฟต์กลุ่ม |
| A2 | แก้บั๊ก/บาลานซ์จาก playtest | ไม่เปิดฟีเจอร์ใหญ่ |
| A3 | เนื้อหาไอเทม **แบ่งเฟส IC1+** | [`ITEM_CONTENT_PLAN.md`](ITEM_CONTENT_PLAN.md) — อัปครบในที่สุด แต่ทีละเฟส |
| A4 | เนื้อหามอน **แบ่งเฟส MC1+** | [`MONSTER_CONTENT_PLAN.md`](MONSTER_CONTENT_PLAN.md) — เติมครบในที่สุด · **ไม่ dump RO ทั้งก้อน** |

**เกณฑ์จบ Wave A:** ไม่มี blocker เล่น · ร้าน/กระเป๋า/หิว ใช้รู้เรื่อง  

**ขนาน content:** หลัง A1–A2 นิ่งพอ → **IC1 ∥ MC1** แล้ว **IC2 ∥ MC2** … จน IC6/MC6 ปิดงาน (ห้าม dump ไอเทมหรือมอนทั้งคลังทีเดียว)

---

### Wave B — หีบรางวัล (L0–L2) ✅ **1.13.18**

เอกสาร: [`CHEST_LOOT_VISION.md`](CHEST_LOOT_VISION.md)

| เฟส | งาน | ผลที่ผู้เล่นเห็น | สถานะ |
|-----|-----|------------------|--------|
| **L0** | `data/chests/` ranks · pools | — | **done** |
| **L1** | `open_chest` · ให้ของ · soft text · หมวดหีบ | เปิดหีบได้ | **done** |
| **L2** | ดรอปบอส/มอน (มอนธรรมดาเกือบไม่ตก) | บอสมีหีบ · ไร้ฟาร์มตายตัว | **done** |

**หลักที่ล็อก:** แรงก์หีบ ≠ การันตีของ · noise + anti_farm  
**เกณฑ์จบ Wave B:** บอสสุ่มหีบ ธรรมดา–S ได้ · เปิดแล้วเข้ากระเป๋า — **ผ่าน**

---

### Wave C — หีบลึก + เนื้อหา (L3–L4) ✅ **1.14.0**

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **L3** | เควส/กระดาน รางวัลหีบ (เงื่อนไขซ่อน) | **done** |
| **L4** | Unit unique ชิ้นเดียว (save + world claim) | **done** (3 ชิ้น) |
| **L5** | หมวดหีบในกระเป๋า | **done 1.22.0** (สรุปแรงก์ · เรียง · เปิดทั้งหมด) |

ขนานได้เล็กน้อย: **N5** unit soft จาก needs

**เกณฑ์จบ Wave C:** มีอย่างน้อย 1–2 unique + เควสหีบ 1 สาย — **ผ่าน**

---

### Wave D — Tama / เวลา (T1–T2) ✅ **1.15.0**

เอกสาร: [`UX_TAMA_VISION.md`](UX_TAMA_VISION.md)

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **T1** | `saved_at` · load delta หิว/ล้าตอนโหลด | **done** |
| **T2** | PERSONAL panel Tama (ASCII + กิน/พัก) | **done** (พื้นฐาน) |
| **T3** | live optional — ทีหลัง | **รอ** |

**เกณฑ์จบ Wave D:** โหลดเกมหลังห่างนานรู้สึก “ไม่ได้ดูแล” แบบ soft — **ผ่าน (T1–T2)**

---

### Wave E — โลก soft ลึก (W1–W2)

เอกสาร: [`WORLD_SERVER_VISION.md`](WORLD_SERVER_VISION.md)  
(W0 rank มีแล้วบางส่วน)

| เฟส | งาน |
|-----|-----|
| **W1** | Player echo ในสนาม (สู้/คุย ไม่แก้เซฟเจ้าของ) | **1.19 done** |
| **W2** | ท้าอันดับ + ค่าหัว | **1.19 lite done** |

**เกณฑ์จบ Wave E:** เจอเงาผู้เล่นอื่นในโลกเดียวกันได้ — **บรรลุ lite**

---

### Wave F — Online / realtime (**ท้ายสุด · ระงับจนกว่า solo นิ่ง**)

| เฟส | งาน | สถานะ |
|-----|-----|--------|
| **H5 room** | live co-op situation จริง | **ระงับ** |
| **W4** | online lite · auth | **ระงับ** |
| **Realtime MP** | หลายคน + มอนโลก | **ระงับ · architecture ใหม่** |

W3 file-host / echo / ขอแรง async = มีแล้ว — **ไม่ขยายเป็น online** ในช่วง solo  
**อย่าเริ่ม Wave F** จนกว่า playtest solo + hotfix ผ่านและทีมยืนยัน
---

## 3. แผนภาพลำดับ

```text
[ตอนนี้ 1.15.0 · T1–T2 done]
     │
     ▼
 A  Playtest + hotfix
     │
     ▼
 B–C  หีบ L0–L4     ✅
     │
     ▼
 D  T1–T2 Tama       ✅  (T3 optional)
     │
     ▼
 E  W1–W2 echo / ท้าอันดับ   ★ ระบบถัดไปหลัก
     │
     ▼
 F  Online / H5 / realtime   (คนละสเกล)
```

**ขนานที่ทำได้โดยไม่ชน:**  
- A2 hotfix ∥ เขียน data L0  
- D (T1) ∥ E (W1) หลัง C เริ่ม  
- อย่าขนาน L4 unique กับ N5 unit soft คนละทีมโดยไม่คุย scope

---

## 4. แผนเวอร์ชันโดยประมาณ (ยืดหยุ่น)

| เวอร์ชันเป้า | เนื้อหา |
|--------------|---------|
| **1.13.18** | L0–L2 หีบ data + เปิด + ดรอป ✅ |
| **1.14.0** | L3–L4 เควส/กระดาน + unit unique ✅ |
| **1.14.1** | คราฟ K1–K2 ✅ |
| **1.15.0** | T1–T2 Tama load delta + panel ✅ |
| **1.16.x** | W1–W2 |
| **2.x** | Online foundation |

เลขจริงปรับตาม playtest — ใช้ Wave เป็นตัวนำ ไม่ยึดเลข

---

## 5. เอกสารอ้างอิงต่อสาย

| สาย | เอกสาร | เฟส |
|-----|--------|-----|
| หีบ | `CHEST_LOOT_VISION.md` | L0–L5 |
| **ไอเทม/การ์ด content** | `ITEM_CONTENT_PLAN.md` | **IC0–IC6** (อัปครบ · แบ่งเฟส) |
| **มอนสเตอร์ content** | `MONSTER_CONTENT_PLAN.md` | **MC0–MC6** (เติมครบ · แบ่งเฟส · ไม่ dump RO) |
| ดรอปมอน (runtime) | `MONSTER_DROPS.md` | D1–D2 + world + hotfix |
| Needs/อาหาร/combat | `NEEDS_COMBAT_FOOD_VISION.md` | N1–N4 ทำแล้ว · N5 |
| Tama | `UX_TAMA_VISION.md` | **T0–T3 (1.20)** |
| ขอแรง | `HELP_SITUATION_VISION.md` | **H0–H5 lite (1.20)** · live room รอ |
| โจมตี/ป้องกัน | `DAMAGE_DEFENSE_VISION.md` | **DD0–DD5 (1.17.1)** |
| โหลดเอาต์ · grip · diversity | `EQUIP_LOADOUT_VISION.md` | **EL0–EL5 + EQ-W/G/A (1.18)** · soft S-P1…14 |
| โลกเซิร์ฟ | `WORLD_SERVER_VISION.md` | **W0–W3 lite (1.21)** · W4 รอ |
| กระเป๋า | `BAG_SYSTEM.md` | หมวดอาหาร+hub |
| คิวสั้น | `IMPROVEMENT_PLAN.md` | อัปเดตราย sprint |

---

## 6. หลักคุณภาพทุกเฟส

1. Soft / anti-spoiler — ไม่โชว์สูตรดิบ  
2. Domain บริสุทธิ์ + pytest + ScriptedIO  
3. เซฟ migrate ผ่าน `save_version` / setdefault  
4. อย่า god-file — หีบแยก `domain/chest_loot.py` + service  
5. เล่นคนเดียวนิ่งก่อน online  

---

## 7. คำสั่งทีม (สั้น)

```bash
cd projects/openworld-fantasy
./game-start              # เล่น
./game-start --test       # เทส
./game-start --dashboard  # สถานะระบบ
```

---

## 8. สรุปหนึ่งย่อหน้า

ตอนนี้เกมอยู่ **alpha ระบบแกน + ขอแรง + needs/อาหาร + ร้าน/กระเป๋าแยกหมวด**  
แผนถัดไป: **playtest → หีบ L0–L2 (หลัก) → หีบลึก/unit → Tama เวลา → echo โลก → online ทีหลัง**  
ไม่เปิด realtime หลายคนจนกว่า Wave A–C นิ่ง
