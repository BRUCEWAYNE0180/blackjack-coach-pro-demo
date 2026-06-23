"""Tests for app.formatting (terminal formatting helpers)."""

from app.formatting import (
    format_cards,
    format_header,
    format_kv,
    format_list,
    format_percentage,
    format_result_status,
    format_section,
    format_warning,
)


class TestFormatHeader:
    def test_contains_title_and_separator(self):
        out = format_header("Basic Strategy")
        assert "Basic Strategy" in out
        # A separator line of '=' is present.
        assert "===" in out
        lines = out.splitlines()
        assert len(lines) == 2
        assert set(lines[1]) == {"="}


class TestFormatKv:
    def test_formats_label_and_value(self):
        out = format_kv("Action", "HIT")
        assert "Action" in out
        assert "HIT" in out
        assert ":" in out

    def test_label_is_padded_to_width(self):
        out = format_kv("X", "y", width=10)
        # Label padded so the colon aligns at the configured width.
        assert out.startswith("X")
        assert out == "X         : y"


class TestFormatPercentage:
    def test_basic(self):
        assert format_percentage(0.85) == "85.0%"

    def test_zero_and_full(self):
        assert format_percentage(0.0) == "0.0%"
        assert format_percentage(1.0) == "100.0%"


class TestFormatResultStatus:
    def test_correct(self):
        out = format_result_status(True)
        assert "CORRECT" in out
        assert "INCORRECT" not in out

    def test_incorrect(self):
        assert "INCORRECT" in format_result_status(False)


class TestFormatCards:
    def test_basic(self):
        assert format_cards(["A", "7"]) == "A, 7"

    def test_single(self):
        assert format_cards(["10"]) == "10"


class TestMiscFormatters:
    def test_section(self):
        assert format_section("Notes") == "-- Notes --"

    def test_list_with_items(self):
        out = format_list(["a", "b"])
        assert "- a" in out
        assert "- b" in out

    def test_list_empty(self):
        assert format_list([]) == "  (none)"

    def test_warning(self):
        assert format_warning("careful") == "! careful"
