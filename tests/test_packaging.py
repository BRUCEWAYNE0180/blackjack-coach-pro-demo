"""Tests for packaging / release invariants."""

import pytest

import app
from app import cli


class TestVersion:
    def test_version_is_1_14_0(self):
        assert app.__version__ == "1.14.0"


class TestCliBackwardCompatibility:
    """Release polish must not change existing CLI behaviour."""

    def test_strategy_default_command(self, capsys):
        assert cli.main(["--cards", "A,7", "--dealer", "9"]) == 0
        out = capsys.readouterr().out
        assert "=== Basic Strategy ===" in out
        assert "HIT" in out

    def test_count_command(self, capsys):
        assert cli.main(
            ["count", "--cards", "2,5,K,A,9", "--decks-remaining", "5"]
        ) == 0
        out = capsys.readouterr().out
        assert "=== Hi-Lo Count ===" in out
        assert "Running count" in out

    def test_simulate_command(self, capsys):
        assert cli.main(["simulate", "--decks", "6", "--seed", "42"]) == 0
        assert "Recommendation" in capsys.readouterr().out

    def test_play_command(self, capsys):
        assert cli.main(["play", "--decks", "6", "--seed", "42"]) == 0
        assert "Outcome" in capsys.readouterr().out

    def test_quiz_command(self, capsys):
        assert cli.main(["quiz", "--seed", "42", "--answer", "H"]) == 0
        assert "Correct action: STAND" in capsys.readouterr().out

    def test_count_quiz_command(self, capsys):
        assert cli.main(
            ["count-quiz", "--cards", "2,5,K,A,9", "--answer", "0"]
        ) == 0
        assert "[ CORRECT ]" in capsys.readouterr().out

    def test_quiz_session_command(self, capsys):
        assert cli.main([
            "quiz-session", "--questions", "10", "--seed", "42",
            "--answers", "H,S,D,H,R,S,H,D,P,S",
        ]) == 0
        assert "Total questions" in capsys.readouterr().out

    def test_count_session_command(self, capsys):
        assert cli.main([
            "count-session", "--batches", "2,5,K|A,9,3|10,6,2",
            "--answers", "1,-1,1",
        ]) == 0
        assert "Total questions" in capsys.readouterr().out

    def test_main_is_callable_entry_point(self):
        # The console-script entry point (blackjack-coach) calls app.cli:main.
        assert callable(cli.main)


class TestCliVersionFlag:
    def test_version_prints_name_and_version(self, capsys):
        exit_code = cli.main(["--version"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 1.14.0"

    def test_short_version_flag(self, capsys):
        exit_code = cli.main(["-V"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert out.strip() == "blackjack-coach 1.14.0"

    def test_usage_uses_console_command_name(self, capsys):
        # A usage error (no required args) must reference the installed command
        # name, not the "python -m app.cli" module invocation.
        with pytest.raises(SystemExit):
            cli.main([])
        err = capsys.readouterr().err
        assert "blackjack-coach" in err
        assert "python -m app.cli" not in err

    def test_help_uses_console_command_name(self, capsys):
        with pytest.raises(SystemExit):
            cli.main(["--help"])
        out = capsys.readouterr().out
        assert "blackjack-coach" in out
