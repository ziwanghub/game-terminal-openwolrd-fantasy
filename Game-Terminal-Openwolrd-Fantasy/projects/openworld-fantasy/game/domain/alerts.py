"""
WO-033 Soft Alert Bus + WO-034 Relic Alert Catalog.

Not a mobile-style notification center. Soft text + optional box for crit.
Domain systems call emit_alert / collect_alert; UI writes via IO when present.

Severity: info | warn | crit
Throttle/de-dupe via player["_alert_throttle"] keyed by throttle_key or code.

WO-034: canonical namespace is relic.* ; burden.* resolves via alias.
relic.spirit_* = display name for morale (no separate Spirit resource).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

# ── severity ─────────────────────────────────────────────────────────────

SEV_INFO = "info"
SEV_WARN = "warn"
SEV_CRIT = "crit"
SEVERITIES = (SEV_INFO, SEV_WARN, SEV_CRIT)

# default min ticks between same throttle_key (player auto_ticks / care ticks)
DEFAULT_THROTTLE_TICKS = {
    SEV_INFO: 0,  # usually not throttled unless catalog says so
    SEV_WARN: 3,
    SEV_CRIT: 5,
}


@dataclass
class Alert:
    code: str
    severity: str = SEV_INFO
    source: str = "system"
    title: str = ""
    body: str = ""
    tags: List[str] = field(default_factory=list)
    throttle_key: str = ""
    throttle_ticks: Optional[int] = None  # None → default by severity
    once_session: bool = False


# ── WO-034: legacy burden.* → canonical relic.* ──────────────────────────

# Call sites may still pass burden.*; resolve to relic.* before lookup/history.
ALERT_CODE_ALIASES: Dict[str, str] = {
    "burden.equip.fit": "relic.equip",
    "burden.equip.strain": "relic.equip_warning",
    "burden.equip.crush": "relic.equip_warning",
    "burden.morale_low": "relic.spirit_low",
    "burden.morale_crit": "relic.spirit_critical",
    "burden.auto_unequip": "relic.auto_unequip",
    "burden.auto_blocked": "relic.auto_blocked",
    "burden.mana_thin": "relic.mana_drain",
    "burden.pre_fight": "relic.pre_fight",
    "burden.pre_dungeon": "relic.pre_dungeon",
}


def resolve_alert_code(code: str) -> str:
    """Map legacy codes to canonical catalog id (identity if unknown)."""
    c = str(code or "").strip()
    return ALERT_CODE_ALIASES.get(c, c)


def reverse_aliases(canonical: str) -> List[str]:
    """Legacy codes that map to this canonical code."""
    can = str(canonical)
    return [k for k, v in ALERT_CODE_ALIASES.items() if v == can]


# ── catalog: relic.* (canonical) ─────────────────────────────────────────

def _relic_catalog() -> Dict[str, Dict[str, Any]]:
    """
    WO-034 Relic Alert Catalog.

    Groups: equip · combat · critical/auto · helper (phase 5 polish codes included
    in catalog for completeness; wiring deferred).
    spirit_* = soft display for morale while carrying relic — not a new resource.
    """
    return {
        # ── 1 equip / install ───────────────────────────────────────────
        "relic.equip": {
            "severity": SEV_INFO,
            "source": "relic",
            "title": "เรลิกเข้ามือ",
            "body": "「{item}」พอประมาณ — ภาระเบา",
            "tags": ["relic", "equip"],
            "throttle_key": "relic.equip",
            "throttle_ticks": 0,
        },
        "relic.equip_warning": {
            "severity": SEV_WARN,
            "source": "relic",
            "title": "เรลิกภาระสูง",
            "body": "「{item}」กดขวัญ · {band_th} · ถอดได้ · ห้อง G ลองได้",
            "tags": ["relic", "equip", "morale"],
            "throttle_key": "relic.equip_warning",
            "throttle_ticks": 0,
        },
        "relic.unequip": {
            "severity": SEV_INFO,
            "source": "relic",
            "title": "ถอดเรลิก",
            "body": "ถอด「{item}」แล้ว — ภาระผ่อน",
            "tags": ["relic", "equip"],
            "throttle_key": "relic.unequip",
            "throttle_ticks": 0,
        },
        # ── 2 combat ────────────────────────────────────────────────────
        "relic.aura_active": {
            "severity": SEV_INFO,
            "source": "relic",
            "title": "ออร่าเรลิก",
            "body": "ออร่าเรลิกเริ่มกดเบา ๆ — คนใกล้รู้สึกได้",
            "tags": ["relic", "aura", "combat"],
            "throttle_key": "relic.aura_active",
            "throttle_ticks": 0,
            "once_session": True,
        },
        "relic.mana_drain": {
            "severity": SEV_WARN,
            "source": "relic",
            "title": "เรลิกดูดมานา",
            "body": "มานาบางจากเรลิก — ระวังสกิล/โซ่คอมโบ",
            "tags": ["relic", "mana", "combat"],
            "throttle_key": "relic.mana_drain",
            "throttle_ticks": 3,
        },
        "relic.spirit_low": {
            "severity": SEV_WARN,
            "source": "relic",
            "title": "จิต/ขวัญหด · เรลิก",
            "body": "ขวัญหดจากภาระเรลิก — กิน พัก หรือถอดของ",
            "tags": ["relic", "morale", "spirit"],
            "throttle_key": "relic.spirit_low",
            "throttle_ticks": 4,
        },
        "relic.spirit_critical": {
            "severity": SEV_CRIT,
            "source": "relic",
            "title": "จิต/ขวัญวิกฤต · เรลิก",
            "body": "ขวัญย่ำจากเรลิก — ถอดหรือหยุดออโต้ · เสี่ยงสกิลพลาด",
            "tags": ["relic", "morale", "spirit", "crit"],
            "throttle_key": "relic.spirit_critical",
            "throttle_ticks": 5,
        },
        "relic.morale_debuff": {
            "severity": SEV_WARN,
            "source": "relic",
            "title": "ขวัญถูกกด · เรลิก",
            "body": "ภาระเรลิกกดขวัญต่อเนื่อง · {band_th}",
            "tags": ["relic", "morale", "combat"],
            "throttle_key": "relic.morale_debuff",
            "throttle_ticks": 4,
        },
        # ── 3 critical / auto ───────────────────────────────────────────
        "relic.critical": {
            "severity": SEV_CRIT,
            "source": "relic",
            "title": "เรลิก · สถานการณ์วิกฤต",
            "body": "ภาระกับขวัญใกล้พัง — ถอดเรลิกหรือพักก่อนต่อ",
            "tags": ["relic", "crit"],
            "throttle_key": "relic.critical",
            "throttle_ticks": 5,
        },
        "relic.auto_blocked": {
            "severity": SEV_CRIT,
            "source": "relic",
            "title": "ออโต้หยุด · เรลิก/ขวัญ",
            "body": "ออโต้หยุดเพราะขวัญกับภาระเรลิก — ถอดของหรือพักก่อนรันต่อ",
            "tags": ["relic", "auto", "crit"],
            "throttle_key": "relic.auto_blocked",
            "throttle_ticks": 3,
        },
        "relic.auto_unequip": {
            "severity": SEV_WARN,
            "source": "relic",
            "title": "ออโต้ถอดเรลิก",
            "body": "ถอด「{item}」เพราะขวัญต่ำ · ภาระเกินนโยบาย",
            "tags": ["relic", "auto"],
            "throttle_key": "relic.auto_unequip",
            "throttle_ticks": 0,
        },
        # ── 4 helper (phase 5) ──────────────────────────────────────────
        "relic.aura_resisted": {
            "severity": SEV_INFO,
            "source": "relic",
            "title": "ต้านออร่าเรลิก",
            "body": "จิตกับเกียร์ต้านออร่าได้ — แรงกดเบาลง",
            "tags": ["relic", "aura", "resist"],
            "throttle_key": "relic.aura_resisted",
            "throttle_ticks": 5,
        },
        "relic.aura_strong": {
            "severity": SEV_WARN,
            "source": "relic",
            "title": "ออร่าเรลิกแรง",
            "body": "ออร่าแผ่แรง · {band_th} — คนใกล้และตัวเองรู้สึกหนัก",
            "tags": ["relic", "aura"],
            "throttle_key": "relic.aura_strong",
            "throttle_ticks": 4,
            "once_session": True,
        },
        # continuity
        "relic.pre_fight": {
            "severity": SEV_WARN,
            "source": "relic",
            "title": "ก่อนสู้ · มีเรลิก",
            "body": "กำลังใส่เรลิก · {band_th} — ขวัญ/สกิลอาจสั่น · ถอดได้ก่อนเข้าวง",
            "tags": ["relic", "combat"],
            "throttle_key": "relic.pre_fight",
            "throttle_ticks": 2,
        },
        "relic.pre_dungeon": {
            "severity": SEV_WARN,
            "source": "relic",
            "title": "ก่อนดัน · เรลิก",
            "body": "ลงดันพร้อมเรลิก · {band_th} — ขวัญอาจร่วงเร็ว · เสบียงและถอดเมื่อต่ำ",
            "tags": ["relic", "dungeon"],
            "throttle_key": "relic.pre_dungeon",
            "throttle_ticks": 1,
        },
    }


def _anima_catalog() -> Dict[str, Dict[str, Any]]:
    """
    WO-037 Anima Presence — Soft Alert codes.
    Anima = Spirit core (player['anima']), NOT needs.morale, NOT relic.spirit_*.
    """
    return {
        "anima.relic_touch": {
            "severity": SEV_INFO,
            "source": "anima",
            "title": "จิตวิญญาณสั่น",
            "body": "จิตวิญญาณของคุณสั่นไหวเล็กน้อย… เรลิกแตะชั้นลึกกว่าขวัญ",
            "tags": ["anima", "relic"],
            "throttle_key": "anima.relic_touch",
            "throttle_ticks": 2,
        },
        "anima.chamber_echo": {
            "severity": SEV_INFO,
            "source": "anima",
            "title": "ห้องก้องจิต",
            "body": "พลังเรลิกแผ่ซ่านในห้อง — รู้สึกหนักแต่ลึกซึ้ง",
            "tags": ["anima", "chamber"],
            "throttle_key": "anima.chamber_echo",
            "throttle_ticks": 1,
        },
        "anima.learn_glow": {
            "severity": SEV_INFO,
            "source": "anima",
            "title": "สมาธิไหล",
            "body": "สมาธิไหลเวียนดีขึ้น — จิตวิญญาณอุ่นขึ้นเล็กน้อย",
            "tags": ["anima", "learn"],
            "throttle_key": "anima.learn_glow",
            "throttle_ticks": 3,
        },
        "anima.mana_flow": {
            "severity": SEV_INFO,
            "source": "anima",
            "title": "มานาไหลคล่อง",
            "body": "สมาธิไหลเวียนดี — มานาใช้ได้คล่องขึ้นชั่วขณะ",
            "tags": ["anima", "magic", "combat"],
            "throttle_key": "anima.mana_flow",
            "throttle_ticks": 3,
        },
        "anima.thin": {
            "severity": SEV_WARN,
            "source": "anima",
            "title": "จิตวิญญาณแผ่ว",
            "body": "จิตวิญญาณแผ่ว — ขวัญอาจร่วงเร็ว · ท่าโฟกัสเสี่ยงสั่น",
            "tags": ["anima", "warn"],
            "throttle_key": "anima.thin",
            "throttle_ticks": 5,
        },
        "anima.deep": {
            "severity": SEV_INFO,
            "source": "anima",
            "title": "จิตวิญญาณลึก",
            "body": "จิตวิญญาณมั่นลึก — ขวัญนิ่งขึ้น · ต้านแรงกดจิตได้ดีขึ้น",
            "tags": ["anima", "calm"],
            "throttle_key": "anima.deep",
            "throttle_ticks": 6,
        },
        "anima.skill_waver": {
            "severity": SEV_WARN,
            "source": "anima",
            "title": "ท่าสั่น · จิต",
            "body": "「{item}」หลุดจังหวะ — จิตวิญญาณยังไม่มั่นพอ",
            "tags": ["anima", "combat", "skill"],
            "throttle_key": "anima.skill_waver",
            "throttle_ticks": 2,
        },
        "anima.resist_mind": {
            "severity": SEV_INFO,
            "source": "anima",
            "title": "ต้านแรงกดจิต",
            "body": "จิตวิญญาณต้านแรงกดได้ — สถานะจิตแผ่วลง",
            "tags": ["anima", "resist"],
            "throttle_key": "anima.resist_mind",
            "throttle_ticks": 4,
        },
    }


def _world_catalog() -> Dict[str, Dict[str, Any]]:
    """WO-038 World Relations Soft Alerts — no raw scores."""
    return {
        "world.divine_glance": {
            "severity": SEV_INFO,
            "source": "world_relations",
            "title": "สายตาจากที่สูง",
            "body": "เทพวายุส่งสายตา… {item} รู้สึก〔{band}〕ขึ้น",
            "tags": ["world", "divine"],
            "throttle_key": "world.divine_glance",
            "throttle_ticks": 3,
        },
        "world.divine_avert": {
            "severity": SEV_WARN,
            "source": "world_relations",
            "title": "สายตาหันหนี",
            "body": "สายสวรรค์หันหนี… {item} 〔{band}〕",
            "tags": ["world", "divine"],
            "throttle_key": "world.divine_avert",
            "throttle_ticks": 3,
        },
        "world.infernal_haze": {
            "severity": SEV_WARN,
            "source": "world_relations",
            "title": "หมอกมาร",
            "body": "พลังมารแผ่ซ่านเบา ๆ… {item} 〔{band}〕 — ขวัญอาจสั่น",
            "tags": ["world", "infernal"],
            "throttle_key": "world.infernal_haze",
            "throttle_ticks": 3,
        },
        "world.infernal_favor": {
            "severity": SEV_INFO,
            "source": "world_relations",
            "title": "เงามารยิ้ม",
            "body": "เงาสายมารพยักหน้า… {item} 〔{band}〕 (อย่าไว้ใจเกิน)",
            "tags": ["world", "infernal"],
            "throttle_key": "world.infernal_favor",
            "throttle_ticks": 3,
        },
        "world.echo_stare": {
            "severity": SEV_WARN,
            "source": "world_relations",
            "title": "เงา echo จ้อง",
            "body": "เงา echo หยุดมองคุณ… {item} 〔{band}〕",
            "tags": ["world", "echo"],
            "throttle_key": "world.echo_stare",
            "throttle_ticks": 3,
        },
        "world.echo_nod": {
            "severity": SEV_INFO,
            "source": "world_relations",
            "title": "เงายอมรับ",
            "body": "เงาโบราณพยัก… {item} 〔{band}〕",
            "tags": ["world", "echo"],
            "throttle_key": "world.echo_nod",
            "throttle_ticks": 3,
        },
        "world.chamber_hush": {
            "severity": SEV_INFO,
            "source": "world_relations",
            "title": "ห้องเงียบ",
            "body": "ห้องทดสอบเงียบผิดปกติ — มีสายตาจากที่สูง",
            "tags": ["world", "chamber"],
            "throttle_key": "world.chamber_hush",
            "throttle_ticks": 2,
        },
        # WO-039 mini-moments
        "world.moment_divine_help": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "สายตาแห่งวายุ",
            "body": "ลมอุ่นพัด — เทพส่งสายตายอมรับการช่วยเหลือ",
            "tags": ["world", "divine", "moment"],
            "throttle_ticks": 2,
        },
        "world.moment_divine_pass": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "ลมเย็น",
            "body": "ลมวายุเย็นลง — สายตาจากที่สูงไม่แน่ใจในคุณ",
            "tags": ["world", "divine", "moment"],
            "throttle_ticks": 2,
        },
        "world.moment_infernal_gaze": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "เงามารยิ้ม",
            "body": "หมอกดำพอใจ — ขวัญสั่น · อย่าไว้ใจเกิน",
            "tags": ["world", "infernal", "moment"],
            "throttle_ticks": 2,
        },
        "world.moment_infernal_reject": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "หันหลังมาร",
            "body": "คุณหันหลังหมอก — มารโกรธแผ่ว แต่จิตยังตั้ง",
            "tags": ["world", "infernal", "moment"],
            "throttle_ticks": 2,
        },
        "world.moment_echo_accept": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "เงายอมรับ",
            "body": "ใบไม้เงียบลง — เงาโบราณยอมรับชั่วขณะ",
            "tags": ["world", "echo", "moment"],
            "throttle_ticks": 2,
        },
        "world.moment_echo_reject": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "ป่าเงียบกริบ",
            "body": "เสียงกระซิบถูกไล่ — เงายังจ้องจากโคนไม้",
            "tags": ["world", "echo", "moment"],
            "throttle_ticks": 2,
        },
        # WO-042 area mini-moments
        "world.moment_cave_coal_accept": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "เถ้าถ้ำ",
            "body": "เถ้าติดนิ้ว — มารในถ้ำพยัก · ขวัญสั่น",
            "tags": ["world", "infernal", "moment", "cave"],
            "throttle_ticks": 2,
        },
        "world.moment_cave_coal_refuse": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "ปัดเถ้า",
            "body": "คุณปัดเถ้า — เงาถ้ำหด · จิตยังตั้ง",
            "tags": ["world", "infernal", "moment", "cave"],
            "throttle_ticks": 2,
        },
        "world.moment_desert_mirage_listen": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "ภาพลวงฟัง",
            "body": "ทรายนิ่ง — เงาโบราณจำชื่อคุณ · จิตสั่นอุ่น",
            "tags": ["world", "echo", "moment", "desert"],
            "throttle_ticks": 2,
        },
        "world.moment_desert_mirage_banish": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "ไล่ภาพลวง",
            "body": "คลื่นร้อนหนา — เงายังจ้องขอบฟ้า",
            "tags": ["world", "echo", "moment", "desert"],
            "throttle_ticks": 2,
        },
        "world.moment_crystal_pray": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "อธิษฐานผลึก",
            "body": "ผลึกส่งแสงอุ่น — สายตาเทพบนยอด · จิตอุ่น · ขวัญนิ่ง",
            "tags": ["world", "divine", "moment", "crystal"],
            "throttle_ticks": 2,
        },
        "world.moment_crystal_pass": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "ผลึกเย็น",
            "body": "แสงผลึกเย็นลง — สายตาจากที่สูงหันหนีแผ่ว",
            "tags": ["world", "divine", "moment", "crystal"],
            "throttle_ticks": 2,
        },
        # WO-044 mountain / city / void moments + foresight gaze
        "world.moment_mountain_pray": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "อธิษฐานบนผา",
            "body": "ลมอุ่นบนผา — สายตาเทพจับจ้อง · จิตอุ่น · ขวัญนิ่ง",
            "tags": ["world", "divine", "moment", "mountain"],
            "throttle_ticks": 2,
        },
        "world.moment_mountain_pass": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "ลมผาเย็น",
            "body": "คุณเดินลงเขา — ลมเย็น · สายตาบนผาหันหนี",
            "tags": ["world", "divine", "moment", "mountain"],
            "throttle_ticks": 2,
        },
        "world.moment_city_bell": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "ระฆังเมือง",
            "body": "ระฆังก้องลาน — เมืองเก่าพยัก · จิตอุ่น",
            "tags": ["world", "divine", "moment", "city"],
            "throttle_ticks": 2,
        },
        "world.moment_city_pass": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "ระฆังเงียบ",
            "body": "ระฆังเงียบเร็ว — สายตาจากหอไม่แน่ใจ",
            "tags": ["world", "divine", "moment", "city"],
            "throttle_ticks": 2,
        },
        "world.moment_void_listen": {
            "severity": SEV_INFO,
            "source": "faction_moment",
            "title": "ฟังสุญญะ",
            "body": "ความว่างพยัก — จิตสั่นเชื่อม · เงาจำคุณในรอยแยก",
            "tags": ["world", "echo", "moment", "void"],
            "throttle_ticks": 2,
        },
        "world.moment_void_cut": {
            "severity": SEV_WARN,
            "source": "faction_moment",
            "title": "ตัดสายสุญญะ",
            "body": "คุณถอยจากขอบ — รอยแยกหด · ขวัญกด · จิตยังตั้ง",
            "tags": ["world", "echo", "moment", "void"],
            "throttle_ticks": 2,
        },
        "world.foresight_divine_gaze": {
            "severity": SEV_INFO,
            "source": "soft_foresight",
            "title": "สายตาเทพ · ใบ้",
            "body": "คุณรู้สึกสายตาจากเทพวายุ… อบอุ่นจากที่สูง · อาจเจอ Mini-Moment",
            "tags": ["world", "foresight", "divine"],
            "throttle_ticks": 5,
        },
        "world.foresight_infernal_haze": {
            "severity": SEV_WARN,
            "source": "soft_foresight",
            "title": "หมอกมาร · ใบ้",
            "body": "เงามารแผ่ซ่านเบา ๆ… ความร้อนคุ้นเคย · ระวังสายตาโลก",
            "tags": ["world", "foresight", "infernal"],
            "throttle_ticks": 5,
        },
        "world.foresight_echo_whisper": {
            "severity": SEV_INFO,
            "source": "soft_foresight",
            "title": "กระซิบ echo · ใบ้",
            "body": "เสียงกระซิบจาก echo… เงาโบราณเหลือบมอง · อาจเจอ Mini-Moment",
            "tags": ["world", "foresight", "echo"],
            "throttle_ticks": 5,
        },
        # WO-046 Relic × Area / Moment synergy
        "world.synergy_resonate": {
            "severity": SEV_INFO,
            "source": "relic_world_synergy",
            "title": "เรลิกกับโลก · จังหวะเดียวกัน",
            "body": "เรลิกของคุณเข้ากับพื้นที่นี้ — Mini-Moment อาจชัด · จิตวิญญาณรู้สึกได้มากขึ้น",
            "tags": ["world", "synergy", "resonate"],
            "throttle_ticks": 3,
        },
        "world.synergy_tension": {
            "severity": SEV_WARN,
            "source": "relic_world_synergy",
            "title": "เรลิกกับโลก · ดึงคนละทาง",
            "body": "เรลิกกับพื้นที่นี้ไม่เข้ากัน — ขวัญกดเร็วขึ้นเล็กน้อย · จิตอาจแผ่ว · ถอด/ย้ายที่ได้",
            "tags": ["world", "synergy", "tension"],
            "throttle_ticks": 3,
        },
        "world.synergy_moment_resonate": {
            "severity": SEV_INFO,
            "source": "relic_world_synergy",
            "title": "Moment · เรลิกสะท้อน",
            "body": "ช่วงเวลานี้เข้ากับเรลิกของคุณ — จิตวิญญาณชัดขึ้น (ลึกกว่าขวัญ)",
            "tags": ["world", "synergy", "moment"],
            "throttle_ticks": 2,
        },
        "world.synergy_moment_tension": {
            "severity": SEV_WARN,
            "source": "relic_world_synergy",
            "title": "Moment · เรลิกไม่เข้าจังหวะ",
            "body": "ช่วงเวลานี้ดึงกับเรลิก — จิตรับผลไม่สมดุล · ขวัญอาจสั่น",
            "tags": ["world", "synergy", "moment"],
            "throttle_ticks": 2,
        },
        "anima.synergy_resonate": {
            "severity": SEV_INFO,
            "source": "relic_world_synergy",
            "title": "จิต · เข้าจังหวะโลก",
            "body": "เรลิกกับโลกมีจังหวะเดียวกัน — จิตวิญญาณชัดขึ้นชั่วขณะ · อุ่น/สั่นรู้สึกได้",
            "tags": ["anima", "synergy"],
            "throttle_ticks": 2,
        },
        "anima.synergy_tension": {
            "severity": SEV_WARN,
            "source": "relic_world_synergy",
            "title": "จิต · โลกดึงคนละทาง",
            "body": "เรลิกกับพื้นที่ไม่เข้ากัน — จิตแผ่ว · ถ้าขวัญต่ำอาจอยากถอด",
            "tags": ["anima", "synergy"],
            "throttle_ticks": 2,
        },
        "anima.spar_area_synergy": {
            "severity": SEV_INFO,
            "source": "relic_world_synergy",
            "title": "ซ้อม · เข้าจังหวะโลก",
            "body": "ซ้อมขณะเรลิกเข้ากับ lean โลก — พันธะ/จิตชัดขึ้นรู้สึกได้",
            "tags": ["anima", "synergy", "chamber"],
            "throttle_ticks": 1,
        },
        # WO-040 Anima × Relic
        "anima.relic_divine": {
            "severity": SEV_INFO,
            "source": "relic_anima",
            "title": "เรลิก · จิตอุ่น",
            "body": "「{item}」แผ่ซ่าน — หนักแต่ลึกซึ้ง · จิตวิญญาณอุ่น · ขวัญลดช้าลง",
            "tags": ["anima", "relic", "divine"],
            "throttle_ticks": 0,
        },
        "anima.relic_infernal": {
            "severity": SEV_WARN,
            "source": "relic_anima",
            "title": "เรลิก · จิตแผ่ว",
            "body": "「{item}」เกาะมาร — จิตวิญญาณแผ่ว · ขวัญอาจร่วงเร็ว",
            "tags": ["anima", "relic", "infernal"],
            "throttle_ticks": 0,
        },
        "anima.relic_echo": {
            "severity": SEV_INFO,
            "source": "relic_anima",
            "title": "เรลิก · จิตสั่น",
            "body": "「{item}」กระซิบ — จิตวิญญาณสั่นไหว · เงาโลกอาจเหลือบมอง",
            "tags": ["anima", "relic", "echo"],
            "throttle_ticks": 0,
        },
        "anima.spar_divine": {
            "severity": SEV_INFO,
            "source": "relic_anima",
            "title": "ซ้อม · จิตลึก",
            "body": "ซ้อมกับ「{item}」— จิตวิญญาณลึกขึ้นเล็กน้อย",
            "tags": ["anima", "chamber", "divine"],
            "throttle_ticks": 1,
        },
        "anima.spar_infernal": {
            "severity": SEV_WARN,
            "source": "relic_anima",
            "title": "ซ้อม · จิตร้อน",
            "body": "ซ้อมกับ「{item}」— ความร้อนดูดจิต · แผ่วลง",
            "tags": ["anima", "chamber", "infernal"],
            "throttle_ticks": 1,
        },
        "anima.spar_echo": {
            "severity": SEV_INFO,
            "source": "relic_anima",
            "title": "ซ้อม · เงาก้อง",
            "body": "ซ้อมกับ「{item}」— จิตสั่นชัด · เงาห้องพยัก",
            "tags": ["anima", "chamber", "echo"],
            "throttle_ticks": 1,
        },
        "world.relic_wind_gaze": {
            "severity": SEV_INFO,
            "source": "relic_anima",
            "title": "สายตาวายุ",
            "body": "ขณะสำรวจ — ลมวายุพัดผ่านเรลิก · สายตาจากที่สูง",
            "tags": ["world", "relic", "divine"],
            "throttle_ticks": 4,
        },
        "world.relic_ember_whisper": {
            "severity": SEV_WARN,
            "source": "relic_anima",
            "title": "กระซิบเถ้า",
            "body": "เรลิกนรกร้อนขึ้นขณะเดิน — ขวัญสั่นแผ่ว",
            "tags": ["world", "relic", "infernal"],
            "throttle_ticks": 4,
        },
        "world.relic_echo_whisper": {
            "severity": SEV_INFO,
            "source": "relic_anima",
            "title": "กระซิบเงา",
            "body": "เรลิกกระซิบชื่อในสายลม — เงาโบราณเหลือบมอง",
            "tags": ["world", "relic", "echo"],
            "throttle_ticks": 4,
        },
        # WO-041 Relic Soft Bonds
        "anima.bond_divine": {
            "severity": SEV_INFO,
            "source": "relic_bond",
            "title": "เรโซแนนซ์ · เทพ",
            "body": "เรลิก {count} ชิ้นสายสวรรค์เรโซแนนซ์ — สายตาเทพจับจ้องอย่างอบอุ่น · จิตอุ่น · ขวัญลดช้า",
            "tags": ["anima", "bond", "divine"],
            "throttle_ticks": 0,
        },
        "anima.bond_infernal": {
            "severity": SEV_WARN,
            "source": "relic_bond",
            "title": "เรโซแนนซ์ · มาร",
            "body": "เรลิก {count} ชิ้นสายมารเรโซแนนซ์ — พลังมารแผ่ซ่านอย่างคุ้นเคย · จิตแผ่วเบา · ขวัญกดปานกลาง",
            "tags": ["anima", "bond", "infernal"],
            "throttle_ticks": 0,
        },
        "anima.bond_echo": {
            "severity": SEV_INFO,
            "source": "relic_bond",
            "title": "เรโซแนนซ์ · เงา",
            "body": "เรลิก {count} ชิ้นเงาโบราณเรโซแนนซ์ — จิตสั่นเป็นจังหวะ · กระซิบหนาขึ้น",
            "tags": ["anima", "bond", "echo"],
            "throttle_ticks": 0,
        },
        "anima.bond_tension": {
            "severity": SEV_WARN,
            "source": "relic_bond",
            "title": "Soft Tension",
            "body": "เรลิกขัด lean ({item}) — พลังสองสายดึงกัน · จิตแผ่ว · ขวัญลดเร็วขึ้นเล็กน้อย",
            "tags": ["anima", "bond", "tension"],
            "throttle_ticks": 0,
        },
        "anima.spar_bond_divine": {
            "severity": SEV_INFO,
            "source": "relic_bond",
            "title": "ซ้อม · พันธะเทพ",
            "body": "ซ้อมเรโซแนนซ์「{item}」— พันธะสวรรค์ชัด · จิตลึกขึ้น",
            "tags": ["anima", "bond", "chamber", "divine"],
            "throttle_ticks": 1,
        },
        "anima.spar_bond_infernal": {
            "severity": SEV_WARN,
            "source": "relic_bond",
            "title": "ซ้อม · พันธะมาร",
            "body": "ซ้อมเรโซแนนซ์「{item}」— ความร้อนคุ้นเคย · จิตแผ่วแต่ทน",
            "tags": ["anima", "bond", "chamber", "infernal"],
            "throttle_ticks": 1,
        },
        "anima.spar_bond_echo": {
            "severity": SEV_INFO,
            "source": "relic_bond",
            "title": "ซ้อม · พันธะเงา",
            "body": "ซ้อมเรโซแนนซ์「{item}」— เงาก้องซ้อน · จิตสั่นชัด",
            "tags": ["anima", "bond", "chamber", "echo"],
            "throttle_ticks": 1,
        },
        "anima.spar_bond_tension": {
            "severity": SEV_WARN,
            "source": "relic_bond",
            "title": "ซ้อม · ขัด lean",
            "body": "ซ้อมขณะเรลิกขัด lean — จิตถูกดึงสองทาง · ระวังขวัญ",
            "tags": ["anima", "bond", "chamber", "tension"],
            "throttle_ticks": 1,
        },
        "world.bond_divine_gaze": {
            "severity": SEV_INFO,
            "source": "relic_bond",
            "title": "สายตาเทพซ้อน",
            "body": "เรโซแนนซ์สวรรค์ขณะสำรวจ — สายตาอบอุ่นจากที่สูงจับจ้องคู่เรลิก",
            "tags": ["world", "bond", "divine"],
            "throttle_ticks": 4,
        },
        "world.bond_infernal_haze": {
            "severity": SEV_WARN,
            "source": "relic_bond",
            "title": "หมอกมารซ้อน",
            "body": "เรโซแนนซ์นรกขณะเดิน — เถ้าคุ้นเคยแผ่ซ่าน · ขวัญสั่นแผ่ว",
            "tags": ["world", "bond", "infernal"],
            "throttle_ticks": 4,
        },
        "world.bond_echo_chorus": {
            "severity": SEV_INFO,
            "source": "relic_bond",
            "title": "คณะกระซิบเงา",
            "body": "เรโซแนนซ์เงา — เสียงกระซิบซ้อนเป็นคณะ · เงาโบราณพยัก",
            "tags": ["world", "bond", "echo"],
            "throttle_ticks": 4,
        },
        "world.bond_tension_wind": {
            "severity": SEV_WARN,
            "source": "relic_bond",
            "title": "ลมขัด lean",
            "body": "เรลิกสองสายดึงลมคนละทาง — อกแน่น · ขวัญสั่น",
            "tags": ["world", "bond", "tension"],
            "throttle_ticks": 4,
        },
        # WO-043 Soft Chorus + Soft Cap
        "anima.chorus_divine": {
            "severity": SEV_INFO,
            "source": "relic_chorus",
            "title": "Soft Chorus · เทพ",
            "body": "เรลิก {count} ชิ้นสายสวรรค์ก้องคณะ — สายตาเทพจับจ้องอย่างอบอุ่นลึกซึ้ง · จิตอุ่นแรง",
            "tags": ["anima", "chorus", "divine"],
            "throttle_ticks": 0,
        },
        "anima.chorus_infernal": {
            "severity": SEV_WARN,
            "source": "relic_chorus",
            "title": "Soft Chorus · มาร",
            "body": "เรลิก {count} ชิ้นสายมารก้องคณะ — พลังมารแผ่ซ่านอย่างมั่นคง · จิตแผ่วแต่แข็งแกร่ง",
            "tags": ["anima", "chorus", "infernal"],
            "throttle_ticks": 0,
        },
        "anima.chorus_echo": {
            "severity": SEV_INFO,
            "source": "relic_chorus",
            "title": "Soft Chorus · เงา",
            "body": "เรลิก {count} ชิ้นเงาก้องคณะ — จิตสั่นไหวแต่เชื่อมโยง · กระซิบหนาขึ้น",
            "tags": ["anima", "chorus", "echo"],
            "throttle_ticks": 0,
        },
        "anima.bond_soft_cap": {
            "severity": SEV_WARN,
            "source": "relic_chorus",
            "title": "Soft Cap · คณะหนา",
            "body": "คณะเรลิก {count} ชิ้นหนา — จิตสั่น · ขวัญกดแผ่ว (ไม่ล็อก · ถอดชิ้นหนึ่งแล้วนิ่มขึ้น)",
            "tags": ["anima", "chorus", "soft_cap"],
            "throttle_ticks": 5,
        },
        "anima.spar_chorus_divine": {
            "severity": SEV_INFO,
            "source": "relic_chorus",
            "title": "ซ้อม · คณะเทพ",
            "body": "ซ้อมคณะเรลิก「{item}」— Chorus สวรรค์ก้อง · จิตลึกขึ้น",
            "tags": ["anima", "chorus", "chamber", "divine"],
            "throttle_ticks": 1,
        },
        "anima.spar_chorus_infernal": {
            "severity": SEV_WARN,
            "source": "relic_chorus",
            "title": "ซ้อม · คณะมาร",
            "body": "ซ้อมคณะเรลิก「{item}」— ความร้อนมั่นคง · จิตแผ่วแต่ทน",
            "tags": ["anima", "chorus", "chamber", "infernal"],
            "throttle_ticks": 1,
        },
        "anima.spar_chorus_echo": {
            "severity": SEV_INFO,
            "source": "relic_chorus",
            "title": "ซ้อม · คณะเงา",
            "body": "ซ้อมคณะเรลิก「{item}」— เงาก้องซ้อน · จิตเชื่อมชัด",
            "tags": ["anima", "chorus", "chamber", "echo"],
            "throttle_ticks": 1,
        },
        "world.chorus_divine_gaze": {
            "severity": SEV_INFO,
            "source": "relic_chorus",
            "title": "สายตาคณะเทพ",
            "body": "Chorus สวรรค์ขณะสำรวจ — สายตาอบอุ่นลึกซึ้งจากที่สูงจับจ้องคณะเรลิก",
            "tags": ["world", "chorus", "divine"],
            "throttle_ticks": 4,
        },
        "world.chorus_infernal_haze": {
            "severity": SEV_WARN,
            "source": "relic_chorus",
            "title": "หมอกคณะมาร",
            "body": "Chorus นรกขณะเดิน — เถ้ามั่นคงแผ่ซ่าน · ขวัญสั่นแผ่ว",
            "tags": ["world", "chorus", "infernal"],
            "throttle_ticks": 4,
        },
        "world.chorus_echo_choir": {
            "severity": SEV_INFO,
            "source": "relic_chorus",
            "title": "คณะกระซิบเงา",
            "body": "Chorus เงา — เสียงกระซิบซ้อนเป็นคณะ · เงาโบราณพยักพร้อมกัน",
            "tags": ["world", "chorus", "echo"],
            "throttle_ticks": 4,
        },
    }


# soft band labels for templates (no raw strain/crush in player text)
_BAND_TH = {
    "fit": "ภาระเบา",
    "strain": "ร้อนมือ",
    "crush": "หนักเกินตัว",
}


def _needs_catalog() -> Dict[str, Dict[str, Any]]:
    """WO-033.4: needs soft warnings (WO-005 vocabulary) on the bus."""
    return {
        "needs.hunger.crit": {
            "severity": SEV_CRIT,
            "source": "needs",
            "title": "หิววิกฤต",
            "body": "ดาเมจ/รับดาเมจแย่ · ควรกิน (เมนู 3)",
            "inline": "…หิววิกฤต — ดาเมจ/รับดาเมจแย่ · ควรกิน (เมนู 3)",
            "tags": ["needs", "hunger", "combat"],
            "throttle_key": "needs.hunger.crit",
            "throttle_ticks": 4,
        },
        "needs.hunger.bad": {
            "severity": SEV_WARN,
            "source": "needs",
            "title": "หิว",
            "body": "ร่างกายไม่เต็มแรง",
            "inline": "…หิว — ร่างกายไม่เต็มแรง",
            "tags": ["needs", "hunger", "combat"],
            "throttle_key": "needs.hunger.bad",
            "throttle_ticks": 3,
        },
        "needs.fatigue.crit": {
            "severity": SEV_CRIT,
            "source": "needs",
            "title": "ล้าวิกฤต",
            "body": "จังหวะเติมช้า · ควรพักหลังไฟต์",
            "inline": "…ล้าวิกฤต — จังหวะเติมช้า · ควรพักหลังไฟต์",
            "tags": ["needs", "fatigue", "combat"],
            "throttle_key": "needs.fatigue.crit",
            "throttle_ticks": 4,
        },
        "needs.fatigue.bad": {
            "severity": SEV_WARN,
            "source": "needs",
            "title": "ล้า",
            "body": "แท่งจังหวะหนักขึ้น",
            "inline": "…ล้า — แท่งจังหวะหนักขึ้น",
            "tags": ["needs", "fatigue", "combat"],
            "throttle_key": "needs.fatigue.bad",
            "throttle_ticks": 3,
        },
        "needs.morale.crit": {
            "severity": SEV_CRIT,
            "source": "needs",
            "title": "ขวัญย่ำแย่",
            "body": "ท่าโฟกัส/สกิลเสี่ยงพลาด",
            "inline": "…ขวัญย่ำแย่ — ท่าโฟกัส/สกิลเสี่ยงพลาด",
            "tags": ["needs", "morale", "combat"],
            "throttle_key": "needs.morale.crit",
            "throttle_ticks": 4,
        },
        "needs.morale.low": {
            "severity": SEV_WARN,
            "source": "needs",
            "title": "ขวัญหด",
            "body": "มืออาจสั่นตอนใช้สกิล",
            "inline": "…ขวัญหด — มืออาจสั่นตอนใช้สกิล",
            "tags": ["needs", "morale", "combat"],
            "throttle_key": "needs.morale.low",
            "throttle_ticks": 3,
        },
        # pressure-hint variants (priority one-liner)
        "needs.pressure.hunger_crit": {
            "severity": SEV_CRIT,
            "source": "needs",
            "title": "หิววิกฤต",
            "body": "ควรกินเสบียง — เสี่ยงสลบ",
            "inline": "…หิววิกฤต −− ควรกินเสบียง — เสี่ยงสลบ",
            "tags": ["needs", "pressure"],
            "throttle_ticks": 5,
        },
        "needs.pressure.fatigue_crit": {
            "severity": SEV_CRIT,
            "source": "needs",
            "title": "ล้าวิกฤต",
            "body": "ควรพัก — จังหวะต่อสู้ช้า",
            "inline": "…ล้าวิกฤต −− ควรพัก — จังหวะต่อสู้ช้า",
            "tags": ["needs", "pressure"],
            "throttle_ticks": 5,
        },
        "needs.pressure.morale_crit": {
            "severity": SEV_CRIT,
            "source": "needs",
            "title": "ขวัญย่ำแย่",
            "body": "ท่าอาจพลาด · ลดความก้าวร้าว",
            "inline": "…ขวัญย่ำแย่ −− ท่าอาจพลาด · ลดความก้าวร้าว",
            "tags": ["needs", "pressure"],
            "throttle_ticks": 5,
        },
        "needs.pressure.hunger_bad": {
            "severity": SEV_WARN,
            "source": "needs",
            "title": "หิว",
            "body": "โจมตี/รับดาเมจ/หลบอ่อนลง",
            "inline": "…หิว − โจมตี/รับดาเมจ/หลบอ่อนลง",
            "tags": ["needs", "pressure"],
            "throttle_ticks": 4,
        },
        "needs.pressure.fatigue_bad": {
            "severity": SEV_WARN,
            "source": "needs",
            "title": "ล้า",
            "body": "จังหวะเติมช้าลง",
            "inline": "…ล้า − จังหวะเติมช้าลง",
            "tags": ["needs", "pressure"],
            "throttle_ticks": 4,
        },
        "needs.pressure.morale_low": {
            "severity": SEV_WARN,
            "source": "needs",
            "title": "ขวัญหด",
            "body": "มืออาจสั่นตอนใช้สกิล",
            "inline": "…ขวัญหด − มืออาจสั่นตอนใช้สกิล",
            "tags": ["needs", "pressure"],
            "throttle_ticks": 4,
        },
    }


_CATALOG: Optional[Dict[str, Dict[str, Any]]] = None


def _build_legacy_burden_entries(relic_cat: Mapping[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Expose burden.* keys that mirror relic.* (discovery + old docs/tests)."""
    out: Dict[str, Dict[str, Any]] = {}
    for legacy, canonical in ALERT_CODE_ALIASES.items():
        base = relic_cat.get(canonical)
        if not base:
            continue
        d = dict(base)
        d["alias_of"] = canonical
        d["legacy"] = True
        # keep throttle on canonical key so old/new share window
        d["throttle_key"] = str(base.get("throttle_key") or canonical)
        out[legacy] = d
    return out


