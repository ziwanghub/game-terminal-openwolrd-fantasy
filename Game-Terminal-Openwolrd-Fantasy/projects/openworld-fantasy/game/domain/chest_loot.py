"""
Chest loot system L0–L5 — sealed chests, open tables, soft drop, quest/board, unit unique, bag UX.

Ranks: common | uncommon | rare | s | ss | sss | unit
Players never see weights / % — only soft labels and open results.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from game.config import SAVES_DIR
from game.data_load.registry import DataRegistry

# Rank order low → high for L5 sort / summary (unit last special)
_RANK_ORDER = ("common", "uncommon", "rare", "s", "ss", "sss", "unit")


def rank_order_index(rank_id: str) -> int:
    rid = str(rank_id or "common").lower()
    try:
        return _RANK_ORDER.index(rid)
    except ValueError:
        return 0


def ensure_chest_state(player: MutableMapping[str, Any]) -> None:
    player.setdefault("unique_owned", [])
    player.setdefault("chest_opens", 0)
    player.setdefault("chest_dry_streak", 0)
    player.setdefault("recent_kill_ids", [])  # anti_farm window
    player.setdefault("flags", {})


def _chests_cfg(reg: DataRegistry) -> Dict[str, Any]:
    return dict(getattr(reg, "chests_cfg", None) or {})


def rank_def(reg: DataRegistry, rank_id: str) -> Dict[str, Any]:
    # ranks.yaml structure: {default, ranks: [...]}
    raw = _chests_cfg(reg).get("ranks") or {}
    ranks = list(raw.get("ranks") or []) if isinstance(raw, dict) else []
    for r in ranks:
        if str(r.get("id")) == str(rank_id):
            return dict(r)
    # fallback
    return {
        "id": "common",
        "name": "ธรรมดา",
        "label": "หีบ · ธรรมดา",
        "symbol": "□",
        "rolls_min": 1,
        "rolls_max": 1,
        "bucket_weights": {"material": 50, "food": 25, "heal": 25},
        "rarity_bias": {"common": 1.0, "uncommon": 0.5},
    }


def all_rank_ids(reg: DataRegistry) -> List[str]:
    raw = _chests_cfg(reg).get("ranks") or {}
    ranks = list(raw.get("ranks") or []) if isinstance(raw, dict) else []
    return [str(r.get("id")) for r in ranks if r.get("id")]


def sealed_item_for_rank(reg: DataRegistry, rank_id: str) -> str:
    pools = _chests_cfg(reg).get("pools") or {}
    sealed = dict(pools.get("sealed_items") or {})
    return str(sealed.get(rank_id) or f"sealed_chest_{rank_id}")


def is_chest_item(item: Mapping[str, Any]) -> bool:
    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    return "chest" in tags or bool(item.get("chest_rank"))


def chest_rank_from_item(item: Mapping[str, Any]) -> str:
    return str(item.get("chest_rank") or "common")


def chest_soft_label(reg: DataRegistry, rank_id: str) -> str:
    """Soft label with symbol, e.g. '□ หีบ · ธรรมดา'."""
    rd = rank_def(reg, rank_id)
    sym = str(rd.get("symbol") or "□")
    label = str(rd.get("label") or rd.get("name") or rank_id)
    return f"{sym} {label}"


def summarize_chest_ranks(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Tuple[str, int]]:
    """
    L5: count sealed chests by rank (highest first).
    Returns list of (rank_id, count).
    """
    from game.domain.equipment import item_by_id

    from game.domain.bag_stack import qty_at

    counts: Dict[str, int] = {}
    for i, iid in enumerate(player.get("inventory_ids") or []):
        it = item_by_id(reg, str(iid)) or {}
        if not is_chest_item(it):
            continue
        rid = chest_rank_from_item(it)
        counts[rid] = counts.get(rid, 0) + qty_at(player, i)
    ordered = sorted(counts.items(), key=lambda kv: rank_order_index(kv[0]), reverse=True)
    return ordered


def format_chest_stash_summary(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """Soft multi-line stash overview for bag category header (box sections)."""
    rows = summarize_chest_ranks(player, reg)
    if not rows:
        return [
            " สถานะคลัง",
            "  ว่าง — หาได้จากบอส · เควส · เหตุการณ์สนาม",
            "---",
            " วิธีใช้",
            "  หมายเลข = เปิดหนึ่งใบ",
            "  A = เปิดทั้งหมด (ยืนยัน)",
            "  0 = กลับ",
        ]
    total = sum(n for _, n in rows)
    lines = [
        " สถานะคลัง",
        f"  รวม  {total} ใบ",
        "  แรงก์สูง ≠ ของดีเสมอ (soft)",
        "---",
        " แยกแรงก์",
    ]
    for rid, n in rows:
        rd = rank_def(reg, rid)
        sym = str(rd.get("symbol") or "□")
        nm = str(rd.get("name") or rid)
        lines.append(f"  {sym}  {nm:<8}  ×{n}")
    lines.extend(
        [
            "---",
            " วิธีใช้",
            "  หมายเลข = เปิดหนึ่งใบ",
            "  A = เปิดทั้งหมด (ยืนยัน)",
            "  0 = กลับ",
        ]
    )
    return lines


def _weighted_pick(weights: Mapping[str, float], rng: random.Random) -> str:
    keys = []
    ws = []
    for k, w in weights.items():
        fw = float(w or 0)
        if fw > 0:
            keys.append(str(k))
            ws.append(fw)
    if not keys:
        return "material"
    total = sum(ws)
    r = rng.random() * total
    acc = 0.0
    for k, w in zip(keys, ws):
        acc += w
        if r <= acc:
            return k
    return keys[-1]


def _player_noise(player: Mapping[str, Any], salt: str = "") -> float:
    """0.72–1.28-ish from hash — not a fixed pattern."""
    src = _chests_cfg  # placate lint
    pid = str(player.get("id") or player.get("name") or "x")
    day = time.strftime("%Y-%m-%d")
    kills = int((player.get("stats") or {}).get("kills") or 0)
    h = hashlib.sha256(f"{pid}|{day}|{kills}|{salt}".encode()).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return 0.72 + n * 0.56


def _anti_farm_mult(player: Mapping[str, Any], mon_id: str, reg: DataRegistry) -> float:
    cfg = (_chests_cfg(reg).get("sources") or {}).get("anti_farm") or {}
    window = int(cfg.get("window_kills") or 8)
    penalty = float(cfg.get("same_id_penalty") or 0.55)
    min_m = float(cfg.get("min_mult") or 0.15)
    recent = list(player.get("recent_kill_ids") or [])
    same = sum(1 for x in recent[-window:] if str(x) == str(mon_id))
    if same <= 1:
        return 1.0
    mult = penalty ** (same - 1)
    return max(min_m, mult)


def note_kill_for_farm(player: MutableMapping[str, Any], mon_id: str) -> None:
    ensure_chest_state(player)
    recent = list(player.get("recent_kill_ids") or [])
    recent.append(str(mon_id))
    player["recent_kill_ids"] = recent[-24:]


def decide_chest_drop(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    source: str,
    mon: Optional[Mapping[str, Any]] = None,
    first_clear: bool = False,
) -> Optional[str]:
    """
    Returns chest rank id or None.
    source: normal_monster | elite_monster | area_boss | dungeon_boss
    """
    ensure_chest_state(player)
    sources = (_chests_cfg(reg).get("sources") or {}).get("sources") or {}
    sc = dict(sources.get(source) or {})
    if not sc:
        # infer from mon
        if mon and mon.get("boss"):
            if mon.get("dungeon_boss"):
                source = "dungeon_boss"
            else:
                source = "area_boss"
            sc = dict(sources.get(source) or {})
        else:
            sc = dict(sources.get("normal_monster") or {"base_chance": 0.01})

    base = float(sc.get("base_chance") or 0.01)
    if first_clear:
        base += float(sc.get("first_clear_bonus") or 0)
    mon_id = str((mon or {}).get("id") or "x")
    chance = base
    chance *= _player_noise(player, salt=source + mon_id)
    chance *= _anti_farm_mult(player, mon_id, reg)
    # hidden pity: dry streak soft
    dry = int(player.get("chest_dry_streak") or 0)
    if dry >= 12:
        chance *= 1.0 + min(0.8, (dry - 11) * 0.04)
    # mastery soft (high mastery slightly better rare finds)
    mastery = 0
    if mon:
        area = str(mon.get("_area_id") or player.get("location") or "")
        mastery = int((player.get("area_mastery") or {}).get(area) or 0)
    chance *= 1.0 + min(0.15, mastery / 400.0)
    # L3: hidden quest flags boost chest chance (never shown)
    flags = dict(player.get("flags") or {})
    if flags.get("chest_table_void") or flags.get("chest_favor"):
        chance *= 1.0 + min(0.35, 0.12 * float(flags.get("chest_favor") or 1))
    if flags.get("chest_table_void"):
        chance *= 1.18
    chance = max(0.0, min(0.92, chance))

    if rng.random() > chance:
        player["chest_dry_streak"] = dry + 1
        return None

    player["chest_dry_streak"] = 0
    # pick rank
    weights = dict(sc.get("rank_weights") or {"common": 1})
    # first clear bias toward higher ranks slightly
    if first_clear:
        for k in list(weights.keys()):
            if k in ("s", "ss", "sss", "rare"):
                weights[k] = float(weights[k]) * 1.25
    rank = _weighted_pick(weights, rng)
    # elite bump
    if mon and mon.get("elite") and rank == "common" and rng.random() < 0.35:
        rank = "uncommon"
    return rank


def grant_sealed_chest(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rank_id: str,
) -> Tuple[bool, str]:
    """Put sealed chest item in bag. Returns (ok, display_name)."""
    from game.domain.equipment import add_item

    iid = sealed_item_for_rank(reg, rank_id)
    if iid not in (reg.items or {}):
        return False, ""
    shown = add_item(player, iid, reg, rarity="common")
    return True, shown


def unique_owned(player: Mapping[str, Any], item_id: str) -> bool:
    return str(item_id) in set(player.get("unique_owned") or [])


def mark_unique_owned(player: MutableMapping[str, Any], item_id: str) -> None:
    ensure_chest_state(player)
    owned = list(player.get("unique_owned") or [])
    if item_id not in owned:
        owned.append(str(item_id))
    player["unique_owned"] = owned


# ── L4 world-scoped unique claims (one per world_id) ──


def unique_claims_path(world_id: str) -> Path:
    d = SAVES_DIR / str(world_id or "default")
    d.mkdir(parents=True, exist_ok=True)
    return d / "unique_claims.json"


def load_unique_claims(world_id: str) -> Dict[str, Any]:
    path = unique_claims_path(world_id)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_unique_claims(world_id: str, claims: Mapping[str, Any]) -> None:
    path = unique_claims_path(world_id)
    path.write_text(json.dumps(dict(claims), ensure_ascii=False, indent=2), encoding="utf-8")


def is_unique_world_claimed(
    world_id: str,
    item_id: str,
    except_player_id: Optional[str] = None,
) -> bool:
    claims = load_unique_claims(world_id)
    owner = claims.get(str(item_id))
    if not owner:
        return False
    if except_player_id and str(owner.get("player_id")) == str(except_player_id):
        return False
    return True


def claim_unique_world(
    world_id: str,
    item_id: str,
    player: Mapping[str, Any],
) -> bool:
    claims = load_unique_claims(world_id)
    iid = str(item_id)
    pid = str(player.get("id") or "")
    if iid in claims and str(claims[iid].get("player_id")) != pid:
        return False
    claims[iid] = {
        "player_id": pid,
        "player_name": player.get("name"),
    }
    save_unique_claims(world_id, claims)
    return True


def unit_unique_defs(reg: DataRegistry) -> List[Dict[str, Any]]:
    """Load unit unique catalog from data/chests/unit_uniques.yaml (+ item fallback)."""
    raw = _chests_cfg(reg).get("unit_uniques") or {}
    items = list(raw.get("uniques") or raw.get("items") or [])
    if items:
        out = []
        for u in items:
            if isinstance(u, dict) and u.get("id"):
                out.append(dict(u))
            elif isinstance(u, str):
                out.append({"id": u, "unique_scope": "save"})
        return out
    # fallback: pools.buckets.unit_unique
    pools = (_chests_cfg(reg).get("pools") or {}).get("buckets") or {}
    return [
        {"id": str(x), "unique_scope": "save"}
        for x in (pools.get("unit_unique") or [])
        if x
    ]


def unique_scope_of(reg: DataRegistry, item_id: str) -> str:
    for u in unit_unique_defs(reg):
        if str(u.get("id")) == str(item_id):
            return str(u.get("unique_scope") or "save")
    it = (reg.items or {}).get(str(item_id)) or {}
    return str(it.get("unique_scope") or "save")


def can_grant_unique(
    player: Mapping[str, Any],
    reg: DataRegistry,
    item_id: str,
) -> bool:
    if unique_owned(player, item_id):
        return False
    scope = unique_scope_of(reg, item_id)
    if scope == "world":
        wid = str(player.get("world_id") or "default")
        pid = str(player.get("id") or "")
        if is_unique_world_claimed(wid, item_id, except_player_id=pid):
            return False
    return True


def grant_unit_unique(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    preferred_id: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """
    Grant one available unit unique or echo_shard.
    Returns (item_id_granted, soft lines for open_chest).
    """
    from game.domain.equipment import add_item

    ensure_chest_state(player)
    defs = unit_unique_defs(reg)
    candidates: List[str] = []
    for u in defs:
        iid = str(u.get("id") or "")
        if not iid or iid not in (reg.items or {}):
            continue
        if can_grant_unique(player, reg, iid):
            candidates.append(iid)
    if preferred_id and preferred_id in candidates:
        iid = preferred_id
    elif candidates:
        iid = str(rng.choice(candidates))
    else:
        iid = "echo_shard" if "echo_shard" in (reg.items or {}) else ""
        if not iid:
            return "", []
        shown = add_item(player, iid, reg)
        return iid, [f" · {shown}  「เงาเคยถูกครอบครองแล้ว」"]

    scope = unique_scope_of(reg, iid)
    if scope == "world":
        wid = str(player.get("world_id") or "default")
        if not claim_unique_world(wid, iid, player):
            shown = add_item(player, "echo_shard", reg) if "echo_shard" in (reg.items or {}) else ""
            return "echo_shard", [f" · {shown}  「เงาโลกนี้มีเจ้าของแล้ว」"] if shown else []

    shown = add_item(player, iid, reg, rarity="rare")
    mark_unique_owned(player, iid)
    lines = [f" · {shown}", " 「ของชิ้นนี้… เหมือนมีเพียงหนึ่งในเส้นทางนี้」"]
    if scope == "world":
        lines.append(" 「…ทั่วทั้งโลกนี้ อาจมีเพียงชิ้นเดียว」")
    return iid, lines


# ── L3: quest / board reward chests ──


def normalize_chest_rank(rank: Any) -> str:
    r = str(rank or "common").strip().lower()
    aliases = {
        "chest_common": "common",
        "chest_uncommon": "uncommon",
        "chest_rare": "rare",
        "chest_s": "s",
        "chest_ss": "ss",
        "chest_sss": "sss",
        "chest_unit": "unit",
        "ธรรมดา": "common",
        "สูง": "uncommon",
        "หายาก": "rare",
        "พันธะ": "unit",
    }
    return aliases.get(r, r)


def board_rank_to_chest(board_rank: str) -> Optional[str]:
    """Soft map mission board rank → sealed chest rank (none for low ranks)."""
    m = {
        "F": None,
        "E": None,
        "D": None,
        "C": "common",
        "B": "uncommon",
        "A": "rare",
        "S": "s",
        "SS": "ss",
        "SSS": "sss",
    }
    return m.get(str(board_rank or "").upper())


def apply_hidden_flags(
    player: MutableMapping[str, Any],
    flag_map: Mapping[str, Any],
) -> List[str]:
    """Set soft hidden flags (never shown as % / checklist)."""
    ensure_chest_state(player)
    flags = dict(player.get("flags") or {})
    lines: List[str] = []
    for k, v in (flag_map or {}).items():
        flags[str(k)] = v
    player["flags"] = flags
    if flag_map:
        lines.append("  …บางอย่างในเส้นทางเปลี่ยนไป (มองไม่เห็นชัด)")
    return lines


def grant_reward_chests(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    *,
    reward_spec: Any = None,
    chance: Optional[float] = None,
    board_rank: Optional[str] = None,
    seed_salt: str = "",
    soft_prefix: str = "  ",
) -> List[str]:
    """
    L3: grant sealed chest(s) from quest/mission reward fields.
    reward_spec: rank str | list of ranks | dict {rank, chance}
    Never shows percentages.
    """
    ensure_chest_state(player)
    lines: List[str] = []
    ranks: List[str] = []
    base_chance = 1.0 if chance is None else float(chance)

    if reward_spec is None and board_rank:
        # soft default for high board ranks: roll chance, not guaranteed
        mapped = board_rank_to_chest(board_rank)
        if not mapped:
            return []
        # chance scales with board rank (hidden)
        rank_u = str(board_rank).upper()
        default_ch = {
            "C": 0.22,
            "B": 0.35,
            "A": 0.48,
            "S": 0.55,
            "SS": 0.62,
            "SSS": 0.72,
        }.get(rank_u, 0.0)
        if default_ch <= 0:
            return []
        noise = _player_noise(player, salt=f"board|{board_rank}|{seed_salt}")
        ch = min(0.9, default_ch * noise)
        rng = random.Random(
            int(hashlib.sha256(f"{player.get('id')}|{seed_salt}|{board_rank}".encode()).hexdigest()[:8], 16)
            ^ int(player.get("chest_opens") or 0)
        )
        if rng.random() > ch:
            return []
        ranks = [mapped]
    elif reward_spec is None:
        return []
    elif isinstance(reward_spec, dict):
        r = reward_spec.get("rank") or reward_spec.get("chest") or reward_spec.get("id")
        if r:
            ranks = [normalize_chest_rank(r)]
        if reward_spec.get("chance") is not None:
            base_chance = float(reward_spec["chance"])
    elif isinstance(reward_spec, (list, tuple)):
        ranks = [normalize_chest_rank(x) for x in reward_spec]
    else:
        ranks = [normalize_chest_rank(reward_spec)]

    if not ranks:
        return []

    noise = _player_noise(player, salt=f"reward|{seed_salt}|{','.join(ranks)}")
    ch = min(1.0, max(0.0, base_chance * (noise if base_chance < 1.0 else 1.0)))
    if base_chance < 1.0:
        rng = random.Random(
            int(hashlib.sha256(f"ch|{player.get('id')}|{seed_salt}".encode()).hexdigest()[:8], 16)
            ^ int(time.time()) % 9973
        )
        # use deterministic salt for tests: prefer player latent
        seed = int(player.get("latent_seed") or 1) + int(player.get("level") or 1) * 17
        seed ^= int(hashlib.md5(seed_salt.encode()).hexdigest()[:6], 16)
        rng = random.Random(seed)
        if rng.random() > ch:
            return []

    for rank in ranks:
        if rank not in set(all_rank_ids(reg) or []) and rank not in (
            "common",
            "uncommon",
            "rare",
            "s",
            "ss",
            "sss",
            "unit",
        ):
            rank = "common"
        ok, shown = grant_sealed_chest(player, reg, rank)
        if ok:
            rd = rank_def(reg, rank)
            label = str(rd.get("label") or rank)
            lines.append(f"{soft_prefix}ได้{label} (ปิดผนึก)")
            lines.append(f"{soft_prefix}เก็บ {shown} — เปิดจากกระเป๋าหมวดหีบ")
        else:
            lines.append(f"{soft_prefix}…เงาหีบเลือนหาย")
    return lines


def apply_reward_block(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    block: Mapping[str, Any],
    *,
    seed_salt: str = "",
) -> List[str]:
    """
    Apply L3 fields from a quest or mission dict:
      reward_chest / reward_chests
      reward_chest_chance
      set_flags / flags_on_complete
    """
    lines: List[str] = []
    flags = block.get("set_flags") or block.get("flags_on_complete") or {}
    if isinstance(flags, dict) and flags:
        lines.extend(apply_hidden_flags(player, flags))

    chest_spec = block.get("reward_chest")
    if chest_spec is None:
        chest_spec = block.get("reward_chests")
    chance = block.get("reward_chest_chance")
    if chest_spec is not None:
        lines.extend(
            grant_reward_chests(
                player,
                reg,
                reward_spec=chest_spec,
                chance=float(chance) if chance is not None else None,
                seed_salt=seed_salt or str(block.get("id") or "reward"),
            )
        )
    return lines


def open_chest(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    rank_id: str,
) -> List[str]:
    """
    Open a chest rank; grant items; return soft narrative lines.
    """
    from game.domain.equipment import add_item

    ensure_chest_state(player)
    # L4: rare SSS → unit path (hidden)
    effective_rank = rank_id
    if rank_id == "sss":
        src = (_chests_cfg(reg).get("sources") or {})
        u_ch = float(src.get("unit_chance_on_sss_open") or 0)
        if u_ch > 0 and rng.random() < u_ch:
            effective_rank = "unit"

    rd = rank_def(reg, effective_rank)
    label = str(rd.get("label") or f"หีบ · {effective_rank}")
    sym = str(rd.get("symbol") or "□")
    rname = str(rd.get("name") or effective_rank)
    # Proportional open card (caller may render_box)
    lines: List[str] = [
        " เปิดหีบ",
        "---",
        f"  {sym}  {label}",
        f"  แรงก์  {rname}",
    ]
    if effective_rank == "unit" and rank_id != "unit":
        lines.append("---")
        lines.append(" 「ผนึกด้านใน… ไม่ใช่หีบธรรมดา」")

    pools = (_chests_cfg(reg).get("pools") or {}).get("buckets") or {}
    rmin = int(rd.get("rolls_min") or 1)
    rmax = max(rmin, int(rd.get("rolls_max") or 1))
    n_rolls = rng.randint(rmin, rmax)
    bias = dict(rd.get("rarity_bias") or {})
    buckets_w = dict(rd.get("bucket_weights") or {"material": 1})

    loot_lines: List[str] = []
    granted = 0
    high_only = True
    for _ in range(n_rolls):
        bucket = _weighted_pick(buckets_w, rng)
        if bucket == "soft_empty":
            bucket = "soft_empty"
        pool = list(pools.get(bucket) or pools.get("material") or ["upgrade_mat"])
        pool = [str(x) for x in pool if str(x) in (reg.items or {})]
        if not pool:
            pool = ["upgrade_mat"] if "upgrade_mat" in (reg.items or {}) else []
        if not pool:
            continue

        if bucket == "unit_unique" or effective_rank == "unit":
            _iid, ulines = grant_unit_unique(player, reg, rng)
            for ul in ulines:
                s = str(ul).strip()
                if s:
                    loot_lines.append(s if s.startswith("·") else f" · {s}")
            if _iid:
                granted += 1
            high_only = False
            continue

        iid = str(rng.choice(pool))
        rid = _roll_rarity_biased(reg, rng, bias)
        it = reg.items.get(iid) or {}
        if str(it.get("kind")) == "material" and rng.random() < 0.6:
            rid = "common"
        if str(it.get("kind")) == "consumable" and rng.random() < 0.5:
            rid = rid if rid in ("common", "uncommon") else "common"

        shown = add_item(player, iid, reg, rarity=rid)
        if shown and "ไม่พบ" not in str(shown):
            loot_lines.append(f" · {shown}")
            granted += 1
            if rid in ("common",) or bucket in ("material", "food", "heal", "soft_empty"):
                high_only = False
            if rid not in ("sacred", "legendary", "divine", "mythic", "rare"):
                high_only = False

    if granted == 0:
        if "city_bread" in (reg.items or {}):
            shown = add_item(player, "city_bread", reg)
            loot_lines.append(f" · {shown}")
            high_only = False
        elif "potion_hp_small" in (reg.items or {}):
            shown = add_item(player, "potion_hp_small", reg)
            loot_lines.append(f" · {shown}")

    player["chest_opens"] = int(player.get("chest_opens") or 0) + 1

    lines.append("---")
    lines.append(" ของที่ได้")
    if loot_lines:
        lines.extend(loot_lines)
    else:
        lines.append(" · (ว่าง — เงาไม่ให้สิ่งใด)")

    # soft flavor
    lines.append("---")
    lines.append(" โทน")
    if effective_rank in ("ss", "sss") and not high_only and granted > 0:
        if rng.random() < 0.55:
            lines.append("  「กล่องใหญ่… ของข้างในเรียบง่าย — โชคยังไม่ถึง」")
        else:
            lines.append("  「ยังไม่ใช่สิ่งที่เงาสัญญา — แต่ก็ใช้ได้」")
    elif effective_rank in ("s", "ss", "sss", "unit") and high_only:
        lines.append("  「เงาสั่น — ของนี้ไม่ธรรมดา」")
    else:
        lines.append("  「ยังไม่ใช่สิ่งที่เงาสัญญา — แต่ก็ใช้ได้」")

    return lines


def _roll_rarity_biased(
    reg: DataRegistry,
    rng: random.Random,
    bias: Mapping[str, float],
) -> str:
    from game.domain.rarity import all_tiers

    tiers = all_tiers(reg)
    ids = []
    weights = []
    for t in tiers:
        tid = str(t.get("id"))
        w = float(t.get("drop_weight") or 1) * float(bias.get(tid) or 0.0)
        # if bias missing key, use small weight for known mid tiers
        if tid not in bias:
            w = float(t.get("drop_weight") or 1) * 0.15
        if w <= 0:
            continue
        ids.append(tid)
        weights.append(w)
    if not ids:
        return "common"
    total = sum(weights)
    r = rng.random() * total
    acc = 0.0
    for tid, w in zip(ids, weights):
        acc += w
        if r <= acc:
            return tid
    return ids[-1]


def try_drop_and_grant_chest(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    source: str,
    mon: Optional[Mapping[str, Any]] = None,
    first_clear: bool = False,
    auto_open: bool = False,
) -> List[str]:
    """
    Decide drop, grant sealed chest (or auto-open). Soft lines for combat log.
    """
    mon = mon or {}
    note_kill_for_farm(player, str(mon.get("id") or "x"))
    rank = decide_chest_drop(
        player, reg, rng, source=source, mon=mon, first_clear=first_clear
    )
    if not rank:
        return []
    rd = rank_def(reg, rank)
    label = str(rd.get("label") or rank)
    lines = [f"「เงาแตก — กล่องตกลงมา」", f"พบ{label}"]
    if auto_open:
        lines.extend(open_chest(player, reg, rng, rank))
    else:
        ok, shown = grant_sealed_chest(player, reg, rank)
        if ok:
            lines.append(f"เก็บ {shown} เข้ากระเป๋า (หมวดหีบ · เปิดจากกระเป๋า)")
        else:
            lines.extend(open_chest(player, reg, rng, rank))
    return lines


def infer_combat_source(mon: Mapping[str, Any]) -> str:
    if mon.get("dungeon_boss") or (mon.get("boss") and mon.get("dungeon_modded")):
        return "dungeon_boss"
    if mon.get("boss"):
        return "area_boss"
    if mon.get("elite") or mon.get("named"):
        return "elite_monster"
    return "normal_monster"
