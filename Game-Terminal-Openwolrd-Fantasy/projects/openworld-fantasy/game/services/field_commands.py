"""Dispatch verb+target commands on the field (and bag-related)."""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Sequence

from game.data_load.registry import DataRegistry
from game.domain.commands import (
    ParsedCommand,
    command_help_lines,
    parse_command,
    resolve_sight_handle,
)
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
    format_upgrade_preview,
    upgrade_equipped_opaque,
)
from game.domain.item_codes import find_equipped_by_code, item_code
from game.domain.item_instances import (
    ensure_item_instances,
    find_instances,
    format_instance_ref,
    get_equipped_instance,
)
from game.domain.party import apply_party_passives_to_player
from game.ports.io import IO


def _confirm_yn(io: IO, prompt: str) -> bool:
    ans = io.read_line(f"{prompt} (y=ตกลง / n=ยกเลิก): ").strip().lower()
    return ans in ("y", "yes", "ใช่", "1")


def try_field_command(
    raw: str,
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    sights: Sequence[Dict[str, Any]],
    *,
    handle_sight: Callable[[Dict[str, Any]], None],
    open_bag: Optional[Callable[[], None]] = None,
) -> bool:
    """
    If input is a verb command, execute and return True (caller should continue field loop).
    Return False to fall through to classic menu keys.
    """
    parsed = parse_command(raw)
    if not parsed:
        # help
        if (raw or "").strip().lower() in ("?", "help", "คำสั่ง"):
            for line in command_help_lines():
                io.write_line(line)
            return True
        return False

    verb = parsed.verb
    target = parsed.target

    if verb in ("fight", "open", "talk"):
        if not sights:
            io.write_line("ไม่มีเป้าหมายในสายตา")
            return True
        if not target:
            io.write_line("ต้องระบุรหัสเป้า เช่น f_mn01 / o_ch01")
            for s in sights:
                io.write_line(
                    f"  {s.get('handle')}: [{s.get('kind')}] {s.get('label')}"
                )
            return True
        # map talk→npc preferred, open→chest, fight→monster soft filter
        sight = resolve_sight_handle(sights, target)
        if not sight:
            io.write_line(f"ไม่พบเป้า «{target}» ในสายตา")
            for s in sights:
                io.write_line(
                    f"  {s.get('handle')}: [{s.get('kind')}] {s.get('label')} — {s.get('hint')}"
                )
            return True
        kind = str(sight.get("kind") or "")
        if verb == "fight" and kind not in ("monster", "echo", "player", "dungeon"):
            io.write_line(f"{sight.get('handle')} ไม่ใช่มอน ({kind}) — ใช้ o_ / talk_ ตามชนิด")
            return True
        if verb == "open" and kind != "chest":
            io.write_line(f"{sight.get('handle')} ไม่ใช่หีบ — ใช้ f_ / talk_")
            return True
        if verb == "talk" and kind not in ("npc", "player", "echo"):
            io.write_line(f"{sight.get('handle')} พูดด้วยแบบ NPC ไม่ได้ ({kind})")
            return True
        io.write_line(f"→ {verb} {sight.get('handle')} [{kind}] {sight.get('label')}")
        handle_sight(sight)
        return True

    if verb == "inspect":
        return _cmd_inspect(player, reg, io, target)

    if verb == "upgrade":
        return _cmd_upgrade(player, reg, io, rng, target)

    if verb == "unequip":
        return _cmd_unequip(player, reg, io, target)

    if verb == "sell":
        return _cmd_sell(player, reg, io, target)

    if verb == "drop":
        return _cmd_drop(player, reg, io, target)

    if verb == "equip":
        return _cmd_equip(player, reg, io, target)

    if verb == "use":
        return _cmd_use(player, reg, io, target)

    if verb == "socket":
        return _cmd_socket(player, reg, io, target)

    io.write_line(f"คำสั่ง «{verb}» ยังไม่รองรับบนสนาม")
    return True


