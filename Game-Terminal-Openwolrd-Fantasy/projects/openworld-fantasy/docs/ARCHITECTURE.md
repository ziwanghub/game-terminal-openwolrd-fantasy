# สถาปัตยกรรมระบบ — Open World Fantasy

**เอกสารตัวกลาง (System Architecture Hub)**  
**อ่านเอกสารนี้ก่อน** เมื่อเข้าทีม / ก่อนออกแบบฟีเจอร์ / ก่อน refactor  

| ฟิลด์ | ค่า |
|-------|-----|
| **เวอร์ชันเกม** | 2.21.0-alpha (`wo-worthiness-1`) |
| **สถานะเอกสาร** | Living hub — อัปเดตเมื่อเพิ่มระบบหลัก |
| **เจ้าของ** | ทีม openworld-fantasy |
| **อัปเดตล่าสุด** | 2026-07-14 (onboarding + U prefs) |

---

## 0. เอกสารนี้คืออะไร

| ใช่ | ไม่ใช่ |
|-----|--------|
| แผนที่ระบบทั้งเกม | คู่มือเล่นละเอียดทุกเมนู |
| ชั้นโค้ด + ขอบเขต module | แทนที่ docs รายระบบทุกชิ้น |
| จุดเข้าสำหรับ dev ใหม่ | **Z-MOS governance** (อยู่ `core/` — อย่า copy โปรโตคอลมาที่นี่) |
| กฎขยาย/อัปเกรด + **Doc Policy** | รายการ bug รายวัน |

**วิธีใช้ 15 นาทีแรก**

1. อ่าน §1–3 (หลักการ + แผนที่ + ชั้นโค้ด)  
2. อ่าน **§ Doc Policy** (เมื่อไหร่เขียน / ไม่เขียน doc)  
3. เปิดตาราง §4–5 หา module / doc รายระบบ  
4. รัน `python3 -m game` + `pytest -q` · แก้ตาม §7  

---

## 1. หลักการออกแบบ (Design Principles)

| # | หลัก | ความหมายในโค้ด |
|---|------|----------------|
| P1 | **Domain ไม่ผูก I/O** | `game/domain/*` ไม่ `print`/`input` — รับ/คืนข้อมูล |
| P2 | **Data-driven** | คอนเทนต์ใน `data/**/*.yaml` · logic อ่านผ่าน `DataRegistry` |
| P3 | **Soft / anti-spoiler** | ผู้เล่นไม่เห็นสูตรดิบ · soft label / flavor |
| P4 | **Open / ไม่ตายตัว** | เลเวลไร้เพดาน · เงื่อนไขอาชีพ/ภารกิจแบบ soft OR |
| P5 | **World-shared state** | ตลาด/ภาษี/กระดานใช้ไฟล์ร่วมต่อ `world_id` |
| P6 | **ทดสอบได้** | `ScriptedIO` + pytest · อย่าพึ่ง terminal จริงใน unit test |
| P7 | **Legacy + วิวัฒน์** | instance / list ขนาน · migrate ผ่าน `save_version` |

---

## 2. แผนที่ระบบ (System Map)

```text
                         ┌─────────────────┐
                         │  app.py / menu  │
                         └────────┬────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   field_loop (สนาม)        │
                    │   commands · sights · bag  │
                    └─┬───────┬───────┬───────┬─┘
                      │       │       │       │
           ┌──────────▼─┐  ┌──▼───┐ ┌─▼────┐ │
           │ combat_    │  │bag_  │ │market│ │ mission
           │ session    │  │hub   │ │ +tax │ │ board
           │ (ATB)      │  └──┬───┘ └──┬───┘ └──┬──
           └──────┬─────┘     │        │        │
                  │     domain│  market.json    │
                  ▼           ▼   tax_fund      ▼
           progression · intelligence · equipment · rarity
           item_instances · quests · personality · dungeon
                                  │
                    ┌─────────────▼─────────────┐
                    │ DataRegistry ← data/*.yaml │
                    │ save_service → saves/       │
                    └────────────────────────────┘
```

### วงจรเศรษฐกิจ (สำคัญ)