def _appraisal_catalog() -> Dict[str, Dict[str, Any]]:
    """WO-051 Appraisal Soft Alerts."""
    return {
        "appraisal.read": {
            "severity": SEV_INFO,
            "source": "appraisal",
            "title": "อ่านชั้น",
            "body": "สมาธิประเมิน 〔{tier}〕 · เป้า{target} — soft อย่างเดียว",
            "tags": ["appraisal", "soft"],
            "throttle_key": "appraisal.read",
            "throttle_ticks": 1,
        },
        "appraisal.grow": {
            "severity": SEV_INFO,
            "source": "appraisal",
            "title": "ตาคมขึ้น",
            "body": "อ่านชั้นได้ลึกขึ้น — ชั้น 〔{tier}〕",
            "tags": ["appraisal", "growth"],
            "throttle_key": "appraisal.grow",
            "throttle_ticks": 4,
        },
    }


def _party_catalog() -> Dict[str, Dict[str, Any]]:
    """WO-PARTY-7 Soft Alerts for companion assist."""
    return {
        "party.assist_cleanse_ok": {
            "severity": SEV_INFO,
            "source": "party",
            "title": "สหายชำระ",
            "body": "「{name}」ชำระอาการ 〔{ailment}〕 ให้คุณ — soft",
            "inline": " …「{name}」ชำระอาการให้คุณ",
            "tags": ["party", "assist", "cleanse"],
            "throttle_key": "party.assist_cleanse_ok",
            "throttle_ticks": 2,
        },
        "party.assist_fail": {
            "severity": SEV_INFO,
            "source": "party",
            "title": "ซุ่มแผ่ว",
            "body": "「{name}」พยายามช่วย — แรงยังไม่พอ (bond/anima soft)",
            "inline": " …「{name}」ช่วยไม่ทันจังหวะ",
            "tags": ["party", "assist", "soft"],
            "throttle_key": "party.assist_fail",
            "throttle_ticks": 2,
        },
    }


