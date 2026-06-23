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
- `app/simulator.py` — Local training simulator: deals hands from the shoe,
  plays a full hand against the dealer (H17/S17), plays basic pair splits, and
  resolves the outcome. Ties together the evaluator, strategy engine, and
  counting (`SimulatedHand`, `deal_initial_hand`, `simulate_training_hand`,
  `HandOutcome`, `PlayedHand`, `play_dealer_hand`, `resolve_outcome`,
  `play_training_hand`, `SplitSubHand`, `PlayedSplitHand`, `can_split_hand`,
  `split_initial_hand`, `play_split_subhand`).
- `app/quiz.py` — Quiz mode and scored sessions: generate/grade basic-strategy
  questions, normalise user actions, and run multi-question strategy/count
  sessions (`QuizQuestion`, `QuizResult`, `CountQuizResult`,
  `QuizSessionResult`, `generate_strategy_question`, `grade_strategy_answer`,
  `normalize_user_action`, `build_strategy_questions`, `run_strategy_session`,
  `run_count_session`).
- `app/cli.py` — Terminal trainer (`python -m app.cli` or the installed
  `blackjack-coach` command, plus `count`, `simulate`, `play`, `quiz`,
  `count-quiz`, `quiz-session`, and `count-session` subcommands).
- `pyproject.toml` — Modern packaging: metadata, the `blackjack-coach` console
  script, the `dev` extra, and `pytest`/`ruff` configuration.
- `.github/workflows/ci.yml` — CI: lint + tests on Python 3.9-3.12.
- `tests/` — Behavioural tests for the evaluator, engine, explanations,
  counting, shoe, simulator, quiz, CLI, and packaging.

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

### v0.4 — Local Shoe Simulator (done)

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

### v0.5 — Complete Hand Simulator (done)

Delivered (educational / simulated practice only):

- **`HandOutcome`** enum — `PLAYER_WIN`, `DEALER_WIN`, `PUSH`, `PLAYER_BUST`,
  `DEALER_BUST`, `SURRENDER`.
- **`PlayedHand`** dataclass — player cards, dealer cards, actions taken, final
  outcome (or `None` when a split was indicated), running count before/after,
  true count after, the recommendations consulted, plus note and warnings.
- **`play_dealer_hand(shoe, dealer_cards, profile)`** — the dealer draws to a
  hard 17+, and on soft 17 hits under **H17** but stands under **S17**.
- **`resolve_outcome(player_cards, dealer_cards, surrendered=False)`** — maps a
  finished hand to a `HandOutcome` (player bust loses first; naturals are
  treated simply as 21, with no payout modelling since no money is involved).
- **`play_training_hand(decks=6, seed=None, profile=DEFAULT_PROFILE)`** — plays
  one full hand using a simplified single-hand model:
  - `SURRENDER` ends the hand; `DOUBLE` takes exactly one card then stands;
    `HIT` draws until strategy says stand or the hand busts; `STAND` ends the
    turn.
  - The dealer reveals its hole card and plays only if the player did not
    surrender, bust, or hit a split.
  - The running count is updated with **visible** cards as they appear; the
    dealer hole card counts once revealed.
- **CLI `play` subcommand:**

  ```bash
  python -m app.cli play --decks 6 --seed 42
  ```

  Prints the starting cards, dealer upcard, actions taken, final player and
  dealer cards, outcome, running count before/after, true count after, and an
  educational note. The strategy, `count`, and `simulate` commands are
  unchanged.
- **Tests** — H17 hits soft 17 / S17 stands soft 17, each `resolve_outcome`
  result (player/dealer bust, push, player/dealer win, surrender),
  `play_training_hand` returning a `PlayedHand`, and the CLI `play` flow; all
  earlier tests remain green.

**Dealer H17 / S17**

- The dealer's only decision is whether to draw. It always draws below 17 and
  stands on hard 17+. On soft 17 the behaviour follows the profile.

**Limitations / out of scope for v0.5**

- **Pair-splitting is not played out.** When basic strategy indicates SPLIT,
  the hand is recorded with a `SPLIT_NOT_IMPLEMENTED` marker and ends with a
  clear note; no money and no split rounds are simulated.
- No betting spread, no Kelly bet sizing, no Illustrious 18, no insurance index.
- No web app.
- Never for real tables: no casino connectivity, no real-money betting, no
  camera/video, no screen scraping, and no promise of winnings.

### v0.6 — Split Hand Simulator (done)

Delivered (educational / simulated practice only):

- **`can_split_hand(player_cards)`** — true for a two-card pair (including any
  two ten-valued cards, e.g. K,Q).
- **`split_initial_hand(shoe, player_cards)`** — divides a pair into two hands
  and deals one new (visible) card to each.
- **`SplitSubHand`** dataclass — one split hand's `cards`, `actions_taken`,
  `final_outcome`, `recommendations`, and `is_complete`.
