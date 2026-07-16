"""
WO-023 Divine Burden — soft cost of wearing high-rarity relics.

Vision: docs/DIVINE_BURDEN_VISION.md
Rules:
  · equip always allowed
  · legendary+ may strain/crush when player is "too weak" (soft, hidden)
  · primary cost = morale drain; light MP tick optional
  · Godforge chamber can mute or full burden via session flags
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry

# Burden starts at legendary rank (tiers.yaml rank 5)
BURDEN_MIN_RANK = 5

FLAVOR_STRAIN = (
    "ของนี้ร้อนมือ…",
    "ภาระแห่งเรลิกกดเบา ๆ",
    "จิตยังไม่คุ้นน้ำหนักชิ้นนี้",
    "ออร่าแผ่เบา — ยังถือไหว",
    "เรลิกร้องในมือ แต่ยังเชื่อฟัง",
)
FLAVOR_CRUSH = (
    "ภาระหนักเกินตัว — เรลิกไม่ใช่ของเรา",
    "ลมจากของเทพกดขวัญ",
    "จิตสั่น — ยังไม่ใช่เจ้าของที่แท้",
    "ออร่ากดแน่น — อยากวางของลง",
    "ทุกก้าวรู้สึกเหมือนถือดวงดาวที่ร้อนเกินไป",
)
AURA_FLAVOR_EXTRA = (
    "เงารอบตัวสั่น — เรลิกแผ่ความรู้สึก",
    "ใครอยู่ใกล้มองตาคุณแปลก ๆ…",
)

# session flag keys
FLAG_GODFORGE = "godforge_session"  # dict on player
FLAG_BURDEN_MUTE = "burden_muted"  # inside session: measure power mode


def rarity_rank(reg: Optional[DataRegistry], rarity_id: str) -> int:
    try:
        from game.domain.rarity import tier_by_id

        return int(tier_by_id(reg, rarity_id or "common").get("rank") or 1)
    except Exception:
        table = {
            "common": 1,
            "uncommon": 2,
            "rare": 3,
            "sacred": 4,
            "legendary": 5,
            "divine": 6,
            "archdivine": 7,
            "mythic": 8,
        }
        return int(table.get(str(rarity_id or "common").lower(), 1))


def soft_affinity_bonus(player: Mapping[str, Any], reg: DataRegistry) -> int:
    """Hidden +0..2 from level-ish latent / unit soft (no formula dump)."""
    bonus = 0
    lv = int(player.get("level") or 1)
    if lv >= 12:
        bonus += 1
    if lv >= 20:
        bonus += 1
    # unit path soft
    try:
        u = str(player.get("unit_class") or player.get("unit_id") or "")
        if u and ("god" in u.lower() or "divine" in u.lower() or "hero" in u.lower()):
            bonus += 1
    except Exception:
        pass
    # intelligence allocation soft (mind resists burden slightly)
    try:
        intel = int((player.get("stats_alloc") or {}).get("intelligence") or 0)
        if intel >= 8:
            bonus += 1
    except Exception:
        pass
    return min(2, bonus)


def player_fit_rank(player: Mapping[str, Any], reg: DataRegistry) -> int:
    """Soft capacity rank 1–8 (hidden). WO-026: slightly more generous mid-game."""
    lv = int(player.get("level") or 1)
    # was //5 — //4 so legendary feels strain earlier in mid levels, less perpetual crush
    base = 1 + max(0, lv // 4)
    return int(max(1, min(8, base + soft_affinity_bonus(player, reg))))


def burden_gap(
    player: Mapping[str, Any],
    reg: DataRegistry,
    rarity_id: str,
) -> int:
    """How much the piece exceeds the player (0 = fit)."""
    rr = rarity_rank(reg, rarity_id)
    if rr < BURDEN_MIN_RANK:
        return 0
    return max(0, rr - player_fit_rank(player, reg))


def gap_band(gap: int) -> str:
    if gap <= 0:
        return "fit"
    if gap == 1:
        return "strain"
    return "crush"


def is_burden_muted(player: Mapping[str, Any]) -> bool:
    """Godforge 'measure power' mode or explicit mute."""
    if player.get("burden_muted") or player.get("_burden_muted"):
        return True
    sess = player.get(FLAG_GODFORGE) or player.get("godforge_session")
    if isinstance(sess, dict):
        if sess.get(FLAG_BURDEN_MUTE) or sess.get("burden_muted"):
            return True
        if str(sess.get("mode") or "") in (
            "power",
            "measure_power",
            "วัดพลัง",
        ):
            return True
    return False


def equipped_burden_pieces(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Dict[str, Any]]:
    """
    List of burden-active equipped pieces.
    Each: slot, item_id, rarity, gap, band, name
    """
    from game.domain.rarity import equip_rarity_for_slot, display_item_name

    out: List[Dict[str, Any]] = []
    if is_burden_muted(player):
        return out
    eq = dict(player.get("equip_ids") or {})
    for slot, iid in eq.items():
        if not iid:
            continue
        it = (reg.items or {}).get(str(iid)) or {}
        if str(it.get("kind") or "") not in ("equipment", "relic", ""):
            # still allow equipment kind only mostly
            if str(it.get("kind") or "") not in ("equipment",):
                continue
        rar = equip_rarity_for_slot(player, str(slot)) or str(it.get("rarity") or "common")
        # chamber loan pieces may force high rarity
        if it.get("chamber_relic") or it.get("divine_burden"):
            rar = str(it.get("rarity") or rar or "legendary")
        g = burden_gap(player, reg, rar)
        if g <= 0 and not it.get("force_burden"):
            continue
        if rarity_rank(reg, rar) < BURDEN_MIN_RANK and not it.get("force_burden"):
            continue
        if g <= 0 and it.get("force_burden"):
            g = 1
        band = gap_band(g)
        if band == "fit" and not it.get("force_burden"):
            continue
        nm = display_item_name(str(it.get("name") or iid), rar, reg)
        out.append(
            {
                "slot": str(slot),
                "item_id": str(iid),
                "rarity": str(rar),
                "gap": int(g),
                "band": band,
                "name": nm,
            }
        )
    out.sort(key=lambda x: (-int(x["gap"]), str(x["slot"])))
    return out


def worst_burden_band(player: Mapping[str, Any], reg: DataRegistry) -> str:
    pieces = equipped_burden_pieces(player, reg)
    if not pieces:
        return "fit"
    if any(p["band"] == "crush" for p in pieces):
        return "crush"
    if any(p["band"] == "strain" for p in pieces):
        return "strain"
    return "fit"


def _flavor(band: str, rng: Optional[random.Random] = None) -> str:
    rng = rng or random.Random()
    if band == "crush":
        return rng.choice(list(FLAVOR_CRUSH))
    return rng.choice(list(FLAVOR_STRAIN))


def soft_burden_status_line(player: Mapping[str, Any], reg: DataRegistry) -> str:
    pieces = equipped_burden_pieces(player, reg)
    if not pieces:
        return ""
    b = worst_burden_band(player, reg)
    n = len(pieces)
    lab = "หนักเกินตัว" if b == "crush" else "ร้อนมือ"
    top = pieces[0].get("name") or "เรลิก"
    return f"ภาระเรลิก · {lab} ({n}) · {top}"


def on_equip_burden_note(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    rarity_id: str,
    item_name: str = "",
    item_id: str = "",
) -> List[str]:
    """Call after equip — Soft Alert Bus (WO-034 relic.*)."""
    if is_burden_muted(player):
        return []
    g = burden_gap(player, reg, rarity_id)
    if rarity_rank(reg, rarity_id) < BURDEN_MIN_RANK:
        return []
    band = gap_band(g)
    name = item_name or "เรลิก"
    iid = str(item_id or "")
    tags: List[str] = list((reg.items.get(iid) or {}).get("tags") or []) if iid else []

    def _anima_wr(lines: List[str]) -> None:
        try:
            from game.domain.stat_arch import anima_presence_lines

            lines.extend(
                anima_presence_lines(player, "relic_equip", item=name, reg=reg)
            )
        except Exception:
            pass
        # WO-040: depth equip — faction lean + anima swing + Soft Alert
        try:
            from game.domain.relic_anima import on_relic_equip_depth

            lines.extend(
                on_relic_equip_depth(
                    player,
                    reg,
                    item_id=iid or name,
                    item_name=name,
                    tags=tags,
                )
            )
        except Exception:
            try:
                from game.domain.world_relations import on_relic_theme

                lines.extend(
                    on_relic_theme(
                        player, item_id=iid, tags=tags, rarity_id=rarity_id
                    )
                )
            except Exception:
                pass

    if band == "fit":
        player.pop("_burden_active", None)
        out: List[str] = []
        try:
            from game.domain.alerts import emit_alert_lines

            out.extend(
                emit_alert_lines(
                    player, "relic.equip", item=name, band=band, force=True
                )
            )
        except Exception:
            out.append(f"  「{name}」เข้ามือพอประมาณ")
        _anima_wr(out)
        return out
    player["_burden_active"] = band
    try:
        from game.domain.alerts import emit_alert_lines

        lines = emit_alert_lines(
            player,
            "relic.equip_warning",
            item=name,
            band=band,
            force=True,
        )
        # keep soft flavor extra once
        lines.append(f"  {_flavor(band)}")
        # crush → optional strong aura cue (catalog ready; light once)
        if band == "crush":
            lines.extend(
                emit_alert_lines(
                    player, "relic.aura_strong", item=name, band=band
                )
            )
        _anima_wr(lines)
        return lines
    except Exception:
        return [
            f"  {_flavor(band)}",
            "  ใบ้: ภาระเรลิก — ขวัญจะค่อยหนัก · ถอดได้เสมอ · ห้อง G ลองก่อน",
        ]


def on_unequip_burden_note(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    rarity_id: str,
    item_name: str = "",
) -> List[str]:
    """WO-034.2: soft alert when removing a legendary+ piece (manual or silent skip)."""
    if is_burden_muted(player):
        return []
    if rarity_rank(reg, rarity_id) < BURDEN_MIN_RANK:
        return []
    name = item_name or "เรลิก"
    try:
        from game.domain.alerts import emit_alert_lines

        return emit_alert_lines(
            player, "relic.unequip", item=name, band="fit", force=True
        )
    except Exception:
        return [f"  ถอด「{name}」แล้ว — ภาระผ่อน"]


def apply_burden_tick(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    context: str = "field",
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Soft drain once per care/combat tick.
    context: field | combat | dungeon
    """
    notes: List[str] = []
    pieces = equipped_burden_pieces(player, reg)
    if not pieces:
        player.pop("_burden_active", None)
        return notes

    rng = rng or random.Random(
        int(player.get("latent_seed") or 1)
        + int(player.get("level") or 1)
        + len(pieces)
    )
    band = worst_burden_band(player, reg)
    player["_burden_active"] = band

    from game.domain.needs import ensure_needs, get_needs

    ensure_needs(player)
    n = get_needs(player)
    morale = int(n.get("morale") or 50)

    # WO-030: medium feel locked from playtest (drop ~10–20 / 15 field ticks target)
    if band == "strain":
        if context == "combat":
            dmg = 1 if rng.random() < 0.40 else 0
        elif context == "dungeon":
            dmg = 1 if rng.random() < 0.58 else 0
        else:  # field care
            dmg = 1 if rng.random() < 0.58 else 0
    else:  # crush
        if context == "combat":
            dmg = 1 if rng.random() < 0.55 else 0
        elif context == "dungeon":
            dmg = 1 if rng.random() < 0.78 else 0
        else:
            dmg = 1 if rng.random() < 0.88 else 0
            # rare spike only if morale still comfortable
            if dmg and morale >= 40 and rng.random() < 0.12:
                dmg = 2

    if dmg > 0:
        # WO-037: Anima soft — high spirit resists burden morale drain
        try:
            from game.domain.stat_arch import anima_morale_drain_factor

            fac = anima_morale_drain_factor(player)
            if fac < 1.0 and dmg > 0 and rng.random() < (1.0 - fac):
                dmg = max(0, dmg - 1)
            elif fac > 1.05 and rng.random() < min(0.35, fac - 1.0):
                dmg = dmg + 1
        except Exception:
            pass
        # WO-040: equipped relic faction lean mult
        try:
            from game.domain.relic_anima import relic_equipped_morale_mult

            rfac = relic_equipped_morale_mult(player, reg)
            if rfac < 1.0 and dmg > 0 and rng.random() < (1.0 - rfac):
                dmg = max(0, dmg - 1)
            elif rfac > 1.05 and rng.random() < min(0.4, rfac - 1.0):
                dmg = dmg + 1
        except Exception:
            pass
        # soft floor: leave a little morale unless already crit
        new_mor = max(0, morale - dmg)
        if morale > 12 and new_mor < 8:
            new_mor = 8
        n["morale"] = new_mor
        player["needs"] = n
        player["_burden_drain_total"] = int(player.get("_burden_drain_total") or 0) + (
            morale - new_mor
        )
        player["_burden_active"] = band
        last = int(player.get("_burden_flavor_tick") or 0)
        tick = int(player.get("auto_ticks") or player.get("_care_ticks") or 0)
        if tick == 0 or tick - last >= 4 or context == "equip":
            notes.append(f"  {_flavor(band, rng)}")
            player["_burden_flavor_tick"] = tick
        # WO-034.3: morale being pressed (throttled)
        try:
            from game.domain.alerts import emit_alert_lines

            notes.extend(
                emit_alert_lines(player, "relic.morale_debuff", band=band)
            )
        except Exception:
            pass

    # WO-034.3: spirit_* = morale display while carrying relic (throttled)
    try:
        from game.domain.needs import band as needs_band
        from game.domain.alerts import emit_alert_lines

        mor_now = int(get_needs(player).get("morale") or 0)
        mb = needs_band("morale", mor_now)
        if mb == "crit":
            notes.extend(
                emit_alert_lines(player, "relic.spirit_critical", band=band)
            )
            # umbrella: crush + crit morale
            if band == "crush":
                notes.extend(
                    emit_alert_lines(player, "relic.critical", band=band)
                )
        elif mb == "low":
            notes.extend(emit_alert_lines(player, "relic.spirit_low", band=band))
    except Exception:
        pass

    # light MP drain on crush → relic.mana_drain (throttled)
    if band == "crush" and context in ("combat", "dungeon", "field"):
        mp = int(player.get("mp") or player.get("mana") or 0)
        mmp = int(player.get("max_mp") or player.get("max_mana") or 0)
        mp_p = 0.26 if context == "combat" else 0.30
        if mmp > 0 and mp > 0 and rng.random() < mp_p:
            if "mp" in player:
                player["mp"] = max(0, mp - 1)
            elif "mana" in player:
                player["mana"] = max(0, mp - 1)
            try:
                from game.domain.alerts import emit_alert_lines

                notes.extend(
                    emit_alert_lines(player, "relic.mana_drain", band=band)
                )
            except Exception:
                if rng.random() < 0.32:
                    notes.append("  เรลิกดูดพลังจิตเบา ๆ…")

    # WO-023.4 / 034.3: aura soft on party (rarer)
    if context in ("field", "dungeon", "combat") and band in ("strain", "crush"):
        try:
            if band == "crush" or rng.random() < 0.45:
                aura_notes = apply_relic_aura(player, reg, rng=rng)
                notes.extend(aura_notes)
                # first combat aura cue
                if context == "combat" and aura_notes:
                    from game.domain.alerts import emit_alert_lines

                    notes.extend(
                        emit_alert_lines(
                            player, "relic.aura_active", band=band
                        )
                    )
        except Exception:
            pass

    return notes


