# Changelog

All notable changes to Blackjack Coach Pro Demo are documented here. This
project is an educational / practice tool only — it never connects to a real
casino, places real bets, uses a camera/video, or promises winnings.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and the project follows semantic-ish versioning for an educational tool.

## [1.4.0] - 2026-06-23

Expanded rule profiles. Adds a range of professional rule profiles and helpers
so the coach understands and explains more blackjack configurations. No changes
to the basic-strategy engine, Hi-Lo math, simulator, split handling, or
scoring.

### Added

- Extended `RuleProfile` with professional metadata: `number_of_decks` (alias
  of `decks`), `resplit_allowed`, `max_split_hands`, `hit_split_aces`,
  `profile_description`, and `notes`.
- Nine new profiles: `SINGLE_DECK_H17_NDAS_NS`, `SINGLE_DECK_S17_DAS_LS`,
  `DOUBLE_DECK_H17_DAS_NS`, `DOUBLE_DECK_S17_DAS_LS`, `FOUR_DECK_H17_DAS_LS`,
  `SIX_DECK_H17_DAS_LS`, `SIX_DECK_S17_DAS_LS`, `EIGHT_DECK_H17_DAS_LS`,
  `EIGHT_DECK_S17_DAS_LS` (existing multi-deck profiles unchanged).
- Helpers: `list_rule_profiles`, `get_rule_profile`, `describe_rule_profile`,
  `normalize_profile_key`, and `profile_supports_{surrender,das,resplit,
  hit_split_aces}`.
- `profiles` command (`--list`, `--profile <KEY>`); `diagnose` now includes a
  profile-context section.

### Changed

- All `--profile` commands accept the new profiles. Bumped the package and
  `app.__version__` to **1.4.0**.

### Quality

- Added `tests/test_rules.py` and CLI tests for `profiles` and new-profile
  acceptance. Full suite passing; ruff clean; CI on Python 3.9-3.12.

### Safety

- `resplit_allowed`, `max_split_hands`, and `hit_split_aces` are descriptive
  **metadata** and do not yet change engine play; this is documented wherever
  they appear. The strategy engine, simulator, and scoring are unchanged.
  Responsible scope is preserved in the Safety / Educational Scope section.

## [1.3.0] - 2026-06-23

Professional rules & decision intelligence. Reframes the coach around decision
intelligence and adds a true-count deviation study mode plus a decision
diagnostics command. No changes to the basic-strategy engine, Hi-Lo math,
simulator, split handling, or scoring.

### Added

- `app/deviations.py` with `DeviationRule`, `DeviationRecommendation`, a small
  explicit `DEFAULT_DEVIATION_RULES` study set, `normalize_true_count`,
  `compare_true_count`, `find_matching_deviation`, and
  `recommend_with_deviation` (wraps the engine without modifying it).
- `app/decision_diagnostics.py` with `DecisionDiagnostic` and
  `explain_decision_factors`, which breaks a recommended play into plain factors
  (hand shape, dealer strength, available options, and H17/S17 rule context).
- CLI commands: `deviations` (`--cards/--dealer/--true-count`, `--list`),
  `deviation-quiz` (`--seed`, `--answer`, interactive), and `diagnose`
  (`--cards`, `--dealer`).

### Changed

- Reframed the product (README and docs) as a professional blackjack coach for
  local practice, demo money, video games, recreational tournaments, and
  training, focused on decision intelligence and rules.
- Bumped the package and `app.__version__` to **1.3.0**.

### Quality

- Added `tests/test_deviations.py` and `tests/test_decision_diagnostics.py`,
  plus CLI tests for the new commands. Full suite passing; ruff clean; CI on
  Python 3.9-3.12.

### Safety

- Deviations and diagnostics are **study/coaching aids** that read the stable
  engine and never modify it. The insurance deviation is study-only and does
  not change the engine's insurance recommendation (always NO). Responsible
  scope (no real-money gambling product, no casino connectivity, camera/video,
  or scraping) is preserved in the Safety / Educational Scope section.

## [1.2.0] - 2026-06-23

Local session history. Adds opt-in, local-only progress tracking. No changes
to strategy, counting, simulation, split, or scoring logic.

### Added

- `app/session_history.py` with `SessionRecord`, `HistorySummary`,
  `default_history_dir`, `ensure_history_dir`, `build_session_record`,
  `save_session_record`, `load_session_record`, `list_session_records`, and
  `summarize_history`.