```text
ลูท/คราฟ → คลัง → ตลาดกลาง (M)
                    │ ภาษี/fee
                    ▼
              tax_fund (ต่อโลก)
                    │ ค่าจ้างประกาศ
                    ▼
           กระดานภารกิจ J (แรงก์ F–SSS)
                    │ รางวัล
                    ▼
              เงิน/XP/ไอเทม → วนใหม่
```

---

## 3. ชั้นโค้ด (Code Layers)

```text
projects/openworld-fantasy/
├── game/
│   ├── app.py              # เมนูหลัก · เข้าโลก
│   ├── config.py           # VERSION · PATH · UI_WIDTH
│   ├── domain/             # ★ logic บริสุทธิ์ (ไม่ I/O)
│   ├── services/           # orchestration + io · field_menus · combat/market
│   ├── ui_terminal/        # ข้อความ · กล่อง · showcase
│   ├── data_load/          # YAML → DataRegistry
│   ├── ports/              # IO Protocol · ScriptedIO · RNG
│   ├── runtime/            # auto_farm
│   └── admin/              # CLI แอดมิน · dashboard ประเมินระบบ
├── data/                   # ★ คอนเทนต์ (YAML) · meta/system_dashboard.yaml
├── saves/{world_id}/       # เซฟตัวละคร + market.json
├── tests/                  # unit / combat / smoke / data_validation
└── docs/                   # เอกสาร (ไฟล์นี้ = hub)
```

| ชั้น | ใส่ได้ | ห้าม |
|------|--------|------|
| **domain** | สูตร, state transform, pure helpers | print, input, path hardcode เกม loop |
| **services** | ลูปเมนู, เรียก domain, เขียน io | สูตรยาวที่ควรอยู่ใน domain |
| **ui_terminal** | format ข้อความ, bar, box | เปลี่ยน state เกมลึก |
| **data** | ตัวเลข/ชื่อ/ตาราง | logic Python |
| **ports** | abstract IO/RNG | business rules |

---

## 4. ระบบหลัก (Catalog)

