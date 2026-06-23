# Release Notes — v1.0.0

## What this project is

**Blackjack Coach Pro Demo** is an educational / practice tool for learning
blackjack **basic strategy** and the **Hi-Lo** counting concept, with a local,
fully simulated practice environment. It is a study aid — not a gambling
product — and runs entirely offline using only the Python standard library.

## What v1.0.0 includes

v1.0.0 is the first stable release. It consolidates and polishes everything
built across v0.1-v0.9 (no new gameplay is added in this release):

- **Basic strategy** for multi-deck **H17** and **S17** with full
  `HIT/STAND/DOUBLE/SPLIT/SURRENDER` decisions and legal-action fallbacks.
- **Educational explanations** for each recommendation; insurance is always
  declined.
- **Hi-Lo counting trainer** (running count and true count) for local practice.
- **Local virtual shoe and simulator**: deal hands, play a full hand against
  the dealer (H17/S17), and play **basic pair splits**.
- **Quiz mode** (strategy quiz and Hi-Lo count quiz), interactive or by flag.
- **Scored training sessions** with accuracy and weak-spot summaries.
- **Packaging and CLI**: the `blackjack-coach` command, modern `pyproject.toml`
  packaging, and CI on Python 3.9-3.12. 242 automated tests; ruff clean.

## Main commands

```bash
blackjack-coach --cards A,7 --dealer 9
blackjack-coach count --cards 2,5,K,A,9 --decks-remaining 5
blackjack-coach play --decks 6 --seed 42
blackjack-coach quiz --seed 42 --answer H
blackjack-coach quiz-session --questions 10 --seed 42 --answers H,S,D,H,R,S,H,D,P,S
```

See [`COMMANDS.md`](COMMANDS.md) for the full command reference.

## What it does NOT do

By design, this tool does not and will not:

- connect to a **real casino** or any online gambling platform;
- place, manage, or automate **real-money bets**, or model a bankroll;
- use a **camera/video** feed or **screen scraping** to read a real table;
- promise **winnings** or present any "guaranteed" system;
- include a **betting spread**, **Kelly** bet sizing, the **Illustrious 18**,
  or **insurance index** plays.

## Educational scope and responsible use

Card counting and the simulator exist purely for **local, simulated**
education. This software is not financial or gambling advice. Gambling carries
financial risk and can be addictive; please follow the laws and venue rules
that apply to you, and seek support from a local problem-gambling helpline if
gambling is causing harm.
