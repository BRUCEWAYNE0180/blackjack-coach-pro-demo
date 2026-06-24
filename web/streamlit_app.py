"""Local Streamlit Web Coach UI for Blackjack Coach Pro Demo (v2.1.0).

A local, browser-based wrapper around the existing engine. Run it with:

    python -m pip install -e ".[web]"
    python -m streamlit run web/streamlit_app.py

This UI is a thin presentation layer over :mod:`app.web_adapter`. It never
changes the strategy recommendation, the correct answers, or the Hi-Lo math, and
it never runs external commands or opens network connections. It is for local
practice / training / learning only - no real betting, no casino connectivity,
and no money handling.

v2.1.0 adds **card buttons** (A, 2-10, J, Q, K) for comfortable player-hand and
dealer-upcard entry, one-click quick examples, clear / reset controls, a
polished colour-coded recommendation, clearer warnings, and a mobile-friendly
layout. A manual text-entry mode is kept for power users. All of this is
presentation only; the engine and CLI are unchanged.
"""

from __future__ import annotations

import streamlit as st

from app import __version__
from app.rules import DEFAULT_PROFILE, PROFILES
from app.web_adapter import (
    EDUCATIONAL_NOTE,
    WEB_CARD_RANKS,
    WEB_QUICK_EXAMPLES,
    WebCoachInput,
    action_visual,
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

# How many card buttons to place per row. Keeping this modest keeps the buttons
# comfortably tappable on a phone-sized screen (mobile-friendly).
_BUTTONS_PER_ROW = 7


# --- Session state helpers (button callbacks) -----------------------------

def _init_state() -> None:
    """Initialise the session state used by the card buttons."""
    st.session_state.setdefault("player_cards", [])
    st.session_state.setdefault("dealer_upcard", None)


def _add_player_card(rank: str) -> None:
    st.session_state.player_cards.append(rank)


def _undo_player_card() -> None:
    if st.session_state.player_cards:
        st.session_state.player_cards.pop()


def _clear_player_cards() -> None:
    st.session_state.player_cards = []


def _set_dealer_upcard(rank: str) -> None:
    st.session_state.dealer_upcard = rank


def _clear_dealer_upcard() -> None:
    st.session_state.dealer_upcard = None


def _reset_all() -> None:
    st.session_state.player_cards = []
    st.session_state.dealer_upcard = None


def _load_example(player: tuple[str, ...], dealer: str) -> None:
    st.session_state.player_cards = list(player)
    st.session_state.dealer_upcard = dealer


# --- Rendering helpers -----------------------------------------------------

def _render_chip(label: str, color: str = "#37474f") -> str:
    """Return HTML for a small rounded card chip (display only)."""
    return (
        f"<span style='display:inline-block;margin:2px 4px;padding:4px 12px;"
        f"border-radius:14px;background:{color};color:white;font-weight:600;"
        f"font-size:16px;'>{label}</span>"
    )


def _render_rank_buttons(prefix: str, on_click) -> None:
    """Render the rank buttons (A, 2-10, J, Q, K) in mobile-friendly rows."""
    ranks = list(WEB_CARD_RANKS)
    for start in range(0, len(ranks), _BUTTONS_PER_ROW):
        row = ranks[start:start + _BUTTONS_PER_ROW]
        columns = st.columns(len(row))
        for column, rank in zip(columns, row):
            column.button(
                rank,
                key=f"{prefix}_{rank}",
                on_click=on_click,
                args=(rank,),
                use_container_width=True,
            )


def _render_card_picker() -> None:
    """Render the player-hand and dealer-upcard card pickers."""
    st.markdown("#### Your hand")
    st.caption("Tap cards to add them to your hand.")
    _render_rank_buttons("player", _add_player_card)

    player_cards = st.session_state.player_cards
    if player_cards:
        chips = "".join(_render_chip(rank) for rank in player_cards)
        st.markdown(f"**Selected:** {chips}", unsafe_allow_html=True)
    else:
        st.markdown("**Selected:** _no cards yet_")

    undo_col, clear_col = st.columns(2)
    undo_col.button(
        "Undo last card", on_click=_undo_player_card,
        use_container_width=True, disabled=not player_cards)
    clear_col.button(
        "Clear hand", on_click=_clear_player_cards,
        use_container_width=True, disabled=not player_cards)

    st.markdown("#### Dealer upcard")
    st.caption("Tap one card for the dealer's upcard.")
    _render_rank_buttons("dealer", _set_dealer_upcard)

    dealer_upcard = st.session_state.dealer_upcard
    if dealer_upcard:
        st.markdown(
            f"**Dealer shows:** {_render_chip(dealer_upcard, '#b71c1c')}",
            unsafe_allow_html=True)
    else:
        st.markdown("**Dealer shows:** _not set_")
    st.button(
        "Clear dealer", on_click=_clear_dealer_upcard,
        use_container_width=True, disabled=not dealer_upcard)


def _render_quick_examples() -> None:
    """Render one-click quick-example buttons."""
    st.markdown("#### Quick examples")
    st.caption("Load a sample hand with one tap.")
    examples = list(WEB_QUICK_EXAMPLES)
    for start in range(0, len(examples), 2):
        row = examples[start:start + 2]
        columns = st.columns(len(row))
        for column, example in zip(columns, row):
            column.button(
                example["label"],
                key=f"example_{example['label']}",
                on_click=_load_example,
                args=(tuple(example["player"]), example["dealer"]),
                use_container_width=True,
            )


def _render_recommendation_banner(output) -> None:
    """Render the polished, colour-coded recommended-action banner."""
    visual = action_visual(output.final_action)
    st.markdown(
        f"<div style='padding:18px;border-radius:12px;background:{visual['color']};"
        f"color:white;text-align:center;margin-bottom:8px;'>"
        f"<div style='font-size:14px;letter-spacing:1px;opacity:0.85;'>"
        f"RECOMMENDED ACTION</div>"
        f"<div style='font-size:34px;font-weight:800;margin-top:4px;'>"
        f"{visual['action']}</div>"
        f"<div style='font-size:15px;margin-top:6px;opacity:0.95;'>"
        f"{visual['description']}</div></div>",
        unsafe_allow_html=True,
    )
    st.caption(format_web_action(output.final_action))


def _render_output(output) -> None:
    """Render the coach output in the main area."""
    _render_recommendation_banner(output)

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


def _render_sidebar() -> dict:
    """Render the sidebar controls and return the collected options."""
    st.sidebar.header("Settings")
    input_mode = st.sidebar.radio(
        "Input mode", ("Card buttons", "Manual text"), index=0,
        help="Use tappable card buttons (default) or type cards manually.")
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
        "input_mode": input_mode,
        "profile_key": profile_key,
        "true_count": true_count,
        "show_odds": show_odds,
        "composition_aware": composition_aware,
        "seen_cards": seen_cards,
        "allow_double": allow_double,
        "allow_surrender": allow_surrender,
        "allow_split": allow_split,
    }


