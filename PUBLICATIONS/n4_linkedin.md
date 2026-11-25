# LinkedIn: результаты протокола N4

Один пост, две версии. Ссылка одна: https://minimir.ilinmaks.com/n4.html

Публиковать ссылкой в первом комментарии, а не в теле поста. Картинка: скриншот
двух графиков со страницы опыта (доля выживших миров по скорости обучения и по
разбросу скоростей), они читаются с телефона.

---

## Русская версия

Третий опыт нашего мини-мира закончен, и впервые за время проекта сбылись
предсказания, которые могли и не сбыться.

Напомню, на чём мы остановились. На сетке живут существа с маленькой нейросетью,
еда бывает двух цветов, один кормит, другой травит. В прошлом опыте цвета время
от времени менялись местами, и тридцать два мира из сорока вымерли на первой же
смене. Вопрос о том, когда выгодно учиться, остался без ответа, потому что
отвечать на него было некому. Поэтому в этот раз мы спросили про то, что идёт
раньше: что нужно популяции, чтобы пережить одну резкую перемену?

Устроено так. Каждый мир доживает до тика перед сменой, потом копируется целиком,
вместе с генератором случайных чисел, и в каждой из двадцати шести копий меняется
ровно одна вещь: скорость обучения у всех особей, разброс этой скорости между
ними или сила яда. История у копий общая до последнего тика, поэтому разницу в
исходе уже нельзя списать на удачу основателей. Правила, по которым будем судить,
мы выложили на GitHub до счёта, и только потом посчитали 150 новых миров.

Если все особи учатся одинаково медленно, не выживает ни один мир из 150. Если
скорости разбросаны вокруг той же медианы, выживает 134. Мир вытягивают несколько
быстрых учеников, причём одного-двух для этого мало, нужно порядка десяти и
больше, а в конце мир заселён потомками одной или двух таких особей.

Второе предсказание шло против классической теории эволюционного спасения, по
которой мягкую перемену переживают чаще. У нас вышло наоборот: при мягком яде
спаслось 44% миров против 58% при обычном. Объяснение записано до прогона. В этом
мире яд заодно и учит, сдвиг вкуса пропорционален энергии, потерянной от укуса, а
большинство укусов маленькие, потому что клетки под существами уже объедены. На
таких укусах слабый яд учит вдвое медленнее или не учит совсем, и существа дольше
едят не то.

Третья гипотеза осталась не определена. Мы ждали, что у каждого мира свой порог
скорости, и по числам на это похоже: в 147 мирах из 150 ответ выглядит
ступенькой, и ступеньки стоят в разных местах. Но планку мы заранее провели на
90%, а верхняя граница интервала вышла 90,7%. Двигать планку после счёта не
стали.

До заморозки каждое правило прогнали на искусственных данных двух сортов, с
эффектом и без него, чтобы убедиться, что оно может и пройти, и провалиться. В
прошлых протоколах мы четыре раза объявляли критерий, который пройти не мог ни
при каком исходе, оттуда эта проверка и взялась.

Теперь оговорки. Это один мир с одним правилом обучения, и пороги на другие миры
не переносятся. Сторону предсказания про яд мы выбрали по пилоту на тридцати
мирах, а проверяли уже на новых ста пятидесяти. И разделить вред яда и его урок
этот опыт не может, для этого нужен следующий.

Графики, отчёт, предрегистрация и код по ссылке в первом комментарии.

---

## Английская версия

The third experiment in our mini-world is finished, and for the first time in
this project the predictions that came true were ones that could have failed.

A reminder of where we stopped. Creatures with a small neural network live on a
grid, and food comes in two colours, one that feeds them and one that poisons
them. In the previous experiment the colours swapped roles from time to time,
and thirty-two worlds out of forty died at the very first swap. The question of
when learning pays went unanswered because nobody was left alive to answer it.
So this time we asked about what comes before: what does a population need in
order to live through one abrupt change?

The setup is this. Each world runs up to the tick before the change, then it is
copied whole, random number generator included, and in each of twenty-six copies
exactly one thing is changed: the learning rate of all individuals, how much
that rate varies between them, or the strength of the poison. The copies share
their history up to the last tick, so a difference in outcome can no longer be
put down to the luck of the founders. We published the rules for judging on
GitHub before the run, and only then computed 150 new worlds.

When every individual learns equally slowly, none of the 150 worlds survives.
When the rates are spread around that same median, 134 survive. A few fast
learners carry the world, and one or two of them are not enough, it takes about
ten or more; by the end the world is populated by the descendants of one or two
of them.

The second prediction ran against classical evolutionary rescue theory, which
expects a milder change to be survived more often. We got the reverse: with mild
poison 44% of worlds were rescued, against 58% with the regular one. The
explanation was written down before the run. In this world poison also teaches,
the shift in taste is proportional to the energy lost on the bite, and most
bites are small because the cells under the creatures are already half eaten. On
those bites a weak poison teaches half as fast or not at all, and the creatures
go on eating the wrong thing for longer.

The third hypothesis stayed undetermined. We expected each world to have its own
threshold rate, and the numbers look that way: in 147 worlds out of 150 the
response is a step, and the steps sit in different places. But we had drawn the
bar at 90% in advance, and the upper bound of the interval came out at 90.7%. We
did not move the bar after the count.

Before freezing, every rule was run on two kinds of artificial data, with an
effect and without one, to make sure it could both pass and fail. In earlier
protocols we declared, four times, a criterion that could not pass under any
outcome, and that is where this check comes from.

Now the caveats. This is one world with one learning rule, and the thresholds do
not carry over to other worlds. We chose the direction of the poison prediction
from a pilot on thirty worlds and tested it on a new hundred and fifty. And this
experiment cannot separate the harm of the poison from its lesson; that takes
the next one.

Charts, report, preregistration and code are in the link in the first comment.

---

## Короткий вариант на 600 знаков

RU: Закончили третий опыт мини-мира, с правилами, выложенными до счёта. Если все
существа учатся одинаково медленно, одну резкую смену еды не переживает ни один
мир из 150. Если скорости обучения разбросаны вокруг той же медианы, выживает
134, их вытягивает десяток быстрых учеников. Мягкий яд оказался хуже обычного,
44% миров против 58%, вопреки классической теории: слабый яд хуже учит. Третья
гипотеза не определена, планку после счёта не двигали. Графики и код по ссылке.

EN: We finished the third mini-world experiment, with the rules published before
the run. When every creature learns equally slowly, not one world out of 150
lives through a single abrupt food change. When learning rates are spread around
the same median, 134 survive, carried by a dozen or so fast learners. Mild
poison turned out worse than regular, 44% of worlds against 58%, contrary to
classical theory: a weak poison teaches worse. The third hypothesis is
undetermined, and we did not move the bar after the count. Charts and code in
the link.
