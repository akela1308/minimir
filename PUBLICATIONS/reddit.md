# Reddit

Четыре варианта под разные сабреддиты. Reddit плохо реагирует на пиар, поэтому
везде текст написан как отчёт, а ссылка стоит в конце одной строкой. Правила
сабреддитов меняются, перед постом стоит глянуть сайдбар: в r/MachineLearning
нужен префикс [R] в заголовке, в r/science личные проекты не пройдут модерацию,
туда не надо.

Для каждого варианта дан английский текст (его и публикуем) и русский перевод,
чтобы было понятно, что именно отправляется.

---

## 1. r/MachineLearning

**Title (EN):** [R] Preregistered ALife experiment on the evolution of learning: the declared failure boundary fired, but the ablation is clean (40/40 extinctions without lifetime plasticity)

**Заголовок по-русски (для понимания):** Предрегистрированный ALife-эксперимент
про эволюцию обучения: объявленная граница провала сработала, но абляция чистая
(40 вымираний из 40 без прижизненной пластичности)

### Текст (EN)

Setup. A grid world, agents with a 25-12-12 network, food, energy,
reproduction, death, no fitness function. Selection acts only through
differences in offspring count. Food has two colours, one nutritious and one
toxic, and the roles reverse at moments drawn from a separate seeded generator,
intervals uniform on [0.5T, 1.5T]. A single synapse is plastic (colour to eat
decision), updated by a three factor rule, and the learning rate for that
synapse is itself a multiplicatively mutating gene. Lifetime changes are not
inherited: genome and phenotype are separate arrays and reproduction copies the
genome.

Hypothesis, from Kozielska and Weissing (PLoS Comput Biol 2024): the evolved
learning rate is higher where the environment changes faster than generations
turn over.

Design. Six conditions on identical seeds from a shared ancestor: never (T=0),
slow (T=5000), life (T=600), fast (T=150), plus life_frozen and never_frozen
where the gene exists but learning is not applied. 40 seeds, 100k ticks, 240
runs. Criteria, readings at 10/20/40 seeds and failure boundaries were frozen
before the first run.

Results.

1. Declared failure boundary fired. 32 of 40 populations in the treatment went
extinct against a declared ceiling of 50 percent, so the primary comparison is
void by preregistration. Median number of rule reversals survived before
extinction is 1 in life, slow and life_frozen alike, so the lethal event is the
first switch rather than the switching frequency. Energy arithmetic explains it
and should have been done in advance: a toxic bite costs about 5 energy against
a cap of 100, one bite shifts taste by about 0.1, and crossing from the innate
+3 to a stable -3 takes roughly 60 poisonings.

2. Ablation is clean. life vs life_frozen, same seeds and ancestor: 8 discordant
pairs, all in one direction, 0 reversed, exact McNemar p = 0.0078. Extinction
32/40 against 40/40. No world survived without lifetime learning.

3. Mechanism. Genome taste stayed near +3.0 in every condition including the
changing ones, while the phenotype in life went to -4.92. Where learning is off,
phenotype equals genome exactly, which also validates the barrier. Within life
learning is visible directly: edible bite fraction goes 0.845 in the first 50
ticks of life to 0.94 by tick 100, and after a reversal agents born before it
drop to 0.66 and recover to 0.98 within about 150 ticks.

4. Criterion 2 was unreachable by construction, and this is the part I would
flag for anyone doing something similar. The declared threshold was two sigma of
the neutral drift of the same gene in never_frozen. The gene mutates
multiplicatively, so without selection it is a random walk in log space and its
variance grows with run length. The threshold went from 0.131 in log10 at tick
2000 to 1.786 at tick 100k, that is from 1x to 61x. The measured effect was
x14.5, or 1.16 in log10. The same effect would have passed at 20k ticks. The
threshold measures run length, not effect size. I am not moving it post hoc; the
next protocol compares against drift at the same tick.

