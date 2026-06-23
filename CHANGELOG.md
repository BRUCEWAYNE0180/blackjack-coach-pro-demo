# Changelog

All notable changes to Blackjack Coach Pro Demo are documented here. This
project is an educational / practice tool only — it never connects to a real
casino, places real bets, uses a camera/video, or promises winnings.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and the project follows semantic-ish versioning for an educational tool.

## [1.26.0] - 2026-06-23

Local repeat pack for missed spots. Using the practice-pack completion history
(v1.25.0), the new `repeat-pack` command builds a focused session from the spots
the user keeps getting wrong: recently / repeatedly missed spots, low-accuracy
spots, and skipped spots (topped up with the review queue, or a starter
educational set when there is no missed history). The correct play for every
item comes from the strategy engine - no strategy logic is duplicated, and
nothing changes the recommendation or the Hi-Lo math.

### Added

- `app/repeat_pack.py`: dataclasses `RepeatPackItem`, `RepeatPack`, and
  `RepeatPackExport`, plus `build_repeat_pack` (priority: missed / low-accuracy
  spots -> skipped -> due review-queue items -> educational fallback, with
  `profile_key` / `count` / `today` / `seed` and spot-id de-duplication;
  reconstructs hands from spot ids and gets the correct action from the drill
  generator / strategy engine), `build_repeat_pack_item_from_spot`,
  `render_repeat_pack`, `render_repeat_pack_markdown` (a checklist), and
  `export_repeat_pack`.
- CLI `repeat-pack` command with `--profile`, `--count`, `--seed`, `--today`,
  `--pack-dir`, `--drill-dir`, `--markdown`, `--export`, and `--output`. With no
  missed history it prints a starter educational repeat pack.

### Changed

- Bumped the package and `app.__version__` to **1.26.0**.

### Quality

- New suite `tests/test_repeat_pack.py` (starter pack with no history; `count`
  respected; `seed` determinism; prioritises missed spots; includes skipped
  spots; profile filter; no duplicate spot ids; engine-sourced action; item
  helper; text + Markdown renderers; export saves a file; no sensitive field
  names; and that building a pack never changes `recommend()`) plus
  `TestCliRepeatPack` in `tests/test_cli.py` for the `repeat-pack` command
  (starter pack, `--count`, `--profile`, `--today`/`--seed`, `--markdown`,
  `--export --output`, and `--version` = 1.26.0). Full suite passing; ruff
  clean.

### Safety

- The repeat pack is **local practice training** only. The correct play for
  every item comes from the existing strategy engine (via the drill generator);
  no strategy logic is duplicated. It never changes `strategy_engine.recommend`,
  the Hi-Lo math, adaptive learning, guided coaching, outcome / session history,
  the EV-snapshot history, the Strategy-vs-EV engine, reporting, the dashboard,
  the drill generator, the drill history, the review scheduler, the
  practice-pack generator, or the practice-pack completion history. It stores /
  exports no money, bankroll, real bets, accounts, tokens, screenshots, or any
  sensitive/personal data, suggests practice without promising results, and uses
  no external dependencies, network, cloud, or database. Exported packs live
  under the git-ignored `.blackjack_coach/reports` tree (unless an explicit
  `--output` path is given) and are never committed.

## [1.25.0] - 2026-06-23

Local practice-pack completion history. The v1.24.0 daily practice pack can now
be marked **done**: `practice-pack --complete` saves a local completion record
(items completed, correct / missed / skipped, completion rate, accuracy), and
`practice-pack --progress` summarises pack streaks and progress over time. It
never changes the correct answers, `strategy_engine.recommend`, or the Hi-Lo
math.

### Added

- `app/practice_pack_history.py`: dataclasses `PracticePackCompletionRecord` and
  `PracticePackProgressSummary`, plus `default_practice_pack_history_dir`,
  `ensure_practice_pack_history_dir`, `build_practice_pack_completion_record`
  (whole-pack completion with no detail, or counts / completion rate / accuracy
  from correct / missed / skipped spot ids, with an optional answers mapping),
  `save_practice_pack_completion_record`, `load_practice_pack_completion_record`,
  `list_practice_pack_completion_records` (with `limit` / `profile_key`),
  `summarize_practice_pack_history` (completed vs partial packs, overall
  completion rate / accuracy, pack streaks, weakest / strongest spots, practice
  recommendations, and a data-quality note), and
  `render_practice_pack_progress_summary`.
- CLI `practice-pack` flags `--complete`, `--completed-spots`,
  `--correct-spots`, `--missed-spots`, `--skipped-spots`, `--pack-dir`, and
  `--progress`. `--complete` saves a completion record (and works alongside
  `--export`); `--progress` shows the completion summary; with no data it prints
  a clear message.

### Changed

- Bumped the package and `app.__version__` to **1.25.0**.

### Quality

- New suite `tests/test_practice_pack_history.py` (complete-all with no detail;
  counts / completion rate / accuracy from detail; save/load roundtrip; list
  `limit` / `profile_key`; empty summary; completed vs partial packs;
  consecutive-day streak; weakest / strongest spot detection; renderer; no
  sensitive field names; serialized JSON has no sensitive keys; and that
  building a record never changes `recommend()`) plus
  `TestCliPracticePackHistory` in `tests/test_cli.py` (`--complete` saves a
  file, detail accuracy, `--progress` no-data message, `--progress` with data,
  `--progress --profile`, `--complete --export`, and `--version` = 1.25.0). Full
  suite passing; ruff clean.

### Safety

- Practice-pack completion history is **local practice training** only. It never
  changes the correct answers, `strategy_engine.recommend`, the Hi-Lo math,
  adaptive learning, guided coaching, outcome / session history, the EV-snapshot
  history, the Strategy-vs-EV engine, reporting, the dashboard, the drill
  generator, the drill history, the review scheduler, or the practice-pack
  generator. Records store no money, bankroll, real bets, accounts, tokens,
  screenshots, or any sensitive/personal data, record practice without promising
  results, and use no external dependencies, network, cloud, or database. Saved
  files live under the git-ignored `.blackjack_coach/practice_packs` tree
  (unless a `--pack-dir` is given) and are never committed.

## [1.24.0] - 2026-06-23

Local daily practice-pack generator. A new `practice-pack` command assembles one
ready-to-practise session for "today" by combining the review-queue's due items
(v1.23.0), weak / EV-disagreement / educational spots from the drill generator
(v1.21.0), and the saved drill history (v1.22.0). It never re-derives the
correct play (that always comes from the strategy engine via the drill
generator) and never changes the recommendation or the Hi-Lo math.

### Added

- `app/practice_pack.py`: dataclasses `PracticePackItem`, `PracticePack`, and
  `PracticePackExport`, plus `build_practice_pack` (due review items -> weak ->
  EV / high-gap -> focus-specific -> educational fallback, with `profile_key` /
  `focus` / `count` / `today` / `seed` and spot-id de-duplication),
  `build_pack_item_from_review_item`, `build_pack_item_from_drill_spot`,
  `render_practice_pack`, `render_practice_pack_markdown` (a checklist), and
  `export_practice_pack`.
