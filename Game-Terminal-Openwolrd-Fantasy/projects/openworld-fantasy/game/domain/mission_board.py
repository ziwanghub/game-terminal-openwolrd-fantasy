"""
Mission board funded by market tax.
Ranks: F < E < D < C < B < A < S < SS < SSS
Special missions: hidden eligibility — player self-assesses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry
from game.domain.market import get_tax_fund, load_market, save_market, withdraw_tax_fund

RANK_ORDER = ["F", "E", "D", "C", "B", "A", "S", "SS", "SSS"]


def _cfg(reg: DataRegistry) -> Dict[str, Any]:
    return dict(getattr(reg, "mission_board", None) or {})


def rank_index(rank: str) -> int:
    r = str(rank or "F").upper()
    try:
        return RANK_ORDER.index(r)
    except ValueError:
        return 0


def ensure_mission_player(player: MutableMapping[str, Any]) -> None:
    player.setdefault("mission_rank", "F")
    player.setdefault("mission_rank_xp", 0)
    player.setdefault("mission_accepts", 0)
    player.setdefault("mission_completes", 0)
    player.setdefault("board_mission", None)  # active
    player.setdefault("board_missions_done", [])


def player_rank(player: Mapping[str, Any]) -> str:
    ensure_mission_player(player)  # type: ignore
    r = str(player.get("mission_rank") or "F").upper()
    return r if r in RANK_ORDER else "F"


def can_accept_rank(player: Mapping[str, Any], mission_rank: str) -> bool:
    """Normal missions: player rank >= mission rank."""
    return rank_index(player_rank(player)) >= rank_index(mission_rank)


def special_eligible(player: Mapping[str, Any], mission: Mapping[str, Any]) -> bool:
    """
    Hidden gates for special missions — never explained to player.
    Soft multi-factor: level, kills, intel, luck, mission history.
    """
    if not mission.get("special"):
        return True
    st = player.get("stats") or {}
    lv = int(player.get("level") or 1)
    kills = int(st.get("kills") or 0)
    completes = int(player.get("mission_completes") or 0)
    intel = int(player.get("intel_current") or player.get("intel_max") or 0)
    luck = float(player.get("luck_score") or 0)
    mr = rank_index(player_rank(player))
    need = rank_index(str(mission.get("rank") or "C"))
    # must be near rank
    if mr < need - 1:
        return False
    score = 0
    if lv >= 4 + need:
        score += 1
    if kills >= 5 + need * 3:
        score += 1
    if completes >= 2 + need:
        score += 1
    if intel >= 2 + need // 2:
        score += 1
    if luck > 0.05:
        score += 1
    if "fox_luck" in (player.get("blessing_flags") or []):
        score += 1
    # threshold soft by difficulty
    need_score = 2 + max(0, need - 2) // 2
    return score >= need_score


def _chain_unlocked(player: Mapping[str, Any], mission: Mapping[str, Any]) -> bool:
    """requires_done: soft story chain — prior mission id(s) must be finished."""
    need = mission.get("requires_done")
    if not need:
        return True
    done = set(player.get("board_missions_done") or [])
    if isinstance(need, str):
        return need in done
    if isinstance(need, (list, tuple)):
        return all(str(x) in done for x in need)
    return True


def list_visible_missions(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Dict[str, Any]]:
    """Missions player may attempt to take (rank filter + special soft + chain)."""
    ensure_mission_player(player)  # type: ignore
    missions = list((_cfg(reg).get("missions") or []))
    out: List[Dict[str, Any]] = []
    done = set(player.get("board_missions_done") or [])
    active = (player.get("board_mission") or {}).get("id")
    for m in missions:
        mid = str(m.get("id") or "")
        if mid == active:
            continue
        # allow repeat non-special after done? once per id for v1 except F/E
        if mid in done and rank_index(str(m.get("rank") or "F")) >= rank_index("C"):
            continue
        if not _chain_unlocked(player, m):
            # chain locked — hidden (no spoiler of next chapter)
            continue
        if m.get("special"):
            if special_eligible(player, m):
                out.append(dict(m))
            # else hidden completely — player never sees
            continue
        if can_accept_rank(player, str(m.get("rank") or "F")):
            out.append(dict(m))
    return out


def _snapshot_progress(player: Mapping[str, Any], mtype: str) -> int:
    st = player.get("stats") or {}
    if mtype == "kill":
        return int(st.get("kills") or 0)
    if mtype == "explore":
        return int(st.get("explores") or 0)
    if mtype == "rest":
        return int(st.get("rests") or 0)
    if mtype == "travel":
        return int(st.get("travels") or 0)
    if mtype == "kill_boss":
        return int(st.get("boss_kills") or 0) or len(player.get("bosses_defeated") or [])
    if mtype == "dungeon_clear":
        return len(player.get("dungeons_cleared") or [])
    return 0


def accept_mission(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    mission_id: str,
    *,
    world_id: Optional[str] = None,
) -> Tuple[bool, str]:
    ensure_mission_player(player)
    if player.get("board_mission"):
        return False, "มีภารกิจกระดานค้างอยู่ — ทำให้เสร็จหรือละทิ้งก่อน"
    world_id = world_id or str(player.get("world_id") or "default")
    missions = {str(m.get("id")): m for m in (_cfg(reg).get("missions") or [])}
    m = missions.get(str(mission_id))
    if not m:
        return False, "ไม่พบภารกิจ"
    if not _chain_unlocked(player, m):
        return False, "…ยังไม่ถึงบทนี้ (หรือยังไม่ครบบางเงื่อนไขที่มองไม่เห็น)"
    if m.get("special") and not special_eligible(player, m):
        return False, "…คุณรู้สึกว่ายังไม่ใช่จังหวะ (หรือยังไม่ถูกเรียก)"
    if not m.get("special") and not can_accept_rank(player, str(m.get("rank") or "F")):
        return False, f"แรงก์กระดานคุณ ({player_rank(player)}) ยังรับงานแรงก์ {m.get('rank')} ไม่ได้"

    wage = int(m.get("wage_cost") or 0)
    fund = get_tax_fund(world_id)
    paid = 0
    if wage > 0:
        paid = withdraw_tax_fund(world_id, wage)
    mtype = str(m.get("type") or "kill")
    player["board_mission"] = {
        "id": m.get("id"),
        "name": m.get("name"),
        "rank": m.get("rank"),
        "type": mtype,
        "target": int(m.get("target") or 1),
        "start_stat": _snapshot_progress(player, mtype),
        "reward_money": int(m.get("reward_money") or 0),
        "reward_xp": int(m.get("reward_xp") or 0),
        "reward_items": list(m.get("reward_items") or []),
        "wage_paid": paid,
        "wage_cost": wage,
        "special": bool(m.get("special")),
        "desc": m.get("desc"),
    }
    player["mission_accepts"] = int(player.get("mission_accepts") or 0) + 1
    notes = f"รับงาน 「{m.get('name')}」 แรงก์ {m.get('rank')}"
    if paid < wage:
        notes += " · (งบค่าจ้างจากภาษีตลาดไม่เต็ม — รางวัลยังตามประกาศ)"
    elif paid > 0:
        notes += f" · ใช้งบภาษีตลาด {paid} เป็นค่าจ้างประกาศ"
    return True, notes


def abandon_mission(player: MutableMapping[str, Any]) -> str:
    ensure_mission_player(player)
    if not player.get("board_mission"):
        return "ไม่มีภารกิจค้าง"
    name = (player.get("board_mission") or {}).get("name")
    player["board_mission"] = None
    # soft rank penalty none — just lose progress
    return f"ละทิ้ง 「{name}」 — ไม่มีบทลงโทษชัด (เสียเวลาเอง)"


def check_mission_progress(player: MutableMapping[str, Any]) -> Tuple[int, int, bool]:
    """Returns (current_delta, target, complete)."""
    ensure_mission_player(player)
    bm = player.get("board_mission")
    if not bm:
        return 0, 0, False
    mtype = str(bm.get("type") or "kill")
    start = int(bm.get("start_stat") or 0)
    now = _snapshot_progress(player, mtype)
    delta = max(0, now - start)
    target = int(bm.get("target") or 1)
    return delta, target, delta >= target


def complete_mission_if_done(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """Call after kills/explore etc. Grants rewards + rank XP."""
    ensure_mission_player(player)
    delta, target, done = check_mission_progress(player)
    if not done:
        return []
    bm = dict(player.get("board_mission") or {})
    notes: List[str] = [f"✔ เคลียร์กระดาน: {bm.get('name')} (แรงก์ {bm.get('rank')})"]
    mon = int(bm.get("reward_money") or 0)
    # soft scale if tax was thin — still pay full from "system" (tax already spent as wage)
    player["money_world"] = int(player.get("money_world") or 0) + mon
    notes.append(f"  รางวัลเงินโลก +{mon}")
    xp = int(bm.get("reward_xp") or 0)
    if xp > 0:
        try:
            from game.domain.leveling import grant_xp

            summary = grant_xp(player, xp, getattr(reg, "levels", None))
            notes.append(f"  XP +{xp}")
            notes.extend(summary.get("notes") or [])
        except Exception:
            notes.append(f"  XP +{xp} (บันทึก)")
    for iid in bm.get("reward_items") or []:
        try:
            from game.domain.equipment import add_item

            add_item(player, str(iid), reg)
            notes.append(f"  ได้ {(reg.items.get(iid) or {}).get('name', iid)}")
        except Exception:
            pass
    # rank progress — frequent accepts/completes raise rank
    player["mission_completes"] = int(player.get("mission_completes") or 0) + 1
    done_ids = list(player.get("board_missions_done") or [])
    mid = str(bm.get("id") or "")
    if mid and mid not in done_ids:
        done_ids.append(mid)
    player["board_missions_done"] = done_ids
    player["board_mission"] = None
    notes.extend(_grant_rank_xp(player, reg, rank=str(bm.get("rank") or "F")))
    # world quests that track board clears
    try:
        from game.domain.quests import bump_quest

        notes.extend(bump_quest(player, reg, "board_complete"))
    except Exception:
        pass
    return notes


def _grant_rank_xp(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    rank: str,
) -> List[str]:
    """More completes at higher ranks grant more board rank XP."""
    notes: List[str] = []
    cur = player_rank(player)
    xp = int(player.get("mission_rank_xp") or 0)
    gain = 1 + rank_index(rank) // 2
    # frequent board use bonus
    accepts = int(player.get("mission_accepts") or 0)
    if accepts >= 5:
        gain += 1
    xp += gain
    player["mission_rank_xp"] = xp
    need_tbl = (_cfg(reg).get("rank_xp_to_next") or {})
    need = int(need_tbl.get(cur) or 5)
    if xp >= need and rank_index(cur) < len(RANK_ORDER) - 1:
        nxt = RANK_ORDER[rank_index(cur) + 1]
        player["mission_rank"] = nxt
        player["mission_rank_xp"] = xp - need
        notes.append(
            f"✦ แรงก์กระดานภารกิจ: {cur} → {nxt} "
            f"(รับงานบ่อย + สำเร็จ — เกณฑ์จริงไม่เปิดเผยทั้งหมด)"
        )
    else:
        notes.append(f"  ความน่าเชื่อถือกระดาน +{gain} (แรงก์ {cur})")
    return notes


def format_board_status(player: Mapping[str, Any], world_id: str) -> List[str]:
    ensure_mission_player(player)  # type: ignore
    lines = [
        f"── ประกาศภารกิจ ──",
        f" แรงก์คุณ: {player_rank(player)}  ·  รับงาน {player.get('mission_accepts', 0)} ครั้ง · "
        f"สำเร็จ {player.get('mission_completes', 0)}",
        f" กองทุนค่าจ้าง (จากภาษีตลาด): {get_tax_fund(world_id)} เงินโลก",
    ]
    bm = player.get("board_mission")
    if bm:
        d, t, _ = check_mission_progress(player)  # type: ignore
        lines.append(f" งานค้าง: {bm.get('name')} [{bm.get('rank')}]  {d}/{t}")
        if bm.get("desc"):
            lines.append(f"  {bm.get('desc')}")
    lines.append("  (แรงก์สูงขึ้นเมื่อมารับ/เคลียร์งานบ่อย — พิเศษต้องประเมินเอง)")
    return lines
