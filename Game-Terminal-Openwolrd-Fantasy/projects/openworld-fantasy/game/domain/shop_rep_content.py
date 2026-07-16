"""
WO-Shop-5 — Shop Reputation Content.

Soft field events near shops + deliver-item quest helpers.
Grants shop_rep (+5–15) without raw numbers in flavor.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# ── Soft field events (help a shop nearby) ──────────────────────────────

SHOP_REP_EVENTS: Dict[str, Dict[str, Any]] = {
    "merchant_road_aid": {
        "id": "merchant_road_aid",
        "shop_id": "traveling_merchant",
        "areas": ("dark_forest", "desert_heat", "mountain_rock", "ancient_city"),
        "label": "รถเร่ติดหล่ม",
        "hint": "เสียงล้อ · พ่อค้าโบกมือ",
        "risk": "ต่ำ",
        "rep": 8,
        "intro": [
            "  รถเร่พ่อค้าติดหล่ม — ของเกลื่อน",
            "  「ช่วยดันหน่อย… ข้าจะจำบุญคุณ」",
        ],
        "help_label": "ช่วยดันรถเร่",
        "help_flavor": [
            "  คุณดันรถจนล้อหมุน — พ่อค้าพยักหน้า",
            "  ความคุ้นกับพ่อค้าเร่ดีขึ้นแผ่ว",
        ],
        "refuse_flavor": ["  คุณเดินผ่าน — รถเร่ยังติด · พ่อค้าถอนหายใจ"],
    },
    "armory_shadow_raid": {
        "id": "armory_shadow_raid",
        "shop_id": "city_armory",
        "areas": ("ancient_city", "dark_forest"),
        "label": "เงาไล่ทั่ง",
        "hint": "เสียงเหล็ก · เงาวิ่งหน้าร้านอาวุธ",
        "risk": "กลาง",
        "rep": 12,
        "intro": [
            "  เงาโจรวิ่งหน้าร้านอาวุธเมือง — ช่างตีโบกค้อน",
            "  「ช่วยกันไล่! ทั่งยังร้อน」",
        ],
        "help_label": "ช่วยไล่เงา · คุ้มโรงตี",
        "help_flavor": [
            "  คุณยืนกั้นทาง — เงาแตกหนี",
            "  ช่างตีพยัก · โรงตีจำคุณได้",
        ],
        "refuse_flavor": ["  คุณถอย — เสียงค้อนยังดังกังวาน"],
    },
    "rare_crystal_errand": {
        "id": "rare_crystal_errand",
        "shop_id": "rare_exchange",
        "areas": ("crystal_peak", "cave_shadow", "ancient_city"),
        "label": "หาเศษผลึก",
        "hint": "คนถือถุงผ้า · กระซิบเรื่องผลึก",
        "risk": "ต่ำ",
        "rep": 10,
        "intro": [
            "  คนจากตลาดวัสดุกระซิบ: 「ช่วยหาเศษผลึกให้ร้าน…」",
            "  「ไม่ต้องครบ — แค่ชี้ทางหรือเก็บแผ่วก็พอ」",
        ],
        "help_label": "ช่วยหา/ชี้ทางผลึก",
        "help_flavor": [
            "  คุณช่วยจนได้เศษเล็ก ๆ — เขายิ้ม",
            "  ตลาดวัสดุหายากจำหน้าคุณได้",
        ],
        "refuse_flavor": ["  คุณส่ายหน้า — เขายังเดินค้นต่อ"],
    },
    "celestial_lantern_lift": {
        "id": "celestial_lantern_lift",
        "shop_id": "celestial_bazaar",
        "areas": ("ancient_city", "crystal_peak"),
        "label": "โคมสวรรค์ดับ",
        "hint": "โคมแสงบาง · ลมเป่า",
        "risk": "ต่ำ",
        "rep": 9,
        "intro": [
            "  โคมตลาดสวรรค์ดับ — แม่ค้าก้มจุดไฟ",
            "  「ช่วยยกโคม… แสงจะกลับ」",
        ],
        "help_label": "ช่วยยกโคม · จุดแสง",
        "help_flavor": [
            "  โคมสว่างอีกครั้ง — ลมอุ่น",
            "  ตลาดสวรรค์รู้สึกเป็นมิตรขึ้น",
        ],
        "refuse_flavor": ["  คุณเดินผ่าน — โคมยังมืดครึ่งหนึ่ง"],
    },
    "infernal_ash_scatter": {
        "id": "infernal_ash_scatter",
        "shop_id": "infernal_market",
        "areas": ("mist_marsh", "cave_shadow", "void_rift"),
        "label": "เถ้าสุญญะกระจัด",
        "hint": "ควันดำ · ถุงเถ้าขาด",
        "risk": "กลาง",
        "rep": 11,
        "intro": [
            "  ถุงเถ้าสุญญะขาด — ควันม้วนพื้น",
            "  คนตลาดนรก: 「ช่วยเก็บเถ้า… อย่าสูด」",
        ],
        "help_label": "ช่วยเก็บเถ้าอย่างระวัง",
        "help_flavor": [
            "  คุณเก็บเถ้าจนถุงแน่น — ควันอ่อนลง",
            "  ตลาดนรกพยักเงียบ ๆ",
        ],
        "refuse_flavor": ["  คุณถอยห่างควัน — เถ้ายังปลิว"],
    },
    "legend_echo_quiet": {
        "id": "legend_echo_quiet",
        "shop_id": "legend_pavilion",
        "areas": ("ancient_city", "void_rift", "crystal_peak"),
        "label": "ศาลาเงียบก้อง",
        "hint": "เสียงสะท้อนจากศาลา",
        "risk": "?",
        "rep": 10,
        "intro": [
            "  ศาลาตำนานก้องแผ่ว — ผู้เฒ่าโบกมือ",
            "  「ช่วยฟังเสียงสะท้อน… แล้วบอกว่าได้ยินอะไร」",
        ],
        "help_label": "นั่งฟัง · บอกสิ่งที่ได้ยิน",
        "help_flavor": [
            "  คุณฟังจนก้องจาง — ผู้เฒ่าพยัก",
            "  ศาลาจำเงาคุณได้",
        ],
        "refuse_flavor": ["  คุณเดินออก — ก้องยังตามแผ่ว"],
    },
}


def events_for_area(area_id: str) -> List[Dict[str, Any]]:
    aid = str(area_id or "")
    return [dict(e) for e in SHOP_REP_EVENTS.values() if aid in (e.get("areas") or ())]


def roll_shop_rep_event_sight(
    player: Mapping[str, Any],
    rng: random.Random,
    *,
    area_id: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Soft chance to inject a shop-rep event into field sights.
    Throttled · lower than mon spam · no %.
    """
    aid = str(area_id or player.get("location") or "")
    pool = events_for_area(aid)
    if not pool:
        return None
    seen = int(player.get("_shop_rep_events_seen") or 0)
    if seen <= 0:
        chance = 0.18
    elif seen >= 5:
        chance = 0.10
    else:
        chance = 0.14
    last_area = str(player.get("_last_shop_rep_event_area") or "")
    if last_area == aid and seen > 0:
        chance *= 0.7
    if rng.random() > chance:
        return None
    last = str(player.get("_last_shop_rep_event") or "")
    candidates = [e for e in pool if e.get("id") != last] or pool
    e = dict(rng.choice(candidates))
    return {
        "kind": "shop_rep_event",
        "event_id": e["id"],
        "shop_id": e.get("shop_id"),
        "label": e.get("label"),
        "hint": e.get("hint"),
        "risk": e.get("risk") or "?",
        "known": True,
        "event": e,
    }


