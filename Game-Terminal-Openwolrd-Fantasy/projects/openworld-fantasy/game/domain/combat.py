"""Turn combat using data registry — combo + defense matchups."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry
from game.domain.combo import apply_defense, resolve_combo
from game.domain.leveling import grant_xp, kill_xp_reward


def pick_monster(
    reg: DataRegistry,
    area_id: str,
    rng: random.Random,
) -> Dict[str, Any]:
    area = reg.areas.get(area_id) or {}
    pool = area.get("monster_pools") or []
    if not pool:
        mid = next(iter(reg.monsters.keys()))
        weight_entries = [{"id": mid, "weight": 1}]
    else:
        weight_entries = pool
    total = sum(int(e.get("weight", 1)) for e in weight_entries)
    roll = rng.randint(1, max(1, total))
    acc = 0
    chosen = weight_entries[0]["id"]
    for e in weight_entries:
        acc += int(e.get("weight", 1))
        if roll <= acc:
            chosen = e["id"]
            break
    base = dict(reg.monsters.get(chosen) or {"id": chosen, "name": chosen})
    lv_min = int(base.get("level_min", 1))
    lv_max = int(base.get("level_max", lv_min))
    mlevel = rng.randint(lv_min, max(lv_min, lv_max))
    hp = int(base.get("hp_base", 50)) + (mlevel - lv_min) * 6 + rng.randint(0, 10)
    atk = int(base.get("atk_base", 8)) + (mlevel - lv_min) // 2
    elements = list(base.get("elements") or ["physical"])
    profiles = list(base.get("attack_profiles") or [])
    if not profiles:
        # derive from elements
        profiles = [
            {
                "id": "basic",
                "tags": elements[:],
                "telegraph": "ศัตรูเตรียมโจมตี...",
                "power": atk,
            }
        ]
        if "fire" in elements:
            profiles.append(
                {
                    "id": "burn",
                    "tags": ["fire", "magic"],
                    "telegraph": "เปลวไฟรวมตัว!",
                    "power": atk + 2,
                }
            )
        if "shadow" in elements:
            profiles.append(
                {
                    "id": "shadow",
                    "tags": ["shadow", "magic"],
                    "telegraph": "เงากระชาก!",
                    "power": atk + 1,
                }
            )
        if "lightning" in elements:
            profiles.append(
                {
                    "id": "spark",
                    "tags": ["lightning", "magic"],
                    "telegraph": "ประกายไฟแลบ!",
                    "power": atk + 3,
                }
            )
    mon = {
        "id": base.get("id", chosen),
        "name": base.get("name", chosen),
        "base_name": base.get("name", chosen),
        "level": mlevel,
        "hp": hp,
        "max_hp": hp,
        "atk": atk,
        "elements": elements,
        "xp_mult": float(base.get("xp_mult", 1.0)),
        "attack_profiles": profiles,
        "statuses": [],
    }
    # optional: monster applies status on hit (catalog id + chance)
    if base.get("apply_status"):
        mon["apply_status"] = base.get("apply_status")
    # D1–D2: carry per-monster drop table + bound card (must survive into combat loot)
    _copy_mon_loot_fields(mon, base)
    if base.get("boss"):
        mon["boss"] = True
    if base.get("elite"):
        mon["elite"] = True
        # S1: elites hit slightly harder / tankier before rarity roll
        mon["hp"] = int(round(int(mon["hp"]) * 1.22))
        mon["max_hp"] = mon["hp"]
        mon["atk"] = int(round(int(mon["atk"]) * 1.12))
        mon["xp_mult"] = float(mon.get("xp_mult") or 1.0) * 1.25
    if base.get("tags"):
        mon["tags"] = list(base.get("tags") or [])
    # MI1–MI2: intel flags (tier / can_flee / never_flee)
    try:
        from game.domain.monster_ai import attach_monster_intel_fields

        attach_monster_intel_fields(mon, base)
    except Exception:
        pass
    # roll enemy rarity and scale
    try:
        from game.domain.rarity import apply_rarity_to_enemy, roll_enemy_rarity

        area_tier = int(area.get("world_tier") or area.get("tier") or 1)
        if base.get("elite") and not base.get("rarity"):
            rid = "uncommon" if rng.random() < 0.55 else "rare"
        else:
            rid = base.get("rarity") or roll_enemy_rarity(
                reg, rng, boss=False, area_tier=area_tier
            )
        mon = apply_rarity_to_enemy(mon, reg, str(rid))
        # rarity helper re-dicts; re-assert loot fields
        _copy_mon_loot_fields(mon, base)
        if base.get("elite"):
            mon["elite"] = True
            # soft elite label if rarity display didn't mark special
            bn = str(mon.get("base_name") or mon.get("name") or "")
            shown = str(mon.get("name") or "")
            if "◆" not in shown and "★" not in shown and "เถื่อน" not in shown:
                mon["name"] = f"◆ {bn}" if bn else shown
        try:
            from game.domain.monster_ai import attach_monster_intel_fields

            attach_monster_intel_fields(mon, base)
        except Exception:
            pass
    except Exception:
        mon["rarity"] = "uncommon" if base.get("elite") else "common"
        if base.get("elite"):
            mon["elite"] = True
            mon["name"] = f"◆ {mon.get('base_name') or mon.get('name')}"
    return mon


def _copy_mon_loot_fields(mon: MutableMapping[str, Any], base: Mapping[str, Any]) -> None:
    """Attach YAML drop table / card bind from catalog onto runtime mon."""
    if base.get("drops") is not None:
        mon["drops"] = list(base.get("drops") or [])
    if base.get("card_id"):
        mon["card_id"] = str(base.get("card_id"))
    if base.get("card_rate"):
        mon["card_rate"] = base.get("card_rate")
    if base.get("rarity") and not mon.get("catalog_rarity"):
        mon["catalog_rarity"] = base.get("rarity")


def apply_world_enemy_mods(mon: Dict[str, Any], player: Mapping[str, Any]) -> Dict[str, Any]:
    """Scale enemy by world difficulty modifiers on the player."""
    mods = player.get("world_modifiers") or {}
    hp_m = float(mods.get("enemy_hp_mult", 1.0))
    atk_m = float(mods.get("enemy_atk_mult", 1.0))
    mon = dict(mon)
    mon["hp"] = max(1, int(round(int(mon.get("hp", 1)) * hp_m)))
    mon["max_hp"] = max(1, int(round(int(mon.get("max_hp", mon["hp"])) * hp_m)))
    mon["atk"] = max(1, int(round(int(mon.get("atk", 1)) * atk_m)))
    # scale profile powers
    profiles = []
    for p in mon.get("attack_profiles") or []:
        p = dict(p)
        if "power" in p:
            p["power"] = max(1, int(round(int(p["power"]) * atk_m)))
        profiles.append(p)
    if profiles:
        mon["attack_profiles"] = profiles
    return mon


def _mastery_mult(player: Mapping[str, Any], area_id: str) -> float:
    mastery = (player.get("area_mastery") or {}).get(area_id, 10)
    return 0.65 + (float(mastery) / 100.0) * 0.75


def skill_options(player: Mapping[str, Any], reg: DataRegistry) -> List[Tuple[str, Dict[str, Any]]]:
    from game.domain.skill_charges import is_skill_usable
    from game.domain.skill_rank import scale_skill_for_player
    from game.domain.skill_slots import normalize_slot

    out = []
    for sid in player.get("skills") or []:
        sk = reg.skills.get(sid)
        if not sk:
            continue
        slot = normalize_slot(sk)
        # defense is chosen in guard phase, not attack menu
        if slot == "defense":
            continue
        if not is_skill_usable(player, sid):
            continue
        scaled = scale_skill_for_player(player, sk, reg, skill_id=sid)
        out.append((sid, scaled))
    return out


def player_attack_damage(
    player: Mapping[str, Any],
    monster: Mapping[str, Any],
    reg: DataRegistry,
    area_id: str,
    skill: Optional[Mapping[str, Any]],
    rng: random.Random,
    power_override: Optional[int] = None,
    elements_override: Optional[Sequence[str]] = None,
) -> Tuple[int, str]:
    # SK-R2: ensure skill is rank-scaled when id known
    if skill and not skill.get("_skill_rank") and skill.get("id"):
        try:
            from game.domain.skill_rank import scale_skill_for_player

            skill = scale_skill_for_player(
                player, skill, reg, skill_id=str(skill.get("id"))
            )
        except Exception:
            pass
    if skill and skill.get("heal") and power_override is None:
        return 0, "heal"
    # buff/debuff-only may have low/zero power
    try:
        from game.domain.skill_slots import normalize_slot

        if skill and normalize_slot(skill) == "buff" and power_override is None:
            return 0, "buff"
    except Exception:
        pass
    base = int(power_override if power_override is not None else (skill or {}).get("power", 8))
    base += int(player.get("bonus_atk", 0))
    try:
        from game.domain.status_fx import active_status_mods

        base += int(active_status_mods(player, reg).get("atk_flat") or 0)
    except Exception:
        pass
    # DD0–DD1: damage_class scales with class-linked powers (hidden)
    sk_elems = list(
        elements_override
        if elements_override is not None
        else (skill or {}).get("elements")
        or ["physical"]
    )
    try:
        from game.domain.damage_class import outbound_power_bonus, resolve_damage_class

        dclass = resolve_damage_class(skill, elements=sk_elems, reg=reg)
        base += int(outbound_power_bonus(player, dclass, reg))
    except Exception:
        if any(e in sk_elems for e in ("arcane", "fire", "water", "holy", "lightning", "shadow")):
            base += int(float(player.get("power_mag", 0)) * 0.35)
    base += rng.randint(0, 5)
    elems = list(sk_elems)
    for t in player.get("gear_tags") or []:
        if t not in elems:
            elems.append(str(t))
    em = reg.element_mult(elems, list(monster.get("elements") or []))
    mon_st = [s.get("id") if isinstance(s, dict) else s for s in (monster.get("statuses") or [])]
    if "freeze" in mon_st and ("lightning" in elems or "fire" in elems):
        em *= 1.35
    mult = _mastery_mult(player, area_id) * em
    if player.get("blessing_turns", 0) > 0:
        mult += 0.12
    # speed slight damage variance edge
    mult += min(0.12, float(player.get("power_spd", 5)) / 200.0)
    # N2: hunger soft ATK mult (hidden)
    try:
        from game.domain.needs import combat_needs_mults

        mult *= float(combat_needs_mults(player).get("atk_mult") or 1.0)
    except Exception:
        pass
    # food buff status atk
    try:
        from game.domain.status_fx import active_status_mods

        am = active_status_mods(player, reg)
        mult *= float(am.get("atk_mult") or 1.0)
    except Exception:
        pass
    dmg = max(1, int(base * mult))
    # crit from attack investment + latent (never show formula)
    crit_chance = float(player.get("crit_chance", 5))
    luck = float(player.get("luck_score") or 0.0)
    crit_chance = min(55.0, crit_chance * (1.0 + luck * 0.3))
    flavor = ""
    if rng.random() * 100 < crit_chance:
        dmg = int(dmg * 1.45)
        flavor = " (คริ!)"
    if em >= 1.25:
        flavor += " (ได้ผลดี!)"
    elif em <= 0.85:
        flavor += " (ต้านทาน...)"
    # S1: soft class label once in a while via elements (no numbers)
    try:
        from game.domain.damage_class import resolve_damage_class, soft_class_label

        dc = resolve_damage_class(skill, elements=elems, reg=reg)
        # only append short class cue when not already flavored heavily
        if dc and flavor.count("(") < 2 and rng.random() < 0.35:
            sn = soft_class_label(dc, reg)
            if sn:
                flavor += f" ·{sn}"
    except Exception:
        pass
    return dmg, flavor


def apply_incoming_damage(
    player: MutableMapping[str, Any],
    raw_dmg: int,
    rng: random.Random,
) -> Tuple[int, str]:
    """
    Speed soft dodge / partial mitigate. Luck biases slightly.
    Never reveal percentages to player — only flavor.
    """
    dmg = max(0, int(raw_dmg))
    if dmg <= 0:
        return 0, ""
    dodge = float(player.get("dodge_chance") or 3.0)
    luck = float(player.get("luck_score") or 0.0)
    dodge = min(40.0, max(0.0, dodge * (1.0 + luck * 0.25)))
    try:
        from game.domain.needs import combat_needs_mults

        nm = combat_needs_mults(player)
        dodge *= float(nm.get("dodge_mult") or 1.0)
        dmg = max(0, int(round(dmg * float(nm.get("incoming_mult") or 1.0))))
    except Exception:
        pass
    roll = rng.random() * 100
    if roll < dodge * 0.35:
        return 0, " (หลบพ้น!)"
    if roll < dodge:
        reduced = max(1, int(dmg * 0.55))
        return reduced, " (รับได้เบาลง)"
    # soft def flat
    def_b = int(player.get("alloc_def_bonus") or 0)
    dmg = max(1, dmg - def_b // 8)
    return dmg, ""


def apply_on_hit_cards(
    player: Mapping[str, Any],
    monster: MutableMapping[str, Any],
    rng: random.Random,
    reg: Optional[DataRegistry] = None,
) -> List[str]:
    """Apply at most one on-hit status per attack (anti power-creep)."""
    from game.domain.status_fx import apply_status, on_hit_chance_cap, status_display_name

    notes: List[str] = []
    effects = list(player.get("on_hit_effects") or [])
    if not effects:
        return notes
    cap = on_hit_chance_cap(reg)
    rng.shuffle(effects)
    for eff in effects:
        st = eff.get("status")
        chance = min(cap, float(eff.get("chance") or 0))
        if not st:
            continue
        applied = apply_status(
            monster, str(st), reg, rng, chance=chance, source="card_on_hit"
        )
        if applied:
            nm = status_display_name(reg, applied)
            notes.append(f"การ์ดติดสถานะ {nm}!")
            break  # only one status per hit
    return notes


def pick_monster_attack(
    monster: Mapping[str, Any],
    rng: random.Random,
    *,
    player: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Choose an attack profile.
    MI1: elite/boss/intel_tier use context-aware weights when `player` is given.
    """
    try:
        from game.domain.monster_ai import pick_smart_monster_attack

        return pick_smart_monster_attack(monster, rng, player=player)
    except Exception:
        profiles = list(monster.get("attack_profiles") or [])
        if not profiles:
            return {
                "tags": list(monster.get("elements") or ["physical"]),
                "telegraph": "ศัตรูโจมตี!",
                "power": int(monster.get("atk", 8)),
            }
        return dict(rng.choice(profiles))


