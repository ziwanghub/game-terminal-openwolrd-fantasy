# Version log (สั้น)

**รูปแบบ:** 1–3 บรรทัดต่อเวอร์ชัน · รายละเอียดระบบอยู่ `ARCHITECTURE.md` + doc รายระบบ  
**คิวงานค้าง:** `IMPROVEMENT_PLAN.md` เท่านั้น  
**เวอร์ชันปัจจุบัน:** `1.13.10-alpha` (`aoe-pack-balance`) — ดู `game/config.py`

---

| เวอร์ชัน | สรุป |
|----------|------|
| **1.13.10** | บาลานซ์ AoE/กลุ่ม · splash diminishing · soft kill XP · spawn กลุ่มตามเลเวล |
| **1.13.9** | เป้า `*` ทั้งกลุ่ม · สกิล AoE · เควส/คราฟ/สกิล bulk |
| **1.13.8** | multi-ATB กลุ่มพร้อมกัน + เลือกเป้า · มอน/ไอเทม bulk · เมือง pool เบา |
| **1.13.7** | Phase D tutorial 7 หน้า · campaign รอบ 2 · กระดาน void · pack roster |
| **1.13.6** | Mode Shell B+C: `shop_hub` · สำรวจ 6=ร้าน · ไฟต์เมนูสั้น · เมืองเริ่ม soft |
| **1.13.5** | Mode Shell A: EXPLORE สั้น · PERSONAL hub (5/I) · `mode_shell` · hotkey alias |
| **1.13.4** | เควส campaign/รอบโลก · ไอเทม pack · `field_actions` · `run_combat_wave` · สายกระดานผลึก |
| **1.13.3** | instance SoT · `field_menus` · ปาร์ตี้ AI เทิร์น · chain กระดาน · multi-ref list |
| **1.13.2** | H/T ครอบคลุม ATB·ตลาด·กระดาน·สติ · ใบ้เมือง · เมนู **U** · แผงชนะ XP ครบ · จูน wage |
| **1.13.1** | ภาษีตลาด → `tax_fund` · กระดานภารกิจ F–SSS · **J** · `MISSION_BOARD` |
| **1.13.0** | ตลาด P2P ต่อโลก · **M** · `MARKET` |
| **1.12.2** | สติใช้ได้ (ATB / NPC ★) · ฟื้นพัก/เวลา/ไอเทม |
| **1.12.1** | Combat ATB · `COMBAT_ATB` |
| **1.12.0** | vagabond · สเตตัส/พร/ทางอาชีพ **C** · `OCCUPATION_STATS_BLESSING` |
| **1.11.1** | instance persist · bag verbs equip/use/socket |
| **1.11.0** | verb_target · sight handles · instance layer |
| **1.10.4** | short codes `sw001` · ถอด/ขาย/ทิ้งของสวม |
| **1.10.3** | gear showcase ตาม rarity |
| **1.10.2** | bag hub หมวด · `BAG_SYSTEM` |
| **1.10.1** | แก้ loot id · sanitize inventory · kill quest backfill |
| **1.10.0** | Stabilize I–IV (แยก loop · playfeel · content · depth) |
| **1.9.4** | แยก combat/consumable/encounter/dungeon session |
| **1.9.1–1.9.3** | status_fx debuff/buff · `STATUS` |
| **1.9.0** | Text UI L1c · chrome · `UIUX_TEXT` |
| **1.8.2** | ScriptedIO · pytest harness · `TESTING` |
| **1.8.x** | ดันเจียน · `DUNGEON` |
| **1.7.x** | rarity tiers · `RARITY` |
| **1.6.x** | combo/unit · narrative ไฟต์/สนาม |
| **1.5.0** | ปาร์ตี้ + inventory ลึก |
| **1.4.0** | skill tree S1 · `SKILL_SYSTEM` |
| **≤1.3** | foundation · worlds · combat base · soft death คลื่นบาลานซ์ |

### เอกสาร hygiene (ไม่ bump เกม)

| วันที่ | |
|--------|--|
| 2026-07-14 | Doc Policy ใน `ARCHITECTURE` · ยุบ occupation docs · ย่อ PHASES/PLAN/WORKSPACE |

```bash
python3 -m game
python3 -m pytest -q
```
