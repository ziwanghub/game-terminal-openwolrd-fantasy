"""
UX-Tama T0 — soft needs on player (hunger / fatigue / morale).

Values 0–100 internal; UI shows soft labels only (no raw % in normal play).
Event-driven ticks from rest / explore / travel / combat / eat.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

NEED_KEYS = ("hunger", "fatigue", "morale")

# Higher hunger/fatigue = worse · higher morale = better
DEFAULT_NEEDS = {
    "hunger": 18,
    "fatigue": 12,
    "morale": 72,
}

# Deltas applied per event (clamped after)
EVENT_DELTAS: Dict[str, Dict[str, int]] = {
    "rest": {"hunger": 4, "fatigue": -18, "morale": 6},
    "explore": {"hunger": 8, "fatigue": 10, "morale": -2},
    "travel": {"hunger": 10, "fatigue": 14, "morale": -3},
    "combat": {"hunger": 5, "fatigue": 8, "morale": -1},
    "combat_win": {"hunger": 3, "fatigue": 4, "morale": 10},
    "combat_loss": {"hunger": 6, "fatigue": 12, "morale": -14},
    "eat": {"hunger": -28, "fatigue": -4, "morale": 6},
    "dungeon_tick": {"hunger": 3, "fatigue": 5, "morale": -1},
}


def ensure_needs(player: MutableMapping[str, Any]) -> Dict[str, int]:
    raw = player.get("needs")
    if not isinstance(raw, dict):
        needs = dict(DEFAULT_NEEDS)
        player["needs"] = needs
        return needs
    out: Dict[str, int] = {}
    for k in NEED_KEYS:
        try:
            out[k] = int(raw.get(k, DEFAULT_NEEDS[k]))
        except (TypeError, ValueError):
            out[k] = DEFAULT_NEEDS[k]
        out[k] = max(0, min(100, out[k]))
    player["needs"] = out
    return out


def get_needs(player: Mapping[str, Any]) -> Dict[str, int]:
    raw = player.get("needs")
    if not isinstance(raw, dict):
        return dict(DEFAULT_NEEDS)
    return {
        k: max(0, min(100, int(raw.get(k, DEFAULT_NEEDS[k]))))
        for k in NEED_KEYS
    }


def _clamp_needs(needs: MutableMapping[str, int]) -> None:
    for k in NEED_KEYS:
        needs[k] = max(0, min(100, int(needs.get(k, DEFAULT_NEEDS[k]))))


def apply_needs_event(
    player: MutableMapping[str, Any],
    event: str,
    *,
    silent: bool = False,
) -> List[str]:
    """
    Apply event deltas. Returns soft note lines (empty if silent or no change felt).
    """
    ensure_needs(player)
    deltas = EVENT_DELTAS.get(str(event) or "")
    if not deltas:
        return []
    needs = dict(player["needs"])
    before = dict(needs)
    for k, d in deltas.items():
        if k in needs:
            needs[k] = int(needs[k]) + int(d)
    _clamp_needs(needs)
    player["needs"] = needs
    if silent:
        return []
    return _soft_change_notes(before, needs, event)


def _soft_change_notes(
    before: Mapping[str, int],
    after: Mapping[str, int],
    event: str,
) -> List[str]:
    notes: List[str] = []
    # only whisper when band changes or large swing
    for key, label in (
        ("hunger", "ท้อง"),
        ("fatigue", "ล้า"),
        ("morale", "ขวัญ"),
    ):
        b, a = int(before.get(key, 0)), int(after.get(key, 0))
        if _band(key, b) != _band(key, a) or abs(a - b) >= 15:
            notes.append(f" …{label}: {soft_label(key, a)}")
    if notes:
        notes.insert(0, "〔สถานะกายใจ〕")
    return notes


def _band(key: str, value: int) -> str:
    v = max(0, min(100, int(value)))
    if key == "morale":
        # higher better
        if v >= 75:
            return "high"
        if v >= 45:
            return "mid"
        if v >= 25:
            return "low"
        return "crit"
    # hunger / fatigue: higher worse
    if v <= 25:
        return "good"
    if v <= 50:
        return "mid"
    if v <= 75:
        return "bad"
    return "crit"


def soft_label(key: str, value: int) -> str:
    band = _band(key, value)
    if key == "hunger":
        return {
            "good": "อิ่ม",
            "mid": "ปกติ",
            "bad": "หิว",
            "crit": "อดอยาก",
        }.get(band, "ปกติ")
    if key == "fatigue":
        return {
            "good": "เบา",
            "mid": "พอไหว",
            "bad": "ล้า",
            "crit": "หมดแรง",
        }.get(band, "พอไหว")
    if key == "morale":
        return {
            "high": "ขวัญดี",
            "mid": "มั่นคง",
            "low": "หด",
            "crit": "ย่ำแย่",
        }.get(band, "มั่นคง")
    return "?"


def format_needs_soft_lines(player: Mapping[str, Any]) -> List[str]:
    n = get_needs(player)
    return [
        "〔สถานะกายใจ · soft〕",
        f" ท้อง  {soft_label('hunger', n['hunger'])}",
        f" ล้า   {soft_label('fatigue', n['fatigue'])}",
        f" ขวัญ  {soft_label('morale', n['morale'])}",
    ]


def format_needs_bar_line(player: Mapping[str, Any], width: int = 8) -> str:
    """Optional compact line (still soft labels, bars without numbers)."""
    from game.domain.bars import ratio_bar

    n = get_needs(player)
    # invert hunger/fatigue for fill feel (full bar = comfortable)
    h_fill = 100 - n["hunger"]
    f_fill = 100 - n["fatigue"]
    m_fill = n["morale"]
    return (
        f"ท้อง {ratio_bar(h_fill, 100, width)} "
        f"ล้า {ratio_bar(f_fill, 100, width)} "
        f"ขวัญ {ratio_bar(m_fill, 100, width)}"
    )


def needs_pressure_hint(player: Mapping[str, Any]) -> Optional[str]:
    """One soft line if something is critical."""
    n = get_needs(player)
    if _band("hunger", n["hunger"]) == "crit":
        return " …ท้องร้อง — ควรกินหรือพัก"
    if _band("fatigue", n["fatigue"]) == "crit":
        return " …ร่างหนัก — ควรพัก"
    if _band("morale", n["morale"]) == "crit":
        return " …ขวัญตก — ชัยชนะเล็กๆ อาจช่วย"
    return None
