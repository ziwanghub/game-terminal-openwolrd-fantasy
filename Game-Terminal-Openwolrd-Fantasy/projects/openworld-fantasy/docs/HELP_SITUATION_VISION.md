# วิสัยทัศน์ + แผนพัฒนา: สถานการณ์ขอแรง · ร่วมทีมช่วย · สังคมโลก

**สถานะ:** **H0–H4 implement แล้ว** (1.13.14) · H5 live co-op ยังไม่ทำ  
**เกมปัจจุบันอ้างอิง:** `1.13.14-alpha`  
**เอกสารแผนรวม:** [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md)  
**เกี่ยวข้อง:** [`WORLD_SERVER_VISION.md`](WORLD_SERVER_VISION.md) · [`WORLD_SOCIAL.md`](WORLD_SOCIAL.md) · [`DUNGEON.md`](DUNGEON.md) · [`UX_TAMA_VISION.md`](UX_TAMA_VISION.md)

---

## 0. เป้าหมายหนึ่งประโยค

เมื่อผู้เล่นติด**สถานการณ์ลำบาก** (เช่น ดันเจียน) บน**เซฟของตัวเอง**  
เขา**ยินยอมเปิดช่อง** ให้ผู้เล่นอื่นในโลก**ร่วมทีมช่วย**ได้ — ไม่ใช่ใครก็เข้าเซฟได้  
อาจ**เสนอของตอบแทน** (เงิน/ไอเทม) หรือ**อาสาไม่รับของ**  
ผู้ช่วยจบสถานการณ์ → เจ้าของกลับมาเจอผล + อ่านเรื่องช่วยเหลือ  
UI ยัง **text + soft / Tama** · ความสนุกอยู่ที่ **ระบบ สังคม เรื่อง กิจกรรม**

---

## 1. หลักการออกแบบ (ล็อกไว้)

| # | หลัก | ความหมาย |
|---|------|----------|
| H-P1 | **Situation บนเซฟเจ้าของ** | ดัน/วิกฤต = state ของผู้เล่น ไม่ใช่ห้องเซิร์ฟกลางก่อน |
| H-P2 | **ช่วย = แทรกเซฟแบบจำกัด** | เขียนผลได้เฉพาะตอน `help.open` + สัญญาชัด |
| H-P3 | **Consent ก่อนเสมอ** | ปิด = echo ทั่วไปห้ามแตะ situation |
| H-P4 | **ไม่ใช่ใครก็เข้าได้** | slots · เงื่อนไขรับ · claim คนแรก |
| H-P5 | **Offer ตอบแทน = optional** | เงิน/ของ/ไม่มี — สังคม ไม่บังคับจ้าง |
| H-P6 | **Escrow ของสัญญา** | ล็อกของตอนเปิด offer · จ่าย/คืนตามผล |
| H-P7 | **Async ก่อน realtime** | เจ้าของ offline ได้ · ผู้ช่วยเล่นกับเงา/ snapshot |
| H-P8 | **Soft / anti-spoiler** | ไม่โชว์สูตร · chronicle เป็นเรื่อง |
| H-P9 | **แยก echo ทั่วไป กับ assist** | ทั่วไปไม่แก้เซฟ · assist แก้ได้จำกัด |
| H-P10 | **Solo นิ่งก่อน แล้วค่อย H-phase** | อย่าเริ่มก่อน playtest แกนนิ่ง |

---

## 2. วิเคราะห์ความพร้อมระบบปัจจุบัน

