"""Tests for app.strategy_matrix (complete strategy-matrix audit)."""

from app.rules import SINGLE_DECK_H17_NDAS_NS, SIX_DECK_H17_DAS_LS
from app.strategy_engine import Action
from app.strategy_matrix import (
    DEALER_UPCARDS,
    audit_strategy_matrix,
    format_strategy_matrix,
    generate_hard_total_matrix,
    generate_pair_matrix,
    generate_soft_total_matrix,
    generate_strategy_matrix,
)

P6 = SIX_DECK_H17_DAS_LS
SD = SINGLE_DECK_H17_NDAS_NS


def _all_cells(rows):
    return [cell for row in rows for cell in row]


class TestMatrixGeneration:
    def test_hard_matrix_has_no_missing_cells(self):
        rows = generate_hard_total_matrix(P6)
        assert len(rows) == 17  # hard 5..21
        for row in rows:
            assert len(row) == len(DEALER_UPCARDS)
            for cell in row:
                assert isinstance(cell.recommended_action, Action)

    def test_soft_matrix_has_no_missing_cells(self):
        rows = generate_soft_total_matrix(P6)
        assert len(rows) == 9  # soft 13..21
        for row in rows:
            assert len(row) == len(DEALER_UPCARDS)
            for cell in row:
                assert isinstance(cell.recommended_action, Action)

    def test_pair_matrix_has_no_missing_cells(self):
        rows = generate_pair_matrix(P6)
        assert len(rows) == 10  # A,A and 2,2..10,10
        for row in rows:
            assert len(row) == len(DEALER_UPCARDS)
            for cell in row:
                assert isinstance(cell.recommended_action, Action)

    def test_total_matrix_has_expected_cell_count(self):
        matrix = generate_strategy_matrix(P6)
        expected = (17 + 9 + 10) * len(DEALER_UPCARDS)  # 36 rows x 10 cols
        assert expected == 360
        assert matrix.total_cells == expected
        assert len(matrix.iter_cells()) == expected

    def test_dealer_upcards_cover_2_to_10_and_ace(self):
        assert DEALER_UPCARDS == ("2", "3", "4", "5", "6", "7", "8", "9", "10", "A")
        matrix = generate_strategy_matrix(P6)
        for row in matrix.hard_totals:
            assert [c.dealer_upcard for c in row] == list(DEALER_UPCARDS)

    def test_all_actions_are_valid(self):
        matrix = generate_strategy_matrix(P6)
        valid = set(Action)
        for cell in matrix.iter_cells():
            assert cell.recommended_action in valid
            assert cell.raw_action in valid


class TestMatrixAudit:
    def test_six_deck_profile_is_complete(self):
        matrix = generate_strategy_matrix(P6)
        report = audit_strategy_matrix(matrix)
        assert report.profile_key == P6.key
        assert report.total_cells == 360
        assert report.missing_cells == []
        assert report.unknown_action_cells == []
        assert report.is_complete is True

    def test_single_deck_profile_is_complete(self):
        matrix = generate_strategy_matrix(SD)
        report = audit_strategy_matrix(matrix)
        assert report.total_cells == 360
        assert report.missing_cells == []
        assert report.is_complete is True

    def test_audit_detects_fallback_cells_without_surrender(self):
        # SINGLE_DECK_H17_NDAS_NS has no surrender and no DAS, so the chart's
        # surrender (and DAS-only split) cells fall back to a legal play.
        sd_report = audit_strategy_matrix(generate_strategy_matrix(SD))
        p6_report = audit_strategy_matrix(generate_strategy_matrix(P6))
        assert len(sd_report.fallback_cells) > 0
        # The permissive six-deck profile allows surrender/DAS, so it has none.
        assert len(p6_report.fallback_cells) == 0
        # A known surrender cell falls back under single deck.
        assert any("Hard 16 vs A" == cid for cid in sd_report.fallback_cells)

    def test_fallback_cells_carry_warnings(self):
        report = audit_strategy_matrix(generate_strategy_matrix(SD))
        assert len(report.warnings) > 0
        assert any("Chart prefers" in w for w in report.warnings)


class TestMatrixFormatting:
    def test_format_contains_header_and_actions(self):
        matrix = generate_strategy_matrix(P6)
        text = format_strategy_matrix(matrix, section="hard")
        assert "Strategy Matrix" in text
        assert P6.key in text
        assert "Hard Totals" in text
        # The dealer header row and a known action are present.
        assert "10" in text and "A" in text
        assert "Hard 11" in text
        # Hard 11 vs 2 doubles in this profile.
        assert "D" in text

    def test_format_sections_select_blocks(self):
        matrix = generate_strategy_matrix(P6)
        soft = format_strategy_matrix(matrix, section="soft")
        assert "Soft Totals" in soft
        assert "Hard Totals" not in soft
        pairs = format_strategy_matrix(matrix, section="pairs")
        assert "Pairs" in pairs
        assert "Pair As" in pairs

    def test_format_all_includes_every_section(self):
        text = format_strategy_matrix(generate_strategy_matrix(P6), section="all")
        assert "Hard Totals" in text
        assert "Soft Totals" in text
        assert "Pairs" in text
