"""Crafting recipes from data — optional min rarity inputs / output rarity."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry
from game.domain.equipment import add_item, count_materials, remove_inventory_id


def list_recipes(reg: DataRegistry, player: Mapping[str, Any]) -> List[Dict[str, Any]]:
    lv = int(player.get("level", 1))
    out = []
    for rid, r in (reg.recipes or {}).items():
        if int(r.get("unlock_level", 1)) <= lv:
            out.append({**r, "id": rid})
    return out


def _input_min_rarity(recipe: Mapping[str, Any], item_id: str) -> Optional[str]:
    """
    inputs_rarity:
      iron_sword: uncommon
      upgrade_mat: common
    or single output_requires_input_rarity applied to all equipment inputs
    """
    table = recipe.get("inputs_rarity") or {}
    if item_id in table:
        return str(table[item_id])
    if recipe.get("require_input_rarity"):
        return str(recipe["require_input_rarity"])
    return None


def can_craft(player: Mapping[str, Any], recipe: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> bool:
    if int(player.get("money_world", 0)) < int(recipe.get("money", 0)):
        return False
    for iid, n in (recipe.get("inputs") or {}).items():
        min_r = _input_min_rarity(recipe, str(iid))
        if min_r and reg is not None:
            from game.domain.rarity import count_materials_min_rarity

            if count_materials_min_rarity(player, str(iid), min_r, reg) < int(n):
                return False
        elif count_materials(player, str(iid)) < int(n):
            return False
    return True


def craft(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    recipe_id: str,
) -> str:
    from game.domain.rarity import (
        display_item_name,
        item_default_rarity,
        remove_materials_min_rarity,
        tier_by_id,
    )

    recipe = (reg.recipes or {}).get(recipe_id)
    if not recipe:
        return "ไม่พบสูตร"
    if int(player.get("level", 1)) < int(recipe.get("unlock_level", 1)):
        return "เลเวลไม่พอ"
    if not can_craft(player, recipe, reg):
        # soft message about rarity
        for iid, n in (recipe.get("inputs") or {}).items():
            min_r = _input_min_rarity(recipe, str(iid))
            if min_r:
                need_name = tier_by_id(reg, min_r).get("name") or min_r
                have = count_materials(player, str(iid))
                from game.domain.rarity import count_materials_min_rarity

                ok_n = count_materials_min_rarity(player, str(iid), min_r, reg)
                if ok_n < int(n):
                    iname = (reg.items.get(str(iid)) or {}).get("name") or iid
                    return (
                        f"วัตถุดิบระดับไม่พอ: ต้องการ {iname} "
                        f"ระดับ≥{need_name} x{n} (ที่มีคุณภาพพอ {ok_n}/{have})"
                    )
        return "วัตถุดิบหรือเงินไม่พอ"
    money = int(recipe.get("money", 0))
    player["money_world"] = int(player.get("money_world", 0)) - money
    for iid, n in (recipe.get("inputs") or {}).items():
        min_r = _input_min_rarity(recipe, str(iid))
        if min_r:
            if not remove_materials_min_rarity(player, str(iid), int(n), min_r, reg):
                return f"วัตถุดิบระดับไม่พอ: {iid}"
        else:
            for _ in range(int(n)):
                if not remove_inventory_id(player, str(iid), reg):
                    bag = list(player.get("card_bag") or [])
                    if str(iid) in bag:
                        bag.remove(str(iid))
                        player["card_bag"] = bag
                    else:
                        return f"วัตถุดิบไม่พอ: {iid}"
    out_id = str(recipe.get("output"))
    # output rarity: explicit or inherit max input requirement or default
    out_r = recipe.get("output_rarity")
    if not out_r:
        # bump one tier above highest required input if any
        ranks = []
        for iid in (recipe.get("inputs") or {}):
            mr = _input_min_rarity(recipe, str(iid))
            if mr:
                ranks.append(int(tier_by_id(reg, mr).get("rank") or 1))
        if ranks:
            want = max(ranks)
            # pick tier id by rank
            for t in (getattr(reg, "rarity", None) or {}).get("tiers") or []:
                if int(t.get("rank") or 0) == min(8, want + int(recipe.get("output_rarity_bonus") or 0)):
                    out_r = t.get("id")
                    break
        if not out_r:
            out_r = item_default_rarity(reg.items.get(out_id) or {}, reg)
    name = add_item(player, out_id, reg, rarity=str(out_r))
    nice = display_item_name(
        str((reg.items.get(out_id) or {}).get("name") or out_id),
        str(out_r),
        reg,
    )
    return f"คราฟสำเร็จ: {recipe.get('name')} → {nice}"