5. H-B2 not confirmed and it narrows an earlier claim of mine. In the stationary
world learning did not get selected away (ratio 1.38, p = 0.115), contradicting
an earlier pilot of mine where a general Hebbian rule over the whole output
layer halved the learning rate within 15k ticks. The difference appears to be
the cost of the plasticity rule rather than the stationarity of the world. One
cheap synapse with a dead zone has nothing for selection to push against.

Caveats. The 8 surviving life worlds are selected on survival, so the x14.5
ratio describes evolution where evolution had time to happen, not the expected
outcome in a random world. One plastic synapse, one grid, one metabolism, no
generalisation to a general learning rule is claimed. H-B3 (frequency gradient)
is untestable on these data rather than refuted, the first switch swamps it:
life vs fast gave 3 discordant against 1, p = 0.625.

One note for anyone recomputing from the raw data: because the rate gene mutates
multiplicatively, all medians and quartiles of the learning rate are taken on
the log10 scale and mapped back, and the life/never ratio is
10 ** median(log10 life - log10 never) over pairs rather than a ratio of linear
medians. Linear medians on the same data give x14.95 instead of x14.47. Food
accuracy is a mean over surviving runs. Extinction fractions use all 40 runs,
everything else uses survivors only.

Preregistration, raw data (240 JSON lines), engine and the full report are in
the repo. Results write up with all tables: https://minimir.ilinmaks.com/results-b.html

### Перевод текста на русский

Конструкция. Мир на сетке, агенты с сетью 25-12-12, еда, энергия, размножение,
смерть, функции приспособленности нет. Отбор действует только через разницу в
числе потомков. У еды два цвета, один питателен, другой токсичен, и роли
переворачиваются в моменты из отдельного засеянного генератора, интервалы
равномерны на [0.5T, 1.5T]. Пластичен один синапс (цвет к решению есть),
обновляется трёхфакторным правилом, а скорость обучения этого синапса сама
является геном, мутирующим множителем. Прижизненные изменения не наследуются:
геном и фенотип это отдельные массивы, размножение копирует геном.

Гипотеза, из Kozielska и Weissing (PLoS Comput Biol 2024): отобранная скорость
обучения выше там, где среда меняется быстрее, чем сменяются поколения.

Дизайн. Шесть условий на одних семенах от общего предка: never (T=0), slow
(T=5000), life (T=600), fast (T=150), плюс life_frozen и never_frozen, где ген
есть, но обучение не применяется. 40 семян, 100 тысяч тиков, 240 прогонов.
Критерии, чтения на 10/20/40 семенах и границы провала заморожены до первого
прогона.

Результаты.

1. Объявленная граница провала сработала. 32 популяции из 40 в лечении вымерли
при объявленном потолке 50 процентов, поэтому главное сравнение недействительно
по предрегистрации. Медианное число переживаемых переворотов правила до
вымирания равно 1 и в life, и в slow, и в life_frozen, то есть летален первый
переворот, а не частота. Энергетическая арифметика это объясняет, и считать её
надо было заранее: токсичный укус стоит около 5 энергии при пределе 100, один
укус сдвигает вкус примерно на 0,1, а переезд от врождённого +3 к устойчивому -3
требует порядка 60 отравлений.

2. Абляция чистая. life против life_frozen, те же семена и предок: 8
расходящихся пар, все в одну сторону, 0 обратных, точный тест Макнемара p =
0,0078. Вымирание 32/40 против 40/40. Без прижизненного обучения не выжил ни
один мир.

3. Механизм. Вкус в геноме остался около +3,0 во всех условиях, включая
меняющиеся, а фенотип в life ушёл к -4,92. Там, где обучение отключено, фенотип
в точности равен геному, что заодно валидирует барьер. Обучение внутри жизни
видно напрямую: доля съедобных укусов идёт от 0,845 в первые 50 тиков жизни к
0,94 к сотому тику, а после переворота родившиеся до него проваливаются до 0,66
и восстанавливаются до 0,98 примерно за 150 тиков.

