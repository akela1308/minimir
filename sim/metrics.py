"""Метрики, которые проверяют гипотезу, а не просто рисуют графики."""
import copy
import numpy as np
from .config import ACTION_NAMES, A_FORWARD, A_EAT, N_ACTIONS


def mi_from_hist(h):
    """Взаимная информация с поправкой на смещение.

    Оценка MI по гистограмме систематически завышена при малом числе сэмплов,
    причём тем сильнее, чем меньше данных. Условия дают разное их количество,
    поэтому сырые значения сравнивать нельзя. Вычитаем асимптотический уровень
    случайности (r-1)(c-1)/(2N ln2) — это то, что метрика показала бы на
    полностью независимых данных того же объёма.
    """
    h = np.asarray(h, dtype=np.float64)
    n = h.sum()
    if n < 1000:
        return dict(mutual_information_bits=None, samples=int(n))
    p = h / n
    pe = p.sum(axis=1, keepdims=True)
    pa = p.sum(axis=0, keepdims=True)
    denom = pe * pa
    nz = (p > 0) & (denom > 0)
    mi = float((p[nz] * np.log2(p[nz] / denom[nz])).sum())
    r = int((h.sum(axis=1) > 0).sum())
    c = int((h.sum(axis=0) > 0).sum())
    chance = (r - 1) * (c - 1) / (2 * n * np.log(2)) if r > 1 and c > 1 else 0.0
    pa1 = pa[pa > 0]
    h_act = -float((pa1 * np.log2(pa1)).sum())
    return dict(mutual_information_bits=mi,
                chance_level_bits=float(chance),
                mi_corrected_bits=float(mi - chance),
                action_entropy_bits=h_act,
                fraction_explained=(mi - chance) / h_act if h_act > 0 else None,
                samples=int(n))


def behaviour_depends_on_energy(engine):
    """ГЛАВНАЯ метрика этапа 1: взаимная информация I(энергия; действие) в битах.

    Это и есть операционализация «петли уязвимости»: насколько поведение
    вообще зависит от внутреннего состояния. У контрольной группы без
    интероцепции ожидаем около нуля — остаётся только косвенная корреляция
    (сытый агент чаще стоит на еде). Разница между группами — наш результат.
    """
    return mi_from_hist(engine.energy_action_hist)


def switch_point(engine):
    """Порог, на котором агент переключается на добычу еды.

    Реактивное существо кормится у самого нуля, упреждающее — заранее.
    Порог безмасштабный: середина между минимальной и максимальной долей
    «пищевых» действий по децилям энергии, а не произвольные 0.5.
    """
    h = engine.energy_action_hist.astype(np.float64)
    totals = h.sum(axis=1)
    forage = h[:, A_FORWARD] + h[:, A_EAT]
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(totals > 50, forage / np.maximum(totals, 1), np.nan)
    valid = ~np.isnan(frac)
    if valid.sum() < 3:
        return dict(by_decile=frac.tolist(), switch_energy=None,
                    amplitude=None, samples=int(totals.sum()))
    lo, hi = float(np.nanmin(frac)), float(np.nanmax(frac))
    mid = (lo + hi) / 2.0
    thr = None
    for b in range(9, -1, -1):                 # идём сверху вниз по сытости
        if valid[b] and frac[b] >= mid:
            thr = b * 10
            break
    return dict(by_decile=frac.tolist(), switch_energy=thr,
                amplitude=hi - lo, samples=int(totals.sum()))


def action_profile(engine):
    c = engine.action_counts
    total = max(int(c.sum()), 1)
    return {name: float(c[i] / total) for i, name in enumerate(ACTION_NAMES)}


def ablate_interoception(engine, ticks=2000):
    """Забираем у обученной популяции сенсор собственной энергии на ходу.

    Падение выживаемости = мера того, насколько существо следит за собой.
    Это операционализация пункта 3 нашего рецепта (петля уязвимости).
    """
    base = _clone_and_run(engine, ticks, interoception=True)
    abl = _clone_and_run(engine, ticks, interoception=False)
    return dict(intact=base, ablated=abl,
                survival_drop=_safe_drop(base["survived"], abl["survived"]))


def ablate_recognition(engine, ticks=2000):
    """То же для узнавания: без него взаимность невозможна в принципе (Аксельрод)."""
    base = _clone_and_run(engine, ticks, recognition=True)
    abl = _clone_and_run(engine, ticks, recognition=False)
    return dict(intact=base, ablated=abl,
                coop_drop=_safe_drop(base["coop_rate"], abl["coop_rate"]))


def _safe_drop(a, b):
    if a in (None, 0) or b is None:
        return None
    return float((a - b) / a)


def _clone_and_run(engine, ticks, **overrides):
    """Форк движка с изменённым конфигом. Популяция и мир копируются как есть."""
    clone = copy.deepcopy(engine)
    for k, v in overrides.items():
        setattr(clone.cfg, k, v)
    clone.pop.cfg = clone.cfg
    clone.world.cfg = clone.cfg
    clone.pop.brains.cfg = clone.cfg
    start_ids = clone.pop.ids()
    start_n = start_ids.size
    tracked = set(start_ids.tolist())
    clone.coop_events = clone.defect_events = 0
    clone.run(ticks)
    still = set(clone.pop.ids().tolist()) & tracked
    st = clone.stats()
    return dict(survived=len(still) / start_n if start_n else 0.0,
                final_pop=st["pop"], mean_E=st["mean_E"],
                coop_rate=st["coop_rate"])


