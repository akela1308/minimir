"""Проверки правок 13 октября 2026 (ИДЕИ_2026-10-13.md, ПОРУЧЕНИЕ_ПРАВКИ_2026-10-13.md).

  * новые флаги выключены по умолчанию и не меняют старые прогоны (бит в бит);
  * метрика при явных порогах 200 и 1000: при 1000 совпадает со старой;
  * neighbour: счётчики настоящий сосед / подмена покрывают все агент-тики;
  * constant и twin: распределение, временная структура, отсутствие себя;
  * шок-проба: отдельный генератор, удар виден, sham ничего не меняет;
  * маркерный ген: наследуется и мутирует, при frozen на вкус не влияет.
"""
import copy
import numpy as np
import pytest

from sim import Config, Engine, metrics
from sim.config import A_FORWARD, A_EAT
from sim.protocol_b import config_b


def _state(eng):
    p = eng.pop
    return (p.alive.tobytes(), p.E.tobytes(), p.y.tobytes(), p.x.tobytes(),
            p.brains.G1.tobytes(), p.brains.G2.tobytes(), p.taste.tobytes(),
            p.taste_lr.tobytes(), eng.energy_action_hist.tobytes(), eng.tick)


# ------------------------------------------------------- бит в бит без флагов
def test_defaults_unchanged_bitwise():
    """Явно выключенные новые флаги равны умолчанию: старые прогоны не меняются."""
    a = Engine(Config(seed=3)); a.run(400)
    b = Engine(Config(seed=3, marker_gene=False, shock_every=0, intero_mode="self")); b.run(400)
    assert _state(a) == _state(b)


def test_shock_configured_but_disabled_is_bitwise_identical():
    """Шок настроен, но раннер его не включил: основной генератор не тронут."""
    a = Engine(Config(seed=3)); a.run(400)
    b = Engine(Config(seed=3, shock_every=100)); b.run(400)   # shock_enabled остаётся False
    assert _state(a) == _state(b)
    assert b.shock_summary()["events"] == 0


# ------------------------------------------------------- пороги 200 и 1000
def test_within_at_1000_equals_legacy_and_200_sees_more_agents():
    cfg = Config(seed=4, track_individual=True)
    eng = Engine(cfg); eng.run(300)
    eng.reset_metrics(); eng.reset_individual()
    eng.run(1400)
    legacy = metrics.within_agent_dependence(eng)
    at1000 = metrics.within_agent_dependence_at(eng, 1000)
    at200 = metrics.within_agent_dependence_at(eng, 200)
    assert legacy["n_agents"] == at1000["n_agents"]
    assert legacy["mean_mi_bits"] == pytest.approx(at1000["mean_mi_bits"], abs=1e-12)
    # порог 200 включает тех, кого пол n>=1000 в mi_from_hist отбрасывал
    assert at200["n_agents"] > at1000["n_agents"]
    assert at200["mean_mi_bits"] is not None


def test_nofloor_estimator_matches_mi_from_hist_above_floor():
    rng = np.random.default_rng(0)
    h = rng.integers(0, 50, size=(10, 8))
    assert h.sum() >= 1000
    assert metrics.mi_corrected_nofloor(h) == pytest.approx(
        mi_from_hist_corrected(h), abs=1e-12)


def mi_from_hist_corrected(h):
    return metrics.mi_from_hist(h)["mi_corrected_bits"]


# ------------------------------------------------------- neighbour: доля соседа
def test_neighbour_counters_cover_all_agent_ticks():
    cfg = Config(seed=5, intero_mode="neighbour")
    eng = Engine(cfg); eng.run(200)
    eng.reset_metrics()
    ticks = 150
    agent_ticks = 0
    for _ in range(ticks):
        agent_ticks += eng.pop.count
        eng.step()
    assert eng.neigh_real + eng.neigh_sub == agent_ticks
    assert eng.neigh_real > 0 and eng.neigh_sub > 0   # и соседи, и подмена встречаются
    # в режиме self счётчики молчат
    e2 = Engine(Config(seed=5)); e2.run(200)
    assert e2.neigh_real == 0 and e2.neigh_sub == 0


# ------------------------------------------------------- constant и twin
def test_constant_mode_is_constant_and_not_zero():
    eng = Engine(Config(seed=5, intero_mode="constant", intero_const=0.5))
    eng.run(300)
    ids = eng.pop.ids()
    e, de = eng._interoceptive_signal(ids, np.full(ids.size, -1))
    assert np.all(e == np.float32(0.5)) and np.all(de == 0)


