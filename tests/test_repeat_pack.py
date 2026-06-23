"""Tests for the repeat-pack generator for missed spots (v1.26.0)."""

import dataclasses

from app.practice_pack import build_practice_pack
from app.practice_pack_history import (
    build_practice_pack_completion_record,
    save_practice_pack_completion_record,
)
from app.repeat_pack import (
    SRC_MISSED,
    RepeatPack,
    build_repeat_pack,
    build_repeat_pack_item_from_spot,
    export_repeat_pack,
    render_repeat_pack,
    render_repeat_pack_markdown,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _gen_dirs(tmp_path):
    return dict(
        drill_dir=tmp_path / "dr", session_dir=tmp_path / "s",
        outcome_dir=tmp_path / "o", ev_dir=tmp_path / "e")


def _seed_missed(tmp_path, *, profile=PROFILE, missed_repeats=2):
    """Create completion records with missed spots; return pack_dir + ids."""
    pack_dir = tmp_path / "packs"
    pack = build_practice_pack(profile_key=profile, count=4, seed=1,
                               **_gen_dirs(tmp_path))
    ids = [i.spot_id for i in pack.items]
    # Record the first spot missed several times, the others mixed.
    for _ in range(missed_repeats):
        rec = build_practice_pack_completion_record(
            pack, correct_spot_ids=ids[1:2], missed_spot_ids=ids[0:1],
            skipped_spot_ids=ids[2:3])
        save_practice_pack_completion_record(rec, pack_dir)
    return pack_dir, ids


class TestBuildPack:
    def test_no_history_starter(self, tmp_path):
        pack = build_repeat_pack(
            pack_dir=tmp_path / "none", drill_dir=tmp_path / "dr", count=5)
        assert isinstance(pack, RepeatPack)
        assert pack.total_items > 0
        assert pack.fallback_items > 0
        assert "starter educational repeat pack" in pack.pack_note

    def test_respects_count(self, tmp_path):
        pack = build_repeat_pack(
            pack_dir=tmp_path / "none", drill_dir=tmp_path / "dr", count=3)
        assert pack.total_items == 3

    def test_seed_deterministic(self, tmp_path):
        pack_dir, _ = _seed_missed(tmp_path)
        a = build_repeat_pack(pack_dir=pack_dir, count=5, seed=42)
        b = build_repeat_pack(pack_dir=pack_dir, count=5, seed=42)
        assert [i.spot_id for i in a.items] == [i.spot_id for i in b.items]

    def test_prioritises_missed(self, tmp_path):
        pack_dir, ids = _seed_missed(tmp_path, missed_repeats=3)
        pack = build_repeat_pack(pack_dir=pack_dir, count=10)
        assert pack.items
        # The repeatedly-missed spot is first and has miss_count >= 3.
        assert pack.items[0].spot_id == ids[0]
        assert pack.items[0].miss_count >= 3

    def test_includes_skipped(self, tmp_path):
        pack_dir, ids = _seed_missed(tmp_path)
        pack = build_repeat_pack(pack_dir=pack_dir, count=10)
        sources = {i.source for i in pack.items}
        # The skipped spot (ids[2]) should surface as a skipped source.
        assert "skipped" in sources

    def test_profile_filter(self, tmp_path):
        pack_dir, _ = _seed_missed(tmp_path, profile=PROFILE)
        # A different profile has no matching completions -> starter pack.
        pack = build_repeat_pack(
            pack_dir=pack_dir, profile_key="SIX_DECK_S17_DAS_LS",
            drill_dir=tmp_path / "dr", count=5)
        assert pack.fallback_items > 0

    def test_no_duplicate_spot_ids(self, tmp_path):
        pack_dir, _ = _seed_missed(tmp_path)
        pack = build_repeat_pack(pack_dir=pack_dir, count=20)
        ids = [i.spot_id for i in pack.items]
        assert len(ids) == len(set(ids))

    def test_item_uses_engine_action(self, tmp_path):
        pack_dir, ids = _seed_missed(tmp_path)
        pack = build_repeat_pack(pack_dir=pack_dir, count=10)
        for item in pack.items:
            expected = recommend(
                list(item.player_cards), item.dealer_upcard,
                get_profile(item.profile_key)).action.value
            assert item.recommended_action == expected


class TestItemHelper:
    def test_build_item_from_spot(self):
        item = build_repeat_pack_item_from_spot(
            ["10", "6"], "10", get_profile(PROFILE), source=SRC_MISSED,
            miss_count=2)
        assert item.player_cards == ("10", "6")
        assert item.dealer_upcard == "10"
        assert item.miss_count == 2
        expected = recommend(["10", "6"], "10", get_profile(PROFILE)).action.value
        assert item.recommended_action == expected


class TestRenderers:
    def test_render_text(self, tmp_path):
        pack = build_repeat_pack(pack_dir=tmp_path / "none", count=4)
        assert "=== Repeat Pack ===" in render_repeat_pack(pack)

    def test_render_markdown_checklist(self, tmp_path):
        pack = build_repeat_pack(pack_dir=tmp_path / "none", count=4)
        md = render_repeat_pack_markdown(pack)
        assert "## Repeat checklist" in md
        assert "- [ ]" in md


class TestExport:
    def test_export_saves_file(self, tmp_path):
        pack = build_repeat_pack(pack_dir=tmp_path / "none", count=4)
        out = tmp_path / "repeat.md"
        export = export_repeat_pack(pack, output_path=out)
        assert export.output_path == str(out)
        assert out.exists()
        assert "Repeat Pack" in out.read_text(encoding="utf-8")


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        pack = build_repeat_pack(pack_dir=tmp_path / "none", count=5)
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
        build_repeat_pack(pack_dir=tmp_path / "none", count=5)
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
