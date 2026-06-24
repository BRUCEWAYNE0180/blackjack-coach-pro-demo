"""Rule profile comparison for Blackjack Coach Pro Demo (v2.5.0).

A small, **local/demo** study tool that auto-plays many simulated rounds under
several rule profiles (always following the coach) and reports how the
WIN / LOSS / PUSH behaviour differs between them. It exists purely to *study*
which table rules tend to be friendlier or harder for the player.

It builds on :func:`app.practice_table.simulate_following_coach` and never
changes ``strategy_engine.recommend`` or the Hi-Lo math. It involves no money,
bankroll, EV-as-decision, real betting, casino connectivity, network access,
camera, screen reading, or scraping. This module imports no Streamlit and is
fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from .practice_table import (
    DemoBalanceResult,
    SimulationResult,
    simulate_demo_balance,
    simulate_following_coach,
    simulation_interpretation,
    simulation_looks_plausible,
)
from .rules import get_profile

# Default number of rounds simulated per profile in a comparison run.
DEFAULT_COMPARE_ROUNDS = 1000
# Default fixed seed so a comparison is reproducible.
DEFAULT_COMPARE_SEED = 42

# Educational notes shown alongside a comparison. These describe well-known
# rule tendencies; they are study aids, never profit promises.
RULE_COMPARISON_NOTES: tuple[str, ...] = (
    "S17 (dealer stands on soft 17) is usually more favorable to the player "
    "than H17 (dealer hits soft 17).",
    "Allowing double after split (DAS) usually helps the player a little.",
    "Late surrender can reduce losses on the worst hands.",
    "More wins does not always mean better EV - pushes, blackjack payouts and "
    "how much you win or lose per hand also matter.",
    "This simulation does not predict winnings or guarantee any result; it only "
    "compares how rule sets behave in a local demo.",
)


@dataclass(frozen=True)
class ProfileComparisonRow:
    """One profile's simulated result inside a comparison."""

    profile_key: str
    profile_name: str
    result: SimulationResult
    plausible: bool
    interpretation: str
    balance: DemoBalanceResult | None = None


@dataclass(frozen=True)
class ComparisonSummary:
    """Highlights across a set of compared profiles (by simulated behaviour)."""

    most_favorable_key: str | None = None
    most_favorable_name: str | None = None
    lowest_loss_key: str | None = None
    lowest_loss_name: str | None = None
    highest_push_key: str | None = None
    highest_push_name: str | None = None
    most_difficult_key: str | None = None
    most_difficult_name: str | None = None
    # Net demo units (profitability proxy, not win %).
    best_units_key: str | None = None
    best_units_name: str | None = None
    worst_units_key: str | None = None
    worst_units_name: str | None = None
    # Set when the profile that wins the most hands is NOT the one with the
    # best net units (i.e. fewer wins can still mean fewer units lost).
    units_beats_winrate_note: str | None = None


def _dedupe_preserving_order(keys: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def compare_profiles(
    profile_keys: list[str],
    rounds: int = DEFAULT_COMPARE_ROUNDS,
    seed: int | None = DEFAULT_COMPARE_SEED,
    starting_balance: float | None = None,
    base_bet: float | None = None,
) -> list[ProfileComparisonRow]:
    """Simulate ``rounds`` auto-play hands for each profile and return a row
    per profile.

    Every profile uses the same fixed ``seed`` so the whole comparison is
    reproducible and deterministic. Duplicate keys are collapsed while
    preserving the first occurrence order. Unknown keys raise ``KeyError`` (via
    :func:`app.rules.get_profile`).

    When both ``starting_balance`` and ``base_bet`` are given, each profile is
    run as a flat-bet **demo-balance** simulation (practice points only); the
    row's ``balance`` holds the :class:`DemoBalanceResult` and ``result`` is its
    result over the hands actually played.
    """
    use_balance = starting_balance is not None and base_bet is not None
    rows: list[ProfileComparisonRow] = []
    for key in _dedupe_preserving_order(list(profile_keys)):
        profile = get_profile(key)
        balance = None
        if use_balance:
            balance = simulate_demo_balance(
                key, rounds=rounds, seed=seed,
                starting_balance=starting_balance, base_bet=base_bet)
            result = balance.result
        else:
            result = simulate_following_coach(key, rounds=rounds, seed=seed)
        rows.append(
            ProfileComparisonRow(
                profile_key=key,
                profile_name=profile.name,
                result=result,
                plausible=simulation_looks_plausible(result),
                interpretation=simulation_interpretation(result),
                balance=balance,
            )
        )
    return rows


def summarize_comparison(rows: list[ProfileComparisonRow]) -> ComparisonSummary:
    """Pick the friendliest / hardest profiles from a comparison.

    "Most favorable" is the highest simulated win rate and "most difficult" is
    the highest simulated loss rate, while ``best_units`` / ``worst_units`` rank
    by net demo units (a profitability proxy). Win % and net units can disagree,
    so a note is set when the most-winning profile is not the best by units.
    These describe the local demo only and never claim a real-world edge or any
    guaranteed outcome.
    """
    if not rows:
        return ComparisonSummary()

    most_favorable = max(rows, key=lambda r: r.result.win_rate)
    lowest_loss = min(rows, key=lambda r: r.result.loss_rate)
    highest_push = max(rows, key=lambda r: r.result.push_rate)
    most_difficult = max(rows, key=lambda r: r.result.loss_rate)
    best_units = max(rows, key=lambda r: r.result.units_per_100)
    worst_units = min(rows, key=lambda r: r.result.units_per_100)

    units_note = None
    if len(rows) > 1 and best_units.profile_key != most_favorable.profile_key:
        units_note = (
            f"{most_favorable.profile_name} wins the most hands, but "
            f"{best_units.profile_name} has the best net units - winning more "
            "hands does not always mean losing fewer units."
        )

    return ComparisonSummary(
        most_favorable_key=most_favorable.profile_key,
        most_favorable_name=most_favorable.profile_name,
        lowest_loss_key=lowest_loss.profile_key,
        lowest_loss_name=lowest_loss.profile_name,
        highest_push_key=highest_push.profile_key,
        highest_push_name=highest_push.profile_name,
        most_difficult_key=most_difficult.profile_key,
        most_difficult_name=most_difficult.profile_name,
        best_units_key=best_units.profile_key,
        best_units_name=best_units.profile_name,
        worst_units_key=worst_units.profile_key,
        worst_units_name=worst_units.profile_name,
        units_beats_winrate_note=units_note,
    )
