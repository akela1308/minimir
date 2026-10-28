# When learning pays: a preregistered artificial-life experiment on lifetime learning under unpredictable rule change

**mini-world, protocol B1-100k-v1. Report version 1.0.1, 28 October 2026 (English version of REPORT_B.md of 7 October 2026 with the amendments of 13 and 28 October; restructured as a report with abstract and methods, so section numbers differ from the Russian original).**

Maksim Ilin, independent researcher, Zagreb, Croatia. https://www.ilinmaks.com

- Results page: https://minimir.ilinmaks.com/results-b.html
- Code, data and the frozen preregistration: https://github.com/akela1308/minimir
- DOI: https://doi.org/10.5281/zenodo.23729180 (release v1.0.1-protocol-b, Zenodo; the archived original v1.0-protocol-b is 10.5281/zenodo.23713553; all versions: https://doi.org/10.5281/zenodo.23713552)

**Corrections of 28 October 2026.** Several statements in this report were stronger than the data; the list of corrections, with the numbers, is in `ERRATUM_2026-10-28.md`. The verdicts and the data do not change. Old wording below is kept, with dated notes next to it; plain factual slips are corrected in place.

## Abstract

We ask whether natural selection switches on lifetime learning only when the environment changes its rules unpredictably and faster than generations turn over, a prediction of the neural-network model of Kozielska and Weissing (2024). In a small artificial-life world, food comes in two colours; at random moments one colour becomes poison and the other food. A single plastic synapse ("taste") can learn the current rule within a life, and the learning rate is itself a heritable gene. Six conditions (stationary, slow, one reversal per lifetime, several reversals per lifetime, plus two ablations with learning switched off) ran on 40 seeds, one ancestor per seed shared by all six conditions, 100,000 ticks each, 240 runs in total, accumulated automatically between 10 and 29 September 2026 under a preregistration frozen before the first run. The declared failure boundary fired: in the treatment condition 32 of 40 populations went extinct at the first reversal (80 percent against a declared limit of 50 percent), so the main comparison is void by our own rules. The ablation held, as the design made nearly certain: without lifetime learning all 40 worlds died, with it 8 survived, eight discordant pairs in one direction, exact McNemar p = 0.0078. In the eight survivors the learning rate went to the ceiling of its range (median about 3.5 against a cap of 4.0) within a few hundred ticks of the first reversal and held there; the ratio to the stationary world, 14.5 at tick 100,000, depends on the cap and on when it is read, so it is not an effect size (see corrections of 28 October). The inherited taste stayed near its starting value in every condition while the learned taste reversed sign, a direct separation of what heredity stores from what a life stores. A second preregistered criterion failed for a methodological reason we name: the neutral-drift threshold was defined so that it grows with run length. Learning did not disappear in the stationary world (H-B2 not confirmed), which narrows an earlier pilot result of ours to expensive plasticity rules only. Protocol B1 is closed; the changes for protocol B2 are listed.

**Keywords:** artificial life, evolution of learning, lifetime plasticity, preregistration, agent-based simulation, environmental change, open science.

## 1. What was declared in advance

The design, the readings and the failure boundaries were frozen in the preregistration (PREREGISTRATION_B.md, version 1.1 of 9 September 2026) before the first run. Nothing below was decided after looking at the data. Where we got something wrong, it is marked as ours and carried into the next protocol rather than corrected here.

**The question.** Does selection switch on lifetime learning only when the world changes its rules unpredictably and faster than generations turn over? This is the prediction of Kozielska and Weissing (2024): learning evolves when the environment changes often and strongly, life is long enough for learning to pay off, and feedback is informative; in a stationary environment innate behaviour wins and learning is selected away.

**The world.** A torus of 128 by 128 cells with patchy food capacity, regrowth and seasons. Agents have 25 sensors and 12 outputs (8 actions, 2 memory values, 2 mark values), driven by a small feed-forward network (25 to 12 to 12) whose weights are the genome, mutated at division. Energy is capped at 100 units; death is irreversible. Lifetime changes are not inherited: a child receives the mutated genome of its parent, never the trained weights.

**Two colours of food.** Cells are coloured in two colours in small patches. At any moment one colour is nutritious and the other is poison; a poisonous bite costs half of what a nutritious bite would give (toxic_factor = -0.5). The rule reverses at moments drawn by a separate random generator seeded from the seed alone, with intervals uniform on [0.5T, 1.5T] and the first reversal no earlier than tick 5,000. Because the moments are unpredictable, no inherited value of the preference can stay correct for long: the right colour can only be learned within a life.

