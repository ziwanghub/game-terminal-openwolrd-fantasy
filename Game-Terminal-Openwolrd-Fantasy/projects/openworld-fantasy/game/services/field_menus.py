"""Field sub-menus extracted from field_loop (keep loop thin)."""
from __future__ import annotations

from typing import Any, Dict

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


def _manage_gear(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    ensure_gear_fields(player)
    apply_party_passives_to_player(player, reg)
    recompute_stats(player, reg)
    while True:
        io.write_line("\n── อุปกรณ์ / กระเป๋า ──")
        for line in format_equip_panel(player, reg):
            io.write_line(line)
        ids = list(player.get("inventory_ids") or [])
        gear = [i for i in ids if (reg.items.get(i) or {}).get("kind") == "equipment"]
        io.write_line(
            "1.สวม  2.ใส่การ์ด  3.ถอดการ์ด  4.อัปเกรด  5.ร้าน  6.คราฟ"
        )
        io.write_line("7.กระเป๋า/ดูไอเทม  8.ดูเกียร์ละเอียด  0.กลับ")
        ch = io.read_line("เลือก: ").strip()
        if ch == "0":
            break
        if ch == "1":
            if not gear:
                io.write_line("ไม่มีอุปกรณ์ในคลัง (ไปร้านหรือลูท)")
                continue
            for i, gid in enumerate(gear, 1):
                it = reg.items.get(gid) or {}
                io.write_line(
                    f"  {i}. {it.get('name')} ({it.get('slot')}) "
                    f"ATK+{it.get('atk', 0)} HP+{it.get('max_hp', 0)} ช่อง{it.get('sockets', 0)}"
                )
            try:
                idx = int(io.read_line("สวม: ").strip()) - 1
                msg = equip_item(player, gear[max(0, min(len(gear) - 1, idx))], reg)
                io.write_line(msg)
                if (player.get("equip_ids") or {}).get("weapon"):
                    for line in bump_quest(player, reg, "equip_weapon"):
                        io.write_line(line)
            except Exception:
                io.write_line("ยกเลิก")
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
                ci = int(io.read_line("การ์ด: ").strip()) - 1
                cid = bag[max(0, min(len(bag) - 1, ci))]
            except Exception:
                continue
            slot = io.read_line("ช่องอุปกรณ์ (weapon/armor): ").strip() or "weapon"
            try:
                si = int(io.read_line("หมายเลขช่องการ์ด (1..): ").strip()) - 1
            except Exception:
                si = 0
            cname = (reg.cards.get(cid) or {}).get("name") or cid
            io.write_line(f" จะใส่: {cname} → {slot} ช่อง {si + 1}")
            conf = io.read_line("ยืนยันใส่การ์ด? (y=ตกลง / n=ยกเลิก): ").strip().lower()
            if conf not in ("y", "yes", "ใช่", "1"):
                io.write_line("ยกเลิกใส่การ์ด")
                continue
            msg = socket_card(player, slot, si, cid, reg)
            io.write_line(msg)
            if "ใส่" in msg:
                bump_stat(player, "cards_socketed", 1)
                for line in bump_quest(player, reg, "socket_card"):
                    io.write_line(line)
        elif ch == "3":
            slot = io.read_line("ถอดจาก (weapon/armor): ").strip() or "weapon"
            socks = (player.get("sockets") or {}).get(slot) or []
            if not any(socks):
                io.write_line("ไม่มีการ์ดเสียบ")
                continue
            for i, cid in enumerate(socks, 1):
                nm = (reg.cards.get(cid) or {}).get("name", "-") if cid else "ว่าง"
                io.write_line(f"  {i}. {nm}")
            try:
                si = int(io.read_line("ช่อง: ").strip()) - 1
                io.write_line(unsocket_card(player, slot, si, reg))
            except Exception:
                io.write_line("ยกเลิก")
        elif ch == "4":
            from game.domain.inventory_sys import (
                can_upgrade_equipped,
                format_upgrade_preview,
            )

            slot = io.read_line("อัปเกรด (weapon/armor/accessory): ").strip() or "weapon"
            if slot not in ("weapon", "armor", "accessory"):
                io.write_line("ช่อง: weapon / armor / accessory")
                continue
            if not can_upgrade_equipped(player, slot):
                io.write_line("ช่องนี้อัปเกรดไม่ได้ (ว่าง หรือถึงขีดแล้ว)")
                continue
            for line in format_upgrade_preview(player, slot, reg):
                io.write_line(line)
            conf = io.read_line("ยืนยันเริ่มพิธีอัปเกรด? (y=ตกลง / n=ยกเลิก): ").strip().lower()
            if conf not in ("y", "yes", "ใช่", "1"):
                io.write_line("ยกเลิกอัปเกรด")
                continue
            msg = upgrade_equipped_opaque(player, slot, reg)
            io.write_line(msg)
            if "สำเร็จ" in msg:
                bump_stat(player, "upgrades", 1)
        elif ch == "5":
            loc = str(player.get("location"))
            io.write_line(
                "ร้าน: 1 เร่/เมือง  2 ตลาดสวรรค์  3 ตลาดนรก"
            )
            io.write_line(
                "      4 ตลาดของหายาก  5 ศาลาตำนาน  0 กลับ"
            )
            sc = io.read_line("เลือก: ").strip()
            if sc == "2":
                run_shop(player, reg, io, shop_id="celestial_bazaar")
            elif sc == "3":
                run_shop(player, reg, io, shop_id="infernal_market")
            elif sc == "4":
                run_shop(player, reg, io, shop_id="rare_exchange")
            elif sc == "5":
                run_shop(player, reg, io, shop_id="legend_pavilion")
            elif sc != "0":
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
            for line in describe_loadout(player, reg):
                io.write_line(line)
            io.read_line("Enter...")


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
    """Soft class change — only if paths qualify; no condition spoilers."""
    from game.domain.class_paths import apply_class_change, list_available_class_paths

    paths = list_available_class_paths(player, reg)
    if not paths:
        io.write_line("…ยังไม่รู้สึกถึงทางแยกอาชีพ (หรือยังไม่ถึงเงื่อนไขที่มองไม่เห็น)")
        io.read_line("Enter...")
        return
    io.write_line("\n── ทางแยกอาชีพ ──")
    io.write_line(" โลกดึงคุณไปทางหนึ่ง… คุณไม่รู้แน่ชัดว่าทำไม")
    for i, path in enumerate(paths, 1):
        to_id = path.get("to_occupation")
        occ = reg.occupations.get(str(to_id)) or {}
        io.write_line(f"  {i}. {path.get('label') or occ.get('name')}")
        if path.get("flavor"):
            io.write_line(f"     “{path.get('flavor')}”")
    io.write_line("  0. ยังไม่เลือก")
    ch = io.read_line("เลือกทาง: ").strip()
    if ch in ("0", ""):
        return
    try:
        idx = int(ch) - 1
        path = paths[max(0, min(len(paths) - 1, idx))]
    except Exception:
        io.write_line("ยกเลิก")
        return
    conf = io.read_line("ยืนยันก้าวสู่ทางนี้? (y/n): ").strip().lower()
    if conf not in ("y", "yes", "ใช่", "1"):
        io.write_line("ถอยกลับ")
        return
    for line in apply_class_change(player, reg, path):
        io.write_line(line)
    player.setdefault("flags", {})["no_class_yet"] = False


def _stat_allocate_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    ensure_progression(player, reg)
    while True:
        io.write_line("\n── แจกแต้มสถานะ ──")
        for line in format_alloc_panel(player):
            io.write_line(line)
        if int(player.get("stat_points") or 0) <= 0:
            io.write_line("(ไม่มีแต้ม — เลเวลอัพเพื่อได้แต้ม)")
            io.read_line("Enter...")
            return
        from game.domain.progression import ALLOCATE_KEYS

        io.write_line("เลือกสถานะที่จะลงทุน:")
        for i, k in enumerate(ALLOCATE_KEYS, 1):
            io.write_line(f"  {i}. {STAT_LABELS[k]}")
        io.write_line("  0. กลับ")
        ch = io.read_line("เลือก: ").strip()
        if ch in ("0", ""):
            return
        try:
            idx = int(ch) - 1
            stat = ALLOCATE_KEYS[max(0, min(len(ALLOCATE_KEYS) - 1, idx))]
        except Exception:
            continue
        n = io.read_line("ใส่กี่แต้ม (default 1): ").strip()
        try:
            pts = int(n) if n else 1
        except Exception:
            pts = 1
        io.write_line(allocate_stat(player, reg, stat, pts))
        for line in try_occupation_rank_up(player, reg):
            io.write_line(line)
        for line in try_unit_unlock(player, reg):
            io.write_line(line)
        # soft class path hint after invest
        try:
            from game.domain.class_paths import list_available_class_paths

            if list_available_class_paths(player, reg):
                io.write_line("…รู้สึกว่าทางอาชีพบางอย่างเปิดแล้ว (กด C)")
        except Exception:
            pass


def _personality_allocate_menu(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    """Player invests personality_points into trait axes (gain methods stay hidden)."""
    ensure_personality(player, reg)
    axes = personality_allocate_menu_axes(reg)
    while True:
        io.write_line()
        for line in format_personality_panel(player, reg):
            io.write_line(line)
        pts = int(player.get("personality_points") or 0)
        if pts <= 0:
            io.write_line(" (ไม่มีแต้มนิสัย — ต้องค้นหาเอง หรือห้องสมุดอาจใบ้เศษๆ)")
            io.write_line(" 1. อ่านแผงอีกครั้ง  0. กลับ")
            ch = io.read_line("เลือก: ").strip()
            if ch in ("0", ""):
                return
            continue
        io.write_line("ลงทุนแต้มนิสัยไปทางใด? (ดันไปขั้ว「สูง」ของแกน)")
        for i, (aid, lab) in enumerate(axes, 1):
            inv_n = int((player.get("personality_invest") or {}).get(aid, 0))
            tag = f" · ลงทุนแล้ว×{inv_n}" if inv_n else ""
            io.write_line(f"  {i}. {lab}{tag}")
        io.write_line("  0. กลับ")
        ch = io.read_line("เลือก: ").strip()
        if ch in ("0", ""):
            return
        try:
            idx = int(ch) - 1
            axis_id, _ = axes[max(0, min(len(axes) - 1, idx))]
        except Exception:
            continue
        n = io.read_line("ใส่กี่แต้ม (default 1): ").strip()
        try:
            use = int(n) if n else 1
        except Exception:
            use = 1
        io.write_line(invest_personality_point(player, reg, axis_id, use))


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
    recipes = list_recipes(reg, player)
    if not recipes:
        io.write_line("ยังไม่มีสูตรคราฟ (เลเวลต่ำเกินไป?)")
        return
    from game.domain.rarity import rarity_label

    io.write_line("\n── คราฟ ──")
    io.write_line(" (บางสูตรต้องการวัตถุดิบระดับขั้นต่ำ — ของคุณภาพต่ำใช้ไม่ได้)")
    for i, r in enumerate(recipes, 1):
        inputs = r.get("inputs") or {}
        ir = r.get("inputs_rarity") or {}
        bits = []
        for k, v in inputs.items():
            nm = (reg.items.get(k) or {}).get("name") or k
            if k in ir:
                bits.append(f"{nm}x{v}(≥{rarity_label(reg, str(ir[k]))})")
            else:
                bits.append(f"{nm}x{v}")
        need = ", ".join(bits)
        out_r = r.get("output_rarity")
        out_bit = f" [{rarity_label(reg, str(out_r))}]" if out_r else ""
        out_nm = (reg.items.get(str(r.get("output"))) or {}).get("name") or r.get("output")
        io.write_line(
            f"  {i}. {r.get('name')} | ใช้: {need} + เงิน {r.get('money', 0)} "
            f"→ {out_nm}{out_bit} (Lv.{r.get('unlock_level', 1)})"
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
    msg = craft(player, reg, rid)
    io.write_line(msg)
    if "สำเร็จ" in msg:
        bump_stat(player, "crafts", 1)
        for line in bump_quest(player, reg, "craft"):
            io.write_line(line)





