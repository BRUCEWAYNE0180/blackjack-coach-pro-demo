"""Local outcome (win/loss) history for Blackjack Coach Pro Demo.

Records the result of played practice hands - wins, losses, pushes, surrenders,
busts, and split / re-split results - in a local JSON folder so the coach can
review outcomes over time and start learning from them. This complements the
v1.7.0 decision tooling and never changes ``strategy_engine.recommend``.

This is a *summary only*: it never stores money, bankroll, real bets, accounts,
tokens, screenshots, or any sensitive data. Standard library only - no database,
no network, no cloud. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .simulator import HandOutcome

if TYPE_CHECKING:  # only used for type hints; avoids any import surprises
    from .simulator import PlayedHand, PlayedSplitHand

# Folder layout for locally stored outcomes (kept out of version control via
# the repository .gitignore, which ignores the whole .blackjack_coach/ tree).
HISTORY_ROOT_DIRNAME = ".blackjack_coach"
OUTCOMES_SUBDIR = "outcomes"

EDUCATIONAL_NOTE = (
    "Local outcome history is a practice summary for self-study only. It stores "
    "no money, bankroll, bets, accounts, or personal data, and never "
    "guarantees winnings."
)

# Outcomes that count as a player win / loss for tally purposes.
_WIN_OUTCOMES = (HandOutcome.PLAYER_WIN, HandOutcome.DEALER_BUST)
_LOSS_OUTCOMES = (HandOutcome.DEALER_WIN, HandOutcome.PLAYER_BUST)

# Human-readable label for a single resolved outcome.
_RESULT_LABELS = {
    HandOutcome.PLAYER_WIN: "Win",
    HandOutcome.DEALER_BUST: "Win (dealer bust)",
    HandOutcome.DEALER_WIN: "Loss",
    HandOutcome.PLAYER_BUST: "Loss (player bust)",
    HandOutcome.PUSH: "Push",
    HandOutcome.SURRENDER: "Surrender",
}


@dataclass(frozen=True)
class OutcomeRecord:
    """A persisted summary of one played practice hand's result."""

    outcome_id: str
    created_at: str
    profile_key: str
    mode: str
    seed: int | None
    player_cards: tuple[str, ...]
    dealer_upcard: str
    dealer_cards: tuple[str, ...]
    actions_taken: list[str]
    final_outcome: str
    result_label: str
    is_split_hand: bool
    split_hands_count: int
    hands_won: int
    hands_lost: int
    hands_pushed: int
    hands_surrendered: int
    player_busts: int
    dealer_busts: int
    warnings: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class OutcomeSummary:
    """Aggregate statistics across a set of :class:`OutcomeRecord`."""

    total_records: int
    wins: int
    losses: int
    pushes: int
    surrenders: int
    player_busts: int
    dealer_busts: int
    split_records: int
    average_split_hands: float
    most_common_profile: str
    most_common_outcomes: list[tuple[str, int]]
    note: str = ""


