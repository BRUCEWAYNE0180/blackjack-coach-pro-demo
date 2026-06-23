# Commands Reference

A quick reference for setting up the project and using every coaching command.
Blackjack Coach Pro Demo is a professional coach for local practice, demo
money, video games, recreational tournaments, and training. (Responsible
scope: not a real-money gambling product; see `PROJECT_RULES.md`.)

The trainer is available two ways once installed: as the `blackjack-coach`
console command, or as `python -m app.cli ...`. Both accept the same
subcommands.

> **Formatting note (v1.1.0):** command output uses clear section headers,
> aligned `label : value` rows, a visible `[ CORRECT ]` / `[ INCORRECT ]`
> badge, and percentage summaries. This is presentation only — the underlying
> strategy, counting, simulation, and scoring logic is unchanged.

## Setup and quality

### version

```bash
blackjack-coach --version
```

Prints the program name and version (e.g. `blackjack-coach 1.0.0`) and exits.

### Install (editable, with dev tools)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Installs the package (standard-library only at runtime) plus `pytest` and
`ruff`.

### Test

```bash
python -m pytest
```

Runs the full automated test suite.

### Lint

```bash
ruff check app tests
```

Runs static checks and import-order rules.

## Trainer commands

### strategy

```bash
blackjack-coach --cards A,7 --dealer 9
```

