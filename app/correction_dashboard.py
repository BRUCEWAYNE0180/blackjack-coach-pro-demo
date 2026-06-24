"""Missed-spot correction dashboard for Blackjack Coach Pro Demo (v1.28.0).

Reads the repeat-pack completion history (v1.27.0) and shows, locally, which
previously-missed spots have been corrected, which are still failing, which are
improving, and which are new - plus a clear next-practice priority list. It is a
read-only summary built on top of :mod:`app.repeat_pack_history`; it never
changes the recommendation, the correct answers, or the Hi-Lo math.

Everything stays local and read-only. Summaries / exports store no money,
bankroll, bets, accounts, tokens, screenshots, or personal data. Standard
library only - no network, no cloud, no database, no external dependencies. The
``.blackjack_coach/`` tree stays git-ignored. The dashboard summarises practice;
it never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .repeat_pack_history import (
    STATUS_CORRECTED,
    STATUS_IMPROVING,
    STATUS_NEW,
    STATUS_PERSISTENT_MISS,
    RepeatSpotProgress,
    build_repeat_spot_progress,
    list_repeat_pack_completion_records,
    summarize_repeat_pack_history,
)
from .reporting import HISTORY_ROOT_DIRNAME, REPORTS_SUBDIR, save_report

# Below this many repeat-pack completions the dashboard flags a LOW sample.
MIN_RECORDS = 3

EDUCATIONAL_NOTE = (
    "Local missed-spot correction dashboard for self-study only. It stores no "
    "money, bankroll, bets, accounts, tokens, or personal data, never changes "
    "the strategy recommendation or the correct answers, and never promises "
    "results."
)

NO_DATA_MESSAGE = (
    "No saved repeat pack completions yet. Use repeat-pack --complete first."
)

# Stable trend labels per correction status.
TREND_CORRECTED = "corrected"
TREND_IMPROVING = "improving"
TREND_NEEDS_URGENT_REVIEW = "needs urgent review"
TREND_NEEDS_MORE_ATTEMPTS = "needs more attempts"
TREND_INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class CorrectionSpotSummary:
    """A per-spot correction summary for the dashboard."""

    spot_id: str
    profile_key: str | None
    status: str
    attempts: int
    corrected: int
    still_missed: int
    skipped: int
    repeat_accuracy: float
    last_seen_at: str
    priority: int
    trend_label: str
    recommended_next_action: str
    tags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CorrectionDashboardSummary:
    """The full missed-spot correction dashboard."""

    created_at: str
    profile_key: str | None
    total_spots: int
    corrected_count: int
    improving_count: int
    persistent_miss_count: int
    new_count: int
    skipped_count: int
    overall_repeat_accuracy: float
    top_corrected_spots: list[str]
    top_persistent_misses: list[str]
    improving_spots: list[str]
    new_spots: list[str]
    next_practice_priorities: list[str]
    dashboard_note: str
    data_quality_note: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CorrectionDashboardExport:
    """The result of exporting a correction dashboard to a file."""

    export_id: str
    created_at: str
    output_path: str
    format: str
    summary: CorrectionDashboardSummary
    note: str = ""


def classify_correction_trend(spot_progress: RepeatSpotProgress) -> str:
    """Return a stable trend label for a spot's correction progress."""
    if spot_progress.status == STATUS_CORRECTED:
        return TREND_CORRECTED
    if spot_progress.status == STATUS_IMPROVING:
        return TREND_IMPROVING
    if spot_progress.status == STATUS_PERSISTENT_MISS:
        return TREND_NEEDS_URGENT_REVIEW
    if spot_progress.status == STATUS_NEW:
        if spot_progress.skipped > 0 and spot_progress.attempts < 2:
            return TREND_INCOMPLETE
        return TREND_NEEDS_MORE_ATTEMPTS
    return TREND_NEEDS_MORE_ATTEMPTS


