"""Field encounters — monster, NPC, chest, player-echo approach."""
from __future__ import annotations

import random
from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.combat import pick_monster
from game.domain.encounters import mark_monster_seen, resolve_approach
from game.domain.narrative import emit_narrative, narrate_field
from game.domain.party import (
    add_member,
    member_from_player_echo,
    member_from_template,
    try_consent_player_hire,
)
from game.domain.personality import (
    apply_event as personality_event,
    note_player_meet,
    npc_roll_modifier,
)
from game.domain.progression import grant_library_key
from game.domain.skill_tree import pick_random_master_id
from game.domain.stats import bump_stat
from game.ports.io import IO
from game.services.combat_session import _run_combat
from game.services.dungeon_session import _enter_dungeon_flow
from game.services.field_shared import _emit_personality_notes
from game.services.shop import run_shop
from game.ui_terminal.panels import approach_outcome_line
from game.ui_terminal.spotlight import rare_loot_banner


def _master_teach_menu_lazy(player, reg, io, mid):
    from game.services.field_menus import _master_teach_menu
    _master_teach_menu(player, reg, io, mid)

def _handle_player_echo(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    other: Dict[str, Any],
) -> None:
    """Approach another world's player save — friend co-op or foe duel (hidden affinity)."""
    from game.domain.world_social import (
        compute_affinity,
        other_as_combatant,
        remember_social,
        resolve_social_outcome,
    )

    cfg = getattr(reg, "world_social", None) or {}
    approaches = list(cfg.get("approaches") or [])
    io.write_line(f"\nคุณพบผู้เล่นในโลกนี้: {other.get('name')}")
    io.write_line(f"  สายที่สังเกตได้: {other.get('occ_path') or other.get('occupation') or '???'}")
    io.write_line("  (ไม่แสดงเลเวล/ค่าพลัง — ใช้ข้อมูลจริงในระบบ)")
    io.write_line("เข้าหาอย่างไร?")
    for i, a in enumerate(approaches, 1):
        io.write_line(f"  {i}. {a.get('label')}")
    io.write_line("  0. เดินจากไป")
    ch = io.read_line("เลือก: ").strip()
    if ch in ("0", ""):
        io.write_line("คุณเดินจากไป...")
        return
    try:
        idx = int(ch) - 1
        approach = approaches[max(0, min(len(approaches) - 1, idx))]
    except Exception:
        io.write_line("ยกเลิก")
        return
    aid = str(approach.get("id") or "polite")
    cost = int(approach.get("cost_world") or 0)
    if cost > 0:
        if int(player.get("money_world", 0)) < cost:
            io.write_line("เงินไม่พอสำหรับท่าทางนี้ — เปลี่ยนเป็นทักทายธรรมดา")
            aid = "polite"
        else:
            player["money_world"] = int(player["money_world"]) - cost
            io.write_line(f"(เสียเงินโลก {cost})")

    # Hidden roll + track player-meet for personality point grants
    _emit_personality_notes(io, note_player_meet(player, reg))
    aff = compute_affinity(player, other, reg, aid, rng)
    outcome = resolve_social_outcome(aff, reg)
    # map soft outcomes
    if outcome == "neutral_friendish":
        outcome = "friend" if rng.random() < 0.55 else "neutral"
    elif outcome == "neutral_foeish":
        outcome = "foe" if rng.random() < 0.55 else "neutral"

    oid = str(other.get("id") or "unknown")
    if outcome == "friend":
        remember_social(player, oid, "friend")
        io.write_line(f"\n✦ {other.get('name')} ยอมเป็นพันธมิตรชั่วคราว!")
        io.write_line("1. ชวนร่วมสู้มอน  2. ชวนเข้าปาร์ตี้ (ต้องยอมรับ)  3. แค่คุยแล้วจาก")
        sub = io.read_line("เลือก: ").strip()
        if sub == "1":
            mon = pick_monster(reg, str(player.get("location")), rng)
            mon = apply_world_enemy_mods(mon, player)
            player["bonus_atk"] = int(player.get("bonus_atk", 0)) + max(
                3, int(other.get("bonus_atk", 5)) // 4
            )
            player["blessings"] = list(player.get("blessings") or []) + [
                f"พันธมิตร:{other.get('name')}"
            ]
            player["blessing_turns"] = max(int(player.get("blessing_turns", 0)), 4)
            io.write_line(
                f"{other.get('name')} ช่วยเสริมแนวรบ! (บัฟชั่วคราวจากค่าสถานะ/เกียร์ของเขา)"
            )
            _run_combat(player, reg, io, rng, mon=mon, ambush=False)
        elif sub == "2":
            ok, why = try_consent_player_hire(player, other, reg, aff, rng)
            if not ok:
                emit_narrative(
                    io,
                    narrate_field(
                        reg, "party_reject", rng, name=other.get("name") or "ผู้พเนจร"
                    ),
                )
                io.write_line(why)
            else:
                mem = member_from_player_echo(other, aff, reg, rng)
                io.write_line(add_member(player, mem, reg))
                emit_narrative(
                    io,
                    narrate_field(
                        reg, "party_join", rng, name=mem.get("name") or other.get("name")
                    ),
                )
                apply_party_passives_to_player(player, reg)
                recompute_stats(player, reg)
        else:
            io.write_line("ได้ข้อมูลเล็กน้อย... (ไม่โชว์เลเวล)")
            know = dict(player.get("knowledge") or {})
            pe = dict(know.get("players") or {})
            pe[oid] = {"name": other.get("name"), "relation": "friend"}
            know["players"] = pe
            player["knowledge"] = know
    elif outcome == "foe":
        remember_social(player, oid, "foe")
        io.write_line(f"\n⚔ {other.get('name')} กลายเป็นศัตรู!")
        io.write_line("(ระบบดึงอาวุธ เกียร์ สเตตัสจริงของเขาเข้าสู่การต่อสู้)")
        foe = other_as_combatant(other)
        foe = apply_world_enemy_mods(foe, player)
        _run_combat(player, reg, io, rng, mon=foe, ambush=rng.random() < 0.25)
    else:
        remember_social(player, oid, "neutral_friendish")
        io.write_line(f"\n{other.get('name')} พยักหน้าแล้วจากไป... ยังไม่มิตรไม่ศัตรูชัด")


