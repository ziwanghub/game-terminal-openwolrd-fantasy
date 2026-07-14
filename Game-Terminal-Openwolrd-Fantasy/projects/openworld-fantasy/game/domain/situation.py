"""
Player situation layer — crisis on owner save + help consent + offer/escrow + resolve.

H0: situation + open/close consent
H1: list open signals in world
H2: gold/item offer escrow
H3: claim, assist resolve, pay helper, owner inbox + chronicle
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

HELP_STATUS_CLOSED = "closed"
HELP_STATUS_OPEN = "open"
HELP_STATUS_CLAIMED = "claimed"
HELP_STATUS_RESOLVED = "resolved"

POLICY_PUBLIC = "public"
POLICY_FRIENDS = "friends"
DEFAULT_SLOTS = 1


def ensure_situation_fields(player: MutableMapping[str, Any]) -> None:
    if "situation" not in player or player.get("situation") is None:
        player["situation"] = None
    player.setdefault("world_inbox", [])
    if not isinstance(player.get("world_inbox"), list):
        player["world_inbox"] = []
    player.setdefault("help_rep", 0)
    player.setdefault("help_assists", 0)
    player.setdefault("help_requests", 0)
    player.setdefault("social_memory", {})


def get_situation(player: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    sit = player.get("situation")
    return dict(sit) if isinstance(sit, dict) and sit.get("kind") else None


def help_block(player: Mapping[str, Any]) -> Dict[str, Any]:
    sit = get_situation(player) or {}
    h = sit.get("help")
    return dict(h) if isinstance(h, dict) else {}


def help_is_open(player: Mapping[str, Any]) -> bool:
    h = help_block(player)
    return bool(h.get("open")) and str(h.get("status") or "") in (
        HELP_STATUS_OPEN,
        HELP_STATUS_CLAIMED,
    )


def help_is_claimable(player: Mapping[str, Any]) -> bool:
    h = help_block(player)
    return bool(h.get("open")) and str(h.get("status") or "") == HELP_STATUS_OPEN


def clear_situation(player: MutableMapping[str, Any]) -> None:
    ensure_situation_fields(player)
    player["situation"] = None


def _severity_from_dungeon_run(run: Mapping[str, Any]) -> str:
    left = int(run.get("turns_left") or 0)
    tmax = max(1, int(run.get("turns_max") or 1))
    ratio = left / tmax
    floor = int(run.get("floor") or 1)
    floors = max(1, int(run.get("floors") or 1))
    if left <= 0 or ratio <= 0.2:
        return "critical"
    if ratio <= 0.4 or (floor >= floors and not run.get("boss_defeated")):
        return "hard"
    if ratio <= 0.65:
        return "hard"
    return "ok"


def severity_label_th(severity: str) -> str:
    return {
        "ok": "ยังไหว",
        "hard": "ตึงเครียด",
        "critical": "วิกฤต",
    }.get(str(severity), "ไม่ชัด")


def _phase_from_dungeon_run(run: Mapping[str, Any]) -> str:
    if run.get("boss_defeated"):
        return "cleared_pending_exit"
    floor = int(run.get("floor") or 1)
    floors = max(1, int(run.get("floors") or 1))
    if floor >= floors:
        return "boss"
    return "floor"


def sync_situation_from_dungeon(
    player: MutableMapping[str, Any],
    *,
    preserve_help: bool = True,
) -> Optional[Dict[str, Any]]:
    ensure_situation_fields(player)
    run = player.get("dungeon_run")
    if not isinstance(run, dict) or not run.get("dungeon_id"):
        player["situation"] = None
        return None

    prev = get_situation(player)
    prev_help = dict((prev or {}).get("help") or {}) if preserve_help else {}

    severity = _severity_from_dungeon_run(run)
    phase = _phase_from_dungeon_run(run)
    help_state = {
        "open": bool(prev_help.get("open")) if preserve_help else False,
        "slots": int(prev_help.get("slots") or DEFAULT_SLOTS),
        "policy": str(prev_help.get("policy") or POLICY_PUBLIC),
        "status": str(prev_help.get("status") or HELP_STATUS_CLOSED),
        "offer": prev_help.get("offer"),
        "escrow": prev_help.get("escrow"),
        "helper_ids": list(prev_help.get("helper_ids") or []),
        "helper_names": list(prev_help.get("helper_names") or []),
        "note": str(prev_help.get("note") or ""),
        "opened_at": prev_help.get("opened_at"),
        "chronicle": list(prev_help.get("chronicle") or []),
    }
    if not help_state["open"]:
        help_state["status"] = HELP_STATUS_CLOSED
        if not preserve_help:
            help_state["opened_at"] = None

    sit = {
        "kind": "dungeon",
        "ref_id": str(run.get("dungeon_id")),
        "label": str(run.get("name") or run.get("dungeon_id")),
        "area_id": str(run.get("area_id") or ""),
        "severity": severity,
        "phase": phase,
        "floor": int(run.get("floor") or 1),
        "floors": int(run.get("floors") or 1),
        "owner_id": player.get("id"),
        "owner_name": player.get("name"),
        "world_id": player.get("world_id") or "default",
        "help": help_state,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    player["situation"] = sit
    return sit


def format_offer_line(offer: Optional[Mapping[str, Any]], escrow: Optional[Mapping[str, Any]] = None) -> str:
    o = dict(offer or {})
    e = dict(escrow or {})
    gold = int(o.get("gold") or e.get("gold") or 0)
    items = list(o.get("item_names") or e.get("item_names") or [])
    parts = []
    if gold > 0:
        parts.append(f"{gold}G")
    if items:
        parts.append("·".join(str(x) for x in items[:3]))
    if not parts:
        return "(อาสา — ไม่ระบุของตอบแทน)"
    return " + ".join(parts)


def _empty_help_closed() -> Dict[str, Any]:
    return {
        "open": False,
        "slots": DEFAULT_SLOTS,
        "policy": POLICY_PUBLIC,
        "status": HELP_STATUS_CLOSED,
        "offer": None,
        "escrow": None,
        "helper_ids": [],
        "helper_names": [],
        "note": "",
        "opened_at": None,
        "chronicle": [],
    }


def _lock_escrow(
    player: MutableMapping[str, Any],
    reg: Any,
    *,
    gold: int,
    item_ids: List[str],
) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
    """Deduct gold/items into escrow. Returns (ok, escrow, notes)."""
    notes: List[str] = []
    gold = max(0, int(gold or 0))
    item_ids = [str(x) for x in (item_ids or []) if x]
    money = int(player.get("money_world") or 0)
    if gold > money:
        return False, None, [f"เงินโลกไม่พอ (มี {money} ต้องการ {gold})"]

    from game.domain.equipment import remove_inventory_id
    from game.data_load.registry import DataRegistry

    removed_names: List[str] = []
    removed_ids: List[str] = []
    # validate all present first
    bag = list(player.get("inventory_ids") or [])
    bag_check = list(bag)
    for iid in item_ids:
        if iid not in bag_check:
            return False, None, [f"ไม่มีไอเทม {iid} ในกระเป๋า"]
        bag_check.remove(iid)

    if gold:
        player["money_world"] = money - gold
        notes.append(f" ล็อกเงินตอบแทน {gold}G")

    for iid in item_ids:
        name = (getattr(reg, "items", {}) or {}).get(iid, {}).get("name") or iid
        if remove_inventory_id(player, iid, reg):
            removed_ids.append(iid)
            removed_names.append(str(name))
            notes.append(f" ล็อกของตอบแทน: {name}")
        else:
            # refund gold already taken
            if gold:
                player["money_world"] = int(player.get("money_world") or 0) + gold
            return False, None, [f"ล็อกของ {iid} ไม่สำเร็จ"]

    escrow = {
        "gold": gold,
        "item_ids": removed_ids,
        "item_names": removed_names,
    }
    offer = {
        "gold": gold,
        "item_ids": list(removed_ids),
        "item_names": list(removed_names),
    }
    return True, {"escrow": escrow, "offer": offer}, notes


def return_escrow_to_owner(player: MutableMapping[str, Any], reg: Any) -> List[str]:
    """Return locked offer to owner (cancel / fail)."""
    h = help_block(player)
    esc = dict(h.get("escrow") or {})
    if not esc:
        return []
    notes: List[str] = []
    gold = int(esc.get("gold") or 0)
    if gold:
        player["money_world"] = int(player.get("money_world") or 0) + gold
        notes.append(f" คืนเงินล็อก {gold}G")
    from game.domain.equipment import add_item

    for iid in list(esc.get("item_ids") or []):
        shown = add_item(player, str(iid), reg)
        notes.append(f" คืนของ: {shown}")
    # clear escrow on situation if present
    sit = get_situation(player)
    if sit:
        help_state = dict(sit.get("help") or {})
        help_state["escrow"] = None
        help_state["offer"] = None
        sit = dict(sit)
        sit["help"] = help_state
        player["situation"] = sit
    return notes


def pay_escrow_to_helper(
    owner: MutableMapping[str, Any],
    helper: MutableMapping[str, Any],
    reg: Any,
) -> List[str]:
    """Transfer escrow from owner situation to helper (success)."""
    h = help_block(owner)
    esc = dict(h.get("escrow") or {})
    if not esc:
        return [" (ไม่มีของตอบแทน — อาสา)"]
    notes: List[str] = []
    gold = int(esc.get("gold") or 0)
    if gold:
        helper["money_world"] = int(helper.get("money_world") or 0) + gold
        notes.append(f" ได้เงินตอบแทน {gold}G")
    from game.domain.equipment import add_item

    for iid in list(esc.get("item_ids") or []):
        shown = add_item(helper, str(iid), reg)
        notes.append(f" ได้ของตอบแทน: {shown}")
    sit = get_situation(owner)
    if sit:
        help_state = dict(sit.get("help") or {})
        help_state["escrow"] = None
        # keep offer record for chronicle display
        sit = dict(sit)
        sit["help"] = help_state
        owner["situation"] = sit
    return notes


def open_help_request(
    player: MutableMapping[str, Any],
    reg: Any = None,
    *,
    note: str = "",
    policy: str = POLICY_PUBLIC,
    slots: int = DEFAULT_SLOTS,
    gold: int = 0,
    item_ids: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    ensure_situation_fields(player)
    sync_situation_from_dungeon(player, preserve_help=True)
    sit = get_situation(player)
    if not sit:
        return False, ["ไม่มีสถานการณ์ที่ขอแรงได้ — ต้องอยู่ในดัน/วิกฤตก่อน"]

    if help_is_open(player):
        return False, ["สัญญาณขอแรงเปิดอยู่แล้ว"]

    note = (note or "").strip()[:80]
    policy = policy if policy in (POLICY_PUBLIC, POLICY_FRIENDS) else POLICY_PUBLIC
    slots = max(1, min(3, int(slots)))
    gold = max(0, int(gold or 0))
    item_ids = list(item_ids or [])

    offer = None
    escrow = None
    extra: List[str] = []
    if gold or item_ids:
        if reg is None:
            return False, ["ต้องการ registry เพื่อล็อกของตอบแทน"]
        ok, bundle, lock_notes = _lock_escrow(player, reg, gold=gold, item_ids=item_ids)
        if not ok or not bundle:
            return False, lock_notes
        offer = bundle["offer"]
        escrow = bundle["escrow"]
        extra = lock_notes

    help_state = {
        "open": True,
        "slots": slots,
        "policy": policy,
        "status": HELP_STATUS_OPEN,
        "offer": offer,
        "escrow": escrow,
        "helper_ids": [],
        "helper_names": [],
        "note": note,
        "opened_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "chronicle": [
            f"เปิดสัญญาณ · {severity_label_th(str(sit.get('severity')))} · {sit.get('label')}",
        ],
    }
    sit = dict(sit)
    sit["help"] = help_state
    sit["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    player["situation"] = sit

    notes = [
        "คุณเปิดสัญญาณขอแรง — ยินยอมให้ผู้อื่นเข้ามาในสถานการณ์นี้บนเส้นทางของคุณ",
        " · ของนอกสัญญาตอบแทนจะไม่ถูกแตะ",
        f" · สถานะ: {severity_label_th(str(sit.get('severity')))} · {sit.get('label')}",
        f" · ตอบแทน: {format_offer_line(offer, escrow)}",
    ]
    notes.extend(extra)
    if note:
        notes.append(f" · ข้อความ: 「{note}」")
    if policy == POLICY_FRIENDS:
        notes.append(" · ขอบเขต: เฉพาะสายสัมพันธ์ (เพื่อน/ความทรงจำสังคม)")
    else:
        notes.append(" · ขอบเขต: สาธารณะในโลก (กระดานสัญญาณ)")
    notes.append(" · บันทึกแล้วพักรอแรงได้จากเมนูสัญญาณ")

    player["help_requests"] = int(player.get("help_requests") or 0) + 1
    append_world_signal_log(
        str(player.get("world_id") or "default"),
        {
            "kind": "sos_open",
            "owner_name": player.get("name"),
            "owner_id": player.get("id"),
            "label": sit.get("label"),
            "policy": policy,
            "offer_line": format_offer_line(offer, escrow),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )
    if reg is not None:
        try:
            from game.domain.quests import bump_quest

            notes.extend(bump_quest(player, reg, "help_open"))
        except Exception:
            pass
    return True, notes


def close_help_request(
    player: MutableMapping[str, Any],
    reg: Any = None,
    *,
    reason: str = "owner_cancel",
) -> Tuple[bool, List[str]]:
    ensure_situation_fields(player)
    sync_situation_from_dungeon(player, preserve_help=True)
    sit = get_situation(player)
    if not sit:
        return False, ["ไม่มีสถานการณ์"]
    if not help_is_open(player) and not help_block(player).get("escrow"):
        return False, ["สัญญาณขอแรงไม่ได้เปิดอยู่"]

    notes: List[str] = []
    if reg is not None and help_block(player).get("escrow"):
        notes.extend(return_escrow_to_owner(player, reg))

    help_state = _empty_help_closed()
    help_state["closed_reason"] = reason
    sit = dict(sit)
    sit["help"] = help_state
    sit["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    player["situation"] = sit
    notes.insert(0, "สัญญาณขอแรงดับลง — ไม่มีใครแทรกสถานการณ์นี้ได้อีกจนกว่าจะเปิดใหม่")
    return True, notes


def format_help_status_lines(player: Mapping[str, Any]) -> List[str]:
    sit = get_situation(player)
    if not sit:
        return ["〔สถานการณ์〕 ไม่มีวิกฤตค้าง"]
    h = help_block(player)
    lines = [
        f"〔สถานการณ์〕 {sit.get('label')} · {severity_label_th(str(sit.get('severity')))}",
        f" ชนิด: {sit.get('kind')} · ช่วง: {sit.get('phase')}",
    ]
    if sit.get("kind") == "dungeon":
        lines.append(f" ชั้น {sit.get('floor')}/{sit.get('floors')}")
    if help_is_open(player):
        st = str(h.get("status") or "")
        if st == HELP_STATUS_CLAIMED:
            lines.append(" สัญญาณขอแรง: ถูก claim — มีผู้ช่วยกำลังยื่นมือ")
        else:
            lines.append(" สัญญาณขอแรง: เปิด (ยินยอมให้ช่วยแบบจำกัด)")
        if h.get("note"):
            lines.append(f" ข้อความ: 「{h.get('note')}」")
        lines.append(f" ตอบแทน: {format_offer_line(h.get('offer'), h.get('escrow'))}")
        lines.append(f" ที่ว่างผู้ช่วย: {h.get('slots', 1)} · นโยบาย: {h.get('policy')}")
    else:
        lines.append(" สัญญาณขอแรง: ปิด — ไม่มีใครแทรกเซฟนี้ได้")
    return lines


def consent_warning_lines() -> List[str]:
    return [
        "〔ขอแรง — ความยินยอม〕",
        "คุณกำลังเปิดให้ผู้อื่นเข้ามาในสถานการณ์นี้บนเส้นทางของคุณ",
        " · พวกเขาจะร่วมทีมในเงา/สถานการณ์นี้",
        " · ผลแพ้–ชนะอาจเปลี่ยนชะตาดันของคุณ",
        " · ของตอบแทนที่ล็อกไว้จะมอบเมื่อสำเร็จ (หรือคืนถ้ายกเลิก)",
        " · ไม่ใช่การเปิดเซฟทั้งก้อน — เฉพาะสถานการณ์นี้",
    ]


# ── H1 board ──────────────────────────────────────────────────────────────


def is_help_friend(viewer: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    """H4: soft friend check via social_memory (no raw affinity dump)."""
    oid = str(owner.get("id") or "")
    vid = str(viewer.get("id") or "")
    if not oid or not vid:
        return False
    mem_v = dict((viewer.get("social_memory") or {}).get(oid) or {})
    mem_o = dict((owner.get("social_memory") or {}).get(vid) or {})
    if mem_v.get("was_friend") or mem_o.get("was_friend"):
        return True
    if int(mem_v.get("friend_pts") or 0) >= 2 or int(mem_o.get("friend_pts") or 0) >= 2:
        return True
    return False


def can_viewer_see_signal(
    viewer: Optional[Mapping[str, Any]],
    owner: Mapping[str, Any],
    help_state: Mapping[str, Any],
) -> bool:
    policy = str(help_state.get("policy") or POLICY_PUBLIC)
    if policy != POLICY_FRIENDS:
        return True
    if viewer is None:
        return False
    return is_help_friend(viewer, owner)


def list_open_help_signals(
    world_id: str,
    *,
    exclude_player_id: Optional[str] = None,
    viewer: Optional[Mapping[str, Any]] = None,
    saves_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Scan world saves for open help situations (soft public / friends cards)."""
    from game.config import SAVES_DIR
    from game.services.save_service import list_saves, load_player

    root = saves_dir or SAVES_DIR
    rows: List[Dict[str, Any]] = []
    folder = Path(root) / world_id
    if not folder.is_dir():
        metas = list_saves(world_id)
        paths = [m["path"] for m in metas]
    else:
        paths = [str(p) for p in sorted(folder.glob("*.json"))]

    for path in paths:
        try:
            p = load_player(path)
        except Exception:
            continue
        pid = str(p.get("id") or "")
        if exclude_player_id and pid == str(exclude_player_id):
            continue
        if not help_is_open(p):
            continue
        run = p.get("dungeon_run")
        if not isinstance(run, dict) or not run.get("dungeon_id"):
            continue
        sit = get_situation(p) or {}
        h = help_block(p)
        if not can_viewer_see_signal(viewer, p, h):
            continue
        claimable = str(h.get("status")) != HELP_STATUS_CLAIMED
        policy = str(h.get("policy") or POLICY_PUBLIC)
        rows.append(
            {
                "owner_id": pid,
                "owner_name": p.get("name") or "?",
                "path": path,
                "label": sit.get("label") or run.get("name") or "สถานการณ์",
                "kind": sit.get("kind") or "dungeon",
                "severity": sit.get("severity") or "hard",
                "severity_label": severity_label_th(str(sit.get("severity") or "hard")),
                "phase": sit.get("phase"),
                "floor": sit.get("floor"),
                "floors": sit.get("floors"),
                "note": h.get("note") or "",
                "offer_line": format_offer_line(h.get("offer"), h.get("escrow")),
                "status": h.get("status"),
                "policy": policy,
                "policy_label": "เพื่อน" if policy == POLICY_FRIENDS else "สาธารณะ",
                "claimable": claimable and help_is_claimable(p),
                "updated_at": sit.get("updated_at") or p.get("updated_at"),
            }
        )
    rows.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return rows


