# Medium, Habr, личный блог: результаты протокола N4

Статья, две версии. Ссылка в конце одна: https://minimir.ilinmaks.com/n4.html
Картинки: два графика со страницы опыта (после абзаца про скорость и после
абзаца про разброс).

---

## Русская версия

### Несколько быстрых учеников спасают популяцию, а мягкий яд делает хуже

В сентябре мы закрыли второй эксперимент мини-мира провалом, который сами себе
объявили заранее: тридцать два мира из сорока вымерли на первой же смене правила
еды. Мы хотели узнать, когда отбор включает способность учиться, а узнали только
то, что наш мир первую смену почти не переживает. Спрашивать про выгоду обучения
у вымерших популяций бессмысленно, поэтому третий опыт задаёт вопрос, который
стоит раньше: что нужно популяции, чтобы пережить одну резкую перемену среды?
У биологов для этого есть название, эволюционное спасение, и есть теория, с
которой можно сверяться.

#### Как устроен опыт

Мир тот же. На сетке живут существа с маленькой нейросетью, еда двух цветов,
один цвет кормит, другой травит. У каждого существа есть вкус, одно число,
которое при жизни сдвигается после каждого укуса, и есть ген скорости, с которой
этот вкус сдвигается. На тике 5000 цвета один раз меняются местами.

Новое в том, как сравниваются условия. Раньше мы запускали разные условия от
одного семени и считали их сопоставимыми. Оказалось, что к моменту смены мир
происходит от горстки исходных линий, в пилоте от одной до двадцати восьми, и
всё, что заложено при основании мира, тонет в этой лотерее. Теперь каждый мир
один раз доживает до тика перед сменой, а потом копируется целиком, вместе с
генератором случайных чисел. В каждой из двадцати шести копий меняется ровно одна
вещь: скорость обучения у всех особей, разброс этой скорости между особями, сила
яда. У копий общая карта, общие особи и общий выученный вкус до последнего тика.

Исход простой: жива ли популяция через двенадцать тысяч тиков после смены.

#### Проверка правил до счёта

В проекте накопился неприятный опыт. Четыре раза мы объявляли критерий, который
не мог пройти ни при каком исходе, и дважды ставили контрольный опыт, который не
мог провалиться. Каждый раз причина была арифметической и видна только задним
числом.

Поэтому в этот раз каждое правило сначала прогнали на искусственных данных двух
сортов. Первый сорт это миры пилота, перемешанные с возвращением, где эффект
правдоподобен. Второй сорт это данные, где эффекта нет по построению. Правило
годится, если на первых оно проходит хотя бы в 80% наборов, а на вторых не чаще
чем в 5%. Отсюда же взялось число миров: при 120 одно из предсказаний проходило
в 82% наборов, при 150 в 93%.

Потом правила выложили на GitHub, и только после этого его серверы посчитали 150
новых миров.

#### Что получилось

Сначала проверка прибора. Чем быстрее учатся все особи, тем чаще мир выживает: от
нуля миров при самой медленной скорости до всех 150 при самой быстрой. Это
ожидаемо, и если бы этого не было, остальное не стоило бы читать.

Дальше главное. Если у всех особей одна и та же медленная скорость, не выживает
ни один мир из 150. Если раздать скорости с разбросом вокруг той же медианы, при
самом широком разбросе выживает 134 мира. Типичная особь по-прежнему учится
слишком медленно и сама бы погибла, мир вытягивают те немногие, кому досталась
высокая скорость. Мы посмотрели, сколько их нужно. Одной или двух не хватает ни
разу, при трёх-девяти спасается примерно каждый четвёртый мир, а когда их тридцать и
больше, почти все. К концу прогона выживший мир заселён потомками одной или двух
таких особей.

Потом предсказание, которое мы заранее назвали самым рискованным. Теория эволюционного
спасения говорит, что мягкую перемену переживают чаще, чем тяжёлую. Мы
предсказали обратное и записали почему: в нашем мире яд заодно и учит. Сдвиг
вкуса после укуса пропорционален потерянной энергии, а большинство укусов
маленькие, потому что клетки под существами уже объедены, таких больше четырёх
из пяти. На маленьком укусе слабый яд учит вдвое медленнее обычного или не учит
совсем, и существо продолжает есть ядовитое. На средних скоростях мягкий яд спас
44% миров, обычный 58%.

#### Что не получилось

Третья гипотеза была про то, что у каждого мира свой порог скорости. По числам
так и выглядит: в 147 мирах из 150 ниже какой-то скорости мир гибнет, выше
выживает, и это место у разных миров различается больше чем в десять раз. Но
правило мы записали иначе: при скорости 1,5 должно выживать меньше 90% миров с
учётом погрешности. Выжило 85%, а верхняя граница интервала вышла 90,7%. Правило
даёт вердикт не определено, и мы так и пишем. Подвинуть планку на один пункт после
счёта значило бы сделать ровно то, от чего предрегистрация должна защищать.

#### Чего этот опыт не показывает

