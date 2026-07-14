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
    # after list repair we'll ensure instances

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
    return notes


def bag_count(player: Mapping[str, Any]) -> int:
    return len(player.get("inventory_ids") or []) + len(player.get("card_bag") or [])


# --- Categorized bag (docs/BAG_SYSTEM.md) ---

BAG_CATEGORIES = (
    "equipment",
    "healing",
    "material",
    "card",
    "other",
)

BAG_CATEGORY_LABELS = {
    "equipment": "อุปกรณ์",
    "healing": "รักษา",
    "material": "วัตถุดิบ",
    "card": "การ์ด",
    "other": "อื่นๆ",
}


def item_category(item_id: str, reg: DataRegistry) -> str:
    """
    Classify inventory item for bag hub.
    Returns: equipment | healing | material | card | other
    """
    iid = str(item_id or "")
    if not iid:
        return "other"
    if iid in (reg.cards or {}) or iid.startswith("card_"):
        return "card"
    it = item_by_id(reg, iid) or {}
    kind = str(it.get("kind") or "")
    slot = str(it.get("slot") or "")
    if kind == "equipment" or slot in ("weapon", "armor", "accessory"):
        return "equipment"
    if kind == "material" or "mat" in iid:
        return "material"
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
        )
    ):
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

    for i, iid in enumerate(ids):
        cat = item_category(str(iid), reg)
        if category and cat != category:
            continue
        it = item_by_id(reg, str(iid)) or {}
        rid = rarity_of_inventory_index(player, i)
        raw_name = str(it.get("name") or (inv[i] if i < len(inv) else iid))
        shown = display_item_name(raw_name, rid, reg)
        meta_bits = []
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
                "category": cat,
                "meta": it,
                "hint": " · ".join(str(x) for x in meta_bits),
            }
        )
    return out


def count_bag_categories(player: Mapping[str, Any], reg: DataRegistry) -> Dict[str, int]:
    counts = {c: 0 for c in BAG_CATEGORIES}
    for e in list_bag_entries(player, reg, None):
        cat = str(e.get("category") or "other")
        counts[cat] = counts.get(cat, 0) + 1
    counts["card"] = len(player.get("card_bag") or [])
    return counts


