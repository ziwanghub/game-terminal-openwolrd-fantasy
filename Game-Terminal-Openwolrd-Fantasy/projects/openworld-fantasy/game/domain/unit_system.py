"""
Unit class + exclusive unit skill (world-unique, one per player).

Rules:
  - Each player may hold at most ONE unit class / unit skill (lifetime).
  - Each unit id (and its exclusive skill) may be claimed by only ONE player
    per world_id (unit_claims.json under saves/{world}/).
  - Unlock chance is intentionally very low (hidden; soft message only).
  - Mastery starts low — unit skill weak until practiced.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.config import SAVES_DIR
from game.data_load.registry import DataRegistry

# Soft default if YAML omits chance — still rare
DEFAULT_UNIT_CHANCE = 0.022
# Absolute ceiling so data cannot accidentally set "easy" unit drops
MAX_UNIT_CHANCE = 0.05
# Joke jackpot may feel legendary but must not delete mid-game combat
JOKE_STYLE_MULT_CAP = 2.15
JOKE_POWER_ABS_CAP = 78


def claims_path(world_id: str) -> Path:
    d = SAVES_DIR / str(world_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / "unit_claims.json"


def load_claims(world_id: str) -> Dict[str, Any]:
    path = claims_path(world_id)
    if not path.exists():
        return {"by_unit": {}, "by_skill": {}, "schema": 2}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"by_unit": {}, "by_skill": {}, "schema": 2}
        # migrate legacy flat {unit_id: {player_id, ...}}
        if "by_unit" not in data and "schema" not in data:
            migrated = {"by_unit": {}, "by_skill": {}, "schema": 2}
            for k, v in data.items():
                if isinstance(v, dict) and v.get("player_id"):
                    migrated["by_unit"][str(k)] = v
                    sk = v.get("exclusive_skill")
                    if sk:
                        migrated["by_skill"][str(sk)] = {
                            "player_id": v.get("player_id"),
                            "player_name": v.get("player_name"),
                            "unit_id": str(k),
                        }
            return migrated
        data.setdefault("by_unit", {})
        data.setdefault("by_skill", {})
        data.setdefault("schema", 2)
        return data
    except Exception:
        return {"by_unit": {}, "by_skill": {}, "schema": 2}


def save_claims(world_id: str, claims: Mapping[str, Any]) -> None:
    path = claims_path(world_id)
    payload = dict(claims)
    payload.setdefault("schema", 2)
    payload.setdefault("by_unit", {})
    payload.setdefault("by_skill", {})
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _owner_of_unit(claims: Mapping[str, Any], unit_id: str) -> Optional[Dict[str, Any]]:
    by_u = claims.get("by_unit") or {}
    # legacy fallback
    if unit_id in by_u:
        o = by_u[unit_id]
        return o if isinstance(o, dict) else None
    if unit_id in claims and isinstance(claims.get(unit_id), dict):
        return claims[unit_id]  # type: ignore
    return None


def is_unit_claimed(
    world_id: str,
    unit_id: str,
    except_player_id: Optional[str] = None,
) -> bool:
    claims = load_claims(world_id)
    owner = _owner_of_unit(claims, unit_id)
    if not owner:
        return False
    if except_player_id and str(owner.get("player_id")) == str(except_player_id):
        return False
    return True


def is_unit_skill_claimed(
    world_id: str,
    skill_id: str,
    except_player_id: Optional[str] = None,
) -> bool:
    """True if this exclusive unit skill already has an owner in the world."""
    if not skill_id:
        return False
    claims = load_claims(world_id)
    by_s = claims.get("by_skill") or {}
    owner = by_s.get(str(skill_id))
    if not owner:
        # scan by_unit for exclusive_skill field
        for uid, rec in (claims.get("by_unit") or {}).items():
            if not isinstance(rec, dict):
                continue
            if str(rec.get("exclusive_skill") or "") == str(skill_id):
                owner = rec
                break
    if not owner:
        return False
    if except_player_id and str(owner.get("player_id")) == str(except_player_id):
        return False
    return True


def player_has_unit(player: Mapping[str, Any]) -> bool:
    """One unit skill max per player — any existing claim blocks further unlocks."""
    if player.get("unit_class_id"):
        return True
    if player.get("unit_skill"):
        return True
    if (player.get("flags") or {}).get("unit_skill_locked"):
        return True
    return False


def claim_unit(
    world_id: str,
    unit_id: str,
    player: Mapping[str, Any],
    *,
    exclusive_skill: Optional[str] = None,
) -> bool:
    """
    Atomic-ish claim under world file lock.
    Returns False if another player already owns this unit or its skill.
    """
    from game.domain.file_lock import world_file_lock

    pid = str(player.get("id") or "")
    if not pid:
        return False
    sk = str(exclusive_skill or "")

    with world_file_lock(world_id, "unit_claims", timeout=6.0):
        claims = load_claims(world_id)
        by_u = dict(claims.get("by_unit") or {})
        by_s = dict(claims.get("by_skill") or {})

        existing = by_u.get(unit_id)
        if existing and str(existing.get("player_id")) != pid:
            return False
        if sk and sk in by_s and str(by_s[sk].get("player_id")) != pid:
            return False

        rec = {
            "player_id": pid,
            "player_name": player.get("name"),
            "exclusive_skill": sk or None,
            "claimed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        by_u[unit_id] = rec
        if sk:
            by_s[sk] = {
                "player_id": pid,
                "player_name": player.get("name"),
                "unit_id": unit_id,
                "claimed_at": rec["claimed_at"],
            }
        claims["by_unit"] = by_u
        claims["by_skill"] = by_s
        claims["schema"] = 2
        save_claims(world_id, claims)
    return True


def ensure_unit_mastery(player: MutableMapping[str, Any]) -> None:
    player.setdefault("unit_mastery", 0)
    player.setdefault("unit_mastery_xp", 0)


def mastery_power_mult(mastery: int) -> float:
    """Level 0 weak … 5 strong."""
    table = [0.55, 0.70, 0.85, 1.0, 1.12, 1.25]
    m = max(0, min(5, int(mastery)))
    return table[m]


def mastery_mana_mult(mastery: int) -> float:
    """Low mastery = unit skill more expensive."""
    table = [1.35, 1.2, 1.1, 1.0, 0.95, 0.9]
    m = max(0, min(5, int(mastery)))
    return table[m]


def soft_mastery_label(mastery: int) -> str:
    labels = ["ยังเงียบ", "กระซิบ", "ตื่นบางส่วน", "ประสาน", "มั่นคง", "ตื่นเต็ม"]
    m = max(0, min(5, int(mastery)))
    return labels[m]


def gain_unit_mastery_xp(
    player: MutableMapping[str, Any],
    amount: int = 1,
    reason: str = "",
) -> List[str]:
    """Hidden XP toward mastery ranks."""
    if not player.get("unit_class_id"):
        return []
    ensure_unit_mastery(player)
    notes: List[str] = []
    player["unit_mastery_xp"] = int(player.get("unit_mastery_xp") or 0) + max(0, amount)
    thresholds = [5, 15, 30, 50, 80]
    cur = int(player.get("unit_mastery") or 0)
    xp = int(player["unit_mastery_xp"])
    while cur < 5 and xp >= thresholds[cur]:
        cur += 1
        player["unit_mastery"] = cur
        notes.append(f"◆ Unit …{soft_mastery_label(cur)} (รู้สึกถึงการประสานลึกขึ้น)")
    return notes


def _unlock_rng(player: Mapping[str, Any]) -> random.Random:
    """Varies across attempts so the same level isn't stuck forever."""
    rolls = int(player.get("unit_unlock_rolls") or 0)
    st = player.get("stats") or {}
    return random.Random(
        int(player.get("latent_seed") or 1)
        + int(player.get("level") or 1) * 1009
        + int(player.get("time_units") or 0)
        + int(st.get("boss_kills") or 0) * 17
        + int(st.get("kills") or 0)
        + rolls * 7919
        + int(time.time()) // 60  # soft minute drift (not pure re-roll spam)
    )


