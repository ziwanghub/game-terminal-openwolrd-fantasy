"""
WO-039 Faction Mini-Moments — small soft encounters (not full quests).

Replayable · Soft Alert + world_relations + Anima · no new resources.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.domain.world_relations import (
    FACTION_DIVINE,
    FACTION_ECHO,
    FACTION_INFERNAL,
    adjust_faction,
    get_faction_score,
)

# ── Content (2–3 samples) ────────────────────────────────────────────────

MINI_MOMENTS: Dict[str, Dict[str, Any]] = {
    "divine_wind_gaze": {
        "id": "divine_wind_gaze",
        "faction": FACTION_DIVINE,
        "areas": ("ancient_city", "crystal_peak"),
        "label": "สายตาแห่งวายุ",
        "hint": "ลมวนรอบคนคุกเข่า · แสงบาง",
        "risk": "ต่ำ",
        "intro": [
            "  ลมวายุวนรอบผู้แปลกหน้าที่คุกเข่า — มือสั่นกุมเครื่องราง",
            "  เขาเงยหน้า: 「ช่วย… ข้าขอแค่คำอธิษฐานคู่」",
        ],
        "choices": {
            "help": {
                "label": "ช่วยอธิษฐานด้วย",
                "faction_delta": 5.0,
                "morale": 3,
                "anima_nudge": 1.0,
                "alert": "world.moment_divine_help",
                "flavor": [
                    "  คุณคุกเข่าคู่ — ลมอุ่นพัดผ่าน",
                    "  …จิตวิญญาณอบอุ่นขึ้น · ขวัญนิ่งลงเล็กน้อย",
                ],
            },
            "refuse": {
                "label": "เดินผ่านไป",
                "faction_delta": -2.0,
                "morale": 0,
                "anima_nudge": 0.0,
                "alert": "world.moment_divine_pass",
                "flavor": [
                    "  คุณเดินผ่าน — ลมเย็นลงชั่วขณะ",
                    "  สายตาจากที่สูง… หันหนีหรือไม่แน่ใจ",
                ],
            },
            "dodge": {
                "label": "หลบมอง · ไม่ยุ่ง",
                "faction_delta": -0.5,
                "morale": 0,
                "anima_nudge": 0.0,
                "alert": "",
                "flavor": ["  คุณเบี่ยงสายตา — ลมยังวน แต่ไม่แตะคุณ"],
            },
        },
    },
    "infernal_haze_echo": {
        "id": "infernal_haze_echo",
        "faction": FACTION_INFERNAL,
        "areas": ("mist_marsh", "cave_shadow"),
        "label": "เงามารแผ่ซ่าน",
        "hint": "หมอกดำ · เสียงหัวเราะไกล",
        "risk": "กลาง",
        "intro": [
            "  หมอกดำข้น — เงาร่างยิ้มในหมอก",
            "  「มารไม่ขอความช่วย… แค่ขอให้เธอมอง」",
        ],
        "choices": {
            "help": {
                "label": "จ้องกลับ · ยอมรับสายตา",
                "faction_delta": 4.0,  # warmer with infernal (risky favor)
                "morale": -4,
                "anima_nudge": -0.6,
                "alert": "world.moment_infernal_gaze",
                "flavor": [
                    "  คุณจ้องกลับ — หมอกยิ้มกว้างขึ้น",
                    "  ขวัญสั่น · จิตวิญญาณรู้สึกแผ่วชั่วขณะ",
                ],
            },
            "refuse": {
                "label": "ปฏิเสธ · หันหลัง",
                "faction_delta": -4.0,
                "morale": -1,
                "anima_nudge": 0.2,
                "alert": "world.moment_infernal_reject",
                "flavor": [
                    "  คุณหันหลัง — หมอกโกรธแผ่ว",
                    "  ขวัญกดเบา ๆ แต่จิตยังตั้งได้",
                ],
            },
            "dodge": {
                "label": "หลบหมอก · หนีทางแห้ง",
                "faction_delta": -1.0,
                "morale": 1,
                "anima_nudge": 0.0,
                "alert": "",
                "flavor": ["  คุณหลบหมอกสำเร็จ — หัวใจยังเต้นแรง"],
            },
        },
    },
    "echo_forest_whisper": {
        "id": "echo_forest_whisper",
        "faction": FACTION_ECHO,
        "areas": ("dark_forest",),
        "label": "เสียงกระซิบจากป่า",
        "hint": "ใบไม้กระซิบชื่อใครสักคน",
        "risk": "?",
        "intro": [
            "  ใบไม้กระซิบชื่อ — ไม่ใช่ชื่อคุณทั้งหมด",
            "  เงาโบราณรอคำตอบ: ยอมรับ · ปฏิเสธ · หรือเงียบ",
        ],
        "choices": {
            "help": {
                "label": "ยอมรับเสียง · ฟังต่อ",
                "faction_delta": 5.0,
                "morale": 1,
                "anima_nudge": 0.7,
                "alert": "world.moment_echo_accept",
                "flavor": [
                    "  คุณฟัง — เงาพยักหน้า",
                    "  …เงาโบราณยอมรับการมีอยู่ของคุณชั่วขณะ",
                ],
            },
            "refuse": {
                "label": "ปฏิเสธ · ไล่เสียง",
                "faction_delta": -3.0,
                "morale": -2,
                "anima_nudge": 0.0,
                "alert": "world.moment_echo_reject",
                "flavor": [
                    "  คุณไล่เสียง — ป่าเงียบกริบเกินไป",
                    "  เงายังจ้องจากโคนไม้",
                ],
            },
            "dodge": {
                "label": "เงียบ · เดินต่อ",
                "faction_delta": 0.5,
                "morale": 0,
                "anima_nudge": 0.15,
                "alert": "",
                "flavor": ["  คุณเงียบเดินต่อ — เสียงกระซิบจางลง"],
            },
        },
    },
    # ── WO-042 Area Mini-Moments expansion ────────────────────────────
    "infernal_cave_coal": {
        "id": "infernal_cave_coal",
        "faction": FACTION_INFERNAL,
        "areas": ("cave_shadow",),
        "label": "เถ้าถ่านใต้ถ้ำ",
        "hint": "ถ่านร้อน · เงายิ้มจากผนัง",
        "risk": "กลาง",
        "intro": [
            "  ถ้ำเงา — ถ่านดำยังอุ่น · เงาบนผนังยิ้มเอง",
            "  เสียงกระซิบ: 「เถ้านี้ของใคร… เธอยอมรับไหม」",
        ],
        "choices": {
            "help": {
                "label": "รับเถ้า · จ้องเงา",
                "faction_delta": 4.5,
                "morale": -3,
                "anima_nudge": -0.5,
                "alert": "world.moment_cave_coal_accept",
                "flavor": [
                    "  เถ้าติดนิ้ว — ร้อนคุ้นเคย",
                    "  ขวัญสั่น · พลังมารในถ้ำพยัก",
                ],
            },
            "refuse": {
                "label": "ปัดเถ้า · ไม่รับ",
                "faction_delta": -3.5,
                "morale": -1,
                "anima_nudge": 0.15,
                "alert": "world.moment_cave_coal_refuse",
                "flavor": [
                    "  คุณปัดเถ้าทิ้ง — เงาบนผนังหด",
                    "  ถ้ำเย็นลงชั่วขณะ · จิตยังตั้ง",
                ],
            },
            "dodge": {
                "label": "เดินเลี่ยง · หาแสงตะเกียง",
                "faction_delta": -0.8,
                "morale": 1,
                "anima_nudge": 0.0,
                "alert": "",
                "flavor": ["  คุณเดินหาตะเกียง — เถ้ายังอุ่นด้านหลัง"],
            },
        },
    },
    "echo_desert_mirage": {
        "id": "echo_desert_mirage",
        "faction": FACTION_ECHO,
        "areas": ("desert_heat",),
        "label": "ภาพลวงทราย",
        "hint": "เงาร่างในคลื่นร้อน · เรียกชื่อ",
        "risk": "?",
        "intro": [
            "  ทะเลทรายร้อนระอุ — ภาพลวงซ้อนเป็นเงาร่าง",
            "  เงาโบราณกระซิบชื่อจากคลื่นร้อน: ฟัง · ไล่ · หรือเมิน",
        ],
        "choices": {
            "help": {
                "label": "ฟังภาพลวง · ยอมรับชื่อ",
                "faction_delta": 5.0,
                "morale": 0,
                "anima_nudge": 0.8,
                "alert": "world.moment_desert_mirage_listen",
                "flavor": [
                    "  คุณฟัง — ภาพลวงพยัก · ทรายนิ่งชั่วขณะ",
                    "  จิตสั่นไหว · เงาโบราณจำคุณได้",
                ],
            },
            "refuse": {
                "label": "ไล่ภาพลวง · ไม่เชื่อ",
                "faction_delta": -3.0,
                "morale": -1,
                "anima_nudge": 0.0,
                "alert": "world.moment_desert_mirage_banish",
                "flavor": [
                    "  คุณไล่ภาพ — คลื่นร้อนหนาขึ้น",
                    "  เงายังจ้องจากขอบฟ้า",
                ],
            },
            "dodge": {
                "label": "เมิน · เดินตามเข็มทิศ",
                "faction_delta": 0.4,
                "morale": 1,
                "anima_nudge": 0.1,
                "alert": "",
                "flavor": ["  คุณเดินตามเข็มทิศ — ภาพลวงจางด้านหลัง"],
            },
        },
    },
    "divine_crystal_prayer": {
        "id": "divine_crystal_prayer",
        "faction": FACTION_DIVINE,
        "areas": ("crystal_peak",),
        "label": "คำอธิษฐานผลึก",
        "hint": "แสงผลึก · คนคุกเข่าบนยอด",
        "risk": "ต่ำ",
        "intro": [
            "  ยอดผลึก — แสงขาวบาง · นักเดินทางคุกเข่าอธิษฐาน",
            "  「ผลึกฟัง… ช่วยส่งคำขอของข้าขึ้นฟ้าด้วยได้ไหม」",
        ],
        "choices": {
            "help": {
                "label": "ร่วมอธิษฐาน · ส่งคำขอ",
                "faction_delta": 5.5,
                "morale": 4,
                "anima_nudge": 1.2,
                "alert": "world.moment_crystal_pray",
                "flavor": [
                    "  ผลึกส่งแสงอุ่น — คำขอลอยขึ้น",
                    "  จิตวิญญาณอุ่น · ขวัญนิ่ง · สายตาเทพบนยอด",
                ],
            },
            "refuse": {
                "label": "ปฏิเสธ · ไม่ยุ่งเรื่องสวรรค์",
                "faction_delta": -2.5,
                "morale": 0,
                "anima_nudge": 0.0,
                "alert": "world.moment_crystal_pass",
                "flavor": [
                    "  คุณเดินผ่าน — แสงผลึกเย็นลงชั่วขณะ",
                    "  สายตาจากที่สูง… หันหนีแผ่ว",
                ],
            },
            "dodge": {
                "label": "ก้มหน้า · ผ่านไปเงียบ ๆ",
                "faction_delta": -0.4,
                "morale": 0,
                "anima_nudge": 0.0,
                "alert": "",
                "flavor": ["  คุณก้มหน้าผ่าน — ผลึกยังส่อง แต่ไม่แตะคุณ"],
            },
        },
    },
    # ── WO-044 Area Mini-Moments (mountain / city / void) ─────────────
    "divine_mountain_gaze": {
        "id": "divine_mountain_gaze",
        "faction": FACTION_DIVINE,
        "areas": ("mountain_rock",),
        "label": "สายตาบนผา",
        "hint": "ลมสูง · เงาร่างบนยอดผา",
        "risk": "ต่ำ",
        "intro": [
            "  เขาหิน — ลมสูงพัด · เงาร่างยืนบนผาหันมามอง",
            "  「…ขอแค่คำอธิษฐานคู่ ก่อนพายุลง」",
        ],
        "choices": {
            "help": {
                "label": "อธิษฐานคู่ · ส่งสายตาขึ้นฟ้า",
                "faction_delta": 5.0,
                "morale": 3,
                "anima_nudge": 1.0,
                "alert": "world.moment_mountain_pray",
                "flavor": [
                    "  ลมอุ่นพัดผ่านผา — สายตาเทพจับจ้องอย่างนิ่ง",
                    "  จิตวิญญาณอุ่น · ขวัญนิ่งบนความสูง",
                ],
            },
            "refuse": {
                "label": "เดินลงเขา · ไม่ยุ่ง",
                "faction_delta": -2.0,
                "morale": 0,
                "anima_nudge": 0.0,
                "alert": "world.moment_mountain_pass",
                "flavor": [
                    "  คุณเดินลง — ลมเย็นฉับ",
                    "  สายตาบนผาหันหนี",
                ],
            },
            "dodge": {
                "label": "ก้มหน้า · เกาะทางเดิน",
                "faction_delta": -0.4,
                "morale": 1,
                "anima_nudge": 0.0,
                "alert": "",
                "flavor": ["  คุณเกาะทางเดิน — ลมยังแรง แต่ไม่แตะจิต"],
            },
        },
    },
    "divine_city_bell": {
        "id": "divine_city_bell",
        "faction": FACTION_DIVINE,
        "areas": ("ancient_city",),
        "label": "ระฆังเมืองเก่า",
        "hint": "เสียงระฆังบาง · คนคุกเข่าที่ลาน",
        "risk": "ต่ำ",
        "intro": [
            "  เมืองโบราณ — ระฆังดังแผ่วจากหอสูง",
            "  นักเดินทางคุกเข่า: 「ช่วยดึงเชือกระฆังคู่ข้า… เมืองจะจำ」",
        ],
        "choices": {
            "help": {
                "label": "ดึงระฆังคู่ · ส่งเสียง",
                "faction_delta": 5.0,
                "morale": 3,
                "anima_nudge": 0.9,
                "alert": "world.moment_city_bell",
                "flavor": [
                    "  ระฆังก้องแผ่ — ลมอุ่นวนลาน",
                    "  จิตอุ่น · เมืองเก่าเหมือนพยัก",
                ],
            },
            "refuse": {
                "label": "เดินผ่านลาน · ไม่ดึง",
                "faction_delta": -2.0,
                "morale": 0,
                "anima_nudge": 0.0,
                "alert": "world.moment_city_pass",
                "flavor": [
                    "  คุณเดินผ่าน — ระฆังเงียบเร็วเกินไป",
                    "  สายตาจากหอ… ไม่แน่ใจ",
                ],
            },
            "dodge": {
                "label": "เลี่ยงลาน · ไปตรอกข้าง",
                "faction_delta": -0.3,
                "morale": 0,
                "anima_nudge": 0.0,
                "alert": "",
                "flavor": ["  คุณเลี่ยงลาน — เสียงระฆังจางหลังหลังคา"],
            },
        },
    },
    "echo_void_pull": {
        "id": "echo_void_pull",
        "faction": FACTION_ECHO,
        "areas": ("void_rift",),
        "label": "แรงดึงสุญญะ",
        "hint": "รอยแยก · เสียงกระซิบจากความว่าง",
        "risk": "กลาง",
        "intro": [
            "  รอยแยกสุญญะ — ความว่างดึงนิ้วคุณเบา ๆ",
            "  เสียงกระซิบซ้อน: 「ฟังชื่อ… หรือตัดสาย」",
        ],
        "choices": {
            "help": {
                "label": "ฟังกระซิบ · ยอมรับแรงดึง",
                "faction_delta": 5.5,
                "morale": -1,
                "anima_nudge": 0.85,
                "alert": "world.moment_void_listen",
                "flavor": [
                    "  คุณฟัง — ความว่างพยัก · ชื่อใครสักคนชัดขึ้น",
                    "  จิตสั่นเชื่อม · เงาโบราณจำคุณในรอยแยก",
                ],
            },
            "refuse": {
                "label": "ตัดสาย · ถอยจากขอบ",
                "faction_delta": -3.5,
                "morale": -2,
                "anima_nudge": 0.1,
                "alert": "world.moment_void_cut",
                "flavor": [
                    "  คุณถอย — รอยแยกหดชั่วขณะ",
                    "  ขวัญกด · แต่จิตยังตั้งจากขอบ",
                ],
            },
            "dodge": {
                "label": "เมิน · เดินเลียบทางแห้ง",
                "faction_delta": 0.3,
                "morale": 1,
                "anima_nudge": 0.1,
                "alert": "",
                "flavor": ["  คุณเลียบทางแห้ง — แรงดึงจางด้านหลัง"],
            },
        },
    },
}


def moments_for_area(area_id: str) -> List[Dict[str, Any]]:
    aid = str(area_id or "")
    return [dict(m) for m in MINI_MOMENTS.values() if aid in (m.get("areas") or ())]


def roll_faction_moment_sight(
    player: Mapping[str, Any],
    rng: random.Random,
    *,
    area_id: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Chance to inject a mini-moment sight (replayable, throttled per area).
    WO-045 polish: first moments slightly easier · later quieter · avoid spam.
    Base ~20%; if never seen a moment this run ~28%; if many seen ~14%.
    """
    aid = str(area_id or player.get("location") or "")
    pool = moments_for_area(aid)
    if not pool:
        return None
    seen_n = int(player.get("_faction_moments_seen") or 0)
    if seen_n <= 0:
        chance = 0.28
    elif seen_n >= 6:
        chance = 0.14
    else:
        chance = 0.20
    # soft area cool-down: same area twice in a row less often
    last_area = str(player.get("_last_faction_moment_area") or "")
    if last_area == aid and seen_n > 0:
        chance *= 0.72
    # WO-046: relic × area synergy mult
    try:
        from game.data_load.registry import get_registry
        from game.domain.relic_anima import (
            moment_chance_factor,
            prefer_moment_faction_for_synergy,
        )

        reg = get_registry()
        if reg is not None:
            chance = min(0.48, max(0.08, chance * float(moment_chance_factor(player, reg, area_id=aid))))
            pool = prefer_moment_faction_for_synergy(player, reg, pool, area_id=aid)
    except Exception:
        pass
    if rng.random() > chance:
        return None
    # avoid same moment twice in a row
    last = str(player.get("_last_faction_moment") or "")
    candidates = [m for m in pool if m.get("id") != last] or pool
    m = dict(rng.choice(candidates))
    return {
        "kind": "faction_moment",
        "moment_id": m["id"],
        "faction": m["faction"],
        "label": m["label"],
        "hint": m["hint"],
        "risk": m.get("risk") or "?",
        "known": True,
        "moment": m,
    }