**What learns.** A single plastic synapse we call taste adds taste × colour to the logit of the eat action when there is food underfoot. Taste is inherited like any other weight and changes during life by a three-factor rule: Δtaste = lr × mod × pre × post, where pre is the colour of the food underfoot, post is tanh of the eat logit, and mod is the energy change of the tick, clipped to [−1, 1] with a dead zone of 0.5. The learning rate lr is itself a gene: inherited, mutated multiplicatively by exp(N(0, 0.3)), bounded to [0, 4], starting at 0.1 for every agent in every condition. Why one synapse and not a general Hebbian rule: in pilots, a general modulated rule across the whole output layer either destroyed the policy within a hundred ticks or relearned too slowly to survive a reversal. Minimal plasticity makes the question about when learning pays, not about whether a particular rule can hold a whole behaviour together. This limit was declared in advance.

**The ancestor.** The same random search for a viable foraging genome as in protocol A, blinded to colour, with an innate taste of +3 (eats colour +1, avoids −1), one ancestor per seed shared by all six conditions.

**Six conditions,** all on the same 40 seeds, 100,000 ticks each:

| condition | mean interval between reversals T | learning applied | role |
| --- | --- | --- | --- |
| never | never | yes | stationary control |
| slow | 5,000 ticks (many generations) | yes | slow change |
| life | 600 ticks (about one lifetime) | yes | treatment |
| fast | 150 ticks (several times per life) | yes | too frequent |
| life_frozen | 600 | no (gene present and drifting, rule not applied) | ablation of learning |
| never_frozen | never | no | neutral drift of the rate gene |

Median lifespan is 550 to 850 ticks in the switching conditions and about 830 in the stationary world, so "life" really is one reversal per lifetime.

**Hypotheses and criteria, registered before the runs.**

- H-B1 (main): the evolved learning rate in life is higher than in never, and the learning is useful. Three conditions had to hold: (1) paired Wilcoxon over seeds on log10 lr, p < 0.01, positive difference of medians; (2) the difference of median log10 lr exceeds two sigma of the between-seed spread of log10 lr in never_frozen, where the gene does nothing; (3) the ablation shows a survival benefit (criterion of H-B4).
- H-B2: in a stationary world learning is selected away, lr in never below never_frozen (paired Wilcoxon, p < 0.01).
- H-B3: reversal several times per lifetime is worse than once per lifetime (higher extinction in fast than in life).
- H-B4 (ablation): a world with changing rules is not survivable without lifetime learning. Exact McNemar test on the seeds where life and life_frozen disagree; benefit declared at p < 0.05 with more pairs in the predicted direction.

**Failure boundaries.** Among others: if more than half of the treatment populations go extinct, the comparison is void and the protocol is replaced by a new version, not tuned (section 7.3 of the preregistration). Readings were declared at 10, 20 and 40 seeds; everything in between is journal, not a claim.

**Accumulation.** 240 runs (40 seeds by 6 conditions by 100,000 ticks) were written automatically by a nightly GitHub Actions job between 10 and 29 September 2026, two seeds per day. No run failed. Raw data: runs/daily/protocol_b.jsonl in the repository.

## 2. Survival, and the number nobody was looking at

The declared failure boundary fired.

| condition | rule changes | learning | extinct | median tick of death | reversals before death |
| --- | --- | --- | --- | --- | --- |
| never | never | yes | 0 / 40 | none | none |
| never_frozen | never | no | 0 / 40 | none | none |
| slow | every ~5,000 ticks | yes | 30 / 40 | 10,741 | 1 |
| life | every ~600 ticks | yes | 32 / 40 | 5,986 | 1 |
| fast | every ~150 ticks | yes | 34 / 40 | 5,833 | 5 |
| life_frozen | every ~600 ticks | no | 40 / 40 | 5,983 | 1 |

Forty seeds per condition, 100,000 ticks per run. Extinct means the population reached zero before the end of the run.

