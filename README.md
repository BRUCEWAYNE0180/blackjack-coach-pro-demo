# Blackjack Coach Pro Demo

An **educational / practice** tool for learning blackjack **basic strategy**.

> This project is a study aid, not a gambling product. It does **not** connect
> to casinos, does **not** place or automate real-money bets, does **not** use
> any camera/video at a real table, and makes **no** promise of winnings.
> See [`docs/PROJECT_RULES.md`](docs/PROJECT_RULES.md).

## What it does (v0.2)

- Recommends the basic-strategy action (`HIT`, `STAND`, `DOUBLE`, `SPLIT`,
  `SURRENDER`) for multi-deck **H17** and **S17** profiles.
- Gives a short **educational explanation** of *why* each action is suggested.
- Adds **warnings**, including the insurance note when the dealer shows an Ace
  (insurance recommendation is always **NO**).
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

v0.2 covers basic strategy, explanations, and a CLI. Card counting (Hi-Lo),
True Count, the Illustrious 18, a simulator, and a web app are **out of scope**
for now. See [`docs/BLACKJACK_COACH_KNOWLEDGE_BASE.md`](docs/BLACKJACK_COACH_KNOWLEDGE_BASE.md)
for the full v0.1-v0.6 roadmap.
