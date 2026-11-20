"""Протокол N4: «Сколько обучения нужно, чтобы пережить перемену» (20.11.2026).

Единая точка правды по условиям и по вмешательству.

Мир: мир B (два цвета еды, яд, один пластичный синапс «вкус») с двумя отличиями:
  1. правило меняется ровно один раз, на фиксированном тике SHIFT
     (Config.switch_once_at). Это классическая постановка эволюционного
     спасения: один резкий сдвиг среды, исход измеряется выживанием;
  2. ген скорости обучения не мутирует (taste_lr_sigma = 0). Вся изменчивость
     скорости задаётся вмешательством за тик до смены и дальше только
     наследуется. Новых мутаций по этому гену нет.

Дизайн с развилкой. На каждом семени мир один раз доживает до тика SHIFT - 1
со скоростью обучения L0 у всех. Затем он копируется (deepcopy вместе с
генератором случайных чисел), и в каждой копии делается одно вмешательство.
Все условия одного семени делят одну и ту же предысторию до последнего тика:
ту же карту, тех же особей, те же запасы энергии, тот же выученный вкус и то
же состояние генератора. Различается только то, что записано ниже.

Часть D, «доза» (бывшая гипотеза N5, градуированная абляция). Всем живым
ставится одна скорость обучения L. Эволюции скорости нет. Измеряется S(L):
доля миров, переживших смену, как функция L.

Часть M, «мягкий яд». Та же серия доз при яде -0.2 вместо -0.5.

Часть V, «изменчивость» (бывшая гипотеза N4). Каждой живой особи ставится
скорость L0 * exp(sigma * z), где z стандартное нормальное число из отдельного
генератора, засеянного только семенем. У одной и той же особи z один во всех
условиях, sigma лишь растягивает его. Медиана остаётся L0, ниже порога из
части D. Измеряется вероятность спасения как функция sigma.

Часть E, «случайные пробы». Доза из части D плюс доля случайных действий
(Config.action_noise). Проверяет, чего не хватает мирам, которые гибнут даже
при быстром обучении: особь перестаёт есть старый цвет раньше, чем решается
попробовать новый, и правило, которое учится только на укусах, замирает.

Проверка F, «заморожено». То же вмешательство, что в V при наибольшей sigma,
но обучение после развилки не применяется. Ожидание: спасения нет по
построению. Если оно есть, это генетическое спасение через врождённый вкус,
отдельная находка, а не подтверждение гипотезы.
"""
import copy

import numpy as np

from .config import Config
from .protocol_b import WORLD_B, config_b

PROTOCOL = "N4-v1"               # заморожен 20.11.2026; правки только новой версией

SHIFT = 5000                     # тик единственной смены правила
HORIZON = 12000                  # тиков наблюдения после смены (пилот 1: самое
                                 # позднее вымирание через 5216 тиков после смены)
TICKS = SHIFT + HORIZON
L0 = 0.1                         # скорость обучения у всех до развилки (как в B1)

# Подтверждающий прогон: семена берутся по порядку с SEED_FIRST, пока не
# наберётся N_CONFIRM годных. Семя негодно, если предок не найден или к тику
# развилки в мире меньше MIN_FORK_POP особей. Годность определяется только
# предысторией до развилки, одинаковой для всех условий, и от исходов не зависит.
# Семена 401 и 402 потрачены 20.11.2026 на пробный прогон всего конвейера
# (раннер, чтение, отказ от второго чтения) и в подтверждающие не входят.
SEED_FIRST = 403
N_CONFIRM = 150
MIN_FORK_POP = 50

