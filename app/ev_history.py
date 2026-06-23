"""Local EV-snapshot history & Strategy-vs-EV review for Blackjack Coach Pro Demo.

Saves a small JSON snapshot of the probability / EV advisory for a hand so the
coach can later review when its main recommendation *agreed* with the best-EV
advisory action and when it *differed*. This improves local self-study and the
transparency of the advisor - it never changes the main strategy recommendation,
never overrides ``strategy_engine.recommend``, and never touches the Hi-Lo math.

This is a *summary only*: it stores no money, bankroll, real bets, accounts,
tokens, screenshots, or any sensitive/personal data. Standard library only - no
database, no network, no cloud. The ``.blackjack_coach/`` tree stays
git-ignored. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for type hints; avoids any import surprises
    from .probability_advisor import (
        CompositionAwareProbabilityAdvice,
        ProbabilityAdvice,
    )

# Folder layout for locally stored EV snapshots (kept out of version control via
# the repository .gitignore, which ignores the whole .blackjack_coach/ tree).
HISTORY_ROOT_DIRNAME = ".blackjack_coach"
EV_SNAPSHOTS_SUBDIR = "ev_snapshots"

# Below this many snapshots the review's data-quality note flags a LOW sample:
# there is simply not enough local history to read agreement patterns into.
MIN_SNAPSHOT_SAMPLE = 10

EDUCATIONAL_NOTE = (
    "EV snapshots are a local advisory audit for self-study only. They store no "
    "money, bankroll, bets, accounts, or personal data, never override the main "
    "strategy recommendation, and never guarantee winnings."
)

# Field names that must never be persisted in a snapshot (defence in depth: the
# record dataclass already excludes them, and tests assert they never appear).
FORBIDDEN_FIELDS = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "bet", "bets", "wager", "wagers", "password", "secret", "screenshot",
)


@dataclass(frozen=True)
class EVSnapshotRecord:
    """A persisted snapshot comparing the main recommendation with the best EV.

    Advisory only - it records *what the advisor estimated* for one hand so the
    user can later review agreement / disagreement. It never changes play.
    """

    snapshot_id: str
    created_at: str
    profile_key: str
    player_cards: tuple[str, ...]
    dealer_upcard: str
    decks: int
    true_count: float | None
    seen_cards: tuple[str, ...]
    recommended_action: str
    best_estimated_action: str | None
    ev_by_action: dict[str, float | None]
    strategy_ev: float | None
    best_ev: float | None
    ev_gap: float | None
    agrees_with_strategy: bool
    has_split_ev: bool
    has_decision_tree: bool
    composition_aware: bool
    exactness_note: str = ""
    approximation_note: str = ""
    warnings: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class EVReviewSummary:
    """Aggregate Strategy-vs-EV statistics across a set of snapshots."""

    total_snapshots: int
    agreement_count: int
    disagreement_count: int
    agreement_rate: float
    most_common_profile: str
    most_common_recommended_actions: list[tuple[str, int]]
    most_common_best_ev_actions: list[tuple[str, int]]
    largest_ev_gaps: list[tuple[str, float]]
    disagreement_spots: list[tuple[str, int]]
    practice_recommendations: list[str] = field(default_factory=list)
    data_quality_note: str = ""
    warnings: list[str] = field(default_factory=list)


def default_ev_history_dir() -> Path:
    """Return the default local EV-snapshot directory (under the current dir)."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / EV_SNAPSHOTS_SUBDIR


def ensure_ev_history_dir(path: str | Path | None = None) -> Path:
    """Create the EV-snapshot directory if needed and return it as a Path."""
    directory = Path(path) if path is not None else default_ev_history_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _action_evs(advice: "ProbabilityAdvice | CompositionAwareProbabilityAdvice"
                ) -> dict[str, float | None]:
    """Collect the per-action EV estimates from an advice object."""
    return {
        estimate.action: estimate.estimated_ev
        for estimate in advice.action_estimates
    }