| ส่วน | สถานะ | ใช้ต่อในแผนนี้ |
|------|--------|----------------|
| ดันเป็น state บนเซฟ | มี | ขยายเป็น `situation` + `help` |
| หลายเซฟต่อ `world_id` | มี | จำลอง P1/P2 บนเครื่องเดียว |
| ตลาด/กระดานไฟล์ร่วมโลก | มี | แพตเทิร์น state โลกร่วม |
| Ranking soft / world_social | มี | กระดานสัญญาณ · ชื่อเสียงผู้ช่วย |
| Player echo ใน sights | มี | ฐานเงา |
| `other_as_combatant` · `member_from_player_echo` | มี | ร่วมทีมช่วย |
| Narrative soft | มี | chronicle |
| แชตโลก / SOS ticket / escrow / เขียนผลกลับ offline | **ยังไม่มี** | สร้างใน H0–H3 |
| Realtime multiplayer | **ยังไม่มี** | หลัง H + W3–W4 |

**สรุปวิเคราะห์:** ฐาน solo + โลกหลายเซฟ + echo **รองรับทิศทาง**  
เคสเต็ม (ขอแรง → ช่วย → จ่ายของ → อ่านชัย) **ยังไม่รองรับในโค้ด** — เป็นแผนเฟส ไม่รื้อเกมทั้งก้อน

---

## 3. โมเดลแนวคิด

### 3.1 Situation (สถานการณ์)

```text
เซฟ P1
  └── situation
        kind: dungeon | crisis | …
        state: snapshot ชั้น/บอส/เวลา soft
        severity: ok | hard | critical   (label UI)
        help:
          open: bool          # ยินยอมแทรก
          slots: int
          policy: public | friends | invite
          offer: { gold?, item_refs?, note? } | null
          escrow: { … }       # ของล็อก
          status: closed | open | claimed | resolved_*
          helper_ids: []
          chronicle: []
```

### 3.2 บทบาท

| บทบาท | ความหมาย |
|--------|----------|
| **Owner (P1)** | เจ้าของเซฟ + situation · เปิด/ปิด consent · วาง offer |
| **Helper (P2)** | รับสัญญาณ · ร่วมทีมชั่วคราว · ได้ของตามสัญญาเมื่อสำเร็จ |
| **Echo owner** | ตัวแทน P1 ตอน offline (AI จาก snapshot) |

### 3.3 สิทธิ์เขียนเซฟ

| การกระทำ | อนุญาตเมื่อ |
|----------|------------|
| อ่าน ranking / แชต | เสมอ (โลก) |
| สู้ echo ทั่วไป | เสมอ · **ไม่** เขียนเซฟเจ้าของ |
| เข้า situation ช่วย | `help.open` + slot ว่าง + claim |
| แก้ผลดัน/วิกฤตบนเซฟ P1 | หลัง assist จบตามกฎ |
| หยิบของ P1 นอก escrow | **ห้าม** |

---

## 4. UX (text · ไม่บังคับภาพ)

### 4.1 P1 ขอแรง

```text
〔สถานการณ์〕 ถ้ำเงา · วิกฤต
1 เปิดสัญญาณขอแรง (ไม่ระบุของ)
2 เปิดพร้อมของตอบแทน
3 ตั้งเงื่อนไขผู้รับ (เพื่อน/สาธารณะ)
0 ยังไม่ขอ
```

### 4.2 กระดานสัญญาณ / แชตโลก (ย่อ)

```text
〔สัญญาณโลก〕
· [ขอแรง] เมษ · ถ้ำเงา · ตอบแทน 50G+ยา
· [ขอแรง] ไพร · ผลึกยอด · (อาสา)
1 รายละเอียด  2 ยื่นมือช่วย  0 กลับ
```

### 4.3 P1 กลับมา

```text
〔จดหมายเงา〕
สถานการณ์ถ้ำเงาจบลงขณะคุณไม่อยู่
ผู้ยื่นมือ: ไพร · สำเร็จ
1 อ่านบันทึกการช่วย  2 เก็บ  0 เข้าโลก
```

Tama / PERSONAL: อารมณ์ soft ตามได้ช่วย / รอแรง / ไม่มีคนมา (เมื่อมี T-phase)

---

## 5. แผนเฟสพัฒนา (H0–H5)

**ยังไม่เริ่มโค้ด** จนกว่า solo + playtest แกน (1.13.x) นิ่งพอ