4. Критерий 2 был недостижим по построению, и именно это я бы отметил для всех,
кто делает нечто похожее. Объявленный порог это два сигма нейтрального дрейфа
того же гена в never_frozen. Ген мутирует множителем, поэтому без отбора это
случайное блуждание в логарифмическом пространстве, и его дисперсия растёт с
длиной прогона. Порог вырос с 0,131 в log10 на тике 2000 до 1,786 на тике 100
тысяч, то есть с 1x до 61x. Измеренный эффект составил x14,5, или 1,16 в log10.
Тот же эффект прошёл бы на 20 тысячах тиков. Порог измеряет длину прогона, а не
величину эффекта. Задним числом я его не двигаю, следующий протокол сравнивает с
дрейфом на том же тике.

5. H-B2 не подтверждена, и это сужает моё же прежнее утверждение. В стационарном
мире обучение не отобралось прочь (отношение 1,38, p = 0,115), что противоречит
моему более раннему пилоту, где общее хеббовское правило на всём выходном слое
снижало скорость обучения вдвое за 15 тысяч тиков. Разница, похоже, в цене
правила пластичности, а не в стационарности мира. Одному дешёвому синапсу с
мёртвой зоной отбору нечего противопоставить.

Замечание для тех, кто будет пересчитывать по сырым данным: поскольку ген
скорости мутирует множителем, все медианы и квартили скорости обучения берутся
на шкале log10 и возвращаются обратно, а отношение life/never это
10 ** median(log10 life - log10 never) по парам, а не отношение линейных медиан.
Линейные медианы на тех же данных дают x14,95 вместо x14,47. Точность еды это
среднее по выжившим прогонам. Доли вымираний считаются по всем 40 прогонам,
всё остальное только по выжившим.

Оговорки. 8 выживших миров life отобраны по выживанию, поэтому отношение x14,5
описывает эволюцию там, где она успела произойти, а не ожидаемый исход в
случайном мире. Один пластичный синапс, одна сетка, один метаболизм, обобщения
на общее правило обучения не заявляется. H-B3 (градиент частоты) не проверяема на
этих данных, а не опровергнута, первый переворот её перекрывает: life против fast
дал 3 расхождения против 1, p = 0,625.

---

## 2. r/artificial, r/singularity

**Title (EN):** I ran 240 evolution simulations to see if selection switches on the ability to learn. 80 percent of the worlds died at the first rule change, and that was the answer I had agreed to accept

### Текст (EN)

I build tiny worlds. Creatures with a small neural network on a grid, food,
energy, reproduction, death, and nothing that hands out a score. No reward
function, no fitness function, no judge. If a creature leaves more offspring,
its design spreads. That is the whole mechanism.

Six months ago I added a rule for myself: the criteria for success get written
down before the simulations run, and the verdict does not get rewritten
afterwards. It is an uncomfortable rule and it just cost me a result I wanted.

The question. Food comes in two colours. One is nutritious, the other is poison,
and they swap roles at random moments. Nothing you can inherit will be right for
long, so the only way to know what is edible today is to learn it while alive. I
gave the creatures exactly one thing they can learn, a taste for a colour, and
made the speed of that learning a gene that can mutate. Then I asked whether
selection turns that speed up in a world that keeps changing, and leaves it
alone in a world that does not.

What happened is that the world turned out to be too cruel to answer the
question. Thirty two populations out of forty died at the very first reversal. I
had declared in advance that above fifty percent extinction the comparison is
void, so it is void, and the protocol gets replaced rather than tuned until the
numbers look good.

The arithmetic I should have done first: a poisonous bite costs about five
energy, a creature can hold a hundred, and crossing from liking one colour to
liking the other takes about sixty poisonings. They die before they can work out
that the rules changed.

Three things did come out of it.

