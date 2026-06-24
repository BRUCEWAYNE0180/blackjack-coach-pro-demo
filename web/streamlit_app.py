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

v2.2.0 adds a **Round result** section after the recommendation: record the
player's and dealer's final cards, the action actually taken, and the WIN /
LOSS / PUSH outcome, then see a decision review that keeps **decision quality**
(did it follow the coach?) separate from the **round outcome** - a correct play
can still lose. The dealer's final cards are used only here and never change the
recommendation, which still depends solely on the player cards and dealer
upcard.

v2.3.0 adds a **Practice table (demo)** mode: the app deals its own local,
simulated cards (it never reads cards from a camera, screen, or real casino),
freezes the coach recommendation, lets the player act (HIT / STAND / DOUBLE /
SURRENDER; SPLIT is auto-played), plays the dealer out automatically per the
profile, computes WIN / LOSS / PUSH, and auto-saves a decision review to a
session history. Local / simulated / educational only - no real money, no
bankroll.

v2.4.0 adds a **learning review** to the practice table: every round gets an
outcome-aware explanation and a conclusion category, weak spots are tracked, a
learning dashboard summarises follow-rate / mistakes / correct-but-lost spots /
repeated situations, mistakes get "next time" advice, and repeated mistakes
suggest drills. Decision quality is always kept separate from the round outcome
- a correct decision that loses is never counted as a mistake.
"""

from __future__ import annotations

import streamlit as st

from app import __version__, practice_review, practice_table
from app.rules import DEFAULT_PROFILE, PROFILES
from app.web_adapter import (
    DOUBLE_PLAY_NOTE,
    EDUCATIONAL_NOTE,
    WEB_ACTIONS,
    WEB_CARD_RANKS,
    WEB_OUTCOMES,
    WEB_QUICK_EXAMPLES,
    WebCoachInput,
    WebRoundInput,
    action_visual,
    build_web_coach_output,
    build_web_round_review,
    double_round_card_warning,
    format_web_action,
    suggest_web_round_outcome,
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
    # v2.2.0 round-result tracker state.
    st.session_state.setdefault("round_player_cards", [])
    st.session_state.setdefault("round_dealer_cards", [])
    st.session_state.setdefault("round_history", [])
    # The coach decision frozen at the initial (two-card) decision point, used
    # by the round review so it never drifts with the final/grown cards.
    st.session_state.setdefault("coach_decision", None)
    # v2.3.0 practice-table (demo game) state.
    st.session_state.setdefault("table_state", None)
    st.session_state.setdefault("table_history", [])


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
    # Clear the round-result *inputs* too (the saved history is kept; it has a
    # dedicated "Clear round history" control).
    st.session_state.round_player_cards = []
    st.session_state.round_dealer_cards = []
    st.session_state.coach_decision = None


def _load_example(player: tuple[str, ...], dealer: str) -> None:
    st.session_state.player_cards = list(player)
    st.session_state.dealer_upcard = dealer


# --- Round-result callbacks (v2.2.0) --------------------------------------

def _add_round_player_card(rank: str) -> None:
    st.session_state.round_player_cards.append(rank)


def _undo_round_player_card() -> None:
    if st.session_state.round_player_cards:
        st.session_state.round_player_cards.pop()


def _clear_round_player_cards() -> None:
    st.session_state.round_player_cards = []


def _add_round_dealer_card(rank: str) -> None:
    st.session_state.round_dealer_cards.append(rank)


def _undo_round_dealer_card() -> None:
    if st.session_state.round_dealer_cards:
        st.session_state.round_dealer_cards.pop()


def _clear_round_dealer_cards() -> None:
    st.session_state.round_dealer_cards = []


def _copy_initial_into_round(player_str: str, dealer_str: str) -> None:
    """Pre-fill the round final-card pickers from the initial hand / upcard."""
    st.session_state.round_player_cards = [
        c.strip() for c in player_str.split(",") if c.strip()]
    st.session_state.round_dealer_cards = (
        [dealer_str.strip()] if dealer_str.strip() else [])


def _clear_round_history() -> None:
    st.session_state.round_history = []


# --- Practice-table callbacks (v2.3.0) ------------------------------------

def _table_deal(profile_key: str) -> None:
    """Deal a new demo round, continuing the current shoe when possible."""
    previous = st.session_state.table_state
    shoe = previous.shoe if previous is not None else None
    st.session_state.table_state = practice_table.start_round(
        profile_key, shoe=shoe)


def _table_new_shoe(profile_key: str) -> None:
    """Shuffle a fresh shoe and deal a new demo round."""
    st.session_state.table_state = practice_table.start_round(
        profile_key, shoe=None)


def _table_action(action: str) -> None:
    """Apply a player action; auto-record the round to history when it ends."""
    state = st.session_state.table_state
    if state is None or state.phase != practice_table.PHASE_PLAYER:
        return
    try:
        practice_table.apply_action(state, action)
    except ValueError:
        return
    if state.is_round_over and not state.recorded:
        record = practice_table.build_round_record(state)
        st.session_state.table_history.append(
            practice_review.build_round_learning(record))
        state.recorded = True


def _clear_table_history() -> None:
    st.session_state.table_history = []


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
        if action == "DOUBLE":
            st.info(DOUBLE_PLAY_NOTE)
        st.caption(format_web_action(output.final_action))
        return

    color = _ACTION_COLOR.get(action, "gray")
    with st.container(border=True):
        st.caption("RECOMMENDED ACTION")
        st.markdown(f"## :{color}[{action}]")
        st.write(visual["description"])
    if action == "DOUBLE":
        # Clarify how a double resolves (a common point of confusion).
        st.info(DOUBLE_PLAY_NOTE)
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


# --- Round-result rendering (v2.2.0) --------------------------------------

# Native colours for the round outcome badge (display only).
_OUTCOME_COLOR = {"WIN": "green", "LOSS": "red", "PUSH": "blue"}


def _render_decision_review(review, initial_player: str, initial_dealer: str) -> None:
    """Render the decision review, keeping decision quality vs outcome apart.

    The ``coach_recommended_action`` comes from the **frozen initial decision**
    (computed on the initial two-card hand vs the dealer upcard) and is never
    recomputed from the final / grown cards.
    """
    with st.container(border=True):
        st.markdown("#### Decision review")
        st.markdown(f"- **Initial player cards:** {initial_player or '(n/a)'}")
        st.markdown(f"- **Dealer upcard:** {initial_dealer or '(n/a)'}")
        st.markdown(
            f"- **Coach recommended action:** {review.coach_recommended_action}")
        st.markdown(f"- **Player action taken:** {review.action_taken}")
        player_final = " ".join(review.player_final_cards) or "(n/a)"
        if review.player_busted:
            player_final += f" (total {review.player_total}, bust)"
        else:
            player_final += f" (total {review.player_total})"
        st.markdown(f"- **Player final cards:** {player_final}")
        dealer_final = " ".join(review.dealer_final_cards) or "(n/a)"
        if review.dealer_busted:
            dealer_final += f" (total {review.dealer_total}, bust)"
        else:
            dealer_final += f" (total {review.dealer_total})"
        st.markdown(f"- **Dealer final cards:** {dealer_final}")
        decision_color = "green" if review.followed_coach else "orange"
        review_word = "correct" if review.followed_coach else "different from coach"
        st.markdown(
            f"- **Decision review:** :{decision_color}[{review.decision_label}] "
            f"({review_word})")
        outcome_color = _OUTCOME_COLOR.get(review.outcome, "gray")
        st.markdown(
            f"- **Outcome:** :{outcome_color}[{review.outcome_label}]")
        st.caption(review.note)


def _round_history_row(review, initial_player: str, initial_dealer: str) -> dict:
    """Build a compact, display-only history row from a review.

    Keeps the initial decision hand and the final hand as separate columns so
    the table never implies the recommendation was derived from the final cards.
    """
    return {
        "Initial": f"{initial_player or '?'} vs {initial_dealer or '?'}",
        "Coach": review.coach_recommended_action,
        "Action taken": review.action_taken,
        "Followed coach": "yes" if review.followed_coach else "no",
        "Player final": " ".join(review.player_final_cards),
        "Dealer final": " ".join(review.dealer_final_cards),
        "Outcome": review.outcome,
    }


def _render_round_history() -> None:
    """Render this session's saved round history and a small summary."""
    history = st.session_state.round_history
    if not history:
        return
    st.markdown("#### Round history (this session)")
    wins = sum(1 for r in history if r["Outcome"] == "WIN")
    losses = sum(1 for r in history if r["Outcome"] == "LOSS")
    pushes = sum(1 for r in history if r["Outcome"] == "PUSH")
    followed = sum(1 for r in history if r["Followed coach"] == "yes")
    followed_but_lost = sum(
        1 for r in history
        if r["Followed coach"] == "yes" and r["Outcome"] == "LOSS")
    st.caption(
        f"{len(history)} round(s) - {wins}W / {losses}L / {pushes}P - "
        f"followed coach {followed}/{len(history)} "
        f"(incl. {followed_but_lost} correct decision(s) that still lost)")
    # Show most recent first; st.table is static so it reconciles cleanly.
    st.table(list(reversed(history)))
    st.button(
        "Clear round history", key="round_clear_history",
        on_click=_clear_round_history, use_container_width=True)