def get_catalog() -> Dict[str, Dict[str, Any]]:
    global _CATALOG
    if _CATALOG is None:
        relic = _relic_catalog()
        _CATALOG = {}
        _CATALOG.update(relic)
        _CATALOG.update(_build_legacy_burden_entries(relic))
        _CATALOG.update(_needs_catalog())
        _CATALOG.update(_anima_catalog())
        _CATALOG.update(_world_catalog())
        _CATALOG.update(_appraisal_catalog())
        _CATALOG.update(_party_catalog())
    else:
        if "relic.equip" not in _CATALOG:
            relic = _relic_catalog()
            _CATALOG.update(relic)
            _CATALOG.update(_build_legacy_burden_entries(relic))
        if "needs.hunger.crit" not in _CATALOG:
            _CATALOG.update(_needs_catalog())
        if "anima.relic_touch" not in _CATALOG:
            _CATALOG.update(_anima_catalog())
        if "world.divine_glance" not in _CATALOG:
            _CATALOG.update(_world_catalog())
        if "appraisal.read" not in _CATALOG:
            _CATALOG.update(_appraisal_catalog())
        if "party.assist_cleanse_ok" not in _CATALOG:
            _CATALOG.update(_party_catalog())
    return _CATALOG


def register_alert_def(code: str, definition: Mapping[str, Any]) -> None:
    """Allow other systems to register codes at runtime (future)."""
    cat = get_catalog()
    cat[str(code)] = dict(definition)


