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
) -> None:
    """One enemy action when their ATB is full."""
    if should_skip_action(mon, reg, rng):
        emit_narrative(io, narrate(reg, "status_tick_freeze", rng, enemy=enemy_name))
        io.write_line("  ศัตรูถูกล็อกสถานะ — ข้ามการโจมตี!")
        tick = process_status_turn(mon, reg, rng, apply_dot=True, min_hp=0)
        if tick.damage:
            io.write_line(f"  [ตัวเลข] สถานะศัตรู −{tick.damage} HP")
        return

    hits = max(1, int(mon.get("extra_hits") or 1))
    guard_skill = None
    for hit_i in range(hits):
        if int(player.get("hp") or 0) <= 0:
            break
        profile = pick_monster_attack(mon, rng)
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
            guards = defense_skills(player, reg)
            io.write_line("เลือกป้องกัน:")
            for i, (sid, sk) in enumerate(guards, 1):
                cost = int(sk.get("cost_mana", 0))
                io.write_line(f"  {i}. {sk.get('name', sid)} (MP {cost})")
            io.write_line("  0. ไม่ป้องกัน")
            gch = io.read_line("กัน: ").strip()
            if gch not in ("0", ""):
                try:
                    gi = int(gch) - 1
                    if 0 <= gi < len(guards):
                        _sid, guard_skill = guards[gi]
                        cost = int(guard_skill.get("cost_mana", 0))
                        if int(player["mana"]) < cost:
                            io.write_line("มานาไม่พอ — กันไม่ได้")
                            guard_skill = None
                        else:
                            player["mana"] = int(player["mana"]) - cost
                            ac = dict(player.get("action_counts") or {})
                            ac["defend"] = int(ac.get("defend", 0)) + 1
                            player["action_counts"] = ac
                            personality_event(player, "combat_defend", reg)
                except Exception:
                    guard_skill = None
        final, grade, gmsg = apply_defense(raw, tags, guard_skill)
        final = apply_player_defense_stat(final, player)
        player["hp"] = int(player["hp"]) - final
        if dodge_fl:
            io.write_line(f"  {dodge_fl.strip()}")
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
        hit_note = apply_monster_hit_status(player, mon, profile, reg, rng)
        if hit_note:
            io.write_line(f"  {hit_note}")

    m_tick = process_status_turn(mon, reg, rng, apply_dot=True, min_hp=0)
    if m_tick.damage:
        io.write_line(f"  [ตัวเลข] สถานะศัตรู −{m_tick.damage} HP")
    p_tick = process_status_turn(player, reg, rng, apply_dot=True, min_hp=1)
    if p_tick.damage:
        io.write_line(f"  [ตัวเลข] สถานะคุณ −{p_tick.damage} HP")


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

    io.write_line(render_mode_actions(MODE_COMBAT))
    if splash:
        n_sp = len([s for s in splash if int(s.get("hp") or 0) > 0])
        eff = splash_damage_mult(n_splash=n_sp, aoe_skill=False)
        eff = min(eff, splash_mult)
        splash_mult = eff
        io.write_line(
            f"  (หลายเป้า: หลัก + กระแส {n_sp} ตัว · กระแสแผ่วเมื่อฝูงใหญ่)"
        )
    try:
        from game.domain.intelligence import format_intel_status_line, ensure_intelligence

        ensure_intelligence(player, reg)
        io.write_line(format_intel_status_line(player))
    except Exception:
        pass
    io.write_line(f"  (คอมโบสูงสุด {max_combo} ขั้น · มานาไม่พอใช้โซ่ไม่ได้)")
    ch = io.read_line("〔ไฟต์〕 เลือก: ").strip()

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
            io.write_line(f"  {i}. {sk.get('name', sid)}{chg} (MP {cost}){flag}{aoe}")
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
            io.write_line(f"ตอนนี้เรียงได้สูงสุด {max_combo} ขั้น")
            return False
        prev = preview_combo_mana(player, reg, skill_ids)
        cost = int(prev.get("total_mana", 0))
        if prev.get("ok") and not prev.get("can_afford", True):
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
            io.write_line(f"มานาไม่พอ (ต้องการ {cost})")
            return False
        player["mana"] = int(player["mana"]) - cost
        skill_label = str(combo.get("flavor") or "สกิล")
        length = int(combo.get("length") or 1)
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
        if combo.get("heal"):
            heal = int(combo["heal"])
            player["hp"] = min(int(player["max_hp"]), int(player["hp"]) + heal)
            io.write_line(f"  [ตัวเลข] ฟื้นฟู {heal} HP · MP -{cost}")
        else:
            dmg = int(combo.get("damage", 0))
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
            st = apply_status_to_monster(
                mon,
                combo.get("status"),
                float(combo.get("status_chance") or 0),
                rng,
                reg,
            )
            if st:
                io.write_line(
                    f"  [สถานะ] {status_display_name(st, reg)} ติดที่ศัตรู"
                )
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
        io.write_line("── ยา / ล้าง / บัฟ ──")
        io.write_line(" 1 ใช้ของจากคลัง  2 ล้างเร็ว  0 กลับ")
        sub = io.read_line("เลือก: ").strip()
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

    # Ambush: enemy strikes once before ATB loop
    if ambush and mon["hp"] > 0 and player["hp"] > 0:
        profile = pick_monster_attack(mon, rng)
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
    io.write_line(
        "  (จังหวะ: แท่งสเตตัสเต็มก่อนเลือกคำสั่ง — ความเร็วแต่ละฝ่ายไม่เท่ากัน · สูตรซ่อน)"
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
                    )
                )
                io.write_line("── ศัตรูขยับ (แท่งจังหวะเต็ม) ──")
                _monster_act(
                    player,
                    mon,
                    reg,
                    io,
                    rng,
                    known=known,
                    enemy_name=enemy_name,
                )
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
            pick = io.read_line("เก็บ: ").strip()
            notes = resolve_loot_pick(player, reg, loot, pick)
            if pick.strip() in ("0", "", "n", "N"):
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
            profile = pick_monster_attack(mon, rng)
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
                _monster_act(
                    player,
                    mon,
                    reg,
                    io,
                    rng,
                    known=known,
                    enemy_name=enemy_name,
                )
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

    # all foes down
    clear_party_call_buffs(player)
    _emit_personality_notes(io, personality_event(player, "combat_win", reg))
    io.write_line(" ⚔ กลุ่มนี้แตกแล้ว")
    mon = last_loot_mon or foes[-1]
    loot = build_combat_loot_table(player, mon, reg, rng)
    if loot:
        emit_narrative(io, narrate_field(reg, "loot", rng))
        for line in present_loot_choices(loot):
            io.write_line(line)
        pick = io.read_line("เก็บ: ").strip()
        notes = resolve_loot_pick(player, reg, loot, pick)
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