def _capture_coach_decision(player_str: str, dealer_str: str, options: dict) -> None:
    """Freeze the coach decision at the initial (two-card) decision point.

    The round review must use the recommendation the coach gave for the
    *initial* hand vs the dealer *upcard* - not whatever the main hand becomes
    if the player keeps hitting (e.g. A,7 -> A,7,K), and never anything derived
    from the final cards. We therefore compute the recommendation on the first
    two player cards and cache it, re-computing only when that initial decision
    (first two cards, upcard, profile, true count) actually changes.
    """
    cards = [c.strip() for c in player_str.split(",") if c.strip()]
    dealer = dealer_str.strip()
    if len(cards) < 2 or not dealer:
        return
    initial_two = cards[:2]
    signature = (
        tuple(initial_two), dealer, options["profile_key"], options["true_count"])
    previous = st.session_state.get("coach_decision")
    if previous and previous.get("signature") == signature:
        return
    try:
        decision_output = build_web_coach_output(WebCoachInput(
            player_cards=",".join(initial_two),
            dealer_upcard=dealer,
            profile_key=options["profile_key"],
            true_count=options["true_count"],
        ))
    except (ValueError, KeyError):
        return
    st.session_state.coach_decision = {
        "signature": signature,
        "initial_player": ",".join(initial_two),
        "dealer_upcard": dealer,
        "coach_action": decision_output.final_action,
    }