- `--save` and `--history-dir` flags on `quiz-session` and `count-session` to
  store a JSON summary locally and print the saved path.
- A new `history` command (with `--limit` and `--dir`) that summarises saved
  sessions: total, average/best/worst accuracy, and most common weak spots.

### Changed

- Bumped the package and `app.__version__` to **1.2.0**.
- Added `.blackjack_coach/` to `.gitignore` so local history is never
  committed.

### Quality

- Added `tests/test_session_history.py` and CLI history tests. Full suite
  passing; ruff clean; CI on Python 3.9-3.12.

### Safety

- History stores a **summary only** (mode, totals, accuracy, weak spots,
  timestamp, id). It never stores money, bankroll, bets, accounts, personal
  data, secrets, screenshots, or casino data. No database, network, or cloud.

## [1.1.0] - 2026-06-23

Terminal visual polish. This release improves how the CLI looks and reads; it
does **not** change any strategy, counting, simulation, split, or scoring
logic.

### Added

- `app/formatting.py` with dependency-free helpers: `format_header`,
  `format_section`, `format_kv`, `format_list`, `format_result_status`,
  `format_percentage`, `format_warning`, and `format_cards`.
- Clear section headers, aligned key/value rows, a visible `[ CORRECT ]` /
  `[ INCORRECT ]` result badge, and percentage summaries across the CLI.

### Changed

- Reformatted the output of every command (`strategy`, `count`, `simulate`,
  `play`, `quiz`, `count-quiz`, `quiz-session`, `count-session`) for clarity.
- Bumped the package and `app.__version__` to **1.1.0**.

### Quality

- Added `tests/test_formatting.py`; updated CLI tests to assert the clearer
  output. Full suite passing; ruff clean; CI on Python 3.9-3.12.

### Safety

- No logic changes: strategy, Hi-Lo math, simulator, split handling, and quiz
  grading are untouched. Still no casino connectivity, real betting, bankroll,
  camera/video, scraping, or promise of winnings.

## [1.0.0] - 2026-06-23

First stable release. This consolidates the work from v0.1 through v0.9 into a
polished, documented, and packaged educational trainer. No new blackjack
gameplay is introduced in this release; it is release polish only.

### Added

- **Basic strategy engine** for multi-deck **H17** and **S17** profiles, with
  `HIT` / `STAND` / `DOUBLE` / `SPLIT` / `SURRENDER` and legal-action fallbacks.
- **Educational explanations** for every recommendation, plus a clear note that
  **insurance is always declined**.
- **Hi-Lo counting trainer**: tag values, running count, and true count, for
  local / simulated practice only.
- **Local virtual shoe and simulator**: deal hands, play a full hand against
  the dealer (H17/S17 dealer logic and outcome resolution), and play **basic
  pair splits**.
- **Quiz mode**: a single strategy quiz and a Hi-Lo running-count quiz, both
  interactive and non-interactive.
- **Scored training sessions**: multi-question strategy and count sessions with
  accuracy and weak-spot summaries.
- **`blackjack-coach` command** plus a `python -m app.cli` entry point covering
  `strategy`, `count`, `simulate`, `play`, `quiz`, `count-quiz`,
  `quiz-session`, and `count-session`.
- **Documentation**: README quick start and command reference, project rules,
  knowledge base / roadmap, release notes, and this changelog.

### Changed

- Bumped the package and `app.__version__` to **1.0.0**.
- Polished the README front page so the project explains itself in ~30 seconds
  (what it is, install, tests, CLI, and educational scope).

### Quality

- **242 automated tests** covering the evaluator, strategy engine,
  explanations, counting, shoe, simulator, quiz, sessions, CLI, and packaging.
- **Ruff** linting (with import sorting) is clean across `app` and `tests`.
- **GitHub Actions CI** runs lint and tests on Python 3.9-3.12 for every push
  to `main` and every pull request.
- Modern packaging via `pyproject.toml` with a `dev` extra (`pytest`, `ruff`).

### Safety

- No casino connectivity, no real-money betting or bankroll, no camera/video,
  and no screen scraping.
- No betting spread, no Kelly bet sizing, no Illustrious 18, and no insurance
  index plays.
- No web app, and no promise of winnings. Card counting and the simulator are
  strictly local and educational.