Prints the basic-strategy action, an explanation, the profile, and the
always-NO insurance note (shown when the dealer's upcard is an Ace).

### count

```bash
blackjack-coach count --cards 2,5,K,A,9 --decks-remaining 5
```

Shows the Hi-Lo running count, decks remaining, and true count for the listed
cards (`--decks-remaining` must be greater than 0).

### simulate

```bash
blackjack-coach simulate --decks 6 --seed 42
```

Deals one opening hand from a local virtual shoe and prints the recommendation
plus the running/true count. `--seed` makes the shuffle reproducible.

### play

```bash
blackjack-coach play --decks 6 --seed 42
blackjack-coach play --decks 6 --seed 5 --profile SIX_DECK_H17_DAS_LS
blackjack-coach play --decks 6 --seed 428 --profile SIX_DECK_H17_DAS_LS
```

Plays a full hand against the dealer (H17/S17 dealer logic) and prints the
actions, final hands, and outcome.

When basic strategy says SPLIT, the simulator plays a full **split / re-split
tree** (v1.6.0): a split hand that is again a pair is re-split up to the
profile's `max_split_hands`, honouring `resplit_allowed`, `hit_split_aces`, and
`double_after_split`. The output lists each sub-hand, labelled `split` or
`re-split` with its depth, plus the number of split hands. The third example
above (seed 428, six-deck H17) re-splits a pair of 8s into three hands. A pair
that cannot be re-split (re-split disallowed or the maximum reached) is played
as a normal total with a clear warning; split aces with `hit_split_aces=false`
get exactly one card and stop.

### quiz

```bash
blackjack-coach quiz --seed 42 --answer H
```

Poses one basic-strategy question and grades your answer
(`H/S/D/P/R` or full names). Omit `--answer` to be prompted interactively.

### count-quiz

```bash
blackjack-coach count-quiz --cards 2,5,K,A,9 --answer 0
```

Checks your Hi-Lo running-count answer for the listed cards.

### quiz-session

```bash
blackjack-coach quiz-session --questions 10 --seed 42 --answers H,S,D,H,R,S,H,D,P,S
```

Runs a scored multi-question strategy session and prints totals, accuracy, and
weak spots. Omit `--answers` to be prompted per question.

### count-session

```bash
blackjack-coach count-session --batches "2,5,K|A,9,3|10,6,2" --answers "1,-1,1"
```

Runs a scored running-count session over several batches (separated by `|`).
Omit `--answers` to be prompted per batch.

## Session history (v1.2.0)

### Save a session

Add `--save` to a session command to store a local JSON summary (and print its
path). Use `--history-dir <path>` to choose where it is written (default:
`./.blackjack_coach/history`).

```bash
blackjack-coach quiz-session --questions 10 --seed 42 --answers H,S,D,H,R,S,H,D,P,S --save
blackjack-coach count-session --batches "2,5,K|A,9,3" --answers "1,0" --save --history-dir ./my-history
```

### history

```bash
blackjack-coach history
blackjack-coach history --limit 5
blackjack-coach history --dir ./my-history
```

Summarises saved sessions: total sessions, average/best/worst accuracy, and the
most common weak spots. `--limit N` summarises only the most recent N sessions;
`--dir` reads from a specific folder. The history is a **summary only** — no
money, accounts, or personal data — and is never committed to git.

## Deviation study mode (v1.3.0)

### deviations

```bash
blackjack-coach deviations --cards 10,6 --dealer 10 --true-count 1
blackjack-coach deviations --list
```

Shows the basic action, whether a studied true-count deviation applies, and the
resulting study recommendation. `--list` lists the available study rules (id,
title, threshold, `basic -> deviation`). Study-only and local; not live casino
advice.

### deviation-quiz

```bash
blackjack-coach deviation-quiz --seed 42 --answer S
```

Poses a deviation study question and grades your answer (`H/S/D/P/R` or full
names). Omit `--answer` to be prompted interactively. Study-only; the insurance
deviation never changes the engine's insurance recommendation.

### diagnose

```bash
blackjack-coach diagnose --cards A,7 --dealer 9
```

Explains the factors behind the recommended play: hand shape (hard/soft/pair),
dealer upcard strength, which options (double/surrender/split) are available or
fall back, and the H17/S17 rule context. Reads the stable strategy engine and
never modifies it.

## Rule profiles (v1.4.0)

### profiles

```bash
blackjack-coach profiles --list
blackjack-coach profiles --profile MULTI_DECK_H17_DAS_LS
```

`--list` shows every profile's key, decks, soft-17 rule, DAS/NDAS, LS/NS, and a
short description. `--profile <KEY>` shows full detail (name, number of decks,
dealer soft-17 rule, double-after-split, late surrender, resplit allowed, max
split hands, hit split aces, blackjack payout, notes, and description).

Rule codes: **H17/S17** = dealer hits/stands on soft 17; **DAS/NDAS** =
double-after-split allowed / not; **LS/NS** = late surrender / none. The
`resplit_allowed`, `max_split_hands`, and `hit_split_aces` fields are
descriptive metadata and do not yet change engine play.

Any profile key can be passed to the other commands via `--profile`, e.g.
`blackjack-coach diagnose --cards A,7 --dealer 9 --profile SIX_DECK_S17_DAS_LS`.

## Profile-aware split rules (v1.5.0)

### split-rules

```bash
blackjack-coach split-rules --cards A,A --profile SIX_DECK_H17_DAS_LS
blackjack-coach split-rules --cards 8,8 --split-hands 2
```

Shows whether the hand is a pair / aces, whether it can split or re-split, the
max split hands, hit-split-aces, double-after-split, a reason, and any
warnings. `--split-hands N` sets how many hands currently exist (1 = an initial
split; 2+ considers a re-split).

In v1.5.0 the simulator and `diagnose` are profile-aware: split aces get one
card each when `hit_split_aces` is false, split sub-hands double only when
`double_after_split` is allowed, and re-split is gated by `resplit_allowed` /
`max_split_hands`. As of v1.6.0 the `play` simulator plays the full re-split
tree (see the `play` section above).

## Complete strategy matrix and decision audit (v1.7.0)

### matrix

```bash
blackjack-coach matrix --profile SIX_DECK_H17_DAS_LS --section hard
blackjack-coach matrix --profile SIX_DECK_H17_DAS_LS --section pairs --audit
blackjack-coach matrix --profile SINGLE_DECK_H17_NDAS_NS --section all
```

Prints the complete basic-strategy decision matrix for a profile: hard totals
5-21, soft totals 13-21, and pairs (A,A and 2,2..10,10) against dealer 2-10 and
A (360 cells). `--section` selects `hard`, `soft`, `pairs`, or `all` (default).
Action codes are uppercase for a direct chart play and lowercase when a legal
fallback was applied. A coverage summary reports total / fallback / missing
cells and warnings; `--audit` adds the detailed list of fallback and missing
cells plus the fallback notes.

### audit

```bash
blackjack-coach audit --cards A,7 --dealer 9 --profile SIX_DECK_H17_DAS_LS
blackjack-coach audit --cards 10,6 --dealer 10 --profile SINGLE_DECK_H17_NDAS_NS
```

Audits a single hand: its category, the strategy table consulted, the raw chart
action vs the recommended action, whether a legal fallback was applied (with the
reason), the legal actions under the profile, any warnings, and a plain-language
explanation. Reads the stable strategy engine and never modifies it. The
`diagnose` command also shows a compact version of this audit.

## Outcome / win-loss history (v1.8.0)

### play --save-outcome

```bash
blackjack-coach play --decks 6 --seed 428 --profile SIX_DECK_H17_DAS_LS --save-outcome
blackjack-coach play --decks 6 --seed 42 --save-outcome --outcome-dir ./my_outcomes
```

Adds `--save-outcome` (and optional `--outcome-dir`) to the `play` command: it
plays the hand, records the result as a local JSON file, and prints the saved
path. Works for both normal hands and split / re-split hands (per-sub-hand
results are counted). The default directory is `./.blackjack_coach/outcomes`.

### outcomes

```bash
blackjack-coach outcomes
blackjack-coach outcomes --limit 10
blackjack-coach outcomes --profile SIX_DECK_H17_DAS_LS
blackjack-coach outcomes --dir ./my_outcomes
```

Summarises the saved outcome history: total records, wins, losses, pushes,
surrenders, player/dealer busts, split records, average split hands, the most
common profile, and the most common outcomes. `--limit N` summarises only the
most recent N records; `--profile <KEY>` filters by rule profile; `--dir <path>`
reads a custom directory. The history is a summary only - no money, bankroll,
bets, accounts, or personal data - and is never committed (the
`.blackjack_coach/` folder is git-ignored).

## Guided coach mode (v1.9.0)

### coach

```bash
blackjack-coach coach --cards A,7 --dealer 9 --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards 8,8 --dealer 6 --profile SIX_DECK_H17_DAS_LS
```

Direct advice for one hand: the coach prints the recommended action, the raw
chart action, whether a fallback was applied, the legal actions, and a
plain-language why. The user does not pick the action - the coach decides and
explains.

Add `--true-count <n>` to fold in the educational deviation study (v1.11.0):

```bash
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 1
blackjack-coach coach --cards 10♠,5♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 4
```

With a true count, the output adds a count-aware advisory: the true count, basic
action, count-adjusted action (when a deviation applies), whether a deviation
was applied, the deviation rule, and the final recommended action. Without
`--true-count`, the coach uses basic strategy only. The insurance deviation is
study-only and never becomes the final action.

### coach-play

```bash
blackjack-coach coach-play --decks 6 --seed 42 --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach-play --decks 6 --seed 42 --profile SIX_DECK_H17_DAS_LS --save-outcome
```

The coach plays a full simulated hand, choosing every action automatically. It
shows a step-by-step recommendation (player cards, dealer upcard, recommended
action, why) for each decision, then the final hands, outcome, result label, and
step count. `--save-outcome` (with optional `--outcome-dir`) stores the result
in the local outcome history (v1.8.0). `--true-count <n>` (v1.11.0) shows the
true count as advisory context per step; the hand is still played with basic
strategy.

How the decision commands relate: `coach` is direct advice; `coach-play` lets
the coach play a hand; `play` is the existing auto-simulation; `audit` is the
technical breakdown; `diagnose` is the expanded explanation. None of them change
the strategy engine.

## Professional card display (v1.10.0)

The card-facing commands (`coach`, `coach-play`, `play`, `simulate`, `diagnose`,
`audit`, `split-rules`) accept and show cards with suits and colour.

Card input forms (all equivalent for the engine):

```bash
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards AS,7H --dealer 9D --profile SIX_DECK_H17_DAS_LS
blackjack-coach coach --cards A,7 --dealer 9 --profile SIX_DECK_H17_DAS_LS
```

- Suits: symbols `♠♥♦♣`, letters `S/H/D/C` (e.g. `AS`, `10H`, `Kd`), or names
  (`A spades`, `Q clubs`). No suit -> rank only.
- Hearts/diamonds render red; spades/clubs use the default colour.

Global display flags (accepted by any command, anywhere on the line):

```bash
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --no-color
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --plain-cards
```

- `--no-color`: plain text, no ANSI colour codes.
- `--plain-cards`: ranks only, no suit symbols.

Colour is used only on a real terminal; captured or piped output is plain text.
The display layer never changes strategy, counting, outcomes, or scoring - the
engine always receives plain ranks.

## Probability & EV advisor (v1.12.0)

### odds

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS
blackjack-coach odds --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS
```

Prints an approximate probability / EV advisory: the recommended action, the
player's bust-if-hit chance, the dealer bust chance, the dealer's final-total
probabilities (17/18/19/20/21/bust), a per-action EV estimate (with win / loss /
push / bust), the best estimated action, and an approximation note. Flags:
`--decks` (idealised model size), `--true-count` (for the recommended action),
`--save-ev-snapshot` and `--ev-dir <path>` (save a local EV snapshot for review;
see "EV snapshot history & review" below), plus the global `--no-color` /
`--plain-cards`.

### coach --show-odds

```bash
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --true-count 1 --show-odds
```

Adds a compact approximate odds summary (bust if hit, dealer bust, best
estimated action) to the coach output.

These figures are **approximate** (idealised shoe, one-card look-ahead) and
never override the recommendation: if the best-EV action differs from the
strategy recommendation, the advisor says so and keeps the recommendation.

## Composition-aware Probability & EV (v1.14.0)

### odds --composition-aware

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
```

Uses the **finite-shoe composition** of the remaining cards instead of an
idealised shoe. The dealer final-total distribution is computed **exactly** for
that shoe (ten-values aggregated, with depletion as the dealer draws). Player
HIT/DOUBLE EV is an approximate one-card look-ahead; SPLIT EV is simplified.

### odds --seen-cards

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --seen-cards 2♣,5♦,K♠,A♥
blackjack-coach odds --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS --seen-cards 10♣,10♦,A♥
```

Lists other exposed/removed cards (comma-separated; plain or suited). They are
removed from the shoe alongside the player's cards and dealer upcard, and the
flag **auto-enables** composition-aware mode. Declaring impossible compositions
(e.g. five aces in one deck) produces a clear warning and never negative counts.

### odds --composition

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --seen-cards 2♣,5♦ --composition
```

Prints a remaining-shoe summary: total cards remaining, removed count, the
known/seen cards, and compact per-rank counts. Implies `--composition-aware`.

### coach --show-odds (composition-aware)

```bash
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 1 --show-odds --seen-cards 2♣,5♦,K♠,A♥
```

`coach` accepts `--composition-aware` and `--seen-cards`; they apply to the
odds block when combined with `--show-odds` and stack with `--true-count`. The
compact block shows the composition-aware status, cards remaining, bust if hit,
dealer bust, and the best estimated action.

This layer cleanly **separates exact, approximate, and advisory**: exact
finite-shoe dealer distribution, approximate player HIT/DOUBLE EV, and (for
pairs) a composition-aware SPLIT/re-split EV (see below). It is advisory only
and never overrides `strategy_engine.recommend()` or the Hi-Lo math.

## Split / re-split EV advisor (v1.15.0)

### odds (pairs)

```bash
blackjack-coach odds --cards 8♠,8♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards A♠,A♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards 10♠,10♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards 8♠,8♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --seen-cards 2♣,5♦,K♠,A♥ --composition
```

When the hand is a pair, `odds` (in composition-aware mode) adds a **Split EV
estimate** block: split allowed, resplit allowed, max split hands, hit split
aces, DAS, the estimated split EV, the number of sub-hands evaluated, whether it
is exact for the active rules, and a compact comparison vs
HIT/STAND/DOUBLE/SURRENDER. The re-split tree is enumerated up to
`max_split_hands`, and split aces that cannot be hit are evaluated exactly.

### coach --show-odds (pairs)

```bash
blackjack-coach coach --cards 8♠,8♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware
```

For pairs, the compact odds block adds a Split EV line and shows whether the
advisory best-EV action **agrees** with the coach's recommendation. The coach's
final recommendation is never overridden automatically.

Honest about exactness: the dealer distribution and the re-split tree are
enumerated deterministically and split aces (one card then stand) are exact;
as of v1.16.0 hittable sub-hands are played with the recursive hit/stand tree;
intra-hand and inter-hand depletion are ignored, so those parts stay approximate
(reported via `is_exact_for_supported_rules`).

## Full player EV decision tree (v1.16.0)

### odds (Player EV decision tree)

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
blackjack-coach odds --cards 8♠,8♥ --dealer 6♦ --profile SIX_DECK_H17_DAS_LS --composition-aware
```

In composition-aware mode, `odds` adds a **Player EV decision tree** block: the
best EV action, the EV by action (`STAND` / `HIT` / `DOUBLE` / `SURRENDER`, and
`SPLIT` for pairs), whether it is exact for the active rules, the
exactness/approximation note, and whether the best-EV action agrees with the
coach's recommendation. `HIT` is a recursive optimal hit/stand tree (no longer a
one-card snapshot). Pairs still show the Split EV estimate block as well.

### coach --show-odds (Player EV decision tree)

```bash
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware
```

The compact odds block shows the player EV best action and whether it agrees
with the coach's recommendation (with a short note when it differs). The coach's
final recommendation is never overridden automatically.

Honest about exactness: `STAND` uses the exact finite-shoe dealer distribution
and `HIT` is fully recursive; for non-pair hands the HIT/STAND/DOUBLE/SURRENDER
set is enumerated. The documented simplifications are fixed
remaining-composition draw probabilities (no intra-hand depletion), the dealer
distribution from the pre-action shoe, and ten-value aggregation. Advisory only.

## Adaptive local learning (v1.13.0)

### learn

```bash
blackjack-coach learn
blackjack-coach learn --profile SIX_DECK_H17_DAS_LS
blackjack-coach learn --dir ./my_outcomes --limit 50
blackjack-coach learn --spot hard_16_vs_10
```

Reads the locally saved outcome history (from `play`/`coach-play
--save-outcome`) and prints an "Adaptive Learning" summary: total records,
profiles seen, the most common profile, your strongest / weakest / high-variance
spots, the most common outcomes, practice recommendations, a data-quality note,
and notes. Spots are keyed by the starting two cards versus the dealer upcard
(e.g. `hard_16_vs_10`, `soft_18_vs_9`, `pair_8_vs_6`, `pair_A_vs_6`).

Flags: `--dir <path>` (history directory, default `./.blackjack_coach/outcomes`),
`--profile <KEY>` (only learn from that profile's outcomes), `--limit N` (only
the most recent N records), and `--spot <spot_id>` (focus on one spot). With no
saved history it prints: *"No saved outcome history yet. Use coach-play/play
with --save-outcome first."*

The recommended workflow is: play with `coach-play --save-outcome`, review with
`learn`, then use `coach --use-history` for personalised context. Learning is
local and read-only; it never changes the strategy recommendation.

### coach --use-history

```bash
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --use-history
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --true-count 1 --show-odds --use-history
blackjack-coach coach --cards A♠,7♥ --dealer 9♦ --profile SIX_DECK_H17_DAS_LS --use-history --history-dir ./my_outcomes
```

Adds a "Local history context" block to the coach output: matching records,
your local win / loss / push rates for this spot (or a similar one), a practice
note, and a caution note. `--history-dir <path>` chooses the outcomes directory.
It combines with `--true-count` and `--show-odds`.

This is **context only** and never changes the recommendation: the main action
always comes from basic strategy and the count math. Confidence is LOW with
fewer than 10 total records, and a spot with fewer than 5 records is flagged as
a small sample. If there is no saved history, the block prints a clear message
and the coach continues normally.

## EV snapshot history & review (v1.17.0)

The probability / EV advisor is advisory only. v1.17.0 lets you save a **local
EV snapshot** of the advisory for a hand and later review when the coach's main
recommendation agreed with the advisory best-EV action and when it differed. It
never changes the recommendation, `strategy_engine.recommend()`, or the Hi-Lo
math.

### odds --save-ev-snapshot

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware --save-ev-snapshot
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware --save-ev-snapshot --ev-dir ./my_ev
```

Computes the odds / EV advisory exactly as before, then saves a local
`EVSnapshotRecord` as JSON and prints the saved path. The snapshot stores the
profile, cards, dealer upcard, decks, optional true count / seen cards, the
recommended and best-EV actions, the per-action EVs, the recommended action's EV
and the best EV, the EV gap, whether they agree, and documentation notes.
`--ev-dir <path>` chooses the directory (default `./.blackjack_coach/ev_snapshots`).

### coach --save-ev-snapshot

```bash
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware --save-ev-snapshot
```

Saves the odds advisory snapshot while keeping the coach's main decision intact.
It **requires `--show-odds`** (there is no advisory to snapshot otherwise);
`--save-ev-snapshot` without `--show-odds` prints a clear error
(`--save-ev-snapshot requires --show-odds`). `--ev-dir <path>` chooses the
directory.

### ev-review

```bash
blackjack-coach ev-review
blackjack-coach ev-review --limit 20
blackjack-coach ev-review --profile SIX_DECK_H17_DAS_LS
blackjack-coach ev-review --disagreements-only
blackjack-coach ev-review --min-gap 0.05
```

Prints an "EV Snapshot Review": total snapshots, agreement count, disagreement
count, agreement rate, the most common profile, the most common recommended
actions, the most common best-EV actions, the largest EV gaps, the disagreement
spots, practice recommendations, a data-quality note, and warnings. Flags:
`--dir <path>` (snapshot directory, default `./.blackjack_coach/ev_snapshots`),
`--limit N`, `--profile <KEY>`, `--disagreements-only` (only snapshots where
strategy and the advisory best-EV action differed), and `--min-gap <ev>` (only
count disagreements whose EV gap is at least that size when detecting gaps /
spots). With fewer than 10 snapshots the data-quality note flags a **LOW
sample**. With no saved data it prints: *"No saved EV snapshots yet. Use
odds/coach with --save-ev-snapshot first."*

A handy local self-study loop is: `coach`/`odds --save-ev-snapshot` →
`ev-review` → `learn`. Snapshots are a safe local summary only - no money,
bankroll, bets, accounts, tokens, screenshots, or personal data - stored under
the git-ignored `.blackjack_coach/` tree and never committed.

## Strategy-vs-EV explanation engine (v1.18.0)

The probability / EV advisor is advisory only. v1.18.0 explains, in plain
language, when the coach's recommendation agrees with the advisory best-EV
action and when it differs - and, when it differs, why (a tiny / small / medium
/ large EV gap, the remaining-shoe composition, the true count, split / re-split
context, a surrender threshold, or the documented limits of the EV model). It is
an explanation layer only and never overrides the recommendation,
`strategy_engine.recommend()`, or the Hi-Lo math.

EV gap bands: `TINY` `[0, 0.02)`, `SMALL` `[0.02, 0.05)`, `MEDIUM` `[0.05,
0.15)`, `LARGE` `[0.15, inf)`; `UNKNOWN` when there is no EV gap.

### odds --explain-ev

```bash
blackjack-coach odds --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --composition-aware --explain-ev
```

Appends a "Strategy vs EV explanation" block: the coach recommendation, the best
EV action, the EV gap, the gap label, the agreement status, the explanation, and
an advisory note. Combines with `--composition-aware`, `--seen-cards`,
`--true-count`, and `--save-ev-snapshot`.

### coach --explain-ev

```bash
blackjack-coach coach --cards 10♠,6♥ --dealer 10♦ --profile SIX_DECK_H17_DAS_LS --show-odds --composition-aware --explain-ev
```

Adds the same explanation block to the coach output while keeping the main
decision intact. It **requires `--show-odds`** (there is no advisory to explain
otherwise); `--explain-ev` without `--show-odds` prints a clear error
(`--explain-ev requires --show-odds`).

### ev-review --explain

```bash
blackjack-coach ev-review --explain
blackjack-coach ev-review --disagreements-only --explain
```

After the normal review, appends Strategy-vs-EV explanations for the top
disagreement spots (largest EV gap first).

### ev-review --large-gaps-only

```bash
blackjack-coach ev-review --large-gaps-only --explain
```

Narrows the review to snapshots whose EV gap is **LARGE**, or **MEDIUM** when
there is no LARGE gap. Pair it with `--explain` to see why those spots differ;
review them with `odds` and `audit`.

## Exportable learning reports (v1.19.0)

### report

```bash
blackjack-coach report
blackjack-coach report --format markdown --print
blackjack-coach report --format json --output report.json
blackjack-coach report --format csv --profile SIX_DECK_H17_DAS_LS
blackjack-coach report --profile SIX_DECK_H17_DAS_LS --limit 20
```

Builds a single local report that combines your session history, outcome /
win-loss history, EV snapshots, the Strategy-vs-EV review, weak / strong spots,
and practice recommendations. The Markdown report has these sections: Overview,
Session training, Outcome history, EV snapshots, Strategy-vs-EV review, Weak
spots, Practice recommendations, and Data quality / warnings.

Flags:

- `--format markdown|json|csv` - output format (default `markdown`; an unknown
  format prints a clear error). CSV is a compact `key,value` layout (stdlib
  `csv`, no pandas).
- `--output <path>` - write to an exact file. Without it, a timestamped file is
  written under `./.blackjack_coach/reports` and the saved path is printed.
- `--print` - also echo the report content to the terminal.
- `--profile <KEY>` - scope outcomes / EV snapshots to one rule profile
  (sessions are not profile-scoped).
- `--limit N` - use only the most recent N records per area.
- `--session-dir` / `--outcome-dir` / `--ev-dir` - read from custom history
  folders.

EV snapshots are included automatically when present (there is no
`--include-ev` flag). With no saved history the report says "No saved local
history yet"; with little data it flags a **LOW sample / limited data** note.
Reports are a local, read-only summary only - no money, bankroll, bets,
accounts, tokens, or personal data - and live under the git-ignored
`.blackjack_coach/reports` tree (unless `--output` is given), never committed.

## Profile dashboard & trends (v1.20.0)

### dashboard

```bash
blackjack-coach dashboard
blackjack-coach dashboard --profile SIX_DECK_H17_DAS_LS
blackjack-coach dashboard --limit 20
blackjack-coach dashboard --markdown
blackjack-coach dashboard --export
blackjack-coach dashboard --profile SIX_DECK_H17_DAS_LS --export --output dashboard.md
```

Shows a local per-profile training dashboard that answers: which profile am I
practising most, where am I failing, which spots have the most Strategy-vs-EV
disagreements, and what should I drill next. It groups outcomes and EV snapshots
by rule profile (sessions are not profile-scoped and are shown globally),
combines the existing summarisers, adds a simple recent-sample trend, and prints
a concrete next-practice plan. The text view has these sections: Dashboard
overview, Profiles, Selected profile (with `--profile`), Trends, Weak spots, EV
disagreements, Next practice plan, and Data quality.

Flags:

- `--profile <KEY>` - scope outcomes / EV snapshots to one rule profile.
- `--limit N` - use only the most recent N records per area.
- `--session-dir` / `--outcome-dir` / `--ev-dir` - read from custom history
  folders.
- `--markdown` - print the dashboard as Markdown (for Notion / GitHub) instead
  of compact text.
- `--export` - save a Markdown file under `./.blackjack_coach/reports` and print
  the path.
- `--output <path>` - save to an exact file path.

With no saved history it prints "No saved local history yet. Use
quiz-session/play/coach-play/odds with save flags first."; with little data it
flags a **LOW sample / limited data** note. The dashboard uses no external chart
libraries (trends are plain text / Markdown tables), exports no sensitive data,
and never changes the strategy recommendation - it only suggests practice.






