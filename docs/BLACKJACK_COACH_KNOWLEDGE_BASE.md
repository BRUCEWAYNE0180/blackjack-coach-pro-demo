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
- `app/strategy_engine.py` — Basic-strategy tables and the `recommend()` API,
  returning an enriched `Recommendation` (action, insurance, reason,
  hand description, profile key, warnings).
- `app/explanations.py` — Short educational notes for each action and state
  (`HIT`, `STAND`, `DOUBLE`, `SPLIT`, `SURRENDER`, `BLACKJACK`, `BUST`,
  insurance-NO).
- `app/counting.py` — Hi-Lo counting trainer: tag values, running count, true
  count, and `CountingState` (educational / simulated practice only).
- `app/shoe.py` — Virtual multi-deck shoe: build, shuffle (seedable), draw,
  cards/decks remaining, penetration, and deck validation.
- `app/simulator.py` — Local training simulator: deals hands from the shoe and
  ties together the evaluator, strategy engine, and counting (`SimulatedHand`,
  `deal_initial_hand`, `simulate_training_hand`).
- `app/cli.py` — Terminal trainer (`python -m app.cli`, plus `count` and
  `simulate` subcommands).
- `tests/` — Behavioural tests for the evaluator, engine, explanations,
  counting, shoe, simulator, and CLI.

## Roadmap

### v0.1 — Basic Strategy Foundation (done)

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

### v0.2 — Explanations & CLI (done)

Delivered:

- **`app/explanations.py`** — concise, plain-language educational notes for
  every action and for the `BLACKJACK`, `BUST`, and insurance-NO states.
- **Enriched `Recommendation`** — now carries `action`, `take_insurance`,
  `reason` (action + educational note), `hand_description`, `profile_key`, and
  an optional `warnings` list.
- **Warnings** — surfaced when the dealer shows an Ace (insurance is always
  NO) and when the chart's preferred play (DOUBLE/SURRENDER/SPLIT) is not legal
  in the current spot, explaining the best legal fallback.
- **`app/cli.py`** — a simple terminal trainer:

  ```bash
  python -m app.cli --cards A,7 --dealer 9 --profile MULTI_DECK_H17_DAS_LS
  ```

  Prints the action, explanation, profile, and the insurance-NO advice when the
  dealer shows an Ace.
- **Tests** — explanation coverage (surrender, double, states), CLI behaviour
  (`A,7` vs `9`), and the insurance-NO notice on a dealer Ace; all v0.1 tests
  remain green.

Still **excluded** in v0.2: Hi-Lo counting, True Count, Illustrious 18,
simulator, web app, real-money/casino features, and any external data
(PDFs/screenshots/feeds).

Deferred to later versions: deeper expected-value / house-edge analysis and
per-profile edge comparisons.

### v0.3 — Hi-Lo Counting Trainer (done)

Delivered (educational / simulated practice only):

- **`app/counting.py`** — the Hi-Lo system:
  - **Tag values:** `2-6 = +1`, `7-9 = 0`, `10/J/Q/K/A = -1`
    (`hilo_value`).
  - **Running count:** cumulative sum of tags
    (`update_running_count`, `update_running_count_many`).
  - **True count:** running count divided by approximate decks remaining
    (`true_count`); raises a clear error when `decks_remaining <= 0`.
  - **`is_counting_allowed_context`** — guard reinforcing that counting is for
    local/simulated practice, never a real table.
  - **`counting_summary`** — a short, neutral educational interpretation of the
    count (no profit claims).
  - **`CountingState`** dataclass — `running_count`, `decks_remaining`,
    `true_count`, `cards_seen`, `note`, and `warnings`.
- **CLI `count` subcommand:**

  ```bash
  python -m app.cli count --cards 2,5,K,A,9 --decks-remaining 5
  ```

  Prints cards seen, running count, decks remaining, true count, and an
  educational note. The existing basic-strategy command is unchanged.
- **Tests** — tag values for every group, multi-card running counts, true-count
  division, the `decks_remaining <= 0` error, and the CLI `count` flow; all
  v0.1/v0.2 tests remain green.

**Definitions**

- **Running count:** the accumulated Hi-Lo tag total for all cards seen so far.
- **True count:** the running count normalised by decks remaining, giving a
  per-deck measure that is comparable across different shoe depths.

**Limitations / out of scope for v0.3**

- No betting spread, no Illustrious 18, no insurance index play, and no Kelly
  bet sizing yet.
- No simulator, no web app.
- Never for real tables: no casino connectivity, no real-money betting, no
  camera/video, and no promise of winnings. No external data
  (PDFs/screenshots/feeds).

Deferred to later versions: count-based deviations (Illustrious 18 / Fab 4),
insurance index, and bet sizing.

### v0.4 — Local Shoe Simulator (current)

Delivered (educational / simulated practice only):

- **`app/shoe.py`** — a virtual multi-deck shoe:
  - `build_shoe(decks=6)` — 52 cards per deck (e.g. 6 decks = 312 cards).
  - `shuffle_shoe(cards, seed=None)` — seedable, deterministic shuffle on a
    copy (original untouched).
  - `draw_card(shoe)` — draws one card and shrinks the shoe.
  - `cards_remaining(shoe)`, `decks_remaining(shoe)`,
    `penetration(shoe, original_size)`.
  - `validate_decks(decks)` — rejects non-positive / non-integer deck counts.
- **`app/simulator.py`** — a local trainer that ties the modules together:
  - **`SimulatedHand`** dataclass — player cards, dealer upcard, optional
    dealer hole card, running count before/after, true count after, the
    `recommendation`, plus an educational note and warnings.
  - `deal_initial_hand(shoe, running_count=0, decks=6)` — deals two player
    cards plus the dealer up and hole cards. Only the **visible** cards (player
    cards + upcard) update the running count; the face-down hole card is not
    counted.
  - `simulate_training_hand(decks=6, seed=None)` — builds and shuffles a fresh
    shoe and deals one training hand.
  - Integrates `app.hand_evaluator` (evaluation), `app.strategy_engine.recommend`
    (action), and `app.counting` (running/true count).
- **CLI `simulate` subcommand:**

  ```bash
  python -m app.cli simulate --decks 6 --seed 42
  ```

  Prints the player cards, dealer upcard, recommendation, running count before
  and after, true count after, and an educational note. The strategy and
  `count` commands are unchanged.
- **Tests** — shoe sizes (1 deck = 52, 6 decks = 312), `validate_decks`
  rejects `<= 0`, seeded shuffle determinism, `draw_card` shrinking the shoe,
  `deal_initial_hand` dealing two player cards + upcard, `simulate_training_hand`
  returning a recommendation, and the CLI `simulate` flow; all earlier tests
  remain green.

**Virtual shoe**

- The shoe is a plain list of rank tokens; suits are omitted because they do
  not affect strategy or Hi-Lo counting. A seedable shuffle gives reproducible
  practice sessions.

**Limitations / out of scope for v0.4**

- The simulator deals the initial hand and gives the opening recommendation; it
  does not yet play out full rounds, dealer draws, or bankroll.
- No betting spread, no Kelly bet sizing, no Illustrious 18, and no insurance
  index play yet.
- No web app.
- Never for real tables: no casino connectivity, no real-money betting, no
  camera/video, no screen scraping, and no promise of winnings. No external
  data (PDFs/screenshots/feeds).

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
