"""Static checks for the local Streamlit Web Coach UI (v2.1.0).

These read the source as text and never import Streamlit, so they run without
the optional web extra installed.
"""

from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "web" / "streamlit_app.py"


def _source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


class TestStreamlitAppExists:
    def test_file_exists(self):
        assert APP_PATH.is_file()


class TestStreamlitAppContent:
    def test_has_title(self):
        assert "Blackjack Coach Pro Demo" in _source()

    def test_has_local_web_coach_ui(self):
        assert "Local Web Coach UI" in _source()

    def test_has_get_coach_decision_button(self):
        assert "Get Coach Decision" in _source()

    def test_has_educational_notice(self):
        source = _source().lower()
        assert "educational" in source or "local practice" in source

    def test_uses_web_adapter(self):
        assert "web_adapter" in _source()


class TestStreamlitAppV21Features:
    """v2.1.0 card buttons, quick examples, clear/reset, polished output."""

    def test_uses_card_rank_buttons(self):
        source = _source()
        assert "WEB_CARD_RANKS" in source
        assert "_render_rank_buttons" in source

    def test_has_quick_examples(self):
        source = _source()
        assert "WEB_QUICK_EXAMPLES" in source
        assert "Quick examples" in source

    def test_has_clear_and_reset_controls(self):
        source = _source()
        assert "Clear hand" in source
        assert "Clear dealer" in source
        assert "Reset all" in source

    def test_keeps_manual_text_mode(self):
        source = _source()
        assert "Manual text" in source
        assert "Player cards" in source
        assert "Dealer upcard" in source

    def test_uses_action_visual_for_polished_output(self):
        assert "action_visual" in _source()

    def test_flags_disabled_recommended_action(self):
        # BUG 1 fix: a disabled recommended action is shown as unavailable,
        # not as a normal coloured recommendation.
        source = _source()
        assert "RECOMMENDED ACTION UNAVAILABLE" in source
        assert "recommended_available" in source

    def test_reset_clears_manual_inputs(self):
        # BUG 2 fix: Reset all clears manual text, seen cards, and true count.
        source = _source()
        for key in ("manual_player", "manual_dealer", "seen_cards",
                    "true_count_value"):
            assert key in source

    def test_player_and_dealer_pickers(self):
        source = _source()
        assert "Your hand" in source
        assert "dealer upcard" in source.lower()


class TestStreamlitAppSafety:
    def test_no_subprocess(self):
        assert "subprocess" not in _source()

    def test_no_os_system(self):
        assert "os.system" not in _source()

    def test_no_http_calls(self):
        source = _source().lower()
        assert "requests" not in source
        assert "http://" not in source.replace("http://localhost", "")
        assert "urllib" not in source

    def test_no_tokens_or_secrets(self):
        source = _source().lower()
        for forbidden in ("token", "secret", "password", "api_key", "apikey"):
            assert forbidden not in source

    def test_no_unsafe_allow_html(self):
        # Raw HTML injection via unsafe_allow_html caused the dynamic-DOM
        # "removeChild" frontend error; the UI must use native components only.
        assert "unsafe_allow_html=True" not in _source()

    def test_no_streamlit_rerun(self):
        # Avoid forcing reruns, which can also trigger unstable re-rendering.
        assert "st.rerun(" not in _source()
        assert "experimental_rerun" not in _source()

    def test_all_buttons_have_unique_keys(self):
        source = _source()
        # Every Streamlit button call in the app passes an explicit key= so the
        # frontend can reconcile widgets stably across reruns.
        button_calls = source.count(".button(")
        key_args = source.count("key=")
        assert button_calls >= 6
        assert key_args >= button_calls
