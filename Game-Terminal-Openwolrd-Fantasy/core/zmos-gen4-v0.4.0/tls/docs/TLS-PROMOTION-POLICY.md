# TLS Promotion Policy
**Version:** 1.0
**System:** Z-MOS v1.4.0 — TLS
**Scope:** Governance for Template Admission and Promotion

---

## 1. Core Principles

### Project ≠ Template
- **Project**: เป็น "ผลผลิต" (Instance) ที่มีข้อมูลลูกค้า แผนก และการตั้งค่าเฉพาะตัว
- **Template**: เป็น "พิมพ์เขียว" (Blueprint) ที่เก็บเฉพาะโครงสร้างและตรรกะที่พิสูจน์แล้ว
- **TLS**: เป็น Knowledge Asset Layer ที่แยกออกจาก Project Runtime โดยสิ้นเชิง

### Separation Rule
- **No Auto-Sync**: ห้ามทำการ Sync อัตโนมัติระหว่าง Project และ Template
- **Manual Extraction**: การเปลี่ยน Project ให้เป็น Template ต้องผ่านกระบวนการ Extraction ที่มีการตรวจสอบ (Sanitization) เสมอ
- **Read-Only Blueprint**: Template ใน TLS เป็น Read-Only สำหรับโปรเจค เวลานำไปใช้ต้อง Copy ออกไปเท่านั้น

---

## 2. Source & Candidate Definitions

- **Source Project**: โปรเจคที่ใช้งานจริงซึ่งเป็นต้นแบบ (e.g., `massageV1-zmos-coreV0.2.2`)
- **Template Candidate**: ชุดไฟล์ที่ถูก Extract ออกมาและส่งเข้าพิจารณาใน TLS (e.g., `landing-premium-massage-v1`)

---

## 3. Extraction Rules (Sanitization)

กระบวนการ Extract ต้องทำสิ่งต่อไปนี้อย่างเคร่งครัด:

1. **Remove Client Data**: ลบชื่อร้าน, ข้อมูลติดต่อจริง, ข้อมูลลูกค้า, และรูปภาพเฉพาะของลูกค้า
2. **Remove Secrets**: ลบ API Keys, Passwords, Token, และ Environment Variables ทั้งหมด
3. **Normalize Config**: แทนที่ค่าใน config ด้วย Placeholder หรือค่า Default (สร้าง `config.default.json`)
4. **Isolate Reusable Code**: แยก Code ส่วนที่เป็น Business Logic ทั่วไปออกจากส่วนที่ Custom เฉพาะเคส
5. **Create Manifest**: สร้าง `template.json` ที่ระบุแหล่งที่มาและจุดประสงค์ชัดเจน
6. **Apply Schema**: ตรวจสอบว่าโครงสร้างตรงกับ `template.schema.json`

---

## 4. Status Promotion Rules

### Stage 1: `draft` → `tested`
**เงื่อนไข:**
- [ ] มี Source Code ครบถ้วนใน `src/`
- [ ] รัน `npm run build` (หรือเทียบเท่า) ผ่านโดยไม่มี Error
- [ ] รันได้ใน Development Environment (Local)
- [ ] สามารถ Inject Config ใหม่ลงไปแล้วระบบทำงานได้ตามคาด
- [ ] QA ผ่าน

### Stage 2: `tested` → `proven`
**เงื่อนไข:**
- [ ] ≥ 1 real project (ถูกส่งไปใช้กับลูกค้าจริง)
- [ ] ≥ no P1 bug (ไม่มี P1 Critical Bugs)
- [ ] ≥ real usage evidence (NOT time only - ต้องมีหลักฐานการใช้งานจริง ห้ามอ้างอิงแค่ระยะเวลา)
- [ ] Core User Journey (เช่น การจอง, การชำระเงิน) ทำงานได้เสถียร

### Stage 3: `proven` → `stable`
**เงื่อนไข:**
- [ ] ถูกใช้ซ้ำในโปรเจคที่แตกต่างกันอย่างน้อย 2 ราย (≥ 2 Use Cases)
- [ ] ไม่มี Regression Issue เมื่อมีการอัปเดต minor version
- [ ] สามารถปรับแต่งผ่าน Config ได้ทั้งหมดโดยไม่ต้องแก้ Source Code (Zero-code Customization)

### Stage 4: `stable` → `deployable`
**เงื่อนไข:**
- [ ] ผ่านการทดสอบ `zcl tls create` และรันได้ทันทีโดยไม่ต้องแก้ Code
- [ ] มี Automated Test ครอบคลุมฟังก์ชันหลัก
- [ ] พร้อมสำหรับการสร้างโปรเจคใหม่แบบ Auto-pilot

---

## 5. Decoupling & Modification Rule

- **Independent Updates**: การอัปเดต Project ไม่ถือเป็นการอัปเดต Template โดยอัตโนมัติ
- **Template Update Protocol**: การแก้ Template ต้องทำผ่านกระบวนการ:
  1. Review Requirement
  2. Re-extract (หากมี code ใหม่จาก project)
  3. Re-validate (Schema + Build)
  4. Version Bump (SemVer)

---

## 6. Anti-Corruption Rules (ห้ามเด็ดขาด)

- ❌ **Direct Copy**: ห้าม Copy folder project ทั้งหมดเข้า TLS โดยไม่ผ่านกระบวนการ Extraction
- ❌ **State Leakage**: ห้ามเก็บไฟล์ `.z-mos/state/` หรือ `runtime-state.json` ใน TLS
- ❌ **Hardcoded Config**: ห้าม Hardcoded ข้อมูลที่ควรอยู่ใน config ลงใน source code ของ template
- ❌ **Sensitive Info**: ห้ามเก็บเบอร์โทรศัพท์จริง, ที่อยู่จริง หรือบัญชีโซเชียลจริงของลูกค้าใน TLS
