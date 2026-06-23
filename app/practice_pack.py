"""Daily practice-pack generator for Blackjack Coach Pro Demo (v1.24.0).

Builds a single, ready-to-practise pack for "today" by combining the local
signals already produced by earlier features: the review-queue's due items
(v1.23.0), weak / EV-disagreement / educational spots from the drill generator
(v1.21.0), and the saved drill history (v1.22.0). Due spots come first, then
weak spots, then EV / high-gap spots, then a focus-specific or educational mix.

Everything stays local and read-only. It never re-derives the correct play
(that always comes from the strategy engine via the drill generator) and never
changes the recommendation or the Hi-Lo math. Packs / exports store no money,
bankroll, bets, accounts, tokens, screenshots, or personal data. Standard
library only - no network, no cloud, no database, no external dependencies. The
``.blackjack_coach/`` tree stays git-ignored. The pack suggests practice; it
never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .drill_generator import (
    SRC_EV_DISAGREEMENT,
    SRC_FALLBACK,
    SRC_HIGH_LOSS,
    SRC_WEAK,
    DrillSpot,
    build_drill_plan,
    build_drill_spot_from_hand,
)
from .reporting import HISTORY_ROOT_DIRNAME, REPORTS_SUBDIR, save_report
from .review_scheduler import (
    ReviewScheduleItem,
    build_review_queue,
    parse_date_or_today,
)
from .rules import DEFAULT_PROFILE, get_profile

# Pack-level focuses and how they map onto the drill generator's focuses.
VALID_FOCUS = ("daily", "due", "weak", "ev", "pairs", "hard", "soft", "mixed")
_DRILL_FOCUS = {
    "daily": "weak",
    "due": "weak",
    "weak": "weak",
    "ev": "ev",
    "pairs": "pairs",
    "hard": "hard",
    "soft": "soft",
    "mixed": "mixed",
}

# Pack item sources.
SRC_DUE_REVIEW = "due_review"

# Priority by source (lower = practise sooner).
_PRIORITY = {
    SRC_DUE_REVIEW: 1,
    SRC_WEAK: 2,
    SRC_HIGH_LOSS: 2,
    SRC_EV_DISAGREEMENT: 2,
    SRC_FALLBACK: 3,
}

EDUCATIONAL_NOTE = (
    "Local daily practice pack for self-study only. It stores no money, "
    "bankroll, bets, accounts, tokens, or personal data, never changes the "
    "strategy recommendation or the correct answers, and never promises results."
)

STARTER_NOTE = (
    "No saved local history yet. Using starter educational practice pack."
)


@dataclass(frozen=True)
class PracticePackItem:
    """One spot to practise in a daily pack."""

    item_id: str
    spot_id: str
    category: str
    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    recommended_action: str
    source: str
    priority: int
    due_at: str
    mastery_level: str
    reason: str
    tags: list[str] = field(default_factory=list)
    note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PracticePack:
    """A generated daily practice pack."""

    pack_id: str
    created_at: str
    date: str
    profile_key: str | None
    focus: str
    total_items: int
    due_items: int
    weak_items: int
    ev_items: int
    mixed_items: int
    items: list[PracticePackItem]
    pack_note: str
    completion_hint: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PracticePackExport:
    """The result of exporting a practice pack to a file."""

    export_id: str
    created_at: str
    output_path: str
    format: str
    pack: PracticePack
    note: str = ""


def build_pack_item_from_review_item(
    review_item: ReviewScheduleItem,
) -> PracticePackItem:
    """Convert a :class:`ReviewScheduleItem` into a pack item.

    The recommended action is obtained from the strategy engine (via the drill
    generator) - it is never re-derived here.
    """
    warnings: list[str] = list(review_item.warnings)
    recommended_action = ""
    category = review_item.category
    try:
        profile = get_profile(review_item.profile_key)
    except KeyError:
        profile = DEFAULT_PROFILE
    try:
        spot = build_drill_spot_from_hand(
            list(review_item.player_cards), review_item.dealer_upcard, profile)
        recommended_action = spot.recommended_action
        category = spot.category or category
    except (ValueError, KeyError):
        warnings.append(
            f"Could not resolve the recommended action for {review_item.spot_id}.")

    return PracticePackItem(
        item_id=uuid.uuid4().hex[:8],
        spot_id=review_item.spot_id,
        category=category,
        player_cards=review_item.player_cards,
        dealer_upcard=review_item.dealer_upcard,
        profile_key=review_item.profile_key,
        recommended_action=recommended_action,
        source=SRC_DUE_REVIEW,
        priority=_PRIORITY[SRC_DUE_REVIEW],
        due_at=review_item.due_at,
        mastery_level=review_item.mastery_level,
        reason=review_item.reason,
        tags=list(review_item.tags),
        warnings=warnings,
    )


def build_pack_item_from_drill_spot(
    drill_spot: DrillSpot,
    source: str = "drill",
) -> PracticePackItem:
    """Convert a :class:`DrillSpot` into a pack item."""
    spot_source = drill_spot.source or source
    return PracticePackItem(
        item_id=uuid.uuid4().hex[:8],
        spot_id=drill_spot.spot_id,
        category=drill_spot.category,
        player_cards=drill_spot.player_cards,
        dealer_upcard=drill_spot.dealer_upcard,
        profile_key=drill_spot.profile_key,
        recommended_action=drill_spot.recommended_action,
        source=spot_source,
        priority=_PRIORITY.get(spot_source, 3),
        due_at="",
        mastery_level="",
        reason=drill_spot.reason,
        tags=list(drill_spot.tags),
        note=drill_spot.note,
    )


def build_practice_pack(
    profile_key: str | None = None,
    focus: str = "daily",
    count: int = 20,
    drill_dir: str | Path | None = None,
    session_dir: str | Path | None = None,
    outcome_dir: str | Path | None = None,
    ev_dir: str | Path | None = None,
    today: str | None = None,
    seed: int | None = None,
) -> PracticePack:
    """Build a daily :class:`PracticePack` from local history (or a starter set).

    Priority: due review-queue items, then weak drill-history spots, then EV /
    high-gap spots, then focus-specific spots, then an educational fallback.
    ``focus`` is one of daily / due / weak / ev / pairs / hard / soft / mixed;
    ``count`` caps the items; ``seed`` makes the order deterministic; duplicate
    spots (by ``spot_id``) are dropped.
    """
    focus = (focus or "daily").lower().strip()
    if focus not in VALID_FOCUS:
        raise ValueError(
            f"Unknown focus '{focus}'. Choose one of: " + ", ".join(VALID_FOCUS)
            + ".")
    if count <= 0:
        raise ValueError("count must be >= 1.")

    today_date = parse_date_or_today(today)

    candidates: list[PracticePackItem] = []
    warnings: list[str] = []

    # 1) Due review-queue items (for the broad focuses).
    include_due = focus in ("daily", "due", "weak", "mixed")
    if include_due:
        queue = build_review_queue(
            drill_dir=drill_dir, profile_key=profile_key,
            today=today_date, due_only=True)
        for item in queue.items:
            candidates.append(build_pack_item_from_review_item(item))

    # 2) Weak / EV / focus / fallback spots from the drill generator (which
    #    already prioritises EV disagreement -> weak -> high-variance -> fallback
    #    and handles the educational fallback set). This reuses the strategy
    #    engine for correct answers; no strategy logic is duplicated here.
    drill_focus = _DRILL_FOCUS.get(focus, "weak")
    drill_plan = build_drill_plan(
        profile_key=profile_key, focus=drill_focus, count=max(count, 1) + 10,
        session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir,
        seed=seed)
    for spot in drill_plan.spots:
        candidates.append(build_pack_item_from_drill_spot(spot))

    using_starter = (
        not include_due or queue.total_items == 0
    ) and all(s.source == SRC_FALLBACK for s in drill_plan.spots)

    # Dedupe by spot_id (keep the highest-priority occurrence, which comes
    # first because due items are appended before drill items).
    seen: set[str] = set()
    deduped: list[PracticePackItem] = []
    for item in candidates:
        if item.spot_id in seen:
            continue
        seen.add(item.spot_id)
        deduped.append(item)

    # Stable sort by priority (due first), preserving insertion order otherwise.
    deduped.sort(key=lambda i: i.priority)
    items = deduped[:count]

    due_items = sum(1 for i in items if i.source == SRC_DUE_REVIEW)
    weak_items = sum(1 for i in items if i.source in (SRC_WEAK, SRC_HIGH_LOSS))
    ev_items = sum(1 for i in items if i.source == SRC_EV_DISAGREEMENT)
    mixed_items = sum(
        1 for i in items
        if i.source not in (SRC_DUE_REVIEW, SRC_WEAK, SRC_HIGH_LOSS,
                            SRC_EV_DISAGREEMENT))

    if using_starter:
        pack_note = STARTER_NOTE + " " + EDUCATIONAL_NOTE
        warnings.append(STARTER_NOTE)
    else:
        pack_note = (
            f"Daily practice pack for {today_date.isoformat()}. "
            + EDUCATIONAL_NOTE)

    completion_hint = (
        "Practise each spot with `blackjack-coach drill --answer <ACTION>` and "
        "save progress with `--save`; then re-run `blackjack-coach review-queue`."
    )

    return PracticePack(
        pack_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        date=today_date.isoformat(),
        profile_key=profile_key,
        focus=focus,
        total_items=len(items),
        due_items=due_items,
        weak_items=weak_items,
        ev_items=ev_items,
        mixed_items=mixed_items,
        items=items,
        pack_note=pack_note,
        completion_hint=completion_hint,
        warnings=list(dict.fromkeys(warnings)),
    )


def _section_for(item: PracticePackItem) -> str:
    if item.source == SRC_DUE_REVIEW:
        return "due"
    if item.source in (SRC_WEAK, SRC_HIGH_LOSS):
        return "weak"
    if item.source == SRC_EV_DISAGREEMENT:
        return "ev"
    return "mixed"


def _item_text(item: PracticePackItem) -> str:
    cards = ", ".join(item.player_cards) if item.player_cards else "?"
    action = item.recommended_action or "?"
    extra = f" (due {item.due_at})" if item.due_at else ""
    return f"  {cards} vs {item.dealer_upcard} -> {action}{extra}"


def render_practice_pack(pack: PracticePack) -> str:
    """Render a compact text view of the practice pack for the terminal."""
    lines = ["=== Daily Practice Pack ==="]
    lines.append(f"Date        : {pack.date}")
    lines.append(f"Profile     : {pack.profile_key or 'all profiles'}")
    lines.append(f"Focus       : {pack.focus}")
    lines.append(f"Total items : {pack.total_items}")
    lines.append(
        f"Breakdown   : due {pack.due_items}, weak {pack.weak_items}, "
        f"ev {pack.ev_items}, mixed {pack.mixed_items}")

    sections = [
        ("due", "Due review"),
        ("weak", "Weak spots"),
        ("ev", "EV / high-gap spots"),
        ("mixed", "Mixed / fallback"),
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


def render_practice_pack_markdown(pack: PracticePack) -> str:
    """Render the practice pack as a Markdown checklist for Notion / GitHub."""
    lines = [
        "# Blackjack Coach Pro Demo - Daily Practice Pack",
        "",
        f"_Generated: {pack.created_at}_",
        "",
        "## Overview",
        "",
        f"- Date: {pack.date}",
        f"- Profile: {pack.profile_key or 'all profiles'}",
        f"- Focus: {pack.focus}",
        f"- Total items: {pack.total_items}",
        f"- Breakdown: due {pack.due_items}, weak {pack.weak_items}, "
        f"ev {pack.ev_items}, mixed {pack.mixed_items}",
        "",
        "## Practice checklist",
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
        lines.append(
            f"- [ ] {cards} vs {item.dealer_upcard} "
            f"({item.category}, {item.source}) - practise: {command}")

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


def default_practice_pack_dir() -> Path:
    """Return the default local directory for exported practice packs."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / REPORTS_SUBDIR


def export_practice_pack(
    pack: PracticePack,
    output_path: str | Path | None = None,
) -> PracticePackExport:
    """Render the pack as Markdown and save it locally; return the export."""
    content = render_practice_pack_markdown(pack)
    if output_path is not None:
        path = Path(output_path)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = default_practice_pack_dir() / f"practice_pack_{stamp}.md"
    saved = save_report(content, path)
    return PracticePackExport(
        export_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        output_path=str(saved),
        format="markdown",
        pack=pack,
        note=EDUCATIONAL_NOTE,
    )
