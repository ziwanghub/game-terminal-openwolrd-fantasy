# ระบบเทสเกม (Game Testing)

โปรเจกต์ใช้ **pytest** แบ่งชั้นตามความเร็วและความครอบคลุม

```bash
# ทั้งหมด
python3 -m pytest -q

# เฉพาะชั้น
python3 -m pytest tests/unit -q
python3 -m pytest tests/data_validation -q
python3 -m pytest tests/combat -q
python3 -m pytest tests/smoke -q
```

## พีระมิดเทส

| ชั้น | โฟลเดอร์ | ทำอะไร | ความเร็ว |
|------|----------|--------|----------|
| **Unit** | `tests/unit/` | โดเมน: นิสัย สกิล ปาร์ตี้ rarity ดันเจียน ฯลฯ | เร็วมาก |
| **Data validation** | `tests/data_validation/` | YAML ชี้ id ถูกต้อง (มอน/ร้าน/สกิล/ดัน) | เร็ว |
| **Combat** | `tests/combat/` | ไฟต์แบบ seed RNG ไม่ต้องพิมพ์ | เร็ว |
| **Smoke / session** | `tests/smoke/` | เล่นเมนูจริงผ่าน `ScriptedIO` | ปานกลาง |

ตอนนี้ unit ~111 เคส + ชั้นใหม่ด้านบน

## ScriptedIO — หัวใจของเทสเกม

`game/ports/io.py` → `ScriptedIO`

- ใส่รายการคำตอบล่วงหน้า (`inputs`)
- เก็บข้อความทั้งหมดใน `outputs`
- หมด input แล้ว → `EOFError` (กัน loop ค้าง CI)

```python
from game.ports.io import ScriptedIO
from game.services.field_loop import run_field

io = ScriptedIO(["1", "0"])  # พัก แล้วออก
run_field(player, reg, io)
assert "พัก" in io.joined() or io.contains("เซฟ")
```

### Helpers

- `tests/conftest.py` — fixture `reg`, `make_player`, `scripted_io`
- `tests/harness/` — `create_script`, `field_exit_script`, `isolated_saves`, `run_field_session`

Smoke **ต้อง** ใช้ `isolated_saves(monkeypatch, tmp_path)` เพื่อไม่เขียนทับ `saves/` จริง

## รายการเทสที่ควรมี (แผน + สถานะ)

### มีแล้ว (unit — ตัวอย่าง)

- registry / ธาตุ / โลก / ranking
- personality, skill tree, combo, unit mastery
- party + inventory + rarity + shop economy
- dungeon lock / escape / clear
- narrative flavor, equipment, leveling, quests

### มีแล้ว (ชั้นใหม่)

- [x] ScriptedIO + harness
- [x] data integrity (area→monster, shop stock, skill prereq, dungeon refs…)
- [x] combat seed: pick monster, damage, victory, XP, element trend
- [x] smoke: create → rest → quests → exit/save (isolated)

### ควรเพิ่มต่อ (backlog)

| เทส | รายละเอียด |
|-----|------------|
| **Combat IO** | ScriptedIO ใน `_run_combat` (โจมตี/หนี/ยา) |
| **Loot choice** | ชนะไฟต์ → เลือกเก็บ/ทิ้ง |
| **Dungeon session** | เข้าดัน → ชั้นสุ่ม → หนีด้วย item / เคลียร์บอส |
| **Shop buy/sell** | ซื้อ rarity, ภาษีขาย, specialty market |
| **Save/load roundtrip** | เซฟแล้วโหลด field state ครบ |
| **Balance snapshot** | ตาราง XP/ดาเมจ seed คงที่ (regression) |
| **Property / fuzz** | สุ่ม action สั้นๆ แล้ว assert ไม่ crash (HP≥0, money≥0) |
| **Browser/WS** (อนาคต) | เทส adapter เดียวกับ ScriptedIO |

## หลักการ

1. **Domain แยก IO** — เทส unit เรียกฟังก์ชันตรง; smoke ใช้ ScriptedIO เท่านั้น
2. **Seed RNG** — combat/dungeon ใช้ `random.Random(seed)` ให้ซ้ำได้
3. **ไม่ spoil formula ใน assert** — ตรวจทิศทาง/ขอบเขต (ชนะ, เงินเพิ่ม, ref ถูกต้อง) ไม่ hard-code ตัวเลขสมดุลลับ
4. **อย่าเขียน saves จริง** — ใช้ `tmp_path` เสมอใน smoke

## เพิ่มเคสใหม่

```text
tests/unit/test_<feature>.py          # โดเมน
tests/data_validation/test_*.py       # ข้อมูล
tests/combat/test_*.py                # ไฟต์ seed
tests/smoke/test_*.py                 # เมนู + ScriptedIO
```

รันเฉพาะไฟล์: `python3 -m pytest tests/smoke/test_scripted_session.py -q`