def resolve_shop_rep_event(
    player: MutableMapping[str, Any],
    event_id: str,
    choice: str,
    *,
    reg: Any = None,
) -> List[str]:
    """
    choice: help | refuse
    Help → +rep 5–15 (from event.rep) soft notes.
    """
    eid = str(event_id or "")
    edef = SHOP_REP_EVENTS.get(eid)
    if not edef:
        return ["  …เหตุการณ์ร้านจางหาย"]
    ch = str(choice or "refuse").lower()
    if ch in ("1", "help", "ช่วย", "h", "y", "yes", "ใช่"):
        ch = "help"
    else:
        ch = "refuse"

    lines: List[str] = []
    if ch == "help":
        lines.extend(list(edef.get("help_flavor") or ["  คุณช่วยจนจบ"]))
        sid = str(edef.get("shop_id") or "")
        rep_amt = int(edef.get("rep") or 8)
        rep_amt = max(5, min(15, rep_amt))
        try:
            from game.domain.shop_experience import (
                bump_shop_rep,
                get_shop_rep,
                shop_rep_soft_label,
            )

            bump_shop_rep(player, sid, amount=rep_amt, reason="quest")
            lab = shop_rep_soft_label(get_shop_rep(player, sid))
            shop_name = sid
            if reg is not None:
                sdef = (getattr(reg, "shops", None) or {}).get(sid) or {}
                shop_name = str(sdef.get("name") or sid)
            lines.append(f"  ความคุ้น「{shop_name}」ดีขึ้น 〔{lab}〕")
        except Exception:
            pass
        # soft morale
        try:
            from game.domain.needs import get_needs, set_needs

            n = get_needs(player)
            n["morale"] = min(100, int(n.get("morale") or 50) + 2)
            set_needs(player, n)
        except Exception:
            pass
    else:
        lines.extend(list(edef.get("refuse_flavor") or ["  คุณเดินจากไป"]))

    player["_last_shop_rep_event"] = eid
    player["_last_shop_rep_event_area"] = str(player.get("location") or "")
    player["_shop_rep_events_seen"] = int(player.get("_shop_rep_events_seen") or 0) + 1
    return lines