The interesting column is the last one. The median number of rule reversals a population lives through before dying is one, in life, in slow and in life_frozen alike. Worlds do not grind down under accumulated switching; they die at the first switch. In slow the first reversal lands around tick 9,615 and death arrives around 10,741, some eleven hundred ticks later. In life the first reversal is around 5,637 and death around 5,986, some three hundred fifty ticks later. In fast the count of reversals is formally higher only because they come every 150 ticks; in time, death arrives at the same place.

So the answer we got belongs to a question we had not asked: in this world a single reversal is lethal, not the frequency of reversals. The same fact makes H-B3 untestable on these data rather than refuted, because whatever gradient of frequency exists is hidden under the first switch. The paired test of life against fast gave three discordant pairs against one, p = 0.625.

> **Note of 28 October 2026 (`ERRATUM_2026-10-28.md`, items 1.10, 1.6).** "Around 5,637" is the median first reversal over the 32 extinct life worlds; over all 40 life worlds the median is 5,553.5. The three switching conditions are also not independent: until the first switch slow, life and fast follow bit-identical trajectories, and their switch schedules are one random quantile stretched to different T. The same seeds survive (life and slow share 6 survivors against 2 expected), so H-B3 was untestable by design, not only because of the bottleneck.

### 2.1 The arithmetic of dying

A calculation that belonged before the runs, not after. At toxic_factor = -0.5 a poisonous bite removes roughly five units of energy. The energy a creature can hold is capped at one hundred. One bite shifts taste by about 0.1 at the starting rate with a saturated modulator. Moving from an inherited taste of +3 through zero to a stable −3 therefore takes on the order of sixty poisonings, which is about three hundred units of energy out of a budget of one hundred.

A creature starting at the default learning rate cannot physically relearn. It dies of poison before it changes the sign of its own preference. Survival is available only to populations that already carry faster learners in the tail of their variation, plus the luck of standing on a food patch when the rule turns.

> **Note of 28 October 2026 (`ERRATUM_2026-10-28.md`, item 1.9).** The calculation above starts the relearning path at +3. After the stationary warm-up, learning pulls the phenotype to 5.3 to 5.5, and relearning starts from there. The order of magnitude does not change.

## 3. The ablation: H-B4 held, a property of the design

> **Note of 28 October 2026 (`ERRATUM_2026-10-28.md`, item 1.4).** This heading read "H-B4 confirmed without reservations" until 28 October. With the taste frozen at +3, every bite of the familiar colour after a reversal costs about 5 energy units, and no heritable change can arrive within the roughly 350 ticks to extinction; section 9 of the preregistration already reports this outcome from the pilot. The McNemar test reduces to "do at least six learning worlds survive", and p = 0.0078 is the smallest value attainable with eight pairs. "Without learning this world cannot be survived" is true, but it is a property of the world we built. The sentence below about the ablation being "the only thing that licenses reading the rise of the learning rate as an adaptation rather than as a passenger of selection" is withdrawn: lineage tracing shows exactly the passenger scenario (see the note in section 4).

The same world, the same seeds, the same ancestor, with lifetime learning applied and with lifetime learning switched off.

- Discordant pairs: eight, all in one direction.
- life survived and life_frozen died: eight cases. The reverse: zero.
- Exact McNemar test: p = 0.0078.
- Extinction: 32 of 40 against 40 of 40.

Not one world out of forty survived without learning. Eight survived with it. This is the only one of the four hypotheses that passed its criterion outright, and it is also the only thing that licenses reading the rise of the learning rate as an adaptation rather than as a passenger of selection. The ablation was added to the main criterion by amendment v1.1, hours before the first run, and it turned out to be the part that worked.

A note on the p values (added 13 October 2026). Both p = 0.0078 in this report are the floor of their tests, not merely a small value: an exact McNemar test on eight discordant pairs and a paired Wilcoxon on eight pairs, under complete unanimity, give exactly 2 / 2^8 = 0.0078, and nothing smaller exists at n = 8. Criterion 1 of H-B1 with its p < 0.01 threshold could therefore pass only by unanimity of all eight pairs and had no power to spare. The verdicts do not change. For protocol B2 the consequence is direct: with 8 to 12 expected pairs, a p < 0.01 threshold for a paired Wilcoxon cannot be declared; a criterion on proportions (McNemar on extinctions, as in H-B4) or a 0.05 threshold with a pre-declared minimum number of pairs is needed.

## 4. What distinguished the eight survivors

The seeds that lived through the first reversal in life: 1, 2, 3, 10, 18, 28, 35, 39.

