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
    st = dict(player.get("stats") or DEFAULT_STATS)
    name = player.get("name", "?")
    lv = player.get("level", 1)
    lines = [
        f"สถิติ: {name} Lv.{lv}",
        f" ฆ่ามอน {st.get('kills', 0)} · บอส {st.get('boss_kills', 0)} · ไฟต์ {st.get('combats', 0)}",
        f" ตาย(soft) {st.get('deaths', 0)} · หนี {st.get('flees', 0)}",
        f" สำรวจ {st.get('explores', 0)} · พัก {st.get('rests', 0)} · เดินทาง {st.get('travels', 0)}",
        f" คราฟ {st.get('crafts', 0)} · อัปเกียร์ {st.get('upgrades', 0)} · ใส่การ์ด {st.get('cards_socketed', 0)}",
        f" เควสสำเร็จ {st.get('quests_completed', 0)} · หีบ {st.get('chests_opened', 0)} · ซื้อของ {st.get('shop_purchases', 0)}",
        f" ติกออโต้ {st.get('auto_ticks', 0)}",
        f" XP รวมที่ได้ {st.get('xp_gained_total', 0)} · เงินโลกที่ได้ {st.get('money_gained_total', 0)}",
        f" บอสที่ชนะ: {len(player.get('bosses_defeated') or [])} ชนิด",
    ]
    return lines
