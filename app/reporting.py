"""Exportable local-learning reports for Blackjack Coach Pro Demo (v1.19.0).

Combines the local session history, outcome / win-loss history, EV-snapshot
history, adaptive-learning summary, and Strategy-vs-EV explanations into a single
report that can be exported as Markdown, JSON, or CSV. Useful for reviewing
progress, saving to Notion / GitHub, or sharing a training summary.

Everything stays local and read-only. Reports are a safe summary only - no
money, bankroll, real bets, accounts, tokens, screenshots, or any
sensitive/personal data, and no private filesystem paths beyond the report's own
output location. Standard library only - no network, no cloud, no database, no
external dependencies. The ``.blackjack_coach/`` tree (history and reports)
stays git-ignored. This never changes the strategy recommendation or the Hi-Lo
math. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .adaptive_learning import LearningSpot, build_learning_summary
from .ev_explainer import summarize_disagreement_explanations
from .ev_history import list_ev_snapshot_records, summarize_ev_snapshots
from .outcome_history import list_outcome_records, summarize_outcomes
from .session_history import list_session_records, summarize_history

# Report files live under the git-ignored .blackjack_coach/ tree.
HISTORY_ROOT_DIRNAME = ".blackjack_coach"
REPORTS_SUBDIR = "reports"

# Below this many records a section is flagged as limited / LOW sample.
LOW_SAMPLE_THRESHOLD = 10

SUPPORTED_FORMATS = ("markdown", "json", "csv")
_FORMAT_EXTENSIONS = {"markdown": ".md", "json": ".json", "csv": ".csv"}

EDUCATIONAL_NOTE = (
    "Local training report for self-study only. It stores no money, bankroll, "
    "bets, accounts, tokens, or personal data, never changes the strategy "
    "recommendation, and never guarantees winnings."
)


@dataclass(frozen=True)
class ReportSummary:
    """A combined, export-ready summary of the local learning history."""

    created_at: str
    profile_key: str | None
    total_sessions: int
    total_outcomes: int
    total_ev_snapshots: int
    session_accuracy: float
    outcome_win_rate: float
    outcome_loss_rate: float
    ev_agreement_rate: float
    weakest_spots: list[str]
    strongest_spots: list[str]
    largest_ev_gaps: list[str]
    practice_recommendations: list[str]
    data_quality_note: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExportedReport:
    """The result of exporting a report to a file."""

    report_id: str
    created_at: str
    format: str
    output_path: str
    summary: ReportSummary
    note: str = ""


def default_reports_dir() -> Path:
    """Return the default local reports directory (under the current dir)."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / REPORTS_SUBDIR


def _spot_label(spot: LearningSpot) -> str:
    """A short, safe label for a learning spot (no sensitive data)."""
    return (
        f"{spot.spot_id} (seen {spot.total_seen}, win "
        f"{spot.win_rate * 100:.0f}%, {spot.confidence_label})"
    )


def _limit_sessions(records: list, limit: int | None) -> list:
    """Apply an optional most-recent-N limit to session records."""
    if limit is not None and limit >= 0:
        return records[-limit:] if limit else []
    return records