def _render_round_result(profile_key: str) -> None:
    """Render the 'Round result' section shown after the recommendation.

    Uses the **frozen** initial coach decision (see :func:`_capture_coach_decision`)
    so the review reflects the recommendation given for the initial hand vs the
    dealer upcard. The dealer's final cards and the player's final cards are
    recorded here only and never change that recommendation.
    """
    decision = st.session_state.get("coach_decision")
    if not decision:
        return
    coach_action = decision["coach_action"]
    initial_player = decision["initial_player"]
    initial_dealer = decision["dealer_upcard"]

    st.markdown("---")
    st.markdown("### Round result")
    st.caption(
        "Record how this round finished. The dealer's other cards and the "
        "final hands are used only here - they never change the recommendation "
        "above. A correct decision can still lose, so the decision review is "
        "kept separate from the outcome.")

    st.markdown(
        f"**Frozen initial decision:** {initial_player or '?'} vs dealer "
        f"{initial_dealer or '?'} - coach recommended **{coach_action}**")
    st.caption(
        "This is the coach's recommendation for the initial two-card hand; it "
        "does not change when you enter the final cards below.")

    st.button(
        "Copy initial hand into final cards", key="round_copy_initial",
        on_click=_copy_initial_into_round, args=(initial_player, initial_dealer),
        use_container_width=True)

    st.markdown("**Player final cards**")
    _render_rank_buttons("round_player", _add_round_player_card)
    round_player = st.session_state.round_player_cards
    if round_player:
        st.markdown(f"Selected: {_card_badges(round_player)}")
    else:
        st.markdown("Selected: _no cards yet_")
    p_undo, p_clear = st.columns(2)
    p_undo.button("Undo player card", key="round_player_undo",
                  on_click=_undo_round_player_card,
                  use_container_width=True, disabled=not round_player)
    p_clear.button("Clear player final", key="round_player_clear",
                   on_click=_clear_round_player_cards,
                   use_container_width=True, disabled=not round_player)

    st.markdown("**Dealer final cards**")
    _render_rank_buttons("round_dealer", _add_round_dealer_card)
    round_dealer = st.session_state.round_dealer_cards
    if round_dealer:
        st.markdown(f"Selected: {_card_badges(round_dealer)}")
    else:
        st.markdown("Selected: _no cards yet_")
    d_undo, d_clear = st.columns(2)
    d_undo.button("Undo dealer card", key="round_dealer_undo",
                  on_click=_undo_round_dealer_card,
                  use_container_width=True, disabled=not round_dealer)
    d_clear.button("Clear dealer final", key="round_dealer_clear",
                   on_click=_clear_round_dealer_cards,
                   use_container_width=True, disabled=not round_dealer)

    player_final_str = ",".join(round_player)
    dealer_final_str = ",".join(round_dealer)

    # Action taken defaults to the (frozen) coach's recommended action.
    action_index = (
        list(WEB_ACTIONS).index(coach_action)
        if coach_action in WEB_ACTIONS else 0
    )
    action_taken = st.radio(
        "Action taken", WEB_ACTIONS, index=action_index,
        key="round_action_taken", horizontal=True)

    # Clarify the one-card double rule and flag final hands that don't match it.
    if action_taken == "DOUBLE":
        st.caption(DOUBLE_PLAY_NOTE)
    double_warning = double_round_card_warning(
        action_taken, initial_player, player_final_str)
    if double_warning:
        st.warning(double_warning)

    suggested = suggest_web_round_outcome(
        player_final_str, dealer_final_str, action_taken)
    if suggested is not None:
        st.caption(f"Suggested from the final cards: {suggested}")
    outcome_index = (
        list(WEB_OUTCOMES).index(suggested)
        if suggested in WEB_OUTCOMES else 0
    )
    outcome = st.radio(
        "Round outcome", WEB_OUTCOMES, index=outcome_index,
        key="round_outcome", horizontal=True)

    save_clicked = st.button(
        "Save round result", key="round_save", type="primary",
        use_container_width=True)

    # The review uses the FROZEN coach action - it never recomputes the
    # recommendation from the final / grown cards.
    review = None
    try:
        review = build_web_round_review(WebRoundInput(
            coach_recommended_action=coach_action,
            action_taken=action_taken,
            player_final_cards=player_final_str,
            dealer_final_cards=dealer_final_str,
            outcome=outcome,
        ))
    except (ValueError, KeyError) as exc:
        st.info(f"Add the final cards to record this round: {exc}")

    if save_clicked:
        if review is None:
            st.warning(
                "Add at least two player final cards and one dealer final "
                "card before saving.")
        else:
            st.session_state.round_history.append(
                _round_history_row(review, initial_player, initial_dealer))
            st.success("Round result saved to this session's history.")

    if review is not None:
        _render_decision_review(review, initial_player, initial_dealer)

    _render_round_history()


