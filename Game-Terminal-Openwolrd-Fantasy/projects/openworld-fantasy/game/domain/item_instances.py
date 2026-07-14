"""
Item instance layer — template vs owned piece (COMMAND_AND_INSTANCE_IDS.md).

Template:  sw001
Owned:     sw001_a3f2#b91c01   (template_ownerShort#instId)

Persistence: inventory_items + equip_instances are source of truth when present.
Legacy lists (inventory_ids / rarities) stay synced for older code paths.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from game.data_load.registry import DataRegistry


def owner_short(player: Mapping[str, Any]) -> str:
    """Stable 4-char owner tag from player id/name."""
    raw = str(player.get("id") or "").strip()
    if not raw:
        raw = str(player.get("name") or "self")
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:4]


def new_inst_id() -> str:
    return secrets.token_hex(3)  # 6 hex chars


def make_instance(
    template_id: str,
    player: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
    *,
    rarity: str = "common",
    upgrade: int = 0,
    sockets: Optional[List[Any]] = None,
    location: str = "bag",
    inst_id: Optional[str] = None,
) -> Dict[str, Any]:
    from game.domain.item_codes import item_code
    from game.domain.rarity import item_default_rarity

    it = {}
    if reg is not None:
        it = (reg.items or {}).get(template_id) or {}
    rid = str(rarity or item_default_rarity(it, reg) or "common")
    code = item_code(template_id, reg)
    oid = owner_short(player)
    iid = str(inst_id or new_inst_id())
    n_sock = int(it.get("sockets") or 0) if it else 0
    socks = list(sockets) if sockets is not None else [None] * n_sock
    return {
        "inst_id": iid,
        "template_id": str(template_id),
        "code": code,
        "owner_id": str(player.get("id") or ""),
        "owner_short": oid,
        "rarity": rid,
        "upgrade": int(upgrade or 0),
        "sockets": socks,
        "location": location,
    }


def format_instance_ref(inst: Mapping[str, Any], *, with_hash: bool = True) -> str:
    """sw001_a3f2#b91c01 or sw001 if no owner."""
    code = str(inst.get("code") or inst.get("template_id") or "?")
    o = str(inst.get("owner_short") or "")
    iid = str(inst.get("inst_id") or "")
    if not o:
        return code
    base = f"{code}_{o}"
    if with_hash and iid:
        return f"{base}#{iid}"
    return base


def parse_instance_ref(raw: str) -> Dict[str, Optional[str]]:
    """
    Parse sw001 / sw001_a3f2 / sw001_a3f2#b91c01 / iron_sword
    → {code_or_id, owner_short, inst_id}
    """
    key = (raw or "").strip().lower()
    out: Dict[str, Optional[str]] = {
        "code_or_id": key,
        "owner_short": None,
        "inst_id": None,
    }
    if not key:
        return out
    if "#" in key:
        left, right = key.split("#", 1)
        out["inst_id"] = right
        key = left
    if "_" in key:
        parts = key.rsplit("_", 1)
        if (
            len(parts) == 2
            and len(parts[1]) == 4
            and all(c in "0123456789abcdef" for c in parts[1])
        ):
            out["code_or_id"] = parts[0]
            out["owner_short"] = parts[1]
            return out
    out["code_or_id"] = key
    return out


def _normalize_inst(
    raw: Mapping[str, Any],
    player: Mapping[str, Any],
    reg: Optional[DataRegistry],
    *,
    location: str,
) -> Dict[str, Any]:
    tid = str(raw.get("template_id") or raw.get("id") or "")
    return make_instance(
        tid,
        player,
        reg,
        rarity=str(raw.get("rarity") or "common"),
        upgrade=int(raw.get("upgrade") or 0),
        sockets=list(raw.get("sockets") or []),
        location=location,
        inst_id=str(raw.get("inst_id") or "") or None,
    )


