"""
Bag, examine, equip panel, opaque upgrade, loot choice.
Player sees soft item properties — upgrade rates/material formulas partly hidden.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry
from game.domain.equipment import (
    add_item,
    count_materials,
    ensure_gear_fields,
    equip_item,
    item_by_id,
    recompute_stats,
    remove_inventory_id,
    upgrade_cost,
)


BAG_SOFT_CAP = 40


def ensure_bag(player: MutableMapping[str, Any]) -> None:
    ensure_gear_fields(player)
    player.setdefault("inventory_ids", [])
    player.setdefault("inventory", [])
    player.setdefault("card_bag", [])
    player.setdefault("bag_cap", BAG_SOFT_CAP)
    player.setdefault("inventory_qty", [])
    try:
        from game.domain.bag_stack import ensure_inventory_qty

        ensure_inventory_qty(player)
    except Exception:
        pass


# Legacy Thai display names → canonical item ids (victory loot bug repair)
_LEGACY_NAME_TO_ID = {
    "ยา HP": "potion_hp",
    "ยา Mana": "potion_mana",
    "ยา HP ขนาดเล็ก": "potion_hp_small",
    "ดาบเหล็ก": "iron_sword",
    "เกราะหนัง": "leather_armor",
    "วัสดุอัพเกรด": "upgrade_mat",
    "วัสดุอัพ": "upgrade_mat",
}


def _strip_rarity_suffix(name: str) -> str:
    """Remove trailing rarity tags like ' [○ธรรมดา]' from display names."""
    s = str(name or "").strip()
    if " [" in s and s.endswith("]"):
        s = s[: s.rfind(" [")].strip()
    return s


def build_name_to_item_id(reg: DataRegistry) -> Dict[str, str]:
    m = dict(_LEGACY_NAME_TO_ID)
    for iid, it in (reg.items or {}).items():
        nm = str(it.get("name") or "")
        if nm:
            m[nm] = iid
    for cid, it in (reg.cards or {}).items():
        nm = str(it.get("name") or "")
        if nm:
            m[nm] = cid
    return m


def sanitize_inventory(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> List[str]:
    """
    Repair inventory/inventory_ids/inventory_rarities parallelism.
    - Pad/truncate rarities to ids
    - Map orphan display names (no id) to known item ids
    - Drop empty slots / unresolvable ghosts
    Returns human-readable repair notes (may be empty).
    """
    ensure_bag(player)
    notes: List[str] = []
    inv = list(player.get("inventory") or [])
    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    # after list repair we'll ensure instances + stack collapse

    # pad ids to inv length with empty for orphans
    while len(ids) < len(inv):
        ids.append("")
    # if ids longer than inv, pad inv with id names later
    while len(inv) < len(ids):
        inv.append("")

    name_map = build_name_to_item_id(reg) if reg is not None else dict(_LEGACY_NAME_TO_ID)
    new_inv: List[str] = []
    new_ids: List[str] = []
    new_rar: List[str] = []

    for i in range(max(len(inv), len(ids))):
        name = str(inv[i] if i < len(inv) else "")
        iid = str(ids[i] if i < len(ids) else "")
        rar = str(rares[i] if i < len(rares) else "common") or "common"

        if reg is not None and iid and iid in reg.items:
            it = reg.items[iid]
            from game.domain.rarity import display_item_name

            shown = display_item_name(str(it.get("name", iid)), rar, reg)
            new_inv.append(shown)
            new_ids.append(iid)
            new_rar.append(rar)
            continue
        if reg is not None and iid and iid in reg.cards:
            # cards should live in card_bag; migrate
            bag = list(player.get("card_bag") or [])
            if iid not in bag:
                bag.append(iid)
            player["card_bag"] = bag
            notes.append(f"ย้ายการ์ด {iid} เข้าถุงการ์ด")
            continue

        # orphan name without valid id
        base = _strip_rarity_suffix(name)
        mapped = name_map.get(base) or name_map.get(name)
        if mapped and reg is not None and (mapped in reg.items or mapped in reg.cards):
            if mapped in (reg.cards or {}):
                bag = list(player.get("card_bag") or [])
                bag.append(mapped)
                player["card_bag"] = bag
                notes.append(f"ซ่อมการ์ดจากชื่อ「{base}」")
                continue
            it = reg.items[mapped]
            from game.domain.rarity import display_item_name

            shown = display_item_name(str(it.get("name", mapped)), rar, reg)
            new_inv.append(shown)
            new_ids.append(mapped)
            new_rar.append(rar)
            notes.append(f"ซ่อมคลัง: 「{base}」→ {mapped}")
            continue

        if not name and not iid:
            continue
        # unresolvable — drop with note
        if name or iid:
            notes.append(f"ลบของที่ id หาย: {name or iid}")

    player["inventory"] = new_inv
    player["inventory_ids"] = new_ids
    player["inventory_rarities"] = new_rar
    # Prefer inventory_items as SoT when already present; else rebuild from ids
    try:
        from game.domain.item_instances import (
            ensure_item_instances,
            sync_canonical_inventory,
            sync_legacy_from_instances,
        )

        existing = [
            x
            for x in (player.get("inventory_items") or [])
            if isinstance(x, dict) and x.get("template_id")
        ]
        if existing and len(existing) == len(new_ids):
            # keep inst_ids; realign templates to sanitized ids
            for i, tid in enumerate(new_ids):
                if i < len(existing):
                    existing[i]["template_id"] = tid
                    existing[i]["rarity"] = new_rar[i] if i < len(new_rar) else "common"
                    existing[i]["location"] = "bag"
            player["inventory_items"] = existing
            sync_legacy_from_instances(player, reg)
            ensure_item_instances(player, reg)
        elif existing and not new_ids:
            # instances win if sanitize dropped broken legacy only
            player["inventory_items"] = existing
            sync_canonical_inventory(player, reg)
        else:
            ensure_item_instances(player, reg)
            sync_legacy_from_instances(player, reg)
    except Exception:
        pass
    # WO-INV-1: merge stackable duplicates + ensure qty parallel
    try:
        from game.domain.bag_stack import collapse_stackable_slots, ensure_inventory_qty

        freed = collapse_stackable_slots(player, reg)
        ensure_inventory_qty(player)
        if freed > 0:
            notes.append(f"จัดกองของซ้ำ · ว่างขึ้น {freed} ช่อง")
    except Exception:
        pass
    return notes


def bag_count(player: Mapping[str, Any]) -> int:
    """Bag *slots* used (each stack = 1 slot; each card = 1 slot)."""
    try:
        from game.domain.bag_stack import bag_slots_used

        return bag_slots_used(player)
    except Exception:
        return len(player.get("inventory_ids") or []) + len(player.get("card_bag") or [])


# --- Categorized bag (docs/BAG_SYSTEM.md) ---

BAG_CATEGORIES = (
    "equipment",
    "food",
    "healing",
    "chest",
    "material",
    "card",
    "relic",
    "other",
)

BAG_CATEGORY_LABELS = {
    "equipment": "อุปกรณ์",
    "food": "อาหาร",
    "healing": "รักษา",
    "chest": "หีบ",
    "material": "วัตถุดิบ",
    "card": "การ์ด",
    "relic": "เรลิก",
    "other": "อื่นๆ",
}


def item_category(item_id: str, reg: DataRegistry) -> str:
    """
    Classify inventory item for bag hub.
    Returns: equipment | food | healing | material | card | relic | other
    Food (อิ่มท้อง) แยกจากยา/รักษา. Relic แยกจากเกียร์ทั่วไป (WO-INV).
    """
    iid = str(item_id or "")
    if not iid:
        return "other"
    if iid in (reg.cards or {}) or iid.startswith("card_"):
        return "card"
    it = item_by_id(reg, iid) or {}
    # WO-INV: relics before generic equipment
    try:
        from game.domain.bag_sell import is_relic_item

        if is_relic_item(iid, it):
            return "relic"
    except Exception:
        if iid.startswith("relic_") or it.get("divine_burden"):
            return "relic"
    kind = str(it.get("kind") or "")
    slot = str(it.get("slot") or "")
    from game.domain.equipment import EQUIP_SLOTS, normalize_slot

    _ns = normalize_slot(str(slot)) if slot else ""
    if kind == "equipment" or _ns in EQUIP_SLOTS or slot in ("weapon", "armor", "accessory"):
        return "equipment"
    if kind == "material" or "mat" in iid:
        return "material"
    # L1: sealed chests
    try:
        from game.domain.chest_loot import is_chest_item

        if is_chest_item(it):
            return "chest"
    except Exception:
        tags0 = it.get("tags") or []
        if isinstance(tags0, str):
            tags0 = [tags0]
        if "chest" in tags0 or it.get("chest_rank"):
            return "chest"
    # N4: food before generic healing
    try:
        from game.domain.needs import is_food_item

        if is_food_item(it):
            return "food"
    except Exception:
        tags = it.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        if "food" in tags or it.get("food_tier") or it.get("hunger_relief"):
            return "food"
        nm = str(it.get("name") or "")
        if any(k in nm for k in ("เสบียง", "ขนม", "อาหาร", "สตูว์", "สำรับ")):
            return "food"
    if any(
        it.get(k)
        for k in (
            "heal_hp",
            "heal_mana",
            "clear_status",
            "clear_all_debuffs",
            "apply_status",
            "restore_intel",
            "boost_intel_max",
            "fill_intel",
            "recovery_kind",
            "recovery_rank",
        )
    ):
        return "healing"
    tags_rec = it.get("tags") or []
    if isinstance(tags_rec, str):
        tags_rec = [tags_rec]
    if "recovery" in tags_rec or str(iid).startswith("recovery_"):
        return "healing"
    if kind == "consumable":
        return "healing"
    if kind == "card":
        return "card"
    return "other"


def list_bag_entries(
    player: Mapping[str, Any],
    reg: DataRegistry,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List bag slots. Each entry: {index, id, name, rarity, category, meta}
    index = 0-based position in inventory_ids (for healing/equipment pops).
    category=None → all non-card inventory; category='card' → card_bag.
    """
    ensure_bag(player)  # type: ignore
    out: List[Dict[str, Any]] = []
    if category == "card":
        for i, cid in enumerate(player.get("card_bag") or []):
            c = reg.cards.get(cid) or reg.items.get(cid) or {}
            out.append(
                {
                    "index": i,
                    "id": cid,
                    "name": str(c.get("name") or cid),
                    "rarity": "common",
                    "category": "card",
                    "meta": c,
                }
            )
        return out

    ids = list(player.get("inventory_ids") or [])
    inv = list(player.get("inventory") or [])
    from game.domain.rarity import rarity_of_inventory_index, display_item_name

    from game.domain.bag_stack import qty_at

    for i, iid in enumerate(ids):
        cat = item_category(str(iid), reg)
        if category and cat != category:
            continue
        it = item_by_id(reg, str(iid)) or {}
        rid = rarity_of_inventory_index(player, i)
        raw_name = str(it.get("name") or (inv[i] if i < len(inv) else iid))
        q = qty_at(player, i)
        meta_bits = []
        chest_rank = ""
        if cat == "food":
            shown = display_item_name(raw_name, rid, reg)
            if q > 1:
                shown = f"{shown} x{q}"
            tier = it.get("food_tier")
            if tier:
                meta_bits.append(f"ชั้น{tier}")
            if it.get("hunger_relief"):
                meta_bits.append("อิ่มท้อง")
            if it.get("heal_hp"):
                meta_bits.append(f"อุ่น+{it['heal_hp']}")
        elif cat == "chest":
            # Chest display uses chest_rank (not inventory rarity) — avoid double label
            try:
                from game.domain.chest_loot import chest_rank_from_item, rank_def

                chest_rank = chest_rank_from_item(it)
                rd = rank_def(reg, chest_rank)
                sym = str(rd.get("symbol") or "□")
                rname = str(rd.get("name") or chest_rank)
                base = str(it.get("name") or "หีบ")
                # clean: "■ หายาก  ·  หีบ · หายาก  ×2"
                shown = f"{sym} {rname}"
                if q > 1:
                    shown = f"{shown}  ×{q}"
                meta_bits.append(base)
            except Exception:
                shown = str(raw_name)
                if q > 1:
                    shown = f"{shown} x{q}"
                if it.get("chest_rank"):
                    chest_rank = str(it.get("chest_rank"))
                    meta_bits.append(f"แรงก์ {chest_rank}")
        else:
            shown = display_item_name(raw_name, rid, reg)
            if q > 1:
                shown = f"{shown} x{q}"
            if it.get("recovery_kind") and it.get("recovery_rank"):
                rk = str(it.get("recovery_kind") or "").upper()
                rr = str(it.get("recovery_rank") or "").upper()
                dur = 3 if rr == "S" else 5
                meta_bits.append(f"Recovery {rk} {rr} · {dur}เทิร์น")
            if it.get("heal_hp"):
                meta_bits.append(f"HP+{it['heal_hp']}")
            if it.get("heal_mana"):
                meta_bits.append(f"MP+{it['heal_mana']}")
        if it.get("atk"):
            meta_bits.append(f"ATK+{it['atk']}")
        if it.get("slot"):
            meta_bits.append(_slot_th(str(it["slot"])))
        out.append(
            {
                "index": i,
                "id": str(iid),
                "name": shown,
                "rarity": rid,
                "qty": q,
                "category": cat,
                "meta": it,
                "hint": " · ".join(str(x) for x in meta_bits),
                "chest_rank": chest_rank,
            }
        )
    # L5: highest chest rank first (unit after sss)
    if category == "chest" and out:
        try:
            from game.domain.chest_loot import rank_order_index

            out.sort(
                key=lambda e: rank_order_index(str(e.get("chest_rank") or "common")),
                reverse=True,
            )
        except Exception:
            pass
    return out