def _current_tick(player: Mapping[str, Any]) -> int:
    return int(
        player.get("auto_ticks")
        or player.get("_care_ticks")
        or player.get("time_units")
        or 0
    )


def _normalize_severity(sev: str) -> str:
    s = str(sev or SEV_INFO).lower().strip()
    if s in ("critical", "danger", "error"):
        return SEV_CRIT
    if s in ("warning", "warn", "caution"):
        return SEV_WARN
    if s in SEVERITIES:
        return s
    return SEV_INFO


def _format_template(tpl: str, ctx: Mapping[str, Any]) -> str:
    try:
        return str(tpl or "").format_map(dict(ctx))
    except Exception:
        try:
            return str(tpl or "").format(**{k: ctx.get(k, "") for k in ctx})
        except Exception:
            return str(tpl or "")


def build_alert(
    code: str,
    *,
    severity: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
    source: Optional[str] = None,
    **ctx: Any,
) -> Alert:
    """Build Alert from catalog + overrides. Resolves burden.* → relic.* (WO-034)."""
    raw = str(code or "")
    canonical = resolve_alert_code(raw)
    cat = get_catalog().get(canonical) or get_catalog().get(raw) or {}
    # if legacy entry was looked up first without resolve (shouldn't), prefer alias_of
    if cat.get("alias_of"):
        canonical = str(cat.get("alias_of") or canonical)
        cat = get_catalog().get(canonical) or cat
    sev = _normalize_severity(severity or cat.get("severity") or SEV_INFO)
    ctx_map = {k: ("" if v is None else v) for k, v in ctx.items()}
    # default keys used in templates
    ctx_map.setdefault("item", ctx_map.get("item_name") or ctx_map.get("name") or "เรลิก")
    band_raw = str(ctx_map.get("band") or "?")
    ctx_map.setdefault("band", band_raw)
    # WO-034.5: soft Thai band for player-facing copy
    if "band_th" not in ctx_map or not ctx_map.get("band_th"):
        ctx_map["band_th"] = _BAND_TH.get(band_raw, band_raw if band_raw != "?" else "ภาระ")
    tit = title if title is not None else str(cat.get("title") or canonical)
    bod = body if body is not None else str(cat.get("body") or "")
    tit = _format_template(tit, ctx_map)
    bod = _format_template(bod, ctx_map)
    th_key = str(cat.get("throttle_key") or canonical)
    th_ticks = cat.get("throttle_ticks")
    if th_ticks is None:
        th_ticks = DEFAULT_THROTTLE_TICKS.get(sev, 3)
    return Alert(
        code=canonical,  # always store canonical for history / God
        severity=sev,
        source=str(source or cat.get("source") or "system"),
        title=tit,
        body=bod,
        tags=list(cat.get("tags") or []),
        throttle_key=th_key,
        throttle_ticks=int(th_ticks) if th_ticks is not None else 0,
        once_session=bool(cat.get("once_session")),
    )


