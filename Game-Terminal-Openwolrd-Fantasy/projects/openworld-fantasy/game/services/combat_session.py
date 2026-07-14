"""Turn combat session — ATB gauges, player/enemy acts when full, loot, soft death."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from game.data_load.registry import DataRegistry
from game.domain.balance import apply_soft_death
from game.domain.boss import check_phase_transition
from game.domain.combo import (
    apply_defense,
    apply_player_defense_stat,
    defense_skills,
    max_combo_for_player,
    parse_combo_input,
    preview_combo_mana,
)
from game.domain.combat import (
    apply_incoming_damage,
    apply_monster_hit_status,
    apply_on_hit_cards,
    apply_status_to_monster,
    apply_world_enemy_mods,
    combo_damage_package,
    monster_raw_damage,
    pick_monster,
    pick_monster_attack,
    player_attack_damage,
    resolve_victory,
    skill_options,
)
from game.domain.combat_atb import (
    advance_until_ready,
    advance_until_ready_multi,
    format_pack_atb_strip,
    init_combat_atb,
    init_pack_atb,
    spend_action,
)
from game.domain.dungeon import (
    apply_dungeon_enemy_mods,
    exit_dungeon,
    get_run,
    in_dungeon,
    note_dungeon_fight,
    on_dungeon_boss_defeated,
)
from game.domain.encounters import mark_monster_seen
from game.domain.inventory_sys import (
    build_combat_loot_table,
    present_loot_choices,
    resolve_loot_pick,
)
from game.domain.narrative import (
    emit_narrative,
    narrate,
    narrate_battle_open,
    narrate_damage_in,
    narrate_damage_out,
    narrate_field,
    narrate_low_hp_warnings,
    narrate_player_action,
    situation_strip,
    status_display_name,
)
from game.domain.party import (
    call_party_power,
    clear_party_call_buffs,
    ensure_party,
    party_assist_damage,
)
from game.domain.personality import (
    apply_event as personality_event,
    check_personality_point_grants,
)
from game.domain.quests import bump_quest, ensure_quests
from game.domain.skill_charges import format_charge_hint, spend_charges
from game.domain.stats import bump_stat, ensure_stats
from game.domain.status_fx import process_status_turn, should_skip_action
from game.domain.unit_system import gain_unit_mastery_xp
from game.ports.io import IO
from game.services.consumables import _combat_quick_cleanse, _use_potion
from game.ui_terminal.panels import soft_death_panel, soft_enemy_vitality, victory_panel
from game.ui_terminal.spotlight import level_up_banner, spotlight
from game.ui_terminal.status import render_combat_vitals, render_mode_chrome


def _emit_personality_notes(io: IO, notes: Optional[List[str]]) -> None:
    if not notes:
        return
    for n in notes:
        if n:
            io.write_line(n)


def _monster_act(
    player: Dict[str, Any],
    mon: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    *,
    known: bool,
    enemy_name: str,
) -> Optional[str]:
    """One enemy action when their ATB is full.

    Returns ``\"fled\"`` if MI2 soft-escape ends the engagement for this foe.
    """
    if should_skip_action(mon, reg, rng):
        emit_narrative(io, narrate(reg, "status_tick_freeze", rng, enemy=enemy_name))
        io.write_line("  ศัตรูถูกล็อกสถานะ — ข้ามการโจมตี!")
        tick = process_status_turn(mon, reg, rng, apply_dot=True, min_hp=0)
        if tick.damage:
            io.write_line(f"  [ตัวเลข] สถานะศัตรู −{tick.damage} HP")
        return None

    # MI2: smart elite may soft-flee before swinging when HP is low
    try:
        from game.domain.monster_ai import try_monster_flee

        fled, flee_msg = try_monster_flee(mon, player, rng)
        if fled:
            nlines = narrate(reg, "enemy_flee", rng, enemy=enemy_name)
            if nlines:
                emit_narrative(io, nlines)
            elif flee_msg:
                io.write_line(f"  {flee_msg}")
            else:
                io.write_line(f"  {enemy_name} ถอย…")
            io.write_line("  (ศัตรูถอย — ไม่มีดรอปจากร่าง)")
            ac = dict(player.get("action_counts") or {})
            ac["enemy_fled"] = int(ac.get("enemy_fled", 0)) + 1
            player["action_counts"] = ac
            return "fled"
    except Exception:
        pass

    hits = max(1, int(mon.get("extra_hits") or 1))
    guard_skill = None
    for hit_i in range(hits):
        if int(player.get("hp") or 0) <= 0:
            break
        profile = pick_monster_attack(mon, rng, player=player)
        tags = list(profile.get("tags") or mon.get("elements") or ["physical"])
        raw = monster_raw_damage(mon, profile, rng)
        raw, dodge_fl = apply_incoming_damage(player, raw, rng)
        if hit_i == 0:
            emit_narrative(
                io,
                narrate(
                    reg,
                    "enemy_telegraph",
                    rng,
                    telegraph=profile.get("telegraph", "ศัตรูโจมตี!"),
                    enemy=enemy_name,
                ),
            )
            if hits > 1:
                io.write_line(f"  (โจมตีซ้ำ {hits} ครั้ง)")
            from game.domain.guard_groups import (
                format_guard_group_box_lines,
                group_menu_rows,
                pick_skill_in_group,
            )
            from game.ui_terminal.layout import render_box

            # DD2: soft groups กันกาย / กันเวท / กันธาตุ (no skill ids)
            g_lines = format_guard_group_box_lines(player, reg)
            io.write_line()
            io.write_line(render_box(g_lines, double=False))
            gch = io.read_line("\n  กัน (เลข · 0): ").strip()
            if gch not in ("0", ""):
                try:
                    rows = group_menu_rows(player, reg)
                    gi = int(gch) - 1
                    if 0 <= gi < len(rows):
                        group_key = str(rows[gi]["key"])
                        skills = list(rows[gi].get("skills") or [])
                        # de-dupe sid
                        seen_s = set()
                        uniq_sk = []
                        for sid, sk in skills:
                            if sid in seen_s:
                                continue
                            seen_s.add(sid)
                            uniq_sk.append((sid, sk))
                        skill_index = None
                        if len(uniq_sk) > 1:
                            # soft sub-pick by flavor name only
                            sub = [
                                f" {rows[gi]['label']} — เลือกท่า",
                                "---",
                            ]
                            for j, (sid, sk) in enumerate(uniq_sk, 1):
                                cost = int(sk.get("cost_mana") or 0)
                                sub.append(
                                    f"  {j}  {sk.get('name', sid)}   "
                                    f"(MP {cost})"
                                )
                            sub.extend(["---", "  0  ใช้ท่าที่เบาที่สุด"])
                            io.write_line()
                            io.write_line(render_box(sub, double=False))
                            sub_ch = io.read_line("\n  ท่า (เลข · 0=เบา): ").strip()
                            if sub_ch not in ("0", ""):
                                try:
                                    skill_index = int(sub_ch) - 1
                                except Exception:
                                    skill_index = None
                        picked = pick_skill_in_group(
                            player, reg, group_key, skill_index=skill_index
                        )
                        if not picked:
                            io.write_line(" ไม่มีท่าในกลุ่มนี้")
                            guard_skill = None
                        else:
                            _sid, guard_skill = picked
                            # SK-R1/R2: rank-scale defense skill mana/reflect/counter
                            try:
                                from game.domain.skill_rank import scale_skill_for_player
                                from game.domain.skill_slots import arm_defense_stance

                                guard_skill = scale_skill_for_player(
                                    player, guard_skill, reg, skill_id=str(_sid)
                                )
                                guard_skill["id"] = _sid
                            except Exception:
                                pass
                            cost = int(guard_skill.get("cost_mana", 0))
                            if int(player["mana"]) < cost:
                                io.write_line(" มานาไม่พอ — กันไม่ได้")
                                guard_skill = None
                            else:
                                player["mana"] = int(player["mana"]) - cost
                                ac = dict(player.get("action_counts") or {})
                                ac["defend"] = int(ac.get("defend", 0)) + 1
                                player["action_counts"] = ac
                                personality_event(player, "combat_defend", reg)
                                try:
                                    from game.domain.skill_slots import arm_defense_stance

                                    for n in arm_defense_stance(player, guard_skill):
                                        if n and ("สะท้อน" in n or "สวน" in n):
                                            io.write_line(f"  {n}")
                                except Exception:
                                    pass
                except Exception:
                    guard_skill = None
        from game.domain.damage_class import resolve_damage_class

        atk_class = resolve_damage_class(profile, tags=tags, reg=reg)
        final, grade, gmsg = apply_defense(
            raw, tags, guard_skill, damage_class=atk_class, reg=reg
        )
        final, def_fl = apply_player_defense_stat(
            final, player, attack_tags=tags, damage_class=atk_class, reg=reg
        )
        player["hp"] = int(player["hp"]) - final
        if dodge_fl:
            io.write_line(f"  {dodge_fl.strip()}")
        if def_fl:
            io.write_line(f"  {def_fl.strip()}")
        emit_narrative(
            io,
            narrate_damage_in(
                reg,
                final,
                int(player.get("max_hp") or 100),
                enemy_name,
                rng,
                guard_grade=str(grade or "none"),
            ),
        )
        io.write_line(f"  [ตัวเลข] ดาเมจเข้า {final}" + (f" · {gmsg}" if gmsg else ""))
        # SK-R1: reflect / counter after taking a hit
        try:
            from game.domain.skill_slots import consume_defense_stance_on_hit

            extra, rnotes = consume_defense_stance_on_hit(player, mon, final, rng)
            for n in rnotes:
                io.write_line(f"  {n}")
            if extra and int(mon.get("hp") or 0) <= 0:
                io.write_line("  ศัตรูล้มจากสะท้อน/สวน!")
        except Exception:
            pass
        hit_note = apply_monster_hit_status(player, mon, profile, reg, rng)
        if hit_note:
            io.write_line(f"  {hit_note}")
        else:
            # DD4 soft resist flavor (no %)
            try:
                from game.domain.status_fx import format_last_resist_note

                rnote = format_last_resist_note(player)
                if rnote:
                    io.write_line(f"  {rnote}")
            except Exception:
                pass

    m_tick = process_status_turn(mon, reg, rng, apply_dot=True, min_hp=0)
    if m_tick.damage:
        io.write_line(f"  [ตัวเลข] สถานะศัตรู −{m_tick.damage} HP")
    p_tick = process_status_turn(player, reg, rng, apply_dot=True, min_hp=1)
    if p_tick.damage:
        io.write_line(f"  [ตัวเลข] สถานะคุณ −{p_tick.damage} HP")
    return None


def _apply_splash_damage(
    io: IO,
    primary_dmg: int,
    splash: Optional[List[Dict[str, Any]]],
    *,
    mult: float,
    reg: DataRegistry,
    rng: random.Random,
    aoe_skill: bool = False,
) -> None:
    """Hit secondary foes for reduced damage (multi-target / AoE)."""
    from game.domain.aoe_balance import (
        apply_soft_splash_kill_flag,
        splash_damage_mult,
    )

    if not splash or primary_dmg <= 0:
        return
    living = [s for s in splash if int(s.get("hp") or 0) > 0]
    if not living:
        return
    # diminishing by pack size; never exceed requested mult
    eff = min(
        mult,
        splash_damage_mult(n_splash=len(living), aoe_skill=aoe_skill),
    )
    for s in living:
        sd = max(1, int(round(primary_dmg * eff)))
        s["hp"] = int(s.get("hp") or 0) - sd
        nm = str(s.get("name") or "???")
        io.write_line(f"  › กระแสโดน {nm} → {sd}")
        if int(s.get("hp") or 0) <= 0:
            apply_soft_splash_kill_flag(s)
            io.write_line(f"  › {nm} ล้มจากกระแส (รางวัลแผ่ว)")


def _player_act(
    player: Dict[str, Any],
    mon: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    *,
    area_id: str,
    known: bool,
    enemy_name: str,
    combat_round: int,
    splash: Optional[List[Dict[str, Any]]] = None,
    splash_mult: float = 0.52,
    pack_foes: Optional[List[Dict[str, Any]]] = None,
) -> Optional[bool]:
    """
    Player command when ATB full.
    Returns True if acted, False if cancelled, None if fled.
    splash: other living foes for multi-target / AoE reduced hits.
    """
    from game.domain.aoe_balance import splash_damage_mult

    io.write_line()
    io.write_line(
        render_combat_vitals(
            player,
            mon,
            known=known,
            situation=situation_strip(player, mon, known=known, reg=reg),
            round_no=combat_round,
        )
    )
    max_combo = max_combo_for_player(player, reg)
    from game.domain.mode_shell import MODE_COMBAT, render_mode_actions
    from game.ui_terminal.layout import render_box

    io.write_line()
    io.write_line(render_mode_actions(MODE_COMBAT))
    meta: List[str] = [" เงื่อนไขเทิร์น", "---"]
    if splash:
        n_sp = len([s for s in splash if int(s.get("hp") or 0) > 0])
        eff = splash_damage_mult(n_splash=n_sp, aoe_skill=False)
        eff = min(eff, splash_mult)
        splash_mult = eff
        meta.append(f" หลายเป้า  หลัก + กระแส {n_sp} ตัว (แผ่วเมื่อฝูงใหญ่)")
    try:
        from game.domain.intelligence import format_intel_status_line, ensure_intelligence

        ensure_intelligence(player, reg)
        meta.append(f" {format_intel_status_line(player).strip()}")
    except Exception:
        pass
    meta.append(f" คอมโบสูงสุด  {max_combo} ขั้น · มานาไม่พอใช้โซ่ไม่ได้")
    try:
        from game.domain.combo_mind import ensure_focus_latent, soft_combo_mind_hint

        ensure_focus_latent(player, reg)
        meta.append(f" {soft_combo_mind_hint(player, reg)}")
    except Exception:
        pass
    try:
        from game.domain.monster_ai import talk_eligible

        if talk_eligible(mon) and not mon.get("_parley_used"):
            meta.append(" เจรจา soft  7 · บางศัตรู · ครั้งเดียว")
    except Exception:
        pass
    io.write_line()
    io.write_line(render_box(meta, double=False))
    ch = io.read_line("\n  〔ไฟต์〕 เลือก (1–7): ").strip()

    try:
        from game.domain.skill_slots import begin_player_action

        begin_player_action(player)
    except Exception:
        pass

    if ch == "1":
        skill = {"power": 8, "elements": ["physical"], "name": "โจมตีปกติ"}
        emit_narrative(
            io,
            narrate_player_action(
                reg, "basic", rng, enemy=enemy_name, skill=skill["name"]
            ),
        )
        dmg, flavor = player_attack_damage(player, mon, reg, area_id, skill, rng)
        crit = "คริ" in flavor
        reflect = float(mon.get("reflect_pct") or 0)
        if reflect > 0:
            back = max(1, int(dmg * reflect))
            player["hp"] = int(player["hp"]) - back
            emit_narrative(io, narrate(reg, "reflect", rng, dmg=back, enemy=enemy_name))
        mon["hp"] = int(mon["hp"]) - dmg
        emit_narrative(
            io,
            narrate_damage_out(
                reg,
                dmg,
                int(mon.get("max_hp") or 1),
                enemy_name,
                rng,
                elements=skill.get("elements"),
                crit=crit,
            ),
        )
        io.write_line(f"  [ตัวเลข] ดาเมจ {dmg}{flavor}")
        io.write_line(f"  {soft_enemy_vitality(mon, known=known)}")
        _apply_splash_damage(
            io, dmg, splash, mult=splash_mult, reg=reg, rng=rng, aoe_skill=False
        )
        for note in apply_on_hit_cards(player, mon, rng, reg):
            io.write_line(f"  {note}")
        from game.domain.party import party_member_turns

        for note in party_member_turns(player, mon, rng, reg):
            io.write_line(note)
        for note in gain_unit_mastery_xp(player, 1, "basic_attack"):
            io.write_line(note)
        emit_narrative(io, narrate_low_hp_warnings(reg, player, mon, enemy_name, rng))
        phase_msg = check_phase_transition(mon, rng)
        if phase_msg:
            io.write_line(phase_msg)
        ac = dict(player.get("action_counts") or {})
        ac["attack"] = int(ac.get("attack", 0)) + 1
        player["action_counts"] = ac
        personality_event(player, "combat_attack", reg)
        return True

    if ch == "2":

        opts = skill_options(player, reg)
        if not opts:
            io.write_line("ไม่มีสกิล")
            return False
        for i, (sid, sk) in enumerate(opts, 1):
            cost = int(sk.get("cost_mana", 0))
            flag = "" if sk.get("combo_ok", True) else " [ไม่เข้าคอมโบ]"
            aoe = " [AoE]" if sk.get("aoe") else ""
            chg = format_charge_hint(player, sid, reg)
            slot = str(sk.get("slot") or "combat")
            slot_tag = {
                "buff": " [บัฟ]",
                "debuff": " [ดีบัฟ]",
                "support": " [ซัพ]",
                "combat": "",
            }.get(slot, "")
            rank_lab = sk.get("_rank_label") or ""
            rank_bit = f" ·{rank_lab}" if rank_lab and rank_lab != "ธรรมดา" else ""
            io.write_line(
                f"  {i}. {sk.get('name', sid)}{chg}{slot_tag}{rank_bit} (MP {cost}){flag}{aoe}"
            )
        io.write_line(f"  พิมพ์หมายเลขเดียว หรือคอมโบ เช่น 2,1,3 (สูงสุด {max_combo})")
        raw = io.read_line("สกิล: ").strip()
        idxs = parse_combo_input(raw, max_n=max_combo)
        if not idxs:
            try:
                idxs = [int(raw)]
            except Exception:
                io.write_line("ยกเลิก")
                return False
        skill_ids = []
        for ix in idxs:
            if 1 <= ix <= len(opts):
                skill_ids.append(opts[ix - 1][0])
        if not skill_ids:
            io.write_line("เลือกไม่ถูกต้อง")
            return False
        if len(skill_ids) > max_combo:
            try:
                from game.domain.combo_mind import soft_combo_too_long_message

                io.write_line(
                    soft_combo_too_long_message(
                        player, len(skill_ids), max_combo, reg
                    )
                )
            except Exception:
                io.write_line(f"ตอนนี้เรียงได้สูงสุด {max_combo} ขั้น")
            return False
        # N2: morale — block focus skills / soft fail
        try:
            from game.domain.needs import skill_blocked_by_morale, skill_fail_chance

            for sid in skill_ids:
                sk = reg.skills.get(sid) or {}
                if skill_blocked_by_morale(player, sk):
                    io.write_line("ขวัญย่ำแย่ — สกิลสมาธิไม่ยอมทำงาน")
                    return True  # spend turn soft
            if rng.random() < skill_fail_chance(player):
                # still pay half mana if affordable, miss effect
                prev0 = preview_combo_mana(player, reg, skill_ids)
                cost0 = int(prev0.get("total_mana", 0)) // 2
                if int(player.get("mana") or 0) >= cost0:
                    player["mana"] = int(player["mana"]) - cost0
                io.write_line("จังหวะหลุด… ขวัญยังไม่นิ่ง — สกิลพลาด")
                return True
        except Exception:
            pass
        prev = preview_combo_mana(player, reg, skill_ids)
        cost = int(prev.get("total_mana", 0))
        if prev.get("ok") and not prev.get("can_afford", True):
            try:
                from game.domain.combo_mind import soft_combo_mana_fail_message

                io.write_line(
                    soft_combo_mana_fail_message(
                        player,
                        cost,
                        int(player.get("mana") or 0),
                        reg,
                        length=len(skill_ids),
                    )
                )
            except Exception:
                io.write_line(
                    f"มานาไม่พอสำหรับลูกโซ่นี้ (ต้องการ {cost} · มี {player.get('mana')})"
                )
            return False
        combo = combo_damage_package(player, mon, reg, area_id, skill_ids, rng)
        if not combo.get("ok"):
            io.write_line("คอมโบใช้ไม่ได้")
            return False
        cost = int(combo.get("total_mana", 0))
        if int(player["mana"]) < cost:
            try:
                from game.domain.combo_mind import soft_combo_mana_fail_message

                io.write_line(
                    soft_combo_mana_fail_message(
                        player,
                        cost,
                        int(player.get("mana") or 0),
                        reg,
                        length=int(combo.get("length") or len(skill_ids)),
                    )
                )
            except Exception:
                io.write_line(f"มานาไม่พอ (ต้องการ {cost})")
            return False
        # SK-R1: buff gate before paying (anti stack)
        try:
            from game.domain.skill_slots import can_cast_buff, normalize_slot

            for sid in skill_ids:
                sk0 = reg.skills.get(sid) or {}
                if normalize_slot(sk0) == "buff":
                    ok_b, why_b = can_cast_buff(player, sk0)
                    if not ok_b:
                        io.write_line(f"  {why_b}")
                        return False
        except Exception:
            pass
        player["mana"] = int(player["mana"]) - cost
        skill_label = str(combo.get("flavor") or "สกิล")
        length = int(combo.get("length") or 1)
        # CM: focus drift after long chains · fusion trains mind soft
        try:
            from game.domain.combo_mind import note_mind_growth, on_combo_resolved

            fnote = on_combo_resolved(player, length, reg)
            if fnote and length >= 3:
                io.write_line(f"  …{fnote}")
            # fusion flavor often contains ! / หลอม — soft train intellect
            flav = str(combo.get("flavor") or "")
            if length >= 2 and (
                "!" in flav
                or "หลอม" in flav
                or "น้ำแข็ง" in flav
                or "ไอน้ำ" in flav
                or "สายฟ้า" in flav
                or combo.get("status")
            ):
                mnote = note_mind_growth(player, 0.22, reason="fusion")
                if mnote:
                    io.write_line(f"  …{mnote}")
            elif length >= 3:
                mnote = note_mind_growth(player, 0.12, reason="combo")
                if mnote:
                    io.write_line(f"  …{mnote}")
        except Exception:
            pass
        # AoE skills expand splash to all other living pack members
        use_splash = list(splash or [])
        use_mult = splash_mult
        is_aoe = any((reg.skills.get(sid) or {}).get("aoe") for sid in skill_ids)
        if pack_foes and is_aoe:
            use_splash = [
                f
                for f in pack_foes
                if f is not mon and int(f.get("hp") or 0) > 0
            ]
            use_mult = splash_damage_mult(
                n_splash=len(use_splash), aoe_skill=True
            )
            if use_splash:
                io.write_line("  ✦ สกิล AoE — กระแสโดนทั้งกลุ่ม (แผ่วตามจำนวน)")
        if length >= 2:
            emit_narrative(
                io,
                narrate_player_action(
                    reg, "combo", rng, skill=skill_label, length=length, enemy=enemy_name
                ),
            )
        else:
            emit_narrative(
                io,
                narrate_player_action(
                    reg, "skill", rng, skill=skill_label, enemy=enemy_name
                ),
            )
        # SK-R1/R2: buff / debuff side effects + mastery tick
        try:
            from game.domain.skill_rank import note_skill_use_mastery, scale_skill_for_player
            from game.domain.skill_slots import (
                apply_buff_skill,
                apply_debuff_from_skill,
                normalize_slot,
            )

            for sid in skill_ids:
                base_sk = reg.skills.get(sid) or {}
                sk_u = scale_skill_for_player(player, base_sk, reg, skill_id=sid)
                slot = normalize_slot(sk_u)
                if slot == "buff":
                    for note in apply_buff_skill(player, sk_u, reg, rng):
                        io.write_line(f"  {note}")
                elif slot in ("debuff", "combat"):
                    for note in apply_debuff_from_skill(
                        mon, sk_u, reg, rng, aoe=bool(sk_u.get("aoe"))
                    ):
                        io.write_line(f"  {note}")
                mnote = note_skill_use_mastery(player, sid, reg, rng)
                if mnote:
                    io.write_line(f"  …{mnote}")
        except Exception:
            pass
        if combo.get("heal"):
            heal = int(combo["heal"])
            player["hp"] = min(int(player["max_hp"]), int(player["hp"]) + heal)
            io.write_line(f"  [ตัวเลข] ฟื้นฟู {heal} HP · MP -{cost}")
        elif int(combo.get("damage") or combo.get("power") or 0) <= 0 and length == 1:
            # pure buff / utility — already applied above
            io.write_line(f"  (ใช้ท่า · MP -{cost})")
        else:
            dmg = int(combo.get("damage") or combo.get("power") or 0)
            reflect = float(mon.get("reflect_pct") or 0)
            if reflect > 0:
                back = max(1, int(dmg * reflect))
                player["hp"] = int(player["hp"]) - back
            mon["hp"] = int(mon["hp"]) - dmg
            crit = "คริ" in str(combo.get("flavor_tag") or "")
            emit_narrative(
                io,
                narrate_damage_out(
                    reg,
                    dmg,
                    int(mon.get("max_hp") or 1),
                    enemy_name,
                    rng,
                    elements=list(combo.get("elements") or []),
                    crit=crit,
                ),
            )
            io.write_line(
                f"  [ตัวเลข] ดาเมจ {dmg}{combo.get('flavor_tag', '')} | MP -{cost} "
                f"({length} ขั้น)"
            )
            io.write_line(f"  {soft_enemy_vitality(mon, known=known)}")
            _apply_splash_damage(
                io,
                dmg,
                use_splash,
                mult=use_mult,
                reg=reg,
                rng=rng,
                aoe_skill=is_aoe,
            )
            n_foes = 1 + len(
                [s for s in (use_splash or []) if int(s.get("hp") or 0) > 0]
            )
            st = apply_status_to_monster(
                mon,
                combo.get("status"),
                float(combo.get("status_chance") or 0),
                rng,
                reg,
                aoe=bool(is_aoe),
                n_targets=n_foes if is_aoe else 1,
                attack_elements=list(combo.get("elements") or []),
            )
            if st:
                io.write_line(
                    f"  [สถานะ] {status_display_name(st, reg)} ติดที่ศัตรู"
                )
            elif combo.get("status") and float(combo.get("status_chance") or 0) > 0:
                try:
                    from game.domain.status_fx import format_last_resist_note

                    rnote = format_last_resist_note(mon)
                    if rnote:
                        io.write_line(f"  ศัตรู: {rnote}")
                except Exception:
                    pass
            for note in apply_on_hit_cards(player, mon, rng, reg):
                io.write_line(f"  {note}")
            from game.domain.party import party_member_turns

            for note in party_member_turns(player, mon, rng, reg):
                io.write_line(note)
            phase_msg = check_phase_transition(mon, rng)
            if phase_msg:
                io.write_line(phase_msg)
        ac = dict(player.get("action_counts") or {})
        ac["attack"] = int(ac.get("attack", 0)) + 1
        if length >= 2:
            bump_stat(player, "combos", 1)
        player["action_counts"] = ac
        for note in spend_charges(player, skill_ids):
            io.write_line(note)
        personality_event(
            player, "combat_combo" if length > 1 else "combat_attack", reg
        )
        return True

    if ch == "3":
        from game.ui_terminal.layout import render_box

        io.write_line()
        io.write_line(
            render_box(
                [
                    " ยา / ล้าง / บัฟ",
                    "---",
                    "  1  ใช้ของจากคลัง",
                    "  2  ล้างเร็ว",
                    "  0  กลับไฟต์",
                ],
                double=False,
            )
        )
        sub = io.read_line("\n  เลือก (1/2/0): ").strip()
        if sub in ("0", ""):
            return False
        if sub == "2":
            if not _combat_quick_cleanse(player, reg, io):
                return False
        else:
            if not _use_potion(player, io, reg):
                return False
        return True

    if ch == "4":
        chance = 40 + int(player.get("pressure", 0)) // 2
        chance += int(
            float((player.get("personality") or {}).get("caution", 0)) / 10
        )
        # ATB speed / luck soft on flee (hidden)
        chance += int(float(player.get("power_spd") or 0) / 8)
        chance += int(float(player.get("luck_score") or 0) * 20)
        if rng.randint(1, 100) < chance:
            emit_narrative(io, narrate(reg, "flee_success", rng, enemy=enemy_name))
            mark_monster_seen(player, mon)
            bump_stat(player, "flees", 1)
            clear_party_call_buffs(player)
            _emit_personality_notes(io, personality_event(player, "combat_flee", reg))
            return None
        emit_narrative(io, narrate(reg, "flee_fail", rng, enemy=enemy_name))
        return True

    if ch == "5":
        ensure_party(player)
        party = list(player.get("party") or [])
        if not party:
            io.write_line("ยังไม่มีสมาชิกปาร์ตี้")
            return False
        for i, m in enumerate(party, 1):
            io.write_line(f"  {i}. {m.get('name')} ({m.get('kind')})")
        try:
            pi = int(io.read_line("เรียกหมายเลข: ").strip()) - 1
        except Exception:
            return False
        ok, msg, _ = call_party_power(player, reg, pi)
        io.write_line(msg)
        return bool(ok)

    if ch == "6":
        # Spend intelligence to surge ATB — does not consume the turn if already full
        # If already full, allow pre-bank surge for next cycle only when not full
        from game.domain.intelligence import spend_intel_for_atb

        conf = io.read_line("ใช้สติเร่งจังหวะ? (y/n · สติจะลด): ").strip().lower()
        if conf not in ("y", "yes", "ใช่", "1"):
            io.write_line("ยกเลิก")
            return False
        ok, msg = spend_intel_for_atb(player, reg, rng)
        io.write_line(msg)
        if not ok:
            return False
        # If still not "action" this beat (gauge was partial) — free action spent intel only
        # If gauge was already full, still costs intel for next surge buff only
        return True

    if ch == "7":
        # MI3 mid-fight soft parley — once per combat, smart foes only
        from game.domain.monster_ai import (
            apply_talk_rewards,
            resolve_monster_talk,
            talk_eligible,
        )

        if mon.get("_parley_used"):
            io.write_line("  เจรจาไปแล้วในไฟต์นี้ — มันไม่ฟังอีก")
            return False
        if not talk_eligible(mon):
            io.write_line("  ศัตรูนี้ไม่ฟังภาษา — เจรจาไม่ได้")
            return False
        mon["_parley_used"] = True
        io.write_line("  คุณลดท่าทาง — พยายามสื่อสารกลางวงรบ…")
        io.write_line("  1 สงบ  2 ของขวัญ  3 ข่ม  4 เลิก")
        sub = io.read_line("  เจรจา: ").strip()
        style_map = {"1": "calm", "2": "gift", "3": "threaten", "4": "walk"}
        style = style_map.get(sub, "calm")
        if sub in ("0", "4", ""):
            io.write_line("  เลิกเจรจา — ยังอยู่ในวงรบ")
            return True  # spent attempt / turn soft
        outcome, lines = resolve_monster_talk(mon, player, style, rng, reg=reg)
        for line in lines:
            if line:
                io.write_line(f"  {line}" if not str(line).startswith(" ") else line)
        if outcome in ("combat", "ambush"):
            io.write_line("  มันไม่ยอม — วงรบดำเนินต่อ (เสียจังหวะ)")
            return True
        if outcome == "flee":
            mon["hp"] = 0
            mon["_escaped"] = True
            for note in apply_talk_rewards(player, mon, "flee", rng, reg=reg):
                io.write_line(note)
            mark_monster_seen(player, mon)
            io.write_line("  (ศัตรูถอยกลางไฟต์ — ไม่มีดรอป)")
            clear_party_call_buffs(player)
            return None  # end fight like player flee path? need mon dead-ish
        # truce / tip / tribute / walk mid-fight: soft leave if truce-like
        if outcome in ("truce", "tip", "tribute", "walk"):
            for note in apply_talk_rewards(player, mon, outcome, rng, reg=reg):
                io.write_line(note)
            if outcome in ("truce", "tip", "tribute"):
                mon["hp"] = 0
                mon["_escaped"] = True
                mark_monster_seen(player, mon)
                io.write_line("  วงรบคลาย — ไม่ฆ่าจบ (ไม่มีดรอปเต็ม)")
                clear_party_call_buffs(player)
                return None
            return True
        return True

    io.write_line("ไม่ถูกต้อง")
    return False


def _run_combat(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    mon: Optional[Dict[str, Any]] = None,
    ambush: bool = False,
) -> None:
    area_id = str(player.get("location"))
    spawn_area = area_id
    if in_dungeon(player):
        run = get_run(player) or {}
        spawn_area = str(
            run.get("area_id")
            or player.get("location_before_dungeon")
            or "dark_forest"
        )
        area_id = spawn_area
    if mon is None:
        mon = pick_monster(reg, spawn_area, rng)
    mon = apply_world_enemy_mods(mon, player)
    if in_dungeon(player):
        mon = apply_dungeon_enemy_mods(mon, player)
        note_dungeon_fight(player)
    bump_stat(player, "combats", 0)
    ensure_stats(player)
    player["_combat_round"] = 0
    know = (player.get("knowledge") or {}).get("monsters") or {}
    known = mon["id"] in know and int(know[mon["id"]].get("fought", 0)) > 0
    display = mon["name"] if known else "???"
    enemy_name = str(display)
    rtag = ""
    if known and mon.get("rarity"):
        try:
            from game.domain.rarity import format_rarity_tag

            rtag = " " + format_rarity_tag(reg, str(mon.get("rarity")))
        except Exception:
            pass

    io.write_line()
    io.write_line(render_mode_chrome("ไฟต์", f"{enemy_name}{rtag}"))
    emit_narrative(io, narrate_battle_open(reg, enemy_name, rng, ambush=ambush))
    if known:
        tier = (
            "สูง"
            if mon["level"] >= player["level"] + 3
            else ("กลาง" if mon["level"] >= player["level"] else "พอไหว?")
        )
        io.write_line(f"   {mon['name']} · ความรู้สึก: {tier}")
        try:
            from game.domain.monster_ai import soft_intel_hint

            hint = soft_intel_hint(mon, known=True)
            if hint:
                io.write_line(hint)
        except Exception:
            pass

    # Ambush: enemy strikes once before ATB loop
    if ambush and mon["hp"] > 0 and player["hp"] > 0:
        profile = pick_monster_attack(mon, rng, player=player)
        raw = monster_raw_damage(mon, profile, rng)
        raw, dodge_fl = apply_incoming_damage(player, raw, rng)
        emit_narrative(
            io,
            narrate(
                reg,
                "enemy_telegraph",
                rng,
                telegraph=profile.get("telegraph", "โจมตี!"),
                enemy=enemy_name,
            ),
        )
        player["hp"] = int(player["hp"]) - raw
        if dodge_fl:
            io.write_line(f"  {dodge_fl.strip()}")
        emit_narrative(
            io,
            narrate_damage_in(
                reg,
                raw,
                int(player.get("max_hp") or 100),
                enemy_name,
                rng,
                guard_grade="none",
            ),
        )
        io.write_line(f"  [ตัวเลข] ดาเมจเข้า {raw} (ยังไม่ทันป้องกัน)")

    init_combat_atb(player, mon, reg, rng, ambush=ambush)
    from game.ui_terminal.layout import render_box as _rb

    io.write_line()
    io.write_line(
        _rb(
            [
                " จังหวะ ATB",
                "---",
                " แท่งเต็มก่อนเลือกคำสั่ง",
                " ความเร็วแต่ละฝ่ายไม่เท่ากัน · สูตรซ่อน",
            ],
            double=False,
        )
    )

    while int(mon.get("hp") or 0) > 0 and int(player.get("hp") or 0) > 0:
        ready = advance_until_ready(player, mon, reg, rng)
        combat_round = int(player.get("_combat_round", 0) or 0) + 1
        player["_combat_round"] = combat_round

        for actor in ready:
            if int(mon.get("hp") or 0) <= 0 or int(player.get("hp") or 0) <= 0:
                break
            if actor == "player":
                result = _player_act(
                    player,
                    mon,
                    reg,
                    io,
                    rng,
                    area_id=area_id,
                    known=known,
                    enemy_name=enemy_name,
                    combat_round=combat_round,
                )
                if result is None:
                    return  # fled
                if result:
                    spend_action(player)
                # cancelled: keep full gauge — re-advance next loop
                else:
                    # force re-prompt: keep atb full
                    player["atb"] = 100.0
            else:
                io.write_line()
                io.write_line(
                    render_combat_vitals(
                        player,
                        mon,
                        known=known,
                        situation=situation_strip(
                            player, mon, known=known, reg=reg
                        ),
                        round_no=combat_round,
                        banner=f"ศัตรูขยับ · จังหวะ {combat_round}",
                    )
                )
                mon_outcome = _monster_act(
                    player,
                    mon,
                    reg,
                    io,
                    rng,
                    known=known,
                    enemy_name=enemy_name,
                )
                if mon_outcome == "fled":
                    mark_monster_seen(player, mon)
                    clear_party_call_buffs(player)
                    io.write_line("  ไฟต์จบ — ศัตรูถอย (ยังไม่ถือว่าฆ่าจบ)")
                    return
                spend_action(mon)

    if int(player.get("hp") or 0) <= 0:
        clear_party_call_buffs(player)
        emit_narrative(
            io, narrate(reg, "defeat", rng, enemy=str(mon.get("name") or enemy_name))
        )
        _emit_personality_notes(io, personality_event(player, "combat_death", reg))
        try:
            from game.domain.needs import apply_needs_event

            for line in apply_needs_event(player, "combat_loss"):
                io.write_line(line)
        except Exception:
            pass
        death_msg = apply_soft_death(player, reg)
        io.write_line()
        io.write_line(soft_death_panel(death_msg))
        mark_monster_seen(player, mon)
        if in_dungeon(player):
            from game.domain.dungeon import drain_dungeon_resources

            io.write_line("สลบในดันเจียน — ร่างถูกเหวี่ยงออกมา...")
            for line in drain_dungeon_resources(player, reg, rng, reason="death"):
                io.write_line(line)
            for line in exit_dungeon(player, reg, success=False, escaped=True):
                io.write_line(line)
        return

    if int(mon.get("hp") or 0) <= 0:
        prev_lv = int(player.get("level", 1))
        try:
            from game.domain.needs import apply_needs_event

            for line in apply_needs_event(player, "combat_win"):
                io.write_line(line)
        except Exception:
            pass
        if mon.get("boss"):
            emit_narrative(
                io,
                narrate(
                    reg, "victory_boss", rng, enemy=str(mon.get("name") or enemy_name)
                ),
            )
        else:
            emit_narrative(
                io,
                narrate(reg, "victory", rng, enemy=str(mon.get("name") or enemy_name)),
            )
        _emit_personality_notes(io, personality_event(player, "combat_win", reg))
        victory_lines = resolve_victory(player, mon, reg, area_id, rng)
        io.write_line()
        # แผงรวม XP/เงิน/โน้ตครบ — ไม่ตัดทิ้ง 6 บรรทัดแรก
        io.write_line(victory_panel(victory_lines, title="ชนะการต่อสู้"))
        if in_dungeon(player) and mon.get("boss"):
            run = get_run(player) or {}
            if mon.get("id") == run.get("boss_id") or mon.get("dungeon_boss"):
                for line in on_dungeon_boss_defeated(player, reg, rng):
                    io.write_line(line)
        _emit_personality_notes(io, check_personality_point_grants(player, reg))
        loot = build_combat_loot_table(player, mon, reg, rng)
        if loot:
            emit_narrative(io, narrate_field(reg, "loot", rng))
            for line in present_loot_choices(loot):
                io.write_line(line)
            pick = io.read_line("เก็บ (A / 1,2 / 0): ").strip()
            notes = resolve_loot_pick(player, reg, loot, pick)
            if pick.strip().lower() in ("0", "", "n", "ไม่", "ทิ้ง"):
                emit_narrative(io, narrate_field(reg, "loot_leave", rng))
            for line in notes:
                io.write_line(line)
        else:
            io.write_line("ไม่พบของหล่น...")
        clear_party_call_buffs(player)
        for line in bump_quest(player, reg, "kill", area_id=area_id):
            io.write_line(line)
        try:
            from game.services.mission_service import try_complete_board_mission

            try_complete_board_mission(player, reg, io)
        except Exception:
            pass
        if mon.get("boss"):
            defeated = list(player.get("bosses_defeated") or [])
            if mon.get("id") not in defeated:
                defeated.append(mon["id"])
            player["bosses_defeated"] = defeated
            io.write_line(
                spotlight(
                    "BOSS DEFEATED",
                    [str(mon.get("name")), "เงาแห่งพื้นที่นี้สั่นคลอน..."],
                    art_id="level_up",
                    category="ui",
                )
            )
            for line in bump_quest(
                player, reg, "kill_boss", area_id=str(mon.get("id"))
            ):
                io.write_line(line)
        if int(player.get("level", 1)) > prev_lv:
            io.write_line(level_up_banner(int(player["level"])))
            ensure_quests(player, reg)


def format_enemy_pack_roster(
    pack: List[Dict[str, Any]],
    *,
    current: int = -1,
) -> List[str]:
    """Soft multi-enemy roster (simultaneous ATB — all present)."""
    n = len(pack)
    if n <= 0:
        return []
    alive = sum(1 for f in pack if int(f.get("hp") or 0) > 0)
    lines = [
        f" ⚔ กลุ่มศัตรู {n} ตัว · เหลือ {alive} — แท่งจังหวะพร้อมกัน · เลือกเป้าตอนโจมตี"
    ]
    for i, foe in enumerate(pack):
        mark = "▸" if i == current else "·"
        name = str(foe.get("name") or "???")
        hp = int(foe.get("hp") or 0)
        mx = max(1, int(foe.get("max_hp") or hp or 1))
        if hp <= 0:
            band = "ล้มแล้ว"
        else:
            r = hp / mx
            if r > 0.66:
                band = "ยังแข็ง"
            elif r > 0.33:
                band = "สะท้าน"
            else:
                band = "ใกล้พัง"
        ready = ""
        if hp > 0 and float(foe.get("atb") or 0) >= 100:
            ready = " · พร้อม"
        lines.append(f"  {mark} {i + 1}. {name} — {band}{ready}")
    return lines


def _alive_indices(foes: List[Dict[str, Any]]) -> List[int]:
    return [i for i, f in enumerate(foes) if int(f.get("hp") or 0) > 0]


def _select_target(
    io: IO,
    foes: List[Dict[str, Any]],
    *,
    known_map: Optional[Dict[int, bool]] = None,
) -> Optional[int]:
    """
    Pick living foe index.
    Returns -1 for ALL living (multi-target cleave).
    Single target auto; multi asks.
    """
    alive = _alive_indices(foes)
    if not alive:
        return None
    if len(alive) == 1:
        return alive[0]
    io.write_line(" เป้า (หลายตัว):")
    for i in alive:
        f = foes[i]
        known = (known_map or {}).get(i, False)
        label = f.get("name") if known else "???"
        io.write_line(
            f"  {i + 1}. {label} — {soft_enemy_vitality(f, known=known)}"
        )
    io.write_line("  * หรือ all = โจมตีทั้งกลุ่ม (ดาเมจกระแสลดลง)")
    raw = io.read_line("เลือกหมายเลขเป้า (Enter=ตัวแรก · *=ทั้งหมด): ").strip()
    if not raw:
        return alive[0]
    low = raw.lower()
    if low in ("*", "all", "a", "ทั้งกลุ่ม", "ทั้งหมด", "0"):
        return -1
    try:
        idx = int(raw) - 1
        if idx in alive:
            return idx
    except Exception:
        pass
    if low.startswith("mn"):
        try:
            idx = int(raw[2:]) - 1
            if idx in alive:
                return idx
        except Exception:
            pass
    io.write_line(" เป้าไม่ชัด — ใช้ตัวแรกที่ยังยืน")
    return alive[0]


def _on_foe_down(
    player: Dict[str, Any],
    mon: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    *,
    area_id: str,
) -> None:
    """Victory slice when one foe in a pack falls."""
    from game.domain.aoe_balance import is_soft_splash_kill, soft_splash_kill_xp_mult

    prev_lv = int(player.get("level", 1))
    enemy_name = str(mon.get("name") or "ศัตรู")
    soft = is_soft_splash_kill(mon)
    emit_narrative(io, narrate(reg, "victory", rng, enemy=enemy_name))
    mon_for_reward = dict(mon)
    if soft:
        # thinner XP — don't farm packs with one cleave
        mon_for_reward["xp_mult"] = float(mon.get("xp_mult") or 1.0) * soft_splash_kill_xp_mult()
        mon_for_reward["boss"] = False
    victory_lines = resolve_victory(player, mon_for_reward, reg, area_id, rng)
    title = f"ล้ม {enemy_name}" + (" · กระแส" if soft else "")
    io.write_line(victory_panel(victory_lines[:8], title=title))
    if soft:
        io.write_line("  (ล้มจากกระแส — รางวัลแผ่วกว่าโฟกัสเป้าเดียว)")
    mark_monster_seen(player, mon)
    for line in bump_quest(player, reg, "kill", area_id=area_id):
        io.write_line(line)
    try:
        from game.services.mission_service import try_complete_board_mission

        try_complete_board_mission(player, reg, io)
    except Exception:
        pass
    if int(player.get("level", 1)) > prev_lv:
        io.write_line(level_up_banner(int(player["level"])))
        ensure_quests(player, reg)


def _run_combat_multi(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    foes: List[Dict[str, Any]],
    *,
    ambush: bool = False,
) -> None:
    """Simultaneous multi-enemy ATB fight with target selection."""
    area_id = str(player.get("location"))
    if in_dungeon(player):
        run = get_run(player) or {}
        area_id = str(
            run.get("area_id")
            or player.get("location_before_dungeon")
            or "dark_forest"
        )
    for i, mon in enumerate(foes):
        foes[i] = apply_world_enemy_mods(dict(mon), player)
        if in_dungeon(player):
            foes[i] = apply_dungeon_enemy_mods(foes[i], player)
    if in_dungeon(player):
        note_dungeon_fight(player)
    ensure_stats(player)
    player["_combat_round"] = 0
    know = (player.get("knowledge") or {}).get("monsters") or {}
    known_map = {
        i: (
            str(f.get("id")) in know
            and int((know.get(str(f.get("id"))) or {}).get("fought", 0)) > 0
        )
        for i, f in enumerate(foes)
    }

    io.write_line()
    io.write_line(render_mode_chrome("ไฟต์", f"กลุ่ม {len(foes)}"))
    emit_narrative(io, narrate_battle_open(reg, "กลุ่มศัตรู", rng, ambush=ambush))
    for line in format_enemy_pack_roster(foes):
        io.write_line(line)

    if ambush and int(player.get("hp") or 0) > 0:
        # each living foe may swing once lightly
        for i, mon in enumerate(foes):
            if int(mon.get("hp") or 0) <= 0:
                continue
            if rng.random() > 0.65:
                continue
            profile = pick_monster_attack(mon, rng, player=player)
            raw = monster_raw_damage(mon, profile, rng)
            raw = max(1, int(raw * 0.75))
            raw, _ = apply_incoming_damage(player, raw, rng)
            player["hp"] = int(player["hp"]) - raw
            nm = mon.get("name") if known_map.get(i) else "???"
            io.write_line(f"  ซุ่มจาก {nm} → ดาเมจ {raw}")
            if int(player["hp"]) <= 0:
                break

    init_pack_atb(player, foes, reg, rng, ambush=ambush)
    io.write_line("  (ทุกตัวมีแท่งจังหวะ · เลือกหมายเลขเป้าเมื่อโจมตี)")
    io.write_line(format_pack_atb_strip(player, foes))

    last_loot_mon: Optional[Dict[str, Any]] = None
    while int(player.get("hp") or 0) > 0 and _alive_indices(foes):
        ready = advance_until_ready_multi(player, foes, reg, rng)
        combat_round = int(player.get("_combat_round", 0) or 0) + 1
        player["_combat_round"] = combat_round

        for side, idx in ready:
            if int(player.get("hp") or 0) <= 0 or not _alive_indices(foes):
                break
            if side == "player":
                io.write_line()
                for line in format_enemy_pack_roster(foes):
                    io.write_line(line)
                io.write_line(format_pack_atb_strip(player, foes))
                t_idx = _select_target(io, foes, known_map=known_map)
                if t_idx is None:
                    spend_action(player)
                    continue
                alive_before = set(_alive_indices(foes))
                splash: Optional[List[Dict[str, Any]]] = None
                from game.domain.aoe_balance import splash_damage_mult

                splash_mult = splash_damage_mult(n_splash=1, aoe_skill=False)
                if t_idx == -1:
                    # multi-target cleave: primary = first alive, splash rest
                    order = _alive_indices(foes)
                    t_idx = order[0]
                    splash = [foes[i] for i in order[1:]]
                    splash_mult = splash_damage_mult(
                        n_splash=len(splash), aoe_skill=False
                    )
                    io.write_line(
                        "  ✦ โจมตีทั้งกลุ่ม (เป้าหลัก + กระแสแผ่ว — ฝูงใหญ่ยิ่งแผ่ว)"
                    )
                mon = foes[t_idx]
                known = known_map.get(t_idx, False)
                enemy_name = str(mon.get("name") if known else "???")
                result = _player_act(
                    player,
                    mon,
                    reg,
                    io,
                    rng,
                    area_id=area_id,
                    known=known,
                    enemy_name=enemy_name,
                    combat_round=combat_round,
                    splash=splash,
                    splash_mult=splash_mult,
                    pack_foes=foes,
                )
                if result is None:
                    return  # fled
                if result:
                    spend_action(player)
                    # resolve any newly downed (primary or splash)
                    for i in list(alive_before):
                        f = foes[i]
                        if int(f.get("hp") or 0) <= 0:
                            last_loot_mon = f
                            _on_foe_down(
                                player, f, reg, io, rng, area_id=area_id
                            )
                    left = len(_alive_indices(foes))
                    if left:
                        io.write_line(f"  เหลือในฝูง: {left} ตัว")
                else:
                    player["atb"] = 100.0
            else:
                mon = foes[int(idx or 0)]
                if int(mon.get("hp") or 0) <= 0:
                    continue
                known = known_map.get(int(idx or 0), False)
                enemy_name = str(mon.get("name") if known else "???")
                io.write_line()
                io.write_line(
                    render_combat_vitals(
                        player,
                        mon,
                        known=known,
                        situation=situation_strip(
                            player, mon, known=known, reg=reg
                        ),
                        round_no=combat_round,
                    )
                )
                io.write_line(f"── ศัตรู #{int(idx or 0) + 1} ขยับ ──")
                mon_outcome = _monster_act(
                    player,
                    mon,
                    reg,
                    io,
                    rng,
                    known=known,
                    enemy_name=enemy_name,
                )
                if mon_outcome == "fled":
                    mon["hp"] = 0
                    mon["_escaped"] = True
                    mark_monster_seen(player, mon)
                    spend_action(mon)
                    continue
                spend_action(mon)

    if int(player.get("hp") or 0) <= 0:
        clear_party_call_buffs(player)
        emit_narrative(io, narrate(reg, "defeat", rng, enemy="กลุ่มศัตรู"))
        _emit_personality_notes(io, personality_event(player, "combat_death", reg))
        death_msg = apply_soft_death(player, reg)
        io.write_line()
        io.write_line(soft_death_panel(death_msg))
        for mon in foes:
            mark_monster_seen(player, mon)
        if in_dungeon(player):
            from game.domain.dungeon import drain_dungeon_resources

            for line in drain_dungeon_resources(player, reg, rng, reason="death"):
                io.write_line(line)
            for line in exit_dungeon(player, reg, success=False, escaped=True):
                io.write_line(line)
        return

    # all foes down (killed or MI2 soft-escaped)
    clear_party_call_buffs(player)
    any_killed = any(
        int(f.get("hp") or 0) <= 0 and not f.get("_escaped") for f in foes
    )
    all_escaped = all(bool(f.get("_escaped")) for f in foes) and foes
    if all_escaped:
        io.write_line(" กลุ่มศัตรูถอยหมด — ไม่มีร่างให้เก็บของ")
    else:
        _emit_personality_notes(io, personality_event(player, "combat_win", reg))
        io.write_line(" ⚔ กลุ่มนี้แตกแล้ว")
        mon = last_loot_mon
        if mon is None or mon.get("_escaped"):
            mon = next(
                (f for f in reversed(foes) if not f.get("_escaped")),
                foes[-1],
            )
        if mon and not mon.get("_escaped") and any_killed:
            loot = build_combat_loot_table(player, mon, reg, rng)
            if loot:
                emit_narrative(io, narrate_field(reg, "loot", rng))
                for line in present_loot_choices(loot):
                    io.write_line(line)
                pick = io.read_line("เก็บ (A / 1,2 / 0): ").strip()
                notes = resolve_loot_pick(player, reg, loot, pick)
                if pick.strip().lower() in ("0", "", "n", "ไม่", "ทิ้ง"):
                    emit_narrative(io, narrate_field(reg, "loot_leave", rng))
                for line in notes:
                    io.write_line(line)
    _emit_personality_notes(io, check_personality_point_grants(player, reg))


def run_combat_wave(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    *,
    count: int = 1,
    ambush: bool = False,
    mon: Optional[Dict[str, Any]] = None,
    monsters: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Multi-enemy combat: simultaneous ATB when 2+ foes; single uses normal fight.
    """
    area_id = str(player.get("location") or "dark_forest")
    if in_dungeon(player):
        run = get_run(player) or {}
        area_id = str(
            run.get("area_id")
            or player.get("location_before_dungeon")
            or area_id
        )
    pack: List[Dict[str, Any]] = []
    if monsters:
        pack = [dict(m) for m in monsters if m]
    elif mon is not None:
        pack = [dict(mon)]
    count = max(1, min(3, int(count or 1)))
    while len(pack) < count:
        m = pick_monster(reg, area_id, rng)
        if pack:
            m = dict(m)
            m["hp"] = max(1, int(int(m.get("hp") or 10) * 0.78))
            m["max_hp"] = int(m["hp"])
            m["atk"] = max(1, int(int(m.get("atk") or 5) * 0.9))
            m["name"] = str(m.get("name") or "ศัตรู") + " (ร่วมฝูง)"
        pack.append(m)
    if len(pack) == 1:
        _run_combat(
            player,
            reg,
            io,
            rng,
            mon=pack[0],
            ambush=ambush,
        )
        return
    _run_combat_multi(player, reg, io, rng, pack, ambush=ambush)


