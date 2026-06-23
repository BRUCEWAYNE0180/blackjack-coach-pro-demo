# Blackjack Coach — Knowledge Base & Roadmap

This is the central design document for Blackjack Coach Pro Demo, a
**professional blackjack coach** for local practice, demo money, video games,
recreational tournaments, and training. It captures the domain knowledge the
tool relies on and the project's evolution.

> Responsible scope: a coaching and practice tool, not a real-money gambling
> product (no casino connectivity, camera/video, or promise of winnings).
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

- `app/rules.py` — `RuleProfile` (with professional metadata) and the profile
  registry; 11 built-in profiles (single/double/four/six/eight deck) plus
  helpers (`list_rule_profiles`, `get_rule_profile`, `describe_rule_profile`,
  `normalize_profile_key`, `profile_supports_*`).
- `app/hand_evaluator.py` — Normalises cards and classifies hands (hard/soft/
  pair), computing totals, blackjack, and bust.
- `app/strategy_engine.py` — Basic-strategy tables and the `recommend()` API,
  returning an enriched `Recommendation` (action, insurance, reason,
  hand description, profile key, warnings).
- `app/explanations.py` — Short educational notes for each action and state
  (`HIT`, `STAND`, `DOUBLE`, `SPLIT`, `SURRENDER`, `BLACKJACK`, `BUST`,
  insurance-NO).
- `app/formatting.py` — Dependency-free terminal formatting helpers (headers,
  aligned key/value rows, result badges, percentages); presentation only.
- `app/cards.py` — Professional card rendering / parsing: `RenderedCard`, suit
  constants, `normalize_rank`/`normalize_suit`, `parse_card`/`parse_cards`,
  `cards_to_ranks`, `format_card`/`format_cards`, `strip_ansi`, and
  `assign_display_suits`. Visual / input layer only - always preserves plain
  ranks for the engine.
- `app/session_history.py` — Local JSON session history (summary only):
  `SessionRecord`, `HistorySummary`, save/load/list, and `summarize_history`.
- `app/outcome_history.py` — Local outcome / win-loss history (summary only):
  `OutcomeRecord`, `OutcomeSummary`, `build_outcome_record` (for `PlayedHand`
  and `PlayedSplitHand`), save/load/list (with limit / profile filters), and
  `summarize_outcomes`. No database, network, or cloud.
- `app/deviations.py` — Educational true-count deviation study (study-only):
  `DeviationRule`, `DeviationRecommendation`, `DEFAULT_DEVIATION_RULES`,
  `find_matching_deviation`, and `recommend_with_deviation` (wraps the engine
  without modifying it).
- `app/decision_diagnostics.py` — Decision intelligence: `DecisionDiagnostic`
  and `explain_decision_factors`, which break a recommended play into plain
  factors (hand shape, dealer strength, available options, rule context, and
  profile-aware split rules).
- `app/strategy_matrix.py` — Complete strategy-matrix audit: `StrategyCell`,
  `StrategyMatrix`, `MatrixAuditReport`, the generators
  (`generate_hard_total_matrix`, `generate_soft_total_matrix`,
  `generate_pair_matrix`, `generate_strategy_matrix`), plus
  `audit_strategy_matrix` and `format_strategy_matrix`. Builds 360-cell
  matrices (hard 5-21, soft 13-21, pairs vs dealer 2-10,A) by calling the engine
  and audits coverage (missing / fallback / unknown cells).
- `app/decision_audit.py` — Per-hand decision audit: `DecisionAudit`,
  `audit_decision`, `legal_actions_for_hand`, `detect_strategy_category`, and
  `detect_table_section`. Reports category, table section, raw vs recommended
  action, fallbacks, and legal actions for one hand.
- `app/guided_coach.py` — Guided coach mode: `CoachStep`, `GuidedCoachResult`,
  `build_coach_step`, `explain_next_best_action`, `build_guided_result`, and
  `play_guided_coach_hand`. The coach picks and explains each action; built on
  `decision_audit` and the simulator, reusing outcome records for labels.
