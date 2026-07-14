"""Box / line layout for terminal (L0/L1 frames)."""
from __future__ import annotations

import unicodedata

from game.config import UI_USE_UNICODE, UI_WIDTH


def display_width(text: str) -> int:
    """Approximate terminal columns (Thai/emoji-safe-ish)."""
    w = 0
    for ch in text:
        if ch == "\t":
            w += 4
            continue
        ea = unicodedata.east_asian_width(ch)
        if ea in ("F", "W"):
            w += 2
        elif unicodedata.category(ch) in ("Mn", "Me", "Cf"):
            continue
        else:
            # Thai letters often render ~1 col in modern terminals
            w += 1
    return w


def pad_to_width(text: str, width: int) -> str:
    """Truncate/pad by display width, not len()."""
    if display_width(text) <= width:
        return text + " " * max(0, width - display_width(text))
    # truncate
    out = []
    w = 0
    for ch in text:
        cw = display_width(ch)
        if w + cw > width - 1:
            break
        out.append(ch)
        w += cw
    s = "".join(out)
    return s + " " * max(0, width - display_width(s))


def _chars(unicode: bool = UI_USE_UNICODE) -> dict:
    if unicode:
        return {
            "tl": "╔",
            "tr": "╗",
            "bl": "╚",
            "br": "╝",
            "h": "═",
            "v": "║",
            "ml": "╠",
            "mr": "╣",
            "s_tl": "┌",
            "s_tr": "┐",
            "s_bl": "└",
            "s_br": "┘",
            "s_h": "─",
            "s_v": "│",
            "s_ml": "├",
            "s_mr": "┤",
        }
    return {
        "tl": "+",
        "tr": "+",
        "bl": "+",
        "br": "+",
        "h": "=",
        "v": "|",
        "ml": "+",
        "mr": "+",
        "s_tl": "+",
        "s_tr": "+",
        "s_bl": "+",
        "s_br": "+",
        "s_h": "-",
        "s_v": "|",
        "s_ml": "+",
        "s_mr": "+",
    }


def hline(width: int = UI_WIDTH, char: str = "═") -> str:
    return char * width


def box_lines(lines: list[str], width: int = UI_WIDTH, double: bool = True) -> list[str]:
    c = _chars()
    if double:
        tl, tr, bl, br, h, v = c["tl"], c["tr"], c["bl"], c["br"], c["h"], c["v"]
        ml, mr = c["ml"], c["mr"]
    else:
        tl, tr, bl, br, h, v = c["s_tl"], c["s_tr"], c["s_bl"], c["s_br"], c["s_h"], c["s_v"]
        ml, mr = c["s_ml"], c["s_mr"]

    inner = width - 2
    out = [f"{tl}{h * inner}{tr}"]
    for line in lines:
        if line == "---":
            out.append(f"{ml}{h * inner}{mr}")
            continue
        text = pad_to_width(str(line), inner)
        out.append(f"{v}{text}{v}")
    out.append(f"{bl}{h * inner}{br}")
    return out


def render_box(lines: list[str], width: int = UI_WIDTH, double: bool = True) -> str:
    return "\n".join(box_lines(lines, width=width, double=double))