The ablation is as clean as I have ever got. Same world, same random seeds, same
ancestor, the only difference being whether lifetime learning is applied at all.
Without it, forty worlds out of forty went extinct. With it, eight survived. In
a world that changes its rules, the ability to learn is not an advantage, it is
the entry fee.

The split between heredity and learning is visible in two numbers. In the
survivors the inherited taste never moved, it stayed at about the value they
started with. The taste learned during life flipped to the opposite sign. The
genome cannot store a rule that changes at random, so it does not try. Knowledge
about today lives inside one life and every generation earns it again.

And the eight survivors did not survive by luck alone. Their populations were
the same size as the ones that died, but their learning rates were slightly
higher before the catastrophe hit. Selection had something to work with, and
after the bottleneck the learning rate in those worlds grew about thirtyfold
within a few hundred ticks.

I also found a mistake of my own that is worth more than the experiment. The
threshold I had promised to beat grows with the length of the run, because the
gene it is based on wanders further the longer you watch it. By the end it
demanded a sixtyfold difference and my effect was fourteenfold. Stop the runs
five times earlier and the same result passes. I am not changing the rule now,
because a criterion invented after seeing the data is not a criterion, but the
next version will be different.

Full write up with all the tables and the caveats, plus a plain language summary
at the end: https://minimir.ilinmaks.com/results-b.html

### Перевод на русский

Я строю крошечные миры. Существа с маленькой нейросетью на сетке, еда, энергия,
размножение, смерть, и ничего, что выставляло бы оценку. Ни функции награды, ни
функции приспособленности, ни судьи. Если существо оставило больше потомков, его
устройство распространилось. Весь механизм в этом.

Полгода назад я ввёл себе правило: критерии успеха записываются до прогонов, а
вердикт после них не переписывается. Правило неудобное, и оно только что стоило
мне результата, который я хотел.

Вопрос. Еда двух цветов. Один питателен, другой ядовит, и они меняются ролями в
случайные моменты. Ничто наследуемое не будет верным долго, поэтому узнать, что
съедобно сегодня, можно только выучив это при жизни. Я дал существам ровно одну
вещь, которую можно выучить, вкус к цвету, и сделал скорость этого обучения
геном, который может мутировать. А дальше спросил, поднимает ли отбор эту
скорость в меняющемся мире и оставляет ли её в покое там, где мир не меняется.

Получилось так, что мир оказался слишком жестоким, чтобы ответить на вопрос.
Тридцать две популяции из сорока погибли на первом же перевороте. Я заранее
объявил, что при вымирании выше пятидесяти процентов сравнение недействительно,
значит оно недействительно, и протокол заменяется, а не подкручивается до
красивых чисел.

Арифметика, которую стоило посчитать первой: ядовитый укус стоит около пяти
единиц энергии, держать существо может сотню, а переезд от любви к одному цвету
к любви к другому требует около шестидесяти отравлений. Они умирают раньше, чем
успевают понять, что правила изменились.

Три вещи из этого всё же вышли.

Абляция получилась самой чистой, какая у меня вообще была. Тот же мир, те же
случайные семена, тот же предок, разница только в том, применяется ли
прижизненное обучение вообще. Без него вымерли сорок миров из сорока. С ним
выжило восемь. В мире, который меняет правила, способность учиться это не
преимущество, это входная плата.

Разделение между наследственностью и обучением видно в двух числах. У выживших
врождённый вкус не сдвинулся, остался примерно тем, с которого начинали. Вкус,
выученный при жизни, развернулся в противоположный знак. Геном не может хранить
правило, которое меняется случайно, поэтому он и не пытается. Знание о сегодняшнем
дне живёт внутри одной жизни, и каждое поколение добывает его заново.

И восемь выживших выжили не на одном везении. Их популяции были такого же
размера, как у погибших, но скорость обучения у них была чуть выше ещё до
катастрофы. Отбору было с чем работать, и после горлышка скорость обучения в тех
мирах выросла примерно в тридцать раз за несколько сотен тиков.

