# RD Index — Open World Fantasy (Terminal)

**ผลิตภัณฑ์:** เกมแฟนตาซี open world / open skill แบบข้อความใน Terminal  
**โปรเจกต์โค้ด:** `projects/openworld-fantasy/`  
**อัปเดตล่าสุด:** 2026-07-14  

## แผนที่เอกสาร (จัดใหม่ให้ตรงเกม — ไม่ใช่เว็บไซต์)

| รหัส | ไฟล์ | หัวข้อเกม | สถานะ |
|------|------|-----------|--------|
| 00 | `00-rd-index.md` | สารบัญ RD | Draft |
| 01 | `01-project-overview.md` | ภาพรวมเกม วิสัยทัศน์ ขอบเขต | Draft |
| 02 | `02-business-requirements.md` | เป้าหมายผลิตภัณฑ์ / ความสำเร็จ | Draft |
| 03 | `03-user-personas.md` | ผู้เล่นเป้าหมาย | Draft |
| 04 | `04-user-journey.md` | เส้นทางเล่นหลัก | Draft |
| 05 | `05-functional-requirements.md` | ฟังก์ชันระบบเกม | Draft |
| 06 | `06-non-functional-requirements.md` | ประสิทธิภาพ เสถียร รองรับ | Draft |
| 07 | `07-page-structure.md` | โครงสร้างจอ/โหมด Terminal (เนื้อหาใหม่ แทน page เว็บ) | Draft |
| 08 | `08-section-requirements.md` | โมดูลระบบเกม (เนื้อหาใหม่) | Draft |
| 09 | `09-ui-ux-requirements.md` | UI ข้อความ ASCII Spotlight | Draft |
| 10 | `10-responsive-requirements.md` | ความเข้ากันได้ Terminal/SSH (จะเขียนทับ) | Stub→เกม |
| 11 | `11-pwa-requirements.md` | เซฟท้องถิ่น / ออฟไลน์ (เนื้อหาใหม่ แทน PWA) | Draft |
| 12–15 | เดิม SEO/Ads/Analytics | **นอกขอบเขต v1** | N/A v1 |
| 16 | `16-content-requirements.md` | คอนเทนต์พื้นที่ มอน สกิล ศิลป์ | Draft |
| 17 | `17-data-schema-requirements.md` | โครง data ไฟล์ / เซฟ | Draft |
| 18 | `18-technical-architecture.md` | สถาปัตย์เทคนิค | Draft |
| 19 | `19-terminal-ui-architecture.md` | สถาปัตย์ชั้น UI Terminal | Draft |
| 20 | `20-deployment-requirements.md` | รัน แจก จิท | Draft |
| 21 | `21-security-requirements.md` | เซฟ แอดมิน ไม่เก็บ secrets | Draft |
| 22 | `22-performance-requirements.md` | เป้าหมาย latency โหลด | Draft |
| 23 | `23-testing-requirements.md` | แผนทดสอบ | Draft |
| 24 | `24-phase-roadmap.md` | เฟส P0–P11 | Draft |
| 25 | `25-open-issues.md` | ประเด็นค้างตัดสินใจ | Draft |

## ชุด RD แกนที่ควรล็อกก่อนโค้ด (Batch A)

1. **01** ภาพรวม  
2. **05** ฟังก์ชัน  
3. **09** UI/UX  
4. **17** Data schema  
5. **18** สถาปัตย์  
6. **24** Roadmap  

## ชุดถัดไป (Batch B)

03 Personas · 04 Journey · 07 Screens · 08 Systems · 16 Content · 25 Open issues  

## เอกสารเว็บเดิมที่เลิกใช้กับเกมนี้

ไฟล์ชื่อเดิม `07-page-structure`, `10-responsive`, `11-pwa`, `12-seo`, … จะ **เขียนทับ/เปลี่ยนชื่อความหมาย** ให้เป็นเกม หรือติดป้าย N/A  
ห้ามอ่านราวกับเป็นสเปคเว็บไซต์

## กฎการแก้ RD

- เปลี่ยนพฤติกรรมเกมที่ผู้เล่นเห็น → อัป RD ก่อนหรือคู่กับโค้ด  
- ใส่สถานะท้ายเอกสาร: Draft | Approved | Deprecated  
- โค้ดขัด RD ที่ Approved → ถือว่าบั๊กหรือต้องเปลี่ยน RD อย่างเป็นทางการ  
