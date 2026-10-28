# Medium (и Habr для русской версии)

Заголовок, подзаголовок и текст. Теги для Medium: Artificial Life, Evolution,
Machine Learning, Research, Open Science. Для Habr: искусственная жизнь,
эволюция, научный метод, предрегистрация.

Ссылка в тексте одна, на страницу результатов:
https://minimir.ilinmaks.com/results-b.html
Код и данные: https://github.com/akela1308/minimir

---

## Русская версия

### Восемьдесят процентов наших миров погибли на первой же смене правила. Мы заранее записали, что это будет значить

*Отчёт о закрытом эксперименте, в котором отрицательный исход был объявлен
заранее, а число сорок из сорока оказалось заложено в саму конструкцию мира*

Полгода назад я поставил себе рамку, которая теперь регулярно портит мне
настроение: критерии объявляются до прогонов, и вердикт после них не
переписывается. В сентябре эта рамка сработала второй раз, и сработала жёстко.

Начну с конструкции, потому что без неё числа ничего не значат.

На сетке живут существа с маленькой нейросетью. Еда, энергия, размножение,
смерть. Никакой функции приспособленности нет: отбор идёт только через разницу в
числе потомков, никто никому не выставляет оценку. Еда бывает двух цветов. В
каждый момент один цвет питателен, а другой ядовит, и роли переворачиваются в
моменты, которые тянет отдельный генератор. Моменты непредсказуемы, поэтому
никакое наследуемое предпочтение не может быть верным долго. Правильный цвет
можно только выучить при жизни.

Учится при этом один синапс. Я называю его вкусом: это прибавка, которая входит
в решение, есть или не есть, и зависит от цвета того, что под ногами. Он
наследуется как обычный вес, а при жизни меняется трёхфакторным правилом: что
съел, что получил, с какой скоростью. Сама скорость это ген, и она мутирует
множителем, так что отбор может поднять или опустить способность учиться, не
трогая больше ничего. Прижизненные изменения не наследуются: ребёнок получает
мутированный геном родителя, а не обученные веса.

Вопрос был взят не с потолка. Kozielska и Weissing в PLoS Computational Biology
за 2024 год предсказывают, что прижизненное обучение отбирается только там, где
среда меняется быстрее, чем сменяются поколения, и давится там, где среда
стационарна. Второе плечо у меня в июльском пилоте получилось случайно, когда я
пытался добиться совсем другого. Первое я и хотел проверить.

Шесть условий на одних и тех же семенах, у каждого семени свой предок, общий
для всех шести условий: правило не меняется никогда, меняется раз в пять тысяч
тиков, раз в шестьсот (это примерно одна жизнь), раз в сто пятьдесят, плюс два
контроля с отключённым обучением. Сорок семян, сто тысяч тиков на прогон, 240
прогонов, всё считалось автоматически на серверах GitHub с 10 по 29 сентября.
Критерии и границы провала были заморожены до первого прогона.

### Что случилось

В условии, ради которого всё ставилось, вымерли тридцать два мира из сорока.
Восемьдесят процентов при объявленном пороге в пятьдесят. Параграф 7.3
предрегистрации на этот случай говорит прямо: сравнение недействительно,
протокол заменяется новым.

Гибли миры не от накопленных переключений. Медианное число переворотов правила,
которое популяция переживает до гибели, равно единице, и там, где правило
меняется раз в шестьсот тиков, и там, где раз в пять тысяч: почти все погибают
на первом же. Сравнить частоты смен между собой на этих данных было нельзя с
самого начала, и это я понял только в октябре: до первой смены три условия со
сменой правила идут по одной и той же траектории, а расписание смен у них
общее, просто растянутое на разную длину. Выживают поэтому одни и те же семена.

Арифметику стоило посчитать до прогонов, а не после. Ядовитый укус отнимает
около пяти единиц энергии, держать существо может сто. Один укус сдвигает вкус
примерно на одну десятую. Значит, переехать от врождённого вкуса плюс три через
ноль к устойчивому минус три стоит порядка шестидесяти отравлений, то есть
трёхсот единиц энергии при запасе в сто (на деле к моменту смены обучение уже
дотянуло вкус до пяти с лишним, так что путь ещё длиннее). Существо со стартовой
скоростью обучения физически не может переучиться. Оно умирает от яда раньше,
чем меняет знак собственного предпочтения.