def _resolve_equip_slot_from_target(
    player: Dict[str, Any],
    reg: DataRegistry,
    target: str,
) -> Optional[str]:
    ensure_item_instances(player, reg)
    if not target:
        # default weapon if any
        if (player.get("equip_ids") or {}).get("weapon"):
            return "weapon"
        return None
    # by slot name
    if target in ("weapon", "armor", "accessory", "อาวุธ", "เกราะ"):
        m = {"อาวุธ": "weapon", "เกราะ": "armor"}.get(target, target)
        return m if (player.get("equip_ids") or {}).get(m) else None
    hits = find_instances(player, reg, target, location="equip")
    if len(hits) == 1 and hits[0].get("_slot"):
        return str(hits[0]["_slot"])
    t = target.lower()
    for slot in ("weapon", "armor", "accessory"):
        inst = get_equipped_instance(player, slot)
        if not inst:
            eid = (player.get("equip_ids") or {}).get(slot)
            if eid and (
                item_code(str(eid), reg).lower() == t or str(eid).lower() == t
            ):
                return slot
            continue
        ref = format_instance_ref(inst).lower()
        code = str(inst.get("code") or "").lower()
        tid = str(inst.get("template_id") or "").lower()
        if t in (ref, code, tid):
            return slot
        if ref.startswith(t) or t.startswith(code):
            return slot
        if t.split("#")[0] == ref.split("#")[0]:
            return slot
    e2 = find_equipped_by_code(player, reg, target)
    if e2:
        return str(e2.get("slot"))
    # template code only (sw001) when unique equipped match
    e3 = find_equipped_by_code(player, reg, t.split("_")[0] if "_" in t else t)
    if e3:
        return str(e3.get("slot"))
    return None


def _cmd_inspect(player: Dict[str, Any], reg: DataRegistry, io: IO, target: str) -> bool:
    ensure_item_instances(player, reg)
    if not target:
        io.write_line("ระบุเป้า เช่น i_sw001 หรือ i_sw001_a3f2#…")
        return True
    # equipped first
    slot = _resolve_equip_slot_from_target(player, reg, target)
    if slot:
        inst = get_equipped_instance(player, slot)
        rid = (inst or {}).get("rarity") or (player.get("equip_rarities") or {}).get(slot) or "common"
        tid = (inst or {}).get("template_id") or (player.get("equip_ids") or {}).get(slot)
        if inst:
            io.write_line(f" รหัสชิ้น: {format_instance_ref(inst)}  (มีเจ้าของ · สวม {slot})")
        for line in examine_item(str(tid), reg, rarity=str(rid)):
            io.write_line(line)
        return True
    hits = find_instances(player, reg, target, location="bag")
    if hits:
        if len(hits) > 1:
            io.write_line(f"พบ {len(hits)} ชิ้น — ระบุรหัสเต็ม (เช่น sw001_a3f2#b91c01):")
            for i, h in enumerate(hits, 1):
                io.write_line(
                    f"  {i}. {format_instance_ref(h)} · "
                    f"{(reg.items.get(str(h.get('template_id'))) or {}).get('name') or h.get('template_id')}"
                )
            return True
        h = hits[0]
        io.write_line(f" รหัสชิ้น: {format_instance_ref(h)}  (ในกระเป๋า · เจ้าของ {h.get('owner_short')})")
        for line in examine_item(str(h.get("template_id")), reg, rarity=str(h.get("rarity"))):
            io.write_line(line)
        return True
    # template only
    from game.domain.item_codes import resolve_code

    tid = resolve_code(target, reg) or target
    if tid in (reg.items or {}) or tid in (reg.cards or {}):
        io.write_line(f" «{target}» = ชนิดของ (template) — ยังไม่ชี้ชิ้นที่มีเจ้าของ")
        for line in examine_item(str(tid), reg):
            io.write_line(line)
        return True
    io.write_line(f"ไม่พบ «{target}»")
    return True


