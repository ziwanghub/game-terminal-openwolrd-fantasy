"""Field digit actions 1–4 extracted from field_loop (rest/explore/approach/travel)."""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional

from game.data_load.registry import DataRegistry
from game.domain.character import apply_field_regen, unlocked_areas
from game.domain.dungeon import in_dungeon
from game.domain.narrative import emit_narrative, field_enter_area, narrate_field
from game.domain.party import (
    add_member,
    apply_party_passives_to_player,
    member_from_template,
    roll_recruit_sight,
    try_recruit_template_offer,
)
from game.domain.personality import apply_event as personality_event
from game.domain.quests import bump_quest
from game.domain.equipment import recompute_stats
from game.domain.stats import bump_stat
from game.ports.io import IO
from game.services.combat_session import run_combat_wave
from game.services.field_shared import _emit_personality_notes


def _try_board_complete(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    try:
        from game.services.mission_service import try_complete_board_mission

        try_complete_board_mission(player, reg, io)
    except Exception:
        pass


def do_rest(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    *,
    area_id: str,
) -> None:
    emit_narrative(io, narrate_field(reg, "rest", rng, area_id=area_id))
    msg = apply_field_regen(player, reg)
    heal = 20 + int(player.get("mana", 0)) // 8
    player["hp"] = min(int(player["max_hp"]), int(player["hp"]) + heal)
    player["mana"] = min(int(player["max_mana"]), int(player["mana"]) + 15)
    player["pressure"] = max(0, int(player.get("pressure", 0)) - 8)
    io.write_line(f"พักผ่อน — {msg} | พักเพิ่ม HP+{heal} MP+15")
    try:
        from game.domain.intelligence import rest_intel_recovery

        imsg = rest_intel_recovery(player)
        if imsg:
            io.write_line(f"  {imsg}")
    except Exception:
        pass
    bump_stat(player, "rests", 1)
    _emit_personality_notes(io, personality_event(player, "rest", reg))
    for line in bump_quest(player, reg, "rest", area_id=area_id):
        io.write_line(line)
    _try_board_complete(player, reg, io)


def do_explore(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    *,
    area_id: str,
) -> None:
    emit_narrative(io, narrate_field(reg, "explore", rng, area_id=area_id))
    bump_stat(player, "explores", 1)
    _emit_personality_notes(io, personality_event(player, "explore", reg))
    if roll_recruit_sight(player, reg, rng):
        offer = try_recruit_template_offer(player, reg, rng)
        if offer:
            emit_narrative(
                io,
                narrate_field(
                    reg,
                    "party_recruit",
                    rng,
                    name=offer.get("name"),
                    area_id=area_id,
                ),
            )
            io.write_line("  มันจ้องคุณ — ยื่นมือรับ? (ต้องได้รับการยอมรับ)")
            if io.read_line("1=ยื่นมือ  อื่น=เดินจาก: ").strip() == "1":
                mem = member_from_template(offer, reg, rng)
                io.write_line(add_member(player, mem, reg))
                emit_narrative(
                    io,
                    narrate_field(reg, "party_join", rng, name=mem.get("name")),
                )
                apply_party_passives_to_player(player, reg)
                recompute_stats(player, reg)
            else:
                emit_narrative(
                    io,
                    narrate_field(
                        reg,
                        "party_reject",
                        rng,
                        name=offer.get("name"),
                    ),
                )
    if rng.random() < 0.35:
        emit_narrative(io, narrate_field(reg, "explore_find", rng, area_id=area_id))
        from game.domain.aoe_balance import pack_size_roll

        pack = pack_size_roll(int(player.get("level") or 1), rng.random())
        if pack > 1:
            io.write_line(
                "  …เงาอีกตัวขยับข้างหลัง"
                if pack == 2
                else "  …เงาหลายตัวล้อม — กลุ่มใหญ่"
            )
        run_combat_wave(player, reg, io, rng, count=pack, ambush=False)
    else:
        emit_narrative(io, narrate_field(reg, "explore_empty", rng, area_id=area_id))
        gain = rng.randint(1, 3)
        am = dict(player.get("area_mastery") or {})
        am[area_id] = min(100, int(am.get(area_id, 0)) + gain)
        player["area_mastery"] = am
        io.write_line(f"ชำนาญพื้นที่ +{gain}%")
    for line in bump_quest(player, reg, "explore", area_id=area_id):
        io.write_line(line)
    _try_board_complete(player, reg, io)


def do_approach(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    *,
    area_id: str,
    sights: List[Dict[str, Any]],
    handle_sight: Callable[[Dict[str, Any]], None],
) -> None:
    if not sights:
        emit_narrative(io, narrate_field(reg, "no_sights", rng, area_id=area_id))
        io.write_line("ไม่มีเป้าหมาย")
        return
    try:
        idx = int(io.read_line("เข้าหาหมายเลข: ").strip()) - 1
        sight = sights[max(0, min(len(sights) - 1, idx))]
    except Exception:
        io.write_line("ยกเลิก")
        return
    handle_sight(sight)


def do_travel(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
) -> None:
    unlocked = unlocked_areas(player, reg)
    io.write_line("\nพื้นที่ที่ไปได้:")
    for i, aid in enumerate(unlocked, 1):
        a = reg.areas[aid]
        m = (player.get("area_mastery") or {}).get(aid, 0)
        io.write_line(
            f"  {i}. {a.get('name')} (ปลด Lv.{a.get('unlock_level', 1)} · ชำนาญ {m}%)"
        )
    locked = [a for aid, a in reg.areas.items() if aid not in unlocked]
    if locked:
        io.write_line(
            "  — ยังล็อก: "
            + ", ".join(
                f"{a.get('name')}(Lv.{a.get('unlock_level')})" for a in locked
            )
        )
    try:
        idx = int(io.read_line("เลือก: ").strip()) - 1
        dest = unlocked[max(0, min(len(unlocked) - 1, idx))]
    except Exception:
        io.write_line("ยกเลิก")
        return
    if in_dungeon(player):
        io.write_line("ติดในดันเจียน — เดินทางไม่ได้จนกว่าจะออก")
        return
    player["location"] = dest
    emit_narrative(io, field_enter_area(reg, dest, rng))
    io.write_line(f"→ ถึง {reg.area_name(dest)}")
    bump_stat(player, "travels", 1)
    for line in bump_quest(player, reg, "travel"):
        io.write_line(line)
    _try_board_complete(player, reg, io)
    if rng.random() < 0.18:
        from game.domain.ui_prefs import ensure_ui_prefs

        prefs = ensure_ui_prefs(player)
        if prefs.get("warn_travel_ambush", True):
            io.write_line("  …ทางแคบ เงาขวาง — อาจถูกซุ่ม (เสี่ยง)")
        emit_narrative(io, narrate_field(reg, "travel_ambush", rng, area_id=dest))
        from game.domain.aoe_balance import pack_size_roll

        # ambush packs rarer / smaller early
        plv = int(player.get("level") or 1)
        pack = pack_size_roll(plv, rng.random() * 0.85)
        run_combat_wave(player, reg, io, rng, count=pack, ambush=True)
