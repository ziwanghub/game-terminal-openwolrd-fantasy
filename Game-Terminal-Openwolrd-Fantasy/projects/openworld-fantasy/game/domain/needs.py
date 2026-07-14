"""
UX-Tama needs — T0 tick + N1–N4 combat/ATB/food/stat resist (soft).

Internal 0–100:
  hunger/fatigue high = worse · morale high = better
UI: bars inverted for comfort + "−" when band bad/crit.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

NEED_KEYS = ("hunger", "fatigue", "morale")

DEFAULT_NEEDS = {
    "hunger": 18,
    "fatigue": 12,
    "morale": 72,
}

EVENT_DELTAS: Dict[str, Dict[str, int]] = {
    "rest": {"hunger": 4, "fatigue": -18, "morale": 6},
    "explore": {"hunger": 8, "fatigue": 10, "morale": -2},
    "travel": {"hunger": 10, "fatigue": 14, "morale": -3},
    "combat": {"hunger": 5, "fatigue": 8, "morale": -1},
    "combat_win": {"hunger": 3, "fatigue": 4, "morale": 10},
    "combat_loss": {"hunger": 6, "fatigue": 12, "morale": -14},
    "eat": {"hunger": -28, "fatigue": -4, "morale": 6},
    "dungeon_tick": {"hunger": 3, "fatigue": 5, "morale": -1},
}


def ensure_needs(player: MutableMapping[str, Any]) -> Dict[str, int]:
    raw = player.get("needs")
    if not isinstance(raw, dict):
        needs = dict(DEFAULT_NEEDS)
        player["needs"] = needs
        return needs
    out: Dict[str, int] = {}
    for k in NEED_KEYS:
        try:
            out[k] = int(raw.get(k, DEFAULT_NEEDS[k]))
        except (TypeError, ValueError):
            out[k] = DEFAULT_NEEDS[k]
        out[k] = max(0, min(100, out[k]))
    player["needs"] = out
    return out


def get_needs(player: Mapping[str, Any]) -> Dict[str, int]:
    raw = player.get("needs")
    if not isinstance(raw, dict):
        return dict(DEFAULT_NEEDS)
    return {
        k: max(0, min(100, int(raw.get(k, DEFAULT_NEEDS[k]))))
        for k in NEED_KEYS
    }


def _clamp_needs(needs: MutableMapping[str, int]) -> None:
    for k in NEED_KEYS:
        needs[k] = max(0, min(100, int(needs.get(k, DEFAULT_NEEDS[k]))))


def _alloc(player: Mapping[str, Any], key: str) -> int:
    return int((player.get("stats_alloc") or {}).get(key) or 0)


def _resist_factors(player: Mapping[str, Any]) -> Dict[str, float]:
    """N3: stat investment softens needs gains / penalties (hidden)."""
    def_pts = _alloc(player, "defense")
    spd_pts = _alloc(player, "speed")
    int_pts = _alloc(player, "intelligence")
    atk_pts = _alloc(player, "atk")
    power_def = float(player.get("power_def") or 0)
    power_intel = float(player.get("power_intel") or 0)
    power_spd = float(player.get("power_spd") or 0)
    return {
        # multiply positive fatigue gains
        "fatigue_gain": 1.0 / (1.0 + 0.03 * def_pts + 0.01 * power_def),
        # multiply morale losses (negative morale deltas get amplified when this >1... use on abs loss)
        "morale_loss": 1.0 / (1.0 + 0.04 * int_pts + 0.02 * power_intel),
        "hunger_gain": 1.0 / (1.0 + 0.015 * def_pts + 0.01 * atk_pts),
        "atb_fatigue_soft": 1.0 / (1.0 + 0.035 * spd_pts + 0.01 * power_spd),
        "atk_hunger_soft": 1.0 / (1.0 + 0.02 * atk_pts),
        "collapse_resist": min(0.65, 0.04 * def_pts + 0.02 * power_def),
        "skill_fail_soft": 1.0 / (1.0 + 0.04 * int_pts + 0.015 * power_intel),
    }


def band(key: str, value: int) -> str:
    v = max(0, min(100, int(value)))
    if key == "morale":
        if v >= 75:
            return "high"
        if v >= 45:
            return "mid"
        if v >= 25:
            return "low"
        return "crit"
    if v <= 25:
        return "good"
    if v <= 50:
        return "mid"
    if v <= 75:
        return "bad"
    return "crit"


def soft_label(key: str, value: int) -> str:
    b = band(key, value)
    if key == "hunger":
        return {"good": "อิ่ม", "mid": "ปกติ", "bad": "หิว", "crit": "อดอยาก"}.get(b, "ปกติ")
    if key == "fatigue":
        return {"good": "เบา", "mid": "พอไหว", "bad": "ล้า", "crit": "หมดแรง"}.get(b, "พอไหว")
    if key == "morale":
        return {"high": "ขวัญดี", "mid": "มั่นคง", "low": "หด", "crit": "ย่ำแย่"}.get(b, "มั่นคง")
    return "?"


def _mark_for(key: str, value: int) -> str:
    """N1: − when bad, −− when crit (morale uses low/crit)."""
    b = band(key, value)
    if key == "morale":
        if b == "crit":
            return "−−"
        if b == "low":
            return "−"
        return ""
    if b == "crit":
        return "−−"
    if b == "bad":
        return "−"
    return ""


def apply_needs_event(
    player: MutableMapping[str, Any],
    event: str,
    *,
    silent: bool = False,
) -> List[str]:
    ensure_needs(player)
    deltas = EVENT_DELTAS.get(str(event) or "")
    if not deltas:
        return []
    resist = _resist_factors(player)
    needs = dict(player["needs"])
    before = dict(needs)
    for k, d in deltas.items():
        if k not in needs:
            continue
        dd = int(d)
        if k == "fatigue" and dd > 0:
            dd = int(round(dd * resist["fatigue_gain"]))
        elif k == "hunger" and dd > 0:
            dd = int(round(dd * resist["hunger_gain"]))
        elif k == "morale" and dd < 0:
            dd = int(round(dd * resist["morale_loss"]))  # dd negative, loss factor <1 softens
        needs[k] = int(needs[k]) + dd
    _clamp_needs(needs)
    player["needs"] = needs
    if silent:
        return []
    return _soft_change_notes(before, needs, event)


def apply_food_relief(
    player: MutableMapping[str, Any],
    *,
    hunger_relief: int = 28,
    fatigue_relief: int = 4,
    morale_boost: int = 6,
    silent: bool = False,
) -> List[str]:
    """N4: direct relief from food items (not potion-as-food)."""
    ensure_needs(player)
    needs = dict(player["needs"])
    before = dict(needs)
    needs["hunger"] = int(needs["hunger"]) - max(0, int(hunger_relief))
    needs["fatigue"] = int(needs["fatigue"]) - max(0, int(fatigue_relief))
    needs["morale"] = int(needs["morale"]) + max(0, int(morale_boost))
    _clamp_needs(needs)
    player["needs"] = needs
    if silent:
        return []
    notes = _soft_change_notes(before, needs, "eat")
    if not notes:
        notes = ["〔สถานะกายใจ〕", " …ท้อง: " + soft_label("hunger", needs["hunger"])]
    return notes


def _soft_change_notes(
    before: Mapping[str, int],
    after: Mapping[str, int],
    event: str,
) -> List[str]:
    notes: List[str] = []
    for key, label in (
        ("hunger", "ท้อง"),
        ("fatigue", "ล้า"),
        ("morale", "ขวัญ"),
    ):
        b, a = int(before.get(key, 0)), int(after.get(key, 0))
        if band(key, b) != band(key, a) or abs(a - b) >= 15:
            mark = _mark_for(key, a)
            prefix = f"{mark} " if mark else ""
            notes.append(f" …{label}: {prefix}{soft_label(key, a)}")
    if notes:
        notes.insert(0, "〔สถานะกายใจ〕")
    return notes


def format_needs_soft_lines(player: Mapping[str, Any]) -> List[str]:
    n = get_needs(player)
    lines = ["〔สถานะกายใจ · soft〕"]
    for key, label in (("hunger", "ท้อง"), ("fatigue", "ล้า"), ("morale", "ขวัญ")):
        mark = _mark_for(key, n[key])
        m = f"{mark} " if mark else ""
        lines.append(f" {label}  {m}{soft_label(key, n[key])}")
    return lines


def format_needs_bar_line(player: Mapping[str, Any], width: int = 8) -> str:
    from game.domain.bars import ratio_bar

    n = get_needs(player)
    parts = []
    for key, label, invert in (
        ("hunger", "ท้อง", True),
        ("fatigue", "ล้า", True),
        ("morale", "ขวัญ", False),
    ):
        fill = (100 - n[key]) if invert else n[key]
        mark = _mark_for(key, n[key])
        m = f"{mark}" if mark else ""
        # space after mark for readability
        prefix = f"{label} {m} " if m else f"{label} "
        parts.append(f"{prefix}{ratio_bar(fill, 100, width)}")
    return " ".join(parts)


def needs_pressure_hint(player: Mapping[str, Any]) -> Optional[str]:
    n = get_needs(player)
    if band("hunger", n["hunger"]) == "crit":
        return " …ท้องร้อง −− ควรกินเสบียง — เสี่ยงสลบ"
    if band("fatigue", n["fatigue"]) == "crit":
        return " …ร่างหนัก −− ควรพัก — แท่งต่อสู้จะช้า"
    if band("morale", n["morale"]) == "crit":
        return " …ขวัญย่ำแย่ −− สกิลอาจพลาด · บอสกดดัน"
    if band("hunger", n["hunger"]) == "bad":
        return " …หิว − โจมตี/ป้องกัน/หลบอ่อนลง"
    if band("fatigue", n["fatigue"]) == "bad":
        return " …ล้า − จังหวะ ATB ช้าลง"
    if band("morale", n["morale"]) == "low":
        return " …ขวัญหด − มืออาจสั่นตอนใช้สกิล"
    return None


# ── N2 combat / ATB modifiers ─────────────────────────────────────────────


def combat_needs_mults(player: Mapping[str, Any]) -> Dict[str, float]:
    """Hidden multipliers for damage / dodge / incoming (+ loadout EQ-W/N)."""
    n = get_needs(player)
    r = _resist_factors(player)
    hb = band("hunger", n["hunger"])
    # base tables
    atk = {"good": 1.02, "mid": 1.0, "bad": 0.92, "crit": 0.80}.get(hb, 1.0)
    # soften ATK penalty with atk investment
    if atk < 1.0:
        pen = 1.0 - atk
        atk = 1.0 - pen * r["atk_hunger_soft"]
    # N5: ร่างจำความอดอยาก — half hunger atk penalty
    flags = player.get("flags") or {}
    if flags.get("n5_hunger_memory") and atk < 1.0:
        atk = 1.0 - (1.0 - atk) * 0.5
    incoming = {"good": 0.98, "mid": 1.0, "bad": 1.06, "crit": 1.14}.get(hb, 1.0)
    dodge = {"good": 1.05, "mid": 1.0, "bad": 0.90, "crit": 0.75}.get(hb, 1.0)
    out = {
        "atk_mult": max(0.7, min(1.15, atk)),
        "incoming_mult": max(0.9, min(1.25, incoming)),
        "dodge_mult": max(0.55, min(1.15, dodge)),
    }
    # EQ-W/N/G/A soft stack
    try:
        from game.domain.loadout_context import loadout_combat_mults

        lm = loadout_combat_mults(player)
        out["atk_mult"] *= float(lm.get("atk_mult") or 1.0)
        out["incoming_mult"] *= float(lm.get("incoming_mult") or 1.0)
        out["atk_mult"] = max(0.65, min(1.2, out["atk_mult"]))
        out["incoming_mult"] = max(0.85, min(1.3, out["incoming_mult"]))
    except Exception:
        pass
    return out


def atb_fatigue_mult(player: Mapping[str, Any]) -> float:
    n = get_needs(player)
    r = _resist_factors(player)
    fb = band("fatigue", n["fatigue"])
    base = {"good": 1.05, "mid": 1.0, "bad": 0.88, "crit": 0.72}.get(fb, 1.0)
    if base < 1.0:
        pen = 1.0 - base
        base = 1.0 - pen * r["atb_fatigue_soft"]
    # N5: ATB ล้าช้าลงน้อยลง
    flags = player.get("flags") or {}
    if flags.get("n5_enduring_tempo") and base < 1.0:
        base = 1.0 - (1.0 - base) * 0.55
    try:
        from game.domain.loadout_context import loadout_combat_mults

        base *= float(loadout_combat_mults(player).get("atb_mult") or 1.0)
    except Exception:
        pass
    return max(0.62, min(1.15, base))


def skill_fail_chance(player: Mapping[str, Any]) -> float:
    """0–1 soft fail chance from low morale (hidden)."""
    n = get_needs(player)
    r = _resist_factors(player)
    mb = band("morale", n["morale"])
    raw = {"high": 0.0, "mid": 0.02, "low": 0.10, "crit": 0.20}.get(mb, 0.02)
    return max(0.0, min(0.35, raw * r["skill_fail_soft"]))


def skill_blocked_by_morale(player: Mapping[str, Any], skill: Optional[Mapping[str, Any]] = None) -> bool:
    """Some focus skills refuse to fire at crit morale."""
    n = get_needs(player)
    if band("morale", n["morale"]) != "crit":
        return False
    if not skill:
        return False
    tags = skill.get("tags") or skill.get("tags_list") or []
    if isinstance(tags, str):
        tags = [tags]
    sid = str(skill.get("id") or "")
    focus_ids = ("focus", "meditate", "channel", "mind")
    if any(t in ("focus", "channel", "mind", "precision") for t in tags):
        return True
    if any(x in sid for x in focus_ids):
        return True
    # high mana skills feel focus-y
    if int(skill.get("mana") or skill.get("mp") or 0) >= 25:
        return True
    return False


def note_n5_hunger_survived(player: MutableMapping[str, Any]) -> List[str]:
    """N5 soft unlock after surviving hunger soft-death / collapse."""
    flags = dict(player.get("flags") or {})
    if flags.get("n5_hunger_memory"):
        return []
    flags["n5_hunger_memory"] = True
    player["flags"] = flags
    labels = list(player.get("soft_titles") or [])
    title = "ร่างจำความอดอยาก"
    if title not in labels:
        labels.append(title)
        player["soft_titles"] = labels
    return [f"「{title}」— ร่างกายจำอะไรบางอย่างไว้"]


def note_n5_morale_boss(player: MutableMapping[str, Any]) -> List[str]:
    """N5: win boss while morale was crit or low (soft)."""
    flags = dict(player.get("flags") or {})
    if flags.get("n5_unbroken_heart"):
        return []
    n = get_needs(player)
    mb = band("morale", n["morale"])
    if mb not in ("crit", "low"):
        return []
    # require crit for full title; low only if already collapsed once
    if mb != "crit" and not flags.get("n5_hunger_memory"):
        return []
    flags["n5_unbroken_heart"] = True
    flags.setdefault("n5_enduring_tempo", True)
    player["flags"] = flags
    labels = list(player.get("soft_titles") or [])
    title = "ใจไม่แตก"
    if title not in labels:
        labels.append(title)
        player["soft_titles"] = labels
    return [f"「{title}」— ขวัญเคยถึงก้นเหวแล้วยังยืน"]


def try_hunger_collapse(
    player: MutableMapping[str, Any],
    rng: random.Random,
    *,
    action: str = "explore",
) -> Tuple[bool, List[str]]:
    """
    N1: crit hunger + heavy action → soft collapse chance.
    Caller applies soft_death if True.
    """
    ensure_needs(player)
    n = get_needs(player)
    if band("hunger", n["hunger"]) != "crit":
        return False, []
    if action not in ("explore", "travel", "combat", "dungeon_tick", "combat_win"):
        return False, []
    r = _resist_factors(player)
    base = 0.12 if action in ("explore", "dungeon_tick") else 0.18
    if action == "travel":
        base = 0.22
    if action == "combat":
        base = 0.15
    chance = base * (1.0 - r["collapse_resist"])
    # hungrier → slightly higher
    chance += max(0, n["hunger"] - 90) * 0.008
    chance = min(0.45, max(0.04, chance))
    if rng.random() > chance:
        return False, ["〔สถานะกายใจ〕", " …ท้อง −− สั่นคลอน แต่ยังยืนไหว"]
    return True, [
        "〔สถานะกายใจ〕",
        " …ร่างกายไม่ไหว — สลบเพราะความหิว",
    ]


def is_food_item(item: Mapping[str, Any]) -> bool:
    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if "food" in tags or item.get("food_tier") or item.get("hunger_relief"):
        return True
    kind = str(item.get("kind") or "")
    name = str(item.get("name") or "")
    if kind == "consumable" and any(k in name for k in ("เสบียง", "ขนม", "อาหาร", "ration", "bread")):
        return True
    return False


# ── T1 load delta (real-time away) ─────────────────────────────────────────

# Soft rates per real hour offline — capped; never kills the save.
LOAD_DELTA_PER_HOUR = {
    "hunger": 2.2,
    "fatigue": 1.6,
    "morale": -1.1,
}
LOAD_DELTA_MAX_HOURS = 48.0
LOAD_DELTA_CAP = {
    "hunger": 42,
    "fatigue": 36,
    "morale": -32,  # max morale loss (negative)
}


def stamp_saved_at(player: MutableMapping[str, Any], when: Optional[float] = None) -> str:
    """Set saved_at ISO + unix. Returns ISO string."""
    import time as _time

    ts = float(when if when is not None else _time.time())
    iso = _time.strftime("%Y-%m-%dT%H:%M:%S", _time.localtime(ts))
    player["saved_at"] = iso
    player["saved_at_unix"] = ts
    player["updated_at"] = iso
    return iso


def parse_saved_at_unix(player: Mapping[str, Any]) -> Optional[float]:
    """Best-effort parse saved_at / saved_at_unix / updated_at."""
    from datetime import datetime

    u = player.get("saved_at_unix")
    if u is not None:
        try:
            return float(u)
        except (TypeError, ValueError):
            pass
    for key in ("saved_at", "updated_at"):
        raw = player.get(key)
        if not raw:
            continue
        s = str(raw).strip().replace("Z", "")
        try:
            return datetime.fromisoformat(s[:19]).timestamp()
        except Exception:
            try:
                return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").timestamp()
            except Exception:
                continue
    return None


def compute_load_delta_hours(
    player: Mapping[str, Any],
    *,
    now: Optional[float] = None,
) -> float:
    import time as _time

    now_ts = float(now if now is not None else _time.time())
    saved = parse_saved_at_unix(player)
    if saved is None:
        return 0.0
    hours = max(0.0, (now_ts - saved) / 3600.0)
    return min(LOAD_DELTA_MAX_HOURS, hours)


def apply_load_delta(
    player: MutableMapping[str, Any],
    *,
    now: Optional[float] = None,
    force_hours: Optional[float] = None,
) -> List[str]:
    """
    T1: simulate neglect while offline. Soft only — no hard death.
    Call once on load. Idempotent per session via load_delta_applied flag
    (cleared on save).
    """
    ensure_needs(player)
    if player.get("_load_delta_done"):
        return []
    hours = (
        float(force_hours)
        if force_hours is not None
        else compute_load_delta_hours(player, now=now)
    )
    player["_load_delta_done"] = True
    # ignore tiny gaps (< 20 min)
    if hours < (20.0 / 60.0):
        return []

    resist = _resist_factors(player)
    needs = dict(player["needs"])
    before = dict(needs)

    dh = int(
        round(
            LOAD_DELTA_PER_HOUR["hunger"]
            * hours
            * resist.get("hunger_gain", 1.0)
        )
    )
    df = int(
        round(
            LOAD_DELTA_PER_HOUR["fatigue"]
            * hours
            * resist.get("fatigue_gain", 1.0)
        )
    )
    dm = int(
        round(
            LOAD_DELTA_PER_HOUR["morale"]
            * hours
            * resist.get("morale_loss", 1.0)
        )
    )
    # caps
    dh = max(0, min(int(LOAD_DELTA_CAP["hunger"]), dh))
    df = max(0, min(int(LOAD_DELTA_CAP["fatigue"]), df))
    # morale delta is negative; clamp magnitude
    max_loss = abs(int(LOAD_DELTA_CAP["morale"]))
    dm = max(-max_loss, min(0, dm))

    needs["hunger"] = int(needs["hunger"]) + dh
    needs["fatigue"] = int(needs["fatigue"]) + df
    needs["morale"] = int(needs["morale"]) + dm
    _clamp_needs(needs)
    player["needs"] = needs
    player["last_load_delta_hours"] = round(hours, 2)

    if dh == 0 and df == 0 and dm == 0:
        return []

    lines: List[str] = ["〔เวลาที่ผ่านไป · soft〕"]
    if hours >= 24:
        lines.append(" …ห่างนาน — ร่างกายและจิตเปลี่ยนไปโดยที่คุณไม่ได้เห็น")
    elif hours >= 6:
        lines.append(" …ห่างไปหลายชั่วโมง — รู้สึกถึงความว่างบนร่าง")
    else:
        lines.append(" …พักนอกเกมครู่หนึ่ง — สถานะกายใจขยับเบาๆ")
    lines.extend(_soft_change_notes(before, needs, "load_delta"))
    # always leave soft care hint if worsened
    if band("hunger", needs["hunger"]) in ("bad", "crit") or band(
        "fatigue", needs["fatigue"]
    ) in ("bad", "crit"):
        lines.append(" …ลองพักหรือกินเสบียง (ตัวละคร · R พัก / E กิน)")
    return [ln for ln in lines if ln]


# ── T2 Tama panel ─────────────────────────────────────────────────────────


def tama_mood_line(player: Mapping[str, Any]) -> str:
    n = get_needs(player)
    hb, fb, mb = band("hunger", n["hunger"]), band("fatigue", n["fatigue"]), band("morale", n["morale"])
    if hb == "crit" or fb == "crit":
        return "「…มองไม่ค่อยชัด — ร่างหนัก」"
    if mb == "crit":
        return "「เงียบ — ขวัญจม」"
    if hb == "bad" and fb == "bad":
        return "「อยากพัก… แล้วก็อยากกิน」"
    if hb == "bad":
        return "「ท้องร้องเบาๆ」"
    if fb == "bad":
        return "「ไหล่ตก — ล้า」"
    if mb in ("high",) and hb == "good":
        return "「พร้อมออกไปอีกนิด」"
    if mb == "high":
        return "「ยังไหว」"
    return "「…นิ่ง หายใจสม่ำเสมอ」"


def format_tama_body(player: Mapping[str, Any]) -> List[str]:
    """Silhouette only (no name/occupation — avoid hub duplication)."""
    n = get_needs(player)
    hb = band("hunger", n["hunger"])
    fb = band("fatigue", n["fatigue"])
    if fb == "crit":
        body = [
            "      .-.  ",
            "     ( x ) ",
            "      \\|/  ",
            "      / \\  ",
        ]
    elif fb == "bad":
        body = [
            "      .-.  ",
            "     ( · ) ",
            "      \\|/  ",
            "      /|   ",
        ]
    elif hb in ("bad", "crit"):
        body = [
            "      .-.  ",
            "     ( o ) ",
            "      /|\\  ",
            "      / \\  ",
        ]
    else:
        body = [
            "      .-.  ",
            "     ( · ) ",
            "      /|\\  ",
            "      / \\  ",
        ]
    return body


def format_tama_ascii(player: Mapping[str, Any], *, with_identity: bool = True) -> List[str]:
    """Minimal terminal silhouette — soft, not spoiler."""
    body = format_tama_body(player)
    mood = f" {tama_mood_line(player)}"
    if not with_identity:
        return [*body, mood]
    name = str(player.get("name") or "ผู้เดินทาง")
    occ = str(player.get("occupation") or player.get("occupation_id") or "")
    head = f" {name}" + (f" · {occ}" if occ else "")
    return [head, *body, mood]


def format_tama_panel(player: Mapping[str, Any], width: int = 10) -> List[str]:
    """T2: ASCII + needs bars + care hints (full page, e.g. status 1)."""
    ensure_needs(player)  # type: ignore
    lines: List[str] = [" Tama · สถานะมีชีวิต", "---"]
    lines.extend(format_tama_ascii(player, with_identity=True))
    lines.append("---")
    lines.append(f" {format_needs_bar_line(player, width=width)}")
    for ln in format_needs_soft_lines(player)[1:]:
        lines.append(ln)
    hint = needs_pressure_hint(player)
    if hint:
        lines.append(hint)
    lines.append("---")
    lines.append(" R พัก  ·  E กิน  ·  2 กระเป๋า")
    return lines


# ── T3 live optional (panel only) ─────────────────────────────────────────

# Soft drip per real second while PERSONAL is open (very slow — not punishing)
_PANEL_LIVE_PER_SEC = {
    "hunger": 0.012,   # ~43s per +1 hunger
    "fatigue": 0.008,
    "morale": -0.006,
}
_PANEL_LIVE_CAP_PER_OPEN = {"hunger": 4, "fatigue": 3, "morale": -3}


def tama_enter_animation_frames(player: Mapping[str, Any]) -> List[List[str]]:
    """
    T3: 2–3 soft frames when entering PERSONAL (ASCII only, no stats spoilers).
    Caller prints frames then final hub.
    """
    ensure_needs(player)  # type: ignore
    n = get_needs(player)
    fb = band("fatigue", n["fatigue"])
    # frame 1: settle
    f1 = [
        "      ...  ",
        "     (   ) ",
        "      | |  ",
        "      . .  ",
        " 「…ลืมตา」",
    ]
    # frame 2: breath
    f2 = [
        "      .-.  ",
        "     ( · ) ",
        "      \\|/  ",
        "      / \\  ",
        " 「…หายใจ」",
    ]
    # frame 3: current body (stable)
    f3 = format_tama_body(player) + [f" {tama_mood_line(player)}"]
    if fb == "crit":
        f2 = [
            "      .-.  ",
            "     ( x ) ",
            "      \\|/  ",
            "      / \\  ",
            " 「…ยังหนัก」",
        ]
    return [f1, f2, f3]


def stamp_tama_panel_open(player: MutableMapping[str, Any]) -> None:
    """Mark wall-clock open for live tick (T3)."""
    import time

    ensure_needs(player)
    player["_tama_panel_opened_unix"] = time.time()
    player["_tama_panel_last_tick_unix"] = time.time()
    player["_tama_live_accum"] = {"hunger": 0, "fatigue": 0, "morale": 0}
    player["_tama_enter_anim_done"] = False


def apply_tama_panel_live_tick(
    player: MutableMapping[str, Any],
    *,
    force: bool = False,
) -> List[str]:
    """
    Soft needs drip while PERSONAL hub is open (wall clock).
    Cap per open session so sitting still never destroys the run.
    """
    import time

    ensure_needs(player)
    try:
        from game.domain.ui_prefs import ensure_ui_prefs

        prefs = ensure_ui_prefs(player)
        if not prefs.get("live_tama", True) and not force:
            return []
    except Exception:
        pass

    now = time.time()
    last = float(player.get("_tama_panel_last_tick_unix") or now)
    opened = float(player.get("_tama_panel_opened_unix") or now)
    # ignore huge gaps (debug pause)
    dt = max(0.0, min(120.0, now - last))
    if dt < 0.8 and not force:
        return []
    player["_tama_panel_last_tick_unix"] = now

    needs = get_needs(player)
    before = dict(needs)
    accum = dict(player.get("_tama_live_accum") or {})
    changed = False

    def _apply_key(key: str, rate: float, cap_abs: int) -> None:
        nonlocal changed
        used = int(accum.get(key) or 0)
        if abs(used) >= abs(cap_abs):
            return
        frac_k = f"_{key}_frac"
        frac = float(accum.get(frac_k) or 0) + rate * dt
        step = int(frac)  # toward 0 truncates; negative for morale
        if step == 0:
            accum[frac_k] = frac
            return
        # room toward cap
        if cap_abs >= 0:
            room = cap_abs - used
            step = max(0, min(step, room))
        else:
            room = cap_abs - used  # e.g. -3 - 0 = -3
            step = min(0, max(step, room))
        if step == 0:
            accum[frac_k] = frac - int(frac)
            return
        needs[key] = int(needs[key]) + step
        accum[key] = used + step
        accum[frac_k] = frac - step
        changed = True

    _apply_key("hunger", _PANEL_LIVE_PER_SEC["hunger"], int(_PANEL_LIVE_CAP_PER_OPEN["hunger"]))
    _apply_key("fatigue", _PANEL_LIVE_PER_SEC["fatigue"], int(_PANEL_LIVE_CAP_PER_OPEN["fatigue"]))
    _apply_key("morale", _PANEL_LIVE_PER_SEC["morale"], int(_PANEL_LIVE_CAP_PER_OPEN["morale"]))

    player["_tama_live_accum"] = accum
    if not changed:
        return []

    _clamp_needs(needs)
    player["needs"] = needs
    notes = _soft_change_notes(before, needs, "panel_live")
    if notes:
        return [" …เวลาบนจอยังไหลเบาๆ"] + notes
    return [" …เวลาบนจอยังไหลเบาๆ"]


def close_tama_panel_session(player: MutableMapping[str, Any]) -> None:
    """Clear session-only live tick keys."""
    for k in (
        "_tama_panel_opened_unix",
        "_tama_panel_last_tick_unix",
        "_tama_live_accum",
        "_tama_enter_anim_done",
    ):
        player.pop(k, None)


def personal_rest_care(player: MutableMapping[str, Any]) -> List[str]:
    """T2 care: rest without full field heal (light)."""
    lines = apply_needs_event(player, "rest")
    # small HP/MP soft recover
    try:
        mhp = int(player.get("max_hp") or 100)
        mmp = int(player.get("max_mana") or 50)
        player["hp"] = min(mhp, int(player.get("hp") or 0) + max(8, mhp // 12))
        player["mana"] = min(mmp, int(player.get("mana") or 0) + max(5, mmp // 15))
        lines = list(lines) + [" …พักครู่ — ลมหายใจยาวขึ้น"]
    except Exception:
        pass
    return lines


def personal_eat_first_food(
    player: MutableMapping[str, Any],
    reg: Any,
) -> List[str]:
    """T2: consume first food in bag (same rules as bag use, simplified)."""
    ensure_needs(player)
    ids = list(player.get("inventory_ids") or [])
    for i, iid in enumerate(ids):
        it = (getattr(reg, "items", None) or {}).get(str(iid)) or {}
        if not is_food_item(it):
            continue
        # remove one
        from game.domain.equipment import remove_inventory_id

        if not remove_inventory_id(player, str(iid), reg):
            continue
        hr = int(it.get("hunger_relief") or (20 + 12 * int(it.get("food_tier") or 1)))
        fr = int(it.get("fatigue_relief") or max(0, 2 * int(it.get("food_tier") or 1)))
        mb = int(it.get("morale_boost") or max(2, 3 * int(it.get("food_tier") or 1)))
        lines = [f"กิน: {it.get('name') or iid}"]
        lines.extend(
            apply_food_relief(
                player, hunger_relief=hr, fatigue_relief=fr, morale_boost=mb
            )
        )
        return lines
    return ["ไม่มีเสบียงในกระเป๋า — ซื้ออาหารหรือคราฟเสบียง"]
