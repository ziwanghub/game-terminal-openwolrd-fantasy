"""
Skill Rank runtime (SK-R0–R2).

- Ranks: N H R S SS SSS (soft labels; no % in UI)
- Scales power / heal / mana / status chance on a *copy* of skill dict
- First-learn roll; early high-rank tax (MP / charge)
- Hidden mastery xp for later upgrade (SK-R3 hooks)
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry

_RANKS_DEFAULT = ["N", "H", "R", "S", "SS", "SSS"]
_SOFT_DEFAULT = {
    "N": "ธรรมดา",
    "H": "สูง",
    "R": "หายาก",
    "S": "S",
    "SS": "SS",
    "SSS": "SSS",
}
_FEEL_DEFAULT = {
    "N": "รู้สึกพอใช้",
    "H": "รู้สึกคมขึ้น",
    "R": "น้ำหนักผิดปกติ",
    "S": "ดุชัด",
    "SS": "น่ากลัว",
    "SSS": "เกือบควบคุมไม่อยู่",
}

_rules_cache: Optional[Dict[str, Any]] = None


def load_rank_rules(reg: Optional[DataRegistry] = None) -> Dict[str, Any]:
    global _rules_cache
    if _rules_cache is not None:
        return _rules_cache
    path = DATA_DIR / "skills" / "rank_rules.yaml"
    raw: Dict[str, Any] = {}
    if path.is_file():
        try:
            from game.data_load.loader import load_file

            data = load_file(path)
            if isinstance(data, dict):
                raw = data
        except Exception:
            raw = {}
    if reg is not None and getattr(reg, "skill_rank_rules", None):
        raw = dict(reg.skill_rank_rules)  # type: ignore[attr-defined]
    _rules_cache = raw or {
        "ranks": list(_RANKS_DEFAULT),
        "soft_label": dict(_SOFT_DEFAULT),
        "soft_feel": dict(_FEEL_DEFAULT),
        "power_mult": [1.0, 1.08, 1.18, 1.32, 1.5, 1.72],
        "heal_mult": [1.0, 1.06, 1.14, 1.24, 1.38, 1.55],
        "mana_mult": [1.0, 1.1, 1.25, 1.48, 1.85, 2.4],
        "status_chance_mult": [1.0, 1.05, 1.12, 1.22, 1.35, 1.48],
        "learn_roll_weights": {
            "N": 52,
            "H": 28,
            "R": 14,
            "S": 5,
            "SS": 0.9,
            "SSS": 0.1,
        },
        "early_high_rank_tax": {
            "max_level": 6,
            "ranks": ["SS", "SSS"],
            "mana_mult_extra": 1.35,
            "force_charge_max": 3,
        },
    }
    return _rules_cache


def clear_rank_rules_cache() -> None:
    global _rules_cache
    _rules_cache = None


def rank_order(reg: Optional[DataRegistry] = None) -> List[str]:
    rules = load_rank_rules(reg)
    ranks = [str(x).upper() for x in (rules.get("ranks") or _RANKS_DEFAULT)]
    return ranks or list(_RANKS_DEFAULT)


def normalize_rank(rank: Any, reg: Optional[DataRegistry] = None) -> str:
    r = str(rank or "N").upper().strip()
    # aliases
    aliases = {
        "NORMAL": "N",
        "COMMON": "N",
        "HIGH": "H",
        "RARE": "R",
        "F": "N",
        "E": "N",
        "D": "H",
        "C": "H",
        "B": "R",
        "A": "S",
    }
    r = aliases.get(r, r)
    order = rank_order(reg)
    if r not in order:
        return order[0] if order else "N"
    return r


def rank_index(rank: Any, reg: Optional[DataRegistry] = None) -> int:
    order = rank_order(reg)
    r = normalize_rank(rank, reg)
    try:
        return order.index(r)
    except ValueError:
        return 0


def soft_rank_label(rank: Any, reg: Optional[DataRegistry] = None) -> str:
    rules = load_rank_rules(reg)
    r = normalize_rank(rank, reg)
    labels = dict(rules.get("soft_label") or _SOFT_DEFAULT)
    return str(labels.get(r) or r)


def soft_rank_feel(rank: Any, reg: Optional[DataRegistry] = None) -> str:
    rules = load_rank_rules(reg)
    r = normalize_rank(rank, reg)
    feels = dict(rules.get("soft_feel") or _FEEL_DEFAULT)
    return str(feels.get(r) or "")


def ensure_skill_ranks(player: MutableMapping[str, Any]) -> Dict[str, str]:
    ranks = dict(player.get("skill_ranks") or {})
    # normalize keys
    out: Dict[str, str] = {}
    for k, v in ranks.items():
        out[str(k)] = normalize_rank(v)
    player["skill_ranks"] = out
    player.setdefault("skill_rank_xp", {})
    return out


def get_skill_rank(
    player: Mapping[str, Any],
    skill_id: str,
    reg: Optional[DataRegistry] = None,
    skill: Optional[Mapping[str, Any]] = None,
) -> str:
    ensure_skill_ranks(player)  # type: ignore[arg-type]
    ranks = player.get("skill_ranks") or {}
    if skill_id in ranks:
        return normalize_rank(ranks[skill_id], reg)
    sk = skill or {}
    if reg is not None and not sk:
        sk = reg.skills.get(skill_id) or {}
    default = sk.get("rank_default") or "N"
    return normalize_rank(default, reg)


def set_skill_rank(
    player: MutableMapping[str, Any],
    skill_id: str,
    rank: Any,
    reg: Optional[DataRegistry] = None,
) -> str:
    ensure_skill_ranks(player)
    r = normalize_rank(rank, reg)
    # respect cap from skill def if available
    if reg is not None:
        sk = reg.skills.get(skill_id) or {}
        cap = sk.get("rank_cap")
        if cap is not None:
            order = rank_order(reg)
            ci = rank_index(cap, reg)
            ri = rank_index(r, reg)
            if ri > ci:
                r = order[ci] if ci < len(order) else r
    player["skill_ranks"][str(skill_id)] = r
    return r


def _table_mult(rules: Mapping[str, Any], key: str, idx: int, default: float = 1.0) -> float:
    table = list(rules.get(key) or [])
    if not table:
        return default
    if idx < 0:
        idx = 0
    if idx >= len(table):
        idx = len(table) - 1
    try:
        return float(table[idx])
    except Exception:
        return default


def scale_skill_for_player(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
    *,
    skill_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return a *copy* of skill with power/heal/mana/status chance scaled by rank.
    Does not mutate registry.
    """
    sk = dict(skill)
    sid = str(skill_id or sk.get("id") or "")
    rank = get_skill_rank(player, sid, reg, skill=sk) if sid else normalize_rank(sk.get("rank_default") or "N", reg)
    rules = load_rank_rules(reg)
    idx = rank_index(rank, reg)
    p_m = _table_mult(rules, "power_mult", idx)
    h_m = _table_mult(rules, "heal_mult", idx)
    mana_m = _table_mult(rules, "mana_mult", idx)
    st_m = _table_mult(rules, "status_chance_mult", idx)
    ref_m = _table_mult(rules, "reflect_mult", idx, 1.0)
    ctr_m = _table_mult(rules, "counter_mult", idx, 1.0)

    # early high-rank tax
    tax = dict(rules.get("early_high_rank_tax") or {})
    tax_ranks = {normalize_rank(x, reg) for x in (tax.get("ranks") or [])}
    plv = int(player.get("level") or 1)
    if rank in tax_ranks and plv <= int(tax.get("max_level") or 6):
        mana_m *= float(tax.get("mana_mult_extra") or 1.35)

    if sk.get("power") is not None:
        sk["power"] = max(0, int(round(int(sk["power"]) * p_m)))
    if sk.get("heal") is not None:
        sk["heal"] = max(0, int(round(int(sk["heal"]) * h_m)))
    if sk.get("cost_mana") is not None:
        sk["cost_mana"] = max(0, int(round(int(sk["cost_mana"]) * mana_m)))
    if sk.get("counter_power") is not None:
        sk["counter_power"] = max(0, int(round(int(sk["counter_power"]) * ctr_m)))
    if sk.get("reflect_pct") is not None:
        sk["reflect_pct"] = min(0.55, float(sk["reflect_pct"]) * ref_m)

    # apply_status chance scale
    aps = sk.get("apply_status")
    if isinstance(aps, dict) and aps.get("chance") is not None:
        aps = dict(aps)
        aps["chance"] = min(0.85, float(aps["chance"]) * st_m)
        sk["apply_status"] = aps
    if sk.get("status_chance") is not None:
        sk["status_chance"] = min(0.85, float(sk["status_chance"]) * st_m)

    sk["_skill_rank"] = rank
    sk["_rank_label"] = soft_rank_label(rank, reg)
    sk["_rank_feel"] = soft_rank_feel(rank, reg)
    sk["id"] = sid or sk.get("id")
    return sk


