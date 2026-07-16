"""
Occupation path, visible stat allocation, hidden latent power,
rank breakthrough, library knowledge, unit class unlock.

Players see: ATK / DEF / MAG / SPD / CRT invested points.
Players never see: latent_growth multipliers or exact formulas.
"""
from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry

# Allocated in P menu (visible). luck is NEVER shown / never allocated here.
# CM3: intelligence removed from free P — grows soft / hidden (see combo_mind).
ALLOCATE_KEYS = ("atk", "defense", "magic", "speed")
# Still stored on stats_alloc for legacy / unit affinity / power recompute
ALLOC_STORAGE_KEYS = ("atk", "defense", "magic", "speed", "intelligence")
# Full keys for latent tables (crit kept for legacy gear affinity)
STAT_KEYS = ("atk", "defense", "magic", "speed", "intelligence", "crit")
STAT_LABELS = {
    "atk": "โจมตี",
    "defense": "ป้องกัน",
    "magic": "เวท",
    "speed": "ความเร็ว",
    "intelligence": "ความฉลาด",
    "crit": "คริติคอล",  # legacy only — not in allocate menu
}


def ensure_progression(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    player.setdefault("stat_points", 0)
    player.setdefault(
        "stats_alloc",
        {k: 0 for k in ALLOC_STORAGE_KEYS},
    )
    # migrate: ensure storage keys exist
    sa = dict(player.get("stats_alloc") or {})
    for k in ALLOC_STORAGE_KEYS:
        sa.setdefault(k, 0)
    player["stats_alloc"] = sa
    # CM3: one-time soft migrate — past P-int invest still counts as mind growth
    flags = dict(player.get("flags") or {})
    if not flags.get("cm3_int_migrated"):
        old_int = int(sa.get("intelligence") or 0)
        if old_int > 0:
            player["learn_points"] = int(player.get("learn_points") or 0) + max(
                0, old_int // 2
            )
            player["mind_growth"] = float(player.get("mind_growth") or 0) + old_int * 0.35
        flags["cm3_int_migrated"] = True
        player["flags"] = flags
    player.setdefault("mind_growth", float(player.get("mind_growth") or 0))
    player.setdefault("power_atk", float(player.get("base_atk", 5)))
    player.setdefault("power_def", 5.0)
    player.setdefault("power_mag", 5.0)
    player.setdefault("power_mdef", float(player.get("power_mag") or 5.0))
    player.setdefault("power_spd", 5.0)
    player.setdefault("power_intel", 3.0)
    player.setdefault("power_crit", 3.0)
    player.setdefault("alloc_atk_bonus", 0)
    player.setdefault("alloc_def_bonus", 0)
    player.setdefault("alloc_mag_bonus", 0)
    player.setdefault("alloc_spd_bonus", 0)
    player.setdefault("gear_def_bias", 0.0)
    player.setdefault("gear_mdef_bias", 0.0)
    player.setdefault("gear_atk_bias", 0.0)
    player.setdefault("gear_mag_bias", 0.0)
    player.setdefault("gear_atb_bias", 0.0)
    player.setdefault("crit_chance", 5.0)
    player.setdefault("dodge_chance", 3.0)  # soft evade %
    player.setdefault("luck_score", 0.0)  # hidden — never display raw
    player.setdefault("learn_points", 0)  # hidden sources
    # WO-035: anima = Spirit core facet value (not morale / not relic.spirit_*)
    try:
        from game.domain.stat_arch import ensure_stat_arch

        ensure_stat_arch(player)
    except Exception:
        player.setdefault("anima", 45.0)
        player.setdefault("world_relations", {})
    player.setdefault("intel_options", False)
    player.setdefault("intel_current", None)  # filled by intelligence.ensure
    player.setdefault("intel_max", 3)
    player.setdefault("intel_max_boost", 0)
    player.setdefault("atb_intel_surge", 0.0)
    player.setdefault("atb_intel_surge_turns", 0)
    player.setdefault("occ_rank_index", 0)
    player.setdefault("occ_rank_title", "")
    player.setdefault("unit_class_id", None)
    player.setdefault("unit_skill", None)
    player.setdefault("library_unlocked", False)
    player.setdefault("library_entries_read", [])
    player.setdefault("library_last_visit", -999)
    player.setdefault("flags", {})
    player.setdefault("blessing_flags", [])
    player.setdefault("emergency_blessings", [])
    if not player.get("latent_seed"):
        raw = f"{player.get('name','x')}|{player.get('occupation_id','y')}|{player.get('birth','z')}"
        player["latent_seed"] = int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)
    if not player.get("occ_rank_title"):
        _sync_rank_title(player, reg)
    # refresh luck soft from birth/area/party (never shown)
    recompute_luck_score(player, reg)


