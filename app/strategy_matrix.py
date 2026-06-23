"""Complete strategy-matrix audit for Blackjack Coach Pro Demo.

Builds full basic-strategy decision matrices (hard totals, soft totals, and
pairs) for a rule profile by calling the stable
:func:`app.strategy_engine.recommend`, then audits them for coverage: missing
cells, unknown actions, and cells where the chart's ideal play falls back to a
legal alternative under the profile's rules.

This module never changes basic strategy. It is a coverage / confidence tool so
the coach can prove it has an answer for every reasonable hand against every
dealer upcard, and explain *how* that answer was reached (direct table action
or a legal fallback).

Educational/coaching tool for local practice, demo money, video games,
recreational tournaments, and training. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .rules import DEFAULT_PROFILE, RuleProfile
from .strategy_engine import Action, recommend

# Dealer upcards, in display order: 2-10 then Ace. These label the columns of
# every matrix and are the canonical coverage set.
DEALER_UPCARDS: tuple[str, ...] = (
    "2", "3", "4", "5", "6", "7", "8", "9", "10", "A",
)

# Compact, single-letter codes used when rendering a matrix as a table.
ACTION_CODES: dict[Action, str] = {
    Action.HIT: "H",
    Action.STAND: "S",
    Action.DOUBLE: "D",
    Action.SPLIT: "P",
    Action.SURRENDER: "R",
}

# Representative two/three-card hands for each hard total (5-21). They are
# deliberately non-pair and non-soft so the engine routes them through the
# hard-total table. Totals 20 and 21 use three cards because no two distinct,
# non-ten cards make them without forming a pair.
_HARD_REPS: dict[int, tuple[str, ...]] = {
    5: ("2", "3"), 6: ("2", "4"), 7: ("2", "5"), 8: ("2", "6"),
    9: ("2", "7"), 10: ("2", "8"), 11: ("2", "9"), 12: ("10", "2"),
    13: ("10", "3"), 14: ("10", "4"), 15: ("10", "5"), 16: ("10", "6"),
    17: ("10", "7"), 18: ("10", "8"), 19: ("10", "9"),
    20: ("10", "7", "3"), 21: ("10", "7", "4"),
}

# Representative soft hands for each soft total (13-21): A,2 .. A,10.
_SOFT_REPS: dict[int, tuple[str, ...]] = {
    13: ("A", "2"), 14: ("A", "3"), 15: ("A", "4"), 16: ("A", "5"),
    17: ("A", "6"), 18: ("A", "7"), 19: ("A", "8"), 20: ("A", "9"),
    21: ("A", "10"),
}

# Representative pairs, in display order: A,A then 2,2 .. 10,10.
_PAIR_REPS: tuple[tuple[str, str], ...] = (
    ("A", "A"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"),
    ("6", "6"), ("7", "7"), ("8", "8"), ("9", "9"), ("10", "10"),
)


@dataclass(frozen=True)
class StrategyCell:
    """One decision in a strategy matrix: a hand vs a dealer upcard.

    Attributes:
        player_category: ``"hard"``, ``"soft"``, or ``"pair"``.
        player_label: Human label for the row, e.g. ``"Hard 16"`` or
            ``"Pair 8s"``.
        representative_cards: A concrete hand that produces this row.
        dealer_upcard: The dealer's upcard label (``"2"``..``"10"``, ``"A"``).
        profile_key: The rule profile used.
        recommended_action: The action the engine recommends under the profile
            (after applying legality fallbacks).
        raw_action: The chart's ideal action assuming every option is legal.
        fallback_applied: True when ``recommended_action`` differs from
            ``raw_action`` because an option was not available.
        warnings: Fallback / advisory notes for this cell.
        reason: The engine's human-readable reason for the recommendation.
    """

    player_category: str
    player_label: str
    representative_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    recommended_action: Action
    raw_action: Action
    fallback_applied: bool
    warnings: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def cell_id(self) -> str:
        """A stable identifier such as ``"Hard 16 vs A"``."""
        return f"{self.player_label} vs {self.dealer_upcard}"


@dataclass(frozen=True)
class StrategyMatrix:
    """A full basic-strategy matrix for one rule profile.

    Each of ``hard_totals``, ``soft_totals`` and ``pairs`` is a list of rows,
    where each row is a list of :class:`StrategyCell` (one per dealer upcard, in
    :data:`DEALER_UPCARDS` order).
    """

    profile_key: str
    hard_totals: list[list[StrategyCell]]
    soft_totals: list[list[StrategyCell]]
    pairs: list[list[StrategyCell]]
    total_cells: int
    missing_cells: list[str] = field(default_factory=list)
    fallback_cells: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def iter_cells(self) -> list[StrategyCell]:
        """Return every cell across all three sections, in order."""
        cells: list[StrategyCell] = []
        for section in (self.hard_totals, self.soft_totals, self.pairs):
            for row in section:
                cells.extend(row)
        return cells

    def section(self, name: str) -> list[list[StrategyCell]]:
        """Return one section's rows by name (``hard``/``soft``/``pairs``)."""
        mapping = {
            "hard": self.hard_totals,
            "soft": self.soft_totals,
            "pairs": self.pairs,
        }
        if name not in mapping:
            raise ValueError(
                f"Unknown matrix section {name!r}; expected one of "
                "hard, soft, pairs."
            )
        return mapping[name]