def resolve_moment_choice(
    player: MutableMapping[str, Any],
    moment_id: str,
    choice: str,
    *,
    reg: Any = None,
) -> List[str]:
    """
    Apply choice → faction + morale + anima soft + Soft Alert.
    choice: help | refuse | dodge
    """
    mid = str(moment_id or "")
    mdef = MINI_MOMENTS.get(mid)
    if not mdef:
        return ["  …เหตุการณ์จางหาย"]
    ch = str(choice or "dodge").lower()
    if ch in ("1", "help", "ช่วย", "h", "y"):
        ch = "help"
    elif ch in ("2", "refuse", "ไม่", "n", "r"):
        ch = "refuse"
    elif ch in ("3", "dodge", "หลบ", "d", "0"):
        ch = "dodge"
    opt = (mdef.get("choices") or {}).get(ch) or (mdef.get("choices") or {}).get("dodge")
    if not opt:
        return ["  …คุณยืนนิ่งจนเหตุการณ์ผ่าน"]

    lines: List[str] = list(opt.get("flavor") or [])
    fac = str(mdef.get("faction") or FACTION_ECHO)
    delta = float(opt.get("faction_delta") or 0)
    if delta:
        lines.extend(adjust_faction(player, fac, delta, reason=f"moment:{mid}:{ch}"))

    # morale soft
    mor_d = int(opt.get("morale") or 0)
    if mor_d:
        try:
            from game.domain.needs import ensure_needs, get_needs

            ensure_needs(player)
            n = get_needs(player)
            n["morale"] = max(0, min(100, int(n.get("morale") or 50) + mor_d))
            player["needs"] = n
        except Exception:
            pass

    # anima nudge + presence (+ WO-046 relic×moment synergy scale)
    an = float(opt.get("anima_nudge") or 0)
    try:
        from game.domain.relic_anima import apply_moment_synergy_nudge

        an, syn_lines = apply_moment_synergy_nudge(
            player,
            reg,
            moment_faction=fac,
            anima_nudge=an,
            area_id=str(player.get("location") or ""),
        )
        lines.extend(syn_lines)
    except Exception:
        pass
    if abs(an) > 0.01:
        try:
            from game.domain.stat_arch import ANIMA_KEY, anima_value, ensure_stat_arch

            ensure_stat_arch(player)
            player[ANIMA_KEY] = max(5.0, min(99.0, anima_value(player) + an))
            player["_anima_presence_felt"] = True
        except Exception:
            pass
    if an > 0.3:
        try:
            from game.domain.stat_arch import anima_presence_lines

            lines.extend(anima_presence_lines(player, "learn_glow", force=False, reg=reg))
        except Exception:
            pass
    elif an < -0.3:
        try:
            from game.domain.stat_arch import anima_presence_lines

            lines.extend(anima_presence_lines(player, "thin_warn", force=False, reg=reg))
        except Exception:
            pass

    # dedicated moment alert
    code = str(opt.get("alert") or "")
    if code:
        try:
            from game.domain.alerts import emit_alert_lines

            lines.extend(
                emit_alert_lines(
                    player,
                    code,
                    force=False,
                    item=str(mdef.get("label") or ""),
                    band=ch,
                )
            )
        except Exception:
            pass

    player["_last_faction_moment"] = mid
    player["_faction_moments_seen"] = int(player.get("_faction_moments_seen") or 0) + 1
    # WO-045: track area for cool-down on re-roll
    try:
        areas = tuple((mdef.get("areas") or ()))
        if areas:
            player["_last_faction_moment_area"] = str(areas[0])
    except Exception:
        pass
    # lean effect tracking for auto
    sc = get_faction_score(player, fac)
    player["_wr_moment_faction"] = fac
    player["_wr_moment_score"] = sc
    return lines