def try_auto_unequip_burden(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """
    Auto policy: unequip worst burden piece when morale low.
    """
    from game.runtime.dungeon_auto import ensure_auto_prefs
    from game.domain.needs import get_needs, band as needs_band

    prefs = ensure_auto_prefs(player)
    if not prefs.get("auto_unequip_burden", True):
        return []
    pieces = equipped_burden_pieces(player, reg)
    if not pieces:
        return []
    n = get_needs(player)
    mor = int(n.get("morale") or 50)
    th = int(prefs.get("morale") or 30)
    # thrift unequips earlier
    mode = str(prefs.get("item_mode") or "normal")
    if mode == "thrift":
        th = min(100, th + 10)
    elif mode == "safe":
        th = min(100, th + 5)

    mb = needs_band("morale", mor)
    # WO-040: also when anima frail + morale stressed
    anima_force = False
    try:
        from game.domain.relic_anima import should_auto_unequip_for_anima

        anima_force = should_auto_unequip_for_anima(
            player, reg, morale=mor, morale_th=th
        )
    except Exception:
        anima_force = False
    # WO-026: only unequip on low/crit or at/below threshold (less twitchy)
    if mor > th and mb not in ("low", "crit") and not anima_force:
        return []
    # WO-041: under Soft Tension prefer minority-lean slot
    slot = ""
    try:
        from game.domain.relic_anima import tension_unequip_preference

        pref = tension_unequip_preference(player, reg)
        if pref and any(str(p.get("slot")) == pref for p in pieces):
            slot = pref
    except Exception:
        slot = ""
    if not slot:
        # prefer unequip crush before strain
        crush = [p for p in pieces if p.get("band") == "crush"]
        worst = (crush or pieces)[0]
        slot = str(worst["slot"])
    worst = next((p for p in pieces if str(p.get("slot")) == slot), pieces[0])
    try:
        from game.domain.equipment import unequip_slot

        msg = unequip_slot(player, slot, reg, skip_relic_alert=True)
        nm = str(worst.get("name") or "เรลิก")
        notes: List[str] = []
        try:
            from game.domain.alerts import emit_alert_lines

            notes.extend(
                emit_alert_lines(
                    player, "relic.auto_unequip", item=nm, force=True
                )
            )
        except Exception:
            notes.append(f"  ออโต้: ถอด「{nm}」เพราะภาระเรลิก (ขวัญ)")
        if anima_force:
            try:
                mode = str(player.get("_relic_bond_mode") or "")
                soft_cap = bool(player.get("_relic_bond_soft_cap"))
                if mode == "tension":
                    notes.append("  …Soft Tension + ขวัญกด — ออโต้ถอดเรลิกที่ขัด lean")
                elif mode == "chorus" and soft_cap:
                    notes.append("  …Soft Cap Chorus + ขวัญกด — ออโต้บางคณะเรลิก")
                else:
                    try:
                        from game.domain.relic_anima import (
                            SYN_AREA_TENSION,
                            evaluate_relic_area_synergy,
                        )

                        syn = evaluate_relic_area_synergy(player, reg)
                        if str(syn.get("mode")) == SYN_AREA_TENSION:
                            notes.append(
                                "  …เรลิกขัด lean โลก + ขวัญกด — ออโต้ถอดเรลิก"
                            )
                        else:
                            notes.append("  …จิตวิญญาณแผ่ว + ขวัญกด — ออโต้ถอดเรลิก")
                    except Exception:
                        notes.append("  …จิตวิญญาณแผ่ว + ขวัญกด — ออโต้ถอดเรลิก")
            except Exception:
                notes.append("  …จิตวิญญาณแผ่ว + ขวัญกด — ออโต้ถอดเรลิก")
        if msg and "กลับ" in str(msg):
            notes.append(f"  {msg}")
        player["_burden_auto_unequips"] = int(player.get("_burden_auto_unequips") or 0) + 1
        player.pop("_relic_faction_lean", None)
        player.pop("_relic_depth_item", None)
        try:
            from game.runtime.auto_run_log import bump_auto_run

            bump_auto_run(player, "burden_unequips")
        except Exception:
            pass
        return notes
    except Exception:
        return []


def should_block_auto_equip_relic(
    player: Mapping[str, Any],
    reg: DataRegistry,
    rarity_id: str,
) -> bool:
    """True if auto should not equip this rarity (default: block strain/crush)."""
    from game.runtime.dungeon_auto import ensure_auto_prefs

    prefs = ensure_auto_prefs(player)  # type: ignore[arg-type]
    if prefs.get("auto_equip_relics", False):
        return False
    if rarity_rank(reg, rarity_id) < BURDEN_MIN_RANK:
        return False
    return gap_band(burden_gap(player, reg, rarity_id)) != "fit"


def pre_fight_burden_alerts(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """WO-034: pre-fight relic alerts + first aura cue."""
    if is_burden_muted(player):
        return []
    band = worst_burden_band(player, reg)
    if band == "fit":
        return []
    lines: List[str] = []
    try:
        from game.domain.alerts import emit_alert_lines
        from game.domain.needs import get_needs, band as needs_band, ensure_needs

        lines.extend(emit_alert_lines(player, "relic.pre_fight", band=band))
        # first-time-in-fight aura (once_session on catalog)
        lines.extend(
            emit_alert_lines(player, "relic.aura_active", band=band)
        )
        if band == "crush":
            lines.extend(
                emit_alert_lines(player, "relic.aura_strong", band=band)
            )
        # early critical umbrella if already spirit-crit + crush
        ensure_needs(player)
        mor = int(get_needs(player).get("morale") or 0)
        if needs_band("morale", mor) == "crit" and band == "crush":
            lines.extend(
                emit_alert_lines(player, "relic.critical", band=band)
            )
            lines.extend(
                emit_alert_lines(player, "relic.spirit_critical", band=band)
            )
        elif needs_band("morale", mor) in ("low", "crit"):
            code = (
                "relic.spirit_critical"
                if needs_band("morale", mor) == "crit"
                else "relic.spirit_low"
            )
            lines.extend(emit_alert_lines(player, code, band=band))
    except Exception:
        lines.append(f"  ⚠ ก่อนสู้ · มีภาระเรลิก ({band})")
    return lines


def burden_summary_for_log(player: Mapping[str, Any], reg: DataRegistry) -> str:
    b = worst_burden_band(player, reg)
    if b == "fit":
        if is_burden_muted(player):
            return "ภาระ: ปิด (ห้อง/โหมดวัดพลัง)"
        return "ภาระ: ไม่มี"
    pieces = equipped_burden_pieces(player, reg)
    return f"ภาระ: {b} ×{len(pieces)}"


# --- WO-023.4 Relic Aura (lite) ---

AURA_FLAVOR = (
    "เพื่อนข้างกายสีหน้าเปลี่ยน… ออร่าเรลิกกดเบา",
    "ออร่าจากเรลิกแผ่ — ปาร์ตี้ขวัญสั่น",
    "ใครอยู่ใกล้รู้สึกถึงภาระชิ้นนี้",
    "เงารอบตัวสั่น — เรลิกแผ่ความรู้สึก",
    "ใครอยู่ใกล้มองตาคุณแปลก ๆ…",
)


def soft_aura_resist_chance(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    band: str = "strain",
) -> float:
    """
    WO-034.5: soft chance to shrug aura pressure (0..~0.55).
    Uses existing affinity / mind / gear resist / morale — no new Spirit resource.
    """
    chance = 0.08
    try:
        chance += 0.06 * soft_affinity_bonus(player, reg)
    except Exception:
        pass
    try:
        intel = int((player.get("stats_alloc") or {}).get("intelligence") or 0)
        if intel >= 5:
            chance += 0.05
        if intel >= 10:
            chance += 0.05
    except Exception:
        pass
    try:
        gsr = float(player.get("gear_status_resist") or 0.0)
        chance += min(0.12, gsr * 0.5)
    except Exception:
        pass
    try:
        from game.domain.needs import get_needs

        mor = int(get_needs(player).get("morale") or 50)  # type: ignore[arg-type]
        if mor >= 70:
            chance += 0.08
        elif mor >= 55:
            chance += 0.04
        elif mor <= 25:
            chance -= 0.06
    except Exception:
        pass
    # WO-035: Anima (Spirit core) soft resist — not morale, not relic.spirit_*
    try:
        from game.domain.stat_arch import apply_anima_to_burden_resist, ensure_stat_arch

        ensure_stat_arch(player)  # type: ignore[arg-type]
        chance += apply_anima_to_burden_resist(player)
    except Exception:
        pass
    # blessings soft tag
    try:
        for b in player.get("blessings") or []:
            bid = str(b if not isinstance(b, dict) else b.get("id") or "")
            if any(k in bid.lower() for k in ("ward", "spirit", "mind", "holy", "calm")):
                chance += 0.06
                break
    except Exception:
        pass
    if band == "crush":
        chance *= 0.65
    return max(0.0, min(0.55, chance))


def apply_relic_aura(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """
    Soft aura on party when wearer is under crush (or multi strain).
    Does not kill · no forced combat.
    WO-034.5: may resist (relic.aura_resisted) or push strong (relic.aura_strong).
    """
    notes: List[str] = []
    if is_burden_muted(player):
        return notes
    band = worst_burden_band(player, reg)
    if band == "fit":
        return notes
    party = list(player.get("party") or [])
    rng = rng or random.Random(
        int(player.get("latent_seed") or 1) + len(party) + int(player.get("level") or 1)
    )

    # only sometimes to avoid spam
    chance = 0.55 if band == "crush" else 0.25
    if rng.random() > chance:
        return notes

    # WO-034.5: soft resist — no party bond hit, soft info alert
    resist_p = soft_aura_resist_chance(player, reg, band=band)
    if rng.random() < resist_p:
        try:
            from game.domain.alerts import emit_alert_lines

            notes.extend(
                emit_alert_lines(player, "relic.aura_resisted", band=band)
            )
        except Exception:
            notes.append("  จิตต้านออร่าเรลิกได้ — แรงกดเบาลง")
        player["_relic_aura_resisted"] = int(player.get("_relic_aura_resisted") or 0) + 1
        return notes

    if not party:
        # still soft self-note rarely for crush
        if band == "crush" and rng.random() < 0.15:
            notes.append(f"  {rng.choice(list(AURA_FLAVOR))}")
            try:
                from game.domain.alerts import emit_alert_lines

                notes.extend(
                    emit_alert_lines(player, "relic.aura_strong", band=band)
                )
            except Exception:
                pass
        return notes

    # soft: reduce bond slightly or set soft flag; prefer flavor
    bonds = dict(player.get("party_bonds") or {})
    touched = 0
    for m in party:
        if not isinstance(m, dict):
            continue
        mid = str(m.get("id") or "")
        if not mid:
            continue
        if band == "crush" and rng.random() < 0.4:
            bonds[mid] = max(0, int(bonds.get(mid) or m.get("bond") or 1) - 1)
            touched += 1
        # companion soft morale if stored
        if "morale" in m and band == "crush":
            m["morale"] = max(0, int(m.get("morale") or 50) - 2)
    if touched:
        player["party_bonds"] = bonds
    notes.append(f"  {rng.choice(list(AURA_FLAVOR))}")
    # strong aura cue when crush actually presses party
    if band == "crush":
        try:
            from game.domain.alerts import emit_alert_lines

            notes.extend(
                emit_alert_lines(player, "relic.aura_strong", band=band)
            )
        except Exception:
            pass
    return notes


def soft_echo_relic_menu_hint(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    """
    Lines for echo encounter UI when player (or echo) has strong burden.
    Caller may offer: ถอย / นอบน้อม / ก้าวร้าว
    """
    band = worst_burden_band(player, reg)
    if band == "fit":
        return []
    return [
        " ออร่าเรลิกแผ่จากเกียร์ — เงาอีกฝ่ายอาจรู้สึก",
        "  ทางเลือก soft: ถอย · นอบน้อม · (ก้าวร้าว = เสี่ยง)",
    ]


def entity_has_relic_presence(
    entity: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> bool:
    """
    Soft: does this player/echo carry legendary+ gear presence?
    Used for echo approach aura UI (WO-024).
    """
    # live player with burden active
    if reg is not None and not entity.get("is_echo_snapshot"):
        try:
            if worst_burden_band(entity, reg) != "fit":
                return True
        except Exception:
            pass
    rars = dict(entity.get("equip_rarities") or {})
    for rid in rars.values():
        if rarity_rank(reg, str(rid)) >= BURDEN_MIN_RANK:
            return True
    # snapshot may only have equip_summary + equip_rarity_summary
    rar_sum = dict(entity.get("equip_rarity_summary") or {})
    for rid in rar_sum.values():
        if rarity_rank(reg, str(rid)) >= BURDEN_MIN_RANK:
            return True
    # gear tags soft
    for t in entity.get("gear_tags") or []:
        s = str(t).lower()
        if s in ("legendary", "divine", "relic", "mythic", "archdivine"):
            return True
    return bool(entity.get("relic_presence") or entity.get("_relic_aura"))


def should_prompt_relic_aura(
    player: Mapping[str, Any],
    other: Mapping[str, Any],
    reg: DataRegistry,
) -> Tuple[bool, str]:
    """
    Returns (show_menu, reason_soft).
    Show when either side radiates relic pressure.
    """
    self_b = worst_burden_band(player, reg)
    self_hot = self_b != "fit" or entity_has_relic_presence(player, reg)
    other_hot = entity_has_relic_presence(other, reg)
    if self_hot and other_hot:
        return True, "ออร่าเรลิกจากทั้งสองฝ่ายกดอากาศ"
    if other_hot:
        return True, "เงาสวมของที่แผ่ออร่า — ขวัญสั่นเมื่อเข้าใกล้"
    if self_hot:
        return True, "เรลิกบนตัวคุณแผ่ — เงาอาจรู้สึกถึงภาระ"
    return False, ""


def apply_echo_relic_reaction(
    player: MutableMapping[str, Any],
    choice: str,
    *,
    rng: Optional[random.Random] = None,
) -> List[str]:
    """Soft resolve for ถอย / นอบน้อม / ก้าวร้าว near relic aura."""
    from game.domain.needs import ensure_needs, get_needs

    rng = rng or random.Random()
    ensure_needs(player)
    n = get_needs(player)
    ch = str(choice or "").lower().strip()
    notes: List[str] = []
    if ch in ("retreat", "ถอย", "r", "back"):
        notes.append("  ถอยห่างจากออร่า — ขวัญไม่โดนหนัก")
        return notes
    if ch in ("humble", "นอบน้อม", "h", "bow"):
        # small morale buffer
        n["morale"] = min(100, int(n["morale"]) + 3)
        player["needs"] = n
        notes.append("  นอบน้อม — ออร่าผ่อนลงชั่วคราว · ขวัญนิ่งขึ้นนิด")
        player["_relic_aura_soothed"] = True
        return notes
    if ch in ("aggro", "ก้าวร้าว", "a", "fight"):
        n["morale"] = max(0, int(n["morale"]) - 8)
        player["needs"] = n
        notes.append("  ก้าวร้าวต่อออร่า — ขวัญสะเทือน · เสี่ยงปะทะ")
        player["_relic_aura_hostile"] = True
        return notes
    notes.append("  (ไม่เลือก — ยืนนิ่งในออร่า)")
    return notes
