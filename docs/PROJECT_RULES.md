# Project Rules — Blackjack Coach Pro Demo

## 1. Purpose

Blackjack Coach Pro Demo is a **professional blackjack coach** for **local
practice, demo money, video games, recreational tournaments, and training**.
Its focus is **decision intelligence**: it recommends the correct play, explains
the rule factors behind it, drills it with quizzes and scored sessions, and
offers true-count deviation study and decision diagnostics.

It is a coaching and practice tool, not a real-money gambling product. The
hard constraints below define the responsible scope; within that scope, the
product should behave like a sharp, helpful coach.

## 2. Hard Constraints (Non-Negotiable)

These constraints define what the project **must never do**:

1. **No casino connectivity.** The software must not connect to, integrate
   with, or communicate with any real casino, online gambling platform, or
   real-money gaming API.
2. **No real-money betting or automation.** It must not place, manage, or
   automate real-money wagers of any kind.
3. **No casino camera/video capture.** It must not use a camera, screen
   capture, or video feed to read cards from a real (live or online) table.
4. **No promise of winnings.** It must not claim, imply, or guarantee profit.
   Blackjack always carries a house edge; good strategy reduces losses, it
   does not guarantee wins.
5. **No facilitation of cheating.** It must not support marked cards, hole-card
   reading, collusion, device-assisted advantage play at real tables, or any
   activity that is illegal or violates casino terms.


## 3. What the Project May Do

- Teach and quiz blackjack basic strategy for defined rule profiles.
- Simulate hands locally with a virtual/random deck for practice.
- Explain the mathematical reasoning (expected value, house edge) in later
  versions, for educational purposes only.
- Demonstrate card-counting concepts (e.g., Hi-Lo) as a **learning topic** in
  later versions, clearly framed as theory and practiced only against the
  built-in simulator.

## 4. Scope of v0.1

- Basic-strategy recommendations for multi-deck shoes, both **H17** (dealer
  hits soft 17) and **S17** (dealer stands on soft 17).
- Actions supported: `HIT`, `STAND`, `DOUBLE`, `SPLIT`, `SURRENDER`.
- **Insurance recommendation is always NO.**
- Fallback behaviour:
  - If `DOUBLE` is indicated but not allowed (e.g. more than two cards),
    fall back to `HIT` (hard hands) or `STAND` (soft "double-else-stand").
  - If `SURRENDER` is indicated but not allowed, fall back to the underlying
    `HIT` / `STAND` / `SPLIT` action.
- **Not** included yet: Hi-Lo counting, True Count, the Illustrious 18,
  a simulator, and a web app. See the knowledge base for the roadmap.

## 5. Rule Profiles

Profiles are defined in `app/rules.py`. v0.1 ships two:

| Key                        | Decks | Soft 17 | DAS | Late Surrender |
|----------------------------|-------|---------|-----|----------------|
| `MULTI_DECK_H17_DAS_LS`    | 6     | Hits    | Yes | Yes            |
| `MULTI_DECK_S17_DAS_LS`    | 6     | Stands  | Yes | Yes            |

## 6. Engineering Conventions

- Language: Python (standard library only for v0.1; `pytest` for tests).
- Code lives in `app/`, tests in `tests/`, documentation in `docs/`.
- Public behaviour is covered by tests; strategy tables are treated as the
  source of truth and validated against well-known basic-strategy charts.
- Changes land via pull request; no direct commits to `main`.

## 7. Professional Quality Gates

As of v0.9 the project enforces these gates on every change:

- **Tests must pass.** Every pull request must pass `python -m pytest` (run
  locally and in CI on Python 3.9-3.12).
- **Lint must pass.** Every pull request must pass `ruff check app tests`.
- **New features require tests.** Any new feature or bug fix must add or update
  tests that cover the new behaviour.
- **Scope is preserved.** Every new function must keep the educational /
  simulated scope: no real casino connectivity, no real-money betting or
  bankroll, no camera/video, no screen scraping, and no promise of winnings.
