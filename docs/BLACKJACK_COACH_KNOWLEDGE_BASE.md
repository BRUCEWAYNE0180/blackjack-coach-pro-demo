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
- `app/ev_history.py` — Local EV-snapshot history & Strategy-vs-EV review
  (summary only): `EVSnapshotRecord`, `EVReviewSummary`,
  `default_ev_history_dir`, `ensure_ev_history_dir`, `build_ev_snapshot_record`
  (from a `ProbabilityAdvice` or `CompositionAwareProbabilityAdvice`),
  save/load/list (with limit / profile / disagreements-only filters), and
  `summarize_ev_snapshots`. Advisory audit only; it never changes the
  recommendation and stores no sensitive data.
- `app/ev_explainer.py` — Strategy-vs-EV explanation engine: `EVGapCategory`,
  `StrategyEVDisagreement`, `DisagreementExplanationSummary`, plus
  `classify_ev_gap`, `explain_strategy_vs_ev` (advice or snapshot),
  `explain_ev_snapshot_record`, and `summarize_disagreement_explanations`.
  Explanation layer only; it never overrides the recommendation or turns the
  advisory EV into the final decision.
- `app/reporting.py` — Exportable local-learning reports: `ReportSummary`,
  `ExportedReport`, `build_report_summary` (combines the session / outcome /
  EV-snapshot / adaptive-learning / Strategy-vs-EV summaries), the
  `render_report_markdown` / `render_report_json` / `render_report_csv`
  renderers, `save_report`, and `export_report`. Local and read-only; exports no
  sensitive data and never changes the recommendation.
- `app/dashboard.py` — Local per-profile dashboard & trends:
  `DashboardProfileSummary`, `DashboardTrendPoint`, `DashboardSummary`, plus
  `build_profile_dashboard`, `build_dashboard_trends`,
  `recommend_next_practice_plan`, `render_dashboard_text`,
  `render_dashboard_markdown`, and `export_dashboard`. Groups the local history
  by profile and suggests practice; a read-only practice aid that never changes
  the recommendation.
- `app/drill_generator.py` — Local weak-spot drill generator: `DrillSpot`,
  `DrillPlan`, `DrillResult`, plus `classify_drill_category`,
  `build_drill_spot_from_hand`, `build_drill_plan`, `grade_drill_answer`,
  `render_drill_plan`, and `render_drill_result`. Builds focused drills from
  history (or a fallback educational set); the correct play comes from the
  strategy engine, so it never duplicates rules or changes the recommendation.
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
  `audit`, `outcomes`, `coach`, `coach-play`, `odds`, `learn`, `ev-review`,
  `report`, and `dashboard` subcommands, plus `drill`; `odds`/`coach
  --show-odds` accept `--explain-ev` and `ev-review` accepts `--explain` /
  `--large-gaps-only`).
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

### v1.13.0 — Adaptive Local Learning (done)

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

### v1.14.0 — Composition-aware Probability & EV Advisor (done)

Upgrades the probability / EV advisor so it can use the **composition of the
remaining shoe / seen cards**. The user supplies their cards, the dealer
upcard, the number of decks, the profile, an optional true count, and now also
any seen / removed cards; the advisor uses that to produce sharper
probabilities and EV. Ten-values (10/J/Q/K) are aggregated into a single "10"
rank, which is exact for value-based blackjack.

Delivered:

- **`app/probability_advisor.py`**: `ShoeComposition`,
  `CompositionAwareProbabilityAdvice`; `build_initial_rank_counts` (A and 2-9 =
  4/deck, 10 = 16/deck, 52/deck total), `remove_known_cards` (accepts plain and
  suited cards, never negative, warns on inconsistency), `build_shoe_composition`,
  `estimate_player_bust_probability_composition`,
  `estimate_dealer_outcomes_composition` (deterministic recursive enumeration
  over remaining counts with depletion, honouring H17/S17, memoised on the
  count vector so it stays fast for 6-8 decks),
  `estimate_action_ev_composition` (STAND vs the finite-shoe dealer
  distribution; HIT/DOUBLE one-card composition look-ahead; SURRENDER -0.5;
  SPLIT simplified with a warning), and `build_composition_aware_advice`
  (falls back to `build_probability_advice` when not composition-aware).
- **CLI**: `odds` gains `--seen-cards`, `--composition-aware`, and
  `--composition` (composition summary); `--seen-cards` / `--composition`
  auto-enable composition-aware mode. `coach` gains `--seen-cards` and
  `--composition-aware`, applied to the `--show-odds` block.
