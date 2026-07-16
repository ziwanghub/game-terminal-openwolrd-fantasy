"""
WO-038 World Relations Lite — divine / infernal / ancient_echo.

Uses player["world_relations"] keys (via stat_arch helpers).
Soft Alert + soft moments only — no raw scores in player UI.
No new resources; links soft to Anima + morale Needs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional

# Faction ids (stored as axis "faction" + id)
FACTION_DIVINE = "divine"
FACTION_INFERNAL = "infernal"
FACTION_ECHO = "ancient_echo"

FACTION_META: Dict[str, Dict[str, str]] = {
    FACTION_DIVINE: {
        "label_th": "สายสวรรค์/เทพ",
        "warm_alert": "world.divine_glance",
        "cold_alert": "world.divine_avert",
        "presence": "เทพวายุส่งสายตา…",
    },
    FACTION_INFERNAL: {
        "label_th": "สายมาร/นรก",
        "warm_alert": "world.infernal_favor",
        "cold_alert": "world.infernal_haze",
        "presence": "พลังมารแผ่ซ่านเบา ๆ…",
    },
    FACTION_ECHO: {
        "label_th": "เงาโบราณ/echo",
        "warm_alert": "world.echo_nod",
        "cold_alert": "world.echo_stare",
        "presence": "เงา echo หยุดมองคุณ…",
    },
}

# Area → primary faction flavor (lite content map)
AREA_FACTION_HINT: Dict[str, str] = {
    "dark_forest": FACTION_ECHO,
    "mist_marsh": FACTION_INFERNAL,
    "ancient_city": FACTION_DIVINE,
    "crystal_peak": FACTION_DIVINE,
    "void_rift": FACTION_ECHO,
    "cave_shadow": FACTION_INFERNAL,
    # WO-044 full map lean
    "mountain_rock": FACTION_DIVINE,
    "desert_heat": FACTION_ECHO,
}

# NPC archetype → faction lean
ARCHETYPE_FACTION: Dict[str, str] = {
    "priest": FACTION_DIVINE,
    "monk": FACTION_DIVINE,
    "sage": FACTION_DIVINE,
    "merchant": FACTION_DIVINE,
    "cultist": FACTION_INFERNAL,
    "witch": FACTION_INFERNAL,
    "bandit": FACTION_INFERNAL,
    "wanderer": FACTION_ECHO,
    "hermit": FACTION_ECHO,
    "scholar": FACTION_ECHO,
}


def ensure_world_relations(player: MutableMapping[str, Any]) -> None:
    from game.domain.stat_arch import ensure_stat_arch

    ensure_stat_arch(player)
    wr = dict(player.get("world_relations") or {})
    # seed faction baselines once
    if not player.get("_wr_seeded"):
        for fid in FACTION_META:
            k = f"faction:{fid}"
            wr.setdefault(k, 42)  # neutral-ish
        player["world_relations"] = wr
        player["_wr_seeded"] = True
    else:
        player.setdefault("world_relations", wr)


def get_faction_score(player: Mapping[str, Any], faction_id: str) -> int:
    from game.domain.stat_arch import get_world_relation

    return int(get_world_relation(player, "faction", faction_id, default=42))


def soft_faction_label(score: int) -> str:
    from game.domain.stat_arch import soft_relation_label

    return soft_relation_label(score)


def adjust_faction(
    player: MutableMapping[str, Any],
    faction_id: str,
    delta: float,
    *,
    reason: str = "",
    force_alert: bool = False,
) -> List[str]:
    """
    Change faction score + Soft Alert (throttled).
    Returns display lines (may be empty if throttled / no change).
    """
    ensure_world_relations(player)
    if faction_id not in FACTION_META:
        return []
    from game.domain.stat_arch import get_world_relation, set_world_relation

    before = get_world_relation(player, "faction", faction_id, default=42)
    after = set_world_relation(
        player, "faction", faction_id, int(round(before + delta))
    )
    if after == before and not force_alert:
        return []

    meta = FACTION_META[faction_id]
    rising = after > before
    code = meta["warm_alert"] if rising else meta["cold_alert"]
    lines: List[str] = []
    try:
        from game.domain.alerts import emit_alert_lines

        lines = emit_alert_lines(
            player,
            code,
            force=force_alert,
            item=meta["label_th"],
            band=soft_faction_label(after),
        )
    except Exception:
        lines = [f"  · {meta['presence']}"]

    # WO-053: personal journal faction gaze
    try:
        from game.domain.personal_system import note_faction_story

        # only when score crosses soft band meaningfully
        if abs(after - before) >= 3 or force_alert:
            note_faction_story(player, faction_id, warm=rising)
    except Exception:
        pass

    # soft anima / morale nudge (no numbers)
    if rising and faction_id == FACTION_DIVINE and delta > 0:
        try:
            from game.domain.stat_arch import anima_presence_lines

            lines.extend(
                anima_presence_lines(player, "learn_glow", force=False)
            )
        except Exception:
            pass
        # tiny anima nudge
        try:
            from game.domain.stat_arch import ANIMA_KEY, anima_value

            player[ANIMA_KEY] = min(99.0, anima_value(player) + min(1.2, abs(delta) * 0.15))
            player["_anima_presence_felt"] = True
        except Exception:
            pass
    if (not rising) and faction_id == FACTION_INFERNAL and after < 35:
        try:
            from game.domain.needs import ensure_needs, get_needs

            ensure_needs(player)
            n = get_needs(player)
            # soft morale pinch (1 pt) rarely
            if int(n.get("morale") or 50) > 15 and abs(delta) >= 2:
                n["morale"] = max(0, int(n["morale"]) - 1)
                player["needs"] = n
        except Exception:
            pass

    player["_wr_last_faction"] = faction_id
    player["_wr_last_score"] = after
    return lines


def faction_for_area(area_id: str) -> str:
    return AREA_FACTION_HINT.get(str(area_id or ""), FACTION_ECHO)


def faction_for_archetype(arch: str) -> str:
    a = str(arch or "").lower()
    if a in ARCHETYPE_FACTION:
        return ARCHETYPE_FACTION[a]
    if any(x in a for x in ("priest", "holy", "heaven", "sage")):
        return FACTION_DIVINE
    if any(x in a for x in ("hell", "cult", "dark", "bandit", "witch")):
        return FACTION_INFERNAL
    return FACTION_ECHO


def on_npc_outcome(
    player: MutableMapping[str, Any],
    *,
    outcome: str,
    archetype: str = "",
    area_id: str = "",
) -> List[str]:
    """Hook after NPC approach resolve."""
    ensure_world_relations(player)
    fac = faction_for_archetype(archetype) if archetype else faction_for_area(area_id)
    oc = str(outcome or "").lower()
    delta = 0.0
    if oc in ("friend", "shop", "master", "help", "gift"):
        delta = 4.0 if oc == "friend" else 2.5
    elif oc in ("hostile", "attack", "flee_bad"):
        delta = -5.0
    elif oc in ("ignore", "leave"):
        delta = -0.5
    else:
        delta = 1.0
    lines = adjust_faction(player, fac, delta, reason=f"npc:{oc}")
    if delta >= 2 and lines:
        # extra soft moment line (natural)
        if fac == FACTION_DIVINE:
            lines.append("  …จิตวิญญาณของคุณอบอุ่นขึ้นเล็กน้อย")
        elif fac == FACTION_ECHO:
            lines.append("  …เงาโบราณยอมรับการมีอยู่ของคุณชั่วขณะ")
    return lines


def on_echo_approach(
    player: MutableMapping[str, Any],
    *,
    choice: str = "neutral",
) -> List[str]:
    """Player-echo social soft → ancient_echo faction."""
    ensure_world_relations(player)
    c = str(choice or "neutral").lower()
    if c in ("humble", "polite", "retreat"):
        return adjust_faction(player, FACTION_ECHO, 3.0, reason="echo_humble")
    if c in ("aggro", "hostile", "attack"):
        return adjust_faction(player, FACTION_ECHO, -4.0, reason="echo_aggro")
    return adjust_faction(player, FACTION_ECHO, 0.5, reason="echo_neutral")


def on_chamber_enter(player: MutableMapping[str, Any]) -> List[str]:
    """Godforge feels divine-leaning soft presence."""
    ensure_world_relations(player)
    lines = adjust_faction(player, FACTION_DIVINE, 1.0, reason="chamber")
    if not lines:
        try:
            from game.domain.alerts import emit_alert_lines

            lines = emit_alert_lines(player, "world.chamber_hush")
        except Exception:
            lines = ["  · ห้องเงียบ — มีสายตาจากที่สูง…"]
    return lines


def on_relic_theme(
    player: MutableMapping[str, Any],
    *,
    item_id: str = "",
    tags: Optional[List[str]] = None,
    rarity_id: str = "",
) -> List[str]:
    """Equip relic soft-tags lean divine/infernal/echo."""
    ensure_world_relations(player)
    tags_l = [str(t).lower() for t in (tags or [])]
    iid = str(item_id or "").lower()
    fac = FACTION_ECHO
    if any(t in tags_l for t in ("holy", "storm", "heaven", "light", "sacred")) or "storm" in iid:
        fac = FACTION_DIVINE
    elif any(t in tags_l for t in ("hell", "dark", "void", "shadow", "curse")) or "hell" in iid or "void" in iid:
        fac = FACTION_INFERNAL
    return adjust_faction(player, fac, 1.5, reason="relic")


def world_relation_needs_mults(player: Mapping[str, Any]) -> Dict[str, float]:
    """
    Soft mults for needs events (morale drain).
    divine high → slower morale loss; infernal low (hostile) → faster.
    """
    ensure_world_relations(player)  # type: ignore[arg-type]
    d = get_faction_score(player, FACTION_DIVINE)
    inf = get_faction_score(player, FACTION_INFERNAL)
    morale_drain = 1.0
    if d >= 65:
        morale_drain *= 0.88
    elif d >= 50:
        morale_drain *= 0.95
    if inf <= 30:
        morale_drain *= 1.10
    elif inf <= 40:
        morale_drain *= 1.04
    # anima recover soft when divine warm
    anima_nudge = 0.0
    if d >= 70:
        anima_nudge = 0.08
    return {
        "morale_drain_mult": max(0.75, min(1.25, morale_drain)),
        "divine_anima_nudge": anima_nudge,
    }


def soft_world_presence_line(player: Mapping[str, Any], area_id: str = "") -> str:
    """One soft line for field hub (optional)."""
    ensure_world_relations(player)  # type: ignore[arg-type]
    fac = faction_for_area(area_id)
    sc = get_faction_score(player, fac)
    lab = soft_faction_label(sc)
    meta = FACTION_META.get(fac) or {}
    name = meta.get("label_th") or fac
    if sc >= 65:
        return f" โลก · {name} 〔{lab}〕 — รู้สึกต้อนรับเบา ๆ"
    if sc <= 30:
        return f" โลก · {name} 〔{lab}〕 — อากาศกดเล็กน้อย"
    return f" โลก · {name} 〔{lab}〕"


def format_world_relations_soft(player: Mapping[str, Any]) -> List[str]:
    """Soft summary for assess / hub (no numbers)."""
    ensure_world_relations(player)  # type: ignore[arg-type]
    lines = [" ④ ความสัมพันธ์โลก (soft)", "---"]
    for fid, meta in FACTION_META.items():
        sc = get_faction_score(player, fid)
        lines.append(f"  · {meta['label_th']:<14} 〔{soft_faction_label(sc)}〕")
    lines.append(" · ไม่โชว์คะแนนดิบ · เปลี่ยนจากคุย NPC / echo / เรลิก / ห้อง G")
    return lines