- **No secrets in the repository.** Never commit secrets, `.env` files, API
  tokens, credentials, private PDFs, or sensitive screenshots. CI must not
  depend on any private secret to run the tests or lint.
- **Changes land via pull request.** No direct commits to `main`; CI must be
  green before merge.
- **UX polish must not alter logic.** Presentation/formatting changes (e.g.
  terminal output) must not change strategy, counting, simulation, split, or
  scoring results. Any change that could affect those must include specific
  tests proving the behaviour is unchanged.
- **Local history must stay a safe summary.** Saved session history must never
  contain secrets, real money, bets, bankroll, accounts, personal data,
  screenshots, or casino data. It is a local summary only (no database, no
  network), and the `.blackjack_coach/` folder must remain git-ignored.
- **Deviations are study-only.** True-count deviation features are a local
  study aid. They must not enable real betting, bankroll, bet spread, Kelly,
  live casino assistance, or camera/video, and must not modify the basic
  strategy engine or change its insurance recommendation (always NO).
- **New rule profiles need tests and descriptions.** Every new rule profile
  must have a `profile_description`, be covered by tests, and be registered in
  `PROFILES`. If a profile field is metadata that does not yet alter engine
  logic (e.g. `resplit_allowed`, `max_split_hands`, `hit_split_aces`), that
  must be documented in the field/profile notes.
- **Metadata promoted to logic needs tests and docs.** When a profile field
  moves from descriptive metadata to active behaviour (as `hit_split_aces` and
  `double_after_split` did for the simulator in v1.5.0), it must have explicit
  tests and updated docs that state the new behaviour, and any part that is
  still simplified (e.g. full re-split) must be called out honestly.
- **All re-split logic must have tests.** As of v1.6.0 the simulator plays a
  full split / re-split tree. Any change to the re-split tree, or to how
  `resplit_allowed`, `max_split_hands`, `hit_split_aces`, or
  `double_after_split` affect split play, must be covered by deterministic
  tests. At minimum the suite must keep proving: re-split is allowed up to
  `max_split_hands`; re-split is blocked when `resplit_allowed` is false;
  `max_split_hands` is never exceeded; split aces with `hit_split_aces=false`
  take exactly one card and stop; split aces with `hit_split_aces=true` play
  normally; and double-after-split is honoured per profile.
- **Any new decision table or matrix change needs a coverage audit and
  cell tests.** Decision-coverage tooling (v1.7.0: `app/strategy_matrix.py` and
  `app/decision_audit.py`) must keep proving full coverage. Whenever a strategy
  table, a representative-hand set, or a matrix generator changes, the suite
  must re-verify: every hard total (5-21), soft total (13-21), and pair (A,A and
  2,2..10,10) is covered against dealer 2-10 and A; there are no missing cells;
  every cell yields a valid `Action`; and fallback cells are detected for
  profiles that restrict surrender / double / split. Coverage tooling reads
  `strategy_engine.recommend` and must never change basic strategy.
- **Outcome history is a local summary only.** The outcome / win-loss history
  (v1.8.0: `app/outcome_history.py`) must store only local practice summaries -
  profile, seed, cards, actions, and result counts. It must never store money,
  bankroll, real bets, wagers, balances, accounts, tokens, screenshots, or any
  sensitive/personal data, and must use no database, network, or cloud. Saved
  records live under the git-ignored `.blackjack_coach/` tree and are never
  committed.
- **Guided coach mode separates concerns.** The coach mode (v1.9.0:
  `app/guided_coach.py`) must keep recommendation, explanation, the executed
  action, and the outcome as distinct pieces. The coach decides and the user
  receives guidance - the user is not asked to choose the action in guided
  mode. Guided coaching reads `strategy_engine.recommend` and the simulator and
  must never change basic strategy.
