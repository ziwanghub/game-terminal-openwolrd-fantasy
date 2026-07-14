"""
Short player-facing item codes (sw001, ar001, …).

Players type these in the bag to inspect equipped / bag gear.
Prefer `code` from item YAML; fallback table + auto-slot codes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from game.data_load.registry import DataRegistry


# Stable defaults (overridden by item YAML `code` when present)
_DEFAULT_CODES: Dict[str, str] = {
    "iron_sword": "sw001",
    "steel_blade": "sw002",
    "shadow_dagger": "sw003",
    "apprentice_staff": "sw004",
    "thorn_blade": "sw005",
    "leather_armor": "ar001",
    "iron_plate": "ar002",
    "mage_robe": "ar003",
    "shadow_cloak": "ar004",
    "thorn_mail": "ar005",
    "copper_ring": "ac001",
    "silver_amulet": "ac002",
    "shadow_band": "ac003",
    "arcane_circlet": "ac004",
}

_SLOT_PREFIX = {
    "weapon": "sw",
    "armor": "ar",
    "accessory": "ac",
}


def item_code(item_id: str, reg: Optional[DataRegistry] = None) -> str:
    """Player-facing short code for an item id."""
    iid = str(item_id or "")
    if not iid:
        return ""
    if reg is not None:
        it = (reg.items or {}).get(iid) or (reg.cards or {}).get(iid) or {}
        c = it.get("code")
        if c:
            return str(c).strip().lower()
    if iid in _DEFAULT_CODES:
        return _DEFAULT_CODES[iid]
    # cards
    if iid.startswith("card_") or (reg and iid in (reg.cards or {})):
        tail = iid.replace("card_", "")[:4]
        return f"cd_{tail}" if tail else "cd000"
    # materials / consumables soft code
    if "mat" in iid:
        return f"mt_{iid[:6]}"
    if "potion" in iid or "heal" in iid:
        return f"pt_{iid[-4:]}" if len(iid) >= 4 else f"pt_{iid}"
    return iid  # fallback: raw id still typeable


def build_code_index(reg: DataRegistry) -> Dict[str, str]:
    """Map short_code.lower() → item_id (first wins; yaml codes preferred)."""
    idx: Dict[str, str] = {}
    for iid, it in (reg.items or {}).items():
        code = item_code(str(iid), reg)
        if code and code not in idx:
            idx[code.lower()] = str(iid)
    for iid in reg.cards or {}:
        code = item_code(str(iid), reg)
        if code and code not in idx:
            idx[code.lower()] = str(iid)
    # also allow raw item id lookup
    for iid in list(reg.items or {}) + list(reg.cards or {}):
        idx.setdefault(str(iid).lower(), str(iid))
    return idx


def resolve_code(raw: str, reg: DataRegistry) -> Optional[str]:
    """Resolve player input to item_id. Accepts short code or full id."""
    key = (raw or "").strip().lower()
    if not key:
        return None
    idx = build_code_index(reg)
    if key in idx:
        return idx[key]
    # unique prefix among codes
    hits = [iid for c, iid in idx.items() if c.startswith(key) and len(key) >= 3]
    # dedupe item ids
    uniq = list(dict.fromkeys(hits))
    if len(uniq) == 1:
        return uniq[0]
    return None


def rarity_observe_tag(reg: Optional[DataRegistry], rarity_id: str) -> str:
    """
    Compact + readable: [○] ธรรมดา
    Symbol alone is easy to miss — always pair with Thai name.
    """
    from game.domain.rarity import tier_by_id

    t = tier_by_id(reg, rarity_id)
    tag = str(t.get("color_tag") or "○")
    name = str(t.get("name") or rarity_id or "ธรรมดา")
    return f"[{tag}] {name}"


def rarity_legend_line(reg: Optional[DataRegistry] = None) -> str:
    """One soft legend line for bag hub."""
    from game.domain.rarity import all_tiers

    parts = []
    for t in all_tiers(reg)[:6]:  # first 6 to keep width
        tag = t.get("color_tag") or "?"
        name = t.get("name") or t.get("id")
        parts.append(f"[{tag}]={name}")
    return "ระดับ: " + " ".join(parts) + " …"


def format_equipped_piece(
    item_id: str,
    reg: DataRegistry,
    rarity_id: str,
    *,
    upgrade: int = 0,
) -> str:
    """e.g. sw001 ดาบเหล็ก [○] ธรรมดา +0"""
    it = (reg.items or {}).get(item_id) or {}
    name = str(it.get("name") or item_id)
    code = item_code(item_id, reg)
    obs = rarity_observe_tag(reg, rarity_id)
    up = f" +{upgrade}" if upgrade else ""
    return f"{code} {name} {obs}{up}"


def list_equipped_entries(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Dict[str, Any]]:
    """
    Equipped slots as dicts for hub / manage:
    {slot, id, code, rarity, upgrade, label}
    """
    from game.domain.rarity import equip_rarity_for_slot

    out: List[Dict[str, Any]] = []
    labels = {"weapon": "อาวุธ", "armor": "เกราะ", "accessory": "เครื่องประดับ"}
    for slot in ("weapon", "armor", "accessory"):
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            continue
        rid = equip_rarity_for_slot(player, slot)
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        out.append(
            {
                "slot": slot,
                "id": str(eid),
                "code": item_code(str(eid), reg),
                "rarity": rid,
                "upgrade": up,
                "label": labels.get(slot, slot),
                "line": format_equipped_piece(str(eid), reg, rid, upgrade=up),
            }
        )
    return out


def find_equipped_by_code(
    player: Mapping[str, Any],
    reg: DataRegistry,
    raw: str,
) -> Optional[Dict[str, Any]]:
    key = (raw or "").strip().lower()
    if not key:
        return None
    from game.domain.item_instances import (
        ensure_item_instances,
        format_instance_ref,
        get_equipped_instance,
        parse_instance_ref,
    )

    ensure_item_instances(player, reg)  # type: ignore
    parsed = parse_instance_ref(key)
    for e in list_equipped_entries(player, reg):
        if e["code"].lower() == key or e["id"].lower() == key:
            return e
        if key in e["code"].lower() and len(key) >= 3:
            return e
        inst = get_equipped_instance(player, str(e.get("slot")))
        if not inst:
            continue
        ref = format_instance_ref(inst).lower()
        if key == ref or key == ref.split("#")[0]:
            return e
        if parsed.get("inst_id") and str(inst.get("inst_id")) == parsed["inst_id"]:
            return e
        code_part = str(parsed.get("code_or_id") or "")
        if code_part in (e["code"].lower(), e["id"].lower(), str(inst.get("code") or "").lower()):
            if not parsed.get("owner_short") or parsed["owner_short"] == inst.get(
                "owner_short"
            ):
                return e
    return None


def format_bag_equip_summary_lines(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """Hub block: equipped pieces with instance refs (owner#inst)."""
    from game.domain.item_instances import (
        ensure_item_instances,
        format_equipped_ref_line,
        format_instance_ref,
        get_equipped_instance,
    )

    ensure_item_instances(player, reg)  # type: ignore
    lines = [" สวมอยู่ (พิมพ์รหัสชิ้นเพื่อดู/จัดการ):"]
    labels = (("weapon", "อาวุธ"), ("armor", "เกราะ"), ("accessory", "เครื่องประดับ"))
    any_eq = False
    example = "sw001"
    for slot, lab in labels:
        eid = (player.get("equip_ids") or {}).get(slot)
        if not eid:
            lines.append(f"   {lab}: —")
            continue
        any_eq = True
        line = format_equipped_ref_line(player, reg, slot)
        lines.append(f"   {lab}: {line}")
        inst = get_equipped_instance(player, slot)
        if inst:
            example = format_instance_ref(inst)
    if any_eq:
        lines.append(f" {rarity_legend_line(reg)}")
        lines.append("  sw001 = ชนิด · sw001_xxxx#yyyy = ชิ้นมีเจ้าของ")
        lines.append(f"  ตัวอย่าง: พิมพ์ {example.split('#')[0]} หรือรหัสเต็ม → จัดการ")
        lines.append("  สนาม: f_mn01 · upgrade_sw001 · ? = ช่วยคำสั่ง")
    return lines
