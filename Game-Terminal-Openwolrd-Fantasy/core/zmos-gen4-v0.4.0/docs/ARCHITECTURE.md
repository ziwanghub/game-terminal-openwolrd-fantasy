# ARCHITECTURE.md

# Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial" — Architecture Overview

## System Goal

Z-MOS เป็น **Deterministic Governance Runtime** สำหรับ AI Agents โดยป้องกันการทำงานที่ไม่ปลอดภัยด้วยการบังคับใช้ Truth-First และ Fail-Closed โดยสมบูรณ์

ทุกการกระทำของ Agent ต้องผ่านการตรวจสอบอย่างเข้มงวดก่อนจึงจะได้รับอนุญาตให้ทำงานจริง

## Core Principles

- **Truth-First**: ระบบต้องรู้สถานะความจริงของโลกก่อนทำการใด ๆ
- **Fail-Closed**: ถ้าข้อมูลไม่ครบหรือตรวจสอบไม่ผ่าน จะบล็อกการทำงานทันที
- **Agent-Centric**: ออกแบบมาเพื่อให้ AI Agent ทำงานร่วมกันได้อย่างมีวินัย
- **Single Source of Truth**: ทุกอย่างอ้างอิงเวอร์ชันจาก `sdk/version.ts` เพียงที่เดียว

## Core Components

- **`sdk/version.ts`** — Single Source of Truth ของเวอร์ชันทั้งระบบ
- **`runWithIntent()`** — ฟังก์ชันหลักและหัวใจของระบบ (Primary Execution Gate)
- **`intent.card.json`** — กำหนดขอบเขตและกฎการทำงานของ Agent
- **`truth.contract.json`** — สถานะความจริงของระบบ ณ ขณะนั้น
- **`trace-integrity.jsonl`** — บันทึกการตัดสินใจทุกครั้งแบบไม่สามารถแก้ไขได้

## Execution Flow

1. Agent เรียก `runWithIntent({ action, handler, agentContext })`
2. Runtime โหลดและตรวจสอบ `intent.card.json` + `truth.contract.json`
3. ประเมิน Hard-Block Conditions ทั้งหมด
4. ถ้าผ่านทุกเงื่อนไข → เรียก `handler()` ให้ทำงาน
5. บันทึกผลลัพธ์และ Trace

## Hard-Block Conditions

ระบบจะบล็อกทันทีเมื่อ:
- Truth verdict ไม่ใช่ `SAFE_TO_CONTINUE`
- Tool หรือ Action ไม่อยู่ใน allow list
- การกระทำอยู่นอกขอบเขตที่กำหนดใน Intent
- ไฟล์ authority ใดไฟล์หนึ่งเสียหายหรือหายไป

## Authority Hierarchy

1. Runtime Truth (truth.contract.json)
2. Execution Intent (intent.card.json)
3. SDK Governance Layer (`runWithIntent()`)
4. Agent Business Logic

## Version Management

ทุกไฟล์ต้องอ้างอิงเวอร์ชันจาก `sdk/version.ts` เพียงไฟล์เดียว ห้าม hardcode เวอร์ชันโดยเด็ดขาด