def should_emit(player: MutableMapping[str, Any], alert: Alert) -> bool:
    """Throttle / once-session gate."""
    tick = _current_tick(player)
    th = dict(player.get("_alert_throttle") or {})
    key = alert.throttle_key or alert.code
    if alert.once_session:
        seen = set(player.get("_alert_once") or [])
        if key in seen:
            return False
    last = th.get(key)
    need = int(alert.throttle_ticks or 0)
    if need > 0 and last is not None:
        try:
            if tick - int(last) < need:
                return False
        except Exception:
            pass
    return True


def mark_emitted(player: MutableMapping[str, Any], alert: Alert) -> None:
    tick = _current_tick(player)
    th = dict(player.get("_alert_throttle") or {})
    key = alert.throttle_key or alert.code
    th[key] = tick
    # prune old keys lightly
    if len(th) > 40:
        items = sorted(th.items(), key=lambda x: int(x[1] or 0))
        th = dict(items[-30:])
    player["_alert_throttle"] = th
    if alert.once_session:
        seen = list(player.get("_alert_once") or [])
        if key not in seen:
            seen.append(key)
        player["_alert_once"] = seen[-24:]


def format_alert_inline(alert: Alert) -> str:
    """
    One combat-style soft line (WO-005 ellipsis vocabulary).
    Prefers catalog `inline`; else  …title — body.
    """
    cat = get_catalog().get(alert.code) or {}
    raw = str(cat.get("inline") or "").strip()
    if raw:
        return raw if raw.startswith(" ") else f" {raw}"
    title = (alert.title or "").strip()
    body = (alert.body or "").strip()
    if title and body:
        return f" …{title} — {body}"
    if title:
        return f" …{title}"
    if body:
        return body if body.startswith(" ") or body.startswith("…") else f" …{body}"
    return f" · {alert.code}"