- **The card display layer is visual only.** The professional card renderer
  (v1.10.0: `app/cards.py`) and its suits/colour must never alter strategy,
  counting, outcomes, or scoring. Every card conversion must preserve the plain
  rank the engine needs (`cards_to_ranks`), and the engine must always be called
  with plain ranks. Colour/suit display is presentation only and must degrade to
  plain text when colour is unsupported or disabled (`--no-color` /
  `--plain-cards`).
- **Count-aware coaching must separate the actions.** When the coach is given a
  true count (v1.11.0), it must keep `basic_action`, `count_adjusted_action`,
  and `final_recommended_action` distinct, and must explain when a deviation
  changes the play. Deviation study must not be silently mixed into the base
  engine: `strategy_engine.recommend` stays unchanged, and the insurance study
  rule is never the coach's final action (insurance advice stays NO). Without a
  true count the coach uses basic strategy.
- **The probability / EV layer is approximate and advisory.** The probability &
  EV advisor (v1.12.0: `app/probability_advisor.py`) must clearly label its
  estimates as approximate and must never override the main recommendation
  without explicit validation and tests. It reads the engine / coach for the
  recommended action and surfaces a clear advisory warning when the best-EV
  action differs. It must stay fast and dependency-free (no large simulations),
  and must not change `strategy_engine.recommend` or the counting math.
- **Adaptive local learning must not change the recommendation without explicit
  validation.** The adaptive-learning layer (v1.13.0: `app/adaptive_learning.py`)
  must keep history, variance, sample size, and the mathematical strategy as
  separate concerns. It may only personalise explanations, detect patterns, flag
  weak spots, recommend practice, and show local context - it must never change
  the main recommended action based on short-term local results, promise an
  edge, or make exact predictions. The main action always comes from
  `strategy_engine.recommend` and the count math, which it must not modify.
  Learning must stay local, transparent, and reversible: read-only over the
  git-ignored `.blackjack_coach/` outcomes, with no network, cloud, database, or
  external dependencies, and no money, bankroll, accounts, tokens, screenshots,
  or sensitive data. Confidence must be LOW below 10 total records, and a spot
  with fewer than 5 records must be flagged as a small sample.
- **Composition-aware probabilities must separate exact, approximate, and
  advisory.** The composition-aware EV layer (v1.14.0: `app/probability_advisor.py`)
  must clearly distinguish exact / finite-shoe computation (the dealer
  distribution from the remaining-card composition), approximation (player
  HIT/DOUBLE one-card look-ahead and the simplified SPLIT EV), and advisory
  output. It must not overwrite the main strategy recommendation without
  explicit validation, must label its approximations, must surface a clear
  warning for inconsistent / impossible compositions (never negative counts),
  and must not change `strategy_engine.recommend` or the Hi-Lo counting math. It
  must stay dependency-free and fast (no large/slow simulations).
- **Split / re-split EV must separate exact, approximate, and simplified.** The
  split EV layer (v1.15.0: `app/probability_advisor.py`) must clearly
  distinguish exact computation (the finite-shoe dealer distribution, the
  re-split tree up to `max_split_hands`, and split aces that take exactly one
  card), approximation (hittable sub-hand one-card look-ahead and ignored
  inter-hand depletion), and advisory output (reported via
  `is_exact_for_supported_rules`). It must respect the profile's split rules
  (`split_allowed`, `resplit_allowed`, `max_split_hands`, `hit_split_aces`,
  double-after-split), must never overwrite the main strategy recommendation
  without explicit validation, and must not change `strategy_engine.recommend`
  or the Hi-Lo counting math. It must stay deterministic / memoised
  (no Monte Carlo) and dependency-free.