- CLI `practice-pack` command with `--profile`, `--focus`
  (daily/due/weak/ev/pairs/hard/soft/mixed), `--count`, `--seed`, `--today`,
  `--drill-dir`, `--session-dir`, `--outcome-dir`, `--ev-dir`, `--markdown`,
  `--export`, and `--output`. With no saved history it prints a starter
  educational pack.

### Changed

- Bumped the package and `app.__version__` to **1.24.0**.

### Quality

- New suite `tests/test_practice_pack.py` (starter pack with no history; `count`
  respected; `seed` determinism; no duplicate spot ids; `focus due` prioritises
  due items; `focus pairs` yields pairs; review-item and drill-spot converters;
  text + Markdown renderers; export saves a file; no sensitive field names; and
  that building a pack never changes `recommend()`) plus `TestCliPracticePack`
  in `tests/test_cli.py` for the `practice-pack` command (starter pack,
  `--focus due --count`, `--focus ev --profile`, `--today`/`--seed`,
  `--markdown`, `--export --output`, and `--version` = 1.24.0). Full suite
  passing; ruff clean.

### Safety

- The practice pack is **local practice training** only. The correct play for
  every item comes from the existing strategy engine (via the drill generator);
  no strategy logic is duplicated. It never changes `strategy_engine.recommend`,
  the Hi-Lo math, adaptive learning, guided coaching, outcome / session history,
  the EV-snapshot history, the Strategy-vs-EV engine, reporting, the dashboard,
  the drill generator, the drill history, or the review scheduler. It stores /
  exports no money, bankroll, real bets, accounts, tokens, screenshots, or any
  sensitive/personal data, suggests practice without promising results, and uses
  no external dependencies, network, cloud, or database. Exported packs live
  under the git-ignored `.blackjack_coach/reports` tree (unless an explicit
  `--output` path is given) and are never committed.

## [1.23.0] - 2026-06-23

Local drill review scheduler & streaks. The v1.22.0 drill history is now turned
into a practical spaced-repetition queue: a new `review-queue` command shows
which spots are due today, overdue, and upcoming, and tracks practice streaks.
Weak spots come back soon, learning spots later, mastered spots much later. It
never re-derives the correct play (that comes from the saved drill results /
strategy engine) and never changes the recommendation or the Hi-Lo math.

### Added

- `app/review_scheduler.py`: dataclasses `ReviewScheduleItem`, `ReviewQueue`,
  and `DrillStreakSummary`, plus `parse_date_or_today`, `calculate_due_date`
  (NEW = today, WEAK = soon, LEARNING = ~2 days, MASTERED = ~7 days),
  `build_review_queue` (loads drill history, schedules each spot, sorts by due /
  priority / soonest / accuracy, with `profile_key` / `limit` / `today` /
  `due_only`), `build_drill_streak_summary` (active days, current / longest
  streak, last practice date), `render_review_queue`, `render_streak_summary`,
  `render_review_queue_markdown`, and `export_review_queue`.
- CLI `review-queue` command with `--profile`, `--limit`, `--drill-dir`,
  `--today`, `--due-only`, `--streaks`, `--markdown`, `--export`, and
  `--output`. With no saved drill sessions it prints a clear message.

### Changed

- Bumped the package and `app.__version__` to **1.23.0**.

### Quality

- New suite `tests/test_review_scheduler.py` (explicit-date parsing; due-date by
  mastery NEW / WEAK / LEARNING / MASTERED; empty queue; queue items from
  sessions; profile filter; due-only filter; limit; empty + consecutive-day
  streaks; text / Markdown renderers; export saves a file; no sensitive field
  names; and that scheduling never changes `recommend()`) plus
  `TestCliReviewQueue` in `tests/test_cli.py` for the `review-queue` command
  (no-data message, with data, `--due-only`, `--streaks`, `--profile`,
  `--today`, `--markdown`, `--export --output`, and `--version` = 1.23.0). Full
  suite passing; ruff clean.

### Safety

- The review scheduler is **local practice training** only. It never re-derives
  or changes the correct answers, and never changes `strategy_engine.recommend`,
  the Hi-Lo math, adaptive learning, guided coaching, outcome / session history,
  the EV-snapshot history, the Strategy-vs-EV engine, reporting, the dashboard,
  the drill generator, or the drill history. It stores / exports no money,
  bankroll, real bets, accounts, tokens, screenshots, or any sensitive/personal
  data, suggests review without promising results, and uses no external
  dependencies, network, cloud, or database. Exported queues live under the
  git-ignored `.blackjack_coach/reports` tree (unless an explicit `--output`
  path is given) and are never committed.

## [1.22.0] - 2026-06-23

Local drill-session history & spaced review. The v1.21.0 drill generator can now
**remember** your graded drills: save them with `drill --answer ... --save`, and
`drill --review` computes per-spot mastery (NEW / WEAK / LEARNING / MASTERED) and
suggests what to review next - a light, local spaced-repetition layer. It never
re-derives the correct play (that always comes from the strategy engine) and
never changes the recommendation or the Hi-Lo math.

### Added

- `app/drill_history.py`: dataclasses `DrillSessionRecord`, `DrillSpotHistory`,
  and `DrillReviewSummary`, plus `default_drill_history_dir`,
  `ensure_drill_history_dir`, `build_drill_session_record` (from a `DrillPlan` +
  graded `DrillResult`s), `save_drill_session_record`,
  `load_drill_session_record`, `list_drill_session_records` (with `limit` /
  `profile_key`), `build_spot_history` (groups by spot / profile and assigns a
  mastery level), and `summarize_drill_history` (mastered / weak / due-review
  spots, overall accuracy, a data-quality note, and practice recommendations).
- CLI `drill` flags `--save`, `--drill-dir`, `--review`, and `--due-only`.
  `drill --answer ... --save` saves the graded result and prints the path;
  `drill --review` shows the mastery / spaced-review summary; `--due-only`
  narrows it to spots still needing work. `--save` without `--answer` prints a
  clear error, and `--review` with no history prints a clear message.

### Changed

- Bumped the package and `app.__version__` to **1.22.0**.
- `dashboard` text / Markdown now also point to `drill --review` (no dashboard
  data change).

### Quality

- New suite `tests/test_drill_history.py` (correct / incorrect / accuracy in a
  session record; save/load roundtrip; `list` with `limit` and `profile_key`;
  per-spot grouping; mastery NEW / WEAK / LEARNING / MASTERED; empty and
  populated summaries; weak / mastered detection; no sensitive field names; and
  that building history never changes `recommend()`) plus `TestCliDrillHistory`
  in `tests/test_cli.py` for the `drill --save` / `--review` / `--due-only`
  flows, the `--save` requires-`--answer` error, the no-history message, and a
  profile-scoped review. Full suite passing; ruff clean.

### Safety

- Drill history is **local practice training** only. It never re-derives or
  changes the correct answers (these come from the existing drill results /
  strategy engine) and never changes `strategy_engine.recommend`, the Hi-Lo
  math, adaptive learning, guided coaching, outcome / session history, the
  EV-snapshot history, the Strategy-vs-EV engine, reporting, the dashboard, or
  the drill generator. Records store no money, bankroll, real bets, accounts,
  tokens, screenshots, or any sensitive/personal data, and suggest review
  without promising results. Saved files live under the git-ignored
  `.blackjack_coach/drill_sessions` tree (unless a `--drill-dir` is given) and
  are never committed. No external dependencies, no network / cloud / database.

