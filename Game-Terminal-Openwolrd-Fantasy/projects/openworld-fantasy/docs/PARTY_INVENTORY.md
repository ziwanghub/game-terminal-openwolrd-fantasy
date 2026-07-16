# ปาร์ตี้ · กระเป๋า · ดรอป · อัปเกรด

**อัปเดต:** WO-PARTY-7 · ตรงโค้ด `2.08.0-alpha` (`wo-party-7-priority-assist`)  
**โดเมน:** `party.py` · `companion_decision_engine.py` · `appraisal.py` · `party_auto.py`

---

## ปาร์ตี้ (สูงสุด 3)

### ชนิดสมาชิก
ผู้เล่น (เงา) · ภูต · สัตว์อสูร · เทพสวรรค์ · เทพมาร · สัตว์สวรรค์ · สัตว์นรก · อื่น

### ได้มา (Recruit)
- **ต้องได้รับการยอมรับ** (consent) — เงื่อนไขซ่อน (เลเวล · พื้นที่ · affinity · ฯลฯ)
- ผู้เล่นอื่น: มิตรภาพ → ชวนเข้าปาร์ตี้ (consent roll)
- สิ่งมีชีวิต: สำรวจมีโอกาสเงาเข้าใกล้
- เคยร่วมทาง: **เชิญกลับ** จากรายชื่อรู้จัก (ถูกกว่า; เงาผู้เล่นต้องพบใหม่ในโลก)

### สัมพันธ์สหาย (Relationship 0–100)
| กลไก | พฤติกรรม |
|------|----------|
| เก็บ | `party_bonds[id]` (0–100) |
| ป้าย soft | เย็นชา → ห่างเหิน → รู้จัก → คุ้นเคย → ไว้ใจ → ผูกพันลึก |
| UI | ใช้คำว่า **สัมพันธ์สหาย** เสมอ (ไม่ใช้คำว่า bond เปล่าๆ) |
| ของขวัญ | เมนู **Y** → ให้ไอเทม/เงิน · like tags **ซ่อน** |
| Decay | คน**นอก**ทีมลดช้ามาก · floor 5 · คนในทีมไม่ลด |
| **≠ เรโซแนนซ์เรลิก** | relic bond / chorus / tension — บนเกียร์ · คนละชั้น |

### อ่านสหาย (WO-PARTY-6 · soft appraisal)
- เมนู **Y → 6** · ฟรี (ไม่เสียมานา)
- ชั้นตาม `appraisal_tier` ของผู้เล่น:
  - พื้นฐาน: ชนิด soft + สัมพันธ์สหาย
  - **S+**: บทบาทซุ่ม (รักษา/พุ่ง/…)
  - **SS+**: โทนของขวัญ (ไม่โชว์ tags)
  - **SSS**: สไตล์ซุ่ม + ใบ้แยกเรลิก
- แผงปาร์ตี้โชว์ blurb หนึ่งบรรทัด (`format_party_appraisal_blurb`)

### Gift Stack Behavior (WO-PARTY-3 · สำคัญ)
- ให้ของขวัญไอเทม = หัก **1 unit** จาก stack เท่านั้น
- ยา/อาหาร/mat ที่กอง `xN` → เหลือ `x(N-1)` · **ไม่** ลบทั้งกอง
- เงินของขวัญ = หักจำนวนที่ระบุ (ไม่เกี่ยวกับ stack)
- ถ้าช่องว่าง/ของหาย → soft ยกเลิก ไม่ปรับสัมพันธ์

### พาสซีฟ (ตลอด)
- ATK / max HP / max MP เบา จากสมาชิก → รวมใน `recompute_stats`
- ไม่ให้ Crit / Dodge / Anima จากปาร์ตี้ (ยัง)

### ในไฟต์
| หัวข้อ | ความจริง (โค้ด) |
|--------|------------------|
| ซุ่มช่วย | **อัตโน** หลังผู้เล่นลงมือ (`party_member_turns`) |
| โอกาสลงมือ | ตามสัมพันธ์สหาย (~28%–**90% soft-cap**) + luck soft |
| **Priority (WO-PARTY-7)** | `companion_decision_engine.decide` — P0 ผู้เล่นวิกฤต → P1 มอนแรง → P2 ทั่วไป |
| แอคชัน | heal · **cleanse** · attack · buff · wait |
| Soft fail | cleanse/heal มี chance สำเร็จจาก Bond + Grade + Anima + role |
| ต้นทุน | **ไม่เสีย MP · ไม่เสียเงิน** |
| เมนู **5** | ดูสถานะ · โฟกัสเบา · **ไม่กินเทิร์น** |
| ดาเมจซุ่ม | Assist Pipeline Lite (grade/identity) · ไม่ rewrite full pipeline |
| Soft Alert | `party.assist_cleanse_ok` / `party.assist_fail` (throttle) |
| Auto | ใช้ `party_member_turns` ชุดเดียว |