| measure at tick 4,000, the last curve point before the first reversal (1,300 to 1,900 ticks earlier) | survivors (n = 8) | died (n = 32) |
| --- | --- | --- |
| population size | 180 (142…229) | 183 (122…254) |
| learning rate, median gene | 0.120 (0.093…0.215) | 0.103 (0.050…0.181) |
| minimum population afterwards | 14 (4…39) | 2 (0…8) |

Medians with interquartile ranges. One-sided Mann-Whitney on the learning rate: p = 0.023.

> **Note of 28 October 2026 (`ERRATUM_2026-10-28.md`, items 1.2, 1.1, 1.5).** The table header read "measure at the first reversal" until 28 October; the first two rows are samples at tick 4,000 (first switches in life fall on ticks 5,317 to 5,882), and at the switch itself the populations were 350 to 893. The conclusion that size does not predict survival is unchanged. Seeds 1 and 2 in the list of survivors are the pilot seeds that section 9 of the preregistration promised not to count; without them 6 of 38 survive, McNemar p = 0.031, and criterion 1 (Wilcoxon p < 0.01) is unreachable with six pairs. Lineage tracing shows that every surviving world descends from one to four individuals alive at the switch (20 founders over 8 worlds), all at or above the 92nd percentile of their population in learning rate. "Selection removes everything except the fast learners within roughly one generation" below means one truncation event, after which the population regrows from near-clones.

Population size before the catastrophe is the same in both groups, so this is not a story about who had more creatures. What differs is the learning rate: a median of 0.120 against 0.103. The difference is small and the ranges overlap, but it exists and it points the predicted way. Selection acted on standing variation. The third row shows how narrow the bottleneck was. Survivors fell to fourteen individuals in the median, in one case to four. The ones that died fell to two. The distance between recovery and extinction is measured in single creatures.

### 4.1 The learning rate after the bottleneck

Median learning-rate gene over living agents, all eight surviving life worlds:

| seed | tick 4,000 | tick 6,000 | tick 10,000 | tick 20,000 | tick 50,000 | tick 100,000 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.09 | 1.93 | 3.26 | 3.02 | 3.47 | 3.40 |
| 2 | 0.10 | 2.46 | 3.39 | 3.28 | 3.65 | 3.07 |
| 3 | 0.12 | 1.10 | 3.23 | 3.57 | 3.42 | 3.53 |
| 10 | 0.17 | 1.31 | 3.88 | 3.38 | 3.18 | 3.55 |
| 18 | 0.11 | 1.27 | 3.26 | 3.44 | 3.43 | 3.34 |
| 28 | 0.21 | 1.47 | 3.49 | 2.83 | 3.31 | 3.58 |
| 35 | 0.12 | 2.38 | 3.53 | 3.70 | 3.38 | 3.56 |
| 39 | 0.15 | 1.79 | 3.28 | 3.44 | 3.30 | 3.45 |

The pattern is identical in all eight worlds. Before the reversal the rate sits near the starting 0.1. Within a few hundred ticks after the reversal it goes up by an order of magnitude, reaches 3.2 to 3.9 by tick ten thousand, and then holds between 2.8 and 3.7 for the remaining ninety thousand, near the top of the permitted range of 4.0. It is not drift and not a slow climb: selection removes everything except the fast learners within roughly one generation, and the population regrows out of them.

Final medians by condition, surviving worlds only:

| condition | learning rate, median | quartiles | food accuracy |
| --- | --- | --- | --- |
| never_frozen | 0.185 | 0.028…0.428 | 1.00 |
| never | 0.296 | 0.104…0.575 | 1.00 |
| slow | 2.832 | 2.673…3.002 | 0.98 |
| life | 3.491 | 3.381…3.555 | 0.93 |
| fast | 3.697 | 3.576…3.734 | 0.79 |

Ratio of medians, life against never: ×14.47, paired Wilcoxon p = 0.0078 on eight pairs. Food accuracy falls with switching frequency exactly as it should: one in the stationary world, 0.93 at one reversal per lifetime, 0.79 at several. The creatures in fast do not manage to relearn in time even though their learning rate is the highest of all.