def format_alert_lines(alert: Alert, *, boxed_crit: bool = True) -> List[str]:
    """Visual soft cues by severity."""
    # needs / combat-inline codes: keep dense one-liner (status panels)
    if "needs" in (alert.tags or []) or alert.source == "needs":
        return [format_alert_inline(alert)]

    sev = alert.severity
    title = (alert.title or "").strip()
    body = (alert.body or "").strip()
    if sev == SEV_CRIT:
        lines = [
            " ✦ วิกฤต · Soft Alert",
            "---",
            f" {title}" if title else " แจ้งเตือน",
        ]
        if body:
            lines.append(f" {body}")
        lines.append("---")
        return lines
    if sev == SEV_WARN:
        out = []
        if title:
            out.append(f"  ⚠ {title}")
        if body:
            out.append(f"  · {body}")
        if not out:
            out.append("  ⚠ แจ้งเตือน")
        return out
    # info
    if title and body:
        return [f"  · {title}: {body}"]
    if title:
        return [f"  · {title}"]
    if body:
        return [f"  · {body}"]
    return [f"  · {alert.code}"]


def collect_alert(
    player: MutableMapping[str, Any],
    code: str,
    *,
    severity: Optional[str] = None,
    force: bool = False,
    record_only: bool = False,
    **ctx: Any,
) -> List[str]:
    """
    Build + throttle. Returns display lines (may be empty if throttled).
    Does not write IO.

    record_only: mark history/throttle but return [] (for background log).
    """
    alert = build_alert(code, severity=severity, **ctx)
    if not force and not should_emit(player, alert):
        return []
    mark_emitted(player, alert)
    # ring buffer last alerts for God
    hist = list(player.get("_alert_history") or [])
    hist.append(
        {
            "code": alert.code,
            "severity": alert.severity,
            "title": alert.title,
            "tick": _current_tick(player),
        }
    )
    player["_alert_history"] = hist[-20:]
    if record_only:
        return []
    return format_alert_lines(alert)