def roll_learn_rank(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
    rng: random.Random,
    reg: Optional[DataRegistry] = None,
) -> str:
    """Weighted roll for first-learn rank; respects rank_cap / rank_default floor lightly."""
    rules = load_rank_rules(reg)
    weights = dict(rules.get("learn_roll_weights") or {})
    order = rank_order(reg)
    cap = normalize_rank(skill.get("rank_cap") or order[-1], reg)
    cap_i = rank_index(cap, reg)
    # default floor: at least rank_default sometimes biased
    floor = normalize_rank(skill.get("rank_default") or "N", reg)
    floor_i = rank_index(floor, reg)

    pairs: List[Tuple[str, float]] = []
    for i, r in enumerate(order):
        if i > cap_i:
            continue
        w = float(weights.get(r) or 0)
        if i < floor_i:
            w *= 0.35  # still possible below default, rarer
        if w <= 0:
            continue
        pairs.append((r, w))
    if not pairs:
        return floor
    total = sum(w for _, w in pairs)
    roll = rng.random() * total
    acc = 0.0
    chosen = pairs[-1][0]
    for r, w in pairs:
        acc += w
        if roll <= acc:
            chosen = r
            break
    return chosen


def apply_learn_rank(
    player: MutableMapping[str, Any],
    skill_id: str,
    skill: Mapping[str, Any],
    rng: random.Random,
    reg: Optional[DataRegistry] = None,
) -> Tuple[str, List[str]]:
    """
    Set rank on learn. Returns (rank, soft_notes).
    Early SS/SSS may force charge lease tax.
    """
    rank = roll_learn_rank(player, skill, rng, reg)
    set_skill_rank(player, skill_id, rank, reg)
    notes: List[str] = []
    feel = soft_rank_feel(rank, reg)
    label = soft_rank_label(rank, reg)
    if feel:
        notes.append(f"ท่านี้… {feel} ({label})")
    rules = load_rank_rules(reg)
    tax = dict(rules.get("early_high_rank_tax") or {})
    tax_ranks = {normalize_rank(x, reg) for x in (tax.get("ranks") or [])}
    plv = int(player.get("level") or 1)
    if rank in tax_ranks and plv <= int(tax.get("max_level") or 6):
        notes.append("พลังหนักมือ — ร่ายแพง/จำกัดครั้ง (รู้สึก)")
        # force limited uses if not already leased
        try:
            from game.domain.skill_charges import charge_info, set_lease

            if charge_info(player, skill_id) is None:
                uses = int(tax.get("force_charge_max") or 3)
                set_lease(player, skill_id, uses, source="rank_tax")
                notes.append(f"ใช้ได้จำกัด ~{uses} ครั้งจนกว่าจะเติมพลัง/เติบโต")
        except Exception:
            pass
    return rank, notes