def default_outcome_history_dir() -> Path:
    """Return the default local outcomes directory (under the current dir)."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / OUTCOMES_SUBDIR


def ensure_outcome_history_dir(path: str | Path | None = None) -> Path:
    """Create the outcomes directory if needed and return it as a Path."""
    directory = Path(path) if path is not None else default_outcome_history_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _classify(outcome: HandOutcome | None) -> str:
    """Classify an outcome as ``win``/``loss``/``push``/``surrender``."""
    if outcome in _WIN_OUTCOMES:
        return "win"
    if outcome in _LOSS_OUTCOMES:
        return "loss"
    if outcome == HandOutcome.PUSH:
        return "push"
    if outcome == HandOutcome.SURRENDER:
        return "surrender"
    return "unresolved"


def _tally(outcomes: list[HandOutcome | None]) -> dict[str, int]:
    """Tally win/loss/push/surrender and bust counts across outcomes."""
    counts = {"win": 0, "loss": 0, "push": 0, "surrender": 0}
    player_busts = 0
    for outcome in outcomes:
        counts[_classify(outcome)] = counts.get(_classify(outcome), 0) + 1
        if outcome == HandOutcome.PLAYER_BUST:
            player_busts += 1
    dealer_busts = 1 if HandOutcome.DEALER_BUST in outcomes else 0
    return {
        "win": counts["win"],
        "loss": counts["loss"],
        "push": counts["push"],
        "surrender": counts["surrender"],
        "player_busts": player_busts,
        "dealer_busts": dealer_busts,
    }


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _build_from_played_hand(
    hand: "PlayedHand", profile_key: str, seed: int | None
) -> OutcomeRecord:
    """Build a record from a non-split :class:`PlayedHand`."""
    outcome = hand.final_outcome
    tally = _tally([outcome])
    label = _RESULT_LABELS.get(outcome, "Unresolved") if outcome else "Unresolved"
    return OutcomeRecord(
        outcome_id=_new_id(),
        created_at=datetime.now().isoformat(timespec="seconds"),
        profile_key=profile_key,
        mode="play",
        seed=seed,
        player_cards=tuple(hand.player_cards),
        dealer_upcard=hand.dealer_cards[0] if hand.dealer_cards else "",
        dealer_cards=tuple(hand.dealer_cards),
        actions_taken=list(hand.actions_taken),
        final_outcome=outcome.value if outcome else "UNRESOLVED",
        result_label=label,
        is_split_hand=False,
        split_hands_count=0,
        hands_won=tally["win"],
        hands_lost=tally["loss"],
        hands_pushed=tally["push"],
        hands_surrendered=tally["surrender"],
        player_busts=tally["player_busts"],
        dealer_busts=tally["dealer_busts"],
        warnings=list(hand.warnings),
        note=hand.note,
    )


def _build_from_split_hand(
    hand: "PlayedSplitHand", profile_key: str, seed: int | None
) -> OutcomeRecord:
    """Build a record from a :class:`PlayedSplitHand` (split / re-split tree)."""
    outcomes = list(hand.outcomes_by_hand)
    tally = _tally(outcomes)
    # Keep per-sub-hand actions readable inside a single list field.
    actions = [
        f"hand {i}: {', '.join(acts) if acts else '(none)'}"
        for i, acts in enumerate(hand.actions_by_hand, start=1)
    ]
    label = (
        f"Split: {tally['win']}W / {tally['loss']}L / {tally['push']}P"
        + (f" / {tally['surrender']}R" if tally["surrender"] else "")
    )
    return OutcomeRecord(
        outcome_id=_new_id(),
        created_at=datetime.now().isoformat(timespec="seconds"),
        profile_key=profile_key,
        mode="play_split",
        seed=seed,
        player_cards=tuple(hand.original_player_cards),
        dealer_upcard=hand.dealer_cards[0] if hand.dealer_cards else "",
        dealer_cards=tuple(hand.dealer_cards),
        actions_taken=actions,
        final_outcome="SPLIT",
        result_label=label,
        is_split_hand=True,
        split_hands_count=hand.num_split_hands,
        hands_won=tally["win"],
        hands_lost=tally["loss"],
        hands_pushed=tally["push"],
        hands_surrendered=tally["surrender"],
        player_busts=tally["player_busts"],
        dealer_busts=tally["dealer_busts"],
        warnings=list(hand.warnings),
        note=hand.note,
    )


def build_outcome_record(
    played_hand: "PlayedHand | PlayedSplitHand",
    profile_key: str,
    seed: int | None = None,
) -> OutcomeRecord:
    """Build an :class:`OutcomeRecord` from a played hand.

    Supports both a normal :class:`app.simulator.PlayedHand` and a
    :class:`app.simulator.PlayedSplitHand` (where per-sub-hand results are
    counted). Detection is by structure so there is no hard import coupling.
    """
    if hasattr(played_hand, "outcomes_by_hand"):
        return _build_from_split_hand(played_hand, profile_key, seed)  # type: ignore[arg-type]
    return _build_from_played_hand(played_hand, profile_key, seed)  # type: ignore[arg-type]


def _record_filename(record: OutcomeRecord) -> str:
    """Build a sortable, filesystem-safe filename for a record."""
    try:
        stamp = datetime.fromisoformat(record.created_at).strftime("%Y%m%d_%H%M%S")
    except ValueError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"outcome_{stamp}_{record.outcome_id}.json"


def save_outcome_record(
    record: OutcomeRecord,
    history_dir: str | Path | None = None,
) -> Path:
    """Save ``record`` as JSON and return the written file path."""
    directory = ensure_outcome_history_dir(history_dir)
    path = directory / _record_filename(record)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(asdict(record), fh, indent=2, sort_keys=True)
    return path


def load_outcome_record(path: str | Path) -> OutcomeRecord:
    """Load an :class:`OutcomeRecord` from a JSON file."""
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return OutcomeRecord(
        outcome_id=data["outcome_id"],
        created_at=data["created_at"],
        profile_key=data["profile_key"],
        mode=data["mode"],
        seed=data.get("seed"),
        player_cards=tuple(data.get("player_cards", [])),
        dealer_upcard=data.get("dealer_upcard", ""),
        dealer_cards=tuple(data.get("dealer_cards", [])),
        actions_taken=list(data.get("actions_taken", [])),
        final_outcome=data["final_outcome"],
        result_label=data.get("result_label", ""),
        is_split_hand=bool(data.get("is_split_hand", False)),
        split_hands_count=int(data.get("split_hands_count", 0)),
        hands_won=int(data.get("hands_won", 0)),
        hands_lost=int(data.get("hands_lost", 0)),
        hands_pushed=int(data.get("hands_pushed", 0)),
        hands_surrendered=int(data.get("hands_surrendered", 0)),
        player_busts=int(data.get("player_busts", 0)),
        dealer_busts=int(data.get("dealer_busts", 0)),
        warnings=list(data.get("warnings", [])),
        note=data.get("note", ""),
    )


def list_outcome_records(
    history_dir: str | Path | None = None,
    limit: int | None = None,
    profile_key: str | None = None,
) -> list[OutcomeRecord]:
    """Return saved outcome records sorted oldest-first.

    Args:
        history_dir: Directory to read (defaults to the local outcomes dir).
        limit: If given, return only the most recent ``limit`` records.
        profile_key: If given, keep only records for that profile.

    Returns an empty list when the directory does not exist yet.
    """
    directory = (
        Path(history_dir) if history_dir is not None
        else default_outcome_history_dir()
    )
    if not directory.is_dir():
        return []

    records: list[OutcomeRecord] = []
    for path in directory.glob("outcome_*.json"):
        try:
            records.append(load_outcome_record(path))
        except (ValueError, KeyError, OSError):
            # Skip unreadable / malformed files rather than failing the listing.
            continue

    if profile_key is not None:
        records = [r for r in records if r.profile_key == profile_key]

    records.sort(key=lambda r: (r.created_at, r.outcome_id))

    if limit is not None and limit >= 0:
        records = records[-limit:] if limit else []
    return records


def summarize_outcomes(records: list[OutcomeRecord]) -> OutcomeSummary:
    """Compute aggregate statistics across ``records``."""
    if not records:
        return OutcomeSummary(
            total_records=0,
            wins=0,
            losses=0,
            pushes=0,
            surrenders=0,
            player_busts=0,
            dealer_busts=0,
            split_records=0,
            average_split_hands=0.0,
            most_common_profile="(none)",
            most_common_outcomes=[],
            note=EDUCATIONAL_NOTE,
        )

    split_records = [r for r in records if r.is_split_hand]
    avg_split = (
        sum(r.split_hands_count for r in split_records) / len(split_records)
        if split_records else 0.0
    )

    profile_counter: Counter[str] = Counter(r.profile_key for r in records)
    outcome_counter: Counter[str] = Counter(r.final_outcome for r in records)

    return OutcomeSummary(
        total_records=len(records),
        wins=sum(r.hands_won for r in records),
        losses=sum(r.hands_lost for r in records),
        pushes=sum(r.hands_pushed for r in records),
        surrenders=sum(r.hands_surrendered for r in records),
        player_busts=sum(r.player_busts for r in records),
        dealer_busts=sum(r.dealer_busts for r in records),
        split_records=len(split_records),
        average_split_hands=avg_split,
        most_common_profile=profile_counter.most_common(1)[0][0],
        most_common_outcomes=outcome_counter.most_common(5),
        note=EDUCATIONAL_NOTE,
    )
