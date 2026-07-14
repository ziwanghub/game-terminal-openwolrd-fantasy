"""
Monster intelligence (MI1–MI2) — soft AI for elite / boss / intel_tier.

MI1: context-aware attack_profile pick (not pure random).
MI2: soft flee when smart + low HP (bosses never flee).
MI3 (later): talk / negotiate — not here.

Formulas stay hidden; player sees telegraph / soft flee lines only.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple


def resolve_monster_intel_tier(monster: Mapping[str, Any]) -> int:
    """
    0 = beast instinct (random profiles)
    1 = cunning (light bias)
    2 = elite mind (status/variety/finisher)
    3 = boss / high intellect (stronger bias; no flee)
    """
    raw = monster.get("intel_tier")
    if raw is not None:
        try:
            return max(0, min(5, int(raw)))
        except (TypeError, ValueError):
            pass
    if monster.get("boss"):
        return 3
    if monster.get("elite"):
        return 2
    rarity = str(monster.get("rarity") or monster.get("catalog_rarity") or "common").lower()
    if rarity in ("legendary", "mythic", "epic"):
        return 2
    if rarity in ("rare", "unique"):
        return 1
    return 0


def attach_monster_intel_fields(
    mon: MutableMapping[str, Any],
    base: Mapping[str, Any],
) -> None:
    """Copy YAML intel flags onto runtime mon (call from pick_monster / spawn_boss)."""
    if base.get("intel_tier") is not None:
        mon["intel_tier"] = int(base["intel_tier"])
    if "can_flee" in base:
        mon["can_flee"] = bool(base.get("can_flee"))
    if base.get("never_flee"):
        mon["never_flee"] = True
    # default boss never flees unless explicitly allowed
    if mon.get("boss") and "never_flee" not in mon and base.get("can_flee") is not True:
        mon["never_flee"] = True
    # ensure resolved tier is cached for soft UI later
    mon["intel_tier"] = resolve_monster_intel_tier(mon)


def _weighted_choice(
    items: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    rng: random.Random,
) -> Dict[str, Any]:
    if not items:
        raise ValueError("empty items")
    total = sum(max(0.0, float(w)) for w in weights)
    if total <= 0:
        return dict(rng.choice(list(items)))
    r = rng.random() * total
    acc = 0.0
    for item, w in zip(items, weights):
        acc += max(0.0, float(w))
        if r <= acc:
            return dict(item)
    return dict(items[-1])


def _profile_power(profile: Mapping[str, Any], monster: Mapping[str, Any]) -> int:
    return int(profile.get("power") or monster.get("atk") or 8)


def score_attack_profiles(
    monster: Mapping[str, Any],
    profiles: Sequence[Mapping[str, Any]],
    player: Optional[Mapping[str, Any]],
    *,
    tier: Optional[int] = None,
) -> List[float]:
    """
    Relative weights for MI1. Pure documentation of bias — no % shown in UI.
    """
    tier = resolve_monster_intel_tier(monster) if tier is None else int(tier)
    if not profiles:
        return []
    powers = [_profile_power(p, monster) for p in profiles]
    max_p = max(powers) or 1
    php_ratio = 1.0
    has_status = False
    if player is not None:
        php = max(0, int(player.get("hp") or 0))
        pmax = max(1, int(player.get("max_hp") or 1))
        php_ratio = php / pmax
        has_status = bool(player.get("statuses"))
    mhp = max(0, int(monster.get("hp") or 0))
    mmax = max(1, int(monster.get("max_hp") or 1))
    mhp_ratio = mhp / mmax
    last_id = monster.get("_last_profile_id")
    weights: List[float] = []
    for p, power in zip(profiles, powers):
        w = 1.0
        pnorm = power / max_p
        if tier <= 0 or player is None:
            weights.append(w)
            continue
        # finish wounded player
        if php_ratio < 0.35 and tier >= 1:
            w += 1.6 * pnorm * (1.0 + 0.25 * (tier - 1))
        # open with status when target is clean
        if p.get("status") or p.get("status_chance"):
            if not has_status and tier >= 1:
                w += 1.4 + 0.2 * tier
            elif has_status:
                w += 0.2 * pnorm
        # variety: avoid repeating last telegraph id
        if last_id and p.get("id") == last_id and len(profiles) > 1 and tier >= 2:
            w *= 0.32
        # mid fight: slight lean to stronger
        if tier >= 2 and 0.35 <= php_ratio <= 0.75:
            w += 0.45 * pnorm
        # desperation when self low (not fleeing yet)
        if mhp_ratio < 0.30 and tier >= 2:
            w += 1.5 * pnorm
        # boss / high mind: prefer multi-tag (element pressure)
        tags = list(p.get("tags") or [])
        if tier >= 3 and len(tags) >= 2:
            w += 0.55
        weights.append(max(0.05, w))
    return weights


def pick_smart_monster_attack(
    monster: Mapping[str, Any],
    rng: random.Random,
    *,
    player: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    MI1 entry: weighted profile pick when intel_tier >= 1 and player context given.
    Falls back to uniform choice for dumb beasts or missing context.
    """
    profiles = list(monster.get("attack_profiles") or [])
    if not profiles:
        return {
            "id": "basic",
            "tags": list(monster.get("elements") or ["physical"]),
            "telegraph": "ศัตรูโจมตี!",
            "power": int(monster.get("atk", 8)),
        }
    tier = resolve_monster_intel_tier(monster)
    if tier <= 0 or player is None:
        chosen = dict(rng.choice(profiles))
    else:
        weights = score_attack_profiles(monster, profiles, player, tier=tier)
        chosen = _weighted_choice(profiles, weights, rng)
    # record last for variety (best-effort if mutable)
    if isinstance(monster, dict):
        monster["_last_profile_id"] = chosen.get("id")
    return chosen


