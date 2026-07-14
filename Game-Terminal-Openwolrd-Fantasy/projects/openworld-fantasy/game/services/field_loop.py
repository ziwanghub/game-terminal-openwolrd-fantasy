"""Main field gameplay loop — sights, approach risk, combo combat, defense."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from game.data_load.registry import DataRegistry, get_registry
from game.domain.character import apply_field_regen, create_player, unlocked_areas, zodiac_from_date
from game.domain.combo import (
    apply_defense,
    defense_skills,
    max_combo_for_player,
    parse_combo_input,
    preview_combo_mana,
    resolve_combo,
)
from game.domain.combat import (
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
from game.domain.balance import apply_soft_death
from game.domain.combo import apply_player_defense_stat
from game.domain.progression import (
    STAT_KEYS,
    STAT_LABELS,
    allocate_stat,
    ensure_progression,
    format_alloc_panel,
    grant_library_key,
    library_visit,
    try_occupation_rank_up,
    try_unit_unlock,
)
from game.domain.personality import (
    apply_event as personality_event,
    check_personality_point_grants,
    ensure_personality,
    format_personality_panel,
    invest_personality_point,
    note_player_meet,
    npc_roll_modifier,
    personality_allocate_menu_axes,
    soft_impression,
)
from game.domain.stats import bump_stat, ensure_stats, format_stats_lines
from game.domain.skill_charges import format_charge_hint, spend_charges
from game.domain.skill_tree import (
    ensure_skill_tree_state,
    format_tree_panel,
    learn_skill,
    list_master_offers,
    list_visible_tree_nodes,
    pick_random_master_id,
    renew_master_skill,
    teach_from_master,
)
from game.ui_terminal.help import maybe_onboarding_tip, show_help, show_tutorial
from game.domain.encounters import build_sights, mark_monster_seen, resolve_approach
from game.domain.equipment import (
    describe_loadout,
    equip_item,
    ensure_gear_fields,
    recompute_stats,
    socket_card,
    unsocket_card,
)
from game.domain.inventory_sys import (
    bag_item_id_at,
    bag_item_rarity_at,
    build_combat_loot_table,
    examine_item,
    format_bag_panel,
    format_equip_panel,
    present_loot_choices,
    resolve_loot_pick,
    soft_upgrade_hint,
    upgrade_equipped_opaque,
)
from game.domain.party import (
    add_member,
    apply_party_passives_to_player,
    call_party_power,
    clear_party_call_buffs,
    ensure_party,
    format_party_panel,
    member_from_player_echo,
    member_from_template,
    party_assist_damage,
    party_size,
    remove_member,
    roll_recruit_sight,
    try_consent_player_hire,
    try_recruit_template_offer,
)
from game.domain.unit_system import gain_unit_mastery_xp, soft_mastery_label
from game.domain.narrative import (
    area_mood,
    emit_narrative,
    field_enter_area,
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
from game.domain.boss import can_challenge_boss, check_phase_transition, spawn_boss
from game.domain.dungeon import (
    advance_floor,
    apply_dungeon_enemy_mods,
    begin_dungeon,
    can_advance_floor,
    dungeon_by_id,
    dungeon_menu_actions,
    ensure_dungeon_state,
    exit_dungeon,
    explore_floor_event,
    format_dungeon_panel,
    get_run,
    in_dungeon,
    note_dungeon_fight,
    on_dungeon_boss_defeated,
    soft_difficulty_text,
    tick_dungeon_time,
    try_escape,
)
from game.domain.craft import craft, list_recipes
from game.domain.quests import bump_quest, ensure_quests, list_quest_lines
from game.ui_terminal.spotlight import spotlight
from game.domain.leveling import xp_progress
from game.ports.io import IO, get_io
from game.runtime.auto_farm import run_auto_farm
from game.services.save_service import save_player
from game.services.shop import run_shop
from game.ui_terminal.spotlight import level_up_banner, rare_loot_banner
from game.ui_terminal.layout import render_box
from game.ui_terminal.status import (
    render_combat_vitals,
    render_field_actions,
    render_mode_chrome,
    render_status_l1,
    render_status_l1c,
)



from game.services.combat_session import _run_combat
from game.services.consumables import _combat_quick_cleanse, _use_potion
from game.services.dungeon_session import _dungeon_field_turn, _enter_dungeon_flow
from game.services.field_encounters import _handle_player_echo, _handle_sight
from game.services.field_shared import _emit_personality_notes

def _io() -> IO:
    return get_io()


def interactive_create(reg: DataRegistry, io: Optional[IO] = None) -> Dict[str, Any]:
    io = io or _io()
    from game.domain.ui_prefs import ensure_ui_prefs

    io.write_line()
    io.write_line(
        render_box(
            [
                " สร้างตัวละคร  (1/3) ชื่อ",
                "---",
                " ตั้งชื่อที่จะใช้ในโลกนี้",
            ],
            double=False,
        )
    )
    name = io.read_line("\n  ชื่อตัวละคร: ").strip() or "นักผจญภัย"

    io.write_line()
    io.write_line(
        render_box(
            [
                " สร้างตัวละคร  (2/3) เพศ",
                "---",
                " 1  ชาย",
                " 2  หญิง",
                "---",
                " พิมพ์ 1 หรือ 2 แล้ว Enter",
            ],
            double=False,
        )
    )
    gender = "ชาย"
    for _ in range(5):
        gch = io.read_line("\n  เลือกเพศ (1–2): ").strip()
        if gch in ("1", "ชาย", "ช", "m", "M", "male"):
            gender = "ชาย"
            break
        if gch in ("2", "หญิง", "ญ", "f", "F", "female"):
            gender = "หญิง"
            break
        io.write_line("  เลือก 1=ชาย หรือ 2=หญิง")
    io.write_line(f"  → เพศ: {gender}")

    io.write_line()
    io.write_line(
        render_box(
            [
                " สร้างตัวละคร  (3/3) วันเกิด",
                "---",
                " รูปแบบ  วัน/เดือน/ปี",
                " ตัวอย่าง  15/6/2000",
            ],
            double=False,
        )
    )
    birth = io.read_line("\n  วันเกิด: ").strip()
    try:
        day, month, year = [int(x) for x in birth.split("/")]
        zodiac = zodiac_from_date(day, month)
        birth_s = f"{day}/{month}/{year}"
    except Exception:
        zodiac = "เมษ"
        birth_s = "1/1/2000"
    io.write_line(f"  → ราศี: {zodiac}  (ผลบางอย่าง… ยังมองไม่เห็น)")

    # Start without fixed class — vagabond in the free city path
    starter_id = "vagabond" if "vagabond" in reg.occupations else next(iter(reg.occupations))
    player = create_player(
        reg,
        name=name,
        occupation_id=str(starter_id),
        zodiac=zodiac,
        gender=gender,
        birth=birth_s,
    )
    skills = list(player.get("skills") or [])
    if "guard_basic" not in skills:
        skills.append("guard_basic")
    player["skills"] = skills
    ensure_ui_prefs(player)
    # Hidden starting stat pool (differs per person — never explain why)
    from game.domain.progression import (
        ensure_progression,
        init_progression,
        roll_starting_stat_points,
    )
    import random as _rnd

    ensure_progression(player, reg)
    init_progression(player, reg)
    start_pts = roll_starting_stat_points(player, reg, _rnd.Random(player.get("latent_seed")))
    player["stat_points"] = int(start_pts)
    player["flags"] = dict(player.get("flags") or {})
    player["flags"]["arrived_city"] = True
    player["flags"]["no_class_yet"] = str(player.get("occupation_id")) == "vagabond"

    io.write_line()
    io.write_line(
        render_box(
            [
                " ถึงเมือง · ผู้มาใหม่",
                "---",
                f" {player['name']} · {player.get('occupation')} · ราศี{zodiac}",
                f" HP {player['hp']}  MP {player['mana']}",
                f" แต้มสถานะเริ่มต้น: {start_pts}  (ทำไมได้เท่านี… ไม่มีใครบอก)",
                " ยังไม่มีอาชีพชัด — ใช้ชีวิต ทำภารกิจง่าย แล้วทางจะเปิดเอง",
                " แจกแต้ม: P · อาชีพ: C เมื่อถึงเวลา · ตั้งค่าจอ: U",
                " กระเป๋า 5 → M ตลาด · J กระดาน · H ช่วย · T บทเรียน",
            ],
            double=False,
        )
    )
    io.read_line("กด Enter เพื่อเริ่ม...")
    return player


from game.services.field_menus import (
    _bag_menu,
    _class_change_menu,
    _manage_gear,
    _master_teach_menu,
    _party_menu,
    _personality_allocate_menu,
    _run_craft_menu,
    _skill_tree_menu,
    _stat_allocate_menu,
    _ui_prefs_menu,
)

def run_field(
    player: Dict[str, Any],
    reg: Optional[DataRegistry] = None,
    io: Optional[IO] = None,
    rng: Optional[random.Random] = None,
    *,
    seed: Optional[int] = None,
) -> None:
    """Main field loop. Pass ``rng`` or ``seed`` for deterministic sessions/tests."""
    from game.domain.ui_prefs import ensure_ui_prefs

    reg = reg or get_registry()
    io = io or _io()
    if rng is None:
        rng = random.Random(seed) if seed is not None else random.Random()
    ensure_ui_prefs(player)
    io.write_line(f"\nเริ่มที่: {reg.area_name(str(player.get('location')))}")
    ensure_gear_fields(player)
    try:
        from game.domain.inventory_sys import sanitize_inventory

        for note in sanitize_inventory(player, reg):
            if note:
                io.write_line(f"  (ซ่อมคลัง) {note}")
    except Exception:
        pass
    ensure_progression(player, reg)
    recompute_stats(player, reg)
    ensure_quests(player, reg)
    sk = list(player.get("skills") or [])
    if "guard_basic" not in sk:
        sk.append("guard_basic")
        player["skills"] = sk
    if not player.get("tutorial_done"):
        show_tutorial(io)
        player["tutorial_done"] = True

    ensure_dungeon_state(player)
    # T1: show offline needs delta once after load
    try:
        notes = player.pop("_pending_load_notes", None)
        if notes:
            for line in notes:
                io.write_line(line)
    except Exception:
        pass
    try:
        from game.domain.situation import format_inbox_preview, ensure_situation_fields

        ensure_situation_fields(player)
        if player.get("world_inbox"):
            for line in format_inbox_preview(player, limit=3):
                io.write_line(line)
            io.write_line(" (อ่านละเอียด: สำรวจ → G → I)")
    except Exception:
        pass
    while True:
        _, need, pct = xp_progress(player, reg.levels)
        player["xp_percent"] = round(pct, 1)
        player["xp_needed"] = need

        # --- Dungeon locked mode ---
        if in_dungeon(player):
            io.write_line()
            run = get_run(player) or {}
            io.write_line(
                render_mode_chrome(
                    "ดันเจียน",
                    f"{run.get('name')} · ชั้น {run.get('floor')}/{run.get('floors')}",
                )
            )
            io.write_line(
                render_status_l1c(
                    player,
                    str(run.get("name") or "ดันเจียน"),
                )
            )
            dg = _dungeon_field_turn(player, reg, io, rng)
            if dg == "quit_save":
                break
            if int(player["hp"]) <= 0:
                player["hp"] = max(10, int(player["max_hp"]) // 2)
            continue

        area_id = str(player.get("location"))
        if str(area_id).startswith("dungeon:"):
            # safety: broken state
            player["location"] = player.get("location_before_dungeon") or "dark_forest"
            area_id = str(player["location"])
        player["time_units"] = int(player.get("time_units", 0)) + 1
        try:
            from game.domain.intelligence import tick_intel_recovery

            imsg = tick_intel_recovery(player, ticks=1)
            if imsg and int(player["time_units"]) % 3 == 0:
                # soft rare whisper — not every tick spam
                if rng.random() < 0.35:
                    io.write_line(f"  …{imsg}")
        except Exception:
            pass
        if player["time_units"] % 5 == 0:
            player["other_players"] = rng.randint(1, 4)
            io.write_line("\n👥 มีผู้เดินทางอื่นในพื้นที่ (จำลอง)")
        else:
            player["other_players"] = rng.randint(0, 2)

        sights = build_sights(player, reg, rng)
        world_id = str(player.get("world_id") or "default")
        area_name = reg.area_name(area_id)

        io.write_line()
        # ── A: chrome + status ──
        io.write_line(render_mode_chrome("สำรวจ", f"{area_name}  ·  โลก {world_id}"))
        io.write_line(render_status_l1c(player, area_name))

        # ── B: area mood (soft, rare) ──
        if int(player.get("time_units", 0)) % 4 == 1:
            mood = area_mood(reg, area_id, rng)
            if mood:
                io.write_line()
                emit_narrative(io, mood, max_lines=1)

        # ── C: sights panel ──
        from game.ui_terminal.layout import render_box
        from game.ui_terminal.status import format_sights_panel_lines

        flavor = ""
        if sights:
            flav_lines = narrate_field(reg, "sights", rng, area_id=area_id)
            if flav_lines:
                flavor = str(flav_lines[0])
        else:
            flav_lines = narrate_field(reg, "no_sights", rng, area_id=area_id)
            if flav_lines:
                flavor = str(flav_lines[0])
        io.write_line()
        io.write_line(
            render_box(
                format_sights_panel_lines(sights, flavor=flavor),
                double=False,
            )
        )
        try:
            maybe_onboarding_tip(player, io, area_id=area_id)
        except Exception:
            pass
        # boss hint
        ok_boss, boss_msg = can_challenge_boss(player, reg, area_id)
        boss_line = ""
        if ok_boss:
            boss_line = f"บอส: {boss_msg}  (B)"
        elif "เลเวล" in str(boss_msg):
            boss_line = f"บอส ล็อก — {boss_msg}"

        # ── D: actions ──
        io.write_line()
        io.write_line(
            render_field_actions(
                stat_points=int(player.get("stat_points") or 0),
                personality_points=int(player.get("personality_points") or 0),
                boss_line=boss_line,
            )
        )
        ch = io.read_line("\n  เลือก (เลขเมนู / เลขเป้า / 0 ออก): ").strip()

        # verb + target commands (f_mn02, upgrade_sw001, …)
        try:
            from game.services.field_commands import try_field_command

            def _open_bag():
                from game.services.bag_hub import run_bag_hub

                run_bag_hub(
                    player,
                    reg,
                    io,
                    open_shop=lambda p, r, i: run_shop(p, r, i),
                    open_craft=lambda p, r, i: _run_craft_menu(p, r, i),
                    open_gear=lambda p, r, i: _manage_gear(p, r, i),
                )

            if try_field_command(
                ch,
                player,
                reg,
                io,
                rng,
                sights,
                handle_sight=lambda s: _handle_sight(player, reg, io, rng, s),
                open_bag=_open_bag,
            ):
                continue
        except Exception as _cmd_exc:
            io.write_line(f"(คำสั่ง) {_cmd_exc}")

        if ch == "1":
            from game.services.field_actions import do_rest

            do_rest(player, reg, io, rng, area_id=area_id)
        elif ch == "2":
            from game.services.field_actions import do_explore

            do_explore(player, reg, io, rng, area_id=area_id)
        elif ch == "3":
            from game.services.field_actions import do_approach

            do_approach(
                player,
                reg,
                io,
                rng,
                area_id=area_id,
                sights=sights,
                handle_sight=lambda s: _handle_sight(player, reg, io, rng, s),
            )
        elif ch == "4":
            from game.services.field_actions import do_travel

            do_travel(player, reg, io, rng)
        elif ch in ("5", "i", "I"):
            # Mode Shell: PERSONAL hub (bag · status · quests · points)
            from game.services.personal_hub import run_personal_hub

            run_personal_hub(player, reg, io, area_name=area_name)
        elif ch == "6":
            # Mode Shell B: SHOP hub (not bag)
            from game.services.shop_hub import run_shop_hub

            run_shop_hub(player, reg, io, area_name=area_name)
        elif ch in ("jnl", "journal", "ความรู้"):
            # journal alias (formerly 6)
            know = player.get("knowledge") or {}
            io.write_line("\n── บันทึกความรู้ ──")
            mons = know.get("monsters") or {}
            if not mons:
                io.write_line("ยังไม่รู้จักมอนสเตอร์")
            else:
                for mid, info in mons.items():
                    io.write_line(
                        f" · {info.get('name', mid)} "
                        f"สู้ {info.get('fought', 0)} ชนะ {info.get('won', 0)}"
                    )
            io.write_line(" (เปิดจากตัวละคร 1 สถานะ/ความรู้สะสมในไฟต์)")
            io.read_line("Enter...")
        elif ch == "7":
            # EXPLORE: auto farm (was 8) — keep 7 as auto for short menu; save via PERSONAL/0
            try:
                n = io.read_line("จำนวนเทิร์นออโต้ (default 12, สูงสุด 40): ").strip()
                ticks = int(n) if n else 12
                ticks = max(1, min(40, ticks))
            except Exception:
                ticks = 12
            continuous = (
                io.read_line("โหมดต่อเนื่องไม่หยุดถาม Enter ทุกติก? (1=ใช่): ").strip()
                == "1"
            )
            reason, sight = run_auto_farm(
                player, reg, io, rng, max_ticks=ticks, continuous=continuous
            )
            if reason == "pause" and sight:
                io.write_line("ดำเนินการเป้าที่หยุดไว้...")
                _handle_sight(player, reg, io, rng, sight)
            elif reason == "hp":
                io.write_line("แนะนำ: พัก (1) หรือยาใน 5→กระเป๋า")
        elif ch == "8":
            # alias: old auto key still works
            try:
                n = io.read_line("จำนวนเทิร์นออโต้ (default 12, สูงสุด 40): ").strip()
                ticks = int(n) if n else 12
                ticks = max(1, min(40, ticks))
            except Exception:
                ticks = 12
            continuous = (
                io.read_line("โหมดต่อเนื่องไม่หยุดถาม Enter ทุกติก? (1=ใช่): ").strip()
                == "1"
            )
            reason, sight = run_auto_farm(
                player, reg, io, rng, max_ticks=ticks, continuous=continuous
            )
            if reason == "pause" and sight:
                _handle_sight(player, reg, io, rng, sight)
        elif ch == "9":
            # alias: quests also in PERSONAL 4
            ensure_quests(player, reg)
            io.write_line("\n── เควส ──")
            for line in list_quest_lines(player, reg):
                io.write_line(line)
            io.write_line(" (หรือกด 5/I → 4 ภารกิจ)")
            io.read_line("Enter...")
        elif ch in ("a", "A"):
            from game.services.field_menus import run_rank_hub

            run_rank_hub(player, reg, io, rng)
        elif ch in ("b", "B"):
            ok, msg = can_challenge_boss(player, reg, area_id)
            if not ok:
                io.write_line(f"ท้าทายไม่ได้: {msg}")
            else:
                io.write_line(f"\n☠ ท้าทายบอส: {msg}")
                conf = io.read_line("ยืนยัน? (1=สู้): ").strip()
                if conf == "1":
                    boss = spawn_boss(reg, area_id, rng)
                    if boss:
                        boss = apply_world_enemy_mods(boss, player)
                        io.write_line(
                            spotlight(
                                "BOSS",
                                [
                                    boss["name"],
                                    f"เฟสสูงสุด {boss.get('max_phases', 1)}",
                                    "เตรียมยาและสกิล",
                                ],
                                art_id="level_up",
                                category="ui",
                            )
                        )
                        _run_combat(player, reg, io, rng, mon=boss, ambush=False)
                    else:
                        io.write_line("ไม่พบบอสใน data")
                else:
                    io.write_line("ถอย")
        elif ch in ("s", "S", "p", "P", "n", "N", "c", "C", "k", "K", "y", "Y", "u", "U", "l", "L"):
            # Hotkey aliases → PERSONAL (Mode Shell Phase A compatibility)
            from game.services.personal_hub import run_personal_hub
            from game.services.field_menus import (
                _class_change_menu,
                _party_menu,
                _personality_allocate_menu,
                _skill_tree_menu,
                _stat_allocate_menu,
                _ui_prefs_menu,
            )

            if ch in ("s", "S"):
                ensure_stats(player)
                io.write_line()
                io.write_line(render_mode_chrome("สถานะเต็ม", reg.area_name(area_id)))
                io.write_line(render_status_l1(player, reg.area_name(area_id)))
                for line in format_stats_lines(player):
                    io.write_line(line)
                io.read_line("Enter...")
            elif ch in ("p", "P"):
                _stat_allocate_menu(player, reg, io)
            elif ch in ("n", "N"):
                _personality_allocate_menu(player, reg, io)
            elif ch in ("c", "C"):
                _class_change_menu(player, reg, io)
            elif ch in ("k", "K"):
                _skill_tree_menu(player, reg, io)
            elif ch in ("y", "Y"):
                _party_menu(player, reg, io)
            elif ch in ("u", "U"):
                _ui_prefs_menu(player, io)
            elif ch in ("l", "L"):
                notes = library_visit(player, reg)
                if notes and "ปิด" in str(notes[0]):
                    emit_narrative(io, narrate_field(reg, "library_denied", rng))
                else:
                    emit_narrative(io, narrate_field(reg, "library", rng))
                for line in notes:
                    io.write_line(line)
                for line in try_occupation_rank_up(player, reg):
                    io.write_line(line)
                for line in try_unit_unlock(player, reg):
                    io.write_line(line)
                io.read_line("Enter...")
        elif ch in ("h", "H"):
            show_help(io)
        elif ch in ("t", "T"):
            show_tutorial(io, force=True)
        elif ch in ("g", "G"):
            # H1–H3: world help board + assist
            from game.services.help_service import run_help_board

            run_help_board(player, reg, io, rng)
        elif ch == "0":
            path = save_player(player)
            io.write_line(f"บันทึกอัตโนมัติ → {path}")
            io.write_line("กลับเมนูหลัก")
            break
        else:
            io.write_line("เลือกไม่ถูกต้อง")

        if int(player.get("blessing_turns") or 0) > 0:
            player["blessing_turns"] = int(player["blessing_turns"]) - 1
            if player["blessing_turns"] <= 0 and player.get("blessings"):
                buffs = list(player.get("blessings") or [])
                if "เพื่อนเดินทาง" in buffs:
                    player["bonus_atk"] = max(0, int(player.get("bonus_atk", 0)) - 2)
                for b in buffs[:2]:
                    emit_narrative(
                        io, narrate(reg, "blessing_expire", rng, buff=b)
                    )
                player["blessings"] = []
                io.write_line("ผลบัฟ/พรหมดอายุ")

        if int(player["hp"]) <= 0:
            player["hp"] = max(10, int(player["max_hp"]) // 2)
