"""Play statistics — track lifetime counters for the character."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping


DEFAULT_STATS: Dict[str, int] = {
    "kills": 0,
    "boss_kills": 0,
    "deaths": 0,
    "combats": 0,
    "flees": 0,
    "travels": 0,
    "explores": 0,
    "rests": 0,
    "crafts": 0,
    "quests_completed": 0,
    "chests_opened": 0,
    "shop_purchases": 0,
    "auto_ticks": 0,
    "xp_gained_total": 0,
    "money_gained_total": 0,
    "upgrades": 0,
    "cards_socketed": 0,
}


def ensure_stats(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    st = dict(player.get("stats") or {})
    for k, v in DEFAULT_STATS.items():
        st.setdefault(k, v)
    player["stats"] = st
    return st


def bump_stat(player: MutableMapping[str, Any], key: str, amount: int = 1) -> None:
    st = ensure_stats(player)
    st[key] = int(st.get(key, 0)) + int(amount)
    player["stats"] = st


def format_stats_lines(player: Mapping[str, Any]) -> List[str]:
    """Lifetime counters — grouped rows for scanability under full status."""
    st = dict(player.get("stats") or DEFAULT_STATS)
    name = player.get("name", "?")
    lv = player.get("level", 1)
    boss_kinds = len(player.get("bosses_defeated") or [])
    lines = [
        f" {name}  ·  Lv.{lv}",
        f" ต่อสู้   ฆ่ามอน {st.get('kills', 0)}"
        f"  ·  บอส {st.get('boss_kills', 0)}"
        f"  ·  ไฟต์ {st.get('combats', 0)}"
        f"  ·  ตาย {st.get('deaths', 0)}"
        f"  ·  หนี {st.get('flees', 0)}",
        f" โลก     สำรวจ {st.get('explores', 0)}"
        f"  ·  พัก {st.get('rests', 0)}"
        f"  ·  เดินทาง {st.get('travels', 0)}"
        f"  ·  ออโต้ {st.get('auto_ticks', 0)}",
        f" ทำของ   คราฟ {st.get('crafts', 0)}"
        f"  ·  อัป {st.get('upgrades', 0)}"
        f"  ·  การ์ด {st.get('cards_socketed', 0)}",
        f" เควส    สำเร็จ {st.get('quests_completed', 0)}"
        f"  ·  หีบ {st.get('chests_opened', 0)}"
        f"  ·  ซื้อ {st.get('shop_purchases', 0)}",
        f" รางวัล  XP รวม {st.get('xp_gained_total', 0)}"
        f"  ·  เงินโลก {st.get('money_gained_total', 0)}",
        f" บอสที่ชนะ  {boss_kinds} ชนิด",
    ]
    return lines