| เฟส | ชื่อ | ขอบเขต | พึ่งพา | สถานะ |
|-----|------|--------|--------|--------|
| **H0** | Situation + consent flag | โมเดล `situation`/`help` บนเซฟ · เปิด/ปิดในดัน | ดันนิ่ง | **1.13.12** |
| **H1** | กระดานสัญญาณโลก | สแกนเซฟ `help.open` · เมนู **G** | H0 · list_saves | **1.13.13** |
| **H2** | Offer + escrow | เงิน/ไอเทมล็อก · คืน/จ่าย | H0 · inventory | **1.13.13** |
| **H3** | Assist party + ผล + chronicle | ยื่นมือ · สู้บอสเงา · เขียนผล · inbox | H1–H2 · echo · combat | **1.13.13** |
| **H4** | สังคมลึก | policy เพื่อน · ชื่อเสียงผู้ช่วย · เควสยื่นมือ · บันทึกสัญญาณโลก | H3 · world_social | **1.13.14** |
| **H5** | Live co-op (optional) | คน 2 online พร้อมกันใน situation | H3 + online foundation | **รอ** |

### H0 — รายละเอียด

- ขยาย state ดัน → `situation` ทั่วไป (เริ่ม kind=dungeon)
- เมนูในดัน: ขอแรง / ยกเลิกสัญญาณ
- soft warning consent
- เทส: เปิด/ปิด flag · เซฟโหลดได้
- **ไม่** ยังไม่มี P2

### H1 — รายละเอียด

- `list_open_help(world_id)` จาก saves
- เมนูโลกหรือสนาม: 〔สัญญาณ〕
- แสดงชื่อ soft · ที่ · severity · มี offer หรือไม่ (ไม่โชว์ ATK)
- เทส: สองเซฟโลกเดียวกัน · เห็นสัญญาณของอีกใบ

### H2 — รายละเอียด

- เลือก gold / item instance ใส่ offer
- ย้ายเข้า `help.escrow` ตอนเปิด
- ยกเลิก/หมดอายุ → คืนของ
- เทส: เปิดแล้วเงินลด · ยกเลิกคืน

### H3 — รายละเอียด (ฮุกหลัก)

- P2 เลือกยื่นมือ → claim slot
- สร้าง assist session จาก situation snapshot + echo P1 + ตัว P2
- ชนะ/แพ้ → apply ไปเซฟ P1 (path แยก, migrate-safe)
- จ่าย escrow ให้ P2 เมื่อ win ตามสัญญา
- `world_inbox` บน P1 + chronicle soft lines
- เทส ScriptedIO: P1 เปิด → P2 ช่วยชนะ → โหลด P1 เห็นเคลียร์ + inbox

### H4 — รายละเอียด

- `policy: friends` ใช้ affinity / social_memory
- soft title ผู้ช่วย
- เควส/กระดานด้านสังคม
- โพสต์เข้า world_chat (ถ้ามี C1) หรือใช้กระดาน H1 เป็นพอ

### H5 — รายละเอียด

- ขยาย ticket เป็น live room
- **อย่าทำ** ก่อน solo นิ่ง + H3 นิ่ง + ทิศ online ชัด

---

## 6. ลำดับแผนรวมทั้งโปรเจกต์

```text
[ปัจจุบัน]  1.13.x alpha · dashboard · solo
     │
     ▼
 A   Playtest นิ่ง (AoE · Mode Shell · เมือง · เศรษฐกิจ)
     │
     ├─► (optional ขนาน) T0–T1 UX-Tama
     ├─► (optional) เนื้อหาตาม feedback
     │
     ▼
 B   W0 Rank soft  และ/หรือ  H0 Situation consent
     │         (W0 กับ H0 ขนานได้ — คนละผิว)
     ▼
 C   W1 Echo ทั่วไปนิ่ง  →  H1 กระดานสัญญาณ
     │
     ▼
 D   H2 Escrow  →  H3 Assist + chronicle   ★ เคส “ขอแรง–ช่วย–อ่านชัย”
     │
     ▼
 E   H4 สังคมลึก · (W2 rank challenge ถ้าต้องการ)
     │
     ▼
 F   Online foundation (W3–W4)  →  H5 live co-op · realtime มอน (คนละสเกล)
```