def count_bag_categories(player: Mapping[str, Any], reg: DataRegistry) -> Dict[str, int]:
    counts = {c: 0 for c in BAG_CATEGORIES}
    for e in list_bag_entries(player, reg, None):
        cat = str(e.get("category") or "other")
        counts[cat] = counts.get(cat, 0) + 1
    counts["card"] = len(player.get("card_bag") or [])
    return counts


def format_bag_hub(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    """
    Hub lines for a box UI — sections:
      header · equipped · bag categories · tools · back
    """
    ensure_bag(player)  # type: ignore
    from game.domain.item_codes import format_bag_equip_summary_lines
    from game.domain.rarity import ensure_inventory_rarity

    ensure_inventory_rarity(player)  # type: ignore
    n = bag_count(player)
    cap = int(player.get("bag_cap") or BAG_SOFT_CAP)
    counts = count_bag_categories(player, reg)
    lines: List[str] = [
        f" กระเป๋า  ({n}/{cap})",
        "---",
        " เลือกหมวดก่อน แล้วค่อยเลือกชิ้น",
        "---",
        " สวมอยู่",
    ]
    # equip summary without its own header noise
    equip_lines = format_bag_equip_summary_lines(player, reg)
    for ln in equip_lines:
        s = str(ln)
        if "สวมอยู่" in s and ":" not in s.split("สวมอยู่")[-1][:3]:
            # skip duplicate header line from helper
            if s.strip().startswith("สวมอยู่"):
                continue
        lines.append(s if s.startswith(" ") else f" {s}")

    lines.append("---")
    lines.append(" หมวดในกระเป๋า")
    lines.extend(
        [
            f"  1  อุปกรณ์     ({counts.get('equipment', 0)})",
            f"  2  อาหาร       ({counts.get('food', 0)})     เสบียง · อิ่ม",
            f"  3  รักษา       ({counts.get('healing', 0)})     ยา · บัฟ",
            f"  4  หีบ         ({counts.get('chest', 0)})     คลัง · เปิดรางวัล",
            f"  5  วัตถุดิบ    ({counts.get('material', 0)})",
            f"  6  การ์ด       ({counts.get('card', 0)})",
            f"  7  อื่นๆ       ({counts.get('other', 0)})",
            f"  R  เรลิก       ({counts.get('relic', 0)})     ภาระเทพ · ไม่ stack",
            "---",
            " เครื่องมือ",
            "  8  เกียร์ที่สวม / ละเอียด",
            "  9  ร้านท้องถิ่น (ทางลัด)",
            "  O  จัดระเบียบ   A  ดูทั้งหมด",
            "  C  คราฟ         M  ร้าน/ตลาด     J  กระดาน",
            "---",
            "  0  กลับ",
        ]
    )
    return lines


def format_category_list(
    player: Mapping[str, Any],
    reg: DataRegistry,
    category: str,
) -> List[str]:
    label = BAG_CATEGORY_LABELS.get(category, category)
    entries = list_bag_entries(player, reg, category)
    lines: List[str] = [
        f" หมวด · {label}",
        "---",
    ]
    if category == "equipment":
        lines.append(" พิมพ์หมายเลขหรือรหัสสั้น (เช่น sw001)")
    if category == "relic":
        lines.append(" เรลิก · ภาระเทพ soft · ไม่ stack · พิมพ์หมายเลข/รหัส")
    if category == "food":
        lines.append(" กิน = อิ่มท้อง · ลดหิว (ไม่ใช่ยา)")
        try:
            from game.domain.needs import format_needs_bar_line, ensure_needs

            ensure_needs(player)  # type: ignore
            lines.append(f" {format_needs_bar_line(player)}")  # type: ignore
        except Exception:
            pass
    if category == "chest":
        try:
            from game.domain.chest_loot import format_chest_stash_summary

            for ln in format_chest_stash_summary(player, reg):
                lines.append(ln)
        except Exception:
            lines.append(" หีบปิดผนึก · แรงก์สูง ≠ ของดีเสมอ")
            lines.append(" หมายเลข = เปิด · A = เปิดทั้งหมด")
    if category == "healing":
        lines.append(" ยา/บัฟ/ล้าง · Recovery ขวด F–S (5 เทิร์น · S=3) · one-shot เก่า")
    lines.append("---")
    if not entries:
        lines.append(" (ว่าง)")
        if category == "food":
            lines.append(" ซื้อที่ร้าน: กระเป๋า→9 หรือ สำรวจ→6")
        lines.append("---")
        lines.append("  0  กลับ")
        return lines
    if category in ("equipment", "relic"):
        from game.ui_terminal.gear_showcase import format_equipment_list_line

        for i, e in enumerate(entries, 1):
            lines.append(
                format_equipment_list_line(
                    i,
                    str(e.get("id") or ""),
                    str(e.get("name") or e.get("id") or "?"),
                    str(e.get("rarity") or "common"),
                    reg,
                    hint=str(e.get("hint") or ""),
                )
            )
    elif category == "chest":
        lines.append(" รายการหีบ")
        for i, e in enumerate(entries, 1):
            # name already "■ หายาก ×2"; hint is base item name if any
            hint = f"  · {e['hint']}" if e.get("hint") else ""
            lines.append(f"  {i}. {e['name']}{hint}")
    else:
        for i, e in enumerate(entries, 1):
            hint = f"  · {e['hint']}" if e.get("hint") else ""
            lines.append(f"  {i}. {e['name']}{hint}")
    lines.append("---")
    lines.append("  0  กลับ")
    return lines


def bag_full(player: Mapping[str, Any]) -> bool:
    cap = int(player.get("bag_cap") or BAG_SOFT_CAP)
    return bag_count(player) >= cap


def try_add_item(
    player: MutableMapping[str, Any],
    item_id: str,
    reg: DataRegistry,
    *,
    rarity: Optional[str] = None,
    amount: int = 1,
) -> Tuple[bool, str]:
    """
    Add with soft-cap harden (WO-INV-1).
    Stacking into an existing stack succeeds even when bag is "full".
    """
    ensure_bag(player)
    from game.domain.bag_stack import can_accept_item
    from game.domain.rarity import item_default_rarity
    from game.domain.equipment import item_by_id

    it = item_by_id(reg, item_id) or {}
    rid = str(rarity or item_default_rarity(it, reg) or "common")
    if not can_accept_item(player, item_id, reg, rarity=rid, amount=amount):
        return False, "กระเป๋าเต็ม — ต้องทิ้งของหรือไม่เก็บ"
    name = add_item(player, item_id, reg, rarity=rarity, amount=amount)
    if not name or str(name).startswith("ไม่พบ"):
        if str(name).startswith("ไม่พบ"):
            return False, name
        return False, "กระเป๋าเต็ม — ต้องทิ้งของหรือไม่เก็บ"
    return True, name


def examine_item(
    item_id: str,
    reg: DataRegistry,
    *,
    rarity: Optional[str] = None,
) -> List[str]:
    """Human-readable item sheet — properties + how to use.

    Equipment uses rarity-tiered premium text showcase (id + weapon level + frame).
    """
    from game.domain.rarity import (
        format_rarity_tag,
        item_default_rarity,
        rarity_label,
        rarity_stat_mult,
        scaled_item_stats,
    )

    it = item_by_id(reg, item_id)
    if not it:
        return [f"ไม่รู้จักไอเทม ({item_id})"]
    name = str(it.get("name") or item_id)
    kind = str(it.get("kind") or "item")
    rid = str(rarity or item_default_rarity(it, reg))
    slot = str(it.get("slot") or "")
    from game.domain.equipment import EQUIP_SLOTS, normalize_slot

    is_equipment = (
        kind == "equipment"
        or normalize_slot(slot) in EQUIP_SLOTS
        or slot in ("weapon", "armor", "accessory", "shield")
    )

    # Premium gear card for equipment — proportional sections (price inside card)
    if is_equipment:
        from game.ui_terminal.gear_showcase import format_examine_with_showcase

        return format_examine_with_showcase(item_id, reg, rarity=rid, howto=True)

    from game.domain.rarity import display_item_name

    shown = display_item_name(name, rid, reg)
    lines = [
        f"── {shown} ──",
        f" ไอดี: {item_id}",
        f" ชนิด: {_kind_th(kind)}",
        f" ระดับ: {format_rarity_tag(reg, rid)} ({rarity_label(reg, rid)})",
    ]
    if it.get("desc"):
        lines.append(f" {it.get('desc')}")
    # combat stats with rarity scaling — armor shows DEF/MDEF; latent HP not listed
    slot_s = slot or "weapon"
    has_combat = any(
        it.get(k)
        for k in ("atk", "max_hp", "max_mana", "def", "defense", "mdef")
    )
    if has_combat:
        st = scaled_item_stats(it, rid, reg, upgrade_level=0, slot=slot_s)
        bits = []
        if st.get("atk"):
            bits.append(f"โจมตี +{st['atk']}")
        if st.get("def"):
            bits.append(f"กันกาย +{st['def']}")
        if st.get("mdef"):
            bits.append(f"กันเวท +{st['mdef']}")
        # only show explicit max_hp (weapons/rare), not latent
        if st.get("max_hp") and not (
            st.get("def") or st.get("mdef") or it.get("latent_hp_pct")
        ):
            bits.append(f"HP +{st['max_hp']}")
        elif st.get("max_hp") and int(it.get("max_hp") or 0) > 0 and not it.get("latent_hp_pct"):
            bits.append(f"HP +{st['max_hp']}")
        if st.get("max_mana"):
            bits.append(f"MP +{st['max_mana']}")
        if bits:
            mult = rarity_stat_mult(reg, rid)
            lines.append(" คุณสมบัติ: " + " · ".join(bits) + f"  (คูณระดับ ×{mult:.2f})")
    # latent never as numbers — soft observation only
    if it.get("latent_hp_pct") or it.get("latent_max_hp") or it.get("latent_tough"):
        lines.append(" …รู้สึกว่าเกราะอุ้มร่าง/อึดอะไรบางอย่าง (ต้องสังเกตเอง)")
    if it.get("atk") and (it.get("latent_atk_pct") or it.get("latent_crit")):
        lines.append(" …คมแฝงอะไรบางอย่าง (สังเกตแรงโจมตีในไฟต์)")
    # default weapon latents are computed at scale time even if YAML omits them
    elif it.get("atk") and not (it.get("def") or it.get("mdef")):
        lines.append(" …คมแฝงอะไรบางอย่าง (สังเกตแรงโจมตีในไฟต์)")
    if it.get("slot"):
        lines.append(f" ช่องสวม: {_slot_th(str(it['slot']))}")
    if it.get("sockets"):
        lines.append(f" ช่องการ์ด: {it.get('sockets')}")
    if it.get("tags"):
        lines.append(" แท็ก: " + ", ".join(str(t) for t in it["tags"]))
    if it.get("set_id"):
        sdef = (getattr(reg, "gear_sets", None) or {}).get(it["set_id"]) or {}
        lines.append(f" เซ็ต: {sdef.get('name') or it['set_id']}")
    if it.get("heal_hp"):
        lines.append(f" ใช้แล้ว: ฟื้น HP ประมาณ {it['heal_hp']}")
    if it.get("heal_mana"):
        lines.append(f" ใช้แล้ว: ฟื้น MP ประมาณ {it['heal_mana']}")
    if it.get("clear_all_debuffs") or str(it.get("clear_status") or "").lower() in (
        "all",
        "*",
        "debuff",
    ):
        lines.append(" ใช้แล้ว: ล้างสถานะผิดปกติเกือบทั้งหมด")
    elif it.get("clear_status"):
        lines.append(f" ใช้แล้ว: ล้างสถานะ ({it['clear_status']})")
    # how to use
    lines.append(" วิธีใช้:")
    if kind == "consumable" or it.get("heal_hp") or it.get("heal_mana"):
        lines.append("  · สนาม: 5 → 2.รักษา → เลือกใช้ · ไฟต์: 3")
    elif kind == "card" or item_id in (reg.cards or {}):
        lines.append("  · สนาม: 5 → 4.การ์ด → ใส่ช่องอาวุธ/เกราะ")
        if it.get("grant_skills"):
            lines.append("  · อาจมอบสกิลเมื่อติดตั้ง")
    elif kind == "material" or "mat" in item_id:
        lines.append("  · ดูใน 5 → 3.วัตถุดิบ · ใช้ตอนคราฟ/อัป (5→8 / เกียร์)")
    else:
        lines.append("  · เก็บในกระเป๋า — ทดลองใช้/คราฟ")
    # prices soft
    if it.get("price_world"):
        lines.append(f" มูลค่าตลาดโลก: ~{it['price_world']}")
    if it.get("price_heaven"):
        lines.append(f" มูลค่าสวรรค์: ~{it['price_heaven']}")
    if it.get("price_hell"):
        lines.append(f" มูลค่านรก: ~{it['price_hell']}")
    return lines


def _kind_th(kind: str) -> str:
    return {
        "equipment": "อุปกรณ์",
        "consumable": "ของใช้",
        "card": "การ์ด",
        "material": "วัสดุ",
        "item": "ไอเทม",
    }.get(kind, kind)


def _slot_th(slot: str) -> str:
    from game.domain.equipment import SLOT_LABEL_TH, normalize_slot

    ns = normalize_slot(slot)
    return SLOT_LABEL_TH.get(ns) or SLOT_LABEL_TH.get(str(slot), slot)


def format_bag_panel(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_bag(player)  # type: ignore
    cap = int(player.get("bag_cap") or BAG_SOFT_CAP)
    n = bag_count(player)
    lines = [f"── กระเป๋า ({n}/{cap}) ──"]
    ids = list(player.get("inventory_ids") or [])
    if not ids:
        lines.append("  (ว่างจากไอเทม — ของใช้/เกียร์/วัสดุ)")
    else:
        from game.domain.bag_stack import qty_at
        from game.domain.rarity import display_item_name, rarity_of_inventory_index as _roi

        for i, iid in enumerate(ids):
            it = reg.items.get(iid) or {}
            name = it.get("name") or iid
            kind = _kind_th(str(it.get("kind") or "item"))
            try:
                rid0 = _roi(player, i)
            except Exception:
                rid0 = "common"
            dname = display_item_name(str(name), rid0, reg)
            q = qty_at(player, i)
            extra = f" x{q}" if q > 1 else ""
            lines.append(f"  {i + 1}. {dname}{extra}  [{kind}]")
    cards = list(player.get("card_bag") or [])
    if cards:
        lines.append(" ── การ์ดในถุง ──")
        for i, cid in enumerate(cards, 1):
            nm = (reg.cards.get(cid) or {}).get("name") or cid
            lines.append(f"  C{i}. {nm}")
    lines.append("  เลือกหมายเลขเพื่อดูรายละเอียด · 0 กลับ")
    return lines


def bag_item_id_at(player: Mapping[str, Any], index_1based: int) -> Optional[str]:
    """Map panel 1-based index to inventory slot item id."""
    ids = list(player.get("inventory_ids") or [])
    if index_1based < 1 or index_1based > len(ids):
        return None
    return str(ids[index_1based - 1])


def bag_item_rarity_at(player: Mapping[str, Any], index_1based: int) -> str:
    from game.domain.rarity import rarity_of_inventory_index

    ids = list(player.get("inventory_ids") or [])
    if index_1based < 1 or index_1based > len(ids):
        return "common"
    try:
        return rarity_of_inventory_index(player, index_1based - 1)
    except Exception:
        return "common"


def format_equip_panel(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    """
    What is worn + soft power — proportional sections for box UI.
    """
    ensure_gear_fields(player)  # type: ignore
    lines: List[str] = [
        " เกียร์ · สวมใส่",
        "---",
        " ช่องสวม",
    ]
    total_atk = 0
    total_hp = 0
    total_mp = 0
    from game.domain.rarity import equip_rarity_for_slot, scaled_item_stats
    from game.domain.rarity import display_item_name as _din

    from game.domain.equipment import (
        EQUIP_SLOT_UI,
        item_grip,
        OFF_HAND_ATK_MULT,
        GRIP_ONE_HAND,
        GRIP_FOCUS,
    )
    from game.domain.item_codes import item_code

    worn_n = 0
    for slot, label in EQUIP_SLOT_UI:
        eid = (player.get("equip_ids") or {}).get(slot)
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        if not eid:
            if slot == "off_hand":
                mid = (player.get("equip_ids") or {}).get("main_hand")
                if mid and item_grip(reg.items.get(mid) or {}) == "two_hand":
                    lines.append(f"  {label:<10}  —  ล็อก · สองมือ")
                    continue
            lines.append(f"  {label:<10}  —  ว่าง")
            continue
        worn_n += 1
        it = reg.items.get(eid) or {}
        name = it.get("name") or eid
        rid = equip_rarity_for_slot(player, slot)
        st = scaled_item_stats(it, rid, reg, upgrade_level=up, slot=slot)
        atk, hp, mp = int(st["atk"]), int(st["max_hp"]), int(st["max_mana"])
        pdef, pmdef = int(st.get("def") or 0), int(st.get("mdef") or 0)
        grip = item_grip(it)
        if slot == "off_hand" and grip in (GRIP_ONE_HAND, GRIP_FOCUS) and atk > 0:
            atk = max(0, int(round(atk * OFF_HAND_ATK_MULT)))
        total_atk += atk
        total_hp += hp
        total_mp += mp
        up_bit = f" +{up}" if up else ""
        grip_bit = ""
        if grip == "two_hand":
            grip_bit = " ·สองมือ"
        elif grip == "shield":
            grip_bit = " ·โล่"
        code = ""
        try:
            code = item_code(str(eid), reg) or ""
        except Exception:
            code = ""
        code_bit = f"  [{code}]" if code else ""
        shown = _din(str(name), rid, reg)
        lines.append(f"  {label:<10}  {shown}{up_bit}{grip_bit}")
        if code:
            lines.append(f"             รหัส  {code}")

        from game.domain.equipment import soft_piece_defense_hint

        is_armor = slot in ("body", "head", "legs", "feet") or grip == "shield"
        is_focus = grip == "focus"
        stat_bits: List[str] = []
        if is_armor or (is_focus and (pdef or pmdef)):
            def_hint = soft_piece_defense_hint(it, slot=slot, grip=grip, st=st)
            if def_hint:
                lines.append(f"             {def_hint.strip()}")
            else:
                if atk:
                    stat_bits.append(f"ATK+{atk}")
                if mp:
                    stat_bits.append(f"MP+{mp}")
                if stat_bits:
                    lines.append(f"             {' · '.join(stat_bits)}")
        else:
            stat_bits = [f"ATK+{atk}"]
            if hp:
                stat_bits.append(f"HP+{hp}")
            if mp:
                stat_bits.append(f"MP+{mp}")
            lines.append(f"             {' · '.join(stat_bits)}")

        socks = list((player.get("sockets") or {}).get(slot) or [])
        if socks:
            filled = 0
            parts: List[str] = []
            for i, cid in enumerate(socks, 1):
                if not cid:
                    parts.append(f"{i}:ว่าง")
                else:
                    filled += 1
                    cname = str((reg.cards.get(cid) or {}).get("name") or cid)
                    parts.append(f"{i}:{cname}")
            lines.append(
                f"             การ์ด  {filled}/{len(socks)}  ·  "
                + " · ".join(parts)
            )

    total_def = int(player.get("equip_def") or 0)
    total_mdef = int(player.get("equip_mdef") or 0)

    soft_bits: List[str] = []
    for note in player.get("loadout_soft_notes") or []:
        soft_bits.append(str(note))
    try:
        from game.domain.loadout_context import soft_weight_label

        soft_bits.append(f"น้ำหนักรู้สึก: {soft_weight_label(player)}")
    except Exception:
        pass
    if soft_bits:
        lines.append("---")
        lines.append(" โทนชุด")
        for s in soft_bits:
            lines.append(f"  · {s}")

    lines.append("---")
    lines.append(" สรุปจากเกียร์")
    lines.append(
        f"  ATK+{total_atk}   กันกาย+{total_def}   กันเวท+{total_mdef}   MP+{total_mp}"
    )
    try:
        from game.domain.equipment import soft_guard_summary

        lines.append(f"  ป้องกัน  {soft_guard_summary(player)}")
    except Exception:
        pass
    lines.append("---")
    lines.append(" ตัวละคร (หลังเกียร์+ปาร์ตี้)")
    lines.append(
        f"  ATK {player.get('bonus_atk')}   "
        f"HP {player.get('hp')}/{player.get('max_hp')}   "
        f"MP {player.get('mana')}/{player.get('max_mana')}"
    )
    if player.get("active_sets") or player.get("partial_sets"):
        lines.append("---")
        lines.append(" เซ็ต")
        if player.get("active_sets"):
            lines.append(
                "  ทำงาน  " + ", ".join(str(x) for x in player["active_sets"])
            )
        if player.get("partial_sets"):
            lines.append(
                "  เศษ     " + ", ".join(str(x) for x in player["partial_sets"])
            )
        for fl in player.get("set_flavors") or []:
            lines.append(f"  “{fl}”")
    if player.get("party_bonus_atk") or player.get("party_bonus_max_hp"):
        lines.append("---")
        lines.append(" ปาร์ตี้")
        lines.append(
            f"  ATK+{player.get('party_bonus_atk', 0)}   "
            f"HP+{player.get('party_bonus_max_hp', 0)}   "
            f"MP+{player.get('party_bonus_max_mana', 0)}"
        )
    lines.append("---")
    lines.append(f" สวม {worn_n} ช่อง  ·  ว่างไม่โชว์สเตตัส")
    lines.append(" พิมพ์รหัสชิ้น (sw001) เพื่อจัดการ  ·  0/Enter กลับ")
    return lines


def format_gear_menu_lines() -> List[str]:
    """Action menu under equip panel."""
    return [
        " จัดการเกียร์",
        "---",
        "  1  สวมอุปกรณ์จากกระเป๋า",
        "  2  ใส่การ์ด",
        "  3  ถอดการ์ด",
        "  4  อัปเกรดที่สวม",
        "---",
        "  5  ร้าน",
        "  6  คราฟ",
        "  7  กระเป๋า / ดูไอเทม",
        "  8  เกียร์ละเอียด (สรุปชุด)",
        "---",
        "  0  กลับ",
    ]


UPGRADE_MAX_LEVEL = 10

# Protect scroll item ids (optional, auto-used on catastrophic fail)
# Rank of the *scroll instance* must be ≥ rank of the *equipped piece*.
PROTECT_BREAK_ID = "scroll_guard_break"  # กันพัง
PROTECT_DOWN_ID = "scroll_guard_level"  # กันลดระดับ


def _gear_rarity_for_slot(
    player: Mapping[str, Any],
    slot: str,
    reg: Optional[DataRegistry] = None,
) -> str:
    from game.domain.rarity import equip_rarity_for_slot, item_default_rarity

    rid = equip_rarity_for_slot(player, slot)
    if rid in (None, "", "None"):
        eid = (player.get("equip_ids") or {}).get(slot)
        if eid and reg is not None:
            rid = item_default_rarity(reg.items.get(eid) or {}, reg)
        else:
            rid = "common"
    return str(rid or "common")


def upgrade_success_chance(
    slot: str,
    level: int,
    *,
    reg: Optional[DataRegistry] = None,
    rarity_id: str = "common",
    player: Optional[Mapping[str, Any]] = None,
) -> float:
    """
    Hidden curve — higher +level AND higher gear rank = lower success.
    Exact % never shown; soft-labeled in UI.
    Tier upgrade_bonus (YAML) softens slightly for well-made pieces but
    rank penalty still dominates on high tiers.
    WO-035.3: luck is a soft multiplier (small) — materials/rank still primary.
    """
    # +0 common: ~92%, +5: ~60%, +9: ~33%
    base = 0.92 - level * 0.065
    from game.domain.rarity import tier_by_id, tier_rank

    rk = int(tier_rank(reg, rarity_id) or 1)
    # rank pressure: common=0 … mythic≈0.175
    base -= (rk - 1) * 0.025
    bonus = float(tier_by_id(reg, rarity_id).get("upgrade_bonus") or 0)
    base += bonus * 0.45  # partial quality hold — net still harder for high rank
    # WO-036: luck soft bias ±~6% relative — rank/materials stay primary
    if player is not None:
        try:
            luck = float(player.get("luck_score") or 0.0)
            base *= 1.0 + max(-0.07, min(0.07, luck * 0.20))
        except Exception:
            pass
    return max(0.16, min(0.96, base))


def upgrade_fail_severity_weights(
    level: int,
    *,
    reg: Optional[DataRegistry] = None,
    rarity_id: str = "common",
) -> Dict[str, float]:
    """
    On failed upgrade roll severity (relative weights, not player-visible %).
    soft  = stay at same +level (materials lost)
    down  = -1 upgrade level (severe)
    break = destroy equipped piece (catastrophic)

    Higher gear rank amplifies down/break (precious pieces shatter harder).
    """
    from game.domain.rarity import tier_rank

    rk = int(tier_rank(reg, rarity_id) or 1)
    # early: almost only soft fail
    if level <= 1:
        w = {"soft": 0.92, "down": 0.08, "break": 0.0}
    elif level <= 3:
        w = {"soft": 0.72, "down": 0.24, "break": 0.04}
    elif level <= 5:
        w = {"soft": 0.55, "down": 0.32, "break": 0.13}
    elif level <= 7:
        w = {"soft": 0.42, "down": 0.35, "break": 0.23}
    else:
        w = {"soft": 0.30, "down": 0.35, "break": 0.35}
    # rank amplify: high tier gear fails more catastrophically
    if rk >= 2:
        amp_d = 1.0 + (rk - 1) * 0.07
        amp_b = 1.0 + (rk - 1) * 0.11
        w["down"] = float(w["down"]) * amp_d
        w["break"] = float(w["break"]) * amp_b
        # high rank opens tiny break chance even at mid levels
        if level >= 2 and w["break"] < 0.02 * (rk - 1):
            w["break"] = max(w["break"], 0.015 * (rk - 1))
    return w


def _roll_fail_severity(
    level: int,
    rng: random.Random,
    *,
    reg: Optional[DataRegistry] = None,
    rarity_id: str = "common",
) -> str:
    w = upgrade_fail_severity_weights(level, reg=reg, rarity_id=rarity_id)
    total = sum(w.values()) or 1.0
    r = rng.random() * total
    acc = 0.0
    for key in ("soft", "down", "break"):
        acc += float(w.get(key) or 0)
        if r <= acc:
            return key
    return "soft"


def risk_label_for_level(
    level: int,
    *,
    reg: Optional[DataRegistry] = None,
    rarity_id: str = "common",
) -> str:
    """Soft risk band shown in preview (no exact %)."""
    from game.domain.rarity import tier_rank

    rk = int(tier_rank(reg, rarity_id) or 1)
    if level <= 1 and rk <= 2:
        return "ล้ม = เสียวัสดุ (ลดระดับ/พังยังแทบไม่มี)"
    if level <= 3 and rk <= 3:
        return "ล้ม = เสียวัสดุ · อาจลดระดับ · พังได้บ้าง"
    if level <= 5 and rk <= 4:
        return "เสี่ยงสูง — ล้มอาจลดระดับ หรือพังชิ้น · ใช้ม้วน rank ตรง"
    if rk >= 5:
        return "อันตรายมาก (rank สูง) — ล้มมักรุนแรง · ม้วนต้อง rank ≥ ชิ้น"
    return "อันตรายมาก — ล้มอาจพังชิ้น · ม้วนกันต้อง rank ≥ ชิ้น"


def count_protect_matching(
    player: Mapping[str, Any],
    protect_id: str,
    gear_rarity: str,
    reg: DataRegistry,
) -> int:
    """How many protect scrolls of rank ≥ gear rank."""
    from game.domain.rarity import count_materials_min_rarity

    return int(count_materials_min_rarity(player, protect_id, gear_rarity, reg))


def try_consume_protect(
    player: MutableMapping[str, Any],
    protect_id: str,
    gear_rarity: str,
    reg: DataRegistry,
) -> bool:
    """
    Consume 1 protect scroll with rarity rank ≥ gear rank.
    Prefers lowest sufficient rank (saves better scrolls).
    """
    from game.domain.rarity import count_materials_min_rarity, remove_materials_min_rarity

    if count_materials_min_rarity(player, protect_id, gear_rarity, reg) < 1:
        return False
    return bool(remove_materials_min_rarity(player, protect_id, 1, gear_rarity, reg))


def can_upgrade_equipped(
    player: Mapping[str, Any],
    slot: str,
) -> bool:
    """True if slot has gear and upgrade level is below cap."""
    from game.domain.equipment import EQUIP_SLOTS, normalize_slot

    ensure_gear_fields(player)  # type: ignore
    slot = normalize_slot(slot)
    if slot not in EQUIP_SLOTS:
        return False
    if not (player.get("equip_ids") or {}).get(slot):
        return False
    cur = int((player.get("upgrade_levels") or {}).get(slot, 0))
    return cur < UPGRADE_MAX_LEVEL


def upgrade_chance_label(
    slot: str,
    level: int,
    *,
    reg: Optional[DataRegistry] = None,
    rarity_id: str = "common",
    player: Optional[Mapping[str, Any]] = None,
) -> str:
    rate = upgrade_success_chance(
        slot, level, reg=reg, rarity_id=rarity_id, player=player
    )
    if rate >= 0.8:
        return "โอกาสสูง"
    if rate >= 0.55:
        return "โอกาสปานกลาง"
    if rate >= 0.35:
        return "เสี่ยงสูง"
    return "เสี่ยงมาก"


def format_upgrade_preview(
    player: Mapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> List[str]:
    """
    Explicit cost sheet so players learn which items matter.
    Shows mats, money, soft success feel, risk, rank-matched protect scrolls.
    """
    from game.domain.equipment import normalize_slot
    from game.domain.rarity import format_rarity_tag, rarity_label

    ensure_gear_fields(player)  # type: ignore
    slot = normalize_slot(slot)
    if not can_upgrade_equipped(player, slot):
        cur = int((player.get("upgrade_levels") or {}).get(slot, 0))
        if cur >= UPGRADE_MAX_LEVEL:
            return ["── อัปเกรด ──", " ชิ้นนี้ถึงขีดอัปแล้ว (อัปต่อไม่ได้)"]
        return ["── อัปเกรด ──", " ไม่มีอุปกรณ์ในช่องนี้"]

    eid = str((player.get("equip_ids") or {}).get(slot) or "")
    it = reg.items.get(eid) or {}
    name = str(it.get("name") or eid)
    from game.domain.item_codes import item_code

    code = item_code(eid, reg)
    cur = int((player.get("upgrade_levels") or {}).get(slot, 0))
    gear_rid = _gear_rarity_for_slot(player, slot, reg)
    cost = upgrade_cost(slot, cur, reg=reg, rarity_id=gear_rid)
    money = int(player.get("money_world") or 0)
    have_um = count_materials(player, "upgrade_mat")
    have_rm = count_materials(player, "rare_mat")
    have_pb = count_protect_matching(player, PROTECT_BREAK_ID, gear_rid, reg)
    have_pd = count_protect_matching(player, PROTECT_DOWN_ID, gear_rid, reg)
    have_pb_any = count_materials(player, PROTECT_BREAK_ID)
    have_pd_any = count_materials(player, PROTECT_DOWN_ID)
    need_m = int(cost["money"])
    need_um = int(cost["upgrade_mat"])
    need_rm = int(cost["rare_mat"])

    um_it = reg.items.get("upgrade_mat") or {}
    rm_it = reg.items.get("rare_mat") or {}
    pb_it = reg.items.get(PROTECT_BREAK_ID) or {}
    pd_it = reg.items.get(PROTECT_DOWN_ID) or {}
    um_name = str(um_it.get("name") or "วัสดุอัพเกรด")
    rm_name = str(rm_it.get("name") or "วัสดุหายาก")
    pb_name = str(pb_it.get("name") or "ม้วนกันพัง")
    pd_name = str(pd_it.get("name") or "ม้วนกันลดระดับ")
    um_code = item_code("upgrade_mat", reg)
    rm_code = item_code("rare_mat", reg)
    rtag = format_rarity_tag(reg, gear_rid)
    rlab = rarity_label(reg, gear_rid)

    def _ok(have: int, need: int) -> str:
        return "✓ พอ" if have >= need else "✗ ไม่พอ"

    lines = [
        "── พิธีอัปเกรด ──",
        f" ชิ้น: {code} {name}  ({_slot_th(slot)})",
        f" Rank ชิ้น: {rtag} ({rlab})  — ม้วนกันต้อง rank ≥ ชิ้นนี้",
        f" ระดับอัป: +{cur}  →  เป้า +{cur + 1}  (สูงสุด +{UPGRADE_MAX_LEVEL})",
        "---",
        " ค่าใช้จ่าย (หักทันทีเมื่อยืนยัน — แม้พิธีล้มเหลวก็เสีย):",
        f"  · เงินโลก: {need_m}  (มี {money})  {_ok(money, need_m)}",
    ]
    if need_um > 0:
        lines.append(
            f"  · {um_name} [{um_code} / upgrade_mat]: ×{need_um}  "
            f"(มี {have_um})  {_ok(have_um, need_um)}"
        )
        desc = um_it.get("desc")
        if desc:
            lines.append(f"      → สำคัญ: {desc}")
        else:
            lines.append("      → สำคัญ: ใช้ในพิธีอัปเกียร์ — เก็บจากลูท/ร้าน")
    if need_rm > 0:
        lines.append(
            f"  · {rm_name} [{rm_code} / rare_mat]: ×{need_rm}  "
            f"(มี {have_rm})  {_ok(have_rm, need_rm)}"
        )
        desc = rm_it.get("desc")
        if desc:
            lines.append(f"      → สำคัญ: {desc}")
        else:
            lines.append("      → สำคัญ: ใช้ตอนอัปขั้นสูง — หายากกว่า")
    else:
        lines.append("  · วัสดุหายาก: ไม่ต้องใช้ในขั้นนี้")

    feel = upgrade_chance_label(
        slot, cur, reg=reg, rarity_id=gear_rid, player=player
    )
    lines.append("---")
    lines.append(f" โอกาสสำเร็จ (ประมาณ): {feel}  (ขึ้นกับ +level และ Rank ชิ้น)")
    lines.append(
        f" ความเสี่ยงเมื่อล้ม: {risk_label_for_level(cur, reg=reg, rarity_id=gear_rid)}"
    )
    lines.append(" ผลเมื่อสำเร็จ: พลังหลัก (โจมตี/กันกาย) ขึ้น · พลังแฝงก็แน่นขึ้น (สังเกตเอง)")
    lines.append("---")
    lines.append(
        f" ม้วนคุ้มครอง (rank ≥ {rlab} เท่านั้น · ใช้เมื่อล้มร้ายแรงอัตโนมัติ):"
    )
    lines.append(
        f"  · {pd_name} [{PROTECT_DOWN_ID}]: ตรง rank {have_pd}  "
        f"(ในถุงทั้งหมด {have_pd_any})  "
        f"{'✓ พร้อม' if have_pd else '· ยังไม่มี rank พอ'}"
    )
    lines.append("      → กันระดับ + ลดเมื่อล้มร้ายแรง")
    lines.append(
        f"  · {pb_name} [{PROTECT_BREAK_ID}]: ตรง rank {have_pb}  "
        f"(ในถุงทั้งหมด {have_pb_any})  "
        f"{'✓ พร้อม' if have_pb else '· ยังไม่มี rank พอ'}"
    )
    lines.append("      → กันชิ้นพังเมื่อล้มร้ายแรงสุด")
    lines.append("      → ม้วน rank สูงกว่าใช้กับชิ้นต่ำกว่าได้ (กินม้วนดีกว่า)")
    if (cur >= 3 or gear_rid not in ("common",)) and have_pb == 0 and have_pd == 0:
        lines.append(
            f"  ⚠ หา {pd_name}/{pb_name} rank ≥ {rlab} จากร้าน/ลูท "
            "(ม้วนธรรมดาใช้กับชิ้นแรงไม่ได้)"
        )
    # readiness summary
    ready = money >= need_m and have_um >= need_um and have_rm >= need_rm
    if ready:
        lines.append(" สถานะ: พร้อมพิธี — ยืนยันได้")
    else:
        lines.append(" สถานะ: ทรัพยากรไม่ครบ — ยืนยันแล้วจะไม่เริ่มพิธี")
    return lines


def upgrade_resources_ok(
    player: Mapping[str, Any],
    slot: str,
    reg: Optional[DataRegistry] = None,
) -> bool:
    if not can_upgrade_equipped(player, slot):
        return False
    cur = int((player.get("upgrade_levels") or {}).get(slot, 0))
    gear_rid = "common"
    if reg is not None:
        gear_rid = _gear_rarity_for_slot(player, slot, reg)
    cost = upgrade_cost(slot, cur, reg=reg, rarity_id=gear_rid)
    money = int(player.get("money_world") or 0)
    if money < int(cost["money"]):
        return False
    if count_materials(player, "upgrade_mat") < int(cost["upgrade_mat"]):
        return False
    if int(cost["rare_mat"]) and count_materials(player, "rare_mat") < int(cost["rare_mat"]):
        return False
    return True


def upgrade_equipped_opaque(
    player: MutableMapping[str, Any],
    slot: str,
    reg: DataRegistry,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Risky upgrade: success / soft fail / downgrade / break.
    Rates scale with +level AND gear rank.
    Protect scrolls must match rank (≥ gear) — auto-consume on bad outcome.
    Base mats + money always consumed on attempt.
    """
    from game.domain.equipment import (
        EQUIP_SLOTS,
        consume_materials,
        destroy_equipped_piece,
        normalize_slot,
    )
    from game.domain.rarity import rarity_label

    ensure_gear_fields(player)
    rng = rng or random.Random()
    slot = normalize_slot(slot)
    if slot not in EQUIP_SLOTS:
        return "ช่องไม่ถูกต้อง"
    if not (player.get("equip_ids") or {}).get(slot):
        return f"ยังไม่มี{_slot_th(slot)}สวมอยู่"
    ups = dict(player.get("upgrade_levels") or {})
    cur = int(ups.get(slot, 0))
    if cur >= UPGRADE_MAX_LEVEL:
        return "ถึงขีดอัปแล้ว — อัปต่อไม่ได้"
    gear_rid = _gear_rarity_for_slot(player, slot, reg)
    rlab = rarity_label(reg, gear_rid)
    cost = upgrade_cost(slot, cur, reg=reg, rarity_id=gear_rid)
    money = int(player.get("money_world", 0))
    if money < cost["money"]:
        return f"เงินไม่พอ (ต้องการ {cost['money']} · มี {money})"
    if count_materials(player, "upgrade_mat") < cost["upgrade_mat"]:
        have = count_materials(player, "upgrade_mat")
        return (
            f"วัสดุอัพเกรดไม่พอ (ต้องการ {cost['upgrade_mat']} · มี {have}) "
            "— หาจากลูท/ร้าน"
        )
    if cost["rare_mat"] and count_materials(player, "rare_mat") < cost["rare_mat"]:
        have = count_materials(player, "rare_mat")
        return (
            f"วัสดุหายากไม่พอ (ต้องการ {cost['rare_mat']} · มี {have}) "
            "— ใช้ตอนอัปขั้นสูง"
        )

    # consume always on attempt
    player["money_world"] = money - cost["money"]
    consume_materials(player, "upgrade_mat", cost["upgrade_mat"], reg)
    if cost["rare_mat"]:
        consume_materials(player, "rare_mat", cost["rare_mat"], reg)

    chance = upgrade_success_chance(
        slot, cur, reg=reg, rarity_id=gear_rid, player=player
    )
    if rng.random() <= chance:
        ups[slot] = cur + 1
        player["upgrade_levels"] = ups
        recompute_stats(player, reg)
        msg = f"อัปเกรด{_slot_th(slot)} สำเร็จ → +{ups[slot]}! (เสริมพลังเพิ่มขึ้น)"
        try:
            from game.domain.soft_feel import soft_upgrade_feel

            for feel in soft_upgrade_feel(player, reg, slot=slot, success=True):
                msg += f"\n  {feel}"
        except Exception:
            pass
        return msg

    # --- fail path: severity roll (rank-aware) ---
    severity = _roll_fail_severity(cur, rng, reg=reg, rarity_id=gear_rid)
    protect_notes: List[str] = []

    if severity == "break":
        if try_consume_protect(player, PROTECT_BREAK_ID, gear_rid, reg):
            protect_notes.append(f"ม้วนกันพัง (rank≥{rlab}) ฉีก — ชิ้นรอด")
            severity = "down"
        else:
            broken_name = destroy_equipped_piece(player, slot, reg)
            low_hint = ""
            if count_materials(player, PROTECT_BREAK_ID) > 0:
                low_hint = f" · มีม้วนกันพังแต่ rank ต่ำกว่า {rlab} ใช้ไม่ได้"
            return (
                f"พิธีล้มร้ายแรงสุด — {_slot_th(slot)} 「{broken_name}」 พังย่อย! "
                f"การ์ดที่เสียบคืนถุง (ถ้ามี) · ต้องการ ม้วนกันพัง rank ≥ {rlab}"
                f"{low_hint}"
            )

    if severity == "down":
        if try_consume_protect(player, PROTECT_DOWN_ID, gear_rid, reg):
            protect_notes.append(f"ม้วนกันลดระดับ (rank≥{rlab}) ฉีก — ระดับ + คงที่")
            severity = "soft"
        else:
            new_lv = max(0, cur - 1)
            ups[slot] = new_lv
            player["upgrade_levels"] = ups
            recompute_stats(player, reg)
            note = (" · " + " · ".join(protect_notes)) if protect_notes else ""
            low_hint = ""
            if count_materials(player, PROTECT_DOWN_ID) > 0 and not protect_notes:
                low_hint = f" · มีม้วนแต่ rank ต่ำกว่า {rlab}"
            if new_lv < cur:
                return (
                    f"อัปเกรดล้มร้ายแรง — ระดับ{_slot_th(slot)} ลด +{cur} → +{new_lv}! "
                    f"วัสดุ/เงินเสียแล้ว{note}{low_hint} · "
                    f"ม้วนกันลดระดับ rank ≥ {rlab} ช่วยได้"
                )
            return (
                f"อัปเกรดล้มเหลว — ขั้นยัง +{cur} · พลังสั่น{note}{low_hint} "
                "(พิธีเกือบทำลาย)"
            )

    # soft fail (default)
    recompute_stats(player, reg)
    note = (" · " + " · ".join(protect_notes)) if protect_notes else ""
    soft = "ใกล้แล้ว..." if chance > 0.6 else "พิธีสั่นคลอน..."
    return f"อัปเกรดล้มเหลว — วัสดุ/เงินถูกใช้แล้ว {soft} (ขั้นยัง +{cur}){note}"


def soft_upgrade_hint(
    slot: str,
    level: int,
    *,
    reg: Optional[DataRegistry] = None,
    rarity_id: str = "common",
) -> str:
    """One-line soft summary (still used in compact UI)."""
    c = upgrade_cost(slot, level, reg=reg, rarity_id=rarity_id)
    parts = [f"เงินโลก ~{c['money']}"]
    if c["upgrade_mat"]:
        parts.append(f"วัสดุอัป ×{c['upgrade_mat']}")
    if c["rare_mat"]:
        parts.append(f"วัสดุหายาก ×{c['rare_mat']}")
    feel = upgrade_chance_label(slot, level, reg=reg, rarity_id=rarity_id)
    return f"อัปถัดไป: {', '.join(parts)} · {feel}"


# ---- Loot choice ----

def present_loot_choices(
    drops: Sequence[Dict[str, Any]],
) -> List[str]:
    """
    drops: [{id, name, note?}]
    Proportional loot panel — box-ready lines.
    """
    lines = [
        " ของที่ตก",
        "---",
        f" ชิ้น    {len(drops)}",
        "---",
        " วิธีเก็บ",
        "  A      เก็บทั้งหมด",
        "  1,3    เลือกเลข (คั่นด้วย , หรือช่องว่าง)",
        "  0      ไม่เก็บ",
        "---",
        " รายการ",
    ]
    if not drops:
        lines.append("  (ไม่มีของ)")
        return lines
    for i, d in enumerate(drops, 1):
        name = str(d.get("name") or d.get("id") or "?")
        note = str(d.get("note") or "").strip()
        if note:
            # short note — source only
            if " · " in note:
                note = note.split(" · ")[-1].strip()
            lines.append(f"  {i}. {name}")
            lines.append(f"      · {note}")
        else:
            lines.append(f"  {i}. {name}")
    return lines


def parse_loot_indices(choice_text: str, n_drops: int) -> List[int]:
    """
    Parse player loot pick into 1-based indices (deduped, sorted).
    A / all / * / ทั้งหมด → every index.
    0 / empty / n → none.
    Otherwise: numbers separated by comma or space (e.g. 1,3 or 1 2 3).
    """
    text = (choice_text or "").strip()
    if not text or text in ("0", "n", "N", "no", "ไม่", "ทิ้ง"):
        return []
    low = text.lower()
    if low in ("a", "all", "*", "ทั้งหมด", "เก็บทั้งหมด", "y", "yes"):
        return list(range(1, n_drops + 1))
    # normalize separators: Thai comma 、 fullwidth ，
    for sep in ("、", "，", ";", "|"):
        text = text.replace(sep, ",")
    idxs: List[int] = []
    for part in text.replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ix = int(part)
        except ValueError:
            continue
        if 1 <= ix <= n_drops and ix not in idxs:
            idxs.append(ix)
    return idxs


def resolve_loot_pick(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    drops: Sequence[Dict[str, Any]],
    choice_text: str,
) -> List[str]:
    """Player picks which drops to keep (all or by number). Respects bag capacity."""
    text = (choice_text or "").strip()
    if text in ("0", "", "n", "N", "no", "ไม่", "ทิ้ง"):
        return ["ทิ้งของทั้งหมดไว้"]
    idxs = parse_loot_indices(text, len(drops))
    if not idxs:
        return ["ไม่ได้เลือก — ของหายไป"]
    notes: List[str] = []
    for ix in idxs:
        d = drops[ix - 1]
        iid = str(d.get("id") or "")
        if not iid:
            continue
        ok, name = try_add_item(player, iid, reg, rarity=d.get("rarity"))
        if ok:
            # cards land in card_bag — soft label
            if iid in (reg.cards or {}) or str(iid).startswith("card_"):
                notes.append(f"เก็บการ์ด {name}")
            else:
                notes.append(f"เก็บ {name}")
        else:
            notes.append(f"เก็บ {d.get('name')} ไม่ได้ — {name}")
    return notes or ["ไม่มีของเข้ากระเป๋า"]


def build_combat_loot_table(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Generate drop options after win — player chooses (A / เลข,comma / 0).
    1) Per-monster drops table (RO-like, soft rates) — primary identity
    2) Generic mat/potion (WO-ITEM-1: strongly reduced when mon table is thick)
    3) Cards: mon card_id first, else element-bias pool (shops never sell)

    Soft source hints on notes — never show drop %.
    """
    from game.domain.balance import material_drop_chances
    from game.domain.monster_drops import (
        mon_drop_entries,
        monster_has_drop_table,
        roll_monster_table_drops,
    )
    from game.domain.rarity import format_rarity_tag, item_default_rarity, roll_rarity

    drops: List[Dict[str, Any]] = []
    up_c, rare_c = material_drop_chances(player)
    # Rehydrate drop table from registry if runtime mon lost YAML fields
    mon = dict(mon)
    mid = str(mon.get("id") or "")
    catalog = (reg.monsters or {}).get(mid) if mid else None
    if catalog:
        if mon.get("drops") is None and catalog.get("drops") is not None:
            mon["drops"] = list(catalog.get("drops") or [])
        if not mon.get("card_id") and catalog.get("card_id"):
            mon["card_id"] = catalog.get("card_id")
        if not mon.get("card_rate") and catalog.get("card_rate"):
            mon["card_rate"] = catalog.get("card_rate")
        if mon.get("boss") is None and catalog.get("boss"):
            mon["boss"] = True
    boss = bool(mon.get("boss"))
    min_rank = 1
    max_rank = 6 if boss else 4
    if boss:
        min_rank = 2
    has_table = monster_has_drop_table(mon)
    table_n = len(mon_drop_entries(mon)) if has_table else 0

    def _pack(iid: str, note: str = "", *, source: str = "") -> Dict[str, Any]:
        it = reg.items.get(iid) or reg.cards.get(iid) or {}
        base = item_default_rarity(it, reg) if it else "common"
        is_card = iid in (reg.cards or {}) or str(iid).startswith("card_")
        if is_card:
            rid = str(it.get("rarity") or base or "common")
        elif it.get("kind") == "equipment" or it.get("slot"):
            rid = roll_rarity(reg, rng, pool="drop", min_rank=min_rank, max_rank=max_rank)
        else:
            rid = base
            if rng.random() < 0.15:
                rid = roll_rarity(reg, rng, pool="drop", min_rank=1, max_rank=3)
        from game.domain.rarity import display_item_name

        nm = it.get("name") or iid
        default_note = "การ์ด" if is_card else format_rarity_tag(reg, rid)
        # WO-ITEM-1: soft source hint (never %)
        src = str(source or "")
        if not src:
            if is_card:
                src = "จากมอน · การ์ด"
            elif (it.get("kind") == "material") or "mat" in str(iid).lower():
                src = "ชิ้นส่วนมอน"
            elif it.get("kind") == "equipment" or it.get("slot"):
                src = "ของจากศัตรู"
            elif it.get("chest_rank"):
                src = "จากหีบ"
            else:
                src = "ดรอปสนาม"
        note_final = note or default_note
        # keep short: main note + soft source
        if src and src not in note_final:
            note_final = f"{note_final} · {src}" if note_final else src
        return {
            "id": iid,
            "name": display_item_name(str(nm), rid, reg) if not is_card else str(nm),
            "note": note_final,
            "rarity": rid,
            "source": src,
        }

    # ── 1) Per-monster table (identity) ──
    for raw in roll_monster_table_drops(player, mon, reg, rng):
        iid = str(raw.get("id") or "")
        note = str(raw.get("note") or "")
        if not note:
            if iid in (reg.cards or {}) or iid.startswith("card_"):
                note = "การ์ด · พันธะ"
            elif (reg.items.get(iid) or {}).get("kind") == "material":
                note = "ชิ้นส่วนมอน"
            elif (reg.items.get(iid) or {}).get("kind") == "equipment":
                note = "อุปกรณ์มอน"
            else:
                note = "จากศัตรู"
        drops.append(_pack(iid, note, source="จากมอน"))

    # ── 2) Generic fallback — WO-ITEM-1/5: thick table → soft reserve only ──
    # WO-ITEM-5 hot-fix (playtest harness): slightly lower than 2.10.0
    # no table: full 1.0 · thin 1–2: 0.22 · ≥3: 0.11 · ≥4: 0.08 · boss: 0.14
    if not has_table:
        gen_scale = 1.0
    elif boss:
        gen_scale = 0.14
    elif table_n >= 4:
        gen_scale = 0.08
    elif table_n >= 3:
        gen_scale = 0.11
    else:
        gen_scale = 0.22
    # still allow tiny soft reserve even on thick tables
    if has_table and not drops and gen_scale < 0.2:
        gen_scale = 0.20  # avoid empty loot feel if table rolled nothing
    if rng.random() < up_c * gen_scale:
        drops.append(_pack("upgrade_mat", "วัสดุสำรอง · ใช้คราฟได้", source="สำรองสนาม"))
    if rng.random() < rare_c * gen_scale * 0.85:
        drops.append(_pack("rare_mat", "วัสดุหายาก · สำรองสนาม", source="สำรองสนาม"))
    if rng.random() < 0.16 * gen_scale:
        drops.append(_pack("potion_hp_small", "ยาสำรองสนาม", source="สำรองสนาม"))
    if rng.random() < 0.07 * gen_scale:
        drops.append(_pack("potion_mana", "ยาสำรองสนาม", source="สำรองสนาม"))
    if mon.get("boss") and rng.random() < 0.35:
        for cid in ("steel_blade", "iron_plate", "shadow_dagger", "arcane_circlet", "scout_spear"):
            if cid in reg.items and rng.random() < 0.45:
                drops.append(_pack(cid, "อุปกรณ์บอส", source="จากบอส"))
                break
    elif (not has_table) and rng.random() < 0.08:
        for cid in ("iron_sword", "leather_armor", "copper_ring", "leather_cap"):
            if cid in reg.items:
                drops.append(_pack(cid, "อุปกรณ์", source="สำรองสนาม"))
                break

    # ── 3) Global card pool only if mon has no card_id (bound card is in table) ──
    bound = str(mon.get("card_id") or "").strip()
    already_card = any(
        str(d.get("id") or "").startswith("card_") or str(d.get("id") or "") in (reg.cards or {})
        for d in drops
    )
    card_ids = list((reg.cards or {}).keys())
    if card_ids and not bound and not already_card:
        mon_els = {str(e).lower() for e in (mon.get("elements") or [])}
        preferred: List[str] = []
        rest: List[str] = []
        for cid in card_ids:
            c = reg.cards.get(cid) or {}
            tags = {str(t).lower() for t in (c.get("grant_tags") or [])}
            if mon_els and tags & mon_els:
                preferred.append(cid)
            else:
                rest.append(cid)
        pool = preferred + rest
        card_chance = 0.18 if boss else 0.045
        if mon.get("elite"):
            card_chance = min(0.30, card_chance + 0.06)
        if mon.get("rarity") in ("rare", "sacred", "legendary"):
            card_chance = min(0.35, card_chance + 0.04)
        recent = list(player.get("recent_kill_ids") or [])
        mid = str(mon.get("id") or "")
        if mid and recent.count(mid) >= 4:
            card_chance *= 0.55
        if pool and rng.random() < card_chance:
            if preferred and rng.random() < 0.65:
                pick_c = preferred[rng.randrange(len(preferred))]
            else:
                pick_c = pool[rng.randrange(len(pool))]
            drops.append(_pack(pick_c, "การ์ด · ดรอป", source="จากมอน · การ์ด"))

    # soft floor: never return completely empty if mon existed
    if not drops and mid:
        drops.append(_pack("upgrade_mat", "เศษสนาม", source="สำรองสนาม"))

    seen = set()
    out = []
    for d in drops:
        key = f"{d['id']}:{d.get('rarity')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out
