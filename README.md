# Blackjack Coach Pro Demo

[![CI](https://github.com/BRUCEWAYNE0180/blackjack-coach-pro-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/BRUCEWAYNE0180/blackjack-coach-pro-demo/actions/workflows/ci.yml)

An **educational / practice** tool for learning blackjack **basic strategy**,
Hi-Lo counting, and hand simulation — entirely offline, with a friendly CLI.

> This project is a study aid, not a gambling product. It does **not** connect
> to casinos, does **not** place or automate real-money bets, does **not** use
> any camera/video at a real table, and makes **no** promise of winnings.
> See [`docs/PROJECT_RULES.md`](docs/PROJECT_RULES.md).

**30-second tour:** install with `pip install -e ".[dev]"`, run the tests with
`python -m pytest`, then try `blackjack-coach --cards A,7 --dealer 9`. It tells
you the basic-strategy play and *why*. Everything is local and educational.

Docs: [Release notes](docs/RELEASE_NOTES_v1.0.0.md) ·
[Commands](docs/COMMANDS.md) · [Changelog](CHANGELOG.md) ·
[Project rules](docs/PROJECT_RULES.md) · [License](LICENSE)

## v1.0.0 feature summary

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
blackjack-coach --cards A,7 --dealer 9
blackjack-coach count --cards 2,5,K,A,9 --decks-remaining 5
blackjack-coach play --decks 6 --seed 42
blackjack-coach quiz --seed 42 --answer H
blackjack-coach quiz-session --questions 10 --seed 42 --answers H,S,D,H,R,S,H,D,P,S
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

**Out of scope for v0.6:** re-splitting (if a split hand could split again it is
played as a normal total, with a warning) and special split-Aces rules (Aces
are split but played normally, with a warning). There is no money, bankroll,
betting units, or payout modelling.

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

Omit `--answers` in either command to be prompted per question/batch. Sessions
are **not** saved (no files, no database, no login) and are **educational
practice only**.

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

v1.0.0 is the first **stable** release: an educational, local, well-tested
trainer with modern packaging and CI. It adds no new gameplay over v0.9 — it is
release polish (docs, changelog, license, metadata, quality).

Planned next (educational/local only): v1.1 terminal/visual polish, v1.2 saved
local session history, v1.3 advanced count deviations (educational only), and a
possible v2.0 web UI if decided later. See
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