> **Note of 28 October 2026 (`ERRATUM_2026-10-28.md`, items 1.3, 1.7).** The "quartiles" column in both tables holds quartiles across seeds of per-run medians, not within-population quartiles; within a population the 75th percentile of the learning rate is exactly 4.000 in all eight surviving life worlds, which is the cap of the gene. The fast quartiles hide seed 10, which survived 632 reversals without learning (rate 0.0004, phenotype equal to genome, eat accuracy 0.70). "Their learning rate is the highest of all" is wrong for fast; under fast switching a fixed innate taste is viable. There are no frozen controls for slow and fast.

## 5. The genome does not move, the phenotype does

Medians over living agents at the end of the run:

| condition | inherited taste (genome) | taste at end of life (phenotype) |
| --- | --- | --- |
| never | +3.04 | +5.58 |
| never_frozen | +3.04 | +3.04 |
| slow | +2.97 | +5.92 |
| life | +2.91 | −4.92 |
| fast | +3.21 | +4.50 |

The inherited taste started at +3.0 and stayed near +3.0 in every condition, including the ones where the rule changes. Evolution did not touch it, and could not: the correct sign changes unpredictably, so no inherited value is worth having. The phenotype diverged. In never_frozen, where learning is switched off, phenotype equals genome exactly, which incidentally confirms that the barrier against inheriting lifetime change is intact. In never, learning pushed taste up to +5.58, reinforcing an already correct innate preference. In life the phenotype went negative: at the moment of measurement the rule stood with colour −1 edible, and the population had learned that while keeping an innate plus.

The genome cannot record the rule. Lifetime learning records it. This is the separation the protocol was built to show, and it is the one place where the result is a picture rather than a p value.

> **Note of 28 October 2026 (`ERRATUM_2026-10-28.md`, item 1.8).** −4.92 is the median over eight worlds. In two of the eight the taste at the last tick is positive (+5.18 and +5.87) because the rule stood the other way; the mean is −2.04. The right statement: the phenotype tracks the current rule while the genome stays put.

## 6. Learning is visible inside a single life

Two curves measured within lifetimes, not between generations, averaged over the eight surviving life worlds.

Food accuracy by age of the agent:

| age of agent, ticks | 0-50 | 50-100 | 100-200 | 200-400 | 400-800 | 800-1600 | 1600+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| share of edible bites | 0.845 | 0.940 | 0.950 | 0.937 | 0.931 | 0.939 | 0.943 |

The young eat noticeably worse, reach a plateau within the first hundred ticks of life and do not improve after that. This is a learning curve inside an individual.

Food accuracy by time since a reversal, separately for agents born before the reversal (who must relearn) and after it (who learn from scratch):

| ticks since the reversal | 0-99 | 100-199 | 200-299 | 300-399 | 400+ |
| --- | --- | --- | --- | --- | --- |
| born before (relearning) | 0.66 | 0.98 | 0.99 | 0.99 | 0.99 |
| born after (learning from scratch) | 0.87 | 0.94 | 0.97 | 0.97 | 0.98 |

Those born before a reversal drop to 0.66 in the first hundred ticks and are back at 0.98 by the next hundred. Relearning takes something like a hundred and fifty ticks, a small fraction of a life. One caveat matters here: this curve is averaged over all reversals in a run, about a hundred and fifty of them, and by most of those the learning rate already stands at 3.4. It describes an evolved population, not a naive one. For a naive population at rate 0.1, relearning costs more than the creature is worth, which is precisely why the first reversal kills it.

## 7. In a stationary world, learning did not go away (H-B2 not confirmed)

We expected that where the world never changes, learning is useless and selection removes its cost, putting never below never_frozen. The opposite happened: 0.296 against 0.185, a ratio of 1.38 at p = 0.115, which is indistinguishable from drift. H-B2 is not confirmed.

This contradicts our own July pilot (C.1), where plasticity being on made the learning rate fall by half within fifteen thousand ticks. The explanation, we think, is the price of the rule. In July a general Hebbian rule ran across the whole output layer: it moved every weight continuously, degraded behaviour, and was therefore actively suppressed by selection. Here a single connection learns, with a dead zone on the modulator, and in a stationary world it merely confirms an innate preference, phenotype +5.58 against genome +3.04. Such learning costs almost nothing, so there is nothing for selection to push against.

The substantive conclusion is a narrowing of our earlier one: the fall of the learning rate in the July pilot was the price of one specific expensive plasticity rule, not a general property of stationary environments. Cheap learning survives idleness.

## 8. Our own measurement error: a threshold that grows with the length of the run

