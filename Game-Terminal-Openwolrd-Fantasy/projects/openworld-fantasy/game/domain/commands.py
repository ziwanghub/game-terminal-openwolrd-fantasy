"""
Command grammar: verb + target (docs/COMMAND_AND_INSTANCE_IDS.md).

Examples:
  f_mn02 / fmn02     fight sight handle
  o_ch01             open chest
  talk_np01          talk NPC
  i_sw001            inspect template or instance ref
  upgrade_sw001_…    upgrade equipped instance
  unequip_… sell_… drop_…
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Longest prefixes first within each verb
_VERB_TABLE: List[Tuple[str, str]] = [
    ("upgrade_", "upgrade"),
    ("unequip_", "unequip"),
    ("discard_", "drop"),
    ("inspect_", "inspect"),
    ("equip_", "equip"),
    ("fight_", "fight"),
    ("open_", "open"),
    ("talk_", "talk"),
    ("socket_", "socket"),
    ("sell_", "sell"),
    ("drop_", "drop"),
    ("use_", "use"),
    ("i_", "inspect"),
    ("f_", "fight"),
    ("o_", "open"),
    # bare short (only with attached target, not alone)
    ("fight", "fight"),
    ("open", "open"),
    ("talk", "talk"),
    ("upgrade", "upgrade"),
    ("unequip", "unequip"),
    ("inspect", "inspect"),
    ("equip", "equip"),
    ("socket", "socket"),
    ("sell", "sell"),
    ("drop", "drop"),
    ("use", "use"),
]

# Field menu single-token reserved (not parsed as verb alone)
_MENU_RESERVED = {
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "s",
    "p",
    "k",
    "n",
    "y",
    "b",
    "h",
    "t",  # tutorial
    "l",
}


@dataclass
class ParsedCommand:
    verb: str
    target: str
    raw: str


def parse_command(raw: str) -> Optional[ParsedCommand]:
    """
    Parse player input into verb + target.
    Returns None if this looks like a plain menu key / empty.
    """
    text = (raw or "").strip()
    if not text:
        return None
    low = text.lower()
    # pure menu token
    if low in _MENU_RESERVED and len(low) <= 2:
        return None
    # spaced: "f mn02" / "upgrade sw001"
    if " " in low:
        parts = low.split(None, 1)
        head, rest = parts[0], parts[1] if len(parts) > 1 else ""
        for pref, verb in _VERB_TABLE:
            p = pref.rstrip("_")
            if head == p or head == pref.rstrip("_"):
                if rest:
                    return ParsedCommand(verb=verb, target=rest.strip(), raw=text)
        # f_mn02 already no space
    # prefix table (longest first — table is ordered)
    for pref, verb in sorted(_VERB_TABLE, key=lambda x: -len(x[0])):
        if low.startswith(pref):
            target = low[len(pref) :].lstrip("_").strip()
            if not target and pref.rstrip("_") in ("f", "o", "i"):
                # bare f / o / i alone → not a command (ambiguous)
                return None
            if not target and pref.endswith("_"):
                return ParsedCommand(verb=verb, target="", raw=text)
            if target or pref.endswith("_"):
                return ParsedCommand(verb=verb, target=target, raw=text)
    # glued short: fmn02 o ch01 style fmn02
    m = re.match(r"^(f|o|i)([a-z]{1,3}\d{1,3})$", low)
    if m:
        verb = {"f": "fight", "o": "open", "i": "inspect"}[m.group(1)]
        return ParsedCommand(verb=verb, target=m.group(2), raw=text)
    # instance / template inspect shorthand: sw001… without verb → inspect
    if re.match(r"^(sw|ar|ac|pt|mt|cd)[a-z0-9_#]+$", low) or re.match(
        r"^[a-z]+_[a-z0-9]+(#\w+)?$", low
    ):
        if low.startswith(("sw", "ar", "ac", "pt", "mt", "cd")) or "#" in low:
            return ParsedCommand(verb="inspect", target=low, raw=text)
    return None


def resolve_sight_handle(
    sights: Sequence[Mapping[str, Any]],
    target: str,
) -> Optional[Dict[str, Any]]:
    """Find sight by handle (mn02) or 1-based index string."""
    key = (target or "").strip().lower()
    if not key:
        return None
    if key.isdigit():
        idx = int(key) - 1
        if 0 <= idx < len(sights):
            return dict(sights[idx])
        return None
    for s in sights:
        h = str(s.get("handle") or "").lower()
        if h == key or h.lstrip("0") == key.lstrip("0"):
            return dict(s)
        # mn2 matches mn02
        if h.replace("0", "") == key.replace("0", "") and h[:2] == key[:2]:
            return dict(s)
    # unique prefix
    hits = [s for s in sights if str(s.get("handle") or "").lower().startswith(key)]
    if len(hits) == 1:
        return dict(hits[0])
    return None


def command_help_lines() -> List[str]:
    return [
        "── คำสั่งรหัส (verb + เป้า) ──",
        "  f_mn02 / fmn02     สู้/เข้าหามอนในสายตา",
        "  o_ch01             เปิดหีบ",
        "  talk_np01          พูดกับ NPC",
        "  i_sw001            ดูชนิด/ชิ้น (inspect)",
        "  upgrade_sw001…     อัปเกรดชิ้นที่สวม (ถ้าชี้ได้)",
        "  unequip_sw001…     ถอด",
        "  equip_sw001        สวมจากคลัง",
        "  use_potion_hp      ใช้ยา/consumable ในคลัง",
        "  socket_card_fire>weapon  ใส่การ์ดลงช่องเกียร์",
        "  sell_… / drop_…    ขาย / ทิ้ง (ยืนยัน y/n)",
        " เมนูเลข 0–9 ยังใช้ได้ · คำสั่งรหัสกันเป้าสลับ",
    ]
