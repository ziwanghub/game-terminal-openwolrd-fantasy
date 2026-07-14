"""
Crafting recipes — min rarity inputs, output rarity,
K1 success/fail · K2 quality · K3 station↔area · K4 food/heal recipes.

Soft / anti-spoiler: never show raw % — only labels (สูง / ปานกลาง / เสี่ยง).
"""
from __future__ import annotations

import hashlib
import random
import time
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry
from game.domain.equipment import add_item, count_materials, remove_inventory_id


def _station_cfg(reg: DataRegistry) -> Dict[str, Any]:
    return dict((_craft_rules(reg).get("stations") or {}))


def station_label(station_id: str, reg: Optional[DataRegistry] = None) -> str:
    """Soft Thai label for a station id."""
    labels: Dict[str, str] = {
        "forge": "หลอม / ตี",
        "camp": "ค่าย / ต้มยา",
        "mystic": "จารึก / เงา",
    }
    if reg is not None:
        cfg = _station_cfg(reg)
        labels.update(dict(cfg.get("labels") or {}))
    return str(labels.get(str(station_id), station_id))


def stations_at_location(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    location: Optional[str] = None,
) -> List[str]:
    """
    K3: which craft stations exist at the player's current area.
    Area YAML ``stations:`` wins; else rules.stations.default (camp).
    """
    loc = str(location if location is not None else player.get("location") or "")
    area = (reg.areas or {}).get(loc) or {}
    raw = area.get("stations")
    if raw:
        return [str(s) for s in raw if s]
    cfg = _station_cfg(reg)
    default = list(cfg.get("default") or ["camp"])
    return [str(s) for s in default if s]