Есть и обратный случай. Там, где правило меняется раз в сто пятьдесят тиков,
один мир из сорока пережил 632 переворота, не учась вообще: скорость обучения
у него упала почти до нуля, а врождённый вкус остался. Когда правило меняется
чаще, чем существо успевает переучиться, фиксированный вкус прав половину
времени, а еда даёт вдвое больше, чем отнимает яд. Так что без обучения не
выжить при смене раз в жизнь, и дальше этого утверждение не идёт.

### Число, которое было заложено в конструкцию

И вот на этом фоне абляция дала результат, который в октябре, после аудита, я
читаю иначе, чем в день написания отчёта.

Тот же мир, те же семена, тот же предок, разница только в том, применяется ли
прижизненное обучение. Без обучения не выжил ни один мир из сорока. С обучением
выжило восемь. Восемь расходящихся пар, все в одну сторону, ноль в обратную,
точный тест Макнемара p = 0,0078.

Это единственная из четырёх зарегистрированных гипотез, прошедшая свой критерий.
Но оговорка есть, и серьёзная. Существо с замороженным вкусом плюс три после
смены правила теряет около пяти единиц энергии на каждом укусе привычного цвета
и не успевает ничего унаследовать за те триста пятьдесят тиков, что остаются до
гибели. Исход абляции был предопределён тем, как мы построили мир, и пилот это
уже показывал. А p = 0,0078 это наименьшее значение, какое вообще бывает при
восьми парах. Вторая оговорка уже против нашей собственной предрегистрации:
раннер начал с первого семени, и два пилотных семени попали в подтверждающие
данные, оба среди выживших. Без них выжило шесть из тридцати восьми, p = 0,031.
Так что рост гена скорости после смены я больше не могу читать как адаптацию,
которую абляция отделила от простого сцепления с теми, кто выжил: прослеживание
родословных показало ровно сцепление, об этом ниже. Условие, кстати, было
добавлено в главный критерий поправкой за несколько часов до первого прогона.

### Где на самом деле лежит знание

Дальше идёт таблица, из-за которой я считаю этот эксперимент не зря поставленным,
хотя главная гипотеза и не прошла.

Врождённый вкус, то есть значение в геноме, стартовал с плюс трёх и остался около
плюс трёх во всех условиях. Включая те, где правило переворачивается. Эволюция
его не тронула и не могла: правильный знак меняется непредсказуемо, поэтому
никакое врождённое значение не выгодно.

А фенотип разошёлся. Там, где обучение отключено, он в точности равен геному,
что заодно подтверждает исправность барьера против наследования прижизненных
изменений. Там, где правило не меняется, обучение дотянуло вкус до плюс пяти с
половиной, усилив и без того верное врождённое предпочтение. А там, где правило
меняется раз в жизнь, фенотип следует за текущим правилом: медиана по восьми
мирам минус 4,92 при врождённом плюс три, а в двух мирах из восьми на последнем
тике вкус положительный, потому что правило там стояло в другом положении.

Геном во всех условиях остался около плюс трёх, выученный при жизни вкус ходил
за правилом. Ради этого разделения протокол и ставился, и видно его прямо в
таблице, без всякого теста.

У выживших, к слову, видно и то, за счёт чего они выжили. Численность на
4000-м тике, последней точке кривой перед сменой, у них такая же, как у
погибших. Отличается скорость обучения: медиана 0,120 против 0,103, p = 0,023 по
одностороннему тесту Манна-Уитни. Отбор работал на разбросе гена, который уже
был в популяции, и родословные показывают, насколько буквально: каждый
выживший мир происходит от одной-четырёх особей, которые к моменту смены
случайно оказались в верхних процентах этого разброса и которым ещё повезло с
едой. В биологии это называется эволюционным спасением за счёт стоячей
изменчивости (evolutionary rescue from standing variation). После горлышка
скорость обучения за несколько сотен тиков ушла к потолку допустимого диапазона
(ген ограничен сверху четвёркой) и девяносто тысяч тиков там держалась. Рост в
тридцать раз, о котором я писал раньше, это отношение к стартовому 0,1, и
размером эффекта оно не является: числитель упёрся в потолок гена.

### Третья новость, которой не ждали