Criterion 2 of H-B1 required the gap between median log10 learning rates to exceed two sigma of the spread of that same gene in never_frozen, where it affects nothing. The intent was right: you need a reference showing what the gene does when it does nothing. The implementation was not.

The rate gene mutates multiplicatively. Without selection that is a random walk on a logarithmic scale, and the variance of a random walk grows with time. So our own threshold grew as the run went on (forty seeds of never_frozen):

| tick | median rate | sd(log10) | 2σ as threshold | as a ratio |
| --- | --- | --- | --- | --- |
| 2,000 | 0.101 | 0.066 | 0.131 | 1x |
| 10,000 | 0.103 | 0.293 | 0.587 | 4x |
| 20,000 | 0.128 | 0.503 | 1.006 | 10x |
| 40,000 | 0.129 | 0.681 | 1.363 | 23x |
| 60,000 | 0.090 | 0.822 | 1.644 | 44x |
| 80,000 | 0.122 | 0.861 | 1.721 | 53x |
| 100,000 | 0.185 | 0.893 | 1.786 | 61x |

The effect we measured is ×14.5, which is 1.16 in log10. The threshold at tick one hundred thousand is 1.786, a sixtyfold range. The threshold overtook the effect somewhere around twenty to thirty thousand ticks. Had we declared a run length of 20,000, this very same effect would have passed.

That is a design error in the criterion and it should be named as one: we chose a bar that rises the longer the experiment runs. It does not measure the size of an effect, it measures the duration of a run. We will not move it after the fact, because a criterion invented after looking at the data is not a criterion. In the next version it compares against drift at the same tick, or uses the distribution of paired differences, or bounds the gene so the neutral walk cannot spread. That gets decided before the runs.

## 9. Verdicts

| hypothesis | statement | result |
| --- | --- | --- |
| H-B1 (main) | learning rate is higher in a changing world, and the learning is useful | not confirmed: criteria 1 and 3 passed, criterion 2 did not; the verdict is overridden by the failure boundary of section 7.3 |
| H-B2 | in a stationary world learning is selected away | not confirmed, and the direction is opposite to the expected one |
| H-B3 | reversal several times per life is worse than once per life | not testable on these data: the bottleneck of the first reversal hides the frequency effect |
| H-B4 (ablation) | a world with changing rules is not survivable without learning | confirmed; true by construction (see corrections) |

## 10. Limits

1. Selection on survival. The eight surviving life worlds that carry the learning rate, the accuracy and the curves are not a random sample of forty. They are a sample selected on survival, so comparing them with never, where all forty survived, compares survivors with non-survivors. The ratio of 14.5 characterises evolution in those worlds where evolution had time to happen, not the expected outcome in a world picked at random.
2. One synapse is plastic. Nothing here generalises to a general learning rule, and we do not claim it does.
3. One world. One grid, one metabolism, one brain size, one ancestor per seed. No transfer is claimed.
4. The browser version on the project's front page is a showcase, not a source of numbers; it differs from the nightly run in several parameters and two engine settings (general Hebbian plasticity and Lamarckian inheritance of learned weights), see ERRATUM section 2.
5. H-B3 remains untested, not refuted.
   > **Note of 28 October 2026 (`ERRATUM_2026-10-28.md`, item 1.6).** Untestable by design, not only because of the bottleneck: the three switching conditions share the pre-switch trajectory and the schedule quantile, and the same seeds survive in all three (4 shared survivors against 0.3 expected).
6. The ceiling of the rate gene (taste_lr_max = 4.0) censors the effect: medians of 3.49 in life and 3.70 in fast, with quartiles up to 3.73, sit at the top of the range, so the ×14.5 ratio is an underestimate, or rather undefined: the cap clips the numerator while the denominator drifts (correction of 28 October, `ERRATUM_2026-10-28.md` item 1.3), and any log-scale criterion compares a censored quantity.
7. How the numbers are computed. Every median and quartile of the learning rate is taken on the log10 scale and mapped back (10 ** median(log10 lr)). The life against never ratio is 10 ** median(log10 life − log10 never) over pairs, a median of ratios on the logarithmic scale rather than a ratio of linear medians; recomputed with linear medians the same data give ×14.95 instead of ×14.47, a different scale and not a discrepancy. Food accuracy is a mean over the surviving runs of a condition. Extinction fractions and ticks of death use all forty runs of a condition; everything else uses the survivors only, because an extinct world has no final state.