def build_ev_snapshot_record(
    advice: "ProbabilityAdvice | CompositionAwareProbabilityAdvice",
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile_key: str,
    decks: int = 6,
    true_count: float | None = None,
    seen_cards: list[str] | tuple[str, ...] | None = None,
) -> EVSnapshotRecord:
    """Build an :class:`EVSnapshotRecord` from a probability / EV advisory.

    Accepts either a :class:`app.probability_advisor.ProbabilityAdvice` or a
    :class:`app.probability_advisor.CompositionAwareProbabilityAdvice`. It
    extracts the coach's recommended action, the advisory best-EV action, the
    per-action EVs, the recommended action's EV (``strategy_ev``), the best EV,
    and the gap between them. The recommendation is *never* changed; when the
    best-EV action differs, ``agrees_with_strategy`` is ``False`` and a clear
    note is added so the difference can be reviewed later.
    """
    recommended_action = advice.recommended_action
    best_estimated_action = advice.best_estimated_action
    ev_by_action = _action_evs(advice)

    warnings = list(advice.warnings)

    strategy_ev = ev_by_action.get(recommended_action)

    # Prefer the decision tree's best EV when present; otherwise derive the best
    # EV from the per-action estimates that have a value.
    decision_tree = getattr(advice, "decision_tree", None)
    has_decision_tree = decision_tree is not None
    best_ev: float | None = None
    if decision_tree is not None and decision_tree.best_ev is not None:
        best_ev = decision_tree.best_ev
    elif best_estimated_action is not None:
        best_ev = ev_by_action.get(best_estimated_action)
    if best_ev is None:
        scored = [v for v in ev_by_action.values() if v is not None]
        best_ev = max(scored) if scored else None

    ev_gap: float | None = None
    if best_ev is not None and strategy_ev is not None:
        ev_gap = best_ev - strategy_ev

    agrees_with_strategy = (
        best_estimated_action is not None
        and recommended_action == best_estimated_action
    )

    split_estimate = getattr(advice, "split_estimate", None)
    has_split_ev = (
        split_estimate is not None and split_estimate.estimated_ev is not None
    )
    composition_aware = hasattr(advice, "shoe_composition")

    exactness_note = ""
    if decision_tree is not None:
        exactness_note = (
            "Exact for these rules."
            if decision_tree.is_exact_for_supported_rules
            else "Includes documented approximations (see approximation note)."
        )

    note_bits: list[str] = []
    if strategy_ev is None:
        note_bits.append(
            f"No EV estimate available for the recommended action "
            f"({recommended_action}); EV gap cannot be computed."
        )
        warnings.append(
            "Recommended action has no comparable EV estimate; review is "
            "partial for this snapshot."
        )
    if best_estimated_action is None:
        note_bits.append("No best-EV action could be estimated for this hand.")
        warnings.append("No scored EV action; agreement is reported as False.")
    if not agrees_with_strategy and best_estimated_action is not None:
        note_bits.append(
            f"Advisory best-EV action ({best_estimated_action}) differs from "
            f"the recommendation ({recommended_action}); recommendation stands."
        )
    note = " ".join(note_bits)

    return EVSnapshotRecord(
        snapshot_id=_new_id(),
        created_at=datetime.now().isoformat(timespec="seconds"),
        profile_key=profile_key,
        player_cards=tuple(str(c) for c in player_cards),
        dealer_upcard=str(dealer_upcard),
        decks=int(decks),
        true_count=true_count,
        seen_cards=tuple(str(c) for c in (seen_cards or [])),
        recommended_action=recommended_action,
        best_estimated_action=best_estimated_action,
        ev_by_action=ev_by_action,
        strategy_ev=strategy_ev,
        best_ev=best_ev,
        ev_gap=ev_gap,
        agrees_with_strategy=agrees_with_strategy,
        has_split_ev=has_split_ev,
        has_decision_tree=has_decision_tree,
        composition_aware=composition_aware,
        exactness_note=exactness_note,
        approximation_note=getattr(advice, "approximation_note", ""),
        warnings=warnings,
        note=note,
    )


def _record_filename(record: EVSnapshotRecord) -> str:
    """Build a sortable, filesystem-safe filename for a record."""
    try:
        stamp = datetime.fromisoformat(record.created_at).strftime("%Y%m%d_%H%M%S")
    except ValueError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"ev_snapshot_{stamp}_{record.snapshot_id}.json"


