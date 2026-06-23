# Blackjack Coach — Knowledge Base & Roadmap

This is the central design document for Blackjack Coach Pro Demo. It captures
the domain knowledge the tool relies on and the planned evolution from v0.1
through v0.6.

> Educational/practice tool only. No casino connectivity, no real-money
> betting/automation, no casino camera/video, no promise of winnings.
> See `PROJECT_RULES.md`.

## Domain Glossary

- **Hard hand:** A hand with no ace, or where every ace must count as 1 to
  avoid busting.
- **Soft hand:** A hand with an ace counted as 11 (e.g. A-6 = "soft 17").
- **Pair:** Two cards of equal value, eligible to split.
- **H17 / S17:** Whether the dealer hits (H17) or stands (S17) on soft 17.
- **DAS:** Double After Split allowed.
- **Late Surrender (LS):** Forfeit half the bet after the dealer checks for
  blackjack.
- **Basic strategy:** The mathematically optimal play for each hand vs the
  dealer upcard, assuming no knowledge of unseen cards.
- **Running count / True count:** Card-counting measures (later versions).
- **Illustrious 18:** A well-known set of count-based strategy deviations.


## Architecture (current)

- `app/rules.py` — `RuleProfile` definitions and the profile registry.
- `app/hand_evaluator.py` — Normalises cards and classifies hands (hard/soft/
  pair), computing totals, blackjack, and bust.
- `app/strategy_engine.py` — Basic-strategy tables and the `recommend()` API.
- `tests/` — Behavioural tests for the evaluator and the engine.

## Roadmap

### v0.1 — Basic Strategy Foundation (current)

- `RuleProfile` model with two profiles: `MULTI_DECK_H17_DAS_LS` and
  `MULTI_DECK_S17_DAS_LS`.
- Hand evaluator for hard totals, soft totals, and pairs.
- Strategy engine returning `HIT`, `STAND`, `DOUBLE`, `SPLIT`, `SURRENDER`.
- Insurance recommendation: **always NO**.
- Fallbacks: double-if-allowed-else-hit/stand; surrender-if-allowed-else the
  underlying hit/stand/split action.
- Tests covering representative chart cells and H17/S17 differences.
- **Explicitly excluded:** Hi-Lo, True Count, Illustrious 18, simulator,
  web app.

### v0.2 — Math & Explanations

- Add expected-value / house-edge reasoning behind each recommendation.
- Surface a short "why" for each decision (e.g. dealer bust odds).
- Compare house edge across rule profiles.

### v0.3 — Card Counting (Hi-Lo) as a Learning Topic

- Implement the Hi-Lo running count and true-count conversion.
- Add the Illustrious 18 (and optionally Fab 4 surrenders) as count-based
  deviations layered on top of basic strategy.
- Strictly educational; practiced only against the built-in simulator.

### v0.4 — Simulator & Drills

- Local virtual-shoe Monte Carlo engine (no real money, no external feeds).
- Drill modes: random hands, weakest-cells focus, timed quizzes.
- Empirical validation of strategy EV and counting concepts.

### v0.5 — Visual / UI Layer

- Interactive strategy charts and quiz/flashcard UX.
- Progress tracking and accuracy stats per hand category.
- Groundwork for a web app front end.

### v0.6 — Web App & Polish

- Browser-based practice app over the existing engine and simulator.
- Profile selection, drill history, and shareable practice sessions.
- Accessibility, responsiveness, and documentation hardening.

## Out-of-Scope (All Versions)

Per `PROJECT_RULES.md`: no casino connectivity, no real-money betting or
automation, no casino camera/video capture, no guarantees of profit, and no
facilitation of cheating or illegal activity.