def _stat_val(player: Mapping[str, Any], key: str) -> int:
    """Alloc first, then legacy stats dict."""
    alloc = player.get("stats_alloc") or {}
    st = player.get("stats") or {}
    return int(alloc.get(key) or st.get(key) or 0)


def _eligible_units(
    player: Mapping[str, Any],
    reg: DataRegistry,
    world_id: str,
) -> List[str]:
    """
    Unit ids that pass hidden conditions and are free in this world.
    Conditions never shown in UI — varied axes so paths feel different.
    """
    units = getattr(reg, "unit_classes", None) or {}
    if not units:
        return []
    pid = str(player.get("id") or "")
    st = player.get("stats") or {}
    oid = str(player.get("occupation_id") or "")
    lib_n = len(player.get("library_entries_read") or [])
    flags = player.get("flags") or {}
    loc = str(player.get("location") or "")
    actions = player.get("action_counts") or {}
    out: List[str] = []
    for uid, u in units.items():
        sk = str(u.get("exclusive_skill") or "")
        if is_unit_claimed(world_id, uid, except_player_id=pid):
            continue
        if sk and is_unit_skill_claimed(world_id, sk, except_player_id=pid):
            continue
        un = u.get("unlock") or {}
        if int(player.get("level", 1)) < int(un.get("min_level", 99)):
            continue
        if un.get("max_level") is not None:
            if int(player.get("level", 1)) > int(un.get("max_level")):
                continue
        allowed = un.get("occupation_ids") or []
        if allowed and oid not in allowed:
            continue
        # hidden stat floors (alloc)
        stat_ok = True
        for stat_key, un_key in (
            ("crit", "min_stat_crit"),
            ("defense", "min_stat_defense"),
            ("magic", "min_stat_magic"),
            ("atk", "min_stat_atk"),
            ("speed", "min_stat_speed"),
            ("intelligence", "min_stat_intelligence"),
        ):
            need = int(un.get(un_key, 0) or 0)
            if need and _stat_val(player, stat_key) < need:
                stat_ok = False
                break
        if not stat_ok:
            continue
        if int(st.get("boss_kills", 0)) < int(un.get("min_boss_kills", 0)):
            continue
        if int(st.get("kills", 0)) < int(un.get("min_kills", 0)):
            continue
        if int(st.get("flees", 0)) < int(un.get("min_flees", 0)):
            continue
        if int(st.get("explores", 0)) < int(un.get("min_explores", 0)):
            continue
        if int(st.get("heals", 0)) < int(un.get("min_heals", 0)):
            continue
        if int(st.get("upgrades", 0) or st.get("gear_upgrades", 0)) < int(
            un.get("min_upgrades", 0)
        ):
            continue
        if int(st.get("chests", 0) or st.get("chests_opened", 0)) < int(
            un.get("min_chests", 0)
        ):
            continue
        combos = int(st.get("combos", 0)) or int(actions.get("attack", 0)) // 3
        if combos < int(un.get("min_combos", 0)):
            continue
        if lib_n < int(un.get("require_library_entries", 0)):
            continue
        req_flag = un.get("require_flag")
        if req_flag and not flags.get(str(req_flag)):
            continue
        need_loc = un.get("require_location") or un.get("location_contains")
        if need_loc and str(need_loc).lower() not in loc.lower():
            continue
        out.append(str(uid))
    return out


