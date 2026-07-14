# RD-08: โมดูลระบบเกม (Game Systems)

**สถานะ:** Draft  
**ชื่อเดิม:** Section Requirements (เว็บ) → **ระบบเกม**

---

## 1. วัตถุประสงค์

แยกระบบย่อยให้ทีม/เฟสรับผิดชอบชัด ผูกกับ FR ใน RD-05

## 2. แผนที่ระบบ

| ระบบ | หน้าที่ | เฟสหลัก |
|------|---------|---------|
| Character | สร้างตัว สถานะ อาชีพ ราศี | P0–P2 |
| World/Area | พื้นที่ เชื่อมต่อ unlock mastery | P1, P8 |
| Encounter | สำรวจ เข้าหา หีบ ซุ่ม | P8 |
| Combat | เทิร์น สกิล คอมโบ มานา | P5 |
| Elements | matchup fusion ซ่อน | P6 |
| Defense | ท่ากันแพ้ทาง | P7 |
| Status/Vitals | regen พิษ ยา | P3 |
| Economy | เงิน ร้าน | P3–P4 |
| Equipment/Cards | เกียร์ ช่องการ์ด | P4 |
| Progression | XP% เลเวล | P4 |
| Knowledge/Journal | สิ่งที่ค้นพบ | P6–P8 |
| Save | เซฟโหลด | P2 |
| Presentation | L0–L2 ASCII | P0–P3 |
| Runtime | ออโต้ ไทม์เมอร์ | P9 |
| Admin | โลก รีเซ็ต | P10 |

## 3. ขอบเขตความรับผิดชอบ (อย่าปน)

- Combat **คำนวณ** ใน domain; UI **แสดงผลเท่านั้น**  
- Elements อ่านจาก data ไม่ hardcode คู่ธาตุใน UI  
- Encounter สุ่มจากตาราง data  

## 4. ประวัติ

| วันที่ | หมายเหตุ |
|--------|----------|
| 2026-07-14 | แปลงเป็นแผนที่ระบบเกม |
