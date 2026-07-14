# RD-18: Technical Architecture

**สถานะ:** Draft  

---

## 1. วัตถุประสงค์

กำหนดสถาปัตย์เทคนิคให้ขยายเฟสได้ โดยแยก domain / data / UI / governance

## 2. สแต็กที่ล็อก (v1)

| ชั้น | เทคโนโลยี |
|------|-----------|
| ภาษา | Python 3.11+ |
| แพ็กเกจ | pyproject.toml |
| คอนเทนต์ | YAML + schema validation |
| เซฟ | JSON |
| UI | Terminal stdlib → Rich optional |
| ทดสอบ | pytest |
| Lint | ruff |
| VCS | Git |
| Governance workspace | `core/` Z-MOS (นอกเกม) |

## 3. แผนผังลอจิก

```text
                    data/*.yaml + art/*.txt
                              │
                        DataRegistry
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
      World/Area          Combat/Elements       Shop/Vitals
      Encounter           Defense/Combo         Cards/Gear
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                         Services
                     (save, travel, level)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ui_terminal      runtime(auto)     admin CLI
              │
              ▼
         Terminal I/O
```

## 4. แพ็กเกจโค้ด (projects/openworld-fantasy)

| แพ็กเกจ | หน้าที่ |
|---------|--------|
| `game.domain` | logic บริสุทธิ์ ไม่ print/input |
| `game.data_load` | โหลด + validate |
| `game.services` | use-case |
| `game.ui_terminal` | แสดงผล + รับอินพุต |
| `game.runtime` | auto, timer |
| `game.admin` | เครื่องมือดูแล |
| `game.ports` | Clock, RNG, IO interfaces |

## 5. กฎสถาปัตย์

1. Domain ห้ามพึ่ง Terminal API  
2. UI ห้ามคำนวณสูตรดาเมจซ้ำนอก domain  
3. คอนเทนต์ใหม่ = ไฟล์ data (+ art) เป็นหลัก  
4. RNG ฉีดได้เพื่อเทสต์ซ้ำ  
5. save_version + migrate  
6. ฟีเจอร์เกมไม่เข้า `core/`  

## 6. ความสัมพันธ์กับ core (Z-MOS)

- `core` = ผู้คุมกฎพัฒนา (session, preflight, trace)  
- ไม่แทนที่ pytest/Python ของเกม  
- ถ้าฝัง `.z-mos/` ภายหลัง → ที่ root โปรเจกต์เกม  

## 7. วิวัฒนาการสเกล (ไม่ทำก่อนจำเป็น)

| Stage | เพิ่มเมื่อ |
|-------|-----------|
| A | ไฟล์ + JSON + terminal (ปัจจุบัน–M5) |
| B | Rich, เทสต์หนา, mods เบา |
| C | SQLite ถ้าเซฟ/คอนเทนต์ใหญ่ |
| D | Server แชร์ domain ถ้ามีมัลติจริง |

## 8. ประวัติ

| วันที่ | หมายเหตุ |
|--------|----------|
| 2026-07-14 | Draft architecture |
