# Medium (и Habr для русской версии)

Заголовок, подзаголовок и текст. Теги для Medium: Artificial Life, Evolution,
Machine Learning, Research, Open Science. Для Habr: искусственная жизнь,
эволюция, научный метод, предрегистрация.

Ссылка в тексте одна, на страницу результатов:
https://minimir.ilinmaks.com/results-b.html
Код и данные: https://github.com/akela1308/minimir

---

## Русская версия

### Восемьдесят процентов наших миров погибли на первой же смене правила. Это и есть результат

*Отчёт о закрытом эксперименте, в котором отрицательный исход был объявлен
заранее, а самым чистым числом оказалось сорок из сорока*

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
в решение «есть или не есть» и зависит от цвета того, что под ногами. Он
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

Шесть условий на одних и тех же семенах и от одного предка: правило не меняется
никогда, меняется раз в пять тысяч тиков, раз в шестьсот (это примерно одна
жизнь), раз в сто пятьдесят, плюс два контроля с отключённым обучением. Сорок
семян, сто тысяч тиков на прогон, 240 прогонов, всё считалось автоматически на
серверах GitHub с 10 по 29 сентября. Критерии и границы провала были заморожены
до первого прогона.

### Что случилось

В условии, ради которого всё ставилось, вымерли тридцать два мира из сорока.
Восемьдесят процентов при объявленном пороге в пятьдесят. Параграф 7.3
предрегистрации на этот случай говорит прямо: сравнение недействительно,
протокол заменяется новым.

Интересно не то, сколько погибло, а когда. Медианное число переворотов правила,
которое популяция переживает до гибели, равно единице. И там, где правило
меняется раз в шестьсот тиков, и там, где раз в пять тысяч. Миры не стираются
постепенно от накопленных переключений, они гибнут на первом же.

Арифметику стоило посчитать до прогонов, а не после. Ядовитый укус отнимает
около пяти единиц энергии, держать существо может сто. Один укус сдвигает вкус
примерно на одну десятую. Значит, переехать от врождённого вкуса плюс три через
ноль к устойчивому минус три стоит порядка шестидесяти отравлений, то есть
трёхсот единиц энергии при запасе в сто. Существо со стартовой скоростью
обучения физически не может переучиться. Оно умирает от яда раньше, чем меняет
знак собственного предпочтения.

### Самое чистое число в проекте

И вот на этом фоне абляция дала результат, которого я, честно говоря, не ожидал.

Тот же мир, те же семена, тот же предок, разница только в том, применяется ли
прижизненное обучение. Без обучения не выжил ни один мир из сорока. С обучением
выжило восемь. Восемь расходящихся пар, все в одну сторону, ноль в обратную,
точный тест Макнемара p = 0,0078.

Это единственная из четырёх зарегистрированных гипотез, прошедшая свой критерий
без оговорок. И она же единственное, что позволяет читать дальнейший рост гена
скорости обучения как адаптацию, а не как попутчика отбора. Условие, кстати, было
добавлено в главный критерий поправкой за несколько часов до первого прогона.
Сработала именно оно.

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
меняется раз в жизнь, фенотип ушёл в минус пять, при врождённом плюс три.

Геном не может записать правило. Прижизненное обучение его записывает. Ровно это
разделение протокол и был построен показать, и это единственное место, где
результат выглядит как картинка, а не как p-значение.

У выживших, к слову, видно и то, за счёт чего они выжили. Численность перед
катастрофой у них такая же, как у погибших. Отличается скорость обучения: медиана
0,120 против 0,103, p = 0,023 по одностороннему тесту Манна-Уитни. Отбор работал
на стоячей изменчивости, пережили те популяции, в хвосте которых уже были
достаточно быстро обучающиеся особи. После горлышка скорость обучения выросла
примерно в тридцать раз за несколько сотен тиков и девяносто тысяч тиков
держалась у верхней границы допустимого диапазона.

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
свойством стационарной среды. Дешёвое обучение переживает собственную
ненужность. Для тех, кто занимается непрерывным обучением в машинном обучении,
это звучит знакомо: пластичность сама по себе не проблема, проблема в том, сколько
она стоит системе, которая ею пользуется.

### Ошибка, про которую проще было бы промолчать

