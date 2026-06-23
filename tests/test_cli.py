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