def save_ev_snapshot_record(
    record: EVSnapshotRecord,
    history_dir: str | Path | None = None,
) -> Path:
    """Save ``record`` as a local JSON file and return the written path."""
    directory = ensure_ev_history_dir(history_dir)
    path = directory / _record_filename(record)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(asdict(record), fh, indent=2, sort_keys=True)
    return path


def load_ev_snapshot_record(path: str | Path) -> EVSnapshotRecord:
    """Load an :class:`EVSnapshotRecord` from a JSON file."""
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return EVSnapshotRecord(
        snapshot_id=data["snapshot_id"],
        created_at=data["created_at"],
        profile_key=data["profile_key"],
        player_cards=tuple(data.get("player_cards", [])),
        dealer_upcard=data.get("dealer_upcard", ""),
        decks=int(data.get("decks", 6)),
        true_count=data.get("true_count"),
        seen_cards=tuple(data.get("seen_cards", [])),
        recommended_action=data["recommended_action"],
        best_estimated_action=data.get("best_estimated_action"),
        ev_by_action=dict(data.get("ev_by_action", {})),
        strategy_ev=data.get("strategy_ev"),
        best_ev=data.get("best_ev"),
        ev_gap=data.get("ev_gap"),
        agrees_with_strategy=bool(data.get("agrees_with_strategy", False)),
        has_split_ev=bool(data.get("has_split_ev", False)),
        has_decision_tree=bool(data.get("has_decision_tree", False)),
        composition_aware=bool(data.get("composition_aware", False)),
        exactness_note=data.get("exactness_note", ""),
        approximation_note=data.get("approximation_note", ""),
        warnings=list(data.get("warnings", [])),
        note=data.get("note", ""),
    )


def list_ev_snapshot_records(
    history_dir: str | Path | None = None,
    limit: int | None = None,
    profile_key: str | None = None,
    disagreements_only: bool = False,
) -> list[EVSnapshotRecord]:
    """Return saved EV snapshots sorted oldest-first.

    Args:
        history_dir: Directory to read (defaults to the local EV-snapshot dir).
        limit: If given (>= 0), return only the most recent ``limit`` records.
        profile_key: If given, keep only records for that profile.
        disagreements_only: If ``True``, keep only snapshots where the advisory
            best-EV action differed from the recommendation.

    Returns an empty list when the directory does not exist yet.
    """
    directory = (
        Path(history_dir) if history_dir is not None
        else default_ev_history_dir()
    )
    if not directory.is_dir():
        return []

    records: list[EVSnapshotRecord] = []
    for path in directory.glob("ev_snapshot_*.json"):
        try:
            records.append(load_ev_snapshot_record(path))
        except (ValueError, KeyError, OSError):
            # Skip unreadable / malformed files rather than failing the listing.
            continue

    if profile_key is not None:
        records = [r for r in records if r.profile_key == profile_key]
    if disagreements_only:
        records = [r for r in records if not r.agrees_with_strategy]

    records.sort(key=lambda r: (r.created_at, r.snapshot_id))

    if limit is not None and limit >= 0:
        records = records[-limit:] if limit else []
    return records


def _spot_label(record: EVSnapshotRecord) -> str:
    """A short, readable label for the hand a snapshot covers."""
    cards = ",".join(record.player_cards) if record.player_cards else "?"
    return f"{cards} vs {record.dealer_upcard}"