def format_board_lines(signals: List[Mapping[str, Any]]) -> List[str]:
    lines = ["〔กระดานสัญญาณขอแรง〕"]
    if not signals:
        lines.append(" (ยังไม่มีสัญญาณที่คุณมองเห็นในโลกนี้)")
        return lines
    for i, s in enumerate(signals, 1):
        st = "รอผู้ช่วย" if s.get("claimable") else "มีคนยื่นมือแล้ว"
        pol = s.get("policy_label") or "สาธารณะ"
        lines.append(
            f" {i}. {s.get('owner_name')} · {s.get('label')} · "
            f"{s.get('severity_label')} · {pol} · {st}"
        )
        lines.append(f"    ตอบแทน: {s.get('offer_line')}")
        if s.get("note"):
            lines.append(f"    「{s.get('note')}」")
    return lines


# ── H4 reputation + world log ──────────────────────────────────────────────


def helper_soft_title(player: Mapping[str, Any]) -> str:
    """Soft reputation title — never show raw rep number in normal UI."""
    rep = int(player.get("help_rep") or 0)
    assists = int(player.get("help_assists") or 0)
    if rep >= 50 or assists >= 12:
        return "เงาผู้ยื่นมือ"
    if rep >= 20 or assists >= 5:
        return "มืออาสา"
    if rep >= 5 or assists >= 1:
        return "ผู้ช่วยใหม่"
    return ""