Ещё я нашёл свою собственную ошибку, которая стоит больше, чем сам эксперимент.
Порог, который я обещал побить, растёт с длиной прогона, потому что ген, на
котором он построен, уходит тем дальше, чем дольше за ним смотришь. К концу он
требовал шестидесятикратной разницы, а мой эффект был в четырнадцать раз.
Останови прогоны в пять раз раньше, и тот же результат проходит. Правило я сейчас
не меняю, потому что критерий, придуманный после взгляда на данные, уже не
критерий, но следующая версия будет другой.

---

## 3. r/alife, r/artificialintelligence, r/compsci

**Title (EN):** Preregistered ALife run: without lifetime plasticity 40 of 40 worlds went extinct, with it 8 survived. The main hypothesis still did not pass

### Текст (EN)

Short version of a protocol that just closed, posted because the negative part
is more useful than the positive part.

The world: grid, small network per agent, two food colours, one nutritious and
one toxic, roles reversing at unpredictable intervals. One plastic synapse
(colour to eat), three factor update, and the learning rate of that synapse is a
multiplicatively mutating gene. No fitness function. Weismann barrier is
explicit: genome and phenotype are separate arrays, reproduction copies the
genome, so nothing learned is inherited.

Six conditions on shared seeds and a shared ancestor, 40 seeds, 100k ticks, 240
runs, all criteria frozen before the first run.

The headline is an extinction, not a confirmation. 32 of 40 treatment
populations died, against a declared failure ceiling of 50 percent, so the
primary comparison is void. The median population survives exactly one rule
reversal, which means the first switch is lethal and the switching frequency
never gets a chance to matter. The energy budget explains it: a toxic bite costs
about 5 of a 100 cap, one bite moves taste by 0.1, and inverting an innate taste
of +3 takes around 60 poisonings.

What does hold up:

Ablation. Same world with learning applied and not applied: 8 discordant pairs,
all one way, exact McNemar p = 0.0078, extinction 32/40 vs 40/40.

Genotype and phenotype separation. Genome taste stays at about +3.0 in all six
conditions. Phenotype equals genome exactly where learning is off, reaches +5.6
in the stationary world, and goes to -4.9 in the changing one. A randomly
changing rule is not something a genome can encode, and the simulation shows
exactly that asymmetry.

Within life curves. Edible bite fraction rises from 0.845 in the first 50 ticks
of life to 0.94 by tick 100. After a reversal, agents born before it drop to
0.66 and recover to 0.98 in about 150 ticks.

Two things worth knowing if you build something similar:

My second criterion was unreachable by construction. It compared the effect to
two sigma of the neutral drift of the same gene, measured at the end of the run.
Multiplicative mutation plus no selection equals a random walk in log space,
whose variance grows with time, so the threshold grew from 1x at tick 2000 to
61x at tick 100k while the effect stayed at 14.5x. Check that your neutral
reference is stationary before freezing a number.

Plasticity cost matters more than environmental stability. An earlier pilot of
mine with a general Hebbian rule over the output layer showed the learning rate
halving in a stationary world, which I had read as selection removing useless
plasticity. With one cheap synapse there is no such fall (ratio 1.38, p =
0.115). The earlier result was about the price of the rule, not about
stationarity.

Code, data, preregistration and report: https://github.com/akela1308/minimir
Results page: https://minimir.ilinmaks.com/results-b.html

### Перевод на русский

Короткая версия только что закрытого протокола, выкладываю потому, что
отрицательная часть полезнее положительной.

Мир: сетка, маленькая сеть на агента, два цвета еды, один питателен, другой
токсичен, роли переворачиваются с непредсказуемыми интервалами. Один пластичный
синапс (цвет к действию есть), трёхфакторное обновление, и скорость обучения
этого синапса это ген, мутирующий множителем. Функции приспособленности нет.
Барьер Вейсмана задан явно: геном и фенотип это отдельные массивы, размножение
копирует геном, поэтому выученное не наследуется.