Второй критерий требовал, чтобы разница медиан логарифма скорости обучения
превышала два сигма разброса того же гена там, где он ни на что не влияет.
Замысел был правильный: нужна точка отсчёта, показывающая, что делает ген, когда
не делает ничего.

Беда в том, что ген мутирует множителем. Без отбора это случайное блуждание по
логарифмической шкале, а дисперсия случайного блуждания растёт со временем. На
двухтысячном тике порог соответствовал разнице в один раз. На двадцатитысячном в
десять. На стотысячном в шестьдесят один. Измеренный эффект составил
четырнадцать с половиной.

То есть я объявил планку, которая тем выше, чем дольше идёт эксперимент. Она
измеряет не силу эффекта, а длину прогона. Если бы длина прогона была объявлена в
двадцать тысяч тиков, тот же самый эффект критерий бы прошёл. Двигать порог
задним числом я не буду, потому что критерий, придуманный после взгляда на данные,
уже не критерий. В следующей версии он сравнивается с дрейфом на том же тике, или
работает с распределением парных разниц, или ген ограничен так, что нейтральное
блуждание не расползается. Это решается до прогонов.

### Зачем вообще публиковать такое

Можно было подкрутить ядовитость, перезапустить и опубликовать красивое
подтверждение. Технически это две строки в конфиге и ночь счёта. Проблема в том,
что результат, полученный после подкрутки под данные, ничего не стоит, а выглядит
точно так же, как результат, полученный честно. Отличить снаружи невозможно,
поэтому единственная защита это заранее объявленные критерии и готовность
опубликовать провал.

Так что протокол B1 закрыт. Восемь из сорока выживших дали очень чистую картину, и
именно поэтому новый протокол нужен: мир должен переживать первую смену правила,
иначе мы измеряем не эволюцию обучения, а узость горлышка. Самое прямое решение
это сделать переворот постепенным, за несколько десятков тиков, чтобы у популяции
было окно, в котором оба цвета слабо питательны. И стартовую скорость обучения
надо засевать распределением, а не одним числом, тогда стоячая изменчивость будет
заявленной, а не случайной.

Все таблицы, оговорки и вывод простым языком лежат на странице результатов, код и
сырые данные в репозитории.

---

## Английская версия

### Eighty percent of our worlds died at the first rule change. That is the result

*A report on a closed experiment where the negative outcome was declared in
advance, and the cleanest number turned out to be forty out of forty*

Half a year ago I set myself a frame that now regularly ruins my mood: criteria
are declared before the runs, and the verdict is not rewritten afterwards. In
september that frame fired for the second time, and it fired hard.

Let me start with the construction, because without it the numbers mean nothing.

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
of my july pilot by accident, while I was trying to get something else entirely.
The first half is what I wanted to test.

Six conditions on identical seeds from a single ancestor: the rule never
changes, changes every five thousand ticks, every six hundred (about one
lifetime), every hundred and fifty, plus two controls with learning switched
off. Forty seeds, one hundred thousand ticks per run, 240 runs, all computed
automatically on GitHub servers between 10 and 29 september. Criteria and
failure boundaries were frozen before the first run.

### What happened

In the condition the whole thing was built for, thirty two worlds out of forty
went extinct. Eighty percent against a declared threshold of fifty. Section 7.3
of the preregistration says plainly what to do in that case: the comparison is
void and the protocol gets replaced.

What is interesting is not how many died but when. The median number of rule
reversals a population lives through before dying is one. Both where the rule
changes every six hundred ticks and where it changes every five thousand. The
worlds are not worn down by accumulated switching, they die at the first switch.

The arithmetic deserved to be done before the runs rather than after. A
poisonous bite removes about five units of energy, and a creature can hold a
hundred. One bite shifts taste by about a tenth. So moving from an inherited
taste of plus three through zero to a stable minus three costs on the order of
sixty poisonings, which is three hundred units of energy against a reserve of a
hundred. A creature at the starting learning rate cannot physically relearn. It
dies of poison before it changes the sign of its own preference.

### The cleanest number in the project

Against that background the ablation produced a result I honestly had not
expected.

Same world, same seeds, same ancestor, with the only difference being whether
lifetime learning is applied. Without learning, not one world out of forty
survived. With learning, eight survived. Eight discordant pairs, all in one
direction, zero in the other, exact McNemar test p = 0.0078.

