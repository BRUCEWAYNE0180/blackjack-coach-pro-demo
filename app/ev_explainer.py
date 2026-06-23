"""Strategy-vs-EV explanation engine for Blackjack Coach Pro Demo (v1.18.0).

Turns the (advisory) probability / EV output into a clear, professional
explanation of *when the coach's main recommendation agrees with the best-EV
advisory action and when it differs* - and, when it differs, *why*: a tiny vs
large EV gap, the remaining-shoe composition, the true count, split / re-split
context, surrender nuances, or the documented limitations of the EV model.

This is an explanation layer only. It never changes the main recommendation,
never overrides ``strategy_engine.recommend``, never turns the advisory EV into
the final decision, and never touches the Hi-Lo counting math. It keeps a clear
separation between the recommended action, the advisory EV action, the size of
the gap, the model's limitations, and the final decision. Standard library
only - no network, no cloud, no database, no sensitive data. See
docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .ev_history import EVSnapshotRecord, build_ev_snapshot_record

if TYPE_CHECKING:  # only for type hints
    from .probability_advisor import (
        CompositionAwareProbabilityAdvice,
        ProbabilityAdvice,
    )

# EV-gap classification band labels.
GAP_UNKNOWN = "UNKNOWN"
GAP_TINY = "TINY"
GAP_SMALL = "SMALL"
GAP_MEDIUM = "MEDIUM"
GAP_LARGE = "LARGE"

# Agreement status labels.
STATUS_AGREES = "AGREES"
STATUS_DIFFERS = "DIFFERS"
STATUS_NO_EV = "NO_EV_ACTION"

# Standing reminder kept on every explanation: EV is advisory only.
ADVISORY_NOTE = (
    "EV is advisory only and never overrides the strategy recommendation "
    "automatically; the coach recommendation stands."
)


@dataclass(frozen=True)
class EVGapCategory:
    """A labelled EV-gap band with its meaning and a short action note."""

    label: str
    min_gap: float | None
    max_gap: float | None
    meaning: str
    action_note: str


@dataclass(frozen=True)
class StrategyEVDisagreement:
    """A clear explanation of strategy vs the advisory best-EV action."""

    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    recommended_action: str
    best_ev_action: str | None
    strategy_ev: float | None
    best_ev: float | None
    ev_gap: float | None
    gap_label: str
    agreement_status: str
    likely_reason: str
    explanation: str
    recommendation_note: str
    approximation_note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DisagreementExplanationSummary:
    """Grouped Strategy-vs-EV explanations across a set of snapshots."""

    total: int
    agreement_count: int
    disagreement_count: int
    group_counts: dict[str, int]
    explanations: list[StrategyEVDisagreement]
    review_notes: list[str] = field(default_factory=list)


# The EV-gap bands. ``classify_ev_gap`` returns one of these. The gap is the
# (non-negative) advisory EV advantage of the best action over the recommended
# action's EV.
_GAP_CATEGORIES: tuple[EVGapCategory, ...] = (
    EVGapCategory(
        label=GAP_TINY, min_gap=0.0, max_gap=0.02,
        meaning="Negligible EV difference.",
        action_note=(
            "Probably not a strong difference - the recommendation is "
            "essentially EV-neutral here."
        ),
    ),
    EVGapCategory(
        label=GAP_SMALL, min_gap=0.02, max_gap=0.05,
        meaning="Small EV difference.",
        action_note=(
            "Probably not a strong difference; keep following the "
            "recommendation."
        ),
    ),
    EVGapCategory(
        label=GAP_MEDIUM, min_gap=0.05, max_gap=0.15,
        meaning="Moderate EV difference.",
        action_note="Worth understanding; review the spot with `odds`.",
    ),
    EVGapCategory(
        label=GAP_LARGE, min_gap=0.15, max_gap=None,
        meaning="Large EV difference.",
        action_note=(
            "Review this spot with `odds` and `audit` to understand why the "
            "advisory EV differs."
        ),
    ),
)

_GAP_UNKNOWN_CATEGORY = EVGapCategory(
    label=GAP_UNKNOWN, min_gap=None, max_gap=None,
    meaning="EV gap could not be computed (missing EV data).",
    action_note=(
        "Run `odds --composition-aware` to compute a fuller EV estimate for "
        "this hand."
    ),
)


def classify_ev_gap(ev_gap: float | None) -> EVGapCategory:
    """Classify an EV gap into a labelled band.

    Bands (by gap magnitude): ``TINY`` [0, 0.02), ``SMALL`` [0.02, 0.05),
    ``MEDIUM`` [0.05, 0.15), ``LARGE`` [0.15, inf). A missing gap is ``UNKNOWN``.
    """
    if ev_gap is None:
        return _GAP_UNKNOWN_CATEGORY
    gap = abs(ev_gap)
    for category in _GAP_CATEGORIES:
        lower = category.min_gap if category.min_gap is not None else float("-inf")
        upper = category.max_gap if category.max_gap is not None else float("inf")
        if lower <= gap < upper:
            return category
    # gap >= the last band's lower bound (LARGE has max_gap=None).
    return _GAP_CATEGORIES[-1]


def _as_record(
    obj: "ProbabilityAdvice | CompositionAwareProbabilityAdvice | EVSnapshotRecord",
    true_count: float | None,
) -> tuple[EVSnapshotRecord, float | None]:
    """Normalise either advice object or a snapshot into an EVSnapshotRecord.

    Returns the record plus the effective true count (an explicit ``true_count``
    argument wins; otherwise a snapshot's stored true count is used). For advice
    objects the shared, tested :func:`build_ev_snapshot_record` does the EV
    extraction so the explainer stays consistent with the saved snapshots.
    """
    if isinstance(obj, EVSnapshotRecord):
        effective_tc = true_count if true_count is not None else obj.true_count
        return obj, effective_tc

    decks = getattr(obj, "decks", 6)
    record = build_ev_snapshot_record(
        obj, list(obj.player_cards), obj.dealer_upcard, obj.profile_key,
        decks=decks, true_count=true_count,
    )
    return record, true_count


def _agreement_status(record: EVSnapshotRecord) -> str:
    if record.best_estimated_action is None:
        return STATUS_NO_EV
    return STATUS_AGREES if record.agrees_with_strategy else STATUS_DIFFERS


def _likely_reason(record: EVSnapshotRecord, true_count: float | None,
                   category: EVGapCategory) -> str:
    """Best-guess reason the advisory EV action could differ from strategy."""
    bits: list[str] = []
    actions = {record.recommended_action, record.best_estimated_action}

    if record.composition_aware:
        seen = len(record.seen_cards)
        if seen:
            bits.append(
                f"the remaining-shoe composition ({seen} extra card(s) seen)")
        else:
            bits.append("the remaining-shoe composition (finite-shoe counts)")
    if true_count is not None and abs(true_count) >= 1:
        bits.append(
            f"the true count ({true_count:g}); the count-aware coach can already "
            "fold in documented deviations")
    if "SPLIT" in actions or record.has_split_ev:
        bits.append("split / re-split modelling for the pair")
    if "SURRENDER" in actions:
        bits.append("a surrender threshold that is close to another action")
    if category.label in (GAP_TINY, GAP_SMALL):
        bits.append(
            "a very close EV call where small model assumptions can tip the "
            "ranking")
    if not bits:
        bits.append(
            "the documented EV-model approximations (idealised/finite-shoe "
            "look-ahead), not a strategy error")
    return "; ".join(bits) + "."


def explain_strategy_vs_ev(
    obj: "ProbabilityAdvice | CompositionAwareProbabilityAdvice | EVSnapshotRecord",
    true_count: float | None = None,
) -> StrategyEVDisagreement:
    """Explain whether the recommendation agrees with the advisory best EV.

    Accepts a :class:`ProbabilityAdvice`, a
    :class:`CompositionAwareProbabilityAdvice`, or an
    :class:`app.ev_history.EVSnapshotRecord`. When they agree, the explanation
    says the EV advisory agrees with the coach recommendation. When they differ,
    it states which action the coach recommends, which the EV advisory estimates
    as best, the size of the difference, the likely reason, and that EV never
    overrides the strategy automatically.
    """
    record, effective_tc = _as_record(obj, true_count)
    category = classify_ev_gap(record.ev_gap)
    status = _agreement_status(record)
    recommended = record.recommended_action
    best = record.best_estimated_action

    cards_text = ", ".join(record.player_cards) if record.player_cards else "?"
    gap_text = "n/a" if record.ev_gap is None else f"{record.ev_gap:+.3f}"

    if status == STATUS_AGREES:
        likely_reason = "Strategy and the advisory EV point to the same action."
        explanation = (
            f"The EV advisory agrees with the coach recommendation "
            f"({recommended}) for {cards_text} vs {record.dealer_upcard}. "
            "Both basic strategy and the approximate EV favour the same play, "
            "so there is nothing to reconcile here."
        )
    elif status == STATUS_NO_EV:
        likely_reason = (
            "No comparable EV action could be estimated for this hand "
            "(missing EV data).")
        explanation = (
            f"The coach recommends {recommended} for {cards_text} vs "
            f"{record.dealer_upcard}, but no advisory best-EV action could be "
            f"estimated, so they cannot be compared. {category.action_note}"
        )
    else:  # DIFFERS
        likely_reason = _likely_reason(record, effective_tc, category)
        explanation = (
            f"The coach recommends {recommended} for {cards_text} vs "
            f"{record.dealer_upcard}, while the advisory best-EV action is "
            f"{best} (EV gap {gap_text}, {category.label} - {category.meaning}). "
            f"This likely comes from {likely_reason} {category.action_note} "
            f"{ADVISORY_NOTE}"
        )

    recommendation_note = (
        f"Recommendation stands: {recommended} (EV is advisory only)."
    )

    return StrategyEVDisagreement(
        player_cards=record.player_cards,
        dealer_upcard=record.dealer_upcard,
        profile_key=record.profile_key,
        recommended_action=recommended,
        best_ev_action=best,
        strategy_ev=record.strategy_ev,
        best_ev=record.best_ev,
        ev_gap=record.ev_gap,
        gap_label=category.label,
        agreement_status=status,
        likely_reason=likely_reason,
        explanation=explanation,
        recommendation_note=recommendation_note,
        approximation_note=record.approximation_note,
        warnings=list(record.warnings),
    )


def explain_ev_snapshot_record(
    record: EVSnapshotRecord,
) -> StrategyEVDisagreement:
    """Explain a saved :class:`EVSnapshotRecord` (Strategy-vs-EV)."""
    return explain_strategy_vs_ev(record)


def _group_key(disagreement: StrategyEVDisagreement) -> str:
    """Map an explanation to a review group key."""
    if disagreement.agreement_status == STATUS_AGREES:
        return "agrees"
    if disagreement.agreement_status == STATUS_NO_EV or disagreement.ev_gap is None:
        return "missing"
    return {
        GAP_TINY: "tiny",
        GAP_SMALL: "small",
        GAP_MEDIUM: "medium",
        GAP_LARGE: "large",
    }.get(disagreement.gap_label, "missing")


def summarize_disagreement_explanations(
    records: list[EVSnapshotRecord],
) -> DisagreementExplanationSummary:
    """Group Strategy-vs-EV explanations across saved snapshots.

    Buckets each snapshot into: ``agrees``, ``tiny`` / ``small`` / ``medium`` /
    ``large`` gap, or ``missing`` (no EV data), and generates plain review notes.
    """
    explanations = [explain_ev_snapshot_record(r) for r in records]
    group_counts: Counter[str] = Counter(_group_key(e) for e in explanations)
    # Ensure every known bucket is present (zero when unused) for stable output.
    counts = {
        key: group_counts.get(key, 0)
        for key in ("agrees", "tiny", "small", "medium", "large", "missing")
    }

    agreement_count = counts["agrees"]
    disagreement_count = len(explanations) - agreement_count

    review_notes = _build_review_notes(len(explanations), counts)

    return DisagreementExplanationSummary(
        total=len(explanations),
        agreement_count=agreement_count,
        disagreement_count=disagreement_count,
        group_counts=counts,
        explanations=explanations,
        review_notes=review_notes,
    )


def _build_review_notes(total: int, counts: dict[str, int]) -> list[str]:
    """Generate plain-language review notes from the grouped counts."""
    notes: list[str] = []
    if total == 0:
        notes.append(
            "No snapshots to explain yet. Save some with "
            "`odds`/`coach --save-ev-snapshot` first.")
        return notes
    if counts["agrees"]:
        notes.append(
            f"{counts['agrees']} snapshot(s) agree with the advisory EV - the "
            "strategy is well aligned there.")
    if counts["tiny"] or counts["small"]:
        close = counts["tiny"] + counts["small"]
        notes.append(
            f"{close} disagreement(s) had a tiny/small EV gap - probably not a "
            "strong difference; keep following the recommendation.")
    if counts["medium"]:
        notes.append(
            f"{counts['medium']} disagreement(s) had a moderate EV gap - worth "
            "reviewing with `odds`.")
    if counts["large"]:
        notes.append(
            f"{counts['large']} disagreement(s) had a LARGE EV gap - review "
            "those spots with `odds` and `audit`.")
    if counts["missing"]:
        notes.append(
            f"{counts['missing']} snapshot(s) had missing EV data and could not "
            "be compared.")
    notes.append(
        "EV stays advisory: these explanations never change the strategy "
        "recommendation.")
    return notes


# Convenience set for callers (e.g. the CLI) that filter by "big" gaps.
LARGE_GAP_LABELS = (GAP_LARGE,)
MEDIUM_OR_LARGE_GAP_LABELS = (GAP_MEDIUM, GAP_LARGE)
