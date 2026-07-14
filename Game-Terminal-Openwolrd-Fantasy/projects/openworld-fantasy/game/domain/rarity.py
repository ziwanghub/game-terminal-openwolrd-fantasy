"""
Rarity / grade system — common → mythic (ธรรมดา…ปฐมกาล).
Applies stat mult to equipment and party companions.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple  # noqa: F401

from game.data_load.registry import DataRegistry


def _cfg(reg: Optional[DataRegistry]) -> Dict[str, Any]:
    if reg is None:
        return {}
    return dict(getattr(reg, "rarity", None) or {})


def all_tiers(reg: Optional[DataRegistry]) -> List[Dict[str, Any]]:
    tiers = list(_cfg(reg).get("tiers") or [])
    if not tiers:
        return [
            {
                "id": "common",
                "name": "ธรรมดา",
                "rank": 1,
                "color_tag": "○",
                "stat_mult": 1.0,
                "price_mult": 1.0,
                "drop_weight": 1,
                "recruit_weight": 1,
            }
        ]
    return sorted(tiers, key=lambda t: int(t.get("rank") or 0))


def tier_by_id(reg: Optional[DataRegistry], rarity_id: str) -> Dict[str, Any]:
    rid = str(rarity_id or _cfg(reg).get("default") or "common")
    for t in all_tiers(reg):
        if str(t.get("id")) == rid:
            return dict(t)
    # fallback first
    tiers = all_tiers(reg)
    return dict(tiers[0]) if tiers else {"id": "common", "name": "ธรรมดา", "stat_mult": 1.0}


def rarity_label(reg: Optional[DataRegistry], rarity_id: str) -> str:
    t = tier_by_id(reg, rarity_id)
    tag = t.get("color_tag") or ""
    name = t.get("name") or rarity_id
    return f"{tag}{name}".strip()


def rarity_stat_mult(reg: Optional[DataRegistry], rarity_id: str) -> float:
    return float(tier_by_id(reg, rarity_id).get("stat_mult") or 1.0)


def rarity_price_mult(reg: Optional[DataRegistry], rarity_id: str) -> float:
    return float(tier_by_id(reg, rarity_id).get("price_mult") or 1.0)


def scale_stat(base: int, rarity_id: str, reg: Optional[DataRegistry], *, floor: int = 0) -> int:
    if not base:
        return 0
    m = rarity_stat_mult(reg, rarity_id)
    return max(floor, int(round(float(base) * m)))


def item_default_rarity(item: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> str:
    if item.get("rarity"):
        return str(item["rarity"])
    kind = str(item.get("kind") or "item")
    defaults = (_cfg(reg).get("item_kind_default") or {}) if reg else {}
    return str(defaults.get(kind) or _cfg(reg).get("default") or "common")


def roll_rarity(
    reg: DataRegistry,
    rng: random.Random,
    *,
    kind: Optional[str] = None,
    pool: str = "drop",
    min_rank: int = 1,
    max_rank: int = 99,
) -> str:
    """
    Weighted roll. pool: drop | recruit
    kind: companion kind for bias (optional)
    """
    tiers = all_tiers(reg)
    weight_key = "drop_weight" if pool == "drop" else "recruit_weight"
    bias = {}
    if kind:
        bias = dict((_cfg(reg).get("kind_rarity_bias") or {}).get(kind) or {})

    weights = []
    ids = []
    for t in tiers:
        rank = int(t.get("rank") or 1)
        if rank < min_rank or rank > max_rank:
            continue
        tid = str(t.get("id"))
        w = float(t.get(weight_key) or t.get("drop_weight") or 1)
        w *= float(bias.get(tid) or 1.0)
        if w <= 0:
            continue
        ids.append(tid)
        weights.append(w)
    if not ids:
        return str(_cfg(reg).get("default") or "common")
    total = sum(weights)
    r = rng.random() * total
    acc = 0.0
    for tid, w in zip(ids, weights):
        acc += w
        if r <= acc:
            return tid
    return ids[-1]


def ensure_inventory_rarity(player: MutableMapping[str, Any]) -> None:
    """Keep inventory_rarities parallel to inventory_ids."""
    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    while len(rares) < len(ids):
        rares.append("common")
    if len(rares) > len(ids):
        rares = rares[: len(ids)]
    player["inventory_rarities"] = rares
    from game.domain.equipment import EQUIP_SLOTS, migrate_equip_loadout

    player.setdefault("equip_rarities", {})
    try:
        migrate_equip_loadout(player)
    except Exception:
        er = dict(player.get("equip_rarities") or {})
        for s in EQUIP_SLOTS:
            er.setdefault(s, None)
        player["equip_rarities"] = er


def append_item_rarity(
    player: MutableMapping[str, Any],
    rarity_id: str,
) -> None:
    """Call AFTER inventory_ids already gained one entry — sets last slot rarity."""
    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    # pad only up to len(ids)-1 then set last
    while len(rares) < max(0, len(ids) - 1):
        rares.append("common")
    rid = str(rarity_id or "common")
    if len(rares) < len(ids):
        rares.append(rid)
    else:
        # overwrite last if already padded by ensure
        if rares:
            rares[-1] = rid
        else:
            rares.append(rid)
    # trim excess
    if len(rares) > len(ids):
        rares = rares[: len(ids)]
    player["inventory_rarities"] = rares
    player.setdefault("equip_rarities", {})


def pop_item_rarity_at(player: MutableMapping[str, Any], index: int) -> str:
    ensure_inventory_rarity(player)
    rares = list(player.get("inventory_rarities") or [])
    if 0 <= index < len(rares):
        r = rares.pop(index)
        player["inventory_rarities"] = rares
        return str(r)
    return "common"


def rarity_of_inventory_index(player: Mapping[str, Any], index: int) -> str:
    rares = list(player.get("inventory_rarities") or [])
    if 0 <= index < len(rares):
        return str(rares[index] or "common")
    return "common"


def find_inventory_index(player: Mapping[str, Any], item_id: str) -> int:
    ids = list(player.get("inventory_ids") or [])
    try:
        return ids.index(item_id)
    except ValueError:
        return -1


def equip_rarity_for_slot(player: Mapping[str, Any], slot: str) -> str:
    from game.domain.equipment import normalize_slot

    er = player.get("equip_rarities") or {}
    ns = normalize_slot(slot)
    r = er.get(ns)
    if r in (None, "", "None"):
        # legacy key fallback
        r = er.get(slot)
    return str(r or "common")


def _latent_rank_scale(reg: DataRegistry, rarity_id: str) -> float:
    """Higher rarity → stronger hidden latent (player must observe)."""
    rk = int(tier_rank(reg, rarity_id) or 1)
    return 0.65 + min(1.8, rk * 0.18)


def scaled_item_stats(
    item: Mapping[str, Any],
    rarity_id: str,
    reg: DataRegistry,
    *,
    upgrade_level: int = 0,
    slot: str = "weapon",
) -> Dict[str, Any]:
    """
    Visible primary: atk (weapons) · def/mdef (armor/shield) · max_mana if any.
    Latent (hidden): hp%/tough/status_resist/crit/atk_pct — scale with rarity rank.
    """
    from game.domain.equipment import normalize_slot

    ns = normalize_slot(slot)
    atk = scale_stat(int(item.get("atk") or 0), rarity_id, reg)
    max_hp = scale_stat(int(item.get("max_hp") or 0), rarity_id, reg)
    max_mana = scale_stat(int(item.get("max_mana") or 0), rarity_id, reg)
    defense = scale_stat(int(item.get("def") or item.get("defense") or 0), rarity_id, reg)
    mdef = scale_stat(int(item.get("mdef") or 0), rarity_id, reg)
    latent_max_hp = scale_stat(int(item.get("latent_max_hp") or 0), rarity_id, reg)
    lat_scale = _latent_rank_scale(reg, rarity_id)
    latent_hp_pct = float(item.get("latent_hp_pct") or 0.0) * lat_scale
    # weapon latents (hidden offense)
    latent_atk_pct = float(item.get("latent_atk_pct") or 0.0) * lat_scale
    latent_crit = float(item.get("latent_crit") or 0.0) * lat_scale
    # armor latents (hidden toughness)
    latent_tough = float(item.get("latent_tough") or 0.0) * lat_scale  # extra power_def soft
    latent_status_resist = float(item.get("latent_status_resist") or 0.0) * lat_scale

    # defaults by kind if YAML omits latent (so every piece differs a bit)
    grip = str(item.get("grip") or "")
    armor_like = ns in ("body", "head", "legs", "feet", "armor")
    shield_like = ns == "off_hand" and (grip == "shield" or defense > 0)
    weapon_like = ns in ("main_hand", "weapon") or (
        ns == "off_hand" and grip in ("one_hand", "two_hand", "focus") and atk > 0
    )
    if armor_like or shield_like:
        if latent_hp_pct <= 0 and not item.get("latent_hp_pct"):
            # mild default latent bulk — varies by weight
            wc = str(item.get("weight_class") or "light")
            base_l = {"heavy": 0.045, "medium": 0.032, "light": 0.022}.get(wc, 0.028)
            if ns == "body":
                base_l *= 1.15
            elif ns == "feet":
                base_l *= 0.7
            latent_hp_pct = base_l * lat_scale
        if latent_tough <= 0 and not item.get("latent_tough"):
            latent_tough = (0.35 + defense * 0.04) * lat_scale * 0.15
        if latent_status_resist <= 0 and not item.get("latent_status_resist"):
            latent_status_resist = (0.008 if shield_like else 0.005) * lat_scale
    if weapon_like and atk > 0:
        if latent_atk_pct <= 0 and not item.get("latent_atk_pct"):
            # higher rank weapons feel sharper — still hidden
            latent_atk_pct = 0.012 * lat_scale
        if latent_crit <= 0 and not item.get("latent_crit"):
            latent_crit = 0.4 * lat_scale  # flat soft crit points

    up = max(0, int(upgrade_level))
    um = rarity_stat_mult(reg, rarity_id)
    atk += int(round(up * 2 * um))
    if armor_like or shield_like:
        defense += int(round(up * 2.2 * um))
        mdef += int(round(up * 1.2 * um))
        latent_hp_pct += 0.004 * up * lat_scale
        latent_tough += 0.08 * up
        latent_status_resist += 0.002 * up
        if max_hp > 0:
            max_hp += int(round(up * 1 * um))
    else:
        # weapon upgrades: primary ATK + hidden offense latents
        latent_atk_pct += 0.006 * up * lat_scale
        latent_crit += 0.15 * up * lat_scale
        if max_hp > 0:
            max_hp += int(round(up * 1 * um))
    if ns in ("main_hand", "off_hand", "weapon", "acc_1", "accessory"):
        max_mana += int(round(up * 1 * um))
    return {
        "atk": atk,
        "max_hp": max_hp,
        "max_mana": max_mana,
        "def": defense,
        "mdef": mdef,
        "latent_max_hp": latent_max_hp,
        "latent_hp_pct": float(latent_hp_pct),
        "latent_atk_pct": float(latent_atk_pct),
        "latent_crit": float(latent_crit),
        "latent_tough": float(latent_tough),
        "latent_status_resist": float(latent_status_resist),
    }


def format_rarity_tag(reg: Optional[DataRegistry], rarity_id: str) -> str:
    t = tier_by_id(reg, rarity_id)
    return f"[{t.get('color_tag', '')}{t.get('name', rarity_id)}]"


def display_item_name(
    base_name: str,
    rarity_id: str,
    reg: Optional[DataRegistry] = None,
    *,
    with_tag: bool = True,
) -> str:
    """
    Name changes with rarity — e.g. 「ดาบเหล็ก · ตำนาน」 or prefix tag.
    """
    t = tier_by_id(reg, rarity_id)
    rname = str(t.get("name") or rarity_id)
    tag = format_rarity_tag(reg, rarity_id) if with_tag else rname
    # common: just name + light tag
    if str(t.get("id")) == "common":
        return f"{base_name} {tag}" if with_tag else str(base_name)
    # higher: rename style
    return f"{base_name} · {rname} {tag}" if with_tag else f"{base_name} · {rname}"


def display_entity_name(
    base_name: str,
    rarity_id: str,
    reg: Optional[DataRegistry] = None,
) -> str:
    """Monster / companion style name with grade."""
    t = tier_by_id(reg, rarity_id)
    if str(t.get("id")) in ("common", "", "None"):
        return str(base_name)
    return f"{t.get('color_tag', '')}{base_name} ({t.get('name')})"


def enemy_threat_mult(reg: Optional[DataRegistry], rarity_id: str) -> float:
    cfg = _cfg(reg)
    table = cfg.get("enemy_threat_mult") or {}
    if rarity_id in table:
        return float(table[rarity_id])
    # fallback: use stat_mult slightly dampened
    return 1.0 + (rarity_stat_mult(reg, rarity_id) - 1.0) * 0.7


def enemy_xp_mult(reg: Optional[DataRegistry], rarity_id: str) -> float:
    cfg = _cfg(reg)
    table = cfg.get("enemy_xp_mult") or {}
    if rarity_id in table:
        return float(table[rarity_id])
    return rarity_stat_mult(reg, rarity_id)


def apply_rarity_to_enemy(
    mon: MutableMapping[str, Any],
    reg: DataRegistry,
    rarity_id: str,
) -> Dict[str, Any]:
    """Scale HP/ATK/profiles/XP and rename for display."""
    mon = dict(mon)
    rid = str(rarity_id or "common")
    thr = enemy_threat_mult(reg, rid)
    xp_m = enemy_xp_mult(reg, rid)
    base_name = str(mon.get("base_name") or mon.get("name") or mon.get("id") or "?")
    mon["base_name"] = base_name
    mon["rarity"] = rid
    mon["name"] = display_entity_name(base_name, rid, reg)
    mon["hp"] = max(1, int(round(int(mon.get("hp") or 1) * thr)))
    mon["max_hp"] = max(1, int(round(int(mon.get("max_hp") or mon["hp"]) * thr)))
    mon["atk"] = max(1, int(round(int(mon.get("atk") or 1) * thr)))
    mon["xp_mult"] = float(mon.get("xp_mult") or 1.0) * xp_m
    profiles = []
    for p in mon.get("attack_profiles") or []:
        p = dict(p)
        if "power" in p:
            p["power"] = max(1, int(round(int(p["power"]) * thr)))
        profiles.append(p)
    if profiles:
        mon["attack_profiles"] = profiles
    return mon


def roll_enemy_rarity(
    reg: DataRegistry,
    rng: random.Random,
    *,
    boss: bool = False,
    area_tier: int = 1,
) -> str:
    """Bosses skew higher; area_tier soft-raises min rank."""
    if boss:
        return roll_rarity(
            reg,
            rng,
            pool="drop",
            min_rank=max(3, min(5, 2 + area_tier // 2)),
            max_rank=8,
        )
    min_r = 1 + max(0, min(2, area_tier // 3))
    max_r = 4 + max(0, min(3, area_tier // 2))
    return roll_rarity(reg, rng, pool="drop", min_rank=min_r, max_rank=max_r)


def tier_rank(reg: Optional[DataRegistry], rarity_id: str) -> int:
    return int(tier_by_id(reg, rarity_id).get("rank") or 1)


def count_materials_min_rarity(
    player: Mapping[str, Any],
    item_id: str,
    min_rarity: str,
    reg: DataRegistry,
) -> int:
    """Count inventory pieces of item_id with rarity rank >= min_rarity."""
    need = tier_rank(reg, min_rarity)
    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    n = 0
    for i, iid in enumerate(ids):
        if str(iid) != str(item_id):
            continue
        rid = rares[i] if i < len(rares) else "common"
        if tier_rank(reg, str(rid)) >= need:
            n += 1
    return n


def remove_inventory_at_index(
    player: MutableMapping[str, Any],
    index: int,
    reg: DataRegistry,
) -> Optional[Tuple[str, str]]:
    """Remove inventory slot by index. Returns (item_id, rarity) or None."""
    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    if index < 0 or index >= len(ids):
        return None
    iid = ids.pop(index)
    rid = rares.pop(index) if index < len(rares) else "common"
    # if rares shorter, trim
    while len(rares) > len(ids):
        rares.pop()
    player["inventory_ids"] = ids
    player["inventory_rarities"] = rares
    name = (reg.items.get(iid) or {}).get("name", iid)
    inv = list(player.get("inventory") or [])
    for j, line in enumerate(inv):
        if str(line).startswith(str(name)):
            inv.pop(j)
            break
    player["inventory"] = inv
    return str(iid), str(rid)


def remove_materials_min_rarity(
    player: MutableMapping[str, Any],
    item_id: str,
    count: int,
    min_rarity: str,
    reg: DataRegistry,
) -> bool:
    """Remove `count` matching items of sufficient rarity (highest first optional)."""
    from game.domain.equipment import remove_inventory_id

    need = tier_rank(reg, min_rarity)
    left = int(count)
    # collect indices matching, prefer lowest sufficient rarity first (save better mats)
    while left > 0:
        ids = list(player.get("inventory_ids") or [])
        rares = list(player.get("inventory_rarities") or [])
        best_i = -1
        best_rank = 999
        for i, iid in enumerate(ids):
            if str(iid) != str(item_id):
                continue
            rid = str(rares[i] if i < len(rares) else "common")
            rk = tier_rank(reg, rid)
            if rk >= need and rk < best_rank:
                best_rank = rk
                best_i = i
        if best_i < 0:
            return False
        # remove by rotating to use remove_inventory_id on that exact instance:
        # temporarily put chosen id at first occurrence of sufficient rarity
        target_id = ids[best_i]
        # swap chosen to a removable position: remove by rebuilding
        new_ids = ids[:best_i] + ids[best_i + 1 :]
        new_rares = rares[:best_i] + rares[best_i + 1 :] if best_i < len(rares) else rares
        player["inventory_ids"] = new_ids
        player["inventory_rarities"] = new_rares
        # sync display inventory names
        name = (reg.items.get(target_id) or {}).get("name", target_id)
        inv = list(player.get("inventory") or [])
        for j, line in enumerate(inv):
            if str(line).startswith(str(name)):
                inv.pop(j)
                break
        player["inventory"] = inv
        left -= 1
    return True
