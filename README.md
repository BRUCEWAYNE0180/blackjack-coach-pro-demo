# Blackjack Coach Pro Demo

An **educational / practice** tool for learning blackjack **basic strategy**.

> This project is a study aid, not a gambling product. It does **not** connect
> to casinos, does **not** place or automate real-money bets, does **not** use
> any camera/video at a real table, and makes **no** promise of winnings.
> See [`docs/PROJECT_RULES.md`](docs/PROJECT_RULES.md).

## What it does (v0.7)

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
- Ships a simple **command-line trainer**.

## Requirements

- Python 3.10+
- `pytest` (tests) and optionally `ruff` (lint) for development.

## Command-line usage

Run the coach from the repository root:

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
pytest            # run the test suite
ruff check app tests   # lint (if ruff is installed)
```

## Scope and roadmap

v0.7 adds an educational **quiz mode** (basic-strategy trainer + Hi-Lo
running-count trainer) on top of the v0.6 split simulator and earlier features.
**Out of scope** for now: betting spread, Kelly bet sizing, the Illustrious 18,
insurance index plays, and a web/UI layer. See
[`docs/BLACKJACK_COACH_KNOWLEDGE_BASE.md`](docs/BLACKJACK_COACH_KNOWLEDGE_BASE.md)
for the full roadmap.
