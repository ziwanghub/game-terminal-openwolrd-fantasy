"""Equipment, cards, sockets — recompute combat stats.

EL0–EL1: multi-slot loadout + grip (one_hand / two_hand / shield / focus).
Legacy slots weapon/armor/accessory migrate → main_hand/body/acc_1.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry

# ── Loadout schema (EL0) ──────────────────────────────────────────
EQUIP_SLOTS: Tuple[str, ...] = (
    "main_hand",
    "off_hand",
    "head",
    "body",
    "legs",
    "feet",
    "acc_1",
)

LEGACY_SLOT_MAP: Dict[str, str] = {
    "weapon": "main_hand",
    "armor": "body",
    "accessory": "acc_1",
}

# reverse for soft labels / card compat groups
SLOT_LABEL_TH: Dict[str, str] = {
    "main_hand": "มือหลัก",
    "off_hand": "มือรอง",
    "head": "ศีรษะ",
    "body": "ลำตัว",
    "legs": "ส่วนล่าง",
    "feet": "เท้า",
    "acc_1": "เครื่องประดับ",
    # legacy aliases
    "weapon": "อาวุธ",
    "armor": "เกราะ",
    "accessory": "เครื่องประดับ",
}

GRIP_ONE_HAND = "one_hand"
GRIP_TWO_HAND = "two_hand"
GRIP_SHIELD = "shield"
GRIP_FOCUS = "focus"

# Off-hand weapon contributes partial ATK (anti dual-OP)
OFF_HAND_ATK_MULT = 0.55

# UI order for numbered pickers
EQUIP_SLOT_UI: Tuple[Tuple[str, str], ...] = (
    ("main_hand", "มือหลัก"),
    ("off_hand", "มือรอง"),
    ("head", "ศีรษะ"),
    ("body", "ลำตัว"),
    ("legs", "ส่วนล่าง"),
    ("feet", "เท้า"),
    ("acc_1", "เครื่องประดับ"),
)


def soft_guard_band(power: float) -> str:
    """Soft band label for total guard feel (alongside numeric equip def)."""
    p = float(power or 0)
    if p < 8.0:
        return "แผ่ว"
    if p < 14.0:
        return "เบา"
    if p < 22.0:
        return "กลาง"
    if p < 32.0:
        return "หนา"
    return "แน่น"


def soft_guard_summary(player: Mapping[str, Any]) -> str:
    """
    Shown: กันกาย N · กันเวท M  (equip scores)
    Soft band from power_def/mdef (includes latent stance).
    """
    ed = int(player.get("equip_def") or 0)
    em = int(player.get("equip_mdef") or 0)
    pdef = float(player.get("power_def") or ed)
    pmdef = float(player.get("power_mdef") or em)
    return (
        f"กันกาย {ed} ({soft_guard_band(pdef)}) · "
        f"กันเวท {em} ({soft_guard_band(pmdef)})"
    )


def soft_piece_primary_hint(
    it: Mapping[str, Any],
    *,
    slot: str = "",
    grip: str = "",
    st: Optional[Mapping[str, Any]] = None,
) -> str:
    """
    Primary visible stats only:
      weapons → ATK (+ MP if any)
      armor/shield → DEF/MDEF
    Latent (HP% / tough / resist / atk% / crit) never listed.
    """
    if not it:
        return ""
    grip = grip or item_grip(it)
    if st is not None:
        d = int(st.get("def") or 0)
        m = int(st.get("mdef") or 0)
        a = int(st.get("atk") or 0)
        mp = int(st.get("max_mana") or 0)
    else:
        d = int(it.get("def") or it.get("defense") or 0)
        m = int(it.get("mdef") or 0)
        a = int(it.get("atk") or 0)
        mp = int(it.get("max_mana") or 0)
    bits: List[str] = []
    armor_like = slot in ("body", "head", "legs", "feet", "armor") or grip == GRIP_SHIELD
    if armor_like or (d > 0 or m > 0) and a <= 0:
        if d > 0:
            bits.append(f"กันกาย +{d}")
        if m > 0:
            bits.append(f"กันเวท +{m}")
        if mp > 0:
            bits.append(f"MP+{mp}")
        if grip == GRIP_SHIELD and not bits:
            bits.append("กันกาย")
        return " · ".join(bits)
    # weapon / focus primary
    if a > 0:
        bits.append(f"โจมตี +{a}")
    if mp > 0:
        bits.append(f"MP+{mp}")
    # dual-stat pieces (rare)
    if d > 0:
        bits.append(f"กันกาย +{d}")
    if m > 0:
        bits.append(f"กันเวท +{m}")
    return " · ".join(bits)


def soft_piece_defense_hint(
    it: Mapping[str, Any],
    *,
    slot: str = "",
    grip: str = "",
    st: Optional[Mapping[str, Any]] = None,
) -> str:
    """Alias: primary stats for piece UI (defense-oriented name kept for callers)."""
    return soft_piece_primary_hint(it, slot=slot, grip=grip, st=st)


def normalize_slot(slot: Optional[str]) -> str:
    """Map legacy or new slot id to canonical EQUIP_SLOTS id."""
    s = str(slot or "").strip()
    if not s:
        return "main_hand"
    if s in LEGACY_SLOT_MAP:
        return LEGACY_SLOT_MAP[s]
    if s in EQUIP_SLOTS:
        return s
    return s


def is_equip_slot(slot: str) -> bool:
    return normalize_slot(slot) in EQUIP_SLOTS


def item_grip(it: Mapping[str, Any]) -> str:
    """Derive grip from YAML grip or tags/slot heuristics."""
    g = str(it.get("grip") or "").strip().lower()
    if g in (GRIP_ONE_HAND, GRIP_TWO_HAND, GRIP_SHIELD, GRIP_FOCUS):
        return g
    tags = {str(t).lower() for t in (it.get("tags") or [])}
    if "shield" in tags or "โล่" in tags:
        return GRIP_SHIELD
    if "two_hand" in tags or "two-handed" in tags or "greatweapon" in tags:
        return GRIP_TWO_HAND
    if "focus" in tags or "catalyst" in tags:
        return GRIP_FOCUS
    # slot hints
    raw_slot = str(it.get("slot") or "")
    if raw_slot in ("shield", "off_hand") and it.get("atk") in (None, 0):
        return GRIP_SHIELD
    if raw_slot == "off_hand" and not it.get("atk"):
        return GRIP_SHIELD
    # default weapon-like → one_hand
    ns = normalize_slot(raw_slot) if raw_slot else "main_hand"
    if ns in ("main_hand", "off_hand") or raw_slot in ("weapon", "shield"):
        return GRIP_ONE_HAND
    return GRIP_ONE_HAND


def item_base_slot(it: Mapping[str, Any]) -> str:
    """Canonical slot preference from item def (before grip target resolve)."""
    raw = str(it.get("slot") or "weapon")
    if raw in ("shield",):
        return "off_hand"
    return normalize_slot(raw)


def allowed_slots_for_item(it: Mapping[str, Any]) -> List[str]:
    """Which loadout slots this piece may occupy."""
    grip = item_grip(it)
    base = item_base_slot(it)
    if base in ("head", "body", "legs", "feet", "acc_1"):
        return [base]
    if grip == GRIP_SHIELD:
        return ["off_hand"]
    if grip == GRIP_TWO_HAND:
        return ["main_hand"]
    if grip == GRIP_FOCUS:
        return ["off_hand", "main_hand"]
    if grip == GRIP_ONE_HAND:
        allow_off = it.get("allow_off_hand")
        if allow_off is False:
            return ["main_hand"]
        return ["main_hand", "off_hand"]
    return [base] if base in EQUIP_SLOTS else ["main_hand"]


def card_slot_matches(equip_slot: str, compatible: Sequence[Any]) -> bool:
    """Card compatible list may use legacy weapon/armor or new slot ids."""
    es = normalize_slot(equip_slot)
    groups: List[str] = []
    for c in compatible or []:
        cs = str(c).strip().lower()
        if cs in ("any", "*"):
            return True
        if cs in ("weapon", "main_hand", "off_hand"):
            groups.extend(["main_hand", "off_hand"])
        elif cs in ("armor", "body", "head", "legs", "feet"):
            groups.extend(["body", "head", "legs", "feet"])
        elif cs in ("accessory", "acc", "acc_1"):
            groups.append("acc_1")
        else:
            groups.append(normalize_slot(cs))
    return es in set(groups)


def _empty_slot_map(default: Any = None) -> Dict[str, Any]:
    return {s: default for s in EQUIP_SLOTS}


def _migrate_slot_dict(
    raw: Mapping[str, Any],
    *,
    default: Any = None,
    list_default: bool = False,
    numeric: bool = False,
) -> Dict[str, Any]:
    """Move legacy keys into new slots; keep already-new keys."""
    out = _empty_slot_map([] if list_default else default)
    data = dict(raw or {})

    def _is_empty(val: Any) -> bool:
        if list_default:
            return not val
        if numeric:
            # 0 is empty for upgrades until legacy migrates
            return val is None or val == "" or val == 0
        return val in (None, "", [])

    # first apply legacy if new empty
    for leg, neu in LEGACY_SLOT_MAP.items():
        if leg not in data:
            continue
        leg_val = data[leg]
        if list_default:
            if leg_val and _is_empty(out.get(neu)):
                out[neu] = list(leg_val) if isinstance(leg_val, list) else leg_val
        elif numeric:
            if leg_val not in (None, "") and int(leg_val or 0) != 0 and _is_empty(out.get(neu)):
                out[neu] = int(leg_val)
        else:
            if leg_val not in (None, "", []) and _is_empty(out.get(neu)):
                out[neu] = leg_val
    for s in EQUIP_SLOTS:
        if s not in data:
            continue
        if list_default:
            if data[s] is not None:
                out[s] = list(data[s]) if isinstance(data[s], list) else data[s]
        elif numeric:
            if data[s] is not None and data[s] != "":
                out[s] = int(data[s] or 0)
        else:
            if data[s] is not None and data[s] != "":
                out[s] = data[s]
    return out


def migrate_equip_loadout(player: MutableMapping[str, Any]) -> None:
    """EL0: weapon→main_hand, armor→body, accessory→acc_1 across equip maps."""
    player["equip_ids"] = _migrate_slot_dict(player.get("equip_ids") or {}, default=None)
    player["upgrade_levels"] = _migrate_slot_dict(
        player.get("upgrade_levels") or {}, default=0, numeric=True
    )
    ups = dict(player["upgrade_levels"])
    for s in EQUIP_SLOTS:
        ups[s] = int(ups.get(s) or 0)
    player["upgrade_levels"] = ups

    socks_in = dict(player.get("sockets") or {})
    socks_out = _empty_slot_map([])
    for leg, neu in LEGACY_SLOT_MAP.items():
        if leg in socks_in and socks_in[leg]:
            if not socks_out.get(neu):
                socks_out[neu] = list(socks_in[leg] or [])
    for s in EQUIP_SLOTS:
        if s in socks_in:
            socks_out[s] = list(socks_in[s] or [])
    player["sockets"] = socks_out

    er_in = dict(player.get("equip_rarities") or {})
    er_out = _empty_slot_map(None)
    for leg, neu in LEGACY_SLOT_MAP.items():
        if leg in er_in and er_in[leg] not in (None, ""):
            if er_out.get(neu) in (None, ""):
                er_out[neu] = er_in[leg]
    for s in EQUIP_SLOTS:
        if s in er_in:
            er_out[s] = er_in[s]
    player["equip_rarities"] = er_out

    eqi_in = dict(player.get("equip_instances") or {})
    eqi_out = _empty_slot_map(None)
    for leg, neu in LEGACY_SLOT_MAP.items():
        if leg in eqi_in and eqi_in[leg]:
            if not eqi_out.get(neu):
                inst = eqi_in[leg]
                if isinstance(inst, dict):
                    inst = dict(inst)
                    inst["location"] = f"equip:{neu}"
                eqi_out[neu] = inst
    for s in EQUIP_SLOTS:
        if s in eqi_in and eqi_in[s]:
            eqi_out[s] = eqi_in[s]
    player["equip_instances"] = eqi_out

    # display cache
    equip_disp = dict(player.get("equip") or {})
    disp_out = _empty_slot_map(None)
    for leg, neu in LEGACY_SLOT_MAP.items():
        if leg in equip_disp and equip_disp[leg]:
            disp_out[neu] = equip_disp[leg]
    for s in EQUIP_SLOTS:
        if s in equip_disp:
            disp_out[s] = equip_disp[s]
    player["equip"] = disp_out


def ensure_gear_fields(player: MutableMapping[str, Any]) -> None:
    player.setdefault("base_atk", int(player.get("bonus_atk", 5)))
    player.setdefault("base_max_hp", int(player.get("max_hp", 100)))
    player.setdefault("base_max_mana", int(player.get("max_mana", 50)))
    player.setdefault("base_skills", list(player.get("skills") or []))
    player.setdefault("inventory_ids", [])
    player.setdefault("card_bag", [])
    player.setdefault("equip_ids", {})
    player.setdefault("sockets", {})
    player.setdefault("upgrade_levels", {})
    player.setdefault("equip_rarities", {})
    player.setdefault("equip_instances", {})
    player.setdefault("equip", {})
    migrate_equip_loadout(player)


def item_by_id(reg: DataRegistry, item_id: str) -> Optional[Dict[str, Any]]:
    return reg.items.get(item_id) or reg.cards.get(item_id)


def add_item(
    player: MutableMapping[str, Any],
    item_id: str,
    reg: DataRegistry,
    *,
    rarity: Optional[str] = None,
) -> str:
    from game.domain.rarity import (
        append_item_rarity,
        ensure_inventory_rarity,
        format_rarity_tag,
        item_default_rarity,
    )

    ensure_gear_fields(player)
    ensure_inventory_rarity(player)
    it = item_by_id(reg, item_id)
    if not it:
        return f"ไม่พบไอเทม {item_id}"
    kind = it.get("kind") or ("card" if item_id.startswith("card_") or item_id in reg.cards else "item")
    from game.domain.rarity import display_item_name

    rid = str(rarity or item_default_rarity(it, reg))
    shown = display_item_name(str(it.get("name", item_id)), rid, reg)
    if kind == "card" or item_id in reg.cards:
        bag = list(player.get("card_bag") or [])
        bag.append(item_id)
        player["card_bag"] = bag
        # legacy display list
        cards = list(player.get("cards") or [])
        cards.append(shown)
        player["cards"] = cards
        # cards bag rarities optional parallel
        cr = list(player.get("card_rarities") or [])
        cr.append(rid)
        player["card_rarities"] = cr
    else:
        ids = list(player.get("inventory_ids") or [])
        ids.append(item_id)
        player["inventory_ids"] = ids
        append_item_rarity(player, rid)
        inv = list(player.get("inventory") or [])
        inv.append(shown)
        player["inventory"] = inv
        # instance layer (owned piece)
        try:
            from game.domain.item_instances import append_instance, ensure_item_instances

            # append_instance re-syncs lists — avoid double-append by only ensuring if already tracked
            items = list(player.get("inventory_items") or [])
            if len(items) == len(ids) - 1:
                from game.domain.item_instances import make_instance, sync_legacy_from_instances

                items.append(
                    make_instance(item_id, player, reg, rarity=rid, location="bag")
                )
                player["inventory_items"] = items
            else:
                player["inventory_items"] = []
                ensure_item_instances(player, reg)
        except Exception:
            pass
    return shown


def remove_inventory_id(player: MutableMapping[str, Any], item_id: str, reg: DataRegistry) -> bool:
    from game.domain.rarity import ensure_inventory_rarity, pop_item_rarity_at

    ids = list(player.get("inventory_ids") or [])
    if item_id not in ids:
        return False
    idx = ids.index(item_id)
    ids.pop(idx)
    player["inventory_ids"] = ids
    ensure_inventory_rarity(player)
    pop_item_rarity_at(player, idx)
    name = (reg.items.get(item_id) or {}).get("name", item_id)
    inv = list(player.get("inventory") or [])
    # remove first display line that starts with name
    for i, line in enumerate(inv):
        if str(line).startswith(str(name)):
            inv.pop(i)
            break
    else:
        if name in inv:
            inv.remove(name)
    player["inventory"] = inv
    return True


def recompute_stats(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    """Rebuild bonus_atk / max_hp / max_mana / skills from base + gear + cards."""
    ensure_gear_fields(player)
    atk = int(player.get("base_atk", 5)) + int(player.get("alloc_atk_bonus", 0))
    max_hp = int(player.get("base_max_hp", 100)) + int(player.get("alloc_def_bonus", 0))
    max_mana = int(player.get("base_max_mana", 50)) + int(player.get("alloc_mag_bonus", 0)) // 2
    # party passive (recruited companions)
    atk += int(player.get("party_bonus_atk") or 0)
    max_hp += int(player.get("party_bonus_max_hp") or 0)
    max_mana += int(player.get("party_bonus_max_mana") or 0)
    pressure = int(player.get("pressure", 10))
    # reset pressure bonus from cards carefully: store base_pressure
    if "base_pressure" not in player:
        player["base_pressure"] = pressure
    pressure = int(player["base_pressure"]) + int(player.get("alloc_spd_bonus", 0)) // 3

    skills = list(player.get("base_skills") or [])
    # always keep progression skills that were unlocked beyond base
    unlocked = [s for s in (player.get("skills") or []) if s not in skills]
    # filter gear-granted from previous recompute using tag
    progression = [s for s in unlocked if not str(s).startswith("_gear_")]

    tags: List[str] = []
    on_hit: List[Dict[str, Any]] = []

    from game.domain.rarity import (
        equip_rarity_for_slot,
        format_rarity_tag,
        item_default_rarity,
        scaled_item_stats,
    )

    soft_notes: List[str] = []
    equip_def = 0  # visible physical defense score from pieces
    equip_mdef = 0  # visible magic defense score
    latent_hp_flat = 0
    latent_hp_pct = 0.0
    latent_atk_pct = 0.0
    latent_crit = 0.0
    latent_tough = 0.0
    latent_status_resist = 0.0
    for slot in EQUIP_SLOTS:
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            player.setdefault("equip", {})[slot] = None
            continue
        it = reg.items.get(eid) or {}
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        rid = equip_rarity_for_slot(player, slot)
        if rid in (None, "None", ""):
            rid = item_default_rarity(it, reg)
        st = scaled_item_stats(it, rid, reg, upgrade_level=up, slot=slot)
        piece_atk = int(st["atk"])
        # dual: off-hand weapon contributes partial ATK
        grip = item_grip(it)
        if slot == "off_hand" and grip in (GRIP_ONE_HAND, GRIP_FOCUS) and piece_atk > 0:
            piece_atk = max(0, int(round(piece_atk * OFF_HAND_ATK_MULT)))
        atk += piece_atk
        # explicit HP only if item still has max_hp (weapons/rare); armor uses latent
        max_hp += int(st.get("max_hp") or 0)
        max_mana += int(st.get("max_mana") or 0)
        equip_def += int(st.get("def") or 0)
        equip_mdef += int(st.get("mdef") or 0)
        latent_hp_flat += int(st.get("latent_max_hp") or 0)
        latent_hp_pct += float(st.get("latent_hp_pct") or 0.0)
        # hidden offense / toughness (never shown on piece sheet)
        latent_atk_pct += float(st.get("latent_atk_pct") or 0.0)
        latent_crit += float(st.get("latent_crit") or 0.0)
        latent_tough += float(st.get("latent_tough") or 0.0)
        latent_status_resist += float(st.get("latent_status_resist") or 0.0)
        for t in it.get("tags") or []:
            if t not in tags:
                tags.append(str(t))
        up_txt = f" +{up}" if up else ""
        rtag = format_rarity_tag(reg, rid)
        player.setdefault("equip", {})[slot] = f"{it.get('name', eid)}{up_txt} {rtag}"

        socks = list((player.get("sockets") or {}).get(slot) or [])
        socket_n = int(it.get("sockets", 0))
        # pad/trim
        while len(socks) < socket_n:
            socks.append(None)
        socks = socks[:socket_n]
        player.setdefault("sockets", {})[slot] = socks

        for cid in socks:
            if not cid:
                continue
            card = reg.cards.get(cid) or {}
            bon = card.get("bonuses") or {}
            card_atk = int(bon.get("atk", 0))
            if slot == "off_hand" and grip in (GRIP_ONE_HAND, GRIP_FOCUS):
                card_atk = max(0, int(round(card_atk * OFF_HAND_ATK_MULT)))
            atk += card_atk
            max_hp += int(bon.get("max_hp", 0))
            max_mana += int(bon.get("max_mana", 0))
            equip_def += int(bon.get("def", 0) or bon.get("defense", 0) or 0)
            equip_mdef += int(bon.get("mdef", 0) or 0)
            pressure += int(bon.get("pressure", 0))
            for t in card.get("grant_tags") or []:
                if t not in tags:
                    tags.append(str(t))
            for sk in card.get("grant_skills") or []:
                if sk not in skills and sk not in progression:
                    progression.append(str(sk))
            if card.get("on_hit"):
                on_hit.append(dict(card["on_hit"]))

    # EL3: soft bias from loadout (stance / grip) — additive to gear def scores
    gear_def = float(equip_def)
    gear_mdef = float(equip_mdef)
    gear_atk = 0.0
    gear_mag = 0.0
    gear_atb = 0.0
    main_id = (player.get("equip_ids") or {}).get("main_hand")
    off_id = (player.get("equip_ids") or {}).get("off_hand")
    main_grip = item_grip(reg.items.get(main_id) or {}) if main_id else None
    off_grip = item_grip(reg.items.get(off_id) or {}) if off_id else None

    if main_grip == GRIP_TWO_HAND:
        gear_atk += 3.5
        gear_def -= 1.0
        gear_atb -= 1.2
        soft_notes.append("ถือสองมือ — มือรองล็อก")
    elif main_grip == GRIP_ONE_HAND and off_grip == GRIP_SHIELD:
        gear_def += 2.5  # shield stance soft (piece def already counted)
        gear_mdef += 1.0
        gear_atk -= 0.5
        gear_atb -= 0.8
        soft_notes.append("มือเดียวกับโล่ — รับกระแทกได้ดีขึ้น")
    elif main_grip == GRIP_ONE_HAND and off_grip in (GRIP_ONE_HAND, GRIP_FOCUS):
        gear_atk += 1.8
        gear_def -= 1.5
        gear_atb += 0.6 if off_grip == GRIP_ONE_HAND else 0.0
        if off_grip == GRIP_FOCUS:
            gear_mag += 3.0
            gear_mdef += 1.5
            soft_notes.append("โฟกัสมือรอง — ม่านเวท soft")
        else:
            soft_notes.append("ถือคู่ — มือรองเสริมพลังแผ่ว")
    elif main_grip == GRIP_ONE_HAND and not off_id:
        gear_atk += 0.5
        gear_atb += 0.4

    # weight / bias soft (small extras beyond explicit def)
    for slot in ("head", "body", "legs", "feet", "off_hand"):
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            continue
        it = reg.items.get(eid) or {}
        bias = it.get("bias") or {}
        if isinstance(bias, dict):
            if bias.get("guard_physical") == "strong":
                gear_def += 1.5
            if bias.get("guard_physical") == "slight":
                gear_def += 0.6
            if bias.get("guard_arcane") == "strong":
                gear_mdef += 1.5
            if bias.get("guard_arcane") == "slight":
                gear_mdef += 0.6
            if bias.get("atb") in ("slight_fast", "fast"):
                gear_atb += 0.8
            if bias.get("atb") in ("slow", "slight_slow"):
                gear_atb -= 0.8
            if bias.get("power") in ("high", "strong"):
                gear_atk += 1.5
        wc = str(it.get("weight_class") or "").lower()
        if slot == "feet":
            gear_atb += 0.5 if wc == "light" else (0.2 if wc != "heavy" else -0.3)
        if wc == "heavy" and slot == "body":
            gear_atb -= 0.4

    if off_grip == GRIP_FOCUS or main_grip == GRIP_FOCUS:
        gear_mag += 1.5

    # latent HP% — hidden; player only sees max_hp change if they notice
    if latent_hp_pct > 0 or latent_hp_flat > 0:
        max_hp = int(round(max_hp * (1.0 + min(0.35, latent_hp_pct)))) + latent_hp_flat
        # no soft note that spoils the mechanic — silent

    # latent offense % on total gear ATK (rank-scaled; observe in combat)
    if latent_atk_pct > 0 and atk > 0:
        atk = int(round(atk * (1.0 + min(0.40, latent_atk_pct))))

    # latent toughness → soft power_def (endurance, not listed on sheet)
    if latent_tough > 0:
        gear_def += min(12.0, latent_tough)

    player["equip_def"] = int(round(equip_def))
    player["equip_mdef"] = int(round(equip_mdef))
    player["latent_hp_pct_total"] = round(latent_hp_pct, 4)
    player["latent_atk_pct_total"] = round(latent_atk_pct, 4)
    player["latent_crit_total"] = round(latent_crit, 4)
    player["latent_tough_total"] = round(latent_tough, 4)
    player["latent_status_resist_total"] = round(latent_status_resist, 4)
    player["gear_def_bias"] = round(gear_def, 2)
    player["gear_mdef_bias"] = round(gear_mdef, 2)
    player["gear_atk_bias"] = round(gear_atk, 2)
    player["gear_mag_bias"] = round(gear_mag, 2)
    player["gear_atb_bias"] = round(gear_atb, 2)
    player["loadout_soft_notes"] = soft_notes

    # --- set bonuses (count across all slots) ---
    set_counts: Dict[str, int] = {}
    for slot in EQUIP_SLOTS:
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            continue
        sid = (reg.items.get(eid) or {}).get("set_id")
        if sid:
            set_counts[str(sid)] = set_counts.get(str(sid), 0) + 1

    active_sets: List[str] = []
    set_flavors: List[str] = []
    partial_sets: List[str] = []
    for set_id, cnt in set_counts.items():
        sdef = (getattr(reg, "gear_sets", None) or {}).get(set_id) or {}
        if not sdef:
            continue
        need = int(sdef.get("pieces_required", 2))
        bon = sdef.get("bonuses") or {}
        if cnt >= need:
            active_sets.append(str(sdef.get("name") or set_id))
            atk += int(bon.get("atk", 0))
            max_hp += int(bon.get("max_hp", 0))
            max_mana += int(bon.get("max_mana", 0))
            pressure += int(bon.get("pressure", 0))
            for t in sdef.get("grant_tags") or []:
                if t not in tags:
                    tags.append(str(t))
            for sk in sdef.get("grant_skills") or []:
                if sk not in skills and sk not in progression:
                    progression.append(str(sk))
            if sdef.get("flavor"):
                set_flavors.append(str(sdef["flavor"]))
        elif cnt >= 1 and need > 1:
            # EL5: partial set soft — fraction of bonuses, no full grant_skills
            frac = min(0.5, (float(cnt) / float(need)) * 0.55)
            atk += max(0, int(round(int(bon.get("atk", 0)) * frac)))
            max_hp += max(0, int(round(int(bon.get("max_hp", 0)) * frac)))
            max_mana += max(0, int(round(int(bon.get("max_mana", 0)) * frac)))
            pressure += max(0, int(round(int(bon.get("pressure", 0)) * frac)))
            # partial tags soft (not full set name)
            for t in sdef.get("grant_tags") or []:
                if t not in tags and frac >= 0.25:
                    tags.append(str(t))
            nm = str(sdef.get("name") or set_id)
            partial_sets.append(f"{nm} · เศษเซ็ต ({cnt}/{need})")
            set_flavors.append(f"เศษของ{nm}สั่นเบา — ยังไม่เต็มวง")

    # preserve HP/mana ratios roughly when max changes
    old_max_hp = max(1, int(player.get("max_hp", max_hp)))
    old_max_mp = max(1, int(player.get("max_mana", max_mana)))
    hp_ratio = float(player.get("hp", max_hp)) / old_max_hp
    mp_ratio = float(player.get("mana", max_mana)) / old_max_mp

    player["bonus_atk"] = atk
    player["max_hp"] = max_hp
    player["max_mana"] = max_mana
    player["pressure"] = pressure
    player["hp"] = max(1, min(max_hp, int(round(max_hp * hp_ratio))))
    player["mana"] = max(0, min(max_mana, int(round(max_mana * mp_ratio))))
    player["skills"] = list(dict.fromkeys(skills + progression + ["guard_basic"]))
    if "guard_basic" not in player["skills"]:
        player["skills"].append("guard_basic")
    player["gear_tags"] = tags
    player["on_hit_effects"] = on_hit
    player["active_sets"] = active_sets
    player["set_flavors"] = set_flavors
    player["partial_sets"] = partial_sets
    # DD5 lite: soft status resist from gear (hidden — feeds resist_chance)
    gear_sr = 0.0
    gear_sr += min(0.10, float(player.get("gear_def_bias") or 0) / 80.0)
    gear_sr += min(0.08, float(player.get("gear_mdef_bias") or 0) / 90.0)
    if "shield" in tags or off_grip == GRIP_SHIELD:
        gear_sr += 0.03
    if "holy" in tags:
        gear_sr += 0.04
    # per-item bias status_resist
    for slot in EQUIP_SLOTS:
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            continue
        bias = (reg.items.get(eid) or {}).get("bias") or {}
        if isinstance(bias, dict):
            sr_b = bias.get("status_resist")
            if sr_b == "strong":
                gear_sr += 0.05
            elif sr_b == "slight":
                gear_sr += 0.02
            elif sr_b == "mid":
                gear_sr += 0.035
    # latent resist from pieces (rank-scaled; never listed on examine)
    gear_sr += min(0.12, float(latent_status_resist))
    player["gear_status_resist"] = round(min(0.28, gear_sr), 4)

    # EQ-W/G/A: weight · stance · climate context (before power fold)
    try:
        from game.domain.loadout_context import recompute_loadout_context

        recompute_loadout_context(player, reg, area_id=str(player.get("location") or ""))
        # merge context soft notes into loadout notes (unique)
        ctx = list(player.get("loadout_context_notes") or [])
        base_notes = list(player.get("loadout_soft_notes") or [])
        for n in ctx:
            if n not in base_notes:
                base_notes.append(n)
        player["loadout_soft_notes"] = base_notes[:8]
    except Exception:
        pass

    # fold EL3 gear bias into power_def / power_mdef (DD1)
    try:
        from game.domain.progression import recompute_powers

        recompute_powers(player, reg)
        # latent crit from weapons (hidden; observe critical hits)
        if latent_crit > 0:
            player["power_crit"] = min(
                65.0, float(player.get("power_crit") or 0) + min(18.0, latent_crit)
            )
            player["crit_chance"] = min(
                55.0,
                float(player.get("crit_chance") or 5.0) + min(12.0, latent_crit * 0.55),
            )
        # climate def/mdef soft mult on power
        clim = player.get("climate_mults") or {}
        if clim:
            player["power_def"] = float(player.get("power_def") or 5) * float(
                clim.get("def") or 1.0
            )
            player["power_mdef"] = float(player.get("power_mdef") or 5) * float(
                clim.get("mdef") or 1.0
            )
    except Exception:
        # fallback without full progression
        player["power_def"] = float(player.get("power_def") or 5.0) + float(
            player.get("gear_def_bias") or 0
        )
        base_m = float(player.get("power_mag") or player.get("power_mdef") or 5.0)
        player["power_mdef"] = base_m * 0.85 + float(player.get("gear_mdef_bias") or 0)
        if latent_crit > 0:
            player["crit_chance"] = min(
                55.0,
                float(player.get("crit_chance") or 5.0) + min(12.0, latent_crit * 0.55),
            )


def _return_equipped_to_bag(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> None:
    """Move currently equipped piece on slot back to bag (no recompute)."""
    from game.domain.rarity import (
        append_item_rarity,
        display_item_name,
        equip_rarity_for_slot,
        item_default_rarity,
    )

    slot = normalize_slot(slot)
    old = (player.get("equip_ids") or {}).get(slot)
    if not old:
        return
    old_r = equip_rarity_for_slot(player, slot)
    old_eq_inst = (player.get("equip_instances") or {}).get(slot)
    ids = list(player.get("inventory_ids") or [])
    ids.append(old)
    player["inventory_ids"] = ids
    append_item_rarity(
        player, old_r or item_default_rarity(reg.items.get(old) or {}, reg)
    )
    old_name = (reg.items.get(old) or {}).get("name", old)
    inv = list(player.get("inventory") or [])
    inv.append(display_item_name(str(old_name), old_r or "common", reg))
    player["inventory"] = inv
    for cid in (player.get("sockets") or {}).get(slot) or []:
        if cid:
            bag = list(player.get("card_bag") or [])
            bag.append(cid)
            player["card_bag"] = bag
    player["cards"] = [
        str((reg.cards.get(c) or {}).get("name", c)) for c in (player.get("card_bag") or [])
    ]
    try:
        from game.domain.item_instances import ensure_item_instances, make_instance

        bag_items = list(player.get("inventory_items") or [])
        if old_eq_inst and isinstance(old_eq_inst, dict):
            back = dict(old_eq_inst)
            back["location"] = "bag"
            bag_items.append(back)
        else:
            bag_items.append(
                make_instance(
                    str(old),
                    player,
                    reg,
                    rarity=str(old_r or "common"),
                    location="bag",
                )
            )
        player["inventory_items"] = bag_items
        ensure_item_instances(player, reg)
    except Exception:
        pass
    eq = dict(player.get("equip_ids") or {})
    eq[slot] = None
    player["equip_ids"] = eq
    er = dict(player.get("equip_rarities") or {})
    er[slot] = None
    player["equip_rarities"] = er
    ups = dict(player.get("upgrade_levels") or {})
    ups[slot] = 0
    player["upgrade_levels"] = ups
    player.setdefault("sockets", {})[slot] = []
    eqi = dict(player.get("equip_instances") or {})
    eqi[slot] = None
    player["equip_instances"] = eqi


def resolve_equip_target(
    player: Mapping[str, Any],
    it: Mapping[str, Any],
    reg: DataRegistry,
    *,
    target_slot: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Pick loadout slot for item. Returns (slot, error_message).
    EL1 grip rules: two_hand locks off; shield off only; dual main+off one_hand.
    """
    allowed = allowed_slots_for_item(it)
    grip = item_grip(it)
    main_id = (player.get("equip_ids") or {}).get("main_hand")
    main_it = reg.items.get(main_id) if main_id else None
    main_grip = item_grip(main_it) if main_it else None

    if target_slot:
        ts = normalize_slot(target_slot)
        if ts not in allowed:
            return None, f"ชิ้นนี้ใส่{SLOT_LABEL_TH.get(ts, ts)}ไม่ได้"
        if ts == "off_hand" and main_grip == GRIP_TWO_HAND:
            return None, "ดาบใหญ่ต้องการสองมือ — ถอดมือหลักก่อนหรือใช้โล่/คู่ไม่ได้"
        if grip == GRIP_TWO_HAND and ts != "main_hand":
            return None, "อาวุธสองมือใส่ได้แค่มือหลัก"
        return ts, None

    # auto target
    if grip == GRIP_SHIELD:
        if main_grip == GRIP_TWO_HAND:
            return None, "ถือสองมืออยู่ — ใส่โล่ไม่ได้ (ถอดดาบใหญ่ก่อน)"
        return "off_hand", None
    if grip == GRIP_TWO_HAND:
        return "main_hand", None
    if grip == GRIP_FOCUS:
        if main_grip == GRIP_TWO_HAND:
            return None, "ถือสองมืออยู่ — ใส่โฟกัสมือรองไม่ได้"
        # prefer off if main has weapon
        if main_id and not (player.get("equip_ids") or {}).get("off_hand"):
            return "off_hand", None
        if "main_hand" in allowed and not main_id:
            return "main_hand", None
        return "off_hand" if "off_hand" in allowed else allowed[0], None
    if grip == GRIP_ONE_HAND:
        if "main_hand" not in allowed and "off_hand" in allowed:
            if main_grip == GRIP_TWO_HAND:
                return None, "ถือสองมืออยู่ — ใส่มีดมือรองไม่ได้"
            return "off_hand", None
        # auto dual: main occupied by one_hand, off empty → off
        off_id = (player.get("equip_ids") or {}).get("off_hand")
        if main_id and main_grip == GRIP_ONE_HAND and not off_id and "off_hand" in allowed:
            return "off_hand", None
        if main_grip == GRIP_TWO_HAND and not main_id:
            pass
        return "main_hand" if "main_hand" in allowed else allowed[0], None
    # armor / acc
    base = item_base_slot(it)
    if base in EQUIP_SLOTS:
        return base, None
    return allowed[0] if allowed else None, "สวมช่องนี้ไม่ได้"


