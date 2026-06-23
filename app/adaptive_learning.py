"""Adaptive local-learning layer for Blackjack Coach Pro Demo.

This layer reads the *locally saved* outcome history (see
:mod:`app.outcome_history`) so the coach can grow more useful with practice:
it groups played hands into recognisable "spots" (e.g. ``hard_16_vs_10``),
detects weak / strong / high-variance spots, suggests what to practise, and
adds personalised local context to the coach output.

Design rules (see docs/PROJECT_RULES.md):
    * It NEVER changes the strategy recommendation. ``strategy_engine.recommend``
      and the counting maths are untouched; the main recommended action is
      always derived from basic strategy, not from short-term local results.
    * History is used only to *explain* patterns, *recommend* practice, *flag*
      weak spots, and show local context - never to promise an edge or make
      exact predictions.
    * Learning is local, transparent, and reversible: it is just a read-only
      summary of JSON files the user already chose to save. No network, no
      cloud, no database, no external dependencies, and no money / bankroll /
      account / token / screenshot data.

Educational/practice tool only.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .hand_evaluator import card_value, evaluate_hand
from .outcome_history import OutcomeRecord, list_outcome_records
from .rules import DEFAULT_PROFILE, RuleProfile

# A spot is only treated as having enough data to read confidently once it has
# at least this many records; below it we always say "small sample".
MIN_SPOT_SAMPLE = 5

# Below this many total records the whole summary's confidence is LOW: there is
# simply not enough local history to read patterns into.
MIN_TOTAL_RECORDS = 10

# Loss rate at / above which a spot is flagged as a weak spot worth practising.
WEAK_LOSS_RATE = 0.5

EDUCATIONAL_NOTE = (
    "Adaptive learning reads only your locally saved practice outcomes. It "
    "personalises context and practice tips but never changes the strategy "
    "recommendation, promises an edge, or makes exact predictions."
)


@dataclass(frozen=True)
class LearningSpot:
    """Aggregated local results for one recognisable hand spot."""

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
        """Number of hands with a win/loss/push/surrender result."""
        return self.wins + self.losses + self.pushes + self.surrenders

    @property
    def loss_rate(self) -> float:
        """Local loss rate across decided hands (0.0 when none decided)."""
        decided = self.decided_hands
        return self.losses / decided if decided else 0.0

    @property
    def win_rate(self) -> float:
        """Local win rate across decided hands (0.0 when none decided)."""
        decided = self.decided_hands
        return self.wins / decided if decided else 0.0


@dataclass(frozen=True)
class LearningSummary:
    """A whole-history adaptive-learning summary."""

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
    """Local-history context for a single coached hand.

    Purely advisory: it is attached alongside (never instead of) the strategy
    recommendation.
    """

    has_history: bool
    matching_records: int
    similar_spot_summary: str
    local_win_rate: float
    local_loss_rate: float
    local_push_rate: float
    practice_note: str
    caution_note: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _SpotInfo:
    """Internal: the structural labels for one hand spot."""

    spot_id: str
    category: str
    player_pattern: str
    dealer_label: str


def _dealer_label(dealer_upcard: str) -> str:
    """Render a dealer upcard for a spot id: ``A``, ``10``, or ``2``..``9``."""
    value = card_value(dealer_upcard)
    if value == 11:
        return "A"
    if value == 10:
        return "10"
    return str(value)


def _describe_hand_spot(
    player_cards: list[str] | tuple[str, ...], dealer_upcard: str
) -> _SpotInfo:
    """Classify a hand into a structured spot description.

    Reuses :func:`app.hand_evaluator.evaluate_hand`; it does not re-implement
    any strategy logic.
    """
    ev = evaluate_hand(player_cards)
    dealer = _dealer_label(dealer_upcard)

    if ev.is_pair:
        pair_label = "A" if ev.pair_value == 11 else str(ev.pair_value)
        pattern = f"pair_{pair_label}"
        category = "pair"
    elif ev.is_soft:
        pattern = f"soft_{ev.total}"
        category = "soft"
    else:
        pattern = f"hard_{ev.total}"
        category = "hard"

    return _SpotInfo(
        spot_id=f"{pattern}_vs_{dealer}",
        category=category,
        player_pattern=pattern,
        dealer_label=dealer,
    )


def classify_hand_spot(
    player_cards: list[str] | tuple[str, ...], dealer_upcard: str
) -> str:
    """Return a stable spot label for a hand, e.g. ``"hard_16_vs_10"``.

    Examples::

        classify_hand_spot(["10", "6"], "10")  -> "hard_16_vs_10"
        classify_hand_spot(["A", "7"], "9")    -> "soft_18_vs_9"
        classify_hand_spot(["8", "8"], "6")    -> "pair_8_vs_6"
        classify_hand_spot(["A", "A"], "6")    -> "pair_A_vs_6"

    Raises:
        ValueError: If the hand or dealer upcard is invalid.
    """
    return _describe_hand_spot(player_cards, dealer_upcard).spot_id


def _profile_key_of(profile: RuleProfile | str) -> str:
    """Return the canonical profile key from a profile object or key string."""
    if isinstance(profile, RuleProfile):
        return profile.key
    return str(profile)


def _record_spot_info(record: OutcomeRecord) -> _SpotInfo | None:
    """Classify the starting spot of a record, or ``None`` if it lacks cards.

    A "spot" is keyed by the *starting* hand (the first two cards) versus the
    dealer upcard - the same shape a user types into ``coach`` - rather than
    the fully played-out final hand. This keeps spots like ``hard_16_vs_10``
    meaningful and lets coach context match saved history.
    """
    if not record.player_cards or not record.dealer_upcard:
        return None
    starting = list(record.player_cards[:2])
    try:
        return _describe_hand_spot(starting, record.dealer_upcard)
    except (ValueError, KeyError):
        return None


def _spot_confidence(total_seen: int, total_records: int) -> str:
    """Confidence label for a spot, honouring the global LOW-data rule."""
    if total_records < MIN_TOTAL_RECORDS or total_seen < MIN_SPOT_SAMPLE:
        return "LOW"
    if total_seen < 15:
        return "MEDIUM"
    return "HIGH"


def _spot_focus(
    *, loss_rate: float, player_busts: int, surrenders: int, win_rate: float
) -> str:
    """Recommend what to focus on for a spot based on its local results."""
    if surrenders > 0 and loss_rate >= WEAK_LOSS_RATE:
        return "Review whether surrender / the basic play is right here."
    if player_busts > 0 and loss_rate >= WEAK_LOSS_RATE:
        return "Frequent busts here - review hit/stand discipline."
    if loss_rate >= WEAK_LOSS_RATE:
        return "High local loss rate - revisit the correct basic play."
    if win_rate >= 0.6:
        return "Going well locally - keep playing the basic-strategy line."
    return "Keep practising; results are mixed so far."


def _build_spot(
    spot_id: str,
    info: _SpotInfo,
    records: list[OutcomeRecord],
    total_records: int,
) -> LearningSpot:
    """Aggregate a list of records that share a spot into a LearningSpot."""
    wins = sum(r.hands_won for r in records)
    losses = sum(r.hands_lost for r in records)
    pushes = sum(r.hands_pushed for r in records)
    surrenders = sum(r.hands_surrendered for r in records)
    player_busts = sum(r.player_busts for r in records)
    dealer_busts = sum(r.dealer_busts for r in records)
    split_records = sum(1 for r in records if r.is_split_hand)
    total_seen = len(records)

    # Most common profile for this spot (spots can appear under > 1 profile).
    profile_key = Counter(r.profile_key for r in records).most_common(1)[0][0]

    decided = wins + losses + pushes + surrenders
    loss_rate = losses / decided if decided else 0.0
    win_rate = wins / decided if decided else 0.0

    focus = _spot_focus(
        loss_rate=loss_rate,
        player_busts=player_busts,
        surrenders=surrenders,
        win_rate=win_rate,
    )
    confidence = _spot_confidence(total_seen, total_records)
    note = ""
    if total_seen < MIN_SPOT_SAMPLE:
        note = "small sample - read this as a hint, not a conclusion."

    return LearningSpot(
        spot_id=spot_id,
        category=info.category,
        player_pattern=info.player_pattern,
        dealer_upcard=info.dealer_label,
        profile_key=profile_key,
        total_seen=total_seen,
        wins=wins,
        losses=losses,
        pushes=pushes,
        surrenders=surrenders,
        player_busts=player_busts,
        dealer_busts=dealer_busts,
        split_records=split_records,
        recommended_focus=focus,
        confidence_label=confidence,
        note=note,
    )


def _is_weak_spot(spot: LearningSpot) -> bool:
    """A spot is weak if its loss rate is high or it busts / surrenders a lot."""
    if spot.decided_hands == 0:
        return False
    return (
        spot.loss_rate >= WEAK_LOSS_RATE
        or spot.player_busts > 0
        or spot.surrenders > 0
    )


def _is_high_variance_spot(spot: LearningSpot) -> bool:
    """High variance: a real mix of wins and losses on only a few samples."""
    return (
        spot.total_seen < 2 * MIN_SPOT_SAMPLE
        and spot.wins > 0
        and spot.losses > 0
    )


def _empty_summary() -> LearningSummary:
    """Return the summary used when there is no saved history at all."""
    return LearningSummary(
        total_records=0,
        profiles_seen=[],
        most_common_profile="(none)",
        strongest_spots=[],
        weakest_spots=[],
        most_common_outcomes=[],
        high_variance_spots=[],
        practice_recommendations=[],
        data_quality_note=(
            "No saved outcome history yet, so there is nothing to learn from. "
            "Use coach-play/play with --save-outcome first."
        ),
        warnings=[],
    )


def _data_quality_note(total_records: int) -> str:
    """Describe how much weight to put on the summary given the data volume."""
    if total_records < MIN_TOTAL_RECORDS:
        return (
            f"LOW confidence: only {total_records} saved record(s) "
            f"(< {MIN_TOTAL_RECORDS}). Treat every pattern below as a weak hint."
        )
    return (
        f"{total_records} saved records. Patterns are indicative for practice "
        "only and never change the strategy recommendation."
    )


def build_learning_summary(outcome_records: list[OutcomeRecord]) -> LearningSummary:
    """Summarise saved outcome records into adaptive-learning insights.

    Groups records by recognisable spot (when player cards / dealer upcard are
    present), detects strongest / weakest / high-variance spots, and proposes
    practice. It is read-only and never alters strategy.
    """
    if not outcome_records:
        return _empty_summary()

    total_records = len(outcome_records)
    profiles_seen = sorted({r.profile_key for r in outcome_records})
    most_common_profile = Counter(
        r.profile_key for r in outcome_records
    ).most_common(1)[0][0]
    most_common_outcomes = Counter(
        r.result_label or r.final_outcome for r in outcome_records
    ).most_common(5)

    # Group records by spot id (skipping records without usable cards).
    grouped: dict[str, list[OutcomeRecord]] = {}
    info_by_spot: dict[str, _SpotInfo] = {}
    for record in outcome_records:
        info = _record_spot_info(record)
        if info is None:
            continue
        grouped.setdefault(info.spot_id, []).append(record)
        info_by_spot.setdefault(info.spot_id, info)

    spots = [
        _build_spot(spot_id, info_by_spot[spot_id], records, total_records)
        for spot_id, records in grouped.items()
    ]

    weak = sorted(
        (s for s in spots if _is_weak_spot(s)),
        key=lambda s: (s.loss_rate, s.player_busts + s.surrenders, s.total_seen),
        reverse=True,
    )[:3]

    strong = sorted(
        (s for s in spots if s.decided_hands and s.win_rate >= 0.5),
        key=lambda s: (s.win_rate, s.total_seen),
        reverse=True,
    )[:3]

    high_variance = sorted(
        (s for s in spots if _is_high_variance_spot(s)),
        key=lambda s: s.total_seen,
        reverse=True,
    )[:3]

    recommendations = _practice_recommendations(weak, high_variance, total_records)

    return LearningSummary(
        total_records=total_records,
        profiles_seen=profiles_seen,
        most_common_profile=most_common_profile,
        strongest_spots=strong,
        weakest_spots=weak,
        most_common_outcomes=most_common_outcomes,
        high_variance_spots=high_variance,
        practice_recommendations=recommendations,
        data_quality_note=_data_quality_note(total_records),
        warnings=[EDUCATIONAL_NOTE],
    )


def _practice_recommendations(
    weak: list[LearningSpot],
    high_variance: list[LearningSpot],
    total_records: int,
) -> list[str]:
    """Turn weak / high-variance spots into plain practice suggestions."""
    recs: list[str] = []
    for spot in weak:
        recs.append(
            f"Drill {spot.spot_id.replace('_', ' ')}: {spot.recommended_focus}"
        )
    for spot in high_variance:
        if spot.spot_id in {s.spot_id for s in weak}:
            continue
        recs.append(
            f"Collect more reps of {spot.spot_id.replace('_', ' ')} - results "
            "are still noisy (high variance, small sample)."
        )
    if not recs:
        if total_records < MIN_TOTAL_RECORDS:
            recs.append(
                "Save more practice outcomes to unlock clearer spot insights."
            )
        else:
            recs.append(
                "No obvious weak spots yet - keep practising the full chart."
            )
    return recs


def _rate(count: int, decided: int) -> float:
    """Safe ratio helper used for local win/loss/push rates."""
    return count / decided if decided else 0.0


def build_history_context(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile | str = DEFAULT_PROFILE,
    history_dir: str | None = None,
) -> CoachHistoryContext:
    """Build local-history context for one hand the coach is advising.

    Loads saved outcomes for ``profile``, looks for the same spot (and, failing
    that, the same player pattern vs any dealer), and reports local rates plus
    a practice / caution note. It never changes the recommendation.
    """
    profile_key = _profile_key_of(profile)
    records = list_outcome_records(history_dir=history_dir, profile_key=profile_key)

    target = _describe_hand_spot(player_cards, dealer_upcard)

    if not records:
        return CoachHistoryContext(
            has_history=False,
            matching_records=0,
            similar_spot_summary=(
                f"No local history yet for {target.spot_id} under {profile_key}."
            ),
            local_win_rate=0.0,
            local_loss_rate=0.0,
            local_push_rate=0.0,
            practice_note=(
                "No saved outcome history yet. Use coach-play/play with "
                "--save-outcome first to build personalised context."
            ),
            caution_note="",
            warnings=[EDUCATIONAL_NOTE],
        )

    exact: list[OutcomeRecord] = []
    similar: list[OutcomeRecord] = []
    for record in records:
        info = _record_spot_info(record)
        if info is None:
            continue
        if info.spot_id == target.spot_id:
            exact.append(record)
            similar.append(record)
        elif info.player_pattern == target.player_pattern:
            similar.append(record)

    used = exact if exact else similar
    wins = sum(r.hands_won for r in used)
    losses = sum(r.hands_lost for r in used)
    pushes = sum(r.hands_pushed for r in used)
    surrenders = sum(r.hands_surrendered for r in used)
    decided = wins + losses + pushes + surrenders

    warnings = [EDUCATIONAL_NOTE]
    if exact:
        scope = f"{len(exact)} exact record(s) for {target.spot_id}"
    elif similar:
        scope = (
            f"No exact {target.spot_id} record(s); using {len(similar)} similar "
            f"{target.player_pattern} record(s) vs other dealer upcards"
        )
    else:
        scope = (
            f"History exists for {profile_key} but none matches {target.spot_id} "
            "or its pattern yet"
        )

    sample_size = len(used)
    caution_note = ""
    if sample_size < MIN_SPOT_SAMPLE:
        caution_note = (
            f"Small sample ({sample_size} record(s)) - this is local noise, not "
            "an edge or a prediction. The strategy recommendation stands."
        )
    else:
        caution_note = (
            "Local results are context only and never override the strategy "
            "recommendation."
        )

    practice_note = _history_practice_note(target.spot_id, used, decided, losses)

    return CoachHistoryContext(
        has_history=True,
        matching_records=len(exact),
        similar_spot_summary=scope,
        local_win_rate=_rate(wins, decided),
        local_loss_rate=_rate(losses, decided),
        local_push_rate=_rate(pushes, decided),
        practice_note=practice_note,
        caution_note=caution_note,
        warnings=warnings,
    )


def _history_practice_note(
    spot_id: str, used: list[OutcomeRecord], decided: int, losses: int
) -> str:
    """Compose the practice note for a coached hand's local history."""
    if not used:
        return (
            f"No local reps of {spot_id.replace('_', ' ')} yet - play a few with "
            "--save-outcome to personalise this."
        )
    loss_rate = losses / decided if decided else 0.0
    if loss_rate >= WEAK_LOSS_RATE:
        return (
            f"You have lost this spot often locally ({spot_id.replace('_', ' ')}). "
            "Practise it and confirm you are playing the basic line."
        )
    return (
        f"You have local reps of {spot_id.replace('_', ' ')}; keep following the "
        "basic-strategy recommendation."
    )