# Сетки условий. Выбраны по двум пилотам 20.11.2026 (семена 301-330, не чтение).
# Пилот 1: при L <= 0.45 не выжил ни один мир из 11, при 1.5 только 7. Пилот 2
# с продлённой сеткой: при 4.0 выживают все 30. Переход растянут от 0.45 до
# 4.0, поэтому сетка уплотнена на подъёме и доведена до потолка гена.
DOSES = [0.1, 0.3, 0.45, 0.6, 0.8, 1.0, 1.5, 2.5, 4.0]   # часть D: скорость у всех
SIGMAS = [0.5, 1.0, 1.5, 2.0]        # часть V: разброс ln(скорости); sigma = 0 это D_L0.1
TOXIC_MAIN = -0.5                    # яд основного мира, как в B1
TOXIC_MILD = -0.2                    # мягкий яд: вторая серия доз (часть M)
NOISE = 0.05                         # часть E: доля случайных действий
E_DOSES = [0.6, 1.5, 4.0]            # часть E: при каких дозах добавляется шум
# пороги, выше которых считаем число особей сразу после вмешательства
TAIL_GRID = [0.3, 0.45, 0.6, 0.8, 1.0, 1.5, 2.5]

WORLD_N4 = dict(WORLD_B,
                switch_mean=0, switch_once_at=SHIFT,
                taste_lr_init=L0, taste_lr_init_sigma=0.0,
                taste_lr_sigma=0.0,          # ген скорости не мутирует
                marker_gene=False, record_dead=False)


def _spec(part, dose=None, sigma=None, toxic=TOXIC_MAIN, learning=True, noise=0.0):
    return dict(part=part, dose=dose, sigma=sigma, toxic=toxic, learning=learning, noise=noise)


def conditions():
    """Все условия протокола: имя -> описание вмешательства на развилке."""
    c = {}
    for L in DOSES:                                   # D: доза, основной яд
        c[f"D_L{L:g}"] = _spec("D", dose=L)
    for L in DOSES:                                   # M: доза, мягкий яд
        c[f"M_L{L:g}"] = _spec("M", dose=L, toxic=TOXIC_MILD)
    for sg in SIGMAS:                                 # V: изменчивость
        c[f"V_s{sg:g}"] = _spec("V", sigma=sg)
    for L in E_DOSES:                                 # E: доза плюс случайные пробы
        c[f"E_L{L:g}"] = _spec("E", dose=L, noise=NOISE)
    c["F_s2"] = _spec("F", sigma=2.0, learning=False)  # F: заморожено
    return c


def config_n4(seed, **overrides):
    """Конфигурация общего прогрева: одна на все условия семени."""
    kw = dict(WORLD_N4, seed=seed)
    kw.update(overrides)
    return Config(**kw)


def seed_z(seed, n):
    """Стандартные нормальные числа для вмешательства части V. Отдельный
    генератор, засеянный только семенем: главный поток мира не тратится."""
    return np.random.default_rng(seed * 104729 + 71).standard_normal(n)


def _lr_summary(lr):
    if lr.size == 0:
        return dict(n=0)
    ll = np.log(np.maximum(lr, 1e-9))
    out = dict(n=int(lr.size),
               lr_min=float(lr.min()), lr_q25=float(np.percentile(lr, 25)),
               lr_median=float(np.median(lr)), lr_q75=float(np.percentile(lr, 75)),
               lr_q90=float(np.percentile(lr, 90)), lr_max=float(lr.max()),
               sd_ln_lr=float(ll.std()))
    out["tail"] = {f"{t:g}": int((lr >= t).sum()) for t in TAIL_GRID}
    return out


def warmup(seed, shift=SHIFT, **overrides):
    """Общая предыстория семени: мир доживает до тика shift - 1."""
    from .engine import Engine
    from .ancestry import find_viable_ancestor

    cfg = config_n4(seed, switch_once_at=shift, **overrides)
    # Предок семени ищется в каноническом мире B (условие never), а не в мире
    # текущего протокола: поиск проверяет жизнеспособность в переданной
    # конфигурации, а кэш ключуется только семенем.
    ancestor, _ = find_viable_ancestor(config_b(seed, "never"))
    eng = Engine(cfg, ancestor=ancestor)
    eng.run(shift - 1)
    return eng