- `app/probability_advisor.py` — Approximate probability & EV advisor:
  `PlayerBustEstimate`, `DealerOutcomeEstimate`, `ActionEVEstimate`,
  `ProbabilityAdvice`, plus `estimate_player_bust_probability`,
  `estimate_dealer_outcomes`, `estimate_action_ev`, and
  `build_probability_advice`. Approximate / advisory only; never overrides the
  recommendation and never changes the engine or counting math.
- `app/split_rules.py` — Profile-aware split rules: `SplitRuleDecision`,
  `is_pair_hand`, `is_ace_pair`, `can_split_initial_hand`, `can_resplit`,
  `can_hit_split_aces`, `can_double_after_split`, and `explain_split_rules`.
- `app/counting.py` — Hi-Lo counting trainer: tag values, running count, true
  count, and `CountingState` (educational / simulated practice only).
- `app/shoe.py` — Virtual multi-deck shoe: build, shuffle (seedable), draw,
  cards/decks remaining, penetration, and deck validation.
- `app/simulator.py` — Local training simulator: deals hands from the shoe,
  plays a full hand against the dealer (H17/S17), plays a full pair-split /
  re-split tree, and resolves the outcome. Ties together the evaluator,
  strategy engine, and counting (`SimulatedHand`, `deal_initial_hand`,
  `simulate_training_hand`, `HandOutcome`, `PlayedHand`, `play_dealer_hand`,
  `resolve_outcome`, `play_training_hand`, `SplitSubHand`, `PlayedSplitHand`,
  `can_split_hand`, `split_initial_hand`, `play_split_subhand`, and the v1.6.0
  re-split tree `_play_split_tree` / `_play_out_position` with the
  `RESPLIT_LIMIT_REACHED` marker).
- `app/quiz.py` — Quiz mode and scored sessions: generate/grade basic-strategy
  questions, normalise user actions, and run multi-question strategy/count
  sessions (`QuizQuestion`, `QuizResult`, `CountQuizResult`,
  `QuizSessionResult`, `generate_strategy_question`, `grade_strategy_answer`,
  `normalize_user_action`, `build_strategy_questions`, `run_strategy_session`,
  `run_count_session`).
- `app/cli.py` — Terminal trainer (`python -m app.cli` or the installed
  `blackjack-coach` command, plus `count`, `simulate`, `play`, `quiz`,
  `count-quiz`, `quiz-session`, `count-session`, `history`, `deviations`,
  `deviation-quiz`, `diagnose`, `profiles`, `split-rules`, `matrix`,
  `audit`, `outcomes`, `coach`, and `coach-play` subcommands).
- `pyproject.toml` — Modern packaging: metadata, the `blackjack-coach` console
  script, the `dev` extra, and `pytest`/`ruff` configuration.
- `.github/workflows/ci.yml` — CI: lint + tests on Python 3.9-3.12.
- `tests/` — Behavioural tests for the evaluator, engine, explanations,
  formatting, counting, shoe, simulator, quiz, CLI, and packaging.

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

### v1.0.0 — Stable Release (done)

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

### v1.1.0 — Terminal Visual Polish (done)

Presentation-only release: the CLI looks clearer and more professional, with
**no changes** to strategy, counting, simulation, split, or scoring logic.

Delivered:

- **`app/formatting.py`** — dependency-free helpers (standard library only, no
  rich/typer/click): `format_header`, `format_section`, `format_kv`,
  `format_list`, `format_result_status`, `format_percentage`, `format_warning`,
  and `format_cards`.
- **Reformatted CLI output** for every command (`strategy`, `count`,
  `simulate`, `play`, `quiz`, `count-quiz`, `quiz-session`, `count-session`):
  titled headers with underlines, aligned `label : value` rows, a visible
  `[ CORRECT ]` / `[ INCORRECT ]` badge, and percentage summaries.
- Version bumped to **1.1.0** (with `tests/test_formatting.py` and updated CLI
  assertions). All tests pass; ruff clean.

Out of scope (unchanged): no logic changes, no casino connectivity, no real
betting/bankroll, no camera/video, no scraping, no betting spread, no Kelly, no
Illustrious 18, no insurance index, no web app, and no promise of winnings.