This is the only one of the four registered hypotheses that passed its criterion
without reservations. It is also the only thing that lets the later rise of the
learning rate gene be read as an adaptation rather than as a passenger of
selection. The condition, incidentally, was added to the main criterion by an
amendment a few hours before the first run. It is the part that worked.

### Where the knowledge actually sits

Next comes the table because of which I consider this experiment worth running,
even though the main hypothesis did not pass.

The inherited taste, meaning the value in the genome, started at plus three and
stayed near plus three in every condition. Including the ones where the rule
reverses. Evolution did not touch it and could not: the correct sign changes
unpredictably, so no inherited value is worth having.

The phenotype, on the other hand, diverged. Where learning is switched off it is
exactly equal to the genome, which incidentally confirms that the barrier
against inheriting lifetime change is intact. Where the rule never changes,
learning pulled taste up to plus five and a half, reinforcing an already correct
innate preference. And where the rule changes once per lifetime, the phenotype
went to minus five while the genome stayed at plus three.

The genome cannot record the rule. Lifetime learning records it. That separation
is exactly what the protocol was built to show, and it is the one place where
the result looks like a picture rather than a p value.

In the survivors you can also see what they survived by. Their population size
before the catastrophe is the same as in those that died. What differs is the
learning rate: a median of 0.120 against 0.103, p = 0.023 on a one sided
Mann-Whitney test. Selection worked on standing variation. The populations that
made it were the ones that already had fast enough learners in the tail. After
the bottleneck the learning rate grew roughly thirtyfold within a few hundred
ticks and then held near the top of the permitted range for ninety thousand
ticks.

### A third piece of news nobody ordered

In the stationary world learning did not disappear. Although by my own july
pilot it should have: there, with plasticity on, the learning rate fell by half
within fifteen thousand ticks. Here the ratio is 1.38 at p = 0.115, which is
indistinguishable from drift.

The explanation, I think, is the price of the rule. In july a general Hebbian
rule ran across the whole output layer: it moved every weight continuously,
degraded behaviour, and selection actively suppressed it. Here a single
connection learns, with a dead zone, and in an unchanging world it merely
confirms an innate preference. Such learning costs almost nothing, so there is
nothing for selection to push against.

The conclusion is not loud but it is useful: the fall of the learning rate in
the july pilot was the price of one specific expensive plasticity rule, not a
general property of stationary environments. Cheap learning survives its own
uselessness. For anyone working on continual learning in machine learning this
should sound familiar: plasticity by itself is not the problem, the problem is
what it costs the system that uses it.

### The error it would have been easier to keep quiet about

The second criterion required the gap between median log learning rates to
exceed two sigma of the spread of that same gene where it affects nothing. The
intent was right: you need a reference point showing what the gene does when it
does nothing.

The trouble is that the gene mutates multiplicatively. Without selection that is
a random walk on a logarithmic scale, and the variance of a random walk grows
with time. At tick two thousand the threshold corresponded to a onefold
difference. At twenty thousand, tenfold. At one hundred thousand, sixtyonefold.
The measured effect was fourteen and a half.

In other words I declared a bar that rises the longer the experiment runs. It
does not measure the size of an effect, it measures the length of a run. If the
run length had been declared at twenty thousand ticks, that very same effect
would have passed. I will not move the threshold after the fact, because a
criterion invented after looking at the data is no longer a criterion. In the
next version it compares against drift at the same tick, or works with the
distribution of paired differences, or the gene is bounded so the neutral walk
cannot spread. That gets decided before the runs.

### Why publish this at all

I could have tuned the toxicity down, rerun everything and published a pretty
confirmation. Technically that is two lines in a config and one night of
compute. The problem is that a result obtained after tuning to the data is worth
nothing, and it looks exactly like a result obtained honestly. There is no way
to tell them apart from the outside, so the only defence is criteria declared in
advance and a willingness to publish the failure.

So protocol B1 is closed. The eight survivors out of forty gave a very clean
picture, and that is precisely why a new protocol is needed: the world has to be
survivable through the first rule change, otherwise what we measure is not the
evolution of learning but the narrowness of a bottleneck. The most direct fix is
to make the reversal gradual over a few dozen ticks, so the population has a
window in which both colours are weakly nutritious. And the starting learning
rate should be seeded as a distribution rather than a single number, so that
standing variation is declared rather than accidental.

All the tables, the caveats and a plain language summary are on the results
page, with the code and raw data in the repository.
