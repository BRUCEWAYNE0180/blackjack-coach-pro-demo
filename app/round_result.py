"""Local round-result tracking for Blackjack Coach Pro Demo (v2.2.0).

Records the final result of a *played round* after the coach gives its initial
recommendation, and reviews the **decision quality** separately from the
**round outcome** - a correct play can still lose, and a mistake can still win,
so a LOSS is never automatically treated as a bad decision.

The initial recommendation depends only on the player cards and the dealer
*upcard*. The dealer's second card and the final hands live here only and are
**never** used to change that recommendation.

Pure standard-library logic: it uses the hand evaluator and the card parser,
imports no Streamlit, and never changes ``strategy_engine.recommend`` or the
Hi-Lo math. Optional local persistence mirrors the project's existing pattern -
JSON files under the git-ignored ``.blackjack_coach/`` tree. It stores no money,
bankroll, bets, accounts, tokens, screenshots, or any sensitive data. See
docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .hand_evaluator import evaluate_hand

# The five player actions the coach can recommend / the player can take.
ACTIONS: tuple[str, ...] = ("HIT", "STAND", "DOUBLE", "SPLIT", "SURRENDER")
# The three round outcomes the player can record.
OUTCOMES: tuple[str, ...] = ("WIN", "LOSS", "PUSH")

# Folder layout for locally stored round results (kept out of version control
# via the repository .gitignore, which ignores the whole .blackjack_coach/ tree).
HISTORY_ROOT_DIRNAME = ".blackjack_coach"
ROUNDS_SUBDIR = "web_rounds"

EDUCATIONAL_NOTE = (
    "Round-result tracking is a local practice log for self-study only. It "
    "records win/loss/push to review decisions - never money, bankroll, bets, "
    "accounts, or personal data - and never guarantees winnings."
)

# A correct decision and a winning round are different things; this note is
# attached to every review so the UI can keep the two clearly separate.
DECISION_VS_OUTCOME_NOTE = (
    "Decision quality is independent of this round's outcome - a correct play "
    "can still lose, and a mistake can still win."
)

# How a double plays out, to clear up a common point of confusion in the UI.
DOUBLE_ONE_CARD_NOTE = (
    "Double: take exactly one additional card, then your turn ends. Do not hit "
    "again after doubling."
)
# Shown when a recorded double's final hand has more than one extra card.
DOUBLE_CARD_COUNT_WARNING = (
    "DOUBLE normally receives exactly one additional card. Check the final "
    "player cards."
)

_OUTCOME_LABELS = {"WIN": "Win", "LOSS": "Loss", "PUSH": "Push"}


def double_card_count_warning(
    action_taken: str | None,
    initial_player_cards: list[str] | tuple[str, ...],
    final_player_cards: list[str] | tuple[str, ...],
) -> str | None:
    """Warn if a recorded double did not take exactly one extra card.

    Returns :data:`DOUBLE_CARD_COUNT_WARNING` when the action taken is DOUBLE and
    the final player hand does not have exactly one more card than the initial
    hand (e.g. initial ``6,5`` -> final ``6,5,K,3``). Returns ``None`` otherwise,
    including for non-double actions or when there are not enough final cards yet
    to judge. This is a display-only check; it never changes the recommendation.
    """
    if str(action_taken or "").strip().upper() != "DOUBLE":
        return None
    if not final_player_cards or len(final_player_cards) < 2:
        return None
    if len(final_player_cards) != len(initial_player_cards) + 1:
        return DOUBLE_CARD_COUNT_WARNING
    return None


def normalize_action(action: str | None) -> str:
    """Normalise and validate a player/coach action token."""
    token = str(action or "").strip().upper()
    if token not in ACTIONS:
        raise ValueError(
            f"Unknown action {action!r}; expected one of {', '.join(ACTIONS)}.")
    return token


def normalize_outcome(outcome: str | None) -> str:
    """Normalise and validate a round outcome token (WIN/LOSS/PUSH)."""
    token = str(outcome or "").strip().upper()
    if token not in OUTCOMES:
        raise ValueError(
            f"Unknown outcome {outcome!r}; expected one of {', '.join(OUTCOMES)}.")
    return token


@dataclass(frozen=True)
class RoundResultReview:
    """A render-ready review of a played round.

    ``followed_coach`` / ``decision_label`` describe **decision quality** and
    depend only on whether the action taken matched the coach's recommendation -
    never on whether the round was won. ``outcome`` / ``outcome_label`` describe
    the **round result** independently.
    """

    coach_recommended_action: str
    action_taken: str
    followed_coach: bool
    decision_label: str
    outcome: str
    outcome_label: str
    suggested_outcome: str | None
    outcome_matches_suggestion: bool
    player_final_cards: tuple[str, ...]
    dealer_final_cards: tuple[str, ...]
    player_total: int
    dealer_total: int
    player_busted: bool
    dealer_busted: bool
    note: str = DECISION_VS_OUTCOME_NOTE


def suggest_outcome(
    player_final_cards: list[str] | tuple[str, ...],
    dealer_final_cards: list[str] | tuple[str, ...],
    action_taken: str | None = None,
) -> str | None:
    """Suggest WIN/LOSS/PUSH from the final hands (a display helper only).

    Returns ``None`` when it cannot be determined (e.g. no cards yet). Surrender
    is treated as a loss (half the bet) for suggestion purposes. This is only a
    convenience for the UI; the user always records the actual outcome.
    """
    if action_taken and str(action_taken).strip().upper() == "SURRENDER":
        return "LOSS"
    if not player_final_cards:
        return None
    player = evaluate_hand(player_final_cards)
    if player.is_bust:
        return "LOSS"
    if not dealer_final_cards:
        return None
    dealer = evaluate_hand(dealer_final_cards)
    if dealer.is_bust:
        return "WIN"
    if player.total > dealer.total:
        return "WIN"
    if player.total < dealer.total:
        return "LOSS"
    return "PUSH"


def build_round_review(
    coach_recommended_action: str,
    action_taken: str,
    player_final_cards: list[str] | tuple[str, ...],
    dealer_final_cards: list[str] | tuple[str, ...],
    outcome: str | None = None,
) -> RoundResultReview:
    """Build a :class:`RoundResultReview` for a played round.

    The recorded ``outcome`` is taken as given (WIN/LOSS/PUSH); if omitted it
    falls back to the suggestion computed from the final hands. The decision
    review (``followed_coach``) is computed purely from the actions and never
    from the outcome.
    """
    coach_action = normalize_action(coach_recommended_action)
    action = normalize_action(action_taken)

    if not player_final_cards:
        raise ValueError("Enter the player's final cards (at least two).")
    player = evaluate_hand(player_final_cards)
    dealer = evaluate_hand(dealer_final_cards) if dealer_final_cards else None

    suggested = suggest_outcome(player_final_cards, dealer_final_cards, action)
    if outcome is None:
        if suggested is None:
            raise ValueError("Provide the round outcome (WIN, LOSS, or PUSH).")
        resolved = suggested
    else:
        resolved = normalize_outcome(outcome)

    followed = action == coach_action
    decision_label = (
        "Followed coach recommendation" if followed
        else "Different from coach recommendation"
    )

    return RoundResultReview(
        coach_recommended_action=coach_action,
        action_taken=action,
        followed_coach=followed,
        decision_label=decision_label,
        outcome=resolved,
        outcome_label=_OUTCOME_LABELS[resolved],
        suggested_outcome=suggested,
        outcome_matches_suggestion=(suggested is not None and suggested == resolved),
        player_final_cards=tuple(player_final_cards),
        dealer_final_cards=tuple(dealer_final_cards) if dealer_final_cards else (),
        player_total=player.total,
        dealer_total=dealer.total if dealer else 0,
        player_busted=player.is_bust,
        dealer_busted=dealer.is_bust if dealer else False,
    )


@dataclass(frozen=True)
class RoundResultRecord:
    """A persisted summary of one played round and its decision review."""

    round_id: str
    created_at: str
    profile_key: str
    initial_player_cards: tuple[str, ...]
    dealer_upcard: str
    coach_recommended_action: str
    action_taken: str
    followed_coach: bool
    decision_label: str
    player_final_cards: tuple[str, ...]
    dealer_final_cards: tuple[str, ...]
    player_total: int
    dealer_total: int
    player_busted: bool
    dealer_busted: bool
    outcome: str
    outcome_label: str
    note: str = DECISION_VS_OUTCOME_NOTE


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def build_round_result_record(
    review: RoundResultReview,
    profile_key: str,
    initial_player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
) -> RoundResultRecord:
    """Build a persistable :class:`RoundResultRecord` from a review."""
    return RoundResultRecord(
        round_id=_new_id(),
        created_at=datetime.now().isoformat(timespec="seconds"),
        profile_key=profile_key,
        initial_player_cards=tuple(initial_player_cards),
        dealer_upcard=dealer_upcard,
        coach_recommended_action=review.coach_recommended_action,
        action_taken=review.action_taken,
        followed_coach=review.followed_coach,
        decision_label=review.decision_label,
        player_final_cards=review.player_final_cards,
        dealer_final_cards=review.dealer_final_cards,
        player_total=review.player_total,
        dealer_total=review.dealer_total,
        player_busted=review.player_busted,
        dealer_busted=review.dealer_busted,
        outcome=review.outcome,
        outcome_label=review.outcome_label,
        note=review.note,
    )


def default_round_history_dir() -> Path:
    """Return the default local round-results directory (under the cwd)."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / ROUNDS_SUBDIR