def build_report_summary(
    profile_key: str | None = None,
    session_dir: str | Path | None = None,
    outcome_dir: str | Path | None = None,
    ev_dir: str | Path | None = None,
    limit: int | None = None,
) -> ReportSummary:
    """Build a combined :class:`ReportSummary` from the local history.

    Loads the session history, outcome history, and EV-snapshot history, applies
    the ``profile_key`` / ``limit`` filters where supported, and combines the
    per-area summaries (``summarize_history``, ``summarize_outcomes``,
    ``summarize_ev_snapshots``, ``build_learning_summary``, and
    ``summarize_disagreement_explanations``). Sessions are not profile-scoped, so
    ``profile_key`` only filters outcomes and EV snapshots.
    """
    session_records = _limit_sessions(
        list_session_records(session_dir), limit)
    outcome_records = list_outcome_records(
        history_dir=outcome_dir, limit=limit, profile_key=profile_key)
    ev_records = list_ev_snapshot_records(
        history_dir=ev_dir, limit=limit, profile_key=profile_key)

    history_summary = summarize_history(session_records)
    outcome_summary = summarize_outcomes(outcome_records)
    ev_summary = summarize_ev_snapshots(ev_records)
    learning_summary = build_learning_summary(outcome_records)

    total_sessions = history_summary.total_sessions
    total_outcomes = outcome_summary.total_records
    total_ev = ev_summary.total_snapshots

    win_rate = (
        outcome_summary.wins / total_outcomes if total_outcomes else 0.0)
    loss_rate = (
        outcome_summary.losses / total_outcomes if total_outcomes else 0.0)

    weakest = [_spot_label(s) for s in learning_summary.weakest_spots]
    strongest = [_spot_label(s) for s in learning_summary.strongest_spots]
    largest_gaps = [
        f"{label} (~{gap:+.3f})"
        for label, gap in ev_summary.largest_ev_gaps
    ]

    # Combine practice recommendations from adaptive learning, EV review, and
    # (when there are EV snapshots) the Strategy-vs-EV explanation review.
    recommendations: list[str] = []
    recommendations.extend(learning_summary.practice_recommendations)
    recommendations.extend(ev_summary.practice_recommendations)
    if ev_records:
        explanation_summary = summarize_disagreement_explanations(ev_records)
        recommendations.extend(explanation_summary.review_notes)
    # De-duplicate while preserving order.
    recommendations = list(dict.fromkeys(recommendations))

    warnings: list[str] = []
    warnings.extend(ev_summary.warnings)
    warnings.extend(learning_summary.warnings)
    warnings = list(dict.fromkeys(warnings))

    data_quality_note = _data_quality_note(
        total_sessions, total_outcomes, total_ev)

    return ReportSummary(
        created_at=datetime.now().isoformat(timespec="seconds"),
        profile_key=profile_key,
        total_sessions=total_sessions,
        total_outcomes=total_outcomes,
        total_ev_snapshots=total_ev,
        session_accuracy=history_summary.average_accuracy,
        outcome_win_rate=win_rate,
        outcome_loss_rate=loss_rate,
        ev_agreement_rate=ev_summary.agreement_rate,
        weakest_spots=weakest,
        strongest_spots=strongest,
        largest_ev_gaps=largest_gaps,
        practice_recommendations=recommendations,
        data_quality_note=data_quality_note,
        warnings=warnings,
    )


def _data_quality_note(sessions: int, outcomes: int, ev: int) -> str:
    """Build a clear data-quality note for the combined report."""
    if sessions == 0 and outcomes == 0 and ev == 0:
        return (
            "No saved local history yet. Run scored sessions "
            "(`quiz-session --save`), play hands (`play/coach-play "
            "--save-outcome`), or save EV snapshots (`odds/coach "
            "--save-ev-snapshot`) first. " + EDUCATIONAL_NOTE
        )
    low_areas = []
    if 0 < outcomes < LOW_SAMPLE_THRESHOLD:
        low_areas.append(f"outcomes ({outcomes})")
    if 0 < ev < LOW_SAMPLE_THRESHOLD:
        low_areas.append(f"EV snapshots ({ev})")
    if 0 < sessions < LOW_SAMPLE_THRESHOLD:
        low_areas.append(f"sessions ({sessions})")
    if low_areas:
        return (
            "LOW sample / limited data in: " + ", ".join(low_areas)
            + ". Treat trends as indicative, not conclusive. " + EDUCATIONAL_NOTE
        )
    return f"{outcomes} outcomes, {sessions} sessions, {ev} EV snapshots. " \
           + EDUCATIONAL_NOTE


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _md_list(items: list[str]) -> list[str]:
    """Render a Markdown bullet list (or a placeholder when empty)."""
    if not items:
        return ["- (none)"]
    return [f"- {item}" for item in items]