В стационарном мире обучение не исчезло. Хотя по моему же июльскому пилоту должно
было: там при включённой пластичности скорость обучения падала вдвое за
пятнадцать тысяч тиков. Здесь отношение 1,38 при p = 0,115, то есть неотличимо от
дрейфа.

Объяснение, по-моему, в цене правила. В июле работало общее хеббовское правило на
всём выходном слое: оно непрерывно двигало все веса, портило поведение, и отбор
его активно давил. Здесь учится одна связь с мёртвой зоной, и в неизменном мире
она просто подтверждает врождённое предпочтение. Такое обучение почти ничего не
стоит, и давить отбору не на что.

Вывод получается не громкий, но полезный: падение скорости обучения в июльском
пилоте было платой за конкретное дорогое правило пластичности, а не общим
свойством стационарной среды. Для тех, кто занимается непрерывным обучением в
машинном обучении, это звучит знакомо: пластичность сама по себе не проблема,
проблема в том, сколько она стоит системе, которая ею пользуется.

### Ошибка в нашем собственном критерии

Второй критерий требовал, чтобы разница медиан логарифма скорости обучения
превышала два сигма разброса того же гена там, где он ни на что не влияет.
Замысел был правильный: нужна точка отсчёта, показывающая, что делает ген, когда
не делает ничего.

Беда в том, что ген мутирует множителем. Без отбора это случайное блуждание по
логарифмической шкале, а дисперсия случайного блуждания растёт со временем. На
двухтысячном тике порог соответствовал разнице в один раз. На двадцатитысячном в
десять. На стотысячном в шестьдесят один. Отношение медиан между условиями на
стотысячном тике было четырнадцать с половиной, и даже это число меряет мало
что: числитель стоит на потолке гена, знаменатель блуждает, и в зависимости от
тика отношение гуляет от десяти до тридцати шести.

То есть я объявил планку, которая тем выше, чем дольше идёт эксперимент, и
сравнивать с ней эффект на фиксированном тике нельзя. Если бы длина прогона
была объявлена в двадцать тысяч тиков, тот же самый результат критерий бы прошёл.
Двигать порог задним числом я не буду: планка, подобранная после взгляда на
данные, уже ничего не проверяет. В следующей версии критерий сравнивается с
дрейфом на том же тике, или работает с распределением парных разниц, или ген
ограничен так, что нейтральное блуждание не расползается. Это решается до
прогонов.

### Зачем вообще публиковать такое

Можно было подкрутить ядовитость, перезапустить и опубликовать красивое
подтверждение. Технически это две строки в конфиге и ночь счёта. Проблема в том,
что результат, подогнанный под данные, ничего не стоит, а выглядит точно так же,
как результат без подгонки. Снаружи их не отличить, поэтому критерии объявлены
заранее, а провал опубликован.

Так что протокол B1 закрыт. Восемь из сорока выживших дали ясную картину, и
именно поэтому новый протокол нужен: мир должен переживать первую смену правила,
иначе мы измеряем не эволюцию обучения, а узость горлышка. Самое прямое решение
это сделать переворот постепенным, за несколько десятков тиков, чтобы у популяции
было окно, в котором оба цвета слабо питательны. И стартовую скорость обучения
надо засевать распределением, а не одним числом, тогда разброс гена будет
заявлен заранее, а не получен случайно.

Все таблицы, оговорки и вывод простым языком лежат на странице результатов, код и
сырые данные в репозитории.

---

## Английская версия

### Eighty percent of our worlds died at the first rule change. We had written down in advance what that would mean

*A report on a closed experiment where the negative outcome was declared in
advance, and the number forty out of forty turned out to be built into the world itself*

Half a year ago I set myself a frame that now regularly ruins my mood: criteria
are declared before the runs, and the verdict is not rewritten afterwards. In
September that frame fired for the second time, and it fired hard.

I will start with the construction, because without it the numbers mean nothing.

Creatures with a small neural network live on a grid. Food, energy,
reproduction, death. There is no fitness function: selection runs only through
differences in the number of offspring, and nobody hands out a score. Food comes
in two colours. At any moment one colour is nutritious and the other is poison,
and the roles reverse at moments drawn by a separate generator. The moments are
unpredictable, so no inherited preference can be right for long. The correct
colour can only be learned while alive.