## [1.21.0] - 2026-06-23

Local weak-spot drill generator. A new `drill` command turns the coach's "what
to practise" guidance into focused practice sessions: it builds drills from your
weak spots, high-loss hands, and Strategy-vs-EV disagreement spots (or a small
educational set when there is no history), poses them, and grades your answer.
The correct play for every drill comes from the stable strategy engine - this
never duplicates strategy rules and never changes the recommendation or the
Hi-Lo math.

### Added

- `app/drill_generator.py`: dataclasses `DrillSpot`, `DrillPlan`, and
  `DrillResult`, plus `classify_drill_category`, `build_drill_spot_from_hand`
  (correct action via `strategy_engine.recommend`; supports suited input),
  `build_drill_plan` (prioritises EV disagreement / weak / high-variance spots
  from local history with `focus`, `count`, and `seed`; falls back to a
  well-known educational set), `grade_drill_answer` (accepts H/S/D/P/R or full
  names), `render_drill_plan`, and `render_drill_result`.
- CLI `drill` command with `--profile`, `--focus`
  (weak/pairs/soft/hard/surrender/ev/mixed), `--count`, `--seed`, `--answer`,
  `--spot`, `--session-dir`, `--outcome-dir`, `--ev-dir`, and `--plan-only`.
  Without `--answer` it prints the plan and poses a drill; with `--answer` it
  grades the selected drill. An invalid action prints a clear error.

### Changed

- Bumped the package and `app.__version__` to **1.21.0**.
- `dashboard` text / Markdown now point to `drill --focus weak` for practising
  the highlighted spots (no change to dashboard data).

### Quality

- New suite `tests/test_drill_generator.py` (category classification; spot
  builder returns the engine's action and supports suited input; no-history
  fallback; `count` / `seed` determinism; `focus pairs` / `focus hard`
  filtering; invalid focus raises; answer grading for H/HIT, correct, and
  incorrect; plan / result renderers; and that building drills never changes
  `recommend()`) plus `TestCliDrill` in `tests/test_cli.py` for the `drill`
  command (no-history plan + question, `--plan-only`, `--focus pairs --count`,
  `--seed`/`--spot`/`--answer`, the invalid-answer error, `--profile`, and
  `--version` = 1.21.0). Full suite passing; ruff clean.

### Safety

- Drills are **local practice training** only: the correct play always comes
  from the existing strategy engine (no duplicated rules), and the generator
  never changes `strategy_engine.recommend`, the Hi-Lo math, adaptive learning,
  guided coaching, outcome / session history, the EV-snapshot history, the
  Strategy-vs-EV engine, the reporting module, or the dashboard. It stores no
  money, bankroll, real bets, accounts, tokens, screenshots, or any
  sensitive/personal data, suggests practice without promising results, and uses
  no external dependencies, network, cloud, or database.

## [1.20.0] - 2026-06-23

Local per-profile training dashboard & trends. A new `dashboard` command turns
the v1.19.0 reports into a more useful decision-making view: it groups the local
session history, outcomes, EV snapshots, Strategy-vs-EV disagreements, weak
spots, and practice recommendations by rule profile, adds a simple
recent-sample trend, and prints a concrete next-practice plan. Everything stays
local and read-only; it never changes the strategy recommendation or the Hi-Lo
math and stores / exports no sensitive data.

### Added

- `app/dashboard.py`: dataclasses `DashboardProfileSummary`,
  `DashboardTrendPoint`, and `DashboardSummary`, plus `build_profile_dashboard`
  (groups outcomes / EV snapshots by profile and combines `summarize_history`,
  `summarize_outcomes`, `summarize_ev_snapshots`, `build_learning_summary`, and
  `summarize_disagreement_explanations`), `build_dashboard_trends` (simple
  recent-sample buckets `recent_1..3`; no date parsing required),
  `recommend_next_practice_plan` (weak spots, low accuracy, high EV
  disagreement, high loss rate), `render_dashboard_text`,
  `render_dashboard_markdown`, and `export_dashboard` (defaults to a timestamped
  file under `./.blackjack_coach/reports`).
- CLI `dashboard` command with `--profile`, `--limit`, `--session-dir`,
  `--outcome-dir`, `--ev-dir`, `--markdown`, `--export`, and `--output`. Prints
  compact text by default; with no saved history it prints a clear message.

### Changed

- Bumped the package and `app.__version__` to **1.20.0**.
- `report` Markdown now points to `dashboard` for an interactive-style CLI
  summary (no behaviour change to the report data).

### Quality

- New suite `tests/test_dashboard.py` (empty history -> zeros and a clear note;
  totals counted; profile filter; most-practiced detection; next-practice plan
  generation; trends return a list even with little data; plan uses weak spots;
  text / Markdown renderers; export saves a file; no sensitive field names; and
  building the dashboard never changes `recommend()`) plus `TestCliDashboard` in
  `tests/test_cli.py` for the `dashboard` command (no-data message, overview
  with data, `--profile`, `--limit`, `--markdown`, `--export`, custom
  `--output`, and `--version` = 1.20.0). Full suite passing; ruff clean.

### Safety

- The dashboard is a **local, read-only practice aid** only: it stores / exports
  no money, bankroll, real bets, accounts, tokens, screenshots, or any
  sensitive/personal data, and no private filesystem paths beyond its own output
  location. It keeps training, outcomes, EV advisory, disagreements, and
  practice recommendations in clearly separated sections, uses no external chart
  libraries (trends are plain text / Markdown tables), and never changes
  `strategy_engine.recommend`, the Hi-Lo math, adaptive learning, guided
  coaching, outcome / session history, the EV-snapshot history, the
  Strategy-vs-EV explanation engine, or the reporting module. Dashboard files
  live under the git-ignored `.blackjack_coach/reports` tree (unless an explicit
  `--output` path is given) and are never committed. No external dependencies,
  no network / cloud / database.

## [1.19.0] - 2026-06-23

Exportable local-learning reports. A new `report` command combines the local
session history, outcome / win-loss history, EV-snapshot history,
Strategy-vs-EV review, weak / strong spots, and practice recommendations into a
single **Markdown / JSON / CSV** report - handy for reviewing progress or saving
to Notion / GitHub. Everything stays local and read-only; it never changes the
strategy recommendation or the Hi-Lo math and exports no sensitive data.

### Added

- `app/reporting.py`: dataclasses `ReportSummary` and `ExportedReport`, plus
  `build_report_summary` (combines `summarize_history`, `summarize_outcomes`,
  `summarize_ev_snapshots`, `build_learning_summary`, and - when EV snapshots
  exist - `summarize_disagreement_explanations`, with `profile_key` / `limit`
  filters), `render_report_markdown`, `render_report_json`, `render_report_csv`
  (stdlib `csv`, key/value rows; no pandas), `save_report`, and `export_report`
  (defaults to a timestamped file under `./.blackjack_coach/reports`).
