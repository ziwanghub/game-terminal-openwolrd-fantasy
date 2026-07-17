"""
WO-Recovery-1 — multi-turn Recovery bottles (HP / MP / PY).

- Rank F–S table (S = Full, duration 3; others duration 5)
- One bottle → active buff per kind; refresh replaces same kind
- Tick on combat beat / field needs events (via apply_needs_event hook)
- Old one-shot potions (heal_hp / heal_mana) are unchanged
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

KIND_HP = "hp"
KIND_MP = "mp"
KIND_PY = "py"
KINDS = (KIND_HP, KIND_MP, KIND_PY)

ACTIVE_KEY = "active_recovery"

# Fallback table if ranks.yaml missing
_FALLBACK_RANKS: Dict[str, Dict[str, Any]] = {
    "F": {"amount": 15, "duration": 5, "full": False},
    "E": {"amount": 20, "duration": 5, "full": False},
    "D": {"amount": 30, "duration": 5, "full": False},
    "C": {"amount": 50, "duration": 5, "full": False},
    "B": {"amount": 80, "duration": 5, "full": False},
    "A": {"amount": 100, "duration": 5, "full": False},
    "S": {"amount": 0, "duration": 3, "full": True},
}

_KIND_SOFT = {
    KIND_HP: "เลือด",
    KIND_MP: "มานา",
    KIND_PY: "ล้า",
}

_KIND_LABEL = {
    KIND_HP: "HP",
    KIND_MP: "MP",
    KIND_PY: "PY",
}

# Events that advance one recovery "turn"
RECOVERY_TICK_EVENTS = frozenset(
    {"combat", "explore", "travel", "rest", "dungeon_tick"}
)

_ranks_cache: Optional[Dict[str, Dict[str, Any]]] = None


def _load_ranks_from_disk() -> Dict[str, Dict[str, Any]]:
    try:
        from game.config import DATA_DIR
        from game.data_load.loader import load_file

        path = DATA_DIR / "recovery" / "ranks.yaml"
        if not path.exists():
            return {k: dict(v) for k, v in _FALLBACK_RANKS.items()}
        raw = load_file(path)
        if not isinstance(raw, dict):
            return {k: dict(v) for k, v in _FALLBACK_RANKS.items()}
        ranks = raw.get("ranks") or {}
        out: Dict[str, Dict[str, Any]] = {}
        for key, spec in ranks.items():
            if not isinstance(spec, dict):
                continue
            rk = str(key).upper()
            out[rk] = {
                "amount": int(spec.get("amount") or 0),
                "duration": int(spec.get("duration") or (3 if rk == "S" else 5)),
                "full": bool(spec.get("full")),
            }
        if not out:
            return {k: dict(v) for k, v in _FALLBACK_RANKS.items()}
        return out
    except Exception:
        return {k: dict(v) for k, v in _FALLBACK_RANKS.items()}


def get_rank_table() -> Dict[str, Dict[str, Any]]:
    global _ranks_cache
    if _ranks_cache is None:
        _ranks_cache = _load_ranks_from_disk()
    return _ranks_cache


def clear_rank_cache() -> None:
    """Test helper."""
    global _ranks_cache
    _ranks_cache = None


def normalize_kind(kind: str) -> str:
    k = str(kind or "").strip().lower()
    if k in ("mana", "m"):
        return KIND_MP
    if k in ("fatigue", "fat", "y", "ล้า"):
        return KIND_PY
    if k in ("h", "blood", "เลือด"):
        return KIND_HP
    if k in KINDS:
        return k
    return ""


def normalize_rank(rank: str) -> str:
    r = str(rank or "").strip().upper()
    if r in get_rank_table():
        return r
    return ""


def rank_spec(rank: str) -> Dict[str, Any]:
    r = normalize_rank(rank)
    table = get_rank_table()
    if r and r in table:
        return dict(table[r])
    return dict(_FALLBACK_RANKS.get(r or "F") or _FALLBACK_RANKS["F"])


def is_recovery_item(it: Mapping[str, Any]) -> bool:
    if not it:
        return False
    if it.get("recovery_kind") and it.get("recovery_rank"):
        return True
    tags = it.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if "recovery" in tags:
        return True
    iid = str(it.get("id") or "")
    return iid.startswith("recovery_")


def parse_recovery_item(it: Mapping[str, Any]) -> Optional[Tuple[str, str]]:
    """Return (kind, rank) or None."""
    if not it:
        return None
    kind = normalize_kind(str(it.get("recovery_kind") or ""))
    rank = normalize_rank(str(it.get("recovery_rank") or ""))
    if kind and rank:
        return kind, rank
    # id pattern recovery_{kind}_{rank}
    iid = str(it.get("id") or "")
    if iid.startswith("recovery_"):
        parts = iid.split("_")
        if len(parts) >= 3:
            kind = normalize_kind(parts[1])
            rank = normalize_rank(parts[2])
            if kind and rank:
                return kind, rank
    return None


def ensure_active(player: MutableMapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = player.get(ACTIVE_KEY)
    if not isinstance(raw, dict):
        raw = {}
        player[ACTIVE_KEY] = raw
    # drop invalid
    cleaned: Dict[str, Dict[str, Any]] = {}
    for k, v in list(raw.items()):
        kind = normalize_kind(str(k))
        if not kind or not isinstance(v, dict):
            continue
        turns = int(v.get("turns_left") or 0)
        if turns <= 0:
            continue
        cleaned[kind] = {
            "kind": kind,
            "rank": normalize_rank(str(v.get("rank") or "F")) or "F",
            "turns_left": turns,
            "amount": int(v.get("amount") or 0),
            "full": bool(v.get("full")),
            "item_id": str(v.get("item_id") or ""),
            "name": str(v.get("name") or ""),
        }
    player[ACTIVE_KEY] = cleaned
    return cleaned


def get_active(player: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = player.get(ACTIVE_KEY)
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in raw.items():
        kind = normalize_kind(str(k))
        if kind and isinstance(v, dict) and int(v.get("turns_left") or 0) > 0:
            out[kind] = dict(v)
    return out


def soft_buff_line(entry: Mapping[str, Any]) -> str:
    kind = normalize_kind(str(entry.get("kind") or ""))
    rank = str(entry.get("rank") or "?")
    left = int(entry.get("turns_left") or 0)
    label = _KIND_LABEL.get(kind, kind.upper() or "?")
    soft = _KIND_SOFT.get(kind, "")
    if entry.get("full"):
        return f"กำลังฟื้น {soft or label} {rank} (เต็ม) · เหลือ {left} เทิร์น"
    amt = int(entry.get("amount") or 0)
    return f"กำลังฟื้น {soft or label} {rank} (+{amt}/เทิร์น) · เหลือ {left} เทิร์น"


def format_active_lines(player: Mapping[str, Any]) -> List[str]:
    active = get_active(player)
    if not active:
        return []
    lines = ["  〔กำลังฟื้น...〕"]
    for kind in KINDS:
        if kind in active:
            lines.append(f"  · {soft_buff_line(active[kind])}")
    return lines


def _apply_one_pulse(
    player: MutableMapping[str, Any],
    entry: Mapping[str, Any],
) -> Tuple[int, str]:
    """
    Apply one recovery tick. Returns (gained_or_relieved, short note fragment).
    """
    kind = normalize_kind(str(entry.get("kind") or ""))
    full = bool(entry.get("full"))
    amount = int(entry.get("amount") or 0)
    rank = str(entry.get("rank") or "?")

    if kind == KIND_HP:
        mhp = max(1, int(player.get("max_hp") or 1))
        before = int(player.get("hp") or 0)
        if full:
            player["hp"] = mhp
        else:
            player["hp"] = min(mhp, before + max(0, amount))
        gained = int(player["hp"]) - before
        return gained, f"HP+{gained}" if gained else "HP (เต็มแล้ว)"

    if kind == KIND_MP:
        mmp = max(0, int(player.get("max_mana") or 0))
        before = int(player.get("mana") or 0)
        if mmp <= 0:
            return 0, "MP (ไม่มีมานา)"
        if full:
            player["mana"] = mmp
        else:
            player["mana"] = min(mmp, before + max(0, amount))
        gained = int(player["mana"]) - before
        return gained, f"MP+{gained}" if gained else "MP (เต็มแล้ว)"

    if kind == KIND_PY:
        try:
            from game.domain.needs import ensure_needs

            ensure_needs(player)
        except Exception:
            player.setdefault("needs", {"hunger": 18, "fatigue": 12, "morale": 72})
        needs = dict(player.get("needs") or {})
        before = int(needs.get("fatigue") or 0)
        if full:
            needs["fatigue"] = 0
        else:
            needs["fatigue"] = max(0, before - max(0, amount))
        player["needs"] = needs
        relieved = before - int(needs["fatigue"])
        return relieved, f"ล้า−{relieved}" if relieved else "ล้า (เบาแล้ว)"

    return 0, f"{rank}?"


def tick_recovery(
    player: MutableMapping[str, Any],
    *,
    silent: bool = False,
) -> List[str]:
    """
    One recovery turn for all active kinds. Clamp to max / floor fatigue at 0.
    """
    active = ensure_active(player)
    if not active:
        return []
    notes: List[str] = []
    bits: List[str] = []
    expired: List[str] = []
    for kind in list(KINDS):
        entry = active.get(kind)
        if not entry:
            continue
        gained, frag = _apply_one_pulse(player, entry)
        left = int(entry.get("turns_left") or 0) - 1
        rank = str(entry.get("rank") or "?")
        if gained or True:
            bits.append(f"{frag}({rank})")
        if left <= 0:
            active.pop(kind, None)
            expired.append(_KIND_LABEL.get(kind, kind))
        else:
            entry["turns_left"] = left
            active[kind] = entry
    player[ACTIVE_KEY] = active
    if silent:
        return []
    if bits:
        notes.append("  กำลังฟื้น... " + " · ".join(bits))
    if expired:
        notes.append("  ผลขวดจาง: " + ", ".join(expired))
    return notes


def apply_recovery_item(
    player: MutableMapping[str, Any],
    it: Mapping[str, Any],
    *,
    item_id: str = "",
    immediate_tick: bool = True,
    silent: bool = False,
) -> List[str]:
    """
    Drink a recovery bottle: attach/replace buff for that kind.
    immediate_tick: first pulse now (counts as turn 1 of duration).
    """
    parsed = parse_recovery_item(it)
    if not parsed:
        return ["  ไม่ใช่ขวด Recovery"]
    kind, rank = parsed
    spec = rank_spec(rank)
    duration = max(1, int(spec.get("duration") or 5))
    amount = int(spec.get("amount") or 0)
    full = bool(spec.get("full"))
    name = str(it.get("name") or item_id or f"recovery_{kind}_{rank.lower()}")

    active = ensure_active(player)
    active[kind] = {
        "kind": kind,
        "rank": rank,
        "turns_left": duration,
        "amount": amount,
        "full": full,
        "item_id": str(item_id or it.get("id") or ""),
        "name": name,
    }
    player[ACTIVE_KEY] = active

    notes: List[str] = []
    if not silent:
        soft = _KIND_SOFT.get(kind, _KIND_LABEL.get(kind, kind))
        if full:
            notes.append(
                f"  ใช้「{name}」→ กำลังฟื้น {soft} {rank} (เต็ม) · {duration} เทิร์น"
            )
        else:
            notes.append(
                f"  ใช้「{name}」→ กำลังฟื้น {soft} {rank} (+{amount}/เทิร์น) · {duration} เทิร์น"
            )
    # First pulse for THIS kind only (do not advance other active bottles)
    if immediate_tick:
        entry = active.get(kind)
        if entry:
            gained, frag = _apply_one_pulse(player, entry)
            left = int(entry.get("turns_left") or 0) - 1
            if left <= 0:
                active.pop(kind, None)
            else:
                entry["turns_left"] = left
                active[kind] = entry
            player[ACTIVE_KEY] = active
            if not silent:
                notes.append(f"  กำลังฟื้น... {frag}({rank})")
                if left <= 0:
                    notes.append(f"  ผลขวดจาง: {_KIND_LABEL.get(kind, kind)}")
    return notes


def find_best_recovery_index(
    player: Mapping[str, Any],
    reg: Any,
    *,
    kind: str,
) -> int:
    """
    Best bag index for recovery kind. Prefers higher rank (S > A > ... > F).
    Returns -1 if none.
    """
    kind = normalize_kind(kind)
    if not kind:
        return -1
    rank_order = {r: i for i, r in enumerate(["F", "E", "D", "C", "B", "A", "S"])}
    ids = list(player.get("inventory_ids") or [])
    inv = list(player.get("inventory") or [])
    n = max(len(ids), len(inv))
    best_i, best_score = -1, -1
    items = getattr(reg, "items", None) or {}
    for i in range(n):
        iid = str(ids[i] if i < len(ids) else "") or ""
        it = dict(items.get(iid) or {})
        if not it and iid:
            continue
        if not it:
            # name fallback skip
            continue
        it.setdefault("id", iid)
        parsed = parse_recovery_item(it)
        if not parsed:
            continue
        k, rank = parsed
        if k != kind:
            continue
        score = rank_order.get(rank, 0)
        # prefer higher rank; tie-break larger amount
        score = score * 1000 + int(rank_spec(rank).get("amount") or 0)
        if score > best_score:
            best_score = score
            best_i = i
    return best_i


def consume_recovery_from_bag(
    player: MutableMapping[str, Any],
    reg: Any,
    *,
    kind: str,
    immediate_tick: bool = True,
    silent: bool = False,
) -> List[str]:
    """
    Find best recovery bottle of kind, remove one unit, apply buff.
    """
    kind = normalize_kind(kind)
    if not kind:
        return ["  ชนิด Recovery ไม่รู้จัก"]
    idx = find_best_recovery_index(player, reg, kind=kind)
    if idx < 0:
        label = _KIND_LABEL.get(kind, kind)
        return [f"  ไม่มีขวด Recovery {label} ในกระเป๋า"]

    items = getattr(reg, "items", None) or {}
    ids = list(player.get("inventory_ids") or [])
    iid = str(ids[idx] if idx < len(ids) else "") or ""
    it = dict(items.get(iid) or {})
    it.setdefault("id", iid)

    # stack-aware remove if available
    try:
        from game.domain.bag_stack import remove_units_at

        removed = remove_units_at(player, idx, reg, amount=1)
        if not removed:
            return [f"  ใช้ขวด Recovery ไม่สำเร็จ"]
    except Exception:
        # parallel list pop
        inv = list(player.get("inventory") or [])
        rar = list(player.get("inventory_rarities") or [])
        if idx < len(inv):
            inv.pop(idx)
        if idx < len(ids):
            ids.pop(idx)
        if idx < len(rar):
            rar.pop(idx)
        player["inventory"] = inv
        player["inventory_ids"] = ids
        player["inventory_rarities"] = rar

    return apply_recovery_item(
        player,
        it,
        item_id=iid,
        immediate_tick=immediate_tick,
        silent=silent,
    )


def try_handle_item_use(
    player: MutableMapping[str, Any],
    it: Mapping[str, Any],
    *,
    item_id: str = "",
    immediate_tick: bool = True,
) -> Optional[List[str]]:
    """
    If item is recovery, apply and return notes; else None (caller continues).
    """
    if not is_recovery_item(it) and not parse_recovery_item(it):
        return None
    return apply_recovery_item(
        player, it, item_id=item_id, immediate_tick=immediate_tick, silent=False
    )


def recovery_amount_table() -> Dict[str, Any]:
    """Public snapshot for tests / UI."""
    table = get_rank_table()
    return {
        r: {
            "amount": int(s.get("amount") or 0),
            "duration": int(s.get("duration") or 5),
            "full": bool(s.get("full")),
        }
        for r, s in table.items()
    }
