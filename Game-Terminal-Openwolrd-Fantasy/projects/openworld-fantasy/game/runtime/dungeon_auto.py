"""
Dungeon auto-play — prefs thresholds, skill plan, regen, full XP.
Boss: manual clear once per depth; then auto rematch allowed.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry
from game.domain.dungeon import (
    apply_dungeon_enemy_mods,
    current_depth,
    explore_floor_event,
    get_run,
    in_dungeon,
    is_boss_encounter_active,
    note_dungeon_fight,
    spawn_floor_boss,
)
from game.domain.needs import (
    append_auto_care_note,
    apply_auto_rest,
    apply_food_relief,
    decide_auto_needs_care,
    ensure_needs,
    get_needs,
    is_food_item,
)
from game.ports.io import IO
from game.runtime.auto_farm import auto_fight
from game.ui_terminal.layout import render_box

AUTO_DUNGEON_TICKS_DEFAULT = 15
DUNGEON_AUTO_XP_FACTOR = 1.0

# WO-017 R3: Field30 showed rest 17/30 (~0.57/tick) still high → fatigue thr 67
# Counters: 1 action = 1 count (see auto_run_log / care bumps)
DEFAULT_AUTO_PREFS: Dict[str, Any] = {
    "hp_pct": 35,
    "mp_pct": 20,
    "hunger": 58,
    "fatigue": 67,  # R3: was 62 — reduce field rest spam
    "morale": 30,
    "low_morale_policy": "caution",
    "skill_plan": [1],
    "item_mode": "normal",
    "inv_manage": True,
    "inv_min_food": 4,
    "inv_min_hp_pots": 1,
    "inv_drop_junk": True,
    "inv_sell_junk": True,  # WO-021: sell junk for small world gold (prefer over drop)
    "inv_bag_free_slots": 2,
    "inv_max_junk_drops": 3,
    # WO-022: soft default ON — thrift mode still restrains spend
    "auto_buy_supplies": True,
    "auto_buy_reserve": 50,  # keep at least this much money_world
    "auto_buy_max": 2,  # max items per care pass
    # WO-023 Divine Burden
    "auto_unequip_burden": True,  # take off crushing relics when morale low
    "auto_equip_relics": False,  # do not auto-wear legendary+ that strains
    # WO-025: soft skip player-echoes that radiate relic aura
    "auto_avoid_relic_echo": True,
    # WO-039: soft-skip/avoid faction mini-moments when faction score very cold
    "auto_avoid_cold_faction": True,
}


def ensure_auto_prefs(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    raw = dict(player.get("auto_prefs") or {})
    out = dict(DEFAULT_AUTO_PREFS)
    out.update({k: raw[k] for k in DEFAULT_AUTO_PREFS if k in raw})
    # clamp
    out["hp_pct"] = int(max(15, min(70, int(out.get("hp_pct") or 40))))
    out["mp_pct"] = int(max(5, min(50, int(out.get("mp_pct") or 25))))
    out["hunger"] = int(max(25, min(85, int(out.get("hunger") or 50))))
    out["fatigue"] = int(max(30, min(90, int(out.get("fatigue") or 55))))
    out["morale"] = int(max(10, min(70, int(out.get("morale") or 35))))
    pol = str(out.get("low_morale_policy") or "caution").lower()
    if pol not in ("ignore", "caution", "retreat"):
        pol = "caution"
    out["low_morale_policy"] = pol
    plan = out.get("skill_plan") or [1]
    if isinstance(plan, str):
        plan = _parse_skill_plan_str(plan)
    out["skill_plan"] = [int(x) for x in plan if str(x).isdigit() or isinstance(x, int)]
    if not out["skill_plan"]:
        out["skill_plan"] = [1]
    mode = str(out.get("item_mode") or "normal").lower()
    if mode not in ("thrift", "normal", "safe"):
        mode = "normal"
    out["item_mode"] = mode
    # P1.4 / WO-021 inv clamps
    out["inv_manage"] = bool(out.get("inv_manage", True))
    out["inv_drop_junk"] = bool(out.get("inv_drop_junk", True))
    out["inv_sell_junk"] = bool(out.get("inv_sell_junk", True))
    out["inv_min_food"] = int(max(0, min(12, int(out.get("inv_min_food") or 2))))
    out["inv_min_hp_pots"] = int(max(0, min(8, int(out.get("inv_min_hp_pots") or 1))))
    out["inv_bag_free_slots"] = int(max(0, min(8, int(out.get("inv_bag_free_slots") or 2))))
    out["inv_max_junk_drops"] = int(max(0, min(6, int(out.get("inv_max_junk_drops") or 3))))
    out["auto_buy_supplies"] = bool(out.get("auto_buy_supplies", True))
    out["auto_buy_reserve"] = int(max(0, min(500, int(out.get("auto_buy_reserve") or 50))))
    out["auto_buy_max"] = int(max(0, min(6, int(out.get("auto_buy_max") or 2))))
    out["auto_unequip_burden"] = bool(out.get("auto_unequip_burden", True))
    out["auto_equip_relics"] = bool(out.get("auto_equip_relics", False))
    out["auto_avoid_relic_echo"] = bool(out.get("auto_avoid_relic_echo", True))
    out["auto_avoid_cold_faction"] = bool(out.get("auto_avoid_cold_faction", True))
    player["auto_prefs"] = out
    return out


def _parse_skill_plan_str(s: str) -> List[int]:
    parts = s.replace(" ", "").replace("→", ",").replace("->", ",").split(",")
    out: List[int] = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
    return out


def list_combat_skill_ids(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    """Ordered combat-usable skills for auto plan indexing (1-based in UI)."""
    out: List[str] = []
    # index 1 always basic physical spam option
    out.append("__basic__")
    for sid in player.get("skills") or []:
        sk = reg.skills.get(str(sid)) or {}
        slot = str(sk.get("slot") or "combat").lower()
        if slot in ("combat", "debuff", "buff", ""):
            if sk.get("power") or slot in ("buff", "debuff") or sk.get("aoe"):
                out.append(str(sid))
            elif sid not in out:
                out.append(str(sid))
    # dedupe preserve order
    seen = set()
    uniq: List[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def skill_plan_labels(
    player: Mapping[str, Any], reg: DataRegistry, plan: Sequence[int]
) -> str:
    ids = list_combat_skill_ids(player, reg)
    names: List[str] = []
    for idx in plan:
        i = int(idx) - 1
        if i < 0 or i >= len(ids):
            names.append("?")
            continue
        sid = ids[i]
        if sid == "__basic__":
            names.append("โจมตีปกติ")
        else:
            names.append(str((reg.skills.get(sid) or {}).get("name") or sid))
    return " → ".join(names)


def count_food(player: Mapping[str, Any], reg: DataRegistry) -> int:
    n = 0
    for iid in player.get("inventory_ids") or []:
        it = (reg.items or {}).get(str(iid)) or {}
        if is_food_item(it):
            n += 1
    return n


def count_potions(
    player: Mapping[str, Any], reg: DataRegistry, *, kind: str = "hp"
) -> int:
    n = 0
    for iid in player.get("inventory_ids") or []:
        it = (reg.items or {}).get(str(iid)) or {}
        s = str(iid).lower()
        if kind == "hp" and ("potion_hp" in s or it.get("heal_hp")):
            n += 1
        elif kind == "mp" and ("potion_mana" in s or "potion_mp" in s or it.get("heal_mana") and not it.get("heal_hp")):
            if "potion_mana" in s or "mana" in s:
                n += 1
    return n


def format_dungeon_auto_hud(player: Mapping[str, Any], reg: DataRegistry) -> str:
    """hp(72/180=40%) mp(12/80=15%) หิว(58) ล้า(40) อาหาร(3)"""
    ensure_needs(player)  # type: ignore
    needs = get_needs(player)  # type: ignore
    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    mp = int(player.get("mana") or 0)
    mmp = max(1, int(player.get("max_mana") or 1))
    hunger = int(needs.get("hunger") or 0)
    fatigue = int(needs.get("fatigue") or 0)
    morale = int(needs.get("morale") or 0)
    food_n = count_food(player, reg)
    depth = current_depth(get_run(player) or {}) if get_run(player) else 0
    hp_pct = int(round(100 * hp / mhp))
    mp_pct = int(round(100 * mp / mmp))
    return (
        f"hp({hp}/{mhp}={hp_pct}%) mp({mp}/{mmp}={mp_pct}%) "
        f"หิว({hunger}) ล้า({fatigue}) ขวัญ({morale}) อาหาร({food_n})"
        f" · ชั้น{depth}"
    )


def _mode_shift(prefs: Mapping[str, Any], mode: str) -> Dict[str, int]:
    """thrift = use items later; safe = use earlier."""
    hp = int(prefs.get("hp_pct") or 40)
    mp = int(prefs.get("mp_pct") or 25)
    hung = int(prefs.get("hunger") or 50)
    fat = int(prefs.get("fatigue") or 55)
    mor = int(prefs.get("morale") or 35)
    if mode == "thrift":
        return {
            "hp_pct": max(15, hp - 12),
            "mp_pct": max(5, mp - 8),
            "hunger": min(85, hung + 12),
            "fatigue": min(90, fat + 12),
            # thrift: tolerate lower morale longer before care
            "morale": max(10, mor - 8),
        }
    if mode == "safe":
        return {
            "hp_pct": min(70, hp + 12),
            "mp_pct": min(50, mp + 10),
            "hunger": max(25, hung - 10),
            "fatigue": max(30, fat - 10),
            # safe: act on morale earlier (higher threshold)
            "morale": min(70, mor + 10),
        }
    return {"hp_pct": hp, "mp_pct": mp, "hunger": hung, "fatigue": fat, "morale": mor}


def _effective_thresholds(
    player: Mapping[str, Any], reg: DataRegistry
) -> Dict[str, int]:
    prefs = ensure_auto_prefs(player)  # type: ignore
    th = _mode_shift(prefs, str(prefs.get("item_mode") or "normal"))
    food_n = count_food(player, reg)
    pot_n = count_potions(player, reg, kind="hp")
    # few consumables → thrift further
    if food_n <= 2:
        th["hunger"] = min(85, th["hunger"] + 8)
    if pot_n <= 1:
        th["hp_pct"] = max(15, th["hp_pct"] - 8)
    # deep floor → safer
    run = get_run(player)
    if run:
        depth = current_depth(run)
        if depth >= 4:
            th["hp_pct"] = min(70, th["hp_pct"] + 5)
            th["morale"] = min(70, int(th.get("morale") or 35) + 5)
    return th


def run_auto_needs_care(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    allow_rest: bool = True,
) -> Tuple[List[str], Optional[str], bool, bool]:
    """
    WO-004: care pass — decide + eat/rest/potion with soft reasons.
    Returns (log_lines, stop_reason, avoid_fight, skipped_tick_for_rest).
    stop_reason: food | morale | None
    """
    lines: List[str] = []
    prefs = ensure_auto_prefs(player)
    th = _effective_thresholds(player, reg)
    ensure_needs(player)
    # WO-023: Divine Burden tick + auto unequip when morale low
    try:
        from game.domain.divine_burden import apply_burden_tick, try_auto_unequip_burden

        bl = apply_burden_tick(player, reg, context="field")
        lines.extend(bl)
        for b in bl:
            append_auto_care_note(player, b)
        ul = try_auto_unequip_burden(player, reg)
        lines.extend(ul)
    except Exception:
        pass
    # P1.4 / WO-021: inventory manage first (sell/drop space + optional buy + warnings)
    try:
        from game.runtime.inventory_auto import (
            auto_free_bag_space,
            soft_stock_warnings,
            try_auto_buy_supplies,
        )

        if prefs.get("inv_manage", True):
            if prefs.get("inv_sell_junk", True) or prefs.get("inv_drop_junk", True):
                lines.extend(
                    auto_free_bag_space(
                        player,
                        reg,
                        need_free=int(prefs.get("inv_bag_free_slots") or 2),
                        max_drops=int(prefs.get("inv_max_junk_drops") or 3),
                    )
                )
            lines.extend(try_auto_buy_supplies(player, reg))
            for w in soft_stock_warnings(player, reg, prefs):
                lines.append(w)
                append_auto_care_note(player, w)
    except Exception:
        pass
    food_n = count_food(player, reg)
    intents = decide_auto_needs_care(
        player,
        hunger_th=int(th["hunger"]),
        fatigue_th=int(th["fatigue"]),
        morale_th=int(th.get("morale") or prefs.get("morale") or 35),
        low_morale_policy=str(prefs.get("low_morale_policy") or "caution"),
        food_available=food_n > 0,
    )
    avoid_fight = False
    stop_reason: Optional[str] = None
    did_rest = False
    did_eat = False
    block_boss = False

    for intent in intents:
        act = str(intent.get("action") or "")
        reason = str(intent.get("reason") or "")
        if act == "set_aggression":
            player["_auto_aggression"] = reason or "normal"
            continue
        if act == "block_boss_auto":
            block_boss = True
            player["_auto_block_boss"] = True
            continue
        if act == "crit_warn":
            if reason:
                lines.append(f"  {reason}")
                append_auto_care_note(player, reason)
            continue
        if act == "stop_retreat":
            if reason:
                lines.append(f"  {reason}")
                append_auto_care_note(player, reason)
            stop_reason = "morale"
            continue
        if act == "avoid_fight":
            avoid_fight = True
            if reason:
                lines.append(f"  {reason}")
                append_auto_care_note(player, reason)
            continue
        if act in ("eat", "eat_morale") and not did_eat:
            if reason:
                lines.append(f"  {reason}")
                append_auto_care_note(player, reason)
            prefer = "morale" if act == "eat_morale" else "hunger"
            notes = _consume_best_food(player, reg, prefer=prefer)
            for n in notes:
                lines.append(n if str(n).startswith(" ") else f"  {n}")
            did_eat = True
            # WO-017 R3: one eat action = one counter
            try:
                from game.runtime.auto_run_log import bump_auto_run

                bump_auto_run(player, "eats")
            except Exception:
                pass
            continue
        if act in ("rest", "rest_long") and allow_rest and not did_rest:
            if reason:
                lines.append(f"  {reason}")
                append_auto_care_note(player, reason)
            # rest_long: apply rest twice (crit morale) — still 1 care action
            rounds = 2 if act == "rest_long" else 1
            for _ in range(rounds):
                for n in apply_auto_rest(player):
                    if n and ("…" in str(n) or "พัก" in str(n) or "สถานะ" in str(n)):
                        lines.append(n if str(n).startswith(" ") else f"  {n}")
            if act == "rest_long":
                lines.append("  ออโต้: พักนานขึ้น (ขวัญวิกฤต) — ไม่สำรวจต่อ")
            else:
                lines.append("  ออโต้: พักครบติก — ไม่สำรวจต่อในจังหวะนี้")
            did_rest = True
            try:
                from game.runtime.auto_run_log import bump_auto_run

                bump_auto_run(player, "rests")
            except Exception:
                pass
            continue

    if not block_boss:
        player.pop("_auto_block_boss", None)

    # HP/MP potions (+ morale food if still low and not just ate)
    pot_notes = use_items_by_thresholds(player, reg, force=False)
    pot_bumped = False
    for n in pot_notes:
        lines.append(n if str(n).startswith(" ") else f"  {n}")
        if not pot_bumped and n and ("ยา" in str(n) or "HP" in str(n) or "MP" in str(n)):
            try:
                from game.runtime.auto_run_log import bump_auto_run

                bump_auto_run(player, "potions")
                pot_bumped = True
            except Exception:
                pass

    ensure_needs(player)
    if count_food(player, reg) <= 0 and int(get_needs(player).get("hunger") or 0) >= th["hunger"]:
        msg = "  ออโต้หยุด: อาหารหมด · หิวถึงเกณฑ์"
        lines.append(msg)
        append_auto_care_note(player, msg)
        stop_reason = stop_reason or "food"

    return lines, stop_reason, avoid_fight, did_rest


def compute_auto_regen(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    in_combat: bool = False,
) -> Dict[str, float]:
    """
    Hidden regen rates per tick/round.
    Returns fractions of max: hp_frac, mp_frac, fatigue_relief (absolute points).
    """
    base_hp = 0.008
    base_mp = 0.015
    base_fat = 1.5  # points reduced
    if in_combat:
        base_hp *= 0.45
        base_mp *= 0.55
        base_fat *= 0.4

    occ = str(player.get("occupation") or "vagabond")
    occ_mod = {
        "priest": (1.35, 1.4, 1.5),
        "mage": (0.85, 1.55, 1.0),
        "warrior": (1.25, 0.75, 1.1),
        "rogue": (1.0, 1.0, 1.35),
        "archer": (1.05, 1.05, 1.1),
        "vagabond": (1.1, 1.0, 1.2),
    }.get(occ, (1.0, 1.0, 1.0))

    flags = set(player.get("blessing_flags") or [])
    bless_hp = 1.15 if "soft_second_wind" in flags else 1.0
    bless_mp = 1.12 if ("quiet_mind" in flags or "grace_mind" in flags) else 1.0
    bless_fat = 1.1 if "grace_body" in flags else 1.0

    pdef = float(player.get("power_def") or 0)
    pmag = float(player.get("power_mag") or 0)
    pspd = float(player.get("power_spd") or 0)
    latent_hp = 1.0 + min(0.25, pdef / 80.0)
    latent_mp = 1.0 + min(0.3, pmag / 70.0)
    latent_fat = 1.0 + min(0.2, pspd / 90.0)

    unit_hp = unit_mp = unit_fat = 1.0
    uid = str(player.get("unit_class_id") or "")
    if uid and reg:
        udef = (getattr(reg, "unit_classes", None) or {}).get(uid) or {}
        if not udef and isinstance(getattr(reg, "unit_classes", None), list):
            for u in reg.unit_classes:  # type: ignore
                if isinstance(u, dict) and u.get("id") == uid:
                    udef = u
                    break
        tier = str(udef.get("power_tier") or "mid")
        mastery = int(player.get("unit_mastery") or 0)
        mboost = 1.0 + min(0.2, mastery / 200.0)
        if tier in ("strong", "broken"):
            unit_hp = 1.12 * mboost
            unit_mp = 1.15 * mboost
            unit_fat = 1.1 * mboost
        elif tier == "mid":
            unit_hp = 1.06 * mboost
            unit_mp = 1.08 * mboost
        # name heuristics
        name = str(udef.get("name") or uid).lower()
        if "aegis" in uid or "iron" in uid or "stone" in uid or "แอจิส" in name:
            unit_hp *= 1.1
        if "nova" in uid or "arcane" in uid or "void" in uid or "โนวา" in name:
            unit_mp *= 1.12

    hp_f = base_hp * occ_mod[0] * bless_hp * latent_hp * unit_hp
    mp_f = base_mp * occ_mod[1] * bless_mp * latent_mp * unit_mp
    fat_r = base_fat * occ_mod[2] * bless_fat * latent_fat * unit_fat

    # hard caps
    hp_f = max(0.0, min(0.045, hp_f))
    mp_f = max(0.0, min(0.055, mp_f))
    fat_r = max(0.0, min(8.0, fat_r))

    # crit hunger soft-cuts HP regen
    try:
        ensure_needs(player)  # type: ignore
        hun = int(get_needs(player).get("hunger") or 0)  # type: ignore
        if hun >= 80:
            hp_f *= 0.35
        elif hun >= 60:
            hp_f *= 0.7
    except Exception:
        pass

    return {"hp_frac": hp_f, "mp_frac": mp_f, "fatigue_relief": fat_r}


def apply_auto_regen(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    in_combat: bool = False,
) -> List[str]:
    rates = compute_auto_regen(player, reg, in_combat=in_combat)
    mhp = max(1, int(player.get("max_hp") or 1))
    mmp = max(1, int(player.get("max_mana") or 1))
    hpg = max(0, int(round(mhp * rates["hp_frac"])))
    mpg = max(0, int(round(mmp * rates["mp_frac"])))
    if hpg:
        player["hp"] = min(mhp, int(player.get("hp") or 0) + hpg)
    if mpg:
        player["mana"] = min(mmp, int(player.get("mana") or 0) + mpg)
    ensure_needs(player)
    needs = dict(player.get("needs") or {})
    before_f = int(needs.get("fatigue") or 0)
    needs["fatigue"] = max(0, before_f - int(round(rates["fatigue_relief"])))
    player["needs"] = needs
    if hpg or mpg or needs["fatigue"] < before_f:
        bits = []
        if hpg:
            bits.append("เลือดอุ่น")
        if mpg:
            bits.append("มานาซึม")
        if needs["fatigue"] < before_f:
            bits.append("ล้าแผ่ว")
        return [f"  รีเจน: {' · '.join(bits)}"]
    return []


def _remove_inv_index(player: MutableMapping[str, Any], reg: DataRegistry, idx: int) -> None:
    try:
        from game.domain.rarity import remove_inventory_at_index

        remove_inventory_at_index(player, idx, reg)
    except Exception:
        ids = list(player.get("inventory_ids") or [])
        rar = list(player.get("inventory_rarities") or [])
        if 0 <= idx < len(ids):
            ids.pop(idx)
            player["inventory_ids"] = ids
        if 0 <= idx < len(rar):
            rar.pop(idx)
            player["inventory_rarities"] = rar


def use_items_by_thresholds(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    force: bool = False,
) -> List[str]:
    """Use food/potion when gauges cross thresholds (incl. morale — P1.3)."""
    notes: List[str] = []
    th = _effective_thresholds(player, reg)
    prefs = ensure_auto_prefs(player)
    ensure_needs(player)
    needs = get_needs(player)
    hunger = int(needs.get("hunger") or 0)
    fatigue = int(needs.get("fatigue") or 0)
    morale = int(needs.get("morale") or 0)
    mor_th = int(th.get("morale") or prefs.get("morale") or 35)
    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    mp = int(player.get("mana") or 0)
    mmp = max(1, int(player.get("max_mana") or 1))
    hp_pct = 100.0 * hp / mhp
    mp_pct = 100.0 * mp / mmp

    # food for hunger / fatigue
    need_food = force or hunger >= th["hunger"] or fatigue >= th["fatigue"]
    # P1.3: eat for morale when low/crit and policy not ignore
    pol = str(prefs.get("low_morale_policy") or "caution")
    need_morale_food = (
        pol != "ignore"
        and morale <= mor_th
        and not need_food
    )
    if need_food:
        n = _consume_best_food(player, reg, prefer="hunger")
        notes.extend(n)
    elif need_morale_food:
        n = _consume_best_food(player, reg, prefer="morale")
        if n and "ไม่มี" not in "".join(n):
            notes.append("  ออโต้: เลือกเสบียงประทังขวัญ")
        notes.extend(n)

    # HP potion
    if force or hp_pct <= th["hp_pct"]:
        n = _consume_potion(player, reg, kind="hp")
        notes.extend(n)

    # MP potion — only if plan needs mana; low morale → thrift MP slightly
    plan_needs_mp = any(int(x) != 1 for x in (prefs.get("skill_plan") or [1]))
    mp_th = int(th["mp_pct"])
    if morale <= mor_th and pol != "ignore":
        # less aggressive skill use path: wait for lower MP before potion
        mp_th = max(5, mp_th - 5)
    if plan_needs_mp and (force or mp_pct <= mp_th):
        n = _consume_potion(player, reg, kind="mp")
        notes.extend(n)

    food_left = count_food(player, reg)
    if food_left <= 2 and notes:
        notes.append("  ⚠ อาหารใกล้หมด — ร้านเงา (8)")
    return notes


def _consume_best_food(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    prefer: str = "hunger",
) -> List[str]:
    """
    prefer: hunger → max hunger_relief; morale → max morale_boost (P1.3).
    """
    ids = list(player.get("inventory_ids") or [])
    best_i, best_score = -1, -1
    for i, iid in enumerate(ids):
        it = (reg.items or {}).get(str(iid)) or {}
        if not is_food_item(it):
            continue
        hr = int(it.get("hunger_relief") or (20 + 12 * int(it.get("food_tier") or 1)))
        mb = int(it.get("morale_boost") or max(2, 3 * int(it.get("food_tier") or 1)))
        score = mb if prefer == "morale" else hr
        if prefer == "morale":
            score = mb * 10 + hr  # prefer morale but break ties with hunger relief
        if score > best_score:
            best_score, best_i = score, i
    if best_i < 0:
        return ["  ออโต้: ไม่มีอาหาร"]
    iid = str(ids[best_i])
    it = (reg.items or {}).get(iid) or {}
    _remove_inv_index(player, reg, best_i)
    hr = int(it.get("hunger_relief") or (20 + 12 * int(it.get("food_tier") or 1)))
    fr = int(it.get("fatigue_relief") or max(0, 2 * int(it.get("food_tier") or 1)))
    mb = int(it.get("morale_boost") or max(2, 3 * int(it.get("food_tier") or 1)))
    apply_food_relief(
        player, hunger_relief=hr, fatigue_relief=fr, morale_boost=mb, silent=True
    )
    if it.get("heal_hp"):
        player["hp"] = min(
            int(player["max_hp"]),
            int(player.get("hp") or 0) + int(it["heal_hp"]),
        )
    if it.get("heal_mana"):
        player["mana"] = min(
            int(player["max_mana"]),
            int(player.get("mana") or 0) + int(it["heal_mana"]),
        )
    left = count_food(player, reg)
    tag = "ขวัญ" if prefer == "morale" else "ท้อง"
    return [
        f"  ใช้เงื่อนไข → กิน「{it.get('name') or iid}」({tag}) · อาหารเหลือ {left}"
    ]


def _consume_potion(
    player: MutableMapping[str, Any], reg: DataRegistry, *, kind: str
) -> List[str]:
    ids = list(player.get("inventory_ids") or [])
    for i, iid in enumerate(ids):
        it = (reg.items or {}).get(str(iid)) or {}
        s = str(iid).lower()
        ok = False
        if kind == "hp" and ("potion_hp" in s or it.get("heal_hp")):
            ok = True
        if kind == "mp" and ("potion_mana" in s or ("mana" in s and "potion" in s)):
            ok = True
        if not ok:
            continue
        _remove_inv_index(player, reg, i)
        if kind == "hp":
            heal = int(it.get("heal_hp") or 40)
            player["hp"] = min(int(player["max_hp"]), int(player.get("hp") or 0) + heal)
            return [f"  ใช้เงื่อนไข → ยา「{it.get('name') or iid}」HP+{heal}"]
        heal = int(it.get("heal_mana") or 30)
        player["mana"] = min(
            int(player["max_mana"]), int(player.get("mana") or 0) + heal
        )
        return [f"  ใช้เงื่อนไข → ยา「{it.get('name') or iid}」MP+{heal}"]
    return []


# backward-compatible alias
def auto_eat_if_needed(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    force: bool = False,
) -> List[str]:
    return use_items_by_thresholds(player, reg, force=force)


def resolve_skill_for_auto_turn(
    player: Mapping[str, Any],
    reg: DataRegistry,
    plan: Sequence[int],
    *,
    plan_step: int = 0,
) -> Tuple[Dict[str, Any], str]:
    """
    Pick skill for this auto-fight turn from plan.
    Returns (skill_dict, label). Mana checked — fallback basic.
    """
    ids = list_combat_skill_ids(player, reg)
    if not plan:
        plan = [1]
    idx = int(plan[plan_step % len(plan)]) - 1
    basic = {
        "power": 8 + int(player.get("bonus_atk", 0)) // 2,
        "elements": ["physical"],
        "name": "โจมตีปกติ",
        "cost_mana": 0,
        "id": "__basic__",
    }
    if idx < 0 or idx >= len(ids):
        return basic, "โจมตีปกติ"
    sid = ids[idx]
    if sid == "__basic__":
        return basic, "โจมตีปกติ"
    sk = dict(reg.skills.get(sid) or {})
    if not sk:
        return basic, "โจมตีปกติ"
    cost = int(sk.get("cost_mana") or sk.get("mana_cost") or 0)
    if int(player.get("mana") or 0) < cost:
        return basic, "โจมตีปกติ (มานาไม่พอ)"
    sk["id"] = sid
    sk.setdefault("name", sid)
    sk["cost_mana"] = cost
    return sk, str(sk.get("name") or sid)


def mark_floor_boss_manual_win(player: MutableMapping[str, Any]) -> None:
    run = player.get("dungeon_run")
    if not isinstance(run, dict):
        return
    run = dict(run)
    depth = current_depth(run)
    won = list(run.get("auto_boss_depths") or [])
    if depth not in won:
        won.append(depth)
    run["auto_boss_depths"] = won
    run["floor_boss_cleared"] = True
    player["dungeon_run"] = run


def can_auto_fight_floor_boss(player: Mapping[str, Any]) -> bool:
    run = get_run(player)
    if not run:
        return False
    depth = current_depth(run)
    won = list(run.get("auto_boss_depths") or [])
    return depth in won or bool(run.get("boss_defeated"))


def _one_auto_tick(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> Tuple[List[str], Optional[str]]:
    lines: List[str] = []
    if not in_dungeon(player) or is_boss_encounter_active(player):
        return ["  ไม่อยู่ในโหมดสำรวจดัน"], "left_dungeon"

    lines.extend(apply_auto_regen(player, reg, in_combat=False))

    # WO-004: needs care (eat / rest / morale policy / potions) with soft reasons
    care_lines, stop_reason, avoid_fight, rested = run_auto_needs_care(
        player, reg, allow_rest=True
    )
    lines.extend(care_lines)
    if stop_reason:
        return lines, stop_reason

    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    if 100.0 * hp / mhp < 8:
        msg = "  ออโต้หยุด: เลือดวิกฤต"
        lines.append(msg)
        append_auto_care_note(player, msg)
        return lines, "hp"

    # Rest used this tick's action slot — no explore/fight
    if rested:
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "auto_ticks", 1)
        except Exception:
            pass
        return lines, None

    try:
        from game.domain.needs import apply_needs_event

        apply_needs_event(player, "dungeon_tick")
    except Exception:
        pass
    try:
        from game.domain.party import tick_relationship_decay

        tick_relationship_decay(player, ticks=1)
    except Exception:
        pass

    prefs = ensure_auto_prefs(player)
    plan = list(prefs.get("skill_plan") or [1])

    if avoid_fight:
        # Still move lightly: soft empty explore without combat table force
        lines.append("  ออโต้: เดินเงียบ — หลีกไฟต์ตามขวัญ")
        try:
            from game.domain.needs import apply_needs_event

            apply_needs_event(player, "explore", silent=True)
        except Exception:
            pass
    else:
        ev = explore_floor_event(player, reg, rng)
        kind = str(ev.get("kind") or "empty")
        for n in (ev.get("notes") or [])[:2]:
            lines.append(f"  {n}" if not str(n).startswith(" ") else n)

        if ev.get("trigger_combat") or kind == "combat":
            from game.domain.combat import pick_monster

            run = get_run(player) or {}
            area = str(run.get("area_id") or "dark_forest")
            mon = pick_monster(reg, area, rng)
            mon = apply_dungeon_enemy_mods(mon, player)
            note_dungeon_fight(player)
            flog = auto_fight(
                player,
                mon,
                reg,
                rng,
                area,
                xp_factor=DUNGEON_AUTO_XP_FACTOR,
                skill_plan=plan,
                use_regen=True,
            )
            for x in flog:
                lines.append(f"  {x}")
            try:
                from game.runtime.auto_run_log import bump_auto_run

                bump_auto_run(player, "fights")
            except Exception:
                pass
            post, stop2, _, _ = run_auto_needs_care(player, reg, allow_rest=False)
            lines.extend(post)
            if stop2:
                return lines, stop2

        # P1.3: no boss auto rematch when morale low/crit (block_boss)
        can_boss_rematch = can_auto_fight_floor_boss(player) and not player.get(
            "_auto_block_boss"
        )
        if can_boss_rematch and rng.random() < 0.12:
            lines.append("  …เงาผู้เฝ้าที่เคยล้ม กลับมาวนอีก (ออโต้จัดการ)")
            boss = spawn_floor_boss(player, reg, rng)
            area = str((get_run(player) or {}).get("area_id") or "dark_forest")
            if boss:
                boss = apply_dungeon_enemy_mods(boss, player)
                flog = auto_fight(
                    player,
                    boss,
                    reg,
                    rng,
                    area,
                    xp_factor=DUNGEON_AUTO_XP_FACTOR,
                    skill_plan=plan,
                    use_regen=True,
                )
                for x in flog:
                    lines.append(f"  {x}")
                try:
                    from game.runtime.auto_run_log import bump_auto_run

                    bump_auto_run(player, "fights")
                except Exception:
                    pass
        elif can_auto_fight_floor_boss(player) and player.get("_auto_block_boss"):
            lines.append("  ออโต้: ขวัญไม่พร้อม — ไม่ท้าเงาผู้เฝ้าเอง")

    if not avoid_fight and rng.random() < 0.18:
        try:
            from game.domain.equipment import add_item

            if "upgrade_mat" in (reg.items or {}):
                nm = add_item(player, "upgrade_mat", reg, rarity="common")
                lines.append(f"  เก็บของอัตโนมัติ: {nm}")
        except Exception:
            pass
    if not avoid_fight and rng.random() < 0.08:
        try:
            from game.domain.equipment import add_item

            if "potion_hp_small" in (reg.items or {}):
                nm = add_item(player, "potion_hp_small", reg)
                lines.append(f"  เก็บของ: {nm}")
        except Exception:
            pass

    try:
        from game.domain.stats import bump_stat

        bump_stat(player, "auto_ticks", 1)
    except Exception:
        pass

    return lines, None


def configure_auto_prefs_menu(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    io: IO,
) -> Dict[str, Any]:
    """Interactive soft setup before dungeon auto."""
    prefs = ensure_auto_prefs(player)
    skills = list_combat_skill_ids(player, reg)

    while True:
        prefs = ensure_auto_prefs(player)
        io.write_line()
        lines = [
            " ตั้งค่าออโต้ในดัน",
            "---",
            f" 1  HP ใช้ยาเมื่อ ≤ {prefs['hp_pct']}%",
            f" 2  MP ใช้ยาเมื่อ ≤ {prefs['mp_pct']}%",
            f" 3  หิว กินเมื่อ ≥ {prefs['hunger']}",
            f" 4  ล้า พัก/กินเมื่อ ≥ {prefs['fatigue']}",
            f" 5  โหมดของ: {prefs['item_mode']}  (thrift/normal/safe)",
            f" 6  ลำดับสกิล: {prefs['skill_plan']} = {skill_plan_labels(player, reg, prefs['skill_plan'])}",
            f" 7  ขวัญ ดูแลเมื่อ ≤ {prefs['morale']}",
            f" 8  นโยบายขวัญ: {prefs['low_morale_policy']}  (ignore/caution/retreat)",
            "---",
            " รายการสกิล (เลขสำหรับแผน):",
        ]
        for i, sid in enumerate(skills, 1):
            if sid == "__basic__":
                lines.append(f"   {i}. โจมตีปกติ")
            else:
                nm = (reg.skills.get(sid) or {}).get("name") or sid
                cost = int((reg.skills.get(sid) or {}).get("cost_mana") or 0)
                lines.append(f"   {i}. {nm} (MP {cost})")
        lines.extend(
            [
                "---",
                "  ตัวอย่างแผน: 2,3,1  → ถ้ามานาไม่พอจะโจมตีปกติ",
                "  0  เริ่มออโต้ด้วยค่านี้",
                "  q  ยกเลิก",
            ]
        )
        io.write_line(render_box(lines, double=False))
        ch = io.read_line("\n  ตั้งออโต้> ").strip().lower()
        if ch in ("0", "", "start", "go"):
            return prefs
        if ch in ("q", "cancel"):
            return prefs
        if ch == "1":
            raw = io.read_line(f"  HP% (15-70) ตอนนี้ {prefs['hp_pct']}: ").strip()
            if raw.isdigit():
                prefs["hp_pct"] = int(raw)
        elif ch == "2":
            raw = io.read_line(f"  MP% (5-50) ตอนนี้ {prefs['mp_pct']}: ").strip()
            if raw.isdigit():
                prefs["mp_pct"] = int(raw)
        elif ch == "3":
            raw = io.read_line(f"  หิว (25-85) ตอนนี้ {prefs['hunger']}: ").strip()
            if raw.isdigit():
                prefs["hunger"] = int(raw)
        elif ch == "4":
            raw = io.read_line(f"  ล้า (30-90) ตอนนี้ {prefs['fatigue']}: ").strip()
            if raw.isdigit():
                prefs["fatigue"] = int(raw)
        elif ch == "5":
            raw = io.read_line("  โหมด thrift/normal/safe: ").strip().lower()
            if raw in ("thrift", "normal", "safe", "t", "n", "s"):
                prefs["item_mode"] = {
                    "t": "thrift",
                    "n": "normal",
                    "s": "safe",
                }.get(raw, raw)
        elif ch == "6":
            raw = io.read_line("  แผนสกิล เช่น 2,3,1: ").strip()
            plan = _parse_skill_plan_str(raw)
            if plan:
                prefs["skill_plan"] = plan
        elif ch == "7":
            raw = io.read_line(f"  ขวัญ (10-70) ตอนนี้ {prefs['morale']}: ").strip()
            if raw.isdigit():
                prefs["morale"] = int(raw)
        elif ch == "8":
            raw = io.read_line("  นโยบาย ignore/caution/retreat: ").strip().lower()
            if raw in ("ignore", "caution", "retreat", "i", "c", "r"):
                prefs["low_morale_policy"] = {
                    "i": "ignore",
                    "c": "caution",
                    "r": "retreat",
                }.get(raw, raw)
        player["auto_prefs"] = prefs
        ensure_auto_prefs(player)


def run_dungeon_auto(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: Optional[random.Random] = None,
    *,
    max_ticks: int = AUTO_DUNGEON_TICKS_DEFAULT,
    continuous: bool = True,
    skip_config: bool = False,
) -> str:
    rng = rng or random.Random()
    from game.runtime.auto_run_log import (
        bump_auto_run,
        emit_auto_run_summary,
        format_god_compact_status,
        is_god_compact,
        observe_auto_lines,
        start_auto_run,
    )

    if not in_dungeon(player):
        io.write_line("ต้องอยู่ในดันเจียนก่อน")
        return "not_in_dungeon"
    if is_boss_encounter_active(player):
        io.write_line("ติดวงบอส — จบไฟต์ก่อน แล้วค่อยออโต้")
        return "boss_lock"

    if not skip_config:
        configure_auto_prefs_menu(player, reg, io)

    prefs = ensure_auto_prefs(player)
    run = get_run(player) or {}
    depth = current_depth(run)
    can_boss = can_auto_fight_floor_boss(player)
    th = _effective_thresholds(player, reg)
    start_auto_run(
        player,
        kind="dungeon",
        label=f"Dungeon Auto · ชั้น {depth}",
        max_ticks=max_ticks,
    )
    intro = [
        " ออโต้ในดัน · ชั้นนี้",
        "---",
        f" ความลึก   ลงมาชั้นที่ {depth}",
        f" ติกสูงสุด  {max_ticks}",
        " XP ออโต้   เต็ม (ไม่ลด %)",
        f" เกณฑ์    HP≤{th['hp_pct']}% MP≤{th['mp_pct']}% "
        f"หิว≥{th['hunger']} ล้า≥{th['fatigue']} ขวัญ≤{th.get('morale', prefs['morale'])}",
        f" ขวัญนโยบาย  {prefs['low_morale_policy']}",
        f" โหมดของ  {prefs['item_mode']}",
        f" สกิล     {skill_plan_labels(player, reg, prefs['skill_plan'])}",
        f" อาหาร    {count_food(player, reg)} ชิ้น",
        f" กระเป๋า  จัดการอัตโน={'เปิด' if prefs.get('inv_manage') else 'ปิด'} "
        f"· ทิ้งขยะ={'เปิด' if prefs.get('inv_drop_junk') else 'ปิด'}",
        f" บอสชั้น  {'ออโต้ได้ (เคยชนะ)' if can_boss else 'ต้องสู้มือ 1 ครั้งก่อน'}",
        "---",
        " รีเจน · กิน/พัก/ยา · ขวัญ · กระเป๋า (ทิ้งขยะ/เตือนเสบียง)",
        " จบรอบมี สรุป Auto Run (WO-011)",
    ]
    io.write_line()
    io.write_line(render_box(intro, double=False))
    io.write_line(format_dungeon_auto_hud(player, reg))

    def _end(stop: str) -> str:
        emit_auto_run_summary(player, io, stop, reg=reg)
        return stop

    for tick in range(1, max_ticks + 1):
        bump_auto_run(player, "ticks")
        if is_god_compact(player):
            io.write_line()
            io.write_line(
                format_god_compact_status(
                    player,
                    f"ดันชั้น{depth}",
                    reg=reg,
                    tick=tick,
                    max_ticks=max_ticks,
                )
            )
        else:
            io.write_line(
                f"\n[ดัน-ออโต้ {tick}/{max_ticks}] {format_dungeon_auto_hud(player, reg)}"
            )
        lines, stop = _one_auto_tick(player, reg, rng)
        for ln in lines:
            io.write_line(ln)
        observe_auto_lines(player, lines)
        if stop:
            io.write_line(f"⏸ หยุดออโต้: {stop}")
            return _end(stop)
        if continuous and tick % 5 == 0:
            ch = io.read_line("  (ติก 5) Enter=ต่อ · s=หยุด: ").strip().lower()
            if ch in ("s", "stop", "q", "0"):
                io.write_line("หยุดออโต้ตามคำสั่ง")
                return _end("user")
        elif not continuous:
            ch = io.read_line("Enter=ต่อ · s=หยุด: ").strip().lower()
            if ch in ("s", "stop", "q", "0"):
                return _end("user")

    io.write_line(f"จบรอบออโต้ {max_ticks} ติก · {format_dungeon_auto_hud(player, reg)}")
    return _end("done")
