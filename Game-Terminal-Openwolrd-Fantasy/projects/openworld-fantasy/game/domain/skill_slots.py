"""
Skill slot taxonomy (SK-R1).

Slots: combat | debuff | buff | defense | support
Defense modes: guard | reflect | counter
Buff anti-stack: 1 buff cast per player action + category exclusive
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry

SLOTS = ("combat", "debuff", "buff", "defense", "support")
DEFENSE_MODES = ("guard", "reflect", "counter")
BUFF_CATEGORIES = ("atk", "def", "tempo", "resource", "generic")


def normalize_slot(skill: Mapping[str, Any]) -> str:
    raw = str(skill.get("slot") or "combat").lower().strip()
    # legacy aliases
    if raw in ("attack", "dmg", "damage"):
        return "combat"
    if raw in ("ailment", "status", "curse"):
        return "debuff"
    if raw in ("guard", "block", "shield"):
        return "defense"
    if raw in ("heal", "utility", "cleanse"):
        return "support"
    if raw in ("self_buff", "enhance"):
        return "buff"
    if raw not in SLOTS:
        # infer
        if skill.get("heal") and not skill.get("power"):
            return "support"
        if skill.get("buff_status") or skill.get("buff_category"):
            return "buff"
        if skill.get("apply_status") and not skill.get("power"):
            return "debuff"
        if skill.get("strong_vs") is not None or skill.get("guard_class"):
            return "defense"
        return "combat"
    return raw


def defense_mode(skill: Mapping[str, Any]) -> str:
    mode = str(skill.get("defense_mode") or "").lower().strip()
    if mode in DEFENSE_MODES:
        return mode
    if skill.get("reflect_pct"):
        return "reflect"
    if skill.get("counter_power") or skill.get("counter"):
        return "counter"
    return "guard"


def buff_category(skill: Mapping[str, Any]) -> str:
    cat = str(skill.get("buff_category") or "").lower().strip()
    if cat in BUFF_CATEGORIES:
        return cat
    # infer from buff_status id
    st = str(skill.get("buff_status") or skill.get("status") or "").lower()
    if st in ("might", "berserk", "power"):
        return "atk"
    if st in ("ward", "aegis", "shell"):
        return "def"
    if st in ("focus", "haste", "swift"):
        return "tempo"
    if st in ("regen", "mana_font", "focus_mana"):
        return "resource"
    return "generic"


def is_offensive_slot(slot: str) -> bool:
    return slot in ("combat", "debuff")


def is_combo_eligible(skill: Mapping[str, Any]) -> bool:
    """Buffs/defense never enter damage combo chains; support heal only solo."""
    slot = normalize_slot(skill)
    if slot in ("buff", "defense"):
        return False
    if slot == "support" and skill.get("heal"):
        return bool(skill.get("combo_ok"))
    if skill.get("combo_ok") is False:
        return False
    return slot in ("combat", "debuff")


def begin_player_action(player: MutableMapping[str, Any]) -> None:
    """Call at start of a player combat action (fresh budget)."""
    player["_buff_casts_this_action"] = 0
    player["_skills_used_this_action"] = []


def can_cast_buff(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
) -> Tuple[bool, str]:
    """
    Anti multi-buff:
    - max 1 buff skill per action
    - category exclusive vs active statuses (soft)
    """
    if normalize_slot(skill) != "buff":
        return True, ""
    used = int(player.get("_buff_casts_this_action") or 0)
    if used >= 1:
        return False, "รอบนี้ตั้งท่าเสริมไปแล้ว — บัฟซ้อนไม่ไหว"
    cat = buff_category(skill)
    # exclusive: if already have a buff status in same category, block soft
    want = str(skill.get("buff_status") or "")
    active = player.get("statuses") or []
    for s in active:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "")
        # map known buffs to categories
        existing_cat = {
            "might": "atk",
            "ward": "def",
            "focus": "tempo",
            "regen": "resource",
        }.get(sid, "")
        if existing_cat and existing_cat == cat and want and sid != want:
            return False, "สถานะแนวเดียวกันยังเกาะอยู่ — ต้องเลือกว่าจะทับหรือรอ"
        if want and sid == want:
            # refresh allowed
            return True, ""
    return True, ""


def mark_buff_cast(player: MutableMapping[str, Any]) -> None:
    player["_buff_casts_this_action"] = int(player.get("_buff_casts_this_action") or 0) + 1


def resolve_skill_for_use(
    player: Mapping[str, Any],
    skill_id: str,
    reg: DataRegistry,
) -> Optional[Dict[str, Any]]:
    """Load skill + apply rank scale."""
    base = reg.skills.get(skill_id)
    if not base:
        return None
    from game.domain.skill_rank import scale_skill_for_player

    sk = scale_skill_for_player(player, base, reg, skill_id=skill_id)
    sk["slot"] = normalize_slot(sk)
    if sk["slot"] == "defense":
        sk["defense_mode"] = defense_mode(sk)
    if sk["slot"] == "buff":
        sk["buff_category"] = buff_category(sk)
    return sk


def apply_buff_skill(
    player: MutableMapping[str, Any],
    skill: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> List[str]:
    """Apply self buff status. Caller checked can_cast_buff."""
    from game.domain.status_fx import apply_status, status_display_name

    notes: List[str] = []
    st = skill.get("buff_status") or skill.get("status")
    if not st:
        # soft fallback might
        st = "might" if buff_category(skill) == "atk" else "ward"
    chance = float(skill.get("buff_chance") or 1.0)
    applied = apply_status(player, str(st), reg, rng, chance=chance, source="skill_buff")
    mark_buff_cast(player)
    if applied:
        nm = status_display_name(reg, applied)
        notes.append(f"สถานะ「{nm}」เกาะตัว — {skill.get('name') or 'บัฟ'}")
    else:
        notes.append("ตั้งท่าแล้ว แต่ความรู้สึกยังไม่นิ่ง…")
    return notes


def apply_debuff_from_skill(
    monster: MutableMapping[str, Any],
    skill: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    aoe: bool = False,
) -> List[str]:
    """Apply at most one status from skill apply_status / status fields."""
    from game.domain.status_fx import apply_status, status_display_name

    notes: List[str] = []
    aps = skill.get("apply_status")
    sid = None
    chance = 0.35
    if isinstance(aps, dict):
        sid = aps.get("id") or aps.get("status")
        chance = float(aps.get("chance") or 0.35)
    elif skill.get("status"):
        sid = skill.get("status")
        chance = float(skill.get("status_chance") or 0.35)
    if not sid:
        return notes
    applied = apply_status(
        monster,
        str(sid),
        reg,
        rng,
        chance=chance,
        source="skill_debuff",
        aoe=aoe,
    )
    if applied:
        nm = status_display_name(reg, applied)
        notes.append(f"ติด「{nm}」บนศัตรู!")
    return notes


def arm_defense_stance(
    player: MutableMapping[str, Any],
    skill: Mapping[str, Any],
) -> List[str]:
    """
    Prepare reflect / counter / guard for incoming hits this round.
    Stored on player for apply_defense path.
    """
    mode = defense_mode(skill)
    notes: List[str] = []
    stance = {
        "mode": mode,
        "skill_id": skill.get("id"),
        "name": skill.get("name"),
        "reflect_pct": float(skill.get("reflect_pct") or 0),
        "counter_power": int(skill.get("counter_power") or 0),
        "charges": 1,
    }
    # also keep full skill ref keys for guard_groups compatibility
    if mode == "guard":
        notes.append(f"ตั้งท่าป้องกัน「{skill.get('name')}」")
    elif mode == "reflect":
        notes.append(f"ตั้งท่าสะท้อน「{skill.get('name')}」— คมรอผู้บุกรุก")
        if stance["reflect_pct"] <= 0:
            stance["reflect_pct"] = 0.12
    elif mode == "counter":
        notes.append(f"ตั้งท่าสวนกลับ「{skill.get('name')}」")
        if stance["counter_power"] <= 0:
            stance["counter_power"] = max(6, int(skill.get("power") or 10))
    player["defense_stance"] = stance
    return notes


def consume_defense_stance_on_hit(
    player: MutableMapping[str, Any],
    monster: MutableMapping[str, Any],
    incoming_final: int,
    rng: random.Random,
) -> Tuple[int, List[str]]:
    """
    After player takes damage: apply reflect damage to mon and/or counter.
    Returns (extra_damage_to_monster, notes).
    """
    stance = dict(player.get("defense_stance") or {})
    if not stance or int(stance.get("charges") or 0) <= 0:
        return 0, []
    notes: List[str] = []
    extra = 0
    mode = str(stance.get("mode") or "guard")
    if mode == "reflect" and incoming_final > 0:
        pct = min(0.45, float(stance.get("reflect_pct") or 0.12))
        back = max(1, int(round(incoming_final * pct)))
        # no status on reflect — pure HP
        monster["hp"] = int(monster.get("hp") or 0) - back
        extra += back
        notes.append(f"สะท้อนกลับ ~{back}!")
    if mode == "counter" and incoming_final > 0:
        cpow = int(stance.get("counter_power") or 8)
        cpow = max(1, cpow + rng.randint(-2, 3))
        monster["hp"] = int(monster.get("hp") or 0) - cpow
        extra += cpow
        notes.append(f"สวนกลับ! (~{cpow})")
    stance["charges"] = int(stance.get("charges") or 1) - 1
    if stance["charges"] <= 0:
        player.pop("defense_stance", None)
    else:
        player["defense_stance"] = stance
    return extra, notes