@dataclass(frozen=True)
class MatrixAuditReport:
    """The result of auditing a :class:`StrategyMatrix` for coverage."""

    profile_key: str
    total_cells: int
    missing_cells: list[str]
    fallback_cells: list[str]
    unknown_action_cells: list[str]
    warnings: list[str]
    is_complete: bool


def _build_cell(
    category: str,
    label: str,
    cards: tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile,
) -> StrategyCell:
    """Build a single :class:`StrategyCell` by consulting the engine twice.

    The recommended action uses the profile's natural legality; the raw action
    forces every option legal to expose the chart's ideal play, so a fallback
    can be detected by comparison.
    """
    recommended = recommend(cards, dealer_upcard, profile)
    raw = recommend(
        cards, dealer_upcard, profile,
        can_double=True, can_surrender=True, can_split=True,
    )
    fallback_notes = [w for w in recommended.warnings if "Chart prefers" in w]
    # A fallback occurred when the engine itself noted the chart's ideal play
    # was unavailable, or when forcing every option legal changes the action.
    fallback = bool(fallback_notes) or recommended.action != raw.action
    return StrategyCell(
        player_category=category,
        player_label=label,
        representative_cards=tuple(cards),
        dealer_upcard=dealer_upcard,
        profile_key=profile.key,
        recommended_action=recommended.action,
        raw_action=raw.action,
        fallback_applied=fallback,
        warnings=fallback_notes,
        reason=recommended.reason,
    )


def _pair_label(rank: str) -> str:
    """Return a pair row label such as ``"Pair As"`` or ``"Pair 10s"``."""
    return f"Pair {rank}s"


def generate_hard_total_matrix(
    profile: RuleProfile = DEFAULT_PROFILE,
) -> list[list[StrategyCell]]:
    """Generate hard-total rows (5-21) vs every dealer upcard."""
    rows: list[list[StrategyCell]] = []
    for total in range(5, 22):
        cards = _HARD_REPS[total]
        label = f"Hard {total}"
        rows.append([
            _build_cell("hard", label, cards, up, profile)
            for up in DEALER_UPCARDS
        ])
    return rows


def generate_soft_total_matrix(
    profile: RuleProfile = DEFAULT_PROFILE,
) -> list[list[StrategyCell]]:
    """Generate soft-total rows (soft 13-21) vs every dealer upcard."""
    rows: list[list[StrategyCell]] = []
    for total in range(13, 22):
        cards = _SOFT_REPS[total]
        label = f"Soft {total}"
        rows.append([
            _build_cell("soft", label, cards, up, profile)
            for up in DEALER_UPCARDS
        ])
    return rows


def generate_pair_matrix(
    profile: RuleProfile = DEFAULT_PROFILE,
) -> list[list[StrategyCell]]:
    """Generate pair rows (A,A and 2,2..10,10) vs every dealer upcard."""
    rows: list[list[StrategyCell]] = []
    for cards in _PAIR_REPS:
        label = _pair_label(cards[0])
        rows.append([
            _build_cell("pair", label, cards, up, profile)
            for up in DEALER_UPCARDS
        ])
    return rows


