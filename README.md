# Game Terminal — Open World Fantasy

เกมแฟนตาซี open skill / open world แบบ **ข้อความใน Terminal** (ยังไม่มีกราฟิก)

## โครงสร้าง

```text
Game-Terminal-Openwolrd-Fantasy/
├── core/          # Z-MOS governance (lite) — ไม่ใช่โค้ดเกม
├── design/        # RD / สเปค
└── projects/
    └── openworld-fantasy/   # ★ เกมจริง (Python)
```

## รันเกม (ปัจจุบัน)

```bash
cd Game-Terminal-Openwolrd-Fantasy/projects/openworld-fantasy
python3 -m game
python3 -m pytest -q
```

ต้องการ Python 3.9+ · `pip install -e ".[dev]"` (PyYAML, pytest)

**เวอร์ชันเกม:** ดู `projects/openworld-fantasy/game/config.py`  
(ปัจจุบัน: `1.13.10-alpha` · `aoe-pack-balance`)

## CI

GitHub Actions: `.github/workflows/ci.yml`  
รัน `pytest` บน `projects/openworld-fantasy` ทุก push/PR ไป `main`

## Remote

```text
git@github.com:ziwanghub/game-terminal-openwolrd-fantasy.git
```

## บทบาทโฟลเดอร์

| ที่ | บทบาท |
|----|--------|
| `projects/openworld-fantasy` | โค้ดเกม · data · tests |
| `core/` | Z-MOS lite (วินัย dev) — อย่าใส่ logic เกม |
| `design/` | เอกสารความต้องการ |

รายละเอียด: `Game-Terminal-Openwolrd-Fantasy/projects/openworld-fantasy/docs/ARCHITECTURE.md`