- CLI `report` command with `--format` (markdown / json / csv), `--output`,
  `--profile`, `--limit`, `--session-dir`, `--outcome-dir`, `--ev-dir`, and
  `--print`. By default it saves a local Markdown report and prints the path;
  EV snapshots are included automatically when present. An unknown `--format`
  produces a clear error.

### Changed

- Bumped the package and `app.__version__` to **1.19.0**.

### Quality

- New suite `tests/test_reporting.py` (empty history -> zeros and a clear note;
  totals counted from sessions / outcomes / EV snapshots; Markdown contains the
  Overview / Practice recommendations / Strategy-vs-EV sections; valid JSON;
  key,value CSV; Markdown / JSON / CSV export saves a file; custom output path;
  unknown format raises; no sensitive field names exported; and export never
  changes `recommend()`) plus `TestCliReport` in `tests/test_cli.py` for the
  `report` command (no-data file, `--print`, json, csv, custom `--output`,
  profile filter, invalid format error, and counts with history). Full suite
  passing; ruff clean.

### Safety

- Reports are a **local, read-only summary** only: they store no money,
  bankroll, real bets, accounts, tokens, screenshots, or any sensitive/personal
  data, and no private filesystem paths beyond the report's own output location.
  They keep training, outcomes, EV advisory, and practice recommendations in
  clearly separated sections, and never change `strategy_engine.recommend`, the
  Hi-Lo math, adaptive learning, guided coaching, outcome / session history, the
  EV-snapshot history, or the Strategy-vs-EV explanation engine. Reports live
  under the git-ignored `.blackjack_coach/reports` tree (unless an explicit
  `--output` path is given) and are never committed. No external dependencies,
  no network / cloud / database.

## [1.18.0] - 2026-06-23

Strategy-vs-EV explanation engine. The probability / EV advisor stays advisory
only, but it now **explains itself**: a clear, professional account of when the
coach's main recommendation agrees with the advisory best-EV action and when it
differs - and, when it differs, why (a tiny / small / medium / large EV gap, the
remaining-shoe composition, the true count, split / re-split context, a
surrender threshold, or the documented limits of the EV model). It never changes
the main recommendation, never overrides `strategy_engine.recommend`, never
turns the advisory EV into the final decision, and never touches the Hi-Lo math.

### Added

- `app/ev_explainer.py`: dataclasses `EVGapCategory`, `StrategyEVDisagreement`,
  and `DisagreementExplanationSummary`, plus `classify_ev_gap` (TINY `[0, 0.02)`,
  SMALL `[0.02, 0.05)`, MEDIUM `[0.05, 0.15)`, LARGE `[0.15, inf)`, UNKNOWN when
  there is no gap), `explain_strategy_vs_ev` (accepts a `ProbabilityAdvice`, a
  `CompositionAwareProbabilityAdvice`, or an `EVSnapshotRecord`),
  `explain_ev_snapshot_record`, and `summarize_disagreement_explanations`
  (groups snapshots into agrees / tiny / small / medium / large / missing and
  generates review notes).
- CLI `odds --explain-ev` and `coach --show-odds --explain-ev`: append a
  "Strategy vs EV explanation" block (coach recommendation, best EV action, EV
  gap, gap label, explanation, advisory note). `coach --explain-ev` without
  `--show-odds` prints a clear error.
- CLI `ev-review --explain` (Strategy-vs-EV explanations for the top
  disagreement spots) and `ev-review --large-gaps-only` (only LARGE-gap
  snapshots, or MEDIUM when there is no LARGE gap).

### Changed

- Bumped the package and `app.__version__` to **1.18.0**.

### Quality

- New suite `tests/test_ev_explainer.py` (gap classification tiny / small /
  medium / large / unknown; agreement and disagreement explanations; that the
  explanation includes both actions and the gap label; composition / true-count
  mentions; the `EVSnapshotRecord` wrapper; grouped summaries; and that
  explaining never changes `recommend()`) plus `TestCliStrategyVsEVExplanation`
  in `tests/test_cli.py` for `odds --explain-ev`,
  `coach --show-odds --explain-ev`, the requires-`--show-odds` error,
  `ev-review --explain`, `ev-review --large-gaps-only`, and the
  disagreements-only path. Full suite passing; ruff clean.

### Safety

- The explanation engine is an **explanation layer only**: it keeps a clear
  separation between the recommended action, the advisory EV action, the size of
  the gap, the model's limitations, and the final decision, and it never
  converts the advisory EV into an automatic override. No change to
  `strategy_engine.recommend`, the Hi-Lo counting math, adaptive learning,
  guided coaching, outcome history, session history, or the v1.17.0 EV-snapshot
  history. No external dependencies, no network / cloud / database, and no
  sensitive data (no money, bankroll, bets, accounts, tokens, or screenshots).

## [1.17.0] - 2026-06-23

EV snapshot history & Strategy-vs-EV review. The probability / EV advisor stays
advisory only, but you can now save a **local snapshot** of the advisory for a
hand and later review when the coach's main recommendation *agreed* with the
advisory best-EV action and when it *differed*. This improves local self-study
and the transparency of the advisor. It never changes the main recommendation,
never overrides `strategy_engine.recommend`, and never touches the Hi-Lo math.

### Added

- `app/ev_history.py`: dataclasses `EVSnapshotRecord` and `EVReviewSummary`,
  plus `default_ev_history_dir`, `ensure_ev_history_dir`,
  `build_ev_snapshot_record` (accepts a `ProbabilityAdvice` or a
  `CompositionAwareProbabilityAdvice`; extracts the recommended action, the
  advisory best-EV action, the per-action EVs, the recommended action's EV, the
  best EV, and the gap, and flags agreement, split EV, decision tree, and
  composition-aware status), `save_ev_snapshot_record`,
  `load_ev_snapshot_record`, `list_ev_snapshot_records` (with `limit`,
  `profile_key`, and `disagreements_only` filters), and
  `summarize_ev_snapshots` (agreement / disagreement counts, largest EV gaps,
  disagreement spots, practice recommendations, and a data-quality note that
  flags a LOW sample below 10 snapshots).
- CLI `odds` flags `--save-ev-snapshot` and `--ev-dir`: compute the advisory as
  before, save a local EV snapshot, and print the saved path.
- CLI `coach` flags `--save-ev-snapshot` and `--ev-dir` (only with
  `--show-odds`): save the odds snapshot while keeping the main decision intact.
  `--save-ev-snapshot` without `--show-odds` prints a clear error.
- CLI `ev-review` command (`--dir`, `--limit`, `--profile`,
  `--disagreements-only`, `--min-gap`): an "EV Snapshot Review" - total
  snapshots, agreement / disagreement counts and rate, most common profile and
  recommended / best-EV actions, largest EV gaps, disagreement spots, practice
  recommendations, a data-quality note, and warnings. With no saved data it
  prints a clear "use `--save-ev-snapshot` first" message.

### Changed

- Bumped the package and `app.__version__` to **1.17.0**.

### Quality

