# Reddit: результаты протокола N4

Три варианта под три сабреддита. Один сабреддит в день. Под каждым английским
текстом стоит русский перевод, чтобы было видно, что именно публикуется.
Ссылка: https://minimir.ilinmaks.com/n4.html

---

## Вариант 1. r/alife

**Title:** Preregistered ALife experiment: a few fast learners rescue the population, and milder poison saves fewer worlds

Follow-up to our earlier post, where 32 of 40 populations died at the first
reversal of a food rule and the main comparison was void. This time we asked
what a population needs to live through one reversal, with the pass rules
committed before the run.

Setup: agents with a small neural network on a grid, two food colours, one
nutritious and one poisonous, one plastic synapse (taste) updated after each
bite, and a heritable learning rate. The rule flips once at tick 5,000. Each
world runs to the tick before the flip and is then deep-copied, RNG state
included, into 26 copies with one intervention each: the same learning rate for
everyone (nine levels), rates spread lognormally around a slow median (four
widths), the same doses under a milder poison, random actions, and a frozen
control. 150 worlds, outcome is survival 12,000 ticks later, everything paired
within a world.

Results:

- Dose response, as a positive control: 0% of worlds survive at rate 0.1, 55% at
  0.6, 100% at 4.0.
- Standing variation rescues: 0 of 150 with no spread, 134 of 150 at the widest
  spread, although the median individual still learns at 0.1. One or two
  individuals above the world's threshold were never enough; with 30 or more,
  rescue was 85% or higher. Survivors descend from one or two of them.
- Milder poison is worse: 44.5% against 58.2% on middle rates, 95% CI for the
  difference [−0.170, −0.105]. We predicted this direction (chosen from a
  30-world pilot, stated in the preregistration). In this world the update
  scales with the energy lost on the bite, so weak poison is a weak teaching
  signal.
- Undetermined: that each world has its own threshold. The rule needed the upper
  CI bound at rate 1.5 below 0.90 and it came out at 0.907. We did not move it.
- With learning off, 0 of 150.

Before freezing we ran every criterion on resampled pilot data and on data with
no effect by construction, because in earlier protocols we had four criteria
that could not pass under any outcome.

Limits: one world, one learning rule, the rate gene does not mutate after the
fork, and the experiment cannot separate the harm of poison from its lesson.

Page with charts, report, preregistration, data and code:
https://minimir.ilinmaks.com/n4.html

Перевод. Заголовок: Предрегистрированный опыт по искусственной жизни: несколько
быстрых учеников спасают популяцию, а мягкий яд спасает меньше миров.
Текст: продолжение прошлого поста, где 32 популяции из 40 погибли на первой смене
правила еды и главное сравнение было недействительно. В этот раз мы спросили, что
нужно популяции, чтобы пережить одну смену, и закоммитили правила до прогона.
Дальше устройство опыта (агенты, два цвета еды, один пластичный синапс,
наследуемая скорость обучения, смена на тике 5000, 26 копий каждого мира с одним
вмешательством, 150 миров), результаты по пунктам (доза как положительный
контроль; разброс спасает, 0 из 150 против 134 из 150, одной-двух быстрых особей
не хватает, при тридцати и больше спасается 85% миров и больше; мягкий яд хуже, 44,5% против
58,2%; порог у каждого мира не определён, верхняя граница 0,907 при планке 0,90,
планку не двигали; без обучения 0 из 150), проверка критериев на синтетических
данных и ограничения.

---

## Вариант 2. r/MachineLearning

**Title:** [R] Testing a preregistered criterion on synthetic null and synthetic effect before freezing it (ALife experiment, 150 worlds)

A methods note from a small artificial-life project. We preregister our
simulation experiments, and four times a criterion we committed turned out to be
unable to pass under any outcome. Example: a threshold defined as twice the
spread of a neutrally drifting gene. That gene mutates multiplicatively, so the
spread grows with run length, and by the end of the run the threshold demanded a
sixtyfold difference.