## 11. What protocol B2 changes

Protocol B1 is closed. Tuning its parameters and recomputing the same data would be fitting, so B2 needs a new preregistration, a new results file and criteria declared before any runs. In order of importance:

1. The world has to be survivable through the first reversal: either a poisonous bite costs two units instead of five (toxic_factor −0.2 to −0.25), or, closer to biology, the reversal is gradual over a few dozen ticks so there is a window in which both colours are weakly nutritious and the new sign can be learned before the old one becomes lethal.
2. The starting learning rate has to be non-zero in practice: either raised to around 0.5, where relearning fits the energy budget, or, more honestly, seeded as a distribution of rates so that standing variation is declared rather than accidental.
3. The drift criterion must be independent of run length: compare against drift at the same tick, use the distribution of paired differences, or bound the gene. A neutral marker gene with the same mutation kernel and no function, carried by every agent, gives an internal reference: the criterion then compares log(lr / marker) in the same world at the same tick.
4. The frequency gradient (H-B3) needs its own condition in a world that reliably survives.
5. The age and learning rate of the dead have to be recorded, not only of the living.
6. Either raise the ceiling of the rate gene or declare the share of agents at the ceiling as a separate metric.
7. Statistical thresholds must match the expected number of pairs (see section 3).

A pilot of these changes on three seeds (13 October 2026) is in the repository under runs/b2/pilot; it is a pilot, not a reading, and nothing in it counts toward B2.

## 12. In plain language

We built a world where food comes in two colours, and from time to time the colours swap roles: what was food becomes poison. The moments of the swap are random, so being born knowing the right colour is impossible. It can only be learned while alive. The question was simple: does selection switch on the ability to learn in a world that keeps changing its rules?

There were two pieces of news. The first is that the world turned out to be too cruel. Eighty percent of the populations died at the very first swap, and in the variant where learning was switched off, every single one died, forty out of forty. We did the arithmetic afterwards and saw why: to relearn at the starting speed, a creature needed to be poisoned about sixty times, and its energy covers about twenty poisonings. It died before it could work out that the rules had changed. That is our mistake in the construction of the world, and we had declared in advance that in this case the protocol gets replaced rather than tuned until the result looks nice.

