"""Tests for app.outcome_history (local win/loss outcome history)."""

import json
from dataclasses import asdict

from app.outcome_history import (
    OutcomeRecord,
    build_outcome_record,
    default_outcome_history_dir,
    ensure_outcome_history_dir,
    list_outcome_records,
    load_outcome_record,
    save_outcome_record,
    summarize_outcomes,
)
from app.rules import MULTI_DECK_H17_DAS_LS, SIX_DECK_H17_DAS_LS
from app.simulator import PlayedHand, PlayedSplitHand, play_training_hand

P6 = SIX_DECK_H17_DAS_LS


def _played_hand() -> PlayedHand:
    hand = play_training_hand(decks=6, seed=42)
    assert isinstance(hand, PlayedHand)
    return hand


def _split_hand() -> PlayedSplitHand:
    hand = play_training_hand(decks=6, seed=428, profile=P6)
    assert isinstance(hand, PlayedSplitHand)
    return hand


def _record(**overrides) -> OutcomeRecord:
    """Build a synthetic record with sensible defaults for summary tests."""
    base = dict(
        outcome_id="abc123",
        created_at="2026-06-23T10:00:00",
        profile_key="SIX_DECK_H17_DAS_LS",
        mode="play",
        seed=1,
        player_cards=("10", "6"),
        dealer_upcard="9",
        dealer_cards=("9", "7"),
        actions_taken=["STAND"],
        final_outcome="PLAYER_WIN",
        result_label="Win",
        is_split_hand=False,
        split_hands_count=0,
        hands_won=1,
        hands_lost=0,
        hands_pushed=0,
        hands_surrendered=0,
        player_busts=0,
        dealer_busts=0,
        warnings=[],
        note="",
    )
    base.update(overrides)
    return OutcomeRecord(**base)


class TestBuildOutcomeRecord:
    def test_from_played_hand(self):
        hand = _played_hand()
        record = build_outcome_record(hand, P6.key, seed=42)
        assert record.is_split_hand is False
        assert record.split_hands_count == 0
        assert record.profile_key == P6.key
        assert record.seed == 42
        assert record.player_cards == tuple(hand.player_cards)
        assert record.final_outcome == hand.final_outcome.value
        # Exactly one of win/loss/push/surrender is recorded for a single hand.
        total = (record.hands_won + record.hands_lost
                 + record.hands_pushed + record.hands_surrendered)
        assert total == 1

    def test_from_split_hand_counts_subhands(self):
        hand = _split_hand()
        record = build_outcome_record(hand, P6.key, seed=428)
        assert record.is_split_hand is True
        assert record.split_hands_count == hand.num_split_hands
        # Each sub-hand is classified exactly once.
        total = (record.hands_won + record.hands_lost
                 + record.hands_pushed + record.hands_surrendered)
        assert total == hand.num_split_hands
        assert record.final_outcome == "SPLIT"
        assert len(record.actions_taken) == hand.num_split_hands