For the latest protocol we added one step before the freeze. Every criterion is
run on two kinds of synthetic data: pilot runs resampled with replacement, where
the effect is plausible, and data in which the effect is absent by construction.
A criterion is kept if it passes on at least 80% of the first and at most 5% of
the second. The same table set the sample size (one criterion passed 82% of the
time at n = 120 and 93% at n = 150). Thresholds are a smallest effect of
interest plus a bootstrap interval, with three verdicts: confirmed, refuted,
undetermined.

The experiment itself: 150 simulated worlds, one abrupt change of the food rule,
each world deep-copied before the change into 26 copies with one intervention
each. Two hypotheses confirmed (standing variation in learning rate rescues the
population, 0 of 150 against 134 of 150; a milder poison rescues fewer worlds,
because the learning signal scales with the harm), one undetermined: its
interval bound came out at 0.907 against a bar of 0.90, and we left the bar.

The caveat we put in the preregistration: the plausible-effect data is the pilot
effect, and pilot effects are inflated.

Report, preregistration, data, code: https://minimir.ilinmaks.com/n4.html

Перевод. Заголовок: [R] Проверка предрегистрированного критерия на синтетическом
нуле и синтетическом эффекте до заморозки (опыт по искусственной жизни, 150
миров). Текст: методическая заметка. Мы предрегистрируем опыты на симуляциях, и
четыре раза закоммиченный критерий не мог пройти ни при каком исходе (пример:
порог как удвоенный разброс нейтрально дрейфующего гена, который растёт с длиной
прогона). В последнем протоколе до заморозки каждый критерий прогоняется на двух
сортах синтетических данных; оставляем, если проходит не реже 80% на первых и не
чаще 5% на вторых; по той же таблице выбран объём. Дальше коротко сам опыт и
результат: две гипотезы подтверждены, одна не определена (граница 0,907 при
планке 0,90, планку оставили). Оговорка из предрегистрации: правдоподобный эффект
это эффект пилота, а пилотные эффекты завышены.

---

## Вариант 3. r/evolution

**Title:** Simulated evolutionary rescue: a population survives one abrupt change only if a few individuals already learn fast, and a milder change is survived less often

I run a small agent-based simulation and would like a check from people who know
the rescue literature better than I do.

Agents forage on a grid for two kinds of food, one nutritious and one poisonous.
Each has a preference that shifts after every bite, and a heritable rate at
which it shifts. Once per run the two foods swap roles. With a slow rate in
every individual, none of 150 populations survive the swap. If the same
populations are given rates spread around that same slow median just before the
swap, up to 134 of 150 survive. The rescued populations descend from one or two
individuals from the fast tail, and it takes roughly ten or more such
individuals present for rescue to be likely; one or two were never enough. The
rate does not mutate after the swap in this design, so this is rescue from
standing variation only.

The part I would like comments on. Theory (Gomulkiewicz and Holt 1995; Chevin,
Lande and Mace 2010) expects a milder environmental change to be survived more
often. Here a milder poison rescued fewer populations, 44% against 58%. My
explanation is that the poison is also the cue: the preference shifts in
proportion to the energy lost, so a weaker poison teaches more slowly and the
animals keep eating it. Is there a known biological analogue, where the severity
of a change is also what makes it detectable?

The criteria were fixed and published before the 150 runs, and one of the three
hypotheses came out undetermined. Details on the project page:
https://minimir.ilinmaks.com/n4.html

Перевод. Заголовок: Эволюционное спасение в симуляции: популяция переживает одну
резкую перемену, только если несколько особей уже учатся быстро, а мягкую
перемену переживают реже. Текст: я веду небольшую агентную симуляцию и хотел бы
проверки от людей, которые знают литературу о спасении лучше меня. Дальше
описание мира, результат про разброс скоростей (0 из 150 против 134 из 150,
спасённые популяции происходят от одной-двух особей из быстрого хвоста, нужно
порядка десяти таких особей), и вопрос: теория ждёт, что мягкую перемену
переживают чаще, а у нас мягкий яд спас меньше популяций, 44% против 58%; моё
объяснение в том, что яд заодно служит сигналом, и слабый яд учит медленнее. Есть
ли известный биологический аналог, где тяжесть перемены заодно делает её
заметной? Критерии были опубликованы до 150 прогонов, одна из трёх гипотез
осталась не определена.
