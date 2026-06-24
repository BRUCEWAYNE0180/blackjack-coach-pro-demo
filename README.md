# Blackjack Coach Pro Demo

[![CI](https://github.com/BRUCEWAYNE0180/blackjack-coach-pro-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/BRUCEWAYNE0180/blackjack-coach-pro-demo/actions/workflows/ci.yml)

A **professional blackjack coach** for **local practice, demo money, video
games, recreational tournaments, and training** — basic strategy, Hi-Lo
counting, a hand simulator, scored drills, true-count deviation study, and
decision diagnostics, all from a friendly offline CLI.

The focus is **decision intelligence**: it tells you the right play *and why*,
breaks down the rule factors behind it, and helps you drill until it sticks.

> Responsible scope: this is a coaching and practice tool, not a real-money
> gambling product. See the [Safety / Educational Scope](#safety--educational-scope)
> section and [`docs/PROJECT_RULES.md`](docs/PROJECT_RULES.md).

**30-second tour:** install with `pip install -e ".[dev]"`, run the tests with
`python -m pytest`, then try `blackjack-coach diagnose --cards A,7 --dealer 9`.
It gives the recommended play, the decision factors behind it, and the rule
context.

Docs: [Release notes](docs/RELEASE_NOTES_v1.0.0.md) ·
[Commands](docs/COMMANDS.md) · [Changelog](CHANGELOG.md) ·
[Project rules](docs/PROJECT_RULES.md) · [License](LICENSE)

## v2.5.0 feature summary

- Recommends the basic-strategy action (`HIT`, `STAND`, `DOUBLE`, `SPLIT`,
  `SURRENDER`) for multi-deck **H17** and **S17** profiles.
- Gives a short **educational explanation** of *why* each action is suggested.
- Adds **warnings**, including the insurance note when the dealer shows an Ace
  (insurance recommendation is always **NO**).
- Includes a **Hi-Lo counting trainer** (running count + true count) for
  **local / simulated practice only**.
- Includes a **local shoe simulator** that deals hands from a virtual shoe so
  you can practise basic strategy and counting together, fully offline.
- **Plays a full hand against the dealer** (H17/S17 dealer logic + outcome
  resolution), including **basic pair splits**, in a simplified educational
  single-hand model.
- Offers an interactive/non-interactive **quiz mode** to drill basic strategy
  and the Hi-Lo running count from the terminal.
- Runs **scored training sessions** (multiple questions) with accuracy and
  weak-spot summaries for both strategy and counting.
- Ships a simple **command-line trainer**, installable as the
  `blackjack-coach` command, with CI and modern packaging.
- **Polished terminal output** (v1.1.0): clear headers, aligned key/value
  rows, visible pass/fail badges, and percentage summaries.
- **Local session history** (v1.2.0): optionally save scored sessions to local
  JSON files and review your progress with `blackjack-coach history`.
- **Deviation study mode** (v1.3.0): study a small set of well-known Hi-Lo
  true-count deviations (`deviations`, `deviation-quiz`) without touching the
  basic-strategy engine.
- **Decision diagnostics** (v1.3.0): `diagnose` explains the factors behind a
  recommended play — hand shape, dealer strength, available options, and the
  rule-profile context.
- **Expanded rule profiles** (v1.4.0): single/double/four/six/eight-deck
  profiles with H17/S17, DAS/NDAS, LS/NS, plus a `profiles` command to list and
  inspect them.
- **Profile-aware split rules** (v1.5.0): the simulator and diagnostics now
  respect split / split-aces / double-after-split rules, with a `split-rules`
  command to inspect them.
- **Full re-split tree simulator** (v1.6.0): the play simulator now plays a real
  split / re-split tree up to `max_split_hands`, honouring `resplit_allowed`,
  `hit_split_aces`, and `double_after_split`.
- **Complete strategy matrix + decision audit** (v1.7.0): print a full
  basic-strategy decision matrix for any profile and audit its coverage
  (`matrix`), and audit how any single hand's recommendation is reached
  (`audit`) - direct table play or a legal fallback.
- **Outcome / win-loss history** (v1.8.0): optionally save played-hand results
  (wins, losses, pushes, surrenders, busts, and split / re-split outcomes) to a
  local JSON folder and review them with `outcomes`.
- **Guided coach mode** (v1.9.0): the coach picks and explains the best play -
  ask for direct advice (`coach`) or let the coach play a full hand
  automatically, step by step (`coach-play`).
- **Professional card display** (v1.10.0): enter and see cards with suits and
  colour (`A♠`, `10♥`, `K♦`, `8♣`) - hearts/diamonds in red - with `--no-color`
  and `--plain-cards` options. Visual only; the engine still uses plain ranks.
- **Count-aware coach advice** (v1.11.0): pass an optional `--true-count` to
  `coach` / `coach-play` and the coach compares basic strategy with the
  educational deviation study, showing the basic action, the count-adjusted
  action, and the final recommendation.
- **Probability & EV advisor** (v1.12.0): `odds` (and `coach --show-odds`) show
  approximate player bust chance, the dealer's final-total distribution, and a
  rough EV per action - advisory only; never overrides the recommendation.
- **Adaptive local learning** (v1.13.0): `learn` reads your locally saved
  outcomes to surface strong / weak / high-variance spots and practice tips,
  and `coach --use-history` adds a personalised local-history context block.
  It personalises context only and never changes the strategy recommendation.
- **Composition-aware EV advisor** (v1.14.0): `odds` / `coach --show-odds` can
  use the actual remaining-shoe composition (`--composition-aware`,
  `--seen-cards`) for an exact finite-shoe dealer distribution and sharper EV.
- **Exact split / re-split EV** (v1.15.0): the advisor estimates the EV of
  splitting and re-splitting pairs against the finite-shoe dealer distribution,
  respecting the profile's split rules.
- **Full player EV decision tree** (v1.16.0): every legal action's EV is unified
  in one recursive player decision tree (advisory only; never overrides the
  recommendation).
- **EV snapshot history & review** (v1.17.0): save a local EV snapshot of the
  advisory (`odds` / `coach --show-odds` with `--save-ev-snapshot`) and review
  when the coach's recommendation agreed with the advisory best-EV action - or
  differed - using `ev-review`. Advisory audit only; it never changes the
  recommendation and stores no sensitive data.
- **Strategy-vs-EV explanation engine** (v1.18.0): `--explain-ev` (on `odds` and
  `coach --show-odds`) and `ev-review --explain` add a clear, professional
  explanation of *when* the coach's recommendation agrees with the advisory
  best-EV action and *when/why* it differs (tiny / small / medium / large EV
  gap, shoe composition, true count, split / re-split, surrender, or model
  limits). Explanation only - it never overrides the recommendation.
- **Exportable learning reports** (v1.19.0): `report` combines your local
  session history, outcomes, EV snapshots, Strategy-vs-EV review, weak spots,
  and practice tips into a single **Markdown / JSON / CSV** report for reviewing
  progress or saving to Notion / GitHub. Local and read-only; it exports no
  sensitive data and never changes the recommendation.
- **Profile dashboard & trends** (v1.20.0): `dashboard` shows a local
  per-profile view - training / outcome / EV totals, recent-sample trends, weak
  spots, Strategy-vs-EV disagreements, and a concrete **next-practice plan** -
  to answer "where am I failing and what should I drill next?". Print it, show
  it as Markdown, or `--export` it. A practice aid only; it never changes the
  recommendation and stores no sensitive data.
- **Weak-spot drill generator** (v1.21.0): `drill` turns your weak spots,
  high-loss hands, and Strategy-vs-EV disagreements (or a base educational set
  when there is no history) into focused practice drills you can answer and get
  graded on. The correct play always comes from the strategy engine - drills
  never change the recommendation and store no sensitive data.
- **Drill session history & spaced review** (v1.22.0): save graded drills with
  `drill --answer ... --save`, then `drill --review` shows per-spot **mastery**
  (NEW / WEAK / LEARNING / MASTERED) and what is **due for review** next - a
  light, local spaced-repetition layer. Local and read-only; it never changes
  the correct answers or the recommendation.
- **Drill review queue & streaks** (v1.23.0): `review-queue` schedules your
  saved drills into a spaced-repetition queue (what is due today, overdue, and
  upcoming) and tracks practice **streaks**. Print it, show it as Markdown, or
  `--export` it. Local and read-only; it never changes the correct answers or
  the recommendation.
- **Daily practice pack generator** (v1.24.0): `practice-pack` builds one
  ready-to-practise session for today by combining due reviews, weak spots, EV
  disagreement spots, and an educational mix (with a starter set when there is
  no history). Reproducible with `--seed`, exportable to Markdown. Local and
  read-only; it never changes the correct answers or the recommendation.
- **Practice pack completion history** (v1.25.0): `practice-pack --complete`
  saves whether you finished a pack (items done, correct / missed / skipped,
  completion rate, accuracy), and `practice-pack --progress` summarises pack
  **streaks** and progress over time. Local and read-only; it never changes the
  correct answers or the recommendation.
- **Repeat pack for missed spots** (v1.26.0): `repeat-pack` builds a focused
  session from the spots you keep missing (recently / repeatedly missed,
  low-accuracy, and skipped), with a starter educational set when there is no
  missed history. Reproducible with `--seed`, exportable to Markdown. Local and
  read-only; it never changes the correct answers or the recommendation.
- **Repeat pack completion history** (v1.27.0): `repeat-pack --complete` saves
  which missed spots you corrected vs still miss (repeat accuracy, repeat
  streaks), and `repeat-pack --progress` summarises correction progress and
  flags persistent misses. Local and read-only; it never changes the correct
  answers or the recommendation.
- **Missed-spot correction dashboard** (v1.28.0): `correction-dashboard` shows
  a clear local view of which errors are **corrected**, **improving**,
  **persistent misses**, or **new**, with per-spot accuracy and concrete
  next-practice priorities. Print it, show it as Markdown, or `--export` it.
  Local and read-only; it never changes the correct answers or the
  recommendation.
- **Correction action plan** (v1.29.0): `correction-plan` turns the correction
  dashboard into a prioritised plan - urgent repeats, focused review, data
  collection, and maintenance - each with a suggested existing command (never
  executed). Local and read-only; it never changes the correct answers or the
  recommendation.
- **Local Web Coach UI** (v2.0.0): an optional Streamlit web page
  (`web/streamlit_app.py`) that wraps the existing engine - enter cards, dealer
  upcard, profile, optional true count and odds, and get the coach's
  recommendation in the browser. Local only; the CLI and engine are unchanged.
- **Web card buttons & UI polish** (v2.1.0): the local web page gains tappable
  **card buttons** (A, 2-10, J, Q, K) for the player hand and dealer upcard,
  one-click **quick examples**, **clear / reset** controls, a **colour-coded**
  recommended-action banner (HIT / STAND / DOUBLE / SPLIT / SURRENDER), clearer
  missing-card warnings, and a mobile-friendly layout - with the manual
  text-entry mode kept. Presentation only; the engine, recommendations, Hi-Lo
  math, and CLI are unchanged.
- **Web round-result tracker** (v2.2.0): after the recommendation, the local web
  page can record how the round finished - the player's and dealer's **final
  cards**, the **action taken**, and the **WIN / LOSS / PUSH** outcome - and show
  a **decision review** that keeps decision quality (did it follow the coach?)
  separate from the round outcome. A correct play can still lose, so a LOSS is
  never marked a bad decision. The initial recommendation still uses only the
  player cards and dealer upcard.
- **Local blackjack practice table** (v2.3.0): a **Practice table (demo)** mode
  in the local web page deals its own simulated cards so you can play a full
  round - the app deals, the coach recommends, you act (HIT / STAND / DOUBLE /
  SURRENDER; SPLIT is auto-played), the dealer plays out automatically, and the
  WIN / LOSS / PUSH outcome, decision review, and a session history are recorded
  for you. Local / simulated / educational only: no camera, no screen reading,
  no scraping, no real casino, no real money or bankroll.
- **Practice table learning review** (v2.4.0): the practice table now explains
  *why* each round ended, categorises the conclusion, tracks **weak spots**,
  gives **"next time" advice** for mistakes, suggests **drills** for repeated
  errors, and shows a **learning dashboard** (follow-coach %, mistakes,
  correct-but-lost spots, most repeated situations). Decision quality is always
  kept separate from the round outcome - a correct decision that loses is never
  counted as a mistake. The dashboard also shows **Wins / Losses / Pushes counts
  and percentages**, and an **Auto-play simulation / Sanity check** panel lets
  you run **100** or **1,000** auto-played hands (optional fixed **Seed**, with a
  spinner) following the coach to confirm the local table resolves correctly -
  it reports wins/losses/pushes (+%), busts, surrenders, doubles and a
  plausibility interpretation. It is a local demo check only: no money,
  bankroll, EV, casino, network, camera, or scraping.
- **Rule profile simulator & strategy comparison** (v2.5.0): a **Rule profile
  comparison** panel (in the Practice table demo page) auto-plays many simulated
  rounds under several rule profiles at once - always following the coach - so
  you can study which table rules tend to be friendlier or harder. Pick the
  profiles, set a fixed **Seed** (default 42, reproducible) and the **hands per
  profile**, then **Compare selected profiles** or **Run 1,000 hands per
  profile**. It shows a comparison table (wins/losses/pushes counts + %, busts,
  surrenders, doubles, followed-coach % = 100%, plausibility) plus a summary
  (most favorable by win %, lowest loss %, highest push %, most difficult) and
  educational notes (S17 vs H17, DAS, late surrender). It also reports **net
  demo units** (units / 100 hands, avg units / hand), a **loss audit** (correct
  vs mistake losses; bust / dealer-made-hand / double / surrender losses), and a
  **coach sanity check** so you can see whether you are really negative or just
  losing more hands. Local/demo study only: no
  money, bankroll, EV-as-decision, casino, network, camera, or scraping, and
  more wins does not always mean better EV.

## EV Snapshot History & Review (v1.17.0)

The probability / EV advisor is **advisory only** - it never overrides the
coach's recommendation. v1.17.0 lets you keep a **local history** of EV
snapshots so you can later review *when the coach's main recommendation agreed
with the advisory best-EV action and when it differed*. This improves local
self-study and the transparency of the advisor without changing the strategy.

Save a snapshot while looking at the odds (or the coach's odds block):

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware --save-ev-snapshot
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware --save-ev-snapshot
```

`coach --save-ev-snapshot` requires `--show-odds` (otherwise there is no odds
advisory to snapshot, and the CLI prints a clear error). Snapshots are written
as local JSON under `./.blackjack_coach/ev_snapshots` (override with `--ev-dir`)
and are never committed.

Review the saved snapshots:

```bash
blackjack-coach ev-review
blackjack-coach ev-review --disagreements-only
blackjack-coach ev-review --profile SIX_DECK_H17_DAS_LS
```

The review reports the total snapshots, agreement / disagreement counts and
rate, the most common profile and recommended / best-EV actions, the largest EV
gaps, the spots where strategy and EV differed, practice recommendations, and a
data-quality note (it flags a **LOW sample** below 10 snapshots). With no saved
data it prints a clear "use `--save-ev-snapshot` first" message.

A handy local self-study loop is: `coach`/`odds --save-ev-snapshot` →
`ev-review` → `learn`. Each snapshot stores only a safe local summary - no
money, bankroll, bets, accounts, tokens, screenshots, or personal data.

## Strategy-vs-EV Explanation Engine (v1.18.0)

The probability / EV advisor is **advisory only**. v1.18.0 adds a plain-language
explanation of *when the coach's recommendation agrees with the advisory
best-EV action and when it differs* - and, when it differs, *why*: a tiny /
small / medium / large EV gap, the remaining-shoe composition, the true count,
split / re-split context, a surrender threshold, or the documented limits of the
EV model. It is an explanation layer only and never overrides the
recommendation.

Add `--explain-ev` to `odds`, or to `coach` together with `--show-odds`:

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware --explain-ev
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware --explain-ev
```

`coach --explain-ev` requires `--show-odds` (otherwise there is no odds advisory
to explain, and the CLI prints a clear error). The block shows the coach
recommendation, the best EV action, the EV gap, the gap label, the explanation,
and an advisory note.

The `ev-review` command can explain the saved snapshots too:

```bash
blackjack-coach ev-review --explain
blackjack-coach ev-review --disagreements-only --explain
blackjack-coach ev-review --large-gaps-only --explain
```

`--explain` appends Strategy-vs-EV explanations for the top disagreement spots
(largest gap first). `--large-gaps-only` narrows the review to snapshots whose
EV gap is **LARGE** (or **MEDIUM** when there is no LARGE gap). EV gap bands:
`TINY` `[0, 0.02)`, `SMALL` `[0.02, 0.05)`, `MEDIUM` `[0.05, 0.15)`, `LARGE`
`[0.15, ∞)`; a tiny / small gap is probably not a strong difference, while a
large gap is worth reviewing with `odds` and `audit`.

## Exportable Learning Reports (v1.19.0)

Once you have practised a little, `report` combines your local **session
history**, **outcome / win-loss history**, **EV snapshots**, **Strategy-vs-EV
review**, **weak / strong spots**, and **practice recommendations** into a
single report you can review, save to Notion / GitHub, or share as a training
summary. It is local and read-only - no network, no cloud, and it exports no
sensitive data (no money, bankroll, bets, accounts, or tokens).

```bash
blackjack-coach report
blackjack-coach report --format markdown --print
blackjack-coach report --format json --output report.json
blackjack-coach report --format csv --profile SIX_DECK_H17_DAS_LS
```

By default a timestamped Markdown report is written under
`./.blackjack_coach/reports` and the saved path is printed. Use `--format`
(`markdown` / `json` / `csv`), `--output <path>` to choose an exact file,
`--print` to also echo the content to the terminal, `--profile` / `--limit` to
scope the data, and `--session-dir` / `--outcome-dir` / `--ev-dir` to point at
custom history folders. EV snapshots are included automatically when present.
With no saved history the report says so clearly; with little data it flags a
**LOW sample / limited data** note.

## Profile Dashboard & Trends (v1.20.0)

`dashboard` turns the exportable reports into a more useful per-profile view for
deciding what to practise next. It groups your local **session history**,
**outcomes**, **EV snapshots**, **Strategy-vs-EV disagreements**, **weak spots**,
and **practice recommendations** by rule profile, adds a simple recent-sample
**trend**, and prints a concrete **next-practice plan**. It answers: which
profile am I practising most, where am I failing, which spots have the most
Strategy-vs-EV disagreements, and what should I drill now.

```bash
blackjack-coach dashboard
blackjack-coach dashboard --profile SIX_DECK_H17_DAS_LS
blackjack-coach dashboard --markdown
blackjack-coach dashboard --export
blackjack-coach dashboard --profile SIX_DECK_H17_DAS_LS --export --output dashboard.md
```

By default the dashboard is printed to the terminal as compact text. `--markdown`
prints Markdown instead (handy for Notion / GitHub); `--export` saves a Markdown
file under `./.blackjack_coach/reports` and prints the path; `--output <path>`
saves to an exact file; `--profile` / `--limit` scope the data; and
`--session-dir` / `--outcome-dir` / `--ev-dir` point at custom history folders.
With no saved history it prints a clear message; with little data it flags a
**LOW sample / limited data** note. It is a practice aid only - no charts, no
external dependencies, no sensitive data - and never changes the strategy
recommendation.

## Weak-Spot Drill Generator (v1.21.0)

`drill` turns the coach's "what to practise" guidance into actual focused
practice sessions. It builds drills from your **weak spots**, **high-loss
hands**, and **Strategy-vs-EV disagreement spots** (and falls back to a small,
well-known educational set when there is no saved history), then poses them and
grades your answer. The correct play for every drill comes from the stable
strategy engine - drills never change the recommendation.

```bash
blackjack-coach drill
blackjack-coach drill --focus pairs --count 10
blackjack-coach drill --focus ev --profile SIX_DECK_H17_DAS_LS
blackjack-coach drill --seed 42 --spot 1 --answer HIT
blackjack-coach drill --focus weak --count 5 --plan-only
```

`--focus` is one of `weak` / `pairs` / `soft` / `hard` / `surrender` / `ev` /
`mixed`; `--count` caps the number of drills; `--seed` makes the order
deterministic; `--plan-only` just prints the plan; and `--answer H/S/D/P/R`
(with `--spot N`) grades the selected drill and explains why. `--profile`,
`--session-dir`, `--outcome-dir`, and `--ev-dir` scope where drills come from.
With no saved history it uses the educational set and says so clearly.

## Drill Session History & Spaced Review (v1.22.0)

Save your graded drills and let the coach track **mastery** per spot. Add
`--save` to a graded drill, then `drill --review` shows how each spot is
progressing (NEW / WEAK / LEARNING / MASTERED) and which spots are **due for
review** next - a light, local spaced-repetition layer built on the v1.21.0
drill generator. The correct answers always come from the strategy engine; this
never changes them.

```bash
blackjack-coach drill --seed 42 --spot 1 --answer HIT --save
blackjack-coach drill --review
blackjack-coach drill --review --due-only
blackjack-coach drill --profile SIX_DECK_H17_DAS_LS --review
```

`--save` requires `--answer` (it saves that graded result); `--drill-dir <path>`
chooses where sessions are stored (default `./.blackjack_coach/drill_sessions`).
`drill --review` summarises total sessions, attempts, overall accuracy, weak /
mastered spots, the due-for-review list, and practice recommendations;
`--due-only` shows just the spots that still need work. With no saved sessions
it says so clearly. Mastery levels: **NEW** (< 2 attempts), **WEAK** (< 60%),
**LEARNING** (60-85%), **MASTERED** (>= 85% over >= 3 attempts). Drill sessions
are a local summary only - no money, accounts, or sensitive data - and are never
committed.

## Drill Review Queue & Streaks (v1.23.0)

`review-queue` turns your saved drill sessions into a local spaced-repetition
schedule: which spots are **due now**, which are **overdue**, and which are
**upcoming** - weak spots come back soon, learning spots later, mastered spots
much later. It also tracks your practice **streaks**. It is built on the v1.22.0
drill history and never changes the correct answers or the recommendation.

```bash
blackjack-coach review-queue
blackjack-coach review-queue --due-only
blackjack-coach review-queue --streaks
blackjack-coach review-queue --profile SIX_DECK_H17_DAS_LS
blackjack-coach review-queue --today 2026-06-23 --due-only
blackjack-coach review-queue --export --output review_queue.md
```

`--due-only` shows just the items due now or overdue; `--streaks` adds the
current / longest streak and active days; `--today YYYY-MM-DD` makes scheduling
deterministic; `--markdown` prints Markdown; `--export` (with optional
`--output`) saves a Markdown file under `./.blackjack_coach/reports`; and
`--profile` / `--limit` / `--drill-dir` scope the queue. Review intervals: NEW /
WEAK -> today/soon, LEARNING -> ~2 days, MASTERED -> ~7 days. With no saved
drill sessions it says so clearly. The scheduler is local practice only - no
sensitive data - and is never committed.

## Daily Practice Pack Generator (v1.24.0)

`practice-pack` assembles one ready-to-practise session for today by combining
every local signal: the review-queue's **due** items, **weak** drill-history
spots, **EV disagreement / high-gap** spots, and a focus-specific or educational
**mix** (with a starter set when there is no saved history). Due spots come
first, then weak, then EV, then the mix.

```bash
blackjack-coach practice-pack
blackjack-coach practice-pack --focus due --count 10
blackjack-coach practice-pack --focus ev --profile SIX_DECK_H17_DAS_LS
blackjack-coach practice-pack --today 2026-06-23 --seed 42
blackjack-coach practice-pack --markdown
blackjack-coach practice-pack --export --output practice_pack.md
```

`--focus` is one of `daily` / `due` / `weak` / `ev` / `pairs` / `hard` / `soft`
/ `mixed`; `--count` caps the items; `--seed` makes the pack deterministic;
`--today YYYY-MM-DD` drives the due scheduling; `--markdown` prints a Markdown
checklist; `--export` (with optional `--output`) saves it under
`./.blackjack_coach/reports`; and `--profile` / `--drill-dir` / `--session-dir`
/ `--outcome-dir` / `--ev-dir` scope where the pack draws from. With no saved
history it prints a starter educational pack and says so. The correct play for
every item comes from the strategy engine - the pack never changes it. (After
practising, save progress with `drill --answer ... --save` and re-run
`review-queue`.)

## Practice Pack Completion History (v1.25.0)

Record whether you actually finished today's pack and track progress over time.
`practice-pack --complete` saves a local completion record (items done, correct
/ missed / skipped, completion rate, accuracy), and `practice-pack --progress`
summarises your pack **streaks**, completion rate, accuracy, and weak / strong
pack spots. It is built on the v1.24.0 generator and never changes the correct
answers or the recommendation.

```bash
blackjack-coach practice-pack --complete
blackjack-coach practice-pack --complete --correct-spots hard_16_vs_10,soft_18_vs_9 --missed-spots pair_8_vs_6
blackjack-coach practice-pack --progress
blackjack-coach practice-pack --progress --profile SIX_DECK_H17_DAS_LS
```

`--complete` marks the generated pack practised (whole pack complete with no
accuracy unless you pass detail); add `--correct-spots`, `--missed-spots`, and
`--skipped-spots` (comma-separated spot ids) to record accuracy. `--pack-dir`
chooses where completions are stored (default
`./.blackjack_coach/practice_packs`). `--progress` shows the completion summary
(optionally scoped with `--profile`); with no saved completions it says so
clearly. Completion records are a local summary only - no money, accounts, or
sensitive data - and are never committed.

## Repeat Pack for Missed Spots (v1.26.0)

`repeat-pack` builds a focused session from the spots you keep getting wrong,
using your practice-pack completion history (v1.25.0): recently missed,
repeatedly missed, low-accuracy, and skipped spots, topped up with the review
queue and a starter educational set when there is no missed history. The correct
play for every item comes from the strategy engine - it never changes it.

```bash
blackjack-coach repeat-pack
blackjack-coach repeat-pack --count 10
blackjack-coach repeat-pack --profile SIX_DECK_H17_DAS_LS
blackjack-coach repeat-pack --today 2026-06-23 --seed 42
blackjack-coach repeat-pack --markdown
blackjack-coach repeat-pack --export --output repeat_pack.md
```

`--count` caps the items; `--seed` makes the pack deterministic; `--profile`
scopes it; `--today YYYY-MM-DD` drives the due-review top-up; `--pack-dir` /
`--drill-dir` point at custom history folders; `--markdown` prints a checklist;
and `--export` (with optional `--output`) saves it under
`./.blackjack_coach/reports`. With no missed history it prints a starter
educational pack and says so. After repeating, record results with
`practice-pack --complete --correct-spots ... --missed-spots ...`.

## Repeat Pack Completion History (v1.27.0)

Record whether your repeat packs actually fixed the spots you kept missing.
`repeat-pack --complete` saves a local completion record (corrected vs still
missed, completion rate, repeat accuracy), and `repeat-pack --progress`
summarises correction progress, repeat **streaks**, and which spots are still
**persistent misses**. It is built on the v1.26.0 repeat-pack generator and never
changes the correct answers or the recommendation.

```bash
blackjack-coach repeat-pack --complete
blackjack-coach repeat-pack --complete --corrected-spots hard_16_vs_10,soft_18_vs_9 --still-missed-spots pair_8_vs_6
blackjack-coach repeat-pack --progress
blackjack-coach repeat-pack --progress --profile SIX_DECK_H17_DAS_LS
```

`--complete` marks the generated repeat pack practised (whole pack complete with
no accuracy unless you pass detail); add `--corrected-spots`,
`--still-missed-spots`, and `--skipped-spots` (comma-separated spot ids) to
record repeat accuracy. `--repeat-dir` chooses where completions are stored
(default `./.blackjack_coach/repeat_packs`). `--progress` shows the correction
summary (optionally scoped with `--profile`); with no saved completions it says
so clearly. Per-spot statuses: NEW, IMPROVING, CORRECTED, PERSISTENT_MISS.
Completion records are a local summary only - no money, accounts, or sensitive
data - and are never committed.

## Missed-Spot Correction Dashboard (v1.28.0)

`correction-dashboard` reads your repeat-pack completion history (v1.27.0) and
shows, at a glance, which previously-missed spots are now **corrected**,
**improving**, **persistent misses**, or **new** - with per-spot repeat accuracy
and a concrete next-practice priority list. It is read-only and never changes
the correct answers or the recommendation.

```bash
blackjack-coach correction-dashboard
blackjack-coach correction-dashboard --profile SIX_DECK_H17_DAS_LS
blackjack-coach correction-dashboard --markdown
blackjack-coach correction-dashboard --export --output correction_dashboard.md
```

`--profile` / `--limit` scope the data; `--markdown` prints a Markdown table;
`--export` (with optional `--output`) saves it under `./.blackjack_coach/reports`;
and `--repeat-dir` points at a custom completion folder. With no saved repeat
completions it says so clearly, and it is useful even with a single record. The
dashboard stores no sensitive data and is never committed.

## Correction Action Plan (v1.29.0)

`correction-plan` turns the missed-spot correction dashboard (v1.28.0) into a
concrete, prioritised plan: which spots to **repeat urgently**, which to
**review**, which need **more data**, and which only need **maintenance** - each
with a suggested existing command. It never executes any command and never
changes the correct answers or the recommendation.

```bash
blackjack-coach correction-plan
blackjack-coach correction-plan --focus urgent
blackjack-coach correction-plan --profile SIX_DECK_H17_DAS_LS
blackjack-coach correction-plan --markdown
blackjack-coach correction-plan --export --output correction_plan.md
```

`--focus` is one of `all` / `urgent` / `persistent` / `improving` / `new` /
`maintenance`; `--profile` / `--limit` scope the data; `--markdown` prints a
Markdown checklist; `--export` (with optional `--output`) saves it under
`./.blackjack_coach/reports`; and `--repeat-dir` points at a custom completion
folder. Priority order: persistent misses, then improving, then new, then
corrected. With no saved repeat completions it says so clearly. The plan only
shows suggested commands - you run them yourself - and stores no sensitive data.

## Local Web Coach UI (v2.0.0)

v2.0.0 adds an optional **local web page** (Streamlit) so you can use the coach
from your browser instead of the terminal. It is a thin wrapper around the same
engine via `app/web_adapter.py` - it does **not** change the strategy
recommendation, the correct answers, or the Hi-Lo math, and the CLI keeps
working exactly as before.

```bash
python -m pip install -e ".[web]"
python -m streamlit run web/streamlit_app.py
blackjack-coach web   # prints these start instructions
```

`blackjack-coach web` just prints the launch instructions (it does not start any
process). Streamlit opens a local page (default `http://localhost:8501`) with a
sidebar for the rule profile, optional true count, odds / composition-aware
toggles, seen cards, and available-action toggles; the main area takes your
player cards and the dealer upcard and shows the recommended action,
explanation, legal actions, optional count-aware and odds / EV blocks, and any
warnings.

The web UI is **local practice / training / learning only** - no real betting,
no casino connectivity, no money handling, and no external commands. Streamlit
is an optional dependency: a normal `pip install -e ".[dev]"` does not require
it, and the full test suite runs without it.

## Web Card Buttons & UI Polish (v2.1.0)

v2.1.0 makes the local web page much friendlier - no more typing `A,7` by hand.

```bash
python -m pip install -e ".[web]"
python -m streamlit run web/streamlit_app.py
```

In the default **Card buttons** mode you build the hand by tapping card buttons
(**A, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K**):

- **Your hand:** tap ranks to add cards, with **Undo last card** and **Clear
  hand**; the selected cards show as live chips.
- **Dealer upcard:** tap one rank for the dealer's card, with **Clear dealer**.
- **Quick examples:** load a sample hand (e.g. *Soft 18 vs 9*, *Hard 16 vs 10*,
  *Pair of 8s vs 10*, *Pair of Aces vs 6*, *11 vs 5*) with one tap.
- **Reset all:** clear the hand and the dealer upcard together.

The recommendation appears as a **polished, colour-coded banner** - HIT, STAND,
DOUBLE, SPLIT, or SURRENDER - with a short description, followed by the
explanation, hand summary, legal actions, and any optional count-aware / odds /
EV blocks. Warnings are clearer when cards are missing or invalid (e.g. *"Enter
at least two player cards"*), and the centred layout works well on a phone.

A **Manual text** input mode (sidebar) keeps the original typed-card entry for
power users. All of this is **presentation only**: the engine, the
recommendation, the correct answers, the Hi-Lo math, and the CLI are unchanged,
and the UI still runs no external commands and handles no money or sensitive
data.

## Web Round Result Tracker (v2.2.0)

v2.2.0 lets you close the loop on a hand. In blackjack the initial decision uses
only the player cards and the dealer's *upcard* - the dealer's hole card must
**not** change that recommendation. But after the round you often want to record
what actually happened. v2.2.0 adds a **Round result** section below the
recommendation for exactly that:

- **Player final cards** and **Dealer final cards** via the same tappable card
  buttons (with undo / clear, and a *Copy initial hand into final cards*
  shortcut).
- **Action taken** (HIT / STAND / DOUBLE / SPLIT / SURRENDER), defaulting to the
  coach's recommendation.
- **Outcome** WIN / LOSS / PUSH, with a suggestion computed from the final cards
  (you can always override it).
- **Save round result** into a session-visible **Round history** (with a small
  summary, including how many correct decisions still lost).

The **Decision review** clearly shows the *coach recommended action*, the
*player action taken*, the *final hand result*, whether the decision was
**correct / different from coach**, and the **outcome (win / loss / push)**.

When the coach recommends **DOUBLE**, the banner clarifies the rule - *take
exactly one additional card, then your turn ends* - and the Round result section
warns if a recorded double's final hand has more than one extra card (e.g.
initial `6,5` but final `6,5,K,3`).

The most important rule: **decision quality and round outcome are separate**. A
correct play can lose and a mistake can win, so a LOSS is never automatically a
bad decision. For example:

> Initial hand `A,7` vs dealer `10` -> coach says **HIT**. Player final cards
> `A,7,K` (18), dealer final cards `10,Q` (20) -> **Outcome: LOSS**, but the
> decision review reads *Followed coach recommendation (correct)*.

This is local and educational only: the dealer's final cards are used here
solely to log the round (never to change the recommendation), and it stores no
money, bankroll, bets, accounts, or personal data. The in-web history is
session-only; optional local persistence (the `app.round_result` module) follows
the project's existing pattern under the git-ignored `.blackjack_coach/` tree.

## Local Blackjack Practice Table (v2.3.0)

v2.3.0 adds a **Practice table (demo)** mode so you can practise a whole round
without typing every card. Pick "Practice table (demo)" in the sidebar "Mode"
selector, then:

1. Press **Start demo round / Deal**. The app deals two player cards plus the
   dealer's upcard and a hidden hole card from its own local shoe.
2. The dealer shows only the upcard; the coach freezes its recommendation
   (HIT / STAND / DOUBLE / SPLIT / SURRENDER) for the initial hand.
3. Choose your action with the buttons. HIT draws a card and you **keep
   playing** - the coach recommendation is **recalculated for the new hand**
   after each HIT (using only the dealer upcard); DOUBLE takes exactly one card
   and ends your turn; STAND ends your turn; SURRENDER forfeits; SPLIT is played
   out automatically by basic strategy (re-splitting is out of scope for the
   demo).
4. The dealer then plays automatically per the rule profile (H17 / S17), the
   app computes **WIN / LOSS / PUSH**, and shows a colour-coded result with a
   **decision review**: the initial hand, the coach's recommended action, the
   action you took, the player/dealer final cards, whether the decision was
   *correct / different from coach*, and the outcome.
5. The round is **auto-saved** to a **session history** (with a summary that
   includes how many correct decisions still lost). Press **Deal next round**
   to continue with the same shoe, or **Shuffle new shoe** to start fresh.

This is a **local, simulated, educational demo**: the app builds, shuffles and
deals from its own shoe and always knows its own cards. It never uses a camera,
never reads the screen, never scrapes, never connects to a real casino, never
automates real bets, and never involves real money or a bankroll. The game logic
lives in the Streamlit-free `app/practice_table.py`, which reuses the existing
shoe, dealer-play and outcome code and **never changes `strategy_engine.recommend`,
the Hi-Lo math, or the coach's decisions**. As always, decision quality is kept
separate from the round outcome - a correct play can still lose.

## Practice Table Learning Review (v2.4.0)

v2.4.0 turns the practice table's history into a **learning review**. Every
finished round now shows:

- a **conclusion category** (correct win / correct loss / different win /
  different loss / push / surrender);
- an **outcome-aware explanation** - e.g. *"You followed the coach. This was a
  correct decision, but the dealer made 20. This does not mean the coach
  recommendation was wrong - repeat the same decision next time."* or *"You won,
  but your action was different from the coach. Do not treat this as a good
  habit automatically."*;
- for **mistakes** (action different from the coach), concrete **next-time
  advice** - e.g. *"Next time: stand on hard 17 vs 6."* or *"Next time: split 8s
  vs 10 if split is allowed."*

A **learning dashboard** summarises the session: total rounds, **Wins / Losses /
Pushes counts and percentages**, **followed-coach %**, **mistakes**, **correct
wins**, **correct decisions that still lost** (tracked as variance, not errors),
**most common missed spots**, most common losing-but-correct spots, and the most
repeated situations. Repeated mistakes produce **drill suggestions** (e.g.
*"Practice hard 16 vs 10"*, *"Practice double spots"*). The counters are derived
from the same session list as the history table, so they always match.

A local **sanity simulation** (`app.practice_table.simulate_following_coach`)
can auto-play many demo rounds following the coach and report WIN / LOSS / PUSH,
to confirm the demo table resolves correctly (a seeded 1500-round run sits at
roughly 42% win / 48% loss / 9% push - a player simply wins fewer than half of
blackjack hands, so a losing-heavy short session is normal variance, not a bug).
It involves no money, EV, casino, network, or scraping.

The single most important rule: **decision quality is separate from the round
outcome.** A correct decision that loses is never counted as a mistake, and a
win after a non-recommended play is never automatically a good habit. The logic
lives in the Streamlit-free `app/practice_review.py` and **never changes
`strategy_engine.recommend`, the Hi-Lo math, or the coach's decisions**. It is
local / educational only and stores no money, bankroll, or sensitive data.

## Rule Profile Simulator & Strategy Comparison (v2.5.0)

v2.5.0 adds a **Rule profile comparison** panel to the Practice table (demo)
page so you can study how different table rules behave. Pick one or more rule
profiles, choose a fixed **Seed** (default 42) and the number of **hands per
profile**, then click **Compare selected profiles** (or the quick **Run 1,000
hands per profile**). The tool auto-plays that many simulated rounds for each
profile - always following the coach - and shows a comparison table:

- Profile, total hands, **wins / losses / pushes** counts and percentages,
  **busts**, **surrenders**, **doubles**, **followed coach %** (always 100% in
  auto-play), and a **plausibility** status.

A short **summary** highlights the **most favorable** profile (highest simulated
win rate), the **lowest loss %**, the **highest push %**, and the **most
difficult** profile (highest simulated loss rate), followed by educational notes:
S17 (dealer stands on soft 17) is usually friendlier than H17; double-after-split
(DAS) usually helps a little; late surrender can reduce losses on the worst
hands; and **more wins does not always mean better EV**.

### Net demo units, loss audit, and coach sanity (v2.5.0)

Win % alone does not answer "am I really negative, or just losing more hands?",
so the simulation also reports **net demo units** using a 1-unit base hand
(WIN +1, LOSS -1, PUSH 0, SURRENDER -0.5, DOUBLE +/-2; a split sums +/-1 per
sub-hand). Natural blackjack is **not** paid 3:2 in the demo (it scores as a
normal +1 win). The comparison table adds **Net units**, **Units / 100 hands**
and **Avg units / hand**, and the summary adds the **best / worst profile by net
units** plus a note when the most-winning profile is not the best by units.

A **loss audit** explains *why* hands were lost, two consistent ways: by quality
(**correct losses** - the auto-player followed the coach but still lost, vs
**mistake losses**) and by mechanism (**bust**, **dealer made a hand**,
**double**, **surrender**, split) - each set sums to the total losses. Because
auto-play always follows the coach, mistake losses are 0 and every loss is a
correct loss (normal variance, not an error). A **coach sanity check** confirms
the auto-play followed the coach on 100% of initial decisions and kept the frozen
initial recommendation separate from the recalculated current one. An
educational note explains that the dealer wins more hands because the player acts
first (and can bust before the dealer draws), and that win % is not the same as
profitability.

Every comparison is **deterministic for a fixed seed**, the per-profile counts
always sum to the total hands, and one or many profiles can be compared. The
logic lives in the Streamlit-free, unit-testable `app/profile_comparison.py`
(building on `app.practice_table.simulate_following_coach`). It is a local/demo
study aid only: it uses **no money, bankroll, EV-as-decision, real betting,
casino connectivity, network, camera, screen reading, or scraping**, never
claims a real-world edge or guaranteed result, and **never changes
`strategy_engine.recommend` or the Hi-Lo math**.

## Terminal visual polish (v1.1.0)

v1.1.0 makes the CLI clearer and more pleasant to practise with. Output now has
section headers, aligned labels, and a visible result badge. The strategy,
counting, simulator, scoring, and grading **logic is unchanged** — this is a
presentation-only improvement (see `app/formatting.py`).

Example (strategy quiz):

```text
=== Strategy Quiz ===
=====================
Player cards  : Q, 3
Dealer upcard : 2
Profile       : MULTI_DECK_H17_DAS_LS
Your answer   : HIT
Correct action: STAND
Result        : [ INCORRECT ]
Why           : Hard 13 vs dealer 2 [MULTI_DECK_H17_DAS_LS]: STAND. ...
```

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

This installs the package (standard-library only at runtime) plus the dev
tools (`pytest`, `ruff`) and runs the test suite. Lint with:

```bash
ruff check app tests
```

## Requirements

- Python 3.9+
- Dev tooling (`pytest`, `ruff`) via the `dev` extra:
  `python -m pip install -e ".[dev]"`.

## Command-line usage

Once installed (see Quick start), the same trainer is available as the
`blackjack-coach` command:

```bash
blackjack-coach --version
blackjack-coach diagnose --cards A,7 --dealer 9
blackjack-coach --cards A,7 --dealer 9
blackjack-coach count --cards 2,5,K,A,9 --decks-remaining 5
blackjack-coach play --decks 6 --seed 42
blackjack-coach quiz --seed 42 --answer H
blackjack-coach quiz-session --questions 10 --seed 42 --answers H,S,D,H,R,S,H,D,P,S
blackjack-coach deviations --cards 10,6 --dealer 10 --true-count 1
blackjack-coach matrix --profile SIX_DECK_H17_DAS_LS --section hard
blackjack-coach audit --cards A,7 --dealer 9 --profile SIX_DECK_H17_DAS_LS
blackjack-coach play --decks 6 --seed 428 --profile SIX_DECK_H17_DAS_LS --save-outcome
blackjack-coach outcomes
blackjack-coach coach --cards A,7 --dealer 9 --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach-play --decks 6 --seed 42 --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach-play --decks 6 --seed 42 --profile SIX_DECK_H17_DAS_LS --save-outcome
blackjack-coach learn
blackjack-coach learn --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --use-history
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --seen-cards 2♣,5♦,K♠,A♥ --composition
blackjack-coach odds --cards 8♠,8♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware --save-ev-snapshot
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware --save-ev-snapshot
blackjack-coach ev-review
blackjack-coach ev-review --disagreements-only
blackjack-coach ev-review --profile SIX_DECK_H17_DAS_LS
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware --explain-ev
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware --explain-ev
blackjack-coach ev-review --disagreements-only --explain
blackjack-coach ev-review --large-gaps-only --explain
blackjack-coach report
blackjack-coach report --format markdown --print
blackjack-coach report --format json --output report.json
blackjack-coach report --format csv --profile SIX_DECK_H17_DAS_LS
blackjack-coach dashboard
blackjack-coach dashboard --profile SIX_DECK_H17_DAS_LS
blackjack-coach dashboard --markdown
blackjack-coach dashboard --export
blackjack-coach drill
blackjack-coach drill --focus pairs --count 10
blackjack-coach drill --seed 42 --spot 1 --answer HIT
blackjack-coach drill --seed 42 --spot 1 --answer HIT --save
blackjack-coach drill --review
blackjack-coach drill --review --due-only
blackjack-coach review-queue
blackjack-coach review-queue --due-only
blackjack-coach review-queue --streaks
blackjack-coach practice-pack
blackjack-coach practice-pack --focus due --count 10
blackjack-coach practice-pack --markdown
blackjack-coach practice-pack --complete
blackjack-coach practice-pack --progress
blackjack-coach repeat-pack
blackjack-coach repeat-pack --markdown
blackjack-coach repeat-pack --complete
blackjack-coach repeat-pack --progress
blackjack-coach correction-dashboard
blackjack-coach correction-dashboard --markdown
blackjack-coach correction-plan
blackjack-coach correction-plan --focus urgent
blackjack-coach web
```

Without installing, run it as a module from the repository root:

```bash
python -m app.cli --cards A,7 --dealer 9 --profile MULTI_DECK_H17_DAS_LS
```

Example output:

```text
Hand:    Soft 18 vs dealer 9
Profile: MULTI_DECK_H17_DAS_LS
Action:  HIT
Why:     Soft 18 vs dealer 9 [MULTI_DECK_H17_DAS_LS]: HIT. Take another card. ...
Insurance: NO (always)
```

When the dealer shows an Ace, the insurance advice is printed explicitly:

```bash
python -m app.cli --cards 10,6 --dealer A
```

```text
Hand:    Hard 16 vs dealer A
Profile: MULTI_DECK_H17_DAS_LS
Action:  SURRENDER
...
Dealer shows an Ace - insurance may be offered.
Insurance advice: NO. Insurance is a side bet that the dealer has blackjack ...
```

### Options

| Flag             | Description                                         |
|------------------|-----------------------------------------------------|
| `--cards`        | Player cards, comma-separated (e.g. `A,7`, `10,6`). |
| `--dealer`       | Dealer upcard (e.g. `9`, `10`, `A`).                |
| `--profile`      | `MULTI_DECK_H17_DAS_LS` (default) or `MULTI_DECK_S17_DAS_LS`. |
| `--no-double`    | Treat doubling as unavailable.                      |
| `--no-surrender` | Treat surrender as unavailable.                     |
| `--no-split`     | Treat splitting as unavailable.                     |

## Hi-Lo counting trainer (v0.3)

Practise the Hi-Lo system against a **local, simulated** shoe. Tag values are
`2-6 = +1`, `7-9 = 0`, and `10/J/Q/K/A = -1`. The running count is the
cumulative sum; the true count divides it by the approximate decks remaining.

```bash
python -m app.cli count --cards 2,5,K,A,9 --decks-remaining 5
```

Example output:

```text
Hi-Lo counting (educational / simulated practice)
Cards seen:       5
Running count:    +0
Decks remaining:  5.0
True count:       +0.00
Note:             Running count +0, true count +0.00 ... educational practice ...
```

`--decks-remaining` must be greater than `0`. This trainer is **educational and
simulated only**: no real tables, no camera/video, no real-money betting, and
no promise of winnings.

## Local shoe simulator (v0.4)

Deal a training hand from a **local virtual shoe**. The simulator shuffles a
multi-deck shoe, deals the player two cards plus the dealer's up and hole
cards, recommends the basic-strategy play, and updates the Hi-Lo count from the
visible cards (the face-down hole card is not counted).

```bash
python -m app.cli simulate --decks 6 --seed 42
```

Example output:

```text
Simulated training hand (local / simulated practice only)
Player cards:         3, 5
Dealer upcard:        J
Recommendation:       HIT
  Why:                Hard 8 vs dealer 10 [MULTI_DECK_H17_DAS_LS]: HIT. ...
Running count before: +0
Running count after:  +1
True count after:     +0.17
Note:                 ... educational practice ...
```

Pass `--seed` for a reproducible shuffle and `--decks` to size the shoe
(`--decks` must be a positive integer). This is **local / simulated practice
only** — never for real tables, betting, camera/video, or screen scraping.

## Full-hand play (v0.5)

Play a complete hand against the dealer from a local virtual shoe. The player
follows basic strategy (simplified single-hand model): `SURRENDER` ends the
hand, `DOUBLE` takes exactly one card then stands, `HIT` draws until strategy
says stand or the hand busts, and `STAND` ends the turn. The dealer then
reveals its hole card and plays per the profile's soft-17 rule (H17/S17).
The running count only includes visible cards; the hole card counts once
revealed.

```bash
python -m app.cli play --decks 6 --seed 42
```

Example output:

```text
Played training hand (local / simulated practice only)
Player starting cards: 3, 5
Dealer upcard:         J
Actions taken:         HIT, HIT, STAND
Final player cards:    3, 5, 4, 6
Final dealer cards:    J, 7
Outcome:               PLAYER_WIN
Running count before:  +0
Running count after:   +3
True count after:      +0.51
Note:                  ... educational practice ...
```

Possible outcomes: `PLAYER_WIN`, `DEALER_WIN`, `PUSH`, `PLAYER_BUST`,
`DEALER_BUST`, `SURRENDER`. No money is ever involved.

### Pair splits (v0.6)

When basic strategy says SPLIT on a pair, the simulator now plays it out: the
pair is divided into two hands, each gets a new card, and each is played
independently. The dealer then plays **once** and each sub-hand is resolved
against the dealer's final hand. The CLI prints the original hand, both split
hands with their actions and outcomes, and the dealer's final cards.

**Re-splitting and split aces** are now fully simulated — see
[Full re-split tree simulator (v1.6.0)](#full-re-split-tree-simulator-v160)
below. There is no money, bankroll, betting units, or payout modelling.

## Quiz mode (v0.7)

Drill your decisions from the terminal. The **strategy quiz** poses a random
hand and grades your action; the **count quiz** checks your Hi-Lo running count.

Strategy quiz (non-interactive, pass your answer):

```bash
python -m app.cli quiz --seed 42 --answer H
```

```text
Strategy quiz (local / educational practice only)
Player cards:   Q, 3
Dealer upcard:  2
Profile:        MULTI_DECK_H17_DAS_LS
Your answer:    HIT
Correct action: STAND
Result:         Incorrect
Why:            Hard 13 vs dealer 2 [MULTI_DECK_H17_DAS_LS]: STAND. ...
```

Accepted answers: `H`/`HIT`, `S`/`STAND`, `D`/`DOUBLE`, `P`/`SPLIT`,
`R`/`SURRENDER` (case-insensitive). Omit `--answer` to be prompted
interactively (`Your action? [H/S/D/P/R]:`).

Count quiz (check your running count):

```bash
python -m app.cli count-quiz --cards 2,5,K,A,9 --answer 0
```

```text
Hi-Lo running-count quiz (local / educational practice only)
Cards:                2, 5, K, A, 9
Your answer:          +0
Correct running count: +0
Result:               Correct
Note:                 ... educational practice ...
```

The quiz is **educational practice only** — no real tables, betting,
camera/video, or promise of winnings.

## Scored training sessions (v0.8)

Run multiple questions at once and get a summary (total, correct, incorrect,
accuracy, and weak spots).

Strategy session (pass one answer per question):

```bash
python -m app.cli quiz-session --questions 10 --seed 42 --answers H,S,D,H,R,S,H,D,P,S
```

```text
Strategy training session (local / educational practice only)
Total questions:  10
Correct:          2
Incorrect:        8
Accuracy:         20.0%
Weak spots:       double, hard, hit, stand, surrender
Note:             You answered 2/10 correctly. ...
```

Count session (one running count per batch; batches separated by `|`):

```bash
python -m app.cli count-session --batches "2,5,K|A,9,3|10,6,2" --answers "1,-1,1"
```

```text
Hi-Lo count training session (local / educational practice only)
Total questions:  3
Correct:          2
Incorrect:        1
Accuracy:         66.7%
Weak spots:       Q2 (A,9,3)
Note:             You answered 2/3 running counts correctly. ...
```

Omit `--answers` in either command to be prompted per question/batch.

## Local session history (v1.2.0)

Add `--save` to a session to store a small JSON **summary** locally, then
review your progress with `history`:

```bash
blackjack-coach quiz-session --questions 10 --seed 42 --answers H,S,D,H,R,S,H,D,P,S --save
blackjack-coach history
```

Example `history` output:

```text
=== Practice History ===
========================
Total sessions  : 2
Average accuracy: 50.0%
Best accuracy   : 100.0%
Worst accuracy  : 0.0%

-- Most common weak spots --
  - hard (x1)
  - hit (x1)
```

Files are written to `./.blackjack_coach/history` by default; override with
`--history-dir <path>` (on a session) or `--dir <path>` (on `history`), and
limit the summary with `history --limit N`. The history stores **only a
summary** (mode, totals, accuracy, weak spots) — never money, bankroll, bets,
accounts, or personal data — and the `.blackjack_coach/` folder is git-ignored
so nothing is committed.

## Deviation study mode (v1.3.0)

Study a small, explicit set of well-known Hi-Lo **true-count deviations**. This
is layered on top of the basic-strategy engine — it never modifies it. It is a
local **study aid**, not live casino assistance, and involves no betting,
bankroll, or bet spread.

```bash
blackjack-coach deviations --cards 10,6 --dealer 10 --true-count 1
blackjack-coach deviations --list
blackjack-coach deviation-quiz --seed 42 --answer S
```

`deviations` shows the basic action, whether a studied deviation applies at the
given true count, and the resulting study recommendation with an explanation.
`deviations --list` lists the available rules (id, title, threshold, and the
`basic -> deviation` change). `deviation-quiz` poses a study question and grades
your answer (omit `--answer` to be prompted).

The set is intentionally small (not the full Illustrious 18) and the insurance
deviation is **study-only** — it does not change the engine's insurance stance
(always NO). Every recommendation notes that results depend on the rule
profile, deck estimation, true-count rounding, and table context.

## Decision diagnostics (v1.3.0)

`diagnose` explains the reasoning behind a recommended play, so you learn the
*why*, not just the *what*:

```bash
blackjack-coach diagnose --cards A,7 --dealer 9
```

It prints the recommended action plus the **decision factors**: the hand shape
(hard / soft / pair), the dealer upcard's strength, which options
(double / surrender / split) are available or fall back, and the rule-profile
(H17/S17) context. It reads the stable strategy engine and never modifies it.

## Expanded rule profiles (v1.4.0)

The coach ships a range of rule profiles for single, double, four, six, and
eight decks, covering H17/S17, DAS/NDAS, and LS/NS combinations. List and
inspect them, and pass any profile to the other commands:

```bash
blackjack-coach profiles --list
blackjack-coach profiles --profile MULTI_DECK_H17_DAS_LS
blackjack-coach diagnose --cards A,7 --dealer 9 --profile SIX_DECK_S17_DAS_LS
```

`profiles --list` shows each profile's key, decks, soft-17 rule, DAS/NDAS,
LS/NS, and a short description; `profiles --profile <KEY>` shows full detail
(name, decks, soft-17, DAS, surrender, resplit, max split hands, hit split
aces, blackjack payout, notes, and description).

Shorthand for the rule codes: **H17/S17** = dealer hits/stands on soft 17;
**DAS/NDAS** = double-after-split allowed / not allowed; **LS/NS** = late
surrender / no surrender. The split-related fields (`resplit_allowed`,
`max_split_hands`, `hit_split_aces`, `double_after_split`) now drive real play
in the simulator — see [Full re-split tree simulator (v1.6.0)](#full-re-split-tree-simulator-v160).

## Profile-aware split rules (v1.5.0)

Some of the v1.4.0 profile metadata now drives real play. The simulator and
`diagnose` respect the profile's split rules, and a `split-rules` command shows
the available options for a hand:

```bash
blackjack-coach split-rules --cards A,A --profile SIX_DECK_H17_DAS_LS
blackjack-coach diagnose --cards A,A --dealer 6 --profile SIX_DECK_H17_DAS_LS
blackjack-coach play --decks 6 --seed 5 --profile SIX_DECK_H17_DAS_LS
```

What is now profile-aware:

- **Split aces**: when `hit_split_aces` is false (the common rule), each split
  ace receives exactly **one card** and is locked; when true, the hands are
  played normally.
- **Double after split**: split sub-hands only double when `double_after_split`
  is allowed.
- **Re-split / max split hands**: `can_resplit` and `max_split_hands` are
  enforced by the split-rule helpers and surfaced as honest warnings. As of
  v1.6.0 the **play** simulator also plays a full re-split tree (see below).

`split-rules` prints whether the hand is a pair / aces, whether it can split or
re-split, the max split hands, hit-split-aces, double-after-split, a reason, and
any warnings.

## Full re-split tree simulator (v1.6.0)

The `play` simulator now plays a real **split / re-split tree** instead of
treating re-splits as a simplified warning. When a split hand is again a pair
and basic strategy says SPLIT, it is re-split — provided the profile allows it:

- **`resplit_allowed`**: when false, a pair that could re-split is played as a
  normal total with a clear warning (it is never re-split).
- **`max_split_hands`**: the tree never produces more than this many hands. Once
  the cap is reached, any further pair is played as a normal total with a
  warning.
- **`hit_split_aces`**: when false, each split ace receives exactly **one card**
  and stops (no hitting, no re-splitting); when true, split aces play normally
  and may even re-split.
- **`double_after_split`**: split sub-hands double only when the profile allows
  doubling after a split.

The dealer still plays **once** for all sub-hands. The CLI shows the number of
split hands and labels each sub-hand as a `split` or `re-split` with its depth:

```bash
blackjack-coach play --decks 6 --seed 428 --profile SIX_DECK_H17_DAS_LS
```

```text
=== Played Hand (SPLIT) ===
Original hand: 8, 8
Dealer upcard: 4
Split hands  : 3

-- Split hand 1 (split, depth 1) --
Cards  : 8, A
Actions: STAND
Outcome: DEALER_BUST

-- Split hand 2 (re-split, depth 2) --
Cards  : 8, 9
Actions: STAND
Outcome: DEALER_BUST

-- Split hand 3 (re-split, depth 2) --
Cards  : 8, 6
Actions: STAND
Outcome: DEALER_BUST
```

There is still no money, bankroll, betting units, or payout modelling — this is
local, simulated practice only.

## Complete strategy matrix (v1.7.0)

Print the full basic-strategy decision matrix for any profile and audit its
coverage. The matrix covers **hard totals 5-21**, **soft totals 13-21**, and
**pairs** (A,A and 2,2..10,10) against every dealer upcard (**2-10 and A**) —
360 decisions per profile — so the coach can prove it has an answer everywhere.

```bash
blackjack-coach matrix --profile SIX_DECK_H17_DAS_LS --section hard
blackjack-coach matrix --profile SIX_DECK_H17_DAS_LS --section pairs --audit
```

```text
=== Strategy Matrix ===
Profile: SIX_DECK_H17_DAS_LS
Section: hard

Strategy Matrix [SIX_DECK_H17_DAS_LS]
Codes: H hit, S stand, D double, P split, R surrender (lowercase = legal fallback)

-- Hard Totals --
            2   3   4   5   6   7   8   9  10   A
...
Hard 16     S   S   S   S   S   H   H   R   R   R
...

-- Coverage summary --
Total cells   : 360
Fallback cells: 0
Missing cells : 0
```

`--section` selects `hard`, `soft`, `pairs`, or `all` (default). Action codes
are shown in **uppercase for a direct chart play** and **lowercase when a legal
fallback was applied** (for example, surrender falling back to hit when the
profile has no surrender). Add `--audit` to list the fallback cells, any missing
cells, and the fallback notes — a quick coverage check when a profile's rules
change which plays are legal.

## Decision audit (v1.7.0)

`audit` reports the mechanics behind a single hand's recommendation: which
category it is, which strategy table is consulted, the raw chart action vs the
recommended action, whether a legal fallback was applied, and which actions are
legal under the profile.

```bash
blackjack-coach audit --cards A,7 --dealer 9 --profile SIX_DECK_H17_DAS_LS
```

```text
=== Decision Audit ===
Cards             : A, 7
Dealer            : 9
Profile           : SIX_DECK_H17_DAS_LS
Hand              : Soft 18 vs dealer 9
Category          : soft
Table section     : soft
Recommended action: HIT
Raw table action  : HIT
Fallback applied  : no
Legal actions     : HIT, STAND, DOUBLE, SURRENDER
Explanation       : Soft 18 vs dealer 9 is read from the soft-totals table. ...
```

Where `diagnose` explains a decision in plain language (and now shows a compact
audit summary too), `audit` reports the underlying mechanics. Both read the
stable strategy engine and never modify it.

## Outcome / win-loss history (v1.8.0)

Optionally record the result of each played practice hand to a local JSON
folder, then review your outcomes over time. This complements the decision
tooling: it tracks **wins, losses, pushes, surrenders, player/dealer busts**,
and **split / re-split results** (counted per sub-hand). It is a summary only —
no money, bankroll, bets, or accounts.

```bash
blackjack-coach play --decks 6 --seed 428 --profile SIX_DECK_H17_DAS_LS --save-outcome
blackjack-coach outcomes
blackjack-coach outcomes --limit 10
blackjack-coach outcomes --profile SIX_DECK_H17_DAS_LS
```

`play --save-outcome` writes one JSON record and prints its path (use
`--outcome-dir` to choose where; the default is `./.blackjack_coach/outcomes`).
`outcomes` summarises the saved records:

```text
=== Outcome History ===
Total records      : 2
Wins               : 4
Losses             : 0
Pushes             : 0
Surrenders         : 0
Player busts       : 0
Dealer busts       : 1
Split records      : 1
Average split hands: 3.00
Most common profile: SIX_DECK_H17_DAS_LS

-- Most common outcomes --
  - SPLIT (x1)
  - PLAYER_WIN (x1)
```

`--limit N` summarises only the most recent N outcomes and `--profile <KEY>`
filters by rule profile. Records store only practice data (profile, seed,
cards, actions, result counts) — never money, bankroll, bets, accounts, tokens,
or personal data — and the `.blackjack_coach/` folder is git-ignored, so nothing
is committed. No database, no network, no cloud.

## Guided coach mode (v1.9.0)

In guided coach mode the **coach decides and explains** - you ask, it teaches.
You do not pick the action; the coach recommends the correct play, explains why,
and (for a full hand) executes each decision and shows the result.

Ask for a single best play:

```bash
blackjack-coach coach --cards A,7 --dealer 9 --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards 8,8 --dealer 6 --profile SIX_DECK_H17_DAS_LS
```

```text
=== Guided Coach ===
Cards             : A, 7
Dealer upcard     : 9
Profile           : SIX_DECK_H17_DAS_LS
Hand              : Soft 18 vs dealer 9
Recommended action: HIT
Raw table action  : HIT
Fallback applied  : no
Legal actions     : HIT, STAND, DOUBLE, SURRENDER
Why             : Soft 18 vs dealer 9 [SIX_DECK_H17_DAS_LS]: HIT. ...
```

Let the coach play a whole hand, step by step:

```bash
blackjack-coach coach-play --decks 6 --seed 42 --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach-play --decks 6 --seed 42 --profile SIX_DECK_H17_DAS_LS --save-outcome
```

Each step shows the player's cards, the dealer upcard, the coach's recommended
action, and why; the result section then shows the final hands, outcome, result
label, and step count. Add `--save-outcome` (and optional `--outcome-dir`) to
store the result in the v1.8.0 outcome history.

How the commands relate: `coach` gives **direct advice** for one hand;
`coach-play` lets the coach **play a full hand** automatically; `play` is the
existing auto-simulation; `audit` is the **technical** breakdown; and
`diagnose` is the **expanded** explanation. The coach never modifies the
strategy engine - it only reads it.

## Count-aware coach advice (v1.11.0)

By default the coach uses basic strategy. If you also know the **true count**,
pass `--true-count` and the coach folds in the educational deviation study,
comparing the basic play with the count-adjusted play and choosing a final
recommendation.

```bash
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 1
blackjack-coach coach --cards 10♠,5♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 4
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach-play --decks 6 --seed 42 --profile SIX_DECK_H17_DAS_LS --true-count 1
```

```text
=== Guided Coach ===
Cards             : 10♠, 6♥
Dealer upcard     : 10♦
Profile           : SIX_DECK_H17_DAS_LS
Hand              : Hard 16 vs dealer 10
Recommended action: SURRENDER
...
-- Count-aware advisory --
True count              : 1
Basic action            : SURRENDER
Count-adjusted action   : STAND
Deviation applied       : yes
Deviation rule          : Hard 16 vs 10: stand at TC >= 0
Final recommended action: STAND
```

- **No `--true-count`**: basic strategy / audit only, exactly as before; no
  deviation is applied.
- **With `--true-count`**: if a studied deviation applies, the final action
  becomes the deviation action and the explanation names the rule; otherwise the
  final action stays the basic play and the coach says no deviation applies.
- `coach-play --true-count` shows the true count per step as **advisory context
  only** - the hand is still played with basic strategy.

The deviation set is intentionally small (study only). The insurance deviation
is never the coach's final action - insurance advice stays NO. The basic engine
recommendation is always preserved and never modified.

## Probability & EV advisor (v1.12.0)

See the risk behind a decision, not just the recommended play. `odds` shows the
approximate player bust chance, the dealer's final-total distribution, and a
rough EV per action; `coach --show-odds` adds a compact version to the coach
output.

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS
blackjack-coach odds --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 1 --show-odds
```

```text
=== Probability Advisor ===
Cards             : 10♠, 6♥
Dealer upcard     : 10♦
Recommended action: SURRENDER
Bust if hit       : 61.5%
Dealer bust       : 21.2%

-- Action EV estimates --
HIT       : EV -0.569 | win 18.5% loss 75.4% push 6.1% bust 61.5%
STAND     : EV -0.576 | ...
SURRENDER : EV -0.500 | ...
Best estimated action: SURRENDER
```

These figures are **approximate** (an idealised shoe with a one-card
look-ahead) and are for understanding risk only. They **never override** the
strategy recommendation - if the best-EV action differs, the coach says so and
keeps the recommendation. `--true-count` and `--decks` are accepted; the global
`--no-color` / `--plain-cards` flags apply.

## Composition-aware Probability & EV (v1.14.0)

The advisor can use the **actual composition** of the remaining shoe. Tell it
which cards you know - your cards, the dealer upcard, and any other cards you
have seen or that were removed - and it sharpens the numbers. The dealer
final-total distribution is then computed **exactly for that finite shoe**
(ten-values aggregated, with card depletion as the dealer draws), while player
HIT/DOUBLE EV uses a one-card look-ahead and stays approximate.

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --seen-cards 2♣,5♦,K♠,A♥ --composition
blackjack-coach odds --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS --seen-cards 10♣,10♦,A♥
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 1 --show-odds --seen-cards 2♣,5♦,K♠,A♥
```

```text
=== Probability Advisor ===
Cards              : 10♠, 6♥
Dealer upcard      : 10♦
Composition-aware  : yes
Cards remaining    : 305
Removed/known cards: 7
Recommended action : SURRENDER
Bust if hit        : 61.6%

-- Shoe composition --
Total cards remaining: 305
Rank counts     : 2:23  3:24  ...  10:93  A:23
```

Flags:

- `--composition-aware` turns on the finite-shoe calculation.
- `--seen-cards <cards>` lists other exposed/removed cards (e.g.
  `2♣,5♦,K♠,A♥`) and **auto-enables** composition-aware mode.
- `--composition` prints the remaining-shoe summary (total cards, removed
  count, and compact per-rank counts); it implies `--composition-aware`.
- On `coach`, `--composition-aware` / `--seen-cards` apply when combined with
  `--show-odds` (and stack with `--true-count`).

This layer **separates exact, approximate, and advisory** clearly: the dealer
distribution is exact finite-shoe, player HIT/DOUBLE EV is an approximate
one-card look-ahead, and SPLIT/re-split EV is now modelled separately (see
below). Impossible compositions (e.g. five aces in one deck) are flagged with a
clear warning. As always, it is **advisory only** and never changes
`strategy_engine.recommend()` or the Hi-Lo counting math.

## Split / re-split EV advisor (v1.15.0)

For pairs, the advisor now computes a proper composition-aware EV for
**splitting and re-splitting** instead of the old simplified placeholder. It
respects the profile's split rules - `split_allowed`, `resplit_allowed`,
`max_split_hands`, `hit_split_aces`, and double-after-split (DAS) - and
enumerates the re-split tree against the exact finite-shoe dealer distribution.

```bash
blackjack-coach odds --cards 8♠,8♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards A♠,A♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach coach --cards 8♠,8♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware
```

```text
-- Split EV estimate --
Split allowed        : yes
Resplit allowed      : yes
Max split hands      : 4
Hit split aces       : no
DAS                  : yes
Estimated split EV   : +0.373
Sub-hands evaluated  : 28
Exact for these rules: no
Compare         : HIT -0.438  STAND -0.125  DOUBLE -0.876  SURRENDER -0.500
```

When the hand is a pair, `odds` adds a **Split EV estimate** block (split rules,
estimated split EV, sub-hands evaluated, and a compact comparison vs
HIT/STAND/DOUBLE/SURRENDER), and `coach --show-odds` adds a compact Split EV
line plus whether the advisory best-EV action **agrees** with the coach's
recommendation.

**Honest about exactness:** the dealer distribution and the re-split tree
(up to `max_split_hands`) are enumerated deterministically, and split aces that
cannot be hit (one card then stand) are evaluated **exactly**. As of v1.16.0,
hittable sub-hands are played out with the recursive optimal hit/stand tree
(below); intra-hand and inter-hand card depletion are still ignored, so those
parts stay **approximate** (reported via `is_exact_for_supported_rules`). It is
**advisory only** - it never overrides the coach's final recommendation,
`strategy_engine.recommend()`, or the Hi-Lo math.

## Full player EV decision tree (v1.16.0)

The HIT EV is no longer a one-card-then-stand snapshot. v1.16.0 plays the hand
out with a **recursive optimal hit/stand tree** over the remaining shoe, and
unifies every legal action's EV into one **player EV decision tree** -
`STAND`, `HIT`, `DOUBLE`, `SURRENDER`, and (for pairs) `SPLIT`.

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards 8♠,8♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware
```

```text
-- Player EV decision tree --
Best EV action       : SURRENDER
Best EV              : -0.500
Composition aware    : yes
Exact for these rules: yes
-- EV by action --
SURRENDER : -0.500
HIT       : -0.565
STAND     : -0.577
DOUBLE    : -1.129

EV vs recommendation: agrees
```

When composition-aware is on, `odds` adds a **Player EV decision tree** block
(best EV action, EV by action, and the exactness / approximation note), and
`coach --show-odds` adds a compact player EV summary plus whether the advisory
best-EV action **agrees** with the coach's recommendation. Pairs still show the
Split EV estimate block.

**Honest about exactness:** `STAND` uses the exact finite-shoe dealer
distribution and `HIT` is a recursive optimal hit/stand tree, so multi-card
draws are no longer truncated to one ply (for non-pair hands this set of actions
is fully enumerated). The documented simplifications are that draws inside the
player tree use fixed remaining-composition probabilities (no intra-hand
depletion), the dealer distribution is taken from the pre-action shoe, and
ten-values are aggregated. It is **advisory only** and never overrides
`strategy_engine.recommend()` or the Hi-Lo math.

## Adaptive local learning (v1.13.0)

The coach gets more useful the more you practise. `learn` reads the **locally
saved** outcome history (see the outcome-history section above) and turns it
into practice insight: it groups played hands into recognisable **spots** (by
the starting two cards versus the dealer upcard, e.g. `hard_16_vs_10`,
`soft_18_vs_9`, `pair_8_vs_6`), then surfaces your strongest, weakest, and
high-variance spots plus concrete practice recommendations.

Recommended workflow:

```bash
blackjack-coach coach-play --decks 6 --seed 42 --profile SIX_DECK_H17_DAS_LS --save-outcome
blackjack-coach learn
blackjack-coach learn --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --use-history
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 1 --show-odds --use-history
```

```text
=== Adaptive Learning ===
=========================
Total records      : 12
Profiles seen      : SIX_DECK_H17_DAS_LS
Most common profile: SIX_DECK_H17_DAS_LS

-- Weakest spots --
  - hard_16_vs_10: 0W/3L/0P (seen 3, win 0.0%, LOW) -> High local loss rate ...

-- Practice recommendations --
  - Drill hard 16 vs 10: High local loss rate - revisit the correct basic play.
```

`learn` options: `--dir <path>` (history directory, default
`./.blackjack_coach/outcomes`), `--profile <KEY>` (only learn from one
profile's outcomes), `--limit N` (only the most recent N), and `--spot
<spot_id>` (focus on one spot, e.g. `hard_16_vs_10`). With no saved history it
prints a clear message: *"No saved outcome history yet. Use coach-play/play
with --save-outcome first."*

`coach --use-history` adds a **Local history context** block - matching
records, your local win/loss/push rates, a practice note, and a caution note -
built from the same saved outcomes. It combines with `--true-count` and
`--show-odds`. Crucially, this is **context only**:

- The main recommended action always comes from basic strategy
  (`strategy_engine.recommend`) and the count math - **never** from short-term
  local results.
- With fewer than 10 total records, confidence is **LOW**; with fewer than 5
  records in a spot, it is flagged as a **small sample**.
- History is used to explain patterns, recommend practice, flag weak spots, and
  show local context - never to change the base strategy, promise an edge, or
  make exact predictions.
- Learning is **local, transparent, and reversible**: it only reads JSON files
  you chose to save. No network, cloud, database, or external dependencies, and
  no money / bankroll / account / token / screenshot data.

## Professional card display (v1.10.0)

Enter and see cards with figures, suits, and colour, so the coach feels like a
complete blackjack calculator. Card input accepts several forms - all of these
mean the same hand to the engine:

```bash
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards AS,7H --dealer 9D --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards A,7 --dealer 9 --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --no-color
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --plain-cards
```

- Suits can be symbols (`♠♥♦♣`), letters (`S/H/D/C`, e.g. `AS`, `10H`, `Kd`), or
  names (`A spades`, `Q clubs`). A card with no suit shows just its rank.
- **Hearts and diamonds are shown in red**; spades and clubs use the terminal's
  default colour so they stay readable on dark backgrounds.
- `--no-color` prints plain text (no ANSI); `--plain-cards` shows ranks only
  (no suit symbols). Colour is used only on a real terminal, so piped or
  redirected output stays plain automatically.
- Simulated hands (`play`, `coach-play`, `simulate`) get deterministic
  decorative suits for a polished look.

This is a **display / input layer only**. The strategy engine always receives
plain ranks (`A♠,7♥` → `["A", "7"]`), so suits and colour never change
strategy, counting, outcomes, or scoring.

## Library usage

```python
from app import recommend, MULTI_DECK_H17_DAS_LS

rec = recommend(["A", "7"], "9", MULTI_DECK_H17_DAS_LS)
print(rec.action.value)        # HIT
print(rec.hand_description)    # Soft 18 vs dealer 9
print(rec.profile_key)         # MULTI_DECK_H17_DAS_LS
print(rec.reason)              # action + short educational note
print(rec.warnings)            # list of advisory notes (may be empty)
```

## Development

```bash
python -m pip install -e ".[dev]"   # install package + dev tooling
python -m pytest                     # run the test suite
ruff check app tests                 # lint
```

Continuous integration runs `ruff check app tests` and `python -m pytest` on
Python 3.9-3.12 for every push to `main` and every pull request
(see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Scope and roadmap

v1.12.0 adds an approximate probability & EV advisor (`app/probability_advisor.py`,
the `odds` command, and `coach --show-odds`): player bust chance, the dealer's
final-total distribution, and a rough EV per action. It is clearly labelled
approximate and never overrides the strategy recommendation. No changes to
`strategy_engine.recommend`, Hi-Lo counting math, guided coaching, outcome
history, or session history. It is a professional coach for local practice,
demo money, video games, recreational tournaments, and training.

Planned next (educational/local only): a possible v2.0 web UI if decided later.
See
[`docs/BLACKJACK_COACH_KNOWLEDGE_BASE.md`](docs/BLACKJACK_COACH_KNOWLEDGE_BASE.md)
for the full roadmap.

## Safety / Educational Scope

This is a study and practice tool only. It deliberately does **not**, and will
not:

- connect to any real casino or online gambling platform;
- place, manage, or automate real-money bets, or model a bankroll;
- use a camera, video feed, or screen scraping to read a real table;
- promise winnings or present any "guaranteed" system;
- include a betting spread, Kelly bet sizing, the Illustrious 18, or insurance
  index plays.

Card counting and the simulator exist purely for **local, simulated**
education.

## Not financial / gambling advice

Nothing here is financial advice or gambling advice. Blackjack always carries a
house edge; good basic strategy reduces losses but **cannot** guarantee wins.
Gambling involves real financial risk and can be addictive. You are responsible
for following the laws and venue rules that apply to you. If gambling is
causing harm, seek support from a local problem-gambling helpline.