### Priority ย่อ (P0–P2)
1. **P0** HP วิกฤต / พิษแรง / ขวัญวิกฤต → heal หรือ cleanse  
2. **P1** elite/boss + HP มอนต่ำ → attack (support อาจ heal ถ้าผู้เล่นยังแผ่ว)  
3. **P2** ตาม role: support เอน cleanse/heal · attack เอนโจมตี  

### Role tag (template)
- `role: support` / `support_nature` — ภูตใบไม้ (`spirit_leaf`) เชี่ยวชาญชำระ  
- `role: attack` — สายโจมตี  
- ไม่มี tag → lean จาก `kind`

### Assist Pipeline Lite (WO-PARTY-4)
- `assist_pipeline_mult()` · clamp ~0.88–1.12  
- grade / identity ใช้ **~ครึ่ง edge** ของผู้เล่น (ทีม = support)  
- boss ×0.92 · elite ×0.96  
- เพดาน hit ≈ `base × 2.4 × rel_pow`  
- บางครั้ง soft flavor «จังหวะซุ่มสอดกับฝีมือคุณ…» (ไม่โชว์ตัวเลข)

### UI
- สนาม **Y** = แผงปาร์ตี้ · ของขวัญ · ปลด · เชิญกลับ
- ไฟต์ **5** = สถานะ/โฟกัส (ไม่ใช่ “เรียกเสียมานา”)

---

## กระเป๋า (อ้างอิง WO-INV)
- Soft cap **40 ช่อง** (stack = 1 ช่อง · การ์ดแยก)
- True stack: ยา/อาหาร/วัตถุดิบ ชนิด+rarity เดียวกัน
- เมนู **5** กระเป๋า: หมวด · **O** จัดระเบียบ · **R** เรลิก
- รายละเอียดเต็ม: [`BAG_SYSTEM.md`](BAG_SYSTEM.md)

## ดรอป
- ชนะไฟต์ → รายการของหล่น → **ผู้เล่นเลือกเก็บ** (comma / 0=ทิ้ง)
- เต็มช่อง → เก็บช่องใหม่ไม่ได้ (stack เข้ากองเดิมได้)

## อัปเกรด
- มี **อัตราสำเร็จ** ลดลงเมื่อ + สูง
- ล้มเหลว: วัสดุ/เงินสลาย ขั้นไม่ขึ้น
- UI ไม่บอกจำนวนวัสดุชัด — ใบ้คลุมเครือ + ระดับความเสี่ยง

---

## ไฟล์
| ที่ | บทบาท |
|----|--------|
| `data/party/companions.yaml` | templates · kinds · max size |
| `game/domain/party.py` | recruit · bond · gift · assist · passive |
| `game/domain/inventory_sys.py` · `bag_stack.py` | กระเป๋า / stack (gift ใช้ 1 unit) |
| `game/services/field_menus.py` | เมนู Y |
| `game/services/combat_session.py` | เมนู 5 · `party_member_turns` |

## Auto Play (WO-PARTY-5)
| ทำ | ไม่ทำ (ตั้งใจ) |
|----|----------------|
| `tick_relationship_decay` | auto recruit |
| soft gift เมื่อ bond แผ่ว + มี mat/อาหารส่วนเกิน | auto dismiss |
| เคารพ `party_min_food_keep` · ไม่ให้ยา HP | auto call บังคับ |
| prefs: `party_care` · `party_gift` · cooldown | บังคับของขวัญทุก tick |

`game/runtime/party_auto.py` · เรียกจาก dungeon auto + `auto_manage_inventory`

## Party × Needs (soft)
- **ซุ่มรักษา:** ลด fatigue เล็ก · +morale เบา (ไม่โชว์ตัวเลข)
- **ให้ของขวัญอาหาร:** แบ่งคำ → ลดหิวผู้เล่นเบา (`apply_food_relief` silent)

## ประวัติสั้น
| เวอร์ชัน | หมายเหตุ |
|----------|----------|
| ≤1.54 | relationship assist · free call focus |
| 2.03 | bag stack (WO-INV) — gift เคยหักทั้งกอง |
| **2.04 / WO-PARTY-3** | gift = 1 unit · doc truth |
| **2.05 / WO-PARTY-4** | assist pipeline lite · chance soft-cap 90% |
| **2.06 / WO-PARTY-5** | auto soft gift · needs heal/food share |
| **2.07 / WO-PARTY-6** | appraise companion soft · UI สัมพันธ์สหาย |
| **2.08 / WO-PARTY-7** | priority engine · cleanse soft · role lean |