def fork(eng, spec):
    """Копия мира с одним вмешательством. Возвращает копию и сводку скоростей
    сразу после вмешательства."""
    clone = copy.deepcopy(eng)
    cfg = clone.cfg
    cfg.toxic_factor = spec["toxic"]
    cfg.taste_learning = spec["learning"]
    cfg.action_noise = spec["noise"]
    clone.pop.cfg = cfg
    clone.world.cfg = cfg
    clone.pop.brains.cfg = cfg
    pop = clone.pop
    ids = pop.ids()
    if ids.size:
        if spec["dose"] is not None:
            pop.taste_lr[ids] = np.float32(spec["dose"])
        else:
            z = seed_z(cfg.seed, ids.size)
            lr = cfg.taste_lr_init * np.exp(spec["sigma"] * z)
            pop.taste_lr[ids] = np.clip(lr, 0.0, cfg.taste_lr_max).astype(np.float32)
    return clone, _lr_summary(pop.taste_lr[ids] if ids.size else np.zeros(0))


def run_fork(clone, ticks):
    """Досчитать копию до тика ticks. Кривая численности каждые 100 тиков."""
    pop = clone.pop
    curve, min_pop, min_tick = [], pop.count, clone.tick
    while clone.tick < ticks and clone.extinct_at is None:
        clone.run(min(50, ticks - clone.tick))
        p = pop.count
        if clone.tick % 100 == 0 or clone.extinct_at is not None or clone.tick >= ticks:
            curve.append([clone.tick, p])      # кривая каждые 100 тиков; минимум ищется каждые 50
        if p < min_pop:
            min_pop, min_tick = p, clone.tick
    ids = pop.ids()
    after = _lr_summary(pop.taste_lr[ids] if ids.size else np.zeros(0))
    if ids.size:
        # скорость не мутирует: разных значений столько, сколько выжило носителей
        vals = sorted({round(float(v), 6) for v in pop.taste_lr[ids]})
        after.update(distinct_lr=len(vals), founder_lr=vals[:40],
                     taste_mean=float(pop.taste[ids].mean()),
                     taste_g_mean=float(pop.taste_g[ids].mean()))
    return dict(rescued=clone.extinct_at is None, extinct=clone.extinct_at,
                pop_end=pop.count, min_pop=min_pop, min_tick=min_tick,
                switches=len(clone.world.switches), after=after, curve=curve)


def measure_seed(seed, conds=None, ticks=TICKS, shift=SHIFT, **overrides):
    """Все условия одного семени: один прогрев, по одной развилке на условие.
    Возвращает список строк для журнала."""
    all_conds = conditions()
    conds = list(all_conds) if conds is None else list(conds)
    def excluded(reason, shared=None):
        return [dict(key=f"EXCLUDED|seed{seed}", label="EXCLUDED", part="X", seed=seed,
                     protocol=PROTOCOL, ticks=ticks, shift=shift, reason=reason,
                     shared=shared, rescued=None)]

    try:
        eng = warmup(seed, shift=shift, **overrides)
    except RuntimeError as e:                     # предок не найден
        return excluded(f"нет предка: {e}")
    ids = eng.pop.ids()
    shared = dict(
        tick=eng.tick, n=int(ids.size),
        energy_mean=(float(eng.pop.E[ids].mean()) if ids.size else None),
        taste_mean=(float(eng.pop.taste[ids].mean()) if ids.size else None),
        lineages=(int(np.unique(eng.pop.lineage[ids]).size) if ids.size else 0))
    if ids.size < MIN_FORK_POP:
        return excluded(f"к развилке {ids.size} особей, меньше {MIN_FORK_POP}", shared)
    rows = []
    for name in conds:
        spec = all_conds[name]
        clone, before = fork(eng, spec)
        res = run_fork(clone, ticks)
        rows.append(dict(
            key=f"{name}|seed{seed}", label=name, part=spec["part"], seed=seed,
            protocol=PROTOCOL, ticks=ticks, shift=shift,
            dose=spec["dose"], sigma=spec["sigma"], toxic=spec["toxic"],
            learning=spec["learning"], noise=spec["noise"],
            shared=shared, before=before, **res))
    return rows
