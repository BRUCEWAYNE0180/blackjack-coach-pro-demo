# Project Rules — Blackjack Coach Pro Demo

## 1. Purpose

Blackjack Coach Pro Demo is an **educational and practice** tool. Its goal is
to help a user learn and drill blackjack **basic strategy** (and, in later
versions, the math behind it) in a safe, offline, simulated environment.

It is a study aid, not a gambling product.

## 2. Hard Constraints (Non-Negotiable)

These constraints define what the project **must never do**:

1. **No casino connectivity.** The software must not connect to, integrate
   with, or communicate with any real casino, online gambling platform, or
   real-money gaming API.
2. **No real-money betting or automation.** It must not place, manage, or
   automate real-money wagers of any kind.
3. **No casino camera/video capture.** It must not use a camera, screen
   capture, or video feed to read cards from a real (live or online) table.
4. **No promise of winnings.** It must not claim, imply, or guarantee profit.
   Blackjack always carries a house edge; good strategy reduces losses, it
   does not guarantee wins.
5. **No facilitation of cheating.** It must not support marked cards, hole-card
   reading, collusion, device-assisted advantage play at real tables, or any
   activity that is illegal or violates casino terms.


## 3. What the Project May Do

- Teach and quiz blackjack basic strategy for defined rule profiles.
- Simulate hands locally with a virtual/random deck for practice.
- Explain the mathematical reasoning (expected value, house edge) in later
  versions, for educational purposes only.
- Demonstrate card-counting concepts (e.g., Hi-Lo) as a **learning topic** in
  later versions, clearly framed as theory and practiced only against the
  built-in simulator.

## 4. Scope of v0.1

- Basic-strategy recommendations for multi-deck shoes, both **H17** (dealer
  hits soft 17) and **S17** (dealer stands on soft 17).
- Actions supported: `HIT`, `STAND`, `DOUBLE`, `SPLIT`, `SURRENDER`.
- **Insurance recommendation is always NO.**
- Fallback behaviour:
  - If `DOUBLE` is indicated but not allowed (e.g. more than two cards),
    fall back to `HIT` (hard hands) or `STAND` (soft "double-else-stand").
  - If `SURRENDER` is indicated but not allowed, fall back to the underlying
    `HIT` / `STAND` / `SPLIT` action.
- **Not** included yet: Hi-Lo counting, True Count, the Illustrious 18,
  a simulator, and a web app. See the knowledge base for the roadmap.

## 5. Rule Profiles

Profiles are defined in `app/rules.py`. v0.1 ships two:

| Key                        | Decks | Soft 17 | DAS | Late Surrender |
|----------------------------|-------|---------|-----|----------------|
| `MULTI_DECK_H17_DAS_LS`    | 6     | Hits    | Yes | Yes            |
| `MULTI_DECK_S17_DAS_LS`    | 6     | Stands  | Yes | Yes            |

## 6. Engineering Conventions

- Language: Python (standard library only for v0.1; `pytest` for tests).
- Code lives in `app/`, tests in `tests/`, documentation in `docs/`.
- Public behaviour is covered by tests; strategy tables are treated as the
  source of truth and validated against well-known basic-strategy charts.
- Changes land via pull request; no direct commits to `main`.

## 7. Professional Quality Gates

As of v0.9 the project enforces these gates on every change:

- **Tests must pass.** Every pull request must pass `python -m pytest` (run
  locally and in CI on Python 3.9-3.12).
- **Lint must pass.** Every pull request must pass `ruff check app tests`.
- **New features require tests.** Any new feature or bug fix must add or update
  tests that cover the new behaviour.
- **Scope is preserved.** Every new function must keep the educational /
  simulated scope: no real casino connectivity, no real-money betting or
  bankroll, no camera/video, no screen scraping, and no promise of winnings.
- **No secrets in the repository.** Never commit secrets, `.env` files, API
  tokens, credentials, private PDFs, or sensitive screenshots. CI must not
  depend on any private secret to run the tests or lint.
- **Changes land via pull request.** No direct commits to `main`; CI must be
  green before merge.

## 8. Responsible-Use Notice

This tool is for learning and entertainment. Gambling involves financial risk
and can be addictive. Users are responsible for complying with all applicable
laws and the rules of any venue they visit. If gambling is causing harm, seek
support from a local problem-gambling helpline.