- New suite `tests/test_ev_history.py` (build a snapshot from a
  composition-aware advisory and from the idealised advisory; agreement and EV
  gap computation; save / load JSON roundtrip; `list` with `limit`,
  `profile_key`, and `disagreements_only`; empty summary; agreement /
  disagreement counts; largest EV gap detection; `min_gap` filtering; LOW-sample
  note; no sensitive fields persisted; building a snapshot never changes
  `recommend()`) plus CLI tests for `odds --save-ev-snapshot`,
  `coach --show-odds --save-ev-snapshot`, the `coach --save-ev-snapshot`
  requires-`--show-odds` error, and `ev-review` (empty, with snapshots,
  `--disagreements-only`, `--profile`, and `--version` = 1.17.0). Full suite
  passing; ruff clean.

### Safety

- EV snapshots are a **local advisory audit only**: they store a safe summary
  (profile, cards, dealer upcard, decks, optional true count / seen cards, the
  recommended and best-EV actions, per-action EVs, the EV gap, agreement, and
  documentation notes) and never store money, bankroll, real bets, accounts,
  tokens, screenshots, or any sensitive/personal data - no database, no network,
  no cloud. Saved files live under the git-ignored `.blackjack_coach/` tree and
  are never committed. The review never overrides the main recommendation
  (advisory differences are reported, not applied), and it makes no change to
  `strategy_engine.recommend`, the Hi-Lo counting math, adaptive learning,
  guided coaching, outcome history, or session history. No external
  dependencies and no large/slow simulations.

## [1.16.0] - 2026-06-23

Full player EV decision tree. v1.15.0 made SPLIT/re-split EV strong, but some
hittable sub-hands still used a one-card-then-stand look-ahead. v1.16.0 replaces
the HIT look-ahead with a recursive optimal hit/stand tree and unifies every
legal action's EV into a single player decision tree, so the advisor is more
professional and less approximate. It remains advisory only and never changes
the recommendation or the Hi-Lo math.

### Added

- `app/probability_advisor.py`: dataclasses `PlayerDecisionEVEstimate` and
  `PlayerEVBranch`, plus `estimate_stand_ev_composition`,
  `estimate_hit_ev_tree` (recursive optimal hit/stand over the remaining
  composition, memoised and depth-capped), `estimate_double_ev_composition`,
  `estimate_surrender_ev`, and `estimate_player_decision_tree_ev` (STAND / HIT /
  DOUBLE / SURRENDER / SPLIT EV in one place, SPLIT delegated to the split
  estimator).
- `odds` (composition-aware) now shows a "Player EV decision tree" block (best
  EV action, EV by action, exactness/approximation note, EV vs recommendation).
- `coach --show-odds` (composition-aware) shows a compact player EV summary and
  whether the advisory best-EV action agrees with the coach's recommendation.

### Changed

- Bumped the package and `app.__version__` to **1.16.0**.
- `build_composition_aware_advice` now evaluates actions through the recursive
  player decision tree and exposes a `decision_tree` field; `best_estimated_action`
  comes from the tree.
- Split sub-hands (`estimate_subhand_ev_after_split`) now play hittable hands
  with the recursive hit/stand tree instead of one-card-then-stand; the split
  approximation note was updated accordingly.

### Quality

- Extended `tests/test_probability_advisor.py` (stand EV: bust = -1, 20 vs 6
  positive; hit tree: hard 11 positive / no first-card bust, hard 20 poor;
  double EV scaled; surrender -0.5 when legal and None otherwise; decision tree
  returns action EVs and a best action; non-pairs exclude SPLIT and pairs
  include it; advice uses the decision tree; the old one-card wording is gone;
  `recommend()` unchanged) plus CLI tests for the Player EV decision tree block
  on `odds` (10,6 / A,7 / 8,8) and `coach --show-odds`. Full suite passing; ruff
  clean.

### Safety

- The player EV tree cleanly separates the main strategy (unchanged), advisory
  EV, exact computation (finite-shoe dealer distribution; fully enumerated
  hit/stand/double/surrender for non-pair hands), and documented approximations
  (fixed remaining-composition draw probabilities with no intra-hand depletion;
  dealer distribution from the pre-action shoe; ten-value aggregation; split
  sub-hand model). It never overrides the recommendation or
  `strategy_engine.recommend`, makes no change to the Hi-Lo counting math,
  adaptive learning, guided coaching, outcome history, or session history, adds
  no external dependencies, and runs no Monte Carlo / slow simulations
  (deterministic + memoised). No money, bankroll, accounts, tokens, screenshots,
  or sensitive data.

## [1.15.0] - 2026-06-23

Composition-aware SPLIT / re-split EV. In v1.14.0 the shoe composition and the
finite-shoe dealer distribution became exact, but SPLIT EV was left simplified.
v1.15.0 replaces that placeholder with a real composition-aware EV for splitting
and re-splitting pairs (A,A / 8,8 / 10,10 / 2,2, ...), respecting the profile's
split rules. It stays advisory only and never changes the recommendation or the
Hi-Lo math.

### Added

- `app/probability_advisor.py`: dataclasses `SplitEVEstimate` and
  `SplitBranchEstimate`; `estimate_split_ev_composition` (pairs only; respects
  `split_allowed`, `resplit_allowed`, `max_split_hands`, `hit_split_aces`, and
  DAS; enumerates the re-split tree against the exact finite-shoe dealer
  distribution), `estimate_subhand_ev_after_split` (per-sub-hand optimal EV with
  memoised re-splits), and `compare_pair_actions_ev` (SPLIT vs HIT/STAND/DOUBLE/
  SURRENDER, sorted by EV).
- `odds` now shows a "Split EV estimate" block for pairs (split rules, estimated
  split EV, sub-hands evaluated, exactness flag, and a compact comparison vs the
  other legal actions).
- `coach --show-odds` shows a compact Split EV line for pairs and whether the
  advisory best-EV action agrees with the coach's recommendation.

### Changed

- Bumped the package and `app.__version__` to **1.15.0**.
- `build_composition_aware_advice` now attaches a `split_estimate` for pairs and
  feeds the real split EV into `best_estimated_action` (still advisory). The
  composition approximation note no longer calls SPLIT "simplified".

### Quality

- Extended `tests/test_probability_advisor.py` (split EV applies only to pairs;
  8,8 vs 6 returns an estimate; A,A respects `hit_split_aces=False` exactly and
  plays normally when `hit_split_aces=True`; re-split respects `max_split_hands`;
  `resplit_allowed=False` blocks re-splits; DAS changes sub-hand EV;
  `compare_pair_actions_ev` includes SPLIT and is sorted; split estimate present
  for pairs and absent for non-pairs; `recommend()` unchanged) plus CLI tests for
  `odds` on 8,8 / A,A / 10,10 and `coach --show-odds` on a pair. Full suite
  passing; ruff clean.

### Safety

- Split/re-split EV cleanly separates exact (finite-shoe dealer; re-split tree;
  one-card split-aces), approximate (hittable sub-hand one-card look-ahead;
  inter-hand depletion ignored), and advisory output, reported via
  `is_exact_for_supported_rules`. It never overrides the coach's final
  recommendation or `strategy_engine.recommend`, makes no change to the Hi-Lo
  counting math, adaptive learning, guided coaching, outcome history, or session
  history, adds no external dependencies, and runs no Monte Carlo / slow
  simulations (deterministic + memoised). No money, bankroll, accounts, tokens,
  screenshots, or sensitive data.