def ensure_round_history_dir(path: str | Path | None = None) -> Path:
    """Create the round-results directory if needed and return it as a Path."""
    directory = Path(path) if path is not None else default_round_history_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _record_filename(record: RoundResultRecord) -> str:
    """Build a sortable, filesystem-safe filename for a record."""
    try:
        stamp = datetime.fromisoformat(record.created_at).strftime("%Y%m%d_%H%M%S")
    except ValueError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"round_{stamp}_{record.round_id}.json"


def save_round_result_record(
    record: RoundResultRecord,
    history_dir: str | Path | None = None,
) -> Path:
    """Save ``record`` as JSON and return the written file path."""
    directory = ensure_round_history_dir(history_dir)
    path = directory / _record_filename(record)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(asdict(record), fh, indent=2, sort_keys=True)
    return path


def load_round_result_record(path: str | Path) -> RoundResultRecord:
    """Load a :class:`RoundResultRecord` from a JSON file."""
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return RoundResultRecord(
        round_id=data["round_id"],
        created_at=data["created_at"],
        profile_key=data.get("profile_key", ""),
        initial_player_cards=tuple(data.get("initial_player_cards", [])),
        dealer_upcard=data.get("dealer_upcard", ""),
        coach_recommended_action=data.get("coach_recommended_action", ""),
        action_taken=data.get("action_taken", ""),
        followed_coach=bool(data.get("followed_coach", False)),
        decision_label=data.get("decision_label", ""),
        player_final_cards=tuple(data.get("player_final_cards", [])),
        dealer_final_cards=tuple(data.get("dealer_final_cards", [])),
        player_total=int(data.get("player_total", 0)),
        dealer_total=int(data.get("dealer_total", 0)),
        player_busted=bool(data.get("player_busted", False)),
        dealer_busted=bool(data.get("dealer_busted", False)),
        outcome=data.get("outcome", ""),
        outcome_label=data.get("outcome_label", ""),
        note=data.get("note", ""),
    )