def hunger_vs_cooperation(engine):
    """Наш собственный вопрос: меняется ли стратегия с уровнем сытости.

    Если кооперация условна (щедрость при сытости, предательство на грани),
    это и есть «нужда деформирует мораль» — эффект, которого у Аксельрода
    не могло быть, потому что его стратегии не имели тела.
    """
    hist = engine.energy_action_hist.astype(np.float64)
    give = hist[:, 5]
    take = hist[:, 6]
    social = give + take
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(social > 0, give / np.maximum(social, 1), np.nan)
    valid = ~np.isnan(rate)
    corr = None
    if valid.sum() >= 3:
        x = np.arange(10)[valid]
        corr = float(np.corrcoef(x, rate[valid])[0, 1])
    return dict(coop_rate_by_energy_decile=rate.tolist(),
                correlation_with_energy=corr,
                social_events=int(social.sum()))


def within_agent_hunger_vs_cooperation(engine, min_social=30):
    """Внутриагентная версия hunger_vs_cooperation — закрывает главный confound.

    Популяционная доля кооперации по децилям энергии обогащена «отнимающими»
    в верхних децилях по построению: `take` сам поднимает энергию агента,
    перемешивая агентов между децилями. Здесь для каждого агента считаем
    give/(give+take) по его собственным децилям за его жизнь и корреляцию с
    децилем, затем усредняем корреляции по агентам. Это свойство индивида,
    а не популяционного облака.

    Требует track_individual=True.
    """
    if not getattr(engine, "track_individual", False):
        return dict(mean_correlation=None, n_agents=0, note="нужен track_individual")
    corrs = []
    for h in engine.all_individual_hists():
        give = h[:, 5].astype(np.float64)
        take = h[:, 6].astype(np.float64)
        social = give + take
        if social.sum() < min_social:
            continue
        valid = social > 0
        if valid.sum() < 3:
            continue
        rate = give[valid] / social[valid]
        x = np.arange(10)[valid]
        if rate.std() < 1e-9:
            continue
        corrs.append(float(np.corrcoef(x, rate)[0, 1]))
    if not corrs:
        return dict(mean_correlation=None, n_agents=0)
    c = np.array(corrs, float)
    return dict(mean_correlation=float(c.mean()),
                sd=float(c.std(ddof=1)) if c.size > 1 else 0.0,
                median=float(np.median(c)), n_agents=int(c.size))


def genome_diversity(engine):
    ids = engine.pop.ids()
    if ids.size < 2:
        return 0.0
    G = engine.pop.brains.genome_matrix(ids)
    return float(G.std(axis=0).mean())


def energy_occupancy(engine):
    """Диагностика прибора: какую часть шкалы энергии популяция реально занимает.

    Если все агенты сидят в двух децилях, взаимная информация физически
    не может быть большой — переключаться не на чем. Низкое MI тогда означает
    не «поведение не зависит от состояния», а «мы не в том диапазоне смотрим».
    Без этого числа главную метрику интерпретировать нельзя.
    """
    h = engine.energy_action_hist.astype(np.float64)
    tot = h.sum()
    if tot == 0:
        return dict(distribution=[0.0] * 10, entropy_bits=0.0, occupied_deciles=0)
    p = h.sum(axis=1) / tot
    nz = p[p > 0]
    return dict(distribution=p.tolist(),
                entropy_bits=float(-(nz * np.log2(nz)).sum()),
                occupied_deciles=int((p > 0.01).sum()))


def sign_metrics(engine):
    """Метрики знакового слоя (этап 3), калибруются в C.2/C.3.

    * mark_rate — доля тиков-действий MARK;
    * mi_state_content_bits — MI(дециль энергии; класс содержания метки):
      «метка вообще о чём-то?» Около нуля -> знака нет, смотреть нечего;
    * own_mark_freshness — средний возраст читаемых СВОИХ меток. Возраст ~1
      означает обход к рекуррентности, а не знак (STAGE3_DESIGN §3);
    * own_vs_other_reads — доля прочтений собственных меток среди всех.
    """
    total_actions = int(engine.action_counts.sum())
    mark_rate = (engine.action_counts[7] / total_actions) if total_actions else 0.0
    mi = mi_from_hist(engine.mark_state_hist)
    fresh = (engine.own_mark_age_sum / engine.own_mark_age_count
             if engine.own_mark_age_count else None)
    reads = engine.own_mark_reads + engine.other_mark_reads
    return dict(mark_rate=float(mark_rate),
                marks_made=int(engine.marks_made),
                mi_state_content_bits=mi.get("mi_corrected_bits"),
                mi_samples=mi.get("samples"),
                own_mark_freshness=fresh,
                own_mark_reads=int(engine.own_mark_reads),
                other_mark_reads=int(engine.other_mark_reads),
                own_read_fraction=(engine.own_mark_reads / reads) if reads else None)


def within_agent_dependence(engine, min_samples=200):
    """Внутриагентная версия главной метрики.

    Populяционная MI смешивает вариацию внутри агента и между агентами:
    действие само меняет энергию, поэтому децили обогащаются определёнными
    стратегиями по построению. Здесь MI считается по каждому агенту за его
    жизнь, а затем усредняется — измеряется свойство индивида, а не
    популяционного облака. Ближе по духу к информационной теории
    индивидуальности (Krakauer и др., 2020).

    Требует включённого engine.track_individual.
    """
    if getattr(engine, "track_individual", False):
        hists = engine.all_individual_hists()
    else:
        hists = None
    if not hists:
        return dict(mean_mi_bits=None, n_agents=0,
                    note="включите cfg.track_individual")
    vals = []
    for h in hists:
        if h.sum() >= min_samples:
            r = mi_from_hist(h)
            if r.get("mi_corrected_bits") is not None:
                vals.append(r["mi_corrected_bits"])
    if not vals:
        return dict(mean_mi_bits=None, n_agents=0)
    v = np.array(vals, float)
    return dict(mean_mi_bits=float(v.mean()),
                sd=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                median=float(np.median(v)),
                n_agents=int(v.size))
