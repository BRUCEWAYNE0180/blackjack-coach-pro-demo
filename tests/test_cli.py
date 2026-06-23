"""Tests for the app.cli command-line interface."""

import pytest

from app import cli


class TestCliBasics:
    def test_soft_18_vs_9(self, capsys):
        exit_code = cli.main(["--cards", "A,7", "--dealer", "9",
                              "--profile", "MULTI_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Soft 18 vs dealer 9" in out
        assert "Action:  HIT" in out
        assert "MULTI_DECK_H17_DAS_LS" in out
        # Educational explanation is present.
        assert "Take another card" in out

    def test_default_profile_used(self, capsys):
        exit_code = cli.main(["--cards", "10,6", "--dealer", "9"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "MULTI_DECK_H17_DAS_LS" in out


class TestCliInsurance:
    def test_insurance_no_shown_when_dealer_ace(self, capsys):
        exit_code = cli.main(["--cards", "10,6", "--dealer", "A"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Dealer shows an Ace" in out
        assert "Insurance advice: NO" in out

    def test_no_insurance_notice_without_ace(self, capsys):
        exit_code = cli.main(["--cards", "10,6", "--dealer", "9"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Dealer shows an Ace" not in out

    def test_insurance_note_not_duplicated(self, capsys):
        # The dedicated insurance block is shown, but the same note must not
        # also appear in the "Notes:" section.
        cli.main(["--cards", "10,6", "--dealer", "A"])
        out = capsys.readouterr().out
        from app.explanations import explain_insurance_no

        assert out.count(explain_insurance_no()) == 1
        # With only the insurance warning present, no "Notes:" block is shown.
        assert "Notes:" not in out


class TestCliErrors:
    def test_invalid_card_errors(self, capsys):
        exit_code = cli.main(["--cards", "Z,7", "--dealer", "9"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err

    def test_invalid_profile_rejected(self):
        # argparse rejects an unknown choice with SystemExit.
        with pytest.raises(SystemExit):
            cli.main(["--cards", "A,7", "--dealer", "9", "--profile", "BOGUS"])


class TestCliCount:
    def test_count_basic(self, capsys):
        exit_code = cli.main(
            ["count", "--cards", "2,5,K,A,9", "--decks-remaining", "5"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Cards seen:       5" in out
        assert "Running count:    +0" in out
        assert "Decks remaining:  5.0" in out
        assert "True count:       +0.00" in out
        # Educational note present.
        assert "educational" in out.lower()

    def test_count_positive_true_count(self, capsys):
        exit_code = cli.main(
            ["count", "--cards", "2,3,4,6", "--decks-remaining", "2"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Running count:    +4" in out
        assert "True count:       +2.00" in out

    def test_count_zero_decks_errors(self, capsys):
        exit_code = cli.main(
            ["count", "--cards", "2,5", "--decks-remaining", "0"]
        )
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "decks_remaining" in err

    def test_count_invalid_card_errors(self, capsys):
        exit_code = cli.main(
            ["count", "--cards", "2,Z", "--decks-remaining", "3"]
        )
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err


class TestCliSimulate:
    def test_simulate_basic(self, capsys):
        exit_code = cli.main(["simulate", "--decks", "6", "--seed", "42"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Player cards:" in out
        assert "Dealer upcard:" in out
        assert "Recommendation:" in out
        assert "Running count before:" in out
        assert "Running count after:" in out
        assert "True count after:" in out
        assert "simulated" in out.lower()

    def test_simulate_seed_is_reproducible(self, capsys):
        cli.main(["simulate", "--decks", "6", "--seed", "42"])
        first = capsys.readouterr().out
        cli.main(["simulate", "--decks", "6", "--seed", "42"])
        second = capsys.readouterr().out
        assert first == second

    def test_simulate_invalid_decks_errors(self, capsys):
        exit_code = cli.main(["simulate", "--decks", "0"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err


class TestCliPlay:
    def test_play_basic(self, capsys):
        exit_code = cli.main(["play", "--decks", "6", "--seed", "42"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Player starting cards:" in out
        assert "Dealer upcard:" in out
        assert "Actions taken:" in out
        assert "Final player cards:" in out
        assert "Final dealer cards:" in out
        assert "Outcome:" in out
        assert "Running count before:" in out
        assert "Running count after:" in out
        assert "True count after:" in out
        assert "simulated" in out.lower()

    def test_play_seed_is_reproducible(self, capsys):
        cli.main(["play", "--decks", "6", "--seed", "42"])
        first = capsys.readouterr().out
        cli.main(["play", "--decks", "6", "--seed", "42"])
        second = capsys.readouterr().out
        assert first == second

    def test_play_invalid_decks_errors(self, capsys):
        exit_code = cli.main(["play", "--decks", "0"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err

    def test_play_split_does_not_fail(self, capsys):
        # Seed 5 deals a splittable pair (8,8); the CLI must render it cleanly.
        exit_code = cli.main(["play", "--decks", "6", "--seed", "5"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "SPLIT" in out
        assert "Original hand:" in out
        assert "Split hand 1:" in out
        assert "Split hand 2:" in out
        assert "Final dealer cards:" in out
        assert "True count after:" in out



class TestCliQuiz:
    def test_quiz_with_answer_correct(self, capsys):
        # seed 42 -> Q,3 vs 2 -> correct STAND.
        exit_code = cli.main(["quiz", "--seed", "42", "--answer", "S"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Player cards:   Q, 3" in out
        assert "Dealer upcard:  2" in out
        assert "Your answer:    STAND" in out
        assert "Correct action: STAND" in out
        assert "Result:         Correct" in out
        assert "Why:" in out

    def test_quiz_with_answer_incorrect(self, capsys):
        exit_code = cli.main(["quiz", "--seed", "42", "--answer", "H"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Your answer:    HIT" in out
        assert "Result:         Incorrect" in out

    def test_quiz_full_name_answer(self, capsys):
        exit_code = cli.main(["quiz", "--seed", "42", "--answer", "stand"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Result:         Correct" in out

    def test_quiz_invalid_answer_errors(self, capsys):
        exit_code = cli.main(["quiz", "--seed", "42", "--answer", "Z"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err

    def test_quiz_interactive_prompt(self, capsys, monkeypatch):
        # Without --answer, the user is prompted; simulate typing "S".
        monkeypatch.setattr("builtins.input", lambda *_: "S")
        exit_code = cli.main(["quiz", "--seed", "42"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Result:         Correct" in out


class TestCliCountQuiz:
    def test_count_quiz_correct(self, capsys):
        # 2(+1) 5(+1) K(-1) A(-1) 9(0) -> running count 0.
        exit_code = cli.main(
            ["count-quiz", "--cards", "2,5,K,A,9", "--answer", "0"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Cards:                2, 5, K, A, 9" in out
        assert "Your answer:          +0" in out
        assert "Correct running count: +0" in out
        assert "Result:               Correct" in out
        assert "educational" in out.lower()

    def test_count_quiz_incorrect(self, capsys):
        exit_code = cli.main(
            ["count-quiz", "--cards", "2,5,K,A,9", "--answer", "3"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Your answer:          +3" in out
        assert "Correct running count: +0" in out
        assert "Result:               Incorrect" in out

    def test_count_quiz_positive(self, capsys):
        # 2,3,4,6 -> +4.
        exit_code = cli.main(
            ["count-quiz", "--cards", "2,3,4,6", "--answer", "4"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Correct running count: +4" in out
        assert "Result:               Correct" in out

    def test_count_quiz_invalid_card_errors(self, capsys):
        exit_code = cli.main(
            ["count-quiz", "--cards", "2,Z", "--answer", "1"]
        )
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err
