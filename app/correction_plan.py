"""Correction action plan for Blackjack Coach Pro Demo (v1.29.0).

Turns the missed-spot correction dashboard (v1.28.0) into a concrete, prioritised
action plan: which spots to repeat urgently, which to review, which need more
data, and which only need maintenance - each with a suggested existing command.

Everything stays local and read-only. It never executes any suggested command,
never changes the recommendation, the correct answers, or the Hi-Lo math, and
never duplicates strategy logic (it only reads local summaries). Plans / exports
store no money, bankroll, bets, accounts, tokens, screenshots, or personal data.
Standard library only - no network, no cloud, no database, no external
dependencies. The ``.blackjack_coach/`` tree stays git-ignored. The plan
suggests practice; it never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .correction_dashboard import build_correction_dashboard
from .repeat_pack_history import (
    STATUS_CORRECTED,
    STATUS_IMPROVING,
    STATUS_NEW,
    STATUS_PERSISTENT_MISS,
    build_repeat_spot_progress,
    list_repeat_pack_completion_records,
)
from .reporting import HISTORY_ROOT_DIRNAME, REPORTS_SUBDIR, save_report

# Plan-level focuses.
VALID_FOCUS = ("all", "urgent", "persistent", "improving", "new", "maintenance")

# Action types per correction status.
ACTION_URGENT_REPEAT = "urgent_repeat"
ACTION_FOCUSED_REVIEW = "focused_review"
ACTION_COLLECT_MORE = "collect_more_attempts"
ACTION_MAINTENANCE = "maintenance"
ACTION_REVIEW = "review"

# Status -> plan priority (lower = act sooner).
_PRIORITY = {
    STATUS_PERSISTENT_MISS: 1,
    STATUS_IMPROVING: 2,
    STATUS_NEW: 3,
    STATUS_CORRECTED: 4,
}

EDUCATIONAL_NOTE = (
    "Local correction action plan for self-study only. It never executes "
    "commands, stores no money, bankroll, bets, accounts, tokens, or personal "
    "data, never changes the strategy recommendation or the correct answers, "
    "and never promises results."
)

NO_DATA_MESSAGE = (
    "No correction history yet. Use repeat-pack --complete first."
)


@dataclass(frozen=True)
class CorrectionPlanItem:
    """One prioritised action for a missed spot."""

    item_id: str
    spot_id: str
    profile_key: str | None
    status: str
    priority: int
    action_type: str
    recommended_command: str
    reason: str
    expected_focus: str
    tags: list[str] = field(default_factory=list)
    note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CorrectionActionPlan:
    """A prioritised correction action plan."""

    plan_id: str
    created_at: str
    profile_key: str | None
    total_items: int
    urgent_items: int
    maintenance_items: int
    data_collection_items: int
    items: list[CorrectionPlanItem]
    plan_note: str
    completion_hint: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CorrectionPlanExport:
    """The result of exporting a correction action plan to a file."""

    export_id: str
    created_at: str
    output_path: str
    format: str
    plan: CorrectionActionPlan
    note: str = ""


def classify_plan_action_type(status: str) -> str:
    """Map a correction status to a plan action type."""
    return {
        STATUS_PERSISTENT_MISS: ACTION_URGENT_REPEAT,
        STATUS_IMPROVING: ACTION_FOCUSED_REVIEW,
        STATUS_NEW: ACTION_COLLECT_MORE,
        STATUS_CORRECTED: ACTION_MAINTENANCE,
    }.get(status, ACTION_REVIEW)


def _command_for(action_type: str, profile_key: str | None) -> str:
    """Build a safe, existing command string for an action type."""
    profile_arg = f" --profile {profile_key}" if profile_key else ""
    base = {
        ACTION_URGENT_REPEAT: "blackjack-coach repeat-pack",
        ACTION_FOCUSED_REVIEW: "blackjack-coach drill --focus weak",
        ACTION_COLLECT_MORE: "blackjack-coach drill --focus weak",
        ACTION_MAINTENANCE: "blackjack-coach correction-dashboard",
        ACTION_REVIEW: "blackjack-coach repeat-pack --progress",
    }.get(action_type, "blackjack-coach correction-dashboard")
    return base + profile_arg


def build_recommended_command(item: CorrectionPlanItem) -> str:
    """Return a safe suggested command for a plan item (never executed)."""
    return _command_for(item.action_type, item.profile_key)


_FOCUS_STATUSES = {
    "all": None,
    "urgent": {STATUS_PERSISTENT_MISS},
    "persistent": {STATUS_PERSISTENT_MISS},
    "improving": {STATUS_IMPROVING},
    "new": {STATUS_NEW},
    "maintenance": {STATUS_CORRECTED},
}

_ACTION_REASON = {
    ACTION_URGENT_REPEAT: "Persistent miss - repeat and drill this spot soon.",
    ACTION_FOCUSED_REVIEW: "Improving - a focused review should lock it in.",
    ACTION_COLLECT_MORE: "New / low sample - collect more repeat attempts.",
    ACTION_MAINTENANCE: "Corrected - keep it in light maintenance.",
    ACTION_REVIEW: "Review this spot.",
}


def build_correction_action_plan(
    profile_key: str | None = None,
    repeat_dir: str | Path | None = None,
    limit: int | None = None,
    focus: str = "all",
) -> CorrectionActionPlan:
    """Build a prioritised correction action plan from repeat-pack history.

    Reuses :func:`app.correction_dashboard.build_correction_dashboard` for the
    summary note and the per-spot correction progress for the items. Priority:
    PERSISTENT_MISS -> IMPROVING -> NEW -> CORRECTED. ``focus`` is one of
    all / urgent / persistent / improving / new / maintenance.
    """
    focus = (focus or "all").lower().strip()
    if focus not in VALID_FOCUS:
        raise ValueError(
            f"Unknown focus '{focus}'. Choose one of: " + ", ".join(VALID_FOCUS)
            + ".")

    created_at = datetime.now().isoformat(timespec="seconds")
    records = list_repeat_pack_completion_records(
        history_dir=repeat_dir, limit=limit, profile_key=profile_key)

    if not records:
        return CorrectionActionPlan(
            plan_id=uuid.uuid4().hex[:8],
            created_at=created_at,
            profile_key=profile_key,
            total_items=0,
            urgent_items=0,
            maintenance_items=0,
            data_collection_items=0,
            items=[],
            plan_note=NO_DATA_MESSAGE,
            completion_hint=(
                "Complete a repeat pack with `repeat-pack --complete` to build a "
                "correction plan."),
            warnings=[],
        )

    # The dashboard summary is reused for the plan note / data-quality wording.
    dashboard = build_correction_dashboard(
        profile_key=profile_key, repeat_dir=repeat_dir, limit=limit)
    progress = build_repeat_spot_progress(records)

    allowed = _FOCUS_STATUSES.get(focus)
    items: list[CorrectionPlanItem] = []
    for spot in progress:
        if allowed is not None and spot.status not in allowed:
            continue
        action_type = classify_plan_action_type(spot.status)
        command = _command_for(action_type, spot.profile_key)
        items.append(CorrectionPlanItem(
            item_id=uuid.uuid4().hex[:8],
            spot_id=spot.spot_id,
            profile_key=spot.profile_key,
            status=spot.status,
            priority=_PRIORITY.get(spot.status, 3),
            action_type=action_type,
            recommended_command=command,
            reason=_ACTION_REASON.get(action_type, ACTION_REVIEW),
            expected_focus=spot.spot_id,
            tags=list(spot.tags),
        ))

    items.sort(key=lambda i: (i.priority, i.spot_id))

    urgent_items = sum(1 for i in items if i.action_type == ACTION_URGENT_REPEAT)
    maintenance_items = sum(
        1 for i in items if i.action_type == ACTION_MAINTENANCE)
    data_collection_items = sum(
        1 for i in items if i.action_type == ACTION_COLLECT_MORE)

    plan_note = (
        f"Correction action plan ({focus}); {urgent_items} urgent, "
        f"{maintenance_items} maintenance, {data_collection_items} data "
        f"collection. " + EDUCATIONAL_NOTE)
    completion_hint = (
        "Run the suggested commands yourself, then re-check with "
        "`blackjack-coach correction-dashboard`.")

    warnings = list(dashboard.warnings)

    return CorrectionActionPlan(
        plan_id=uuid.uuid4().hex[:8],
        created_at=created_at,
        profile_key=profile_key,
        total_items=len(items),
        urgent_items=urgent_items,
        maintenance_items=maintenance_items,
        data_collection_items=data_collection_items,
        items=items,
        plan_note=plan_note,
        completion_hint=completion_hint,
        warnings=warnings,
    )


def _section_for(item: CorrectionPlanItem) -> str:
    if item.action_type == ACTION_URGENT_REPEAT:
        return "urgent"
    if item.action_type == ACTION_FOCUSED_REVIEW:
        return "review"
    if item.action_type == ACTION_COLLECT_MORE:
        return "new"
    if item.action_type == ACTION_MAINTENANCE:
        return "maintenance"
    return "review"


def _item_text(item: CorrectionPlanItem) -> str:
    return f"  {item.spot_id} [{item.status}] -> {item.recommended_command}"


def render_correction_plan(plan: CorrectionActionPlan) -> str:
    """Render a compact text view of the correction action plan."""
    lines = ["=== Correction Action Plan ==="]
    if plan.total_items == 0:
        lines.append(plan.plan_note)
        lines.append(f"Hint: {plan.completion_hint}")
        return "\n".join(lines)

    lines.append("")
    lines.append("-- Overview --")
    lines.append(f"Profile           : {plan.profile_key or 'all profiles'}")
    lines.append(f"Total items       : {plan.total_items}")
    lines.append(f"Urgent repeats    : {plan.urgent_items}")
    lines.append(f"Data collection   : {plan.data_collection_items}")
    lines.append(f"Maintenance       : {plan.maintenance_items}")

    sections = [
        ("urgent", "Urgent repeats"),
        ("review", "Focused review"),
        ("new", "New / data collection"),
        ("maintenance", "Maintenance"),
    ]
    for key, title in sections:
        section_items = [i for i in plan.items if _section_for(i) == key]
        if not section_items:
            continue
        lines.append("")
        lines.append(f"-- {title} --")
        lines.extend(_item_text(i) for i in section_items)

    lines.append("")
    lines.append(f"Completion: {plan.completion_hint}")
    if plan.warnings:
        lines.append("")
        lines.append("-- Notes --")
        lines.extend(f"  - {w}" for w in plan.warnings)
    lines.append("")
    lines.append("Educational / local practice only - no real bets, no winnings.")
    return "\n".join(lines)


def render_correction_plan_markdown(plan: CorrectionActionPlan) -> str:
    """Render the correction action plan as a Markdown checklist."""
    lines = [
        "# Blackjack Coach Pro Demo - Correction Action Plan",
        "",
        f"_Generated: {plan.created_at}_",
        "",
        "## Overview",
        "",
    ]
    if plan.total_items == 0:
        lines.append(plan.plan_note)
        lines += ["", f"_{plan.completion_hint}_", ""]
        return "\n".join(lines)

    lines += [
        f"- Profile: {plan.profile_key or 'all profiles'}",
        f"- Total items: {plan.total_items}",
        f"- Urgent repeats: {plan.urgent_items}",
        f"- Data collection: {plan.data_collection_items}",
        f"- Maintenance: {plan.maintenance_items}",
        "",
        "## Action checklist",
        "",
    ]
    for item in plan.items:
        lines.append(
            f"- [ ] {item.spot_id} ({item.status}, {item.action_type}) - "
            f"{item.reason} Run: `{item.recommended_command}`")

    lines += ["", "## Notes", "", f"- {plan.plan_note}", f"- {plan.completion_hint}"]
    if plan.warnings:
        lines.append("")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    lines += [
        "",
        "---",
        "",
        "_Educational / local practice only - no real bets, no winnings._",
        "",
    ]
    return "\n".join(lines)


def default_correction_plan_dir() -> Path:
    """Return the default local directory for exported correction plans."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / REPORTS_SUBDIR


def export_correction_plan(
    plan: CorrectionActionPlan,
    output_path: str | Path | None = None,
) -> CorrectionPlanExport:
    """Render the plan as Markdown and save it locally; return the export."""
    content = render_correction_plan_markdown(plan)
    if output_path is not None:
        path = Path(output_path)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = default_correction_plan_dir() / f"correction_plan_{stamp}.md"
    saved = save_report(content, path)
    return CorrectionPlanExport(
        export_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        output_path=str(saved),
        format="markdown",
        plan=plan,
        note=EDUCATIONAL_NOTE,
    )