def init_progression(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    """Call once after create/load — safe full init."""
    ensure_progression(player, reg)
    _sync_rank_title(player, reg)
    recompute_powers(player, reg)


def _occ(player: Mapping[str, Any], reg: DataRegistry) -> Dict[str, Any]:
    oid = str(player.get("occupation_id") or "")
    return dict(reg.occupations.get(oid) or {})


def _latent_mult(player: Mapping[str, Any], reg: DataRegistry, stat: str) -> float:
    occ = _occ(player, reg)
    base = float((occ.get("latent_growth") or {}).get(stat, 1.0))
    # unit class overrides blend
    uid = player.get("unit_class_id")
    if uid and getattr(reg, "unit_classes", None):
        u = reg.unit_classes.get(uid) or {}
        ug = (u.get("latent_growth") or {}).get(stat)
        if ug is not None:
            base = (base + float(ug)) / 2.0
    # tiny stable noise so pure reverse-engineering is harder (±4%)
    seed = int(player.get("latent_seed", 1))
    noise = 1.0 + (((seed + hash(stat)) % 17) - 8) * 0.005
    return base * noise


def recompute_luck_score(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    """
    Hidden luck — never shown. Factors: birth, seed, area, party size, gear sets, flags.
    Can be positive or slightly negative.
    """
    seed = int(player.get("latent_seed") or 1)
    birth = str(player.get("birth") or "1/1/2000")
    try:
        day = int(birth.split("/")[0])
        month = int(birth.split("/")[1])
    except Exception:
        day, month = 1, 1
    base = (((seed % 97) - 48) * 0.002) + ((day + month * 3) % 11 - 5) * 0.004
    # area soft
    loc = str(player.get("location") or "")
    base += ((hash(loc) % 9) - 4) * 0.003
    # party
    party_n = len(player.get("party") or [])
    base += (party_n - 1) * 0.01 if party_n else 0.0
    # gear sets active
    sets = len(player.get("active_sets") or [])
    base += sets * 0.025
    # blessing fox luck
    if "fox_luck" in (player.get("blessing_flags") or []):
        base += 0.06
    # clamp soft
    player["luck_score"] = max(-0.25, min(0.45, base))


def recompute_powers(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    """Turn allocated points + latent into combat powers. Not shown raw."""
    # setdefaults only — do not call ensure_progression (avoids recursion)
    player.setdefault("stats_alloc", {k: 0 for k in ALLOC_STORAGE_KEYS})
    alloc = player.get("stats_alloc") or {}
    # base from occupation starting affinity
    occ = _occ(player, reg)
    base_atk = float(player.get("base_atk", occ.get("atk", 5)))
    powers = {
        "atk": base_atk * 0.35,
        "defense": 4.0 + float(occ.get("hp", 100)) / 40.0,
        "magic": 3.0 + float(occ.get("mana", 50)) / 25.0,
        "speed": 5.0 + float(occ.get("pressure", 10)) / 10.0,
        "intelligence": 3.0,
        "crit": 2.5,
    }
    # P menu stats + legacy intelligence storage (not in ALLOCATE_KEYS)
    for st in ALLOC_STORAGE_KEYS:
        pts = int(alloc.get(st, 0))
        mult = _latent_mult(player, reg, st)
        # diminishing returns on raw points
        gain = (pts * 1.15) * mult + (max(0, pts) ** 0.85) * 0.35 * mult
        powers[st] = powers[st] + gain
    # CM3: soft mind growth (learn/read) feeds intellect power lightly
    mg = float(player.get("mind_growth") or 0)
    if mg > 0:
        powers["intelligence"] = powers["intelligence"] + min(12.0, mg * 0.55)
    # legacy crit points still count toward crit power if present
    crit_pts = int(alloc.get("crit", 0))
    if crit_pts:
        powers["crit"] += crit_pts * 1.1 * _latent_mult(player, reg, "crit")

    player["power_atk"] = powers["atk"]
    player["power_def"] = powers["defense"] + float(player.get("gear_def_bias") or 0.0)
    player["power_mag"] = powers["magic"]
    # DD1: magic defense — primarily from magic invest + small defense blend + gear mdef bias
    mag_pts = int(alloc.get("magic", 0))
    def_pts_pre = int(alloc.get("defense", 0))
    mdef_base = powers["magic"] * 0.85 + powers["defense"] * 0.25 + mag_pts * 0.4
    mdef_base += def_pts_pre * 0.15
    mdef_base += float(player.get("gear_mdef_bias") or 0.0)
    player["power_mdef"] = max(1.0, mdef_base)
    player["power_spd"] = powers["speed"] + float(player.get("gear_atb_bias") or 0.0) * 0.35
    player["power_intel"] = powers["intelligence"]
    # Attack investment secretly feeds crit (player asked: โจมตี → คริแฝง)
    atk_pts = int(alloc.get("atk", 0))
    powers["crit"] += atk_pts * 0.45 * _latent_mult(player, reg, "atk")
    player["power_crit"] = min(65.0, powers["crit"])

    # Feed into existing combat fields used by gear recompute
    player["alloc_atk_bonus"] = int(round(powers["atk"] - base_atk * 0.35))
    player["alloc_def_bonus"] = int(round(powers["defense"]))
    player["alloc_mag_bonus"] = int(round(powers["magic"]))
    player["alloc_spd_bonus"] = int(round(powers["speed"]))
    # Crit chance: base + from attack investment + crit power
    player["crit_chance"] = min(
        55.0, 5.0 + powers["crit"] * 1.05 + atk_pts * 0.35
    )
    # Dodge / soft mitigation from speed (never show exact %)
    spd_pts = int(alloc.get("speed", 0))
    player["dodge_chance"] = min(35.0, 3.0 + powers["speed"] * 0.55 + spd_pts * 0.4)
    # HP / MP growth rates (used on level-up)
    def_pts = int(alloc.get("defense", 0))
    mag_pts = int(alloc.get("magic", 0))
    player["hp_growth_bias"] = 1.0 + def_pts * 0.04 + powers["defense"] * 0.01
    player["mp_growth_bias"] = 1.0 + mag_pts * 0.04 + powers["magic"] * 0.012
    # Intelligence pool + special options (spendable current vs max)
    try:
        from game.domain.intelligence import ensure_intelligence

        ensure_intelligence(player, reg)
    except Exception:
        intel_pts = int(alloc.get("intelligence", 0))
        learn = int(player.get("learn_points") or 0)
        player["intel_options"] = (
            intel_pts + learn >= 3
            or powers["intelligence"] >= 8
            or "quiet_mind" in (player.get("blessing_flags") or [])
        )
    recompute_luck_score(player, reg)


def on_level_up_points(player: MutableMapping[str, Any], reg: DataRegistry, levels: int = 1) -> List[str]:
    ensure_progression(player, reg)
    occ = _occ(player, reg)
    per = int(occ.get("points_per_level", 3))
    gain = per * max(1, levels)
    # HP/MP grow with defense/magic investment bias (hidden)
    hp_b = float(player.get("hp_growth_bias") or 1.0)
    mp_b = float(player.get("mp_growth_bias") or 1.0)
    hp_gain = max(2, int(round(4 * levels * hp_b)))
    mp_gain = max(1, int(round(2 * levels * mp_b)))
    player["base_max_hp"] = int(player.get("base_max_hp", player.get("max_hp", 100))) + hp_gain
    player["base_max_mana"] = int(player.get("base_max_mana", player.get("max_mana", 50))) + mp_gain
    notes: List[str] = []
    # WO-052: after Lv30+ no manual P points — automatic growth
    try:
        from game.domain.auto_growth import (
            on_level_up_auto_growth,
            should_grant_stat_points,
            soft_threshold_flag,
        )

        if should_grant_stat_points(player):
            player["stat_points"] = int(player.get("stat_points", 0)) + gain
            notes.append(
                f"ได้แต้มสถานะ +{gain} (เหลือ {player['stat_points']} แต้ม — กด P เพื่อแจก)"
            )
            if soft_threshold_flag(player):
                notes.append(" …พลังเริ่มอั้น — ใกล้จังหวะที่แต้มจะไม่อยู่ในมือ")
        else:
            auto_notes = on_level_up_auto_growth(player, reg, levels)
            notes.extend(auto_notes)
            if not any("พัฒนา" in str(n) or "ไหล" in str(n) for n in auto_notes):
                notes.append(" พลังไหลเวียนเองตามเลเวล… (ไม่ได้อยู่ในมือเป็นแต้ม)")
    except Exception:
        player["stat_points"] = int(player.get("stat_points", 0)) + gain
        notes.append(
            f"ได้แต้มสถานะ +{gain} (เหลือ {player['stat_points']} แต้ม — กด P เพื่อแจก)"
        )
    notes.extend(try_occupation_rank_up(player, reg))
    notes.extend(try_unit_unlock(player, reg))
    # rare blessing roll (no formula shown)
    try:
        import random
        from game.domain.blessings import try_level_up_blessing

        notes.extend(
            try_level_up_blessing(
                player, reg, random.Random(int(player.get("latent_seed") or 1) + int(player.get("level") or 1)),
                levels=levels,
            )
        )
    except Exception:
        pass
    # soft notify class path may open (no spoilers)
    try:
        from game.domain.class_paths import soft_offer_hint

        hint = soft_offer_hint(player, reg)
        if hint:
            notes.append(hint)
            # sticky soft flag — field UI can nudge without spoiling how
            player.setdefault("flags", {})["class_offer_pending"] = True
    except Exception:
        pass
    try:
        from game.domain.soft_feel import soft_level_up_bundle

        notes.extend(soft_level_up_bundle(player, reg))
    except Exception:
        pass
    recompute_powers(player, reg)
    try:
        from game.domain.stat_arch import recompute_anima, ensure_stat_arch

        ensure_stat_arch(player)
        recompute_anima(player, reg)
    except Exception:
        pass
    return notes


def roll_starting_stat_points(
    player: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
) -> int:
    """
    Hidden starting pool — different per character.
    Factors: name, birth, seed. Range ~4–9. Never explain to player.
    """
    rng = rng or random.Random()
    seed = int(player.get("latent_seed") or 0)
    if not seed:
        raw = f"{player.get('name')}|{player.get('birth')}"
        seed = int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)
    birth = str(player.get("birth") or "1/1/2000")
    try:
        day = int(birth.split("/")[0])
        month = int(birth.split("/")[1])
    except Exception:
        day, month = 1, 1
    base = 5 + (seed % 5)  # 5–9
    # birth soft swing ±1
    swing = ((day + month) % 3) - 1
    total = base + swing
    # tiny roll
    if rng.random() < 0.15:
        total += 1
    if rng.random() < 0.12:
        total -= 1
    return max(4, min(9, int(total)))


def allocate_stat(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    stat: str,
    points: int = 1,
) -> str:
    ensure_progression(player, reg)
    # WO-052: manual P locked after auto growth
    try:
        from game.domain.auto_growth import (
            is_manual_p_locked,
            refuse_manual_allocate_message,
            activate_auto_growth_if_needed,
        )

        if is_manual_p_locked(player):
            activate_auto_growth_if_needed(player, reg)
            return refuse_manual_allocate_message(player)
    except Exception:
        pass
    if stat == "luck":
        return "ค่านี้… แจกตรงๆ ไม่ได้"
    if stat == "intelligence":
        # CM3: no free P dump into intellect — soft refusal
        return (
            "ความฉลาด… แจกตรงๆ ไม่ได้ "
            "· โตจากการเรียน/อ่าน/คิดในสนาม (รู้สึกเป็นแบนด์ ไม่ใช่แต้ม P)"
        )
    if stat not in ALLOCATE_KEYS and stat != "crit":
        return "สถานะไม่ถูกต้อง"
    if stat == "crit":
        # legacy: map to atk flavor
        stat = "atk"
    points = max(1, int(points))
    have = int(player.get("stat_points", 0))
    if have < points:
        return "แต้มไม่พอ"
    alloc = dict(player.get("stats_alloc") or {})
    alloc[stat] = int(alloc.get(stat, 0)) + points
    player["stats_alloc"] = alloc
    player["stat_points"] = have - points
    recompute_powers(player, reg)
    # re-run gear so bonus_atk includes new power
    try:
        from game.domain.equipment import recompute_stats

        recompute_stats(player, reg)
    except Exception:
        pass
    # WO-048: grade progress + soft feedback (no raw numbers)
    old_g = new_g = None
    try:
        from game.domain.stat_grades import apply_invest_to_grades, invest_feedback_message

        old_g, new_g, old_t, new_t = apply_invest_to_grades(player, stat, points)
        msg = invest_feedback_message(
            player,
            stat,
            old_letter=old_g,
            new_letter=new_g,
            points_left=int(player["stat_points"]),
            old_tier=old_t,
            new_tier=new_t,
        )
    except Exception:
        try:
            from game.domain.stat_arch import soft_facet_label, recompute_anima

            recompute_anima(player, reg)
            feel = soft_facet_label(min(100, int(alloc[stat]) * 12.0 + 10))
            msg = (
                f"「{STAT_LABELS[stat]}」รู้สึกหนาขึ้น · 〔{feel}〕 · "
                f"แต้มเหลือ {player['stat_points']} · (V=ประเมินตัวเอง)"
            )
        except Exception:
            msg = (
                f"เพิ่ม{STAT_LABELS[stat]} · เหลือแต้ม {player['stat_points']}"
            )
    try:
        from game.domain.stat_arch import recompute_anima

        recompute_anima(player, reg)
    except Exception:
        pass
    # soft path band if secret occupation active (stat+style HSR)
    if player.get("unit_class_id"):
        try:
            from game.domain.soft_feel import soft_unit_affinity_feel

            for line in soft_unit_affinity_feel(player, reg, force=False):
                msg += f"\n  {line}"
        except Exception:
            pass
    return msg


def _sync_rank_title(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    occ = _occ(player, reg)
    ranks = list(occ.get("ranks") or [])
    idx = int(player.get("occ_rank_index", 0))
    if ranks and 0 <= idx < len(ranks):
        player["occ_rank_title"] = ranks[idx].get("title", "")
    elif not player.get("occ_rank_title"):
        player["occ_rank_title"] = occ.get("name", "")


def _check_rank_conditions(player: Mapping[str, Any], rank: Mapping[str, Any]) -> bool:
    st = player.get("stats") or {}
    alloc = player.get("stats_alloc") or {}
    if int(player.get("level", 1)) < int(rank.get("min_level", 1)):
        return False
    if int(alloc.get("atk", 0)) < int(rank.get("min_stat_atk", 0)):
        return False
    if int(alloc.get("defense", 0)) < int(rank.get("min_stat_defense", 0)):
        return False
    if int(alloc.get("magic", 0)) < int(rank.get("min_stat_magic", 0)):
        return False
    if int(alloc.get("speed", 0)) < int(rank.get("min_stat_speed", 0)):
        return False
    if int(alloc.get("crit", 0)) < int(rank.get("min_stat_crit", 0)):
        return False
    if int(st.get("kills", 0)) < int(rank.get("min_kills", 0)):
        return False
    if int(st.get("boss_kills", 0)) < int(rank.get("min_boss_kills", 0)):
        return False
    if int(st.get("flees", 0)) < int(rank.get("min_flees", 0)):
        return False
    # combos tracked loosely via action attack as proxy if no combo stat
    combos = int(st.get("combos", 0)) or int((player.get("action_counts") or {}).get("attack", 0)) // 3
    if combos < int(rank.get("min_combos", 0)):
        return False
    lib = len(player.get("library_entries_read") or [])
    if lib < int(rank.get("library_entries", 0)):
        return False
    return True


def try_occupation_rank_up(player: MutableMapping[str, Any], reg: DataRegistry) -> List[str]:
    """Silent check — if conditions met, rank advances. No spoiler of requirements."""
    ensure_progression(player, reg)
    occ = _occ(player, reg)
    ranks = list(occ.get("ranks") or [])
    if not ranks:
        return []
    idx = int(player.get("occ_rank_index", 0))
    notes = []
    while idx + 1 < len(ranks):
        nxt = ranks[idx + 1]
        if not _check_rank_conditions(player, nxt):
            break
        idx += 1
        player["occ_rank_index"] = idx
        player["occ_rank_title"] = nxt.get("title", "")
        notes.append(f"✦ อาชีพก้าวหน้า: {nxt.get('title')} (เงื่อนไขบางอย่างครบโดยไม่รู้ตัว...)")
        sk = nxt.get("reward_skill")
        if sk and sk in reg.skills:
            skills = list(player.get("skills") or [])
            base = list(player.get("base_skills") or [])
            if sk not in skills:
                skills.append(sk)
                player["skills"] = skills
            if sk not in base:
                base.append(sk)
                player["base_skills"] = base
            notes.append(f"  ได้สกิลสายอาชีพ: {(reg.skills.get(sk) or {}).get('name', sk)}")
    return notes


def try_unit_unlock(player: MutableMapping[str, Any], reg: DataRegistry) -> List[str]:
    """At most one unit class; exclusive claim per world; mastery starts at 0."""
    from game.domain.unit_system import try_unit_unlock_with_claim

    return try_unit_unlock_with_claim(player, reg)


def library_can_access(player: Mapping[str, Any], reg: DataRegistry) -> Tuple[bool, str]:
    if player.get("library_unlocked"):
        return True, "เปิดอยู่"
    access = getattr(reg, "library_access", None) or {}
    groups = list(access.get("access_groups") or [])
    st = player.get("stats") or {}
    flags = player.get("flags") or {}
    reactions = len((player.get("knowledge") or {}).get("reactions") or [])
    quests = len(player.get("quests_done") or [])
    for g in groups:
        if g.get("require_flag") and not flags.get(g["require_flag"]):
            continue
        if int(player.get("level", 1)) < int(g.get("min_level", 0)):
            continue
        if reactions < int(g.get("min_reactions", 0)):
            continue
        if quests < int(g.get("min_quests_done", 0)):
            continue
        if int(st.get("boss_kills", 0)) < int(g.get("min_boss_kills", 0)):
            continue
        if int(st.get("kills", 0)) < int(g.get("min_kills", 0)):
            continue
        return True, "เงื่อนไขบางอย่างครบ — ประตูเปิด"
    return False, "ประตูปิดสนิท (คุณยังไม่รู้ว่าทำไม)"


def library_visit(player: MutableMapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_progression(player, reg)
    ok, why = library_can_access(player, reg)
    notes = []
    if not ok and not player.get("library_unlocked"):
        return [f"ห้องสมุด: {why}"]
    player["library_unlocked"] = True
    access = getattr(reg, "library_access", None) or {}
    cd = int(access.get("visit_cooldown", 8))
    last = int(player.get("library_last_visit", -999))
    now = int(player.get("time_units", 0))
    if now - last < cd and last >= 0:
        return [f"บรรณารักษ์โบกมือ: กลับมาใหม่ภายหลัง (คูลดาวน์ {cd - (now - last)} หน่วยเวลา)"]

    entries = list((getattr(reg, "library_entries", None) or {}).values())
    read = set(player.get("library_entries_read") or [])
    unread = [e for e in entries if e.get("id") not in read]
    if not unread:
        player["library_last_visit"] = now
        return ["คุณอ่านครบทุกเล่มที่มีในตอนนี้..."]

    n = int(access.get("entries_per_visit", 1))
    rng = random.Random(int(player.get("latent_seed", 1)) + now)
    rng.shuffle(unread)
    got = unread[:n]
    for e in got:
        read.add(e["id"])
        notes.append(f"📖 {e.get('title')}")
        body = str(e.get("body") or "").strip()
        for line in body.splitlines():
            if line.strip():
                notes.append(f"   {line.strip()}")
    player["library_entries_read"] = list(read)
    player["library_last_visit"] = now
    # CM4/5: soft mind growth from reading
    try:
        from game.domain.combo_mind import note_mind_growth

        mnote = note_mind_growth(player, 0.55, reason="library")
        if mnote:
            notes.append(mnote)
    except Exception:
        pass
    # WO-037: Anima soft moment after reading
    try:
        from game.domain.stat_arch import anima_presence_lines, recompute_anima

        recompute_anima(player, reg)
        notes.extend(anima_presence_lines(player, "library", reg=reg))
    except Exception:
        pass
    # personality fragment tips (partial / rumor / rare complete) — separate pool
    try:
        from game.domain.personality import (
            apply_event as personality_event,
            roll_personality_library_tip,
        )

        notes.extend(personality_event(player, "library_visit", reg))
        tip_notes = roll_personality_library_tip(player, reg)
        if tip_notes:
            notes.append("── ชั้นหนังสือนิสัย (เศษข้อมูล) ──")
            notes.extend(tip_notes)
    except Exception:
        pass
    # rank/unit may unlock after knowledge
    notes.extend(try_occupation_rank_up(player, reg))
    notes.extend(try_unit_unlock(player, reg))
    return notes


def grant_library_key(player: MutableMapping[str, Any]) -> str:
    flags = dict(player.get("flags") or {})
    flags["library_key_item"] = True
    player["flags"] = flags
    player["library_unlocked"] = True
    return "ได้กุญแจความรู้แปลกปลอม — ห้องสมุดอาจเปิดรับคุณ"


def format_alloc_panel(player: Mapping[str, Any]) -> List[str]:
    """
    Stat invest overview — WO-035 soft shell (no raw ×N / power dump).
    luck never listed; crit legacy not shown in menu.
    WO-052: after Lv30+ show auto-growth panel instead.
    """
    try:
        from game.domain.auto_growth import format_p_menu_or_auto, is_manual_p_locked

        if is_manual_p_locked(player):
            return format_p_menu_or_auto(player)
    except Exception:
        pass
    try:
        from game.domain.stat_arch import SOFT_INVEST_UI, format_soft_invest_lines

        if SOFT_INVEST_UI:
            return format_soft_invest_lines(player)
    except Exception:
        pass
    # fallback legacy if soft module missing
    alloc = player.get("stats_alloc") or {}
    pts = int(player.get("stat_points") or 0)
    lines: List[str] = [
        " แจกแต้มสถานะ",
        "---",
        f" แต้มคงเหลือ  {pts}",
    ]
    for i, k in enumerate(ALLOCATE_KEYS, 1):
        n = int(alloc.get(k, 0))
        filled = min(8, n)
        dots = "█" * filled + "░" * (8 - filled)
        lines.append(f"  {i}. {STAT_LABELS[k]:<8}  [{dots}]")
    return lines


def format_alloc_menu_lines(player: Mapping[str, Any]) -> List[str]:
    """Numbered invest choices only (used under the overview box)."""
    try:
        from game.domain.stat_arch import SOFT_INVEST_UI, format_soft_invest_menu_lines

        if SOFT_INVEST_UI:
            return format_soft_invest_menu_lines(player)
    except Exception:
        pass
    nkeys = len(ALLOCATE_KEYS)
    lines: List[str] = [
        " ลงทุนที่",
        "---",
    ]
    for i, k in enumerate(ALLOCATE_KEYS, 1):
        lines.append(f"  {i}  {STAT_LABELS[k]:<8}")
    lines.append("---")
    lines.append("  0  กลับ")
    lines.append(f" พิมพ์ 1–{nkeys} แล้วใส่จำนวนแต้ม")
    return lines
