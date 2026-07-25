"""Быстрые проверки движка (блок 0.4). Каждый тест — секунды, не минуты.

  .venv/bin/python -m pytest tests/ -q

Проверяются пять вещей, на которых стоит всё остальное:
  * детерминизм прогона по seed'у;
  * сохранение энергии (приход еды минус расходы = изменение энергии);
  * поведение mi_from_hist на синтетике (идеальная связь / независимость);
  * побитовая воспроизводимость предка из кэша;
  * что условие shuffled сохраняет распределение входа 8, но зануляет MI о себе.
"""
import numpy as np
import pytest

from sim import Config, Engine, metrics
from sim.config import (A_FORWARD, A_LEFT, A_RIGHT, A_EAT, A_MARK, N_IN, N_OUT)
from sim.metrics import mi_from_hist


# --------------------------------------------------------------- детерминизм
def test_determinism_same_seed():
    """Два движка с одним seed дают идентичные stats() через 500 тиков."""
    a = Engine(Config(seed=3))
    b = Engine(Config(seed=3))
    a.run(500)
    b.run(500)
    assert a.stats() == b.stats()


def test_different_seed_diverges():
    """Санити: разные seed'ы расходятся (иначе seed не работает)."""
    a = Engine(Config(seed=1)); a.run(500)
    b = Engine(Config(seed=2)); b.run(500)
    assert a.stats() != b.stats()


# ----------------------------------------------------------- энергобаланс
def test_energy_conservation_single_agent():
    """Приход энергии (съеденное) минус расходы = изменение суммарной энергии.

    Изолируем баланс от неконсервативных путей: один агент (нет социальных
    трансфертов и толчеи), отрост выключен (ресурс убывает только едой),
    e_max/возраст/порог размножения задраны так, что нет клипа, смертей и
    рождений. Тогда справедливо строгое равенство с точностью до float32.
    """
    cfg = Config(seed=7, init_pop=1, ancestor_mode="random", seed_ancestor=True,
                 regrowth=0.0, crowd_cost=0.0, think_cost=0.0, social=False,
                 e_start=300.0, e_max=1e9, max_age=10 ** 9, repro_threshold=1e9,
                 season_period=0)
    eng = Engine(cfg)
    ids = eng.pop.ids()
    E0 = float(eng.pop.E[ids].sum())
    R0 = eng.world.total_resource()
    N = 150
    eng.run(N)
    ids = eng.pop.ids()
    assert ids.size == 1, "агент не должен был умереть или размножиться"
    E1 = float(eng.pop.E[ids].sum())
    R1 = eng.world.total_resource()
    c = eng.action_counts
    eaten = (R0 - R1) * cfg.energy_per_resource
    cost = (N * cfg.basal_cost + cfg.move_cost * c[A_FORWARD]
            + cfg.turn_cost * (c[A_LEFT] + c[A_RIGHT]) + cfg.eat_cost * c[A_EAT]
            + cfg.mark_cost * c[A_MARK])
    residual = (E1 - E0) - (eaten - cost)
    assert abs(residual) < 0.05, f"баланс не сходится: остаток {residual}"


# ------------------------------------------------------------- mi_from_hist
def test_mi_perfect_dependence():
    """Идеальная связь по квадратной таблице даёт ~log2(min(r,c)) бит."""
    n = 8
    h = np.eye(n, dtype=np.int64) * 5000            # каждая строка -> ровно своё действие
    r = mi_from_hist(h)
    assert abs(r["mi_corrected_bits"] - np.log2(n)) < 0.02


def test_mi_independence_near_zero():
    """Независимость даёт около нуля после поправки на смещение."""
    row = np.array([0.3, 0.1, 0.2, 0.15, 0.25])
    col = np.array([0.2, 0.4, 0.1, 0.3])
    joint = np.outer(row, col) * 200000              # ровно произведение маргиналов
    h = np.round(joint).astype(np.int64)
    r = mi_from_hist(h)
    assert abs(r["mi_corrected_bits"]) < 0.01


def test_mi_too_few_samples():
    """Мало данных -> метрика честно отказывается считать."""
    h = np.eye(8, dtype=np.int64) * 10
    r = mi_from_hist(h)
    assert r["mutual_information_bits"] is None


# ----------------------------------------------------------------- предок
def test_ancestor_reproducible_from_cache():
    """Предок из кэша воспроизводится побитово при повторной загрузке."""
    from sim.ancestry import find_viable_ancestor
    cfg = Config(seed=1)
    g1, t1 = find_viable_ancestor(cfg)
    g2, t2 = find_viable_ancestor(cfg)
    assert t1 == t2
    for a, b in zip(g1, g2):
        assert np.array_equal(a, b)
    assert g1[0].shape == (N_IN, cfg.n_hidden)
    assert g1[2].shape == (cfg.n_hidden, N_OUT)


# ---------------------------------------------------------------- shuffled
def test_shuffled_preserves_distribution_kills_self_mi():
    """shuffled: то же распределение входа 8, но ~0 MI с собственной энергией.

    Накопливаем совместную гистограмму (свой дециль энергии; дециль сигнала)
    по многим независимым перестановкам. Маргинал сигнала обязан совпасть
    с маргиналом собственной энергии (перестановка сохраняет мультимножество),
    а взаимная информация — упасть до нуля.
    """
    cfg = Config(seed=5)
    eng = Engine(cfg)
    eng.run(400)                                     # получить разнобой энергий
    ids = eng.pop.ids()
    assert ids.size >= 20

    self_vals, shuf_vals = [], []
    joint = np.zeros((10, 10), dtype=np.int64)
    for _ in range(300):
        e_self, _ = eng._interoceptive_signal(ids, np.full(ids.size, -1))
        # временно переключаем режим на shuffled
        eng.cfg.intero_mode = "shuffled"
        e_shuf, _ = eng._interoceptive_signal(ids, np.full(ids.size, -1))
        eng.cfg.intero_mode = "self"
        # перестановка сохраняет мультимножество значений
        assert np.allclose(np.sort(e_self), np.sort(e_shuf))
        bs = np.clip((e_self * 10).astype(int), 0, 9)
        bh = np.clip((e_shuf * 10).astype(int), 0, 9)
        np.add.at(joint, (bs, bh), 1)
        self_vals.append(e_self); shuf_vals.append(e_shuf)

    # маргиналы совпадают (то же распределение входа)
    mself = joint.sum(axis=1)
    mshuf = joint.sum(axis=0)
    assert np.array_equal(mself, mshuf)
    # но информации о себе не осталось
    r = mi_from_hist(joint)
    assert r["mi_corrected_bits"] < 0.01