def note_skill_use_mastery(
    player: MutableMapping[str, Any],
    skill_id: str,
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
) -> Optional[str]:
    """
    SK-R3 lite: hidden xp; rare soft try-upgrade message (no guaranteed up).
    """
    if not skill_id:
        return None
    ensure_skill_ranks(player)
    xp_map = dict(player.get("skill_rank_xp") or {})
    xp_map[skill_id] = int(xp_map.get(skill_id) or 0) + 1
    player["skill_rank_xp"] = xp_map
    rules = load_rank_rules(reg)
    need = int(rules.get("mastery_to_try_upgrade") or 18)
    if xp_map[skill_id] < need or xp_map[skill_id] % need != 0:
        return None
    rng = rng or random.Random()
    chance = float(rules.get("upgrade_base_chance") or 0.22)
    if rng.random() >= chance:
        return "ท่านี้คุ้นมือขึ้น… แต่ยังไม่เปลี่ยนโทน"
    # upgrade one step
    order = rank_order(reg)
    cur = get_skill_rank(player, skill_id, reg)
    ci = rank_index(cur, reg)
    if ci >= len(order) - 1:
        return "ท่านี้ถึงขีดที่รู้สึกได้แล้ว"
    # cap
    sk = (reg.skills.get(skill_id) if reg else None) or {}
    cap_i = rank_index(sk.get("rank_cap") or order[-1], reg) if sk else len(order) - 1
    if ci >= cap_i:
        return None
    new_r = order[ci + 1]
    set_skill_rank(player, skill_id, new_r, reg)
    return f"ท่านี้… เปลี่ยนโทน — {soft_rank_feel(new_r, reg)} ({soft_rank_label(new_r, reg)})"