### v1.2.0 — Local Session History (done)

Adds opt-in, local-only progress tracking. No changes to strategy, counting,
simulation, split, or scoring logic.

Delivered:

- **`app/session_history.py`** with a `SessionRecord` summary dataclass and a
  `HistorySummary` aggregate, plus `default_history_dir`, `ensure_history_dir`,
  `build_session_record`, `save_session_record`, `load_session_record`,
  `list_session_records`, and `summarize_history`.
- **`--save` / `--history-dir`** on `quiz-session` and `count-session`: write a
  JSON summary to `./.blackjack_coach/history` (or a chosen folder) and print
  the path.
- **`history` command** (`--limit`, `--dir`): summarises saved sessions with
  total, average/best/worst accuracy, and the most common weak spots.
- Version bumped to **1.2.0**; `.blackjack_coach/` added to `.gitignore`.
- Tests: `tests/test_session_history.py` and CLI history tests; all earlier
  tests still pass; ruff clean.

Privacy / safety: the history stores a **summary only** (mode, totals,
accuracy, weak spots, timestamp, id). It never stores money, bankroll, bets,
accounts, personal data, secrets, screenshots, or casino data; there is no
database, network, or cloud, and history files are never committed.

### v1.3.0 — Professional Rules & Decision Intelligence (done)

Reframes the coach around decision intelligence and adds true-count deviation
study plus decision diagnostics. No changes to the basic-strategy engine, Hi-Lo
math, simulator, split, or scoring.

Delivered:

- **`app/deviations.py`**: `DeviationRule` and `DeviationRecommendation`
  dataclasses; a small, explicit `DEFAULT_DEVIATION_RULES` study set (a few
  common Hi-Lo deviations, plus a study-only insurance note); helpers
  `normalize_true_count`, `compare_true_count`, `find_matching_deviation`; and
  `recommend_with_deviation`, which calls `strategy_engine.recommend` and only
  overrides the action when a deviation applies.
- **`app/decision_diagnostics.py`**: `DecisionDiagnostic` and
  `explain_decision_factors`, a professional breakdown of *why* a play is
  recommended (hand shape, dealer strength, double/surrender/split
  availability and fallbacks, and H17/S17 rule context). It reads the engine
  and never modifies it; it does not invent exact EV.
- **CLI**: `deviations` (`--cards/--dealer/--true-count`, `--list`),
  `deviation-quiz` (`--seed`, `--answer`, interactive), and `diagnose`
  (`--cards`, `--dealer`).
- Reframed product positioning (README/docs) as a professional coach for local
  practice, demo money, video games, recreational tournaments, and training.
- Version bumped to **1.3.0**; tests in `tests/test_deviations.py` and
  `tests/test_decision_diagnostics.py` plus CLI tests; all earlier tests pass;
  ruff clean.

Decision intelligence is **coaching, not live assistance**: local-only, no
casino connectivity, no betting/bankroll/bet-spread/Kelly, and the insurance
deviation never changes the engine's insurance recommendation (always NO). The
deviation set is intentionally small (not the full Illustrious 18), and
recommendations note their dependence on the rule profile, deck estimation,
true-count rounding, and table context.

### v1.4.0 — Expanded Rule Profiles (done)

Expands the rule profiles so the coach understands and explains more blackjack
configurations. No changes to the basic-strategy engine, Hi-Lo math, simulator,
split, or scoring.

Delivered:

- **`RuleProfile` metadata**: added `number_of_decks` (alias of `decks`),
  `resplit_allowed`, `max_split_hands`, `hit_split_aces`, `profile_description`,
  and `notes`. Existing profiles and fields are unchanged (backward
  compatible).
- **Nine new profiles** alongside the original two: `SINGLE_DECK_H17_NDAS_NS`,
  `SINGLE_DECK_S17_DAS_LS`, `DOUBLE_DECK_H17_DAS_NS`, `DOUBLE_DECK_S17_DAS_LS`,
  `FOUR_DECK_H17_DAS_LS`, `SIX_DECK_H17_DAS_LS`, `SIX_DECK_S17_DAS_LS`,
  `EIGHT_DECK_H17_DAS_LS`, `EIGHT_DECK_S17_DAS_LS`.