def _cmd_upgrade(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: random.Random,
    target: str,
) -> bool:
    ensure_gear_fields(player)
    ensure_item_instances(player, reg)
    slot = _resolve_equip_slot_from_target(player, reg, target or "weapon")
    if not slot:
        io.write_line("อัปเกรด: ต้องชี้ชิ้นที่สวม เช่น upgrade_sw001 หรือ upgrade_weapon")
        # list owned equipped
        for s in ("weapon", "armor", "accessory"):
            inst = get_equipped_instance(player, s)
            if inst:
                io.write_line(f"  · {format_instance_ref(inst)} ({s})")
        return True
    if not can_upgrade_equipped(player, slot):
        io.write_line("ชิ้นนี้อัปเกรดไม่ได้ (ถึงขีดหรือว่าง)")
        return True
    for line in format_upgrade_preview(player, slot, reg):
        io.write_line(line)
    if not _confirm_yn(io, "ยืนยันเริ่มพิธีอัปเกรด?"):
        io.write_line("ยกเลิกอัปเกรด")
        return True
    msg = upgrade_equipped_opaque(player, slot, reg, rng)
    io.write_line(msg)
    apply_party_passives_to_player(player, reg)
    recompute_stats(player, reg)
    ensure_item_instances(player, reg)
    return True


def _cmd_unequip(player: Dict[str, Any], reg: DataRegistry, io: IO, target: str) -> bool:
    slot = _resolve_equip_slot_from_target(player, reg, target or "weapon")
    if not slot:
        io.write_line("ถอด: ระบุชิ้นที่สวม เช่น unequip_sw001")
        return True
    if not _confirm_yn(io, f"ถอด {slot}?"):
        io.write_line("ยกเลิกถอด")
        return True
    io.write_line(unequip_slot(player, slot, reg))
    apply_party_passives_to_player(player, reg)
    recompute_stats(player, reg)
    ensure_item_instances(player, reg)
    return True


def _cmd_sell(player: Dict[str, Any], reg: DataRegistry, io: IO, target: str) -> bool:
    slot = _resolve_equip_slot_from_target(player, reg, target)
    if not slot:
        io.write_line("ขายจากคำสั่งสนามรองรับของที่สวม — sell_sw001")
        return True
    if not _confirm_yn(io, "ขายชิ้นที่สวม?"):
        io.write_line("ยกเลิกขาย")
        return True
    io.write_line(sell_equipped_slot(player, slot, reg))
    apply_party_passives_to_player(player, reg)
    recompute_stats(player, reg)
    ensure_item_instances(player, reg)
    return True


def _cmd_drop(player: Dict[str, Any], reg: DataRegistry, io: IO, target: str) -> bool:
    slot = _resolve_equip_slot_from_target(player, reg, target)
    if not slot:
        io.write_line("ทิ้งจากคำสั่งสนามรองรับของที่สวม — drop_sw001")
        return True
    if not _confirm_yn(io, "ทิ้งถาวร? กู้คืนไม่ได้"):
        io.write_line("ยกเลิกทิ้ง")
        return True
    io.write_line(discard_equipped_slot(player, slot, reg))
    apply_party_passives_to_player(player, reg)
    recompute_stats(player, reg)
    ensure_item_instances(player, reg)
    return True


def _cmd_equip(player: Dict[str, Any], reg: DataRegistry, io: IO, target: str) -> bool:
    """equip_sw001 / equip_iron_sword — from bag inventory."""
    from game.domain.item_codes import resolve_code
    from game.domain.quests import bump_quest

    ensure_item_instances(player, reg)
    if not target:
        io.write_line("สวม: equip_sw001 หรือ equip_iron_sword")
        return True
    hits = find_instances(player, reg, target, location="bag")
    tid = None
    if hits:
        if len(hits) > 1:
            io.write_line(f"พบ {len(hits)} ชิ้นในคลัง — ระบุรหัสเต็มก่อนสวม:")
            for i, h in enumerate(hits, 1):
                io.write_line(f"  {i}. {format_instance_ref(h)}")
            return True
        tid = str(hits[0].get("template_id"))
    else:
        tid = resolve_code(target, reg) or target
        if tid not in (player.get("inventory_ids") or []):
            io.write_line(f"ไม่มี «{target}» ในคลังสำหรับสวม")
            return True
    name = (reg.items.get(tid) or {}).get("name") or tid
    if not _confirm_yn(io, f"สวม {name}?"):
        io.write_line("ยกเลิกสวม")
        return True
    msg = equip_item(player, tid, reg)
    io.write_line(msg)
    apply_party_passives_to_player(player, reg)
    recompute_stats(player, reg)
    for line in bump_quest(player, reg, "equip_weapon"):
        io.write_line(line)
    ensure_item_instances(player, reg)
    return True


