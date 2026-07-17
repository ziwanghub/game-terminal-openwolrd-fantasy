"""
WO-Worthiness-1 — Path of Worthiness (Lite).

เข้าถึงได้ ≠ สมควรได้
- Soft wall: Whisper / Trial / Reward Lock
- Farm/chest loot ceiling: ≤ legendary (rank 5)
- Trial T1/T2: reuse area bosses + one-time manual grants
- Auto: no first-trial clear, no god-tier / trial-exclusive grants
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.data_load.registry import DataRegistry

# ── rarity ceiling (farm path) ─────────────────────────────────────────────

FARM_MAX_RARITY_RANK = 5  # legendary
FARM_MAX_RARITY_ID = "legendary"
GOD_TIER_IDS = frozenset({"divine", "archdivine", "mythic"})

# Trial-exclusive rewards (never from farm/chest/auto)
TRIAL_EXCLUSIVE_ITEMS = frozenset(
    {
        "relic_divine_laurel",
        "relic_god_eye",
    }
)

# ── trials (boss reuse + flag) ─────────────────────────────────────────────

TRIALS: Dict[str, Dict[str, Any]] = {
    "t1_forest": {
        "id": "t1_forest",
        "boss_id": "boss_forest_king",
        "area_id": "dark_forest",
        "reward_item": "relic_divine_laurel",
        "reward_rarity": "legendary",
        "label": "พิสูจน์ · ราชันย์เถื่อน",
        "soft_ready_lv": 5,
    },
    "t2_marsh": {
        "id": "t2_marsh",
        "boss_id": "boss_mist_hydra",
        "area_id": "mist_marsh",
        "reward_item": "relic_god_eye",
        "reward_rarity": "divine",
        "label": "พิสูจน์ · ไฮดราหมอก",
        "soft_ready_lv": 9,
    },
}

BOSS_TO_TRIAL = {str(v["boss_id"]): k for k, v in TRIALS.items()}

# Area soft wall (Whisper until trial flag)
# mist_marsh: need T1 · mountain_rock: need T2
AREA_WHISPER: Dict[str, str] = {
    "mist_marsh": "t1_forest",
    "mountain_rock": "t2_marsh",
}

STATE_KEY = "worthiness"


def ensure_worthiness(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    st = player.get(STATE_KEY)
    if not isinstance(st, dict):
        st = {}
    st.setdefault("trials_cleared", [])
    st.setdefault("rewards_granted", [])
    st.setdefault("god_eye_owned", False)
    # list copy safety
    if not isinstance(st.get("trials_cleared"), list):
        st["trials_cleared"] = list(st.get("trials_cleared") or [])
    if not isinstance(st.get("rewards_granted"), list):
        st["rewards_granted"] = list(st.get("rewards_granted") or [])
    player[STATE_KEY] = st
    return st


def trials_cleared(player: Mapping[str, Any]) -> List[str]:
    st = player.get(STATE_KEY) if isinstance(player.get(STATE_KEY), dict) else {}
    return [str(x) for x in (st.get("trials_cleared") or [])]


def has_trial(player: Mapping[str, Any], trial_id: str) -> bool:
    return str(trial_id) in trials_cleared(player)


def trial_for_boss(boss_id: str) -> Optional[Dict[str, Any]]:
    tid = BOSS_TO_TRIAL.get(str(boss_id or ""))
    if not tid:
        return None
    return dict(TRIALS[tid])


def is_trial_boss(boss_id: str) -> bool:
    return str(boss_id or "") in BOSS_TO_TRIAL


def is_first_trial_pending(player: Mapping[str, Any], boss_id: str) -> bool:
    tr = trial_for_boss(boss_id)
    if not tr:
        return False
    return not has_trial(player, str(tr["id"]))


# ── Soft wall ─────────────────────────────────────────────────────────────


def soft_wall_for_area(player: Mapping[str, Any], area_id: str) -> str:
    """
    Return open | whisper for area soft wall (lite).
    Reward Lock is global for loot, not per-area enter.
    """
    aid = str(area_id or "")
    need = AREA_WHISPER.get(aid)
    if not need:
        return "open"
    if has_trial(player, need):
        return "open"
    return "whisper"


def area_whisper_lines(
    player: Mapping[str, Any],
    reg: DataRegistry,
    area_id: str,
) -> List[str]:
    """Soft 'ยังไม่พร้อม' when entering whisper area — never hard block."""
    if soft_wall_for_area(player, area_id) != "whisper":
        return []
    area = reg.areas.get(str(area_id)) or {}
    name = str(area.get("name") or area_id)
    need = AREA_WHISPER.get(str(area_id)) or ""
    tr = TRIALS.get(need) or {}
    boss_hint = str(tr.get("label") or "การพิสูจน์ก่อนหน้า")
    return [
        f"  …ลมที่{name}กระซิบว่าคุณยังไม่พร้อม",
        f"  「เข้าได้ — แต่เงายังไม่ยอมรับ · {boss_hint}」",
        "  ถอยไปเตรียมตัวได้ · เข้าถึงได้ ≠ สมควรได้",
    ]


def trial_readiness_lines(
    player: Mapping[str, Any],
    reg: DataRegistry,
    boss_id: str,
) -> List[str]:
    """Soft prep hints before challenging a trial boss (manual)."""
    tr = trial_for_boss(boss_id)
    if not tr:
        return []
    lines: List[str] = []
    lv = int(player.get("level") or 1)
    need_lv = int(tr.get("soft_ready_lv") or 1)
    if is_first_trial_pending(player, boss_id):
        lines.append(f"  「วงพิสูจน์ · {tr.get('label')} — ต้องลงมือเอง」")
        if lv < need_lv:
            lines.append(
                f"  …ระดับยังบาง (แนะนำ ~{need_lv}+) — ยังท้าได้ แต่ลมบอกว่าไม่พร้อม"
            )
        try:
            from game.domain.needs import ensure_needs, get_needs

            ensure_needs(player)  # type: ignore[arg-type]
            n = get_needs(player)
            if int(n.get("hunger") or 0) >= 70 or int(n.get("fatigue") or 0) >= 70:
                lines.append("  …กายยังหิวหรือล้า — เตรียมอาหาร/พักก่อนจะดีกว่า")
            if int(n.get("morale") or 100) <= 35:
                lines.append("  …ขวัญบาง — วงพิสูจน์จะหนักขึ้น")
        except Exception:
            pass
        if not has_trial(player, "t1_forest") and str(tr.get("id")) == "t2_marsh":
            lines.append("  …ยังไม่ได้พิสูจน์ป่า — เส้นทางหนองจะโหดกว่า")
    else:
        lines.append("  「วงนี้เคยผ่านแล้ว — รีรันได้ แต่ของสมควรไม่ซ้ำ」")
    return lines


# ── Rarity / item ceiling ─────────────────────────────────────────────────


def rarity_rank(reg: Optional[DataRegistry], rarity_id: str) -> int:
    try:
        from game.domain.rarity import tier_rank

        return int(tier_rank(reg, rarity_id))
    except Exception:
        return 1


def clamp_farm_rarity(
    reg: Optional[DataRegistry],
    rarity_id: str,
    *,
    allow_god: bool = False,
) -> str:
    """Clamp to ≤ legendary unless allow_god (trial grant path)."""
    rid = str(rarity_id or "common")
    if allow_god:
        return rid
    if rid in GOD_TIER_IDS or rarity_rank(reg, rid) > FARM_MAX_RARITY_RANK:
        return FARM_MAX_RARITY_ID
    return rid


def is_god_tier_rarity(rarity_id: str) -> bool:
    return str(rarity_id or "") in GOD_TIER_IDS


def is_trial_exclusive_item(item_id: str) -> bool:
    return str(item_id or "") in TRIAL_EXCLUSIVE_ITEMS


def item_blocked_on_farm(
    item_id: str,
    reg: DataRegistry,
    *,
    allow_god: bool = False,
) -> bool:
    """True if item must not appear on farm/chest/normal loot paths."""
    if allow_god:
        return False
    iid = str(item_id or "")
    if is_trial_exclusive_item(iid):
        return True
    it = (reg.items or {}).get(iid) or (reg.cards or {}).get(iid) or {}
    base_r = str(it.get("rarity") or "common")
    if is_god_tier_rarity(base_r) or rarity_rank(reg, base_r) > FARM_MAX_RARITY_RANK:
        return True
    return False


def filter_farm_drop_id(
    item_id: str,
    reg: DataRegistry,
    *,
    allow_god: bool = False,
) -> Optional[str]:
    """Return item_id or None if blocked on farm path."""
    if item_blocked_on_farm(item_id, reg, allow_god=allow_god):
        return None
    return str(item_id)


# ── Auto policy ───────────────────────────────────────────────────────────


def auto_may_fight_boss(
    player: Mapping[str, Any],
    mon: Mapping[str, Any],
) -> Tuple[bool, str]:
    """
    Auto may not complete first trial.
    After trial cleared, rematch auto is allowed (still no trial grant).
    """
    if not mon.get("boss"):
        return True, ""
    mid = str(mon.get("id") or "")
    if not is_trial_boss(mid):
        return True, ""
    if is_first_trial_pending(player, mid):
        return False, "วงพิสูจน์ต้องลงมือเอง — ออโต้ข้ามบอสนี้ไม่ได้"
    return True, ""


def combat_via_auto(player: Mapping[str, Any]) -> bool:
    return bool(player.get("_combat_via_auto"))


def set_combat_via_auto(player: MutableMapping[str, Any], value: bool) -> None:
    if value:
        player["_combat_via_auto"] = True
    else:
        player.pop("_combat_via_auto", None)


# ── Trial completion / grants ─────────────────────────────────────────────


def on_boss_defeated_worthiness(
    player: MutableMapping[str, Any],
    mon: Mapping[str, Any],
    reg: DataRegistry,
    *,
    via_auto: bool = False,
) -> List[str]:
    """
    After area boss kill: first manual trial → grant exclusive reward once.
    Auto first-trial: no grant (should be blocked earlier; soft line if slipped).
    """
    ensure_worthiness(player)
    mid = str(mon.get("id") or "")
    tr = trial_for_boss(mid)
    if not tr:
        return []

    tid = str(tr["id"])
    lines: List[str] = []

    if via_auto or combat_via_auto(player):
        if is_first_trial_pending(player, mid):
            lines.append("  …ออโต้แตะวงพิสูจน์ไม่ได้ — ของสมควรยังหลับอยู่")
        return lines

    if has_trial(player, tid):
        lines.append("  「เงารู้จักคุณแล้ว — รางวัลพิสูจน์ไม่ซ้ำ」")
        return lines

    # Mark cleared
    st = ensure_worthiness(player)
    cleared = list(st.get("trials_cleared") or [])
    if tid not in cleared:
        cleared.append(tid)
    st["trials_cleared"] = cleared

    reward_id = str(tr.get("reward_item") or "")
    granted = list(st.get("rewards_granted") or [])
    if reward_id and reward_id not in granted:
        from game.domain.equipment import add_item

        rid = str(tr.get("reward_rarity") or "legendary")
        # trial path may grant god-tier rarity
        shown = add_item(player, reward_id, reg, rarity=rid)
        if shown and "ไม่พบ" not in str(shown):
            granted.append(reward_id)
            st["rewards_granted"] = granted
            if reward_id == "relic_god_eye":
                st["god_eye_owned"] = True
                lines.append("  「ดวงตาพระเจ้าเปิด — หนึ่งครั้งต่อวิญญาณนี้」")
            elif reward_id == "relic_divine_laurel":
                lines.append("  「พวงหรีดวายุแรกยอมรับการพิสูจน์」")
            lines.append(f"  ได้ {shown}")
            lines.append("  …เข้าถึงได้ ≠ สมควรได้ — คุณพิสูจน์แล้ว")
        else:
            lines.append("  …เงายอมรับการพิสูจน์ แต่ของยังไม่โผล่ (กระเป๋า?)")
    else:
        lines.append("  「วงพิสูจน์ผ่าน — ธงความสมควรถูกจารึก」")

    player[STATE_KEY] = st
    return lines


def travel_worthiness_lines(
    player: Mapping[str, Any],
    reg: DataRegistry,
    area_id: str,
) -> List[str]:
    """Combine whisper soft wall lines for travel arrival."""
    return area_whisper_lines(player, reg, area_id)


def emit_worthiness_soft_alert(
    player: MutableMapping[str, Any],
    *,
    body: str = "",
) -> List[str]:
    """Soft lines for worthiness (no hard catalog dependency)."""
    lines: List[str] = []
    if body:
        lines.append(body if str(body).startswith(" ") else f"  {body}")
    else:
        lines.append("  …ลมบอกว่ายังไม่พร้อม")
    return lines