What learns is a single synapse. I call it taste: an addition that enters the
decision to eat or not to eat and depends on the colour of whatever is underfoot.
It is inherited like any other weight, and during life it changes by a three
factor rule: what was eaten, what it gave, at what rate. The rate itself is a
gene, and it mutates multiplicatively, so selection can raise or lower the
capacity to learn without touching anything else. Lifetime changes are not
inherited: the child gets the mutated genome of the parent, not the trained
weights.

The question was not pulled out of thin air. Kozielska and Weissing, in PLoS
Computational Biology 2024, predict that lifetime learning is selected for only
where the environment changes faster than generations turn over, and is
suppressed where the environment is stationary. The second half of that came out
of my July pilot by accident, while I was trying to get something else entirely.
The first half is what I wanted to test.

Six conditions on identical seeds, each seed with its own ancestor shared by all
six conditions: the rule never changes, changes every five thousand ticks, every
six hundred (about one lifetime), every hundred and fifty, plus two controls with
learning switched off. Forty seeds, one hundred thousand ticks per run, 240
runs, all computed automatically on GitHub servers between 10 and 29 September.
Criteria and failure boundaries were frozen before the first run.

### What happened

In the condition the whole thing was built for, thirty two worlds out of forty
went extinct. Eighty percent against a declared threshold of fifty. Section 7.3
of the preregistration says plainly what to do in that case: the comparison is
void and the protocol gets replaced.

The worlds were not worn down by accumulated switching. The median number of
rule reversals a population lives through before dying is one, both where the
rule changes every six hundred ticks and where it changes every five thousand:
almost all of them die at the first switch. Comparing switching frequencies on
these data was never possible, and I only understood that in October: until the
first switch the three switching conditions follow the same trajectory, and
their schedules are one random draw stretched to different lengths. So the same
seeds survive in all three.

The arithmetic deserved to be done before the runs rather than after. A
poisonous bite removes about five units of energy, and a creature can hold a
hundred. One bite shifts taste by about a tenth. So moving from an inherited
taste of plus three through zero to a stable minus three costs on the order of
sixty poisonings, which is three hundred units of energy against a reserve of a
hundred (by the time of the switch learning had already pulled the taste past
five, so the road is longer still). A creature at the starting learning rate
cannot physically relearn. It dies of poison before it changes the sign of its
own preference.

There is an opposite case too. Where the rule changes every hundred and fifty
ticks, one world out of forty lived through 632 reversals without learning at
all: its learning rate fell to almost zero and the inherited taste stayed. When
the rule flips faster than a creature can relearn, a fixed taste is right half
the time, and food gives twice what poison takes. So learning was required for
survival at one reversal per lifetime, and that is as far as the claim goes.

### The number the design guaranteed

Against that background the ablation produced a result that I read differently
now, after the October audit, than on the day I wrote the report.

Same world, same seeds, same ancestor, with the only difference being whether
lifetime learning is applied. Without learning, not one world out of forty
survived. With learning, eight survived. Eight discordant pairs, all in one
direction, zero in the other, exact McNemar test p = 0.0078.

This is the only one of the four registered hypotheses that passed its
criterion. There is a serious caveat, though. A creature with a frozen taste of
plus three pays about five units of energy per bite of the familiar colour after
a reversal and cannot inherit anything within the three hundred and fifty ticks
it has left. The outcome of the ablation was decided by how we built the world,
and the pilot had already shown it. And p = 0.0078 is the smallest value eight
pairs can produce. A second caveat goes against our own preregistration: the
runner started at seed 1, so the two pilot seeds ended up in the confirmatory
data, both among the survivors. Without them six of thirty eight survive and
p = 0.031. So I can no longer read the rise of the learning rate gene after the
switch as an adaptation that the ablation separated from plain hitchhiking with
whoever survived: lineage tracing shows exactly the hitchhiking, more on that
below. The condition, incidentally, was added to the main criterion by an
amendment a few hours before the first run.

### Where the knowledge actually sits

Next comes the table that, for me, justifies the whole experiment, even though
the main hypothesis did not pass.

The inherited taste, meaning the value in the genome, started at plus three and
stayed near plus three in every condition. Including the ones where the rule
reverses. Evolution did not touch it and could not: the correct sign changes
unpredictably, so no inherited value is worth having.

