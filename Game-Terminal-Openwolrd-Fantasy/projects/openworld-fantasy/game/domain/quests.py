"""Light quest tracking and rewards."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from game.data_load.registry import DataRegistry
from game.domain.equipment import add_item
from game.domain.leveling import grant_xp


def _deps_met(player: Mapping[str, Any], q: Mapping[str, Any]) -> bool:
    done = set(player.get("quests_done") or [])
    for dep in q.get("depends_on") or []:
        if dep not in done:
            return False
    return True


def ensure_quests(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    player.setdefault("quests", {})
    player.setdefault("quests_done", [])
    player.setdefault("bosses_defeated", [])
    player.setdefault("stats", {})
    qstate: Dict[str, Any] = dict(player["quests"])
    lv = int(player.get("level", 1))
    kills = int((player.get("stats") or {}).get("kills") or 0)
    travels = int((player.get("stats") or {}).get("travels") or 0)
    board_n = int(player.get("mission_completes") or 0)
    for qid, q in reg.quests.items():
        if qid in player["quests_done"]:
            continue
        if int(q.get("unlock_level", 1)) > lv:
            continue
        if not _deps_met(player, q):
            continue
        qtype = str(q.get("type") or "")
        target = int(q.get("target", 1))
        if qid not in qstate:
            # Backfill progress from lifetime stats when quest first unlocks
            prog = 0
            if qtype == "kill":
                prog = kills
            elif qtype == "travel":
                prog = travels
            elif qtype == "board_complete":
                prog = board_n
            qstate[qid] = {
                "progress": min(prog, target),
                "completed": False,
            }
        else:
            # Keep kill/travel/board aligned with lifetime stats (never go backwards)
            st = dict(qstate[qid])
            if not st.get("completed"):
                cur = int(st.get("progress") or 0)
                if qtype == "kill" and kills > cur:
                    st["progress"] = min(kills, target)
                    qstate[qid] = st
                elif qtype == "travel" and travels > cur:
                    st["progress"] = min(travels, target)
                    qstate[qid] = st
                elif qtype == "board_complete" and board_n > cur:
                    st["progress"] = min(board_n, target)
                    qstate[qid] = st
    player["quests"] = qstate
    # auto-complete any newly unlocked quests already at target
    for qid, st in list(qstate.items()):
        if st.get("completed") or qid in player["quests_done"]:
            continue
        q = reg.quests.get(qid) or {}
        if int(st.get("progress") or 0) >= int(q.get("target", 1)):
            complete_quest(player, reg, qid, qstate)
    # second unlock pass after auto-complete (deps may open)
    qstate = dict(player.get("quests") or {})
    done = set(player.get("quests_done") or [])
    kills = int((player.get("stats") or {}).get("kills") or 0)
    travels = int((player.get("stats") or {}).get("travels") or 0)
    board_n = int(player.get("mission_completes") or 0)
    for qid, q in reg.quests.items():
        if qid in done or qid in qstate:
            continue
        if int(q.get("unlock_level", 1)) > lv:
            continue
        if not _deps_met(player, q):
            continue
        qtype = str(q.get("type") or "")
        prog = 0
        if qtype == "kill":
            prog = kills
        elif qtype == "travel":
            prog = travels
        elif qtype == "board_complete":
            prog = board_n
        target = int(q.get("target", 1))
        qstate[qid] = {"progress": min(prog, target), "completed": False}
        if prog >= target:
            complete_quest(player, reg, qid, qstate)
            qstate = dict(player.get("quests") or {})
    player["quests"] = dict(player.get("quests") or qstate)


def bump_quest(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    event: str,
    *,
    area_id: Optional[str] = None,
    amount: int = 1,
) -> List[str]:
    """
    event: kill | explore | rest | kill_area | travel | equip_weapon | socket_card | kill_boss | craft | dungeon_clear
    Optional kwargs via amount; boss_id/area_id for filters.
    """
    ensure_quests(player, reg)
    notes: List[str] = []
    qstate = dict(player.get("quests") or {})
    boss_id = None
    # allow boss_id passed as area_id misuse — use separate via player temp
    for qid, st in list(qstate.items()):
        if st.get("completed") or qid in (player.get("quests_done") or []):
            continue
        q = reg.quests.get(qid) or {}
        if not _deps_met(player, q) and qid not in qstate:
            continue
        qtype = str(q.get("type") or "")
        match = False
        if event == "kill" and qtype == "kill":
            match = True
        elif event == "kill" and qtype == "kill_area" and area_id == q.get("area"):
            match = True
        elif event == "explore" and qtype == "explore_area" and area_id == q.get("area"):
            match = True
        elif event == "rest" and qtype == "rest":
            match = True
        elif event == "travel" and qtype == "travel":
            match = True
        elif event == "equip_weapon" and qtype == "equip_weapon":
            match = True
        elif event == "socket_card" and qtype == "socket_card":
            match = True
        elif event == "craft" and qtype == "craft":
            match = True
        elif event == "dungeon_clear" and qtype == "dungeon_clear":
            if not q.get("dungeon_id") or area_id == q.get("dungeon_id"):
                match = True
        elif event == "kill_boss" and qtype == "kill_boss":
            # area_id here carries boss_id when event is kill_boss
            if area_id and area_id == q.get("boss_id"):
                match = True
            elif not q.get("boss_id"):
                match = True
        elif event == "board_complete" and qtype == "board_complete":
            match = True
        elif event == "help_open" and qtype == "help_open":
            match = True
        elif event == "help_assist" and qtype == "help_assist":
            match = True
        if not match:
            continue
        st = dict(st)
        st["progress"] = int(st.get("progress", 0)) + amount
        target = int(q.get("target", 1))
        qstate[qid] = st
        if st["progress"] >= target:
            notes.extend(complete_quest(player, reg, qid, qstate))
    player["quests"] = qstate
    # unlock newly available quests after completion
    ensure_quests(player, reg)
    return notes


def complete_quest(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    qid: str,
    qstate: Optional[Dict[str, Any]] = None,
) -> List[str]:
    q = reg.quests.get(qid) or {}
    qstate = qstate if qstate is not None else dict(player.get("quests") or {})
    st = dict(qstate.get(qid) or {})
    if st.get("completed") or qid in (player.get("quests_done") or []):
        return []
    st["completed"] = True
    st["progress"] = int(q.get("target", 1))
    qstate[qid] = st
    player["quests"] = qstate
    done = list(player.get("quests_done") or [])
    if qid not in done:
        done.append(qid)
    player["quests_done"] = done

    lines = [f"✔ เควสสำเร็จ: {q.get('name', qid)}"]
    if q.get("marks_round"):
        player["campaign_round"] = max(
            int(player.get("campaign_round") or 0),
            int(q.get("marks_round") or 1),
        )
        lines.append(f"  ✦ ปิดรอบโลกที่ {player['campaign_round']} (soft)")
    if q.get("campaign"):
        chs = list(player.get("campaign_chapters") or [])
        chap = str(q.get("chapter") or "")
        if chap and chap not in chs:
            chs.append(chap)
            player["campaign_chapters"] = chs
    try:
        from game.domain.stats import bump_stat

        bump_stat(player, "quests_completed", 1)
    except Exception:
        pass
    try:
        from game.domain.personality import apply_event as personality_event

        lines.extend(personality_event(player, "quest_complete", reg))
    except Exception:
        pass
    xp = int(q.get("reward_xp", 0))
    if xp:
        wmod = float((player.get("world_modifiers") or {}).get("xp_mult", 1.0))
        xp = max(1, int(round(xp * wmod)))
        summary = grant_xp(player, xp, reg.levels)
        lines.append(f"  รางวัล XP +{summary['gained']}")
        for n in summary["notes"]:
            lines.append(f"  {n}")
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "xp_gained_total", summary["gained"])
        except Exception:
            pass
    # WO-052: quest completion fuels auto growth (Lv30+)
    try:
        from game.domain.auto_growth import is_auto_growth_mode, pulse_auto_growth

        if is_auto_growth_mode(player):
            for gn in pulse_auto_growth(player, "quest", reg=reg, magnitude=1.2):
                lines.append(gn)
    except Exception:
        pass
    money = int(q.get("reward_money", 0))
    if money:
        money_m = float((player.get("world_modifiers") or {}).get("money_mult", 1.0))
        money = max(1, int(round(money * money_m)))
        player["money_world"] = int(player.get("money_world", 0)) + money
        lines.append(f"  เงินโลก +{money}")
        try:
            from game.domain.stats import bump_stat

            bump_stat(player, "money_gained_total", money)
        except Exception:
            pass
    # WO-021: optional special currency from quests (not combat RNG only)
    mh = int(q.get("reward_money_heaven") or q.get("reward_heaven") or 0)
    if mh > 0:
        player["money_heaven"] = int(player.get("money_heaven") or 0) + mh
        lines.append(f"  เงินสวรรค์ +{mh}")
    ml = int(q.get("reward_money_hell") or q.get("reward_hell") or 0)
    if ml > 0:
        player["money_hell"] = int(player.get("money_hell") or 0) + ml
        lines.append(f"  เงินนรก +{ml}")
    for iid in q.get("reward_items") or []:
        name = add_item(player, str(iid), reg)
        lines.append(f"  ได้ {name}")
    # WO-Shop-5: shop reputation reward (soft label, no raw number)
    try:
        shop_id = str(q.get("shop_id") or q.get("reward_shop_id") or "")
        rep_amt = int(q.get("reward_shop_rep") or q.get("shop_rep") or 0)
        if shop_id and rep_amt > 0:
            from game.domain.shop_experience import (
                bump_shop_rep,
                get_shop_rep,
                shop_rep_soft_label,
            )

            bump_shop_rep(player, shop_id, amount=max(5, min(15, rep_amt)), reason="quest")
            sname = shop_id
            sdef = (getattr(reg, "shops", None) or {}).get(shop_id) or {}
            if sdef.get("name"):
                sname = str(sdef["name"])
            lines.append(
                f"  ความคุ้น「{sname}」ดีขึ้น 〔{shop_rep_soft_label(get_shop_rep(player, shop_id))}〕"
            )
    except Exception:
        pass
    # L3: sealed chest + hidden flags
    try:
        from game.domain.chest_loot import apply_reward_block

        lines.extend(
            apply_reward_block(
                player,
                reg,
                q,
                seed_salt=f"quest|{qid}",
            )
        )
    except Exception:
        pass
    return lines


def list_quest_lines(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_quests(player, reg)  # type: ignore
    lines = []
    qstate = player.get("quests") or {}
    for qid, st in qstate.items():
        if st.get("completed"):
            continue
        q = reg.quests.get(qid) or {}
        prog = int(st.get("progress", 0))
        target = int(q.get("target", 1))
        chain = ""
        deps = q.get("depends_on") or []
        if deps:
            chain = f" [สาย: {', '.join(deps)}]"
        hint = ""
        if str(q.get("type") or "") == "kill":
            kills = int((player.get("stats") or {}).get("kills") or 0)
            if kills > 0 and prog < target:
                left = max(0, target - prog)
                hint = f" · เหลืออีก ~{left} ครั้ง"
        soft = str(q.get("soft_hint") or "").strip()
        soft_bit = f"  〔{soft}〕" if soft else ""
        lines.append(
            f" · {q.get('name')}: {prog}/{target} — {q.get('description')}{chain}{hint}"
        )
        if soft_bit:
            lines.append(f"   {soft_bit}")
    # show locked chain hints
    done = set(player.get("quests_done") or [])
    lv = int(player.get("level", 1))
    locked = []
    for qid, q in reg.quests.items():
        if qid in done or qid in qstate:
            continue
        if int(q.get("unlock_level", 1)) > lv:
            locked.append(f"   🔒 {q.get('name')} (Lv.{q.get('unlock_level')})")
        elif not _deps_met(player, q):
            locked.append(f"   🔒 {q.get('name')} (ต้องทำ: {', '.join(q.get('depends_on') or [])})")
    if not lines:
        lines.append(" · (ไม่มีเควสค้าง)")
    if locked:
        lines.append(" ยังล็อก:")
        lines.extend(locked[:6])
    if done:
        lines.append(f" สำเร็จแล้ว: {len(done)} เควส")
    # soft campaign / round goal
    rnd = int(player.get("campaign_round") or 0)
    chs = list(player.get("campaign_chapters") or [])
    camp_active = [
        qid
        for qid, q in reg.quests.items()
        if q.get("campaign") and qid not in done and qid in qstate
    ]
    if rnd or chs or camp_active:
        lines.append("── รอบเรื่อง (soft) ──")
        if rnd:
            lines.append(f" รอบที่ปิดแล้ว: {rnd}")
        if chs:
            lines.append(f" บทที่เปิดแล้ว: {', '.join(chs)}")
        if camp_active:
            lines.append(f" สายเรื่องค้าง: {len(camp_active)} เควส")
        else:
            lines.append(" (ยังไม่มีสายเรื่องค้าง — สำรวจ/กระดาน/บอสเพื่อเปิดต่อ)")
    return lines