def _rematch_bag_instances(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry],
    ids: List[str],
    rares: List[str],
    old_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Align bag instances to inventory_ids without losing inst_id when possible.
    Match by (template_id, rarity) greedily from old list.
    """
    pool = [dict(x) for x in old_items if x and x.get("template_id")]
    out: List[Dict[str, Any]] = []
    for i, tid in enumerate(ids):
        rid = str(rares[i] if i < len(rares) else "common") or "common"
        found = None
        for j, cand in enumerate(pool):
            if str(cand.get("template_id")) == str(tid) and str(
                cand.get("rarity") or "common"
            ) == rid:
                found = pool.pop(j)
                break
        if found is None:
            for j, cand in enumerate(pool):
                if str(cand.get("template_id")) == str(tid):
                    found = pool.pop(j)
                    found["rarity"] = rid
                    break
        if found:
            found["location"] = "bag"
            found["owner_short"] = owner_short(player)
            if player.get("id"):
                found["owner_id"] = str(player.get("id"))
            if not found.get("inst_id"):
                found["inst_id"] = new_inst_id()
            if not found.get("code") and reg is not None:
                from game.domain.item_codes import item_code

                found["code"] = item_code(str(tid), reg)
            out.append(found)
        else:
            out.append(
                make_instance(
                    str(tid), player, reg, rarity=rid, location="bag"
                )
            )
    return out


def ensure_item_instances(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
    *,
    force_rebuild: bool = False,
) -> None:
    """
    Ensure inventory_items + equip_instances.

    Persistence rules:
    - Prefer existing inventory_items when present (keep inst_id).
    - Only create new inst_id for brand-new slots.
    - Equipped: keep inst_id if same template_id.
    """
    from game.domain.equipment import ensure_gear_fields
    from game.domain.rarity import ensure_inventory_rarity

    ensure_gear_fields(player)
    ensure_inventory_rarity(player)
    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    old_items = [dict(x) for x in (player.get("inventory_items") or []) if isinstance(x, dict)]

    if force_rebuild or not old_items:
        items = _rematch_bag_instances(player, reg, ids, rares, [])
    elif len(old_items) == len(ids):
        # same length: fix fields, keep inst_ids; realign template if drifted
        items = []
        for i, tid in enumerate(ids):
            inst = dict(old_items[i])
            rid = str(rares[i] if i < len(rares) else inst.get("rarity") or "common")
            if str(inst.get("template_id")) != str(tid):
                # slot drifted — rematch this index from pool
                rem = _rematch_bag_instances(
                    player, reg, [tid], [rid], [inst] + old_items[i + 1 :]
                )
                inst = rem[0] if rem else make_instance(
                    str(tid), player, reg, rarity=rid, location="bag"
                )
            else:
                inst["template_id"] = str(tid)
                inst["rarity"] = rid
                inst["location"] = "bag"
                inst["owner_short"] = owner_short(player)
                if player.get("id"):
                    inst["owner_id"] = str(player.get("id"))
                if not inst.get("inst_id"):
                    inst["inst_id"] = new_inst_id()
                if reg is not None and not inst.get("code"):
                    from game.domain.item_codes import item_code

                    inst["code"] = item_code(str(tid), reg)
            items.append(inst)
    else:
        # length mismatch: rematch preserving as many inst_ids as possible
        items = _rematch_bag_instances(player, reg, ids, rares, old_items)

    player["inventory_items"] = items

    # equipped instances — preserve inst_id (multi-slot EL0+)
    from game.domain.equipment import EQUIP_SLOTS, migrate_equip_loadout

    try:
        migrate_equip_loadout(player)  # type: ignore
    except Exception:
        pass
    eq_inst = dict(player.get("equip_instances") or {})
    for slot in EQUIP_SLOTS:
        eq_inst.setdefault(slot, None)
        tid = (player.get("equip_ids") or {}).get(slot)
        if not tid:
            eq_inst[slot] = None
            continue
        cur = eq_inst.get(slot)
        rid = str((player.get("equip_rarities") or {}).get(slot) or "common")
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        socks = list((player.get("sockets") or {}).get(slot) or [])
        if (
            cur
            and isinstance(cur, dict)
            and str(cur.get("template_id")) == str(tid)
            and cur.get("inst_id")
        ):
            cur = dict(cur)
            cur["upgrade"] = up
            cur["rarity"] = str(
                (player.get("equip_rarities") or {}).get(slot) or cur.get("rarity") or rid
            )
            cur["sockets"] = socks if socks else list(cur.get("sockets") or [])
            cur["location"] = f"equip:{slot}"
            cur["owner_short"] = owner_short(player)
            if player.get("id"):
                cur["owner_id"] = str(player.get("id"))
            if reg is not None:
                from game.domain.item_codes import item_code

                cur["code"] = item_code(str(tid), reg)
            eq_inst[slot] = cur
        else:
            # try reclaim inst_id from previous cur if same template was lost only fields
            keep_id = None
            if cur and isinstance(cur, dict) and str(cur.get("template_id")) == str(tid):
                keep_id = cur.get("inst_id")
            eq_inst[slot] = make_instance(
                str(tid),
                player,
                reg,
                rarity=rid,
                upgrade=up,
                sockets=socks,
                location=f"equip:{slot}",
                inst_id=str(keep_id) if keep_id else None,
            )
    player["equip_instances"] = eq_inst


def sync_legacy_from_instances(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> None:
    """Write inventory_ids / rarities / inventory names from inventory_items."""
    from game.domain.rarity import display_item_name

    items = list(player.get("inventory_items") or [])
    ids: List[str] = []
    rares: List[str] = []
    names: List[str] = []
    for inst in items:
        tid = str(inst.get("template_id") or "")
        rid = str(inst.get("rarity") or "common")
        ids.append(tid)
        rares.append(rid)
        if reg is not None:
            nm = (reg.items.get(tid) or {}).get("name") or tid
            names.append(display_item_name(str(nm), rid, reg))
        else:
            names.append(tid)
    player["inventory_ids"] = ids
    player["inventory_rarities"] = rares
    player["inventory"] = names
    player["inventory_source"] = "instances"


def sync_canonical_inventory(
    player: MutableMapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> None:
    """
    Prefer inventory_items as single source of truth, then mirror to legacy lists.

    - If bag instances exist → normalize + legacy rebuilt (inst_id preserved).
    - Else rebuild instances from inventory_ids, then mirror legacy.
    Equip slots fixed via ensure_item_instances after bag is settled.
    """
    items = [x for x in (player.get("inventory_items") or []) if isinstance(x, dict)]
    if items:
        clean = [dict(x) for x in items if x.get("template_id")]
        for inst in clean:
            inst["location"] = "bag"
            if not inst.get("inst_id"):
                inst["inst_id"] = new_inst_id()
            if not inst.get("owner_short"):
                inst["owner_short"] = owner_short(player)
            if player.get("id"):
                inst["owner_id"] = str(player.get("id"))
            if reg is not None and not inst.get("code"):
                from game.domain.item_codes import item_code

                inst["code"] = item_code(str(inst.get("template_id")), reg)
        player["inventory_items"] = clean
        sync_legacy_from_instances(player, reg)
        # equip only — ensure_item_instances keeps bag when lengths match
        ensure_item_instances(player, reg, force_rebuild=False)
        # re-assert bag SoT if ensure rematched wrongly
        if len(player.get("inventory_items") or []) != len(clean):
            player["inventory_items"] = clean
        sync_legacy_from_instances(player, reg)
        return
    ensure_item_instances(player, reg, force_rebuild=True)
    sync_legacy_from_instances(player, reg)


def append_instance(
    player: MutableMapping[str, Any],
    template_id: str,
    reg: DataRegistry,
    *,
    rarity: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_item_instances(player, reg)
    from game.domain.rarity import item_default_rarity

    it = reg.items.get(template_id) or {}
    rid = str(rarity or item_default_rarity(it, reg))
    inst = make_instance(template_id, player, reg, rarity=rid, location="bag")
    bag = list(player.get("inventory_items") or [])
    bag.append(inst)
    player["inventory_items"] = bag
    sync_legacy_from_instances(player, reg)
    return inst


def pop_instance_at(
    player: MutableMapping[str, Any],
    index: int,
    reg: Optional[DataRegistry] = None,
) -> Optional[Dict[str, Any]]:
    """Remove bag instance at index; sync legacy lists."""
    items = list(player.get("inventory_items") or [])
    if index < 0 or index >= len(items):
        # fall back to ids only
        ids = list(player.get("inventory_ids") or [])
        if 0 <= index < len(ids):
            ids.pop(index)
            player["inventory_ids"] = ids
            rares = list(player.get("inventory_rarities") or [])
            if index < len(rares):
                rares.pop(index)
            player["inventory_rarities"] = rares
            inv = list(player.get("inventory") or [])
            if index < len(inv):
                inv.pop(index)
            player["inventory"] = inv
            ensure_item_instances(player, reg)
        return None
    inst = items.pop(index)
    player["inventory_items"] = items
    sync_legacy_from_instances(player, reg)
    return inst


def find_instances(
    player: Mapping[str, Any],
    reg: DataRegistry,
    raw: str,
    *,
    location: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find bag + equipped instances matching ref."""
    ensure_item_instances(player, reg)  # type: ignore
    parsed = parse_instance_ref(raw)
    code = parsed["code_or_id"] or ""
    from game.domain.item_codes import item_code, resolve_code

    tid = resolve_code(code, reg) or code
    hits: List[Dict[str, Any]] = []

    def _match(inst: Mapping[str, Any]) -> bool:
        loc = str(inst.get("location") or "")
        if location == "bag" and loc != "bag":
            return False
        if location and location.startswith("equip") and not loc.startswith("equip"):
            return False
        if parsed["inst_id"] and str(inst.get("inst_id")) != parsed["inst_id"]:
            return False
        if parsed["owner_short"] and str(inst.get("owner_short")) != parsed["owner_short"]:
            return False
        itid = str(inst.get("template_id") or "")
        icode = str(inst.get("code") or item_code(itid, reg))
        if itid == tid or icode == code or itid == code or icode == tid:
            return True
        return False

    for inst in player.get("inventory_items") or []:
        if _match(inst):
            hits.append(dict(inst))
    for slot, inst in (player.get("equip_instances") or {}).items():
        if inst and _match(inst):
            d = dict(inst)
            d["_slot"] = slot
            hits.append(d)
    return hits