- **Helpers**: `list_rule_profiles`, `get_rule_profile`, `describe_rule_profile`,
  `normalize_profile_key`, and `profile_supports_{surrender,das,resplit,
  hit_split_aces}`.
- **CLI**: a `profiles` command (`--list`, `--profile <KEY>`); all `--profile`
  commands accept the new profiles; `diagnose` adds a profile-context section.

**Rule codes:** H17/S17 = dealer hits/stands on soft 17; DAS/NDAS =
double-after-split allowed / not; LS/NS = late surrender / none.

**Metadata note:** `resplit_allowed`, `max_split_hands`, and `hit_split_aces`
are descriptive metadata for now and do not yet change engine play; this is
documented on the fields and in profile notes. Every new profile has a
description and tests.

### v1.5.0 — Profile-Aware Split Rules (done)

Promotes part of the v1.4.0 profile metadata into active behaviour in the
simulator and diagnostics. No changes to basic strategy, Hi-Lo math,
deviations, or session history.

Delivered:

- **`app/split_rules.py`**: `SplitRuleDecision` plus `is_pair_hand`,
  `is_ace_pair`, `can_split_initial_hand`, `can_resplit`, `can_hit_split_aces`,
  `can_double_after_split`, and `explain_split_rules`.
- **Simulator**: split aces honour `hit_split_aces` (one card each and locked
  when false; normal play when true); split sub-hands double only when
  `double_after_split` is allowed; re-split is gated by `resplit_allowed` /
  `max_split_hands` with honest warnings.
- **Diagnostics**: `diagnose` adds profile-aware split-rule factors (pair,
  split allowed, resplit, max split hands, hit split aces, DAS/NDAS), with
  explicit split-aces context for A,A and split context for 8,8.
- **CLI**: a `split-rules` command (`--cards`, `--profile`, `--split-hands`).

**How the profile fields are used now:**

- `double_after_split` and `hit_split_aces` actively change simulator play.
- `resplit_allowed` and `max_split_hands` gate the split-rule helpers and
  surface honest warnings; the **play** simulator's full re-split tree arrives
  in v1.6.0 (below).

### v1.6.0 — Full Re-Split Tree Simulator (done)

Completes the split logic started in v1.5.0: the play simulator now plays a
real split / re-split tree rather than treating re-splits as a simplified
warning. No changes to basic strategy, Hi-Lo math, deviations, or session
history.

Delivered:

- **Simulator re-split tree** (`_play_split_tree`, `_play_out_position` in
  `app/simulator.py`): the opening pair is split, and each resulting hand may
  itself be re-split up to `profile.max_split_hands` when basic strategy says
  SPLIT and the rules allow it.
- **Rule enforcement**:
  - `resplit_allowed=false` → a pair that could re-split is played as a normal
    total with a clear warning.
  - `max_split_hands` → never exceeded; once reached, further pairs are played
    as totals with a warning.
  - `hit_split_aces=false` → each split ace gets exactly one card and stops (no
    hitting, no re-splitting); `true` → split aces play normally and may
    re-split.
  - `double_after_split` → split sub-hands double only when allowed.
- **Result model**: `SplitSubHand` records `hand_id`, `split_depth`, and
  `from_resplit`; `PlayedSplitHand` records `num_split_hands`. A new
  `RESPLIT_LIMIT_REACHED` marker flags a pair played as a total because the
  rules forbade a re-split. The legacy `RESPLIT_NOT_IMPLEMENTED` marker is no
  longer produced.
- **CLI**: `play` shows the number of split hands and labels each sub-hand as
  `split` or `re-split` with its depth.
- **Tests**: a deterministic `TestFullResplitTree` suite (re-split up to the
  max, blocked when disallowed, max respected, split-aces one-card vs normal,
  DAS allowed/disallowed) plus a CLI re-split test.