- **The player EV decision tree must separate strategy, advisory EV, exactness,
  and approximation.** The player EV tree (v1.16.0: `app/probability_advisor.py`)
  must distinguish the main strategy (unchanged), advisory EV, exact computation
  (the finite-shoe dealer distribution and the fully enumerated
  hit/stand/double/surrender tree for non-pair hands), and documented
  approximation (fixed remaining-composition draw probabilities with no
  intra-hand depletion, the dealer distribution from the pre-action shoe,
  ten-value aggregation, and the split sub-hand model). It must never overwrite
  the main strategy recommendation without explicit validation, must report its
  exactness via `is_exact_for_supported_rules`, and must not change
  `strategy_engine.recommend` or the Hi-Lo counting math. It must stay
  deterministic / memoised (no Monte Carlo) and dependency-free.
- **EV snapshots are a local advisory audit.** The EV-snapshot history and
  Strategy-vs-EV review (v1.17.0: `app/ev_history.py`) must never change the
  main strategy recommendation, never override `strategy_engine.recommend`, and
  never modify the Hi-Lo counting math, the probability / EV advisor, adaptive
  learning, guided coaching, outcome history, or session history. When the
  advisory best-EV action differs from the recommendation, the review only
  *reports* it - it is never applied. Snapshots store only a safe local summary
  (profile, cards, dealer upcard, decks, optional true count / seen cards, the
  recommended and best-EV actions, per-action EVs, the EV gap, agreement, and
  documentation notes) and must never store money, bankroll, real bets, wagers,
  balances, accounts, tokens, screenshots, or any sensitive/personal data, with
  no database, network, or cloud. Saved files live under the git-ignored
  `.blackjack_coach/ev_snapshots` directory (unless the user passes `--ev-dir`)
  and are never committed. It must stay dependency-free with no large/slow
  simulations.
- **Strategy-vs-EV explanations must keep the layers separate.** The
  Strategy-vs-EV explanation engine (v1.18.0: `app/ev_explainer.py`) must always
  separate the recommended action, the advisory EV action, the size of the EV
  gap, the limitations of the EV model, and the final decision. It must never
  convert the advisory EV into an automatic override of the main strategy: when
  they differ it only reports and explains the difference, and the coach
  recommendation stands. It must never change `strategy_engine.recommend`, the
  Hi-Lo counting math, the probability / EV advisor, adaptive learning, guided
  coaching, outcome history, session history, or the EV-snapshot history, and it
  must stay dependency-free with no network, cloud, database, or sensitive data.
- **Exportable reports are local and must not include sensitive data.** The
  learning reports (v1.19.0: `app/reporting.py`, the `report` command) are local
  and read-only, and must keep training, outcomes, EV advisory, and practice
  recommendations in clearly separated sections. They must never include money,
  bankroll, real bets, accounts, tokens, screenshots, or any sensitive/personal
  data, and no private filesystem paths beyond the report's own output location.
  Reports must never change `strategy_engine.recommend`, the Hi-Lo counting
  math, or any of the upstream summaries they combine, and must stay
  dependency-free with no network, cloud, or database. Report files live under
  the git-ignored `.blackjack_coach/reports` tree (unless the user passes an
  explicit `--output` path) and are never committed.
- **Dashboards are local and must not include sensitive data.** The per-profile
  dashboards (v1.20.0: `app/dashboard.py`, the `dashboard` command) are local
  and read-only, and must keep training, outcomes, EV advisory, Strategy-vs-EV
  disagreements, and practice recommendations in clearly separated sections.
  They must never include money, bankroll, real bets, accounts, tokens,
  screenshots, or any sensitive/personal data, and no private filesystem paths
  beyond the dashboard's own output location. They must use no external chart
  libraries (trends are plain text / Markdown only) and must never change the
  main strategy - they only suggest practice. Dashboards must not change
  `strategy_engine.recommend`, the Hi-Lo counting math, or any upstream summary
  they combine, and must stay dependency-free with no network, cloud, or
  database. Dashboard files live under the git-ignored `.blackjack_coach/reports`
  tree (unless the user passes an explicit `--output` path) and are never
  committed.