Это один мир, одно правило обучения и один пластичный синапс, пороги относятся к
нему и никуда не переносятся. Сторону предсказания про яд мы выбрали по пилоту на
тридцати мирах и сказали об этом в предрегистрации, проверка шла на новых ста
пятидесяти. Разделить две роли яда, вред и урок, этот опыт не может: для этого
нужно условие, где сила урока задаётся отдельно от потери энергии, и это
следующий опыт. Ещё четыре выживших популяции к концу наблюдения почти вымерли;
если считать их погибшими, выводы не меняются.

Отчёт с таблицами, предрегистрация, сырые данные и код лежат на странице опыта:
https://minimir.ilinmaks.com/n4.html

---

## Английская версия

### A few fast learners save the population, and gentler poison makes things worse

In September we closed the second mini-world experiment on a failure we had
declared for ourselves in advance: thirty-two worlds out of forty died at the
first reversal of the food rule. We had wanted to learn when selection switches
on the ability to learn, and all we learned was that our world hardly ever lives
through the first reversal. There is no point asking extinct populations whether
learning pays, so the third experiment asks the question that comes first: what
does a population need in order to live through one abrupt change of its
environment? Biologists have a name for this, evolutionary rescue, and a theory
to check against.

#### How the experiment works

The world is the same. Creatures with a small neural network live on a grid, and
food comes in two colours, one that feeds and one that poisons. Each creature
has a taste, a single number that shifts after every bite during its life, and a
gene for the rate at which that taste shifts. At tick 5,000 the colours swap
once.

What is new is how conditions are compared. We used to start different
conditions from one seed and treat them as comparable. It turned out that by the
time the rule changes a world descends from a handful of the original lineages,
between one and twenty-eight in the pilot, and whatever was set at the founding
drowns in that lottery. Now each world runs once up to the tick before the
change and is then copied whole, random number generator included. In each of
twenty-six copies exactly one thing is changed: the learning rate of all
individuals, how much that rate varies between individuals, the strength of the
poison. The copies share one map, the same individuals and the same learned
taste up to the last tick.

The outcome is simple: is the population alive twelve thousand ticks after the
change.

#### Testing the rules before the run

The project has some unpleasant history here. Four times we declared a criterion
that could not pass under any outcome, and twice we set up a control that could
not fail. Each time the reason was arithmetic and visible only in hindsight.

So this time every rule was first run on two kinds of artificial data. The first
kind is pilot worlds resampled with replacement, where the effect is plausible.
The second is data where the effect is absent by construction. A rule is usable
if it passes on at least 80% of the first kind and on no more than 5% of the
second. The number of worlds came from the same exercise: at 120 one of the
predictions passed in 82% of datasets, at 150 in 93%.

Then the rules went up on GitHub, and only after that did its servers compute
150 new worlds.

#### What came out

First the instrument check. The faster all individuals learn, the more often the
world survives: from no worlds at the slowest rate to all 150 at the fastest.
That was expected, and without it nothing else would be readable.

Then the main result. When every individual has the same slow rate, none of the
150 worlds survives. When rates are handed out with a spread around that same
median, 134 worlds survive at the widest spread. The typical individual still
learns too slowly and would have died; the world is carried by the few that
happened to get a high rate. We looked at how many are needed. One or two were
never enough, with three to nine about one world in four is rescued, and with
thirty or more nearly all are. By the end of the run a surviving world is
populated by the descendants of one or two such individuals.

Then the prediction we had named in advance as the riskiest. Evolutionary rescue theory says a mild
change is survived more often than a severe one. We predicted the opposite and
wrote down why: in our world poison also teaches. The shift in taste after a
bite is proportional to the energy lost, and most bites are small, because the
cells under the creatures are already partly eaten, more than four out of five
of them. On a small bite a weak poison teaches half as fast as the regular one
or not at all, and the creature keeps eating the poisonous colour. On middle
rates mild poison rescued 44% of worlds and regular poison 58%.

#### What did not come out

The third hypothesis was that each world has its own threshold rate. The numbers
look that way: in 147 worlds out of 150 the world dies below some rate and lives
above it, and that point differs between worlds by more than a factor of ten.
But the rule we wrote down was different: at rate 1.5 fewer than 90% of worlds
should survive, uncertainty included. 85% survived, and the upper bound of the
interval came out at 90.7%. The rule says undetermined, and that is what we
report. Moving the bar by one point after the count would be exactly what
preregistration is supposed to prevent.

#### What this experiment does not show

This is one world, one learning rule and one plastic synapse, and the thresholds
belong to it and go nowhere else. We chose the direction of the poison
prediction from a pilot on thirty worlds and said so in the preregistration; the
test ran on a new hundred and fifty. The experiment cannot separate the two
roles of poison, harm and lesson. That needs a condition where the strength of
the lesson is set apart from the energy lost, and that is the next experiment.
Four surviving populations had nearly died out by the end of the observation;
counting them as extinct changes none of the conclusions.

The report with tables, the preregistration, the raw data and the code are on
the page of the experiment: https://minimir.ilinmaks.com/n4.html
