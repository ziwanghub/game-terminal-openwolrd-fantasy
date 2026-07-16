# WO-028 — Human Playtest Round (หลัง Relic Depth)

| ฟิลด์ | ค่า |
|--------|-----|
| **WO** | WO-028 |
| **เวอร์ชัน** | `1.73.0-alpha`+ |
| **เป้า** | ยืนยัน mid-relic path + Chamber + ลูปพื้นที่บนเซฟจริง/harness |
| **ขึ้นกับ** | WO-026 guide · WO-027 depth |

**ผล harness:** `exports/WO028_PLAYTEST_LOG.md`  
**รัน:** `python3 scripts/wo028_playtest_harness.py`

---

## 1. เป้า playtest (มือ ~60–90 นาที)

| Block | ทำ | ผ่านเมื่อ |
|-------|-----|----------|
| **P1 Bootstrap** | เซฟใหม่ · บทเรียน 9 · Auto Policy เปิด | รู้ G / B / ภาระ |
| **P2 Forest loop** | ป่ามืด สำรวจ+ไฟต์ · เควส forest_walker / champion path | อยากกลับป่า |
| **P3 Early relic** | weight_of_storm หรือ ห้อง G ยืม storm/hell | ใส่ได้ · ขวัญกด · ถอดได้ |
| **P4 Chamber** | G → ยืม → spar 2–3 · 7 สรุป · 6 ออก | เงินไม่เพิ่ม · สรุปชัด |
| **P5 Mid path (soft)** | รู้เควส เถ้าโลกันตร์ / หักปริซึม (แม้ยังไม่เคลียร์) | เควสโผล่ในรายการเมื่อปลด |
| **P6 Marsh loop** | ไปหนองหมอก · side quest ใหม่ | flavor + เหตุผลกลับ |
| **P7 Economy** | ใส่ crush แล้ว auto/มือ 3 ไฟต์ | เงินได้แต่แผ่ว · ไม่พัง |

---

## 2. แบบบันทึกมือ (คัดลอก)

```markdown
### รอบ WO-028 · วันที่ · เวอร์ชัน

| Block | ผ่าน | โน้ต | P1/P2/P3 |
|-------|:----:|------|----------|
| P1 | ☐ | | |
| P2 Forest | ☐ | | |
| P3 Relic | ☐ | | |
| P4 Chamber | ☐ | | |
| P5 Mid path | ☐ | | |
| P6 Marsh | ☐ | | |
| P7 Economy | ☐ | | |

Feel 1–5: ภาระ__/5 Chamber__/5 ลูปป่า-หนอง__/5 Economy__/5
Hotfix ต้องการ: …
```

---

## 3. Acceptance WO-028

- [x] คู่มือ playtest มือ  
- [x] Harness ตรวจ mid-relic quest graph + chamber + burden economy  
- [x] Export log  
- [x] Test Run เมนู shortcut (optional H)  

---

## 4. Changelog

| วันที่ | เหตุการณ์ |
|--------|-----------|
| 2026-07-15 | สร้าง WO-028 guide + harness |