- **Tests**: extended `tests/test_probability_advisor.py` and CLI tests.

**Honest about exactness:** the dealer distribution is exact finite-shoe; the
player HIT/DOUBLE EV is an approximate one-card look-ahead; SPLIT EV was
simplified here (improved in v1.15.0). Per `PROJECT_RULES.md`, composition-aware
probabilities clearly separate exact / finite-shoe, approximation, and advisory,
and must not override the main strategy without explicit validation. It does not
change `strategy_engine.recommend` or the Hi-Lo counting math, adds no external
dependencies, and runs no large/slow simulations.

### v1.15.0 — Composition-aware Split / Re-split EV Advisor (done)

Builds directly on v1.14.0. The composition layer and exact finite-shoe dealer
distribution were already in place, but SPLIT EV was a simplified placeholder.
v1.15.0 makes the advisor properly evaluate **splitting and re-splitting** pairs
(A,A / 8,8 / 10,10 / 2,2, ...) using the remaining shoe composition and the
profile's split rules, so the coach is far more professional when analysing
pairs.

Delivered:

- **`app/probability_advisor.py`**: `SplitEVEstimate`, `SplitBranchEstimate`;
  `estimate_split_ev_composition` (pairs only; respects `split_allowed`,
  `resplit_allowed`, `max_split_hands`, `hit_split_aces`, DAS; builds the
  re-split tree to the cap and falls back to a normal hand once the cap is hit;
  split aces get one card and stop unless `hit_split_aces`),
  `estimate_subhand_ev_after_split` (per-sub-hand optimal EV, memoised on
  rank/depth/hand-count), and `compare_pair_actions_ev` (SPLIT vs
  HIT/STAND/DOUBLE/SURRENDER, sorted by EV). `build_composition_aware_advice`
  attaches a `split_estimate` for pairs and feeds the real split EV into
  `best_estimated_action`.
- **CLI**: `odds` shows a "Split EV estimate" block for pairs; `coach
  --show-odds` shows a compact Split EV line and whether the advisory best-EV
  action agrees with the coach's recommendation.
- **Tests**: extended `tests/test_probability_advisor.py` and CLI tests.

**Limits / honesty:** the dealer distribution and the re-split tree (up to
`max_split_hands`) are enumerated deterministically, and split aces that cannot
be hit are evaluated **exactly** (`is_exact_for_supported_rules=True`). Hittable
sub-hands reuse the one-card-then-stand look-ahead and inter-hand card depletion
is ignored, so those cases remain **approximate** (improved in v1.16.0). Per
`PROJECT_RULES.md`, split/re-split EV separates exact, approximate, and
simplified, and never overrides the main strategy without explicit validation.
No change to `strategy_engine.recommend` or the Hi-Lo math; no external
dependencies; no Monte Carlo / slow simulations.

### v1.16.0 — Full Player EV Decision Tree (done)

Builds on v1.15.0. The composition layer, exact finite-shoe dealer
distribution, and split/re-split EV were already in place, but some hittable
sub-hands still used a one-card-then-stand look-ahead. v1.16.0 replaces the HIT
look-ahead with a **recursive optimal hit/stand tree** and unifies every legal
action's EV into one player decision tree, so the advisor is more professional
and less approximate.

Delivered:

- **`app/probability_advisor.py`**: `PlayerDecisionEVEstimate`, `PlayerEVBranch`;
  `estimate_stand_ev_composition` (vs the exact dealer distribution; bust = -1),
  `estimate_hit_ev_tree` (recursive optimal hit/stand over the remaining
  composition, memoised on `(total, is_soft)` and depth-capped),
  `estimate_double_ev_composition` (one card then stand, doubled),
  `estimate_surrender_ev` (-0.5 when legal), and
  `estimate_player_decision_tree_ev` (STAND / HIT / DOUBLE / SURRENDER / SPLIT,
  SPLIT delegated to the split estimator). `build_composition_aware_advice`
  exposes a `decision_tree` field and takes `best_estimated_action` from it;
  split sub-hands now play hittable hands with the recursive tree.
- **CLI**: `odds` shows a "Player EV decision tree" block (best EV action, EV by
  action, exactness note, EV vs recommendation); `coach --show-odds` shows a
  compact player EV summary and agreement with the recommendation.
- **Tests**: extended `tests/test_probability_advisor.py` and CLI tests.