def render_report_markdown(summary: ReportSummary) -> str:
    """Render a :class:`ReportSummary` as readable Markdown."""
    profile = summary.profile_key or "all profiles"
    lines = [
        "# Blackjack Coach Pro Demo - Learning Report",
        "",
        f"_Generated: {summary.created_at}_",
        "",
        "## Overview",
        "",
        f"- Profile scope: {profile}",
        f"- Sessions: {summary.total_sessions}",
        f"- Outcomes: {summary.total_outcomes}",
        f"- EV snapshots: {summary.total_ev_snapshots}",
        "",
        "## Session training",
        "",
        f"- Average accuracy: {_pct(summary.session_accuracy)}",
        "",
        "## Outcome history",
        "",
        f"- Win rate: {_pct(summary.outcome_win_rate)}",
        f"- Loss rate: {_pct(summary.outcome_loss_rate)}",
        "",
        "## EV snapshots",
        "",
        f"- EV agreement rate: {_pct(summary.ev_agreement_rate)}",
        "",
        "## Strategy-vs-EV review",
        "",
        "_Largest advisory EV gaps (recommendation stands; EV is advisory):_",
        "",
    ]
    lines += _md_list(summary.largest_ev_gaps)
    lines += [
        "",
        "## Weak spots",
        "",
        "_Weakest spots:_",
        "",
    ]
    lines += _md_list(summary.weakest_spots)
    lines += ["", "_Strongest spots:_", ""]
    lines += _md_list(summary.strongest_spots)
    lines += [
        "",
        "## Practice recommendations",
        "",
    ]
    lines += _md_list(summary.practice_recommendations)
    lines += [
        "",
        "## Data quality / warnings",
        "",
        f"- {summary.data_quality_note}",
    ]
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


def render_report_json(summary: ReportSummary) -> str:
    """Render a :class:`ReportSummary` as pretty, safe JSON."""
    return json.dumps(asdict(summary), indent=2, sort_keys=True)


def render_report_csv(summary: ReportSummary) -> str:
    """Render a :class:`ReportSummary` as a compact key,value CSV (stdlib)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["key", "value"])
    data = asdict(summary)
    for key in (
        "created_at", "profile_key", "total_sessions", "total_outcomes",
        "total_ev_snapshots", "session_accuracy", "outcome_win_rate",
        "outcome_loss_rate", "ev_agreement_rate", "data_quality_note",
    ):
        value = data.get(key)
        writer.writerow([key, "" if value is None else value])
    for key in (
        "weakest_spots", "strongest_spots", "largest_ev_gaps",
        "practice_recommendations", "warnings",
    ):
        items = data.get(key) or []
        writer.writerow([key, " | ".join(str(item) for item in items)])
    return buffer.getvalue()


_RENDERERS = {
    "markdown": render_report_markdown,
    "json": render_report_json,
    "csv": render_report_csv,
}


def save_report(content: str, output_path: str | Path) -> Path:
    """Write ``content`` to ``output_path`` (creating parent dirs) and return it."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _default_output_path(report_format: str) -> Path:
    """Build the default timestamped report path for a format."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = _FORMAT_EXTENSIONS[report_format]
    return default_reports_dir() / f"report_{stamp}{extension}"


def export_report(
    format: str = "markdown",
    output_path: str | Path | None = None,
    profile_key: str | None = None,
    session_dir: str | Path | None = None,
    outcome_dir: str | Path | None = None,
    ev_dir: str | Path | None = None,
    limit: int | None = None,
) -> ExportedReport:
    """Build, render, and save a local learning report.

    ``format`` is one of ``markdown`` / ``json`` / ``csv``. When ``output_path``
    is not given, a timestamped file is written under
    ``./.blackjack_coach/reports``. Raises :class:`ValueError` for an unknown
    format.
    """
    report_format = format.lower().strip()
    if report_format not in _RENDERERS:
        raise ValueError(
            f"Unknown report format '{format}'. Choose one of: "
            + ", ".join(SUPPORTED_FORMATS) + "."
        )

    summary = build_report_summary(
        profile_key=profile_key,
        session_dir=session_dir,
        outcome_dir=outcome_dir,
        ev_dir=ev_dir,
        limit=limit,
    )
    content = _RENDERERS[report_format](summary)

    path = (
        Path(output_path) if output_path is not None
        else _default_output_path(report_format)
    )
    saved_path = save_report(content, path)

    return ExportedReport(
        report_id=uuid.uuid4().hex[:8],
        created_at=summary.created_at,
        format=report_format,
        output_path=str(saved_path),
        summary=summary,
        note=EDUCATIONAL_NOTE,
    )