## [1.14.0] - 2026-06-23

Composition-aware probability & EV. The advisor can now use the actual
composition of the remaining shoe - the player's cards, the dealer upcard, and
any seen / removed cards - to compute sharper numbers. The dealer final-total
distribution is computed exactly for that finite shoe; player HIT/DOUBLE EV
stays an approximate one-card look-ahead and SPLIT EV is simplified. It remains
advisory only and never changes the strategy recommendation or the Hi-Lo math.

### Added

- `app/probability_advisor.py`: dataclasses `ShoeComposition` and
  `CompositionAwareProbabilityAdvice`, plus `build_initial_rank_counts`
  (ten-values aggregated, 52 cards/deck), `remove_known_cards` (accepts plain
  and suited cards; never goes negative, warns on inconsistency),
  `build_shoe_composition`, `estimate_player_bust_probability_composition`,
  `estimate_dealer_outcomes_composition` (exact finite-shoe distribution with
  depletion + count-vector memoisation; fast for 6-8 decks),
  `estimate_action_ev_composition`, and `build_composition_aware_advice`.
- CLI `odds` flags: `--seen-cards <cards>`, `--composition-aware`, and
  `--composition` (shows the remaining-shoe summary with compact per-rank
  counts). `--seen-cards` and `--composition` auto-enable composition-aware
  mode.
- CLI `coach` flags: `--seen-cards <cards>` and `--composition-aware`, applied
  to the odds block when combined with `--show-odds` (stacks with
  `--true-count`).

### Changed

- Bumped the package and `app.__version__` to **1.14.0**.
- `odds` / `coach --show-odds` output now indicates composition-aware status
  and (for `odds`) decks and cards remaining; the idealised (non-composition)
  output is unchanged.

### Quality

- Extended `tests/test_probability_advisor.py` (rank-count totals; `remove_known_cards`
  reduction, face collapse, suited cards, and no-negative warning; shoe
  composition removal; composition bust for hard 20 / hard 11 / soft; dealer
  distribution sums to ~1.0 and valid H17 vs S17; composition action EV and the
  simplified-split warning; composition advice returns a `ShoeComposition`,
  keeps the recommended action, warns on inconsistent input, and never changes
  `recommend()`) plus CLI tests for `odds --composition-aware`, `--seen-cards`,
  `--composition`, and `coach --show-odds` composition variants. Full suite
  passing; ruff clean.

### Safety

- The composition-aware layer cleanly separates exact (finite-shoe dealer),
  approximate (player HIT/DOUBLE one-card look-ahead), and simplified (SPLIT)
  computations, and is advisory only - it never overrides the main strategy
  recommendation without explicit validation. No change to
  `strategy_engine.recommend`, the Hi-Lo counting math, adaptive learning,
  guided coaching, outcome history, or session history. No external
  dependencies, no large/slow simulations, and no money, bankroll, accounts,
  tokens, screenshots, or sensitive data.

## [1.13.0] - 2026-06-23

Adaptive local learning. The coach now grows more useful with practice: it
reads your **locally saved** outcome history to detect strong / weak /
high-variance spots, recommend what to practise, and add a personalised
local-history context block to the coach output. This is a read-only learning
layer - it **never** changes the strategy recommendation, the count math, or
the probability advisor, and it makes no promises and no predictions.

### Added

- `app/adaptive_learning.py`: dataclasses `LearningSpot`, `LearningSummary`,
  and `CoachHistoryContext`, plus `classify_hand_spot` (e.g. `hard_16_vs_10`,
  `soft_18_vs_9`, `pair_8_vs_6`, `pair_A_vs_6`, reusing the existing hand
  evaluator), `build_learning_summary` (groups saved `OutcomeRecord`s by
  starting spot / profile / outcome and detects weakest, strongest, and
  high-variance spots with practice recommendations), `build_history_context`
  (local context for one hand), and `format_learning_summary`.
- CLI `learn` command (`--dir`, `--profile`, `--limit`, `--spot`): an
  "Adaptive Learning" summary - total records, profiles seen, most common
  profile, strongest / weakest / high-variance spots, most common outcomes,
  practice recommendations, a data-quality note, and notes. With no saved data
  it prints a clear "use --save-outcome first" message.
- CLI `coach --use-history` (with optional `--history-dir`): appends a "Local
  history context" block (matching records, local win/loss/push rates, a
  practice note, and a caution note), and combines with `--true-count` /
  `--show-odds`.

### Changed

- Bumped the package and `app.__version__` to **1.13.0**.

### Quality

- New suite `tests/test_adaptive_learning.py` (spot classification; empty,
  profile-count, weakest, strongest, and LOW-confidence summaries; history
  context with and without local data and profile filtering; and a guard that
  history never changes the recommended action) plus CLI tests for `learn`
  (empty, with data, profile filter) and `coach --use-history` (with / without
  history, combined with count + odds, action unchanged). Full suite passing;
  ruff clean; CI on Python 3.9-3.12.

### Safety

- Learning is local, transparent, and reversible: it only reads JSON outcomes
  the user chose to save. The main recommended action always comes from basic
  strategy and the count math, never from short-term local results. Confidence
  is LOW below 10 total records, and a spot with fewer than 5 records is flagged
  as a small sample. No change to `strategy_engine.recommend`, the Hi-Lo
  counting math, the probability advisor, guided coaching, outcome history, or
  session history. No network, cloud, database, or external dependencies, and no
  money, bankroll, accounts, tokens, screenshots, or sensitive data.

## [1.12.0] - 2026-06-23

Approximate probability & EV advisor. The coach can now explain risk - player
bust chance, the dealer's final-total distribution, and a rough EV per action -
alongside the recommended play. These are clearly labelled **approximate** and
never override the strategy recommendation.

### Added

- `app/probability_advisor.py`: `PlayerBustEstimate`, `DealerOutcomeEstimate`,
  `ActionEVEstimate`, `ProbabilityAdvice`, and the helpers
  `estimate_player_bust_probability`, `estimate_dealer_outcomes` (deterministic
  recursive enumeration honouring H17/S17), `estimate_action_ev`, and
  `build_probability_advice`. Uses an idealised 13-rank shoe and a one-card
  look-ahead - fast and dependency-free.
- CLI `odds` command (`--cards`, `--dealer`, `--profile`, `--decks`,
  `--true-count`): player bust-if-hit, dealer bust, dealer 17/18/19/20/21/bust
  probabilities, per-action EV estimates, the best estimated action, and the
  approximation note.
- CLI `coach --show-odds`: appends a compact approximate odds summary (bust if
  hit, dealer bust, best estimated action) to the coach output.

### Changed

- Bumped the package and `app.__version__` to **1.12.0**.

### Quality

