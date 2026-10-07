# dev.to (и Hashnode)

Front matter для dev.to, вставляется первым в редакторе:

```yaml
---
title: "A preregistered artificial life experiment that runs itself on GitHub Actions, and the threshold bug that ate the result"
published: false
description: "Forty seeds, six conditions, one hundred thousand ticks each, on free CI. Plus a design error worth copying down: a significance threshold that grows with the length of the run."
tags: python, githubactions, science, machinelearning
---
```

Теги на dev.to максимум четыре. Публиковать с `published: false`, посмотреть
превью, потом переключить.

---

## Английская версия

### A preregistered artificial life experiment that runs itself on GitHub Actions, and the threshold bug that ate the result

I run a small artificial life project: creatures with a tiny neural network on a
grid, food, energy, reproduction, death, and no fitness function anywhere.
Selection happens only through differences in offspring count. Last month the
second experiment finished accumulating, and the engineering side of it is
probably more reusable than the biology, so that is what this post is about.

Two things here might be worth stealing. One is a setup where a multi week
experiment accumulates itself on free CI and republishes its own results page.
The other is a mistake in the statistical criterion that I would not have caught
by reading my own code, only by plotting the threshold over time.

#### The question, in one paragraph

Food comes in two colours. One is nutritious, the other is poison, and the roles
reverse at unpredictable moments. Nothing inherited can be right for long, so
the correct colour can only be learned within a life. What learns is a single
plastic synapse, and the rate at which it learns is itself a gene that mutates
multiplicatively. The hypothesis, taken from Kozielska and Weissing 2024, is
that selection raises that rate where the world keeps changing its rules.

#### One source of truth for conditions

The first thing that saved me real debugging time was refusing to let condition
definitions live in more than one file. Six conditions, one dict:

```python
CONDS = ["never", "slow", "life", "fast", "life_frozen", "never_frozen"]
SWITCH  = dict(never=0, slow=5000, life=600, fast=150, life_frozen=600, never_frozen=0)
PLASTIC = dict(never=True, slow=True, life=True, fast=True,
               life_frozen=False, never_frozen=False)
```

The nightly job, the statistics module and the page builder all import this. A
condition cannot drift between the runner and the analysis, because there is
nowhere for it to drift to. The two `frozen` conditions are the ablation: the
gene is present and inherited, the learning simply is not applied. That one flag
is the difference between a correlation and a causal claim, and it costs one
boolean.

#### The barrier that has to be explicit

If you simulate inheritance with arrays, Lamarckian inheritance is the default
and you will not notice. The parent's weight array is right there, and copying it
is the obvious thing to do. So the genome and the phenotype are separate arrays,
and reproduction copies the genome only:

```python
# simplified from sim/brain.py, where the arrays are G1/G2 and W1/W2
child.genome   = mutate(parent.genome)      # inherited
child.weights  = child.genome.copy()        # phenotype starts from the genome
# lifetime learning writes to child.weights and never back to child.genome
```

This gave me a free correctness check. In the condition where learning is
switched off, the measured phenotype must equal the genome exactly. It does:
+3.04 against +3.04. If it had not, the barrier was leaking somewhere.

#### Accumulating on free CI

One cron entry, two seeds per night, a hundred thousand ticks each. The runner
reads how many seeds are already in the results file, computes which seeds are
missing, runs those, appends one JSON line per run, then regenerates the public
journal page from everything accumulated so far and commits it.

Three details that matter more than they look:

The results file is append only JSON lines. Never rewritten, never sorted, never
deduplicated in place. A crashed job leaves a short file, not a corrupted one.

Every line carries the protocol name, the tick count and the commit hash it was
produced by. When I later changed the engine, I could tell at a glance which
rows were no longer comparable. Earlier in the project I lost a pilot dataset
because runs of different length were pooled, and the lines did not say so.

The runner stops itself. Target forty seeds, and when the file already has forty
it exits without computing anything. The experiment ends on its own on the date
the preregistration implied, not on the date I remembered to switch it off.

Total cost: zero. 240 runs of a hundred thousand ticks each fit inside the free
GitHub Actions allowance for a public repository, two runs at a time.

#### The bug worth writing down

Here is the part I would want someone to tell me about before I made it.

The criterion declared in advance was a double one. A paired test at p below
0.01, and the gap between median log10 learning rates exceeding two sigma of the
spread of that same gene in a control where it affects nothing. The second half
is the interesting idea: before claiming that a gene moved, show what that gene
does when nothing pushes it.

The gene mutates multiplicatively, `rate *= exp(N(0, 0.3))`. With no selection
that is a random walk in log space, and the variance of a random walk grows
linearly with time. So the control does not give you a fixed reference. It gives
you a reference that widens every tick.