def try_monster_flee(
    monster: MutableMapping[str, Any],
    player: Mapping[str, Any],
    rng: random.Random,
) -> Tuple[bool, Optional[str]]:
    """
    MI2: smart enemies may soft-flee when HP is low.
    Bosses / never_flee stay. At most one roll per fight (_fled_attempted).
    Returns (fled, soft_message).
    """
    if monster.get("_escaped") or monster.get("_fled_attempted"):
        return False, None
    if monster.get("never_flee") or monster.get("boss"):
        return False, None
    if monster.get("can_flee") is False:
        return False, None

    tier = resolve_monster_intel_tier(monster)
    # need mind OR explicit can_flee
    if tier < 2 and monster.get("can_flee") is not True:
        return False, None

    mhp = max(0, int(monster.get("hp") or 0))
    mmax = max(1, int(monster.get("max_hp") or 1))
    ratio = mhp / mmax
    # only consider when clearly losing
    threshold = 0.30 if tier >= 3 else 0.26
    if monster.get("can_flee") is True:
        threshold = max(threshold, 0.32)
    if ratio > threshold or mhp <= 0:
        return False, None

    # one attempt flag even if fail — avoids spam checks every ATB
    monster["_fled_attempted"] = True

    # soft chance (hidden): higher when more desperate / smarter / outleveled
    base = 0.14 + 0.07 * max(0, tier - 1)
    if ratio < 0.16:
        base += 0.14
    if ratio < 0.09:
        base += 0.12
    plv = int(player.get("level") or 1)
    mlv = int(monster.get("level") or 1)
    if plv >= mlv + 3:
        base += 0.10
    if plv >= mlv + 6:
        base += 0.08
    # wounded player less likely to scare elite away (they smell blood)
    php = max(0, int(player.get("hp") or 0))
    pmax = max(1, int(player.get("max_hp") or 1))
    if php / pmax < 0.25:
        base *= 0.45
    # explicit can_flee on lower tier
    if monster.get("can_flee") is True and tier < 2:
        base = max(base, 0.22)
    chance = min(0.58, max(0.05, base))
    if rng.random() >= chance:
        return False, None

    monster["_escaped"] = True
    mon_name = str(monster.get("name") or monster.get("base_name") or "ศัตรู")
    lines = [
        f"{mon_name} เห็นช่องว่าง — หันหลังวิ่งหายไปในเงา…",
        f"ท่าทาง {mon_name} แตก — มันเลือกถอยก่อนสาย!",
        f"คุณยังไม่ทันปิดจบ — {mon_name} หายจากวงรบ",
        f"{mon_name} กระชากตัวถอย… เหลือแต่รอยฝุ่น",
    ]
    return True, lines[rng.randint(0, len(lines) - 1)]


def soft_intel_hint(monster: Mapping[str, Any], *, known: bool = False) -> Optional[str]:
    """Optional soft line when player already knows the species — no numbers."""
    if not known:
        return None
    tier = resolve_monster_intel_tier(monster)
    if tier >= 3:
        return "  (รู้สึกว่ามันคิดเป็น… ไม่ใช่แค่ทุ่มพลัง)"
    if tier >= 2:
        return "  (ท่าทางฉลาดกว่ามอนธรรมดา — อาจเลือกท่า/ถอย/คุย)"
    if tier >= 1:
        return "  (มีเล่ห์เล็กน้อยในจังหวะโจมตี)"
    return None


# ── MI3: talk / soft negotiate (approach tool, not combat core) ───────────────

TALK_STYLES = ("calm", "gift", "threaten", "walk")


