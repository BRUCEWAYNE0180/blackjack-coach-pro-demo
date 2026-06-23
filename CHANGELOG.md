# Changelog

All notable changes to Blackjack Coach Pro Demo are documented here. This
project is an educational / practice tool only — it never connects to a real
casino, places real bets, uses a camera/video, or promises winnings.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and the project follows semantic-ish versioning for an educational tool.

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
