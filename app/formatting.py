"""Terminal formatting helpers for Blackjack Coach Pro Demo.

Small, dependency-free helpers that give the CLI a clearer, more professional
look. These functions only format text — they never change strategy, counting,
simulation, or scoring logic. Standard library only (no rich/typer/click).

Educational/practice tool only. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from collections.abc import Iterable

# Default left-pad width for key/value labels.
DEFAULT_KV_WIDTH = 16


def format_header(title: str) -> str:
    """Return a titled header with an underline separator.

    Example::

        === Basic Strategy ===
        =======================
    """
    line = f"=== {title} ==="
    return f"{line}\n{'=' * len(line)}"


def format_section(title: str) -> str:
    """Return a lightweight sub-section heading, e.g. ``-- Notes --``."""
    return f"-- {title} --"


def format_kv(label: str, value: object, width: int = DEFAULT_KV_WIDTH) -> str:
    """Return an aligned ``label : value`` line.

    The label is left-padded to ``width`` so a block of lines lines up.
    """
    return f"{label:<{width}}: {value}"


def format_list(items: Iterable[object]) -> str:
    """Return a bulleted list, or ``  (none)`` when empty."""
    materialized = [str(item) for item in items]
    if not materialized:
        return "  (none)"
    return "\n".join(f"  - {item}" for item in materialized)


def format_result_status(is_correct: bool) -> str:
    """Return a visible pass/fail badge for a graded answer."""
    return "[ CORRECT ]" if is_correct else "[ INCORRECT ]"


def format_percentage(value: float) -> str:
    """Format a fraction in ``[0, 1]`` as a one-decimal percentage.

    Example: ``0.85`` -> ``"85.0%"``.
    """
    return f"{value * 100:.1f}%"


def format_warning(message: str) -> str:
    """Return a message prefixed with a visible warning marker."""
    return f"! {message}"


def format_cards(cards: Iterable[str]) -> str:
    """Render a sequence of card ranks as ``"A, 7"``."""
    return ", ".join(str(card) for card in cards)