**How the profile fields are used now:** `double_after_split`, `hit_split_aces`,
`resplit_allowed`, and `max_split_hands` all drive real play in the play
simulator's re-split tree. Per `PROJECT_RULES.md`, all re-split logic must be
covered by deterministic tests.

### v1.7.0 — Complete Strategy Matrix & Decision Audit (done)

Makes the coach more confident and transparent about its decisions without
changing basic strategy. Two new read-only layers sit on top of
`strategy_engine.recommend`.

Delivered:

- **`app/strategy_matrix.py`**: generates full decision matrices for a profile
  (hard 5-21, soft 13-21, pairs A,A and 2,2..10,10 vs dealer 2-10,A = 360
  cells) and audits coverage. `StrategyCell` records the recommended action,
  the raw chart action, and whether a legal fallback applied; `StrategyMatrix`
  and `MatrixAuditReport` summarise total / missing / fallback cells and
  warnings; `format_strategy_matrix` renders a compact table (uppercase = direct
  play, lowercase = legal fallback).
- **`app/decision_audit.py`**: `audit_decision` reports, for one hand, the
  category, table section, raw vs recommended action, fallback (with reason),
  legal actions, and a plain explanation. Helpers `detect_strategy_category`,
  `detect_table_section`, and `legal_actions_for_hand` back it.
- **CLI**: a `matrix` command (`--profile`, `--section`, `--audit`) and an
  `audit` command (`--cards`, `--dealer`, `--profile`). `diagnose` now embeds a
  compact audit summary.
- **Tests**: `tests/test_strategy_matrix.py` and `tests/test_decision_audit.py`
  prove full coverage (no missing cells, valid actions, fallback detection for
  restrictive profiles) plus CLI behaviour.

**Coverage focus:** this version improves decision coverage across hard totals,
soft totals, pairs, every dealer upcard, and every rule profile, and explains
whether each play is a direct chart action or a legal fallback. Per
`PROJECT_RULES.md`, any new decision table or matrix change needs a coverage
audit and cell tests.

### v1.8.0 — Outcome / Win-Loss History (done)

Adds a local outcome history so the coach can record and review the results of
played practice hands, complementing the v1.7.0 decision tooling. Basic
strategy is untouched (`strategy_engine.recommend` is not modified).

Delivered:

- **`app/outcome_history.py`**: `OutcomeRecord` and `OutcomeSummary`, plus
  `default_outcome_history_dir`, `ensure_outcome_history_dir`,
  `build_outcome_record` (handles both `PlayedHand` and `PlayedSplitHand`,
  counting per-sub-hand wins/losses/pushes/surrenders and busts),
  `save_outcome_record`, `load_outcome_record`, `list_outcome_records` (with
  `limit` and `profile_key`), and `summarize_outcomes`.
- **CLI**: `play --save-outcome [--outcome-dir PATH]` records a played hand;
  `outcomes [--limit N] [--profile KEY] [--dir PATH]` summarises the history
  (totals, busts, split records, average split hands, most common profile and
  outcomes).
- **Tests**: `tests/test_outcome_history.py` (build from normal and split
  hands, save/load roundtrip, list with limit / profile filters, summary
  counts, no sensitive fields) plus CLI tests.

**Storage policy:** summary only - profile, seed, cards, actions, and result
counts. No money, bankroll, bets, accounts, tokens, screenshots, or sensitive
data; no database, network, or cloud. Records live under the git-ignored
`.blackjack_coach/outcomes/` folder. Per `PROJECT_RULES.md`, outcome history
must remain a local summary and never store sensitive data.

### v1.9.0 — Guided Coach Mode (done)

Lets the coach drive: it picks and explains the best play, and can play a full
simulated hand step by step. The user asks; the coach decides and teaches. Basic
strategy is untouched (`strategy_engine.recommend` is not modified).

Delivered:

- **`app/guided_coach.py`**: `CoachStep` and `GuidedCoachResult`, plus
  `build_coach_step` and `explain_next_best_action` (direct advice via
  `decision_audit`), `build_guided_result`, and `play_guided_coach_hand` (a full
  hand played by `play_training_hand`, reconstructed into coach steps; reuses
  v1.8.0 `build_outcome_record` for result labels and tallies). Supports normal
  and split / re-split hands.
- **CLI**: `coach` (direct advice for one hand) and `coach-play` (the coach
  plays a full hand automatically, step by step, with optional
  `--save-outcome` / `--outcome-dir`). `diagnose` now points to `coach` and
  `audit`.
- **Tests**: `tests/test_guided_coach.py` (coach step matches the engine, split
  context, full-hand result, determinism, engine unchanged) plus CLI tests.

**Separation of concerns:** recommendation, explanation, the executed action,
and the outcome stay distinct; the coach decides and the user receives guidance.
Per `PROJECT_RULES.md`, the user is not asked to choose the action in guided
mode, and the coach never changes the strategy engine.

### v1.10.0 — Professional Card Renderer (done)

Makes cards look and read like a real blackjack calculator: figures, suits, and
colour for input and output. Strategy is untouched - this is a presentation /
parsing layer.

Delivered:

- **`app/cards.py`**: `RenderedCard`; the `SUIT_SYMBOLS` / `SUIT_NAMES` /
  `RED_SUITS` / `BLACK_SUITS` constants; `normalize_rank`, `normalize_suit`,
  `parse_card`, `parse_cards`, `cards_to_ranks`, `format_card`, `format_cards`,
  `strip_ansi`, and `assign_display_suits` (deterministic decorative suits for
  simulated cards). ANSI red for hearts/diamonds; default colour for
  spades/clubs.
- **CLI**: the card-facing commands (`coach`, `coach-play`, `play`, `simulate`,
  `diagnose`, `audit`, `split-rules`) render suits and colour; global
  `--no-color` and `--plain-cards` flags; colour auto-disables off a TTY.
- **Tests**: `tests/test_cards.py` (normalisation, parsing, colour, ANSI
  stripping, deterministic suits) plus CLI tests for Unicode/letter suit input,
  `--no-color`, and `--plain-cards`.

**Visual only:** suits and colour never affect strategy, counting, outcomes, or
scoring. Card input accepts `A♠`, `AS`, `A spades`, `10H`, `Q clubs`, `Kd`, and
suitless `A,7`; the engine always receives plain ranks (`cards_to_ranks`). Per
`PROJECT_RULES.md`, the card display layer must preserve ranks for the engine.

### v1.11.0 — Count-Aware Coach Advisor (done)

Connects the educational true-count deviation study to the guided coach. The
user can supply an optional true count and the coach compares basic strategy
with the count-adjusted play and chooses a final recommendation. Basic strategy
is untouched (`strategy_engine.recommend` is not modified).

Delivered:

- **`app/guided_coach.py`**: count-aware fields on `CoachStep`
  (`basic_action`, `count_adjusted_action`, `true_count`, `deviation_applied`,
  `deviation_rule_id`, `deviation_title`, `final_recommended_action`,
  `count_note`) and `true_count` on `GuidedCoachResult`. `build_coach_step` /
  `explain_next_best_action` accept `true_count` and consult
  `deviations.recommend_with_deviation`; `play_guided_coach_hand` passes a true
  count as advisory context only.
- **CLI**: `coach --true-count <n>` (basic vs count-adjusted vs final action,
  with the deviation rule) and `coach-play --true-count <n>` (advisory true
  count per step; the hand is played with basic strategy).
- **Tests**: count-aware cases in `tests/test_guided_coach.py` (deviation
  applies / does not by true count; hard 15/16/10; insurance never final;
  engine unchanged) plus CLI tests.

**Separation:** the coach keeps basic action, count-adjusted action, and final
recommended action distinct and explains any deviation. The deviation study is
study-only - the insurance rule never becomes a final action, and without a
true count the coach uses basic strategy. Per `PROJECT_RULES.md`, deviation
study must not be silently mixed into the base engine.

### v1.12.0 — Probability & EV Advisor (done)