def monster_raw_damage(monster: Mapping[str, Any], profile: Mapping[str, Any], rng: random.Random) -> int:
    power = int(profile.get("power") or monster.get("atk", 8))
    dmg = power + rng.randint(-2, 4)
    return max(1, dmg)


def apply_status_to_monster(
    monster: MutableMapping[str, Any],
    status_id: Optional[str],
    chance: float,
    rng: random.Random,
    reg: Optional[DataRegistry] = None,
    *,
    aoe: bool = False,
    n_targets: int = 1,
    attack_elements: Optional[Sequence[str]] = None,
) -> Optional[str]:
    from game.domain.status_fx import apply_status

    if not status_id:
        return None
    return apply_status(
        monster,
        str(status_id),
        reg,
        rng,
        chance=float(chance),
        source="combo",
        aoe=aoe,
        n_targets=n_targets,
        attack_elements=attack_elements,
    )


def apply_monster_hit_status(
    player: MutableMapping[str, Any],
    monster: Mapping[str, Any],
    profile: Mapping[str, Any],
    reg: Optional[DataRegistry],
    rng: random.Random,
) -> Optional[str]:
    """Monster attack may apply catalog status to player (resist applies)."""
    from game.domain.status_fx import try_apply_attack_status

    return try_apply_attack_status(
        player, monster, reg, rng, profile=profile, source="monster_hit"
    )


