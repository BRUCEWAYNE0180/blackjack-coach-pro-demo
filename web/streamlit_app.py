"""Local Streamlit Web Coach UI for Blackjack Coach Pro Demo (v2.0.0).

A local, browser-based wrapper around the existing engine. Run it with:

    python -m pip install -e ".[web]"
    python -m streamlit run web/streamlit_app.py

This UI is a thin presentation layer over :mod:`app.web_adapter`. It never
changes the strategy recommendation, the correct answers, or the Hi-Lo math, and
it never runs external commands or opens network connections. It is for local
practice / training / learning only - no real betting, no casino connectivity,
and no money handling.
"""

from __future__ import annotations

import streamlit as st

from app import __version__
from app.rules import DEFAULT_PROFILE, PROFILES
from app.web_adapter import (
    EDUCATIONAL_NOTE,
    WebCoachInput,
    build_web_coach_output,
    format_web_action,
)

# Commands the user can run themselves in a terminal (shown as text only - the
# UI never executes them).
_PRACTICE_COMMANDS = [
    "blackjack-coach drill",
    "blackjack-coach practice-pack",
    "blackjack-coach repeat-pack",
    "blackjack-coach correction-plan",
]


def _render_sidebar() -> dict:
    """Render the sidebar controls and return the collected options."""
    st.sidebar.header("Settings")
    profile_key = st.sidebar.selectbox(
        "Rule profile", sorted(PROFILES), index=sorted(PROFILES).index(
            DEFAULT_PROFILE.key) if DEFAULT_PROFILE.key in PROFILES else 0)
    use_true_count = st.sidebar.checkbox("Use true count", value=False)
    true_count = None
    if use_true_count:
        true_count = st.sidebar.number_input(
            "True count", min_value=-20.0, max_value=20.0, value=0.0, step=0.5)
    show_odds = st.sidebar.checkbox("Show odds / EV", value=False)
    composition_aware = st.sidebar.checkbox("Composition-aware odds", value=False)
    seen_cards = st.sidebar.text_input(
        "Seen cards (optional)", value="",
        help="Other exposed/removed cards, e.g. 2\u2663,5\u2666")

    st.sidebar.subheader("Available actions")
    allow_double = st.sidebar.checkbox("Allow double", value=True)
    allow_surrender = st.sidebar.checkbox("Allow surrender", value=True)
    allow_split = st.sidebar.checkbox("Allow split", value=True)

    st.sidebar.info(EDUCATIONAL_NOTE)
    return {
        "profile_key": profile_key,
        "true_count": true_count,
        "show_odds": show_odds,
        "composition_aware": composition_aware,
        "seen_cards": seen_cards,
        "allow_double": allow_double,
        "allow_surrender": allow_surrender,
        "allow_split": allow_split,
    }


def _render_output(output) -> None:
    """Render the coach output in the main area."""
    st.subheader("Recommended action")
    st.markdown(f"## {output.final_action}")
    st.caption(format_web_action(output.final_action))

    st.markdown(f"**Why:** {output.explanation}")
    st.markdown(f"**Hand:** {output.hand_summary}")
    st.markdown(f"**Legal actions:** {', '.join(output.legal_actions) or '(none)'}")

    if output.count_adjusted_action is not None:
        st.markdown("### Count-aware advisory")
        st.markdown(f"- Basic action: {output.basic_action}")
        st.markdown(f"- Count-adjusted action: {output.count_adjusted_action}")
        st.markdown(f"- Final recommended action: {output.final_action}")

    if output.odds_summary is not None:
        st.markdown("### Odds (approximate, advisory)")
        for key, value in output.odds_summary.items():
            st.markdown(f"- {key.replace('_', ' ').title()}: {value}")

    if output.ev_summary is not None:
        st.markdown("### EV (advisory only)")
        st.markdown(f"- Best EV action: {output.ev_summary['best_ev_action']}")
        st.markdown(
            f"- Agrees with recommendation: "
            f"{output.ev_summary['agrees_with_recommendation']}")
        st.json(output.ev_summary["ev_by_action"])

    if output.warnings:
        st.markdown("### Warnings")
        for warning in output.warnings:
            st.warning(warning)


def main() -> None:
    """Render the local Web Coach UI."""
    st.set_page_config(page_title="Blackjack Coach Pro Demo", page_icon="\u2660")
    st.title("Blackjack Coach Pro Demo")
    st.markdown("### Local Web Coach UI")
    st.caption(f"Version {__version__} - {EDUCATIONAL_NOTE}")

    options = _render_sidebar()

    st.markdown("Enter your hand and the dealer's upcard, then ask the coach.")
    player_cards = st.text_input(
        "Player cards", value="A,7",
        help="Comma-separated, e.g. A,7 or A\u2660,7\u2665")
    dealer_upcard = st.text_input(
        "Dealer upcard", value="9", help="e.g. 9 or 9\u2666")

    if st.button("Get Coach Decision"):
        web_input = WebCoachInput(
            player_cards=player_cards,
            dealer_upcard=dealer_upcard,
            profile_key=options["profile_key"],
            true_count=options["true_count"],
            show_odds=options["show_odds"],
            composition_aware=options["composition_aware"],
            seen_cards=options["seen_cards"] or None,
            allow_double=options["allow_double"],
            allow_surrender=options["allow_surrender"],
            allow_split=options["allow_split"],
        )
        try:
            output = build_web_coach_output(web_input)
        except (ValueError, KeyError) as exc:
            st.error(f"Error: {exc}")
        else:
            _render_output(output)

    st.markdown("---")
    st.markdown("### Practice tools (run these in your terminal)")
    st.caption(
        "These are reminders only - the web UI never runs commands for you.")
    for command in _PRACTICE_COMMANDS:
        st.code(command, language="bash")


if __name__ == "__main__":  # pragma: no cover
    main()
