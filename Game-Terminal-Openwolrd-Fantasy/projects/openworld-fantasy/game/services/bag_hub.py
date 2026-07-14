"""Categorized bag hub — equipment / healing / materials / cards (docs/BAG_SYSTEM.md)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from game.data_load.registry import DataRegistry
from game.domain.equipment import (
    discard_equipped_slot,
    equip_item,
    ensure_gear_fields,
    recompute_stats,
    sell_equipped_slot,
    socket_card,
    unequip_slot,
)
from game.domain.inventory_sys import (
    can_upgrade_equipped,
    examine_item,
    format_bag_hub,
    format_bag_panel,
    format_category_list,
    format_equip_panel,
    format_upgrade_preview,
    list_bag_entries,
    sanitize_inventory,
    soft_upgrade_hint,
    upgrade_equipped_opaque,
)
from game.domain.item_codes import (
    find_equipped_by_code,
    item_code,
    resolve_code,
)
from game.domain.party import apply_party_passives_to_player
from game.domain.quests import bump_quest
from game.domain.status_fx import (
    apply_status,
    cleanse,
    clear_statuses,
    status_display_name,
)
from game.ports.io import IO
from game.services.shop import run_shop


def confirm_yn(io: IO, prompt: str) -> bool:
    """
    Safety confirm — y/ใช่/1 = yes, anything else (incl. n) = cancel.
    Prevents accidental equip / socket / sell / upgrade.
    """
    ans = io.read_line(f"{prompt} (y=ตกลง / n=ยกเลิก): ").strip().lower()
    return ans in ("y", "yes", "ใช่", "1")


def _resolve_equipment_pick(
    entries: List[Dict[str, Any]],
    ch: str,
    reg: DataRegistry,
) -> Optional[Dict[str, Any]]:
    """
    Resolve equipment selection: 1-based index, short code (sw001), or item id.
    """
    raw = (ch or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        pick = int(raw) - 1
        if 0 <= pick < len(entries):
            return entries[pick]
        return None
    key = raw.lower()
    # short code / full id via registry
    resolved = resolve_code(key, reg)
    if resolved:
        for e in entries:
            if str(e.get("id")) == resolved:
                return e
    for e in entries:
        code = item_code(str(e.get("id") or ""), reg).lower()
        if code == key or str(e.get("id") or "").lower() == key:
            return e
    hits = [e for e in entries if key in str(e.get("id") or "").lower()]
    if len(hits) == 1:
        return hits[0]
    hits = [e for e in entries if key in item_code(str(e.get("id") or ""), reg).lower()]
    if len(hits) == 1:
        return hits[0]
    hits = [e for e in entries if key in str(e.get("name") or "").lower()]
    if len(hits) == 1:
        return hits[0]
    return None


def _manage_equipped(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    entry: Dict[str, Any],
) -> None:
    """
    Inspect equipped piece by code (e.g. sw001).
    Menu keys stable: 1 ถอด · 2 กลับ · 3 อัป(ถ้าได้) · 4 ขาย · 5 ทิ้ง
    """
    slot = str(entry["slot"])
    iid = str(entry["id"])
    rid = str(entry.get("rarity") or "common")
    for line in examine_item(iid, reg, rarity=rid):
        io.write_line(line)
    up = int(entry.get("upgrade") or 0)
    can_up = can_upgrade_equipped(player, slot)
    io.write_line(f" สถานะ: สวมอยู่ ({entry.get('label')}) · อัป +{up}")
    if can_up:
        io.write_line(f" {soft_upgrade_hint(slot, up)}")
    else:
        io.write_line(" อัปเกรด: ถึงขีดแล้ว / อัปต่อไม่ได้ — ไม่มีเมนูอัป")
    io.write_line("---")
    io.write_line(" 1. ถอดออก")
    io.write_line(" 2. ย้อนกลับ")
    if can_up:
        io.write_line(" 3. อัพเกรด")
    io.write_line(" 4. ขาย")
    io.write_line(" 5. ทิ้ง")
    sub = io.read_line("เลือก: ").strip()
    if sub in ("2", "0", ""):
        return
    if sub == "1":
        if not confirm_yn(io, "ถอดชิ้นนี้ออกจากตัว?"):
            io.write_line("ยกเลิกถอด")
            return
        msg = unequip_slot(player, slot, reg)
        io.write_line(msg)
        apply_party_passives_to_player(player, reg)
        recompute_stats(player, reg)
        return
    if sub == "3":
        if not can_up:
            io.write_line("ชิ้นนี้อัปเกรดไม่ได้ (ไม่มีเมนูอัป)")
            return
        # full cost sheet — teach materials
        for line in format_upgrade_preview(player, slot, reg):
            io.write_line(line)
        if not confirm_yn(io, "ยืนยันเริ่มพิธีอัปเกรด?"):
            io.write_line("ยกเลิกอัปเกรด")
            return
        msg = upgrade_equipped_opaque(player, slot, reg, random.Random())
        io.write_line(msg)
        apply_party_passives_to_player(player, reg)
        recompute_stats(player, reg)
        for line in bump_quest(player, reg, "upgrade_gear"):
            io.write_line(line)
        return
    if sub == "4":
        if not confirm_yn(io, "ขายชิ้นนี้?"):
            io.write_line("ยกเลิกขาย")
            return
        msg = sell_equipped_slot(player, slot, reg)
        io.write_line(msg)
        apply_party_passives_to_player(player, reg)
        recompute_stats(player, reg)
        return
    if sub == "5":
        if not confirm_yn(io, "ทิ้งถาวร? กู้คืนไม่ได้"):
            io.write_line("ยกเลิกทิ้ง")
            return
        msg = discard_equipped_slot(player, slot, reg)
        io.write_line(msg)
        apply_party_passives_to_player(player, reg)
        recompute_stats(player, reg)
        return
    io.write_line("เลือกจากเมนูที่แสดง")


def _use_inventory_index(
    player: Dict[str, Any],
    reg: DataRegistry,
    index: int,
    io: IO,
) -> bool:
    """Consume / use one inventory slot by absolute index."""
    ids = list(player.get("inventory_ids") or [])
    inv = list(player.get("inventory") or [])
    rar = list(player.get("inventory_rarities") or [])
    if index < 0 or index >= len(ids):
        io.write_line("ไม่มีชิ้นนั้น")
        return False
    item_id = str(ids.pop(index))
    item_name = inv.pop(index) if index < len(inv) else item_id
    if index < len(rar):
        rar.pop(index)
    while len(inv) > len(ids):
        inv.pop()
    while len(rar) > len(ids):
        rar.pop()
    player["inventory_ids"] = ids
    player["inventory"] = inv
    player["inventory_rarities"] = rar

    it = reg.items.get(item_id) or {}
    io.write_line(f"ใช้: {it.get('name') or item_name}")

    if it.get("clear_all_debuffs") or str(it.get("clear_status") or "").lower() in (
        "all",
        "*",
        "debuff",
    ):
        cleared = cleanse(player, reg, mode="all_debuffs", item_id=item_id)
        if cleared:
            io.write_line(
                "ล้าง: " + ", ".join(status_display_name(reg, c) for c in cleared)
            )
        else:
            io.write_line("(ไม่มี debuff ที่ล้างได้)")
        return True
    if it.get("clear_status") and not it.get("heal_hp") and not it.get("apply_status"):
        cleared = clear_statuses(
            player,
            reg,
            item_id=item_id,
            clear_spec=it.get("clear_status"),
            tags=["poison", "ailment"],
        )
        if cleared:
            io.write_line(
                "ล้าง: " + ", ".join(status_display_name(reg, c) for c in cleared)
            )
        else:
            io.write_line("(ไม่มีสถานะที่ล้างได้)")
        return True
    if it.get("apply_status"):
        applied = apply_status(
            player,
            str(it["apply_status"]),
            reg,
            random.Random(),
            ignore_resist=True,
            source=item_id,
        )
        if applied:
            io.write_line(f"ได้บัฟ/สถานะ: {status_display_name(reg, applied)}")
    if it.get("heal_hp"):
        h = int(it["heal_hp"])
        old = int(player.get("hp") or 0)
        player["hp"] = min(int(player["max_hp"]), old + h)
        io.write_line(f"ฟื้น HP +{h} → {player['hp']}/{player['max_hp']}")
    if it.get("heal_mana"):
        m = int(it["heal_mana"])
        player["mana"] = min(int(player["max_mana"]), int(player.get("mana") or 0) + m)
        io.write_line(f"ฟื้น MP +{m} → {player['mana']}/{player['max_mana']}")
    # intelligence restore / boost items
    if any(it.get(k) for k in ("restore_intel", "boost_intel_max", "fill_intel")):
        try:
            from game.domain.intelligence import apply_intel_item

            for note in apply_intel_item(player, it):
                io.write_line(note)
        except Exception:
            io.write_line("…จิตเปลี่ยนไปบ้าง")
    if not any(
        it.get(k)
        for k in (
            "heal_hp",
            "heal_mana",
            "apply_status",
            "clear_status",
            "clear_all_debuffs",
            "restore_intel",
            "boost_intel_max",
            "fill_intel",
        )
    ):
        io.write_line("ใช้แล้ว (ไม่มีผลรักษาชัดเจน)")
    return True


def _category_loop(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    category: str,
) -> None:
    while True:
        io.write_line()
        for line in format_category_list(player, reg, category):
            io.write_line(line)
        entries = list_bag_entries(player, reg, category)
        if category == "healing":
            ch = io.read_line("ใช้หมายเลข (0=กลับ): ").strip()
        elif category == "equipment":
            ch = io.read_line("เลือกชิ้น (หมายเลขหรือ sw001 · 0=กลับ): ").strip()
        elif category == "material":
            ch = io.read_line("ดูหมายเลข (0=กลับ): ").strip()
        elif category == "card":
            ch = io.read_line("เลือกการ์ด (0=กลับ): ").strip()
        else:
            ch = io.read_line("เลือก (0=กลับ): ").strip()
        if ch in ("0", ""):
            return

        entry = None
        if category == "equipment":
            entry = _resolve_equipment_pick(entries, ch, reg)
            if entry is None:
                io.write_line("ไม่พบชิ้นนั้น — ใส่หมายเลข หรือไอดีเช่น sw001")
                continue
        else:
            try:
                pick = int(ch) - 1
            except Exception:
                io.write_line("ใส่หมายเลข")
                continue
            if pick < 0 or pick >= len(entries):
                io.write_line("นอกช่วง")
                continue
            entry = entries[pick]

        iid = str(entry["id"])
        idx = int(entry["index"])

        if category == "healing":
            _use_inventory_index(player, reg, idx, io)
            recompute_stats(player, reg)
            continue

        if category == "equipment":
            for line in examine_item(iid, reg, rarity=entry.get("rarity")):
                io.write_line(line)
            io.write_line(" 1.สวม  0.กลับ")
            sub = io.read_line("เลือก: ").strip()
            if sub == "1":
                name = (reg.items.get(iid) or {}).get("name") or iid
                if not confirm_yn(io, f"สวม {name}?"):
                    io.write_line("ยกเลิกสวม")
                    continue
                msg = equip_item(player, iid, reg)
                io.write_line(msg)
                apply_party_passives_to_player(player, reg)
                recompute_stats(player, reg)
                for line in bump_quest(player, reg, "equip_weapon"):
                    io.write_line(line)
            continue

        if category == "material":
            for line in examine_item(iid, reg, rarity=entry.get("rarity")):
                io.write_line(line)
            io.write_line("(วัตถุดิบใช้ตอนคราฟ/อัปเกียร์ — ใช้ตรงๆ ไม่ได้)")
            io.read_line("Enter...")
            continue

        if category == "card":
            for line in examine_item(iid, reg):
                io.write_line(line)
            card_name = str((reg.cards.get(iid) or reg.items.get(iid) or {}).get("name") or iid)
            io.write_line("ใส่ช่อง: 1=อาวุธ  2=เกราะ  0=ไม่ใส่")
            slot_ch = io.read_line("ช่อง: ").strip()
            if slot_ch in ("0", ""):
                io.write_line("ยกเลิกใส่การ์ด")
                continue
            slot = {"1": "weapon", "2": "armor"}.get(slot_ch)
            if not slot:
                io.write_line("ช่องไม่ถูกต้อง — ยกเลิก")
                continue
            socks = list((player.get("sockets") or {}).get(slot) or [])
            if not socks:
                ensure_gear_fields(player)
                recompute_stats(player, reg)
                socks = list((player.get("sockets") or {}).get(slot) or [])
            if not socks:
                io.write_line("ช่องนี้ยังไม่มีซ็อกเก็ต (สวมเกียร์ที่มีช่องก่อน)")
                continue
            slot_th = "อาวุธ" if slot == "weapon" else "เกราะ"
            io.write_line(f"ช่อง 1..{len(socks)} บน{slot_th}")
            try:
                si = int(io.read_line("หมายเลขช่อง: ").strip()) - 1
            except Exception:
                io.write_line("ยกเลิก — ใส่หมายเลขช่องไม่ถูกต้อง")
                continue
            if si < 0 or si >= len(socks):
                io.write_line("ช่องนอกช่วง — ยกเลิก")
                continue
            # summary + y/n before commit
            io.write_line(f" จะใส่: {card_name} → {slot_th} ช่อง {si + 1}")
            if socks[si]:
                prev = (reg.cards.get(socks[si]) or {}).get("name") or socks[si]
                io.write_line(f" (ช่องนี้มี {prev} อยู่ — จะถูกถอดกลับถุง)")
            if not confirm_yn(io, "ยืนยันใส่การ์ด?"):
                io.write_line("ยกเลิกใส่การ์ด")
                continue
            msg = socket_card(player, slot, max(0, si), iid, reg)
            io.write_line(msg)
            for line in bump_quest(player, reg, "socket_card"):
                io.write_line(line)
            recompute_stats(player, reg)
            continue

        for line in examine_item(iid, reg, rarity=entry.get("rarity")):
            io.write_line(line)
        io.write_line(" 1.ลองใช้  0.กลับ")
        if io.read_line("เลือก: ").strip() == "1":
            _use_inventory_index(player, reg, idx, io)


def run_bag_hub(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    *,
    open_shop=None,
    open_craft=None,
    open_gear=None,
) -> None:
    """
    Main bag hub (field menu 5).
    open_shop / open_craft / open_gear: optional callables(player, reg, io)

    At hub prompt you may type:
      0–9 menu, or equipped short code (sw001) to manage worn gear.
    """
    sanitize_inventory(player, reg)
    ensure_gear_fields(player)
    try:
        from game.domain.item_instances import ensure_item_instances

        ensure_item_instances(player, reg)
    except Exception:
        pass
    while True:
        apply_party_passives_to_player(player, reg)
        recompute_stats(player, reg)
        io.write_line()
        for line in format_bag_hub(player, reg):
            io.write_line(line)
        ch = io.read_line("เลือกประเภท/ไอดี/คำสั่ง (equip_ sw001 · use_ · ?): ").strip()
        if ch in ("0", ""):
            break
        # verb commands inside bag hub
        if ch in ("?", "help", "คำสั่ง"):
            from game.domain.commands import command_help_lines

            for line in command_help_lines():
                io.write_line(line)
            continue
        # equipped ref first (sw001 / sw001_xxxx#…) before inspect-parse
        eq_hit = find_equipped_by_code(player, reg, ch)
        if eq_hit:
            _manage_equipped(player, reg, io, eq_hit)
            continue
        # only explicit verbs (equip_/use_/socket_/…) — not bare sw001
        try:
            from game.domain.commands import parse_command
            from game.services.field_commands import try_field_command
            import random as _rnd

            parsed = parse_command(ch)
            if parsed and parsed.verb not in ("inspect",) and (
                "_" in ch or parsed.verb in ("equip", "use", "socket", "upgrade", "unequip", "sell", "drop")
            ):
                try_field_command(
                    ch,
                    player,
                    reg,
                    io,
                    _rnd.Random(),
                    [],
                    handle_sight=lambda s: None,
                )
                continue
        except Exception as exc:
            io.write_line(f"(คำสั่ง) {exc}")
        if ch == "1":
            _category_loop(player, reg, io, "equipment")
        elif ch == "2":
            _category_loop(player, reg, io, "healing")
        elif ch == "3":
            _category_loop(player, reg, io, "material")
        elif ch == "4":
            _category_loop(player, reg, io, "card")
        elif ch == "5":
            _category_loop(player, reg, io, "other")
        elif ch == "6":
            if open_gear:
                open_gear(player, reg, io)
            else:
                for line in format_equip_panel(player, reg):
                    io.write_line(line)
                # also allow picking by code from equip panel view
                sub = io.read_line("พิมพ์ไอดีที่สวม (เช่น sw001) หรือ Enter กลับ: ").strip()
                if sub:
                    eq2 = find_equipped_by_code(player, reg, sub)
                    if eq2:
                        _manage_equipped(player, reg, io, eq2)
                    else:
                        io.write_line("ไม่พบไอดีนั้นบนตัว")
        elif ch == "7":
            io.write_line(" ร้านหลักอยู่ที่สำรวจ → 6 (โหมดร้าน)")
            ans = io.read_line("ทางลัดร้านท้องถิ่น? (y=เปิด / n=กลับ): ").strip().lower()
            if ans in ("y", "yes", "ใช่", "1"):
                if open_shop:
                    open_shop(player, reg, io)
                else:
                    run_shop(player, reg, io)
        elif ch == "8":
            if open_craft:
                open_craft(player, reg, io)
            else:
                io.write_line("คราฟ: สำรวจ → 6 → 5 หรือเมนูเกียร์")
        elif ch == "9":
            for line in format_bag_panel(player, reg):
                io.write_line(line)
            io.read_line("Enter...")
        elif ch in ("m", "M"):
            from game.services.shop_hub import run_shop_hub

            run_shop_hub(player, reg, io)
        elif ch in ("j", "J"):
            from game.services.mission_service import run_mission_board

            run_mission_board(player, reg, io)
        else:
            # try resolve as bag equipment code not equipped
            resolved = resolve_code(ch, reg)
            if resolved and resolved in (player.get("inventory_ids") or []):
                for line in examine_item(
                    resolved,
                    reg,
                    rarity=None,
                ):
                    io.write_line(line)
                io.write_line("(ชิ้นนี้อยู่ในคลัง — ไปเมนู 1.อุปกรณ์ เพื่อสวม)")
                io.read_line("Enter...")
            else:
                io.write_line("เลือก 0–9 หรือพิมพ์ไอดีที่สวม เช่น sw001")
