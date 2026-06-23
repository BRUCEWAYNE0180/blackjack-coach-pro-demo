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

## v1.7.0 feature summary

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

v1.7.0 adds a complete strategy-matrix audit and a per-hand decision audit
(`app/strategy_matrix.py`, `app/decision_audit.py`, and the `matrix` / `audit`
commands), so the coach can prove full decision coverage across hard totals,
soft totals, pairs, dealer upcards, and profiles, and explain whether each play
is a direct chart action or a legal fallback. No changes to basic strategy,
Hi-Lo math, deviations, the simulator, or session history. It is a professional
coach for local practice, demo money, video games, recreational tournaments,
and training.

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