The second piece of news is more interesting. The eight worlds that scraped through the catastrophe behaved exactly as the hypothesis predicted. They survived on the luck of the tail: each surviving world descends from one to four individuals that happened to sit in the top few percent of a neutral spread of the gene (see corrections, item 1.5). Within a few hundred ticks after the catastrophe the learning rate in the population grew about thirtyfold (to the ceiling of the gene's range) and stayed there until the end of the run. The inherited taste meanwhile did not change at all, and that is correct: you cannot write into heredity something that changes at random. The taste learned during life, on the other hand, flipped to the opposite sign. Heredity holds the design of the creature, and knowledge about what is edible today lives only within one life and is earned again by every generation.

And a third thing we had not expected. In the unchanging world, learning did not disappear, although by our own July sketch it should have. In July we tried expensive learning that damaged behaviour, and selection threw it out. Here learning is cheap, one single connection, and there is no reason to throw it out. So it is not that learning is always wasteful in a stable world, only learning that you have to pay dearly for.

One more thing needs saying, about our own measurement error. We declared in advance that the effect had to exceed the spread of random drift, which is the right idea, but we chose a poor way to compute it. The result was that the longer the experiment ran, the higher the bar we had set ourselves. By the end of the run it demanded a sixtyfold difference, and the effect was fourteenfold. Had we stopped the runs five times earlier, the same result would have passed. We will not change the rule after the fact, because a criterion invented after looking at the data is not a criterion, but in the next version it will be different, and we have written down how. (This paragraph is in the Russian original, section 11; it was missing from the English version until 28 October 2026.)

## Data and code availability

- Repository with the engine, the frozen preregistration, the raw results (runs/daily/protocol_b.jsonl, 240 lines, one per run), the analysis scripts and the tests: https://github.com/akela1308/minimir
- Results page with the same tables: https://minimir.ilinmaks.com/results-b.html
- Observation journal, rebuilt nightly by GitHub Actions: https://minimir.ilinmaks.com/journal.html
- Live browser version of the world (showcase, not a source of numbers): https://minimir.ilinmaks.com/
- Dependencies of the engine: numpy only; analysis uses scipy and matplotlib.

## How to cite

Ilin, M. (2026). When learning pays: a preregistered artificial-life experiment on lifetime learning under unpredictable rule change (mini-world, protocol B1-100k-v1). Report version 1.0.1. Zenodo. https://doi.org/10.5281/zenodo.23729180. Results page: https://minimir.ilinmaks.com/results-b.html

```
@techreport{ilin2026minimir_b,
  author      = {Ilin, Maksim},
  title       = {When learning pays: a preregistered artificial-life experiment on lifetime learning under unpredictable rule change (mini-world, protocol B1-100k-v1)},
  institution = {Independent},
  year        = {2026},
  month       = {10},
  version     = {1.0.1},
  doi         = {10.5281/zenodo.23729180},
  url         = {https://minimir.ilinmaks.com/results-b.html}
}
```

## Corrections

Added 28 October 2026. The full text with the numbers and the source of each number is in `ERRATUM_2026-10-28.md`; one line per item here. The verdicts under the registered criteria, the failure boundary and the data do not change.

1. Pilot seeds 1 and 2 are in the confirmatory data against section 9 of the preregistration; without them McNemar p = 0.031 and criterion 1 is unreachable (ERRATUM 1.1; note in section 4).
2. The table in section 4 was mislabelled: the samples are at tick 4,000, 1,300 to 1,900 ticks before the first reversal (ERRATUM 1.2; header corrected, note in section 4).
3. The number 14.5 and "thirtyfold" are not effect sizes: the numerator sits at the gene cap, the denominator drifts; the right statement is "went to the ceiling of its range" (ERRATUM 1.3; abstract corrected, notes in sections 4.1, 10.6, 12).
4. The ablation H-B4 is true by construction; "the cleanest result" and "the only thing that licenses reading the rise as adaptation" are withdrawn (ERRATUM 1.4; notes in sections 3, 9).
5. The eight surviving worlds descend from 1 to 4 individuals from the upper tail of a neutral spread of the gene: evolutionary rescue from standing variation; "they did not survive by chance" is withdrawn (ERRATUM 1.5; notes in sections 4, 12).
6. The conditions slow, life and fast are dependent by construction (shared pre-switch trajectory, one schedule quantile); H-B3 was untestable by design (ERRATUM 1.6; notes in sections 2, 10.5).
7. In fast, seed 10 survived without learning; the quartiles in section 4.1 are across-seed quartiles of per-run medians and hide this case (ERRATUM 1.7; note in section 4.1).
8. −4.92 is the median over eight worlds, two of which are positive; the right statement is "the phenotype tracks the current rule" (ERRATUM 1.8; note in section 5).
9. The arithmetic of dying in section 2.1 should start from 5.3 to 5.5, not +3; same order of magnitude (ERRATUM 1.9; note in section 2.1).
10. "The first switch around tick 5,637" is the median over the extinct worlds; over all forty it is 5,553.5 (ERRATUM 1.10; note in section 2).
11. There are forty ancestors, one per seed, shared by the six conditions; "from one shared ancestor" in the abstract was corrected in place (ERRATUM 1.11).
12. Cross-machine reproducibility is incomplete: for 6 of 40 seeds the trajectories diverge on another machine, and two slow worlds flip outcome (ERRATUM 1.12).
13. The browser showcase differs from the measured protocol not in four parameters but also in two engine settings; section 10.4 corrected in place (ERRATUM section 2).
14. Plain factual slips corrected in place: "12 actions" (now 12 outputs), "median lifespan 500 to 800" (now 550 to 850 in the switching conditions, about 830 in the stationary world), the missing fourth plain-language paragraph restored in section 12.

## References

Kozielska, M., Weissing, F. J. (2024). A neural network model for the evolution of learning in changing environments. PLoS Computational Biology, 20(1), e1011840. https://doi.org/10.1371/journal.pcbi.1011840

Ilin, M. (2026). Preregistration B: when learning pays (PREREGISTRATION_B.md, v1.1, 9 September 2026). https://github.com/akela1308/minimir/blob/main/PREREGISTRATION_B.md

Ilin, M. (2026). REPORT: «мини-мир», автономная ночная сессия (report on protocol A, interoception, and the July pilots; in Russian; REPORT.md). https://github.com/akela1308/minimir/blob/main/REPORT.md
