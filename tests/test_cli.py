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

    def test_play_shows_resplit_tree(self, capsys):
        # Seed 428 with this profile re-splits into three hands; the CLI must
        # show the extra hand and label it as a re-split.
        exit_code = cli.main(["play", "--decks", "6", "--seed", "428",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Split hands  : 3" in out
        assert "Split hand 3" in out
        assert "re-split" in out



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



class TestCliProfiles:
    def test_profiles_list(self, capsys):
        exit_code = cli.main(["profiles", "--list"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Rule Profiles ===" in out
        assert "MULTI_DECK_H17_DAS_LS" in out
        assert "SIX_DECK_S17_DAS_LS" in out
        assert "decks" in out

    def test_profiles_detail(self, capsys):
        exit_code = cli.main(["profiles", "--profile", "MULTI_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Key" in out
        assert "Number of decks" in out
        assert "Late surrender" in out
        assert "Blackjack payout" in out

    def test_profiles_default_lists(self, capsys):
        # With no flags, 'profiles' lists all profiles.
        exit_code = cli.main(["profiles"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Rule Profiles ===" in out


class TestCliNewProfilesAccepted:
    def test_strategy_accepts_new_profile(self, capsys):
        exit_code = cli.main(["--cards", "A,7", "--dealer", "9",
                              "--profile", "SIX_DECK_S17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "SIX_DECK_S17_DAS_LS" in out

    def test_diagnose_accepts_new_profile(self, capsys):
        exit_code = cli.main(["diagnose", "--cards", "A,7", "--dealer", "9",
                              "--profile", "SIX_DECK_S17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Profile context" in out
        assert "S17" in out

    def test_deviations_accepts_new_profile(self, capsys):
        exit_code = cli.main(["deviations", "--cards", "10,6", "--dealer", "10",
                              "--true-count", "1", "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Deviation Study ===" in out



class TestCliSplitRules:
    def test_split_rules_works(self, capsys):
        exit_code = cli.main(["split-rules", "--cards", "8,8",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Split Rules ===" in out
        assert "Can split" in out
        assert "Double after split" in out

    def test_split_rules_aces(self, capsys):
        exit_code = cli.main(["split-rules", "--cards", "A,A",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Is aces           : yes" in out
        assert "Hit split aces" in out

    def test_split_rules_non_pair(self, capsys):
        exit_code = cli.main(["split-rules", "--cards", "10,9"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Is pair           : no" in out

    def test_diagnose_aces_split_context(self, capsys):
        exit_code = cli.main(["diagnose", "--cards", "A,A", "--dealer", "6",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Split rules:" in out
        assert "Split aces:" in out

    def test_diagnose_includes_audit_summary(self, capsys):
        exit_code = cli.main(["diagnose", "--cards", "A,7", "--dealer", "9",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Audit summary" in out
        assert "Table section" in out
        assert "Raw table action" in out
        assert "Legal actions" in out
        assert "Profile rules" in out


class TestCliMatrix:
    def test_matrix_hard_section(self, capsys):
        exit_code = cli.main(["matrix", "--profile", "SIX_DECK_H17_DAS_LS",
                              "--section", "hard"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Strategy Matrix ===" in out
        assert "Hard Totals" in out
        assert "Soft Totals" not in out
        assert "Hard 16" in out
        assert "Total cells   : 360" in out

    def test_matrix_soft_section(self, capsys):
        exit_code = cli.main(["matrix", "--profile", "SIX_DECK_H17_DAS_LS",
                              "--section", "soft"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Soft Totals" in out
        assert "Soft 18" in out

    def test_matrix_pairs_section(self, capsys):
        exit_code = cli.main(["matrix", "--profile", "SIX_DECK_H17_DAS_LS",
                              "--section", "pairs"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Pairs" in out
        assert "Pair As" in out

    def test_matrix_default_section_is_all(self, capsys):
        exit_code = cli.main(["matrix", "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Hard Totals" in out
        assert "Soft Totals" in out
        assert "Pairs" in out

    def test_matrix_audit_shows_summary(self, capsys):
        exit_code = cli.main(["matrix", "--profile", "SINGLE_DECK_H17_NDAS_NS",
                              "--section", "pairs", "--audit"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Coverage summary" in out
        assert "Total cells" in out
        assert "Fallback cells" in out
        assert "Missing cells" in out
        assert "Audit detail" in out

    def test_matrix_invalid_section_rejected(self):
        with pytest.raises(SystemExit):
            cli.main(["matrix", "--section", "bogus"])

    def test_matrix_invalid_profile_rejected(self):
        with pytest.raises(SystemExit):
            cli.main(["matrix", "--profile", "BOGUS"])


class TestCliAudit:
    def test_audit_works(self, capsys):
        exit_code = cli.main(["audit", "--cards", "A,7", "--dealer", "9",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Decision Audit ===" in out
        assert "Table section" in out
        assert "Recommended action" in out
        assert "Raw table action" in out
        assert "Fallback applied" in out
        assert "Legal actions" in out
        assert "Explanation" in out

    def test_audit_detects_fallback(self, capsys):
        # Hard 16 vs 10 under a no-surrender profile falls back.
        exit_code = cli.main(["audit", "--cards", "10,6", "--dealer", "10",
                              "--profile", "SINGLE_DECK_H17_NDAS_NS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Fallback applied  : yes" in out
        assert "Raw table action  : SURRENDER" in out

    def test_audit_invalid_card_errors(self, capsys):
        exit_code = cli.main(["audit", "--cards", "Z,7", "--dealer", "9"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err


class TestCliOutcomes:
    def test_play_save_outcome_creates_file(self, capsys, tmp_path):
        exit_code = cli.main(["play", "--decks", "6", "--seed", "42",
                              "--save-outcome", "--outcome-dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved outcome" in out
        files = list(tmp_path.glob("outcome_*.json"))
        assert len(files) == 1

    def test_play_save_split_outcome_creates_file(self, capsys, tmp_path):
        exit_code = cli.main(["play", "--decks", "6", "--seed", "428",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--save-outcome", "--outcome-dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved outcome" in out
        assert len(list(tmp_path.glob("outcome_*.json"))) == 1

    def test_outcomes_shows_total_records(self, capsys, tmp_path):
        cli.main(["play", "--decks", "6", "--seed", "42",
                  "--save-outcome", "--outcome-dir", str(tmp_path)])
        cli.main(["play", "--decks", "6", "--seed", "428",
                  "--profile", "SIX_DECK_H17_DAS_LS",
                  "--save-outcome", "--outcome-dir", str(tmp_path)])
        capsys.readouterr()  # clear
        exit_code = cli.main(["outcomes", "--dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Outcome History ===" in out
        assert "Total records      : 2" in out
        assert "Wins" in out
        assert "Losses" in out
        assert "Split records" in out

    def test_outcomes_limit_respected(self, capsys, tmp_path):
        for seed in (42, 428, 5):
            cli.main(["play", "--decks", "6", "--seed", str(seed),
                      "--profile", "SIX_DECK_H17_DAS_LS",
                      "--save-outcome", "--outcome-dir", str(tmp_path)])
        capsys.readouterr()
        exit_code = cli.main(["outcomes", "--dir", str(tmp_path), "--limit", "1"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total records      : 1" in out

    def test_outcomes_profile_filter(self, capsys, tmp_path):
        cli.main(["play", "--decks", "6", "--seed", "42",
                  "--profile", "MULTI_DECK_H17_DAS_LS",
                  "--save-outcome", "--outcome-dir", str(tmp_path)])
        cli.main(["play", "--decks", "6", "--seed", "428",
                  "--profile", "SIX_DECK_H17_DAS_LS",
                  "--save-outcome", "--outcome-dir", str(tmp_path)])
        capsys.readouterr()
        exit_code = cli.main(["outcomes", "--dir", str(tmp_path),
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total records      : 1" in out
        assert "SIX_DECK_H17_DAS_LS" in out

    def test_outcomes_empty_dir(self, capsys, tmp_path):
        exit_code = cli.main(["outcomes", "--dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total records      : 0" in out
        assert "No saved outcomes yet" in out


class TestCliCoach:
    def test_coach_works(self, capsys):
        exit_code = cli.main(["coach", "--cards", "A,7", "--dealer", "9",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Guided Coach ===" in out
        assert "Recommended action" in out
        assert "Raw table action" in out
        assert "Legal actions" in out
        assert "Why" in out

    def test_coach_pair_split(self, capsys):
        exit_code = cli.main(["coach", "--cards", "8,8", "--dealer", "6",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Recommended action: SPLIT" in out

    def test_coach_invalid_card_errors(self, capsys):
        exit_code = cli.main(["coach", "--cards", "Z,7", "--dealer", "9"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err

    def test_coach_play_works(self, capsys):
        exit_code = cli.main(["coach-play", "--decks", "6", "--seed", "42",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Guided Coach - Played Hand ===" in out
        assert "Step 1" in out
        assert "Coach recommends" in out
        assert "Final outcome" in out
        assert "Result label" in out
        assert "Total steps" in out

    def test_coach_play_reproducible(self, capsys):
        cli.main(["coach-play", "--decks", "6", "--seed", "42"])
        first = capsys.readouterr().out
        cli.main(["coach-play", "--decks", "6", "--seed", "42"])
        second = capsys.readouterr().out
        assert first == second

    def test_coach_play_save_outcome_creates_file(self, capsys, tmp_path):
        exit_code = cli.main(["coach-play", "--decks", "6", "--seed", "428",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--save-outcome", "--outcome-dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved outcome" in out
        assert len(list(tmp_path.glob("outcome_*.json"))) == 1

    def test_coach_play_invalid_decks_errors(self, capsys):
        exit_code = cli.main(["coach-play", "--decks", "0"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err


class TestCliCardDisplay:
    def test_coach_accepts_unicode_suits(self, capsys):
        exit_code = cli.main(["coach", "--cards", "A\u2660,7\u2665",
                              "--dealer", "9\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "A\u2660" in out and "7\u2665" in out
        # Engine still sees plain ranks: soft 18 vs 9.
        assert "Soft 18 vs dealer 9" in out
        assert "Recommended action: HIT" in out

    def test_coach_accepts_letter_suits(self, capsys):
        exit_code = cli.main(["coach", "--cards", "AS,7H", "--dealer", "9D",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "A\u2660" in out and "7\u2665" in out

    def test_coach_plain_cards_strips_suits(self, capsys):
        exit_code = cli.main(["coach", "--cards", "A\u2660,7\u2665",
                              "--dealer", "9\u2666", "--plain-cards",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Cards             : A, 7" in out
        assert "\u2660" not in out and "\u2665" not in out

    def test_coach_no_color_has_no_ansi(self, capsys):
        exit_code = cli.main(["coach", "--cards", "A\u2660,7\u2665",
                              "--dealer", "9\u2666", "--no-color",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "\033[" not in out
        # Suits are still shown (colour off, symbols on).
        assert "A\u2660" in out

    def test_coach_suitless_shows_rank_only(self, capsys):
        exit_code = cli.main(["coach", "--cards", "A,7", "--dealer", "9",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Cards             : A, 7" in out

    def test_captured_output_has_no_ansi_by_default(self, capsys):
        # Non-TTY (captured) output should be plain text even without --no-color.
        cli.main(["coach", "--cards", "A\u2660,7\u2665", "--dealer", "9\u2666"])
        out = capsys.readouterr().out
        assert "\033[" not in out

    def test_play_still_works_with_card_display(self, capsys):
        exit_code = cli.main(["play", "--decks", "6", "--seed", "42"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Played Hand ===" in out
        assert "Final player cards" in out


class TestCliCountAwareCoach:
    def test_coach_true_count_deviation(self, capsys):
        exit_code = cli.main(["coach", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666", "--true-count", "1",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "True count" in out
        assert "Basic action" in out
        assert "Final recommended action" in out
        assert "Deviation applied" in out
        assert "Deviation rule" in out
        assert "Hard 16 vs 10" in out
        assert "Final recommended action: STAND" in out

    def test_coach_true_count_no_deviation(self, capsys):
        exit_code = cli.main(["coach", "--cards", "A,7", "--dealer", "9",
                              "--true-count", "1",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Deviation applied" in out
        assert "Deviation rule" not in out
        assert "Final recommended action: HIT" in out

    def test_coach_without_true_count_has_no_count_block(self, capsys):
        exit_code = cli.main(["coach", "--cards", "A,7", "--dealer", "9",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Count-aware advisory" not in out
        assert "Recommended action" in out

    def test_coach_play_true_count_advisory(self, capsys):
        exit_code = cli.main(["coach-play", "--decks", "6", "--seed", "42",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--true-count", "1"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "True count (advisory): 1" in out
        assert "True count" in out


class TestCliOdds:
    def test_odds_works(self, capsys):
        exit_code = cli.main(["odds", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Probability Advisor ===" in out
        assert "Bust if hit" in out
        assert "Dealer bust" in out
        assert "Action EV estimates" in out
        assert "Best estimated action" in out
        assert "Recommended action" in out

    def test_odds_soft_hand(self, capsys):
        exit_code = cli.main(["odds", "--cards", "A\u2660,7\u2665",
                              "--dealer", "9\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        # Soft 18 cannot bust on one card.
        assert "Bust if hit       : 0.0%" in out

    def test_odds_invalid_card_errors(self, capsys):
        exit_code = cli.main(["odds", "--cards", "Z,7", "--dealer", "9"])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Error" in err

    def test_coach_show_odds(self, capsys):
        exit_code = cli.main(["coach", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666", "--show-odds",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Odds (approximate)" in out
        assert "Bust if hit" in out
        assert "Best estimated action" in out
        # The final recommendation is still shown and not overridden.
        assert "Recommended action" in out

    def test_coach_show_odds_with_true_count(self, capsys):
        exit_code = cli.main(["coach", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666", "--show-odds",
                              "--true-count", "1",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Odds (approximate)" in out
        assert "Count-aware advisory" in out


class TestCliCompositionAware:
    """v1.14.0 composition-aware probability & EV advisor."""

    def test_odds_composition_aware(self, capsys):
        exit_code = cli.main(["odds", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Probability Advisor ===" in out
        assert "Composition-aware  : yes" in out
        assert "Cards remaining" in out
        assert "Action EV estimates" in out

    def test_odds_seen_cards_enables_composition_aware(self, capsys):
        exit_code = cli.main(["odds", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--seen-cards", "2\u2663,5\u2666,K\u2660,A\u2665"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Composition-aware  : yes" in out
        # 2 player + 1 dealer + 4 seen = 7 removed.
        assert "Cards remaining    : 305" in out

    def test_odds_composition_shows_summary(self, capsys):
        exit_code = cli.main(["odds", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--seen-cards", "2\u2663,5\u2666", "--composition"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "-- Shoe composition --" in out
        assert "Total cards remaining" in out
        assert "Rank counts" in out

    def test_odds_plain_has_no_composition(self, capsys):
        # Without any composition flag the original output is preserved.
        exit_code = cli.main(["odds", "--cards", "A\u2660,7\u2665",
                              "--dealer", "9\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Composition-aware" not in out
        assert "Bust if hit       : 0.0%" in out

    def test_coach_show_odds_composition_aware(self, capsys):
        exit_code = cli.main(["coach", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666", "--show-odds",
                              "--composition-aware",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Odds (approximate)" in out
        assert "Composition-aware    : yes" in out
        assert "Recommended action" in out

    def test_coach_show_odds_seen_cards(self, capsys):
        exit_code = cli.main(["coach", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666", "--show-odds",
                              "--true-count", "1",
                              "--seen-cards", "2\u2663,5\u2666,K\u2660,A\u2665",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Composition-aware    : yes" in out
        assert "Count-aware advisory" in out


class TestCliSplitEV:
    """v1.15.0 composition-aware split / re-split EV advisor."""

    def test_odds_pair_8_8_shows_split_ev(self, capsys):
        exit_code = cli.main(["odds", "--cards", "8\u2660,8\u2665",
                              "--dealer", "6\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "-- Split EV estimate --" in out
        assert "Estimated split EV" in out
        assert "Max split hands" in out
        assert "DAS" in out

    def test_odds_pair_aces_shows_split_context(self, capsys):
        exit_code = cli.main(["odds", "--cards", "A\u2660,A\u2665",
                              "--dealer", "6\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "-- Split EV estimate --" in out
        assert "Hit split aces       : no" in out
        # Split aces (one card then stand) are evaluated exactly.
        assert "Exact for these rules: yes" in out

    def test_odds_pair_tens_works(self, capsys):
        exit_code = cli.main(["odds", "--cards", "10\u2660,10\u2665",
                              "--dealer", "6\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "-- Split EV estimate --" in out
        # Standing on 20 beats splitting tens; the advisory should not pick SPLIT.
        assert "Best estimated action: STAND" in out

    def test_odds_non_pair_has_no_split_ev(self, capsys):
        exit_code = cli.main(["odds", "--cards", "10\u2660,6\u2665",
                              "--dealer", "6\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Split EV estimate" not in out

    def test_coach_pair_show_odds_composition_aware(self, capsys):
        exit_code = cli.main(["coach", "--cards", "8\u2660,8\u2665",
                              "--dealer", "6\u2666", "--show-odds",
                              "--composition-aware",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Odds (approximate)" in out
        assert "Split EV" in out
        assert "EV vs recommendation" in out
        # The coach's final recommendation is still shown (no override).
        assert "Recommended action" in out


class TestCliPlayerEVTree:
    """v1.16.0 full player EV decision tree."""

    def test_odds_composition_aware_shows_decision_tree(self, capsys):
        exit_code = cli.main(["odds", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "-- Player EV decision tree --" in out
        assert "Best EV action" in out
        assert "-- EV by action --" in out
        assert "EV vs recommendation" in out

    def test_odds_16_vs_10_shows_ev_by_action(self, capsys):
        exit_code = cli.main(["odds", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        # Each legal action has an EV line in the tree block.
        assert "SURRENDER :" in out
        assert "HIT       :" in out
        assert "STAND     :" in out

    def test_odds_soft_18_vs_9_works(self, capsys):
        exit_code = cli.main(["odds", "--cards", "A\u2660,7\u2665",
                              "--dealer", "9\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "-- Player EV decision tree --" in out
        assert "Best EV action       : HIT" in out

    def test_odds_pair_shows_both_tree_and_split(self, capsys):
        exit_code = cli.main(["odds", "--cards", "8\u2660,8\u2665",
                              "--dealer", "6\u2666",
                              "--profile", "SIX_DECK_H17_DAS_LS",
                              "--composition-aware"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "-- Player EV decision tree --" in out
        assert "-- Split EV estimate --" in out

    def test_coach_show_odds_shows_player_ev_summary(self, capsys):
        exit_code = cli.main(["coach", "--cards", "10\u2660,6\u2665",
                              "--dealer", "10\u2666", "--show-odds",
                              "--composition-aware",
                              "--profile", "SIX_DECK_H17_DAS_LS"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Player EV best action" in out
        assert "EV vs recommendation" in out
        assert "Recommended action" in out



class TestCliLearn:
    """Adaptive local-learning 'learn' command and coach --use-history."""

    def _save_outcomes(self, outcome_dir, count=12, profile="SIX_DECK_H17_DAS_LS"):
        for seed in range(1, count + 1):
            cli.main([
                "coach-play", "--decks", "6", "--seed", str(seed),
                "--profile", profile, "--save-outcome",
                "--outcome-dir", str(outcome_dir),
            ])

    def test_learn_without_data_shows_clear_message(self, capsys, tmp_path):
        exit_code = cli.main(["learn", "--dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Adaptive Learning ===" in out
        assert "No saved outcome history yet" in out
        assert "--save-outcome" in out

    def test_learn_with_saved_outcomes_shows_total(self, capsys, tmp_path):
        self._save_outcomes(tmp_path, count=12)
        capsys.readouterr()  # discard coach-play output
        exit_code = cli.main(["learn", "--dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total records      : 12" in out
        assert "Strongest spots" in out
        assert "Weakest spots" in out

    def test_learn_profile_filter(self, capsys, tmp_path):
        self._save_outcomes(tmp_path, count=6, profile="SIX_DECK_H17_DAS_LS")
        capsys.readouterr()
        exit_code = cli.main([
            "learn", "--dir", str(tmp_path),
            "--profile", "SIX_DECK_H17_DAS_LS",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "SIX_DECK_H17_DAS_LS" in out
        # A profile with no saved outcomes yields the empty-history message.
        exit_code = cli.main([
            "learn", "--dir", str(tmp_path),
            "--profile", "SIX_DECK_S17_DAS_LS",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "No saved outcome history yet" in out

    def test_coach_use_history_without_history(self, capsys, tmp_path):
        exit_code = cli.main([
            "coach", "--cards", "10,6", "--dealer", "10",
            "--profile", "SIX_DECK_H17_DAS_LS",
            "--use-history", "--history-dir", str(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Recommended action" in out
        assert "Local history context" in out
        assert "No saved outcome history yet" in out

    def test_coach_use_history_with_history(self, capsys, tmp_path):
        self._save_outcomes(tmp_path, count=12)
        capsys.readouterr()
        exit_code = cli.main([
            "coach", "--cards", "10,6", "--dealer", "10",
            "--profile", "SIX_DECK_H17_DAS_LS",
            "--use-history", "--history-dir", str(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Local history context" in out
        assert "Local win rate" in out
        assert "Caution" in out

    def test_coach_combined_count_odds_history(self, capsys, tmp_path):
        self._save_outcomes(tmp_path, count=12)
        capsys.readouterr()
        exit_code = cli.main([
            "coach", "--cards", "10,6", "--dealer", "10",
            "--profile", "SIX_DECK_H17_DAS_LS",
            "--true-count", "1", "--show-odds",
            "--use-history", "--history-dir", str(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Count-aware advisory" in out
        assert "Odds (approximate)" in out
        assert "Local history context" in out

    def test_coach_use_history_does_not_change_action(self, capsys, tmp_path):
        # Action with history must match action without history.
        cli.main([
            "coach", "--cards", "10,6", "--dealer", "10",
            "--profile", "SIX_DECK_H17_DAS_LS",
        ])
        base = capsys.readouterr().out
        base_action = [line for line in base.splitlines()
                       if line.startswith("Recommended action")][0]

        self._save_outcomes(tmp_path, count=12)
        capsys.readouterr()
        cli.main([
            "coach", "--cards", "10,6", "--dealer", "10",
            "--profile", "SIX_DECK_H17_DAS_LS",
            "--use-history", "--history-dir", str(tmp_path),
        ])
        with_history = capsys.readouterr().out
        hist_action = [line for line in with_history.splitlines()
                       if line.startswith("Recommended action")][0]
        assert base_action == hist_action



class TestCliEVSnapshotHistory:
    """v1.17.0 EV snapshot history & Strategy-vs-EV review."""

    def test_odds_save_ev_snapshot_creates_file(self, capsys, tmp_path):
        exit_code = cli.main([
            "odds", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--save-ev-snapshot", "--ev-dir", str(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved EV snapshot" in out
        assert len(list(tmp_path.glob("ev_snapshot_*.json"))) == 1

    def test_coach_show_odds_save_ev_snapshot_creates_file(self, capsys, tmp_path):
        exit_code = cli.main([
            "coach", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--show-odds",
            "--composition-aware",
            "--save-ev-snapshot", "--ev-dir", str(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved EV snapshot" in out
        assert len(list(tmp_path.glob("ev_snapshot_*.json"))) == 1

    def test_coach_save_ev_snapshot_without_show_odds_errors(self, capsys, tmp_path):
        exit_code = cli.main([
            "coach", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS",
            "--save-ev-snapshot", "--ev-dir", str(tmp_path),
        ])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "--save-ev-snapshot requires --show-odds" in err
        assert not list(tmp_path.glob("ev_snapshot_*.json"))

    def test_ev_review_without_data_shows_clear_message(self, capsys, tmp_path):
        exit_code = cli.main(["ev-review", "--dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== EV Snapshot Review ===" in out
        assert "No saved EV snapshots yet" in out
        assert "--save-ev-snapshot" in out

    def test_ev_review_with_snapshots_shows_total(self, capsys, tmp_path):
        for _ in range(3):
            cli.main([
                "odds", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
                "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
                "--save-ev-snapshot", "--ev-dir", str(tmp_path),
            ])
        capsys.readouterr()  # discard odds output
        exit_code = cli.main(["ev-review", "--dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total snapshots    : 3" in out
        assert "Agreement count" in out
        assert "Agreement rate" in out

    def test_ev_review_disagreements_only_filters(self, capsys, tmp_path):
        # 10,6 vs 10 agrees (both SURRENDER), so disagreements-only is empty.
        cli.main([
            "odds", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--save-ev-snapshot", "--ev-dir", str(tmp_path),
        ])
        capsys.readouterr()
        exit_code = cli.main([
            "ev-review", "--dir", str(tmp_path), "--disagreements-only",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "No saved EV snapshots yet" in out

    def test_ev_review_profile_filter(self, capsys, tmp_path):
        cli.main([
            "odds", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--save-ev-snapshot", "--ev-dir", str(tmp_path),
        ])
        capsys.readouterr()
        # A matching profile shows the snapshot.
        exit_code = cli.main([
            "ev-review", "--dir", str(tmp_path),
            "--profile", "SIX_DECK_H17_DAS_LS",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total snapshots    : 1" in out
        # A non-matching profile yields the empty message.
        exit_code = cli.main([
            "ev-review", "--dir", str(tmp_path),
            "--profile", "SIX_DECK_S17_DAS_LS",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "No saved EV snapshots yet" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliStrategyVsEVExplanation:
    """v1.18.0 Strategy-vs-EV explanation engine."""

    def test_odds_explain_ev_works(self, capsys):
        exit_code = cli.main([
            "odds", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--explain-ev",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Strategy vs EV explanation" in out
        assert "Coach recommendation" in out
        assert "Best EV action" in out
        assert "Gap label" in out
        assert "Advisory note" in out

    def test_odds_composition_aware_explain_ev(self, capsys):
        exit_code = cli.main([
            "odds", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--explain-ev",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Strategy vs EV explanation" in out
        assert "Explanation" in out

    def test_odds_explain_ev_disagreement(self, capsys):
        # 2,9 vs A: coach recommends DOUBLE, advisory best EV is HIT (LARGE gap).
        exit_code = cli.main([
            "odds", "--cards", "2\u2660,9\u2665", "--dealer", "A\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--explain-ev",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Agreement           : DIFFERS" in out
        assert "never overrides the strategy recommendation" in out

    def test_coach_show_odds_explain_ev(self, capsys):
        exit_code = cli.main([
            "coach", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--show-odds",
            "--composition-aware", "--explain-ev",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Strategy vs EV explanation" in out
        # The coach's main recommendation is still shown (no override).
        assert "Recommended action" in out

    def test_coach_explain_ev_without_show_odds_errors(self, capsys):
        exit_code = cli.main([
            "coach", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--explain-ev",
        ])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "--explain-ev requires --show-odds" in err

    def test_ev_review_explain_with_snapshots(self, capsys, tmp_path):
        # Save an agreement and a disagreement snapshot.
        cli.main([
            "odds", "--cards", "10\u2660,6\u2665", "--dealer", "10\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--save-ev-snapshot", "--ev-dir", str(tmp_path),
        ])
        cli.main([
            "odds", "--cards", "2\u2660,9\u2665", "--dealer", "A\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--save-ev-snapshot", "--ev-dir", str(tmp_path),
        ])
        capsys.readouterr()  # discard odds output
        exit_code = cli.main(["ev-review", "--dir", str(tmp_path), "--explain"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total snapshots" in out
        assert "Strategy vs EV explanations" in out
        # The disagreement spot is explained.
        assert "DIFFERS" in out or "Best EV action" in out

    def test_ev_review_large_gaps_only(self, capsys, tmp_path):
        # Agreement + a LARGE-gap disagreement (2,9 vs A) + a MEDIUM one.
        for cards, dealer in [
            ("10\u2660,6\u2665", "10\u2666"),   # agreement
            ("2\u2660,9\u2665", "A\u2666"),     # LARGE gap (DOUBLE vs HIT)
            ("4\u2660,10\u2665", "A\u2666"),    # MEDIUM gap (HIT vs SURRENDER)
        ]:
            cli.main([
                "odds", "--cards", cards, "--dealer", dealer,
                "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
                "--save-ev-snapshot", "--ev-dir", str(tmp_path),
            ])
        capsys.readouterr()
        exit_code = cli.main([
            "ev-review", "--dir", str(tmp_path), "--large-gaps-only", "--explain",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        # Only the LARGE-gap snapshot survives the filter.
        assert "Total snapshots    : 1" in out

    def test_ev_review_disagreements_only_explain(self, capsys, tmp_path):
        cli.main([
            "odds", "--cards", "2\u2660,9\u2665", "--dealer", "A\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--save-ev-snapshot", "--ev-dir", str(tmp_path),
        ])
        capsys.readouterr()
        exit_code = cli.main([
            "ev-review", "--dir", str(tmp_path), "--disagreements-only",
            "--explain",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Strategy vs EV explanations" in out



class TestCliReport:
    """v1.19.0 exportable learning reports."""

    def test_report_no_data_creates_file(self, capsys, tmp_path):
        out = tmp_path / "report.md"
        exit_code = cli.main(["report", "--output", str(out)])
        printed = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Learning Report ===" in printed
        assert "Saved" in printed
        assert out.exists()

    def test_report_markdown_print_shows_overview(self, capsys, tmp_path):
        exit_code = cli.main([
            "report", "--format", "markdown", "--print",
            "--output", str(tmp_path / "r.md"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "## Overview" in out
        assert "## Practice recommendations" in out

    def test_report_json_creates_json(self, capsys, tmp_path):
        out = tmp_path / "r.json"
        exit_code = cli.main(["report", "--format", "json", "--output", str(out)])
        capsys.readouterr()
        assert exit_code == 0
        import json
        json.loads(out.read_text(encoding="utf-8"))

    def test_report_csv_creates_csv(self, capsys, tmp_path):
        out = tmp_path / "r.csv"
        exit_code = cli.main(["report", "--format", "csv", "--output", str(out)])
        capsys.readouterr()
        assert exit_code == 0
        assert out.read_text(encoding="utf-8").startswith("key,value")

    def test_report_output_path_is_used(self, capsys, tmp_path):
        out = tmp_path / "sub" / "my_report.md"
        exit_code = cli.main(["report", "--output", str(out)])
        printed = capsys.readouterr().out
        assert exit_code == 0
        assert out.exists()
        assert str(out) in printed

    def test_report_profile_filter_works(self, capsys, tmp_path):
        exit_code = cli.main([
            "report", "--profile", "SIX_DECK_H17_DAS_LS",
            "--output", str(tmp_path / "r.md"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved" in out

    def test_report_invalid_format_errors(self, capsys, tmp_path):
        exit_code = cli.main([
            "report", "--format", "xml", "--output", str(tmp_path / "r.xml"),
        ])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Unknown report format" in err

    def test_report_with_history_counts(self, capsys, tmp_path):
        session_dir = tmp_path / "history"
        outcome_dir = tmp_path / "outcomes"
        cli.main([
            "quiz-session", "--questions", "3", "--seed", "1",
            "--answers", "H,S,D", "--save", "--history-dir", str(session_dir),
        ])
        cli.main([
            "coach-play", "--decks", "6", "--seed", "5",
            "--profile", "SIX_DECK_H17_DAS_LS", "--save-outcome",
            "--outcome-dir", str(outcome_dir),
        ])
        capsys.readouterr()
        exit_code = cli.main([
            "report", "--print", "--output", str(tmp_path / "r.md"),
            "--session-dir", str(session_dir), "--outcome-dir", str(outcome_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Sessions: 1" in out
        assert "Outcomes: 1" in out



class TestCliDashboard:
    """v1.20.0 profile dashboard & trends."""

    def _seed(self, tmp_path):
        session_dir = tmp_path / "history"
        outcome_dir = tmp_path / "outcomes"
        ev_dir = tmp_path / "ev"
        cli.main([
            "quiz-session", "--questions", "3", "--seed", "1",
            "--answers", "H,S,D", "--save", "--history-dir", str(session_dir),
        ])
        cli.main([
            "coach-play", "--decks", "6", "--seed", "5",
            "--profile", "SIX_DECK_H17_DAS_LS", "--save-outcome",
            "--outcome-dir", str(outcome_dir),
        ])
        cli.main([
            "odds", "--cards", "2\u2660,9\u2665", "--dealer", "A\u2666",
            "--profile", "SIX_DECK_H17_DAS_LS", "--composition-aware",
            "--save-ev-snapshot", "--ev-dir", str(ev_dir),
        ])
        return session_dir, outcome_dir, ev_dir

    def test_dashboard_no_data_shows_clear_message(self, capsys, tmp_path):
        exit_code = cli.main([
            "dashboard",
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Dashboard overview ===" in out
        assert "No saved local history yet" in out

    def test_dashboard_with_data_shows_overview(self, capsys, tmp_path):
        session_dir, outcome_dir, ev_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "dashboard", "--session-dir", str(session_dir),
            "--outcome-dir", str(outcome_dir), "--ev-dir", str(ev_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Dashboard overview ===" in out
        assert "Total outcomes    : 1" in out
        assert "Next practice plan" in out

    def test_dashboard_profile_filter(self, capsys, tmp_path):
        session_dir, outcome_dir, ev_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "dashboard", "--profile", "SIX_DECK_H17_DAS_LS",
            "--session-dir", str(session_dir),
            "--outcome-dir", str(outcome_dir), "--ev-dir", str(ev_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Selected profile: SIX_DECK_H17_DAS_LS" in out

    def test_dashboard_limit(self, capsys, tmp_path):
        session_dir, outcome_dir, ev_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "dashboard", "--limit", "20",
            "--session-dir", str(session_dir),
            "--outcome-dir", str(outcome_dir), "--ev-dir", str(ev_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Dashboard overview ===" in out

    def test_dashboard_markdown_prints_headings(self, capsys, tmp_path):
        session_dir, outcome_dir, ev_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "dashboard", "--markdown",
            "--session-dir", str(session_dir),
            "--outcome-dir", str(outcome_dir), "--ev-dir", str(ev_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "# Blackjack Coach Pro Demo - Profile Dashboard" in out
        assert "## Dashboard overview" in out

    def test_dashboard_export_creates_file(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        session_dir, outcome_dir, ev_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "dashboard", "--export",
            "--session-dir", str(session_dir),
            "--outcome-dir", str(outcome_dir), "--ev-dir", str(ev_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved dashboard" in out
        reports = list((tmp_path / ".blackjack_coach" / "reports").glob("dashboard_*.md"))
        assert len(reports) == 1

    def test_dashboard_output_path(self, capsys, tmp_path):
        session_dir, outcome_dir, ev_dir = self._seed(tmp_path)
        out_file = tmp_path / "dashboard.md"
        capsys.readouterr()
        exit_code = cli.main([
            "dashboard", "--output", str(out_file),
            "--session-dir", str(session_dir),
            "--outcome-dir", str(outcome_dir), "--ev-dir", str(ev_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out_file.exists()
        assert str(out_file) in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliDrill:
    """v1.21.0 weak-spot drill generator."""

    def test_drill_no_history_shows_plan_and_question(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--count", "3",
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Plan ===" in out
        assert "Total drills: 3" in out
        assert "Drill 1" in out
        # Clear fallback note when there is no history.
        assert "educational drill set" in out

    def test_drill_plan_only(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--plan-only", "--count", "5",
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Plan ===" in out
        assert "Drill 1" not in out

    def test_drill_focus_pairs_count(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--focus", "pairs", "--count", "5",
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Focus       : pairs" in out

    def test_drill_seed_spot_answer(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--seed", "42", "--spot", "1", "--answer", "HIT",
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Result ===" in out
        assert "Correct action" in out
        assert "Result" in out

    def test_drill_invalid_answer_errors(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--spot", "1", "--answer", "ZZZ",
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "Invalid action" in err

    def test_drill_profile_works(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--profile", "SIX_DECK_H17_DAS_LS", "--count", "3",
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Profile     : SIX_DECK_H17_DAS_LS" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliDrillHistory:
    """v1.22.0 drill session history & spaced review."""

    def test_drill_answer_save_creates_file(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--seed", "42", "--spot", "1", "--answer", "HIT", "--save",
            "--drill-dir", str(tmp_path),
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved drill session" in out
        assert len(list(tmp_path.glob("drill_session_*.json"))) == 1

    def test_drill_save_without_answer_errors(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--save", "--drill-dir", str(tmp_path),
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        err = capsys.readouterr().err
        assert exit_code == 2
        assert "--save requires --answer" in err

    def test_drill_review_no_data_message(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--review", "--drill-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Review ===" in out
        assert "No saved drill sessions yet" in out

    def test_drill_review_with_data_shows_total(self, capsys, tmp_path):
        for seed in (1, 2):
            cli.main([
                "drill", "--seed", str(seed), "--spot", "1", "--answer", "HIT",
                "--save", "--drill-dir", str(tmp_path),
                "--session-dir", str(tmp_path / "s"),
                "--outcome-dir", str(tmp_path / "o"),
                "--ev-dir", str(tmp_path / "e"),
            ])
        capsys.readouterr()
        exit_code = cli.main(["drill", "--review", "--drill-dir", str(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total sessions  : 2" in out
        assert "Practice recommendations" in out

    def test_drill_review_due_only(self, capsys, tmp_path):
        cli.main([
            "drill", "--seed", "1", "--spot", "1", "--answer", "HIT",
            "--save", "--drill-dir", str(tmp_path),
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        capsys.readouterr()
        exit_code = cli.main([
            "drill", "--review", "--due-only", "--drill-dir", str(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Due for review" in out

    def test_drill_profile_review_works(self, capsys, tmp_path):
        exit_code = cli.main([
            "drill", "--profile", "SIX_DECK_H17_DAS_LS", "--review",
            "--drill-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Review ===" in out



class TestCliReviewQueue:
    """v1.23.0 drill review scheduler & streaks."""

    def _seed(self, tmp_path):
        drill_dir = tmp_path / "drills"
        cli.main([
            "drill", "--seed", "1", "--spot", "1", "--answer", "HIT", "--save",
            "--drill-dir", str(drill_dir),
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ])
        return drill_dir

    def test_review_queue_no_data_message(self, capsys, tmp_path):
        exit_code = cli.main([
            "review-queue", "--drill-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Review Queue ===" in out
        assert "No saved drill sessions yet" in out

    def test_review_queue_with_data(self, capsys, tmp_path):
        drill_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "review-queue", "--drill-dir", str(drill_dir), "--today",
            "2026-12-31",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Review Queue ===" in out
        assert "Total items" in out

    def test_review_queue_due_only(self, capsys, tmp_path):
        drill_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "review-queue", "--drill-dir", str(drill_dir), "--today",
            "2026-12-31", "--due-only",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Due now" in out

    def test_review_queue_streaks(self, capsys, tmp_path):
        drill_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "review-queue", "--drill-dir", str(drill_dir), "--streaks",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Current streak" in out

    def test_review_queue_profile(self, capsys, tmp_path):
        drill_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "review-queue", "--drill-dir", str(drill_dir),
            "--profile", "SIX_DECK_H17_DAS_LS",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Review Queue ===" in out

    def test_review_queue_today(self, capsys, tmp_path):
        drill_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "review-queue", "--drill-dir", str(drill_dir), "--today",
            "2026-06-23",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Drill Review Queue ===" in out

    def test_review_queue_markdown(self, capsys, tmp_path):
        drill_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "review-queue", "--drill-dir", str(drill_dir), "--markdown",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "# Blackjack Coach Pro Demo - Drill Review Queue" in out
        assert "## Due now" in out

    def test_review_queue_export_output(self, capsys, tmp_path):
        drill_dir = self._seed(tmp_path)
        out_file = tmp_path / "review.md"
        capsys.readouterr()
        exit_code = cli.main([
            "review-queue", "--drill-dir", str(drill_dir), "--export",
            "--output", str(out_file),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out_file.exists()
        assert "Saved review queue" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliPracticePack:
    """v1.24.0 daily practice pack generator."""

    def _dirs(self, tmp_path):
        return [
            "--drill-dir", str(tmp_path / "dr"),
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ]

    def test_practice_pack_no_data_starter(self, capsys, tmp_path):
        exit_code = cli.main(["practice-pack", "--count", "4", *self._dirs(tmp_path)])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Daily Practice Pack ===" in out
        assert "starter educational practice pack" in out

    def test_practice_pack_focus_due_count(self, capsys, tmp_path):
        exit_code = cli.main([
            "practice-pack", "--focus", "due", "--count", "10",
            *self._dirs(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Daily Practice Pack ===" in out
        assert "Focus       : due" in out

    def test_practice_pack_focus_ev_profile(self, capsys, tmp_path):
        exit_code = cli.main([
            "practice-pack", "--focus", "ev", "--profile",
            "SIX_DECK_H17_DAS_LS", *self._dirs(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Daily Practice Pack ===" in out

    def test_practice_pack_today_seed(self, capsys, tmp_path):
        exit_code = cli.main([
            "practice-pack", "--today", "2026-06-23", "--seed", "42",
            *self._dirs(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Date        : 2026-06-23" in out

    def test_practice_pack_markdown(self, capsys, tmp_path):
        exit_code = cli.main([
            "practice-pack", "--markdown", *self._dirs(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "# Blackjack Coach Pro Demo - Daily Practice Pack" in out
        assert "## Practice checklist" in out

    def test_practice_pack_export_output(self, capsys, tmp_path):
        out_file = tmp_path / "practice_pack.md"
        exit_code = cli.main([
            "practice-pack", "--export", "--output", str(out_file),
            *self._dirs(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out_file.exists()
        assert "Saved practice pack" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliPracticePackHistory:
    """v1.25.0 practice pack completion history."""

    def _gen_dirs(self, tmp_path):
        return [
            "--drill-dir", str(tmp_path / "dr"),
            "--session-dir", str(tmp_path / "s"),
            "--outcome-dir", str(tmp_path / "o"),
            "--ev-dir", str(tmp_path / "e"),
        ]

    def test_complete_creates_file(self, capsys, tmp_path):
        pack_dir = tmp_path / "packs"
        exit_code = cli.main([
            "practice-pack", "--complete", "--pack-dir", str(pack_dir),
            *self._gen_dirs(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved pack completion" in out
        assert len(list(pack_dir.glob("practice_pack_*.json"))) == 1

    def test_complete_with_detail_accuracy(self, capsys, tmp_path):
        pack_dir = tmp_path / "packs"
        exit_code = cli.main([
            "practice-pack", "--complete",
            "--correct-spots", "hard_16_vs_10,soft_18_vs_9",
            "--missed-spots", "pair_8_vs_6",
            "--pack-dir", str(pack_dir), *self._gen_dirs(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved pack completion" in out
        # 2 correct of 3 completed -> 67% accuracy.
        assert "67% accuracy" in out

    def test_progress_no_data_message(self, capsys, tmp_path):
        exit_code = cli.main([
            "practice-pack", "--progress", "--pack-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Practice Pack Progress ===" in out
        assert "No saved practice pack completions yet" in out

    def test_progress_with_data(self, capsys, tmp_path):
        pack_dir = tmp_path / "packs"
        cli.main([
            "practice-pack", "--complete", "--pack-dir", str(pack_dir),
            *self._gen_dirs(tmp_path),
        ])
        capsys.readouterr()
        exit_code = cli.main([
            "practice-pack", "--progress", "--pack-dir", str(pack_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total packs" in out

    def test_progress_profile(self, capsys, tmp_path):
        exit_code = cli.main([
            "practice-pack", "--progress", "--profile", "SIX_DECK_H17_DAS_LS",
            "--pack-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Practice Pack Progress ===" in out

    def test_complete_export_does_not_break(self, capsys, tmp_path):
        pack_dir = tmp_path / "packs"
        out_file = tmp_path / "pack.md"
        exit_code = cli.main([
            "practice-pack", "--complete", "--export", "--output",
            str(out_file), "--pack-dir", str(pack_dir), *self._gen_dirs(tmp_path),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out_file.exists()
        assert "Saved practice pack" in out
        assert "Saved pack completion" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliRepeatPack:
    """v1.26.0 repeat pack for missed spots."""

    def test_repeat_pack_no_data_starter(self, capsys, tmp_path):
        exit_code = cli.main([
            "repeat-pack", "--count", "4",
            "--pack-dir", str(tmp_path / "p"), "--drill-dir", str(tmp_path / "dr"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Repeat Pack ===" in out
        assert "starter educational repeat pack" in out

    def test_repeat_pack_count(self, capsys, tmp_path):
        exit_code = cli.main([
            "repeat-pack", "--count", "10", "--pack-dir", str(tmp_path / "p"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Repeat Pack ===" in out

    def test_repeat_pack_profile(self, capsys, tmp_path):
        exit_code = cli.main([
            "repeat-pack", "--profile", "SIX_DECK_H17_DAS_LS",
            "--pack-dir", str(tmp_path / "p"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Repeat Pack ===" in out

    def test_repeat_pack_today_seed(self, capsys, tmp_path):
        exit_code = cli.main([
            "repeat-pack", "--today", "2026-06-23", "--seed", "42",
            "--pack-dir", str(tmp_path / "p"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Date        : 2026-06-23" in out

    def test_repeat_pack_markdown(self, capsys, tmp_path):
        exit_code = cli.main([
            "repeat-pack", "--markdown", "--pack-dir", str(tmp_path / "p"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "# Blackjack Coach Pro Demo - Repeat Pack" in out
        assert "## Repeat checklist" in out

    def test_repeat_pack_export_output(self, capsys, tmp_path):
        out_file = tmp_path / "repeat_pack.md"
        exit_code = cli.main([
            "repeat-pack", "--export", "--output", str(out_file),
            "--pack-dir", str(tmp_path / "p"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out_file.exists()
        assert "Saved repeat pack" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliRepeatPackHistory:
    """v1.27.0 repeat pack completion history."""

    def test_complete_creates_file(self, capsys, tmp_path):
        repeat_dir = tmp_path / "rp"
        exit_code = cli.main([
            "repeat-pack", "--complete", "--repeat-dir", str(repeat_dir),
            "--pack-dir", str(tmp_path / "p"), "--drill-dir", str(tmp_path / "dr"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved repeat completion" in out
        assert len(list(repeat_dir.glob("repeat_pack_*.json"))) == 1

    def test_complete_with_detail_accuracy(self, capsys, tmp_path):
        repeat_dir = tmp_path / "rp"
        exit_code = cli.main([
            "repeat-pack", "--complete",
            "--corrected-spots", "hard_16_vs_10,soft_18_vs_9",
            "--still-missed-spots", "pair_8_vs_6",
            "--repeat-dir", str(repeat_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Saved repeat completion" in out
        assert "67% corrected" in out

    def test_progress_no_data_message(self, capsys, tmp_path):
        exit_code = cli.main([
            "repeat-pack", "--progress", "--repeat-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Repeat Pack Progress ===" in out
        assert "No saved repeat pack completions yet" in out

    def test_progress_with_data(self, capsys, tmp_path):
        repeat_dir = tmp_path / "rp"
        cli.main([
            "repeat-pack", "--complete", "--repeat-dir", str(repeat_dir),
        ])
        capsys.readouterr()
        exit_code = cli.main([
            "repeat-pack", "--progress", "--repeat-dir", str(repeat_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Total repeat packs" in out

    def test_progress_profile(self, capsys, tmp_path):
        exit_code = cli.main([
            "repeat-pack", "--progress", "--profile", "SIX_DECK_H17_DAS_LS",
            "--repeat-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Repeat Pack Progress ===" in out

    def test_complete_export_does_not_break(self, capsys, tmp_path):
        repeat_dir = tmp_path / "rp"
        out_file = tmp_path / "repeat.md"
        exit_code = cli.main([
            "repeat-pack", "--complete", "--export", "--output", str(out_file),
            "--repeat-dir", str(repeat_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out_file.exists()
        assert "Saved repeat pack" in out
        assert "Saved repeat completion" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliCorrectionDashboard:
    """v1.28.0 missed-spot correction dashboard."""

    def _seed(self, tmp_path):
        repeat_dir = tmp_path / "rp"
        for _ in range(2):
            cli.main([
                "repeat-pack", "--complete",
                "--corrected-spots", "hard_16_vs_10",
                "--still-missed-spots", "pair_8_vs_6",
                "--repeat-dir", str(repeat_dir),
            ])
        return repeat_dir

    def test_no_data_message(self, capsys, tmp_path):
        exit_code = cli.main([
            "correction-dashboard", "--repeat-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Missed-Spot Correction Dashboard ===" in out
        assert "No saved repeat pack completions yet" in out

    def test_with_data(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "correction-dashboard", "--repeat-dir", str(repeat_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Missed-Spot Correction Dashboard ===" in out
        assert "Total spots" in out

    def test_profile(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "correction-dashboard", "--profile", "SIX_DECK_H17_DAS_LS",
            "--repeat-dir", str(repeat_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Missed-Spot Correction Dashboard ===" in out

    def test_markdown(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "correction-dashboard", "--repeat-dir", str(repeat_dir), "--markdown",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "# Blackjack Coach Pro Demo - Missed-Spot Correction Dashboard" in out
        assert "## Status counts" in out

    def test_export_output(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        out_file = tmp_path / "correction_dashboard.md"
        capsys.readouterr()
        exit_code = cli.main([
            "correction-dashboard", "--repeat-dir", str(repeat_dir),
            "--export", "--output", str(out_file),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out_file.exists()
        assert "Saved correction dashboard" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliCorrectionPlan:
    """v1.29.0 correction action plan."""

    def _seed(self, tmp_path):
        repeat_dir = tmp_path / "rp"
        for _ in range(2):
            cli.main([
                "repeat-pack", "--complete",
                "--corrected-spots", "hard_16_vs_10",
                "--still-missed-spots", "pair_8_vs_6",
                "--repeat-dir", str(repeat_dir),
            ])
        return repeat_dir

    def test_no_data_message(self, capsys, tmp_path):
        exit_code = cli.main([
            "correction-plan", "--repeat-dir", str(tmp_path / "empty"),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Correction Action Plan ===" in out
        assert "No correction history yet" in out

    def test_with_data(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "correction-plan", "--repeat-dir", str(repeat_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Correction Action Plan ===" in out
        assert "Total items" in out

    def test_focus_urgent(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "correction-plan", "--repeat-dir", str(repeat_dir), "--focus",
            "urgent",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Urgent repeats" in out

    def test_profile(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "correction-plan", "--profile", "SIX_DECK_H17_DAS_LS",
            "--repeat-dir", str(repeat_dir),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "=== Correction Action Plan ===" in out

    def test_markdown(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        capsys.readouterr()
        exit_code = cli.main([
            "correction-plan", "--repeat-dir", str(repeat_dir), "--markdown",
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "# Blackjack Coach Pro Demo - Correction Action Plan" in out
        assert "## Action checklist" in out

    def test_export_output(self, capsys, tmp_path):
        repeat_dir = self._seed(tmp_path)
        out_file = tmp_path / "correction_plan.md"
        capsys.readouterr()
        exit_code = cli.main([
            "correction-plan", "--repeat-dir", str(repeat_dir),
            "--export", "--output", str(out_file),
        ])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out_file.exists()
        assert "Saved correction plan" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"



class TestCliWeb:
    """v2.0.0 local Web Coach UI launch instructions."""

    def test_web_shows_instructions(self, capsys):
        exit_code = cli.main(["web"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Local Web Coach UI" in out
        assert 'pip install -e ".[web]"' in out

    def test_web_mentions_streamlit_run(self, capsys):
        exit_code = cli.main(["web"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "streamlit run web/streamlit_app.py" in out

    def test_version_prints_2_3_0(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 2.3.0"