def _handle_sight(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    sight: Dict[str, Any],
) -> None:
    kind = sight.get("kind")
    if kind == "dungeon":
        did = str(sight.get("dungeon_id") or "")
        _enter_dungeon_flow(player, reg, io, rng, did)
        return
    if kind == "player":
        emit_narrative(io, narrate_field(reg, "approach_player", rng))
        other = sight.get("player_echo")
        if isinstance(other, dict):
            _handle_player_echo(player, reg, io, rng, other)
        else:
            io.write_line("เงาผู้เล่นจางหาย...")
        return
    if kind == "monster":
        mon = dict(sight.get("monster") or pick_monster(reg, str(player.get("location")), rng))
        outcome = resolve_approach("monster", reg, rng)
        emit_narrative(io, narrate_field(reg, "approach_monster", rng))
        io.write_line(f"\nเข้าหา: {sight.get('label')} ({sight.get('hint')})")
        if outcome == "flee":
            io.write_line("มันหนีไป... คุณจำเค้าโครงได้เพียงเลือนราง")
            io.write_line(approach_outcome_line("monster", "flee"))
            mark_monster_seen(player, mon)
        elif outcome == "rare_talk":
            io.write_line("สิ่งมีชีวิตนั้น... ส่งเสียงเหมือนพูด? ได้ชำนาญ +2%")
            io.write_line(approach_outcome_line("monster", "rare_talk"))
            aid = str(player.get("location"))
            am = dict(player.get("area_mastery") or {})
            am[aid] = min(100, int(am.get(aid, 0)) + 2)
            player["area_mastery"] = am
            mark_monster_seen(player, mon)
        elif outcome == "ambush":
            io.write_line("มันกระโจนใส่ก่อน!")
            io.write_line(approach_outcome_line("monster", "ambush"))
            _run_combat(player, reg, io, rng, mon=mon, ambush=True)
        else:
            io.write_line("เข้าสู่การต่อสู้")
            io.write_line(approach_outcome_line("monster", str(outcome or "fair_combat")))
            _run_combat(player, reg, io, rng, mon=mon, ambush=False)
    elif kind == "npc":
        # pick hidden archetype + approach style (player only sees labels)
        archetypes = list((getattr(reg, "npc_archetypes", None) or {}).keys()) or [
            "wanderer"
        ]
        arch = rng.choice(archetypes)
        emit_narrative(io, narrate_field(reg, "approach_npc", rng))
        io.write_line(f"\nเข้าหาคนแปลกหน้า ({sight.get('hint')})...")
        io.write_line("คุณจะพูด/ทำอย่างไร?")
        io.write_line("  1. ทักทายสุภาพ")
        io.write_line("  2. ยื่นของขวัญเล็กน้อย (เงิน 25)")
        io.write_line("  3. ท้าพิสูจน์ฝีมือ")
        io.write_line("  4. ข่มขู่")
        io.write_line("  5. รักษาระยะ")
        io.write_line("  6. เสนอช่วยเหลือ")
        # Special intel-gated option (cost current ความฉลาด — not always useful)
        from game.domain.intelligence import (
            can_use_special_option,
            format_intel_status_line,
            try_special_option,
        )

        intel_need = 2
        can_sp, _why = can_use_special_option(player, intel_need)
        if can_sp:
            io.write_line("  7. ★ อ่านท่าทางลึก (ใช้สติ — ผลไม่แน่นอน)")
        else:
            io.write_line("  7. ★ อ่านท่าทางลึก (สติไม่พอ — ใช้ไม่ได้ตอนนี้)")
        io.write_line(format_intel_status_line(player))
        ans = io.read_line("เลือก: ").strip()
        approach_map = {
            "1": "polite",
            "2": "gift",
            "3": "challenge",
            "4": "threaten",
            "5": "cautious",
            "6": "aid",
        }
        if ans == "7":
            spent, msg, success = try_special_option(
                player, intel_need, rng, base_success=0.68, reason="insight"
            )
            io.write_line(msg)
            if not spent:
                approach_id = "polite"
            elif success:
                approach_id = "aid" if rng.random() < 0.5 else "polite"
                io.write_line("  …คุณเห็นช่องว่างในท่าทางเขา (อาจเป็นประโยชน์)")
                player.setdefault("flags", {})["npc_read_success"] = True
            else:
                approach_id = "cautious"
                io.write_line("  …อ่านผิดทาง หรือเขาปิดบังดี (เสียสติไปแล้ว)")
        else:
            approach_id = approach_map.get(ans, "polite")
        if approach_id == "gift":
            if int(player.get("money_world", 0)) >= 25:
                player["money_world"] -= 25
                _emit_personality_notes(io, personality_event(player, "gift_money", reg))
            else:
                io.write_line("เงินไม่พอ — เปลี่ยนเป็นทักทาย")
                approach_id = "polite"
        _emit_personality_notes(io, personality_event(player, f"approach_{approach_id}", reg))
        mod = npc_roll_modifier(player, reg, arch, approach_id, rng)

        # re-weight outcome using hidden compatibility
        outcome = resolve_approach("npc", reg, rng)
        roll = rng.random() + float(mod.get("friend_bias", 0))
        if approach_id == "threaten" or roll < -0.15 + float(mod.get("ambush_bias", 0)):
            if outcome not in ("hostile", "trap_disguise") and rng.random() < 0.45:
                outcome = "hostile"
        if roll > 0.55 and outcome == "ignore":
            outcome = "friend"
        if roll > 0.7 and arch == "master":
            outcome = "master"
        if roll > 0.5 and arch == "merchant":
            outcome = "shop"

        if outcome == "hostile" or outcome == "trap_disguise":
            emit_narrative(io, narrate_field(reg, "npc_outcome_hostile", rng))
            io.write_line("เป็นศัตรู!" if outcome == "hostile" else "หน้ากากหลุด — มอนปลอมคน!")
            io.write_line(approach_outcome_line("npc", str(outcome)))
            personality_event(player, "npc_hostile", reg)
            _run_combat(player, reg, io, rng, ambush=True)
        elif outcome == "shop":
            emit_narrative(io, narrate_field(reg, "npc_outcome_shop", rng))
            emit_narrative(io, narrate_field(reg, "shop", rng))
            io.write_line("พบพ่อค้า!")
            io.write_line(approach_outcome_line("npc", "shop"))
            personality_event(player, "npc_shop", reg)
            disc = float(mod.get("shop_discount") or 0)
            sur = float(mod.get("shop_surcharge") or 0)
            if disc > 0:
                io.write_line("เขาดูถูกชะตากับคุณ... ราคารู้สึกดีขึ้น (ซ่อน)")
                player["flags"] = dict(player.get("flags") or {})
                player["flags"]["shop_discount"] = disc
            if sur > 0:
                io.write_line("เขาไม่ชอบท่าทางคุณ... ของแพงขึ้น (ซ่อน)")
                player["flags"] = dict(player.get("flags") or {})
                player["flags"]["shop_surcharge"] = sur
            if io.read_line("เข้าไปดูร้าน? (1=ใช่): ").strip() == "1":
                run_shop(player, reg, io, shop_id="traveling_merchant")
            player.get("flags", {}).pop("shop_discount", None)
            player.get("flags", {}).pop("shop_surcharge", None)
        elif outcome == "friend":
            personality_event(player, "npc_friend", reg)
            emit_narrative(io, narrate_field(reg, "npc_outcome_friend", rng))
            io.write_line("ได้เพื่อนเดินทาง! (ความเข้ากันส่งผลซ่อน)")
            io.write_line(approach_outcome_line("npc", "friend"))
            atk_b = 2 + (1 if float(mod.get("compatibility") or 0) > 0.4 else 0)
            player["bonus_atk"] = int(player.get("bonus_atk", 0)) + atk_b
            player["blessings"] = list(player.get("blessings") or []) + ["เพื่อนเดินทาง"]
            player["blessing_turns"] = max(int(player.get("blessing_turns", 0)), 3 + atk_b)
        elif outcome == "master":
            personality_event(player, "npc_master", reg)
            emit_narrative(io, narrate_field(reg, "npc_outcome_master", rng))
            io.write_line("✨ พบอาจารย์!")
            io.write_line(approach_outcome_line("npc", "master"))
            mid = pick_random_master_id(reg, rng)
            if mid:
                _master_teach_menu_lazy(player, reg, io, mid)
            else:
                # fallback legacy gifts
                skills = list(player.get("skills") or [])
                if "guard_water_veil" not in skills:
                    skills.append("guard_water_veil")
                    player["skills"] = skills
                    io.write_line("ได้ท่าป้องกัน: ม่านน้ำ")
                teach = bool(mod.get("teach_bonus"))
                if "water_bolt" not in skills and (teach or rng.random() < 0.5):
                    skills.append("water_bolt")
                    player["skills"] = skills
                    io.write_line("ได้สกิล: กระสุนน้ำ" + (" (สอนพิเศษ)" if teach else ""))
            if mod.get("library_hint"):
                from game.domain.progression import grant_library_key

                io.write_line(grant_library_key(player))
            player["blessings"] = list(player.get("blessings") or []) + ["พรอาจารย์"]
            player["blessing_turns"] = max(int(player.get("blessing_turns", 0)), 8)
            player["disciple_of"] = "อาจารย์พเนจร"
        else:
            emit_narrative(io, narrate_field(reg, "npc_outcome_ignore", rng))
            io.write_line("เขาไม่สนใจคุณ...")
            io.write_line(approach_outcome_line("npc", "ignore"))
    elif kind == "chest":
        outcome = resolve_approach("chest", reg, rng)
        emit_narrative(io, narrate_field(reg, "approach_chest", rng))
        io.write_line(f"\nเปิดหีบ ({sight.get('hint')})...")
        if outcome == "ambush":
            io.write_line("!!! ของในหีบคือฟันและเงา — มอนสเตอร์!")
            io.write_line(approach_outcome_line("chest", "ambush"))
            _run_combat(player, reg, io, rng, ambush=True)
        elif outcome == "empty_trap":
            from game.domain.status_fx import apply_status, status_display_name

            applied = apply_status(player, "poison", reg, rng, source="chest_trap")
            nm = status_display_name(reg, applied or "poison")
            io.write_line(f"กับดัก! ติด{nm}")
            io.write_line(approach_outcome_line("chest", "empty_trap"))
        elif outcome == "rare_relic":
            from game.domain.equipment import add_item

            gold = rng.randint(80, 150)
            player["money_world"] = int(player.get("money_world", 0)) + gold
            name = add_item(player, "rare_mat", reg)
            io.write_line(
                rare_loot_banner(name, f"เงินโลก +{gold} · วัสดุหายากเข้าคลัง")
            )
            io.write_line(approach_outcome_line("chest", "rare_relic"))
            if rng.random() < 0.4:
                io.write_line(grant_library_key(player))
        elif outcome == "loot_weak":
            amt = rng.randint(10, 30)
            money_m = float((player.get("world_modifiers") or {}).get("money_mult", 1.0))
            amt = max(1, int(round(amt * money_m)))
            player["money_world"] = int(player.get("money_world", 0)) + amt
            bump_stat(player, "chests_opened", 1)
            bump_stat(player, "money_gained_total", amt)
            io.write_line(f"เศษเงิน +{amt}")
            io.write_line(approach_outcome_line("chest", "loot_weak"))
        else:
            from game.domain.equipment import add_item

            amt = rng.randint(25, 80)
            money_m = float((player.get("world_modifiers") or {}).get("money_mult", 1.0))
            amt = max(1, int(round(amt * money_m)))
            player["money_world"] = int(player.get("money_world", 0)) + amt
            loot_id = rng.choice(
                [
                    "potion_hp",
                    "potion_mana",
                    "potion_hp_small",
                    "iron_sword",
                    "card_fire",
                    "card_vitality",
                ]
            )
            name = add_item(player, loot_id, reg)
            bump_stat(player, "chests_opened", 1)
            bump_stat(player, "money_gained_total", amt)
            io.write_line(f"ได้เงินโลก +{amt} และ {name}")


