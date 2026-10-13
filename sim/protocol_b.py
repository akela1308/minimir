"""Протокол B: «Когда выгодно учиться». Единая точка правды для конфигурации.

Мир B отличается от мира A ровно тремя вещами, и все три записаны здесь:
  1. два типа еды, роли которых меняются в непредсказуемые моменты;
  2. мир богаче (patch_threshold 0.0 и regrowth 0.008 вместо 0.35 и 0.004),
     чтобы питательная половина давала приток, сопоставимый с миром A;
  3. врождённый «вкус» предка (ест цвет +1) как единственный пластичный
     параметр (см. Config.taste).

Условия (все на одних и тех же seed'ах, с одним предком на seed):
  never        правило не меняется, пластичность включена      (стационарный контроль)
  slow         T = 5000 тиков, много поколений                  (медленная смена)
  life         T = 600 тиков, около одной жизни                 (ЛЕЧЕНИЕ)
  fast         T = 150 тиков, несколько раз за жизнь            (слишком часто)
  life_frozen  T = 600, обучение не применяется                  (абляция обучения)
  never_frozen правило не меняется, обучение не применяется      (нейтральный дрейф гена скорости)
"""
from .config import Config

CONDS = ["never", "slow", "life", "fast", "life_frozen", "never_frozen"]
SWITCH = dict(never=0, slow=5000, life=600, fast=150, life_frozen=600, never_frozen=0)
PLASTIC = dict(never=True, slow=True, life=True, fast=True, life_frozen=False, never_frozen=False)

WORLD_B = dict(food_types=2, patch_threshold=0.0, regrowth=0.008, toxic_factor=-0.5,
               taste=True, hebbian=False,
               signs=False, social=False, intero_mode="self", interoception=True)


def config_b(seed, cond, **overrides):
    if cond not in CONDS:
        raise ValueError(f"неизвестное условие протокола B: {cond}")
    kw = dict(WORLD_B, seed=seed, switch_mean=SWITCH[cond])
    if not PLASTIC[cond]:
        # замороженный вкус: ген скорости есть и дрейфует, но не применяется
        kw.update(taste_learning=False)
    kw.update(overrides)
    return Config(**kw)


# ----------------------------------------------------------------- измерение
SAMPLE_EVERY = 2000


def _overall_accuracy(eng):
    """Точность еды за всё окно измерения: по возрастным корзинам, они не обнуляются."""
    g, b = int(eng.age_good.sum()), int(eng.age_bad.sum())
    return g / (g + b) if (g + b) else None


def _dead_summary(pop, cfg):
    """Сводка по погибшим с прошлой точки кривой: сколько, медианный возраст,
    медиана гена скорости (и маркера, если он есть). Медианы на линейной шкале,
    как и lr_median живых в той же точке; сравнение живых и погибших на одном
    тике и есть ответ на вопрос «кто умирает на смене правила»."""
    import numpy as np
    n = len(pop.dead_lr)
    out = dict(dead_n=n,
               dead_age_median=(float(np.median(pop.dead_age)) if n else None),
               dead_lr_median=(float(np.median(pop.dead_lr)) if n else None))
    if cfg.marker_gene:
        out["dead_marker_median"] = float(np.median(pop.dead_marker)) if n else None
    return out


def measure_b(job):
    """Один прогон протокола B -> строка чисел для журнала.

    Прогрев = switch_from_tick (правило ещё не менялось). Накопители точности
    и кривых обнуляются на границе прогрева, чтобы в них попал только мир,
    который уже меняет правила. Ген скорости обучения пишется кривой
    (медиана по живым каждые SAMPLE_EVERY тиков): главный результат это
    не одна точка, а траектория.
    """
    import numpy as np
    from .engine import Engine

    cfg = config_b(job["cfg"]["seed"], job["label"], **job.get("overrides", {}))
    ticks = int(job["ticks"])
    eng = Engine(cfg)
    curve = []
    state = dict(peak=0, min_after_switch=None, first_switch=None)

    def rec(e):
        p = e.pop.count
        state["peak"] = max(state["peak"], p)
        if e.world.switches:
            if state["first_switch"] is None:
                state["first_switch"] = e.world.switches[0]
            m = state["min_after_switch"]
            state["min_after_switch"] = p if m is None else min(m, p)
        if e.tick % SAMPLE_EVERY == 0:
            st = e.stats()
            point = dict(
                tick=e.tick, pop=p,
                lr_median=st["taste_lr_median"], lr_mean=st["taste_lr_mean"],
                taste_g=st["taste_g_mean"], taste=st["taste_mean"],
                acc=st["eat_accuracy"], switches=st["switches"])
            if cfg.marker_gene:
                # 13.10.2026 (ИДЕИ §2.5, B2): маркер и отношение lr/marker на том же тике
                point.update(marker_median=st["marker_median"],
                             lr_over_marker=st["lr_over_marker_median"])
            if cfg.record_dead:
                # 13.10.2026 (B2 §0.3): погибшие за окно между точками кривой
                point.update(_dead_summary(e.pop, cfg))
                e.pop.dead_age.clear(); e.pop.dead_lr.clear(); e.pop.dead_marker.clear()
            curve.append(point)
            e.eat_good = e.eat_bad = 0        # точность в кривой — по окну

    warm = min(cfg.switch_from_tick, ticks)
    eng.run(warm, on_log=rec)
    eng.reset_metrics()
    eng.run(ticks - warm, on_log=rec)

    st = eng.stats()
    ids = eng.pop.ids()
    life = float(np.median(eng.pop.lifespans)) if eng.pop.lifespans else None
    lr = eng.pop.taste_lr[ids] if ids.size else np.zeros(0)
    extra = {}
    if cfg.marker_gene:
        # 13.10.2026 (ИДЕИ §2.5, B2): нейтральный маркер в конце прогона
        m = eng.pop.marker[ids] if ids.size else np.zeros(0)
        extra = dict(marker_median=st["marker_median"], marker_q25=st["marker_q25"],
                     marker_q75=st["marker_q75"],
                     lr_over_marker_median=st["lr_over_marker_median"],
                     marker_init=cfg.marker_init,
                     lr_at_ceiling=(float((lr >= cfg.taste_lr_max * 0.99).mean()) if lr.size else None),
                     marker_at_ceiling=(float((m >= cfg.taste_lr_max * 0.99).mean()) if m.size else None))
    if cfg.record_dead:
        # 13.10.2026 (B2 §0.3): всего погибших за прогон; окна по погибшим лежат в curve
        extra["dead_total"] = int(eng.pop.deaths)
        extra["record_dead"] = True
    return dict(
        key=job["key"], label=job["label"], seed=cfg.seed,
        switch_mean=cfg.switch_mean, learning=cfg.taste_learning,
        extinct=eng.extinct_at, pop=st["pop"], peak_pop=state["peak"],
        min_pop_after_switch=state["min_after_switch"],
        first_switch=state["first_switch"], switches=st["switches"],
        median_life=life,
        lr_median=st["taste_lr_median"], lr_mean=st["taste_lr_mean"],
        lr_q25=(float(np.percentile(lr, 25)) if lr.size else None),
        lr_q75=(float(np.percentile(lr, 75)) if lr.size else None),
        lr_init=cfg.taste_lr_init,
        taste_g=st["taste_g_mean"], taste=st["taste_mean"],
        eat_accuracy=_overall_accuracy(eng),
        age_curve=eng.age_curve(),
        recovery=eng.recovery_curve(),
        curve=curve,
        **extra,
    )
