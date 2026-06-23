"""Tests for app.shoe (virtual shoe)."""

import pytest

from app.shoe import (
    CARDS_PER_DECK,
    build_shoe,
    cards_remaining,
    decks_remaining,
    draw_card,
    penetration,
    shuffle_shoe,
    validate_decks,
)


class TestBuildShoe:
    def test_one_deck_is_52_cards(self):
        assert len(build_shoe(1)) == 52

    def test_six_decks_is_312_cards(self):
        assert len(build_shoe(6)) == 312

    def test_default_is_six_decks(self):
        assert len(build_shoe()) == 6 * CARDS_PER_DECK

    def test_rank_distribution_one_deck(self):
        shoe = build_shoe(1)
        # 4 of every non-ten rank; 16 ten-valued cards (10/J/Q/K).
        assert shoe.count("A") == 4
        assert shoe.count("5") == 4
        ten_valued = sum(shoe.count(r) for r in ("10", "J", "Q", "K"))
        assert ten_valued == 16


class TestValidateDecks:
    def test_accepts_positive(self):
        assert validate_decks(6) == 6

    @pytest.mark.parametrize("bad", [0, -1, -6])
    def test_rejects_non_positive(self, bad):
        with pytest.raises(ValueError):
            validate_decks(bad)

    def test_rejects_non_int(self):
        with pytest.raises(ValueError):
            validate_decks(2.5)

    def test_build_shoe_rejects_zero(self):
        with pytest.raises(ValueError):
            build_shoe(0)



class TestShuffle:
    def test_seed_is_deterministic(self):
        a = shuffle_shoe(build_shoe(2), seed=42)
        b = shuffle_shoe(build_shoe(2), seed=42)
        assert a == b

    def test_different_seeds_differ(self):
        a = shuffle_shoe(build_shoe(6), seed=1)
        b = shuffle_shoe(build_shoe(6), seed=2)
        assert a != b

    def test_shuffle_preserves_cards(self):
        original = build_shoe(1)
        shuffled = shuffle_shoe(original, seed=7)
        assert sorted(shuffled) == sorted(original)
        # Original is not mutated.
        assert original == build_shoe(1)


class TestDrawAndRemaining:
    def test_draw_reduces_shoe(self):
        shoe = build_shoe(1)
        before = cards_remaining(shoe)
        card = draw_card(shoe)
        assert isinstance(card, str)
        assert cards_remaining(shoe) == before - 1

    def test_draw_from_empty_raises(self):
        with pytest.raises(ValueError):
            draw_card([])

    def test_decks_remaining(self):
        shoe = build_shoe(2)
        assert decks_remaining(shoe) == 2.0
        draw_card(shoe)
        assert decks_remaining(shoe) == 103 / 52


class TestPenetration:
    def test_no_cards_dealt(self):
        shoe = build_shoe(1)
        assert penetration(shoe, 52) == 0.0

    def test_half_dealt(self):
        shoe = build_shoe(1)
        for _ in range(26):
            draw_card(shoe)
        assert penetration(shoe, 52) == 0.5

    def test_invalid_original_size(self):
        with pytest.raises(ValueError):
            penetration(build_shoe(1), 0)
