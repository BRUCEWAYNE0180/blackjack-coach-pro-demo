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
    """Initialise the session state used by the card buttons and manual inputs.

    Manual-text and sidebar inputs are given stable keys so that ``Reset all``
    can clear them too (see :func:`_reset_all`). Initialising here (instead of
    via widget ``value=``) avoids the "value set via Session State" warning.
    """
    st.session_state.setdefault("player_cards", [])
    st.session_state.setdefault("dealer_upcard", None)
    st.session_state.setdefault("manual_player", "A,7")
    st.session_state.setdefault("manual_dealer", "9")
    st.session_state.setdefault("seen_cards", "")
    st.session_state.setdefault("use_true_count", False)
    st.session_state.setdefault("true_count_value", 0.0)


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
    """Clear *everything*: button cards, manual text, seen cards, true count.

    Run as a button ``on_click`` callback, so writing to widget-keyed session
    state here is allowed and takes effect before the widgets are rebuilt. This
    also clears any stale result / warnings, since the result area recomputes
    from the (now empty) inputs on the next run.
    """
    st.session_state.player_cards = []
    st.session_state.dealer_upcard = None
    st.session_state.manual_player = ""
    st.session_state.manual_dealer = ""
    st.session_state.seen_cards = ""
    st.session_state.use_true_count = False
    st.session_state.true_count_value = 0.0


def _load_example(player: tuple[str, ...], dealer: str) -> None:
    st.session_state.player_cards = list(player)
    st.session_state.dealer_upcard = dealer


# --- Rendering helpers -----------------------------------------------------

# Native Streamlit colour names per action (used for stable colour-highlight
# markdown - no raw HTML, so React reconciliation stays sane between reruns).
# This is display-only and never changes the recommendation.
_ACTION_COLOR = {
    "HIT": "blue",
    "STAND": "green",
    "DOUBLE": "orange",
    "SPLIT": "violet",
    "SURRENDER": "red",
}


def _card_badges(cards) -> str:
    """Return native colour-highlight markdown for a list of card ranks.

    Uses Streamlit's built-in ``:colour-background[...]`` markdown directive
    (rendered by Streamlit, not via ``unsafe_allow_html``), which avoids the
    dynamic-DOM ``removeChild`` errors that raw HTML injection can trigger.
    """
    return " ".join(f":gray-background[{rank}]" for rank in cards)


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
        st.markdown(f"**Selected:** {_card_badges(player_cards)}")
    else:
        st.markdown("**Selected:** _no cards yet_")

    undo_col, clear_col = st.columns(2)
    undo_col.button(
        "Undo last card", key="undo_player", on_click=_undo_player_card,
        use_container_width=True, disabled=not player_cards)
    clear_col.button(
        "Clear hand", key="clear_player", on_click=_clear_player_cards,
        use_container_width=True, disabled=not player_cards)

    st.markdown("#### Dealer upcard")
    st.caption("Tap one card for the dealer's upcard.")
    _render_rank_buttons("dealer", _set_dealer_upcard)

    dealer_upcard = st.session_state.dealer_upcard
    if dealer_upcard:
        st.markdown(f"**Dealer shows:** :red-background[{dealer_upcard}]")
    else:
        st.markdown("**Dealer shows:** _not set_")
    st.button(
        "Clear dealer", key="clear_dealer", on_click=_clear_dealer_upcard,
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
    """Render the polished, colour-coded recommended-action banner.

    Built entirely from native Streamlit components (a bordered container plus
    colour-highlight markdown) - no ``unsafe_allow_html`` - so it renders
    without the dynamic-DOM ``removeChild`` error and stays display-only.

    If the recommended action is disabled by the user's "Available actions"
    toggles, it is shown clearly as *unavailable* (neutral, not as a normal
    coloured recommendation) so the UI never presents a disabled action as the
    main play. The engine recommendation itself is unchanged.
    """
    visual = action_visual(output.final_action)
    action = visual["action"]
    legal = ", ".join(output.legal_actions) or "(none)"

    if not output.recommended_available:
        with st.container(border=True):
            st.caption("RECOMMENDED ACTION UNAVAILABLE")
            st.markdown(f"## :gray[{action}]")
            st.markdown(f"**{action} is disabled**")
            st.write(
                f"Base strategy recommends {action}, but {action.lower()} is "
                f"disabled. Legal actions are {legal}.")
        st.caption(format_web_action(output.final_action))
        return

    color = _ACTION_COLOR.get(action, "gray")
    with st.container(border=True):
        st.caption("RECOMMENDED ACTION")
        st.markdown(f"## :{color}[{action}]")
        st.write(visual["description"])
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
    use_true_count = st.sidebar.checkbox("Use true count", key="use_true_count")
    true_count = None
    if use_true_count:
        true_count = st.sidebar.number_input(
            "True count", min_value=-20.0, max_value=20.0, step=0.5,
            key="true_count_value")
    show_odds = st.sidebar.checkbox("Show odds / EV", value=False)
    composition_aware = st.sidebar.checkbox("Composition-aware odds", value=False)
    seen_cards = st.sidebar.text_input(
        "Seen cards (optional)", key="seen_cards",
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
            "Player cards", key="manual_player",
            help="Comma-separated, e.g. A,7 or A\u2660,7\u2665")
        dealer_upcard = st.text_input(
            "Dealer upcard", key="manual_dealer", help="e.g. 9 or 9\u2666")
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
        "Get Coach Decision", key="get_decision", type="primary",
        use_container_width=True)
    reset_col.button(
        "Reset all", key="reset_all", on_click=_reset_all,
        use_container_width=True)

    # When the inputs are "ready" the result is shown live and recomputed on
    # every rerun, so it always reflects the *current* input - this is what
    # keeps warnings from going stale when the user fixes an invalid entry or
    # presses Reset all. Button mode waits for two cards before showing
    # anything (to avoid premature warnings); manual mode is ready once both
    # fields have text.
    if input_mode == "Manual text":
        ready = bool(player_cards.strip()) and bool(dealer_upcard.strip())
    else:
        ready = (
            len(st.session_state.player_cards) >= 2
            and bool(st.session_state.dealer_upcard)
        )

    # Render the result inside a single stable container so the DOM node at this
    # position is consistent across reruns (this, plus dropping unsafe_allow_html
    # and giving every widget a unique key, avoids the React removeChild error).
    result_area = st.container()
    with result_area:
        if evaluate_clicked or ready:
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
                "Add at least two player cards and the dealer's upcard, then "
                "press **Get Coach Decision**.")

    st.markdown("---")
    st.markdown("### Practice tools (run these in your terminal)")
    st.caption(
        "These are reminders only - the web UI never runs commands for you.")
    for command in _PRACTICE_COMMANDS:
        st.code(command, language="bash")


if __name__ == "__main__":  # pragma: no cover
    main()
