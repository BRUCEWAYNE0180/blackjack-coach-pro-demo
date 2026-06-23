"""Tests for app.cards (professional card rendering / parsing)."""

import pytest

from app.cards import (
    RenderedCard,
    assign_display_suits,
    cards_to_ranks,
    format_card,
    format_cards,
    normalize_rank,
    normalize_suit,
    parse_card,
    parse_cards,
    strip_ansi,
)


class TestNormalize:
    def test_normalize_rank_accepts_known_ranks(self):
        assert normalize_rank("A") == "A"
        assert normalize_rank("10") == "10"
        assert normalize_rank("j") == "J"
        assert normalize_rank("Q") == "Q"
        assert normalize_rank("k") == "K"
        assert normalize_rank("T") == "10"

    def test_normalize_rank_rejects_unknown(self):
        with pytest.raises(ValueError):
            normalize_rank("Z")

    def test_normalize_suit_accepts_letters_and_symbols(self):
        assert normalize_suit("S") == "S"
        assert normalize_suit("h") == "H"
        assert normalize_suit("D") == "D"
        assert normalize_suit("c") == "C"
        assert normalize_suit("♠") == "S"
        assert normalize_suit("♥") == "H"
        assert normalize_suit("♦") == "D"
        assert normalize_suit("♣") == "C"

    def test_normalize_suit_accepts_names(self):
        assert normalize_suit("spades") == "S"
        assert normalize_suit("hearts") == "H"
        assert normalize_suit("diamonds") == "D"
        assert normalize_suit("clubs") == "C"

    def test_normalize_suit_rejects_unknown(self):
        with pytest.raises(ValueError):
            normalize_suit("x")


class TestParseCard:
    def test_unicode_suit(self):
        card = parse_card("A♠")
        assert card.rank == "A"
        assert card.suit == "S"
        assert card.label == "A♠"

    def test_letter_suit_ten(self):
        assert parse_card("10H").label == "10♥"

    def test_name_suit_with_space(self):
        assert parse_card("Q clubs").label == "Q♣"

    def test_lowercase_letter_suit(self):
        card = parse_card("Kd")
        assert card.rank == "K"
        assert card.suit == "D"

    def test_no_suit(self):
        card = parse_card("A")
        assert card.rank == "A"
        assert card.suit is None
        assert card.label == "A"
        assert card.plain_label == "A"

    def test_invalid_rank_raises(self):
        with pytest.raises(ValueError):
            parse_card("Z♠")


class TestParseCards:
    def test_parse_unicode_list(self):
        cards = parse_cards("A♠,7♥")
        assert len(cards) == 2
        assert cards[0].rank == "A" and cards[0].suit == "S"
        assert cards[1].rank == "7" and cards[1].suit == "H"

    def test_cards_to_ranks(self):
        assert cards_to_ranks(parse_cards("A♠,7♥")) == ["A", "7"]
        assert cards_to_ranks(parse_cards("AS,7H")) == ["A", "7"]
        assert cards_to_ranks(parse_cards("A,7")) == ["A", "7"]

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_cards("")


class TestFormatting:
    def test_color_includes_ansi_for_red_suits(self):
        hearts = format_card(parse_card("A♥"), color=True)
        diamonds = format_card(parse_card("10♦"), color=True)
        assert "\033[31m" in hearts
        assert "\033[0m" in hearts
        assert "\033[31m" in diamonds

    def test_black_suits_have_no_color(self):
        spades = format_card(parse_card("A♠"), color=True)
        clubs = format_card(parse_card("K♣"), color=True)
        assert "\033[" not in spades
        assert "\033[" not in clubs

    def test_no_color_has_no_ansi(self):
        hearts = format_card(parse_card("A♥"), color=False)
        assert "\033[" not in hearts
        assert hearts == "A♥"

    def test_show_suit_false_shows_rank_only(self):
        assert format_card(parse_card("A♥"), color=True, show_suit=False) == "A"

    def test_format_cards_joins(self):
        text = format_cards(parse_cards("A♠,7♥"), color=False)
        assert text == "A♠, 7♥"

    def test_strip_ansi(self):
        colored = format_card(parse_card("A♥"), color=True)
        assert strip_ansi(colored) == "A♥"


class TestAssignDisplaySuits:
    def test_deterministic_with_seed(self):
        a = assign_display_suits(["A", "7", "K"], seed=1)
        b = assign_display_suits(["A", "7", "K"], seed=1)
        assert [c.label for c in a] == [c.label for c in b]

    def test_returns_rendered_cards_with_suits(self):
        cards = assign_display_suits(["A", "7"], seed=5)
        assert all(isinstance(c, RenderedCard) for c in cards)
        assert all(c.suit in {"S", "H", "D", "C"} for c in cards)
        assert cards_to_ranks(cards) == ["A", "7"]

    def test_visual_only_preserves_ranks(self):
        # Decorative suits must not change the ranks the engine sees.
        ranks = ["10", "6", "A"]
        assert cards_to_ranks(assign_display_suits(ranks, seed=3)) == ranks