# Practise-priority weighting per status (lower = practise sooner).
_STATUS_PRIORITY = {
    STATUS_PERSISTENT_MISS: 1,
    STATUS_IMPROVING: 2,
    STATUS_NEW: 3,
    STATUS_CORRECTED: 4,
}


def _next_action(status: str) -> str:
    return {
        STATUS_PERSISTENT_MISS: "Run repeat-pack and drill this spot soon.",
        STATUS_IMPROVING: "Repeat next session to lock it in.",
        STATUS_NEW: "Collect more repeat attempts.",
        STATUS_CORRECTED: "Maintain later.",
    }.get(status, "Repeat next session.")


def _spot_summary(progress: RepeatSpotProgress) -> CorrectionSpotSummary:
    return CorrectionSpotSummary(
        spot_id=progress.spot_id,
        profile_key=progress.profile_key,
        status=progress.status,
        attempts=progress.attempts,
        corrected=progress.corrected,
        still_missed=progress.still_missed,
        skipped=progress.skipped,
        repeat_accuracy=progress.repeat_accuracy,
        last_seen_at=progress.last_seen_at,
        priority=_STATUS_PRIORITY.get(progress.status, 3),
        trend_label=classify_correction_trend(progress),
        recommended_next_action=_next_action(progress.status),
        tags=list(progress.tags),
    )


def _label(spot: CorrectionSpotSummary) -> str:
    return (
        f"{spot.spot_id} (acc {spot.repeat_accuracy * 100:.0f}%, "
        f"{spot.corrected}/{spot.attempts})")


def build_correction_dashboard(
    profile_key: str | None = None,
    repeat_dir: str | Path | None = None,
    limit: int | None = None,
) -> CorrectionDashboardSummary:
    """Build the missed-spot correction dashboard from repeat-pack completions."""
    records = list_repeat_pack_completion_records(
        history_dir=repeat_dir, limit=limit, profile_key=profile_key)
    created_at = datetime.now().isoformat(timespec="seconds")

    if not records:
        return CorrectionDashboardSummary(
            created_at=created_at,
            profile_key=profile_key,
            total_spots=0,
            corrected_count=0,
            improving_count=0,
            persistent_miss_count=0,
            new_count=0,
            skipped_count=0,
            overall_repeat_accuracy=0.0,
            top_corrected_spots=[],
            top_persistent_misses=[],
            improving_spots=[],
            new_spots=[],
            next_practice_priorities=[],
            dashboard_note=NO_DATA_MESSAGE,
            data_quality_note=NO_DATA_MESSAGE + " " + EDUCATIONAL_NOTE,
            warnings=[],
        )

    progress = build_repeat_spot_progress(records)
    spots = [_spot_summary(p) for p in progress]
    review_summary = summarize_repeat_pack_history(records)

    corrected = [s for s in spots if s.status == STATUS_CORRECTED]
    improving = [s for s in spots if s.status == STATUS_IMPROVING]
    persistent = [s for s in spots if s.status == STATUS_PERSISTENT_MISS]
    new_spots_list = [s for s in spots if s.status == STATUS_NEW]
    skipped_spots = [s for s in spots if s.skipped > 0]

    # Most persistent misses first (most attempts), then improving (mid
    # accuracy), then new (few attempts), then skipped.
    persistent_sorted = sorted(persistent, key=lambda s: -s.attempts)
    improving_sorted = sorted(improving, key=lambda s: s.repeat_accuracy)

    preliminary = CorrectionDashboardSummary(
        created_at=created_at,
        profile_key=profile_key,
        total_spots=len(spots),
        corrected_count=len(corrected),
        improving_count=len(improving),
        persistent_miss_count=len(persistent),
        new_count=len(new_spots_list),
        skipped_count=len(skipped_spots),
        overall_repeat_accuracy=review_summary.overall_repeat_accuracy,
        top_corrected_spots=[_label(s) for s in corrected[:5]],
        top_persistent_misses=[_label(s) for s in persistent_sorted[:5]],
        improving_spots=[_label(s) for s in improving_sorted[:5]],
        new_spots=[_label(s) for s in new_spots_list[:5]],
        next_practice_priorities=[],
        dashboard_note="",
        data_quality_note="",
        warnings=[],
    )

    priorities = recommend_correction_next_actions(preliminary)

    if len(records) < MIN_RECORDS:
        data_quality_note = (
            f"LOW sample: only {len(records)} repeat pack completion(s) "
            f"(< {MIN_RECORDS}); treat the dashboard as indicative. "
            + EDUCATIONAL_NOTE
        )
    else:
        data_quality_note = (
            f"{len(records)} repeat pack completions across {len(spots)} "
            f"spot(s). " + EDUCATIONAL_NOTE)

    dashboard_note = (
        f"{len(corrected)} corrected, {len(improving)} improving, "
        f"{len(persistent)} persistent, {len(new_spots_list)} new. "
        + EDUCATIONAL_NOTE)

    return CorrectionDashboardSummary(
        created_at=created_at,
        profile_key=profile_key,
        total_spots=len(spots),
        corrected_count=len(corrected),
        improving_count=len(improving),
        persistent_miss_count=len(persistent),
        new_count=len(new_spots_list),
        skipped_count=len(skipped_spots),
        overall_repeat_accuracy=review_summary.overall_repeat_accuracy,
        top_corrected_spots=[_label(s) for s in corrected[:5]],
        top_persistent_misses=[_label(s) for s in persistent_sorted[:5]],
        improving_spots=[_label(s) for s in improving_sorted[:5]],
        new_spots=[_label(s) for s in new_spots_list[:5]],
        next_practice_priorities=priorities,
        dashboard_note=dashboard_note,
        data_quality_note=data_quality_note,
        warnings=[],
    )