**ลำดับแนะนำสั้น**

1. playtest / solo นิ่ง  
2. H0 (consent บนดัน) — ถูกและลดความเสี่ยง design  
3. W1 echo ถ้ายังบาง — ก่อน H3  
4. H1 → H2 → H3  
5. H4 · Tama mood ผูก social  
6. realtime ทีหลัง  

**อย่า** กระโดด H3 ก่อน H0–H2 และ echo/combat เสถียร  
**อย่า** เริ่ม H5/netcode ตอนนี้

---

## 7. งานต่อโมดูล (เมื่อลงมือ)

| โมดูลใหม่/ขยาย | เฟส |
|----------------|------|
| `domain/situation.py` หรือขยาย `dungeon.py` | H0 |
| `domain/help_offer.py` (escrow) | H2 |
| `domain/assist_session.py` / service | H3 |
| `services/help_board.py` | H1 |
| `data` chronicle templates | H3 |
| เทส `tests/unit/test_help_situation_*.py` | ทุกเฟส |
| เซฟ: `situation`, `world_inbox`, migrate `save_version` | H0+ |

ของเดิมใช้ต่อ: `world_social`, `party.member_from_player_echo`, `combat_session`, `narrative`, `save_service`, Mode Shell

---

## 8. ความเสี่ยงและกัน

| ความเสี่ยง | แนวกันในแผน |
|------------|-------------|
| AFK ให้คนอื่นเคลียร์ทั้งเกม | จำกัด kind/ชั้น · cooldown · ลดรางวัล owner เล็กน้อย |
| ถูกฉวยของในเซฟ | escrow เท่านั้น · ห้ามเปิดถุงเต็ม |
| เซฟชน P1 เข้าขณะ P2 ช่วย | ล็อก `help.status=claimed` · P1 รอหรืออ่านอย่างเดียว |
| สแปมสัญญาณ | 1 สัญญาณต่อตัว · cooldown |
| God-file combat/field | H3 แยก `assist_*` อย่ายัด field_loop ยาวเกิน |
| สับสน echo ทั่วไป | UI แยกคำ · โค้ดแยก flag |

---

## 9. เกณฑ์พร้อมเริ่ม H0

1. Playtest หลัง 1.13.x ผ่านรอบหนึ่ง (หรือทีมยอมรับความเสี่ยง)  
2. ดัน solo เคลียร์/ล้ม ทำงานนิ่ง  
3. ตกลง: consent + escrow + แยก echo  
4. ไม่ชนคิวร้อน (bug ไฟต์/เซฟวิกฤต)  

---

## 10. สิ่งที่จงใจยังไม่ทำใน H-phase

- Realtime มอนทั้งแมพหลายคน  
- แชตสแปมแบบ MMO  
- ใครก็เปิดเซฟใครก็ได้โดยไม่ consent  
- บังคับมีของตอบแทนถึงจะช่วย  
- แทนที่ solo dungeon ด้วย always-online dungeon server  

---

## 11. Changelog เอกสารนี้

| วันที่ | หมายเหตุ |
|--------|----------|
| 2026-07-14 | วิเคราะห์ + แผน H0–H5 · situation บนเซฟ · consent · offer · ลำดับรวมกับ W/T/playtest |
| 2026-07-14 | **H0** implement: `domain/situation.py` · เมนูดัน 6 · เซฟ `situation` · เทส |
| 2026-07-14 | **H1–H3**: กระดาน G · escrow · assist combat · inbox chronicle |
| 2026-07-14 | **H4**: friends policy · help_rep · world_signals log · เควส first_sos/first_hand |