The phenotype, on the other hand, diverged. Where learning is switched off it is
exactly equal to the genome, which incidentally confirms that the barrier
against inheriting lifetime change is intact. Where the rule never changes,
learning pulled taste up to plus five and a half, reinforcing an already correct
innate preference. And where the rule changes once per lifetime, the phenotype
tracks the current rule: the median over eight worlds is minus 4.92 while the
genome stayed at plus three, and in two of the eight worlds the taste at the
last tick is positive, because the rule stood the other way there.

The genome stayed near plus three in every condition; the taste learned during
life moved with the rule. That separation is what the protocol was built to
show, and you can see it straight in the table, without a test.

In the survivors you can also see what they survived by. Their population size
at tick 4,000, the last curve point before the switch, is the same as in those
that died. What differs is the learning rate: a median of 0.120 against 0.103,
p = 0.023 on a one sided Mann-Whitney test. Selection worked on the spread of
the gene that was already in the population, and the lineages show how
literally: each surviving world descends from one to four individuals that
happened to sit in the top few percent of that spread at the moment of the
switch and that also got lucky with food. In biology this is called evolutionary
rescue from standing variation. After the bottleneck the learning rate went to
the ceiling of its permitted range within a few hundred ticks (the gene is
capped at four) and held there for ninety thousand ticks. The thirtyfold rise I
wrote about earlier is the ratio to the starting value of 0.1, and it is not an
effect size: the numerator sits at the cap of the gene.

### A third piece of news nobody ordered

In the stationary world learning did not disappear. Although by my own July
pilot it should have: there, with plasticity on, the learning rate fell by half
within fifteen thousand ticks. Here the ratio is 1.38 at p = 0.115, which is
indistinguishable from drift.

The explanation, I think, is the price of the rule. In July a general Hebbian
rule ran across the whole output layer: it moved every weight continuously,
degraded behaviour, and selection actively suppressed it. Here a single
connection learns, with a dead zone, and in an unchanging world it merely
confirms an innate preference. Such learning costs almost nothing, so there is
nothing for selection to push against.

The conclusion is not loud but it is useful: the fall of the learning rate in
the July pilot was the price of one specific expensive plasticity rule, not a
general property of stationary environments. For anyone working on continual
learning in machine learning this should sound familiar: plasticity by itself is
not the problem, the problem is what it costs the system that uses it.

### The error in our own criterion

The second criterion required the gap between median log learning rates to
exceed two sigma of the spread of that same gene where it affects nothing. The
intent was right: you need a reference point showing what the gene does when it
does nothing.

The trouble is that the gene mutates multiplicatively. Without selection that is
a random walk on a logarithmic scale, and the variance of a random walk grows
with time. At tick two thousand the threshold corresponded to a onefold
difference. At twenty thousand, tenfold. At one hundred thousand, sixtyonefold.
The ratio of medians between conditions at tick one hundred thousand was
fourteen and a half, and even that number measures little: the numerator sits at
the cap of the gene, the denominator wanders, and depending on the tick the
ratio moves anywhere from ten to thirty six.

In other words I declared a bar that rises the longer the experiment runs, and
an effect read at a fixed tick cannot be compared against it. If the run length
had been declared at twenty thousand ticks, that very same effect would have
passed. I will not move the threshold after the fact: a bar picked after looking
at the data no longer tests anything. In the next version the criterion compares
against drift at the same tick, or works with the distribution of paired
differences, or the gene is bounded so the neutral walk cannot spread. That gets
decided before the runs.

### Why publish this at all

I could have tuned the toxicity down, rerun everything and published a pretty
confirmation. Technically that is two lines in a config and one night of
compute. The problem is that a result fitted to the data is worth nothing, and
it looks exactly like a result that was not. From the outside nobody can tell
them apart, so the criteria were declared in advance and the failure is
published.

So protocol B1 is closed. The eight survivors out of forty gave a clear picture,
and that is precisely why a new protocol is needed: the world has to be
survivable through the first rule change, otherwise what we measure is not the
evolution of learning but the narrowness of a bottleneck. The most direct fix is
to make the reversal gradual over a few dozen ticks, so the population has a
window in which both colours are weakly nutritious. And the starting learning
rate should be seeded as a distribution rather than a single number, so that the
spread of the gene is declared in advance rather than left to chance.

All the tables, the caveats and a plain language summary are on the results
page, with the code and raw data in the repository.