def format_bag_hub(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    """Hub lines: categories + counts + equipped summary (with short codes)."""
    ensure_bag(player)  # type: ignore
    from game.domain.item_codes import format_bag_equip_summary_lines
    from game.domain.rarity import ensure_inventory_rarity

    ensure_inventory_rarity(player)  # type: ignore
    n = bag_count(player)
    cap = int(player.get("bag_cap") or BAG_SOFT_CAP)
    counts = count_bag_categories(player, reg)
    lines = [f"── กระเป๋า ({n}/{cap}) ──"]
    lines.extend(format_bag_equip_summary_lines(player, reg))
    lines.extend(
        [
            "---",
            f" 1. อุปกรณ์     ({counts.get('equipment', 0)})",
            f" 2. รักษา       ({counts.get('healing', 0)})  ← ยา · บัฟ · ล้างสถานะ",
            f" 3. วัตถุดิบ    ({counts.get('material', 0)})",
            f" 4. การ์ด       ({counts.get('card', 0)})",
            f" 5. อื่นๆ       ({counts.get('other', 0)})",
            " 6. ที่สวมอยู่ / เกียร์ละเอียด",
            " 7. ร้าน (ทางลัด · หลัก=สำรวจ→6)",
            " 8. คราฟ (ทางลัด)",
            " 9. ดูทั้งหมด",
            " M. โหมดร้าน/ตลาด   J. กระดานภารกิจ",
            " 0. กลับ",
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
    lines = [f"── {label} ──"]
    if category == "equipment":
        lines.append("  (ไอดีสั้น เช่น sw001 · ชื่อ · [สัญลักษณ์] ชื่อระดับ — พิมพ์หมายเลข/ไอดี)")
    if not entries:
        lines.append("  (ว่าง)")
        lines.append("  0. กลับ")
        return lines
    if category == "equipment":
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
    else:
        for i, e in enumerate(entries, 1):
            hint = f"  {e['hint']}" if e.get("hint") else ""
            lines.append(f"  {i}. {e['name']}{hint}")
    lines.append("  0. กลับ")
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
) -> Tuple[bool, str]:
    ensure_bag(player)
    if bag_full(player):
        return False, "กระเป๋าเต็ม — ต้องทิ้งของหรือไม่เก็บ"
    name = add_item(player, item_id, reg, rarity=rarity)
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
    is_equipment = kind == "equipment" or slot in ("weapon", "armor", "accessory")

    # Premium gear card for equipment (id + ระดับอาวุธ + frame by rarity)
    if is_equipment:
        from game.ui_terminal.gear_showcase import format_examine_with_showcase

        lines = format_examine_with_showcase(item_id, reg, rarity=rid, howto=True)
        if it.get("price_world"):
            lines.append(f" มูลค่าตลาดโลก: ~{it['price_world']}")
        if it.get("price_heaven"):
            lines.append(f" มูลค่าสวรรค์: ~{it['price_heaven']}")
        if it.get("price_hell"):
            lines.append(f" มูลค่านรก: ~{it['price_hell']}")
        return lines

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
    # combat stats with rarity scaling
    slot_s = slot or "weapon"
    if it.get("atk") or it.get("max_hp") or it.get("max_mana"):
        st = scaled_item_stats(it, rid, reg, upgrade_level=0, slot=slot_s)
        bits = []
        if st["atk"]:
            bits.append(f"โจมตี +{st['atk']}")
        if st["max_hp"]:
            bits.append(f"HP +{st['max_hp']}")
        if st["max_mana"]:
            bits.append(f"MP +{st['max_mana']}")
        if bits:
            mult = rarity_stat_mult(reg, rid)
            lines.append(" คุณสมบัติ: " + " · ".join(bits) + f"  (คูณระดับ ×{mult:.2f})")
    else:
        bits = []
        if it.get("atk"):
            bits.append(f"โจมตี +{it['atk']}")
        if it.get("max_hp"):
            bits.append(f"HP +{it['max_hp']}")
        if it.get("max_mana"):
            bits.append(f"MP +{it['max_mana']}")
        if bits:
            lines.append(" คุณสมบัติ: " + " · ".join(bits))
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
    return {"weapon": "อาวุธ", "armor": "เกราะ", "accessory": "เครื่องประดับ"}.get(slot, slot)


def format_bag_panel(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_bag(player)  # type: ignore
    cap = int(player.get("bag_cap") or BAG_SOFT_CAP)
    n = bag_count(player)
    lines = [f"── กระเป๋า ({n}/{cap}) ──"]
    ids = list(player.get("inventory_ids") or [])
    if not ids:
        lines.append("  (ว่างจากไอเทม — ของใช้/เกียร์/วัสดุ)")
    else:
        # stack counts
        from collections import Counter

        c = Counter(ids)
        # show each stack; rarity may differ — show first index rarity as sample
        from game.domain.rarity import format_rarity_tag, rarity_of_inventory_index

        shown = 0
        keys = sorted(c.keys())
        for iid in keys:
            cnt = c[iid]
            shown += 1
            it = reg.items.get(iid) or {}
            name = it.get("name") or iid
            kind = _kind_th(str(it.get("kind") or "item"))
            from game.domain.rarity import display_item_name, rarity_of_inventory_index as _roi

            try:
                idx0 = list(player.get("inventory_ids") or []).index(iid)
                rid0 = _roi(player, idx0)
            except Exception:
                rid0 = "common"
            dname = display_item_name(str(name), rid0, reg)
            extra = f" x{cnt}" if cnt > 1 else ""
            lines.append(f"  {shown}. {dname}{extra}  [{kind}]")
    cards = list(player.get("card_bag") or [])
    if cards:
        lines.append(" ── การ์ดในถุง ──")
        for i, cid in enumerate(cards, 1):
            nm = (reg.cards.get(cid) or {}).get("name") or cid
            lines.append(f"  C{i}. {nm}")
    lines.append("  เลือกหมายเลขเพื่อดูรายละเอียด · 0 กลับ")
    return lines


def bag_item_id_at(player: Mapping[str, Any], index_1based: int) -> Optional[str]:
    """Map panel index to unique item id (first of stacked)."""
    from collections import Counter

    ids = list(player.get("inventory_ids") or [])
    keys = sorted(Counter(ids).keys())
    if index_1based < 1 or index_1based > len(keys):
        return None
    return keys[index_1based - 1]


def bag_item_rarity_at(player: Mapping[str, Any], index_1based: int) -> str:
    from collections import Counter
    from game.domain.rarity import rarity_of_inventory_index

    ids = list(player.get("inventory_ids") or [])
    keys = sorted(Counter(ids).keys())
    if index_1based < 1 or index_1based > len(keys):
        return "common"
    iid = keys[index_1based - 1]
    try:
        idx0 = ids.index(iid)
        return rarity_of_inventory_index(player, idx0)
    except Exception:
        return "common"


def format_equip_panel(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    """What is worn + soft power bonuses (visible)."""
    ensure_gear_fields(player)  # type: ignore
    lines = ["── สวมใส่อุปกรณ์ ──"]
    total_atk = 0
    total_hp = 0
    total_mp = 0
    from game.domain.rarity import equip_rarity_for_slot, format_rarity_tag, scaled_item_stats

    for slot, label in (("weapon", "อาวุธ"), ("armor", "เกราะ"), ("accessory", "เครื่องประดับ")):
        eid = (player.get("equip_ids") or {}).get(slot)
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        if not eid:
            lines.append(f" {label}: (ว่าง)")
            continue
        it = reg.items.get(eid) or {}
        name = it.get("name") or eid
        rid = equip_rarity_for_slot(player, slot)
        st = scaled_item_stats(it, rid, reg, upgrade_level=up, slot=slot)
        atk, hp, mp = st["atk"], st["max_hp"], st["max_mana"]
        total_atk += atk
        total_hp += hp
        total_mp += mp
        from game.domain.rarity import display_item_name as _din

        lines.append(f" {label}: {_din(str(name), rid, reg)}  +{up}")
        lines.append(f"   เสริมพลัง: ATK+{atk} · HP+{hp} · MP+{mp}")
        if it.get("tags"):
            lines.append("   แท็ก: " + ", ".join(str(t) for t in it["tags"]))
        socks = list((player.get("sockets") or {}).get(slot) or [])
        if socks:
            parts = []
            for cid in socks:
                if not cid:
                    parts.append("ว่าง")
                else:
                    parts.append(str((reg.cards.get(cid) or {}).get("name") or cid))
            lines.append("   การ์ด: " + ", ".join(parts))
    lines.append(f" รวมจากเกียร์ (โดยประมาณ): ATK+{total_atk} · HP+{total_hp} · MP+{total_mp}")
    if player.get("active_sets"):
        lines.append(" เซ็ตที่ทำงาน: " + ", ".join(str(x) for x in player["active_sets"]))
        for fl in player.get("set_flavors") or []:
            lines.append(f"  “{fl}”")
    if player.get("party_bonus_atk") or player.get("party_bonus_max_hp"):
        lines.append(
            f" ปาร์ตี้ (พาสซีฟ): ATK+{player.get('party_bonus_atk', 0)} · "
            f"HP+{player.get('party_bonus_max_hp', 0)} · MP+{player.get('party_bonus_max_mana', 0)}"
        )
    lines.append(
        f" สถานะรวมปัจจุบัน: ATK {player.get('bonus_atk')} · "
        f"HP {player.get('hp')}/{player.get('max_hp')} · "
        f"MP {player.get('mana')}/{player.get('max_mana')}"
    )
    return lines


UPGRADE_MAX_LEVEL = 10


def upgrade_success_chance(slot: str, level: int) -> float:
    """Hidden curve — higher level = lower success. Exact % soft-labeled in UI."""
    # +0: 95%, +5: ~70%, +9: ~40%
    base = 0.95 - level * 0.06
    return max(0.25, min(0.98, base))


def can_upgrade_equipped(
    player: Mapping[str, Any],
    slot: str,
) -> bool:
    """True if slot has gear and upgrade level is below cap."""
    ensure_gear_fields(player)  # type: ignore
    if slot not in ("weapon", "armor", "accessory"):
        return False
    if not (player.get("equip_ids") or {}).get(slot):
        return False
    cur = int((player.get("upgrade_levels") or {}).get(slot, 0))
    return cur < UPGRADE_MAX_LEVEL


def upgrade_chance_label(slot: str, level: int) -> str:
    rate = upgrade_success_chance(slot, level)
    if rate >= 0.8:
        return "โอกาสสูง"
    if rate >= 0.55:
        return "โอกาสปานกลาง"
    return "เสี่ยงสูง"


def format_upgrade_preview(
    player: Mapping[str, Any],
    slot: str,
    reg: DataRegistry,
) -> List[str]:
    """
    Explicit cost sheet so players learn which items matter.
    Shows item names, ids, need vs have, money, soft success feel.
    """
    ensure_gear_fields(player)  # type: ignore
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
    cost = upgrade_cost(slot, cur)
    money = int(player.get("money_world") or 0)
    have_um = count_materials(player, "upgrade_mat")
    have_rm = count_materials(player, "rare_mat")
    need_m = int(cost["money"])
    need_um = int(cost["upgrade_mat"])
    need_rm = int(cost["rare_mat"])

    um_it = reg.items.get("upgrade_mat") or {}
    rm_it = reg.items.get("rare_mat") or {}
    um_name = str(um_it.get("name") or "วัสดุอัพเกรด")
    rm_name = str(rm_it.get("name") or "วัสดุหายาก")
    um_code = item_code("upgrade_mat", reg)
    rm_code = item_code("rare_mat", reg)

    def _ok(have: int, need: int) -> str:
        return "✓ พอ" if have >= need else "✗ ไม่พอ"

    lines = [
        "── พิธีอัปเกรด ──",
        f" ชิ้น: {code} {name}  ({_slot_th(slot)})",
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

    feel = upgrade_chance_label(slot, cur)
    lines.append("---")
    lines.append(f" โอกาสสำเร็จ (ประมาณ): {feel}")
    lines.append(" ผลเมื่อสำเร็จ: พลังชิ้นเกียร์เพิ่มขึ้นเล็กน้อย (ATK/HP/MP ตามชนิด)")
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
) -> bool:
    if not can_upgrade_equipped(player, slot):
        return False
    cur = int((player.get("upgrade_levels") or {}).get(slot, 0))
    cost = upgrade_cost(slot, cur)
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
    Upgrade with success rate. Costs already shown in preview; failures still consume.
    """
    ensure_gear_fields(player)
    rng = rng or random.Random()
    if slot not in ("weapon", "armor", "accessory"):
        return "ช่องไม่ถูกต้อง"
    if not (player.get("equip_ids") or {}).get(slot):
        return f"ยังไม่มี{_slot_th(slot)}สวมอยู่"
    ups = dict(player.get("upgrade_levels") or {})
    cur = int(ups.get(slot, 0))
    if cur >= UPGRADE_MAX_LEVEL:
        return "ถึงขีดอัปแล้ว — อัปต่อไม่ได้"
    cost = upgrade_cost(slot, cur)
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
    from game.domain.equipment import consume_materials

    consume_materials(player, "upgrade_mat", cost["upgrade_mat"], reg)
    if cost["rare_mat"]:
        consume_materials(player, "rare_mat", cost["rare_mat"], reg)

    chance = upgrade_success_chance(slot, cur)
    if rng.random() <= chance:
        ups[slot] = cur + 1
        player["upgrade_levels"] = ups
        recompute_stats(player, reg)
        return f"อัปเกรด{_slot_th(slot)} สำเร็จ → +{ups[slot]}! (เสริมพลังเพิ่มขึ้น)"
    recompute_stats(player, reg)
    soft = "ใกล้แล้ว..." if chance > 0.6 else "พิธีสั่นคลอน..."
    return f"อัปเกรดล้มเหลว — วัสดุ/เงินถูกใช้แล้ว {soft} (ขั้นยัง +{cur})"


def soft_upgrade_hint(slot: str, level: int) -> str:
    """One-line soft summary (still used in compact UI)."""
    c = upgrade_cost(slot, level)
    parts = [f"เงินโลก ~{c['money']}"]
    if c["upgrade_mat"]:
        parts.append(f"วัสดุอัป ×{c['upgrade_mat']}")
    if c["rare_mat"]:
        parts.append(f"วัสดุหายาก ×{c['rare_mat']}")
    feel = upgrade_chance_label(slot, level)
    return f"อัปถัดไป: {', '.join(parts)} · {feel}"


# ---- Loot choice ----

def present_loot_choices(
    drops: Sequence[Dict[str, Any]],
) -> List[str]:
    """drops: [{id, name, note?}]"""
    lines = ["── ของที่ตก ──", " เลือกเก็บ (พิมพ์หมายเลขคั่นด้วย comma) หรือ 0 = ไม่เก็บ"]
    for i, d in enumerate(drops, 1):
        note = f" — {d['note']}" if d.get("note") else ""
        lines.append(f"  {i}. {d.get('name')}{note}")
    return lines


def resolve_loot_pick(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    drops: Sequence[Dict[str, Any]],
    choice_text: str,
) -> List[str]:
    """Player picks which drops to keep. Respects bag capacity."""
    notes: List[str] = []
    text = choice_text.strip()
    if text in ("0", "", "n", "N"):
        return ["ทิ้งของทั้งหมดไว้"]
    idxs: List[int] = []
    for part in text.replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idxs.append(int(part))
        except ValueError:
            continue
    if not idxs:
        return ["ไม่ได้เลือก — ของหายไป"]
    for ix in idxs:
        if ix < 1 or ix > len(drops):
            continue
        d = drops[ix - 1]
        iid = str(d.get("id") or "")
        if not iid:
            continue
        ok, name = try_add_item(player, iid, reg, rarity=d.get("rarity"))
        if ok:
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
    """Generate drop options after win — player chooses. Each piece may roll rarity."""
    from game.domain.balance import material_drop_chances
    from game.domain.rarity import format_rarity_tag, item_default_rarity, roll_rarity

    drops: List[Dict[str, Any]] = []
    up_c, rare_c = material_drop_chances(player)
    boss = bool(mon.get("boss"))
    min_rank = 1
    max_rank = 6 if boss else 4
    if boss:
        min_rank = 2

    def _pack(iid: str, note: str = "") -> Dict[str, Any]:
        it = reg.items.get(iid) or {}
        base = item_default_rarity(it, reg)
        # equipment rolls higher variance; mats often keep default with small upgrade chance
        if it.get("kind") == "equipment" or it.get("slot"):
            rid = roll_rarity(reg, rng, pool="drop", min_rank=min_rank, max_rank=max_rank)
        else:
            rid = base
            if rng.random() < 0.15:
                rid = roll_rarity(reg, rng, pool="drop", min_rank=1, max_rank=3)
        from game.domain.rarity import display_item_name

        nm = it.get("name") or iid
        return {
            "id": iid,
            "name": display_item_name(str(nm), rid, reg),
            "note": note or format_rarity_tag(reg, rid),
            "rarity": rid,
        }

    if rng.random() < up_c:
        drops.append(_pack("upgrade_mat", "วัสดุ"))
    if rng.random() < rare_c:
        drops.append(_pack("rare_mat", "วัสดุหายาก"))
    if rng.random() < 0.25:
        drops.append(_pack("potion_hp_small", "ใช้ได้"))
    if rng.random() < 0.12:
        drops.append(_pack("potion_mana", "ใช้ได้"))
    if mon.get("boss") and rng.random() < 0.35:
        for cid in ("steel_blade", "iron_plate", "shadow_dagger", "arcane_circlet"):
            if cid in reg.items and rng.random() < 0.45:
                drops.append(_pack(cid, "อุปกรณ์"))
                break
    elif rng.random() < 0.08:
        for cid in ("iron_sword", "leather_armor", "copper_ring"):
            if cid in reg.items:
                drops.append(_pack(cid, "อุปกรณ์"))
                break
    seen = set()
    out = []
    for d in drops:
        key = f"{d['id']}:{d.get('rarity')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out