def equip_item(
    player: MutableMapping[str, Any],
    item_id: str,
    reg: DataRegistry,
    *,
    target_slot: Optional[str] = None,
) -> str:
    from game.domain.rarity import (
        ensure_inventory_rarity,
        rarity_of_inventory_index,
    )

    ensure_gear_fields(player)
    ensure_inventory_rarity(player)
    it = reg.items.get(item_id)
    if not it or it.get("kind") != "equipment":
        return "ไม่ใช่อุปกรณ์"
    if item_id not in (player.get("inventory_ids") or []):
        return "ไม่มีไอเทมนี้ในคลัง"

    slot, err = resolve_equip_target(player, it, reg, target_slot=target_slot)
    if err or not slot:
        return err or "สวมช่องนี้ไม่ได้"
    slot = normalize_slot(slot)
    grip = item_grip(it)

    soft_extra: List[str] = []
    # two_hand: force clear off_hand
    if grip == GRIP_TWO_HAND or slot == "main_hand" and grip == GRIP_TWO_HAND:
        off_id = (player.get("equip_ids") or {}).get("off_hand")
        if off_id:
            _return_equipped_to_bag(player, "off_hand", reg)
            soft_extra.append("ต้องใช้สองมือ — ถอดของมือรองกลับกระเป๋า")

    # capture rarity + instance of the piece being equipped
    idx = list(player.get("inventory_ids") or []).index(item_id)
    new_rarity = rarity_of_inventory_index(player, idx)
    moved_inst = None
    try:
        from game.domain.item_instances import ensure_item_instances, pop_instance_at

        ensure_item_instances(player, reg)
        items = list(player.get("inventory_items") or [])
        if 0 <= idx < len(items) and str(items[idx].get("template_id")) == str(item_id):
            moved_inst = pop_instance_at(player, idx, reg)
        else:
            remove_inventory_id(player, item_id, reg)
            ensure_item_instances(player, reg)
    except Exception:
        remove_inventory_id(player, item_id, reg)
        moved_inst = None

    # unequip old on target slot
    if (player.get("equip_ids") or {}).get(slot):
        _return_equipped_to_bag(player, slot, reg)

    player.setdefault("equip_ids", {})[slot] = item_id
    er = dict(player.get("equip_rarities") or {})
    er[slot] = new_rarity
    player["equip_rarities"] = er
    n = int(it.get("sockets", 0))
    if moved_inst and moved_inst.get("sockets"):
        player.setdefault("sockets", {})[slot] = list(moved_inst.get("sockets") or [None] * n)
    else:
        player.setdefault("sockets", {})[slot] = [None] * n
    ups = dict(player.get("upgrade_levels") or {})
    if moved_inst and int(moved_inst.get("upgrade") or 0) > 0:
        ups[slot] = int(moved_inst.get("upgrade") or 0)
    else:
        ups[slot] = 0
    player["upgrade_levels"] = ups
    try:
        from game.domain.item_instances import ensure_item_instances, make_instance

        eqi = dict(player.get("equip_instances") or {})
        if moved_inst:
            moved_inst = dict(moved_inst)
            moved_inst["location"] = f"equip:{slot}"
            moved_inst["rarity"] = new_rarity
            eqi[slot] = moved_inst
        else:
            eqi[slot] = make_instance(
                item_id,
                player,
                reg,
                rarity=new_rarity,
                upgrade=int(ups.get(slot) or 0),
                sockets=list((player.get("sockets") or {}).get(slot) or []),
                location=f"equip:{slot}",
            )
        player["equip_instances"] = eqi
        ensure_item_instances(player, reg)
    except Exception:
        pass
    recompute_stats(player, reg)
    from game.domain.rarity import display_item_name as _din2

    lab = SLOT_LABEL_TH.get(slot, slot)
    msg = f"สวม {_din2(str(it.get('name')), new_rarity, reg)} ({lab}) แล้ว · ช่องการ์ด {n}"
    for bit in soft_extra:
        msg += f" · {bit}"
    notes = player.get("loadout_soft_notes") or []
    if notes and not soft_extra:
        msg += f" · {notes[0]}"
    try:
        from game.domain.soft_feel import soft_equip_feel

        for feel in soft_equip_feel(player, reg, slot=slot, item_id=item_id):
            msg += f"\n  {feel}"
    except Exception:
        pass
    return msg


