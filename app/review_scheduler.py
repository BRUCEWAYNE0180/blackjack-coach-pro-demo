"""Local drill review scheduler & streaks for Blackjack Coach Pro Demo (v1.23.0).

Turns the saved drill-session history (v1.22.0) into a light, local
spaced-repetition queue: which spots are due today, what is overdue, what is
coming up, plus a practice-streak summary. Weak spots come back soon, learning
spots later, and mastered spots much later.

Everything stays local and read-only. It never re-derives the correct play (that
comes from the strategy engine via the saved drill results) and never changes
the recommendation or the Hi-Lo math. Records / exports store no money,
bankroll, bets, accounts, tokens, screenshots, or personal data. Standard
library only - no network, no cloud, no database, no external dependencies. The
``.blackjack_coach/`` tree stays git-ignored. The scheduler suggests practice;
it never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from .drill_history import (
    DrillSpotHistory,
    build_spot_history,
    list_drill_session_records,
)
from .reporting import HISTORY_ROOT_DIRNAME, REPORTS_SUBDIR, save_report

# Mastery -> base review interval in days (spaced repetition).
_INTERVAL_DAYS = {
    "NEW": 0,
    "WEAK": 1,
    "LEARNING": 2,
    "MASTERED": 7,
}

# Mastery -> scheduling priority (higher = more urgent).
_PRIORITY = {
    "WEAK": 3,
    "NEW": 2,
    "LEARNING": 1,
    "MASTERED": 0,
}

# Below this many total attempts the queue flags a LOW sample.
MIN_ATTEMPTS = 10

EDUCATIONAL_NOTE = (
    "Local review scheduler for self-study only. It stores no money, bankroll, "
    "bets, accounts, tokens, or personal data, never changes the strategy "
    "recommendation or the correct answers, and never promises results."
)

NO_DATA_MESSAGE = (
    "No saved drill sessions yet. Use drill --answer <ACTION> --save first."
)


@dataclass(frozen=True)
class ReviewScheduleItem:
    """One spot scheduled for review, with its due date and urgency."""

    spot_id: str
    profile_key: str
    category: str
    player_cards: tuple[str, ...]
    dealer_upcard: str
    mastery_level: str
    attempts: int
    accuracy: float
    last_seen_at: str
    due_at: str
    days_until_due: int
    is_due: bool
    priority: int
    reason: str
    tags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewQueue:
    """A scheduled drill-review queue (due / overdue / upcoming)."""

    created_at: str
    profile_key: str | None
    total_items: int
    due_count: int
    overdue_count: int
    upcoming_count: int
    items: list[ReviewScheduleItem]
    next_review_note: str
    data_quality_note: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DrillStreakSummary:
    """A local practice-streak summary from saved drill sessions."""

    total_saved_drill_sessions: int
    active_days: int
    current_streak_days: int
    longest_streak_days: int
    last_practice_date: str | None
    newest_session_id: str | None
    practice_frequency_note: str
    warnings: list[str] = field(default_factory=list)


def parse_date_or_today(value: str | None = None) -> date:
    """Parse a ``YYYY-MM-DD`` string, or return today's local date when None.

    Accepts an explicit date for deterministic tests. Raises ``ValueError`` for
    a malformed date. No external dependencies.
    """
    if value is None:
        return date.today()
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Invalid date '{value}'. Use YYYY-MM-DD.") from exc


def _date_of(timestamp: str) -> date | None:
    """Best-effort extract the date from an ISO timestamp string."""
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp).date()
    except ValueError:
        try:
            return datetime.strptime(timestamp[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def calculate_due_date(
    spot_history: DrillSpotHistory,
    today: str | date | None = None,
) -> tuple[str, str]:
    """Return the ``(due_at, reason)`` for a spot based on its mastery.

    Intervals (from the last practice): NEW = today, WEAK = ~1 day (today when a
    recent miss is likely), LEARNING = 2 days, MASTERED = 7 days. When there is
    no reliable ``last_seen_at`` the spot is due today.
    """
    today_date = today if isinstance(today, date) else parse_date_or_today(today)
    mastery = spot_history.mastery_level
    interval = _INTERVAL_DAYS.get(mastery, 0)

    # A recently/largely missed weak spot should come back today.
    if mastery == "WEAK" and spot_history.accuracy < 0.5:
        interval = 0

    last_seen = _date_of(spot_history.last_seen_at)
    if last_seen is None:
        due_at = today_date
        reason = (
            f"{mastery}: no reliable last-practice date, scheduled for today.")
        return due_at.isoformat(), reason

    due_at = last_seen + timedelta(days=interval)
    if interval == 0:
        reason = f"{mastery}: review today."
    elif interval == 1:
        reason = f"{mastery}: review within a day."
    else:
        reason = f"{mastery}: review in {interval} days."
    return due_at.isoformat(), reason


def _schedule_item(
    spot: DrillSpotHistory,
    today_date: date,
) -> ReviewScheduleItem:
    """Build a :class:`ReviewScheduleItem` for a spot at ``today_date``."""
    due_at, reason = calculate_due_date(spot, today_date)
    due_date = parse_date_or_today(due_at)
    days_until_due = (due_date - today_date).days
    is_due = days_until_due <= 0

    warnings: list[str] = []
    if _date_of(spot.last_seen_at) is None:
        warnings.append(
            f"Spot {spot.spot_id} has no reliable last-practice date.")

    return ReviewScheduleItem(
        spot_id=spot.spot_id,
        profile_key=spot.profile_key,
        category=spot.category,
        player_cards=spot.player_cards,
        dealer_upcard=spot.dealer_upcard,
        mastery_level=spot.mastery_level,
        attempts=spot.attempts,
        accuracy=spot.accuracy,
        last_seen_at=spot.last_seen_at,
        due_at=due_at,
        days_until_due=days_until_due,
        is_due=is_due,
        priority=_PRIORITY.get(spot.mastery_level, 1),
        reason=reason,
        tags=list(spot.tags),
        warnings=warnings,
    )


def _data_quality_note(total_attempts: int, total_items: int) -> str:
    if total_items == 0:
        return NO_DATA_MESSAGE + " " + EDUCATIONAL_NOTE
    if total_attempts < MIN_ATTEMPTS:
        return (
            f"LOW sample: only {total_attempts} drill attempt(s) "
            f"(< {MIN_ATTEMPTS}); treat the schedule as indicative. "
            + EDUCATIONAL_NOTE
        )
    return (
        f"{total_attempts} drill attempts across {total_items} spot(s). "
        + EDUCATIONAL_NOTE
    )


def build_review_queue(
    drill_dir: str | Path | None = None,
    profile_key: str | None = None,
    limit: int | None = None,
    today: str | date | None = None,
    due_only: bool = False,
) -> ReviewQueue:
    """Build the scheduled drill-review queue from saved drill sessions."""
    today_date = today if isinstance(today, date) else parse_date_or_today(today)
    records = list_drill_session_records(
        history_dir=drill_dir, profile_key=profile_key)

    created_at = datetime.now().isoformat(timespec="seconds")
    if not records:
        return ReviewQueue(
            created_at=created_at,
            profile_key=profile_key,
            total_items=0,
            due_count=0,
            overdue_count=0,
            upcoming_count=0,
            items=[],
            next_review_note=NO_DATA_MESSAGE,
            data_quality_note=NO_DATA_MESSAGE + " " + EDUCATIONAL_NOTE,
            warnings=[],
        )

    spot_histories = build_spot_history(records)
    items = [_schedule_item(spot, today_date) for spot in spot_histories]

    if due_only:
        items = [item for item in items if item.is_due]

    # Sort: due first, then higher priority, sooner due, lower accuracy.
    items.sort(key=lambda i: (
        not i.is_due, -i.priority, i.days_until_due, i.accuracy))

    if limit is not None and limit >= 0:
        items = items[:limit] if limit else []

    due_count = sum(1 for i in items if i.is_due)
    overdue_count = sum(1 for i in items if i.days_until_due < 0)
    upcoming_count = sum(1 for i in items if not i.is_due)
    total_attempts = sum(s.attempts for s in spot_histories)

    if due_count:
        next_review_note = (
            f"{due_count} spot(s) due now - practise them with "
            "`drill --focus weak`.")
    elif items:
        soonest = min(items, key=lambda i: i.days_until_due)
        next_review_note = (
            f"Nothing due now; next review in {soonest.days_until_due} day(s) "
            f"({soonest.spot_id}).")
    else:
        next_review_note = "Nothing scheduled."

    warnings: list[str] = []
    for item in items:
        warnings.extend(item.warnings)
    warnings = list(dict.fromkeys(warnings))

    return ReviewQueue(
        created_at=created_at,
        profile_key=profile_key,
        total_items=len(items),
        due_count=due_count,
        overdue_count=overdue_count,
        upcoming_count=upcoming_count,
        items=items,
        next_review_note=next_review_note,
        data_quality_note=_data_quality_note(total_attempts, len(spot_histories)),
        warnings=warnings,
    )


def _streak_runs(days: list[date]) -> tuple[int, int]:
    """Return (current_streak, longest_streak) from sorted unique dates.

    The current streak is the consecutive run ending at the most recent date.
    """
    if not days:
        return 0, 0
    longest = 1
    run = 1
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
    # Current streak: trailing consecutive run ending at the last date.
    current = 1
    for prev, curr in zip(reversed(days[:-1]), reversed(days)):
        # iterate from the end backwards
        if (curr - prev).days == 1:
            current += 1
        else:
            break
    return current, longest


def build_drill_streak_summary(
    drill_dir: str | Path | None = None,
    profile_key: str | None = None,
    today: str | date | None = None,
) -> DrillStreakSummary:
    """Build a local practice-streak summary from saved drill sessions."""
    records = list_drill_session_records(
        history_dir=drill_dir, profile_key=profile_key)

    if not records:
        return DrillStreakSummary(
            total_saved_drill_sessions=0,
            active_days=0,
            current_streak_days=0,
            longest_streak_days=0,
            last_practice_date=None,
            newest_session_id=None,
            practice_frequency_note=NO_DATA_MESSAGE + " " + EDUCATIONAL_NOTE,
            warnings=[],
        )

    dates = sorted({
        d for d in (_date_of(r.created_at) for r in records) if d is not None
    })
    current, longest = _streak_runs(dates)
    last_practice = dates[-1].isoformat() if dates else None
    newest = sorted(records, key=lambda r: (r.created_at, r.session_id))[-1]

    note = (
        f"Practised on {len(dates)} day(s); current streak {current} day(s), "
        f"longest {longest}. " + EDUCATIONAL_NOTE
    )

    return DrillStreakSummary(
        total_saved_drill_sessions=len(records),
        active_days=len(dates),
        current_streak_days=current,
        longest_streak_days=longest,
        last_practice_date=last_practice,
        newest_session_id=newest.session_id,
        practice_frequency_note=note,
        warnings=[],
    )


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def _item_line(item: ReviewScheduleItem) -> str:
    cards = ", ".join(item.player_cards) if item.player_cards else "?"
    return (
        f"  {cards} vs {item.dealer_upcard} [{item.mastery_level}, "
        f"acc {_pct(item.accuracy)}] due {item.due_at} - {item.reason}")


def render_review_queue(queue: ReviewQueue) -> str:
    """Render a compact text view of the review queue for the terminal."""
    lines = ["=== Drill Review Queue ==="]
    if queue.total_items == 0:
        lines.append(NO_DATA_MESSAGE)
        lines.append(f"Data quality: {queue.data_quality_note}")
        return "\n".join(lines)

    lines.append(f"Total items : {queue.total_items}")
    lines.append(f"Due now     : {queue.due_count}")
    lines.append(f"Overdue     : {queue.overdue_count}")
    lines.append(f"Upcoming    : {queue.upcoming_count}")

    due_items = [i for i in queue.items if i.is_due]
    upcoming_items = [i for i in queue.items if not i.is_due]

    lines.append("")
    lines.append("-- Due now --")
    if due_items:
        lines.extend(_item_line(i) for i in due_items)
    else:
        lines.append("  (nothing due)")

    lines.append("")
    lines.append("-- Upcoming --")
    if upcoming_items:
        lines.extend(_item_line(i) for i in upcoming_items)
    else:
        lines.append("  (nothing upcoming)")

    lines.append("")
    lines.append(f"Next review : {queue.next_review_note}")
    lines.append(f"Data quality: {queue.data_quality_note}")
    if queue.warnings:
        lines.append("")
        lines.append("-- Warnings --")
        lines.extend(f"  - {w}" for w in queue.warnings)
    lines.append("")
    lines.append("Educational / local practice only - no real bets, no winnings.")
    return "\n".join(lines)


def render_streak_summary(summary: DrillStreakSummary) -> str:
    """Render a compact text view of the practice-streak summary."""
    lines = ["=== Drill Streaks ==="]
    if summary.total_saved_drill_sessions == 0:
        lines.append(NO_DATA_MESSAGE)
        return "\n".join(lines)
    lines.append(f"Current streak : {summary.current_streak_days} day(s)")
    lines.append(f"Longest streak : {summary.longest_streak_days} day(s)")
    lines.append(f"Active days    : {summary.active_days}")
    lines.append(f"Last practice  : {summary.last_practice_date or '(n/a)'}")
    lines.append(f"Saved sessions : {summary.total_saved_drill_sessions}")
    lines.append(f"Note           : {summary.practice_frequency_note}")
    return "\n".join(lines)


def _md_list(items: list[str]) -> list[str]:
    if not items:
        return ["- (none)"]
    return [f"- {item}" for item in items]


def render_review_queue_markdown(
    queue: ReviewQueue,
    streak: DrillStreakSummary | None = None,
) -> str:
    """Render the review queue (and optional streaks) as Markdown."""
    lines = [
        "# Blackjack Coach Pro Demo - Drill Review Queue",
        "",
        f"_Generated: {queue.created_at}_",
        "",
        "## Overview",
        "",
    ]
    if queue.total_items == 0:
        lines.append(NO_DATA_MESSAGE)
        lines += ["", f"_{queue.data_quality_note}_", ""]
        return "\n".join(lines)

    lines += [
        f"- Total items: {queue.total_items}",
        f"- Due now: {queue.due_count}",
        f"- Overdue: {queue.overdue_count}",
        f"- Upcoming: {queue.upcoming_count}",
        f"- Next review: {queue.next_review_note}",
    ]

    due_items = [i for i in queue.items if i.is_due]
    upcoming_items = [i for i in queue.items if not i.is_due]

    def _row(item: ReviewScheduleItem) -> str:
        cards = ", ".join(item.player_cards) if item.player_cards else "?"
        return (
            f"| {cards} vs {item.dealer_upcard} | {item.mastery_level} | "
            f"{_pct(item.accuracy)} | {item.due_at} | {item.reason} |")

    lines += ["", "## Due now", ""]
    if due_items:
        lines.append("| Hand | Mastery | Accuracy | Due | Reason |")
        lines.append("| --- | --- | ---: | --- | --- |")
        lines.extend(_row(i) for i in due_items)
    else:
        lines.append("_Nothing due now._")

    lines += ["", "## Upcoming", ""]
    if upcoming_items:
        lines.append("| Hand | Mastery | Accuracy | Due | Reason |")
        lines.append("| --- | --- | ---: | --- | --- |")
        lines.extend(_row(i) for i in upcoming_items)
    else:
        lines.append("_Nothing upcoming._")

    if streak is not None:
        lines += ["", "## Streaks", ""]
        if streak.total_saved_drill_sessions == 0:
            lines.append("_No saved drill sessions yet._")
        else:
            lines += [
                f"- Current streak: {streak.current_streak_days} day(s)",
                f"- Longest streak: {streak.longest_streak_days} day(s)",
                f"- Active days: {streak.active_days}",
                f"- Last practice: {streak.last_practice_date or '(n/a)'}",
            ]

    lines += ["", "## Data quality", "", f"- {queue.data_quality_note}"]
    if queue.warnings:
        lines.append("")
        lines += _md_list(queue.warnings)
    lines += [
        "",
        "---",
        "",
        "_Educational / local practice only - no real bets, no winnings._",
        "",
    ]
    return "\n".join(lines)


def default_review_queue_dir() -> Path:
    """Return the default local directory for exported review queues."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / REPORTS_SUBDIR


def export_review_queue(
    queue: ReviewQueue,
    streak: DrillStreakSummary | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Render the review queue as Markdown and save it locally; return the path.

    When ``output_path`` is not given a timestamped file is written under
    ``./.blackjack_coach/reports``.
    """
    content = render_review_queue_markdown(queue, streak=streak)
    if output_path is not None:
        path = Path(output_path)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = default_review_queue_dir() / f"review_queue_{stamp}.md"
    return save_report(content, path)
