"""
WO-040–043 Anima × Relic · Soft Bonds · Soft Chorus.
WO-046 Relic × Moment / Area Soft Synergy Lite.

Relics lean faction and breathe into Anima.
2 same lean → Resonance · 3+ same lean → Soft Chorus · mixed → Tension.
Soft Cap when chorus stacks hard (prevent runaway feel).
Relic lean match area → resonate (moment chance + anima clear).
Relic lean clash area → soft tension with the world.
No new resources · Soft Alert + presence only.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry
from game.domain.world_relations import (
    FACTION_DIVINE,
    FACTION_ECHO,
    FACTION_INFERNAL,
)

# WO-046: relic lean vs area lean
SYN_NONE = "none"
SYN_RESONATE = "resonate"
SYN_AREA_TENSION = "area_tension"

# item_id / tag → faction lean
_RELIC_ID_LEAN: Dict[str, str] = {
    "relic_storm_fang": FACTION_DIVINE,
    "relic_aegis_sky": FACTION_DIVINE,
    "relic_hell_ember_blade": FACTION_INFERNAL,
    "relic_void_whisper_ring": FACTION_ECHO,  # void whisper → echo/ancient
    # WO-042 bond pairs
    "relic_hell_brand_charm": FACTION_INFERNAL,
    "relic_echo_shroud": FACTION_ECHO,
    # WO-043 third pieces (enable Soft Chorus)
    "relic_divine_laurel": FACTION_DIVINE,
    "relic_god_eye": FACTION_DIVINE,
    "relic_hell_ash_greaves": FACTION_INFERNAL,
    "relic_echo_sandals": FACTION_ECHO,
}

_DIVINE_TAGS = frozenset({"holy", "storm", "heaven", "light", "sacred", "sky"})
_INFERNAL_TAGS = frozenset({"hell", "fire", "dark", "curse", "blood"})
_ECHO_TAGS = frozenset({"shadow", "void", "arcane", "ancient", "echo"})

# Bond modes
BOND_NONE = "none"
BOND_RESONANCE = "resonance"  # exactly 2 same lean
BOND_CHORUS = "chorus"  # 3+ same lean (WO-043)
BOND_TENSION = "tension"

CHORUS_MIN = 3
# Soft Cap: at 4+ pieces same lean, add light pressure (feel heavy, not numbers)
SOFT_CAP_COUNT = 4

def resolve_relic_faction(
    item_id: str = "",
    tags: Optional[List[str]] = None,
    reg: Optional[DataRegistry] = None,
) -> str:
    """Return divine | infernal | ancient_echo for a relic."""
    iid = str(item_id or "")
    if iid in _RELIC_ID_LEAN:
        return _RELIC_ID_LEAN[iid]
    tags_l = {str(t).lower() for t in (tags or [])}
    if reg is not None and iid:
        it = (reg.items or {}).get(iid) or {}
        tags_l |= {str(t).lower() for t in (it.get("tags") or [])}
        # material hint
        mat = str(it.get("material") or "").lower()
        if mat in ("storm", "skysteel"):
            return FACTION_DIVINE
        if mat in ("hellsteel",):
            return FACTION_INFERNAL
        if mat in ("void",):
            return FACTION_ECHO
    if tags_l & _DIVINE_TAGS:
        return FACTION_DIVINE
    if tags_l & _INFERNAL_TAGS:
        return FACTION_INFERNAL
    if tags_l & _ECHO_TAGS:
        return FACTION_ECHO
    if "storm" in iid or "sky" in iid or "aegis" in iid:
        return FACTION_DIVINE
    if "hell" in iid:
        return FACTION_INFERNAL
    if "void" in iid:
        return FACTION_ECHO
    return FACTION_ECHO


def _is_relic_class(item: Mapping[str, Any], item_id: str = "") -> bool:
    """True if item participates in lean / soft bonds."""
    if item.get("divine_burden") or item.get("chamber_relic") or item.get("force_burden"):
        return True
    rar = str(item.get("rarity") or "")
    if rar in ("legendary", "divine", "mythic"):
        return True
    iid = str(item_id or "")
    if iid.startswith("relic_") or iid in _RELIC_ID_LEAN:
        return True
    kind = str(item.get("kind") or "")
    return kind == "relic"


def equipped_relic_leans(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Tuple[str, str, str]]:
    """
    List (slot, item_id, faction) for equipped relic-class pieces.
    WO-041: include all divine_burden / legendary equipped, not only burden-strain.
    """
    out: List[Tuple[str, str, str]] = []
    seen_slots: set = set()

    # Primary: scan equip_ids for relic-class (bonds need multi-slot)
    for slot, iid in (player.get("equip_ids") or {}).items():
        if not iid:
            continue
        it = (reg.items or {}).get(str(iid)) or {}
        # inventory rarity may outrank yaml
        rar_map = player.get("equip_rarities") or {}
        rar = str(rar_map.get(str(slot)) or it.get("rarity") or "")
        if rar in ("legendary", "divine", "mythic"):
            pass  # relic-class by rarity
        elif not _is_relic_class(it, str(iid)):
            continue
        fac = resolve_relic_faction(str(iid), list(it.get("tags") or []), reg)
        out.append((str(slot), str(iid), fac))
        seen_slots.add(str(slot))

    # Also pick up burden pieces missed (e.g. force_burden commons)
    try:
        from game.domain.divine_burden import equipped_burden_pieces

        for p in equipped_burden_pieces(player, reg):
            slot = str(p.get("slot") or "")
            if slot in seen_slots:
                continue
            iid = str(p.get("item_id") or p.get("id") or "")
            if not iid:
                continue
            fac = resolve_relic_faction(iid, reg=reg)
            out.append((slot, iid, fac))
            seen_slots.add(slot)
    except Exception:
        pass
    return out


def primary_relic_faction(player: Mapping[str, Any], reg: DataRegistry) -> Optional[str]:
    leans = equipped_relic_leans(player, reg)
    if not leans:
        return None
    # prefer majority lean, else first
    counts: Dict[str, int] = {}
    for _, _, fac in leans:
        counts[fac] = counts.get(fac, 0) + 1
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def evaluate_relic_bonds(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> Dict[str, Any]:
    """
    WO-041/043: evaluate soft bond state from equipped relic leans.

    Returns:
      mode: none | resonance | chorus | tension
      faction: primary lean or None
      count: pieces in majority lean
      factions: sorted unique leans
      size: total relic pieces
      soft_cap: True when chorus stacks hard (4+ or cap pressure)
    """
    leans = equipped_relic_leans(player, reg)
    if len(leans) < 2:
        return {
            "mode": BOND_NONE,
            "faction": leans[0][2] if leans else None,
            "count": len(leans),
            "factions": [leans[0][2]] if leans else [],
            "size": len(leans),
            "soft_cap": False,
        }
    counts: Dict[str, int] = {}
    for _, _, fac in leans:
        counts[fac] = counts.get(fac, 0) + 1
    unique = sorted(counts.keys())
    max_c = max(counts.values())
    majority = [f for f, c in counts.items() if c == max_c]

    # pure single-faction stack
    if len(unique) == 1 and max_c >= 2:
        fac = unique[0]
        soft_cap = max_c >= SOFT_CAP_COUNT
        if max_c >= CHORUS_MIN:
            return {
                "mode": BOND_CHORUS,
                "faction": fac,
                "count": max_c,
                "factions": unique,
                "size": len(leans),
                "soft_cap": soft_cap,
            }
        return {
            "mode": BOND_RESONANCE,
            "faction": fac,
            "count": max_c,
            "factions": unique,
            "size": len(leans),
            "soft_cap": False,
        }
    # multi-faction mix → tension
    if len(unique) >= 2:
        return {
            "mode": BOND_TENSION,
            "faction": majority[0] if majority else None,
            "count": max_c,
            "factions": unique,
            "size": len(leans),
            "pair": sorted(unique),
            "soft_cap": False,
        }
    return {
        "mode": BOND_NONE,
        "faction": majority[0] if majority else None,
        "count": max_c,
        "factions": unique,
        "size": len(leans),
        "soft_cap": False,
    }


def sync_bond_state(player: MutableMapping[str, Any], reg: DataRegistry) -> Dict[str, Any]:
    """Cache bond evaluation on player for ticks / auto."""
    prev_mode = str(player.get("_relic_bond_mode") or BOND_NONE)
    bond = evaluate_relic_bonds(player, reg)
    player["_relic_bond_mode"] = bond.get("mode") or BOND_NONE
    player["_relic_bond_faction"] = bond.get("faction")
    player["_relic_bond_count"] = int(bond.get("count") or 0)
    player["_relic_bond_factions"] = list(bond.get("factions") or [])
    player["_relic_bond_soft_cap"] = bool(bond.get("soft_cap"))
    # WO-053: journal when bond mode changes to meaningful state
    try:
        mode = str(bond.get("mode") or BOND_NONE)
        if mode != prev_mode and mode in (BOND_RESONANCE, BOND_CHORUS, BOND_TENSION):
            from game.domain.personal_system import note_bond_story

            note_bond_story(player, mode, str(bond.get("faction") or ""))
    except Exception:
        pass
    return bond


def _apply_soft_cap_edge(
    player: MutableMapping[str, Any],
    *,
    n: int,
    force_lines: bool = True,
) -> List[str]:
    """
    WO-043 Soft Cap: when stack hard, light anima waver + morale pinch.
    Not a hard block — feel of weight / over-resonance.
    """
    lines: List[str] = []
    if n < SOFT_CAP_COUNT:
        return lines
    from game.domain.stat_arch import ANIMA_KEY, anima_value, ensure_stat_arch

    ensure_stat_arch(player)
    a = anima_value(player)
    # WO-047: Soft Cap feel medium — pull center a bit clearer, not punishing
    if a > 70:
        player[ANIMA_KEY] = max(5.0, a - 0.55)
    elif a < 30:
        player[ANIMA_KEY] = min(99.0, a + 0.3)
    else:
        player[ANIMA_KEY] = max(5.0, a - 0.28)
    try:
        from game.domain.needs import ensure_needs, get_needs

        ensure_needs(player)
        needs = get_needs(player)
        mor = int(needs.get("morale") or 50)
        # only pinch if morale still comfortable (avoid double-punish low)
        if mor > 28:
            needs["morale"] = max(0, mor - 1)
            player["needs"] = needs
    except Exception:
        pass
    if force_lines:
        # WO-045/047: Soft Cap alert throttled
        try:
            from game.domain.alerts import emit_alert_lines

            lines.extend(
                emit_alert_lines(
                    player, "anima.bond_soft_cap", force=False, count=str(n)
                )
            )
        except Exception:
            if not player.get("_relic_soft_cap_felt"):
                lines.append(
                    "  Soft Cap · คณะเรลิกหนา — จิตสั่น · ขวัญกดแผ่ว "
                    "(ไม่ล็อก · ถอดชิ้นหนึ่งแล้วนิ่มขึ้น)"
                )
    player["_relic_soft_cap_felt"] = True
    return lines


def on_relic_bond_pulse(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    force: bool = False,
    context: str = "equip",
) -> List[str]:
    """
    WO-041/043: Soft Bond / Chorus / Tension pulse after equip or when asked.
    Throttled unless force=True (equip path uses force when bond newly forms).
    """
    from game.domain.stat_arch import ANIMA_KEY, anima_value, ensure_stat_arch

    ensure_stat_arch(player)
    bond = sync_bond_state(player, reg)
    mode = str(bond.get("mode") or BOND_NONE)
    lines: List[str] = []

    prev = str(player.get("_relic_bond_announced") or "")
    sig = (
        f"{mode}:{bond.get('faction')}:{bond.get('count')}:"
        f"{int(bool(bond.get('soft_cap')))}:{','.join(bond.get('factions') or [])}"
    )
    if not force and prev == sig and context == "equip":
        return []
    # soft throttle on non-equip
    if not force and context != "equip":
        last = int(player.get("_relic_bond_pulse_tick") or -99)
        tick = int(player.get("auto_ticks") or player.get("time_units") or 0)
        if tick - last < 3 and prev == sig:
            return []

    if mode == BOND_CHORUS:
        fac = str(bond.get("faction") or FACTION_ECHO)
        n = int(bond.get("count") or 3)
        a = anima_value(player)
        if fac == FACTION_DIVINE:
            # warmer than resonance, soft-capped gain
            gain = 2.4 if n < SOFT_CAP_COUNT else 1.6
            player[ANIMA_KEY] = min(99.0, a + gain)
            code = "anima.chorus_divine"
            flavor = (
                "  Soft Chorus · สายตาเทพจับจ้องอย่างอบอุ่นลึกซึ้ง · "
                "จิตอุ่นแรง · ขวัญลดช้า"
            )
        elif fac == FACTION_INFERNAL:
            # plate but stable heat
            delta = -0.35 if n < SOFT_CAP_COUNT else -0.55
            player[ANIMA_KEY] = max(5.0, a + delta)
            code = "anima.chorus_infernal"
            flavor = (
                "  Soft Chorus · พลังมารแผ่ซ่านอย่างมั่นคง · "
                "จิตแผ่วแต่แข็งแกร่ง · ขวัญกดปานกลาง"
            )
        else:
            gain = 1.1 if n < SOFT_CAP_COUNT else 0.55
            player[ANIMA_KEY] = max(5.0, min(99.0, a + gain))
            code = "anima.chorus_echo"
            flavor = (
                "  Soft Chorus · จิตสั่นไหวแต่เชื่อมโยง · "
                "เงาก้องซ้อน · กระซิบหนาขึ้น"
            )
        player["_anima_presence_felt"] = True
        try:
            from game.domain.alerts import emit_alert_lines
            from game.domain.world_relations import adjust_faction

            lines.extend(
                emit_alert_lines(player, code, force=True, count=str(n), band=fac)
            )
            # chorus faction boost — soft capped at 4+
            boost = 2.2 + 0.35 * max(0, n - CHORUS_MIN)
            if bond.get("soft_cap"):
                boost = min(boost, 2.6)
            lines.extend(
                adjust_faction(player, fac, boost, reason=f"relic_chorus:{fac}")
            )
        except Exception:
            lines.append(flavor)
        if flavor not in "\n".join(lines):
            lines.append(flavor)
        if bond.get("soft_cap"):
            lines.extend(_apply_soft_cap_edge(player, n=n, force_lines=True))

    elif mode == BOND_RESONANCE:
        fac = str(bond.get("faction") or FACTION_ECHO)
        n = int(bond.get("count") or 2)
        a = anima_value(player)
        if fac == FACTION_DIVINE:
            player[ANIMA_KEY] = min(99.0, a + 1.8)
            code = "anima.bond_divine"
            flavor = "  เรลิกเรโซแนนซ์ · สายตาเทพจับจ้องอย่างอบอุ่น · จิตวิญญาณอุ่นลึก"
        elif fac == FACTION_INFERNAL:
            player[ANIMA_KEY] = max(5.0, a - 0.6)
            code = "anima.bond_infernal"
            flavor = "  เรลิกเรโซแนนซ์ · พลังมารแผ่ซ่านอย่างคุ้นเคย · จิตแผ่วแต่ทนขึ้น"
        else:
            player[ANIMA_KEY] = max(5.0, min(99.0, a + 0.7))
            code = "anima.bond_echo"
            flavor = "  เรลิกเรโซแนนซ์ · จิตสั่นเป็นจังหวะ · เงาโบราณพยัก"
        player["_anima_presence_felt"] = True
        try:
            from game.domain.alerts import emit_alert_lines
            from game.domain.world_relations import adjust_faction

            lines.extend(
                emit_alert_lines(player, code, force=True, count=str(n), band=fac)
            )
            boost = 1.5 + 0.4 * max(0, n - 2)
            lines.extend(
                adjust_faction(player, fac, boost, reason=f"relic_bond:{fac}")
            )
        except Exception:
            lines.append(flavor)
        if flavor not in "\n".join(lines):
            lines.append(flavor)

    elif mode == BOND_TENSION:
        a = anima_value(player)
        player[ANIMA_KEY] = max(5.0, a - 0.9)
        player["_anima_presence_felt"] = True
        factions = list(bond.get("factions") or [])
        lab = " × ".join(factions) if factions else "ขัด lean"
        try:
            from game.domain.alerts import emit_alert_lines

            lines.extend(
                emit_alert_lines(
                    player,
                    "anima.bond_tension",
                    force=True,
                    band=lab,
                    item=lab,
                )
            )
        except Exception:
            lines.append(f"  เรลิกขัด lean ({lab}) — จิตแผ่ว · ขวัญกดเร็วขึ้นเล็กน้อย")
        flavor = f"  Soft Tension · {lab} — พลังสองสายดึงกันในอก"
        if flavor not in "\n".join(lines):
            lines.append(flavor)

    player["_relic_bond_announced"] = sig
    player["_relic_bond_pulse_tick"] = int(
        player.get("auto_ticks") or player.get("time_units") or 0
    )
    return lines

def on_relic_equip_depth(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    item_id: str,
    item_name: str = "",
    tags: Optional[List[str]] = None,
) -> List[str]:
    """
    WO-040.1: deeper equip — faction lean + anima nudge + Soft Alert by lean.
    WO-041: after single-lean note, pulse Soft Bond / Tension if multi-relic.
    """
    from game.domain.stat_arch import ANIMA_KEY, anima_value, ensure_stat_arch
    from game.domain.world_relations import adjust_faction

    ensure_stat_arch(player)
    fac = resolve_relic_faction(item_id, tags, reg)
    name = item_name or "เรลิก"
    lines: List[str] = []

    # store active lean for ticks / explore
    player["_relic_faction_lean"] = fac
    player["_relic_depth_item"] = str(item_id)

    # faction soft (slightly stronger than lite theme)
    lines.extend(adjust_faction(player, fac, 2.0, reason=f"relic_depth:{item_id}"))

    # anima by lean
    a = anima_value(player)
    if fac == FACTION_DIVINE:
        player[ANIMA_KEY] = min(99.0, a + 1.4)
        code = "anima.relic_divine"
        flavor = "  พลังเรลิกแผ่ซ่าน — รู้สึกหนักแต่ลึกซึ้ง · จิตวิญญาณอุ่นขึ้น"
    elif fac == FACTION_INFERNAL:
        player[ANIMA_KEY] = max(5.0, a - 1.1)
        code = "anima.relic_infernal"
        flavor = "  ความร้อน/เงามารเกาะจิต — จิตวิญญาณแผ่ว · ขวัญอาจร่วงเร็ว"
    else:
        # echo: oscillate / tremble
        player[ANIMA_KEY] = max(5.0, min(99.0, a + 0.35))
        code = "anima.relic_echo"
        flavor = "  เรลิกกระซิบ — จิตวิญญาณสั่นไหว · มีโอกาสเจอสายตาเงา"

    player["_anima_presence_felt"] = True
    # WO-045: if multi-relic bond/chorus will speak, keep lean anima only + short alert
    # (avoid double wall of flavor + bond text)
    multi = len(equipped_relic_leans(player, reg)) >= 2
    try:
        from game.domain.alerts import emit_alert_lines

        lines.extend(
            emit_alert_lines(
                player, code, force=not multi, item=name, band=fac
            )
        )
    except Exception:
        if not multi:
            lines.append(flavor)
    if not multi and flavor not in "\n".join(lines):
        lines.append(flavor)
    elif multi and not lines:
        lines.append(f"  「{name}」เข้าชุดเรลิก — จิตรับ lean {fac}")

    # WO-041: multi-relic bond / tension (equip already applied on player)
    lines.extend(on_relic_bond_pulse(player, reg, force=True, context="equip"))
    return lines


def evaluate_relic_area_synergy(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    area_id: str = "",
) -> Dict[str, Any]:
    """
    WO-046: compare equipped relic primary lean vs area faction lean.

    Returns:
      mode: none | resonate | area_tension
      relic_faction / area_faction
    """
    aid = str(area_id or player.get("location") or "")
    try:
        from game.domain.world_relations import faction_for_area

        area_fac = str(faction_for_area(aid) or FACTION_ECHO)
    except Exception:
        area_fac = FACTION_ECHO
    relic_fac = primary_relic_faction(player, reg)
    if not relic_fac or not equipped_relic_leans(player, reg):
        return {
            "mode": SYN_NONE,
            "relic_faction": relic_fac,
            "area_faction": area_fac,
            "area_id": aid,
        }
    if str(relic_fac) == str(area_fac):
        mode = SYN_RESONATE
    else:
        mode = SYN_AREA_TENSION
    return {
        "mode": mode,
        "relic_faction": str(relic_fac),
        "area_faction": area_fac,
        "area_id": aid,
    }


def moment_chance_factor(
    player: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
    *,
    area_id: str = "",
) -> float:
    """WO-046: mult for Mini-Moment roll (resonate >1, area tension slightly <1)."""
    if reg is None:
        try:
            from game.data_load.registry import get_registry

            reg = get_registry()
        except Exception:
            reg = None
    if reg is None:
        return 1.0
    syn = evaluate_relic_area_synergy(player, reg, area_id=area_id)
    mode = str(syn.get("mode") or SYN_NONE)
    if mode == SYN_RESONATE:
        # bond/chorus slightly stronger pull
        bond = evaluate_relic_bonds(player, reg)
        bm = str(bond.get("mode") or BOND_NONE)
        if bm == BOND_CHORUS:
            return 1.42
        if bm == BOND_RESONANCE:
            return 1.35
        return 1.28
    if mode == SYN_AREA_TENSION:
        return 0.88
    return 1.0


def prefer_moment_faction_for_synergy(
    player: Mapping[str, Any],
    reg: Optional[DataRegistry],
    pool: List[Dict[str, Any]],
    *,
    area_id: str = "",
) -> List[Dict[str, Any]]:
    """When resonate, bias pool toward moments of matching faction."""
    if not pool or reg is None:
        return pool
    syn = evaluate_relic_area_synergy(player, reg, area_id=area_id)
    if str(syn.get("mode")) != SYN_RESONATE:
        return pool
    fac = str(syn.get("relic_faction") or "")
    matched = [m for m in pool if str(m.get("faction") or "") == fac]
    return matched or pool


def apply_moment_synergy_nudge(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry],
    *,
    moment_faction: str,
    anima_nudge: float,
    area_id: str = "",
) -> Tuple[float, List[str]]:
    """
    WO-046: scale anima nudge when relic lean matches moment/area.
    Returns (scaled_nudge, soft_lines).
    """
    lines: List[str] = []
    an = float(anima_nudge)
    if reg is None or abs(an) < 0.01:
        return an, lines
    syn = evaluate_relic_area_synergy(player, reg, area_id=area_id)
    mode = str(syn.get("mode") or SYN_NONE)
    rfac = str(syn.get("relic_faction") or "")
    mfac = str(moment_faction or "")
    if mode == SYN_RESONATE and rfac and rfac == mfac:
        an = an * 1.35
        try:
            from game.domain.alerts import emit_alert_lines

            lines.extend(
                emit_alert_lines(
                    player, "world.synergy_moment_resonate", force=False, band=rfac
                )
            )
        except Exception:
            lines.append("  เรลิกสะท้อนกะช่วงเวลานี้ — จิตวิญญาณชัดขึ้น")
    elif mode == SYN_AREA_TENSION:
        # world clashes — anima effects slightly harsher if negative, weaker if positive
        if an > 0:
            an = an * 0.75
        else:
            an = an * 1.15
        try:
            from game.domain.alerts import emit_alert_lines

            lines.extend(
                emit_alert_lines(
                    player, "world.synergy_moment_tension", force=False, band=rfac
                )
            )
        except Exception:
            pass
    return an, lines


def relic_area_synergy_morale_factor(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    area_id: str = "",
) -> float:
    """
    Extra morale drain mult from area clash / slight ease on resonate.
    WO-047 feel polish: tension slightly clearer (1.09), resonate ease soft (0.96).
    """
    syn = evaluate_relic_area_synergy(player, reg, area_id=area_id)
    mode = str(syn.get("mode") or SYN_NONE)
    if mode == SYN_AREA_TENSION:
        return 1.09
    if mode == SYN_RESONATE:
        return 0.96
    return 1.0


def relic_equipped_morale_mult(player: Mapping[str, Any], reg: DataRegistry) -> float:
    """
    While wearing relic: divine slows morale drain, infernal speeds it.
    WO-041: Soft Bond deepens effect; Soft Tension accelerates drain.
    WO-043: Soft Chorus deeper; Soft Cap adds light pressure (not runaway).
    WO-046: × area synergy factor (resonate ease / area tension press).
    Stacks softly with anima_morale_drain_factor (caller multiplies).
    """
    bond = evaluate_relic_bonds(player, reg)
    mode = str(bond.get("mode") or BOND_NONE)
    n = int(bond.get("count") or 0)
    soft_cap = bool(bond.get("soft_cap"))

    if mode == BOND_TENSION:
        base = 1.16
    elif mode == BOND_CHORUS:
        fac = str(bond.get("faction") or "")
        if fac == FACTION_DIVINE:
            mult = 0.80 if n >= 4 else 0.82
            base = 0.86 if soft_cap and mult < 0.84 else mult
        elif fac == FACTION_INFERNAL:
            base = 1.10 if soft_cap else 1.07
        else:
            base = 1.06 if soft_cap else 1.05
    elif mode == BOND_RESONANCE:
        fac = str(bond.get("faction") or "")
        extra = min(0.06, 0.02 * max(0, n - 2))
        if fac == FACTION_DIVINE:
            base = max(0.78, 0.84 - extra)
        elif fac == FACTION_INFERNAL:
            base = 1.08 + extra * 0.5
        else:
            base = 1.04
    else:
        fac = primary_relic_faction(player, reg)
        if not fac:
            return 1.0
        if fac == FACTION_DIVINE:
            base = 0.88
        elif fac == FACTION_INFERNAL:
            base = 1.12
        else:
            base = 1.03

    try:
        base = float(base) * float(
            relic_area_synergy_morale_factor(player, reg)
        )
    except Exception:
        pass
    return base


def synergy_foresight_lines(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    area_id: str = "",
    brief: bool = False,
) -> List[str]:
    """WO-046 Soft Foresight lines for relic×area synergy."""
    syn = evaluate_relic_area_synergy(player, reg, area_id=area_id)
    mode = str(syn.get("mode") or SYN_NONE)
    if mode == SYN_NONE:
        return []
    lines: List[str] = []
    rfac = str(syn.get("relic_faction") or "")
    afac = str(syn.get("area_faction") or "")
    if mode == SYN_RESONATE:
        if brief:
            # WO-047: warmer, less jargon
            lines.append("  …เรลิกกับพื้นที่มีจังหวะเดียวกัน — จิตอุ่น/สั่นชัดขึ้นได้")
        else:
            try:
                from game.domain.alerts import emit_alert_lines

                lines.extend(
                    emit_alert_lines(
                        player,  # type: ignore[arg-type]
                        "world.synergy_resonate",
                        force=False,
                        band=rfac,
                    )
                )
            except Exception:
                lines.append(
                    "  เรลิกของคุณสะท้อนกะพื้นที่นี้ — "
                    "Mini-Moment อาจชัด · จิตวิญญาณรู้สึกได้มากขึ้น"
                )
            if not any("สะท้อน" in str(x) or "จังหวะ" in str(x) for x in lines):
                lines.append(
                    "  เรลิกกับโลกมีจังหวะเดียวกัน — moment ตรง lean อาจโผล่ง่ายขึ้น"
                )
    else:
        if brief:
            lines.append("  …เรลิกกับโลกดึงคนละทาง — ขวัญอาจร่วงเร็วขึ้นเล็กน้อย")
        else:
            try:
                from game.domain.alerts import emit_alert_lines

                lines.extend(
                    emit_alert_lines(
                        player,  # type: ignore[arg-type]
                        "world.synergy_tension",
                        force=False,
                        band=rfac,
                    )
                )
            except Exception:
                lines.append(
                    "  เรลิกกับพื้นที่นี้ไม่เข้ากัน — "
                    "ขวัญกดเร็วขึ้นเล็กน้อย · จิตอาจแผ่ว"
                )
            if not any("ขัด" in str(x) or "ดึง" in str(x) or "ไม่เข้า" in str(x) for x in lines):
                lines.append(
                    "  Soft Tension กับโลก — ถอดเรลิกหรือย้ายพื้นที่แล้วขวัญอาจนิ่งขึ้น"
                )
    return lines


def try_area_synergy_presence_pulse(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    area_id: str = "",
    force: bool = False,
) -> List[str]:
    """
    Soft Anima presence when exploring with resonate/tension (throttled).
    WO-047: slightly more present (throttle 3 · nudge clearer · band soft note).
    """
    syn = evaluate_relic_area_synergy(player, reg, area_id=area_id)
    mode = str(syn.get("mode") or SYN_NONE)
    if mode == SYN_NONE:
        return []
    tick = int(player.get("auto_ticks") or player.get("time_units") or 0)
    last = int(player.get("_synergy_presence_tick") or -99)
    if not force and tick - last < 3:
        return []
    from game.domain.stat_arch import (
        ANIMA_KEY,
        anima_band,
        anima_presence_lines,
        anima_value,
        ensure_stat_arch,
    )

    ensure_stat_arch(player)
    a = anima_value(player)
    fac = str(syn.get("relic_faction") or FACTION_ECHO)
    lines: List[str] = []
    if mode == SYN_RESONATE:
        if fac == FACTION_DIVINE:
            player[ANIMA_KEY] = min(99.0, a + 0.75)
        elif fac == FACTION_INFERNAL:
            player[ANIMA_KEY] = max(5.0, a - 0.35)
        else:
            player[ANIMA_KEY] = max(5.0, min(99.0, a + 0.5))
        player["_anima_presence_felt"] = True
        try:
            from game.domain.alerts import emit_alert_lines

            lines.extend(
                emit_alert_lines(player, "anima.synergy_resonate", force=False, band=fac)
            )
        except Exception:
            lines.append("  เรลิกกับโลกเรโซแนนซ์ — จิตวิญญาณชัดขึ้นชั่วขณะ")
        # soft band whisper when deep/thin (not every time — only if band extreme)
        try:
            b = anima_band(player)
            if b == "deep" and fac == FACTION_DIVINE:
                lines.extend(
                    anima_presence_lines(player, "deep_calm", force=False, reg=reg)
                )
            elif b in ("thin", "frail"):
                lines.extend(
                    anima_presence_lines(player, "thin_warn", force=False, reg=reg)
                )
        except Exception:
            pass
    else:
        player[ANIMA_KEY] = max(5.0, a - 0.55)
        player["_anima_presence_felt"] = True
        try:
            from game.domain.alerts import emit_alert_lines

            lines.extend(
                emit_alert_lines(player, "anima.synergy_tension", force=False, band=fac)
            )
        except Exception:
            lines.append("  เรลิกขัด lean โลก — จิตแผ่ว · อาจอยากถอดหรือย้ายที่")
        try:
            if anima_band(player) in ("thin", "frail"):
                lines.extend(
                    anima_presence_lines(player, "thin_warn", force=False, reg=reg)
                )
        except Exception:
            pass
    player["_synergy_presence_tick"] = tick
    return lines


def on_chamber_spar_with_relic(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    rounds: int = 1,
) -> List[str]:
    """Deeper anima swing when sparring · bond/chorus deepen."""
    leans = equipped_relic_leans(player, reg)
    if not leans:
        return []
    from game.domain.stat_arch import ANIMA_KEY, anima_value, ensure_stat_arch

    ensure_stat_arch(player)
    bond = sync_bond_state(player, reg)
    fac = str(bond.get("faction") or leans[0][2])
    name = leans[0][1]
    it = (reg.items or {}).get(name) or {}
    nm = str(it.get("name") or name)
    a = anima_value(player)
    lines: List[str] = []
    r = max(1, rounds)
    mode = str(bond.get("mode") or BOND_NONE)
    n = int(bond.get("count") or 0)

    if mode == BOND_CHORUS:
        if fac == FACTION_DIVINE:
            gain = 1.7 * r if not bond.get("soft_cap") else 1.1 * r
            player[ANIMA_KEY] = min(99.0, a + gain)
            code = "anima.spar_chorus_divine"
        elif fac == FACTION_INFERNAL:
            player[ANIMA_KEY] = max(5.0, a - 0.35 * r)
            code = "anima.spar_chorus_infernal"
        else:
            player[ANIMA_KEY] = max(5.0, min(99.0, a + 0.9 * r))
            code = "anima.spar_chorus_echo"
        try:
            from game.domain.alerts import emit_alert_lines
            from game.domain.world_relations import adjust_faction

            lines.extend(
                emit_alert_lines(player, code, force=False, item=nm, band=fac)
            )
            boost = 1.6 * r
            if bond.get("soft_cap"):
                boost = min(boost, 1.8)
            lines.extend(adjust_faction(player, fac, boost, reason="spar_chorus"))
        except Exception:
            lines.append(f"  ซ้อมคณะเรลิก「{nm}」— Chorus ก้องชัดขึ้น")
        if bond.get("soft_cap") and n >= SOFT_CAP_COUNT:
            lines.extend(_apply_soft_cap_edge(player, n=n, force_lines=False))
            lines.append("  …คณะหนา — Soft Cap แผ่วตอนซ้อม")
    elif mode == BOND_RESONANCE:
        if fac == FACTION_DIVINE:
            player[ANIMA_KEY] = min(99.0, a + 1.3 * r)
            code = "anima.spar_bond_divine"
        elif fac == FACTION_INFERNAL:
            player[ANIMA_KEY] = max(5.0, a - 0.45 * r)
            code = "anima.spar_bond_infernal"
        else:
            player[ANIMA_KEY] = max(5.0, min(99.0, a + 0.65 * r))
            code = "anima.spar_bond_echo"
        try:
            from game.domain.alerts import emit_alert_lines
            from game.domain.world_relations import adjust_faction

            lines.extend(
                emit_alert_lines(player, code, force=False, item=nm, band=fac)
            )
            lines.extend(
                adjust_faction(player, fac, 1.2 * r, reason="spar_bond")
            )
        except Exception:
            lines.append(f"  ซ้อมเรโซแนนซ์「{nm}」— พันธะเรลิกชัดขึ้น")
    elif mode == BOND_TENSION:
        player[ANIMA_KEY] = max(5.0, a - 0.85 * r)
        try:
            from game.domain.alerts import emit_alert_lines

            lines.extend(
                emit_alert_lines(
                    player, "anima.spar_bond_tension", force=False, item=nm
                )
            )
        except Exception:
            lines.append("  ซ้อมขณะเรลิกขัด lean — จิตถูกดึงสองทาง")
    else:
        if fac == FACTION_DIVINE:
            player[ANIMA_KEY] = min(99.0, a + 0.9 * r)
            code = "anima.spar_divine"
        elif fac == FACTION_INFERNAL:
            player[ANIMA_KEY] = max(5.0, a - 0.7 * r)
            code = "anima.spar_infernal"
        else:
            player[ANIMA_KEY] = max(5.0, min(99.0, a + (0.5 if a < 50 else -0.3)))
            code = "anima.spar_echo"
        try:
            from game.domain.alerts import emit_alert_lines
            from game.domain.world_relations import adjust_faction

            lines.extend(
                emit_alert_lines(player, code, force=False, item=nm, band=fac)
            )
            lines.extend(adjust_faction(player, fac, 0.8, reason="spar_relic"))
        except Exception:
            lines.append(f"  ซ้อมกับ「{nm}」— จิตวิญญาณสั่นชัดขึ้น")

    # WO-046: spar in area matching relic lean → synergy deepen
    try:
        loc = str(player.get("location") or "")
        syn = evaluate_relic_area_synergy(player, reg, area_id=loc)
        if str(syn.get("mode")) == SYN_RESONATE:
            a2 = anima_value(player)
            fac2 = str(syn.get("relic_faction") or fac)
            if fac2 == FACTION_DIVINE:
                player[ANIMA_KEY] = min(99.0, a2 + 0.35 * r)
            elif fac2 == FACTION_INFERNAL:
                player[ANIMA_KEY] = max(5.0, a2 - 0.15 * r)
            else:
                player[ANIMA_KEY] = max(5.0, min(99.0, a2 + 0.25 * r))
            try:
                from game.domain.alerts import emit_alert_lines

                lines.extend(
                    emit_alert_lines(
                        player, "anima.spar_area_synergy", force=False, band=fac2
                    )
                )
            except Exception:
                lines.append("  ซ้อมขณะเรลิกสะท้อนกะ lean โลก — พันธะชัดขึ้น")
        elif str(syn.get("mode")) == SYN_AREA_TENSION:
            a2 = anima_value(player)
            player[ANIMA_KEY] = max(5.0, a2 - 0.25 * r)
            lines.append("  …ซ้อมขณะเรลิกขัด lean โลก — จิตถูกดึงแผ่ว")
    except Exception:
        pass

    player["_anima_presence_felt"] = True
    return lines


def try_relic_explore_whisper(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: Optional[random.Random] = None,
    *,
    area_id: str = "",
) -> List[str]:
    """
    Soft chance while exploring with relic equipped.
    WO-043: Soft Chorus raises whisper/gaze chance (echo highest).
    """
    leans = equipped_relic_leans(player, reg)
    if not leans:
        return []
    rng = rng or random.Random(
        int(player.get("latent_seed") or 1)
        + int(player.get("time_units") or 0)
        + int(player.get("auto_ticks") or 0)
    )
    bond = evaluate_relic_bonds(player, reg)
    mode = str(bond.get("mode") or BOND_NONE)
    chance = 0.12
    if mode == BOND_CHORUS:
        fac_b = str(bond.get("faction") or "")
        if fac_b == FACTION_ECHO:
            chance = 0.26
        elif fac_b == FACTION_DIVINE:
            chance = 0.18
        else:
            chance = 0.16
        if bond.get("soft_cap"):
            chance = min(0.28, chance + 0.02)
    elif mode == BOND_RESONANCE:
        fac_b = str(bond.get("faction") or "")
        if fac_b == FACTION_ECHO:
            chance = 0.20
        elif fac_b == FACTION_DIVINE:
            chance = 0.15
        else:
            chance = 0.14
    elif mode == BOND_TENSION:
        chance = 0.10
    if rng.random() > chance:
        return []

    fac = str(bond.get("faction") or leans[0][2])
    lines: List[str] = []
    try:
        from game.domain.alerts import emit_alert_lines
        from game.domain.world_relations import adjust_faction

        if mode == BOND_CHORUS and fac == FACTION_DIVINE:
            code = "world.chorus_divine_gaze"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(
                adjust_faction(player, FACTION_DIVINE, 1.15, reason="explore_chorus")
            )
        elif mode == BOND_CHORUS and fac == FACTION_INFERNAL:
            code = "world.chorus_infernal_haze"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(
                adjust_faction(player, FACTION_INFERNAL, 0.95, reason="explore_chorus")
            )
        elif mode == BOND_CHORUS and fac == FACTION_ECHO:
            code = "world.chorus_echo_choir"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(
                adjust_faction(player, FACTION_ECHO, 1.25, reason="explore_chorus")
            )
        elif mode == BOND_RESONANCE and fac == FACTION_DIVINE:
            code = "world.bond_divine_gaze"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(
                adjust_faction(player, FACTION_DIVINE, 0.9, reason="explore_bond")
            )
        elif mode == BOND_RESONANCE and fac == FACTION_INFERNAL:
            code = "world.bond_infernal_haze"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(
                adjust_faction(player, FACTION_INFERNAL, 0.75, reason="explore_bond")
            )
        elif mode == BOND_RESONANCE and fac == FACTION_ECHO:
            code = "world.bond_echo_chorus"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(
                adjust_faction(player, FACTION_ECHO, 1.0, reason="explore_bond")
            )
        elif mode == BOND_TENSION:
            code = "world.bond_tension_wind"
            lines.extend(emit_alert_lines(player, code, force=False))
            try:
                from game.domain.needs import ensure_needs, get_needs

                ensure_needs(player)
                n = get_needs(player)
                if int(n.get("morale") or 50) > 18 and rng.random() < 0.45:
                    n["morale"] = max(0, int(n["morale"]) - 1)
                    player["needs"] = n
            except Exception:
                pass
        elif fac == FACTION_DIVINE:
            code = "world.relic_wind_gaze"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(adjust_faction(player, FACTION_DIVINE, 0.6, reason="explore_relic"))
        elif fac == FACTION_INFERNAL:
            code = "world.relic_ember_whisper"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(adjust_faction(player, FACTION_INFERNAL, 0.5, reason="explore_relic"))
            try:
                from game.domain.needs import ensure_needs, get_needs

                ensure_needs(player)
                n = get_needs(player)
                if int(n.get("morale") or 50) > 20 and rng.random() < 0.4:
                    n["morale"] = max(0, int(n["morale"]) - 1)
                    player["needs"] = n
            except Exception:
                pass
        else:
            code = "world.relic_echo_whisper"
            lines.extend(emit_alert_lines(player, code, force=False))
            lines.extend(adjust_faction(player, FACTION_ECHO, 0.7, reason="explore_relic"))
    except Exception:
        lines.append("  …เรลิกกระซิบตามลมสำรวจ")
    return lines


def should_auto_unequip_for_anima(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    morale: int,
    morale_th: int,
) -> bool:
    """
    WO-040.3: unequip when anima frail + morale stressed.
    WO-041.2: Soft Tension + morale low.
    WO-043: Soft Cap chorus + morale stressed → thin the choir.
    WO-046: area tension (relic vs world lean) + morale stressed.
    """
    from game.domain.stat_arch import anima_band, anima_value

    if not equipped_relic_leans(player, reg):
        return False
    band = anima_band(player)  # type: ignore[arg-type]
    a = anima_value(player)
    if band == "frail" and morale <= morale_th + 12:
        return True
    if a < 22 and morale <= 35:
        return True
    bond = evaluate_relic_bonds(player, reg)
    mode = str(bond.get("mode") or "")
    if mode == BOND_TENSION and morale <= morale_th + 8:
        return True
    if mode == BOND_TENSION and morale <= 38 and a < 40:
        return True
    # Soft Cap / heavy chorus + low morale → drop one piece
    if mode == BOND_CHORUS and bond.get("soft_cap") and morale <= morale_th + 10:
        return True
    if mode == BOND_CHORUS and bond.get("soft_cap") and morale <= 36 and a < 45:
        return True
    # WO-046: relic lean clashes with area
    syn = evaluate_relic_area_synergy(player, reg)
    if str(syn.get("mode")) == SYN_AREA_TENSION and morale <= morale_th + 6:
        return True
    if str(syn.get("mode")) == SYN_AREA_TENSION and morale <= 36 and a < 42:
        return True
    return False


def tension_unequip_preference(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> Optional[str]:
    """
    Prefer unequipping a minority-lean relic under Soft Tension.
    WO-043: under Soft Cap chorus, prefer thinning non-weapon majority piece.
    Returns slot id or None.
    """
    bond = evaluate_relic_bonds(player, reg)
    mode = str(bond.get("mode") or "")
    leans = equipped_relic_leans(player, reg)
    if len(leans) < 2:
        return None

    if mode == BOND_CHORUS and bond.get("soft_cap"):
        # drop accessory/legs/feet/head before main_hand
        prio = {
            "acc_1": 0,
            "feet": 1,
            "legs": 2,
            "head": 3,
            "off_hand": 4,
            "body": 5,
            "main_hand": 9,
        }
        ordered = sorted(leans, key=lambda t: (prio.get(t[0], 5), t[0]))
        return ordered[0][0] if ordered else None

    if mode != BOND_TENSION:
        return None
    counts: Dict[str, int] = {}
    for _, _, fac in leans:
        counts[fac] = counts.get(fac, 0) + 1
    ordered = sorted(leans, key=lambda t: (counts.get(t[2], 0), t[0]))
    return ordered[0][0] if ordered else None