Шесть условий на общих семенах и общем предке, 40 семян, 100 тысяч тиков, 240
прогонов, все критерии заморожены до первого прогона.

Главное здесь это вымирание, а не подтверждение. 32 популяции из 40 в лечении
погибли при объявленном потолке провала в 50 процентов, поэтому главное
сравнение недействительно. Медианная популяция переживает ровно один переворот
правила, то есть летален первый переворот, а частота переключений просто не
получает шанса на что-то повлиять. Энергетический бюджет это объясняет: токсичный
укус стоит около 5 при пределе 100, один укус двигает вкус на 0,1, а обращение
врождённого вкуса +3 требует порядка 60 отравлений.

Что устояло:

Абляция. Тот же мир с применяемым обучением и без: 8 расходящихся пар, все в
одну сторону, точный тест Макнемара p = 0,0078, вымирание 32/40 против 40/40.

Разделение генотипа и фенотипа. Вкус в геноме держится около +3,0 во всех шести
условиях. Фенотип в точности равен геному там, где обучение отключено, достигает
+5,6 в стационарном мире и уходит к -4,9 в меняющемся. Случайно меняющееся
правило это не то, что геном способен закодировать, и симуляция показывает ровно
эту асимметрию.

Кривые внутри жизни. Доля съедобных укусов растёт с 0,845 в первые 50 тиков жизни
до 0,94 к сотому тику. После переворота родившиеся до него проваливаются до 0,66
и восстанавливаются до 0,98 примерно за 150 тиков.

Две вещи, которые стоит знать, если строите нечто похожее:

Мой второй критерий был недостижим по построению. Он сравнивал эффект с двумя
сигма нейтрального дрейфа того же гена, измеренного в конце прогона.
Множительная мутация плюс отсутствие отбора это случайное блуждание в
логарифмическом пространстве, дисперсия которого растёт со временем, поэтому
порог вырос с 1x на тике 2000 до 61x на тике 100 тысяч, а эффект остался 14,5x.
Проверяйте, стационарен ли ваш нейтральный контроль, прежде чем замораживать
число.

Цена пластичности важнее стабильности среды. Мой более ранний пилот с общим
хеббовским правилом на выходном слое показывал падение скорости обучения вдвое в
стационарном мире, и я читал это как снятие отбором бесполезной пластичности. С
одним дешёвым синапсом такого падения нет (отношение 1,38, p = 0,115). Прежний
результат был про цену правила, а не про стационарность.

---

## 4. r/evolution, r/biology (осторожно, там строгие модераторы и симуляции не все любят)

**Title (EN):** Simulation result: a trait that cannot be encoded in the genome because the right value changes at random, and what the population does instead

### Текст (EN)

This is from an artificial life simulation rather than from an organism, so take
it as a model result and not as evidence about any real lineage. I think the
mechanism is clean enough to be worth describing anyway.

The setup gives a population a problem with no heritable solution. Food comes in
two colours, one nutritious and one toxic, and the roles reverse at moments
drawn at random. There is no fitness function in the simulation, just food,
energy, reproduction and death, so selection acts only through differential
reproduction. Agents have one plastic connection, a preference for a colour,
which they can adjust during life. The rate at which they adjust it is itself a
heritable gene, and acquired changes are not inherited: offspring start from the
parental genome, not from the parent's trained state.

After 100k ticks on 40 independent replicates, the inherited value of the colour
preference sits at about +3.0 in every treatment, including the ones where the
rule reverses repeatedly. It is where it started. Selection did not shift it in
either direction, which is what you would expect when the adaptive value of a
trait alternates unpredictably: no fixed value is favoured, so there is no
gradient to climb.

The phenotype tells the other half. In the control where plasticity is disabled,
end of life preference equals the genome exactly. In the stationary world,
learning pushes the preference further in the direction the genome already
pointed, from +3.0 to +5.6, so it reinforces rather than replaces. In the world
where the rule reverses about once per lifetime, the end of life preference sits
at -4.9 while the genome is still at +3.0. The population carries an innate
preference for one colour and a learned preference for the other, and the learned
one is the one that matches today's rule.

