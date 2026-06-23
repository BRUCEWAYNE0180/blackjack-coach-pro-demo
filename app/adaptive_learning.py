"""Adaptive local learning for Blackjack Coach Pro Demo.

Reads the locally saved outcome history (see :mod:`app.outcome_history`) to
detect patterns, weak spots, and practice opportunities, so the coach becomes
more useful with use. This *personalises explanations and suggests practice* -
it never changes the mathematical strategy: ``strategy_engine.recommend`` and
the probability/EV advisor are not modified, and short-run results never alter
the recommended action.

Learning is local, transparent, and reversible (it reads JSON files under the
git-ignored ``.blackjack_coach/`` tree). No network, cloud, database, or
external dependencies; no money, bankroll, accounts, tokens, or sensitive data.
See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .hand_evaluator import card_value, evaluate_hand
from .outcome_history import OutcomeRecord, list_outcome_records
from .rules import DEFAULT_PROFILE, RuleProfile

# Confidence / sampling thresholds (kept explicit and conservative).
_LOW_CONFIDENCE_RECORDS = 10   # fewer total records -> LOW confidence overall
_SMALL_SAMPLE_SPOT = 5         # fewer records in a spot -> "small sample"

_NO_DATA_NOTE = (
    "No saved outcome history yet. Use coach-play/play with --save-outcome "
    "first, then review with 'learn'."
)
_CAUTION_NOTE = (
    "Local history reflects short-run variance, not a strategy change. The "
    "recommended action always comes from basic strategy, never from results."
)


@dataclass(frozen=True)
class LearningSpot:
    """Aggregated local results for one hand 'spot' (pattern vs dealer)."""

    spot_id: str
    category: str
    player_pattern: str
    dealer_upcard: str
    profile_key: str
    total_seen: int
    wins: int
    losses: int
    pushes: int
    surrenders: int
    player_busts: int
    dealer_busts: int
    split_records: int
    recommended_focus: str
    confidence_label: str
    note: str = ""

    @property
    def decided_hands(self) -> int:
        return self.wins + self.losses + self.pushes + self.surrenders

    @property
    def win_rate(self) -> float:
        total = self.decided_hands
        return self.wins / total if total else 0.0

    @property
    def loss_rate(self) -> float:
        total = self.decided_hands
        return self.losses / total if total else 0.0


@dataclass(frozen=True)
class LearningSummary:
    """A local-learning summary across saved outcome records."""

    total_records: int
    profiles_seen: list[str]
    most_common_profile: str
    strongest_spots: list[LearningSpot]
    weakest_spots: list[LearningSpot]
    most_common_outcomes: list[tuple[str, int]]
    high_variance_spots: list[LearningSpot]
    practice_recommendations: list[str]
    data_quality_note: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CoachHistoryContext:
    """Local-history context for a single hand the coach is advising on."""

    has_history: bool
    matching_records: int
    similar_spot_summary: str
    local_win_rate: float
    local_loss_rate: float
    local_push_rate: float
    practice_note: str
    caution_note: str
    warnings: list[str] = field(default_factory=list)


def _upcard_label(dealer_upcard: str) -> str:
    """Normalise a dealer upcard to a label (``"A"``, ``"10"``, ``"2".."9"``)."""
    value = card_value(dealer_upcard)
    return "A" if value == 11 else str(value)


def classify_hand_spot(
    player_cards: list[str] | tuple[str, ...], dealer_upcard: str
) -> str:
    """Return a stable spot id such as ``hard_16_vs_10`` or ``pair_A_vs_6``."""
    ev = evaluate_hand(player_cards)
    up = _upcard_label(dealer_upcard)
    if ev.is_pair:
        rank = "A" if ev.pair_value == 11 else str(ev.pair_value)
        return f"pair_{rank}_vs_{up}"
    if ev.is_soft:
        return f"soft_{ev.total}_vs_{up}"
    return f"hard_{ev.total}_vs_{up}"


def _spot_category(spot_id: str) -> str:
    return spot_id.split("_", 1)[0]  # "hard" / "soft" / "pair"


def _record_spot(record: OutcomeRecord) -> str:
    """Classify a record by its *starting* two cards (the spot it began as)."""
    starting = tuple(record.player_cards[:2])
    return classify_hand_spot(starting, record.dealer_upcard)


def _focus_for(win_rate: float, loss_rate: float, small_sample: bool) -> str:
    """Pick a recommended focus label from the local rates."""
    if small_sample:
        return "gather more data"
    if loss_rate >= 0.6:
        return "review / drill"
    if win_rate >= 0.55:
        return "solid"
    return "monitor"


def _build_spot(records: list[OutcomeRecord], total_records: int) -> LearningSpot:
    """Aggregate a list of records that share a spot into a LearningSpot."""
    first = records[0]
    spot_id = _record_spot(first)
    wins = sum(r.hands_won for r in records)
    losses = sum(r.hands_lost for r in records)
    pushes = sum(r.hands_pushed for r in records)
    surrenders = sum(r.hands_surrendered for r in records)
    player_busts = sum(r.player_busts for r in records)
    dealer_busts = sum(r.dealer_busts for r in records)
    split_records = sum(1 for r in records if r.is_split_hand)
    total_seen = len(records)
    small_sample = total_seen < _SMALL_SAMPLE_SPOT

    decided = wins + losses + pushes + surrenders
    win_rate = wins / decided if decided else 0.0
    loss_rate = losses / decided if decided else 0.0

    confidence = "LOW" if (total_records < _LOW_CONFIDENCE_RECORDS or small_sample) else "MEDIUM"
    note_parts = []
    if small_sample:
        note_parts.append("small sample")
    note_parts.append(f"{wins}W/{losses}L/{pushes}P over {total_seen} record(s)")

    return LearningSpot(
        spot_id=spot_id,
        category=_spot_category(spot_id),
        player_pattern=spot_id.rsplit("_vs_", 1)[0],
        dealer_upcard=_upcard_label(first.dealer_upcard),
        profile_key=first.profile_key,
        total_seen=total_seen,
        wins=wins,
        losses=losses,
        pushes=pushes,
        surrenders=surrenders,
        player_busts=player_busts,
        dealer_busts=dealer_busts,
        split_records=split_records,
        recommended_focus=_focus_for(win_rate, loss_rate, small_sample),
        confidence_label=confidence,
        note="; ".join(note_parts),
    )


def _empty_summary() -> LearningSummary:
    return LearningSummary(
        total_records=0,
        profiles_seen=[],
        most_common_profile="(none)",
        strongest_spots=[],
        weakest_spots=[],
        most_common_outcomes=[],
        high_variance_spots=[],
        practice_recommendations=[],
        data_quality_note=_NO_DATA_NOTE,
        warnings=[_CAUTION_NOTE],
    )


def build_learning_summary(outcome_records: list[OutcomeRecord]) -> LearningSummary:
    """Summarise saved outcome records into local-learning insights.

    Groups records by spot, ranks strongest / weakest / high-variance spots, and
    generates practice recommendations. Never changes strategy; everything here
    is descriptive of *local* practice results.
    """
    if not outcome_records:
        return _empty_summary()

    total_records = len(outcome_records)
    profiles_seen = sorted({r.profile_key for r in outcome_records})
    profile_counter: Counter[str] = Counter(r.profile_key for r in outcome_records)
    outcome_counter: Counter[str] = Counter(r.final_outcome for r in outcome_records)

    # Group records by spot id.
    by_spot: dict[str, list[OutcomeRecord]] = {}
    for record in outcome_records:
        spot_id = _record_spot(record)
        by_spot.setdefault(spot_id, []).append(record)

    spots = [_build_spot(recs, total_records) for recs in by_spot.values()]

    # Weakest: highest loss rate (then most losses) among spots with any decision.
    decided_spots = [s for s in spots if s.decided_hands > 0]
    weakest = sorted(
        decided_spots, key=lambda s: (s.loss_rate, s.losses), reverse=True
    )
    weakest = [s for s in weakest if s.loss_rate >= 0.5][:5]

    # Strongest: highest win rate among spots with any decision.
    strongest = sorted(
        decided_spots, key=lambda s: (s.win_rate, s.wins), reverse=True
    )
    strongest = [s for s in strongest if s.win_rate >= 0.5][:5]

    # High variance: small sample with both wins and losses present.
    high_variance = [
        s for s in spots
        if s.total_seen < _SMALL_SAMPLE_SPOT and s.wins > 0 and s.losses > 0
    ]

    practice = _practice_recommendations(weakest, high_variance)

    if total_records < _LOW_CONFIDENCE_RECORDS:
        quality = (
            f"LOW confidence: only {total_records} record(s) saved. Save more "
            "hands for more meaningful patterns."
        )
    else:
        quality = (
            f"{total_records} records saved across {len(profiles_seen)} "
            "profile(s). Local patterns are descriptive, not predictive."
        )

    return LearningSummary(
        total_records=total_records,
        profiles_seen=profiles_seen,
        most_common_profile=profile_counter.most_common(1)[0][0],
        strongest_spots=strongest,
        weakest_spots=weakest,
        most_common_outcomes=outcome_counter.most_common(5),
        high_variance_spots=high_variance,
        practice_recommendations=practice,
        data_quality_note=quality,
        warnings=[_CAUTION_NOTE],
    )


def _practice_recommendations(
    weakest: list[LearningSpot], high_variance: list[LearningSpot]
) -> list[str]:
    """Turn weak / high-variance spots into plain practice suggestions."""
    recs: list[str] = []
    for spot in weakest[:3]:
        recs.append(
            f"Review {spot.spot_id}: local loss rate "
            f"{spot.loss_rate * 100:.0f}% over {spot.total_seen} record(s)."
        )
    for spot in high_variance[:3]:
        if spot.spot_id not in (s.spot_id for s in weakest[:3]):
            recs.append(
                f"Gather more data on {spot.spot_id} (small, mixed sample)."
            )
    if not recs:
        recs.append("No clear weak spots yet - keep practising to build data.")
    return recs


def build_history_context(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    history_dir: str | None = None,
) -> CoachHistoryContext:
    """Return local-history context for the hand the coach is advising on.

    Loads local outcomes for the profile and looks for the same spot. Never
    changes the recommendation; it only adds local context, and is explicit when
    the sample is small or missing.
    """
    spot_id = classify_hand_spot(player_cards, dealer_upcard)
    records = list_outcome_records(history_dir=history_dir, profile_key=profile.key)

    if not records:
        return CoachHistoryContext(
            has_history=False,
            matching_records=0,
            similar_spot_summary=f"No local history for {spot_id}.",
            local_win_rate=0.0,
            local_loss_rate=0.0,
            local_push_rate=0.0,
            practice_note=_NO_DATA_NOTE,
            caution_note=_CAUTION_NOTE,
            warnings=[],
        )

    matching = [
        r for r in records
        if _record_spot(r) == spot_id
    ]
    wins = sum(r.hands_won for r in matching)
    losses = sum(r.hands_lost for r in matching)
    pushes = sum(r.hands_pushed for r in matching)
    decided = wins + losses + pushes
    win_rate = wins / decided if decided else 0.0
    loss_rate = losses / decided if decided else 0.0
    push_rate = pushes / decided if decided else 0.0

    if not matching:
        summary = f"No local records yet for {spot_id} (history exists for other spots)."
        practice = (
            "No local data for this exact spot; play it with --save-outcome to "
            "build context."
        )
    else:
        summary = (
            f"{spot_id}: {wins}W / {losses}L / {pushes}P over "
            f"{len(matching)} record(s)."
        )
        if len(matching) < _SMALL_SAMPLE_SPOT:
            practice = (
                f"Small sample ({len(matching)} record(s)); treat as context "
                "only, not a trend."
            )
        else:
            practice = (
                f"Local loss rate {loss_rate * 100:.0f}% here - a candidate for "
                "extra practice if high."
            )

    return CoachHistoryContext(
        has_history=True,
        matching_records=len(matching),
        similar_spot_summary=summary,
        local_win_rate=win_rate,
        local_loss_rate=loss_rate,
        local_push_rate=push_rate,
        practice_note=practice,
        caution_note=_CAUTION_NOTE,
        warnings=[],
    )


def _format_spot_line(spot: LearningSpot) -> str:
    return (
        f"{spot.spot_id} [{spot.confidence_label}] "
        f"{spot.wins}W/{spot.losses}L/{spot.pushes}P "
        f"(focus: {spot.recommended_focus})"
    )


def format_learning_summary(summary: LearningSummary) -> str:
    """Render a :class:`LearningSummary` as compact text for the terminal."""
    lines: list[str] = []
    lines.append(f"Total records      : {summary.total_records}")
    if summary.total_records == 0:
        lines.append(summary.data_quality_note)
        return "\n".join(lines)

    lines.append(f"Profiles seen      : {', '.join(summary.profiles_seen)}")
    lines.append(f"Most common profile: {summary.most_common_profile}")

    lines.append("")
    lines.append("-- Strongest spots --")
    if summary.strongest_spots:
        lines.extend(f"  - {_format_spot_line(s)}" for s in summary.strongest_spots)
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("-- Weakest spots --")
    if summary.weakest_spots:
        lines.extend(f"  - {_format_spot_line(s)}" for s in summary.weakest_spots)
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("-- High variance spots --")
    if summary.high_variance_spots:
        lines.extend(f"  - {_format_spot_line(s)}" for s in summary.high_variance_spots)
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("-- Most common outcomes --")
    if summary.most_common_outcomes:
        lines.extend(f"  - {label} (x{count})" for label, count in summary.most_common_outcomes)
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("-- Practice recommendations --")
    lines.extend(f"  - {rec}" for rec in summary.practice_recommendations)

    lines.append("")
    lines.append(f"Data quality       : {summary.data_quality_note}")
    return "\n".join(lines)
