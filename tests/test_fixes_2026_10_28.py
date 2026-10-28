"""Правки 28 октября 2026 (рецензия и решения владельца, CHANGES_A2B2.md):

  * twin: близнец это пара (слот, birth_tick); слот мёртвого близнеца, занятый
    новорождённым в том же тике, больше не читается молча;
  * режимы кроме twin бит в бит как прежде (twin_birth не трогает генератор);
  * объявленные seed'ы A2 и B2 начинаются с 201, не с 1.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

from sim import Config, Engine

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "runs" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _state(eng):
    p = eng.pop
    return (p.alive.tobytes(), p.E.tobytes(), p.y.tobytes(), p.x.tobytes(),
            p.brains.G1.tobytes(), p.taste_lr.tobytes(), eng.energy_action_hist.tobytes(), eng.tick)


# ------------------------------------------------------------ близнец
def test_twin_birth_tick_guard_no_silent_slot_reuse():
    """Сценарий из рецензии: cull() освобождает слот близнеца, reproduce() того же
    тика отдаёт его новорождённому; до правки проверка alive не срабатывала и
    агент читал энергию новорождённого (545 молчаливых подмен за 5000 тиков на
    seed 101). Считаем на считывании сенсоров: сколько раз слот близнеца к
    следующему считыванию оказался занят другим агентом (сценарий есть), и
    сколько раз движок при этом НЕ переназначил близнеца (должно быть ноль)."""
    cfg = Config(seed=101, intero_mode="twin", interoception=True)
    eng = Engine(cfg)
    pop = eng.pop
    n = cfg.max_pop
    prev_slot = np.full(n, -1, dtype=np.int64)
    prev_birth = np.full(n, -2, dtype=np.int64)
    prev_self_birth = np.full(n, -2, dtype=np.int64)
    counts = dict(scenario=0, silent=0, mismatch_after=0, sensed=0)
    orig = eng._interoceptive_signal

    def spy(ids, partner):
        tw0 = pop.twin[ids]
        # до вызова: слот тот же, что на прошлом считывании, но в нём другой агент
        had = (prev_slot[ids] >= 0) & (tw0 == prev_slot[ids]) & (pop.birth_tick[ids] == prev_self_birth[ids])
        reoccupied = had & pop.alive[np.where(tw0 >= 0, tw0, 0)] & (pop.birth_tick[np.where(tw0 >= 0, tw0, 0)] != prev_birth[ids])
        counts["scenario"] += int(reoccupied.sum())
        out = orig(ids, partner)
        tw = pop.twin[ids]
        ok = tw >= 0
        counts["sensed"] += int(ok.sum())
        # после вызова: движок обязан был переназначить (слот или birth изменились)
        not_reassigned = reoccupied & (tw == tw0) & (pop.twin_birth[ids] == prev_birth[ids])
        counts["silent"] += int(not_reassigned.sum())
        # инвариант: сигнал читается у того, кого назначили
        counts["mismatch_after"] += int((pop.birth_tick[tw[ok]] != pop.twin_birth[ids[ok]]).sum())
        prev_slot[ids[ok]] = tw[ok]
        prev_birth[ids[ok]] = pop.birth_tick[tw[ok]]
        prev_self_birth[ids[ok]] = pop.birth_tick[ids[ok]]
        return out

    eng._interoceptive_signal = spy
    for _ in range(1500):
        if not eng.step():
            break
    assert counts["sensed"] > 10_000
    assert counts["scenario"] > 10, counts          # переиспользование слота до следующего считывания бывает
    assert counts["silent"] == 0, counts            # и ни разу не прошло молча
    assert counts["mismatch_after"] == 0, counts    # birth_tick близнеца всегда равен записанному


def test_twin_birth_field_reset_on_birth_and_assignment():
    eng = Engine(Config(seed=5, intero_mode="twin"))
    eng.run(300)
    ids = eng.pop.ids()
    sensed = ids[eng.pop.age[ids] > 0]
    tw = eng.pop.twin[sensed]
    assert np.all(tw >= 0)
    # записанный birth_tick совпадает с birth_tick близнеца; расхождения возможны
    # только там, где близнец умер в конце этого тика и его слот уже занял
    # новорождённый (их не больше, чем новорождённых), и они снимаются на
    # следующем считывании (test_twin_birth_tick_guard_no_silent_slot_reuse)
    newborn = ids[eng.pop.age[ids] == 0]
    live = eng.pop.alive[tw]
    mismatch = eng.pop.birth_tick[tw[live]] != eng.pop.twin_birth[sensed[live]]
    assert mismatch.sum() <= newborn.size
    assert np.all(eng.pop.age[tw[live][mismatch]] == 0)
    assert np.all(eng.pop.twin[newborn] == -1) and np.all(eng.pop.twin_birth[newborn] == -1)


def test_non_twin_modes_untouched_by_twin_birth():
    """Поле twin_birth не обращается к генератору: self/shuffled/constant/off не
    меняются при его наличии (сравнение с прогоном, где поле заведомо не трогается)."""
    for mode in ("self", "shuffled", "constant", "off"):
        a = Engine(Config(seed=3, intero_mode=mode, interoception=(mode != "off"))); a.run(300)
        b = Engine(Config(seed=3, intero_mode=mode, interoception=(mode != "off")))
        b.pop.twin_birth[:] = 12345                 # мусор в поле не влияет ни на что вне twin
        b.run(300)
        assert _state(a) == _state(b), mode


# ------------------------------------------------------------ seed'ы
def test_seed_defaults_start_at_201():
    a2c, a2s, b2 = _load("a2_controls"), _load("a2_shock"), _load("daily_b2")
    assert a2c.SEED_START == 201 and a2s.SEED_START == 201 and b2.SEED_START == 201
    ja, jb = _load("journal_a2"), _load("journal_b2")
    assert ja.SEED_START == 201 and jb.SEED_START == 201
    # B2: план прогонов берёт только объявленные seed'ы, по порядку
    assert b2.plan_seeds([], 2, 40) == ([201, 202], set())
    rows = [dict(seed=201, label=c) for c in b2.CONDS] + [dict(seed=202, label="never")]
    rows += [dict(seed=5, label=c) for c in b2.CONDS]      # строка B1-нумерации не считается
    todo, done = b2.plan_seeds(rows, 2, 40)
    assert todo == [202, 203] and done == {201}
    full = [dict(seed=s, label=c) for s in range(201, 241) for c in b2.CONDS]
    assert b2.plan_seeds(full, 2, 40) == ([], set(range(201, 241)))
    # объявленные множества не пересекаются со старыми
    assert not set(range(201, 221)) & set(range(1, 57)) and not set(range(201, 241)) & set(range(1, 41))