def unequip_slot(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> str:
    """Move equipped piece back to inventory; cards in sockets return to card_bag."""
    from game.domain.rarity import (
        append_item_rarity,
        display_item_name,
        equip_rarity_for_slot,
        ensure_inventory_rarity,
    )

    ensure_gear_fields(player)
    ensure_inventory_rarity(player)
    slot = normalize_slot(slot)
    if slot not in EQUIP_SLOTS:
        return "ช่องไม่ถูกต้อง"
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return f"ไม่มี{_slot_label(slot)}สวมอยู่"
    rid = equip_rarity_for_slot(player, slot)
    it = reg.items.get(eid) or {}
    # return socketed cards
    for cid in (player.get("sockets") or {}).get(slot) or []:
        if cid:
            bag = list(player.get("card_bag") or [])
            bag.append(cid)
            player["card_bag"] = bag
    player.setdefault("sockets", {})[slot] = []
    # inventory
    ids = list(player.get("inventory_ids") or [])
    ids.append(eid)
    player["inventory_ids"] = ids
    append_item_rarity(player, rid or "common")
    inv = list(player.get("inventory") or [])
    inv.append(display_item_name(str(it.get("name") or eid), rid or "common", reg))
    player["inventory"] = inv
    # clear equip
    eq = dict(player.get("equip_ids") or {})
    eq[slot] = None
    player["equip_ids"] = eq
    er = dict(player.get("equip_rarities") or {})
    er[slot] = None
    player["equip_rarities"] = er
    ups = dict(player.get("upgrade_levels") or {})
    ups[slot] = 0
    player["upgrade_levels"] = ups
    player["cards"] = [
        str((reg.cards.get(c) or {}).get("name", c)) for c in (player.get("card_bag") or [])
    ]
    recompute_stats(player, reg)
    try:
        from game.domain.item_instances import ensure_item_instances

        player["inventory_items"] = []
        player["equip_instances"] = dict(player.get("equip_instances") or {})
        player["equip_instances"][slot] = None
        ensure_item_instances(player, reg)
    except Exception:
        pass
    from game.domain.item_codes import item_code

    code = item_code(str(eid), reg)
    shown = display_item_name(str(it.get("name") or eid), rid or "common", reg)
    return f"ถอด {code} {shown} กลับเข้ากระเป๋าแล้ว"


def sell_equipped_slot(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> str:
    """Sell currently equipped piece for world money (no shop tax UI)."""
    from game.domain.balance import sell_price
    from game.domain.item_codes import item_code
    from game.domain.rarity import display_item_name, equip_rarity_for_slot

    ensure_gear_fields(player)
    slot = normalize_slot(slot)
    if slot not in EQUIP_SLOTS:
        return "ช่องไม่ถูกต้อง"
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return f"ไม่มี{_slot_label(slot)}สวมอยู่"
    it = reg.items.get(eid) or {}
    rid = equip_rarity_for_slot(player, slot)
    base = int(it.get("price_world") or 40)
    pay = sell_price(base, reg, player, rarity=rid)
    # return socket cards first
    for cid in (player.get("sockets") or {}).get(slot) or []:
        if cid:
            bag = list(player.get("card_bag") or [])
            bag.append(cid)
            player["card_bag"] = bag
    player.setdefault("sockets", {})[slot] = []
    eq = dict(player.get("equip_ids") or {})
    eq[slot] = None
    player["equip_ids"] = eq
    er = dict(player.get("equip_rarities") or {})
    er[slot] = None
    player["equip_rarities"] = er
    ups = dict(player.get("upgrade_levels") or {})
    ups[slot] = 0
    player["upgrade_levels"] = ups
    player["money_world"] = int(player.get("money_world") or 0) + pay
    recompute_stats(player, reg)
    shown = display_item_name(str(it.get("name") or eid), rid, reg)
    return f"ขาย {item_code(str(eid), reg)} {shown} ได้เงินโลก +{pay}"


def discard_equipped_slot(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> str:
    """Destroy equipped piece permanently; socket cards return to bag."""
    from game.domain.item_codes import item_code
    from game.domain.rarity import display_item_name, equip_rarity_for_slot

    ensure_gear_fields(player)
    slot = normalize_slot(slot)
    if slot not in EQUIP_SLOTS:
        return "ช่องไม่ถูกต้อง"
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return f"ไม่มี{_slot_label(slot)}สวมอยู่"
    it = reg.items.get(eid) or {}
    rid = equip_rarity_for_slot(player, slot)
    for cid in (player.get("sockets") or {}).get(slot) or []:
        if cid:
            bag = list(player.get("card_bag") or [])
            bag.append(cid)
            player["card_bag"] = bag
    player.setdefault("sockets", {})[slot] = []
    eq = dict(player.get("equip_ids") or {})
    eq[slot] = None
    player["equip_ids"] = eq
    er = dict(player.get("equip_rarities") or {})
    er[slot] = None
    player["equip_rarities"] = er
    ups = dict(player.get("upgrade_levels") or {})
    ups[slot] = 0
    player["upgrade_levels"] = ups
    recompute_stats(player, reg)
    shown = display_item_name(str(it.get("name") or eid), rid, reg)
    return f"ทิ้ง {item_code(str(eid), reg)} {shown} แล้ว (หายถาวร)"


def _slot_label(slot: str) -> str:
    return SLOT_LABEL_TH.get(normalize_slot(slot), slot)


def socket_card(
    player: MutableMapping[str, Any],
    slot: str,
    socket_index: int,
    card_id: str,
    reg: DataRegistry,
) -> str:
    ensure_gear_fields(player)
    slot = normalize_slot(slot)
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return f"ยังไม่มี{_slot_label(slot)}"
    it = reg.items.get(eid) or {}
    socks = list((player.get("sockets") or {}).get(slot) or [])
    n = int(it.get("sockets", 0))
    if socket_index < 0 or socket_index >= n:
        return "ช่องไม่ถูกต้อง"
    if card_id not in (player.get("card_bag") or []):
        return "ไม่มีการ์ดนี้"
    card = reg.cards.get(card_id) or {}
    compat = list(card.get("compatible") or ["weapon", "armor"])
    if not card_slot_matches(slot, compat):
        return f"การ์ดนี้ใส่{_slot_label(slot)}ไม่ได้"

    # return previous card
    prev = socks[socket_index] if socket_index < len(socks) else None
    bag = list(player.get("card_bag") or [])
    bag.remove(card_id)
    if prev:
        bag.append(prev)
    player["card_bag"] = bag

    while len(socks) < n:
        socks.append(None)
    socks[socket_index] = card_id
    player.setdefault("sockets", {})[slot] = socks

    # sync display cards list roughly
    player["cards"] = [
        str((reg.cards.get(c) or {}).get("name", c)) for c in bag
    ]
    recompute_stats(player, reg)
    return f"ใส่ {(card.get('name') or card_id)} ใน {slot} ช่อง {socket_index + 1}"


def unsocket_card(player: MutableMapping[str, Any], slot: str, socket_index: int, reg: DataRegistry) -> str:
    ensure_gear_fields(player)
    slot = normalize_slot(slot)
    socks = list((player.get("sockets") or {}).get(slot) or [])
    if socket_index < 0 or socket_index >= len(socks) or not socks[socket_index]:
        return "ช่องว่าง"
    cid = socks[socket_index]
    socks[socket_index] = None
    player.setdefault("sockets", {})[slot] = socks
    bag = list(player.get("card_bag") or [])
    bag.append(cid)
    player["card_bag"] = bag
    player["cards"] = [str((reg.cards.get(c) or {}).get("name", c)) for c in bag]
    recompute_stats(player, reg)
    return f"ถอดการ์ดจาก {_slot_label(slot)} ช่อง {socket_index + 1}"


def gear_attack_bonus_elements(player: Mapping[str, Any]) -> List[str]:
    return list(player.get("gear_tags") or [])


def count_materials(player: Mapping[str, Any], mat_id: str) -> int:
    return sum(1 for x in (player.get("inventory_ids") or []) if x == mat_id)


def consume_materials(player: MutableMapping[str, Any], mat_id: str, n: int, reg: DataRegistry) -> bool:
    if count_materials(player, mat_id) < n:
        return False
    for _ in range(n):
        if not remove_inventory_id(player, mat_id, reg):
            return False
    return True


def upgrade_cost(
    slot: str,
    level: int,
    *,
    reg: Optional[DataRegistry] = None,
    rarity_id: str = "common",
) -> Dict[str, int]:
    """
    Material costs for next upgrade — rises with +level AND gear rank.
    Early (+0→+1, +1→+2) soft so starters can try once;
    high rank pieces cost more money/mats (precious to reforge).
    """
    from game.domain.rarity import tier_rank

    nxt = level + 1
    ns = normalize_slot(slot)
    acc = 0.85 if ns in ("acc_1", "accessory") else 1.0
    rk = int(tier_rank(reg, rarity_id) or 1)
    # rank cost mult: common 1.0 … mythic ~1.7
    r_mult = 0.92 + rk * 0.08
    # Early curve (playtest: first upgrade reachable ~40–80 world gold on common)
    if nxt == 1:
        money = int(40 * acc * r_mult)
        um = 1
        rm = 1 if rk >= 6 else 0
    elif nxt == 2:
        money = int(70 * acc * r_mult)
        um = 1 + (1 if rk >= 5 else 0)
        rm = 1 if rk >= 5 else 0
    elif nxt == 3:
        money = int(110 * acc * r_mult)
        um = max(1, int(2 * acc)) + (1 if rk >= 4 else 0)
        rm = 1 if rk >= 4 else 0
    else:
        # mid/late: steeper money after +6 (risk + cost pressure)
        money = int((50 + nxt * 55 + (nxt ** 2) * 8) * acc * r_mult)
        if nxt >= 7:
            money = int(money * (1.0 + 0.08 * (nxt - 6)))
        um = max(
            1,
            int(
                (1 + nxt // 2 + (1 if nxt >= 5 else 0) + (1 if nxt >= 8 else 0)) * acc
            ),
        )
        if rk >= 4:
            um += 1
        if rk >= 6:
            um += 1
        if nxt >= 8:
            um += 1
        rm = (1 if nxt >= 4 else 0) + (1 if nxt >= 6 else 0) + (1 if nxt >= 9 else 0)
        if rk >= 4 and nxt >= 3:
            rm = max(rm, 1)
        if rk >= 6:
            rm += 1
        if nxt >= 8:
            rm += 1
    return {
        "upgrade_mat": int(um),
        "rare_mat": int(rm),
        "money": int(money),
    }


def destroy_equipped_piece(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> str:
    """
    Break equipped piece on upgrade catastrophe — gear is gone.
    Socketed cards return to bag; piece itself is destroyed.
    """
    ensure_gear_fields(player)
    slot = normalize_slot(slot)
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return "ไม่มีชิ้นในช่อง"
    name = str((reg.items.get(eid) or {}).get("name") or eid)
    # return socketed cards only
    for cid in (player.get("sockets") or {}).get(slot) or []:
        if cid:
            bag = list(player.get("card_bag") or [])
            bag.append(cid)
            player["card_bag"] = bag
    player["cards"] = [
        str((reg.cards.get(c) or {}).get("name", c)) for c in (player.get("card_bag") or [])
    ]
    eids = dict(player.get("equip_ids") or {})
    eids[slot] = None
    player["equip_ids"] = eids
    player.setdefault("equip", {})[slot] = None
    er = dict(player.get("equip_rarities") or {})
    er.pop(slot, None)
    player["equip_rarities"] = er
    ups = dict(player.get("upgrade_levels") or {})
    ups.pop(slot, None)
    player["upgrade_levels"] = ups
    socks = dict(player.get("sockets") or {})
    socks[slot] = []
    player["sockets"] = socks
    ein = dict(player.get("equip_instances") or {})
    ein.pop(slot, None)
    player["equip_instances"] = ein
    # clear two-hand lock soft
    if slot == "main_hand":
        pass
    recompute_stats(player, reg)
    return name


def upgrade_equipped(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
    rng: Optional[Any] = None,
) -> str:
    """Route to opaque risk upgrade (fail / downgrade / break + protect scrolls)."""
    from game.domain.inventory_sys import upgrade_equipped_opaque

    return upgrade_equipped_opaque(player, slot, reg, rng=rng)


def describe_loadout(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    """
    Detailed loadout summary for gear menu option 8 — sectioned soft UI.
    No raw %; upgrade readiness is soft (พอ/ยังไม่พอ).
    """
    ensure_gear_fields(player)  # type: ignore
    try:
        from game.domain.rarity import display_item_name, equip_rarity_for_slot
    except Exception:
        display_item_name = None  # type: ignore
        equip_rarity_for_slot = None  # type: ignore

    um = count_materials(player, "upgrade_mat")
    rm = count_materials(player, "rare_mat")
    money = int(player.get("money_world") or 0)

    lines: List[str] = [
        " เกียร์ละเอียด",
        "---",
        " สวมอยู่",
    ]
    worn = 0
    empty: List[str] = []

    for slot, lab in EQUIP_SLOT_UI:
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            if slot == "off_hand":
                mid = (player.get("equip_ids") or {}).get("main_hand")
                if mid and item_grip(reg.items.get(mid) or {}) == GRIP_TWO_HAND:
                    lines.append(f"  {lab:<10} (ล็อก · สองมือ)")
                    worn += 1  # slot accounted
                    continue
            empty.append(lab)
            continue
        worn += 1
        it = reg.items.get(eid) or {}
        raw_name = str(it.get("name") or eid)
        rid = "common"
        if equip_rarity_for_slot is not None:
            try:
                rid = str(equip_rarity_for_slot(player, slot) or "common")
            except Exception:
                rid = str(it.get("rarity") or "common")
        if display_item_name is not None:
            try:
                name = display_item_name(raw_name, rid, reg)
            except Exception:
                name = raw_name
        else:
            name = raw_name
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        up_bit = f" +{up}" if up else ""
        grip = item_grip(it)
        grip_bit = ""
        if grip == GRIP_TWO_HAND:
            grip_bit = " ·สองมือ"
        elif grip == GRIP_SHIELD:
            grip_bit = " ·โล่"
        elif grip == GRIP_FOCUS:
            grip_bit = " ·โฟกัส"
        lines.append(f"  {lab:<10} {name}{up_bit}{grip_bit}")
        try:
            from game.domain.rarity import equip_rarity_for_slot, scaled_item_stats

            rid = equip_rarity_for_slot(player, slot)
            st = scaled_item_stats(it, rid, reg, upgrade_level=up, slot=slot)
            def_hint = soft_piece_defense_hint(it, slot=slot, grip=grip, st=st)
        except Exception:
            def_hint = soft_piece_defense_hint(it, slot=slot, grip=grip)
        if def_hint:
            lines.append(f"             {def_hint}")

        socks = list((player.get("sockets") or {}).get(slot) or [])
        if socks:
            parts = []
            filled = 0
            for cid in socks:
                if cid:
                    filled += 1
                    parts.append(str((reg.cards.get(cid) or {}).get("name") or cid))
                else:
                    parts.append("ว่าง")
            lines.append(f"             ซ็อกเก็ต {filled}/{len(socks)}: " + " · ".join(parts))

        cost = upgrade_cost(slot, up, reg=reg, rarity_id=str(rid or "common"))
        need_u = int(cost.get("upgrade_mat") or 0)
        need_r = int(cost.get("rare_mat") or 0)
        need_m = int(cost.get("money") or 0)
        can = money >= need_m and um >= need_u and rm >= need_r
        feel = "พออัป" if can else "ยังไม่พอ"
        cost_bits = [f"เงิน {need_m}", f"วัสดุ {need_u}"]
        if need_r:
            cost_bits.append(f"หายาก {need_r}")
        lines.append(f"             อัปถัดไป: {' · '.join(cost_bits)}  ({feel})")

    if empty:
        lines.append("---")
        lines.append(" ช่องว่าง: " + " · ".join(empty))

    soft_notes = list(player.get("loadout_soft_notes") or [])
    if soft_notes:
        lines.append("---")
        lines.append(" รู้สึกจากชุด")
        for note in soft_notes:
            lines.append(f"  「{note}」")

    lines.append("---")
    lines.append(" คลังเกียร์")
    bag = list(player.get("card_bag") or [])
    if bag:
        names = [(reg.cards.get(c) or {}).get("name", c) for c in bag]
        lines.append(f"  การ์ดในถุง ({len(bag)}): " + " · ".join(str(n) for n in names))
    else:
        lines.append("  การ์ดในถุง: (ว่าง)")
    have_pb = count_materials(player, "scroll_guard_break")
    have_pd = count_materials(player, "scroll_guard_level")
    lines.append(f"  วัสดุอัป x{um}  ·  หายาก x{rm}  ·  เงินโลก {money}")
    lines.append(f"  ม้วนกันลดระดับ x{have_pd}  ·  ม้วนกันพัง x{have_pb}")
    lines.append("  (ม้วนกันต้อง rank ≥ ชิ้นที่อัป · rank สูงใช้กับชิ้นต่ำได้)")

    lines.append("---")
    lines.append(" พลังรวม (จากเกียร์+สถานะ)")
    lines.append(
        f"  ATK {player.get('bonus_atk', 0)}  ·  "
        f"HP {player.get('hp')}/{player.get('max_hp')}  ·  "
        f"MP {player.get('mana')}/{player.get('max_mana')}"
    )
    lines.append(f"  ป้องกันรวม  {soft_guard_summary(player)}")
    lines.append("  (อาวุธโชว์โจมตี · เกราะโชว์กัน · พลังแฝงต้องสังเกตเอง)")
    lines.append("  (อัปเสี่ยงล้ม/ลด/+พัง · Rank สูงเสี่ยงและแพงกว่า · ม้วน rank ตรง)")
    tags = list(player.get("gear_tags") or [])
    if tags:
        # soft: map known tags lightly
        soft_tags = []
        for t in tags:
            ts = str(t)
            soft_tags.append(
                {
                    "fire": "ไฟ",
                    "water": "น้ำ",
                    "wind": "ลม",
                    "shadow": "เงา",
                    "holy": "แสง",
                    "arcane": "เวท",
                    "physical": "กาย",
                }.get(ts, ts)
            )
        lines.append("  แท็ก: " + " · ".join(soft_tags))

    if player.get("active_sets"):
        lines.append("---")
        lines.append(" เซ็ตที่สั่น")
        for sname in player.get("active_sets") or []:
            lines.append(f"  ◆ {sname}")
        for fl in player.get("set_flavors") or []:
            lines.append(f"    “{fl}”")

    lines.append("---")
    lines.append(" ใบ้: อัปใช้เมนู 4 · ใส่การ์ดเมนู 2 · หาวัสดุจากลูท/ร้าน")
    return lines