def try_unit_unlock_with_claim(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    force_uid: Optional[str] = None,
    force_success: bool = False,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Attempt unit awaken:
      - already has unit → no-op
      - world claim exclusive per unit id + exclusive skill
      - very low chance even when eligible
    """
    if player_has_unit(player):
        return []

    from game.domain.progression import ensure_progression, recompute_powers

    units = getattr(reg, "unit_classes", None) or {}
    if not units:
        return []
    ensure_progression(player, reg)
    world_id = str(player.get("world_id") or "default")
    pid = str(player.get("id") or "")
    if not pid:
        # ensure stable id for claims
        player["id"] = f"p_{int(player.get('latent_seed') or 1)}"
        pid = str(player["id"])

    # count every eligibility check path as a roll attempt (anti-spam soft)
    player["unit_unlock_rolls"] = int(player.get("unit_unlock_rolls") or 0) + 1
    rng = rng or _unlock_rng(player)

    candidates = _eligible_units(player, reg, world_id)
    if force_uid and force_uid in units:
        if force_uid not in candidates and not force_success:
            # still respect world claim unless tests force
            if is_unit_claimed(world_id, force_uid, except_player_id=pid):
                return ["…เงา Unit ชนิดนี้ถูกผู้อื่นครอบครองในโลกนี้แล้ว"]
        candidates = [force_uid] if force_uid in units else candidates

    if not candidates:
        return []

    # Very rare success: per-candidate chance, pick at most one
    winners: List[str] = []
    for uid in candidates:
        u = units[uid]
        un = u.get("unlock") or {}
        chance = float(un.get("chance", DEFAULT_UNIT_CHANCE))
        chance = max(0.0, min(MAX_UNIT_CHANCE, chance))
        if force_success or rng.random() <= chance:
            winners.append(uid)

    if not winners:
        # soft whisper only rarely so player doesn't farm messages
        if rng.random() < 0.08:
            return ["…ได้ยินเสียงจากที่ไกล — ยังไม่ใช่คราวนี้"]
        return []

    uid = rng.choice(winners)
    u = units[uid]
    sk = str(u.get("exclusive_skill") or "")

    if not claim_unit(world_id, uid, player, exclusive_skill=sk):
        return ["…เงา Unit ถูกผู้อื่นครอบครองในโลกนี้แล้ว"]

    # permanent one-unit lock on this character
    player["unit_class_id"] = uid
    player["unit_class_name"] = u.get("name", uid)
    player["unit_skill"] = sk
    flags = dict(player.get("flags") or {})
    flags["unit_skill_locked"] = True
    player["flags"] = flags
    ensure_unit_mastery(player)
    player["unit_mastery"] = 0
    player["unit_mastery_xp"] = 0

    if sk and sk in (reg.skills or {}):
        skills = list(player.get("skills") or [])
        if sk not in skills:
            skills.append(sk)
            player["skills"] = skills
        base = list(player.get("base_skills") or [])
        if sk not in base:
            base.append(sk)
            player["base_skills"] = base

    recompute_powers(player, reg)
    sk_name = (reg.skills.get(sk) or {}).get("name") if sk else None
    lines = [
        f"◆◆◆ อาชีพลับปลุกขึ้น: {u.get('name')} ◆◆◆",
        " (ชั้น Unit — คนละระบบจากอาชีพหลัก · ได้สกิลเฉพาะติดตัว)",
        f"สถานะ: {soft_mastery_label(0)} — ยังเงียบ ต้องใช้และประยุกต์",
        "ชนิดนี้มีเจ้าของได้เพียงหนึ่งในโลก · คุณรับอาชีพลับอื่นไม่ได้แล้ว",
        "ความแรงขึ้นกับแนวลงแต้ม + สไตล์การเล่นที่สะสม — ระบบไม่บอกเงื่อนไข",
    ]
    tier = str(u.get("power_tier") or "")
    if tier == "joke":
        lines.append("…ดูอ่อนแอจนน่าสงสัย (อาจไม่ใช่ของไร้ค่าตลอดไป)")
    elif tier == "broken":
        lines.append("…พลังดิบมหาศาล — แต่จะฟังคุณหรือไม่ ยังไม่รู้")
    if sk_name:
        lines.insert(1, f"สกิลอาชีพลับ: {sk_name}")
    sk_def = (reg.skills.get(sk) or {}) if sk else {}
    if sk_def:
        lines.append(f" {soft_affinity_feel(player, sk_def, reg)}")
    return lines


def _player_style_signals(player: Mapping[str, Any]) -> Dict[str, float]:
    """
    Normalize playstyle signals to ~0..1 (hidden).
    Built from stats already tracked — no extra UI.
    """
    st = player.get("stats") or {}
    alloc = player.get("stats_alloc") or {}
    actions = player.get("action_counts") or {}

    def _n(v: float, soft: float) -> float:
        return max(0.0, min(1.0, float(v) / max(1.0, soft)))

    kills = float(st.get("kills") or 0)
    flees = float(st.get("flees") or 0)
    explores = float(st.get("explores") or actions.get("explore") or 0)
    heals = float(st.get("heals") or 0)
    bosses = float(st.get("boss_kills") or 0)
    combos = float(st.get("combos") or 0) or float(actions.get("attack") or 0) / 3.0
    upgrades = float(st.get("upgrades") or st.get("gear_upgrades") or 0)
    chests = float(st.get("chests") or st.get("chests_opened") or 0)
    rests = float(st.get("rests") or 0)
    lib = float(len(player.get("library_entries_read") or []))
    money = float(player.get("money_world") or 0)
    loc = str(player.get("location") or "").lower()
    atk_p = float(alloc.get("atk") or 0)
    def_p = float(alloc.get("defense") or 0)
    mag_p = float(alloc.get("magic") or 0)
    spd_p = float(alloc.get("speed") or 0)
    crit_p = float(alloc.get("crit") or 0)
    int_p = float(alloc.get("intelligence") or 0)

    return {
        "kills": _n(kills, 80.0),
        "flees": _n(flees, 12.0),
        "explores": _n(explores, 40.0),
        "heals": _n(heals, 25.0),
        "boss_kills": _n(bosses, 6.0),
        "combos": _n(combos, 40.0),
        "upgrades": _n(upgrades, 15.0),
        "chests": _n(chests, 20.0),
        "rests": _n(rests, 15.0),
        "library": _n(lib, 8.0),
        # inverted / lifestyle
        "low_kills": max(0.0, 1.0 - _n(kills, 50.0)),
        "low_money": max(0.0, 1.0 - _n(money, 800.0)),
        "low_atk": max(0.0, 1.0 - _n(atk_p, 12.0)),
        "atk_pts": _n(atk_p, 14.0),
        "def_pts": _n(def_p, 14.0),
        "magic_pts": _n(mag_p, 14.0),
        "speed_pts": _n(spd_p, 14.0),
        "crit_pts": _n(crit_p, 12.0),
        "intel_pts": _n(int_p, 12.0),
        # location one-hots (0/1)
        "loc_void": 1.0 if "void" in loc else 0.0,
        "loc_crystal": 1.0 if "crystal" in loc else 0.0,
        "loc_marsh": 1.0 if "marsh" in loc or "mist" in loc else 0.0,
        "loc_desert": 1.0 if "desert" in loc else 0.0,
        "loc_forest": 1.0 if "forest" in loc else 0.0,
        "loc_cave": 1.0 if "cave" in loc or "shadow" in loc else 0.0,
        "loc_mountain": 1.0 if "mountain" in loc or "rock" in loc else 0.0,
        "loc_city": 1.0 if "city" in loc or "ancient" in loc else 0.0,
    }


def unit_style_score(
    player: Mapping[str, Any],
    unit_def: Optional[Mapping[str, Any]] = None,
    reg: Optional[DataRegistry] = None,
) -> float:
    """
    0..1 how much current playstyle matches this unit's hidden wants.
    Defaults by power_tier if unit has no style_wants.
    """
    uid = str(player.get("unit_class_id") or "")
    if unit_def is None and reg is not None and uid:
        unit_def = (getattr(reg, "unit_classes", None) or {}).get(uid) or {}
    unit_def = unit_def or {}
    wants = dict(unit_def.get("style_wants") or {})
    tier = str(unit_def.get("power_tier") or "mid")
    if not wants:
        # mild defaults so mid/strong still vary a bit
        wants = {
            "joke": {"flees": 0.4, "explores": 0.5, "low_kills": 0.4, "library": 0.3, "low_money": 0.3},
            "broken": {"boss_kills": 0.5, "kills": 0.35, "upgrades": 0.25, "combos": 0.2},
            "weak": {"explores": 0.3, "heals": 0.3, "rests": 0.2},
            "mid": {"kills": 0.3, "explores": 0.3, "combos": 0.25},
            "strong": {"kills": 0.35, "boss_kills": 0.25, "combos": 0.25, "upgrades": 0.15},
        }.get(tier, {"kills": 0.3, "explores": 0.3})
    sig = _player_style_signals(player)
    # optional location bonus keys inside wants (loc_*)
    num = 0.0
    den = 0.0
    for key, w in wants.items():
        ww = float(w or 0)
        if ww <= 0:
            continue
        den += ww
        num += ww * float(sig.get(str(key), 0.0))
    if den <= 0:
        return 0.45
    return max(0.0, min(1.0, num / den))


def unit_style_resonance_mult(
    player: Mapping[str, Any],
    *,
    reg: Optional[DataRegistry] = None,
    unit_def: Optional[Mapping[str, Any]] = None,
) -> float:
    """
    Hidden Style Resonance (HSR):
      joke  — looks weak; high style match → extremely strong
      broken — looks strong; low style match → nearly useless
    Never exposed as numbers.
    """
    uid = str(player.get("unit_class_id") or "")
    if unit_def is None and reg is not None and uid:
        unit_def = (getattr(reg, "unit_classes", None) or {}).get(uid) or {}
    unit_def = unit_def or {}
    tier = str(unit_def.get("power_tier") or "mid")
    score = unit_style_score(player, unit_def, reg)

    if tier == "joke":
        # trash → jackpot (capped — playtest-safe)
        if score < 0.32:
            return 0.22 + score * 0.9
        if score < 0.55:
            return 0.55 + (score - 0.32) * 1.35
        # high match: strong surprise, not infinite
        return min(JOKE_STYLE_MULT_CAP, 1.0 + (score - 0.55) * 2.8)

    if tier == "broken":
        # demands matching lifestyle — mismatch gutters hard
        if score < 0.38:
            return 0.12 + score * 0.65  # near useless
        if score < 0.62:
            return 0.42 + (score - 0.38) * 1.45
        return min(1.22, 0.88 + (score - 0.62) * 0.95)

    if tier == "weak":
        return max(0.35, min(1.35, 0.4 + score * 0.95))
    if tier == "strong":
        return max(0.45, min(1.3, 0.55 + score * 0.75))
    # mid
    return max(0.4, min(1.28, 0.5 + score * 0.8))


def unit_skill_affinity_mult(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
) -> float:
    """
    Stat-investment affinity for unit skill elements.
    Wrong build → skill nearly useless (combined later with style resonance).
    """
    if not skill.get("unit_only"):
        return 1.0
    # guard / defense units
    if skill.get("guard_class") or skill.get("slot") == "defense":
        pdef = float(player.get("power_def") or 0)
        pmdef = float(player.get("power_mdef") or 0)
        score = pdef * 0.65 + pmdef * 0.35
        return max(0.28, min(1.35, 0.22 + score / 28.0))

    elems = {str(e).lower() for e in (skill.get("elements") or [])}
    mag_set = {
        "arcane",
        "fire",
        "water",
        "holy",
        "lightning",
        "shadow",
        "nature",
        "wind",
    }
    has_mag = bool(elems & mag_set)
    has_phys = "physical" in elems or not elems
    patk = float(player.get("power_atk") or 0)
    pmag = float(player.get("power_mag") or 0)
    pcrit = float(player.get("power_crit") or 0)
    pspd = float(player.get("power_spd") or 0)

    if has_mag and not has_phys:
        # wind/speed-tagged soft: mix mag + speed for light jokes
        if elems <= {"wind"} or elems == {"wind"}:
            return max(
                0.22,
                min(1.45, 0.15 + pmag / 40.0 + pspd / 38.0 + pcrit / 130.0),
            )
        return max(0.22, min(1.45, 0.18 + pmag / 32.0 + pcrit / 120.0))
    if has_phys and not has_mag:
        return max(0.28, min(1.4, 0.22 + patk / 36.0 + pcrit / 100.0))
    if has_mag and has_phys:
        blend = (patk + pmag) * 0.5 + pcrit * 0.15
        return max(0.30, min(1.35, 0.25 + blend / 38.0))
    if skill.get("heal") and not skill.get("power"):
        return max(0.35, min(1.3, 0.3 + pmag / 40.0 + float(player.get("power_def") or 0) / 50.0))
    return max(0.35, min(1.25, 0.35 + pspd / 45.0 + patk / 60.0))


def unit_effective_mult(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> float:
    """Combined stat affinity × style resonance × mastery (mastery applied outside optional)."""
    aff = unit_skill_affinity_mult(player, skill)
    sty = unit_style_resonance_mult(player, reg=reg)
    return max(0.05, aff * sty)


def soft_path_band(mult: float) -> str:
    """Standard soft language: ผิดทาง / พอใช้ / เข้าทาง — no numbers."""
    if mult < 0.45:
        return "ผิดทาง"
    if mult < 0.85:
        return "พอใช้"
    return "เข้าทาง"


def soft_affinity_feel(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> str:
    """Soft one-liner — path band + unit flavor."""
    if reg is None:
        try:
            from game.data_load.registry import get_registry

            reg = get_registry()
        except Exception:
            reg = None
    m = unit_effective_mult(player, skill, reg)
    band = soft_path_band(m)
    uid = str(player.get("unit_class_id") or "")
    tier = ""
    if reg is not None and uid:
        tier = str(((getattr(reg, "unit_classes", None) or {}).get(uid) or {}).get("power_tier") or "")
    if band == "ผิดทาง":
        if tier == "broken":
            return "「ผิดทาง」อาชีพลับดูแรงแต่ไม่ยอมออกแรง — สไตล์/แต้มยังไม่ตรง"
        if tier == "joke":
            return "「ผิดทาง」อาชีพลับยังเงียบราวของไร้ค่า"
        return "「ผิดทาง」อาชีพลับแผ่ว — แนวเล่น/แต้มยังไม่เข้า"
    if band == "พอใช้":
        return "「พอใช้」อาชีพลับตอบบ้าง — ยังไม่สุด"
    # เข้าทาง
    if tier == "joke" and m >= 1.6:
        return "「เข้าทาง」สิ่งที่เคยไร้ค่า ระเบิดแรงผิดปกติ…"
    if tier == "broken":
        return "「เข้าทาง」อาชีพลับสั่นเต็มแรง — ของแรงฟังคุณแล้ว"
    return "「เข้าทาง」อาชีพลับสั่นชัด — แนวเล่นเข้าทางสกิล"


def apply_unit_skill_scaling(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
    power: int,
    mana: int,
    reg: Optional[DataRegistry] = None,
) -> Tuple[int, int]:
    """
    Scale unit skill by mastery × stat affinity × style resonance.
    joke + matching style can exceed unmatched broken; wrong style gutters both.
    """
    if not skill.get("unit_only"):
        return power, mana
    if not player.get("unit_class_id"):
        return power, mana
    if reg is None:
        try:
            from game.data_load.registry import get_registry

            reg = get_registry()
        except Exception:
            reg = None
    m = int(player.get("unit_mastery") or 0)
    aff = unit_skill_affinity_mult(player, skill)
    sty = unit_style_resonance_mult(player, reg=reg)
    uid = str(player.get("unit_class_id") or "")
    tier = ""
    if reg is not None and uid:
        tier = str(
            ((getattr(reg, "unit_classes", None) or {}).get(uid) or {}).get("power_tier")
            or skill.get("unit_power_tier")
            or ""
        )
    base = int(power)
    # joke "true form": matching lifestyle reveals hidden power floor
    if tier == "joke" and sty >= 1.2:
        base = max(base, int(12 + sty * 9))  # ~23–31 before mult
        aff = max(aff, 0.72)
    elif tier == "joke" and sty >= 0.9:
        base = max(base, int(6 + sty * 5))
        aff = max(aff, 0.55)
    combined = aff * sty
    p = int(round(base * mastery_power_mult(m) * combined))
    # soft ceilings — joke may surprise, not erase the game
    lv = max(1, int(player.get("level") or 1))
    joke_cap = min(JOKE_POWER_ABS_CAP, max(26, int(16 + lv * 2.0)))
    abs_cap = joke_cap if tier == "joke" else 110
    if tier == "broken" and sty < 0.4:
        # mismatched broken: hard soft floor so it *feels* wasted
        p = min(p, max(1, int(base * 0.12 * mastery_power_mult(m))))
    p = max(1, min(abs_cap, p))
    c = int(round(mana * mastery_mana_mult(m)))
    if combined < 0.5:
        c = int(round(c * 1.08))
    return p, max(0, c)