def _collect_inputs(input_mode: str) -> tuple[str, str]:
    """Return ``(player_cards_str, dealer_upcard_str)`` for the chosen mode."""
    if input_mode == "Manual text":
        player_cards = st.text_input(
            "Player cards", value="A,7",
            help="Comma-separated, e.g. A,7 or A\u2660,7\u2665")
        dealer_upcard = st.text_input(
            "Dealer upcard", value="9", help="e.g. 9 or 9\u2666")
        return player_cards, dealer_upcard

    _render_card_picker()
    st.markdown("---")
    _render_quick_examples()
    player_cards = ",".join(st.session_state.player_cards)
    dealer_upcard = st.session_state.dealer_upcard or ""
    return player_cards, dealer_upcard


def main() -> None:
    """Render the local Web Coach UI."""
    st.set_page_config(
        page_title="Blackjack Coach Pro Demo", page_icon="\u2660",
        layout="centered")
    _init_state()

    st.title("Blackjack Coach Pro Demo")
    st.markdown("### Local Web Coach UI")
    st.caption(f"Version {__version__} - {EDUCATIONAL_NOTE}")

    options = _render_sidebar()
    input_mode = options["input_mode"]

    st.markdown("Pick your hand and the dealer's upcard, then ask the coach.")
    player_cards, dealer_upcard = _collect_inputs(input_mode)

    st.markdown("---")
    decide_col, reset_col = st.columns([2, 1])
    evaluate_clicked = decide_col.button(
        "Get Coach Decision", type="primary", use_container_width=True)
    reset_col.button(
        "Reset all", on_click=_reset_all, use_container_width=True)

    # In button mode the result is shown live once the hand is complete, so it
    # persists while you keep adding cards. In manual mode it waits for the
    # button. Either way the warnings below are clear about what is missing.
    auto_ready = (
        input_mode == "Card buttons"
        and len(st.session_state.player_cards) >= 2
        and bool(st.session_state.dealer_upcard)
    )

    if evaluate_clicked or auto_ready:
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
            # validate_web_cards raises clear, user-facing messages (e.g.
            # "Enter at least two player cards" / "Enter the dealer upcard").
            st.warning(f"Cannot give a decision yet: {exc}")
        else:
            _render_output(output)
    else:
        st.info(
            "Add at least two player cards and the dealer's upcard, then press "
            "**Get Coach Decision**.")

    st.markdown("---")
    st.markdown("### Practice tools (run these in your terminal)")
    st.caption(
        "These are reminders only - the web UI never runs commands for you.")
    for command in _PRACTICE_COMMANDS:
        st.code(command, language="bash")


if __name__ == "__main__":  # pragma: no cover
    main()
