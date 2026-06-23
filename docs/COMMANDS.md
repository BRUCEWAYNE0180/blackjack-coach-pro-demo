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