| tick | 2σ threshold, log10 | as a ratio |
|---|---|---|
| 2 000 | 0.131 | 1x |
| 20 000 | 1.006 | 10x |
| 100 000 | 1.786 | 61x |

The effect I measured was 1.16 in log10, a ratio of 14.5. It would have passed
the criterion at twenty thousand ticks and failed at a hundred thousand. Same
effect, same data, different declared run length.

That is not a statistical subtlety, it is a unit error of a sort: the threshold
measures the duration of the run rather than the size of the effect. I am not
moving it now, because a criterion rewritten after seeing the data is not a
criterion. But if you are comparing anything against a neutral control, check
whether your control is stationary. Plot it against time before you freeze the
number.

#### What the runs produced

For completeness, since the engineering existed to answer something.

The declared failure boundary fired. In the main condition thirty two
populations out of forty went extinct, against a declared ceiling of fifty
percent, so the comparison is void and the protocol is replaced rather than
retuned. The median population lives through exactly one rule reversal before
dying, so the lethal thing is the first switch and not the switching frequency.
The arithmetic, which belonged before the runs: a poisonous bite costs about
five energy, the cap is a hundred, one bite shifts taste by about 0.1, and
crossing from plus three to minus three takes sixty poisonings. A creature at
the starting rate cannot afford to relearn.

The ablation is clean. Without lifetime learning, forty worlds out of forty
died. With it, eight survived. Eight discordant pairs, zero in the other
direction, exact McNemar p = 0.0078.

And the clearest mechanism: the inherited taste stayed at about plus three in
every condition, while in the changing world the learned phenotype flipped to
minus five. The genome cannot record a rule that changes at random, lifetime
learning can.

Code, raw data and the frozen preregistration:
https://github.com/akela1308/minimir
Full results with tables and caveats:
https://minimir.ilinmaks.com/results-b.html

---

## Русская версия (для Habr, если захочется инженерный вариант)

### Предрегистрированный ALife-эксперимент, который сам считается на GitHub Actions, и баг в пороге, съевший результат

Я веду небольшой проект про искусственную жизнь: существа с крошечной
нейросетью на сетке, еда, энергия, размножение, смерть, и ни одной функции
приспособленности. Отбор идёт только через разницу в числе потомков. В прошлом
месяце второй эксперимент закончил накопление, и инженерная часть там, кажется,
полезнее биологической, так что про неё и напишу.

Две вещи тут стоит унести с собой. Первая это схема, при которой многонедельный
эксперимент сам копится на бесплатном CI и сам перепубликовывает свою страницу
результатов. Вторая это ошибка в статистическом критерии, которую я бы не нашёл
чтением собственного кода, только нарисовав порог как функцию времени.

#### Вопрос в одном абзаце

Еда двух цветов. Один питателен, другой ядовит, и роли переворачиваются в
непредсказуемые моменты. Ничто наследуемое не может быть верным долго, поэтому
правильный цвет можно выучить только при жизни. Учится один пластичный синапс, а
скорость его обучения сама является геном, мутирующим множителем. Гипотеза,
взятая у Kozielska и Weissing 2024, состоит в том, что отбор поднимает эту
скорость там, где мир меняет правила.

#### Одна точка правды по условиям

Первое, что сэкономило мне реальное время на отладке, это отказ держать
определения условий больше чем в одном файле. Шесть условий, один словарь:

```python
CONDS = ["never", "slow", "life", "fast", "life_frozen", "never_frozen"]
SWITCH  = dict(never=0, slow=5000, life=600, fast=150, life_frozen=600, never_frozen=0)
PLASTIC = dict(never=True, slow=True, life=True, fast=True,
               life_frozen=False, never_frozen=False)
```

Суточная задача, модуль статистики и сборщик страницы импортируют это. Условие
не может разъехаться между прогоном и анализом, потому что разъезжаться некуда.
Два условия `frozen` это абляция: ген есть и наследуется, просто обучение не
применяется. Этот один флаг отличает корреляцию от причинного утверждения и
стоит одного булева значения.

#### Барьер, который надо делать явно

Если наследование моделируется массивами, ламарковское наследование получается
по умолчанию, и вы этого не заметите. Массив весов родителя лежит прямо тут, и
скопировать его это самое очевидное действие. Поэтому геном и фенотип это
отдельные массивы, а размножение копирует только геном:

```python
# упрощённо, по sim/brain.py, где массивы называются G1/G2 и W1/W2
child.genome  = mutate(parent.genome)     # наследуется
child.weights = child.genome.copy()       # фенотип стартует от генома
# прижизненное обучение пишет в child.weights и никогда обратно в геном
```

