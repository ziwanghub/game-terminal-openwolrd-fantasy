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

**เวอร์ชันเกม:** ดู `Game-Terminal-Openwolrd-Fantasy/projects/openworld-fantasy/game/config.py`  
(ปัจจุบัน: `1.48.0-alpha` · `solo-polish-post-cm` — Skill Rank · Combo Mind · MI)

## CI

GitHub Actions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)  
- ทุก **push / PR** ไป `main`  
- `pip install -e ".[dev]"` แล้ว `pytest -q` ใน `openworld-fantasy`  
- แสดง `APP_VERSION` หลังเทส

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