The cost side is severe and is the main reason I am not claiming a confirmation
of the hypothesis I preregistered. Thirty two of forty populations in that
treatment went extinct, almost all of them at the first reversal rather than
gradually. The energy arithmetic is simple enough to be worth stating: a toxic
bite costs about five units out of a hundred unit reserve, each bite shifts the
preference by about a tenth, and reversing a preference of +3 takes around sixty
bites. A naive individual starves or poisons itself before it can relearn. Only
populations that already carried faster learners in the tail of their variation
made it through, which is standing variation doing the work in a single
generation.

The ablation is the one part that passed its declared criterion. In the same
worlds with lifetime adjustment disabled, all forty replicates went extinct,
against thirty two of forty with it. Exact McNemar on the eight discordant pairs
gives p = 0.0078.

Preregistration, raw data and a full report with limitations:
https://minimir.ilinmaks.com/results-b.html

### Перевод на русский

Это результат симуляции искусственной жизни, а не организма, так что принимайте
его как модельный результат, а не как свидетельство о какой-либо реальной линии.
Мне кажется, механизм достаточно чистый, чтобы его стоило описать.

Конструкция ставит популяции задачу, у которой нет наследуемого решения. Еда
двух цветов, один питателен, другой токсичен, и роли переворачиваются в случайно
выбранные моменты. Функции приспособленности в симуляции нет, есть только еда,
энергия, размножение и смерть, поэтому отбор действует исключительно через
разницу в размножении. У агентов есть одна пластичная связь, предпочтение к
цвету, которую они могут подстраивать при жизни. Скорость подстройки сама
является наследуемым геном, а приобретённые изменения не наследуются: потомство
стартует от родительского генома, а не от обученного состояния родителя.

После 100 тысяч тиков на 40 независимых репликах наследуемое значение
предпочтения цвета стоит около +3,0 во всех условиях, включая те, где правило
переворачивается многократно. То есть там, где начинало. Отбор не сдвинул его ни
в одну сторону, чего и следует ожидать, когда адаптивная ценность признака
непредсказуемо чередуется: никакое фиксированное значение не предпочитается,
значит и градиента, по которому карабкаться, нет.

Фенотип рассказывает вторую половину. В контроле с отключённой пластичностью
предпочтение в конце жизни в точности равно геному. В стационарном мире обучение
двигает предпочтение дальше в ту сторону, куда геном уже указывал, с +3,0 до
+5,6, то есть усиливает, а не заменяет. В мире, где правило переворачивается
примерно раз за жизнь, предпочтение в конце жизни стоит на -4,9, тогда как геном
по-прежнему на +3,0. Популяция несёт врождённое предпочтение к одному цвету и
выученное к другому, и выученное это как раз то, которое соответствует
сегодняшнему правилу.

Сторона издержек тяжёлая, и это главная причина, по которой я не заявляю
подтверждения предрегистрированной гипотезы. Тридцать две популяции из сорока в
этом условии вымерли, почти все на первом перевороте, а не постепенно.
Энергетическая арифметика достаточно проста, чтобы её назвать: токсичный укус
стоит около пяти единиц при запасе в сто, каждый укус сдвигает предпочтение
примерно на одну десятую, а обращение предпочтения +3 требует порядка шестидесяти
укусов. Наивная особь гибнет от яда раньше, чем успевает переучиться. Прошли
только те популяции, которые уже несли в хвосте изменчивости более быстро
обучающихся, и это стоячая изменчивость, сработавшая за одно поколение.

Абляция это единственная часть, прошедшая свой объявленный критерий. В тех же
мирах с отключённой прижизненной подстройкой вымерли все сорок реплик, против
тридцати двух из сорока с подстройкой. Точный тест Макнемара на восьми
расходящихся парах даёт p = 0,0078.