def generate_strategy_matrix(
    profile: RuleProfile = DEFAULT_PROFILE,
) -> StrategyMatrix:
    """Generate the full strategy matrix (hard, soft, pairs) for a profile."""
    hard = generate_hard_total_matrix(profile)
    soft = generate_soft_total_matrix(profile)
    pairs = generate_pair_matrix(profile)

    matrix = StrategyMatrix(
        profile_key=profile.key,
        hard_totals=hard,
        soft_totals=soft,
        pairs=pairs,
        total_cells=0,
    )
    total = len(matrix.iter_cells())
    fallback_cells = [c.cell_id for c in matrix.iter_cells() if c.fallback_applied]
    warnings: list[str] = []
    for cell in matrix.iter_cells():
        for note in cell.warnings:
            if note not in warnings:
                warnings.append(note)

    # Rebuild as a fully-populated, frozen matrix.
    return StrategyMatrix(
        profile_key=profile.key,
        hard_totals=hard,
        soft_totals=soft,
        pairs=pairs,
        total_cells=total,
        missing_cells=[],
        fallback_cells=fallback_cells,
        warnings=warnings,
    )


def audit_strategy_matrix(matrix: StrategyMatrix) -> MatrixAuditReport:
    """Audit a matrix for coverage and surface fallbacks and issues.

    Detects missing cells (a row/column with no decision), unknown actions
    (anything outside the :class:`Action` enum), and fallback cells (where the
    chart's ideal play was not legal under the profile). Collects the unique
    fallback warnings for review.
    """
    cells = matrix.iter_cells()
    valid_actions = set(Action)

    missing: list[str] = list(matrix.missing_cells)
    fallback: list[str] = []
    unknown: list[str] = []
    warnings: list[str] = []

    expected_columns = len(DEALER_UPCARDS)
    for section in (matrix.hard_totals, matrix.soft_totals, matrix.pairs):
        for row in section:
            if len(row) != expected_columns:
                # A short row means at least one dealer upcard is uncovered.
                covered = {c.dealer_upcard for c in row}
                for up in DEALER_UPCARDS:
                    if up not in covered:
                        label = row[0].player_label if row else "(unknown row)"
                        missing.append(f"{label} vs {up}")

    for cell in cells:
        if cell.recommended_action not in valid_actions:
            unknown.append(cell.cell_id)
        if cell.fallback_applied:
            fallback.append(cell.cell_id)
        for note in cell.warnings:
            if note not in warnings:
                warnings.append(note)

    is_complete = not missing and not unknown
    return MatrixAuditReport(
        profile_key=matrix.profile_key,
        total_cells=matrix.total_cells,
        missing_cells=missing,
        fallback_cells=fallback,
        unknown_action_cells=unknown,
        warnings=warnings,
        is_complete=is_complete,
    )


def _cell_code(cell: StrategyCell) -> str:
    """Compact code for a cell: uppercase for a direct play, lowercase for a
    legal fallback."""
    code = ACTION_CODES[cell.recommended_action]
    return code.lower() if cell.fallback_applied else code


def _format_section(
    title: str, rows: list[list[StrategyCell]], label_width: int
) -> list[str]:
    """Render one matrix section as aligned table lines."""
    lines = [f"-- {title} --"]
    header_cells = " ".join(f"{up:>3}" for up in DEALER_UPCARDS)
    lines.append(f"{'':<{label_width}} {header_cells}")
    for row in rows:
        label = row[0].player_label if row else "(empty)"
        codes = " ".join(f"{_cell_code(c):>3}" for c in row)
        lines.append(f"{label:<{label_width}} {codes}")
    return lines


def format_strategy_matrix(matrix: StrategyMatrix, section: str = "all") -> str:
    """Render a matrix as compact text for the terminal.

    Args:
        matrix: The matrix to render.
        section: ``"hard"``, ``"soft"``, ``"pairs"``, or ``"all"``.
    """
    if section not in ("hard", "soft", "pairs", "all"):
        raise ValueError(
            f"Unknown section {section!r}; expected hard, soft, pairs, or all."
        )

    label_width = 9
    lines = [f"Strategy Matrix [{matrix.profile_key}]"]
    lines.append(
        "Codes: H hit, S stand, D double, P split, R surrender "
        "(lowercase = legal fallback)"
    )
    lines.append("")

    wanted = ("hard", "soft", "pairs") if section == "all" else (section,)
    titles = {"hard": "Hard Totals", "soft": "Soft Totals", "pairs": "Pairs"}
    blocks: list[str] = []
    for name in wanted:
        section_lines = _format_section(titles[name], matrix.section(name), label_width)
        blocks.append("\n".join(section_lines))
    lines.append("\n\n".join(blocks))
    return "\n".join(lines)