- **Drills are local practice training built on the engine.** The weak-spot
  drill generator (v1.21.0: `app/drill_generator.py`, the `drill` command) must
  obtain the correct action for every drill from the existing
  `strategy_engine.recommend` / decision audit - it must never duplicate or
  re-implement strategy rules. It must never change the main strategy
  recommendation, the Hi-Lo counting math, adaptive learning, guided coaching,
  outcome / session history, the EV-snapshot history, the Strategy-vs-EV engine,
  the reporting module, or the dashboard. It suggests and runs practice without
  promising results, stores / exports no money, bankroll, real bets, accounts,
  tokens, screenshots, or sensitive/personal data, and stays dependency-free
  with no network, cloud, or database.
- **Drill history is local training only.** The drill-session history and spaced
  review (v1.22.0: `app/drill_history.py`, the `drill --save` / `drill --review`
  flags) are local and read-only. They must never re-derive or change the
  correct answers (these always come from the existing drill results / strategy
  engine), and must never change `strategy_engine.recommend`, the Hi-Lo counting
  math, adaptive learning, guided coaching, outcome / session history, the
  EV-snapshot history, the Strategy-vs-EV engine, the reporting module, the
  dashboard, or the drill generator. They store no money, bankroll, real bets,
  accounts, tokens, screenshots, or sensitive/personal data, suggest review
  without promising results, and stay dependency-free with no network, cloud, or
  database. Drill-session files live under the git-ignored
  `.blackjack_coach/drill_sessions` tree (unless the user passes a `--drill-dir`
  path) and are never committed.
- **The review scheduler is local and only suggests practice.** The drill review
  scheduler & streaks (v1.23.0: `app/review_scheduler.py`, the `review-queue`
  command) are local and read-only. They must never change the main strategy
  recommendation, the correct answers, or the engine math, and must never change
  `strategy_engine.recommend`, the Hi-Lo counting math, adaptive learning,
  guided coaching, outcome / session history, the EV-snapshot history, the
  Strategy-vs-EV engine, the reporting module, the dashboard, the drill
  generator, or the drill history. They store / export no money, bankroll, real
  bets, accounts, tokens, screenshots, or sensitive/personal data, suggest
  review without promising results, and stay dependency-free with no network,
  cloud, or database. Exported review queues live under the git-ignored
  `.blackjack_coach/reports` tree (unless the user passes an explicit `--output`
  path) and are never committed.
- **Practice packs are local and only suggest practice.** The daily
  practice-pack generator (v1.24.0: `app/practice_pack.py`, the `practice-pack`
  command) is local and read-only. The correct play for every item must come
  from the existing strategy engine (via the drill generator) - it must never
  duplicate or re-derive strategy logic. It must never change the main strategy
  recommendation, the correct answers, or the engine math, and must never change
  `strategy_engine.recommend`, the Hi-Lo counting math, adaptive learning,
  guided coaching, outcome / session history, the EV-snapshot history, the
  Strategy-vs-EV engine, the reporting module, the dashboard, the drill
  generator, the drill history, or the review scheduler. It stores / exports no
  money, bankroll, real bets, accounts, tokens, screenshots, or sensitive/
  personal data, suggests practice without promising results, and stays
  dependency-free with no network, cloud, or database. Exported packs live under
  the git-ignored `.blackjack_coach/reports` tree (unless the user passes an
  explicit `--output` path) and are never committed.
- **Practice-pack completion history is local and only records practice.** The
  practice-pack completion history (v1.25.0: `app/practice_pack_history.py`, the
  `practice-pack --complete` / `--progress` flags) is local and read-only. It
  must never change the main strategy recommendation, the correct answers, or
  the engine math, and must never change `strategy_engine.recommend`, the Hi-Lo
  counting math, adaptive learning, guided coaching, outcome / session history,
  the EV-snapshot history, the Strategy-vs-EV engine, the reporting module, the
  dashboard, the drill generator, the drill history, the review scheduler, or
  the practice-pack generator. It stores no money, bankroll, real bets,
  accounts, tokens, screenshots, or sensitive/personal data, records practice
  without promising results, and stays dependency-free with no network, cloud,
  or database. Completion files live under the git-ignored
  `.blackjack_coach/practice_packs` tree (unless the user passes a `--pack-dir`
  path) and are never committed.
