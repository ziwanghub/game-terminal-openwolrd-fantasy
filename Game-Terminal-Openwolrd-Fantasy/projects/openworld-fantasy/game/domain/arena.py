"""
WO-Arena-1 — Arena System (First Version).

Team lineup 1–4 (player + up to 3 companions), 3 rounds per session,
strategy scoring (not win/lose only), mystery invites, tiered foes.
Soft bands only in player-facing copy — no drop % UI.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry

# ── Tiers ──────────────────────────────────────────────────────────────
TIERS: Tuple[str, ...] = ("normal", "elite", "legendary", "divine")
TIER_LABEL_TH: Dict[str, str] = {
    "normal": "สามัญ",
    "elite": "ชั้นเลิศ",
    "legendary": "ตำนาน",
    "divine": "เทพ",
}
TIER_MYSTERY_HINT: Dict[str, str] = {
    "normal": "กลิ่นฝุ่นสนาม · แรงกดแผ่ว",
    "elite": "เงาแน่น · จังหวะคม",
    "legendary": "ก้องเก่า · หายใจหนัก",
    "divine": "แสง/เถ้าซ้อน · เกือบกลืน",
}

# Promote thresholds (internal total score 0–300 from 3 rounds × ~100)
PROMOTE_MIN: Dict[str, int] = {
    "normal": 95,  # even 0 wins can promote if play well
    "elite": 120,
    "legendary": 150,
    "divine": 999,  # no deeper than divine
}

# Soft band cutoffs on total (3 rounds)
BAND_CUTOFFS: Tuple[Tuple[int, str, str], ...] = (
    (200, "legend_soft", "ตำนานแผ่ว"),
    (155, "sharp", "เฉียบ"),
    (110, "keen", "คม"),
    (70, "faint", "จาง"),
    (0, "dim", "เลือน"),
)

# Max foes on screen per fight (combat multi soft cap)
MAX_FOES_PER_FIGHT = 3


@dataclass
class RoundResult:
    won: bool
    score: int
    axes: Dict[str, int] = field(default_factory=dict)
    foe_names: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class SessionResult:
    tier: str
    rounds: List[RoundResult]
    total_score: int
    wins: int
    band_id: str
    band_label: str
    promoted: bool
    rewards: List[str] = field(default_factory=list)
    reward_items: List[str] = field(default_factory=list)


def ensure_arena_state(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    st = dict(player.get("arena") or {})
    st.setdefault("sessions", 0)
    st.setdefault("best_total", 0)
    st.setdefault("deepest_tier", "normal")
    st.setdefault("unlocked_tiers", ["normal"])
    st.setdefault("invite_flags", {})
    st.setdefault("last_band", "")
    st.setdefault("last_tier", "")
    player["arena"] = st
    return st


def party_lineup_size(player: Mapping[str, Any], lineup_ids: Optional[Sequence[str]] = None) -> int:
    """Player always counts as 1 + selected companions."""
    if lineup_ids is not None:
        return 1 + len([x for x in lineup_ids if x])
    return 1 + len(list(player.get("party") or [])[:3])


def available_companions(player: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for m in player.get("party") or []:
        if isinstance(m, dict) and m.get("id"):
            out.append(dict(m))
    return out[:3]


def select_lineup(
    player: Mapping[str, Any],
    indices: Sequence[int],
) -> List[str]:
    """
    indices: 1-based companion indices to bring (empty = solo).
    Returns list of companion ids (max 3).
    """
    comps = available_companions(player)
    chosen: List[str] = []
    for i in indices:
        j = int(i) - 1
        if 0 <= j < len(comps):
            mid = str(comps[j].get("id") or "")
            if mid and mid not in chosen:
                chosen.append(mid)
        if len(chosen) >= 3:
            break
    return chosen


def apply_lineup_to_party(
    player: MutableMapping[str, Any],
    lineup_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    """
    Temporarily restrict party to lineup for arena session.
    Stores full party in _arena_party_backup.
    """
    full = list(player.get("party") or [])
    player["_arena_party_backup"] = full
    if not lineup_ids:
        player["party"] = []
        return []
    idset = {str(x) for x in lineup_ids}
    player["party"] = [m for m in full if str(m.get("id") or "") in idset][:3]
    return list(player["party"])


def restore_party_after_arena(player: MutableMapping[str, Any]) -> None:
    bak = player.pop("_arena_party_backup", None)
    if bak is not None:
        player["party"] = list(bak)[:3]


# ── Mystery invite ─────────────────────────────────────────────────────


def _invite_weight_components(player: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> Dict[str, float]:
    """Soft weights for tier selection — not pure random."""
    w = {t: 1.0 for t in TIERS}
    # base: normal dominant
    w["normal"] = 8.0
    w["elite"] = 3.0
    w["legendary"] = 0.8
    w["divine"] = 0.15

    st = ensure_arena_state(player) if isinstance(player, dict) else {}
    unlocked = set(st.get("unlocked_tiers") or ["normal"])

    # shop rep soft
    try:
        from game.domain.shop_experience import get_shop_rep

        rep_sum = sum(get_shop_rep(player, sid) for sid in (
            "city_armory", "traveling_merchant", "legend_pavilion", "rare_exchange"
        ))
        if rep_sum >= 200:
            w["elite"] += 2.0
            w["legendary"] += 0.8
        if rep_sum >= 280:
            w["divine"] += 0.25
    except Exception:
        pass

    # anima
    try:
        from game.domain.stat_arch import anima_value

        a = float(anima_value(player))
        if a >= 55:
            w["elite"] += 1.0
        if a >= 70:
            w["legendary"] += 0.6
            w["divine"] += 0.2
        if a >= 85:
            w["divine"] += 0.35
    except Exception:
        pass

    # quests / bosses
    done = set(player.get("quests_done") or [])
    bosses = list(player.get("bosses_defeated") or [])
    if len(done) >= 5:
        w["elite"] += 1.2
    if len(done) >= 12:
        w["legendary"] += 0.7
    if bosses:
        w["legendary"] += 1.0 + 0.3 * min(3, len(bosses))
        w["divine"] += 0.15 * min(4, len(bosses))

    # prior arena score
    best = int(st.get("best_total") or 0)
    if best >= 110:
        w["elite"] += 1.5
    if best >= 155:
        w["legendary"] += 1.2
    if best >= 200:
        w["divine"] += 0.5

    # grade soft
    try:
        from game.domain.stat_grades import grade_revealed

        if grade_revealed(player):
            g = str(player.get("player_grade") or "C").upper()
            if g in ("A", "S", "SS", "SSS"):
                w["legendary"] += 0.5
            if g in ("S", "SS", "SSS"):
                w["divine"] += 0.4
    except Exception:
        pass

    # lock deeper tiers until unlocked (soft — still can roll if unlocked)
    for t in TIERS:
        if t not in unlocked and t != "normal":
            # still allow tiny weight if many flags, else near zero
            if t == "elite" and (bosses or len(done) >= 3):
                w[t] = max(w[t], 1.5)
            elif t == "legendary" and (len(bosses) >= 1 and best >= 120):
                w[t] = max(w[t] * 0.5, 0.3)
            elif t == "divine" and (len(bosses) >= 2 and best >= 170):
                w[t] = max(w[t] * 0.4, 0.08)
            else:
                w[t] *= 0.05 if t != "elite" else 0.35

    return w


def roll_mystery_invite(
    player: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    force_tier: Optional[str] = None,
) -> Dict[str, Any]:
    """Mystery invite card — soft hints, no stats."""
    ensure_arena_state(player)  # type: ignore[arg-type]
    if force_tier and force_tier in TIERS:
        tier = force_tier
    else:
        weights = _invite_weight_components(player, reg)
        total = sum(max(0.01, weights[t]) for t in TIERS)
        r = rng.random() * total
        acc = 0.0
        tier = "normal"
        for t in TIERS:
            acc += max(0.01, weights[t])
            if r <= acc:
                tier = t
                break
    return {
        "kind": "mystery",
        "tier": tier,
        "label": "เงา ???",
        "hint": TIER_MYSTERY_HINT.get(tier, "แรงกดไม่ชัด"),
        "tier_label": TIER_LABEL_TH.get(tier, tier),
        # do not show tier_label until accept? soft show pressure only
        "soft_pressure": TIER_MYSTERY_HINT.get(tier, ""),
    }


def reveal_invite_soft(invite: Mapping[str, Any]) -> str:
    """After accept — still soft, can name tier band vaguely."""
    tier = str(invite.get("tier") or "normal")
    return f"โทนสนาม 〔{TIER_LABEL_TH.get(tier, tier)}〕 · {TIER_MYSTERY_HINT.get(tier, '')}"


# ── Foe team building ──────────────────────────────────────────────────


def _mons_by_flags(reg: DataRegistry) -> Dict[str, List[str]]:
    buckets: Dict[str, List[str]] = {
        "normal": [],
        "elite": [],
        "legendary": [],
        "divine": [],
        "boss": [],
    }
    for mid, mon in (reg.monsters or {}).items():
        if mon.get("boss"):
            buckets["boss"].append(mid)
        rar = str(mon.get("rarity") or "common").lower()
        if rar in ("divine", "mythic"):
            buckets["divine"].append(mid)
        elif rar in ("legendary", "sacred"):
            buckets["legendary"].append(mid)
        elif mon.get("elite") or rar in ("rare", "uncommon"):
            buckets["elite"].append(mid)
        else:
            buckets["normal"].append(mid)
    return buckets


def build_foe_team(
    reg: DataRegistry,
    tier: str,
    rng: random.Random,
    *,
    player_team_size: int = 1,
    round_index: int = 0,
) -> List[Dict[str, Any]]:
    """
    NPC team 1–3 combatants (screen cap). Roster feel of 1–4 via round variety.
    Scales slightly with player_team_size.
    """
    from game.domain.combat import pick_monster

    tier = tier if tier in TIERS else "normal"
    buckets = _mons_by_flags(reg)
    # count: solo often 1 foe; full team up to 3
    base_n = 1
    if player_team_size >= 2:
        base_n = 2
    if player_team_size >= 4 or tier in ("legendary", "divine"):
        base_n = min(MAX_FOES_PER_FIGHT, 2 + (1 if round_index >= 1 else 0))
    if tier == "divine":
        base_n = min(MAX_FOES_PER_FIGHT, max(2, base_n))
    n = max(1, min(MAX_FOES_PER_FIGHT, base_n + (1 if round_index == 2 and tier != "normal" else 0)))
    n = min(MAX_FOES_PER_FIGHT, n)

    pool_ids: List[str] = []
    if tier == "normal":
        pool_ids = buckets["normal"] or list((reg.monsters or {}).keys())
    elif tier == "elite":
        pool_ids = buckets["elite"] or buckets["normal"]
    elif tier == "legendary":
        pool_ids = buckets["legendary"] or buckets["elite"] or buckets["boss"]
    else:
        pool_ids = buckets["divine"] or buckets["legendary"] or buckets["boss"]

    if not pool_ids:
        pool_ids = list((reg.monsters or {}).keys())[:5]

    foes: List[Dict[str, Any]] = []
    for i in range(n):
        mid = pool_ids[rng.randrange(len(pool_ids))]
        base = dict(reg.monsters.get(mid) or {"id": mid, "name": mid})
        # materialize like pick_monster lite
        lv_min = int(base.get("level_min", 1))
        lv_max = int(base.get("level_max", lv_min + 2))
        mlevel = rng.randint(lv_min, max(lv_min, lv_max))
        hp = int(base.get("hp_base", 50)) + (mlevel - lv_min) * 6
        atk = int(base.get("atk_base", 8)) + (mlevel - lv_min) // 2
        # tier scale
        scale = {"normal": 1.0, "elite": 1.2, "legendary": 1.45, "divine": 1.75}.get(tier, 1.0)
        # player team scale soft
        scale *= 1.0 + 0.06 * max(0, player_team_size - 1)
        # round heat
        scale *= 1.0 + 0.05 * round_index
        mon = {
            "id": base.get("id", mid),
            "name": base.get("name", mid),
            "level": mlevel,
            "hp": max(8, int(hp * scale)),
            "max_hp": max(8, int(hp * scale)),
            "atk": max(2, int(atk * scale)),
            "elements": list(base.get("elements") or ["physical"]),
            "elite": bool(base.get("elite") or tier in ("elite", "legendary", "divine")),
            "rarity": base.get("rarity") or (
                "divine" if tier == "divine" else "rare" if tier == "legendary" else "common"
            ),
            "arena_tier": tier,
            "drops": list(base.get("drops") or []),
        }
        if tier == "divine":
            mon["name"] = str(mon["name"]) + " 〔เงาเทพ〕"
        elif tier == "legendary":
            mon["name"] = str(mon["name"]) + " 〔ก้อง〕"
        foes.append(mon)
    return foes


# ── Scoring ────────────────────────────────────────────────────────────


def score_round_from_metrics(
    *,
    won: bool,
    damage_dealt: int,
    damage_taken: int,
    skills_used: int,
    skill_variety: int,
    assists: int,
    hp_ratio_end: float,
    rounds_taken: int,
    acted: bool,
) -> RoundResult:
    """
    Internal 0–100-ish per round from strategy axes.
    Soft design: win helps but loss can still score high.
    """
    axes: Dict[str, int] = {}
    # Pressure 0–28
    axes["pressure"] = min(28, int(damage_dealt / 8) + (6 if won else 0))
    # Craft 0–20
    axes["craft"] = min(20, skills_used * 3 + skill_variety * 4)
    # Team 0–16
    axes["team"] = min(16, assists * 5)
    # Poise 0–16
    hr = max(0.0, min(1.0, float(hp_ratio_end)))
    axes["poise"] = int(hr * 14) + (2 if damage_taken < 30 else 0)
    # Tempo 0–10 (faster better, soft)
    axes["tempo"] = max(0, 10 - max(0, rounds_taken - 3))
    # Resolve 0–10
    if not acted:
        axes["resolve"] = 0
    elif won:
        axes["resolve"] = 10
    else:
        axes["resolve"] = 7 if damage_dealt > 0 else 2

    total = sum(axes.values())
    # cap ~100
    total = min(100, total)
    notes = []
    if not won and total >= 55:
        notes.append("แพ้รอบ แต่จังหวะ/แรงกดยังคม")
    if won and total >= 70:
        notes.append("รอบนี้เล่นคม")
    return RoundResult(won=won, score=total, axes=axes, notes=notes)


def simulate_round_fight(
    player: MutableMapping[str, Any],
    foes: Sequence[Mapping[str, Any]],
    reg: DataRegistry,
    rng: random.Random,
    *,
    lineup_size: int = 1,
) -> RoundResult:
    """
    Lightweight arena fight for scoring + harness (not full ATB UI).
    Uses power_atk / party bonds soft.
    """
    if not foes:
        return score_round_from_metrics(
            won=True,
            damage_dealt=0,
            damage_taken=0,
            skills_used=0,
            skill_variety=0,
            assists=0,
            hp_ratio_end=1.0,
            rounds_taken=1,
            acted=True,
        )
    atk = int(player.get("power_atk") or player.get("bonus_atk") or player.get("atk") or 10)
    # party soft assist power
    party = list(player.get("party") or [])
    bond_avg = 40
    if party:
        bonds = player.get("party_bonds") or {}
        vals = [int(bonds.get(str(m.get("id")), 40) or 40) for m in party if isinstance(m, dict)]
        if vals:
            bond_avg = sum(vals) // len(vals)
    assist_p = 0.2 + (bond_avg / 100.0) * 0.45 + 0.08 * max(0, lineup_size - 1)

    skills = list(player.get("skills") or [])
    skill_n = min(6, max(1, len(skills)))
    dmg_dealt = 0
    dmg_taken = 0
    assists = 0
    skills_used = 0
    variety = set()
    rounds_taken = 0
    # clone foes
    pack = [dict(f) for f in foes]
    for f in pack:
        f["hp"] = int(f.get("hp") or f.get("max_hp") or 20)
        f["max_hp"] = int(f.get("max_hp") or f["hp"])

    hp0 = max(1, int(player.get("hp") or 20))
    mhp = max(1, int(player.get("max_hp") or hp0))
    player_hp = hp0

    for turn in range(1, 14):
        rounds_taken = turn
        # player hit focus first living foe
        living = [f for f in pack if int(f.get("hp") or 0) > 0]
        if not living:
            break
        target = living[0]
        sk = skills[rng.randrange(len(skills))] if skills else "basic"
        variety.add(str(sk))
        skills_used += 1
        hit = max(3, int(atk * (0.7 + rng.random() * 0.7)))
        # soft weakness lite ignore — flat
        target["hp"] = int(target["hp"]) - hit
        dmg_dealt += hit
        # assists
        if party and rng.random() < assist_p:
            ad = max(1, int(2 + bond_avg / 20 + rng.randint(0, 4)))
            target["hp"] = int(target["hp"]) - ad
            dmg_dealt += ad
            assists += 1
        living = [f for f in pack if int(f.get("hp") or 0) > 0]
        if not living:
            break
        # foes swing
        for f in living:
            fatk = int(f.get("atk") or 5)
            raw = max(1, int(fatk * (0.5 + rng.random() * 0.6)))
            # soft def
            raw = max(1, int(raw * (0.85 if lineup_size >= 3 else 1.0)))
            player_hp -= raw
            dmg_taken += raw
            if player_hp <= 0:
                break
        if player_hp <= 0:
            break

    won = player_hp > 0 and all(int(f.get("hp") or 0) <= 0 for f in pack)
    if player_hp < 1:
        player_hp = 1  # soft — arena doesn't soft-death kill save, restore later
    # write back hp soft (caller may restore)
    player["_arena_round_hp"] = player_hp
    hr = player_hp / float(mhp)
    res = score_round_from_metrics(
        won=won,
        damage_dealt=dmg_dealt,
        damage_taken=dmg_taken,
        skills_used=skills_used,
        skill_variety=len(variety),
        assists=assists,
        hp_ratio_end=hr,
        rounds_taken=rounds_taken,
        acted=skills_used > 0,
    )
    res.foe_names = [str(f.get("name") or f.get("id")) for f in pack]
    if won:
        res.notes.append("ชนะรอบ")
    else:
        res.notes.append("แพ้รอบ")
    return res


def total_and_band(rounds: Sequence[RoundResult]) -> Tuple[int, str, str]:
    total = sum(int(r.score) for r in rounds)
    for cut, bid, lab in BAND_CUTOFFS:
        if total >= cut:
            return total, bid, lab
    return total, "dim", "เลือน"


def can_promote(tier: str, total_score: int, wins: int) -> bool:
    """Lose all 3 but high score can still promote (except past divine)."""
    need = int(PROMOTE_MIN.get(tier, 999))
    if tier == "divine":
        return False
    if total_score >= need:
        return True
    # win path softer threshold
    if wins >= 2 and total_score >= int(need * 0.75):
        return True
    return False


def next_tier(tier: str) -> Optional[str]:
    try:
        i = TIERS.index(tier)
    except ValueError:
        return None
    if i + 1 < len(TIERS):
        return TIERS[i + 1]
    return None


def unlock_tier(player: MutableMapping[str, Any], tier: str) -> None:
    st = ensure_arena_state(player)
    unlocked = list(st.get("unlocked_tiers") or ["normal"])
    if tier not in unlocked:
        unlocked.append(tier)
    st["unlocked_tiers"] = unlocked
    # deepest
    order = {t: i for i, t in enumerate(TIERS)}
    cur = str(st.get("deepest_tier") or "normal")
    if order.get(tier, 0) > order.get(cur, 0):
        st["deepest_tier"] = tier
    player["arena"] = st


# ── Rewards ────────────────────────────────────────────────────────────


def reward_plan(
    tier: str,
    band_id: str,
    wins: int,
    *,
    player_grade: str = "C",
) -> Dict[str, Any]:
    """
    Rewards by score band + tier. F with good band still rewarded.
    Divine + sharp+ → rare soft.
    """
    money = 0
    items: List[str] = []
    xp = 0
    # band base
    band_money = {"dim": 0, "faint": 15, "keen": 40, "sharp": 75, "legend_soft": 110}
    band_xp = {"dim": 0, "faint": 20, "keen": 55, "sharp": 100, "legend_soft": 140}
    money = int(band_money.get(band_id, 0))
    xp = int(band_xp.get(band_id, 0))
    # tier mult
    tmult = {"normal": 1.0, "elite": 1.35, "legendary": 1.8, "divine": 2.4}.get(tier, 1.0)
    money = int(money * tmult)
    xp = int(xp * tmult)
    # win bonus small
    money += wins * 8
    xp += wins * 12

    if band_id in ("keen", "sharp", "legend_soft"):
        items.append("upgrade_mat")
    if band_id in ("sharp", "legend_soft"):
        items.append("potion_hp")
    if tier in ("elite", "legendary", "divine") and band_id != "dim":
        items.append("rare_mat")
    if tier == "divine" and band_id in ("keen", "sharp", "legend_soft"):
        items.append("rare_mat")
        # rare gear soft id if exists — keep mat/consumable safe
        items.append("shop_rare_crystal_lens")
    if tier == "legendary" and band_id in ("sharp", "legend_soft"):
        items.append("scroll_guard_level")

    # F grade does NOT zero rewards
    return {
        "money": money,
        "xp": xp,
        "items": items,
        "shop_rep": 6 if band_id in ("keen", "sharp", "legend_soft") else (
            3 if band_id == "faint" else 0
        ),
        "anima_nudge": 0.4 if band_id in ("sharp", "legend_soft") else (
            0.2 if band_id == "keen" else 0.0
        ),
    }


def apply_rewards(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    plan: Mapping[str, Any],
    *,
    tier: str,
) -> List[str]:
    lines: List[str] = []
    money = int(plan.get("money") or 0)
    if money > 0:
        player["money_world"] = int(player.get("money_world") or 0) + money
        lines.append(f"  เงินโลก +{money}")
    xp = int(plan.get("xp") or 0)
    if xp > 0:
        try:
            from game.domain.leveling import grant_xp

            summary = grant_xp(player, xp, reg.levels)
            lines.append(f"  XP +{summary.get('gained', xp)}")
            for n in summary.get("notes") or []:
                lines.append(f"  {n}")
        except Exception:
            lines.append(f"  XP +{xp}")
    try:
        from game.domain.equipment import add_item

        for iid in plan.get("items") or []:
            if iid in (reg.items or {}):
                nm = add_item(player, str(iid), reg)
                lines.append(f"  ได้ {nm}")
    except Exception:
        pass
    rep_amt = int(plan.get("shop_rep") or 0)
    if rep_amt > 0:
        try:
            from game.domain.shop_experience import (
                bump_shop_rep,
                get_shop_rep,
                shop_rep_soft_label,
                on_arena_or_spar_win,
            )

            # prefer fame hook + small armory bump
            lines.extend(on_arena_or_spar_win(player, reg, source="arena", amount=max(5, rep_amt)))
        except Exception:
            pass
    nudge = float(plan.get("anima_nudge") or 0)
    if nudge > 0:
        try:
            from game.domain.stat_arch import _nudge_anima

            _nudge_anima(player, nudge)
            lines.append("  จิตอุ่นขึ้นแผ่วหลังอารีน่า (Anima soft)")
        except Exception:
            pass
    return lines


def run_arena_session_logic(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    tier: str = "normal",
    lineup_ids: Optional[Sequence[str]] = None,
) -> SessionResult:
    """
    Full 3-round session with simulated fights + scoring + rewards + promote.
    """
    ensure_arena_state(player)
    tier = tier if tier in TIERS else "normal"
    lineup_ids = list(lineup_ids or [])
    apply_lineup_to_party(player, lineup_ids)
    team_size = party_lineup_size(player, lineup_ids)
    # snapshot hp
    hp_backup = int(player.get("hp") or 1)
    mhp = max(1, int(player.get("max_hp") or hp_backup))

    rounds: List[RoundResult] = []
    try:
        for ri in range(3):
            # soft heal between rounds
            player["hp"] = max(1, min(mhp, int(player.get("hp") or mhp) + mhp // 8))
            foes = build_foe_team(
                reg, tier, rng, player_team_size=team_size, round_index=ri
            )
            rr = simulate_round_fight(
                player, foes, reg, rng, lineup_size=team_size
            )
            if player.get("_arena_round_hp"):
                player["hp"] = max(1, int(player["_arena_round_hp"]))
            rounds.append(rr)
    finally:
        restore_party_after_arena(player)
        # restore some hp after arena (not soft-death)
        player["hp"] = max(1, min(mhp, max(hp_backup // 2, int(player.get("hp") or 1))))

    total, band_id, band_lab = total_and_band(rounds)
    wins = sum(1 for r in rounds if r.won)
    promoted = can_promote(tier, total, wins)
    if promoted:
        nt = next_tier(tier)
        if nt:
            unlock_tier(player, nt)

    st = ensure_arena_state(player)
    st["sessions"] = int(st.get("sessions") or 0) + 1
    st["best_total"] = max(int(st.get("best_total") or 0), total)
    st["last_band"] = band_id
    st["last_tier"] = tier
    player["arena"] = st

    grade = str(player.get("player_grade") or "C")
    plan = reward_plan(tier, band_id, wins, player_grade=grade)
    # dim band → no rewards
    reward_lines: List[str] = []
    if band_id != "dim":
        reward_lines = apply_rewards(player, reg, plan, tier=tier)
    else:
        reward_lines = ["  คะแนนเลือน — ไม่มีรางวัลหลัก"]

    return SessionResult(
        tier=tier,
        rounds=rounds,
        total_score=total,
        wins=wins,
        band_id=band_id,
        band_label=band_lab,
        promoted=promoted,
        rewards=reward_lines,
        reward_items=list(plan.get("items") or []),
    )


def format_session_summary(result: SessionResult) -> List[str]:
    lines = [
        f" อารีน่า · ชั้น 〔{TIER_LABEL_TH.get(result.tier, result.tier)}〕",
        "---",
        f" ชนะ {result.wins}/3 รอบ · แบนด์กลยุทธ์ 〔{result.band_label}〕",
    ]
    # soft total — rounded display without formula
    soft_pts = max(0, int(round(result.total_score / 5.0) * 5))
    lines.append(f" แต้มกลยุทธ์รวม ~{soft_pts} (soft · ไม่โชว์สูตร)")
    for i, r in enumerate(result.rounds, 1):
        wl = "ชนะ" if r.won else "แพ้"
        lines.append(f"  รอบ {i}: {wl} · คมประมาณ {r.score}")
        for n in r.notes[:1]:
            lines.append(f"    · {n}")
    if result.promoted:
        nt = next_tier(result.tier)
        if nt:
            lines.append(
                f" ไขชั้นลึก: 〔{TIER_LABEL_TH.get(nt, nt)}〕 เปิด soft"
            )
    lines.append("---")
    lines.append(" รางวัล")
    if result.rewards:
        lines.extend(result.rewards)
    else:
        lines.append("  (ไม่มี)")
    return lines