def get_equipped_instance(
    player: Mapping[str, Any],
    slot: str,
) -> Optional[Dict[str, Any]]:
    from game.domain.equipment import normalize_slot

    eq = player.get("equip_instances") or {}
    ns = normalize_slot(slot)
    inst = eq.get(ns)
    if not inst and slot in eq:
        inst = eq.get(slot)
    return dict(inst) if inst else None


def format_equipped_ref_line(
    player: Mapping[str, Any],
    reg: DataRegistry,
    slot: str,
) -> str:
    """Display line for hub: sw001_a3f2#… ดาบเหล็ก [○] ธรรมดา +1"""
    from game.domain.item_codes import format_equipped_piece, rarity_observe_tag
    from game.domain.rarity import equip_rarity_for_slot

    ensure_item_instances(player, reg)  # type: ignore
    inst = get_equipped_instance(player, slot)
    tid = (player.get("equip_ids") or {}).get(slot)
    if not tid:
        return "—"
    if not inst:
        rid = equip_rarity_for_slot(player, slot)
        up = int((player.get("upgrade_levels") or {}).get(slot, 0))
        return format_equipped_piece(str(tid), reg, rid, upgrade=up)
    name = (reg.items.get(str(inst.get("template_id"))) or {}).get("name") or inst.get(
        "template_id"
    )
    rid = str(inst.get("rarity") or "common")
    up = int(inst.get("upgrade") or 0)
    ref = format_instance_ref(inst)
    obs = rarity_observe_tag(reg, rid)
    up_s = f" +{up}" if up else ""
    return f"{ref} {name} {obs}{up_s}"