- **Repeat packs are local and only suggest practice.** The repeat-pack
  generator (v1.26.0: `app/repeat_pack.py`, the `repeat-pack` command) is local
  and read-only. The correct play for every item must come from the existing
  strategy engine (via the drill generator) - it must never duplicate or
  re-derive strategy logic. It must never change the main strategy
  recommendation, the correct answers, or the engine math, and must never change
  `strategy_engine.recommend`, the Hi-Lo counting math, adaptive learning,
  guided coaching, outcome / session history, the EV-snapshot history, the
  Strategy-vs-EV engine, the reporting module, the dashboard, the drill
  generator, the drill history, the review scheduler, the practice-pack
  generator, or the practice-pack completion history. It stores / exports no
  money, bankroll, real bets, accounts, tokens, screenshots, or sensitive/
  personal data, suggests practice without promising results, and stays
  dependency-free with no network, cloud, or database. Exported repeat packs
  live under the git-ignored `.blackjack_coach/reports` tree (unless the user
  passes an explicit `--output` path) and are never committed.
- **Repeat-pack completion history is local and only records practice.** The
  repeat-pack completion history (v1.27.0: `app/repeat_pack_history.py`, the
  `repeat-pack --complete` / `--progress` flags) is local and read-only. It must
  never change the main strategy recommendation, the correct answers, or the
  engine math, and must never change `strategy_engine.recommend`, the Hi-Lo
  counting math, adaptive learning, guided coaching, outcome / session history,
  the EV-snapshot history, the Strategy-vs-EV engine, the reporting module, the
  dashboard, the drill generator, the drill history, the review scheduler, the
  practice-pack generator, the practice-pack completion history, or the
  repeat-pack generator. It stores no money, bankroll, real bets, accounts,
  tokens, screenshots, or sensitive/personal data, records practice without
  promising results, and stays dependency-free with no network, cloud, or
  database. Completion files live under the git-ignored
  `.blackjack_coach/repeat_packs` tree (unless the user passes a `--repeat-dir`
  path) and are never committed.
- **The correction dashboard is local and only summarises practice.** The
  missed-spot correction dashboard (v1.28.0: `app/correction_dashboard.py`, the
  `correction-dashboard` command) is local and read-only. It must never change
  the main strategy recommendation, the correct answers, or the engine math, and
  must never change `strategy_engine.recommend`, the Hi-Lo counting math,
  adaptive learning, guided coaching, outcome / session history, the EV-snapshot
  history, the Strategy-vs-EV engine, the reporting module, the dashboard, the
  drill generator, the drill history, the review scheduler, the practice-pack
  generator, the practice-pack completion history, the repeat-pack generator, or
  the repeat-pack completion history. It stores / exports no money, bankroll,
  real bets, accounts, tokens, screenshots, or sensitive/personal data,
  summarises practice without promising results, and stays dependency-free with
  no network, cloud, or database. Exported dashboards live under the git-ignored
  `.blackjack_coach/reports` tree (unless the user passes an explicit `--output`
  path) and are never committed.
- **Correction action plans are local and only suggest practice.** The
  correction action plan (v1.29.0: `app/correction_plan.py`, the
  `correction-plan` command) is local and read-only. It must never execute any
  suggested command automatically, never change the main strategy
  recommendation, the correct answers, or the engine math, and never change
  `strategy_engine.recommend`, the Hi-Lo counting math, adaptive learning,
  guided coaching, outcome / session history, the EV-snapshot history, the
  Strategy-vs-EV engine, the reporting module, the dashboard, the drill
  generator, the drill history, the review scheduler, the practice-pack
  generator, the practice-pack completion history, the repeat-pack generator,
  the repeat-pack completion history, or the correction dashboard. It must not
  duplicate strategy logic (it reads local summaries and references existing
  commands only), stores / exports no money, bankroll, real bets, accounts,
  tokens, screenshots, or sensitive/personal data, and stays dependency-free
  with no network, cloud, or database. Exported plans live under the
  git-ignored `.blackjack_coach/reports` tree (unless the user passes an
  explicit `--output` path) and are never committed.