Это дало бесплатную проверку корректности. В условии с отключённым обучением
измеренный фенотип обязан в точности равняться геному. Так и есть: +3,04 против
+3,04. Если бы не совпало, значит барьер где-то протекает.

#### Накопление на бесплатном CI

Одна строка в cron, два семени за ночь, по сто тысяч тиков каждое. Раннер
читает, сколько семян уже есть в файле результатов, вычисляет недостающие,
считает их, дописывает по одной JSON-строке на прогон, затем пересобирает
публичную страницу журнала по всему накопленному и коммитит её.

Три детали, которые важнее, чем выглядят.

Файл результатов это append-only JSON lines. Не перезаписывается, не
сортируется, не дедуплицируется на месте. Упавшая задача оставляет короткий
файл, а не испорченный.

Каждая строка несёт имя протокола, число тиков и хеш коммита, на котором она
получена. Когда я позже менял движок, было видно сразу, какие строки больше не
сопоставимы. Раньше в этом проекте я потерял пилотный датасет именно потому, что
в один пул попали прогоны разной длины, и строки об этом не сообщали.

Раннер останавливается сам. Цель сорок семян, и когда в файле уже сорок, он
выходит, ничего не посчитав. Эксперимент заканчивается в тот день, который
следует из предрегистрации, а не в тот, когда я вспомнил его выключить.

Стоимость: ноль. 240 прогонов по сто тысяч тиков укладываются в бесплатную квоту
GitHub Actions для публичного репозитория, по два прогона за раз.

#### Баг, который стоит записать

Теперь то, о чём я хотел бы, чтобы мне рассказали заранее.

Объявленный критерий был двойной. Парный тест с p меньше 0,01 и превышение
разницей медиан логарифма скорости обучения двух сигм разброса того же гена в
контроле, где он ни на что не влияет. Вторая половина это интересная идея:
прежде чем заявлять, что ген сдвинулся, покажи, что этот ген делает, когда его
никто не толкает.

Ген мутирует множителем, `rate *= exp(N(0, 0.3))`. Без отбора это случайное
блуждание в логарифмическом пространстве, а дисперсия случайного блуждания
растёт линейно со временем. То есть контроль даёт не фиксированную точку
отсчёта, а точку отсчёта, которая расширяется каждый тик.

| тик | порог 2σ, log10 | во сколько раз |
|---|---|---|
| 2 000 | 0,131 | 1x |
| 20 000 | 1,006 | 10x |
| 100 000 | 1,786 | 61x |

Измеренный эффект составил 1,16 в log10, то есть отношение 14,5. На двадцати
тысячах тиков он бы критерий прошёл, на ста тысячах не прошёл. Тот же эффект, те
же данные, разная объявленная длина прогона.

Это не статистическая тонкость, это по сути ошибка размерности: порог измеряет
длительность прогона, а не величину эффекта. Сейчас я его не двигаю, потому что
критерий, переписанный после взгляда на данные, уже не критерий. Но если вы
сравниваете что-нибудь с нейтральным контролем, проверьте, стационарен ли ваш
контроль. Нарисуйте его как функцию времени до того, как заморозите число.

#### Что дали прогоны

Для полноты, раз инженерия существовала ради ответа.

Объявленная граница провала сработала. В основном условии вымерли тридцать два
мира из сорока при объявленном потолке в пятьдесят процентов, так что сравнение
недействительно, и протокол заменяется, а не перенастраивается. Медианная
популяция переживает ровно один переворот правила до гибели, значит летален
первый переворот, а не частота переворотов. Арифметика, которой место было до
прогонов: ядовитый укус стоит около пяти единиц энергии, предел сто, один укус
сдвигает вкус примерно на 0,1, а переезд от плюс трёх к минус трём требует
шестидесяти отравлений. Существо со стартовой скоростью не может позволить себе
переучивание.

Абляция чистая. Без прижизненного обучения вымерли сорок миров из сорока. С ним
выжило восемь. Восемь расходящихся пар, ноль в обратную сторону, точный тест
Макнемара p = 0,0078.

И самый наглядный механизм: врождённый вкус остался около плюс трёх во всех
условиях, а в меняющемся мире выученный фенотип развернулся в минус пять. Геном
не может записать правило, которое меняется случайно, прижизненное обучение
может.

Код, сырые данные и замороженная предрегистрация:
https://github.com/akela1308/minimir
Полные результаты с таблицами и оговорками:
https://minimir.ilinmaks.com/results-b.html
