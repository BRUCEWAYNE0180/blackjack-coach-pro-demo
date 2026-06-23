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
