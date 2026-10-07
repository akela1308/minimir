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

Но в той же серии получился самый чистый результат за всё время проекта. Тот же
мир, те же семена, тот же предок, только прижизненное обучение отключено:
вымерли все сорок из сорока. С обучением выжило восемь. Точный тест Макнемара
даёт p = 0,0078. Без способности учиться этот мир не переживается вообще.

И отдельно то, что мне нравится больше всего. У выживших врождённый вкус не
изменился совсем, остался тем же, с которым начинали. А выученный при жизни
развернулся в противоположный знак. Наследственность хранит устройство существа,
а знание о том, что съедобно сегодня, живёт только внутри одной жизни и каждым
поколением добывается заново.

Ещё мы нашли ошибку в собственном критерии. Порог, с которым мы сравнивали
эффект, растёт вместе с длиной прогона, потому что ген скорости обучения мутирует
множителем и без отбора расползается по логарифмической шкале. К стотысячному
тику он требовал шестидесятикратной разницы, а эффект был в четырнадцать раз.
Остановили бы прогоны в пять раз раньше, тот же самый результат прошёл бы.
Задним числом правило менять не будем, в следующей версии оно будет другим, и мы
написали, каким.

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

240 runs, forty seeds, six conditions, one hundred thousand ticks each. Here is
what came out.

Eighty percent of the populations died at the very first reversal of the rule.
By our preregistration that is the failure boundary: the comparison the whole
thing was built for is void, and the protocol gets replaced rather than tuned
until the numbers look good.

And yet the same series produced the cleanest result in the project so far. Same
world, same seeds, same ancestor, with lifetime learning switched off: all forty
out of forty went extinct. With learning, eight survived. The exact McNemar test
gives p = 0.0078. Without the ability to learn, this world is not survivable at
all.

Then the part I like most. In the survivors the inherited taste did not change
at all, it stayed what they started with. The taste learned during life flipped
to the opposite sign. Heredity holds the design of the creature, while knowledge
about what is edible today lives only inside one life and is earned again by
every generation.

We also found an error in our own criterion. The threshold we compared the
effect against grows with the length of the run, because the learning rate gene
mutates multiplicatively and without selection it spreads out on a logarithmic
scale. By tick one hundred thousand it demanded a sixtyfold difference, and the
effect was fourteenfold. Had we stopped the runs five times earlier, that very
same result would have passed. We will not move the rule after the fact. The
next version has a different one, and we have written down which.

The full breakdown with tables, caveats and a plain language summary at the end
is in the link below.

---

## Короткий вариант, если нужен пост на 600 знаков

RU: Закрыли второй эксперимент мини-мира. Восемьдесят процентов популяций
погибли на первой же смене пищевого правила, и по нашей предрегистрации это
граница провала, а не результат. Зато абляция вышла идеальной: без прижизненного
обучения вымерли все сорок миров из сорока, с обучением выжило восемь, p =
0,0078. У выживших врождённый вкус не сдвинулся, а выученный развернулся в
минус. Наследственность хранит устройство, знание о сегодняшнем дне живёт внутри
одной жизни. Разбор целиком, включая нашу собственную ошибку в критерии, по
ссылке.

EN: We closed the second mini-world experiment. Eighty percent of the
populations died at the first change of the food rule, and by our own
preregistration that is a failure boundary, not a result. The ablation, though,
came out perfect: without lifetime learning all forty worlds out of forty went
extinct, with learning eight survived, p = 0.0078. In the survivors the
inherited taste did not budge while the learned one flipped negative. Heredity
holds the design, knowledge about today lives inside a single life. The full
breakdown, including an error of our own in the criterion, is in the link.