# --- Practice-table rendering (v2.3.0) ------------------------------------

def _render_table_history() -> None:
    """Render this session's learning review: dashboard, drills, and history."""
    learnings = st.session_state.table_history
    if not learnings:
        return
    dashboard = practice_review.build_learning_dashboard(learnings)

    st.markdown("#### Learning dashboard")
    st.caption(
        "Decision quality is tracked separately from the round outcome - a "
        "correct decision that loses is never counted as a mistake.")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Rounds", dashboard.total_rounds)
    col_b.metric("Followed coach", f"{dashboard.followed_coach_pct:.0f}%")
    col_c.metric("Mistakes", dashboard.mistakes)
    col_d, col_e = st.columns(2)
    col_d.metric("Correct but lost", dashboard.correct_but_lost)
    col_e.metric("Different but won", dashboard.different_but_won)

    if dashboard.most_common_missed_spots:
        st.markdown("**Most common missed spots (mistakes):**")
        for spot, count in dashboard.most_common_missed_spots:
            st.markdown(f"- {spot} - {count}x")
    if dashboard.most_common_losing_correct_spots:
        st.markdown("**Correct decisions that still lost (variance, not errors):**")
        for spot, count in dashboard.most_common_losing_correct_spots:
            st.markdown(f"- {spot} - {count}x")
    if dashboard.most_repeated_situations:
        st.markdown("**Most repeated situations:**")
        for spot, count in dashboard.most_repeated_situations:
            st.markdown(f"- {spot} - {count}x")
    if dashboard.drill_suggestions:
        st.markdown("**Suggested drills (repeated mistakes):**")
        for drill in dashboard.drill_suggestions:
            st.markdown(f"- {drill}")

    st.markdown("#### Session history")
    rows = [practice_review.learning_row(entry) for entry in reversed(learnings)]
    st.table(rows)
    st.button(
        "Clear session history", key="table_clear_history",
        on_click=_clear_table_history, use_container_width=True)


