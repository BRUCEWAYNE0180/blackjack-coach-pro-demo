"""Repeat-pack generator for missed spots in Blackjack Coach Pro Demo (v1.26.0).

Uses the practice-pack completion history (v1.25.0) to build a focused repeat
session for the spots the user keeps getting wrong: recently missed spots,
repeatedly missed spots, low-accuracy spots, and skipped spots, topped up with
the review queue or a starter educational set when needed.

Everything stays local and read-only. The correct play for every item comes from
the strategy engine (via the drill generator) - no strategy logic is duplicated,
and nothing here changes the recommendation or the Hi-Lo math. Packs / exports
store no money, bankroll, bets, accounts, tokens, screenshots, or personal data.
Standard library only - no network, no cloud, no database, no external
dependencies. The ``.blackjack_coach/`` tree stays git-ignored. The pack
suggests practice; it never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .drill_generator import _FALLBACK_HANDS, build_drill_spot_from_hand
from .practice_pack_history import list_practice_pack_completion_records
from .reporting import HISTORY_ROOT_DIRNAME, REPORTS_SUBDIR, save_report
from .review_scheduler import build_review_queue, parse_date_or_today
from .rules import DEFAULT_PROFILE, get_profile

# Item sources.
SRC_MISSED = "missed"
SRC_LOW_ACCURACY = "low_accuracy"
SRC_SKIPPED = "skipped"
SRC_DUE_REVIEW = "due_review"
SRC_FALLBACK = "educational_fallback"

# Priority by source (lower = practise sooner).
_PRIORITY = {
    SRC_MISSED: 1,
    SRC_LOW_ACCURACY: 1,
    SRC_SKIPPED: 2,
    SRC_DUE_REVIEW: 3,
    SRC_FALLBACK: 4,
}

# A spot is "low accuracy" once it has enough attempts and a poor hit rate.
_LOW_ACCURACY_THRESHOLD = 0.60
_MIN_ATTEMPTS_FOR_ACCURACY = 2

EDUCATIONAL_NOTE = (
    "Local repeat pack for self-study only. The correct play always comes from "
    "the strategy engine; it stores no money, bankroll, bets, accounts, or "
    "tokens, never changes the recommendation or the correct answers, and never "
    "promises results."
)

STARTER_NOTE = (
    "No missed practice pack history yet. Using starter educational repeat pack."
)

_VALUE_RANKS = {"2", "3", "4", "5", "6", "7", "8", "9", "10", "A"}


@dataclass(frozen=True)
class RepeatPackItem:
    """One spot to repeat because it was missed / low-accuracy / skipped."""

    item_id: str
    spot_id: str
    profile_key: str
    category: str
    player_cards: tuple[str, ...]
    dealer_upcard: str
    recommended_action: str
    miss_count: int
    attempt_count: int
    accuracy: float
    last_missed_at: str
    source: str
    priority: int
    reason: str
    tags: list[str] = field(default_factory=list)
    note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepeatPack:
    """A generated repeat pack focused on missed / weak spots."""

    pack_id: str
    created_at: str
    date: str
    profile_key: str | None
    total_items: int
    missed_items: int
    low_accuracy_items: int
    fallback_items: int
    items: list[RepeatPackItem]
    pack_note: str
    completion_hint: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepeatPackExport:
    """The result of exporting a repeat pack to a file."""

    export_id: str
    created_at: str
    output_path: str
    format: str
    pack: RepeatPack
    note: str = ""


def _spot_id_to_hand(spot_id: str) -> tuple[list[str], str] | None:
    """Best-effort reconstruction of (player_cards, dealer) from a spot id.

    Handles the ``<kind>_<value>_vs_<dealer>`` ids produced by
    ``adaptive_learning.classify_hand_spot`` (e.g. ``hard_16_vs_10``,
    ``soft_18_vs_9``, ``pair_8_vs_6``). Returns ``None`` when it cannot be
    reconstructed.
    """
    parts = spot_id.split("_vs_")
    if len(parts) != 2:
        return None
    left, dealer = parts
    if dealer not in _VALUE_RANKS:
        return None
    left_parts = left.split("_")
    if len(left_parts) != 2:
        return None
    kind, value = left_parts

    if kind == "pair":
        if value not in _VALUE_RANKS:
            return None
        return [value, value], dealer

    if kind == "soft":
        try:
            total = int(value)
        except ValueError:
            return None
        kicker = total - 11
        if 2 <= kicker <= 9:
            return ["A", str(kicker)], dealer
        return None

    if kind == "hard":
        try:
            total = int(value)
        except ValueError:
            return None
        # Two non-ace cards (2..10) summing to the total; prefer a 10 anchor.
        for first in range(min(10, total - 2), 1, -1):
            second = total - first
            if 2 <= second <= 10:
                return [str(first), str(second)], dealer
        return None

    return None


def build_repeat_pack_item_from_spot(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile=DEFAULT_PROFILE,
    source: str = SRC_MISSED,
    spot_id: str | None = None,
    miss_count: int = 0,
    attempt_count: int = 0,
    accuracy: float = 0.0,
    last_missed_at: str = "",
    reason: str = "",
) -> RepeatPackItem:
    """Build a :class:`RepeatPackItem` from a hand, using the strategy engine.

    The recommended action comes from
    :func:`app.drill_generator.build_drill_spot_from_hand` (the strategy engine)
    - it is never re-derived here.
    """
    spot = build_drill_spot_from_hand(list(player_cards), dealer_upcard, profile)
    return RepeatPackItem(
        item_id=uuid.uuid4().hex[:8],
        spot_id=spot_id or spot.spot_id,
        profile_key=profile.key,
        category=spot.category,
        player_cards=spot.player_cards,
        dealer_upcard=spot.dealer_upcard,
        recommended_action=spot.recommended_action,
        miss_count=miss_count,
        attempt_count=attempt_count,
        accuracy=accuracy,
        last_missed_at=last_missed_at,
        source=source,
        priority=_PRIORITY.get(source, 4),
        reason=reason or spot.reason,
        tags=list(spot.tags),
    )


def _aggregate_spots(records) -> dict[str, dict]:
    """Aggregate per-spot miss / attempt / accuracy stats across records."""
    stats: dict[str, dict] = {}
    for record in records:
        for spot_id in record.completed_spot_ids:
            entry = stats.setdefault(spot_id, {
                "attempts": 0, "misses": 0, "skips": 0, "last_missed_at": ""})
            entry["attempts"] += 1
        for spot_id in record.missed_spot_ids:
            entry = stats.setdefault(spot_id, {
                "attempts": 0, "misses": 0, "skips": 0, "last_missed_at": ""})
            entry["misses"] += 1
            if record.created_at >= entry["last_missed_at"]:
                entry["last_missed_at"] = record.created_at
        for spot_id in record.skipped_spot_ids:
            entry = stats.setdefault(spot_id, {
                "attempts": 0, "misses": 0, "skips": 0, "last_missed_at": ""})
            entry["skips"] += 1
    return stats


def _classify_source(entry: dict) -> str | None:
    """Pick the repeat source for a spot, or None if it should not repeat."""
    attempts = entry["attempts"]
    misses = entry["misses"]
    skips = entry["skips"]
    correct = max(attempts - misses, 0)
    accuracy = correct / attempts if attempts else 0.0
    if attempts >= _MIN_ATTEMPTS_FOR_ACCURACY and accuracy < _LOW_ACCURACY_THRESHOLD:
        return SRC_LOW_ACCURACY
    if misses >= 1:
        return SRC_MISSED
    if skips >= 1:
        return SRC_SKIPPED
    return None


def build_repeat_pack(
    profile_key: str | None = None,
    count: int = 20,
    pack_dir: str | Path | None = None,
    drill_dir: str | Path | None = None,
    today: str | None = None,
    seed: int | None = None,
) -> RepeatPack:
    """Build a repeat pack from missed / weak practice-pack spots.

    Priority: recently/repeatedly missed spots and low-accuracy spots, then
    skipped spots, then due review-queue items, then a starter educational set
    when there is no missed history. ``count`` caps the items, ``seed`` makes the
    order deterministic, and duplicate spots (by ``spot_id``) are dropped.
    """
    if count <= 0:
        raise ValueError("count must be >= 1.")

    today_date = parse_date_or_today(today)
    profile = get_profile(profile_key) if profile_key else DEFAULT_PROFILE

    records = list_practice_pack_completion_records(
        history_dir=pack_dir, profile_key=profile_key)
    stats = _aggregate_spots(records)

    warnings: list[str] = []
    candidates: list[RepeatPackItem] = []
    seen: set[str] = set()

    def _add(spot_id: str, source: str, entry: dict | None) -> None:
        if spot_id in seen:
            return
        hand = _spot_id_to_hand(spot_id)
        if hand is None:
            warnings.append(f"Could not reconstruct spot '{spot_id}'; skipped.")
            return
        cards, dealer = hand
        misses = entry["misses"] if entry else 0
        attempts = entry["attempts"] if entry else 0
        correct = max(attempts - misses, 0)
        accuracy = correct / attempts if attempts else 0.0
        last_missed = entry["last_missed_at"] if entry else ""
        reason = {
            SRC_MISSED: f"Missed {misses} time(s); revisit it.",
            SRC_LOW_ACCURACY: (
                f"Low accuracy ({accuracy * 100:.0f}% over {attempts}); drill it."),
            SRC_SKIPPED: "Previously skipped; give it a try.",
            SRC_DUE_REVIEW: "Due for scheduled review.",
        }.get(source, "")
        try:
            item = build_repeat_pack_item_from_spot(
                cards, dealer, profile, source=source, spot_id=spot_id,
                miss_count=misses, attempt_count=attempts, accuracy=accuracy,
                last_missed_at=last_missed, reason=reason)
        except (ValueError, KeyError):
            warnings.append(f"Could not resolve action for '{spot_id}'; skipped.")
            return
        seen.add(spot_id)
        candidates.append(item)

    # 1) History-derived spots (missed / low-accuracy / skipped), ordered by
    #    miss count then recency so the worst offenders come first.
    ordered_spots = sorted(
        stats.items(),
        key=lambda kv: (kv[1]["misses"], kv[1]["last_missed_at"]),
        reverse=True)
    for spot_id, entry in ordered_spots:
        source = _classify_source(entry)
        if source is not None:
            _add(spot_id, source, entry)

    using_starter = len(candidates) == 0

    # 2) Top up with due review-queue items when we have history but few spots.
    if not using_starter and len(candidates) < count:
        queue = build_review_queue(
            drill_dir=drill_dir, profile_key=profile_key,
            today=today_date, due_only=True)
        for review_item in queue.items:
            _add(review_item.spot_id, SRC_DUE_REVIEW, None)

    # 3) Educational fallback when there is no missed history at all.
    if using_starter:
        for cards, dealer in _FALLBACK_HANDS:
            try:
                item = build_repeat_pack_item_from_spot(
                    cards, dealer, profile, source=SRC_FALLBACK,
                    reason="Starter educational spot.")
            except (ValueError, KeyError):
                continue
            if item.spot_id in seen:
                continue
            seen.add(item.spot_id)
            candidates.append(item)
        warnings.append(STARTER_NOTE)

    # Deterministic ordering: shuffle within each priority, then sort by
    # priority (stable) so the most urgent spots stay first.
    if seed is not None:
        rng = random.Random(seed)
        groups: dict[int, list[RepeatPackItem]] = {}
        for item in candidates:
            groups.setdefault(item.priority, []).append(item)
        shuffled: list[RepeatPackItem] = []
        for priority in sorted(groups):
            bucket = groups[priority]
            rng.shuffle(bucket)
            shuffled.extend(bucket)
        candidates = shuffled
    else:
        candidates.sort(key=lambda i: i.priority)

    items = candidates[:count]

    low_accuracy_items = sum(1 for i in items if i.source == SRC_LOW_ACCURACY)
    fallback_items = sum(1 for i in items if i.source == SRC_FALLBACK)
    missed_items = len(items) - low_accuracy_items - fallback_items

    if using_starter:
        pack_note = STARTER_NOTE + " " + EDUCATIONAL_NOTE
    else:
        pack_note = (
            f"Repeat pack for {today_date.isoformat()} focused on missed / weak "
            "spots. " + EDUCATIONAL_NOTE)

    completion_hint = (
        "Practise each spot with `blackjack-coach drill --answer <ACTION>` and "
        "record it with `practice-pack --complete --correct-spots ... "
        "--missed-spots ...`.")

    return RepeatPack(
        pack_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        date=today_date.isoformat(),
        profile_key=profile_key,
        total_items=len(items),
        missed_items=missed_items,
        low_accuracy_items=low_accuracy_items,
        fallback_items=fallback_items,
        items=items,
        pack_note=pack_note,
        completion_hint=completion_hint,
        warnings=list(dict.fromkeys(warnings)),
    )


def _section_for(item: RepeatPackItem) -> str:
    if item.source == SRC_LOW_ACCURACY:
        return "low"
    if item.source == SRC_FALLBACK:
        return "fallback"
    return "missed"


def _item_text(item: RepeatPackItem) -> str:
    cards = ", ".join(item.player_cards) if item.player_cards else "?"
    action = item.recommended_action or "?"
    detail = ""
    if item.miss_count:
        detail = f" (missed x{item.miss_count})"
    return f"  {cards} vs {item.dealer_upcard} -> {action}{detail}"


def render_repeat_pack(pack: RepeatPack) -> str:
    """Render a compact text view of the repeat pack for the terminal."""
    lines = ["=== Repeat Pack ==="]
    lines.append(f"Date        : {pack.date}")
    lines.append(f"Profile     : {pack.profile_key or 'all profiles'}")
    lines.append(f"Total items : {pack.total_items}")
    lines.append(
        f"Breakdown   : missed {pack.missed_items}, low-accuracy "
        f"{pack.low_accuracy_items}, fallback {pack.fallback_items}")

    sections = [
        ("missed", "Missed spots"),
        ("low", "Low-accuracy spots"),
        ("fallback", "Fallback spots"),
    ]
    for key, title in sections:
        section_items = [i for i in pack.items if _section_for(i) == key]
        if not section_items:
            continue
        lines.append("")
        lines.append(f"-- {title} --")
        lines.extend(_item_text(i) for i in section_items)

    if not pack.items:
        lines.append("")
        lines.append("  (no items)")

    lines.append("")
    lines.append(f"Pack note   : {pack.pack_note}")
    lines.append(f"Completion  : {pack.completion_hint}")
    if pack.warnings:
        lines.append("")
        lines.append("-- Notes --")
        lines.extend(f"  - {w}" for w in pack.warnings)
    lines.append("")
    lines.append("Educational / local practice only - no real bets, no winnings.")
    return "\n".join(lines)


def render_repeat_pack_markdown(pack: RepeatPack) -> str:
    """Render the repeat pack as a Markdown checklist for Notion / GitHub."""
    lines = [
        "# Blackjack Coach Pro Demo - Repeat Pack",
        "",
        f"_Generated: {pack.created_at}_",
        "",
        "## Overview",
        "",
        f"- Date: {pack.date}",
        f"- Profile: {pack.profile_key or 'all profiles'}",
        f"- Total items: {pack.total_items}",
        f"- Breakdown: missed {pack.missed_items}, low-accuracy "
        f"{pack.low_accuracy_items}, fallback {pack.fallback_items}",
        "",
        "## Repeat checklist",
        "",
    ]
    if not pack.items:
        lines.append("_No items in this pack._")
    for item in pack.items:
        cards = ", ".join(item.player_cards) if item.player_cards else "?"
        profile_arg = f" --profile {item.profile_key}" if item.profile_key else ""
        command = (
            f"`blackjack-coach coach --cards {cards} --dealer "
            f"{item.dealer_upcard}{profile_arg}`")
        miss = f" (missed x{item.miss_count})" if item.miss_count else ""
        lines.append(
            f"- [ ] {cards} vs {item.dealer_upcard} ({item.category}, "
            f"{item.source}){miss} - practise: {command}")

    lines += ["", "## Notes", "", f"- {pack.pack_note}", f"- {pack.completion_hint}"]
    if pack.warnings:
        lines.append("")
        for warning in pack.warnings:
            lines.append(f"- {warning}")
    lines += [
        "",
        "---",
        "",
        "_Educational / local practice only - no real bets, no winnings._",
        "",
    ]
    return "\n".join(lines)


def default_repeat_pack_dir() -> Path:
    """Return the default local directory for exported repeat packs."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / REPORTS_SUBDIR


def export_repeat_pack(
    pack: RepeatPack,
    output_path: str | Path | None = None,
) -> RepeatPackExport:
    """Render the pack as Markdown and save it locally; return the export."""
    content = render_repeat_pack_markdown(pack)
    if output_path is not None:
        path = Path(output_path)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = default_repeat_pack_dir() / f"repeat_pack_{stamp}.md"
    saved = save_report(content, path)
    return RepeatPackExport(
        export_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        output_path=str(saved),
        format="markdown",
        pack=pack,
        note=EDUCATIONAL_NOTE,
    )