Adds an approximate probability / EV layer so the coach can explain risk, not
just the recommended play. Approximate and advisory only - it never overrides
the recommendation and does not change the engine or counting math.

Delivered:

- **`app/probability_advisor.py`**: `PlayerBustEstimate`,
  `DealerOutcomeEstimate`, `ActionEVEstimate`, `ProbabilityAdvice`, and
  `estimate_player_bust_probability`, `estimate_dealer_outcomes` (deterministic
  recursive enumeration honouring H17/S17), `estimate_action_ev`,
  `build_probability_advice`. Idealised 13-rank shoe with a one-card
  look-ahead; fast and dependency-free.
- **CLI**: `odds` (full advisory: bust-if-hit, dealer 17-21/bust distribution,
  per-action EV, best estimated action) and `coach --show-odds` (compact
  summary).
- **Tests**: `tests/test_probability_advisor.py` (bust estimates, dealer
  distribution sums to ~1, surrender EV -0.5, illegal-action warning, advice
  assembly, engine unchanged) plus CLI tests.

**Approximate & advisory:** estimates are clearly labelled approximate and never
override the strategy recommendation; if the best-EV action differs, the advisor
says so and keeps the recommendation. Per `PROJECT_RULES.md`, the probability/EV
layer must label approximations and must not override the main recommendation
without explicit validation and tests.

### v1.13.0 — Adaptive Local Learning (current)

Adds a read-only adaptive-learning layer so the coach becomes more useful with
use: it reads the locally saved outcome history to detect patterns, weak spots,
and practice opportunities, and adds personalised local context to the coach.
Crucially, it learns from local history to **personalise context**, not to
**change the base strategy**: the main recommended action stays driven by basic
strategy and the count math, never by short-term local results.

Delivered:

- **`app/adaptive_learning.py`**: `LearningSpot`, `LearningSummary`, and
  `CoachHistoryContext`; `classify_hand_spot` (e.g. `hard_16_vs_10`,
  `soft_18_vs_9`, `pair_8_vs_6`, `pair_A_vs_6`, built on the existing hand
  evaluator and keyed by the starting two cards versus the dealer upcard);
  `build_learning_summary` (groups saved `OutcomeRecord`s by spot / profile /
  outcome, detects weakest / strongest / high-variance spots, and generates
  practice recommendations); `build_history_context` (per-hand local context,
  filtered by profile, with exact-spot then similar-pattern fallback); and
  `format_learning_summary`.
- **CLI**: `learn` (`--dir`, `--profile`, `--limit`, `--spot`) prints the
  Adaptive Learning summary, with a clear "use --save-outcome first" message
  when there is no data; `coach --use-history` (`--history-dir`) appends a Local
  history context block (matching records, local win/loss/push rates, practice
  note, caution note) and combines with `--true-count` / `--show-odds`.
- **Tests**: `tests/test_adaptive_learning.py` (spot classification; empty /
  profile-count / weakest / strongest / LOW-confidence summaries; history
  context with and without local data and profile filtering; and a guard that
  history never changes the recommended action) plus CLI tests for `learn` and
  `coach --use-history`.

**Learns locally, not blindly:** confidence is LOW below 10 total records, and a
spot with fewer than 5 records is flagged as a small sample. Per
`PROJECT_RULES.md`, adaptive learning keeps history, variance, sample size, and
the mathematical strategy separate, must not change the main recommendation
without explicit validation, promises no edge, and makes no exact predictions.
It is local, transparent, and reversible (read-only over the git-ignored
`.blackjack_coach/` outcomes; no network, cloud, database, or external
dependencies; no money, bankroll, accounts, tokens, screenshots, or sensitive
data) and does not change `strategy_engine.recommend` or the counting math.

### v2.0 — Possible Web UI (if decided later)

- A browser front end over the existing engine and simulator, only if and when
  decided. Subject to the same educational, no-real-money constraints.

## Out-of-Scope (All Versions)

Per `PROJECT_RULES.md`: no casino connectivity, no real-money betting or
automation, no casino camera/video capture, no guarantees of profit, and no
facilitation of cheating or illegal activity.