def list_round_result_records(
    history_dir: str | Path | None = None,
    limit: int | None = None,
    profile_key: str | None = None,
) -> list[RoundResultRecord]:
    """Return saved round records sorted oldest-first.

    Returns an empty list when the directory does not exist yet. Unreadable or
    malformed files are skipped rather than failing the listing.
    """
    directory = (
        Path(history_dir) if history_dir is not None
        else default_round_history_dir()
    )
    if not directory.is_dir():
        return []

    records: list[RoundResultRecord] = []
    for path in directory.glob("round_*.json"):
        try:
            records.append(load_round_result_record(path))
        except (ValueError, KeyError, OSError):
            continue

    if profile_key is not None:
        records = [r for r in records if r.profile_key == profile_key]

    records.sort(key=lambda r: (r.created_at, r.round_id))

    if limit is not None and limit >= 0:
        records = records[-limit:] if limit else []
    return records


@dataclass(frozen=True)
class RoundResultSummary:
    """Aggregate statistics that keep decision quality and outcome separate."""

    total_rounds: int
    wins: int
    losses: int
    pushes: int
    followed_coach: int
    differed_from_coach: int
    followed_but_lost: int
    differed_but_won: int
    note: str = EDUCATIONAL_NOTE


def summarize_round_results(
    records: list[RoundResultRecord],
) -> RoundResultSummary:
    """Compute aggregate statistics across ``records``.

    Deliberately reports decision quality (followed coach) and round outcome
    (win/loss/push) as separate dimensions, plus the two informative crosses:
    decisions that followed the coach yet lost, and decisions that differed yet
    won - underlining that outcome does not equal decision quality.
    """
    wins = sum(1 for r in records if r.outcome == "WIN")
    losses = sum(1 for r in records if r.outcome == "LOSS")
    pushes = sum(1 for r in records if r.outcome == "PUSH")
    followed = sum(1 for r in records if r.followed_coach)
    differed = sum(1 for r in records if not r.followed_coach)
    followed_but_lost = sum(
        1 for r in records if r.followed_coach and r.outcome == "LOSS")
    differed_but_won = sum(
        1 for r in records if not r.followed_coach and r.outcome == "WIN")
    return RoundResultSummary(
        total_rounds=len(records),
        wins=wins,
        losses=losses,
        pushes=pushes,
        followed_coach=followed,
        differed_from_coach=differed,
        followed_but_lost=followed_but_lost,
        differed_but_won=differed_but_won,
    )