**Limits / honesty:** `STAND` uses the exact finite-shoe dealer distribution and
`HIT` is a recursive optimal tree, so multi-card draws are no longer truncated to
one ply (for non-pair hands the HIT/STAND/DOUBLE/SURRENDER set is fully
enumerated, `is_exact_for_supported_rules=True`). Documented simplifications:
player-tree draws use fixed remaining-composition probabilities (no intra-hand
depletion), the dealer distribution is from the pre-action shoe, ten-values are
aggregated, and the SPLIT portion keeps its own approximations. Per
`PROJECT_RULES.md`, the player EV tree separates main strategy, advisory EV,
exactness, and approximation, and never overrides the main strategy without
explicit validation. No change to `strategy_engine.recommend` or the Hi-Lo math;
no external dependencies; no Monte Carlo / slow simulations.

### v1.17.0 — EV Snapshot History & Review (done)

Builds on the v1.12.0-v1.16.0 probability / EV advisor. The advisor is advisory
only, but there was no way to **remember** its output or to study, over many
hands, when the coach's main recommendation agreed with the advisory best-EV
action and when it differed. v1.17.0 adds a **local EV-snapshot history** and a
**Strategy-vs-EV review** so the advisor becomes more transparent and useful for
local self-study. It saves only a safe local summary and never changes play.

Delivered:

- **`app/ev_history.py`**: `EVSnapshotRecord` (snapshot id, timestamp, profile,
  cards, dealer upcard, decks, optional true count / seen cards, the recommended
  and best-EV actions, per-action EVs, the recommended action's EV, the best EV,
  the EV gap, agreement, `has_split_ev` / `has_decision_tree` /
  `composition_aware` flags, an exactness note, an approximation note, warnings,
  and a note) and `EVReviewSummary` (total snapshots, agreement / disagreement
  counts and rate, most common profile, most common recommended / best-EV
  actions, largest EV gaps, disagreement spots, practice recommendations, a
  data-quality note, and warnings). Functions: `default_ev_history_dir`,
  `ensure_ev_history_dir`, `build_ev_snapshot_record` (from a `ProbabilityAdvice`
  or `CompositionAwareProbabilityAdvice`), `save_ev_snapshot_record`,
  `load_ev_snapshot_record`, `list_ev_snapshot_records` (limit / profile /
  disagreements-only filters), and `summarize_ev_snapshots` (LOW sample below 10
  snapshots).
- **CLI**: `odds` and `coach --show-odds` gain `--save-ev-snapshot` /
  `--ev-dir`; `coach --save-ev-snapshot` requires `--show-odds` (clear error
  otherwise). New `ev-review` command (`--dir`, `--limit`, `--profile`,
  `--disagreements-only`, `--min-gap`) prints the Strategy-vs-EV review, or a
  clear "use `--save-ev-snapshot` first" message when there is no data.
- **Tests**: new `tests/test_ev_history.py` (build from composition-aware /
  idealised advice, agreement and EV-gap computation, save/load roundtrip, list
  filters, empty / counting / largest-gap / LOW-sample / min-gap summaries, no
  sensitive fields, and a guard that building a snapshot never changes
  `recommend()`) plus CLI tests for the new flags and `ev-review`.

**Limits / honesty:** EV snapshots are a **local advisory audit only**. They
never override the main recommendation (differences are reported, not applied),
never change `strategy_engine.recommend` or the Hi-Lo math, and store no money,
bankroll, bets, accounts, tokens, screenshots, or personal data - no database,
no network, no cloud. Saved files live under the git-ignored `.blackjack_coach/`
tree and are never committed. No external dependencies and no slow simulations.

### v1.18.0 — Strategy-vs-EV Explanation Engine (done)

Builds on the v1.12.0-v1.17.0 probability / EV advisor and the v1.17.0
EV-snapshot history. The advisor could compute EV, save snapshots, and review
agreement / disagreement, but it did not yet *explain* a discrepancy in clear
language. v1.18.0 adds an explanation engine that tells the user when the
coach's recommendation agrees with the advisory best-EV action and when it
differs - and why - while keeping a strict separation between the recommended
action, the advisory EV action, the gap size, the model's limits, and the final
decision. It never changes play.

Delivered:

- **`app/ev_explainer.py`**: `EVGapCategory` (labelled gap band with meaning and
  action note), `StrategyEVDisagreement` (player cards, dealer upcard, profile,
  recommended action, best EV action, strategy / best EV, EV gap, gap label,
  agreement status, likely reason, explanation, recommendation note,
  approximation note, warnings), and `DisagreementExplanationSummary`. Functions:
  `classify_ev_gap` (TINY `[0, 0.02)`, SMALL `[0.02, 0.05)`, MEDIUM `[0.05,
  0.15)`, LARGE `[0.15, inf)`, UNKNOWN when missing), `explain_strategy_vs_ev`
  (accepts a `ProbabilityAdvice`, a `CompositionAwareProbabilityAdvice`, or an
  `EVSnapshotRecord` - reusing the tested `build_ev_snapshot_record` for advice
  so the explanation matches the saved snapshots), `explain_ev_snapshot_record`,
  and `summarize_disagreement_explanations` (groups into agrees / tiny / small /
  medium / large / missing with review notes).
- **CLI**: `odds --explain-ev` and `coach --show-odds --explain-ev` append a
  "Strategy vs EV explanation" block; `coach --explain-ev` requires
  `--show-odds` (clear error otherwise). `ev-review --explain` adds explanations
  for the top disagreement spots, and `ev-review --large-gaps-only` narrows the
  review to LARGE-gap (or MEDIUM when no LARGE) snapshots.
- **Tests**: new `tests/test_ev_explainer.py` and `TestCliStrategyVsEVExplanation`
  in `tests/test_cli.py`.

**Limits / honesty:** the explanation engine is an explanation layer only. When
the advisory best-EV action differs from the recommendation it only *reports and
explains* it; it never converts the advisory EV into an automatic override. A
tiny / small gap is flagged as probably not a strong difference; a large gap is
flagged for review with `odds` and `audit`. Per `PROJECT_RULES.md`, the
explanations always separate the recommended action, the advisory EV action, the
gap size, the model limitations, and the final decision. No change to
`strategy_engine.recommend`, the Hi-Lo math, adaptive learning, guided coaching,
outcome / session history, or the EV-snapshot history; no external dependencies;
no network / cloud / database; no sensitive data.

### v1.19.0 — Exportable Learning Reports (done)

Builds on every local-history feature so far (session history v1.2.0, outcome
history v1.8.0, adaptive learning v1.13.0, EV-snapshot history v1.17.0, and the
Strategy-vs-EV explanation engine v1.18.0). Those summaries lived behind
separate commands; v1.19.0 combines them into a single **exportable report**
(Markdown / JSON / CSV) for reviewing progress or saving to Notion / GitHub. It
stays local, read-only, and dependency-free, and never changes play.

Delivered:

- **`app/reporting.py`**: `ReportSummary` (created_at, profile scope, totals for
  sessions / outcomes / EV snapshots, session accuracy, outcome win / loss rate,
  EV agreement rate, weakest / strongest spots, largest EV gaps, combined
  practice recommendations, a data-quality note, and warnings) and
  `ExportedReport` (report id, created_at, format, output path, summary, note).
  Functions: `build_report_summary` (loads session / outcome / EV history with
  `profile_key` / `limit` filters and combines `summarize_history`,
  `summarize_outcomes`, `summarize_ev_snapshots`, `build_learning_summary`, and
  `summarize_disagreement_explanations`), `render_report_markdown` /
  `render_report_json` / `render_report_csv` (stdlib `csv`, key/value rows),
  `save_report`, and `export_report` (defaults to a timestamped file under
  `./.blackjack_coach/reports`; raises `ValueError` for an unknown format).
- **CLI**: new `report` command with `--format`, `--output`, `--profile`,
  `--limit`, `--session-dir`, `--outcome-dir`, `--ev-dir`, and `--print`. EV
  snapshots are included automatically when present (no `--include-ev` flag is
  added in v1.19.0).
- **Tests**: new `tests/test_reporting.py` and `TestCliReport` in
  `tests/test_cli.py`.

**Limits / honesty:** reports are a local, read-only summary only. They keep
training, outcomes, EV advisory, and practice recommendations in clearly
separated sections, store no money / bankroll / bets / accounts / tokens /
screenshots / personal data, and include no private filesystem paths beyond the
report's own output location. Per `PROJECT_RULES.md`, the report never changes
`strategy_engine.recommend`, the Hi-Lo math, adaptive learning, guided coaching,
outcome / session history, the EV-snapshot history, or the Strategy-vs-EV
explanation engine. Files live under the git-ignored `.blackjack_coach/reports`
tree (unless an explicit `--output` is given) and are never committed. No
external dependencies; no network / cloud / database.

### v1.20.0 — Profile Dashboard & Trends (done)