def test_twin_never_self_and_is_a_living_agent_energy():
    eng = Engine(Config(seed=5, intero_mode="twin"))
    eng.run(400)
    for _ in range(50):
        eng.step()
        ids = eng.pop.ids()
        # близнец назначается при первом же считывании сенсоров, поэтому у
        # родившихся на этом тике (возраст 0) его ещё нет; у остальных обязан быть
        sensed = ids[eng.pop.age[ids] > 0]
        tw = eng.pop.twin[sensed]
        assert np.all(tw >= 0)
        assert not np.any(tw == sensed)
        # близнец был жив на момент считывания; к концу тика мог умереть, тогда
        # на следующем считывании его заменят: проверяем, что мёртвых не больше,
        # чем умерло за этот тик
        assert (~eng.pop.alive[tw]).sum() <= max(1, int(0.1 * sensed.size))


def test_twin_keeps_temporal_structure_shuffled_destroys_it():
    """Лаг-1 автокорреляция входа 8: у twin как у self, у shuffled около нуля."""
    def lag1(mode, ticks=300):
        eng = Engine(Config(seed=6, intero_mode=mode))
        eng.run(300)
        # следим за агентами, живыми в начале окна; берём только доживших до конца
        ids0 = eng.pop.ids()
        birth0 = eng.pop.birth_tick[ids0].copy()
        series = np.full((ticks, ids0.size), np.nan, dtype=np.float64)
        for t in range(ticks):
            ids = eng.pop.ids()
            partner, _ = eng._nearest_partner(ids)
            e, _ = eng._interoceptive_signal(ids, partner)
            pos = np.searchsorted(ids, ids0)
            pos = np.clip(pos, 0, ids.size - 1)
            ok = (ids[pos] == ids0) & (eng.pop.birth_tick[ids0] == birth0)
            series[t, ok] = e[pos[ok]]
            eng.step()
        full = ~np.isnan(series).any(axis=0)
        s = series[:, full]
        assert s.shape[1] >= 5
        x, y = s[:-1], s[1:]
        xc, yc = x - x.mean(0), y - y.mean(0)
        r = (xc * yc).sum(0) / np.sqrt((xc ** 2).sum(0) * (yc ** 2).sum(0) + 1e-12)
        return float(np.nanmean(r))
    r_self, r_twin, r_shuf = lag1("self"), lag1("twin"), lag1("shuffled")
    assert r_self > 0.9
    assert r_twin > 0.8
    assert r_shuf < 0.3
    assert r_twin - r_shuf > 0.5


def test_twin_marginal_close_to_self():
    """Распределение входа 8 у twin близко к распределению собственной энергии."""
    eng = Engine(Config(seed=6, intero_mode="twin"))
    eng.run(300)
    own, twin = [], []
    for _ in range(200):
        ids = eng.pop.ids()
        own.append(eng.pop.E[ids] / eng.cfg.e_max)
        e, _ = eng._interoceptive_signal(ids, np.full(ids.size, -1))
        twin.append(e)
        eng.step()
    own = np.concatenate(own); twin = np.concatenate(twin)
    assert abs(own.mean() - twin.mean()) < 0.05
    assert abs(own.std() - twin.std()) < 0.05


# ------------------------------------------------------- шок-проба
def test_shock_abrupt_removes_energy_and_counts_groups():
    cfg = Config(seed=7, shock_every=50, shock_frac=0.2, shock_amount=20.0,
                 shock_min_energy=30.0, shock_window=20, shock_survival_ticks=60)
    eng = Engine(cfg); eng.run(200)
    eng.reset_metrics()
    eng.shock_enabled = True
    # дойти до тика, кратного 50, и снять энергию перед ударом
    while eng.tick % 50 != 0:
        eng.step()
    ids = eng.pop.ids()
    E_before = eng.pop.E.copy()
    eng.step()
    shocked = np.flatnonzero(eng.shock_group == 1)
    control = np.flatnonzero(eng.shock_group == 2)
    assert shocked.size == control.size > 0
    # у ударенных энергия упала примерно на 20 относительно контроля того же тика
    drop_s = (E_before[shocked] - eng.pop.E[shocked]).mean()
    drop_c = (E_before[control] - eng.pop.E[control]).mean()
    assert 15 < drop_s - drop_c < 25
    eng.run(100)
    s = eng.shock_summary()
    assert s["events"] >= 1
    assert s["samples_shocked"] > 0 and s["samples_control"] > 0
    assert s["checked_shocked"] == s["n_shocked"] - (eng.shock_group == 1).sum()


def test_shock_sham_changes_no_energy():
    cfg = Config(seed=7, shock_every=50, shock_mode="sham")
    a = Engine(Config(seed=7)); a.run(260)
    b = Engine(cfg); b.run(200); b.shock_enabled = True; b.run(60)
    # sham выбирает группы, но не трогает энергию: мир идёт как без шока
    assert _state(a) == _state(b)
    assert b.shock_summary()["n_shocked"] > 0