def run_shop_rep_event_menu(
    player: MutableMapping[str, Any],
    sight: Mapping[str, Any],
    io: Any,
    *,
    reg: Any = None,
) -> None:
    """Interactive soft menu for a shop-rep field event."""
    edef = sight.get("event") or SHOP_REP_EVENTS.get(str(sight.get("event_id") or ""))
    if not isinstance(edef, dict):
        io.write_line("  …เหตุการณ์จาง")
        return
    for line in edef.get("intro") or []:
        io.write_line(line)
    help_lab = str(edef.get("help_label") or "ช่วย")
    io.write_line(f"  1. {help_lab}")
    io.write_line("  2. เดินจากไป")
    ch = io.read_line("\n  เลือก (1/2): ").strip().lower()
    notes = resolve_shop_rep_event(
        player, str(edef.get("id") or sight.get("event_id")), ch, reg=reg
    )
    for n in notes:
        io.write_line(n)


def auto_resolve_shop_rep_event(
    player: MutableMapping[str, Any],
    sight: Mapping[str, Any],
    *,
    reg: Any = None,
    prefer_help: bool = True,
) -> List[str]:
    """Auto-play soft resolve (usually help)."""
    eid = str(sight.get("event_id") or (sight.get("event") or {}).get("id") or "")
    return resolve_shop_rep_event(
        player, eid, "help" if prefer_help else "refuse", reg=reg
    )


# ── Deliver-item quest helpers ──────────────────────────────────────────


def count_item_in_bag(player: Mapping[str, Any], item_id: str) -> int:
    iid = str(item_id or "")
    ids = list(player.get("inventory_ids") or [])
    qtys = list(player.get("inventory_qty") or [])
    total = 0
    for i, x in enumerate(ids):
        if str(x) != iid:
            continue
        q = 1
        if i < len(qtys):
            try:
                q = max(1, int(qtys[i] or 1))
            except Exception:
                q = 1
        total += q
    return total


def try_deliver_shop_quests(
    player: MutableMapping[str, Any],
    reg: Any,
    shop_id: str,
) -> List[str]:
    """
    For active deliver_item quests matching this shop:
    if bag has enough items, consume and complete.
    """
    from game.domain.quests import complete_quest, ensure_quests

    ensure_quests(player, reg)
    notes: List[str] = []
    sid = str(shop_id or "")
    qstate = dict(player.get("quests") or {})
    for qid, st in list(qstate.items()):
        if st.get("completed") or qid in (player.get("quests_done") or []):
            continue
        q = (getattr(reg, "quests", None) or {}).get(qid) or {}
        if str(q.get("type") or "") != "deliver_item":
            continue
        if str(q.get("shop_id") or "") != sid:
            continue
        need_id = str(q.get("item") or q.get("item_id") or "")
        need_n = int(q.get("target") or 1)
        if not need_id or need_n <= 0:
            continue
        have = count_item_in_bag(player, need_id)
        if have < need_n:
            # soft progress note only when close
            st2 = dict(st)
            st2["progress"] = min(have, need_n)
            qstate[qid] = st2
            player["quests"] = qstate
            continue
        # consume need_n units
        if not _consume_item_units(player, reg, need_id, need_n):
            continue
        notes.append(f"  ส่งมอบของให้ร้านครบ — เควส「{q.get('name') or qid}」")
        notes.extend(complete_quest(player, reg, qid, qstate))
        qstate = dict(player.get("quests") or {})
    player["quests"] = qstate
    return notes


def _consume_item_units(
    player: MutableMapping[str, Any],
    reg: Any,
    item_id: str,
    amount: int,
) -> bool:
    """Remove up to amount units of item_id from bag (stack-aware)."""
    try:
        from game.domain.bag_stack import qty_at, remove_units_at
    except Exception:
        remove_units_at = None  # type: ignore
        qty_at = None  # type: ignore

    left = int(amount)
    if left <= 0:
        return True
    # iterate from end so indices stay valid
    ids = list(player.get("inventory_ids") or [])
    for i in range(len(ids) - 1, -1, -1):
        if left <= 0:
            break
        if str(ids[i]) != str(item_id):
            continue
        if remove_units_at is not None:
            q = qty_at(player, i) if qty_at else 1
            take = min(left, max(1, int(q)))
            if remove_units_at(player, i, reg, amount=take):
                left -= take
                ids = list(player.get("inventory_ids") or [])
        else:
            # fallback: remove whole slot
            try:
                from game.domain.rarity import remove_inventory_at_index

                if remove_inventory_at_index(player, i, reg):
                    left -= 1
                    ids = list(player.get("inventory_ids") or [])
            except Exception:
                return False
    return left <= 0


def friend_bonus_lines(player: Mapping[str, Any], shop_id: str) -> List[str]:
    """Soft VIP lines when rep band is friend (80+)."""
    try:
        from game.domain.shop_experience import get_shop_rep, shop_rep_band

        if shop_rep_band(get_shop_rep(player, shop_id)) != "friend":
            return []
    except Exception:
        return []
    return [
        " ลูกค้าประจำ — ร้านยิ้มทัก · ราคาใจดีขึ้นชัด",
        " ชั้นของพิเศษเปิดกว้าง (soft · ไม่ dump)",
    ]