def format_skill_rank_hint(
    player: Mapping[str, Any],
    skill_id: str,
    reg: Optional[DataRegistry] = None,
) -> str:
    """Short soft line for menus — no formulas."""
    r = get_skill_rank(player, skill_id, reg)
    feel = soft_rank_feel(r, reg)
    lab = soft_rank_label(r, reg)
    if feel:
        return f"{lab} · {feel}"
    return lab


def try_rank_nudge_item(
    player: MutableMapping[str, Any],
    skill_id: str,
    reg: DataRegistry,
    rng: random.Random,
    *,
    bonus: float = 0.0,
) -> Tuple[bool, str]:
    """
    SK-R5 lite: consumable essence attempts soft rank-up (hidden chance).
    Never shows %. Returns (consumed_ok_effect, message).
    """
    ensure_skill_ranks(player)
    if skill_id not in (player.get("skills") or []):
        return False, "ยังไม่มีท่านี้ในตัว — กระซิบไม่เกาะ"
    sk = reg.skills.get(skill_id) or {}
    if not sk:
        return False, "ไม่รู้จักท่านั้น"
    order = rank_order(reg)
    cur = get_skill_rank(player, skill_id, reg)
    ci = rank_index(cur, reg)
    cap_i = rank_index(sk.get("rank_cap") or order[-1], reg)
    if ci >= cap_i or ci >= len(order) - 1:
        return True, "ท่านี้ถึงขีดที่รู้สึกได้แล้ว — แก่นสลายเป็นไอ"
    rules = load_rank_rules(reg)
    chance = float(rules.get("upgrade_base_chance") or 0.22) + 0.12 + float(bonus)
    chance = min(0.72, max(0.08, chance))
    if rng.random() >= chance:
        # still burn item; small mastery
        xp_map = dict(player.get("skill_rank_xp") or {})
        xp_map[skill_id] = int(xp_map.get(skill_id) or 0) + 3
        player["skill_rank_xp"] = xp_map
        return True, "กระซิบผ่านไป… ท่าไม่เปลี่ยนโทน (คุ้นมือขึ้นนิด)"
    new_r = order[ci + 1]
    set_skill_rank(player, skill_id, new_r, reg)
    return (
        True,
        f"ท่า「{sk.get('name') or skill_id}」… เปลี่ยนโทน — "
        f"{soft_rank_feel(new_r, reg)} ({soft_rank_label(new_r, reg)})",
    )
