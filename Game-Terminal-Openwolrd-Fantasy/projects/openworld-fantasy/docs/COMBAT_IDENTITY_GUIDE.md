# Soft Combat Identity + Weakness Lite (WO-054)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-054 |
| **สถานะ** | shipped @ `2.01.0-alpha` |
| **โมดูล** | `game/domain/combat_identity.py` |
| **ผูก** | Damage Pipeline · Combat session · Auto farm · Personal journal |
| **หลัก** | Soft Feel · ตัวตนในไฟต์ · ไม่ dump สูตร |

---

## 1. Soft Combat Identity

Personal System ส่งผลใน combat ผ่าน:

| แหล่ง | Pre-fight / Hit soft | Mult เบา (ซ่อน) |
|--------|----------------------|-----------------|
| เกรด S–SSS | พลังไหลเวียนแรง | ≈ +2–3.5% |
| เกรด F–E | แรงแผ่ว | ≈ −2% |
| Bond resonance | เรลิกเรโซแนนซ์ | ≈ +2% |
| Bond chorus | คณะเรลิกส่งผ่าน | ≈ +3.5% |
| Bond tension | เรลิกตึงเครียด | ≈ −1.5% |
| Faction อุ่นในพื้นที่ | สายตาเทพ / เงามาร / echo | ≈ +1.5% |
| Anima ลึก/แผ่ว | (ซ้อน presence) | ≈ ±1% |

**Clamp identity:** 0.94–1.08  
**Hit flavor:** throttle (ไม่ทุกฮิต)

---

## 2. Weakness Lite (Appraisal SS+)

| | |
|--|--|
| เงื่อนไข | มอนถูก appraise ชั้น **SS** หรือ **SSS** |
| ใบ้ soft | ธาตุ/แนวที่ทะลุได้ · ไม่โชว์ mult % |
| SSS เพิ่ม | สาย soft เช่น “น้ำ+ลม → หนาว/ช้าลง” (ไม่ใช่ recipe เต็ม) |
| Micro mult | โจมด้วยธาตุที่ตรงจุดอ่อน soft → **+3–6%** เท่านั้น |
| S หรือต่ำกว่า | ไม่มี weakness lite |

**นอกขอบเขต:** fusion อัตโนมัติ · weakness recipes เต็ม · เฉลยสูตร SSS

---

## 3. UX flow

```
เข้าไฟต์
  → burden / needs soft alerts
  → Soft Combat Identity pre-fight (1–3 บรรทัด)
  → (ถ้า appraise SS+ แล้ว) ใบ้จุดอ่อน soft

ฮิต
  → pipeline grade mult
  → identity + weakness lite micro mult
  → soft flavor บางครั้ง

ชนะ
  → journal soft (บอส/elite / บางครั้ง)
  → clear fight identity flags
```

| ที่ | |
|----|--|
| Manual combat | `combat_session` |
| Auto | `auto_farm` เก็บ pre-fight lines |
| I / Appraisal | ตั้ง `_appraised_targets` → เปิด weakness lite |

---

## 4. ห้ามโชว์ผู้เล่น

- `power_*` · growth_mult · identity mult ดิบ · matchup 1.4  
- สูตรดาเมจ · recipe เต็ม  

---

## 5. ทดสอบ

| | |
|--|--|
| Unit | `tests/unit/test_wo054_combat_identity.py` |
| Harness | `scripts/wo054_combat_identity_playtest.py` |

---

## Changelog

| วันที่ | |
|--------|--|
| 2026-07-16 | WO-054 Soft Combat Identity + Weakness Lite |