def talk_eligible(monster: Mapping[str, Any]) -> bool:
    """
    Whether this foe can hold a soft exchange.
    Explicit can_talk wins; else intel_tier ≥ 2 (elite mind+) or rare_talk beasts lightly.
    """
    if monster.get("can_talk") is False:
        return False
    if monster.get("can_talk") is True:
        return True
    if monster.get("boss") and monster.get("can_talk") is not True:
        # bosses: only if YAML allows (default no chat mid-approach)
        return False
    return resolve_monster_intel_tier(monster) >= 2


def bias_monster_approach(
    base_outcome: str,
    monster: Mapping[str, Any],
    player: Mapping[str, Any],
    rng: random.Random,
) -> str:
    """
    Soft re-roll for smart foes: more rare_talk / flee, less pure ambush spam.
    Never shows weights. Keeps base often so wild fights still feel wild.
    """
    tier = resolve_monster_intel_tier(monster)
    if tier <= 0:
        return base_outcome
    # explicit dumb beasts
    if monster.get("can_talk") is False and tier < 2:
        return base_outcome

    r = rng.random()
    # smart: sometimes open a dialogue window instead of fight
    talk_boost = 0.10 + 0.06 * min(3, tier)
    if talk_eligible(monster) and r < talk_boost:
        return "rare_talk"
    # cautious smart: slightly more pre-fight flee when player much stronger
    plv = int(player.get("level") or 1)
    mlv = int(monster.get("level") or 1)
    if (
        tier >= 2
        and not monster.get("boss")
        and monster.get("can_flee") is not False
        and plv >= mlv + 4
        and r < 0.14
    ):
        return "flee"
    # smart hunters: slightly more ambush when player is wounded
    php = max(0, int(player.get("hp") or 0))
    pmax = max(1, int(player.get("max_hp") or 1))
    if tier >= 2 and php / pmax < 0.4 and r > 0.82:
        return "ambush"
    return base_outcome


def resolve_monster_talk(
    monster: MutableMapping[str, Any],
    player: MutableMapping[str, Any],
    style: str,
    rng: random.Random,
    *,
    reg: Any = None,
) -> Tuple[str, List[str]]:
    """
    MI3 dialogue resolution.

    Returns (outcome, soft_lines) where outcome is one of:
      truce | tip | tribute | combat | ambush | flee | walk
    Hidden rolls — never expose %.
    """
    style = str(style or "calm").lower()
    if style not in TALK_STYLES:
        style = "calm"
    mon_name = str(monster.get("name") or monster.get("base_name") or "สิ่งมีชีวิต")
    tier = resolve_monster_intel_tier(monster)
    lines: List[str] = []

    if style == "walk":
        lines.append(f"คุณถอยช้าๆ — {mon_name} จ้องแล้วยังไม่พุ่งตาม…")
        return "walk", lines

    # base success (hidden)
    luck = float(player.get("luck_score") or 0.0)
    intel_pts = int((player.get("stats_alloc") or {}).get("intelligence") or 0)
    caution = float((player.get("personality") or {}).get("caution") or 0)
    courage = float((player.get("personality") or {}).get("courage") or 0)
    base = 0.38 + 0.04 * min(4, tier) + luck * 0.25 + intel_pts * 0.02

    if style == "calm":
        base += 0.08 + caution * 0.01
        lines.append(f"คุณลดอาวุธ — พูดกับ {mon_name} ด้วยน้ำเสียงราบ…")
    elif style == "gift":
        cost = 15 + max(0, tier) * 5
        if int(player.get("money_world") or 0) >= cost:
            player["money_world"] = int(player.get("money_world") or 0) - cost
            base += 0.22
            lines.append(f"คุณยื่นสิ่งของ/เงินเล็กน้อย (เสียเงินโลก {cost})…")
        else:
            base -= 0.12
            lines.append("อยากยื่นของขวัญ แต่กระเป๋าเบา — มันมองอย่างสงสัย…")
            style = "calm"
    elif style == "threaten":
        base -= 0.10 + (0.06 if tier >= 2 else 0)
        base += courage * 0.008
        lines.append(f"คุณข่ม {mon_name} — มันไม่กระตุกแบบสัตว์ธรรมดา…")

    # level gap: weaker player harder to impress
    plv = int(player.get("level") or 1)
    mlv = int(monster.get("level") or 1)
    if mlv >= plv + 4:
        base -= 0.12
    if plv >= mlv + 3:
        base += 0.08

    base = max(0.12, min(0.88, base))
    roll = rng.random()
    success = roll < base

    if style == "threaten" and not success:
        # smart + threaten fail → ambush or combat
        if tier >= 2 and rng.random() < 0.55:
            lines.append(f"{mon_name} ไม่ยอม — กระโจนใส่ก่อน!")
            return "ambush", lines
        lines.append(f"{mon_name} ตอบด้วยเขี้ยว/คมอาวุธ — เข้าปะทะ!")
        return "combat", lines

    if style == "threaten" and success:
        # scare off
        if not monster.get("boss") and (monster.get("can_flee") is not False):
            monster["_escaped"] = True
            lines.append(f"{mon_name} ถอยหลัง… แล้วหายไปในเงา (ถูกข่มจนถอย)")
            return "flee", lines
        lines.append(f"{mon_name} ยืนนิ่ง — ไม่สู้ แต่ก็ไม่ยอมถอย (ตรึงสถานการณ์)")
        return "truce", lines

    if not success:
        if rng.random() < 0.4:
            lines.append(f"มันไม่เข้าใจ — หรือไม่สนใจ — แล้วขยับเข้าใกล้!")
            return "combat", lines
        lines.append(f"{mon_name} หันหลัง… การสนทนาจบแบบคลุมเครือ")
        return "walk", lines

    # success branches
    branch = rng.random()
    if branch < 0.34:
        # truce + mastery
        lines.append(f"{mon_name} ผงกหัว/ส่งเสียงต่ำ — เหมือนยอมรับการไม่สู้")
        lines.append("  (ได้ช่องว่างหายใจ · ชำนาญพื้นที่งอกเงย)")
        return "truce", lines
    if branch < 0.62:
        # tip / knowledge soft
        tips = [
            "มันชี้ทาง/ส่งเสียงไปทางหนึ่ง — คุณจำกลิ่นลมพื้นที่นี้ได้ชัดขึ้น",
            "ในสายตาของมัน… เหมือนมีคำเตือนเรื่องภัยในแถบนี้",
            "คุณรู้สึกว่า ‘ทางที่ปลอดภัยกว่า’ โผล่ในหัว (ใบ้พื้นที่)",
        ]
        lines.append(tips[rng.randint(0, len(tips) - 1)])
        return "tip", lines
    if branch < 0.82 and style == "gift":
        lines.append(f"{mon_name} ทิ้งของเล็กน้อยแล้วจากไป…")
        return "tribute", lines
    # default success = soft leave without fight
    lines.append(f"{mon_name} หันหลังเดินจาก — วงรบไม่เกิด")
    return "truce", lines