- New suite `tests/test_probability_advisor.py` (bust estimates, dealer
  distribution sums to ~1, surrender EV -0.5, illegal-action warning, advice
  assembly, engine unchanged) plus CLI tests for `odds` and `coach --show-odds`.
  Full suite passing; ruff clean; CI on Python 3.9-3.12.

### Safety

- Approximate advisory only: probabilities/EV use a simplified model and do not
  claim perfect accuracy. They never override the strategy recommendation (a
  clear advisory warning is shown if the best-EV action differs). No change to
  `strategy_engine.recommend`, Hi-Lo counting math, guided coaching, outcome
  history, or session history. No casino connectivity, real betting, bankroll,
  camera/video, or promise of winnings.

## [1.11.0] - 2026-06-23

Count-aware coach advice. The guided coach can now fold in the educational
true-count deviation study: enter your cards, the dealer upcard, a profile, and
optionally a `--true-count`, and the coach compares basic strategy with the
count-adjusted play and picks a final recommendation. Without a true count the
coach behaves exactly as in v1.10.0. Basic strategy is unchanged
(`strategy_engine.recommend` is never modified) and the insurance study rule is
never the coach's final action.

### Added

- `app/guided_coach.py`: count-aware fields on `CoachStep` (`basic_action`,
  `count_adjusted_action`, `true_count`, `deviation_applied`,
  `deviation_rule_id`, `deviation_title`, `final_recommended_action`,
  `count_note`) and an optional `true_count` on `GuidedCoachResult`.
  `build_coach_step` / `explain_next_best_action` accept `true_count` and
  consult `deviations.recommend_with_deviation`.
- CLI `coach --true-count <n>`: shows the true count, basic action,
  count-adjusted action (when a deviation applies), whether a deviation was
  applied, the deviation rule, and the final recommended action.
- CLI `coach-play --true-count <n>`: shows the true count as advisory context
  per step (the hand is still played with basic strategy).

### Changed

- Bumped the package and `app.__version__` to **1.11.0**.

### Quality

- New count-aware tests in `tests/test_guided_coach.py` (deviation applies /
  does not apply by true count, hard 15/16/10 cases, insurance never final,
  engine unchanged) plus CLI tests for `coach --true-count` and
  `coach-play --true-count`. Full suite passing; ruff clean; CI on Python
  3.9-3.12.

### Safety

- The coach keeps basic action, count-adjusted action, and final recommended
  action separate, and always explains when a deviation changes the play. The
  deviation study stays study-only (insurance never becomes a final action);
  `strategy_engine.recommend`, Hi-Lo counting math, the simulator, outcome
  history, and session history are unchanged. No casino connectivity, real
  betting, bankroll, bet spread, camera/video, or promise of winnings.

## [1.10.0] - 2026-06-23

Professional card display. Cards can now be entered and shown with figures,
suits, and colour - `A♠`, `10♥`, `K♦`, `8♣` - so the coach feels like a complete
blackjack calculator. Hearts and diamonds render in red; spades and clubs use
the terminal's default colour. This is a presentation / input layer only: it
never changes strategy, counting, outcomes, or scoring (every conversion keeps
the plain rank the engine needs).

### Added

- `app/cards.py`: `RenderedCard`, the `SUIT_SYMBOLS` / `SUIT_NAMES` /
  `RED_SUITS` / `BLACK_SUITS` constants, and the helpers `normalize_rank`,
  `normalize_suit`, `parse_card`, `parse_cards`, `cards_to_ranks`,
  `format_card`, `format_cards`, `strip_ansi`, and `assign_display_suits`
  (deterministic decorative suits for simulated cards).
- Card input accepts suits in several forms: `A♠`, `AS`, `A spades`, `Kd`,
  `10♥`, `Q clubs`, as well as the existing suitless `A,7`.
- Global display flags `--no-color` (plain, no ANSI) and `--plain-cards` (ranks
  only, no suit symbols).

### Changed

- The card-facing commands (`coach`, `coach-play`, `play`, `simulate`,
  `diagnose`, `audit`, `split-rules`) now render hands with suits and colour.
  User-typed suits are preserved; simulated hands get deterministic decorative
  suits. Colour is used only on a real terminal (captured / piped output stays
  plain).
- Bumped the package and `app.__version__` to **1.10.0**.

### Quality

- New suite `tests/test_cards.py` (rank/suit normalisation, parsing, colour,
  ANSI stripping, deterministic suits) plus CLI tests for Unicode/letter suit
  input, `--no-color`, and `--plain-cards`. Full suite passing; ruff clean; CI
  on Python 3.9-3.12.

### Safety

- Visual / parsing only: no change to `strategy_engine.recommend`, the hand
  evaluator, Hi-Lo counting, outcomes, scoring, session history, or outcome
  history. The engine always receives plain ranks. No casino connectivity, real
  betting, bankroll, camera/video, scraping, or promise of winnings.

## [1.9.0] - 2026-06-23

Guided coach mode. The coach now picks and explains the best play - the user
asks, the coach decides and teaches. A direct-advice command answers "what do I
do with this hand?", and a guided full-hand command plays a simulated hand where
the coach chooses every action automatically. Basic strategy is unchanged:
`strategy_engine.recommend` is never modified.

### Added

- `app/guided_coach.py`: `CoachStep`, `GuidedCoachResult`, `build_coach_step`,
  `explain_next_best_action`, `build_guided_result`, and
  `play_guided_coach_hand`. Built on the v1.7.0 `decision_audit` and the
  simulator; reuses v1.8.0 outcome records for result labels.
- CLI `coach` command (`--cards`, `--dealer`, `--profile`): the coach's single
  best play with the raw table action, fallback, legal actions, and a clear
  why.
- CLI `coach-play` command (`--decks`, `--seed`, `--profile`,
  `--save-outcome`, `--outcome-dir`): the coach plays a full hand, showing a
  step-by-step recommendation for each decision, the final result, and
  optionally saving the outcome (reusing v1.8.0 outcome history).

### Changed

- `diagnose` now points to `coach` (direct advice) and `audit` (technical
  breakdown).
- Bumped the package and `app.__version__` to **1.9.0**.

### Quality

- New deterministic suite `tests/test_guided_coach.py` plus CLI tests for
  `coach` and `coach-play`. Full suite passing; ruff clean; CI on Python
  3.9-3.12.

### Safety

- Guided coaching keeps recommendation, explanation, the executed action, and
  the outcome separate; the coach decides and the user receives guidance. No
  change to basic strategy, the engine recommendation, deviations, the
  simulator, the matrix/audit tooling, or outcome history. No casino
  connectivity, real betting, bankroll, camera/video, scraping, or promise of
  winnings.

## [1.8.0] - 2026-06-23

Local outcome (win/loss) history. The coach can now record the results of
played practice hands - wins, losses, pushes, surrenders, busts, and split /
re-split results - to a local JSON folder and summarise them, complementing the
v1.7.0 decision tooling. Basic strategy is unchanged:
`strategy_engine.recommend` is never touched.

### Added

- `app/outcome_history.py`: `OutcomeRecord`, `OutcomeSummary`, and the helpers
  `default_outcome_history_dir`, `ensure_outcome_history_dir`,
  `build_outcome_record` (supports both `PlayedHand` and `PlayedSplitHand`,
  counting per-sub-hand results), `save_outcome_record`, `load_outcome_record`,
  `list_outcome_records` (with `limit` and `profile_key` filters), and
  `summarize_outcomes`.