def recommend_correction_next_actions(
    summary: CorrectionDashboardSummary,
) -> list[str]:
    """Generate concrete next-practice priorities from the dashboard counts."""
    actions: list[str] = []
    if summary.persistent_miss_count:
        actions.append(
            "Run `repeat-pack` for persistent misses - they need urgent review.")
    if summary.new_count:
        actions.append(
            "Use `drill` to collect more attempts on NEW spots.")
    if summary.improving_count:
        actions.append(
            "Repeat IMPROVING spots next session to lock them in.")
    if summary.corrected_count:
        actions.append(
            "Keep CORRECTED spots in light maintenance.")
    if summary.skipped_count:
        actions.append(
            "Avoid skipping persistent misses - complete them next time.")
    if summary.total_spots < MIN_RECORDS:
        actions.append(
            "Low sample - collect more `repeat-pack --complete` records for a "
            "clearer picture.")
    if not actions:
        actions.append(
            "Keep completing repeat packs with `repeat-pack --complete`.")
    return actions


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def _text_list(items: list[str]) -> list[str]:
    if not items:
        return ["  - (none)"]
    return [f"  - {item}" for item in items]


def render_correction_dashboard(summary: CorrectionDashboardSummary) -> str:
    """Render a compact text view of the correction dashboard for the terminal."""
    lines = ["=== Missed-Spot Correction Dashboard ==="]
    if summary.total_spots == 0:
        lines.append(NO_DATA_MESSAGE)
        lines.append(f"Data quality: {summary.data_quality_note}")
        return "\n".join(lines)

    lines.append("")
    lines.append("-- Overview --")
    lines.append(f"Profile          : {summary.profile_key or 'all profiles'}")
    lines.append(f"Total spots      : {summary.total_spots}")
    lines.append(f"Corrected        : {summary.corrected_count}")
    lines.append(f"Improving        : {summary.improving_count}")
    lines.append(f"Persistent misses: {summary.persistent_miss_count}")
    lines.append(f"New / low sample : {summary.new_count}")
    lines.append(f"Skipped          : {summary.skipped_count}")
    lines.append(f"Repeat accuracy  : {_pct(summary.overall_repeat_accuracy)}")

    lines.append("")
    lines.append("-- Corrected --")
    lines.extend(_text_list(summary.top_corrected_spots))
    lines.append("")
    lines.append("-- Improving --")
    lines.extend(_text_list(summary.improving_spots))
    lines.append("")
    lines.append("-- Persistent misses --")
    lines.extend(_text_list(summary.top_persistent_misses))
    lines.append("")
    lines.append("-- New / low sample --")
    lines.extend(_text_list(summary.new_spots))
    lines.append("")
    lines.append("-- Next practice priorities --")
    lines.extend(_text_list(summary.next_practice_priorities))

    lines.append("")
    lines.append(f"Data quality: {summary.data_quality_note}")
    if summary.warnings:
        lines.append("")
        lines.append("-- Warnings --")
        lines.extend(_text_list(summary.warnings))
    lines.append("")
    lines.append("Educational / local practice only - no real bets, no winnings.")
    return "\n".join(lines)


