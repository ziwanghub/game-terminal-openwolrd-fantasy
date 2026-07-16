"""
WO-Shop-3/4 — Shop Experience + Reputation Economy.

Soft flavor dialogue, per-shop reputation (0–100), dynamic pricing,
stock unlock by rep, best-buyer hints, category order by tone.
Never show raw % or raw rep numbers in player-facing flavor.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# ── Reputation (WO-Shop-4) ──────────────────────────────────────────────
SHOP_REP_MIN = 0
SHOP_REP_MAX = 100
SHOP_REP_START = 25  # band 20–30 start
SHOP_REP_START_JITTER = 5  # start in 20–30
REP_UNLOCK_UNCOMMON = 35  # uncommon stock soft-open
REP_UNLOCK_RARE = 60  # rare+ stock opens more
REP_BUY_MAX_DISC = 0.12  # buy cheaper up to -12%
REP_SELL_MAX_BONUS = 0.08  # sell pays up to +8%
DAY_WAVE_AMP = 0.02  # soft day wave (keeps total economy sane)

# Known system shops (seed rep)
KNOWN_SHOP_IDS: Tuple[str, ...] = (
    "traveling_merchant",
    "city_armory",
    "rare_exchange",
    "celestial_bazaar",
    "infernal_market",
    "legend_pavilion",
)

# Category order by shop identity (first = featured)
SHOP_CAT_PRIORITY: Dict[str, Tuple[str, ...]] = {
    "traveling_merchant": ("healing", "food", "material", "equipment", "other", "card"),
    "city_armory": ("equipment", "material", "other", "healing", "food", "card"),
    "rare_exchange": ("material", "other", "healing", "equipment", "food", "card"),
    "celestial_bazaar": ("healing", "food", "other", "material", "equipment", "card"),
    "infernal_market": ("healing", "material", "other", "equipment", "food", "card"),
    "legend_pavilion": ("material", "healing", "other", "equipment", "food", "card"),
}

# Soft default greetings if yaml omits (neutral band)
SHOP_GREET_DEFAULTS: Dict[str, List[str]] = {
    "traveling_merchant": [
        "「ลุยทางไกลมานาน — ของใช้ครบในรถเร่」",
        "「ยา เสบียง น้ำชา… เลือกได้ แล้วไปต่อทาง」",
        "「ถนนยังอีกยาว ของพกติดตัวไว้ดีกว่า」",
    ],
    "city_armory": [
        "「ที่นี่เด่นเรื่องเกียร์เหล็ก — ลับคม ซ่อมเกราะ」",
        "「เสียงทั่งดัง — หาอาวุธและวัสดุอัปที่นี่」",
        "「คมดีกว่ามัว — เลือกลองถือก่อนซื้อ」",
    ],
    "rare_exchange": [
        "「ผลึก ม้วน mat หายาก — ไม่ขายเกียร์」",
        "「ของจากสนาม เอามาแลกที่นี่ได้คุ้มกว่า」",
        "「ผงผลึกและม้วนกัน… ชั้นกลางของตลาด」",
    ],
    "celestial_bazaar": [
        "「แสงบาง — เครื่องรางและพรแผ่ว (เงินสวรรค์)」",
        "「ไม่ขายคมดาบ — ขายความสงบและ blessing」",
        "「ลมฟ้าแผ่ว… เลือกของอุ่นใจ」",
    ],
    "infernal_market": [
        "「เถ้าและสัญญา — ระวังมือ (เงินนรก)」",
        "「ที่นี่แลกไฟมืดเบา — ไม่ใช่ร้านยาทั่วไป」",
        "「ควันข้น… สัญญานรกยังมีขาย」",
    ],
    "legend_pavilion": [
        "「ศาลาเงียบ — รับซื้อของแรงก์สูง · ตำนานเบา」",
        "「ของตำนานวางน้อย — ส่วนใหญ่รับซื้อ」",
        "「เสียงก้องแผ่ว… ดู stock เบา แล้วค่อยขายของแรง」",
    ],
}

# WO-Shop-4: cold / warm dialogue overlays by rep band
SHOP_GREET_COLD: Dict[str, List[str]] = {
    "traveling_merchant": [
        "「…ของมี — ซื้อก็ซื้อ ไม่ซื้อก็ไป」",
        "「ยังไม่คุ้นหน้า — เลือกรวดเร็ว」",
    ],
    "city_armory": [
        "「ทั่งไม่ว่าง — พูดสั้น ๆ」",
        "「ลูกค้าใหม่… ดูของได้ แต่ราคาปกตินะ」",
    ],
    "rare_exchange": [
        "「mat ดี ๆ ไม่โชว์คนแปลกหน้า」",
        "「เงียบ ๆ — เลือกแล้วจ่าย」",
    ],
    "celestial_bazaar": [
        "「แสงยังไม่เปิดเต็ม — เลือกเบา ๆ」",
        "「ผู้มาใหม่… พรยังแผ่ว」",
    ],
    "infernal_market": [
        "「ควันข้น — อย่าถ่วงเวลา」",
        "「สัญญายังไม่ไว้ใจคุณ」",
    ],
    "legend_pavilion": [
        "「ศาลารับคนคุ้น — วันนี้ดูเฉย ๆ」",
        "「ของตำนานไม่โชว์ง่าย」",
    ],
}

SHOP_GREET_KNOWN: Dict[str, List[str]] = {
    "traveling_merchant": [
        "「คุ้นหน้าแล้ว — เสบียงชุดกลางมี」",
        "「มาบ่อยขึ้น… ของใช้จัดให้ครบ」",
    ],
    "city_armory": [
        "「มือเริ่มจำค้อน — ดูเกียร์ได้เต็มขึ้น」",
        "「คุ้นโรงตีแล้ว — วัสดุอัปเปิดบ้าง」",
    ],
    "rare_exchange": [
        "「รู้จักชั้นกลาง — ผลึกโชว์ได้บางส่วน」",
        "「คุ้นตลาด mat แล้ว — เลือกช้า ๆ」",
    ],
    "celestial_bazaar": [
        "「แสงจำคุณได้ครึ่งหนึ่ง — blessing แผ่ว」",
        "「คุ้นลานฟ้า — โคมยังอุ่น」",
    ],
    "infernal_market": [
        "「ควันจำกลิ่นคุณ — เลือกสัญญาได้」",
        "「คุ้นตลาดนรก — อย่าเพิ่งวางใจเต็ม」",
    ],
    "legend_pavilion": [
        "「ศาลาเริ่มจำเงา — stock เบายังเปิด」",
        "「คุ้นเสียงก้อง… รับซื้อแรงขึ้นนิด」",
    ],
}

SHOP_GREET_WARM: Dict[str, List[str]] = {
    "traveling_merchant": [
        "「โอ้ ลูกค้าประจำทาง! ของดีคัดไว้ให้」",
        "「กลับมาอีกแล้ว — เสบียงชุดพิเศษมีนะ」",
    ],
    "city_armory": [
        "「มือคุ้นทั่ง — เอาของชั้นดีให้เลือก」",
        "「เพื่อนโรงตี! วันนี้ลับคมให้พิเศษ」",
    ],
    "rare_exchange": [
        "「รู้จักกันแล้ว — เปิดชั้น mat หายากให้ดู」",
        "「ของผลึกชุดดี เก็บไว้ให้คุณ」",
    ],
    "celestial_bazaar": [
        "「แสงต้อนรับคุ้น — blessing อุ่นขึ้น」",
        "「ใบหน้าคุ้นในตลาดฟ้า… ยินดี」",
    ],
    "infernal_market": [
        "「ควันอ่อนลงเมื่อคุณมา — เลือกสัญญาได้」",
        "「มือคุ้นเถ้า — เปิดของมืดเบาให้」",
    ],
    "legend_pavilion": [
        "「ศาลาจำคุณได้ — stock เบาเปิดให้」",
        "「เงาคุ้น… รับซื้อของแรงให้ดีขึ้น」",
    ],
}

# WO-Shop-6: friend band (rep 80+) — VIP soft
SHOP_GREET_FRIEND: Dict[str, List[str]] = {
    "traveling_merchant": [
        "「ลูกค้าประจำ! ชาและเสบียงชุดใจดีจัดไว้」",
        "「ทางร่วมกันมานาน — ราคาและของอุ่นเป็นพิเศษ」",
    ],
    "city_armory": [
        "「ลูกค้าประจำโรงตี — เกียร์ชั้นดีเปิดกว้าง」",
        "「ทั่งจำมือคุณ — วันนี้ลับคมฟรีแผ่ว (soft)」",
    ],
    "rare_exchange": [
        "「ลูกค้าประจำตลาด mat — ชั้นหายากเปิดเต็ม」",
        "「ผลึกสำหรับคุณคัดแล้ว — ยินดีต้อนรับ」",
    ],
    "celestial_bazaar": [
        "「ลูกค้าประจำตลาดฟ้า — blessing อุ่นชัด」",
        "「แสงจำชื่อเงาคุณ — เลือกของใจได้」",
    ],
    "infernal_market": [
        "「ลูกค้าประจำเถ้า — สัญญาชั้นดีมี」",
        "「ควันยิ้มเมื่อคุณมา — ระวังมือเหมือนเดิม」",
    ],
    "legend_pavilion": [
        "「ลูกค้าประจำศาลา — รับเรลิกเบาและของตำนาน」",
        "「ก้องจำคุณ — ราคาแรงก์สูงใจดีขึ้น」",
    ],
}

SHOP_SPECIALTY_HINTS: Dict[str, str] = {
    "traveling_merchant": "ที่นี่เด่นเรื่องยา·เสบียงเดินทาง",
    "city_armory": "ที่นี่เด่นเรื่องเกียร์เหล็กและวัสดุอัป",
    "rare_exchange": "ที่นี่รับ mat/ผลึก/ม้วนดี — ไม่ขายเกียร์",
    "celestial_bazaar": "ที่นี่เด่นเรื่องเครื่องราง·พร (เงินสวรรค์)",
    "infernal_market": "ที่นี่เด่นเรื่องสัญญา·เถ้าสุญญะ (เงินนรก)",
    "legend_pavilion": "ที่นี่รับซื้อแรงก์สูง · stock ตำนานเบา",
}

# Which shop is soft-best for selling certain mat families
BEST_SELL_HINTS: Dict[str, str] = {
    "upgrade_mat": "city_armory",
    "rare_mat": "rare_exchange",
    "shop_armory_whetstone": "city_armory",
    "shop_armory_temper_oil": "city_armory",
    "shop_armory_rivet_pack": "city_armory",
    "crystal_dust": "rare_exchange",
    "cave_crystal_shard": "rare_exchange",
    "prism_shard": "rare_exchange",
    "shop_rare_crystal_lens": "rare_exchange",
    "shop_rare_prism_vial": "rare_exchange",
    "scroll_guard_level": "rare_exchange",
    "scroll_guard_break": "rare_exchange",
    "void_ash": "infernal_market",
    "void_filament": "infernal_market",
    "shop_infernal_void_token": "infernal_market",
    "shop_legend_memory_fragment": "legend_pavilion",
    "shop_legend_echo_thread": "legend_pavilion",
    "goblin_scrap": "traveling_merchant",
    "rat_tail": "traveling_merchant",
    "stone_chip": "traveling_merchant",
}

# Soft floors as fraction of buy-ref
JUNK_SOFT_FLOOR_RATIO = 0.18
MAT_SOFT_FLOOR_RATIO = 0.22
# Overall mult clamp (rep + day + bias) — buy can go to ~0.86, sell to ~1.12
DYNAMIC_CLAMP_BUY = (0.86, 1.08)
DYNAMIC_CLAMP_SELL = (0.92, 1.12)
# legacy alias for tests that import DYNAMIC_CLAMP
DYNAMIC_CLAMP = (0.86, 1.12)


def shop_id_of(shop: Optional[Mapping[str, Any]], fallback: str = "") -> str:
    if not shop:
        return str(fallback or "")
    return str(shop.get("id") or fallback or "")


def game_day_index(player: Mapping[str, Any]) -> int:
    """Soft day from time_units (20 ticks ≈ 1 day)."""
    tu = int(player.get("time_units") or player.get("auto_ticks") or 0)
    return max(0, tu // 20)


def _start_rep_for(shop_id: str) -> int:
    """Deterministic start in 20–30 band."""
    h = abs(hash(str(shop_id) or "shop")) % (SHOP_REP_START_JITTER * 2 + 1)
    return int(SHOP_REP_START - SHOP_REP_START_JITTER + h)


def ensure_shop_rep(player: MutableMapping[str, Any], shop_ids: Optional[Sequence[str]] = None) -> Dict[str, int]:
    """
    Ensure shop_rep dict exists; seed missing shops at 20–30 start.
    Returns the dict (also stored on player).
    """
    reps = dict(player.get("shop_rep") or {})
    # migrate tiny Shop-3 caps (≤30) only if value looks like old scale and never seeded
    # keep existing values if already set
    ids = list(shop_ids or KNOWN_SHOP_IDS)
    for sid in ids:
        if not sid:
            continue
        if sid not in reps:
            reps[sid] = _start_rep_for(sid)
        else:
            reps[sid] = int(max(SHOP_REP_MIN, min(SHOP_REP_MAX, int(reps[sid]))))
    player["shop_rep"] = reps
    return reps


def get_shop_rep(player: Mapping[str, Any], shop_id: str = "") -> int:
    """Per-shop reputation 0–100 (read-only safe)."""
    sid = str(shop_id or "")
    reps = player.get("shop_rep") or {}
    if not isinstance(reps, dict):
        return _start_rep_for(sid)
    if sid and sid in reps:
        return int(max(SHOP_REP_MIN, min(SHOP_REP_MAX, int(reps[sid]))))
    if sid:
        return _start_rep_for(sid)
    return SHOP_REP_START


def shop_rep_band(rep: int) -> str:
    """cold | cool | known | warm | friend — soft only."""
    r = int(rep)
    if r < 25:
        return "cold"
    if r < 40:
        return "cool"
    if r < 60:
        return "known"
    if r < 80:
        return "warm"
    return "friend"


def shop_rep_soft_label(rep: int) -> str:
    """Player-facing relationship word — no number."""
    return {
        "cold": "แปลกหน้า",
        "cool": "รู้จักเล็กน้อย",
        "known": "คุ้นเคย",
        "warm": "ไว้ใจ",
        "friend": "ลูกค้าใจดี",
    }.get(shop_rep_band(rep), "รู้จัก")


def shop_rep_score(player: Mapping[str, Any], shop_id: str = "") -> int:
    """
    Back-compat 0–40-ish score used by older paths.
    Prefer get_shop_rep for Shop-4 economy.
    """
    local = get_shop_rep(player, shop_id)
    help_rep = int(player.get("help_rep") or 0)
    # blend lightly so help_rep still matters, but shop_rep is primary
    blended = int(local * 0.4 + min(40, help_rep // 3))
    return min(40, blended)


def bump_shop_rep(
    player: MutableMapping[str, Any],
    shop_id: str,
    *,
    amount: int = 1,
    reason: str = "trade",
) -> int:
    """
    Add reputation for a shop. Returns new value.
    reasons: buy · sell_mat · sell · quest · trade
    """
    if not shop_id:
        return 0
    ensure_shop_rep(player, [shop_id])
    reps = dict(player.get("shop_rep") or {})
    cur = int(reps.get(shop_id) or _start_rep_for(shop_id))
    # soft gain scaling: harder near cap
    amt = max(0, int(amount))
    if cur >= 90:
        amt = max(0, (amt + 1) // 2)
    if reason == "sell_mat":
        amt = max(amt, 1)
    if reason == "quest":
        amt = max(amt, 3)
    if reason == "buy":
        amt = max(1, amt)
    new = int(max(SHOP_REP_MIN, min(SHOP_REP_MAX, cur + amt)))
    reps[shop_id] = new
    player["shop_rep"] = reps
    return new


def grant_shop_rep_quest(
    player: MutableMapping[str, Any],
    shop_id: str,
    *,
    amount: int = 5,
) -> List[str]:
    """Hook for quests related to a shop — soft notes, no raw numbers."""
    if not shop_id:
        return []
    before = get_shop_rep(player, shop_id)
    after = bump_shop_rep(player, shop_id, amount=amount, reason="quest")
    if after <= before:
        return []
    name = shop_id
    return [f" ความคุ้นกับร้านดีขึ้นแผ่ว 〔{shop_rep_soft_label(after)}〕"]


def _grade_letter(player: Mapping[str, Any]) -> str:
    """Player grade letter if revealed, else C-neutral."""
    try:
        from game.domain.stat_grades import grade_revealed

        if not grade_revealed(player):
            return "C"
        return str(player.get("player_grade") or "C").upper()
    except Exception:
        return str(player.get("player_grade") or "C").upper() or "C"


def grade_shop_price_bias(player: Mapping[str, Any], *, side: str = "buy") -> float:
    """
    WO-Shop-6: Grade soft bias on shop prices.
    High grade buys cheaper; low grade soft surcharge. Clamp ±0.04.
    """
    order = ("F", "E", "D", "C", "B", "A", "S", "SS", "SSS")
    g = _grade_letter(player)
    idx = order.index(g) if g in order else 4
    t = (idx / max(1, len(order) - 1)) * 2.0 - 1.0
    if side == "buy":
        return max(-0.04, min(0.04, -0.035 * t))
    return max(-0.03, min(0.03, 0.025 * t))


def dynamic_price_mult(
    player: Mapping[str, Any],
    shop: Optional[Mapping[str, Any]] = None,
    *,
    side: str = "buy",
    shop_id: str = "",
) -> float:
    """
    Dynamic mult for buy/sell.
    WO-Shop-4: rep primary — buy up to -12%, sell up to +8%.
    WO-Shop-6: + grade soft bias.
    Day wave + shop bias soft. Clamped separately per side.
    """
    sid = shop_id_of(shop, shop_id)
    day = game_day_index(player)
    day_wave = DAY_WAVE_AMP * math.sin((day % 7) * (math.pi / 3.5))
    rep = get_shop_rep(player, sid)
    rep_n = max(0.0, min(1.0, rep / float(SHOP_REP_MAX)))
    if side == "buy":
        rep_adj = -REP_BUY_MAX_DISC * rep_n
        lo, hi = DYNAMIC_CLAMP_BUY
    else:
        rep_adj = REP_SELL_MAX_BONUS * rep_n
        lo, hi = DYNAMIC_CLAMP_SELL
    bias = 0.0
    if shop:
        key = "buy_bias" if side == "buy" else "sell_bias"
        if shop.get(key) is not None:
            bias = float(shop[key])
            bias = max(-0.03, min(0.03, bias))
        else:
            if sid == "city_armory" and side == "buy":
                bias = 0.015
            elif sid == "rare_exchange" and side == "sell":
                bias = 0.02
            elif sid == "traveling_merchant" and side == "buy":
                bias = -0.01
            elif sid == "legend_pavilion" and side == "sell":
                bias = 0.01
    grade_adj = grade_shop_price_bias(player, side=side)
    mult = 1.0 + day_wave + rep_adj + bias + grade_adj
    return max(lo, min(hi, mult))


def apply_dynamic_to_price(
    price: int,
    player: Mapping[str, Any],
    shop: Optional[Mapping[str, Any]] = None,
    *,
    side: str = "buy",
    shop_id: str = "",
) -> int:
    m = dynamic_price_mult(player, shop, side=side, shop_id=shop_id)
    return max(1, int(round(int(price) * m)))


def soft_band_floor(
    buy_ref: int,
    net: int,
    *,
    band: str,
) -> int:
    """Ensure junk/mat soft floor after tax."""
    buy_ref = max(1, int(buy_ref))
    net = max(1, int(net))
    if band == "junk":
        floor = max(1, int(round(buy_ref * JUNK_SOFT_FLOOR_RATIO)))
        return max(net, floor)
    if band == "mat":
        floor = max(2, int(round(buy_ref * MAT_SOFT_FLOOR_RATIO)))
        return max(net, floor)
    return net


def stock_unlocked_for_rep(
    rarity: str,
    rep: int,
    *,
    entry: Optional[Mapping[str, Any]] = None,
    player: Optional[Mapping[str, Any]] = None,
) -> bool:
    """
    WO-Shop-4/6: gate stock by reputation (+ soft grade boost).
    - explicit entry.min_rep always wins
    - common: always
    - uncommon: rep >= 35 (S+ grade soft -8)
    - rare+: rep >= 60 (S+ grade soft -10)
    High grade + high rep → opens stock sooner than low grade.
    """
    entry = entry or {}
    if entry.get("min_rep") is not None:
        return int(rep) >= int(entry["min_rep"])
    if entry.get("always_show") or entry.get("rep_free"):
        return True
    rid = str(rarity or "common").lower()
    r = int(rep)
    # WO-Shop-6: high personal grade soft-boosts effective rep for unlock
    if player is not None:
        g = _grade_letter(player)
        if g in ("S", "SS", "SSS"):
            r += 12
        elif g in ("A", "B"):
            r += 5
        elif g in ("F", "E", "D"):
            r -= 5
    if rid in ("common", "", "junk"):
        return True
    if rid == "uncommon":
        return r >= REP_UNLOCK_UNCOMMON
    # rare, sacred, legendary, divine, mythic...
    return r >= REP_UNLOCK_RARE


def pick_greeting(
    shop: Optional[Mapping[str, Any]],
    shop_id: str = "",
    *,
    rng: Optional[random.Random] = None,
    player: Optional[Mapping[str, Any]] = None,
) -> str:
    """WO-Shop-6: full band dialogue — cold/cool/known/warm/friend."""
    sid = shop_id_of(shop, shop_id)
    rep = get_shop_rep(player or {}, sid) if player is not None else SHOP_REP_START
    band = shop_rep_band(rep)
    lines: List[str] = []
    if band in ("cold", "cool"):
        lines = list(SHOP_GREET_COLD.get(sid) or [])
    elif band == "known":
        lines = list(SHOP_GREET_KNOWN.get(sid) or SHOP_GREET_DEFAULTS.get(sid) or [])
    elif band == "warm":
        lines = list(SHOP_GREET_WARM.get(sid) or [])
    elif band == "friend":
        lines = list(SHOP_GREET_FRIEND.get(sid) or SHOP_GREET_WARM.get(sid) or [])
    # yaml greetings as fill / mix for known+
    if shop:
        raw = shop.get("greetings") or shop.get("dialogue") or shop.get("lines")
        yaml_lines: List[str] = []
        if isinstance(raw, str) and raw.strip():
            yaml_lines = [raw.strip()]
        elif isinstance(raw, (list, tuple)):
            yaml_lines = [str(x).strip() for x in raw if str(x).strip()]
        if not lines:
            lines = yaml_lines
        elif yaml_lines and band in ("known", "warm", "friend"):
            lines = lines + yaml_lines
    if not lines:
        lines = list(SHOP_GREET_DEFAULTS.get(sid) or ["「ยินดีต้อนรับ」"])
    if rng is None:
        seed = abs(hash(sid)) + int((player or {}).get("time_units") or 0) + rep
        rng = random.Random(seed % 99991)
    return lines[rng.randrange(len(lines))]


def specialty_hint(shop: Optional[Mapping[str, Any]], shop_id: str = "") -> str:
    if shop:
        for k in ("specialty_hint", "hint", "deals_in"):
            if shop.get(k):
                return str(shop[k]).strip()
    sid = shop_id_of(shop, shop_id)
    return SHOP_SPECIALTY_HINTS.get(sid, "ร้านระบบ — ของใช้ทั่วไป")


def rep_progress_hint(player: Mapping[str, Any], shop_id: str = "") -> str:
    """Soft hint without numbers — how to improve standing / locked stock."""
    rep = get_shop_rep(player, shop_id)
    band = shop_rep_band(rep)
    if band in ("cold", "cool"):
        return "ร้านนี้รับซื้อ/ราคาดีขึ้นถ้าคุณมาบ่อยหรือช่วยงานที่เกี่ยวข้อง"
    if band == "known":
        if rep < REP_UNLOCK_RARE:
            return "คุ้นขึ้นอีกนิด อาจเปิดชั้นของหายากให้ดู"
        return "ความคุ้นดี — ราคาเป็นมิตรขึ้นแผ่ว"
    if band == "warm":
        return "ร้านไว้ใจคุณ — ของชั้นดีเปิดมากขึ้น"
    return "ลูกค้าใจดี — ราคาและ stock เปิดกว้าง (soft)"


def category_order_for_shop(
    shop_id: str = "", shop: Optional[Mapping[str, Any]] = None
) -> Tuple[str, ...]:
    sid = shop_id_of(shop, shop_id)
    if shop and shop.get("cat_order"):
        raw = shop["cat_order"]
        if isinstance(raw, (list, tuple)) and raw:
            return tuple(str(x) for x in raw)
    return SHOP_CAT_PRIORITY.get(
        sid, ("food", "healing", "equipment", "material", "card", "other")
    )


def best_buyer_shop_id(
    item_id: str,
    *,
    item: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    """Which shop soft-recommends for selling this id (mat/junk families)."""
    iid = str(item_id or "")
    if iid in BEST_SELL_HINTS:
        return BEST_SELL_HINTS[iid]
    it = dict(item or {})
    tags = it.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tag_l = {str(t).lower() for t in tags}
    blob = iid.lower() + " " + " ".join(tag_l)
    if "crystal" in blob or "prism" in blob or "scroll" in blob:
        return "rare_exchange"
    if "armory" in blob or "upgrade" in blob or iid in ("upgrade_mat", "rare_mat"):
        return "city_armory"
    if "legend" in blob:
        return "legend_pavilion"
    if "void" in blob or "hell" in blob or "infernal" in blob:
        return "infernal_market"
    if "scrap" in blob or "junk" in blob or "chip" in blob:
        return "traveling_merchant"
    if str(it.get("kind") or "").lower() in ("material", "mat") or "mat" in iid.lower():
        return "rare_exchange"
    return None


def best_buyer_soft_line(
    item_id: str,
    reg: Any = None,
    *,
    current_shop_id: str = "",
    item: Optional[Mapping[str, Any]] = None,
) -> str:
    """Player-facing soft hint — no prices."""
    bid = best_buyer_shop_id(item_id, item=item)
    if not bid:
        return ""
    name = bid
    if reg is not None:
        try:
            sdef = (getattr(reg, "shops", None) or {}).get(bid) or {}
            name = str(sdef.get("name") or bid)
        except Exception:
            pass
    if current_shop_id and current_shop_id == bid:
        return f"ร้านนี้รับซื้อ「{name}」แนวนี้ได้ดี"
    return f"รับซื้อดีที่สุดที่「{name}」(soft)"


def soft_market_day_line(player: Mapping[str, Any]) -> str:
    """Optional hub flavor about market day feel — no numbers."""
    day = game_day_index(player) % 7
    bands = (
        "ตลาดเงียบ — ราคารู้สึกนิ่ง",
        "ลมซื้อขายแผ่ว — ของบางชิ้นอุ่น",
        "วันคึก — ราคาขยับแผ่ว",
        "วันกลาง — ซื้อขายปกติ",
        "ตลาดหนา — รับซื้อ mat รู้สึกดีขึ้นนิด",
        "เย็นตลาด — เสบียงเด่น",
        "วันพัก — ร้านพูดน้อย ราคาคง",
    )
    return bands[day]


# ── WO-Shop-6: deep integration (Anima · Grade · Relic · Arena/Spar) ─────

RELIC_LEGEND_SELL_RATIO = 0.14  # soft buyback at legend — not dump
ARENA_SHOP_REP_GAIN = 10


def shop_anima_warmth_on_visit(
    player: MutableMapping[str, Any],
    shop_id: str,
    *,
    reg: Any = None,
) -> List[str]:
    """
    High shop rep → slight Anima warmth (Personal/Anima link).
    Throttled per shop per few time_units. No raw numbers.
    """
    sid = str(shop_id or "")
    rep = get_shop_rep(player, sid)
    if rep < 60:
        return []
    # throttle
    key = f"_shop_anima_warm_{sid}"
    last = int(player.get(key) or -999)
    tu = int(player.get("time_units") or 0)
    if tu - last < 8 and last >= 0:
        return []
    player[key] = tu
    try:
        from game.domain.stat_arch import _nudge_anima

        nudge = 0.35 if rep < 80 else 0.55
        _nudge_anima(player, nudge)
    except Exception:
        try:
            from game.domain.stat_arch import ANIMA_KEY, anima_value, ensure_stat_arch

            ensure_stat_arch(player)
            cur = float(anima_value(player))
            player[ANIMA_KEY] = max(5.0, min(99.0, cur + (0.35 if rep < 80 else 0.55)))
        except Exception:
            return []
    try:
        from game.domain.personal_system import note_anima_story

        note_anima_story(player, f"shop_warm:{sid}")
    except Exception:
        pass
    if rep >= 80:
        return [" จิตอุ่นแผ่วเมื่อร้านทัก — ลูกค้าประจำ (Anima soft)"]
    return [" จิตนิ่งขึ้นเล็กน้อยในร้านที่คุ้น (Anima soft)"]


def legend_accepts_relic_sell(shop_id: str = "", shop: Optional[Mapping[str, Any]] = None) -> bool:
    """Legend pavilion soft-accepts relic buyback (single sell, not bulk)."""
    sid = shop_id_of(shop, shop_id)
    return sid == "legend_pavilion"


def relic_legend_sell_price(
    base: int,
    player: Mapping[str, Any],
    shop: Optional[Mapping[str, Any]] = None,
    *,
    rarity: str = "legendary",
) -> int:
    """
    Soft relic buyback at legend pavilion — low ratio, rep helps a little.
    Never high enough to break economy.
    """
    buy_ref = max(1, int(base))
    rep = get_shop_rep(player, shop_id_of(shop, "legend_pavilion"))
    rep_n = rep / float(SHOP_REP_MAX)
    ratio = RELIC_LEGEND_SELL_RATIO * (1.0 + 0.25 * rep_n)  # up to ~0.175
    # rarity soft
    rk = str(rarity or "legendary").lower()
    if rk in ("divine", "mythic", "archdivine"):
        ratio *= 0.85  # even softer — not dump divine
    price = max(5, int(round(buy_ref * ratio)))
    try:
        price = apply_dynamic_to_price(
            price, player, shop, side="sell", shop_id="legend_pavilion"
        )
    except Exception:
        pass
    return max(5, price)


def on_arena_or_spar_win(
    player: MutableMapping[str, Any],
    reg: Any = None,
    *,
    source: str = "spar",
    amount: int = ARENA_SHOP_REP_GAIN,
) -> List[str]:
    """
    WO-Shop-6: Arena/spar win → soft shop fame (+rep).
    Primary: city_armory · secondary: traveling_merchant (word of road).
    Throttled so spam spar doesn't break economy.
    """
    tu = int(player.get("time_units") or 0)
    last = int(player.get("_shop_arena_rep_tu") or -999)
    if tu - last < 5 and last >= 0:
        return []
    player["_shop_arena_rep_tu"] = tu
    amt = max(5, min(12, int(amount or ARENA_SHOP_REP_GAIN)))
    notes: List[str] = []
    # armory gets most fame
    a1 = bump_shop_rep(player, "city_armory", amount=amt, reason="quest")
    notes.append(
        f" ชื่อเสียงซ้อม/ประลองแผ่ถึงโรงตี 〔{shop_rep_soft_label(a1)}〕"
    )
    # merchant hears the tale
    a2 = bump_shop_rep(
        player, "traveling_merchant", amount=max(3, amt // 2), reason="quest"
    )
    notes.append(
        f" ข่าวลือถึงรถเร่ 〔{shop_rep_soft_label(a2)}〕"
    )
    if source == "arena":
        notes.append("  (Arena soft — ไม่โชว์ตัวเลข rep)")
    else:
        notes.append("  (Spar/ประลอง soft — ชื่อร้านดีขึ้นแผ่ว)")
    try:
        from game.domain.personal_system import note_anima_story

        note_anima_story(player, f"fame_{source}")
    except Exception:
        pass
    return notes


def integration_hub_lines(
    player: Mapping[str, Any],
    shop_id: str,
) -> List[str]:
    """Extra soft hub lines for final polish (no numbers)."""
    lines: List[str] = []
    rep = get_shop_rep(player, shop_id)
    band = shop_rep_band(rep)
    g = _grade_letter(player)
    if band == "friend":
        lines.append(" ★ ลูกค้าประจำ — ราคา·stock·บทสนทนาเปิดกว้าง")
    elif band == "warm":
        lines.append(" ★ ความคุ้นดี — ของชั้นดีเริ่มโชว์")
    if g in ("S", "SS", "SSS") and rep >= 40:
        lines.append(" เกรดสูง + คุ้นร้าน — ซื้อเกียร์รู้สึกคุ้มขึ้น (soft)")
    elif g in ("F", "E", "D") and rep < 40:
        lines.append(" เกรดยังแผ่ว — คุ้นร้านจะช่วยราคา/ชั้นของได้")
    if shop_id == "legend_pavilion":
        lines.append(" ศาลา — รับซื้อเรลิกเบา (ทีละชิ้น · ไม่ bulk)")
    return lines
