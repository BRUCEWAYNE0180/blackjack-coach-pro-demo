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
        assert "=== Basic Strategy ===" in out
        assert "HIT" in out
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
        # With only the insurance warning present, no separate notes block is
        # shown (the dedicated insurance section already covers it).
        assert "-- Notes --" not in out


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
        assert "=== Hi-Lo Count ===" in out
        assert "Cards seen     : 5" in out
        assert "Running count  : +0" in out
        assert "Decks remaining: 5.0" in out
        assert "True count     : +0.00" in out
        # Educational note present.
        assert "educational" in out.lower()

    def test_count_positive_true_count(self, capsys):
        exit_code = cli.main(
            ["count", "--cards", "2,3,4,6", "--decks-remaining", "2"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Running count  : +4" in out
        assert "True count     : +2.00" in out

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
        assert "=== Training Simulator ===" in out
        assert "Player cards" in out
        assert "Dealer upcard" in out
        assert "Recommendation" in out
        assert "Running count before" in out
        assert "Running count after" in out
        assert "True count after" in out
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
        assert "=== Played Hand ===" in out
        assert "Player starting cards" in out
        assert "Dealer upcard" in out
        assert "Actions taken" in out
        assert "Final player cards" in out
        assert "Final dealer cards" in out
        assert "Outcome" in out
        assert "Running count before" in out
        assert "Running count after" in out
        assert "True count after" in out
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
        assert "Original hand" in out
        assert "Split hand 1" in out
        assert "Split hand 2" in out
        assert "Final dealer cards" in out
        assert "True count after" in out



class TestCliQuiz:
    def test_quiz_with_answer_correct(self, capsys):
        # seed 42 -> Q,3 vs 2 -> correct STAND.
        exit_code = cli.main(["quiz", "--seed", "42", "--answer", "S"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Player cards  : Q, 3" in out
        assert "Dealer upcard : 2" in out
        assert "Your answer   : STAND" in out
        assert "Correct action: STAND" in out
        assert "[ CORRECT ]" in out
        assert "Why" in out

    def test_quiz_with_answer_incorrect(self, capsys):
        exit_code = cli.main(["quiz", "--seed", "42", "--answer", "H"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Your answer   : HIT" in out
        assert "[ INCORRECT ]" in out

    def test_quiz_full_name_answer(self, capsys):
        exit_code = cli.main(["quiz", "--seed", "42", "--answer", "stand"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "[ CORRECT ]" in out

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
        assert "[ CORRECT ]" in out


class TestCliCountQuiz:
    def test_count_quiz_correct(self, capsys):
        # 2(+1) 5(+1) K(-1) A(-1) 9(0) -> running count 0.
        exit_code = cli.main(
            ["count-quiz", "--cards", "2,5,K,A,9", "--answer", "0"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Hi-Lo Count Quiz ===" in out
        assert "2, 5, K, A, 9" in out
        assert "Correct running count: +0" in out
        assert "[ CORRECT ]" in out
        assert "educational" in out.lower()

    def test_count_quiz_incorrect(self, capsys):
        exit_code = cli.main(
            ["count-quiz", "--cards", "2,5,K,A,9", "--answer", "3"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Your answer          : +3" in out
        assert "Correct running count: +0" in out
        assert "[ INCORRECT ]" in out

    def test_count_quiz_positive(self, capsys):
        # 2,3,4,6 -> +4.
        exit_code = cli.main(
            ["count-quiz", "--cards", "2,3,4,6", "--answer", "4"]
        )
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Correct running count: +4" in out
        assert "[ CORRECT ]" in out

    def test_count_quiz_invalid_card_errors(self, capsys):
        exit_code = cli.main(
            ["count-quiz", "--cards", "2,Z", "--answer", "1"]
        )
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err



class TestCliQuizSession:
    def test_quiz_session_with_answers(self, capsys):
        exit_code = cli.main([
            "quiz-session", "--questions", "10", "--seed", "42",
            "--answers", "H,S,D,H,R,S,H,D,P,S",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Strategy Training Session ===" in out
        assert "Total questions" in out
        assert "Correct" in out
        assert "Incorrect" in out
        assert "Accuracy" in out
        assert "Weak spots" in out
        assert "educational" in out.lower()

    def test_quiz_session_all_correct(self, capsys):
        # Build the questions to learn the correct answers, then answer them.
        from app.quiz import build_strategy_questions

        qs = build_strategy_questions(5, seed=99)
        answers = ",".join(q.correct_action for q in qs)
        exit_code = cli.main([
            "quiz-session", "--questions", "5", "--seed", "99",
            "--answers", answers,
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Correct        : 5" in out
        assert "Accuracy       : 100.0%" in out

    def test_quiz_session_answer_mismatch_errors(self, capsys):
        exit_code = cli.main([
            "quiz-session", "--questions", "3", "--seed", "1", "--answers", "H,S",
        ])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err

    def test_quiz_session_interactive(self, capsys, monkeypatch):
        answers = iter(["H", "S", "D"])
        monkeypatch.setattr("builtins.input", lambda *_: next(answers))
        exit_code = cli.main(["quiz-session", "--questions", "3", "--seed", "1"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total questions" in out


class TestCliCountSession:
    def test_count_session_with_answers(self, capsys):
        exit_code = cli.main([
            "count-session", "--batches", "2,5,K|A,9,3|10,6,2",
            "--answers", "1,-1,1",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Hi-Lo Count Training Session ===" in out
        assert "Total questions" in out
        assert "Correct        : 2" in out
        assert "Incorrect      : 1" in out
        assert "Accuracy" in out
        assert "Q2" in out  # weak spot

    def test_count_session_all_correct(self, capsys):
        exit_code = cli.main([
            "count-session", "--batches", "2,5,K|A,9,3|10,6,2",
            "--answers", "1,0,1",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Correct        : 3" in out
        assert "Accuracy       : 100.0%" in out

    def test_count_session_interactive(self, capsys, monkeypatch):
        answers = iter(["1", "0", "1"])
        monkeypatch.setattr("builtins.input", lambda *_: next(answers))
        exit_code = cli.main([
            "count-session", "--batches", "2,5,K|A,9,3|10,6,2",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Correct        : 3" in out

    def test_count_session_non_integer_answer_errors(self, capsys):
        exit_code = cli.main([
            "count-session", "--batches", "2,5", "--answers", "x",
        ])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err



class TestCliSessionHistory:
    def test_quiz_session_save_creates_file(self, capsys, tmp_path):
        exit_code = cli.main([
            "quiz-session", "--questions", "3", "--seed", "42",
            "--answers", "H,S,D", "--save", "--history-dir", str(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved" in out
        files = list(tmp_path.glob("session_*.json"))
        assert len(files) == 1

    def test_count_session_save_creates_file(self, capsys, tmp_path):
        exit_code = cli.main([
            "count-session", "--batches", "2,5,K|A,9,3|10,6,2",
            "--answers", "1,0,1", "--save", "--history-dir", str(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved" in out
        assert len(list(tmp_path.glob("session_*.json"))) == 1

    def test_history_shows_total_sessions(self, capsys, tmp_path):
        # Save two sessions, then summarise them.
        cli.main(["quiz-session", "--questions", "3", "--seed", "42",
                  "--answers", "H,S,D", "--save", "--history-dir", str(tmp_path)])
        cli.main(["count-session", "--batches", "2,5,K|A,9,3",
                  "--answers", "1,0", "--save", "--history-dir", str(tmp_path)])
        capsys.readouterr()  # clear
        exit_code = cli.main(["history", "--dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Practice History ===" in out
        assert "Total sessions  : 2" in out
        assert "Average accuracy" in out
        assert "Best accuracy" in out
        assert "Worst accuracy" in out

    def test_history_empty_dir(self, capsys, tmp_path):
        exit_code = cli.main(["history", "--dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "No saved sessions yet" in out

    def test_history_limit_respected(self, capsys, tmp_path):
        # Save three sessions; --limit 0 should summarise none.
        for _ in range(3):
            cli.main(["count-session", "--batches", "2,5,K",
                      "--answers", "1", "--save", "--history-dir", str(tmp_path)])
        capsys.readouterr()
        exit_code = cli.main(["history", "--dir", str(tmp_path), "--limit", "0"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "No saved sessions yet" in out

        # --limit 2 should summarise only two of the three sessions.
        exit_code = cli.main(["history", "--dir", str(tmp_path), "--limit", "2"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total sessions  : 2" in out



class TestCliDeviations:
    def test_deviations_list(self, capsys):
        exit_code = cli.main(["deviations", "--list"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Deviation Study Rules ===" in out
        assert "hard_16_vs_10" in out
        assert "HIT -> STAND" in out
        assert "insurance" in out

    def test_deviations_applies(self, capsys):
        # 10,6 = hard 16 vs 10 at TC 1 -> deviation STAND.
        exit_code = cli.main([
            "deviations", "--cards", "10,6", "--dealer", "10", "--true-count", "1",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Deviation Study ===" in out
        assert "Study recommendation: STAND" in out
        assert "Deviation           : STAND" in out

    def test_deviations_does_not_apply(self, capsys):
        # At TC -1 no deviation applies -> basic strategy stands as the play.
        exit_code = cli.main([
            "deviations", "--cards", "10,6", "--dealer", "10", "--true-count", "-1",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "none - play basic strategy" in out

    def test_deviations_requires_cards_or_list(self, capsys):
        exit_code = cli.main(["deviations"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err


class TestCliDeviationQuiz:
    def test_deviation_quiz_with_answer(self, capsys):
        exit_code = cli.main(["deviation-quiz", "--seed", "42", "--answer", "S"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Deviation Quiz ===" in out
        assert "Player hand" in out
        assert "True count" in out
        assert "Correct action" in out
        assert ("[ CORRECT ]" in out) or ("[ INCORRECT ]" in out)

    def test_deviation_quiz_reproducible(self, capsys):
        cli.main(["deviation-quiz", "--seed", "7", "--answer", "S"])
        first = capsys.readouterr().out
        cli.main(["deviation-quiz", "--seed", "7", "--answer", "S"])
        second = capsys.readouterr().out
        assert first == second

    def test_deviation_quiz_invalid_answer_errors(self, capsys):
        exit_code = cli.main(["deviation-quiz", "--seed", "42", "--answer", "Z"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err

    def test_deviation_quiz_interactive(self, capsys, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda *_: "S")
        exit_code = cli.main(["deviation-quiz", "--seed", "42"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Deviation Quiz" in out



class TestCliDiagnose:
    def test_diagnose_works(self, capsys):
        exit_code = cli.main(["diagnose", "--cards", "A,7", "--dealer", "9"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Decision Diagnostic ===" in out

    def test_diagnose_shows_action_and_factors(self, capsys):
        exit_code = cli.main(["diagnose", "--cards", "A,7", "--dealer", "9"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Recommended action:" in out
        assert "Decision factors" in out
        # The soft-hand factor is surfaced.
        assert "soft" in out.lower()

    def test_diagnose_hard_total(self, capsys):
        exit_code = cli.main(["diagnose", "--cards", "10,6", "--dealer", "10"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Hard 16" in out
        assert "hard" in out.lower()

    def test_diagnose_pair(self, capsys):
        exit_code = cli.main(["diagnose", "--cards", "8,8", "--dealer", "10"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Recommended action: SPLIT" in out
        assert "split" in out.lower()

    def test_diagnose_invalid_card_errors(self, capsys):
        exit_code = cli.main(["diagnose", "--cards", "Z,7", "--dealer", "9"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err
