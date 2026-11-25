# dev.to, Hashnode: протокол N4 с инженерной стороны

Статья, две версии. Ссылки: страница опыта https://minimir.ilinmaks.com/n4.html
и репозиторий https://github.com/akela1308/minimir

Для dev.to в шапке: `published: false`, посмотреть превью, потом включить.
Теги: `simulation`, `python`, `opensource`, `science`.

---

## English version

### Fork the world, not the seed: a paired design for simulation experiments

We run a small artificial-life world: creatures with a tiny neural network on a
grid, two colours of food, one nutritious and one poisonous. In the last
experiment the colours swapped and 32 of 40 populations died at the first swap.
This time we wanted to know what a population needs to live through one swap,
and we ran into a design problem that probably applies to other simulation
experiments too.

#### Same seed does not mean same world

The usual way to compare two conditions is to run both from one seed. We did
that for months. Then we looked at lineages and found that by tick 5,000 a world
descends from between 1 and 28 of its founding lineages. A parameter set at
tick 0 has gone through that lottery before it can matter, so the comparison is
between two different histories that happen to share a number.

The fix is to fork later. Run the world once up to the tick before the event,
then copy all of it and apply one intervention per copy (simplified from
`sim/protocol_n4.py`):

```python
def fork(eng, spec):
    clone = copy.deepcopy(eng)          # world, population, RNG state
    cfg = clone.cfg
    cfg.toxic_factor = spec["toxic"]
    cfg.taste_learning = spec["learning"]
    ids = clone.pop.ids()
    if spec["dose"] is not None:        # same learning rate for everyone
        clone.pop.taste_lr[ids] = spec["dose"]
    else:                               # spread around the same median
        z = seed_z(cfg.seed, ids.size)  # separate generator, seeded by seed only
        clone.pop.taste_lr[ids] = np.clip(L0 * np.exp(spec["sigma"] * z), 0, LR_MAX)
    return clone
```

Because the copy includes the generator state, the 26 copies of one world are
identical up to the last tick: same map, same individuals, same energy. One
detail matters here. The random numbers for the spread come from a
separate generator seeded by the seed alone, so every individual gets the same
`z` in all conditions and `sigma` only stretches it. Drawing them from the main
stream would have shifted everything downstream.

Tests assert that forks share their history and differ only by the
intervention, that a fork is deterministic, and that with the new parameter
switched off the engine reproduces old runs bit for bit.

#### Test the criterion before you freeze it

We preregister: the pass rules are committed before the confirmatory run. Four
times in this project a rule we committed could not pass under any outcome. One
compared an effect capped at 0.9 with a threshold that came out at 0.96 to 1.57.

So before freezing we now run each criterion on synthetic data twice (in
outline; the script is `runs/n4/attainability_check.py`):

```python
for n in (60, 90, 120, 150):
    for name in ("K1", "K2", "K3", "K4"):
        for _ in range(400):
            d = resample(pilot, n)               # plausible effect
            hit_effect += passes(name, d)
            hit_null += passes(name, null_for(name, d))   # no effect by construction
```

A criterion is kept if it passes on at least 80% of the first kind and at most
5% of the second. That table also picked the sample size: one criterion passed
in 82% of datasets at 120 worlds and 93% at 150.

The runner refuses to start a confirmatory run until the preregistration file
exists without the word draft in its name, and the reader refuses to read twice.
Each check is about a dozen lines.

#### What the 150 worlds showed

With the same slow learning rate in every individual, 0 of 150 worlds survive.
With rates spread around the same median, 134 do. The survivors descend from one
or two fast learners, and one or two fast learners in the population were never
enough to start with; it took about ten or more.

Mild poison rescued fewer worlds than regular poison, 44% against 58%, the
opposite of what evolutionary rescue theory expects. In this world the update
after a bite scales with the energy lost, so a weak poison is also a weak
training signal.

A third hypothesis stayed undetermined: the bar was at 90% and the upper bound
of the interval came out at 90.7%. We left the bar where it was.