- **The Web Coach UI is a local presentation layer only.** The Streamlit Web
  Coach UI (v2.0.0: `app/web_adapter.py` and `web/streamlit_app.py`, the `web`
  command; extended in v2.1.0 with card buttons, quick examples, clear / reset,
  a colour-coded recommendation, and a mobile-friendly layout) is local-only and
  must never change the main strategy recommendation, the correct answers, or
  the engine math, never override the recommendation with EV, and never change
  `strategy_engine.recommend`, the Hi-Lo counting math, or any engine module.
  The v2.1.0 display-only helpers (`WEB_CARD_RANKS`, `WEB_QUICK_EXAMPLES`,
  `action_visual`) are presentation / input only and must not touch strategy,
  counting, or EV. It must never run external commands automatically (no shell,
  no subprocess, no network), must add no FastAPI / Telegram / database / cloud,
  and must handle no money, bankroll, accounts, tokens, or sensitive/personal
  data. `app/web_adapter.py` must stay Streamlit-free and testable; the
  Streamlit UI imports the adapter, never the reverse. Streamlit is an optional
  `web` dependency and must not be required by the engine, the CLI, or the test
  suite, and the CLI must keep working unchanged.
- **The round-result tracker is local, educational, and outcome-separated.**
  The v2.2.0 round-result tracker (`app/round_result.py` and the web-adapter
  wrappers `WebRoundInput` / `build_web_round_review` / `suggest_web_round_outcome`,
  surfaced in the web "Round result" section) records only what happened in a
  played round - the final cards, the action taken, and the WIN/LOSS/PUSH
  outcome. It must keep **decision quality separate from round outcome**: a
  correct play that loses must never be marked a bad decision, and the outcome
  must never be used to re-grade the decision. The dealer's final cards may be
  recorded but must **never** change the recommendation, which depends only on
  the player cards and the dealer upcard. It must not change
  `strategy_engine.recommend`, the Hi-Lo math, the correct answers, or use EV as
  the main decision. `app/round_result.py` must stay Streamlit-free and
  standard-library only (no network, no external API, no database, no
  login/auth). It must store no money, bankroll, bets, wagers, balances,
  accounts, tokens, screenshots, or personal data. The in-web history is
  session-only; optional JSON persistence must live under the git-ignored
  `.blackjack_coach/` tree and must never be committed.
- **The practice table is a local, simulated demo only.** The v2.3.0 practice
  table (`app/practice_table.py`, surfaced as the web "Practice table (demo)"
  mode) is a local game that **generates and knows its own cards**: it builds,
  shuffles and deals from its own shoe. It must never use a camera, never read
  the screen, never scrape, never connect to a real casino, never automate real
  bets, and never involve real money or a bankroll. It must keep **decision
  quality separate from the round outcome** (a correct play that loses is never
  a bad decision) and must freeze the coach recommendation at the initial
  decision point. It must not change `strategy_engine.recommend`, the Hi-Lo
  math, the coach decisions, or the correct answers, and must not use EV as the
  main decision. `app/practice_table.py` must stay Streamlit-free and reuse the
  existing shoe / dealer-play / outcome code rather than duplicating strategy.
  It must store no money, bankroll, bets, wagers, balances, accounts, tokens,
  screenshots, or personal data; the in-web session history is session-only. No
  FastAPI, no Telegram, no external API, no database, no login/auth, and the CLI
  must keep working unchanged.
