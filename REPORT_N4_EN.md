# How much learning does it take to survive a change: evolutionary rescue by standing variation in learning rate, and a milder change that is harder to survive

**A preregistered artificial-life experiment (mini-world, protocol N4-v1)**

*Maksim Ilin, independent researcher, Zagreb. 21 November 2026. Release v1.1.0-protocol-n4, DOI
[10.5281/zenodo.24544016](https://doi.org/10.5281/zenodo.24544016).*

*The preregistration `PREREGISTRATION_N4.md` was frozen by commit `944e88d` on
20 November 2026, before the first confirmatory run. The run and the single
reading were executed on GitHub's machines in one job; the result is commit
`9f1706e`. Russian original of this report: `REPORT_N4.md`. Code, pilots and the
write-up were produced together with Claude models; the question, the design
decisions and the decision to freeze were the author's.*

## Abstract

A population of simple learning agents faces one abrupt reversal of which of two
food colours is nutritious and which is poisonous. Each of 150 worlds was run
once up to the tick before the reversal and then copied 26 times, each copy
receiving a single intervention on the learning rate of its individuals, on the
spread of that rate, or on the strength of the poison. The outcome is survival
of the population 12,000 ticks later. Four criteria and one validity check were
frozen in advance, after each had been tested on synthetic data with and without
an effect. Two hypotheses were confirmed: a spread of learning rates rescues
populations whose median individual learns too slowly (0 of 150 worlds survive
with no spread, 134 of 150 with the widest), and a milder poison saves fewer
worlds, the opposite of what classical rescue theory predicts (0.445 against
0.582 on middle rates). A third, that each world has its own threshold, stayed
undetermined under the declared rule. With learning switched off no world
survived.

## 1. Summary of verdicts

| | claim | verdict | numbers |
|---|---|---|---|
| K1 | instrument check: survival rises with the learning rate | confirmed | difference 0.875, 95% CI [0.840, 0.908], threshold 0.20 |
| K2 | each world has its own threshold | undetermined | S(0.6) = 0.547 [0.467, 0.627]; S(1.5) = 0.853 [0.793, 0.907] |
| K3 | a spread of learning rates rescues | confirmed | difference 0.893, 95% CI [0.840, 0.940], threshold 0.10 |
| K4 | a milder change is worse | milder is worse, as predicted | difference −0.137, 95% CI [−0.170, −0.105], bound −0.05 |
| F | no rescue without learning | clean | 0 of 150 |

This is the first protocol of the project in which hypotheses declared in
advance were confirmed nontrivially: K3 and K4 could have failed, and the
attainability check showed that before the freeze.

## 2. What was declared

The world is world B of the project (two food colours, poison, one plastic
synapse called taste, a heritable learning rate) with a single reversal of the
food rule at tick 5,000. Each world runs to tick 4,999 with a learning rate of
0.1 in every individual, is then copied together with the state of its random
number generator, and each of 26 copies receives one intervention:

| part | intervention at the fork | levels |
|---|---|---|
| D, dose | every individual gets the same learning rate L, poison −0.5 | L = 0.1, 0.3, 0.45, 0.6, 0.8, 1.0, 1.5, 2.5, 4.0 |
| M, mild poison | the same at poison −0.2 | the same nine L |
| V, variation | each individual gets 0.1 · exp(sigma · z), poison −0.5 | sigma = 0.5, 1.0, 1.5, 2.0 |
| E, random tries | a dose from part D plus 5% random actions | L = 0.6, 1.5, 4.0 |
| F, frozen | as V at sigma 2.0, learning switched off after the fork | one |

The gene for the learning rate does not mutate after the fork. The outcome of a
copy is whether the population is alive at tick 17,000. The unit of analysis is
the seed and all comparisons are paired within a seed. The confirmatory sample
is 150 valid seeds starting at 403, read once, with no interim reading.
Confidence intervals are percentile bootstrap over seeds (10,000 resamples);
trends are within-seed permutation tests (20,000 permutations). Full text:
`PREREGISTRATION_N4.md`; criteria as code: `runs/n4_analyze.py`.

Before the freeze every criterion was run on two kinds of synthetic data
(`runs/n4/attainability_check.py`): pilot seeds resampled with replacement,
where the effect is plausible, and data in which the effect is absent by
construction. At 150 seeds the criteria passed in 100%, 99%, 100% and 93% of
plausible-effect datasets and in 0% of null datasets.

## 3. Data

3,900 rows: 150 seeds (403 to 552) by 26 conditions, all computed on commit
`944e88d` under the label `N4-v1`. No seed was excluded; populations at the fork
ranged from 245 to 586 individuals (median 429). Files:
`runs/n4/protocol_n4.jsonl`, `runs/n4/reading_n4.json`, `runs/n4/reading_n4.txt`.

Share of worlds rescued:

| learning rate L | 0.1 | 0.3 | 0.45 | 0.6 | 0.8 | 1.0 | 1.5 | 2.5 | 4.0 |
|---|---|---|---|---|---|---|---|---|---|
| D, poison −0.5 | 0.00 | 0.04 | 0.32 | 0.55 | 0.70 | 0.76 | 0.85 | 0.97 | 1.00 |
| M, poison −0.2 | 0.00 | 0.02 | 0.17 | 0.35 | 0.58 | 0.68 | 0.80 | 0.90 | 0.97 |

| spread sigma | 0 | 0.5 | 1.0 | 1.5 | 2.0 |
|---|---|---|---|---|---|
| V | 0.00 | 0.01 | 0.39 | 0.77 | 0.89 |

Part E (5% random actions): 0.61 at L 0.6, 0.91 at L 1.5, 1.00 at L 4.0. Part F
(learning off): 0 of 150.

## 4. The criteria one by one

**K1, positive control.** The trend over nine rates is significant (permutation
p below 0.001). The mean share rescued at L from 1.0 to 4.0 exceeds the mean at
L 0.1 and 0.3 by 0.875. The instrument sees the dose response, so the other
criteria can be read.

**K2, each world has its own threshold: undetermined.** The lower condition
holds with room to spare: at L 0.6 the share rescued is 0.547 with a lower bound
of 0.467 against the required 0.10. The upper condition fails: at L 1.5 the
share is 0.853 and the upper bound of the interval, 0.907, lies above the 0.90
ceiling. There is no refutation either, since that would need the lower bound at
L 1.5 above 0.90 and it is 0.793. The threshold is not moved after the fact. The
gap from the pilot is easy to see: in the pilot 0.77 of worlds were rescued at
L 1.5, in the confirmatory run 0.85, so the transition is somewhat narrower than
thirty worlds had suggested.

**K3, variety rescues: confirmed.** With the same rate of 0.1 in every
individual, none of the 150 worlds survived. With rates spread around that same
median, 0.39 survive at sigma 1.0, 0.77 at sigma 1.5 and 0.89 at sigma 2.0. The
trend is significant and the difference between the extreme levels is 0.893.

**K4, a milder change: milder is worse, as predicted.** On rates 0.45, 0.6, 0.8
and 1.0, mild poison rescues 0.445 of worlds on average and regular poison
0.582. The difference is −0.137 and the interval lies entirely below −0.05. The
effect is larger than in the pilot (−0.10). The direction of the prediction was
chosen from the pilot, which the preregistration states; the test ran on new
seeds.

**F, validity check: clean.** With learning switched off and the widest spread
no world survived. Rescue in part V goes through lifetime learning and not
through the heritable innate taste.

## 5. Declared descriptive analyses

No criteria attached; these do not count toward the hypotheses.

**Distribution of thresholds.** The lowest rate at which a world is rescued:

| threshold | 0.3 | 0.45 | 0.6 | 0.8 | 1.0 | 1.5 | 2.5 | 4.0 |
|---|---|---|---|---|---|---|---|---|
| worlds | 6 | 42 | 36 | 21 | 10 | 13 | 17 | 5 |

In 147 of 150 worlds the response to the rate is monotone: below its threshold
the world dies, above it the world lives. Thresholds differ between worlds by
more than a factor of ten. This is what K2 was about, but the declared rule did
not confirm it, and it is given here as description only.

**How parts D and V connect.** The number of individuals that received a rate
above their own world's threshold predicts rescue in part V:

| individuals above threshold | 0 | 1-2 | 3-9 | 10-29 | 30 or more |
|---|---|---|---|---|---|
| sigma 1.0: share rescued (worlds) | 0.00 (17) | 0.00 (15) | 0.17 (29) | 0.58 (64) | 0.85 (20) |
| sigma 1.5 | none | 0.00 (1) | 0.38 (16) | 0.54 (24) | 0.93 (104) |
| sigma 2.0 | none | none | none | 0.58 (19) | 0.97 (126) |

The five worlds with a threshold of 4.0 are not in this table, because the
number of individuals above 4.0 was not recorded. One or two fast individuals
are not enough for rescue; it takes on the order of ten or more.

**Who founded the surviving worlds in part V.** In surviving worlds the median
learning rate at the end of the run is 1.38 (sigma 1.0), 3.58 (sigma 1.5) and
4.0 (sigma 2.0), from a starting median of 0.1. One or two distinct values of
the rate remain at the end: the world is repopulated by the descendants of one
or two fast individuals.

**Random tries.** At L 0.6 the gain is +0.060 (14 worlds gained, 5 lost,
McNemar p = 0.064); at L 1.5 it is +0.053 (10 against 2, p = 0.039). The sign is
the same at both rates, unlike in the pilot. The effect is small and was not a
criterion.

**Time to extinction.** Median 410 ticks after the reversal, the latest 11,220
against a horizon of 12,000. 0.4% of extinctions came later than 6,000 ticks.

## 6. Checks

- Recomputing the reading from the raw rows on another machine gave the same
  numbers for every criterion.
- Seeds 403 and 500 were recomputed on another machine: outcome, final
  population and tick of extinction matched the GitHub run in all 26 conditions
  of each.
- Four rescued populations ended with fewer than 50 individuals (seeds 407, 441,
  453, 551; the smallest had 2). Counting them as extinct changes no verdict.
- All rows were computed on the frozen commit, and there was no second reading.

## 7. Why milder poison is worse here

The explanation was written into the preregistration before the run. In the
learning rule the strength of the lesson equals the energy lost on the bite,
saturating at two units and with a dead zone below half a unit, so poison both
harms and teaches. A full bite saturates the signal under either poison, but
full bites are rare: before the reversal, in 82 to 83% of food cells under an
individual the remaining resource is below 0.37 (measured on seeds 301, 305 and
312). On such cells mild poison teaches more weakly than regular poison, and
below a resource of 0.07 it does not teach at all because the loss falls inside
the dead zone. At a typical remainder of 0.1 the shift of taste from mild poison
is half as large. Classical rescue theory expects the opposite outcome because
in it the severity of a change is only harm.

This experiment cannot separate the two roles of poison. That needs a condition
in which the strength of the lesson is set independently of the harm.

## 8. What this does and does not show

Shown in this world: a population in which everyone learns equally slowly does
not survive one abrupt change, while a population with the same median rate and
a spread around it survives in most cases, carried by a few fast learners. This
is evolutionary rescue from standing variation, shown by intervention and not by
correlation: the only difference between copies of one world is the spread that
was set.

Shown in this world: a milder change is survived less often.

Neither confirmed nor refuted: that the transition from death to rescue is
stretched in the sense of the declared rule.

Limits. One world, one learning rule, one plastic synapse. In part D the rate
does not evolve. In part V the gene does not mutate. Survival to tick 17,000
says nothing about the long run, and four populations had not stabilised at the
horizon. The direction of K4 came from a pilot on thirty worlds.

## 9. Next

1. A condition that separates harm from lesson: the strength of the learning
   signal set apart from the energy lost. This is the direct test of the
   explanation in section 7.
2. K2 as a new version, with thresholds chosen from these 150 worlds and tested
   on new seeds.
3. A return to the question of protocol B1, when learning pays, in a world that
   can now live through the first reversal: a starting spread of rates with
   sigma near 1.5.

## References

- G. Bell, A. Gonzalez. Evolutionary rescue can prevent extinction following
  environmental change. *Ecology Letters*, 2009.
- L.-M. Chevin, R. Lande, G. M. Mace. Adaptation, plasticity, and extinction in a
  changing environment: towards a predictive theory. *PLoS Biology*, 2010.
- R. Gomulkiewicz, R. D. Holt. When does evolution by natural selection prevent
  extinction? *Evolution*, 1995.
- G. E. Hinton, S. J. Nowlan. How learning can guide evolution. *Complex
  Systems*, 1987.
- M. Ilin. When learning pays: a preregistered artificial-life experiment on
  lifetime learning under unpredictable rule change (mini-world, protocol
  B1-100k-v1). Zenodo, 2026. https://doi.org/10.5281/zenodo.23729180
- M. Kozielska, F. J. Weissing. A neural network model for the evolution of
  learning in changing environments. *PLoS Computational Biology*, 2024.

## Data and code

Repository: https://github.com/akela1308/minimir. Page of the experiment in five
languages: https://minimir.ilinmaks.com/n4.html. Code is MIT; report texts,
preregistrations and data in `runs/` are CC BY 4.0.