def format_stations_line(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> str:
    """One soft line: area name + station labels."""
    loc = str(player.get("location") or "")
    area = (reg.areas or {}).get(loc) or {}
    area_nm = str(area.get("name") or loc or "ไม่ทราบที่")
    st = stations_at_location(player, reg)
    if not st:
        return f"ที่: {area_nm} · สถานี: (ไม่มี)"
    bits = [station_label(s, reg) for s in st]
    return f"ที่: {area_nm} · สถานี: {', '.join(bits)}"


def station_ok_for_recipe(
    player: Mapping[str, Any],
    recipe: Mapping[str, Any],
    reg: DataRegistry,
) -> bool:
    """True if recipe has no station or location has that station."""
    need = str(recipe.get("station") or "").strip()
    if not need:
        return True
    return need in stations_at_location(player, reg)


def list_recipes(
    reg: DataRegistry,
    player: Mapping[str, Any],
    *,
    require_station: bool = True,
) -> List[Dict[str, Any]]:
    """
    Recipes unlocked by level.
    K3: by default only recipes whose station is available here.
    Pass require_station=False to list all known (level-gated) formulas.
    """
    lv = int(player.get("level", 1))
    available = set(stations_at_location(player, reg)) if require_station else None
    out = []
    for rid, r in (reg.recipes or {}).items():
        if int(r.get("unlock_level", 1)) > lv:
            continue
        if available is not None:
            st = str(r.get("station") or "").strip()
            if st and st not in available:
                continue
        out.append({**r, "id": rid})
    return out


def count_recipes_elsewhere(
    reg: DataRegistry,
    player: Mapping[str, Any],
) -> int:
    """How many level-unlocked recipes need a different station (soft hint)."""
    here = list_recipes(reg, player, require_station=True)
    all_known = list_recipes(reg, player, require_station=False)
    return max(0, len(all_known) - len(here))


def craft_elsewhere_hint(reg: DataRegistry) -> str:
    """Soft travel hint for recipes locked to other stations."""
    return str((_station_cfg(reg).get("elsewhere_hint") or "")).strip()


def _rng_choice(rng: random.Random, seq: Sequence[Any], default: Any = None) -> Any:
    if not seq:
        return default
    try:
        return rng.choice(list(seq))
    except Exception:
        return list(seq)[0]


def _rng_shuffle(rng: random.Random, items: List[Any]) -> None:
    try:
        rng.shuffle(items)
    except Exception:
        pass


def _craft_rules(reg: DataRegistry) -> Dict[str, Any]:
    return dict(getattr(reg, "craft_rules", None) or {})


def _input_min_rarity(recipe: Mapping[str, Any], item_id: str) -> Optional[str]:
    """
    inputs_rarity:
      iron_sword: uncommon
      upgrade_mat: common
    or require_input_rarity applied to all
    """
    table = recipe.get("inputs_rarity") or {}
    if item_id in table:
        return str(table[item_id])
    if recipe.get("require_input_rarity"):
        return str(recipe["require_input_rarity"])
    return None


def can_craft(
    player: Mapping[str, Any],
    recipe: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> bool:
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


def _resolve_output_rarity(recipe: Mapping[str, Any], reg: DataRegistry) -> str:
    from game.domain.rarity import item_default_rarity, tier_by_id

    out_id = str(recipe.get("output") or "")
    out_r = recipe.get("output_rarity")
    if out_r:
        return str(out_r)
    ranks = []
    for iid in recipe.get("inputs") or {}:
        mr = _input_min_rarity(recipe, str(iid))
        if mr:
            ranks.append(int(tier_by_id(reg, mr).get("rank") or 1))
    if ranks:
        want = max(ranks) + int(recipe.get("output_rarity_bonus") or 0)
        for t in (getattr(reg, "rarity", None) or {}).get("tiers") or []:
            if int(t.get("rank") or 0) == min(8, want):
                return str(t.get("id") or "common")
    return item_default_rarity(reg.items.get(out_id) or reg.cards.get(out_id) or {}, reg)


def _planned_consume_ranks(
    player: Mapping[str, Any],
    recipe: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Tuple[str, str, int]]:
    """
    Simulate which inventory slots would be consumed (lowest sufficient rarity first).
    Returns list of (item_id, rarity_id, surplus_tiers vs min).
    """
    from game.domain.rarity import tier_rank

    ids = list(player.get("inventory_ids") or [])
    rares = list(player.get("inventory_rarities") or [])
    # work on copies of indices still available
    available = list(range(len(ids)))
    planned: List[Tuple[str, str, int]] = []

    for iid, n in (recipe.get("inputs") or {}).items():
        iid = str(iid)
        min_r = _input_min_rarity(recipe, iid)
        need = tier_rank(reg, min_r) if min_r else 1
        left = int(n)
        while left > 0:
            best_i = -1
            best_rank = 999
            best_pos = -1
            for pos, i in enumerate(available):
                if str(ids[i]) != iid:
                    continue
                rid = str(rares[i] if i < len(rares) else "common")
                rk = tier_rank(reg, rid)
                if rk >= need and rk < best_rank:
                    best_rank = rk
                    best_i = i
                    best_pos = pos
            if best_i < 0:
                break
            surplus = max(0, best_rank - need)
            rid = str(rares[best_i] if best_i < len(rares) else "common")
            planned.append((iid, rid, surplus))
            available.pop(best_pos)
            left -= 1
    return planned


def material_quality_mult(
    player: Mapping[str, Any],
    recipe: Mapping[str, Any],
    reg: DataRegistry,
) -> float:
    """K2: average surplus tiers above min → bonus mult."""
    rules = _craft_rules(reg)
    qcfg = dict(rules.get("quality") or {})
    planned = _planned_consume_ranks(player, recipe, reg)
    if not planned:
        return 1.0
    avg_surplus = sum(s for _, _, s in planned) / max(1, len(planned))
    max_tiers = float(qcfg.get("max_bonus_tiers") or 2)
    per = float(qcfg.get("per_tier_bonus") or 0.08)
    used = min(max_tiers, avg_surplus)
    mult = 1.0 + used * per
    # all exact min → slight soft product
    if avg_surplus < 0.01:
        mult *= float(qcfg.get("at_min_soft") or 0.97)
    return mult


def _level_soft_mult(player: Mapping[str, Any], recipe: Mapping[str, Any], reg: DataRegistry) -> float:
    rules = _craft_rules(reg)
    lcfg = dict(rules.get("level_soft") or {})
    unlock = int(recipe.get("unlock_level") or 1)
    lv = int(player.get("level") or 1)
    over = max(0, lv - unlock)
    per = float(lcfg.get("per_level") or 0.012)
    cap = float(lcfg.get("max_bonus") or 0.08)
    return 1.0 + min(cap, over * per)


def _player_noise(player: Mapping[str, Any], salt: str, reg: DataRegistry) -> float:
    rules = _craft_rules(reg)
    ncfg = dict(rules.get("noise") or {})
    lo = float(ncfg.get("min") or 0.92)
    hi = float(ncfg.get("max") or 1.08)
    pid = str(player.get("id") or player.get("name") or "x")
    day = time.strftime("%Y-%m-%d")
    crafts = int((player.get("stats") or {}).get("crafts") or 0)
    h = hashlib.sha256(f"{pid}|{day}|{crafts}|{salt}".encode()).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return lo + n * (hi - lo)


def craft_success_chance(
    player: Mapping[str, Any],
    recipe: Mapping[str, Any],
    reg: DataRegistry,
) -> float:
    """Hidden P_success — never show raw value in UI."""
    rules = _craft_rules(reg)
    bases = dict(rules.get("base_success") or {})
    out_r = _resolve_output_rarity(recipe, reg)
    # recipe override
    sc = recipe.get("success") or {}
    if isinstance(sc, dict) and sc.get("base") is not None:
        base = float(sc["base"])
    else:
        base = float(bases.get(out_r) or bases.get("default") or 0.85)

    chance = base
    chance *= material_quality_mult(player, recipe, reg)
    chance *= _level_soft_mult(player, recipe, reg)
    # K3: slight mult when station matches (identity if already filtered)
    scfg = dict(rules.get("stations") or {})
    if station_ok_for_recipe(player, recipe, reg):
        chance *= float(scfg.get("match_mult") or 1.0)
    chance *= _player_noise(player, salt=str(recipe.get("id") or "craft"), reg=reg)

    lo = float(rules.get("chance_min") or 0.12)
    hi = float(rules.get("chance_max") or 0.97)
    return max(lo, min(hi, chance))


def craft_chance_label(chance: float, reg: Optional[DataRegistry] = None) -> str:
    """Soft label only — no percent."""
    rules = _craft_rules(reg) if reg is not None else {}
    labels = dict(rules.get("labels") or {})
    high = float(labels.get("high") or 0.80)
    mid = float(labels.get("mid") or 0.55)
    if chance >= high:
        return "โอกาสสูง"
    if chance >= mid:
        return "โอกาสปานกลาง"
    return "เสี่ยงสูง"


def recipe_chance_label(
    player: Mapping[str, Any],
    recipe: Mapping[str, Any],
    reg: DataRegistry,
) -> str:
    if not can_craft(player, recipe, reg):
        return "ยังไม่พร้อม"
    return craft_chance_label(craft_success_chance(player, recipe, reg), reg)


def _consume_inputs(
    player: MutableMapping[str, Any],
    recipe: Mapping[str, Any],
    reg: DataRegistry,
) -> Tuple[bool, List[Tuple[str, str]]]:
    """
    Consume inputs. Returns (ok, list of (item_id, rarity) consumed).
    """
    from game.domain.rarity import remove_materials_min_rarity, tier_rank

    consumed: List[Tuple[str, str]] = []
    # consume via existing helpers but track by snapshotting inventory delta
    before_ids = list(player.get("inventory_ids") or [])
    before_rar = list(player.get("inventory_rarities") or [])

    for iid, n in (recipe.get("inputs") or {}).items():
        min_r = _input_min_rarity(recipe, str(iid))
        if min_r:
            if not remove_materials_min_rarity(player, str(iid), int(n), min_r, reg):
                return False, consumed
        else:
            for _ in range(int(n)):
                if not remove_inventory_id(player, str(iid), reg):
                    bag = list(player.get("card_bag") or [])
                    if str(iid) in bag:
                        bag.remove(str(iid))
                        player["card_bag"] = bag
                        consumed.append((str(iid), "common"))
                    else:
                        return False, consumed

    # infer consumed by multiset diff (order-independent)
    after_ids = list(player.get("inventory_ids") or [])
    after_rar = list(player.get("inventory_rarities") or [])
    from collections import Counter

    def bag_key(ids, rares):
        c: Counter = Counter()
        for i, iid in enumerate(ids):
            rid = str(rares[i] if i < len(rares) else "common")
            c[(str(iid), rid)] += 1
        return c

    before_c = bag_key(before_ids, before_rar)
    after_c = bag_key(after_ids, after_rar)
    for key, cnt in before_c.items():
        lost = cnt - after_c.get(key, 0)
        for _ in range(max(0, lost)):
            consumed.append(key)
    return True, consumed


def _refund_partial(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    consumed: Sequence[Tuple[str, str]],
    money_paid: int,
    *,
    refund_money_pct: float,
    refund_mat_pct: float,
    rng: random.Random,
) -> List[str]:
    lines: List[str] = []
    back_m = int(round(money_paid * max(0.0, min(1.0, refund_money_pct))))
    if back_m > 0:
        player["money_world"] = int(player.get("money_world") or 0) + back_m
        lines.append(f"  เงินคืนบางส่วน +{back_m}")

    # return roughly refund_mat_pct of items (at least try)
    n = len(consumed)
    if n <= 0:
        return lines
    target = max(0, int(round(n * refund_mat_pct)))
    # shuffle copy
    pool = list(consumed)
    _rng_shuffle(rng, pool)
    returned = 0
    for iid, rid in pool:
        if returned >= target:
            break
        # don't refund cards into inventory_ids incorrectly
        if iid in (reg.cards or {}) or str(iid).startswith("card_"):
            bag = list(player.get("card_bag") or [])
            bag.append(iid)
            player["card_bag"] = bag
        else:
            add_item(player, iid, reg, rarity=rid)
        returned += 1
    if returned:
        lines.append(f"  วัตถุดิบบางส่วนกลับมา ({returned} ชิ้น)")
    return lines


def craft(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    recipe_id: str,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Attempt craft. Returns soft message (สำเร็จ / ล้มเหลว / เงื่อนไขไม่พอ).
    K1: success roll · soft/hard fail refunds
    K2: quality mult from materials above min rank
    """
    from game.domain.rarity import (
        display_item_name,
        tier_by_id,
    )

    rng = rng or random.Random()
    recipe = (reg.recipes or {}).get(recipe_id)
    if not recipe:
        return "ไม่พบสูตร"
    if int(player.get("level", 1)) < int(recipe.get("unlock_level", 1)):
        return "เลเวลไม่พอ"
    # K3: station must match location
    if not station_ok_for_recipe(player, recipe, reg):
        need = str(recipe.get("station") or "")
        need_lbl = station_label(need, reg) if need else "?"
        scfg = _station_cfg(reg)
        msgs = list(scfg.get("missing_messages") or [])
        soft = _rng_choice(rng, msgs, "「ที่นี่ไม่มีสถานีสำหรับงานนี้」")
        here = format_stations_line(player, reg)
        return (
            f"สถานีไม่ตรง: ต้องการ「{need_lbl}」\n"
            f"  {here}\n"
            f"  {soft}"
        )
    if not can_craft(player, recipe, reg):
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

    rules = _craft_rules(reg)
    fail_cfg = dict(rules.get("fail") or {})
    sc_over = recipe.get("success") if isinstance(recipe.get("success"), dict) else {}
    money = int(recipe.get("money", 0))
    chance = craft_success_chance(player, recipe, reg)
    label = craft_chance_label(chance, reg)

    # pay + consume first (risk after commit — crafting starts)
    player["money_world"] = int(player.get("money_world", 0)) - money
    ok, consumed = _consume_inputs(player, recipe, reg)
    if not ok:
        # refund money if consume failed mid-way (shouldn't if can_craft)
        player["money_world"] = int(player.get("money_world", 0)) + money
        return "วัตถุดิบไม่พอ (ระหว่างหัก)"

    roll = rng.random()
    if roll <= chance:
        out_id = str(recipe.get("output"))
        out_r = _resolve_output_rarity(recipe, reg)
        shown = add_item(player, out_id, reg, rarity=str(out_r))
        if shown and "ไม่พบ" not in str(shown):
            nice = shown
        else:
            nice = display_item_name(
                str(
                    (reg.items.get(out_id) or reg.cards.get(out_id) or {}).get("name")
                    or out_id
                ),
                str(out_r),
                reg,
            )
        flavors = list(fail_cfg.get("success_flavors") or [])
        flavor = _rng_choice(rng, flavors, "「ค้อนและไฟยอม」")
        return f"คราฟสำเร็จ: {recipe.get('name')} → {nice}  {flavor}"

    # ── fail ──
    hard_chance = float(sc_over.get("hard_chance") if sc_over.get("hard_chance") is not None else fail_cfg.get("hard_chance") or 0.18)
    mode = str(sc_over.get("fail_mode") or fail_cfg.get("mode") or "soft")
    is_hard = mode == "hard" or (mode == "soft" and rng.random() < hard_chance)

    refund_m = float(
        sc_over.get("refund_money_pct")
        if sc_over.get("refund_money_pct") is not None
        else fail_cfg.get("refund_money_pct") or 0.45
    )
    refund_mat = float(
        sc_over.get("refund_mat_pct")
        if sc_over.get("refund_mat_pct") is not None
        else fail_cfg.get("refund_mat_pct") or 0.50
    )

    if is_hard:
        msgs = list(fail_cfg.get("hard_messages") or ["「เถ้าเท่านั้นที่เหลือ」"])
        msg = _rng_choice(rng, msgs, "「เถ้าเท่านั้นที่เหลือ」")
        return f"คราฟล้มเหลว: {recipe.get('name')}  {msg}  (รู้สึก:{label})"

    msgs = list(fail_cfg.get("soft_messages") or ["「สูตรสั่น — ครั้งนี้ยังไม่ถึง」"])
    msg = _rng_choice(rng, msgs, "「สูตรสั่น — ครั้งนี้ยังไม่ถึง」")
    lines = [f"คราฟล้มเหลว: {recipe.get('name')}  {msg}  (รู้สึก:{label})"]
    lines.extend(
        _refund_partial(
            player,
            reg,
            consumed,
            money,
            refund_money_pct=refund_m,
            refund_mat_pct=refund_mat,
            rng=rng,
        )
    )
    return "\n".join(lines)