- **`play_split_subhand(shoe, subhand_cards, dealer_upcard, profile,
  running_count)`** — plays one sub-hand: no surrender after a split; DOUBLE
  honours `profile.double_after_split` and takes one card then stands; HIT
  draws until stand or bust. If strategy would re-split, a
  `RESPLIT_NOT_IMPLEMENTED` marker is recorded and the hand is played as a
  normal total instead.
- **`PlayedSplitHand`** dataclass — the original pair, the dealer's final
  cards, the two `split_hands`, plus `actions_by_hand`, `outcomes_by_hand`,
  `recommendations_by_hand`, running count before/after, true count after,
  note, and warnings.
- **`play_training_hand`** now returns a `PlayedSplitHand` when the opening
  recommendation is SPLIT on a real pair: both sub-hands are played, the dealer
  reveals its hole card and plays **once**, and each sub-hand is resolved
  against the dealer's final hand. The running count is updated with visible
  cards as they appear.
- **CLI** — `python -m app.cli play` prints the split layout (original hand,
  both split hands with actions and outcomes, dealer final cards, counts, and
  warnings) when a split occurs.
- **Tests** — `can_split_hand` (8,8 and K,Q true; 10,9 false), split deal
  creating two hands and shrinking the shoe, `play_split_subhand` completeness,
  a split seed returning a `PlayedSplitHand` with two outcomes, the dealer
  playing once, and split-Aces / re-split warning paths; all earlier tests
  remain green.

**Limitations / out of scope for v0.6**

- **Re-splitting is not modelled** (a split hand that could split again is
  played as a normal total, with a warning).
- **Special split-Aces rules** (one card per Ace, no re-split) are not
  modelled; Aces are split but played normally, with a warning.
- No money, bankroll, betting units, or payout modelling. Double-after-split is
  honoured only insofar as `profile.double_after_split` allows a normal double.
- No betting spread, no Kelly, no Illustrious 18, no insurance index, no UI.
- Never for real tables: no casino connectivity, no real-money betting, no
  camera/video, no screen scraping, and no promise of winnings.

### v0.7 — Training Quiz Mode (done)

Delivered (educational practice only):

- **`app/quiz.py`**:
  - **`QuizQuestion`** dataclass — `player_cards`, `dealer_upcard`,
    `profile_key`, `correct_action`, `explanation`, `tags`.
  - **`QuizResult`** dataclass — `question`, `user_action`, `is_correct`,
    `correct_action`, `explanation`.
  - **`generate_strategy_question(seed=None, profile=DEFAULT_PROFILE)`** —
    builds a reproducible question (never a natural blackjack) using the
    strategy engine for the correct action and explanation.
  - **`grade_strategy_answer(question, user_action)`** — grades an answer.
  - **`normalize_user_action(raw_action)`** — accepts `H/S/D/P/R` and the full
    names (case-insensitive); rejects anything else.
- **CLI `quiz` subcommand** — `python -m app.cli quiz --seed 42 --answer H`
  prints the cards, dealer upcard, profile, your answer, the correct action, a
  Correct/Incorrect verdict, and an educational explanation. Without `--answer`
  it prompts interactively (`Your action? [H/S/D/P/R]:`).
- **CLI `count-quiz` subcommand** — `python -m app.cli count-quiz --cards
  2,5,K,A,9 --answer 0` checks the Hi-Lo running count and prints the cards,
  your answer, the correct running count, a Correct/Incorrect verdict, and an
  educational note.

**Strategy trainer / count trainer**

- The strategy trainer reuses the v0.1+ engine as the source of truth, so quiz
  answers always match the basic-strategy charts (including H17/S17).
- The count trainer reuses the v0.3 Hi-Lo tags, so the "correct" running count
  is the cumulative tag sum of the listed cards.

**Limitations / out of scope for v0.7**

- One question at a time (no scored sessions, streaks, or persistence yet).
- The strategy quiz grades the opening two-card decision only.
- No betting spread, no Kelly, no Illustrious 18, no insurance index, no web/UI.
- Never for real tables: no casino connectivity, no real-money betting, no
  camera/video, no screen scraping, and no promise of winnings.

### v0.8 — Scored Training Sessions (done)

Delivered (educational practice only):

- **`QuizSessionResult`** dataclass — `mode`, `total_questions`,
  `correct_answers`, `incorrect_answers`, `accuracy` (fraction 0.0-1.0),
  `results`, `weak_spots`, `note`.
- **`CountQuizResult`** dataclass — one graded count batch (`cards`,
  `user_answer`, `correct_count`, `is_correct`).
- **`build_strategy_questions(num_questions, seed, profile)`** — reproducible
  question list (each question uses `seed + index`).
- **`run_strategy_session(num_questions=10, seed=None, answers=None,
  profile=DEFAULT_PROFILE)`** — scores a strategy session; computes accuracy
  and derives **weak spots** from the tags/actions of missed questions.
- **`run_count_session(cards_batches, answers)`** — scores a running-count
  session over several batches; weak spots label the missed batches.
