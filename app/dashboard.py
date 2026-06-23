"""Local per-profile training dashboard & trends for Blackjack Coach Pro Demo.

Turns the local history (session history, outcome / win-loss history,
EV-snapshot history, adaptive-learning summary, and Strategy-vs-EV
explanations) into a per-profile dashboard that answers practical questions:
which profile am I practising most, where am I failing, which spots have the
most Strategy-vs-EV disagreements, what should I drill next, and am I improving.

Everything stays local and read-only. The dashboard is a practice aid only - it
never changes the strategy recommendation or the Hi-Lo math, and it stores no
money, bankroll, bets, accounts, tokens, screenshots, or personal data. Standard
library only - no network, no cloud, no database, no external chart libraries
(trends are shown as simple text / Markdown). The ``.blackjack_coach/`` tree
stays git-ignored. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .adaptive_learning import LearningSpot, build_learning_summary
from .ev_history import EVSnapshotRecord, list_ev_snapshot_records, summarize_ev_snapshots
from .outcome_history import (
    OutcomeRecord,
    list_outcome_records,
    summarize_outcomes,
)
from .reporting import (
    HISTORY_ROOT_DIRNAME,
    REPORTS_SUBDIR,
    save_report,
)
from .session_history import (
    SessionRecord,
    list_session_records,
    summarize_history,
)

# Below this many records an area is flagged as limited / LOW sample.
LOW_SAMPLE_THRESHOLD = 10

EDUCATIONAL_NOTE = (
    "Local training dashboard for self-study only. It stores no money, "
    "bankroll, bets, accounts, tokens, or personal data, never changes the "
    "strategy recommendation, and never guarantees winnings."
)

NO_DATA_MESSAGE = (
    "No saved local history yet. Use quiz-session/play/coach-play/odds with "
    "save flags first."
)


@dataclass(frozen=True)
class DashboardProfileSummary:
    """Per-profile training / outcome / EV summary for the dashboard."""

    profile_key: str
    total_sessions: int
    total_outcomes: int
    total_ev_snapshots: int
    session_accuracy: float
    outcome_win_rate: float
    outcome_loss_rate: float
    ev_agreement_rate: float
    top_weak_spots: list[str]
    top_strong_spots: list[str]
    top_ev_disagreements: list[str]
    largest_ev_gaps: list[str]
    recommended_next_drills: list[str]
    data_quality_note: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DashboardTrendPoint:
    """One point in a simple training trend (a recent-sample bucket)."""

    bucket_label: str
    total_sessions: int
    total_outcomes: int
    total_ev_snapshots: int
    session_accuracy: float
    outcome_win_rate: float
    ev_agreement_rate: float
    note: str = ""


@dataclass(frozen=True)
class DashboardSummary:
    """The full local dashboard, grouped by profile, with trends and a plan."""

    created_at: str
    profiles: list[DashboardProfileSummary]
    selected_profile: str | None
    total_sessions: int
    total_outcomes: int
    total_ev_snapshots: int
    best_profile: str | None
    weakest_profile: str | None
    most_practiced_profile: str | None
    trend_points: list[DashboardTrendPoint]
    global_weak_spots: list[str]
    global_ev_disagreements: list[str]
    next_practice_plan: list[str]
    data_quality_note: str
    warnings: list[str] = field(default_factory=list)


def _spot_label(spot: LearningSpot) -> str:
    """A short, safe label for a learning spot (no sensitive data)."""
    return (
        f"{spot.spot_id} (seen {spot.total_seen}, win "
        f"{spot.win_rate * 100:.0f}%, {spot.confidence_label})"
    )


def _readable_spot(spot_id: str) -> str:
    """Turn a spot id like ``hard_16_vs_10`` into ``hard 16 vs 10``."""
    return spot_id.replace("_", " ")


def _limit_recent(records: list, limit: int | None) -> list:
    """Apply an optional most-recent-N limit to a record list."""
    if limit is not None and limit >= 0:
        return records[-limit:] if limit else []
    return records


def _profile_drills(
    weakest: list[LearningSpot],
    ev_disagreement_spots: list[tuple[str, int]],
    largest_gaps: list[tuple[str, float]],
) -> list[str]:
    """Build concrete next-drill suggestions for one profile."""
    drills: list[str] = []
    for spot in weakest[:3]:
        drills.append(f"Practice {_readable_spot(spot.spot_id)}")
    if any("SURRENDER" in label for label, _ in ev_disagreement_spots):
        drills.append("Review surrender spots")
    for label, _ in ev_disagreement_spots[:2]:
        drills.append(f"Review Strategy-vs-EV disagreement at {label}")
    if largest_gaps:
        spot = largest_gaps[0][0]
        drills.append(
            f"Run coach --show-odds --explain-ev on high-gap spot {spot}")
    # De-duplicate while keeping order.
    return list(dict.fromkeys(drills))


def _build_profile_summary(
    profile_key: str,
    session_summary,
    outcome_records: list[OutcomeRecord],
    ev_records: list[EVSnapshotRecord],
) -> DashboardProfileSummary:
    """Assemble a :class:`DashboardProfileSummary` for one profile."""
    outcome_summary = summarize_outcomes(outcome_records)
    ev_summary = summarize_ev_snapshots(ev_records)
    learning_summary = build_learning_summary(outcome_records)

    total_outcomes = outcome_summary.total_records
    win_rate = outcome_summary.wins / total_outcomes if total_outcomes else 0.0
    loss_rate = outcome_summary.losses / total_outcomes if total_outcomes else 0.0

    top_weak = [_spot_label(s) for s in learning_summary.weakest_spots[:5]]
    top_strong = [_spot_label(s) for s in learning_summary.strongest_spots[:5]]
    top_disagreements = [
        f"{label} (x{count})"
        for label, count in ev_summary.disagreement_spots[:5]
    ]
    largest_gaps = [
        f"{label} (~{gap:+.3f})" for label, gap in ev_summary.largest_ev_gaps[:5]
    ]
    drills = _profile_drills(
        learning_summary.weakest_spots,
        ev_summary.disagreement_spots,
        ev_summary.largest_ev_gaps,
    )

    warnings: list[str] = []
    note = _area_quality_note(
        session_summary.total_sessions, total_outcomes,
        ev_summary.total_snapshots)

    return DashboardProfileSummary(
        profile_key=profile_key,
        total_sessions=session_summary.total_sessions,
        total_outcomes=total_outcomes,
        total_ev_snapshots=ev_summary.total_snapshots,
        session_accuracy=session_summary.average_accuracy,
        outcome_win_rate=win_rate,
        outcome_loss_rate=loss_rate,
        ev_agreement_rate=ev_summary.agreement_rate,
        top_weak_spots=top_weak,
        top_strong_spots=top_strong,
        top_ev_disagreements=top_disagreements,
        largest_ev_gaps=largest_gaps,
        recommended_next_drills=drills,
        data_quality_note=note,
        warnings=warnings,
    )


def _area_quality_note(sessions: int, outcomes: int, ev: int) -> str:
    """Build a per-area data-quality note."""
    low = []
    if 0 < outcomes < LOW_SAMPLE_THRESHOLD:
        low.append(f"outcomes ({outcomes})")
    if 0 < ev < LOW_SAMPLE_THRESHOLD:
        low.append(f"EV snapshots ({ev})")
    if 0 < sessions < LOW_SAMPLE_THRESHOLD:
        low.append(f"sessions ({sessions})")
    if low:
        return "LOW sample / limited data in: " + ", ".join(low) + "."
    return f"{outcomes} outcomes, {sessions} sessions, {ev} EV snapshots."


def build_dashboard_trends(
    records: list,
    bucket: str = "recent",
    limit: int | None = None,
) -> list[DashboardTrendPoint]:
    """Build a simple training trend from a mixed list of saved records.

    ``records`` may mix :class:`SessionRecord`, :class:`OutcomeRecord`, and
    :class:`EVSnapshotRecord`. They are sorted by ``created_at`` (best-effort;
    formats can vary), optionally limited to the most recent ``limit``, then
    split into up to three contiguous "recent" buckets (``recent_1`` oldest ..
    ``recent_3`` newest). Each bucket reuses the existing summarisers for its
    accuracy / win-rate / agreement-rate. Returns an empty list when there are
    no records.
    """
    if not records:
        return []

    ordered = sorted(records, key=lambda r: getattr(r, "created_at", "") or "")
    ordered = _limit_recent(ordered, limit)
    if not ordered:
        return []

    num_buckets = min(3, len(ordered))
    # Ceiling division so the last bucket holds any remainder.
    size = (len(ordered) + num_buckets - 1) // num_buckets
    points: list[DashboardTrendPoint] = []
    for index in range(num_buckets):
        chunk = ordered[index * size:(index + 1) * size]
        if not chunk:
            continue
        sessions = [r for r in chunk if isinstance(r, SessionRecord)]
        outcomes = [r for r in chunk if isinstance(r, OutcomeRecord)]
        evs = [r for r in chunk if isinstance(r, EVSnapshotRecord)]

        session_acc = summarize_history(sessions).average_accuracy if sessions else 0.0
        if outcomes:
            outcome_summary = summarize_outcomes(outcomes)
            win_rate = (
                outcome_summary.wins / outcome_summary.total_records
                if outcome_summary.total_records else 0.0
            )
        else:
            win_rate = 0.0
        agreement = summarize_ev_snapshots(evs).agreement_rate if evs else 0.0

        points.append(DashboardTrendPoint(
            bucket_label=f"recent_{index + 1}",
            total_sessions=len(sessions),
            total_outcomes=len(outcomes),
            total_ev_snapshots=len(evs),
            session_accuracy=session_acc,
            outcome_win_rate=win_rate,
            ev_agreement_rate=agreement,
            note=(
                f"{len(sessions)} sessions, {len(outcomes)} outcomes, "
                f"{len(evs)} EV snapshots"
            ),
        ))
    return points


def recommend_next_practice_plan(dashboard: DashboardSummary) -> list[str]:
    """Build a concrete next-practice plan from a (preliminary) dashboard.

    Uses weak spots, low session accuracy, high EV-disagreement spots, and high
    loss rate. When there is little data it asks the user to save more history
    first. It only suggests practice - it never changes the strategy.
    """
    total = (dashboard.total_sessions + dashboard.total_outcomes
             + dashboard.total_ev_snapshots)
    if total == 0:
        return [NO_DATA_MESSAGE]

    plan: list[str] = []

    # Focus on the selected profile when given, else the most-practised one.
    focus_key = dashboard.selected_profile or dashboard.most_practiced_profile
    focus = next(
        (p for p in dashboard.profiles if p.profile_key == focus_key), None)
    if focus is None and dashboard.profiles:
        focus = dashboard.profiles[0]

    if focus is not None:
        plan.extend(focus.recommended_next_drills)
        if focus.total_outcomes and focus.outcome_loss_rate > 0.55:
            plan.append(
                f"Loss rate is high on {focus.profile_key} "
                f"({focus.outcome_loss_rate * 100:.0f}%); review the weak spots "
                "above with `audit` and `diagnose`.")
        if focus.total_sessions and focus.session_accuracy < 0.8:
            plan.append(
                f"Session accuracy is {focus.session_accuracy * 100:.0f}%; run "
                "more `quiz-session` drills to push it up.")

    # Global signals.
    for label in dashboard.global_ev_disagreements[:2]:
        plan.append(f"Review Strategy-vs-EV disagreement at {label}")

    if len(plan) < 2:
        plan.append(
            "Keep saving sessions, outcomes, and EV snapshots to sharpen these "
            "recommendations.")

    # Low-data nudge.
    if total < LOW_SAMPLE_THRESHOLD:
        plan.append(
            "Limited data so far - save more sessions/outcomes/snapshots for a "
            "more reliable plan.")

    return list(dict.fromkeys(plan))


def _global_weak_spots(outcome_records: list[OutcomeRecord]) -> list[str]:
    """Top global weak spots across all profiles."""
    summary = build_learning_summary(outcome_records)
    return [_spot_label(s) for s in summary.weakest_spots[:5]]


def _global_ev_disagreements(ev_records: list[EVSnapshotRecord]) -> list[str]:
    """Top global Strategy-vs-EV disagreement spots across all profiles."""
    summary = summarize_ev_snapshots(ev_records)
    return [f"{label} (x{count})" for label, count in summary.disagreement_spots[:5]]


def _pick_best_weakest(
    profiles: list[DashboardProfileSummary],
) -> tuple[str | None, str | None]:
    """Pick the best / weakest profile by outcome win rate (needs outcomes)."""
    scored = [p for p in profiles if p.total_outcomes > 0]
    if not scored:
        return None, None
    best = max(scored, key=lambda p: (p.outcome_win_rate, p.total_outcomes))
    weakest = min(scored, key=lambda p: (p.outcome_win_rate, -p.total_outcomes))
    return best.profile_key, weakest.profile_key


def build_profile_dashboard(
    profile_key: str | None = None,
    session_dir: str | Path | None = None,
    outcome_dir: str | Path | None = None,
    ev_dir: str | Path | None = None,
    limit: int | None = None,
) -> DashboardSummary:
    """Build the local per-profile :class:`DashboardSummary`.

    Loads the session, outcome, and EV-snapshot history, groups outcomes and EV
    snapshots by ``profile_key`` (sessions are not profile-scoped and are shown
    globally), and combines the existing summarisers per profile. When
    ``profile_key`` is given the dashboard is scoped to that profile.
    """
    session_records = _limit_recent(list_session_records(session_dir), limit)
    outcome_records = list_outcome_records(
        history_dir=outcome_dir, limit=limit, profile_key=profile_key)
    ev_records = list_ev_snapshot_records(
        history_dir=ev_dir, limit=limit, profile_key=profile_key)

    session_summary = summarize_history(session_records)

    # The set of profiles present in outcomes + EV snapshots.
    profile_keys = sorted(
        {r.profile_key for r in outcome_records}
        | {r.profile_key for r in ev_records}
    )

    profiles: list[DashboardProfileSummary] = []
    for key in profile_keys:
        p_outcomes = [r for r in outcome_records if r.profile_key == key]
        p_evs = [r for r in ev_records if r.profile_key == key]
        profiles.append(_build_profile_summary(
            key, session_summary, p_outcomes, p_evs))

    total_outcomes = len(outcome_records)
    total_ev = len(ev_records)
    total_sessions = session_summary.total_sessions

    most_practiced = None
    if profiles:
        most_practiced = max(
            profiles,
            key=lambda p: (p.total_outcomes + p.total_ev_snapshots,
                           p.profile_key),
        ).profile_key
    best_profile, weakest_profile = _pick_best_weakest(profiles)

    trend_points = build_dashboard_trends(
        [*session_records, *outcome_records, *ev_records])

    global_weak = _global_weak_spots(outcome_records)
    global_disagreements = _global_ev_disagreements(ev_records)

    warnings: list[str] = []
    if total_sessions and len(profiles) > 1:
        warnings.append(
            "Sessions are not profile-scoped; session stats are shown globally "
            "for every profile.")

    data_quality_note = _dashboard_quality_note(
        total_sessions, total_outcomes, total_ev)

    dashboard = DashboardSummary(
        created_at=datetime.now().isoformat(timespec="seconds"),
        profiles=profiles,
        selected_profile=profile_key,
        total_sessions=total_sessions,
        total_outcomes=total_outcomes,
        total_ev_snapshots=total_ev,
        best_profile=best_profile,
        weakest_profile=weakest_profile,
        most_practiced_profile=most_practiced,
        trend_points=trend_points,
        global_weak_spots=global_weak,
        global_ev_disagreements=global_disagreements,
        next_practice_plan=[],
        data_quality_note=data_quality_note,
        warnings=warnings,
    )
    # Compute the plan from the assembled dashboard, then attach it.
    plan = recommend_next_practice_plan(dashboard)
    return dataclasses.replace(dashboard, next_practice_plan=plan)


def _dashboard_quality_note(sessions: int, outcomes: int, ev: int) -> str:
    """Build the top-level dashboard data-quality note."""
    if sessions == 0 and outcomes == 0 and ev == 0:
        return NO_DATA_MESSAGE + " " + EDUCATIONAL_NOTE
    low = []
    if 0 < outcomes < LOW_SAMPLE_THRESHOLD:
        low.append(f"outcomes ({outcomes})")
    if 0 < ev < LOW_SAMPLE_THRESHOLD:
        low.append(f"EV snapshots ({ev})")
    if 0 < sessions < LOW_SAMPLE_THRESHOLD:
        low.append(f"sessions ({sessions})")
    if low:
        return (
            "LOW sample / limited data in: " + ", ".join(low)
            + ". Treat trends as indicative, not conclusive. " + EDUCATIONAL_NOTE
        )
    return (
        f"{outcomes} outcomes, {sessions} sessions, {ev} EV snapshots. "
        + EDUCATIONAL_NOTE
    )


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _text_list(items: list[str], indent: str = "  - ") -> list[str]:
    if not items:
        return [f"{indent}(none)"]
    return [f"{indent}{item}" for item in items]


def render_dashboard_text(dashboard: DashboardSummary) -> str:
    """Render the dashboard as a compact text summary for the terminal."""
    d = dashboard
    lines = ["=== Dashboard overview ==="]
    if (d.total_sessions == 0 and d.total_outcomes == 0
            and d.total_ev_snapshots == 0):
        lines.append(NO_DATA_MESSAGE)
        lines.append(f"Data quality: {d.data_quality_note}")
        return "\n".join(lines)

    lines += [
        f"Generated         : {d.created_at}",
        f"Total sessions    : {d.total_sessions}",
        f"Total outcomes    : {d.total_outcomes}",
        f"Total EV snapshots: {d.total_ev_snapshots}",
        f"Most practiced    : {d.most_practiced_profile or '(n/a)'}",
        f"Best profile      : {d.best_profile or '(n/a)'}",
        f"Weakest profile   : {d.weakest_profile or '(n/a)'}",
        "",
        "-- Profiles --",
    ]
    for p in d.profiles:
        lines.append(
            f"  {p.profile_key}: {p.total_outcomes} outcomes "
            f"(win {_pct(p.outcome_win_rate)}), {p.total_ev_snapshots} EV "
            f"(agree {_pct(p.ev_agreement_rate)})")
    if not d.profiles:
        lines.append("  (no profile-scoped outcomes or EV snapshots yet)")

    if d.selected_profile:
        lines.append("")
        lines.append(f"-- Selected profile: {d.selected_profile} --")
        selected = next(
            (p for p in d.profiles if p.profile_key == d.selected_profile), None)
        if selected is None:
            lines.append("  (no saved data for this profile yet)")
        else:
            lines.append(f"  Session accuracy : {_pct(selected.session_accuracy)}")
            lines.append(f"  Win / loss rate  : {_pct(selected.outcome_win_rate)} "
                         f"/ {_pct(selected.outcome_loss_rate)}")
            lines.append(f"  EV agreement     : {_pct(selected.ev_agreement_rate)}")

    lines.append("")
    lines.append("-- Trends (recent buckets) --")
    if d.trend_points:
        for tp in d.trend_points:
            lines.append(
                f"  {tp.bucket_label}: acc {_pct(tp.session_accuracy)}, win "
                f"{_pct(tp.outcome_win_rate)}, EV agree "
                f"{_pct(tp.ev_agreement_rate)} ({tp.note})")
    else:
        lines.append("  (not enough data for trends yet)")

    lines.append("")
    lines.append("-- Weak spots --")
    lines += _text_list(d.global_weak_spots)

    lines.append("")
    lines.append("-- EV disagreements --")
    lines += _text_list(d.global_ev_disagreements)

    lines.append("")
    lines.append("-- Next practice plan --")
    lines += _text_list(d.next_practice_plan)
    lines.append("")
    lines.append("Run `blackjack-coach drill --focus weak` to practice these spots.")
    lines.append("Run `blackjack-coach drill --review` to see drill mastery.")

    lines.append("")
    lines.append(f"Data quality: {d.data_quality_note}")
    if d.warnings:
        lines.append("")
        lines.append("-- Warnings --")
        lines += _text_list(d.warnings)
    lines.append("")
    lines.append("Educational / local practice only - no real bets, no winnings.")
    return "\n".join(lines)


def _md_list(items: list[str]) -> list[str]:
    if not items:
        return ["- (none)"]
    return [f"- {item}" for item in items]


def render_dashboard_markdown(dashboard: DashboardSummary) -> str:
    """Render the dashboard as Markdown for saving or pasting into Notion."""
    d = dashboard
    lines = [
        "# Blackjack Coach Pro Demo - Profile Dashboard",
        "",
        f"_Generated: {d.created_at}_",
        "",
        "## Dashboard overview",
        "",
    ]
    if (d.total_sessions == 0 and d.total_outcomes == 0
            and d.total_ev_snapshots == 0):
        lines.append(NO_DATA_MESSAGE)
        lines += ["", f"_{d.data_quality_note}_", ""]
        return "\n".join(lines)

    lines += [
        f"- Total sessions: {d.total_sessions}",
        f"- Total outcomes: {d.total_outcomes}",
        f"- Total EV snapshots: {d.total_ev_snapshots}",
        f"- Most practiced profile: {d.most_practiced_profile or '(n/a)'}",
        f"- Best profile: {d.best_profile or '(n/a)'}",
        f"- Weakest profile: {d.weakest_profile or '(n/a)'}",
        "",
        "## Profiles",
        "",
        "| Profile | Outcomes | Win rate | EV snapshots | EV agreement |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for p in d.profiles:
        lines.append(
            f"| {p.profile_key} | {p.total_outcomes} | "
            f"{_pct(p.outcome_win_rate)} | {p.total_ev_snapshots} | "
            f"{_pct(p.ev_agreement_rate)} |")
    if not d.profiles:
        lines.append("| (none) | 0 | 0.0% | 0 | 0.0% |")

    if d.selected_profile:
        lines += ["", f"## Selected profile: {d.selected_profile}", ""]
        selected = next(
            (p for p in d.profiles if p.profile_key == d.selected_profile), None)
        if selected is None:
            lines.append("_No saved data for this profile yet._")
        else:
            lines += [
                f"- Session accuracy: {_pct(selected.session_accuracy)}",
                f"- Win rate: {_pct(selected.outcome_win_rate)}",
                f"- Loss rate: {_pct(selected.outcome_loss_rate)}",
                f"- EV agreement: {_pct(selected.ev_agreement_rate)}",
                "",
                "_Recommended drills:_",
                "",
            ]
            lines += _md_list(selected.recommended_next_drills)

    lines += ["", "## Trends", ""]
    if d.trend_points:
        lines.append("| Bucket | Sessions | Outcomes | EV | Accuracy | Win rate | EV agreement |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for tp in d.trend_points:
            lines.append(
                f"| {tp.bucket_label} | {tp.total_sessions} | "
                f"{tp.total_outcomes} | {tp.total_ev_snapshots} | "
                f"{_pct(tp.session_accuracy)} | {_pct(tp.outcome_win_rate)} | "
                f"{_pct(tp.ev_agreement_rate)} |")
    else:
        lines.append("_Not enough data for trends yet._")

    lines += ["", "## Weak spots", ""]
    lines += _md_list(d.global_weak_spots)
    lines += ["", "## EV disagreements", ""]
    lines += _md_list(d.global_ev_disagreements)
    lines += ["", "## Next practice plan", ""]
    lines += _md_list(d.next_practice_plan)
    lines += [
        "",
        "_Run `blackjack-coach drill --focus weak` to practice these spots._",
        "_Run `blackjack-coach drill --review` to see drill mastery._",
    ]
    lines += ["", "## Data quality", "", f"- {d.data_quality_note}"]
    if d.warnings:
        lines.append("")
        lines += _md_list(d.warnings)
    lines += [
        "",
        "---",
        "",
        "_Educational / local practice only - no real bets, no winnings._",
        "",
    ]
    return "\n".join(lines)


def default_dashboard_dir() -> Path:
    """Return the default local dashboard directory (under the reports tree)."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / REPORTS_SUBDIR


def export_dashboard(
    dashboard: DashboardSummary,
    output_path: str | Path | None = None,
) -> Path:
    """Render the dashboard as Markdown and save it locally; return the path.

    When ``output_path`` is not given a timestamped file is written under
    ``./.blackjack_coach/reports``.
    """
    content = render_dashboard_markdown(dashboard)
    if output_path is not None:
        path = Path(output_path)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = default_dashboard_dir() / f"dashboard_{stamp}.md"
    return save_report(content, path)