| ระบบ | โมดูลหลัก | เอกสารลึก | ทางเข้าผู้เล่น |
|------|-----------|-----------|----------------|
| สนาม | `field_loop` + `field_menus` + `field_actions` | UIUX_TEXT | เมนู 1–9 |
| คำสั่ง verb | `domain/commands.py`, `field_commands.py` | COMMAND_AND_INSTANCE_IDS | `f_mn01`, `?` |
| ไฟต์ ATB | multi-ATB · เป้า/* · AoE balance | COMBAT_ATB | เข้าหา / สำรวจ |
| กระเป๋า/เกียร์ | `bag_hub.py`, `inventory_sys.py`, `equipment.py` | BAG_SYSTEM | **5** |
| Instance ของ | `item_instances.py`, `item_codes.py` | COMMAND_AND_INSTANCE_IDS | sw001_xxxx#yyyy |
| Rarity UI | `rarity.py`, `gear_showcase.py` | RARITY, UIUX_TEXT | ดูอุปกรณ์ |
| สเตตัส/พร/อาชีพ | `progression.py`, `blessings.py`, `class_paths.py` | OCCUPATION_STATS_BLESSING | **P** / **C** |
| ความฉลาด | `intelligence.py` | OCCUPATION_STATS_BLESSING | ไฟต์ **6** · NPC ★ |
| ตลาด | `market.py`, `market_service.py` | MARKET | กระเป๋า **M** |
| แดชบอร์ดประเมินระบบ | `admin/dashboard.py` · `data/meta/system_dashboard.yaml` | IMPROVEMENT_PLAN | `python3 -m game.admin.dashboard` · admin **8** |
| สถานการณ์ขอแรง (H0–H4) | `situation.py` · `help_service.py` · ดัน **6** · **G** | HELP_SITUATION_VISION | consent · escrow · friends · rep · log |
| Needs T0+N1–N4 | `domain/needs.py` · combat/atb/consumables | NEEDS_COMBAT_FOOD_VISION | แถบ− · combat · อาหาร |
| Soft Alert Bus | `domain/alerts.py` · `relic.*` / needs / alias | SOFT_ALERT_VISION · RELIC_ALERT_PLAN | soft text · throttle · God log |
| Stat 3-layer | `domain/stat_arch.py` · needs · progression | STAT_ARCHITECTURE | Needs · Core · anima · soft P |
| World Relations | `domain/world_relations.py` · Soft Alert | STAT_ARCHITECTURE | divine/infernal/echo soft |
| Faction Moments | `domain/faction_moments.py` · sights | STAT_ARCHITECTURE §0.8/0.11/0.13 | Mini soft · 9 moments ครบ 8 พื้นที่ |
| Soft Foresight | `domain/soft_foresight.py` | STAT_ARCHITECTURE §0.13 | dungeon prep · world gaze · moment hint |
| Anima × Relic | `domain/relic_anima.py` · Soft Alert | STAT_ARCHITECTURE §0.9–0.15 | lean · Bonds · Chorus · Cap · **area synergy** · auto |
| Divine Burden | `domain/divine_burden.py` · chamber · aura | DIVINE_BURDEN_VISION | ใส่เรลิก · ขวัญ soft · G ห้อง |
| Rank soft (W0) | `world_social.py` · เมนู **3** | WORLD_SERVER_VISION | soft band · rank_board.json |
| ภาษี→ภารกิจ | `mission_board.py`, `mission_service.py` | MISSION_BOARD | กระเป๋า **J** |
| เควสโลก | `quests.py` | (ใน quests.yaml) | **9** |
| ดันเจียน | `dungeon.py`, `dungeon_session.py` | DUNGEON | สายตา dg |
| ปาร์ตี้ | `party.py` (`party_member_turns`) | PARTY_INVENTORY | **Y** · เทิร์นในไฟต์ |
| นิสัย | `personality.py` | PERSONALITY | **N** |
| สถานะผิดปกติ | `status_fx.py` | STATUS | ไฟต์/ยา |
| เซฟ | `save_service.py` | — | **7** |
| ตั้งค่าจอ | `ui_prefs.py` | — | **U** |
| Onboarding | `ui_terminal/help.py` | — | **H** / **T** · ใบ้เมือง |
| Mode Shell | `mode_shell` · `personal_hub` · `shop_hub` | **MODE_SHELL_DESIGN** | สำรวจ·ตัวละคร·ร้าน·ไฟต์ |
| Worthiness lite | `domain/worthiness.py` · loot ceiling · T1/T2 trial | **WO_WORTHINESS_1** | Whisper แมพ · บอสมือ · ของเทพ |
| เทส | `tests/**` | TESTING | `pytest -q` |

---

## 5. ดัชนีเอกสาร (Doc Index)

### บังคับอ่าน (3 ชั้น — อย่าเพิ่มชั้นที่ 4)
| ชั้น | แหล่ง | บทบาท |
|------|--------|--------|
| A | **`ARCHITECTURE.md`** (ไฟล์นี้) | แผนที่ระบบ + Doc Policy + กฎทีม |
| B | `README.md` | รันเกม · เมนูสั้น |
| C | monorepo `../../README.md` + `core/` | **Z-MOS** วินัย session — โปรโตคอลอยู่ที่นี่อย่างเดียว |

### แผนงาน (บาง)
| เอกสาร | บทบาท |
|--------|--------|
| `IMPROVEMENT_PLAN.md` | **คิวงานที่ยังไม่ทำ** + สถานะเฟส (ไม่เก็บ changelog ยาว) |
| `ROADMAP.md` | **แผนพัฒนาหลัก** Wave A–F · ลำดับหีบ/Tama/โลก/online |
| `PHASES.md` | **log เวอร์ชันสั้น** (1–3 บรรทัด/เวอร์ชัน) |
| `TESTING.md` | วิธีเทส / harness |

### รายระบบ (เขียนเมื่อผ่าน Doc Policy เท่านั้น)
| เอกสาร | ระบบ |
|--------|------|
| `BAG_SYSTEM.md` | กระเป๋าหมวด |
| `COMBAT_ATB.md` | แท่งจังหวะไฟต์ |
| `COMMAND_AND_INSTANCE_IDS.md` | คำสั่ง + instance ID |
| `MARKET.md` | ตลาดผู้เล่น |
| `MISSION_BOARD.md` | ภาษี + กระดานแรงก์ |
| `OCCUPATION_STATS_BLESSING.md` | อาชีพ · สเตตัส · พร · ฉลาด · โชค · latent · ห้องสมุด · Unit |
| `UIUX_TEXT.md` | อ้างอิง UI ลึก (หลัก frame อยู่ §1 + code) |
| `RARITY.md` | ระดับของ |
| `STATUS.md` | debuff/buff |
| `SKILL_SYSTEM.md` / `COMBO_UNIT.md` | สกิลคอมโบ |
| `DUNGEON.md` | ดันเจียน |
| `PERSONALITY.md` | นิสัย |
| `WORLD_SOCIAL.md` | โลก social (ของปัจจุบัน) |
| `WORLD_SERVER_VISION.md` | **วิสัยทัศน์** โลก-เซิร์ฟ · echo · อันดับท้าสู้ (W0–W4 · ยังไม่ทำ) |
| `UX_TAMA_VISION.md` | **วิสัยทัศน์** UX แนวทามาก๊อต · needs · เวลา hybrid (T0 ทำแล้ว · T1–T3) |
| `NEEDS_COMBAT_FOOD_VISION.md` | **วิสัยทัศน์** needs→combat/ATB · อาหาร tier · unit soft (N1–N4 ทำแล้ว · N5) |
| `CHEST_LOOT_VISION.md` | **วิสัยทัศน์** หีบ SSS–ธรรมดา · unit unique · ดรอป soft (L0–L5) |
| `ITEM_CONTENT_PLAN.md` | **แผนเฟส** อัปเดตไอเทม/การ์ดทั้งก้อน (IC0–IC6 · แบ่งเฟส) |
| `MONSTER_CONTENT_PLAN.md` | **แผนเฟส** เพิ่มมอนสเตอร์ (MC0–MC6 · ไม่ dump RO) |
| `MONSTER_DROPS.md` | ดรอปต่อมอน soft · card_id |
| `HELP_SITUATION_VISION.md` | **วิสัยทัศน์** ขอแรง · situation บนเซฟ · ร่วมทีมช่วย · escrow (H0–H5 · ยังไม่ทำ) |
| `NARRATIVE.md` | flavor ไฟต์/สนาม |
| `WORKSPACE.md` | ลิงก์ monorepo สั้น (ไม่ซ้ำ Z-MOS) |
| `MODE_SHELL_DESIGN.md` | โหมดสำรวจ/ตัวละคร/ร้าน/ไฟต์ |

### Single source of truth
| ความรู้ | แหล่งเดียว |
|--------|------------|
| วินัย dev / session / preflight | **Z-MOS `core/`** + monorepo README |
| แผนที่ระบบเกม | **ไฟล์นี้** |
| พฤติกรรมละเอียดที่รันได้ | **โค้ด domain + pytest** |
| ตัวเลขคอนเทนต์ | **`data/**/*.yaml`** (ห้าม copy ตารางยาวลง md) |
| คิวงานค้าง | **`IMPROVEMENT_PLAN.md`** |
| Work Order (WO) backlog | **`WO_BACKLOG.md`** |
| แผนพัฒนาหลัก (Wave) | **`ROADMAP.md`** |
| แผนเฟสอัปเดตไอเทม (IC0–IC6) | **`ITEM_CONTENT_PLAN.md`** — อัปครบแต่แบ่งเฟส |
| แผนเฟสเพิ่มมอน (MC0–MC6) | **`MONSTER_CONTENT_PLAN.md`** — เติมครบแต่แบ่งเฟส · ไม่ dump RO |
| วิสัยทัศน์โลก-เซิร์ฟ (W0–W4) | **`WORLD_SERVER_VISION.md`** |
| วิสัยทัศน์ UX-Tama (T0–T3) | **`UX_TAMA_VISION.md`** |
| วิสัยทัศน์ needs combat/อาหาร (N1–N5) | **`NEEDS_COMBAT_FOOD_VISION.md`** |
| วิสัยทัศน์หีบรางวัล (L0–L5) | **`CHEST_LOOT_VISION.md`** |
| วิสัยทัศน์ขอแรง/ช่วย situation (H0–H5) | **`HELP_SITUATION_VISION.md`** |
| คะแนนประเมินระบบ (แดชบอร์ด) | **`data/meta/system_dashboard.yaml`** (+ รัน `game.admin.dashboard`) |
| ประวัติเวอร์ชัน | **`PHASES.md`** (สั้น) |

### นอกโปรเจกต์
| ที่ | บทบาท |
|----|---------|
| `../../core/` (Z-MOS) | วินัยพัฒนา — **ไม่ใช่** logic เกม · **ไม่** แทน ARCHITECTURE |
| `../../design/` | RD ความต้องการ (สเปคระดับ product) |

---

## 6. ข้อมูลและสถานะ (State)

### ต่อตัวละคร (`saves/{world}/{player_id}.json`)
- สถานะเล่น: hp, xp, location, stats, quests  
- กระเป๋า: `inventory_ids` + `inventory_items` (instance) · soft cap `bag_cap` (40)  
- คลังส่วนตัว (WO-Storage-1): `warehouse` { items, money, pass_hash, prefs.auto_stash } · cap 200  

- เกียร์: `equip_ids` + `equip_instances`  
- กระดาน: `mission_rank`, `board_mission`, `mission_*`  
- ตลาด: `market_inbox`  
- สติ: `intel_current` / `intel_max`  
- `save_version` — เพิ่มเมื่อ schema เปลี่ยน · migrate ใน `load_player`

### ต่อโลก (แชร์)
| ไฟล์ | เนื้อหา |
|------|---------|
| `saves/{world}/market.json` | listings, sales_log, **tax_fund**, pending_payouts |

### คอนเทนต์
| path | เนื้อหา |
|------|---------|
| `data/items/` | ไอเทม |
| `data/monsters/` | มอน |
| `data/areas/` | พื้นที่ |
| `data/occupations/` | อาชีพ + class_paths |
| `data/missions/board.yaml` | ภารกิจกระดาน |
| `data/blessings/` | พร |
| `data/rarity/` | ระดับ |
| `data/quests/` | เควสโลก |

---

## Doc Policy (หยุดเอกสารบวม)

**หลัก:** Z-MOS ≠ docs เกม · อย่าเขียนสองที่เรื่องเดียวกัน

### เมื่อไหร่ *ไม่* เขียนไฟล์ `.md` ใหม่
- ฟีเจอร์เล็ก / แก้บั๊ก / ปรับตัวเลข YAML  
- แค่เพิ่มเมนูหรือข้อความ UI  
- สิ่งที่อธิบายได้ใน **1 แถว §4** + เทส 1–2 เคส  
- โปรโตคอล dev (session, preflight, trust) → ชี้ `core/` เท่านั้น

### เมื่อไหร่ *เขียนหรืออัป* doc ระบบ
อย่างน้อย **1** ข้อ:
1. กฎซ่อน / soft formula / anti-spoiler ที่พลาดง่าย  
2. state ข้ามไฟล์หรือข้ามเซฟ (เช่น `market.json` + tax + board)  
3. instance / dual schema / migrate  
4. คนใหม่เปิดโค้ดแล้วเข้าใจผิดใน ~10 นาที  

ถ้าผ่านเกณฑ์ → อัป doc เดิมก่อน · **สร้างไฟล์ใหม่เมื่อเป็นระบบคนละโดเมนจริงๆ**

### ขั้นต่ำเมื่อเพิ่มระบบ (แทน “md ทุกครั้ง”)
1. แถวใน **§4 Catalog**  
2. เทสที่เกี่ยว  
3. `PHASES.md` 1–3 บรรทัด + `config.APP_VERSION` ถ้าปล่อยเวอร์ชัน  
4. doc ลึก — **เฉพาะเมื่อ** ผ่านเกณฑ์ด้านบน

### ห้ามซ้ำ Z-MOS
- ห้าม copy execution loop / trust tier / `zcl` ลง `docs/*` เกม  
- `WORKSPACE.md` = ลิงก์สั้น · รายละเอียดอยู่ monorepo README  
- Z-MOS เต็ม (gates บังคับทุก mutate) = เฟส Later — **ยังไม่ใช้ควบคุม logic เกม**

---

## 7. กฎสำหรับทีม (ทำงานเหมือนเจ้าของระบบ)

### เพิ่มฟีเจอร์
1. ตรวจ **Doc Policy** — ส่วนใหญ่แค่ §4 + เทส  
2. Logic → `domain/` · เมนู/io → `services/`  
3. ตัวเลขที่ดีไซน์ปรับบ่อย → YAML (ไม่ dump ลง md)  
4. อย่าโชว์สูตรดิบใน UI (ใช้ soft label)  
5. เพิ่มเทสใน `tests/unit/` หรือ smoke  
6. ถ้าแตะเซฟ → เพิ่ม `save_version` + migrate ใน `load_player`  
7. ปล่อยเวอร์ชัน → `PHASES.md` สั้น + `config.APP_VERSION`  
8. คิวค้าง → `IMPROVEMENT_PLAN.md` เท่านั้น (ไม่เขียนซ้ำใน PHASES)

### ห้าม
- ใส่สูตรยาวใน `field_loop` ถ้าแยก domain ได้  
- Commit เซฟผู้เล่นจริง / ข้อมูล sensitive  
- ผูกเกมกับ Z-MOS gates แบบบังคับรันเล่นไม่ได้  
- เดาเป้าอัตโนมัติเมื่อกำกวม (คำสั่ง/หลายชิ้น) — list หรือ error ชัด  
- สร้าง `.md` ใหม่ “เพราะเคยทำแบบนั้น” โดยไม่ผ่าน Doc Policy  
- คัดลอกตาราง YAML ยาวเข้า docs  

### Definition of Done (ขั้นต่ำ)
- [ ] pytest ที่เกี่ยวผ่าน  
- [ ] soft UI ไม่สปอยล์สูตรหลัก  
- [ ] แถว §4 อัปแล้ว (doc ลึกถ้าผ่าน Policy)  
- [ ] ไม่พัง save เก่า (migrate หรือ default)

---

## 8. จุดเสี่ยงที่เจ้าของระบบต้องรู้

| ความเสี่ยง | รายละเอียด | แนวทาง |
|------------|------------|--------|
| **Dual inventory** | `inventory_ids` + `inventory_items` | ระยะยาว: instance เป็น source of truth |
| **field_loop ใหญ่** | เมนูรวมศูนย์ | แยก service ต่อเมนูต่อ |
| **ความซับซ้อน UX** | ระบบเยอะ | onboarding เมือง / tutorial ต่อระบบ |
| **ตลาด multi-save** | ไม่มี lock ไฟล์ realtime | เหมาะ offline async · ระวัง concurrent write |
| **บาลานซ์ tax/mission** | กองทุน vs รางวัล | จูน `wage_cost` / fee ใน data |

---

## 9. ลำดับอ่านโค้ด (onboarding ทางเทคนิค)

```text
1. game/config.py
2. game/app.py → world_service / field_loop
3. game/data_load/registry.py
4. game/ports/io.py (ScriptedIO)
5. game/domain/character.py + progression.py
6. game/services/bag_hub.py + market_service.py
7. game/services/combat_session.py + combat_atb.py
8. tests/harness + tests/unit/*
```

---

## 10. Changelog เอกสารนี้

| วันที่ | หมายเหตุ |
|--------|----------|
| 2026-07-14 | สร้าง ARCHITECTURE.md เป็น hub กลางครั้งแรก (1.13.1) |
| 2026-07-14 | **Doc Policy** · single source · ดัชนี 3 ชั้น · แยก Z-MOS ชัด · ยุบ docs ซ้ำ |
| 2026-07-14 | ลิงก์ **WORLD_SERVER_VISION** (W0–W4) ในดัชนี + plan |
| 2026-07-14 | ลิงก์ **UX_TAMA_VISION** (T0–T3) ในดัชนี + plan |
| 2026-07-14 | แดชบอร์ดระบบเกม 1.13.11 · `admin/dashboard` · YAML scores |
| 2026-07-14 | ลิงก์ **HELP_SITUATION_VISION** (H0–H5) ในดัชนี + plan |
| 2026-07-14 | **H0** `situation.py` · consent ในดัน 1.13.12 |
| 2026-07-14 | **H1–H3** กระดาน G · escrow · assist 1.13.13 |
| 2026-07-14 | **H4** friends policy · help_rep · world_signals · เควส 1.13.14 |
| 2026-07-14 | **T0** needs · **W0** rank soft 1.13.15 |
| 2026-07-14 | **N1–N4** needs combat/อาหาร 1.13.16 |

---

*เมื่อสงสัย “ระบบนี้เชื่อมกับอะไร” → เริ่มจากไฟล์นี้ แล้วตามลิงก์ §5*  
*เมื่อสงสัย “ต้องเขียน doc ไหม” → Doc Policy ด้านบน*