def test_shock_slow_total_equals_amount():
    cfg = Config(seed=7, shock_every=50, shock_mode="slow", shock_slow_ticks=10,
                 shock_amount=20.0, shock_window=5, shock_survival_ticks=30)
    eng = Engine(cfg); eng.run(200); eng.shock_enabled = True
    while eng.tick % 50 != 0:
        eng.step()
    eng.step()
    shocked = np.flatnonzero(eng.shock_group == 1)
    assert shocked.size > 0
    assert np.allclose(eng.shock_left[shocked], 20.0 - 20.0 / 10, atol=1e-4) or \
        np.allclose(eng.shock_left[shocked], 20.0, atol=1e-4)
    eng.run(12)
    assert np.all(eng.shock_left[shocked] <= 1e-4)


# ------------------------------------------------------- маркерный ген
def test_marker_gene_inherits_and_mutates_but_does_nothing():
    cfg = config_b(1, "never_frozen", marker_gene=True)
    eng = Engine(cfg); eng.run(1500)
    ids = eng.pop.ids()
    m = eng.pop.marker[ids]
    assert np.all(m > 0)
    assert m.std() > 0                      # мутирует
    assert np.all(m <= cfg.taste_lr_max)
    st = eng.stats()
    assert st["marker_median"] is not None and st["lr_over_marker_median"] is not None
    # frozen: вкус остался равен геному, маркер на это не влияет
    assert np.allclose(eng.pop.taste[ids], eng.pop.taste_g[ids])


def test_marker_gene_off_leaves_protocol_b_bitwise():
    a = Engine(config_b(1, "life")); a.run(600)
    b = Engine(config_b(1, "life", marker_gene=False)); b.run(600)
    assert _state(a) == _state(b)
    assert a.stats()["marker_median"] is None


# ------------------------------------------------------- постепенная смена правила
def test_switch_ramp_off_is_bitwise_identical_to_b1():
    a = Engine(config_b(1, "life")); a.run(6500)
    b = Engine(config_b(1, "life", switch_ramp_ticks=0)); b.run(6500)
    assert _state(a) == _state(b)


def test_switch_ramp_interpolates_factors():
    cfg = config_b(1, "life", switch_ramp_ticks=100)
    eng = Engine(cfg)
    w = eng.world
    tox = cfg.toxic_factor
    # дойти до первой смены
    while not w.switches:
        assert eng.step(), "популяция вымерла до первой смены, тест не о том"
    t_sw = w.switches[0]
    yx_new = np.argwhere(w.food_type == w.good_type)[:5]          # новый съедобный
    yx_old = np.argwhere(w.food_type != w.good_type)[:5]          # старый съедобный
    f_new0 = w.energy_factor(yx_new[:, 0], yx_new[:, 1])
    f_old0 = w.energy_factor(yx_old[:, 0], yx_old[:, 1])
    # сразу после смены новый цвет ещё почти яд, старый почти еда
    assert np.allclose(f_new0, tox, atol=0.06) and np.allclose(f_old0, 1.0, atol=0.06)
    eng.run(50)
    f_new = w.energy_factor(yx_new[:, 0], yx_new[:, 1])
    assert tox < f_new[0] < 1.0                                   # на полпути
    eng.run(60)
    f_new1 = w.energy_factor(yx_new[:, 0], yx_new[:, 1])
    f_old1 = w.energy_factor(yx_old[:, 0], yx_old[:, 1])
    assert w.t - t_sw >= 100
    assert np.allclose(f_new1, 1.0) and np.allclose(f_old1, tox)


# ------------------------------------------------------- посев распределением скоростей
def test_taste_lr_init_sigma_off_is_bitwise_and_on_spreads():
    a = Engine(config_b(1, "never_frozen")); a.run(300)
    b = Engine(config_b(1, "never_frozen", taste_lr_init_sigma=0.0)); b.run(300)
    assert _state(a) == _state(b)
    c = Engine(config_b(1, "never_frozen", taste_lr_init_sigma=1.0))
    lr0 = c.pop.taste_lr[c.pop.ids()]
    assert lr0.std() > 0 and abs(np.median(np.log10(lr0)) - np.log10(0.1)) < 0.25
    assert np.all(lr0 <= c.cfg.taste_lr_max) and np.all(lr0 >= 0)


# ------------------------------------------------------- абляция подменой
def test_ablation_by_substitution_returns_paired_fields():
    eng = Engine(Config(seed=5)); eng.run(300)
    r = metrics.ablate_interoception(eng, ticks=50, mode="shuffled")
    assert r["mode"] == "shuffled" and r["ticks"] == 50
    assert 0 <= r["intact"]["survived"] <= 1 and 0 <= r["ablated"]["survived"] <= 1
    # движок не тронут: популяция исходного движка не изменилась
    assert eng.tick == 300
    r0 = metrics.ablate_interoception(eng, ticks=50)
    assert r0["mode"] == "off"
