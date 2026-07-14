# RD-24: Phase Roadmap

**สถานะ:** Draft  
**ผลิตภัณฑ์:** Open World Fantasy (Terminal)

---

## 1. วัตถุประสงค์

แบ่งงานพัฒนาเป็นเฟสที่ส่งมอบเล่นได้ทีละขั้น ผูกกับ Functional Requirements (RD-05)

## 2. หลักการ

- ทำ `projects/openworld-fantasy` เท่านั้นสำหรับฟีเจอร์เกม  
- `core` = governance ไม่ใช่เฟสเกม  
- แต่ละเฟสจบเมื่อ: เล่นตรวจได้ + เทสต์หลักผ่าน (เมื่อมี) + ไม่ทำลายเซฟโดยไม่มี migrator  

## 3. ตารางเฟส

| เฟส | ชื่อ | ส่งมอบหลัก | FR หลัก |
|-----|------|------------|---------|
| **P0** | Foundation | โครงแพ็กเกจ, แยก domain/UI, เล่น prototype ผ่าน `-m game`, UI L0/L1 | FR-CHAR-02, FR-UI-01 |
| **P1** | Data + Art | โหลด YAML พื้นที่/มอน/สกิล, art_loader, ดูภาพเบื้องต้น | FR-WORLD-01, FR-UI-02 |
| **P2** | Save | เซฟ/โหลด เลือกตัว, ui_prefs, save_version | FR-CHAR-03, FR-SAVE-* |
| **P3** | Vitals + Shop pot + Spotlight | regen, status, ร้านยา, Spotlight ของหายาก | FR-VIT-*, FR-UI-04 |
| **P4** | Level + Gear + Cards | XP%, ร้านเกียร์, ช่องการ์ด | FR-LVL-*, FR-ECO-* |
| **P5** | Combat core | สกิลเลข คอมโบ มานา โลดาเมจ | FR-CBT-01..04,10 |
| **P6** | Elements + Journal | matchup fusion knowledge | FR-CBT-05,06 FR-ENC-05 |
| **P7** | Defense matchups | เฟสกัน strong/weak | FR-CBT-07,09 |
| **P8** | Risk world | unlock พื้นที่ ??? เข้าหา หีบ silhouette | FR-WORLD-02..04 FR-ENC-* |
| **P9** | Runtime | auto-farm pause timer | FR-RT-* |
| **P10** | Multi-world + Admin | เลือกโลก สร้างโลก รีเซ็ต | FR-CHAR-04 FR-ADM-* FR-WORLD-06 |
| **P11** | Polish | บาลานซ์ QA เนื้อหา เอกสารผู้เล่น | ทั้งหมดที่ค้าง |

## 4. ไมล์สโตนผู้เล่น

| Milestone | เฟส | ความรู้สึก |
|-----------|------|-----------|
| M1 | P0–P1 | เล่นจากโครง+data |
| M2 | +P2 | เซฟได้ |
| M3 | +P3–P4 | อยู่รอด โต ใส่การ์ด |
| M4 | +P5–P7 | ไฟต์ลึก |
| M5 | +P8 | โลกเสี่ยง + ASCII มอน |
| M6 | +P9–P11 | ออโต้ หลายโลก พร้อมเล่นยาว |

## 5. พึ่งพา

```text
P0 → P1 → P2 → (P3 ∥ P4 หลัง P2) → P5 → P6 → P7 → P8 → P9 → P10 → P11
```

ห้ามเริ่ม P8/P9 ก่อน P1+P2 เสถียร

## 6. Definition of Done ต่อเฟส

- [ ] พฤติกรรมตรง RD-05 ที่ระบุในเฟส  
- [ ] ไม่ regress ฟีเจอร์เฟสก่อนหน้าที่ Approved  
- [ ] อัป docs/PHASES หรือ changelog สั้นในโปรเจกต์  
- [ ] (ตั้งแต่ P2) เซฟเก่า migrate หรือประกาศ breaking ชัด  

## 7. สถานะปัจจุบัน (ณ ร่างนี้)

| รายการ | สถานะ |
|--------|--------|
| Prototype เล่นได้ | มี (เมนู 9 legacy) |
| เอนจิน data-driven | **P0–P8 หลักใช้งาน** (เมนู 1–2) |
| Data YAML | areas/monsters/skills/items/levels/fusions/encounters |
| เลเวลไม่จำกัด + XP scale | มี |
| คอมโบ + ป้องกันแพ้ทาง + ??? สนาม | มี (v0.3.0) |
| RD ชุดนี้ | Draft |

## 8. ประวัติ

| วันที่ | หมายเหตุ |
|--------|----------|
| 2026-07-14 | Draft จัดเฟส P0–P11 |