def _md_list(items: list[str]) -> list[str]:
    if not items:
        return ["- (none)"]
    return [f"- {item}" for item in items]


def render_correction_dashboard_markdown(
    summary: CorrectionDashboardSummary,
) -> str:
    """Render the correction dashboard as Markdown for Notion / GitHub."""
    lines = [
        "# Blackjack Coach Pro Demo - Missed-Spot Correction Dashboard",
        "",
        f"_Generated: {summary.created_at}_",
        "",
        "## Overview",
        "",
    ]
    if summary.total_spots == 0:
        lines.append(NO_DATA_MESSAGE)
        lines += ["", f"_{summary.data_quality_note}_", ""]
        return "\n".join(lines)

    lines += [
        f"- Profile: {summary.profile_key or 'all profiles'}",
        f"- Total spots: {summary.total_spots}",
        f"- Repeat accuracy: {_pct(summary.overall_repeat_accuracy)}",
        "",
        "## Status counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
        f"| Corrected | {summary.corrected_count} |",
        f"| Improving | {summary.improving_count} |",
        f"| Persistent misses | {summary.persistent_miss_count} |",
        f"| New / low sample | {summary.new_count} |",
        f"| Skipped | {summary.skipped_count} |",
        "",
        "## Persistent misses",
        "",
    ]
    lines += _md_list(summary.top_persistent_misses)
    lines += ["", "## Corrected spots", ""]
    lines += _md_list(summary.top_corrected_spots)
    lines += ["", "## Improving spots", ""]
    lines += _md_list(summary.improving_spots)
    lines += ["", "## Next practice priorities", ""]
    lines += [f"- [ ] {action}" for action in summary.next_practice_priorities] \
        or ["- (none)"]
    lines += ["", "## Data quality", "", f"- {summary.data_quality_note}"]
    if summary.warnings:
        lines.append("")
        lines += _md_list(summary.warnings)
    lines += [
        "",
        "---",
        "",
        "_Educational / local practice only - no real bets, no winnings._",
        "",
    ]
    return "\n".join(lines)


def default_correction_dashboard_dir() -> Path:
    """Return the default local directory for exported correction dashboards."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / REPORTS_SUBDIR


def export_correction_dashboard(
    summary: CorrectionDashboardSummary,
    output_path: str | Path | None = None,
) -> CorrectionDashboardExport:
    """Render the dashboard as Markdown and save it locally; return the export."""
    content = render_correction_dashboard_markdown(summary)
    if output_path is not None:
        path = Path(output_path)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = default_correction_dashboard_dir() / f"correction_dashboard_{stamp}.md"
    saved = save_report(content, path)
    return CorrectionDashboardExport(
        export_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        output_path=str(saved),
        format="markdown",
        summary=summary,
        note=EDUCATIONAL_NOTE,
    )