- CLI `play` flags `--save-outcome` and `--outcome-dir`: play a hand, record the
  result locally, and print the saved path.
- CLI `outcomes` command (`--limit`, `--profile`, `--dir`): summarise the local
  win/loss history (totals, busts, split records, average split hands, most
  common profile and outcomes).

### Changed

- Bumped the package and `app.__version__` to **1.8.0**.

### Quality

- New deterministic suite `tests/test_outcome_history.py` plus CLI tests for
  `play --save-outcome` and `outcomes`. Full suite passing; ruff clean; CI on
  Python 3.9-3.12.

### Safety

- Summary only: outcome history stores no money, bankroll, real bets, accounts,
  tokens, screenshots, or sensitive data - no database, no network, no cloud.
  The `.blackjack_coach/` tree (including `outcomes/`) stays git-ignored. No
  change to basic strategy, the engine recommendation, deviations, the
  simulator, the matrix/audit tooling, or scored session history.

## [1.7.0] - 2026-06-23

Complete strategy-matrix audit and per-hand decision audit. Makes the coach
more confident and transparent: it can now print a full basic-strategy decision
matrix for any profile, audit its coverage, and explain for any single hand how
the recommendation was reached (direct table play or a legal fallback). Basic
strategy itself is unchanged: both new layers only read
`strategy_engine.recommend`.

### Added

- `app/strategy_matrix.py`: `StrategyCell`, `StrategyMatrix`,
  `MatrixAuditReport`, the generators `generate_hard_total_matrix`,
  `generate_soft_total_matrix`, `generate_pair_matrix`,
  `generate_strategy_matrix`, plus `audit_strategy_matrix` and
  `format_strategy_matrix`. A full matrix covers hard 5-21, soft 13-21, and
  pairs (A,A and 2,2..10,10) against dealer 2-10 and A: 360 cells per profile.
- `app/decision_audit.py`: `DecisionAudit`, `audit_decision`,
  `legal_actions_for_hand`, `detect_strategy_category`, and
  `detect_table_section`.
- CLI `matrix` command (`--profile`, `--section hard|soft|pairs|all`,
  `--audit`): prints the compact matrix with a dealer 2-10,A header and a
  coverage summary (total / fallback / missing cells, warnings).
- CLI `audit` command (`--cards`, `--dealer`, `--profile`): reports a hand's
  category, table section, recommended vs raw table action, fallback applied,
  legal actions, warnings, and a plain explanation.

### Changed

- `diagnose` now includes a compact audit summary (table section, raw table
  action, fallback applied, legal actions, profile rules) so it explains both
  the *why* and the underlying mechanics.
- Bumped the package and `app.__version__` to **1.7.0**.

### Quality

- New deterministic suites `tests/test_strategy_matrix.py` and
  `tests/test_decision_audit.py` plus CLI tests for `matrix`, `audit`, and the
  `diagnose` audit summary. Full suite passing; ruff clean; CI on Python
  3.9-3.12.

### Safety

- Coverage / explainability only: no change to basic strategy, the engine
  recommendation, deviations, the simulator, or session history. No casino
  connectivity, real betting, bankroll, camera/video, scraping, or promise of
  winnings. Responsible scope is preserved.

## [1.6.0] - 2026-06-23

Full re-split tree simulator. Completes the split/re-split logic that v1.5.0
began: the local play simulator now plays a real re-split tree instead of
treating re-splits as a simplified warning. No changes to basic strategy,
Hi-Lo math, deviations, or session history.

### Added

- `app/simulator.py`: `_play_split_tree` and `_play_out_position`, which build
  and play a full split / re-split tree from an opening pair.
- `SplitSubHand` now records `hand_id` (1-based play order), `split_depth`
  (1 = initial split, 2+ = re-split), and `from_resplit`.
- `PlayedSplitHand.num_split_hands` reports the final number of sub-hands.
- `RESPLIT_LIMIT_REACHED` marker, recorded when a pair would re-split but the
  rules forbid it (re-split disallowed or `max_split_hands` reached).

### Changed

- The simulator now plays real re-splits up to `profile.max_split_hands`,
  honouring `resplit_allowed`, `hit_split_aces`, and `double_after_split`:
  - A split hand that is again a pair is re-split when basic strategy says so
    and the rules allow it.
  - When `resplit_allowed` is false, or `max_split_hands` is reached, the pair
    is played as a normal total with a clear warning.
  - Split aces with `hit_split_aces=false` receive exactly one card and stop;
    with `hit_split_aces=true` they play normally (and may re-split).
- `play` output shows the number of split hands and, per sub-hand, whether it
  came from a split or a re-split (with its depth).
- `diagnose` and rule-profile notes updated: re-split / max-split-hands are now
  enforced by the simulator, not descriptive metadata.
- The legacy `RESPLIT_NOT_IMPLEMENTED` marker is no longer produced (kept only
  so external imports do not break).
- Bumped the package and `app.__version__` to **1.6.0**.

### Quality

- Added a deterministic `TestFullResplitTree` suite plus a CLI re-split test;
  updated existing split tests for the real tree. Full suite passing; ruff
  clean; CI on Python 3.9-3.12.

### Safety

- Behaviour change is local/simulated coaching only; basic strategy, the engine
  recommendation, deviations, and session history are unchanged. No casino
  connectivity, real betting, bankroll, camera/video, scraping, or promise of
  winnings. Responsible scope is preserved in the Safety / Educational Scope
  section.

## [1.5.0] - 2026-06-23

Profile-aware split rules. Promotes part of the v1.4.0 profile metadata from
description into active simulator/diagnostic behaviour. No changes to basic
strategy, Hi-Lo math, deviations, or session history.

### Added

- `app/split_rules.py` with `SplitRuleDecision` and helpers: `is_pair_hand`,
  `is_ace_pair`, `can_split_initial_hand`, `can_resplit`, `can_hit_split_aces`,
  `can_double_after_split`, and `explain_split_rules`.
- `split-rules` command (`--cards`, `--profile`, `--split-hands`).

### Changed

- The simulator now honours split-aces (`hit_split_aces`): when false, each
  split ace gets exactly one card and is locked; when true, hands play
  normally. Split sub-hands double only when `double_after_split` is allowed.
  Re-split is gated by `resplit_allowed` / `max_split_hands` with honest
  warnings (full multi-round re-split still simplified).
- `diagnose` now includes profile-aware split-rule factors (and an accurate
  metadata note).
- Bumped the package and `app.__version__` to **1.5.0**.

### Quality

- Added `tests/test_split_rules.py`; extended simulator, diagnostics, and CLI
  tests. Full suite passing; ruff clean; CI on Python 3.9-3.12.

### Safety

- Behaviour change is local/simulated coaching only; basic strategy, the engine
  recommendation, deviations, and session history are unchanged. `max_split_
  hands` and full re-split remain partly metadata, documented where surfaced.
  Responsible scope is preserved in the Safety / Educational Scope section.

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
