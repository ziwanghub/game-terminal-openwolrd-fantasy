"""
WO-PARTY-7 — Smart Companion Assist Priority (Soft Decision Engine).

Pick action by situation priority (P0–P2), then soft success rolls.
Does NOT control party manually · max 3 members · O(1) per member.
Auto Play uses the same decide() via party_member_turns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# Actions
ACT_HEAL = "heal"
ACT_CLEANSE = "cleanse"
ACT_ATTACK = "attack"
ACT_BUFF = "buff"
ACT_WAIT = "wait"

# Priority bands
P0 = 0  # player crisis
P1 = 1  # mon pressure
P2 = 2  # general

# Role tags (from template.role or inferred from kind)
ROLE_SUPPORT = "support"  # cleanse + heal lean (ภูตใบไม้ / spirit support)
ROLE_ATTACK = "attack"  # damage lean
ROLE_BALANCED = "balanced"

_SUPPORT_KINDS = frozenset({"spirit", "heaven_god", "heaven_beast"})
_ATTACK_KINDS = frozenset({"beast", "hell_beast", "hell_god", "player"})

# Thresholds (soft, hidden)
HP_CRIT = 0.28
HP_LOW = 0.42
MORALE_CRIT = 28
MON_LOW = 0.22
MON_PRESSURE = 0.35


@dataclass
class Decision:
    action: str
    priority: int
    reason: str = ""
    cleanse_target: str = ""  # status id e.g. poison
    meta: Dict[str, Any] = field(default_factory=dict)


def member_role(member: Mapping[str, Any], reg: Optional[Any] = None) -> str:
    """Resolve role tag: template.role > kind lean."""
    raw = str(member.get("role") or member.get("assist_role") or "").lower().strip()
    if raw in ("support", "support_nature", "healer", "cleanse"):
        return ROLE_SUPPORT
    if raw in ("attack", "dps", "striker", "shadow"):
        return ROLE_ATTACK
    # template lookup
    tid = str(member.get("template_id") or member.get("id") or "")
    if reg is not None and tid:
        try:
            from game.domain.party import template_by_id

            tpl = template_by_id(reg, tid) or {}
            tr = str(tpl.get("role") or tpl.get("assist_role") or "").lower()
            if tr in ("support", "support_nature", "healer"):
                return ROLE_SUPPORT
            if tr in ("attack", "dps", "striker"):
                return ROLE_ATTACK
            # id/name soft: leaf / tree nature
            if "leaf" in tid or "tree" in tid or "nature" in tid:
                return ROLE_SUPPORT
        except Exception:
            pass
    kind = str(member.get("kind") or "other")
    if kind in _SUPPORT_KINDS:
        return ROLE_SUPPORT
    if kind in _ATTACK_KINDS:
        return ROLE_ATTACK
    return ROLE_BALANCED


def _player_hp_ratio(player: Mapping[str, Any]) -> float:
    return int(player.get("hp") or 0) / max(1, int(player.get("max_hp") or 1))


def _mon_hp_ratio(mon: Mapping[str, Any]) -> float:
    return int(mon.get("hp") or 0) / max(1, int(mon.get("max_hp") or mon.get("hp") or 1))


def _morale(player: Mapping[str, Any]) -> int:
    try:
        from game.domain.needs import get_needs

        return int(get_needs(player).get("morale") or 50)
    except Exception:
        n = player.get("needs") or {}
        return int(n.get("morale") or 50)


def _debuff_ids(player: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for s in player.get("statuses") or []:
        if not isinstance(s, dict):
            continue
        kind = str(s.get("kind") or "debuff")
        if kind != "debuff":
            continue
        sid = str(s.get("id") or "")
        if sid:
            out.append(sid)
    return out


def _strong_ailments(player: Mapping[str, Any]) -> List[str]:
    """Poison and other soft-priority cleanses."""
    strong = {"poison", "burn", "bleed", "curse", "doom", "plague"}
    found = []
    for sid in _debuff_ids(player):
        if sid.lower() in strong or "poison" in sid.lower():
            found.append(sid)
    return found


def success_chance(
    player: Mapping[str, Any],
    member: Mapping[str, Any],
    *,
    action: str,
    bond: int,
    reg: Optional[Any] = None,
) -> float:
    """
    Soft success for cleanse / support (and light fail for others).
    f(Rank/grade, Bond, Anima) — no raw % shown to player.
    """
    b = max(0, min(100, int(bond)))
    base = 0.42 + (b / 100.0) * 0.38  # ~0.42–0.80 from bond

    # player grade (Rank)
    try:
        if player.get("grade_revealed"):
            g = str(player.get("player_grade") or "C").upper()
            g_m = {
                "F": -0.08,
                "E": -0.05,
                "D": -0.02,
                "C": 0.0,
                "B": 0.03,
                "A": 0.05,
                "S": 0.07,
                "SS": 0.08,
                "SSS": 0.09,
            }.get(g, 0.0)
            base += g_m
    except Exception:
        pass

    # anima soft
    try:
        from game.domain.stat_arch import anima_value

        a = float(anima_value(player))
        if a >= 70:
            base += 0.05
        elif a >= 55:
            base += 0.02
        elif a < 35:
            base -= 0.04
    except Exception:
        pass

    # companion rarity soft
    rar = str(member.get("rarity") or "common").lower()
    rar_b = {
        "common": 0.0,
        "uncommon": 0.02,
        "rare": 0.03,
        "sacred": 0.04,
        "legendary": 0.05,
        "divine": 0.06,
        "archdivine": 0.07,
        "mythic": 0.08,
    }.get(rar, 0.0)
    base += rar_b

    role = member_role(member, reg)
    if action == ACT_CLEANSE and role == ROLE_SUPPORT:
        base += 0.10
    if action == ACT_HEAL and role == ROLE_SUPPORT:
        base += 0.06
    if action == ACT_ATTACK and role == ROLE_ATTACK:
        base += 0.04

    # cleanse harder than heal
    if action == ACT_CLEANSE:
        base -= 0.05
    if action in (ACT_ATTACK, ACT_BUFF, ACT_HEAL):
        # attack/heal usually "succeed" — high floor
        if action != ACT_CLEANSE:
            base = max(base, 0.72)

    return max(0.18, min(0.92, base))


def decide(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    member: Mapping[str, Any],
    *,
    bond: int,
    reg: Optional[Any] = None,
    team_cleansed_this_round: bool = False,
) -> Decision:
    """
    Priority pick for one companion (after assist_chance already passed).
    """
    role = member_role(member, reg)
    hp_r = _player_hp_ratio(player)
    mon_r = _mon_hp_ratio(mon)
    morale = _morale(player)
    ailments = _strong_ailments(player)
    mon_threat = bool(mon.get("elite") or mon.get("boss"))

    # ── P0: player crisis ─────────────────────────────────────────
    # Strong poison / ailment first for support (or any if severe)
    if ailments and not team_cleansed_this_round:
        want_cleanse = role == ROLE_SUPPORT or hp_r < HP_LOW or len(ailments) >= 1
        if want_cleanse and (role == ROLE_SUPPORT or hp_r < HP_CRIT or morale <= MORALE_CRIT):
            return Decision(
                ACT_CLEANSE,
                P0,
                reason="p0_ailment",
                cleanse_target=ailments[0],
                meta={"role": role, "ailments": list(ailments)},
            )
        if role == ROLE_SUPPORT and ailments:
            return Decision(
                ACT_CLEANSE,
                P0,
                reason="p0_support_cleanse",
                cleanse_target=ailments[0],
                meta={"role": role},
            )

    if hp_r < HP_CRIT:
        if role == ROLE_ATTACK and mon_threat and mon_r <= MON_LOW and hp_r >= 0.15:
            # attack lean may finish mon if player not about to die instantly
            return Decision(ACT_ATTACK, P0, reason="p0_finish_under_pressure", meta={"role": role})
        return Decision(ACT_HEAL, P0, reason="p0_hp_crit", meta={"role": role, "hp_r": round(hp_r, 3)})

    if morale <= MORALE_CRIT and role == ROLE_SUPPORT:
        return Decision(ACT_HEAL, P0, reason="p0_morale", meta={"morale": morale})

    if hp_r < HP_LOW and role in (ROLE_SUPPORT, ROLE_BALANCED):
        if ailments and not team_cleansed_this_round and role == ROLE_SUPPORT:
            return Decision(
                ACT_CLEANSE,
                P0,
                reason="p0_hp_low_cleanse",
                cleanse_target=ailments[0],
                meta={"role": role},
            )
        return Decision(ACT_HEAL, P0, reason="p0_hp_low", meta={"role": role})

    # ── P1: mon pressure (elite/boss + low HP) ─────────────────────
    if mon_threat and mon_r <= MON_PRESSURE:
        if role == ROLE_SUPPORT and hp_r < 0.55:
            return Decision(ACT_HEAL, P1, reason="p1_support_hold", meta={"mon_r": round(mon_r, 3)})
        return Decision(ACT_ATTACK, P1, reason="p1_mon_pressure", meta={"mon_r": round(mon_r, 3)})

    if mon_r <= MON_LOW:
        return Decision(ACT_ATTACK, P1, reason="p1_mon_low", meta={"mon_r": round(mon_r, 3)})

    # ── P2: general ───────────────────────────────────────────────
    if role == ROLE_SUPPORT:
        if ailments and not team_cleansed_this_round:
            return Decision(
                ACT_CLEANSE,
                P2,
                reason="p2_support_cleanse",
                cleanse_target=ailments[0],
                meta={"role": role},
            )
        if hp_r < 0.70:
            return Decision(ACT_HEAL, P2, reason="p2_support_heal")
        if mon_r > 0.55:
            return Decision(ACT_BUFF, P2, reason="p2_support_buff")
        return Decision(ACT_ATTACK, P2, reason="p2_support_chip")

    if role == ROLE_ATTACK:
        if hp_r < 0.35:
            return Decision(ACT_HEAL, P2, reason="p2_attack_self_save")
        return Decision(ACT_ATTACK, P2, reason="p2_attack")

    # balanced
    if hp_r < 0.50:
        return Decision(ACT_HEAL, P2, reason="p2_bal_heal")
    if mon_r < 0.40:
        return Decision(ACT_ATTACK, P2, reason="p2_bal_attack")
    return Decision(ACT_BUFF if mon_r > 0.6 else ACT_ATTACK, P2, reason="p2_bal_default")


def decide_for_tests(
    *,
    hp_ratio: float = 1.0,
    mon_ratio: float = 1.0,
    morale: int = 70,
    statuses: Optional[Sequence[str]] = None,
    kind: str = "spirit",
    role: str = "",
    elite: bool = False,
    boss: bool = False,
    bond: int = 50,
) -> Decision:
    """Deterministic helper for unit tests (no full player dict required)."""
    player: Dict[str, Any] = {
        "hp": int(100 * hp_ratio),
        "max_hp": 100,
        "needs": {"hunger": 20, "fatigue": 20, "morale": morale},
        "statuses": [{"id": s, "kind": "debuff", "remaining": 3} for s in (statuses or [])],
        "grade_revealed": True,
        "player_grade": "B",
    }
    mon: Dict[str, Any] = {
        "hp": int(100 * mon_ratio),
        "max_hp": 100,
        "elite": elite,
        "boss": boss,
    }
    member: Dict[str, Any] = {"id": "t", "kind": kind, "role": role, "rarity": "common"}
    return decide(player, mon, member, bond=bond, reg=None)
