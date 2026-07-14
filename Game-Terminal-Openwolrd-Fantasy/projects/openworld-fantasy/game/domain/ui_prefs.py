"""Player UI preferences (density, flavor) — soft defaults + field menu U."""
from __future__ import annotations

from typing import Any, Dict, List, MutableMapping, Optional, Sequence, Tuple


DEFAULT_PREFS: Dict[str, Any] = {
    "density": "standard",  # compact | standard | full
    "flavor": "on",  # on | brief | off
    "art": "rare_only",  # off | rare_only | all
    "clear_screen": False,
    "combat_numbers": True,
    "soft_labels": True,
    "warn_travel_ambush": True,
    "live_tama": True,  # T3: soft drip + enter anim on PERSONAL
    "tama_enter_anim": True,
}

# (key, label, choices cycle)
PREF_OPTIONS: List[Tuple[str, str, Sequence[Any]]] = [
    ("density", "ความหนาแน่นจอ", ("compact", "standard", "full")),
    ("flavor", "บรรยาย flavor", ("on", "brief", "off")),
    ("art", "ศิลปะ ASCII", ("off", "rare_only", "all")),
    ("combat_numbers", "ตัวเลขในไฟต์", (True, False)),
    ("soft_labels", "ป้าย soft (ไม่สปอยล์)", (True, False)),
    ("warn_travel_ambush", "เตือนเสี่ยงซุ่มตอนเดินทาง", (True, False)),
    ("live_tama", "Tama เวลาไหลบนจอ (T3)", (True, False)),
    ("tama_enter_anim", "แอนิเมชันเข้าตัวละคร (T3)", (True, False)),
    ("clear_screen", "ล้างจอก่อนสถานะ (ทดลอง)", (False, True)),
]


def ensure_ui_prefs(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    prefs = dict(DEFAULT_PREFS)
    raw = player.get("ui_prefs")
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k in DEFAULT_PREFS:
                prefs[k] = v
    player["ui_prefs"] = prefs
    return prefs


def flavor_max_lines(player: MutableMapping[str, Any]) -> int:
    prefs = ensure_ui_prefs(player)
    mode = str(prefs.get("flavor") or "on")
    if mode == "off":
        return 0
    if mode == "brief":
        return 1
    return 3


def use_compact_vitals(player: MutableMapping[str, Any]) -> bool:
    prefs = ensure_ui_prefs(player)
    return str(prefs.get("density") or "standard") in ("compact", "standard")


def prefs_menu_lines(player: MutableMapping[str, Any]) -> List[str]:
    prefs = ensure_ui_prefs(player)
    lines = [" ตั้งค่าจอ (U)", "---"]
    for i, (key, label, _choices) in enumerate(PREF_OPTIONS, 1):
        val = prefs.get(key)
        if isinstance(val, bool):
            shown = "เปิด" if val else "ปิด"
        else:
            shown = str(val)
        lines.append(f" {i}. {label}: {shown}")
    lines.append(" 0. กลับ")
    lines.append(" พิมพ์หมายเลขเพื่อสลับค่า")
    return lines


def cycle_pref(player: MutableMapping[str, Any], index_1based: int) -> Optional[str]:
    """Cycle one pref by menu number. Returns soft note or None if invalid."""
    prefs = ensure_ui_prefs(player)
    if index_1based < 1 or index_1based > len(PREF_OPTIONS):
        return None
    key, label, choices = PREF_OPTIONS[index_1based - 1]
    cur = prefs.get(key)
    try:
        idx = list(choices).index(cur)  # type: ignore[arg-type]
    except ValueError:
        idx = 0
    nxt = choices[(idx + 1) % len(choices)]
    prefs[key] = nxt
    player["ui_prefs"] = prefs
    if isinstance(nxt, bool):
        shown = "เปิด" if nxt else "ปิด"
    else:
        shown = str(nxt)
    return f"{label} → {shown}"
