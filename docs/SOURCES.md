# Sources — Blackjack Coach Pro Demo

This document tracks the categories of source material that inform the
project, with an initial classification. It is a living document: concrete
references are added as they are reviewed and verified.

All sources are used for **educational** purposes. Nothing here endorses
real-money gambling or guarantees any outcome (see `PROJECT_RULES.md`).

## Classification Overview

| Category            | Role in project                                  | Used in |
|---------------------|--------------------------------------------------|---------|
| Basic strategy      | The core HIT/STAND/DOUBLE/SPLIT/SURRENDER charts | v0.1    |
| Math / EV           | Expected value, house edge, why charts are right | v0.2+   |
| Card counting       | Hi-Lo system, running/true count theory          | v0.3+   |
| Simulation          | Monte Carlo validation, drill engine             | v0.4+   |
| Visual / UI         | Presentation, quiz UX, web app                   | v0.5+   |
| Discarded           | Out-of-scope or against project rules            | n/a     |

---

## 1. Basic Strategy (v0.1)

Foundational charts for multi-deck H17 and S17 with DAS and late surrender.

- **Type:** Strategy charts and decision tables.
- **What we take:** The exact play for every (player hand, dealer upcard)
  combination, including pair-splitting and surrender exceptions.
- **Candidate references:** Authoritative basic-strategy chart providers and
  standard blackjack texts. (To be cited specifically as each chart cell is
  validated by tests.)
- **Status:** Encoded in `app/strategy_engine.py`; validated by tests.


## 2. Math / Expected Value (v0.2+)

Material explaining *why* each basic-strategy decision is correct.

- **Type:** Probability and expected-value analysis, house-edge derivations.
- **What we take:** EV-per-decision reasoning, dealer bust probabilities,
  effect of rule variations (H17 vs S17, DAS, surrender) on house edge.
- **Status:** Planned. Used to generate explanations alongside recommendations.

## 3. Card Counting (v0.3+)

Counting theory, treated strictly as an educational topic.

- **Type:** Hi-Lo tag values, running count, true-count conversion, betting
  and playing correlation, the Illustrious 18 / Fab 4 deviations.
- **What we take:** The Hi-Lo system and a small set of well-known index
  plays, practiced only against the built-in simulator.
- **Constraint:** Never applied to real tables or via camera/video capture.
- **Status:** Planned.

## 4. Simulation (v0.4+)

Material for building and validating a Monte Carlo / drill engine.

- **Type:** Shoe modelling, shuffle/penetration assumptions, variance and
  risk-of-ruin concepts, statistical validation techniques.
- **What we take:** Methods to validate strategy EV empirically and to drive
  realistic practice drills.
- **Status:** Planned.

## 5. Visual / UI (v0.5+)

Material for presentation and user experience.

- **Type:** Quiz/flashcard UX patterns, chart visualisation, web app design.
- **What we take:** Layouts for strategy charts, drill feedback, and progress
  tracking.
- **Status:** Planned.

## 6. Discarded Sources

Categories explicitly **out of scope** or in conflict with project rules:

- Real-money casino APIs, betting bots, or auto-play integrations.
- Live/online table camera or screen-scraping card readers.
- "Guaranteed win" systems, progressive betting schemes (e.g. Martingale)
  presented as winning strategies, and any get-rich claims.
- Hole-carding, marked-card, collusion, or device-assisted real-table
  advantage techniques.
- Any source promoting illegal activity or violation of venue terms.

These are recorded here so the boundary stays explicit and auditable.