def format_helper_badge(player: Mapping[str, Any]) -> str:
    title = helper_soft_title(player)
    if title:
        return f"〔{title}〕"
    return ""


def grant_assist_reputation(helper: MutableMapping[str, Any], *, amount: int = 5) -> List[str]:
    ensure_situation_fields(helper)
    helper["help_rep"] = int(helper.get("help_rep") or 0) + max(0, amount)
    helper["help_assists"] = int(helper.get("help_assists") or 0) + 1
    title = helper_soft_title(helper)
    notes = [f" ชื่อเสียงผู้ช่วยเบาขึ้น"]
    if title:
        notes.append(f" ฉายา soft: 「{title}」")
    return notes


def append_world_signal_log(
    world_id: str,
    entry: Dict[str, Any],
    *,
    saves_dir: Optional[Path] = None,
    max_entries: int = 40,
) -> None:
    from game.config import SAVES_DIR

    root = Path(saves_dir or SAVES_DIR) / world_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / "world_signals.json"
    data: Dict[str, Any] = {"messages": []}
    if path.is_file():
        try:
            import json

            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except Exception:
            pass
    msgs = list(data.get("messages") or [])
    entry = dict(entry)
    entry.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
    msgs.insert(0, entry)
    data["messages"] = msgs[:max_entries]
    import json

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_world_signal_log(
    world_id: str,
    *,
    limit: int = 12,
    saves_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    from game.config import SAVES_DIR

    path = Path(saves_dir or SAVES_DIR) / world_id / "world_signals.json"
    if not path.is_file():
        return []
    try:
        import json

        raw = json.loads(path.read_text(encoding="utf-8"))
        msgs = list((raw or {}).get("messages") or [])
        return [dict(m) for m in msgs[:limit] if isinstance(m, dict)]
    except Exception:
        return []


def format_world_signal_log_lines(messages: List[Mapping[str, Any]]) -> List[str]:
    lines = ["〔บันทึกสัญญาณโลก〕"]
    if not messages:
        lines.append(" (ยังเงียบ)")
        return lines
    for m in messages:
        kind = str(m.get("kind") or "")
        ts = str(m.get("ts") or "")[:16]
        if kind == "sos_open":
            pol = "เพื่อน" if m.get("policy") == POLICY_FRIENDS else "สาธารณะ"
            lines.append(
                f" · {ts} เปิดขอแรง · {m.get('owner_name')} · {m.get('label')} ({pol})"
            )
        elif kind == "sos_resolved":
            lines.append(
                f" · {ts} ฝ่าสำเร็จ · {m.get('owner_name')} ถูกช่วยโดย {m.get('helper_name')}"
            )
        else:
            lines.append(f" · {ts} {kind}")
    return lines


# ── H3 claim / resolve ─────────────────────────────────────────────────────


def append_chronicle(player: MutableMapping[str, Any], line: str) -> None:
    sit = get_situation(player)
    if not sit:
        return
    h = dict(sit.get("help") or {})
    ch = list(h.get("chronicle") or [])
    ch.append(str(line)[:120])
    h["chronicle"] = ch[-40:]
    sit = dict(sit)
    sit["help"] = h
    player["situation"] = sit


def claim_help_for_helper(
    owner: MutableMapping[str, Any],
    helper: Mapping[str, Any],
) -> Tuple[bool, List[str]]:
    if not help_is_claimable(owner):
        return False, ["สัญญาณนี้รับไม่ได้แล้ว (ปิดหรือมีคน claim แล้ว)"]
    hid = str(helper.get("id") or "")
    if hid and hid == str(owner.get("id") or ""):
        return False, ["ช่วยตัวเองบนสัญญาณนี้ไม่ได้"]
    sit = get_situation(owner)
    if not sit:
        return False, ["ไม่มีสถานการณ์"]
    h = dict(sit.get("help") or {})
    if not can_viewer_see_signal(helper, owner, h):
        return False, ["สัญญาณนี้สงวนสำหรับสายสัมพันธ์ — คุณมองไม่เห็น/รับไม่ได้"]
    helpers = list(h.get("helper_ids") or [])
    names = list(h.get("helper_names") or [])
    if hid and hid not in helpers:
        helpers.append(hid)
    hname = str(helper.get("name") or "ผู้ยื่นมือ")
    badge = format_helper_badge(helper)
    if hname not in names:
        names.append(hname)
    slots = int(h.get("slots") or 1)
    h["helper_ids"] = helpers[:slots]
    h["helper_names"] = names[:slots]
    h["status"] = HELP_STATUS_CLAIMED
    h["claimed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    sit = dict(sit)
    sit["help"] = h
    owner["situation"] = sit
    append_chronicle(owner, f"เงาของ「{hname}」{badge} ยื่นมือเข้ามา")
    notes = [
        f"คุณยื่นมือช่วย「{owner.get('name')}」ใน {sit.get('label')}",
        " · ร่วมทีมเงาเจ้าของ — สู้เพื่อฝ่าสถานการณ์",
    ]
    if badge:
        notes.append(f" · {badge}")
    return True, notes


def apply_assist_victory(
    owner: MutableMapping[str, Any],
    helper: MutableMapping[str, Any],
    reg: Any,
) -> List[str]:
    """Owner dungeon clears via helper; pay escrow; inbox; close help open flag."""
    from game.domain.dungeon import on_dungeon_boss_defeated

    notes: List[str] = []
    hname = str(helper.get("name") or "ผู้ยื่นมือ")
    append_chronicle(owner, f"「{hname}」ร่วมฝ่า — บอส/วิกฤตล้ม")
    append_chronicle(owner, "ทางออกเปิด — สัญญาณขอแรงจะดับหลังสรุป")

    # clear dungeon boss state on owner
    run = owner.get("dungeon_run")
    if isinstance(run, dict) and not run.get("boss_defeated"):
        notes.extend(on_dungeon_boss_defeated(owner, reg))
    elif isinstance(run, dict):
        run = dict(run)
        run["locked"] = False
        owner["dungeon_run"] = run

    pay_notes = pay_escrow_to_helper(owner, helper, reg)
    notes.append("── ตอบแทนผู้ช่วย ──")
    notes.extend(pay_notes)

    # soft helper rewards beyond escrow
    helper["money_world"] = int(helper.get("money_world") or 0) + 15
    notes.append(" ผู้ช่วยได้รับค่าแรงโลกเบา +15G")
    notes.extend(grant_assist_reputation(helper, amount=5))

    sit = get_situation(owner)
    chronicle = list((help_block(owner).get("chronicle") or []))
    push_world_inbox(
        owner,
        {
            "type": "sos_resolved",
            "result": "win",
            "helper_name": hname,
            "helper_id": helper.get("id"),
            "helper_title": helper_soft_title(helper),
            "label": (sit or {}).get("label"),
            "chronicle": chronicle,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )

    # H4: social bond soft
    try:
        from game.domain.world_social import remember_social

        remember_social(owner, str(helper.get("id") or ""), "friend")
        remember_social(helper, str(owner.get("id") or ""), "friend")
        notes.append(" ความสัมพันธ์ soft: เหมือนได้เพื่อนร่วมทาง")
    except Exception:
        pass

    append_world_signal_log(
        str(owner.get("world_id") or "default"),
        {
            "kind": "sos_resolved",
            "owner_name": owner.get("name"),
            "owner_id": owner.get("id"),
            "helper_name": hname,
            "helper_id": helper.get("id"),
            "label": (sit or {}).get("label"),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )

    if reg is not None:
        try:
            from game.domain.quests import bump_quest

            notes.extend(bump_quest(helper, reg, "help_assist"))
        except Exception:
            pass

    # close help but keep dungeon until owner exits
    if sit:
        h = _empty_help_closed()
        h["status"] = HELP_STATUS_RESOLVED
        h["last_result"] = "win"
        h["last_helper_name"] = hname
        h["chronicle"] = chronicle
        sit = dict(sit)
        sit["help"] = h
        sit["phase"] = "cleared_pending_exit"
        owner["situation"] = sit

    notes.append(f"✦ สถานการณ์ของ「{owner.get('name')}」ฝ่าสำเร็จด้วยแรง「{hname}」")
    return notes


def owner_exit_cleanup(player: MutableMapping[str, Any], reg: Any) -> List[str]:
    """When leaving dungeon: return escrow if help still open, clear situation."""
    notes: List[str] = []
    h = help_block(player)
    if h.get("escrow") and (
        help_is_open(player) or str(h.get("status")) == HELP_STATUS_CLAIMED
    ):
        notes.extend(return_escrow_to_owner(player, reg))
    clear_situation(player)
    return notes


def apply_assist_failure(
    owner: MutableMapping[str, Any],
    helper: Mapping[str, Any],
) -> List[str]:
    hname = str(helper.get("name") or "ผู้ยื่นมือ")
    append_chronicle(owner, f"「{hname}」ยื่นมือแต่ยังฝ่าไม่สำเร็จ")
    sit = get_situation(owner)
    if sit:
        h = dict(sit.get("help") or {})
        # reopen for another helper; keep escrow
        h["open"] = True
        h["status"] = HELP_STATUS_OPEN
        h["helper_ids"] = []
        h["helper_names"] = []
        sit = dict(sit)
        sit["help"] = h
        owner["situation"] = sit
    return [
        "ยังฝ่าไม่สำเร็จ — สัญญาณเปิดอีกครั้งให้ผู้อื่น",
        " ของตอบแทนยังถูกล็อกไว้",
    ]


def push_world_inbox(player: MutableMapping[str, Any], entry: Dict[str, Any]) -> None:
    ensure_situation_fields(player)
    box = list(player.get("world_inbox") or [])
    box.insert(0, entry)
    player["world_inbox"] = box[:30]


def format_inbox_preview(player: Mapping[str, Any], limit: int = 5) -> List[str]:
    ensure_situation_fields(player)  # type: ignore[arg-type]
    box = list(player.get("world_inbox") or [])
    if not box:
        return ["〔จดหมายเงา〕 ว่าง"]
    lines = ["〔จดหมายเงา〕"]
    for e in box[:limit]:
        if e.get("type") == "sos_resolved":
            res = "สำเร็จ" if e.get("result") == "win" else str(e.get("result"))
            lines.append(
                f" · {e.get('label') or 'สถานการณ์'} — {res} · ผู้ช่วย {e.get('helper_name')}"
            )
        else:
            lines.append(f" · {e.get('type')}")
    return lines


def pop_inbox_detail(player: MutableMapping[str, Any], index: int = 0) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    ensure_situation_fields(player)
    box = list(player.get("world_inbox") or [])
    if index < 0 or index >= len(box):
        return None, ["ไม่มีรายการ"]
    entry = dict(box[index])
    lines = [f"── {entry.get('type')} ──"]
    if entry.get("type") == "sos_resolved":
        lines.append(f" สถานการณ์: {entry.get('label')}")
        lines.append(f" ผล: {entry.get('result')} · ผู้ช่วย: {entry.get('helper_name')}")
        lines.append(" บันทึก:")
        for c in list(entry.get("chronicle") or [])[-12:]:
            lines.append(f"  · {c}")
    return entry, lines
