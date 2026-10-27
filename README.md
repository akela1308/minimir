# mini-world (minimir)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23713553.svg)](https://doi.org/10.5281/zenodo.23713553)

A small artificial-life world for preregistered experiments on the evolution of learning. Creatures on a 128 by 128 torus look for food, burn energy, reproduce and die; each one is driven by a tiny neural network that passes to its offspring with mutations. No rewards, no goals. Every experiment has a control condition on the same seed, the same map and the same genome shape, and every hypothesis, criterion and failure boundary is frozen in a preregistration before the first run.

**Live site:** [live experiment](https://minimir.ilinmaks.com/) · [results of protocol B](https://minimir.ilinmaks.com/results-b.html) · [observation journal](https://minimir.ilinmaks.com/journal.html) · [about](https://minimir.ilinmaks.com/about.html). GitHub Pages, nothing to install.

Russian version of this file: [README.ru.md](README.ru.md). Reports and preregistrations are in Russian unless marked otherwise; the results pages on the site are in English.

## What is closed

| experiment | protocol | verdict | where |
| --- | --- | --- | --- |
| 1. Interoception (`self` against `shuffled`) | A, two readings passed | not confirmed, the signal sits inside the noise | `REPORT.md` |
| 2. When learning pays | B1-100k-v1, closed 7 October 2026 | the declared failure boundary fired (32 of 40 treatment worlds died at the first rule reversal); the ablation H-B4 confirmed, exact McNemar p = 0.0078 | `REPORT_B.md` (RU), `REPORT_B_EN.md` (EN), [results page](https://minimir.ilinmaks.com/results-b.html) |

Protocol B in one table (40 seeds per condition, 100,000 ticks per run, 240 runs, accumulated automatically from 10 to 29 September 2026, no run failed):

| condition | rule changes | learning | extinct | median tick of death | reversals before death |
| --- | --- | --- | --- | --- | --- |
| never | never | yes | 0 / 40 | none | none |
| never_frozen | never | no | 0 / 40 | none | none |
| slow | every ~5,000 ticks | yes | 30 / 40 | 10,741 | 1 |
| life | every ~600 ticks | yes | 32 / 40 | 5,986 | 1 |
| fast | every ~150 ticks | yes | 34 / 40 | 5,833 | 5 |
| life_frozen | every ~600 ticks | no | 40 / 40 | 5,983 | 1 |

Without lifetime learning not one world out of forty survived a change of the food rule. With it, eight did, and in those eight the median learning rate rose 14.5-fold within a few hundred ticks of the first reversal and stayed there for the remaining 90,000 ticks, while the inherited preference did not move at all. The main hypothesis is still not confirmed, by our own preregistered rules: the world was too harsh, and one of our criteria was built so that it grows with run length. Both errors are named in the report and fixed in protocol B2, not retroactively.

Protocol B1 accumulates no further; the nightly job stops at seed 40. Tuning B1 and recomputing the same data would be fitting. B2 gets its own preregistration (draft: `PREREGISTRATION_B2_черновик.md`, pilot: `runs/b2/pilot/`).

## Three things that are easy to confuse

- **Live experiment**: the world runs in the reader's browser and dies with the tab. A showcase of the method, not a source of numbers.
- **Recorded run**: an exact replay of one saved run, finite and looped.
- **Observation journal**: what actually accumulates. Once a day GitHub Actions runs new seeds, appends raw numbers to the repository and rebuilds the page. Nobody's computer has to be on.

## The hypothesis being tested

Not "growing a mind in general", but one testable claim per protocol. Protocol A:

> If an agent has access to a signal about its own state and death is irreversible, evolution will produce behaviour that depends on the internal state, and that is cheaper to explain by "it is hungry" than by mechanics.

Protocol B, after Kozielska and Weissing (2024):

> Selection switches on lifetime learning only where the world changes its rules unpredictably and faster than generations turn over.

Exact wording of hypotheses and the main metric: `PREREGISTRATION.md` (A) and `PREREGISTRATION_B.md` (B). Prior work and our own mistakes: `PRIOR_WORK.md`. Design of the sign layer: `STAGE3_DESIGN.md`.

## Run it

```bash
pip install -r requirements.txt     # numpy for the engine; scipy, matplotlib, pytest for analysis and tests
python run.py smoke                 # 3,000 ticks, checks the world is alive
python run.py paired --ticks 200000 # interoception vs control, one seed
python run.py social --ticks 200000 # stage 1.5: a dilemma built from metabolism
python experiments.py compare --seeds 20 --ticks 200000   # four conditions, Wilcoxon
python analyze.py list
pytest
```

Speed: 380 to 600 ticks per second at working population sizes, so 200,000 ticks take 6 to 9 minutes on one core. Results are written incrementally to JSONL (one line per run), series are resumable, and a failed run does not stop the series.

## Where things are

| file | contents |
| --- | --- |
| `sim/config.py` | all parameters plus indices of actions and sensors |
| `sim/world.py` | torus 128 by 128, patchy capacity, regrowth, seasons, `energy_budget()` |
| `sim/brain.py` | genome = MLP 25 to 12 to 12, mutation at division, `hebbian_update()` |
| `sim/population.py` | agent slots, birth, irreversible death, `lifespans` |
| `sim/ancestry.py` | `find_viable_ancestor()`: ancestor selection with a cache in `runs/ancestors/` |
| `sim/engine.py` | one tick: sensors, choice, actions, metabolism, selection |
| `sim/protocol_b.py` | world B: two colours of food, rule reversals, the plastic taste synapse |
| `sim/metrics.py` | metrics that test the hypotheses |
| `runs/daily_b.py`, `runs/journal_b.py` | the nightly protocol B run and the journal rebuild |
| `runs/daily/protocol_b.jsonl` | raw results of protocol B, 240 lines |
| `.github/workflows/daily.yml` | schedule: run, journal, commit, publish |
| `PREREGISTRATION_B.md` | the frozen protocol B |
| `REPORT_B.md`, `REPORT_B_EN.md` | the report on protocol B, Russian and English |
| `PUBLICATIONS/` | texts about the results for LinkedIn, Medium, dev.to and Reddit |

## Honest list of simplifications

One grid, one metabolism, one brain size, one ancestor per seed. In protocol B a single synapse is plastic, so nothing generalises to a general learning rule. The browser version differs from the nightly run in four parameters listed on the front page. The full list is in `README.ru.md` and in the reports.

## How to cite

Ilin, M. (2026). mini-world (minimir): preregistered artificial-life experiments on the evolution of learning. Protocol B1-100k-v1: when learning pays. Version 1.0-protocol-b. Zenodo. https://doi.org/10.5281/zenodo.23713553

The DOI above points to release v1.0-protocol-b. The DOI for all versions is 10.5281/zenodo.23713552. Results page: https://minimir.ilinmaks.com/results-b.html

A `CITATION.cff` file is in the repository; GitHub shows it under "Cite this repository".

## Author

Maksim Ilin, AI engineer and AI consultant, Zagreb. https://www.ilinmaks.com · [about](https://www.ilinmaks.com/about/en)

## License

Code: MIT. Text of the reports, the preregistrations and the data in `runs/`: CC BY 4.0. See `LICENSE`.
