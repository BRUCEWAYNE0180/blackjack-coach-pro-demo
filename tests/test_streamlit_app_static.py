"""Static checks for the local Streamlit Web Coach UI (v2.0.0).

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
