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
```

Plays a full hand against the dealer (H17/S17 dealer logic), including basic
pair splits, and prints the actions, final hands, and outcome.

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
`max_split_hands` (full multi-round re-split is still simplified, with an honest
warning).
