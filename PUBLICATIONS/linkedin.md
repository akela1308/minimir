# LinkedIn

Один пост, две версии. Ссылка в конце одна: https://minimir.ilinmaks.com/results-b.html

Публиковать лучше ссылкой в первом комментарии, а не в теле поста, LinkedIn
занижает охват постам с внешними ссылками. Картинка: скриншот таблицы
выживаемости со страницы результатов, она читается с телефона.

---

## Русская версия

Второй эксперимент нашего мини-мира закрыт, и закрыт отрицательным результатом,
который мы сами себе объявили заранее.

Коротко, о чём речь. На сетке живут существа с маленькой нейросетью. Еда бывает
двух цветов, один цвет питателен, другой ядовит, и время от времени они меняются
ролями в случайные моменты. Родиться со знанием правильного цвета невозможно,
его можно только выучить при жизни. Вопрос был простой: включит ли отбор
способность учиться там, где мир меняет правила? Это предсказание из работы
Kozielska и Weissing в PLoS Computational Biology за 2024 год, и мы хотели
проверить его в своём мире.

240 прогонов, сорок семян, шесть условий, по сто тысяч тиков каждый. Что
получилось.

Восемьдесят процентов популяций погибли на первом же перевороте правила. По
нашей предрегистрации это граница провала: сравнение, ради которого всё
ставилось, недействительно, протокол заменяется, а не подкручивается до красивых
чисел.

В той же серии подтвердилось то, что мы сами заложили в конструкцию мира. Тот же
мир, те же семена, тот же предок, только прижизненное обучение отключено:
вымерли все сорок из сорока. С обучением выжило восемь. Точный тест Макнемара
даёт p = 0,0078, и это наименьшее значение, какое вообще бывает при восьми
парах. Без способности учиться этот мир не переживается, но мы сами его таким
построили: замороженный вкус после смены правила смертелен сам по себе. А
выжившие восемь миров, как показало прослеживание родословных, происходят от
одной-четырёх особей, которые к моменту смены случайно оказались в верхнем
хвосте разброса гена скорости обучения. Везение хвоста; в биологии это называют
эволюционным спасением за счёт стоячей изменчивости.

В этих восьми мирах есть ещё одно наблюдение, для которого не нужен тест.
Врождённый вкус у выживших не изменился совсем, остался тем же, с которым
начинали. А выученный при жизни ходил вслед за правилом: в шести мирах из
восьми на последнем тике он стоял с обратным знаком, в двух правило к тому
моменту вернулось, и вкус вернулся с ним. Правило дня в генах не хранится,
каждое поколение выучивает его само.

Ещё мы нашли ошибку в собственном критерии. Порог, с которым мы сравнивали
эффект, растёт вместе с длиной прогона, потому что ген скорости обучения мутирует
множителем и без отбора расползается по логарифмической шкале. К стотысячному
тику он требовал разницы в шестьдесят раз. Отношение между условиями к этому
моменту было около четырнадцати, и это число само по себе мало что меряет: у
выживших ген ушёл к потолку своего диапазона, а в стационарном мире он просто
блуждает. Остановили бы прогоны в пять раз раньше, тот же самый результат прошёл
бы. Задним числом правило менять не будем, в следующей версии оно будет другим,
и мы написали, каким.

Часть формулировок первого отчёта оказалась сильнее данных, в том числе из-за
двух пилотных семян, попавших в подтверждающие прогоны. Поправки от 28 октября
лежат рядом с отчётом, это версия v1.0.1.

Полный разбор с таблицами, оговорками и выводом простым языком в конце по ссылке
ниже.

---

## Английская версия

Our second mini-world experiment is closed, and it closed on a negative verdict
that we had declared for ourselves in advance.

What it is about, briefly. Creatures with a small neural network live on a grid.
Food comes in two colours, one nutritious and one poisonous, and from time to
time they swap roles at random moments. Being born knowing the right colour is
impossible, it can only be learned while alive. The question was simple: does
selection switch on the ability to learn in a world that keeps changing its
rules? That is a prediction from Kozielska and Weissing in PLoS Computational
Biology, 2024, and we wanted to test it in our own world.

240 runs, forty seeds, six conditions, one hundred thousand ticks each, and this
is what came out.

Eighty percent of the populations died at the very first reversal of the rule.
By our preregistration that is the failure boundary: the comparison the whole
thing was built for is void, and the protocol gets replaced rather than tuned
until the numbers look good.

The same series also confirmed something we had built into the world ourselves.
Same world, same seeds, same ancestor, with lifetime learning switched off: all
forty out of forty went extinct. With learning, eight survived. The exact McNemar
test gives p = 0.0078, which is the smallest value eight pairs can produce.
Without the ability to learn this world cannot be survived, but we built it that
way: a frozen taste after a reversal is lethal on its own. And the eight
survivors, once we traced their lineages, each descend from one to four
individuals that happened to sit in the upper tail of the spread of the learning
rate gene at the moment of the switch. Luck of the tail; in biology this is
called evolutionary rescue from standing variation.

Those eight worlds hold one more observation, and it needs no test. The
inherited taste in the survivors did not change at all, it stayed what they
started with. The taste learned during life followed the rule: in six of the
eight worlds it stood at the opposite sign on the last tick, in the other two
the rule had swung back by then and the taste had swung with it. The genes carry
no rule of the day; each generation learns it for itself.

We also found an error in our own criterion. The threshold we compared the
effect against grows with the length of the run, because the learning rate gene
mutates multiplicatively and without selection it spreads out on a logarithmic
scale. By tick one hundred thousand it demanded a sixtyfold difference. The
ratio between conditions at that point was about fourteen, and that number by
itself measures little: in the survivors the gene had gone to the ceiling of its
range, while in the stationary world it simply wanders. Had we stopped the runs
five times earlier, that very same result would have passed. We will not move
the rule after the fact. The next version has a different one, and we have
written down which.

Some statements in the first report were stronger than the data, partly because
two pilot seeds ended up among the confirmatory runs. The corrections of 28
October sit next to the report as version v1.0.1.

The full breakdown with tables, caveats and a plain language summary at the end
is in the link below.

---

## Короткий вариант, если нужен пост на 600 знаков

RU: Закрыли второй эксперимент мини-мира. Восемьдесят процентов популяций
погибли на первой же смене пищевого правила, и по нашей предрегистрации это
граница провала: главное сравнение недействительно. Абляция сработала, как и
было заложено: без прижизненного обучения вымерли все сорок миров из сорока, с
обучением выжило восемь, p = 0,0078. У выживших врождённый вкус не сдвинулся, а
выученный ходил вслед за правилом. Разбор целиком, включая нашу собственную
ошибку в критерии и поправки от 28 октября, по ссылке.

EN: We closed the second mini-world experiment. Eighty percent of the
populations died at the first change of the food rule, and by our own
preregistration that is a failure boundary: the main comparison is void. The
ablation held, as the design required: without lifetime learning all forty
worlds out of forty went extinct, with learning eight survived, p = 0.0078. In
the survivors the inherited taste did not budge while the learned one followed
the rule. The full breakdown, including an error of our own in the criterion
and the corrections of 28 October, is in the link.
