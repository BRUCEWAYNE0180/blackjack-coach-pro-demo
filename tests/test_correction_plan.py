"""Tests for the correction action plan (v1.29.0)."""

import dataclasses

from app.correction_plan import (
    ACTION_COLLECT_MORE,
    ACTION_FOCUSED_REVIEW,
    ACTION_MAINTENANCE,
    ACTION_URGENT_REPEAT,
    CorrectionActionPlan,
    CorrectionPlanItem,
    build_correction_action_plan,
    build_recommended_command,
    classify_plan_action_type,
    export_correction_plan,
    render_correction_plan,
    render_correction_plan_markdown,
)
from app.repeat_pack import build_repeat_pack
from app.repeat_pack_history import (
    build_repeat_pack_completion_record,
    save_repeat_pack_completion_record,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _seed(tmp_path, *, profile=PROFILE, repeats=3,
          corrected=("hard_16_vs_10",), still_missed=("pair_8_vs_6",)):
    repeat_dir = tmp_path / "rp"
    pack = build_repeat_pack(
        profile_key=profile, pack_dir=tmp_path / "none",
        drill_dir=tmp_path / "dr", count=4)
    for _ in range(repeats):
        rec = build_repeat_pack_completion_record(
            pack, corrected_spot_ids=list(corrected),
            still_missed_spot_ids=list(still_missed))
        rec = dataclasses.replace(rec, profile_key=profile)
        save_repeat_pack_completion_record(rec, repeat_dir)
    return repeat_dir


class TestClassify:
    def test_persistent_miss(self):
        assert classify_plan_action_type("PERSISTENT_MISS") == ACTION_URGENT_REPEAT

    def test_improving(self):
        assert classify_plan_action_type("IMPROVING") == ACTION_FOCUSED_REVIEW

    def test_new(self):
        assert classify_plan_action_type("NEW") == ACTION_COLLECT_MORE

    def test_corrected(self):
        assert classify_plan_action_type("CORRECTED") == ACTION_MAINTENANCE


class TestBuildPlan:
    def test_no_data(self, tmp_path):
        plan = build_correction_action_plan(repeat_dir=tmp_path / "none")
        assert isinstance(plan, CorrectionActionPlan)
        assert plan.total_items == 0
        assert "No correction history yet" in plan.plan_note

    def test_persistent_creates_urgent(self, tmp_path):
        plan = build_correction_action_plan(repeat_dir=_seed(tmp_path))
        assert plan.urgent_items >= 1
        assert any(i.action_type == ACTION_URGENT_REPEAT for i in plan.items)

    def test_corrected_creates_maintenance(self, tmp_path):
        plan = build_correction_action_plan(repeat_dir=_seed(tmp_path))
        assert plan.maintenance_items >= 1
        assert any(i.action_type == ACTION_MAINTENANCE for i in plan.items)

    def test_profile_filter(self, tmp_path):
        repeat_dir = _seed(tmp_path, profile=PROFILE)
        plan = build_correction_action_plan(
            repeat_dir=repeat_dir, profile_key="SIX_DECK_S17_DAS_LS")
        assert plan.total_items == 0

    def test_respects_limit(self, tmp_path):
        repeat_dir = _seed(tmp_path)
        plan = build_correction_action_plan(repeat_dir=repeat_dir, limit=0)
        assert plan.total_items == 0

    def test_focus_urgent(self, tmp_path):
        plan = build_correction_action_plan(
            repeat_dir=_seed(tmp_path), focus="urgent")
        assert plan.items
        assert all(i.status == "PERSISTENT_MISS" for i in plan.items)

    def test_focus_maintenance(self, tmp_path):
        plan = build_correction_action_plan(
            repeat_dir=_seed(tmp_path), focus="maintenance")
        assert plan.items
        assert all(i.status == "CORRECTED" for i in plan.items)


class TestRecommendedCommand:
    def test_includes_profile(self):
        item = CorrectionPlanItem(
            item_id="x", spot_id="s", profile_key=PROFILE,
            status="PERSISTENT_MISS", priority=1,
            action_type=ACTION_URGENT_REPEAT, recommended_command="",
            reason="", expected_focus="")
        command = build_recommended_command(item)
        assert f"--profile {PROFILE}" in command
        assert command.startswith("blackjack-coach")

    def test_no_profile(self):
        item = CorrectionPlanItem(
            item_id="x", spot_id="s", profile_key=None,
            status="CORRECTED", priority=4,
            action_type=ACTION_MAINTENANCE, recommended_command="",
            reason="", expected_focus="")
        command = build_recommended_command(item)
        assert "--profile" not in command


class TestRenderers:
    def test_text_has_header(self, tmp_path):
        plan = build_correction_action_plan(repeat_dir=_seed(tmp_path))
        assert "=== Correction Action Plan ===" in render_correction_plan(plan)

    def test_markdown_checklist(self, tmp_path):
        plan = build_correction_action_plan(repeat_dir=_seed(tmp_path))
        md = render_correction_plan_markdown(plan)
        assert "## Action checklist" in md
        assert "- [ ]" in md


class TestExport:
    def test_export_saves_file(self, tmp_path):
        plan = build_correction_action_plan(repeat_dir=_seed(tmp_path))
        out = tmp_path / "plan.md"
        export = export_correction_plan(plan, output_path=out)
        assert export.output_path == str(out)
        assert out.exists()
        assert "Correction Action Plan" in out.read_text(encoding="utf-8")


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        plan = build_correction_action_plan(repeat_dir=_seed(tmp_path))
        field_names = {f.name for f in dataclasses.fields(plan)}
        for forbidden in FORBIDDEN:
            assert forbidden not in field_names
        for item in plan.items:
            item_fields = {f.name for f in dataclasses.fields(item)}
            for forbidden in FORBIDDEN:
                assert forbidden not in item_fields

    def test_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        build_correction_action_plan(repeat_dir=_seed(tmp_path))
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