def summarize_ev_snapshots(
    records: list[EVSnapshotRecord],
    min_gap: float | None = None,
) -> EVReviewSummary:
    """Compute the Strategy-vs-EV review summary across ``records``.

    Counts agreement / disagreement between the recommendation and the advisory
    best-EV action, detects the largest EV gaps and the spots where strategy and
    EV most often differ, and generates practice recommendations. When fewer
    than :data:`MIN_SNAPSHOT_SAMPLE` snapshots are present the data-quality note
    flags a LOW sample. ``min_gap`` (if given) keeps only disagreements whose EV
    gap is at least that size for the gap / spot detection.
    """
    if not records:
        return EVReviewSummary(
            total_snapshots=0,
            agreement_count=0,
            disagreement_count=0,
            agreement_rate=0.0,
            most_common_profile="(none)",
            most_common_recommended_actions=[],
            most_common_best_ev_actions=[],
            largest_ev_gaps=[],
            disagreement_spots=[],
            practice_recommendations=[],
            data_quality_note=(
                "No EV snapshots yet (LOW sample). " + EDUCATIONAL_NOTE
            ),
            warnings=[],
        )

    total = len(records)
    agreement_count = sum(1 for r in records if r.agrees_with_strategy)
    disagreement_count = total - agreement_count
    agreement_rate = agreement_count / total

    profile_counter: Counter[str] = Counter(r.profile_key for r in records)
    rec_counter: Counter[str] = Counter(r.recommended_action for r in records)
    best_counter: Counter[str] = Counter(
        r.best_estimated_action for r in records
        if r.best_estimated_action is not None
    )

    # Disagreements (optionally filtered by a minimum EV gap) drive both the
    # largest-gap list and the disagreement-spot tally.
    disagreements = [r for r in records if not r.agrees_with_strategy]
    if min_gap is not None:
        disagreements = [
            r for r in disagreements
            if r.ev_gap is not None and r.ev_gap >= min_gap
        ]

    gapped = [r for r in disagreements if r.ev_gap is not None]
    gapped.sort(key=lambda r: r.ev_gap, reverse=True)
    largest_ev_gaps = [
        (
            f"{_spot_label(r)} [{r.recommended_action} -> "
            f"{r.best_estimated_action}]",
            r.ev_gap,
        )
        for r in gapped[:5]
    ]

    spot_counter: Counter[str] = Counter(_spot_label(r) for r in disagreements)
    disagreement_spots = spot_counter.most_common(5)

    warnings: list[str] = []
    missing_strategy_ev = sum(1 for r in records if r.strategy_ev is None)
    if missing_strategy_ev:
        warnings.append(
            f"{missing_strategy_ev} snapshot(s) had no EV for the recommended "
            "action; their EV gap could not be computed."
        )

    practice_recommendations = _build_practice_recommendations(
        total, agreement_rate, disagreement_spots, largest_ev_gaps
    )

    if total < MIN_SNAPSHOT_SAMPLE:
        data_quality_note = (
            f"LOW sample: only {total} snapshot(s) (< {MIN_SNAPSHOT_SAMPLE}); "
            "treat agreement patterns as indicative, not conclusive. "
            + EDUCATIONAL_NOTE
        )
    else:
        data_quality_note = (
            f"{total} snapshots reviewed. " + EDUCATIONAL_NOTE
        )

    return EVReviewSummary(
        total_snapshots=total,
        agreement_count=agreement_count,
        disagreement_count=disagreement_count,
        agreement_rate=agreement_rate,
        most_common_profile=profile_counter.most_common(1)[0][0],
        most_common_recommended_actions=rec_counter.most_common(5),
        most_common_best_ev_actions=best_counter.most_common(5),
        largest_ev_gaps=largest_ev_gaps,
        disagreement_spots=disagreement_spots,
        practice_recommendations=practice_recommendations,
        data_quality_note=data_quality_note,
        warnings=warnings,
    )


def _build_practice_recommendations(
    total: int,
    agreement_rate: float,
    disagreement_spots: list[tuple[str, int]],
    largest_ev_gaps: list[tuple[str, float]],
) -> list[str]:
    """Generate plain practice tips from the review (advisory only)."""
    tips: list[str] = []
    if total < MIN_SNAPSHOT_SAMPLE:
        tips.append(
            "Save more EV snapshots (odds/coach --save-ev-snapshot) to build a "
            "more reliable review."
        )
    if agreement_rate >= 0.95:
        tips.append(
            "The recommendation and the advisory best-EV action agree on almost "
            "every hand - the strategy is well aligned with the EV estimate."
        )
    else:
        tips.append(
            "Review the disagreement spots below: these are hands where the "
            "advisory EV favoured a different action (the recommendation still "
            "stands; EV is advisory)."
        )
    for spot, count in disagreement_spots[:3]:
        tips.append(
            f"Study {spot}: strategy and advisory EV differed {count} time(s)."
        )
    if largest_ev_gaps:
        spot, gap = largest_ev_gaps[0]
        tips.append(
            f"Largest advisory EV gap: {spot} (~{gap:+.3f}). Understand why the "
            "EV estimate differs, then keep following the recommendation."
        )
    return tips
