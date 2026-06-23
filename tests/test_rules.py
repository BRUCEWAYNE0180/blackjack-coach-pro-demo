"""Tests for app.rules (expanded rule profiles and helpers)."""

import pytest

from app.rules import (
    EIGHT_DECK_H17_DAS_LS,
    MULTI_DECK_H17_DAS_LS,
    SINGLE_DECK_H17_NDAS_NS,
    SIX_DECK_S17_DAS_LS,
    describe_rule_profile,
    get_rule_profile,
    list_rule_profiles,
    normalize_profile_key,
    profile_supports_das,
    profile_supports_hit_split_aces,
    profile_supports_resplit,
    profile_supports_surrender,
)


class TestListAndGet:
    def test_list_includes_existing_and_new(self):
        keys = {p.key for p in list_rule_profiles()}
        # Existing (backward compatible)
        assert "MULTI_DECK_H17_DAS_LS" in keys
        assert "MULTI_DECK_S17_DAS_LS" in keys
        # New
        for key in [
            "SINGLE_DECK_H17_NDAS_NS", "SINGLE_DECK_S17_DAS_LS",
            "DOUBLE_DECK_H17_DAS_NS", "DOUBLE_DECK_S17_DAS_LS",
            "FOUR_DECK_H17_DAS_LS", "SIX_DECK_H17_DAS_LS",
            "SIX_DECK_S17_DAS_LS", "EIGHT_DECK_H17_DAS_LS",
            "EIGHT_DECK_S17_DAS_LS",
        ]:
            assert key in keys

    def test_get_rule_profile_exact_key(self):
        p = get_rule_profile("SIX_DECK_S17_DAS_LS")
        assert p.key == "SIX_DECK_S17_DAS_LS"

    def test_get_rule_profile_unknown_raises(self):
        with pytest.raises(KeyError):
            get_rule_profile("NO_SUCH_PROFILE")


class TestNormalizeKey:
    def test_accepts_lowercase_and_spaces(self):
        assert normalize_profile_key("  six deck s17 das ls  ") == "SIX_DECK_S17_DAS_LS"

    def test_accepts_hyphens(self):
        assert normalize_profile_key("multi-deck-h17-das-ls") == "MULTI_DECK_H17_DAS_LS"

    def test_normalized_lookup_works(self):
        assert get_rule_profile("six deck s17 das ls").key == "SIX_DECK_S17_DAS_LS"


class TestDescribe:
    def test_contains_decks_soft17_das_surrender(self):
        desc = describe_rule_profile(SIX_DECK_S17_DAS_LS)
        assert "6 decks" in desc
        assert "S17" in desc
        assert "DAS" in desc
        assert "LS" in desc

    def test_single_deck_ndas_ns(self):
        desc = describe_rule_profile(SINGLE_DECK_H17_NDAS_NS)
        assert "1 deck" in desc
        assert "H17" in desc
        assert "NDAS" in desc
        assert "NS" in desc


class TestSupportsHelpers:
    def test_surrender_true_false(self):
        assert profile_supports_surrender(SIX_DECK_S17_DAS_LS) is True
        assert profile_supports_surrender(SINGLE_DECK_H17_NDAS_NS) is False

    def test_das_true_false(self):
        assert profile_supports_das(SIX_DECK_S17_DAS_LS) is True
        assert profile_supports_das(SINGLE_DECK_H17_NDAS_NS) is False

    def test_resplit_and_hit_split_aces_metadata(self):
        assert profile_supports_resplit(MULTI_DECK_H17_DAS_LS) is True
        assert profile_supports_hit_split_aces(MULTI_DECK_H17_DAS_LS) is False


class TestProfileValues:
    def test_existing_profiles_compatible(self):
        # Backward-compatible fields still present.
        p = MULTI_DECK_H17_DAS_LS
        assert p.decks == 6
        assert p.number_of_decks == 6
        assert p.dealer_hits_soft_17 is True
        assert p.double_after_split is True
        assert p.late_surrender is True

    def test_six_deck_s17(self):
        p = SIX_DECK_S17_DAS_LS
        assert p.number_of_decks == 6
        assert p.dealer_hits_soft_17 is False

    def test_eight_deck_h17(self):
        p = EIGHT_DECK_H17_DAS_LS
        assert p.number_of_decks == 8
        assert p.dealer_hits_soft_17 is True