def _render_table_round_result(state) -> None:
    """Render a finished demo round: outcome, decision review, conclusion."""
    record = practice_table.build_round_record(state)
    learning = practice_review.build_round_learning(record)
    outcome_color = _OUTCOME_COLOR.get(record.outcome, "gray")
    with st.container(border=True):
        st.caption("ROUND RESULT")
        st.markdown(f"## :{outcome_color}[{record.outcome}]")
        st.write(record.conclusion)

    st.markdown("#### Decision review")
    st.markdown(
        f"- **Initial hand:** {record.initial_hand} vs dealer "
        f"{record.dealer_upcard} ({learning.hand_type})")
    st.markdown(f"- **Coach recommended action:** {record.coach_action}")
    st.markdown(f"- **Player action taken:** {record.action_taken}")
    st.markdown(f"- **Player final cards:** {record.player_final}")
    st.markdown(f"- **Dealer final cards:** {record.dealer_final}")
    decision_color = "green" if record.followed_coach else "orange"
    review_word = "correct" if record.followed_coach else "different from coach"
    st.markdown(
        f"- **Decision review:** :{decision_color}[{record.decision_label}] "
        f"({review_word})")
    st.markdown(
        f"- **Conclusion:** {learning.conclusion_category.replace('_', ' ')}")
    st.info(learning.explanation)
    if learning.next_time_advice:
        st.warning(learning.next_time_advice)
    if record.decision_steps:
        st.markdown("**Action sequence:**")
        for index, step in enumerate(record.decision_steps, start=1):
            st.markdown(
                f"{index}. Hand {step['hand']} ({step['total']}) - "
                f"coach {step['coach']}, you {step['action']}")
    st.caption(record.note)


def _render_practice_table(profile_key: str) -> None:
    """Render the local demo blackjack table (deal, play, auto-resolve)."""
    st.markdown("### Practice table (demo)")
    st.caption(practice_table.EDUCATIONAL_NOTE)

    deal_col, shoe_col = st.columns(2)
    deal_col.button(
        "Start demo round / Deal", key="table_deal", type="primary",
        on_click=_table_deal, args=(profile_key,), use_container_width=True)
    shoe_col.button(
        "Shuffle new shoe", key="table_new_shoe",
        on_click=_table_new_shoe, args=(profile_key,), use_container_width=True)

    state = st.session_state.table_state
    if state is None:
        st.info("Press **Start demo round / Deal** to deal a local hand.")
        _render_table_history()
        return

    # Player hand.
    st.markdown(
        f"**Your hand:** {_card_badges(state.player_cards)} "
        f"- total {practice_table.describe_total(state.player_cards)}")

    # Dealer hand: only the upcard is shown until the hand is resolved.
    if state.dealer_revealed:
        st.markdown(
            f"**Dealer:** {_card_badges(state.dealer_cards)} "
            f"- total {practice_table.describe_total(state.dealer_cards)}")
    else:
        st.markdown(
            f"**Dealer shows:** :red-background[{state.dealer_upcard}] "
            f"+ hidden card")

    # Frozen coach recommendation for the initial hand.
    st.caption(
        f"Initial recommendation (frozen for review): "
        f"the coach said {state.coach_action} on "
        f"{','.join(state.initial_player_cards)} vs {state.dealer_upcard}.")

    if state.phase == practice_table.PHASE_PLAYER:
        # Live recommendation for the *current* hand (recalculated after each
        # HIT). HIT never ends the turn.
        current = state.current_coach_action or state.coach_action
        current_color = _ACTION_COLOR.get(current, "gray")
        st.markdown(f"**Current coach recommendation:** :{current_color}[{current}]")
        if state.current_coach_reason:
            st.caption(state.current_coach_reason)
        actions = practice_table.legal_actions(state)
        if "DOUBLE" in actions:
            st.caption(DOUBLE_PLAY_NOTE)
        if "SPLIT" in actions:
            st.caption(
                "Splitting plays both hands automatically in the demo "
                "(re-splitting is out of scope).")
        columns = st.columns(len(actions))
        for column, act in zip(columns, actions):
            column.button(
                act, key=f"table_act_{act}", on_click=_table_action,
                args=(act,), use_container_width=True)
        st.caption(
            "HIT draws one card and you keep playing; the recommendation "
            "updates. STAND / DOUBLE / SURRENDER end your turn and the dealer "
            "plays automatically.")
    else:
        _render_table_round_result(state)
        st.button(
            "Deal next round", key="table_next", type="primary",
            on_click=_table_deal, args=(profile_key,), use_container_width=True)

    _render_table_history()


def _render_sidebar() -> dict:
    """Render the sidebar controls and return the collected options."""
    st.sidebar.header("Settings")
    mode = st.sidebar.radio(
        "Mode", ("Coach", "Practice table (demo)"), index=0,
        help="Coach: get a recommendation for a hand you enter. "
             "Practice table: play a full local demo round.")
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
        "mode": mode,
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

    if options["mode"] == "Practice table (demo)":
        st.markdown(
            "Play a full local demo round: the app deals its own cards, the "
            "coach recommends, you act, and the dealer plays out automatically.")
        _render_practice_table(options["profile_key"])
        return

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
                _capture_coach_decision(player_cards, dealer_upcard, options)
                _render_round_result(options["profile_key"])
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
