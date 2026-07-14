"""Consumable use — potions, cleanse, buff items (field + combat)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from game.data_load.registry import DataRegistry, get_registry
from game.domain.narrative import status_display_name
from game.ports.io import IO


def _combat_quick_cleanse(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
) -> bool:
    """Spend panacea or antidote from bag for a quick debuff cleanse in combat."""
    from game.domain.status_fx import cleanse, clear_statuses, status_display_name

    ids = list(player.get("inventory_ids") or [])
    inv = list(player.get("inventory") or [])
    rar = list(player.get("inventory_rarities") or [])
    pick_id = None
    pick_i = -1
    for prefer in ("panacea", "antidote"):
        if prefer in ids:
            pick_id = prefer
            pick_i = ids.index(prefer)
            break
    if pick_i < 0:
        # name fallback
        for i, name in enumerate(inv):
            n = str(name)
            if "ถอน" in n or "แก้พิษ" in n or "แก้" in n:
                pick_i = i
                pick_id = ids[i] if i < len(ids) else ""
                break
    if pick_i < 0:
        io.write_line("ไม่มียาแก้พิษหรือยาถอนสถานะในคลัง")
        return False
    # consume
    if pick_i < len(inv):
        inv.pop(pick_i)
    if pick_i < len(ids):
        ids.pop(pick_i)
    if pick_i < len(rar):
        rar.pop(pick_i)
    player["inventory"] = inv
    player["inventory_ids"] = ids
    player["inventory_rarities"] = rar
    it = reg.items.get(str(pick_id)) or {}
    if it.get("clear_all_debuffs") or pick_id == "panacea" or "ถอน" in str(
        it.get("name") or ""
    ):
        cleared = cleanse(player, reg, mode="all_debuffs", item_id=str(pick_id or "panacea"))
    else:
        cleared = clear_statuses(
            player,
            reg,
            item_id=str(pick_id or "antidote"),
            clear_spec=it.get("clear_status") or "poison",
            tags=["poison", "ailment"],
        )
    if cleared:
        io.write_line(
            "ล้างเร็ว: "
            + ", ".join(status_display_name(reg, c) for c in cleared)
        )
    else:
        io.write_line("ใช้ยาล้างแล้ว (ไม่มี debuff ที่ล้างได้)")
    return True


def _is_consumable_entry(
    reg: DataRegistry, item_id: str, label: str
) -> bool:
    it = (reg.items.get(item_id) or {}) if item_id else {}
    if it.get("kind") == "consumable":
        return True
    if any(it.get(k) for k in ("heal_hp", "heal_mana", "clear_status", "clear_all_debuffs", "apply_status")):
        return True
    # name fallback only when id unknown
    if not item_id or item_id not in reg.items:
        lab = str(label)
        keys = ("ยา", "HP", "Mana", "มานา", "เครื่องราง", "สัญญา", "ถอน", "ขี้ผึ้ง", "ชา", "น้ำมัน")
        return any(k in lab for k in keys)
    return False


def _use_potion(
    player: Dict[str, Any],
    io: IO,
    reg: Optional[DataRegistry] = None,
) -> bool:
    from game.domain.status_fx import cleanse, clear_statuses, status_display_name

    reg = reg or get_registry()
    inv = list(player.get("inventory") or [])
    ids = list(player.get("inventory_ids") or [])
    rar = list(player.get("inventory_rarities") or [])
    # pad parallel lists to inventory length (ids are source of truth when present)
    while len(ids) < len(inv):
        ids.append("")
    while len(rar) < len(inv):
        rar.append("common")
    usable_idx: List[int] = []
    for i, name in enumerate(inv):
        iid = str(ids[i] or "")
        if _is_consumable_entry(reg, iid, str(name)):
            usable_idx.append(i)
    if not usable_idx:
        io.write_line("ไม่มีของใช้ได้")
        return False
    for n, bi in enumerate(usable_idx, 1):
        iid = str(ids[bi] or "")
        disp = (reg.items.get(iid) or {}).get("name") or inv[bi]
        tag = f" [{iid}]" if iid and iid in reg.items else ""
        io.write_line(f"  {n}. {disp}{tag}")
    try:
        pi = int(io.read_line("ใช้: ").strip()) - 1
        bi = usable_idx[max(0, min(len(usable_idx) - 1, pi))]
    except Exception:
        return False
    item_name = str(inv.pop(bi))
    item_id = str(ids.pop(bi) or "")
    if bi < len(rar):
        rar.pop(bi)
    while len(ids) > len(inv):
        ids.pop()
    while len(rar) > len(inv):
        rar.pop()
    player["inventory"] = inv
    player["inventory_ids"] = ids
    player["inventory_rarities"] = rar

    it = dict(reg.items.get(item_id) or {})
    # resolve by display name if id missing/unknown
    if not it:
        for iid, defn in reg.items.items():
            if str(defn.get("name")) == item_name:
                item_id = iid
                it = dict(defn)
                break

    def _report_cleared(cleared: List[str], prefix: str) -> None:
        if cleared:
            names = ", ".join(status_display_name(reg, c) for c in cleared)
            io.write_line(f"{prefix}ล้าง: {names}")
        else:
            io.write_line(f"{prefix}(ไม่มีสถานะที่ล้างได้)")

    if it.get("clear_all_debuffs") or str(it.get("clear_status") or "").lower() in (
        "all",
        "*",
        "debuff",
    ):
        cleared = cleanse(player, reg, mode="all_debuffs", item_id=item_id or "panacea")
        _report_cleared(cleared, "ยาถอนสถานะ — ")
        return True
    if it.get("clear_status") and not it.get("heal_hp") and not it.get("heal_mana") and not it.get(
        "apply_status"
    ):
        cleared = clear_statuses(
            player,
            reg,
            item_id=item_id or "antidote",
            clear_spec=it.get("clear_status"),
            tags=["poison", "ailment"],
        )
        _report_cleared(cleared, "ยาแก้ — ")
        return True
    if it.get("apply_status"):
        from game.domain.status_fx import apply_status, status_display_name as sname

        sid = str(it.get("apply_status"))
        applied = apply_status(
            player, sid, reg, random.Random(), chance=1.0, source=item_id or "item", ignore_resist=True
        )
        if applied:
            io.write_line(f"ได้บัฟ/สถานะ: {sname(reg, applied)}")
        else:
            io.write_line("ใช้แล้ว แต่ผลไม่ติด")
        # small heal if also heal_hp
        if it.get("heal_hp"):
            h = int(it["heal_hp"])
            player["hp"] = min(int(player["max_hp"]), int(player["hp"]) + h)
            io.write_line(f"ฟื้น HP +{h}")
        return True

    if "สัญญา" in item_name or "นรก" in item_name or item_id == "hell_contract":
        player["bonus_atk"] = int(player.get("bonus_atk", 0)) + 5
        player["base_atk"] = int(player.get("base_atk", 0)) + 5
        player["blessings"] = list(player.get("blessings") or []) + ["สัญญานรก"]
        player["blessing_turns"] = max(int(player.get("blessing_turns", 0)), 8)
        io.write_line("สัญญานรก! ATK+5 ชั่วคราว (~8 เทิร์น) — มีราคา...")
    elif "เครื่องราง" in item_name or "สวรรค์" in item_name or item_id == "blessed_charm":
        player["hp"] = min(int(player["max_hp"]), int(player["hp"]) + 80)
        player["mana"] = min(int(player["max_mana"]), int(player["mana"]) + 40)
        cleared = clear_statuses(player, reg, item_id="blessed_charm", tags=["ailment"])
        extra = ""
        if cleared:
            extra = " · ล้าง " + ", ".join(status_display_name(reg, c) for c in cleared)
        io.write_line(f"เครื่องรางสวรรค์: ฟื้น HP/MP มาก{extra}")
    elif it.get("heal_mana") or "Mana" in item_name or "มานา" in item_name:
        heal = int(it.get("heal_mana") or 35)
        player["mana"] = min(int(player["max_mana"]), int(player["mana"]) + heal)
        io.write_line(f"ฟื้น MP +{heal}")
    elif "พิษ" in item_name or "แก้" in item_name or item_id == "antidote":
        cleared = clear_statuses(
            player, reg, item_id="antidote", clear_spec="poison", tags=["poison", "ailment"]
        )
        _report_cleared(cleared, "")
    else:
        heal = int(it.get("heal_hp") or 40)
        player["hp"] = min(int(player["max_hp"]), int(player["hp"]) + heal)
        # potion may also clear lightly if flagged
        if it.get("clear_status"):
            clear_statuses(player, reg, clear_spec=it.get("clear_status"))
        io.write_line(f"ฟื้น HP +{heal}")
    return True