- **CLI `quiz-session`** — `python -m app.cli quiz-session --questions 10
  --seed 42 --answers H,S,D,...` prints totals, correct/incorrect, accuracy,
  weak spots, and a note. Without `--answers`, prompts per question
  (`Q1 Your action? [H/S/D/P/R]:`).
- **CLI `count-session`** — `python -m app.cli count-session --batches
  "2,5,K|A,9,3|10,6,2" --answers "1,-1,1"` prints the same summary for the
  running count. Without `--answers`, prompts per batch
  (`Q1 Running count?:`).

**Strategy session / count session / weak spots**

- Strategy sessions reuse the engine for the correct action of every question,
  so scores always match basic strategy (H17/S17).
- Weak spots aggregate the failed questions' tags (e.g. `hard`, `stand`) for
  strategy, and the missed batch labels for counting.

**Limitations / out of scope for v0.8**

- Sessions are in-memory only: no saving to files, no database, no login.
- Strategy questions grade the opening two-card decision only.
- No betting spread, no Kelly, no Illustrious 18, no insurance index, no
  web/UI.
- Never for real tables: no casino connectivity, no real-money betting, no
  camera/video, no screen scraping, and no promise of winnings.

### v0.9 — Professional Hardening (done)

Delivered (no new gameplay scope; tooling and quality only):

- **Packaging** — a `pyproject.toml` (setuptools build backend) declares the
  project metadata, `requires-python = ">=3.9"`, an empty runtime dependency
  list (standard library only), and a `dev` extra (`pytest`, `ruff`).
- **Console command** — a `blackjack-coach` entry point maps to
  `app.cli:main`, so all subcommands work as `blackjack-coach ...` once
  installed with `python -m pip install -e ".[dev]"`.
- **Continuous integration** — `.github/workflows/ci.yml` runs `ruff check
  app tests` and `python -m pytest` on Python 3.9, 3.10, 3.11, and 3.12 for
  every push to `main` and every pull request.
- **Quality gates** — documented in `PROJECT_RULES.md`: every PR must pass
  tests and lint, new features need tests, new functions must preserve the
  educational/simulated scope, and no secrets/`.env`/tokens/private files are
  ever committed.
- **Tooling config** — `[tool.pytest.ini_options]` and `[tool.ruff]`
  (line length, target version, and `E/F/W/I` lint rules) live in
  `pyproject.toml`; a convenience `requirements-dev.txt` installs `-e .[dev]`
  without duplicating version pins.
- **Tests** — assert `app.__version__ == "0.9.0"` and that every existing CLI
  subcommand still works (backward compatibility); all earlier tests remain
  green.

**Limitations / out of scope for v0.9**

- No new gameplay features (no betting spread, Kelly, Illustrious 18, insurance
  index, or web app).
- Still local/simulated only: no casino connectivity, no real-money betting or
  bankroll, no camera/video, no screen scraping, and no promise of winnings.

### v1.0.0 — Stable Release (current)

The first **stable** release. It is release polish only: no new blackjack
gameplay is added. v1.0.0 consolidates v0.1-v0.9 into a documented, packaged,
educational/local trainer.

Delivered:

- Version bumped to **1.0.0** in `app.__version__` and `pyproject.toml`, with a
  matching version test.
- **`CHANGELOG.md`** (a single stable 1.0.0 entry: Added / Changed / Quality /
  Safety), **`LICENSE`** (MIT), **`docs/RELEASE_NOTES_v1.0.0.md`**, and
  **`docs/COMMANDS.md`** (full command reference).
- **README** polished for a ~30-second understanding (what it is, install,
  tests, CLI, educational scope), with a v1.0.0 feature summary and a
  "Not financial / gambling advice" section.
- **`PROJECT_RULES.md`** gains **Release Rules** (tests pass, CI green, no
  secrets/sensitive data, no out-of-scope changes, mandatory release notes).

v1.0.0 is explicitly an **educational / local / simulated** release: no casino
connectivity, no real-money betting or bankroll, no camera/video, no screen
scraping, no betting spread, no Kelly, no Illustrious 18, no insurance index,
no web app, and no promise of winnings.

## Future Roadmap (post-1.0.0)

All future work stays educational and local unless explicitly decided
otherwise.

### v1.1 — Visual / Terminal Polish

- Nicer terminal output (tables/colour), clearer prompts, and quiz UX polish.

### v1.2 — Saved Local Session History

- Optionally persist practice-session results **locally** (opt-in), for
  progress tracking. No accounts, no cloud, no sensitive data.

### v1.3 — Advanced Deviations (educational only)

- Teach well-known count-based deviations (e.g. the Illustrious 18) as a
  **learning topic**, practiced only against the local simulator. Still no real
  betting, bankroll, or bet sizing.

### v2.0 — Possible Web UI (if decided later)

- A browser front end over the existing engine and simulator, only if and when
  decided. Subject to the same educational, no-real-money constraints.

## Out-of-Scope (All Versions)

Per `PROJECT_RULES.md`: no casino connectivity, no real-money betting or
automation, no casino camera/video capture, no guarantees of profit, and no
facilitation of cheating or illegal activity.
