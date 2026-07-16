"""Field encounters — monster, NPC, chest, player-echo approach."""
from __future__ import annotations

import random
from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.combat import apply_world_enemy_mods, pick_monster
from game.domain.encounters import mark_monster_seen, resolve_approach
from game.domain.equipment import recompute_stats
from game.domain.narrative import emit_narrative, narrate_field
from game.domain.party import (
    add_member,
    apply_party_passives_to_player,
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


def _handle_monster_talk(
    player: Dict[str, Any],
    mon: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    *,
    sight: Optional[Dict[str, Any]] = None,
) -> None:
    """
    MI3: soft talk / negotiate with a monster (usually intel_tier ≥ 2).
    Outcomes: truce · tip · tribute · flee · combat · ambush · walk.
    """
    from game.domain.monster_ai import (
        apply_talk_rewards,
        resolve_monster_talk,
        talk_eligible,
    )
    from game.ui_terminal.layout import render_box

    mon_name = str(
        (sight or {}).get("label")
        or mon.get("name")
        or mon.get("base_name")
        or "???"
    )
    eligible = talk_eligible(mon)
    if not eligible:
        # beast rare_talk: legacy one-liner (no menu)
        io.write_line("สิ่งมีชีวิตนั้น... ส่งเสียงเหมือนพูด? ได้ชำนาญพื้นที่งอกเงย")
        io.write_line(approach_outcome_line("monster", "rare_talk"))
        for note in apply_talk_rewards(player, mon, "truce", rng, reg=reg):
            io.write_line(note)
        mark_monster_seen(player, mon)
        _emit_personality_notes(io, personality_event(player, "approach_polite", reg))
        return

    io.write_line(f"  {mon_name}… ไม่พุ่งทันที — เหมือนรอการตอบสนอง")
    io.write_line(approach_outcome_line("monster", "rare_talk"))
    box = [
        " สื่อสาร (soft)",
        "---",
        "  1  พูดสงบ / ลดอาวุธ",
        "  2  ยื่นของขวัญเล็กน้อย (เงินโลก)",
        "  3  ข่มขู่",
        "  4  เดินจากไปช้าๆ",
        "---",
        "  (ผลไม่แน่นอน · ไม่โชว์%)",
    ]
    io.write_line()
    io.write_line(render_box(box, double=False))
    ch = io.read_line("\n  เลือก (1–4): ").strip()
    style_map = {"1": "calm", "2": "gift", "3": "threaten", "4": "walk"}
    style = style_map.get(ch, "calm")
    if ch in ("0", ""):
        style = "walk"

    outcome, lines = resolve_monster_talk(mon, player, style, rng, reg=reg)
    for line in lines:
        if line:
            io.write_line(f"  {line}" if not str(line).startswith(" ") else line)

    if outcome in ("combat", "ambush"):
        io.write_line(approach_outcome_line("monster", outcome if outcome == "ambush" else "fair_combat"))
        mark_monster_seen(player, mon)
        if style == "threaten":
            _emit_personality_notes(io, personality_event(player, "approach_threaten", reg))
        _run_combat(
            player, reg, io, rng, mon=mon, ambush=(outcome == "ambush")
        )
        return

    # peaceful-ish ends
    for note in apply_talk_rewards(player, mon, outcome, rng, reg=reg):
        io.write_line(note)
    mark_monster_seen(player, mon)
    if style == "gift":
        _emit_personality_notes(io, personality_event(player, "approach_gift", reg))
    elif style == "threaten":
        _emit_personality_notes(io, personality_event(player, "approach_threaten", reg))
    elif style == "walk":
        _emit_personality_notes(io, personality_event(player, "approach_cautious", reg))
    else:
        _emit_personality_notes(io, personality_event(player, "approach_polite", reg))
    if outcome == "flee":
        io.write_line(approach_outcome_line("monster", "flee"))
    else:
        io.write_line("  ▸ ผล: การเผชิญหน้าจบโดยไม่ต้องฆ่าจบ")

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
    nm = other.get("name") or "เงานิรนาม"
    io.write_line(f"\nคุณพบเงาในโลกนี้: เงา·{nm}")
    io.write_line(f"  สายที่สังเกตได้: {other.get('occ_path') or other.get('occupation') or '???'}")
    if other.get("soft_titles"):
        io.write_line(f"  ฉายาเลือน: {other['soft_titles'][0]}")
    io.write_line("  (echo จากบันทึกโลก — ไม่แสดงเลเวล/ค่าพลัง · ไม่ทำร้ายเซฟเจ้าของ)")

    # WO-024: Relic Aura soft gate before normal approach
    try:
        from game.domain.divine_burden import (
            apply_echo_relic_reaction,
            should_prompt_relic_aura,
            soft_echo_relic_menu_hint,
        )

        show_aura, aura_why = should_prompt_relic_aura(player, other, reg)
        if show_aura:
            io.write_line(f"  〔ออร่าเรลิก〕 {aura_why}")
            for ln in soft_echo_relic_menu_hint(player, reg):
                if ln.strip():
                    io.write_line(ln if ln.startswith(" ") else f" {ln}")
            io.write_line("  R ถอยห่าง   H นอบน้อม   A ก้าวร้าว   Enter เข้าหาตามปกติ")
            aura_ch = io.read_line("  ออร่า> ").strip().lower()
            if aura_ch in ("r", "retreat", "ถอย"):
                for ln in apply_echo_relic_reaction(player, "retreat", rng=rng):
                    io.write_line(ln)
                try:
                    from game.domain.world_relations import on_echo_approach

                    for ln in on_echo_approach(player, choice="retreat"):
                        io.write_line(ln)
                except Exception:
                    pass
                io.write_line("คุณถอยห่างจากเงา...")
                return
            if aura_ch in ("h", "humble", "นอบน้อม", "bow"):
                for ln in apply_echo_relic_reaction(player, "humble", rng=rng):
                    io.write_line(ln)
                # humble → bias next social toward polite
                player["_echo_approach_bias"] = "polite"
                try:
                    from game.domain.world_relations import on_echo_approach

                    for ln in on_echo_approach(player, choice="humble"):
                        io.write_line(ln)
                except Exception:
                    pass
            elif aura_ch in ("a", "aggro", "ก้าวร้าว", "fight"):
                for ln in apply_echo_relic_reaction(player, "aggro", rng=rng):
                    io.write_line(ln)
                player["_echo_approach_bias"] = "hostile"
                try:
                    from game.domain.world_relations import on_echo_approach

                    for ln in on_echo_approach(player, choice="aggro"):
                        io.write_line(ln)
                except Exception:
                    pass
            # else continue into normal approach
    except Exception:
        pass

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
    # WO-024: soft bias from aura menu
    bias = str(player.pop("_echo_approach_bias", "") or "")
    if bias == "polite" and aid in ("hostile", "threat", "challenge"):
        aid = "polite"
        io.write_line("  (ท่าทางผ่อนลงหลังนอบน้อม)")
    elif bias == "hostile" and aid in ("polite", "gift", "friendly"):
        # keep player choice but mark foeish later via affinity noise
        player["_relic_aura_hostile"] = True
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
        io.write_line(f"\n⚔ เงา·{other.get('name')} กลายเป็นศัตรู!")
        io.write_line("(สู้กับ snapshot — เซฟเจ้าของเงาไม่ถูกแก้)")
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

    # WO-039: Faction Mini-Moments
    if kind == "faction_moment":
        try:
            from game.domain.faction_moments import run_moment_menu

            io.write_line()
            io.write_line(f"── {sight.get('label') or 'สายตาโลก'} ──")
            run_moment_menu(player, sight, io, reg=reg)
        except Exception as e:
            io.write_line(f"  …สายตาโลกจาง ({e})")
        return

    # WO-Shop-5: shop reputation soft events
    if kind == "shop_rep_event":
        try:
            from game.domain.shop_rep_content import run_shop_rep_event_menu

            io.write_line()
            io.write_line(f"── {sight.get('label') or 'เหตุการณ์ร้าน'} ──")
            run_shop_rep_event_menu(player, sight, io, reg=reg)
        except Exception as e:
            io.write_line(f"  …เหตุการณ์ร้านจาง ({e})")
        return

    if kind == "companion":
        emit_narrative(io, narrate_field(reg, "party_recruit", rng, name=sight.get("label")))
        io.write_line(f"\nเข้าหา: {sight.get('label')} ({sight.get('hint')})")
        io.write_line("  เงาจ้องคุณ — ยื่นมือรับร่วมทาง? (ต้องได้รับการยอมรับ · อาจมีราคา)")
        if io.read_line("1=ยื่นมือ  อื่น=เดินจาก: ").strip() != "1":
            emit_narrative(io, narrate_field(reg, "party_reject", rng, name=sight.get("label")))
            return
        tpl = sight.get("companion_template")
        if not isinstance(tpl, dict):
            tid = str(sight.get("companion_template_id") or "")
            from game.domain.party import template_by_id
            tpl = template_by_id(reg, tid) or {}
        if not tpl:
            io.write_line("  เงาจางหาย...")
            return
        from game.domain.party import attempt_join_template, apply_party_passives_to_player
        from game.domain.equipment import recompute_stats
        ok, notes = attempt_join_template(player, reg, tpl, rng)
        for n in notes:
            io.write_line(n if str(n).startswith(" ") or "✦" in str(n) else f"  {n}")
        if ok:
            emit_narrative(io, narrate_field(reg, "party_join", rng, name=tpl.get("name")))
            apply_party_passives_to_player(player, reg)
            recompute_stats(player, reg)
        else:
            emit_narrative(io, narrate_field(reg, "party_reject", rng, name=tpl.get("name") or sight.get("label")))
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
        # MI3: smart monsters bias approach (talk / flee / ambush soft)
        try:
            from game.domain.monster_ai import bias_monster_approach

            outcome = bias_monster_approach(outcome, mon, player, rng)
        except Exception:
            pass
        emit_narrative(io, narrate_field(reg, "approach_monster", rng))
        io.write_line(f"\nเข้าหา: {sight.get('label')} ({sight.get('hint')})")
        if outcome == "flee":
            io.write_line("มันหนีไป... คุณจำเค้าโครงได้เพียงเลือนราง")
            io.write_line(approach_outcome_line("monster", "flee"))
            mark_monster_seen(player, mon)
        elif outcome == "rare_talk":
            _handle_monster_talk(player, mon, reg, io, rng, sight=sight)
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

        # WO-038: world relations soft from NPC outcome
        def _wr_npc(oc: str) -> None:
            try:
                from game.domain.world_relations import on_npc_outcome

                aid = str(player.get("location") or "")
                for ln in on_npc_outcome(
                    player, outcome=oc, archetype=str(arch or ""), area_id=aid
                ):
                    io.write_line(ln)
            except Exception:
                pass

        if outcome == "hostile" or outcome == "trap_disguise":
            emit_narrative(io, narrate_field(reg, "npc_outcome_hostile", rng))
            io.write_line("เป็นศัตรู!" if outcome == "hostile" else "หน้ากากหลุด — มอนปลอมคน!")
            io.write_line(approach_outcome_line("npc", str(outcome)))
            personality_event(player, "npc_hostile", reg)
            _wr_npc("hostile")
            _run_combat(player, reg, io, rng, ambush=True)
        elif outcome == "shop":
            emit_narrative(io, narrate_field(reg, "npc_outcome_shop", rng))
            emit_narrative(io, narrate_field(reg, "shop", rng))
            io.write_line("พบพ่อค้า!")
            io.write_line(approach_outcome_line("npc", "shop"))
            personality_event(player, "npc_shop", reg)
            _wr_npc("shop")
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
            _wr_npc("friend")
            atk_b = 2 + (1 if float(mod.get("compatibility") or 0) > 0.4 else 0)
            player["bonus_atk"] = int(player.get("bonus_atk", 0)) + atk_b
            player["blessings"] = list(player.get("blessings") or []) + ["เพื่อนเดินทาง"]
            player["blessing_turns"] = max(int(player.get("blessing_turns", 0)), 3 + atk_b)
        elif outcome == "master":
            personality_event(player, "npc_master", reg)
            emit_narrative(io, narrate_field(reg, "npc_outcome_master", rng))
            io.write_line("✨ พบอาจารย์!")
            io.write_line(approach_outcome_line("npc", "master"))
            _wr_npc("master")
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
                io.write_line(grant_library_key(player))
            player["blessings"] = list(player.get("blessings") or []) + ["พรอาจารย์"]
            player["blessing_turns"] = max(int(player.get("blessing_turns", 0)), 8)
            player["disciple_of"] = "อาจารย์พเนจร"
        else:
            emit_narrative(io, narrate_field(reg, "npc_outcome_ignore", rng))
            io.write_line("เขาไม่สนใจคุณ...")
            io.write_line(approach_outcome_line("npc", "ignore"))
            _wr_npc("ignore")
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
            # module-level import only — local import made grant_library_key
            # UnboundLocalError on this branch (rare_relic before master branch)
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


