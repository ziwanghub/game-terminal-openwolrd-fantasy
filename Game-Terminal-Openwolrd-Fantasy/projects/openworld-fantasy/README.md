# Open World Fantasy (Terminal)

เกมข้อความ open-world fantasy — ยังไม่มีกราฟิก

```text
Game-Terminal-Openwolrd-Fantasy/projects/openworld-fantasy/
```

## อ่านก่อน (3 ชั้น)

| ชั้น | ไฟล์ | บทบาท |
|------|------|--------|
| เกม | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | แผนที่ระบบ · **Doc Policy** · กฎทีม |
| รัน | ไฟล์นี้ | คำสั่ง · เมนูสั้น |
| วินัย dev | [`../../README.md`](../../README.md) + `core/` | **Z-MOS** — session/preflight ไม่ใช่ logic เกม |

แผนหลัก: [`docs/ROADMAP.md`](docs/ROADMAP.md) · คิวงาน: [`docs/IMPROVEMENT_PLAN.md`](docs/IMPROVEMENT_PLAN.md) · log เวอร์ชัน: [`docs/PHASES.md`](docs/PHASES.md)

## รัน (1.15.0-alpha · tama-t1-t2)

```bash
cd projects/openworld-fantasy
./game-start                 # แนะนำ — เริ่มเกม
./game-start --dashboard     # แดชบอร์ดระบบ (text)
./game-start --test          # pytest -q
./game-start --help          # ตัวเลือก + เมนูสั้น

# เทียบเท่า
python3 -m game
python3 -m pytest -q
python3 -m game.admin.dashboard
```

| เมนูหลัก | |
|----------|--|
| **1** | เข้าโลก (เซฟล่าสุด / สร้างใหม่) |
| **2** | โหลดตัวละครในโลก |
| **3** | อันดับชื่อเสียง |
| **4** | เกี่ยวกับ |
| **5** | นำเข้า export |
| **8** | แอดมิน |
| **0** | ออก |

**Mode Shell:** 〔สำรวจ〕1–4 · **5/I** ตัวละคร · **6** ร้าน · **7** ออโต้ · **G** สัญญาณขอแรง · **0** ออก  
〔ดัน〕**6** ขอแรง/พักรอแรง · 〔ตัวละคร〕กระเป๋า·เควส · 〔ร้าน〕M·คราฟ  
คำสั่ง: `f_mn01` · `sw001` · `?`

## โครงเอนจิน

```text
game/domain/      # logic บริสุทธิ์
game/services/    # ลูป + I/O
game/ui_terminal/ # ข้อความ
game/data_load/   # YAML → registry
data/             # คอนเทนต์
tests/            # pytest + ScriptedIO
docs/             # hub = ARCHITECTURE.md
```

## เอกสาร (อย่าบวม)

- **บังคับ:** `docs/ARCHITECTURE.md` (รวม Doc Policy)  
- **คิว/log:** `IMPROVEMENT_PLAN` · `PHASES`  
- **รายระบบ:** ดูดัชนี §5 ใน ARCHITECTURE — สร้างไฟล์ใหม่เมื่อผ่าน Policy เท่านั้น  
- **Z-MOS:** อย่า copy โปรโตคอลเข้า `docs/` เกม