def format_learning_summary(summary: LearningSummary) -> str:
    """Render a :class:`LearningSummary` as compact text for the CLI."""
    lines: list[str] = []
    lines.append(f"Total records: {summary.total_records}")

    if summary.total_records == 0:
        lines.append(summary.data_quality_note)
        return "\n".join(lines)

    lines.append(f"Profiles seen: {', '.join(summary.profiles_seen) or '(none)'}")
    lines.append(f"Most common profile: {summary.most_common_profile}")

    lines.append("Strongest spots:")
    lines.append(_format_spot_lines(summary.strongest_spots))

    lines.append("Weakest spots:")
    lines.append(_format_spot_lines(summary.weakest_spots))

    lines.append("High variance spots:")
    lines.append(_format_spot_lines(summary.high_variance_spots))

    lines.append("Most common outcomes:")
    if summary.most_common_outcomes:
        for label, count in summary.most_common_outcomes:
            lines.append(f"  - {label} (x{count})")
    else:
        lines.append("  (none)")

    lines.append("Practice recommendations:")
    if summary.practice_recommendations:
        for rec in summary.practice_recommendations:
            lines.append(f"  - {rec}")
    else:
        lines.append("  (none)")

    lines.append(f"Data quality: {summary.data_quality_note}")
    for warning in summary.warnings:
        lines.append(f"Note: {warning}")
    return "\n".join(lines)


def _format_spot_lines(spots: list[LearningSpot]) -> str:
    """Render a list of spots as indented one-line summaries."""
    if not spots:
        return "  (none)"
    rows = []
    for spot in spots:
        rows.append(
            f"  - {spot.spot_id}: {spot.wins}W/{spot.losses}L/{spot.pushes}P"
            f" (seen {spot.total_seen}, {spot.confidence_label}) "
            f"-> {spot.recommended_focus}"
        )
    return "\n".join(rows)
