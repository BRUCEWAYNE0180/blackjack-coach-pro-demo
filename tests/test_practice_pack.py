"""Tests for the daily practice-pack generator (v1.24.0)."""

import dataclasses

from app.drill_generator import build_drill_spot_from_hand
from app.drill_history import DrillSessionRecord, save_drill_session_record
from app.practice_pack import (
    PracticePack,
    PracticePackItem,
    build_pack_item_from_drill_spot,
    build_pack_item_from_review_item,
    build_practice_pack,
    export_practice_pack,
    render_practice_pack,
    render_practice_pack_markdown,
)
from app.review_scheduler import build_review_queue
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _empty(tmp_path):
    return dict(
        drill_dir=tmp_path / "dr", session_dir=tmp_path / "s",
        outcome_dir=tmp_path / "o", ev_dir=tmp_path / "e")


def _save_drill_session(drill_dir, *, created_at, session_id, spot_id="s1",
                        is_correct=False, profile=PROFILE,
                        player_cards=("10", "6"), dealer="10"):
    record = DrillSessionRecord(
        session_id=session_id, created_at=created_at, profile_key=profile,
        focus="weak", total_drills=1, correct_count=1 if is_correct else 0,
        incorrect_count=0 if is_correct else 1,
        accuracy=1.0 if is_correct else 0.0,
        spot_results=[{
            "spot_id": spot_id, "profile_key": profile, "category": "hard_total",
            "player_cards": list(player_cards), "dealer_upcard": dealer,
            "recommended_action": "STAND",
            "user_answer": "STAND" if is_correct else "HIT",
            "is_correct": is_correct,
        }],
        weak_spots=[] if is_correct else [spot_id],
        mastered_spots=[spot_id] if is_correct else [],
        next_review_spots=[spot_id], note="", warnings=[])
    return save_drill_session_record(record, drill_dir)


class TestBuildPack:
    def test_no_history_starter_pack(self, tmp_path):
        pack = build_practice_pack(count=5, **_empty(tmp_path))
        assert isinstance(pack, PracticePack)
        assert pack.total_items > 0
        assert "starter educational practice pack" in pack.pack_note
        assert pack.warnings

    def test_respects_count(self, tmp_path):
        pack = build_practice_pack(count=3, **_empty(tmp_path))
        assert pack.total_items == 3
        assert len(pack.items) == 3

    def test_seed_is_deterministic(self, tmp_path):
        kw = _empty(tmp_path)
        a = build_practice_pack(count=5, seed=42, **kw)
        b = build_practice_pack(count=5, seed=42, **kw)
        assert [i.spot_id for i in a.items] == [i.spot_id for i in b.items]

    def test_no_duplicate_spot_ids(self, tmp_path):
        pack = build_practice_pack(count=20, **_empty(tmp_path))
        ids = [i.spot_id for i in pack.items]
        assert len(ids) == len(set(ids))

    def test_focus_due_prioritises_due_items(self, tmp_path):
        kw = _empty(tmp_path)
        # A weak spot practised long ago -> due now.
        _save_drill_session(kw["drill_dir"], created_at="2026-01-01T10:00:00",
                            session_id="a", spot_id="hard_16_vs_10")
        pack = build_practice_pack(
            focus="due", count=10, today="2026-12-31", **kw)
        assert pack.due_items >= 1
        # The first item should be a due-review item.
        assert pack.items[0].source == "due_review"

    def test_focus_pairs_prioritises_pairs(self, tmp_path):
        pack = build_practice_pack(focus="pairs", count=10, **_empty(tmp_path))
        assert pack.items
        assert all(i.category in ("pair", "split") for i in pack.items)


class TestItemConverters:
    def test_from_review_item(self, tmp_path):
        kw = _empty(tmp_path)
        _save_drill_session(kw["drill_dir"], created_at="2026-01-01T10:00:00",
                            session_id="a", spot_id="hard_16_vs_10")
        queue = build_review_queue(
            drill_dir=kw["drill_dir"], today="2026-12-31")
        assert queue.items
        item = build_pack_item_from_review_item(queue.items[0])
        assert isinstance(item, PracticePackItem)
        assert item.source == "due_review"
        # Recommended action comes from the engine.
        expected = recommend(["10", "6"], "10", get_profile(PROFILE)).action.value
        assert item.recommended_action == expected

    def test_from_drill_spot(self):
        spot = build_drill_spot_from_hand(["8", "8"], "6", get_profile(PROFILE))
        item = build_pack_item_from_drill_spot(spot)
        assert isinstance(item, PracticePackItem)
        assert item.player_cards == ("8", "8")
        assert item.recommended_action == spot.recommended_action


class TestRenderers:
    def test_render_text_has_header(self, tmp_path):
        pack = build_practice_pack(count=4, **_empty(tmp_path))
        text = render_practice_pack(pack)
        assert "=== Daily Practice Pack ===" in text
        assert "Total items" in text

    def test_render_markdown_has_checklist(self, tmp_path):
        pack = build_practice_pack(count=4, **_empty(tmp_path))
        md = render_practice_pack_markdown(pack)
        assert "## Practice checklist" in md
        assert "- [ ]" in md


class TestExport:
    def test_export_saves_file(self, tmp_path):
        pack = build_practice_pack(count=4, **_empty(tmp_path))
        out = tmp_path / "pack.md"
        export = export_practice_pack(pack, output_path=out)
        assert export.output_path == str(out)
        assert out.exists()
        assert "Daily Practice Pack" in out.read_text(encoding="utf-8")


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        pack = build_practice_pack(count=5, **_empty(tmp_path))
        field_names = {f.name for f in dataclasses.fields(pack)}
        for forbidden in FORBIDDEN:
            assert forbidden not in field_names
        for item in pack.items:
            item_fields = {f.name for f in dataclasses.fields(item)}
            for forbidden in FORBIDDEN:
                assert forbidden not in item_fields

    def test_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        build_practice_pack(count=5, **_empty(tmp_path))
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