def resolve_victory(
    player: MutableMapping[str, Any],
    monster: Mapping[str, Any],
    reg: DataRegistry,
    area_id: str,
    rng: random.Random,
) -> List[str]:
    lines: List[str] = ["ชนะการต่อสู้!"]
    # CM: soft focus after victory (hidden)
    try:
        from game.domain.combo_mind import on_victory_focus

        fmsg = on_victory_focus(player, reg)
        if fmsg and rng.random() < 0.35:
            lines.append(fmsg)
    except Exception:
        pass
    # EQ-G: train stance affinity
    try:
        from game.domain.loadout_context import on_combat_victory_stance, recompute_loadout_context

        recompute_loadout_context(player, reg, area_id=area_id)
        for note in on_combat_victory_stance(player, reg):
            lines.append(note)
    except Exception:
        pass
    # N5: boss win at low morale
    try:
        if monster.get("boss"):
            from game.domain.needs import note_n5_morale_boss

            for note in note_n5_morale_boss(player):
                lines.append(note)
    except Exception:
        pass
    xp = kill_xp_reward(
        int(player.get("level", 1)),
        int(monster.get("level", 1)),
        float(monster.get("xp_mult", 1.0)),
        reg.levels,
    )
    wmod = float((player.get("world_modifiers") or {}).get("xp_mult", 1.0))
    xp = max(1, int(round(xp * wmod)))
    summary = grant_xp(player, xp, reg.levels)
    lines.append(
        f"ได้รับ XP +{summary['gained']} ({summary['xp']}/{summary['xp_needed']} · {summary['xp_percent']:.0f}%)"
    )
    for n in summary["notes"]:
        lines.append(n)
    try:
        from game.domain.stats import bump_stat

        bump_stat(player, "xp_gained_total", summary["gained"])
        bump_stat(player, "kills", 1)
        bump_stat(player, "combats", 1)
        if monster.get("boss"):
            bump_stat(player, "boss_kills", 1)
    except Exception:
        pass

    amt = rng.randint(10, 40) + int(monster.get("level", 1))
    money_m = float((player.get("world_modifiers") or {}).get("money_mult", 1.0))
    amt = max(1, int(round(amt * money_m)))
    kind = rng.choice(["world", "heaven", "hell"])
    if kind == "world":
        player["money_world"] = int(player.get("money_world", 0)) + amt
        lines.append(f"เงินโลก +{amt}")
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "money_gained_total", amt)
        except Exception:
            pass
    elif kind == "heaven":
        g = max(1, amt // 6)
        player["money_heaven"] = int(player.get("money_heaven", 0)) + g
        lines.append(f"เงินสวรรค์ +{g}")
    else:
        g = max(1, amt // 4)
        player["money_hell"] = int(player.get("money_hell", 0)) + g
        lines.append(f"เงินนรก +{g}")

    gain = 3 + int(player.get("mastery_gain_bonus", 0))
    am = dict(player.get("area_mastery") or {})
    am[area_id] = min(100, int(am.get(area_id, 0)) + gain)
    player["area_mastery"] = am
    player["pressure"] = min(100, int(player.get("pressure", 0)) + rng.randint(3, 10))

    know = dict(player.get("knowledge") or {})
    mons = dict(know.get("monsters") or {})
    entry = dict(mons.get(monster["id"]) or {"seen": True, "fought": 0, "won": 0})
    entry["seen"] = True
    entry["fought"] = int(entry.get("fought", 0)) + 1
    entry["won"] = int(entry.get("won", 0)) + 1
    entry["name"] = monster.get("name")
    mons[monster["id"]] = entry
    know["monsters"] = mons
    # journal reaction unlocks from last combat flavors stored on monster temp
    reactions = list(know.get("reactions") or [])
    for r in monster.get("_discovered_reactions") or []:
        if r not in reactions:
            reactions.append(r)
            lines.append(f"บันทึกความรู้: {r}")
    know["reactions"] = reactions
    player["knowledge"] = know

    # Item loot is chosen after combat (A / เลข,comma / 0) — no auto-grant here.
    # Track kills for mon-drop + chest anti_farm soft
    try:
        from game.domain.chest_loot import note_kill_for_farm

        note_kill_for_farm(player, str(monster.get("id") or ""))
    except Exception:
        pass
    # L2: sealed chest drop (boss likely · normal mon rare)
    try:
        from game.domain.chest_loot import (
            infer_combat_source,
            try_drop_and_grant_chest,
        )

        src = infer_combat_source(monster)
        first = False
        mid = str(monster.get("id") or "")
        if monster.get("boss") and mid:
            cleared = list(player.get("bosses_defeated") or [])
            # first clear if not yet in list before this fight's append below
            first = mid not in cleared
        chest_lines = try_drop_and_grant_chest(
            player,
            reg,
            rng,
            source=src,
            mon=dict(monster),
            first_clear=first,
            auto_open=False,
        )
        lines.extend(chest_lines)
    except Exception:
        pass

    ac = dict(player.get("action_counts") or {})
    ac["attack"] = int(ac.get("attack", 0)) + 1
    player["action_counts"] = ac
    skills = list(player.get("skills") or [])
    if ac["attack"] >= 8 and "fire_ball" not in skills and rng.random() < 0.35:
        skills.append("fire_ball")
        lines.append("ปลดสกิลใหม่: ลูกไฟ")
    if "water_bolt" not in skills and rng.random() < 0.12:
        skills.append("water_bolt")
        lines.append("ปลดสกิล: กระสุนน้ำ")
    if "wind_slash" not in skills and int(player.get("level", 1)) >= 3 and rng.random() < 0.15:
        skills.append("wind_slash")
        lines.append("ปลดสกิล: ลมบาด")
    if "lightning_spark" not in skills and int(player.get("level", 1)) >= 5 and rng.random() < 0.12:
        skills.append("lightning_spark")
        lines.append("ปลดสกิล: ประกายสายฟ้า")
    if "guard_water_veil" not in skills and ac.get("defend", 0) >= 4 and rng.random() < 0.4:
        skills.append("guard_water_veil")
        lines.append("เรียนรู้ท่าป้องกัน: ม่านน้ำ")
    if area_id == "cave_shadow" and int(player.get("pressure", 0)) >= 30:
        if "shadow_step" in reg.skills and "shadow_step" not in skills and rng.random() < 0.25:
            skills.append("shadow_step")
            lines.append("ปลดสกิล: ก้าวเงา")
    player["skills"] = skills
    return lines


def combo_damage_package(
    player: Mapping[str, Any],
    monster: Mapping[str, Any],
    reg: DataRegistry,
    area_id: str,
    skill_ids: Sequence[str],
    rng: random.Random,
) -> Dict[str, Any]:
    from game.domain.combo import max_combo_for_player
    from game.domain.unit_system import apply_unit_skill_scaling, gain_unit_mastery_xp

    max_n = max_combo_for_player(player, reg)
    combo = resolve_combo(skill_ids, reg, max_n=max_n, player=player)
    if not combo.get("ok"):
        return combo

    # scale unit_only skills in chain by mastery
    skills = list(combo.get("skills") or [])
    if len(skills) == 1 and skills[0].get("unit_only"):
        p, mcost = apply_unit_skill_scaling(
            player,
            skills[0],
            int(combo.get("power") or skills[0].get("power") or 0),
            int(combo.get("total_mana") or skills[0].get("cost_mana") or 0),
            reg=reg,
        )
        combo["power"] = p
        combo["total_mana"] = mcost
        if skills[0].get("heal"):
            heal = int(skills[0].get("heal") or 0)
            heal = int(round(heal * (p / max(1, int(skills[0].get("power") or p or 1)))))
            combo["heal"] = max(1, heal)

    if combo.get("heal") and not combo.get("power"):
        return combo
    if combo.get("heal") and len(skills) == 1:
        return combo

    fake = {
        "power": combo["power"],
        "elements": combo["elements"],
        "name": combo["flavor"],
    }
    dmg, flavor = player_attack_damage(
        player,
        monster,
        reg,
        area_id,
        fake,
        rng,
        power_override=combo["power"],
        elements_override=combo["elements"],
    )
    combo["damage"] = dmg
    combo["flavor_tag"] = flavor
    # mastery xp when using unit skill
    if any(s.get("unit_only") for s in skills):
        notes = list(gain_unit_mastery_xp(player, 2, "unit_skill") or [])
        try:
            from game.domain.soft_feel import soft_unit_combat_feel

            for s in skills:
                if s.get("unit_only"):
                    notes.extend(soft_unit_combat_feel(player, s, int(dmg), reg=reg))
        except Exception:
            pass
        combo["mastery_notes"] = notes  # type: ignore
    elif int(combo.get("length") or 1) >= 3:
        combo["mastery_notes"] = gain_unit_mastery_xp(player, 1, "long_combo")  # type: ignore
    return combo