def _cmd_use(player: Dict[str, Any], reg: DataRegistry, io: IO, target: str) -> bool:
    """use_potion_hp / use first matching consumable in bag."""
    from game.domain.item_codes import resolve_code
    from game.services.bag_hub import _use_inventory_index

    if not target:
        io.write_line("ใช้ของ: use_potion_hp หรือ use + รหัสยา")
        return True
    tid = resolve_code(target, reg) or target
    ids = list(player.get("inventory_ids") or [])
    idx = -1
    for i, iid in enumerate(ids):
        if str(iid) == str(tid) or str(iid).lower() == target.lower():
            idx = i
            break
    if idx < 0:
        # try by name fragment
        for i, iid in enumerate(ids):
            nm = str((reg.items.get(iid) or {}).get("name") or "")
            if target in nm or target in str(iid):
                idx = i
                tid = iid
                break
    if idx < 0:
        io.write_line(f"ไม่พบ «{target}» ในคลัง")
        return True
    name = (reg.items.get(str(tid)) or {}).get("name") or tid
    if not _confirm_yn(io, f"ใช้ {name}?"):
        io.write_line("ยกเลิกใช้")
        return True
    _use_inventory_index(player, reg, idx, io)
    recompute_stats(player, reg)
    ensure_item_instances(player, reg)
    return True


def _cmd_socket(player: Dict[str, Any], reg: DataRegistry, io: IO, target: str) -> bool:
    """
    socket_card_fire>weapon or socket_card_fire>1
    or socket_card_fire (defaults weapon slot 1)
    """
    from game.domain.item_codes import resolve_code
    from game.domain.quests import bump_quest

    ensure_gear_fields(player)
    ensure_item_instances(player, reg)
    if not target:
        io.write_line("ใส่การ์ด: socket_card_fire>weapon หรือ socket_card_fire>1")
        return True
    card_part = target
    slot_part = "weapon"
    si = 0
    if ">" in target:
        card_part, slot_part = target.split(">", 1)
        slot_part = slot_part.strip()
    card_part = card_part.strip()
    cid = resolve_code(card_part, reg) or card_part
    bag = list(player.get("card_bag") or [])
    if cid not in bag:
        if not str(cid).startswith("card_") and f"card_{cid}" in bag:
            cid = f"card_{cid}"
        elif card_part not in bag:
            found = None
            for c in bag:
                nm = str((reg.cards.get(c) or {}).get("name") or c)
                if card_part in nm.lower() or card_part in str(c).lower():
                    found = c
                    break
            if not found:
                io.write_line(f"ไม่มีการ์ด «{card_part}» ในถุง")
                return True
            cid = found
    if slot_part in ("1", "weapon", "อาวุธ", "w"):
        slot = "weapon"
        si = 0
    elif slot_part in ("2", "armor", "เกราะ", "a"):
        slot = "armor"
        si = 0
    elif slot_part.isdigit():
        slot = "weapon"
        si = max(0, int(slot_part) - 1)
    else:
        slot = "weapon"
        si = 0
    if not (player.get("equip_ids") or {}).get(slot):
        io.write_line(f"ยังไม่สวม{slot} — สวมเกียร์ก่อน")
        return True
    socks = list((player.get("sockets") or {}).get(slot) or [])
    if not socks:
        io.write_line("ช่องนี้ยังไม่มีซ็อกเก็ต")
        return True
    if si >= len(socks):
        si = 0
    cname = (reg.cards.get(cid) or {}).get("name") or cid
    slot_th = "อาวุธ" if slot == "weapon" else "เกราะ"
    io.write_line(f" จะใส่: {cname} → {slot_th} ช่อง {si + 1}")
    if not _confirm_yn(io, "ยืนยันใส่การ์ด?"):
        io.write_line("ยกเลิกใส่การ์ด")
        return True
    msg = socket_card(player, slot, si, cid, reg)
    io.write_line(msg)
    for line in bump_quest(player, reg, "socket_card"):
        io.write_line(line)
    recompute_stats(player, reg)
    ensure_item_instances(player, reg)
    return True
