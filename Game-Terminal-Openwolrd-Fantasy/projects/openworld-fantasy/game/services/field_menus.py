"""Field sub-menus extracted from field_loop (keep loop thin)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.class_paths import apply_class_change, list_available_class_paths
from game.domain.craft import craft, list_recipes
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
    examine_item,
    format_bag_panel,
    format_equip_panel,
    upgrade_equipped_opaque,
)
from game.domain.narrative import emit_narrative, narrate_field
from game.domain.party import (
    apply_party_passives_to_player,
    ensure_party,
    format_party_panel,
    party_size,
    remove_member,
)
from game.domain.personality import (
    ensure_personality,
    format_personality_panel,
    invest_personality_point,
    personality_allocate_menu_axes,
)
from game.domain.progression import (
    STAT_LABELS,
    allocate_stat,
    ensure_progression,
    format_alloc_panel,
    try_occupation_rank_up,
    try_unit_unlock,
)
from game.domain.quests import bump_quest
from game.domain.skill_tree import (
    ensure_skill_tree_state,
    format_tree_panel,
    learn_skill,
    list_master_offers,
    list_visible_tree_nodes,
    renew_master_skill,
    teach_from_master,
)
from game.domain.stats import bump_stat
from game.domain.ui_prefs import cycle_pref, prefs_menu_lines
from game.ports.io import IO
from game.services.shop import run_shop
from game.ui_terminal.layout import render_box


def _ui_prefs_menu(player: Dict[str, Any], io: IO) -> None:
    from game.domain.ui_prefs import cycle_pref, prefs_menu_lines
    from game.ui_terminal.layout import render_box

    while True:
        io.write_line()
        io.write_line(render_box(prefs_menu_lines(player), double=False))
        ch = io.read_line("เลือก: ").strip()
        if ch in ("0", "", "q", "Q"):
            break
        try:
            n = int(ch)
        except ValueError:
            io.write_line("พิมพ์หมายเลข หรือ 0 กลับ")
            continue
        note = cycle_pref(player, n)
        if note:
            io.write_line(f"  {note}")
        else:
            io.write_line("หมายเลขไม่ถูกต้อง")


def _pick_equip_slot(
    io: IO,
    player: Dict[str, Any],
    reg: DataRegistry,
    *,
    title: str = "เลือกช่อง",
    include_accessory: bool = True,
    hands_only: bool = False,
) -> Optional[str]:
    """Numbered slot picker — multi-slot loadout (EL0+)."""
    from game.domain.equipment import (
        EQUIP_SLOT_UI,
        LEGACY_SLOT_MAP,
        item_grip,
        normalize_slot,
    )
    from game.ui_terminal.layout import render_box

    if hands_only:
        slots = [("main_hand", "มือหลัก"), ("off_hand", "มือรอง")]
    else:
        slots = list(EQUIP_SLOT_UI)
        if not include_accessory:
            slots = [(s, l) for s, l in slots if s != "acc_1"]
    lines = [f" {title}", "---"]
    for i, (sid, lab) in enumerate(slots, 1):
        eid = (player.get("equip_ids") or {}).get(sid)
        if eid:
            nm = (reg.items.get(eid) or {}).get("name") or eid
            up = int((player.get("upgrade_levels") or {}).get(sid, 0))
            up_bit = f"  +{up}" if up else ""
            lines.append(f"  {i}  {lab:<12}  {nm}{up_bit}")
        else:
            empty = "(ว่าง)"
            if sid == "off_hand":
                mid = (player.get("equip_ids") or {}).get("main_hand")
                if mid and item_grip(reg.items.get(mid) or {}) == "two_hand":
                    empty = "(ล็อก · สองมือ)"
            lines.append(f"  {i}  {lab:<12}  {empty}")
    lines.extend(["---", "  0  ยกเลิก"])
    io.write_line()
    io.write_line(render_box(lines, double=False))
    raw = io.read_line(f"\n  ช่อง (1–{len(slots)} · 0): ").strip()
    if raw in ("0", "", "q", "Q"):
        return None
    # allow english / legacy ids
    if raw in LEGACY_SLOT_MAP or raw in dict(EQUIP_SLOT_UI):
        ns = normalize_slot(raw)
        if ns == "acc_1" and not include_accessory:
            return None
        if hands_only and ns not in ("main_hand", "off_hand"):
            return None
        return ns
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(slots):
            return slots[idx][0]
    except Exception:
        pass
    io.write_line(f"  เลือก 1–{len(slots)}")
    return None


def _manage_gear(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    ensure_gear_fields(player)
    apply_party_passives_to_player(player, reg)
    recompute_stats(player, reg)
    from game.domain.inventory_sys import format_gear_menu_lines
    from game.ui_terminal.layout import render_box

    while True:
        apply_party_passives_to_player(player, reg)
        recompute_stats(player, reg)
        io.write_line()
        io.write_line(render_box(format_equip_panel(player, reg), double=False))
        io.write_line()
        io.write_line(render_box(format_gear_menu_lines(), double=False))
        ids = list(player.get("inventory_ids") or [])
        gear = [i for i in ids if (reg.items.get(i) or {}).get("kind") == "equipment"]
        ch = io.read_line("\n  เลือก (1–8 · 0 กลับ): ").strip()
        if ch in ("0", ""):
            break
        if ch == "1":
            if not gear:
                io.write_line(" ไม่มีอุปกรณ์ในคลัง (ไปร้านหรือลูท)")
                continue
            pick_lines = [" สวมจากกระเป๋า", "---"]
            from game.domain.equipment import SLOT_LABEL_TH, item_grip, normalize_slot

            for i, gid in enumerate(gear, 1):
                it = reg.items.get(gid) or {}
                slot_lab = SLOT_LABEL_TH.get(
                    normalize_slot(str(it.get("slot") or "")),
                    str(it.get("slot") or ""),
                )
                grip = item_grip(it)
                grip_bit = ""
                if grip == "two_hand":
                    grip_bit = " ·สองมือ"
                elif grip == "shield":
                    grip_bit = " ·โล่"
                elif grip == "one_hand":
                    grip_bit = " ·มือเดียว"
                pick_lines.append(
                    f"  {i}. {it.get('name')}  ({slot_lab}{grip_bit})  "
                    f"ATK+{it.get('atk', 0)} HP+{it.get('max_hp', 0)}"
                )
            pick_lines.extend(["---", "  0  ยกเลิก"])
            io.write_line()
            io.write_line(render_box(pick_lines, double=False))
            try:
                raw = io.read_line("\n  สวมหมายเลข: ").strip()
                if raw in ("0", ""):
                    continue
                idx = int(raw) - 1
                iid = gear[max(0, min(len(gear) - 1, idx))]
                it = reg.items.get(iid) or {}
                # EL4: dual / off-hand soft choice when one_hand and main filled
                target_slot = None
                from game.domain.equipment import (
                    GRIP_ONE_HAND,
                    GRIP_TWO_HAND,
                    item_grip,
                    allowed_slots_for_item,
                )

                grip = item_grip(it)
                allowed = allowed_slots_for_item(it)
                main_id = (player.get("equip_ids") or {}).get("main_hand")
                off_id = (player.get("equip_ids") or {}).get("off_hand")
                if (
                    grip == GRIP_ONE_HAND
                    and "off_hand" in allowed
                    and main_id
                    and not off_id
                ):
                    main_g = item_grip(reg.items.get(main_id) or {})
                    if main_g == GRIP_ONE_HAND:
                        conf = [
                            " ใส่มือไหน?",
                            "---",
                            "  1  มือหลัก (แทนของเดิม)",
                            "  2  มือรอง (ถือคู่)",
                            "---",
                            "  0  ยกเลิก",
                        ]
                        io.write_line()
                        io.write_line(render_box(conf, double=False))
                        hand = io.read_line("\n  มือ (1–2 · 0): ").strip()
                        if hand in ("0", ""):
                            continue
                        if hand == "2":
                            target_slot = "off_hand"
                        else:
                            target_slot = "main_hand"
                elif grip == GRIP_TWO_HAND and off_id:
                    conf = [
                        " อาวุธสองมือ",
                        "---",
                        " ต้องว่างมือรอง — ของมือรองจะกลับกระเป๋า",
                        "---",
                        "  1  ยืนยันใส่",
                        "  0  ยกเลิก",
                    ]
                    io.write_line()
                    io.write_line(render_box(conf, double=False))
                    conf_ch = io.read_line("\n  ยืนยัน (1 · 0): ").strip()
                    if conf_ch not in ("1", "y", "Y", "ใช่"):
                        io.write_line(" ยกเลิก")
                        continue
                msg = equip_item(
                    player, iid, reg, target_slot=target_slot
                )
                io.write_line(f" {msg}")
                if (player.get("equip_ids") or {}).get("main_hand") or (
                    player.get("equip_ids") or {}
                ).get("weapon"):
                    for line in bump_quest(player, reg, "equip_weapon"):
                        io.write_line(line)
            except Exception:
                io.write_line(" ยกเลิก")
        elif ch == "2":
            bag = list(player.get("card_bag") or [])
            if not bag:
                io.write_line("ไม่มีการ์ด — ซื้อที่ร้านหรือลูท")
                continue
            for i, cid in enumerate(bag, 1):
                c = reg.cards.get(cid) or {}
                io.write_line(
                    f"  {i}. {c.get('name')} เข้ากับ {c.get('compatible')} "
                    f"+{c.get('bonuses')}"
                )
            try:
                ci = int(io.read_line("\n  การ์ดหมายเลข: ").strip()) - 1
                cid = bag[max(0, min(len(bag) - 1, ci))]
            except Exception:
                continue
            slot = _pick_equip_slot(
                io, player, reg, title="ใส่การ์ดที่ช่อง", include_accessory=True
            )
            if not slot:
                continue
            try:
                si = int(io.read_line("  หมายเลขช่องการ์ดบนชิ้น (1.. · Enter=1): ").strip() or "1") - 1
            except Exception:
                si = 0
            cname = (reg.cards.get(cid) or {}).get("name") or cid
            from game.domain.equipment import SLOT_LABEL_TH, normalize_slot

            slot_th = SLOT_LABEL_TH.get(normalize_slot(slot), slot)
            io.write_line(f" จะใส่: {cname} → {slot_th} ช่อง {si + 1}")
            conf = io.read_line(" ยืนยันใส่การ์ด? (y/n): ").strip().lower()
            if conf not in ("y", "yes", "ใช่", "1"):
                io.write_line(" ยกเลิกใส่การ์ด")
                continue
            msg = socket_card(player, slot, si, cid, reg)
            io.write_line(f" {msg}")
            if "ใส่" in msg:
                bump_stat(player, "cards_socketed", 1)
                for line in bump_quest(player, reg, "socket_card"):
                    io.write_line(line)
        elif ch == "3":
            slot = _pick_equip_slot(
                io, player, reg, title="ถอดการ์ดจากช่อง", include_accessory=True
            )
            if not slot:
                continue
            socks = (player.get("sockets") or {}).get(slot) or []
            if not any(socks):
                io.write_line(" ไม่มีการ์ดเสียบในช่องนี้")
                continue
            sock_lines = [" ช่องการ์ด", "---"]
            for i, cid in enumerate(socks, 1):
                nm = (reg.cards.get(cid) or {}).get("name", "-") if cid else "ว่าง"
                sock_lines.append(f"  {i}  {nm}")
            sock_lines.extend(["---", "  0  ยกเลิก"])
            io.write_line()
            io.write_line(render_box(sock_lines, double=False))
            try:
                raw = io.read_line("\n  ถอดช่อง (เลข · 0): ").strip()
                if raw in ("0", ""):
                    continue
                si = int(raw) - 1
                io.write_line(f" {unsocket_card(player, slot, si, reg)}")
            except Exception:
                io.write_line(" ยกเลิก")
        elif ch == "4":
            from game.domain.inventory_sys import (
                can_upgrade_equipped,
                format_upgrade_preview,
            )

            slot = _pick_equip_slot(
                io, player, reg, title="อัปเกรดช่อง", include_accessory=True
            )
            if not slot:
                continue
            if not can_upgrade_equipped(player, slot):
                io.write_line(" ช่องนี้อัปเกรดไม่ได้ (ว่าง หรือถึงขีดแล้ว)")
                continue
            prev = format_upgrade_preview(player, slot, reg)
            io.write_line()
            io.write_line(render_box([" ตัวอย่างอัป", "---", *[f" {x}" for x in prev]], double=False))
            conf = io.read_line("\n  ยืนยันอัปเกรด? (y/n): ").strip().lower()
            if conf not in ("y", "yes", "ใช่", "1"):
                io.write_line(" ยกเลิกอัปเกรด")
                continue
            msg = upgrade_equipped_opaque(player, slot, reg)
            io.write_line()
            io.write_line(render_box([" ผลอัป", "---", f" {msg}"], double=False))
            if "สำเร็จ" in msg:
                bump_stat(player, "upgrades", 1)
        elif ch == "5":
            loc = str(player.get("location"))
            io.write_line()
            io.write_line(
                render_box(
                    [
                        " ร้าน (ทางลัดจากเกียร์)",
                        "---",
                        "  1  เร่ / เมือง",
                        "  2  ตลาดสวรรค์",
                        "  3  ตลาดนรก",
                        "  4  ตลาดวัสดุหายาก",
                        "  5  ศาลาตำนาน",
                        "  0  กลับ",
                    ],
                    double=False,
                )
            )
            sc = io.read_line("\n  เลือก (1–5 · 0): ").strip()
            if sc == "2":
                run_shop(player, reg, io, shop_id="celestial_bazaar")
            elif sc == "3":
                run_shop(player, reg, io, shop_id="infernal_market")
            elif sc == "4":
                run_shop(player, reg, io, shop_id="rare_exchange")
            elif sc == "5":
                run_shop(player, reg, io, shop_id="legend_pavilion")
            elif sc == "1" or (sc not in ("0", "") and sc not in ("2", "3", "4", "5")):
                shop_id = (
                    "city_armory"
                    if loc in ("ancient_city", "crystal_peak")
                    else "traveling_merchant"
                )
                run_shop(player, reg, io, shop_id=shop_id)
        elif ch == "6":
            _run_craft_menu(player, reg, io)
        elif ch == "7":
            _bag_menu(player, reg, io)
        elif ch == "8":
            from game.ui_terminal.layout import render_box

            recompute_stats(player, reg)
            io.write_line()
            io.write_line(render_box(describe_loadout(player, reg), double=False))
            io.read_line("\n  Enter...")


def _bag_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    while True:
        for line in format_bag_panel(player, reg):
            io.write_line(line)
        ch = io.read_line("ดูไอเทมหมายเลข (หรือ C1=การ์ดแรก) 0=กลับ: ").strip()
        if ch in ("0", ""):
            return
        if ch.upper().startswith("C"):
            try:
                ci = int(ch[1:]) - 1
                bag = list(player.get("card_bag") or [])
                cid = bag[max(0, min(len(bag) - 1, ci))]
            except Exception:
                io.write_line("การ์ดไม่ถูกต้อง")
                continue
            for line in examine_item(cid, reg):
                io.write_line(line)
            io.read_line("Enter...")
            continue
        try:
            idx = int(ch)
        except Exception:
            continue
        iid = bag_item_id_at(player, idx)
        if not iid:
            io.write_line("ไม่มีไอเทมหมายเลขนั้น")
            continue
        for line in examine_item(iid, reg, rarity=bag_item_rarity_at(player, idx)):
            io.write_line(line)
        io.write_line(" 1.สวม(ถ้าเป็นเกียร์)  0.กลับรายการ")
        sub = io.read_line("เลือก: ").strip()
        if sub == "1":
            it = reg.items.get(iid) or {}
            if it.get("kind") == "equipment" or it.get("slot") in (
                "weapon",
                "armor",
                "accessory",
            ):
                io.write_line(equip_item(player, iid, reg))
            else:
                io.write_line("สวมชิ้นนี้ไม่ได้ — อ่านวิธีใช้ด้านบน")


def _party_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    ensure_party(player)
    apply_party_passives_to_player(player, reg)
    recompute_stats(player, reg)
    while True:
        io.write_line()
        for line in format_party_panel(player, reg):
            io.write_line(line)
        io.write_line(" 1.ปลดสมาชิก  0.กลับ  (รับสมาชิกใหม่: เจอในโลก/สำรวจ)")
        ch = io.read_line("เลือก: ").strip()
        if ch in ("0", ""):
            return
        if ch == "1":
            if party_size(player) <= 0:
                io.write_line("ไม่มีใครในทีม")
                continue
            try:
                idx = int(io.read_line("ปลดหมายเลข: ").strip()) - 1
            except Exception:
                continue
            party = list(player.get("party") or [])
            name = (party[idx].get("name") if 0 <= idx < len(party) else "?")
            msg = remove_member(player, idx)
            io.write_line(msg)
            emit_narrative(
                io, narrate_field(reg, "party_dismiss", name=name or "?")
            )
            apply_party_passives_to_player(player, reg)
            recompute_stats(player, reg)



def _class_change_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    """
    Soft occupation offers — accept or permanently decline.
    Conditions never shown. Declined occupation will not return.
    Other offers may still appear later.
    """
    from game.domain.class_paths import (
        apply_class_change,
        decline_class_offer,
        list_available_class_paths,
    )

    paths = list_available_class_paths(player, reg)
    if not paths:
        declined = player.get("declined_occupations") or []
        if declined:
            io.write_line("…ไม่มีข้อเสนออาชีพตอนนี้ (บางทางคุณผลักออกไปแล้ว)")
        else:
            io.write_line("…ยังไม่รู้สึกถึงข้อเสนออาชีพ (เงื่อนไขที่มองไม่เห็นยังไม่ถึง)")
        io.read_line("Enter...")
        return
    io.write_line("\n── ข้อเสนออาชีพ ──")
    io.write_line(" ระบบยื่นทางมา… คุณไม่รู้ว่าทำไมถึงถูกเสนอ")
    io.write_line(" รับ = เข้าสายนั้น · ปฏิเสธ = ทางนั้นหายไปถาวร")
    io.write_line(" (อาชีพอื่นยังอาจเสนอทีหลัง · 0 = ปิดคิดก่อน ทางยังอยู่)")
    for i, path in enumerate(paths, 1):
        to_id = path.get("to_occupation")
        occ = reg.occupations.get(str(to_id)) or {}
        io.write_line(f"  {i}. {path.get('label') or occ.get('name')}")
        if path.get("flavor"):
            io.write_line(f"     “{path.get('flavor')}”")
    io.write_line("  0. ปิด (ยังไม่ตัดสินใจ)")
    ch = io.read_line("เลือกข้อเสนอ: ").strip()
    if ch in ("0", ""):
        io.write_line("…เก็บข้อเสนอไว้ก่อน")
        return
    try:
        idx = int(ch) - 1
        path = paths[max(0, min(len(paths) - 1, idx))]
    except Exception:
        io.write_line("ยกเลิก")
        return
    label = path.get("label") or (
        (reg.occupations.get(str(path.get("to_occupation"))) or {}).get("name")
    )
    io.write_line(f"\n ข้อเสนอ: {label}")
    if path.get("flavor"):
        io.write_line(f" “{path.get('flavor')}”")
    conf = io.read_line(
        "  y = รับอาชีพนี้   n = ปฏิเสธถาวร (หายไป)   0 = คิดก่อน: "
    ).strip().lower()
    if conf in ("0", ""):
        io.write_line("…ยังไม่ตัดสินใจ ทางนี้ยังอยู่")
        return
    if conf in ("n", "no", "ไม่", "ปฏิเสธ", "2"):
        for line in decline_class_offer(player, path):
            io.write_line(line)
        return
    if conf not in ("y", "yes", "ใช่", "1", "รับ"):
        io.write_line("ยกเลิก")
        return
    for line in apply_class_change(player, reg, path):
        io.write_line(line)


def _stat_allocate_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    ensure_progression(player, reg)
    from game.domain.progression import ALLOCATE_KEYS, format_alloc_menu_lines
    from game.ui_terminal.layout import render_box

    while True:
        io.write_line()
        io.write_line(render_box(format_alloc_panel(player), double=False))
        if int(player.get("stat_points") or 0) <= 0:
            io.write_line()
            io.write_line(
                render_box(
                    [
                        " ไม่มีแต้มคงเหลือ",
                        "---",
                        " เลเวลอัพเพื่อได้แต้มใหม่",
                        " 0  กลับ",
                    ],
                    double=False,
                )
            )
            io.read_line("\n  Enter...")
            return

        io.write_line()
        io.write_line(render_box(format_alloc_menu_lines(player), double=False))
        nkeys = len(ALLOCATE_KEYS)
        ch = io.read_line(f"\n  เลือกสถานะ (1–{nkeys} · 0 กลับ): ").strip()
        if ch in ("0", "", "q", "Q"):
            return
        try:
            idx = int(ch) - 1
            if idx < 0 or idx >= len(ALLOCATE_KEYS):
                io.write_line(f"  เลือก 1–{nkeys} เท่านั้น")
                continue
            stat = ALLOCATE_KEYS[idx]
        except Exception:
            io.write_line(f"  พิมพ์เลข 1–{nkeys}")
            continue

        left = int(player.get("stat_points") or 0)
        lab = STAT_LABELS.get(stat, stat)
        n = io.read_line(f"  ใส่กี่แต้มใน「{lab}」 (1–{left} · Enter=1): ").strip()
        try:
            pts = int(n) if n else 1
        except Exception:
            pts = 1
        pts = max(1, min(left, pts))
        msg = allocate_stat(player, reg, stat, pts)
        io.write_line()
        io.write_line(render_box([" ผล", "---", f" {msg}"], double=False))
        for line in try_occupation_rank_up(player, reg):
            io.write_line(line)
        for line in try_unit_unlock(player, reg):
            io.write_line(line)
        # soft class path hint after invest
        try:
            from game.domain.class_paths import soft_offer_hint

            hint = soft_offer_hint(player, reg)
            if hint:
                io.write_line(f" {hint}")
        except Exception:
            pass


def _personality_allocate_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    """Player invests personality_points into trait axes (gain methods stay hidden)."""
    ensure_personality(player, reg)
    from game.domain.personality import format_personality_menu_lines
    from game.ui_terminal.layout import render_box

    axes = personality_allocate_menu_axes(reg)
    while True:
        io.write_line()
        io.write_line(render_box(format_personality_panel(player, reg), double=False))
        pts = int(player.get("personality_points") or 0)
        if pts <= 0:
            io.write_line()
            io.write_line(
                render_box(
                    [
                        " ไม่มีแต้มนิสัย",
                        "---",
                        " ต้องค้นหาเอง · ห้องสมุดอาจใบ้เศษๆ",
                        "---",
                        "  1  อ่านแผงอีกครั้ง",
                        "  0  กลับ",
                    ],
                    double=False,
                )
            )
            ch = io.read_line("\n  เลือก (1 · 0): ").strip()
            if ch in ("0", ""):
                return
            continue

        io.write_line()
        io.write_line(
            render_box(format_personality_menu_lines(player, reg), double=False)
        )
        ch = io.read_line(f"\n  เลือกทาง (1–{len(axes)} · 0 กลับ): ").strip()
        if ch in ("0", "", "q", "Q"):
            return
        try:
            idx = int(ch) - 1
            if idx < 0 or idx >= len(axes):
                io.write_line(f"  เลือก 1–{len(axes)}")
                continue
            axis_id, lab = axes[idx]
        except Exception:
            io.write_line("  พิมพ์เลข")
            continue
        left = int(player.get("personality_points") or 0)
        n = io.read_line(
            f"  ใส่กี่แต้มใน「{lab}」 (1–{left} · Enter=1): "
        ).strip()
        try:
            use = int(n) if n else 1
        except Exception:
            use = 1
        use = max(1, min(left, use))
        msg = invest_personality_point(player, reg, axis_id, use)
        io.write_line()
        io.write_line(render_box([" ผล", "---", f" {msg}"], double=False))


def _skill_tree_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    """Occupation skill tree — learn with prereqs + multi-currency costs."""
    ensure_skill_tree_state(player)
    while True:
        io.write_line()
        nodes = list_visible_tree_nodes(player, reg)
        for line in format_tree_panel(player, reg):
            io.write_line(line)
        io.write_line(" เลือกหมายเลขเพื่อเรียน/เติม · 0 กลับ")
        ch = io.read_line("เลือก: ").strip()
        if ch in ("0", ""):
            return
        try:
            idx = int(ch) - 1
            if idx < 0 or idx >= len(nodes):
                io.write_line("หมายเลขไม่ถูกต้อง")
                continue
            node = nodes[idx]
        except Exception:
            io.write_line("ยกเลิก")
            continue
        sid = str(node.get("id"))
        st = node.get("_status")
        if st == "owned":
            io.write_line("มีสกิลนี้อยู่แล้ว")
            continue
        if st == "near":
            io.write_line("ยังเรียนไม่ได้ — ขาดพื้นฐาน หรือต้องหานักสอน")
            continue
        if st == "depleted":
            io.write_line(renew_master_skill(player, reg, sid))
            continue
        # available
        methods = list((node.get("learn") or {}).get("method") or ["self"])
        if "self" not in methods and "rank" not in methods:
            io.write_line("สกิลนี้ต้องเรียนจากอาจารย์หรือเควส — เมนูนี้เรียนเองไม่ได้")
            continue
        conf = io.read_line("ยืนยันเรียน? (1=ใช่): ").strip()
        if conf != "1":
            continue
        io.write_line(learn_skill(player, reg, sid))


def _master_teach_menu(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    master_id: str,
) -> None:
    from game.domain.skill_tree import get_master

    m = get_master(reg, master_id)
    if not m:
        io.write_line("อาจารย์เงียบ... (ยังไม่มีข้อมูล)")
        return
    io.write_line(f"\n── {m.get('name', master_id)} ──")
    if m.get("flavor"):
        io.write_line(f"  {m.get('flavor')}")
    offers = list_master_offers(reg, master_id)
    if not offers:
        io.write_line("ไม่มีบทเรียนในตอนนี้")
        return
    for i, off in enumerate(offers, 1):
        sid = str(off.get("skill_id"))
        sk = reg.skills.get(sid) or {}
        name = sk.get("name") or sid
        lease = off.get("lease_uses")
        lease_s = f"· ใช้ได้ {lease} ครั้ง" if lease is not None else "· ถาวร"
        fee = []
        if off.get("fee_world"):
            fee.append(f"โลก{off['fee_world']}")
        if off.get("fee_heaven"):
            fee.append(f"สวรรค์{off['fee_heaven']}")
        if off.get("fee_hell"):
            fee.append(f"นรก{off['fee_hell']}")
        fee_s = ",".join(fee) if fee else "ฟรี?"
        owned = sid in (player.get("skills") or [])
        tag = " [รู้แล้ว]" if owned else ""
        io.write_line(f"  {i}. {name}{tag}  ค่า:{fee_s} {lease_s}")
    io.write_line("  0. ลาจาก")
    ch = io.read_line("ขอเรียนข้อ: ").strip()
    if ch in ("0", ""):
        return
    try:
        idx = int(ch) - 1
        off = offers[max(0, min(len(offers) - 1, idx))]
    except Exception:
        io.write_line("ยกเลิก")
        return
    io.write_line(teach_from_master(player, reg, master_id, str(off.get("skill_id"))))


def _run_craft_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    import random as _rnd

    from game.domain.craft import (
        count_recipes_elsewhere,
        format_stations_line,
        recipe_chance_label,
        station_label,
    )
    from game.domain.rarity import rarity_label

    recipes = list_recipes(reg, player, require_station=True)
    io.write_line("\n── คราฟ ──")
    io.write_line(f" {format_stations_line(player, reg)}")
    io.write_line(" (วัตถุดิบขั้นต่ำ · โอกาส soft · สูตรตามสถานีพื้นที่)")
    elsewhere = count_recipes_elsewhere(reg, player)
    if elsewhere > 0:
        from game.domain.craft import craft_elsewhere_hint

        hint = craft_elsewhere_hint(reg)
        io.write_line(f" (อีก ~{elsewhere} สูตรต้องสถานีอื่น{(' · ' + hint) if hint else ''})")

    if not recipes:
        io.write_line(" ที่นี่ยังไม่มีสูตรที่ใช้ได้ (เลเวล/สถานี)")
        io.write_line("  0. กลับ")
        io.read_line("Enter...")
        return

    # soft sort: unlock level · station · name (K4 list friendliness)
    recipes = sorted(
        recipes,
        key=lambda r: (
            int(r.get("unlock_level") or 1),
            str(r.get("station") or ""),
            str(r.get("name") or r.get("id") or ""),
        ),
    )

    last_st = None
    for i, r in enumerate(recipes, 1):
        st = str(r.get("station") or "")
        if st and st != last_st and len(recipes) >= 6:
            io.write_line(f" ··· {station_label(st, reg)} ···")
            last_st = st
        inputs = r.get("inputs") or {}
        ir = r.get("inputs_rarity") or {}
        bits = []
        for k, v in inputs.items():
            nm = (reg.items.get(k) or reg.cards.get(k) or {}).get("name") or k
            if k in ir:
                bits.append(f"{nm}x{v}(≥{rarity_label(reg, str(ir[k]))})")
            else:
                bits.append(f"{nm}x{v}")
        need = ", ".join(bits)
        out_r = r.get("output_rarity")
        out_bit = f" [{rarity_label(reg, str(out_r))}]" if out_r else ""
        out_nm = (
            (reg.items.get(str(r.get("output"))) or reg.cards.get(str(r.get("output"))) or {}).get(
                "name"
            )
            or r.get("output")
        )
        feel = recipe_chance_label(player, r, reg)
        st_bit = f" · {station_label(st, reg)}" if st else ""
        io.write_line(
            f"  {i}. {r.get('name')}{st_bit} | ใช้: {need} + เงิน {r.get('money', 0)} "
            f"→ {out_nm}{out_bit} (Lv.{r.get('unlock_level', 1)}) · {feel}"
        )
    io.write_line("  0. กลับ")
    ch = io.read_line("คราฟหมายเลข: ").strip()
    if ch in ("0", ""):
        return
    try:
        idx = int(ch) - 1
        rid = str(recipes[max(0, min(len(recipes) - 1, idx))].get("id"))
    except Exception:
        io.write_line("ยกเลิก")
        return
    msg = craft(player, reg, rid, rng=_rnd.Random())
    for line in str(msg).splitlines():
        io.write_line(line)
    if "สำเร็จ" in msg:
        bump_stat(player, "crafts", 1)
        for line in bump_quest(player, reg, "craft"):
            io.write_line(line)


def run_rank_hub(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: Any,
    rng: Any = None,
) -> None:
    """
    W0 board + W2 lite rank challenge from explore (A key).
    """
    import random

    from game.domain.world_social import (
        apply_rank_challenge_result,
        build_world_ranking,
        challenge_bounty,
        format_ranking_lines,
        try_rank_challenge,
        write_echo_snapshot,
    )
    from game.ui_terminal.layout import render_box

    rng = rng or random.Random()
    world_id = str(player.get("world_id") or "default")
    # ensure our echo is fresh
    try:
        write_echo_snapshot(player, world_id)
    except Exception:
        pass

    while True:
        lines = format_ranking_lines(world_id, reg, viewer=player)
        menu = [
            " อันดับโลก · ท้าเงา · ร่องรอย",
            "---",
            *lines[:20],
            "---",
            "  1  ท้าอันดับ (จ่ายค่าหัว · สู้เงา)",
            "  2  บันทึกร่องรอย (รีเฟรช echo ของคุณ)",
            "  0  กลับ",
        ]
        io.write_line()
        io.write_line(render_box(menu, double=False))
        ch = io.read_line("\n  เลือก (1–2 · 0): ").strip()
        if ch in ("0", "", "q", "Q"):
            break
        if ch == "2":
            try:
                path = write_echo_snapshot(player, world_id)
                if path:
                    io.write_line("  ร่องรอยของคุณถูกจารึกใหม่ (เงาในโลกนี้สดขึ้น soft)")
                else:
                    io.write_line("  บันทึกไม่ได้ — ตรวจ id ตัวละคร")
            except Exception:
                io.write_line("  บันทึกร่องรอยล้มเหลวเบาๆ")
            io.read_line("Enter...")
            continue
        if ch != "1":
            continue
        board = build_world_ranking(world_id, reg, limit=10)
        if not board:
            io.write_line(" ยังไม่มีชื่อบนบอร์ด")
            continue
        pick_lines = [" ท้าอันดับไหน?", "---"]
        for row in board:
            b = challenge_bounty(int(row["rank"]), reg)
            pick_lines.append(
                f"  {row['rank']}  {row.get('name')} · {row.get('soft_band')} "
                f"· ค่าหัว ~{b}"
            )
        pick_lines.extend(["---", "  0  ยกเลิก"])
        io.write_line()
        io.write_line(render_box(pick_lines, double=False))
        raw = io.read_line("\n  อันดับ (เลข · 0): ").strip()
        if raw in ("0", ""):
            continue
        try:
            tr = int(raw)
        except Exception:
            io.write_line(" เลขไม่ถูกต้อง")
            continue
        ok, msg, foe = try_rank_challenge(player, reg, rng, target_rank=tr)
        io.write_line(f" {msg}")
        if not ok or not foe:
            continue
        conf = io.read_line(" ยืนยันสู้เงาอันดับ? (1=ใช่): ").strip()
        if conf != "1":
            # refund bounty
            ctx = player.pop("_rank_challenge", None) or {}
            player["money_world"] = int(player.get("money_world") or 0) + int(
                ctx.get("bounty") or 0
            )
            io.write_line(" ยกเลิก — คืนค่าหัว")
            continue
        from game.services.combat_session import _run_combat

        _run_combat(player, reg, io, rng, mon=foe, ambush=False)
        won = int(player.get("hp") or 0) > 0
        for line in apply_rank_challenge_result(player, reg, won=won):
            io.write_line(f" {line}")
        io.read_line("Enter...")

