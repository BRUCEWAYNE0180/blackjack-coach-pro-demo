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