- **The learning review is local, educational, and outcome-separated.** The
  v2.4.0 practice-table learning review (`app/practice_review.py`, surfaced in
  the web Practice table mode) explains rounds, categorises conclusions, tracks
  weak spots, gives next-time advice, suggests drills, and builds a dashboard.
  It must **never use the round outcome to call a correct decision a mistake**:
  a "mistake" means only that the action differed from the coach, and a correct
  decision that loses must be tracked as variance, never as an error. A win
  after a non-recommended action must never be presented as automatically good.
  It must not change `strategy_engine.recommend`, the Hi-Lo math, the coach
  decisions, or the correct answers, and must not use EV as the main decision.
  `app/practice_review.py` must stay Streamlit-free; it must store no money,
  bankroll, bets, accounts, tokens, screenshots, or personal data (the session
  history is in-memory only), and add no camera / screen reading / scraping /
  external API / database / login. The CLI must keep working unchanged.
- **The rule-profile comparison is a local/demo study aid only.** The v2.5.0
  rule-profile comparison (`app/profile_comparison.py`, surfaced as the web
  "Rule profile comparison" panel) auto-plays many simulated rounds under
  several profiles - always following the coach - and reports WIN / LOSS / PUSH
  behaviour per profile so the user can study which rules tend to be friendlier
  or harder. It must reuse `app.practice_table.simulate_following_coach` and be
  deterministic for a fixed seed. It is a study aid that **must never claim a
  real-world edge or guarantee any result**, must not use EV as the decision,
  and must not change `strategy_engine.recommend`, the Hi-Lo math, the coach
  decisions, or the correct answers. `app/profile_comparison.py` must stay
  Streamlit-free; it must involve no money, bankroll, real betting, casino
  connectivity, camera, screen reading, scraping, external API, database, or
  login, and the CLI must keep working unchanged.
- **Net demo units and the loss audit are demo-only study aids, never profit.**
  The v2.5.0 net-units accounting (1-unit base hand, DOUBLE +/-2, SURRENDER
  -0.5), loss audit (correct vs mistake losses; bust / dealer-made-hand /
  double / surrender losses) and coach sanity check are computed only from the
  local auto-play simulation. They must **never be presented as real-world
  profit, EV guidance, or a guarantee**, must not introduce money, bankroll, or
  bets, and must keep decision quality separate from outcome (a correct decision
  that loses is a correct loss, not a mistake). Natural blackjack is not paid
  3:2 in the demo and this limitation must be stated, not hidden.
- **The demo balance is practice points, never real money or a betting system.**
  The v2.5.0 demo balance (`simulate_demo_balance` / `DemoBalanceResult`,
  surfaced in the simulation and comparison panels) is a flat-bet running total
  of **demo points only**. It must use a single flat base bet (no Martingale,
  progressive, all-in, or any bet-after-result progression), must never let the
  balance go negative (it stops early when it cannot cover the next bet), and
  must never be presented as real money, bankroll advice, a betting strategy, or
  a profit prediction. It must keep reusing the existing simulation engine and
  must not change `strategy_engine.recommend`, the Hi-Lo math, or the coach
  decisions.

## 8. Release Rules

For a tagged release (e.g. **v1.0.0**), all of the following must hold before
the release pull request is merged:

- All automated tests pass (`python -m pytest`) locally and in CI.
- CI is **green** for the release branch (lint + tests on all supported Python
  versions).
- No secrets, credentials, `.env` files, or API tokens are present anywhere in
  the repository.
- No sensitive data, private PDFs, or screenshots are committed.
- No changes outside the educational/simulated scope (see Section 2).
- **Release notes are mandatory**: a `docs/RELEASE_NOTES_v<version>.md` and a
  matching `CHANGELOG.md` entry must accompany the release.
- The version is bumped consistently in `app.__version__` and `pyproject.toml`.

Tags and GitHub releases are created only **after** the release PR is merged.

## 9. Responsible-Use Notice

This tool is for learning and entertainment. Gambling involves financial risk
and can be addictive. Users are responsible for complying with all applicable
laws and the rules of any venue they visit. If gambling is causing harm, seek
support from a local problem-gambling helpline.