The run happened on GitHub Actions on the frozen commit, and two worlds
recomputed on another machine matched in all 26 conditions.

Page with charts and the full report: https://minimir.ilinmaks.com/n4.html
Code and data: https://github.com/akela1308/minimir

---

## Русская версия

### Разветвлять мир, а не семя: парный дизайн для опытов на симуляциях

У нас есть маленький мир искусственной жизни: существа с крошечной нейросетью на
сетке, еда двух цветов, один цвет кормит, другой травит. В прошлом опыте цвета
менялись местами, и 32 популяции из 40 вымерли на первой же смене. В этот раз мы
хотели узнать, что нужно популяции, чтобы одну смену пережить, и упёрлись в
проблему дизайна, которая, скорее всего, есть и у других опытов на симуляциях.

#### Одно семя ещё не значит один мир

Обычно два условия сравнивают, запуская оба от одного семени. Мы так делали
несколько месяцев. Потом посмотрели на родословные и увидели, что к тику 5000 мир
происходит от 1-28 линий основателей. Параметр, заданный на нулевом тике,
проходит через эту лотерею раньше, чем начинает что-то значить, и сравниваются
на деле две разные истории с общим номером.

Решение: разветвлять позже. Мир один раз доживает до тика перед событием, потом
копируется целиком, и в каждой копии делается одно вмешательство (код выше, в
английской версии, функция `fork`).

Копия включает состояние генератора, поэтому 26 копий одного мира совпадают до
последнего тика: та же карта, те же особи, та же энергия. Здесь важна
одна деталь. Случайные числа для разброса берутся из
отдельного генератора, засеянного только семенем, так что у каждой особи одно и
то же `z` во всех условиях, а `sigma` его только растягивает. Если брать их из
главного потока, всё дальнейшее сдвинулось бы.

Тесты проверяют, что у копий общая история и различаются они только
вмешательством, что развилка детерминирована и что при выключенном новом
параметре движок воспроизводит старые прогоны бит в бит.

#### Проверять критерий до заморозки

Мы предрегистрируем опыты: правила прохождения коммитятся до подтверждающего
прогона. Четыре раза в этом проекте закоммиченное правило не могло пройти ни при
каком исходе. Одно сравнивало эффект, ограниченный сверху числом 0,9, с порогом,
который получался от 0,96 до 1,57.

Поэтому теперь до заморозки каждый критерий прогоняется на синтетических данных
дважды: на пересэмплированных мирах пилота, где эффект правдоподобен, и на
данных, где эффекта нет по построению. Критерий остаётся, если проходит не реже
чем в 80% первых и не чаще чем в 5% вторых. По той же таблице выбран объём: при
120 мирах один критерий проходил в 82% наборов, при 150 в 93%.

Раннер отказывается начинать подтверждающий прогон, пока файл предрегистрации не
лежит в репозитории без слова черновик в имени, а чтение отказывается читать
второй раз. Каждая из этих проверок занимает около десятка строк.

#### Что показали 150 миров

При одной и той же медленной скорости обучения у всех особей выживает 0 миров из
150. При скоростях, разбросанных вокруг той же медианы, выживает 134. Выжившие
происходят от одного-двух быстрых учеников, но одного-двух быстрых особей в
популяции для спасения не хватило ни разу, понадобилось порядка десяти и больше.

Мягкий яд спас меньше миров, чем обычный, 44% против 58%, вопреки теории
эволюционного спасения. В этом мире сдвиг вкуса после укуса пропорционален
потерянной энергии, поэтому слабый яд это ещё и слабый обучающий сигнал.

Третья гипотеза осталась не определена: планка стояла на 90%, а верхняя граница
интервала вышла 90,7%. Планку оставили на месте.

Счёт шёл на GitHub Actions на замороженном коммите, и два мира, пересчитанные на
другой машине, совпали во всех 26 условиях.

Страница с графиками и полным отчётом: https://minimir.ilinmaks.com/n4.html
Код и данные: https://github.com/akela1308/minimir