def emit_alert(
    player: MutableMapping[str, Any],
    code: str,
    *,
    io: Any = None,
    severity: Optional[str] = None,
    force: bool = False,
    log_auto: bool = True,
    care_note: bool = True,
    **ctx: Any,
) -> List[str]:
    """
    Emit alert: optional write to io, care notes, auto run log.
    Returns lines that were (or would be) shown.
    """
    lines = collect_alert(player, code, severity=severity, force=force, **ctx)
    if not lines:
        return []

    canon = resolve_alert_code(code)
    if io is not None:
        try:
            sev = _normalize_severity(
                severity
                or (get_catalog().get(canon) or get_catalog().get(code) or {}).get("severity")
                or SEV_INFO
            )
            if sev == SEV_CRIT:
                try:
                    from game.ui_terminal.layout import render_box

                    io.write_line()
                    io.write_line(render_box(lines, double=False))
                except Exception:
                    for ln in lines:
                        io.write_line(ln)
            else:
                for ln in lines:
                    io.write_line(ln)
        except Exception:
            pass

    if care_note:
        try:
            from game.domain.needs import append_auto_care_note

            # one compact line for care ring
            compact = " ".join(x.strip() for x in lines if x.strip())[:100]
            if compact:
                append_auto_care_note(player, compact)
        except Exception:
            pass

    if log_auto:
        try:
            from game.runtime.auto_run_log import log_auto_event

            sev = _normalize_severity(
                severity
                or (get_catalog().get(canon) or get_catalog().get(code) or {}).get("severity")
                or SEV_INFO
            )
            level = "warn" if sev in (SEV_WARN, SEV_CRIT) else "info"
            msg = " · ".join(
                x.strip(" -·✦⚠") for x in lines if x.strip() and not x.strip().startswith("---")
            )[:80]
            if msg:
                log_auto_event(player, "alert", msg, level=level)
        except Exception:
            pass

    return lines


def emit_alert_lines(
    player: MutableMapping[str, Any],
    code: str,
    *,
    force: bool = False,
    **ctx: Any,
) -> List[str]:
    """Alias for collect_alert — domain returns lines for caller to merge."""
    return collect_alert(player, code, force=force, **ctx)


def recent_alerts(player: Mapping[str, Any], *, limit: int = 8) -> List[Dict[str, Any]]:
    hist = list(player.get("_alert_history") or [])
    return hist[-limit:]