def apply_talk_rewards(
    player: MutableMapping[str, Any],
    monster: Mapping[str, Any],
    outcome: str,
    rng: random.Random,
    *,
    reg: Any = None,
) -> List[str]:
    """Side effects for successful / soft talk outcomes. Soft messages only."""
    notes: List[str] = []
    aid = str(player.get("location") or "")
    am = dict(player.get("area_mastery") or {})
    if outcome in ("truce", "tip", "tribute", "flee"):
        gain = 2 if outcome == "tip" else 1
        if outcome == "truce":
            gain = 2
        if aid:
            am[aid] = min(100, int(am.get(aid, 0)) + gain)
            player["area_mastery"] = am
            notes.append(f"  ชำนาญพื้นที่ +{gain}% (รู้สึก)")
    if outcome == "tip":
        # library / soft knowledge
        try:
            from game.domain.progression import grant_library_key

            if rng.random() < 0.28:
                notes.append(grant_library_key(player))
        except Exception:
            pass
        know = dict(player.get("knowledge") or {})
        mons = dict(know.get("monsters") or {})
        mid = str(monster.get("id") or "")
        if mid:
            entry = dict(mons.get(mid) or {"seen": True, "fought": 0, "won": 0})
            entry["seen"] = True
            entry["talked"] = int(entry.get("talked") or 0) + 1
            entry["name"] = monster.get("name")
            mons[mid] = entry
            know["monsters"] = mons
            player["knowledge"] = know
    if outcome == "tribute":
        try:
            from game.domain.equipment import add_item

            loot_id = rng.choice(
                ["herb_bundle", "upgrade_mat", "potion_hp_small", "goblin_scrap"]
            )
            if reg is not None:
                name = add_item(player, loot_id, reg)
                notes.append(f"  ได้ {name}")
            else:
                inv = list(player.get("inventory_ids") or [])
                inv.append(loot_id)
                player["inventory_ids"] = inv
                notes.append(f"  ได้ของเล็กน้อย ({loot_id})")
        except Exception:
            gold = rng.randint(8, 22)
            player["money_world"] = int(player.get("money_world") or 0) + gold
            notes.append(f"  เศษเงินโลก +{gold}")
    if outcome == "truce":
        ac = dict(player.get("action_counts") or {})
        ac["monster_talk"] = int(ac.get("monster_talk", 0)) + 1
        player["action_counts"] = ac
    return notes
