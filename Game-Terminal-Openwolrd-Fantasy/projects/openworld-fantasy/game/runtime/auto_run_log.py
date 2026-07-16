"""
WO-011: Playtest Auto Run Logger + End-of-Run Summary + God compact helpers.

Lightweight — no LLM / multiplayer. Session state on player["_auto_run"].
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from game.data_load.registry import DataRegistry
from game.ports.io import IO

# Event kinds for God-readable log
KIND_EAT = "eat"
KIND_REST = "rest"
KIND_POTION = "potion"
KIND_FIGHT = "fight"
KIND_AVOID = "avoid"
KIND_NEEDS = "needs"
KIND_STOP = "stop"
KIND_PAUSE = "pause"
KIND_DECISION = "decision"
KIND_TICK = "tick"
KIND_ALERT = "alert"

MAX_EVENTS = 100

REASON_THAI = {
    "done": "ครบรอบที่ตั้งไว้",
    "stop": "ผู้เล่นหยุด",
    "user": "ผู้เล่นหยุด",
    "hp": "เลือดต่ำ / วิกฤต",
    "food": "อาหาร/หิว",
    "morale": "ขวัญ (นโยบาย retreat)",
    "time": "ครบเวลา playtest",
    "pause": "เจอเป้าเสี่ยง (รอมือ)",
    "not_in_dungeon": "ไม่อยู่ในดัน",
    "boss_lock": "ติดวงบอส",
    "left_dungeon": "ออกจากดัน",
}


def is_god_compact(player: Mapping[str, Any]) -> bool:
    prefs = player.get("ui_prefs") or {}
    if isinstance(prefs, dict) and prefs.get("god_compact"):
        return True
    return bool(player.get("playtest_god_compact"))


def set_god_compact(player: MutableMapping[str, Any], on: bool) -> None:
    prefs = dict(player.get("ui_prefs") or {})
    prefs["god_compact"] = bool(on)
    player["ui_prefs"] = prefs
    player["playtest_god_compact"] = bool(on)


def ensure_auto_run(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    raw = player.get("_auto_run")
    if isinstance(raw, dict) and raw.get("active") is not None:
        return raw  # type: ignore[return-value]
    sess: Dict[str, Any] = {
        "active": False,
        "kind": "",
        "label": "",
        "started_unix": 0.0,
        "ticks": 0,
        "max_ticks": 0,
        "max_seconds": 0,
        "eats": 0,
        "rests": 0,
        "potions": 0,
        "fights": 0,
        "avoids": 0,
        "pauses": 0,
        "events": [],
        "stop_reason": "",
        "outcome": "",
    }
    player["_auto_run"] = sess
    return sess


def start_auto_run(
    player: MutableMapping[str, Any],
    *,
    kind: str = "field",
    label: str = "",
    max_ticks: int = 0,
    max_seconds: int = 0,
) -> Dict[str, Any]:
    """Begin a tracked auto session (resets counters)."""
    money0 = int(player.get("money_world") or 0)
    heaven0 = int(player.get("money_heaven") or 0)
    hell0 = int(player.get("money_hell") or 0)
    sess: Dict[str, Any] = {
        "active": True,
        "kind": str(kind or "field"),
        "label": str(label or kind or "auto"),
        "started_unix": float(time.time()),
        "ticks": 0,
        "max_ticks": int(max_ticks or 0),
        "max_seconds": int(max_seconds or 0),
        "eats": 0,
        "rests": 0,
        "potions": 0,
        "fights": 0,
        "avoids": 0,
        "pauses": 0,
        "buys": 0,
        "sells": 0,
        "burden_unequips": 0,
        "money_start": money0,
        "heaven_start": heaven0,
        "hell_start": hell0,
        "morale_start": int((player.get("needs") or {}).get("morale") or 0),
        "events": [],
        "stop_reason": "",
        "outcome": "",
    }
    player["_auto_run"] = sess
    log_auto_event(
        player,
        KIND_DECISION,
        f"เริ่มรัน {sess['label']}"
        + (f" · ติก≤{max_ticks}" if max_ticks else "")
        + (f" · เวลา≤{max_seconds}s" if max_seconds else "")
        + f" · เงินโลก {money0}",
    )
    return sess


def bump_auto_run(player: MutableMapping[str, Any], key: str, n: int = 1) -> None:
    sess = ensure_auto_run(player)
    if not sess.get("active"):
        return
    if key == "ticks":
        sess["ticks"] = int(sess.get("ticks") or 0) + int(n)
        return
    if key in (
        "eats",
        "rests",
        "potions",
        "fights",
        "avoids",
        "pauses",
        "buys",
        "sells",
        "burden_unequips",
    ):
        sess[key] = int(sess.get(key) or 0) + int(n)


def log_auto_event(
    player: MutableMapping[str, Any],
    kind: str,
    message: str,
    *,
    level: str = "info",
) -> None:
    """
    Record a God-readable event. Always appends to session if active;
    also mirrors important care into auto_care_notes.
    """
    msg = str(message or "").strip()
    if not msg:
        return
    sess = ensure_auto_run(player)
    tick = int(sess.get("ticks") or 0)
    entry = {
        "t": tick,
        "kind": str(kind or "info"),
        "level": str(level or "info"),
        "msg": msg,
        "unix": float(time.time()),
    }
    if sess.get("active"):
        ev = list(sess.get("events") or [])
        ev.append(entry)
        sess["events"] = ev[-MAX_EVENTS:]
        player["_auto_run"] = sess
    # ring buffer for hub log (always, for God)
    if kind in (
        KIND_EAT,
        KIND_REST,
        KIND_POTION,
        KIND_FIGHT,
        KIND_NEEDS,
        KIND_STOP,
        KIND_AVOID,
        KIND_PAUSE,
        KIND_DECISION,
        KIND_ALERT,
    ):
        try:
            from game.domain.needs import append_auto_care_note

            tag = {
                KIND_EAT: "กิน",
                KIND_REST: "พัก",
                KIND_POTION: "ยา",
                KIND_FIGHT: "สู้",
                KIND_NEEDS: "กายใจ",
                KIND_STOP: "หยุด",
                KIND_AVOID: "เลี่ยง",
                KIND_PAUSE: "พักรอบ",
                KIND_DECISION: "ตัดสิน",
                KIND_ALERT: "เตือน",
            }.get(kind, kind)
            append_auto_care_note(player, f"[{tag}] {msg}", limit=32)
        except Exception:
            pass


def observe_auto_lines(
    player: MutableMapping[str, Any],
    lines: Sequence[str],
    *,
    count: bool = False,
) -> None:
    """
    Log soft lines for God (events).

    WO-017 R3: by default does NOT bump counters (count=False).
    Counters are bumped once at action sites (care / fight / avoid)
    so 1 action = 1 count. Set count=True only for legacy one-shot batches
    that are not paired with explicit bumps — still at most once per kind.
    """
    if not ensure_auto_run(player).get("active"):
        return
    seen: set = set()
    for raw in lines:
        t = str(raw or "").strip()
        if not t:
            continue
        low = t
        # rest — one log line per batch
        if "พัก" in low and ("ออโต้" in low or "…" in low or "ล้า" in low):
            if "rest" not in seen:
                seen.add("rest")
                if count:
                    bump_auto_run(player, "rests")
                log_auto_event(player, KIND_REST, t[:80])
        # eat / food
        elif (
            any(k in low for k in ("กิน", "เสบียง", "ประทังขวัญ"))
            and "เหลือน้อย" not in low
            and "ไม่มี" not in low
            and "เตือน" not in low
        ):
            if "eat" not in seen:
                seen.add("eat")
                if count:
                    bump_auto_run(player, "eats")
                log_auto_event(player, KIND_EAT, t[:80])
        # potion
        elif ("ยา" in low and "ออโต้" in low) or (
            "HP" in low and ("+" in low or "ฟื้น" in low)
        ):
            if "potion" not in seen:
                seen.add("potion")
                if count:
                    bump_auto_run(player, "potions")
                log_auto_event(player, KIND_POTION, t[:80])
        # WO-022 economy: auto buy / sell junk
        elif "ออโต้ซื้อ" in low or low.startswith("ฉุกเฉิน:") or "ฉุกเฉิน:" in low:
            if "buy" not in seen:
                seen.add("buy")
                if count:
                    bump_auto_run(player, "buys")
                log_auto_event(player, KIND_DECISION, t[:80])
        elif "ขาย「" in low or "ขาย\"" in low or "ออโต้กระเป๋า: ขาย" in low:
            if "sell" not in seen:
                seen.add("sell")
                if count:
                    bump_auto_run(player, "sells")
                log_auto_event(player, KIND_DECISION, t[:80])
        # fight results — prefer primary outcome line only
        elif "ออโต้ชนะ" in low or "ออโต้: แพ้" in low:
            if "fight" not in seen:
                seen.add("fight")
                if count:
                    bump_auto_run(player, "fights")
                log_auto_event(
                    player,
                    KIND_FIGHT,
                    t[:80],
                    level="warn" if "แพ้" in low else "info",
                )
        elif "เลี่ยง" in low or "หลีกไฟต์" in low or "เลี่ยงมอน" in low or "เดินเงียบ" in low:
            if "avoid" not in seen:
                seen.add("avoid")
                if count:
                    bump_auto_run(player, "avoids")
                log_auto_event(player, KIND_AVOID, t[:80])
        # needs stress (log only, never count)
        elif any(
            k in low
            for k in (
                "ขวัญหด",
                "ขวัญย่ำ",
                "ขวัญวิกฤต",
                "หิววิกฤต",
                "ล้าวิกฤต",
                "ขวัญไม่นิ่ง",
                "ลดความก้าวร้าว",
            )
        ):
            if "needs" not in seen:
                seen.add("needs")
                log_auto_event(player, KIND_NEEDS, t[:80], level="warn")


def auto_run_time_up(player: Mapping[str, Any]) -> bool:
    sess = player.get("_auto_run") or {}
    if not isinstance(sess, dict) or not sess.get("active"):
        return False
    max_s = int(sess.get("max_seconds") or 0)
    if max_s <= 0:
        return False
    started = float(sess.get("started_unix") or 0)
    if started <= 0:
        return False
    return (time.time() - started) >= max_s


def elapsed_seconds(player: Mapping[str, Any]) -> float:
    sess = player.get("_auto_run") or {}
    if not isinstance(sess, dict):
        return 0.0
    started = float(sess.get("started_unix") or 0)
    if started <= 0:
        return 0.0
    return max(0.0, time.time() - started)


def _outcome_for(player: Mapping[str, Any], reason: str) -> str:
    reason = str(reason or "")
    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    pct = 100.0 * hp / mhp
    if reason == "hp" or hp <= 0:
        if hp <= 0 or pct < 8:
            return "เกือบตาย / เลือดวิกฤต"
        return "หยุดเพราะเลือดต่ำ"
    if reason in ("food",):
        return "หยุด — หิว/เสบียง (รอดแต่ต้องเติม)"
    if reason in ("morale",):
        return "หยุด — ขวัญ (นโยบาย retreat)"
    if reason in ("done", "time"):
        if pct < 25:
            return "รอดครบรอบ · เลือดบาง"
        return "รอดครบรอบ"
    if reason in ("stop", "user"):
        return "หยุดโดยผู้เล่น (รอด)"
    if reason == "pause":
        return "พักรอบ — รอมือจัดการเป้า"
    return f"จบ ({REASON_THAI.get(reason, reason)})"


def format_auto_run_summary(
    player: Mapping[str, Any],
    reg: Any = None,
    *,
    reason: Optional[str] = None,
) -> List[str]:
    """
    5–10 soft lines for God playtest after auto stops.
    """
    sess = dict(player.get("_auto_run") or {})
    # prefer finished snapshot
    last = player.get("_auto_run_last")
    if isinstance(last, dict) and not sess.get("active"):
        sess = {**last, **sess} if not last.get("summary_ready") else last

    r = str(reason or sess.get("stop_reason") or "done")
    kind = str(sess.get("kind") or "auto")
    label = str(sess.get("label") or kind)
    ticks = int(sess.get("ticks") or 0)
    elapsed = float(sess.get("elapsed_sec") or 0)
    if elapsed <= 0 and sess.get("started_unix"):
        try:
            elapsed = max(0.0, time.time() - float(sess["started_unix"]))
        except Exception:
            elapsed = 0.0

    eats = int(sess.get("eats") or 0)
    rests = int(sess.get("rests") or 0)
    pots = int(sess.get("potions") or 0)
    fights = int(sess.get("fights") or 0)
    avoids = int(sess.get("avoids") or 0)
    buys = int(sess.get("buys") or 0)
    sells = int(sess.get("sells") or 0)
    outcome = str(sess.get("outcome") or _outcome_for(player, r))
    money_now = int(player.get("money_world") or 0)
    money_start = int(sess.get("money_start") or money_now)
    money_delta = money_now - money_start
    heaven_d = int(player.get("money_heaven") or 0) - int(sess.get("heaven_start") or 0)
    hell_d = int(player.get("money_hell") or 0) - int(sess.get("hell_start") or 0)

    # needs snapshot
    needs_line = "หิว ? · ล้า ? · ขวัญ ?"
    try:
        from game.domain.needs import format_combat_needs_compact, get_needs, soft_label

        needs_line = format_combat_needs_compact(player)  # type: ignore[arg-type]
    except Exception:
        try:
            from game.domain.needs import get_needs, soft_label

            n = get_needs(player)  # type: ignore[arg-type]
            needs_line = (
                f"หิว {soft_label('hunger', int(n['hunger']))} · "
                f"ล้า {soft_label('fatigue', int(n['fatigue']))} · "
                f"ขวัญ {soft_label('morale', int(n['morale']))}"
            )
        except Exception:
            pass

    pol = "?"
    try:
        from game.runtime.dungeon_auto import ensure_auto_prefs

        prefs = ensure_auto_prefs(player)  # type: ignore[arg-type]
        pol = str(prefs.get("low_morale_policy") or "caution")
    except Exception:
        pass

    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    time_bit = f"{mins}น{secs:02d}ว" if mins else f"{secs} วินาที"
    if ticks:
        time_bit = f"{time_bit} · {ticks} ติก"

    # care intensity for God tuning (WO-017 R2)
    care_rate = ""
    if ticks > 0:
        care_rate = f" · เฉลี่ยกิน {eats / ticks:.1f}/ติก · พัก {rests / ticks:.1f}/ติก"

    why_stop = REASON_THAI.get(r, r)
    why_live = outcome
    # clearer "why survived / why stopped" for playtest notes
    if r == "food":
        why_live = "รอด — หยุดก่อนสลบ (เสบียง/หิว)"
    elif r == "morale":
        why_live = "รอด — นโยบายขวัญสั่งหยุด"
    elif r == "done" and fights == 0:
        why_live = "รอดครบรอบ — แทบไม่สู้ (ข้ามเป้า/เลี่ยง)"
    elif r == "done" and eats + rests > ticks:
        why_live = "รอดครบรอบ — care ถี่ (กิน/พักมากกว่าติก)"

    lines: List[str] = [
        " สรุป Auto Run · Playtest",
        "---",
        f" รอบ   {label} ({kind})",
        f" เวลา  {time_bit}",
        f" ทำ    กิน {eats} · พัก {rests} · ยา {pots} · สู้ {fights}"
        + (f" · เลี่ยง {avoids}" if avoids else "")
        + (f" · ซื้อ {buys}" if buys else "")
        + (f" · ขายขยะ {sells}" if sells else "")
        + care_rate,
        f" หยุด  {why_stop}",
        f" ผล    {why_live}",
        f" กายใจ {needs_line}",
        f" ชีพ   HP {hp}/{mhp} · นโยบาย {pol}",
        f" เงิน  โลก {money_now}"
        + (f" ({money_delta:+d})" if money_delta else "")
        + (
            f" · สวรรค์{'+' if heaven_d >= 0 else ''}{heaven_d}"
            if heaven_d
            else ""
        )
        + (f" · นรก{'+' if hell_d >= 0 else ''}{hell_d}" if hell_d else ""),
    ]
    # WO-023/026: burden status for God (readable)
    try:
        from game.domain.divine_burden import (
            burden_summary_for_log,
            soft_burden_status_line,
            worst_burden_band,
        )

        bu = int(sess.get("burden_unequips") or 0)
        drain = int(player.get("_burden_drain_total") or 0)
        mor_now = 0
        try:
            from game.domain.needs import get_needs

            mor_now = int(get_needs(player).get("morale") or 0)  # type: ignore[arg-type]
        except Exception:
            pass
        mor0 = int(sess.get("morale_start") or mor_now)
        bb = worst_burden_band(player, reg)
        # WO-030: clearer God wording when already unequipped
        if bb == "fit" and (bu or drain):
            lines.append(" ภาระ: ตอนนี้ไม่มี (เคยกด/ถอดระหว่างรัน)")
        else:
            lines.append(f" {burden_summary_for_log(player, reg)}")
        sl = soft_burden_status_line(player, reg)
        if sl:
            lines.append(f"  {sl}")
        bits = []
        if bu:
            bits.append(f"ถอดภาระ×{bu}")
        if drain:
            bits.append(f"ขวัญโดนภาระรวม~{drain}")
        if mor0 and mor_now != mor0:
            bits.append(f"ขวัญ {mor0}→{mor_now}")
        if bits:
            lines.append("  God·ภาระ  " + " · ".join(bits))
        if bb == "crush":
            lines.append("  ใบ้  ภาระหนัก — ถอดหรือพักขวัญก่อนดันยาว")
        elif bb == "strain":
            lines.append("  ใบ้  เรลิกร้อนมือ — ใช้ได้แต่ดูแลขวัญ")
        elif bu:
            lines.append("  ใบ้  Auto ถอดเรลิกแล้ว — ใส่ใหม่เมื่อขวัญนิ่ง")
    except Exception:
        pass
    # WO-033: Soft Alert history for God (readable, short)
    try:
        from game.domain.alerts import recent_alerts

        ra = recent_alerts(player, limit=3)
        if ra:
            bits = []
            for a in ra:
                code = str(a.get("code") or "")
                sev = str(a.get("severity") or "")
                if code:
                    bits.append(f"{code}({sev})" if sev else code)
            if bits:
                lines.append(" Soft Alert ล่าสุด  " + " · ".join(bits))
    except Exception:
        pass
    # last notable events (2–3)
    events = list(sess.get("events") or [])
    notables = [
        e
        for e in events
        if str(e.get("kind"))
        in (KIND_FIGHT, KIND_REST, KIND_EAT, KIND_NEEDS, KIND_STOP, KIND_AVOID)
    ][-3:]
    if notables:
        lines.append("---")
        lines.append(" ไฮไลต์ (ทำไมถึงจุดนี้)")
        for e in notables:
            lines.append(f"  · t{e.get('t', '?')}: {e.get('msg', '')}"[:72])
    _ = reg
    return lines


def finish_auto_run(
    player: MutableMapping[str, Any],
    reason: str,
    *,
    reg: Any = None,
) -> List[str]:
    """Close session, store last snapshot, return summary lines."""
    sess = ensure_auto_run(player)
    r = str(reason or "done")
    elapsed = elapsed_seconds(player)
    sess["active"] = False
    sess["stop_reason"] = r
    sess["elapsed_sec"] = float(elapsed)
    sess["outcome"] = _outcome_for(player, r)
    log_auto_event(player, KIND_STOP, f"หยุด: {REASON_THAI.get(r, r)} → {sess['outcome']}")
    # freeze copy for hub
    snap = dict(sess)
    snap["summary_ready"] = True
    player["_auto_run_last"] = snap
    player["_auto_run"] = sess
    return format_auto_run_summary(player, reg, reason=r)


def emit_auto_run_summary(
    player: MutableMapping[str, Any],
    io: IO,
    reason: str,
    *,
    reg: Any = None,
) -> List[str]:
    """finish + print boxed summary to IO. WO-015/016: also archive last run."""
    from game.ui_terminal.layout import render_box

    lines = finish_auto_run(player, reason, reg=reg)
    # archive for God measurement (keep last 12 runs)
    try:
        hist = list(player.get("_playtest_run_history") or [])
        snap = dict(player.get("_auto_run_last") or {})
        snap["summary_lines"] = list(lines)
        hist.append(snap)
        player["_playtest_run_history"] = hist[-12:]
    except Exception:
        pass
    io.write_line()
    io.write_line(render_box(lines, double=False))
    return lines


def format_playtest_history(player: Mapping[str, Any], *, limit: int = 8) -> List[str]:
    """WO-016: multi-run God log — last Auto Runs for playtest comparison."""
    hist = list(player.get("_playtest_run_history") or [])
    lines: List[str] = [" Playtest Run History (God)", "---"]
    if not hist:
        lines.append(" (ยังไม่มีสรุปรัน — รัน Field/Dungeon Auto ก่อน)")
        return lines
    for i, run in enumerate(hist[-limit:], 1):
        label = run.get("label") or run.get("kind") or "auto"
        reason = run.get("stop_reason") or "?"
        outcome = run.get("outcome") or ""
        ticks = run.get("ticks") or 0
        fights = run.get("fights") or 0
        eats = run.get("eats") or 0
        rests = run.get("rests") or 0
        lines.append(
            f"  #{i} {label} · ติก {ticks} · สู้ {fights} · "
            f"กิน {eats} · พัก {rests}"
        )
        lines.append(
            f"     หยุด={REASON_THAI.get(str(reason), reason)} · ผล={outcome}"
        )
    lines.append("---")
    lines.append(f" รวม {len(hist)} รันในประวัติ (เก็บสูงสุด 12)")
    return lines


def format_policy_status_line(player: Mapping[str, Any], reg: Any = None) -> str:
    """Prominent one-liner for current Auto Policy (playtest)."""
    try:
        from game.services.auto_policy_hub import care_auto_oneliner
        from game.runtime.dungeon_auto import ensure_auto_prefs

        prefs = ensure_auto_prefs(player)  # type: ignore[arg-type]
        pol = str(prefs.get("low_morale_policy") or "caution")
        if reg is not None:
            one = care_auto_oneliner(player, reg)  # type: ignore[arg-type]
            return f"Policy {pol} · {one}"
        return f"Policy {pol} · HP≤{prefs.get('hp_pct')}% · หิว≥{prefs.get('hunger')}"
    except Exception:
        return "Policy ?"


def format_god_compact_status(
    player: Mapping[str, Any],
    area_name: str = "",
    *,
    reg: Any = None,
    tick: Optional[int] = None,
    max_ticks: Optional[int] = None,
) -> str:
    """
    Compact God line: HP · Needs · Policy (for auto ticks / playtest).
    """
    name = player.get("name", "?")
    lv = player.get("level", 1)
    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    needs = "?"
    try:
        from game.domain.needs import format_combat_needs_compact

        needs = format_combat_needs_compact(player)  # type: ignore[arg-type]
    except Exception:
        pass
    pol = format_policy_status_line(player, reg)
    pol_short = str(pol).replace("Policy ", "P:", 1)
    tick_bit = ""
    if tick is not None:
        if max_ticks:
            tick_bit = f"[{tick}/{max_ticks}] "
        else:
            tick_bit = f"[{tick}] "
    area = f" · {area_name}" if area_name else ""
    return (
        f"{tick_bit}{name} Lv.{lv} HP {hp}/{mhp}{area}\n"
        f"  กายใจ {needs}\n"
        f"  {pol_short}"
    )


def format_god_compact_box_lines(
    player: Mapping[str, Any],
    *,
    reg: Any = None,
    area_name: str = "",
) -> List[str]:
    """Box lines for God compact panel (personal / playtest)."""
    lines: List[str] = [
        " God Compact · Playtest",
        "---",
    ]
    for part in format_god_compact_status(player, area_name, reg=reg).split("\n"):
        lines.append(f" {part}" if not str(part).startswith(" ") else part)
    lines.append("---")
    lines.append(f" {format_policy_status_line(player, reg)}")
    if is_god_compact(player):
        lines.append(" God Compact: เปิด")
    else:
        lines.append(" God Compact: ปิด (สลับใน Test Run)")
    last = player.get("_auto_run_last")
    if isinstance(last, dict) and last.get("stop_reason"):
        lines.append(
            f" รันล่าสุด: {last.get('label')} → "
            f"{REASON_THAI.get(str(last.get('stop_reason')), last.get('stop_reason'))}"
        )
    return lines


def format_recent_auto_events(
    player: Mapping[str, Any],
    *,
    limit: int = 12,
) -> List[str]:
    """Lines for hub history — prefer session events then care notes."""
    lines: List[str] = [" Auto Run Log (God)", "---"]
    sess = player.get("_auto_run_last") or player.get("_auto_run") or {}
    events = list((sess or {}).get("events") or []) if isinstance(sess, dict) else []
    if events:
        for e in events[-limit:]:
            k = str(e.get("kind") or "?")
            lines.append(f"  t{e.get('t', '?')} [{k}] {e.get('msg', '')}"[:70])
    else:
        notes = list(player.get("auto_care_notes") or [])
        if notes:
            for n in notes[-limit:]:
                lines.append(f"  · {n}"[:70])
        else:
            lines.append(" (ยังไม่มี event — รัน Auto / Test Run ก่อน)")
    return lines


def run_playtest_hub(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: Any = None,
    *,
    area_name: str = "",
) -> None:
    """
    WO-011: Test Run menu — timed/tick field auto + summaries + God compact.
    """
    import random
    from game.ui_terminal.layout import render_box

    rng = rng or random.Random()

    while True:
        god = "เปิด" if is_god_compact(player) else "ปิด"
        menu = [
            " Test Run · Playtest",
            "---",
            " เตรียม Needs + Auto Play",
            f"  God Compact  {god}",
            f"  {format_policy_status_line(player, reg)}"[:56],
            "---",
            "  1  Field Auto  12 ติก (continuous)",
            "  2  Field Auto  30 ติก (playtest ยาว)",
            "  3  Field Auto  60 วินาที (wall clock)",
            "  4  Field Auto  กำหนดติกเอง",
            "---",
            "  5  ดูสรุป Auto ล่าสุด",
            "  6  ดู Log เหตุการณ์",
            f"  7  สลับ God Compact (ตอนนี้ {god})",
            "  8  ตั้ง Auto Policy",
            "  9  ประวัติหลายรัน (God Measurement)",
            "  G  ห้องทดสอบเรลิก (Godforge Chamber)",
            "  H  WO-028 Playtest checklist (God)",
            "---",
            "  0  กลับ",
        ]
        # embed compact status
        try:
            for ln in format_god_compact_box_lines(player, reg=reg, area_name=area_name)[2:6]:
                if ln not in menu:
                    pass
        except Exception:
            pass
        io.write_line()
        io.write_line(render_box(menu, double=False))
        io.write_line()
        io.write_line(render_box(format_god_compact_box_lines(player, reg=reg, area_name=area_name), double=False))
        ch = io.read_line("\n  Playtest> ").strip().lower()
        if ch in ("0", "", "q"):
            return
        if ch == "7":
            set_god_compact(player, not is_god_compact(player))
            io.write_line(
                "  God Compact → "
                + ("เปิด" if is_god_compact(player) else "ปิด")
            )
            continue
        if ch == "8":
            from game.services.auto_policy_hub import run_auto_policy_hub

            run_auto_policy_hub(player, reg, io)
            continue
        if ch in ("g", "godforge", "chamber", "relic"):
            from game.services.godforge_chamber import run_godforge_chamber

            run_godforge_chamber(player, reg, io)
            continue
        if ch in ("h", "wo028", "checklist"):
            io.write_line()
            io.write_line(render_box([
                " WO-028 Playtest Checklist (God)",
                "---",
                " 1  บทเรียน T หน้า 9 เรลิก · Policy B ถอดภาระ",
                " 2  ป่ามืด: เควสเสียงในพุ่ม / เฝ้าทางราก",
                " 3  เรลิก: น้ำหนักวายุ หรือ ห้อง G ยืม+ใส่",
                " 4  ห้อง G: spar 2–3 · 7 สรุป · 6 ออก (เงินไม่เพิ่ม)",
                " 5  mid: เถ้าโลกันตร์ / หักปริซึม / เกราะฟ้า (ปลดตามสาย)",
                " 6  หนองหมอก: ลดปลิง · ทางกออ้อ",
                " 7  ใส่ crush แล้วสู้ 3 ไฟต์ — เงินแผ่วแต่รอด",
                " 8  ถ้ำ/ทะเลทราย · เขา/ผลึก · เมือง/รอยแยก (area loops)",
                "---",
                " คู่มือเต็ม: docs/WO028_HUMAN_PLAYTEST.md",
                " Harness: python3 scripts/wo028_playtest_harness.py",
                " Stat:    python3 scripts/wo036_stat_playtest.py",
                " Area: python3 scripts/wo031_area_loop_check.py · wo032_area_loop_check.py",
            ], double=False))
            io.read_line("Enter...")
            continue
        if ch == "5":
            last = player.get("_auto_run_last")
            if not last:
                io.write_line("  (ยังไม่มีสรุป — รัน Auto ก่อน)")
            else:
                io.write_line(
                    render_box(
                        format_auto_run_summary(player, reg),
                        double=False,
                    )
                )
            io.read_line("Enter...")
            continue
        if ch == "6":
            io.write_line(render_box(format_recent_auto_events(player), double=False))
            io.read_line("Enter...")
            continue
        if ch == "9":
            io.write_line(
                render_box(format_playtest_history(player), double=False)
            )
            io.read_line("Enter...")
            continue
        if ch in ("1", "2", "3", "4"):
            from game.runtime.auto_farm import run_auto_farm

            max_ticks = 12
            max_seconds = 0
            if ch == "1":
                max_ticks = 12
            elif ch == "2":
                max_ticks = 30
            elif ch == "3":
                max_ticks = 200  # safety cap
                max_seconds = 60
            elif ch == "4":
                raw = io.read_line("  จำนวนติก (5–80): ").strip()
                try:
                    max_ticks = max(5, min(80, int(raw)))
                except Exception:
                    max_ticks = 12
            io.write_line(
                f"  เริ่ม Test Run · ติก≤{max_ticks}"
                + (f" · เวลา≤{max_seconds}s" if max_seconds else "")
            )
            # run_auto_farm will start_auto_run when wired; pass via player hint
            player["_playtest_max_seconds"] = max_seconds
            reason, sight = run_auto_farm(
                player,
                reg,
                io,
                rng,
                max_ticks=max_ticks,
                continuous=True,
            )
            player.pop("_playtest_max_seconds", None)
            if reason == "pause" and sight:
                io.write_line(
                    f"  (pause เป้า: {sight.get('label')} — จัดการเองที่สนาม)"
                )
            io.read_line("Enter...")
            continue
        io.write_line("  เลือก 1–8 หรือ 0")