class TestSaveLoad:
    def test_save_load_roundtrip(self, tmp_path):
        record = _record(seed=7, player_cards=("8", "8"))
        path = save_outcome_record(record, tmp_path)
        assert path.exists()
        assert path.name.startswith("outcome_")
        loaded = load_outcome_record(path)
        assert loaded == record

    def test_saved_json_is_valid(self, tmp_path):
        path = save_outcome_record(_record(), tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["profile_key"] == "SIX_DECK_H17_DAS_LS"
        assert data["final_outcome"] == "PLAYER_WIN"


class TestEnsureDir:
    def test_ensure_creates_directory(self, tmp_path):
        target = tmp_path / "outcomes_here"
        assert not target.exists()
        created = ensure_outcome_history_dir(target)
        assert created.is_dir()

    def test_default_dir_is_local_blackjack_coach(self):
        path = default_outcome_history_dir()
        assert path.name == "outcomes"
        assert ".blackjack_coach" in path.parts


class TestListOutcomeRecords:
    def test_empty_dir_returns_empty(self, tmp_path):
        assert list_outcome_records(tmp_path) == []

    def test_limit_is_respected(self, tmp_path):
        for i in range(3):
            save_outcome_record(
                _record(outcome_id=f"id{i}", created_at=f"2026-06-23T10:0{i}:00"),
                tmp_path,
            )
        assert len(list_outcome_records(tmp_path)) == 3
        assert len(list_outcome_records(tmp_path, limit=1)) == 1
        assert len(list_outcome_records(tmp_path, limit=2)) == 2
        assert list_outcome_records(tmp_path, limit=0) == []

    def test_profile_filter(self, tmp_path):
        save_outcome_record(_record(outcome_id="a", profile_key="SIX_DECK_H17_DAS_LS"), tmp_path)
        save_outcome_record(_record(outcome_id="b", profile_key="MULTI_DECK_H17_DAS_LS"), tmp_path)
        six = list_outcome_records(tmp_path, profile_key="SIX_DECK_H17_DAS_LS")
        assert len(six) == 1
        assert six[0].profile_key == "SIX_DECK_H17_DAS_LS"


class TestSummarize:
    def test_counts_win_loss_push_surrender(self):
        records = [
            _record(final_outcome="PLAYER_WIN", hands_won=1),
            _record(final_outcome="DEALER_WIN", hands_won=0, hands_lost=1),
            _record(final_outcome="PUSH", hands_won=0, hands_pushed=1),
            _record(final_outcome="SURRENDER", hands_won=0, hands_surrendered=1),
        ]
        summary = summarize_outcomes(records)
        assert summary.total_records == 4
        assert summary.wins == 1
        assert summary.losses == 1
        assert summary.pushes == 1
        assert summary.surrenders == 1

    def test_counts_busts(self):
        records = [
            _record(hands_lost=1, hands_won=0, player_busts=1, final_outcome="PLAYER_BUST"),
            _record(hands_won=1, dealer_busts=1, final_outcome="DEALER_BUST"),
        ]
        summary = summarize_outcomes(records)
        assert summary.player_busts == 1
        assert summary.dealer_busts == 1

    def test_counts_split_records_and_average(self):
        records = [
            _record(is_split_hand=True, split_hands_count=2, hands_won=2),
            _record(is_split_hand=True, split_hands_count=4, hands_won=2, hands_lost=2),
            _record(is_split_hand=False, split_hands_count=0),
        ]
        summary = summarize_outcomes(records)
        assert summary.split_records == 2
        assert summary.average_split_hands == 3.0  # (2 + 4) / 2

    def test_most_common_profile(self):
        records = [
            _record(profile_key="SIX_DECK_H17_DAS_LS"),
            _record(profile_key="SIX_DECK_H17_DAS_LS"),
            _record(profile_key="MULTI_DECK_H17_DAS_LS"),
        ]
        summary = summarize_outcomes(records)
        assert summary.most_common_profile == "SIX_DECK_H17_DAS_LS"

    def test_empty_summary(self):
        summary = summarize_outcomes([])
        assert summary.total_records == 0
        assert summary.most_common_profile == "(none)"
        assert "self-study" in summary.note


class TestNoSensitiveData:
    def test_record_has_no_money_or_account_fields(self):
        # The record schema must never include money / bankroll / account /
        # token / wager / balance fields (only practice summary data).
        forbidden = ("bankroll", "money", "bet", "wager", "account",
                     "token", "balance", "password", "secret")
        keys = set(asdict(_record()).keys())
        for key in keys:
            assert not any(bad in key.lower() for bad in forbidden), key

    def test_profiles_are_just_rule_keys(self):
        # Sanity: building from a real hand stores only rule/practice data.
        record = build_outcome_record(_played_hand(), MULTI_DECK_H17_DAS_LS.key)
        data = asdict(record)
        assert "seed" in data
        assert "profile_key" in data
        assert "player_cards" in data