def run_moment_menu(
    player: MutableMapping[str, Any],
    sight: Mapping[str, Any],
    io: Any,
    *,
    reg: Any = None,
) -> None:
    """Interactive 3-choice mini-moment (manual field)."""
    m = sight.get("moment") or MINI_MOMENTS.get(str(sight.get("moment_id") or ""))
    if not isinstance(m, dict):
        io.write_line("  …สายตาโลกจางไป")
        return
    mid = str(m.get("id") or sight.get("moment_id") or "")
    for ln in m.get("intro") or []:
        io.write_line(ln)
    choices = m.get("choices") or {}
    order = [("help", "1"), ("refuse", "2"), ("dodge", "3")]
    io.write_line("---")
    for key, num in order:
        opt = choices.get(key) or {}
        io.write_line(f"  {num}  {opt.get('label') or key}")
    io.write_line("  0  เงียบ · เดินจาก")
    raw = io.read_line("  โลกมองคุณ> ").strip().lower()
    if raw in ("0", "", "q"):
        raw = "dodge"
    lines = resolve_moment_choice(player, mid, raw, reg=reg)
    for ln in lines:
        io.write_line(ln if str(ln).startswith(" ") else f"  {ln}")


def auto_resolve_moment(
    player: MutableMapping[str, Any],
    sight: Mapping[str, Any],
    *,
    reg: Any = None,
    prefs: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    """
    Auto: prefer dodge/help by faction score; avoid if policy + cold faction.
    """
    m = sight.get("moment") or MINI_MOMENTS.get(str(sight.get("moment_id") or ""))
    if not isinstance(m, dict):
        return []
    mid = str(m.get("id") or "")
    fac = str(m.get("faction") or FACTION_ECHO)
    sc = get_faction_score(player, fac)
    prefs = prefs or {}
    # optional: skip entirely if cold and avoid flag
    if prefs.get("auto_avoid_cold_faction", True) and sc <= 28:
        return [f"  ออโต้เลี่ยง Mini-Moment〔{m.get('label')}〕— สายตาโลกเย็น"]
    # choose
    if sc >= 55:
        choice = "help"
    elif sc <= 35:
        choice = "dodge" if fac == FACTION_INFERNAL else "refuse"
    else:
        choice = "dodge"
    lines = [f"  ออโต้เลือก: {choice} · {m.get('label')}"]
    lines.extend(resolve_moment_choice(player, mid, choice, reg=reg))
    return lines


def should_auto_pause_moment(player: Mapping[str, Any], sight: Mapping[str, Any]) -> bool:
    """True = pause auto for player decision (high stakes / cold faction)."""
    m = sight.get("moment") or {}
    fac = str(m.get("faction") or sight.get("faction") or "")
    sc = get_faction_score(player, fac) if fac else 42
    # pause if very cold infernal or first time
    if int(player.get("_faction_moments_seen") or 0) == 0:
        return True
    if fac == FACTION_INFERNAL and sc <= 35:
        return True
    return False