Builds on the v1.19.0 exportable reports and every local-history feature behind
them. Reports gave a flat snapshot; v1.20.0 adds a per-profile **dashboard**
that groups the history by rule profile, shows a simple recent-sample trend, and
turns the data into a concrete next-practice plan - answering "which profile am
I practising most, where am I failing, which spots have the most Strategy-vs-EV
disagreements, and what should I drill next?". It stays local, read-only, and
dependency-free, and never changes play.

Delivered:

- **`app/dashboard.py`**: `DashboardProfileSummary` (per-profile totals,
  accuracy / win / loss / EV-agreement rates, top weak / strong spots, top EV
  disagreements, largest EV gaps, recommended drills, a data-quality note), 
  `DashboardTrendPoint` (a recent-sample bucket), and `DashboardSummary` (the
  profile list, selected profile, global totals, best / weakest / most-practised
  profile, trend points, global weak spots and EV disagreements, the
  next-practice plan, and a data-quality note). Functions:
  `build_profile_dashboard`, `build_dashboard_trends` (simple `recent_1..3`
  buckets; no fragile date parsing), `recommend_next_practice_plan`,
  `render_dashboard_text`, `render_dashboard_markdown`, and `export_dashboard`.
- **CLI**: new `dashboard` command with `--profile`, `--limit`,
  `--session-dir`, `--outcome-dir`, `--ev-dir`, `--markdown`, `--export`, and
  `--output`. The `report` Markdown now points users to `dashboard`.
- **Tests**: new `tests/test_dashboard.py` and `TestCliDashboard` in
  `tests/test_cli.py`.

**Limits / honesty:** the dashboard is a read-only practice aid. It combines the
existing per-area summaries by profile, uses no external chart libraries (trends
are plain text / Markdown tables), and only suggests practice - it never changes
the recommendation. Sessions are not profile-scoped, so session stats are shown
globally (with a note when several profiles are present). Per `PROJECT_RULES.md`
it keeps training, outcomes, EV advisory, disagreements, and recommendations in
separate sections, stores / exports no sensitive data, and never changes
`strategy_engine.recommend`, the Hi-Lo math, adaptive learning, guided coaching,
outcome / session history, the EV-snapshot history, the Strategy-vs-EV engine,
or the reporting module. No external dependencies; no network / cloud / database.

### v1.21.0 — Weak-Spot Drill Generator (current)

Builds on adaptive learning (v1.13.0), the EV-snapshot history (v1.17.0), the
reports (v1.19.0), and the dashboard (v1.20.0). Those features could say *what*
to practise; v1.21.0 actually *generates and runs* focused practice drills from
the same local signals, grading answers against the stable strategy engine. It
stays local, read-only, and dependency-free, and never changes play.

Delivered:

- **`app/drill_generator.py`**: `DrillSpot` (spot id, category, cards, dealer,
  profile, recommended action, reason, source, priority, difficulty, tags),
  `DrillPlan` (plan id, profile, total, focus, spots, source summary, practice
  note, warnings), and `DrillResult` (answer, correct action, correctness,
  explanation, next-review hint). Functions: `classify_drill_category`,
  `build_drill_spot_from_hand` (correct action from `strategy_engine.recommend`;
  suited input via `app.cards`), `build_drill_plan` (prioritises EV
  disagreement / weak / high-variance spots from history, with a well-known
  educational fallback; `focus`, `count`, and `seed`), `grade_drill_answer`
  (reuses `quiz.normalize_user_action`), `render_drill_plan`, and
  `render_drill_result`.
- **CLI**: new `drill` command with `--profile`, `--focus`, `--count`,
  `--seed`, `--answer`, `--spot`, the history dirs, and `--plan-only`. The
  `dashboard` output now points to `drill --focus weak`.
- **Tests**: new `tests/test_drill_generator.py` and `TestCliDrill` in
  `tests/test_cli.py`.

**Limits / honesty:** drills are local practice training. The correct play
always comes from the existing strategy engine (no duplicated rules), and the
generator never changes `strategy_engine.recommend`, the Hi-Lo math, adaptive
learning, guided coaching, outcome / session history, the EV-snapshot history,
the Strategy-vs-EV engine, the reporting module, or the dashboard. Per
`PROJECT_RULES.md` it stores no sensitive data, suggests practice without
promising results, and uses no external dependencies, network, cloud, or
database.

### v2.0 — Possible Web UI (if decided later)

- A browser front end over the existing engine and simulator, only if and when
  decided. Subject to the same educational, no-real-money constraints.

## Out-of-Scope (All Versions)

Per `PROJECT_RULES.md`: no casino connectivity, no real-money betting or
automation, no casino camera/video capture, no guarantees of profit, and no
facilitation of cheating or illegal activity.
