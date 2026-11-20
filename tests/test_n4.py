"""Протокол N4 (20.11.2026): одна смена на фиксированном тике, развилка мира,
критерии как код. Проверяется, что новое не трогает старое и что каждый
критерий способен и пройти, и провалиться."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs"))

from sim.config import Config                       # noqa: E402
from sim.engine import Engine                       # noqa: E402
from sim.protocol_b import config_b                 # noqa: E402
from sim import protocol_n4 as n4                   # noqa: E402
import n4_analyze as an                             # noqa: E402

SMALL = dict(grid_h=48, grid_w=48, init_pop=40, max_pop=600)


def test_switch_once_fires_exactly_once():
    cfg = config_b(7, "never", switch_once_at=300, **SMALL)
    eng = Engine(cfg)
    eng.run(299)
    assert eng.world.switches == []
    eng.run(1)
    assert eng.world.switches == [300]
    good = eng.world.good_type
    eng.run(900)
    assert eng.world.switches == [300]          # второй смены нет
    assert eng.world.good_type == good


def test_switch_once_off_by_default_is_bit_identical():
    """Без опции мир B считается как раньше: поле switch_once_at ничего не тратит."""
    a = Engine(config_b(7, "life", **SMALL)); a.run(400)
    b = Engine(config_b(7, "life", switch_once_at=0, **SMALL)); b.run(400)
    assert a.pop.count == b.pop.count
    assert np.array_equal(a.pop.E[a.pop.ids()], b.pop.E[b.pop.ids()])
    assert np.array_equal(a.world.resource, b.world.resource)


def test_switch_once_rejects_schedule():
    try:
        Config(food_types=2, taste=True, switch_mean=600, switch_once_at=300)
    except ValueError:
        return
    raise AssertionError("switch_once_at вместе с switch_mean должны отвергаться")


def test_forks_share_history_and_differ_only_by_intervention():
    eng = n4.warmup(11, shift=400, **SMALL)
    assert eng.tick == 399 and eng.world.switches == []
    ids = eng.pop.ids()
    lr0 = eng.pop.taste_lr[ids].copy()
    assert np.allclose(lr0, n4.L0)               # до развилки скорость у всех одна
    c = n4.conditions()
    a, _ = n4.fork(eng, c["D_L1.5"])
    b, _ = n4.fork(eng, c["V_s1"])
    # исходный мир не тронут
    assert np.allclose(eng.pop.taste_lr[ids], n4.L0)
    # всё, кроме скорости обучения, у копий совпадает
    for attr in ("E", "taste", "taste_g", "x", "y", "age"):
        assert np.array_equal(getattr(a.pop, attr)[ids], getattr(b.pop, attr)[ids]), attr
    assert np.array_equal(a.world.resource, b.world.resource)
    assert np.allclose(a.pop.taste_lr[ids], 1.5)
    assert b.pop.taste_lr[ids].std() > 0


def test_variation_scales_the_same_z():
    """У одной особи z один во всех условиях части V: sigma только растягивает."""
    eng = n4.warmup(11, shift=400, **SMALL)
    ids = eng.pop.ids()
    c = n4.conditions()
    a, _ = n4.fork(eng, c["V_s0.5"])
    b, _ = n4.fork(eng, c["V_s1"])
    la, lb = np.log(a.pop.taste_lr[ids] / n4.L0), np.log(b.pop.taste_lr[ids] / n4.L0)
    inside = (b.pop.taste_lr[ids] < 3.9)         # не упёрлись в потолок гена
    assert np.allclose(lb[inside], 2.0 * la[inside], atol=1e-4)


def test_fork_is_deterministic():
    r1 = n4.measure_seed(11, conds=["D_L1.5", "V_s1.5"], ticks=900, shift=400, **SMALL)
    r2 = n4.measure_seed(11, conds=["D_L1.5", "V_s1.5"], ticks=900, shift=400, **SMALL)
    for x, y in zip(r1, r2):
        assert x["rescued"] == y["rescued"] and x["pop_end"] == y["pop_end"]
        assert x["curve"] == y["curve"]


def test_frozen_fork_does_not_learn():
    eng = n4.warmup(11, shift=400, **SMALL)
    clone, _ = n4.fork(eng, n4.conditions()["F_s2"])
    before = clone.pop.taste[clone.pop.ids()].copy()
    ids0 = clone.pop.ids()
    clone.run(30)
    still = clone.pop.alive[ids0] & (clone.pop.age[ids0] >= 30)
    assert np.array_equal(clone.pop.taste[ids0][still], before[still])


# ------------------------------------------------------------ критерии как код
def _table(n, probs, rng, comonotone=True):
    """Синтетика: probs = {условие: вероятность спасения}."""
    u = rng.random(n)
    y = {}
    for c, p in probs.items():
        draw = u if comonotone else rng.random(n)
        y[c] = {s: int(draw[s] < p) for s in range(n)}
    return y


FLAT = {c: 0.3 for c in an.D_ALL + an.V_ALL + [m for m, _ in an.M_MID] + [an.F_COND]}
RISING = dict(FLAT)
RISING.update({"D_L0.1": 0.0, "D_L0.3": 0.0, "D_L0.45": 0.05, "D_L0.6": 0.25, "D_L0.8": 0.45,
               "D_L1": 0.55, "D_L1.5": 0.6, "D_L2.5": 0.65, "D_L4": 0.65,
               "V_s0.5": 0.0, "V_s1": 0.15, "V_s1.5": 0.35, "V_s2": 0.5,
               "M_L0.45": 0.0, "M_L0.6": 0.05, "M_L0.8": 0.2, "M_L1": 0.3,
               "F_s2": 0.0})


def test_perm_trend_sees_trend_and_ignores_flat():
    rng = np.random.default_rng(1)
    up = np.array([[int(rng.random() < p) for p in (0.0, 0.2, 0.5, 0.8)] for _ in range(60)], float)
    flat = np.array([[int(rng.random() < 0.4) for _ in range(4)] for _ in range(60)], float)
    assert an.perm_trend(up, n_perm=2000)[1] < 0.01
    assert an.perm_trend(flat, n_perm=2000)[1] > 0.05


def test_mcnemar_matches_known_values():
    assert abs(an.mcnemar_exact(8, 0) - 0.0078125) < 1e-9
    assert an.mcnemar_exact(5, 5) == 1.0
    assert an.mcnemar_exact(0, 0) == 1.0


def test_every_criterion_can_pass_and_can_fail():
    rng = np.random.default_rng(2)
    good = an.evaluate(_table(150, RISING, rng))
    assert good["K1"]["verdict"] == "подтверждено"
    assert good["K2"]["verdict"] == "подтверждено"
    assert good["K3"]["verdict"] == "подтверждено"
    assert good["K4"]["verdict"] == "мягче хуже"
    assert good["F"]["verdict"] == "чисто"

    rng = np.random.default_rng(3)
    null = an.evaluate(_table(150, FLAT, rng, comonotone=False))
    assert null["K1"]["verdict"] != "подтверждено"
    assert null["K3"]["verdict"] != "подтверждено"
    assert null["K4"]["verdict"] not in ("мягче хуже", "мягче лучше")
    assert null["F"]["verdict"] != "чисто"

    sharp = dict(RISING, **{"D_L0.6": 0.0, "D_L1.5": 1.0})
    assert an.evaluate(_table(150, sharp, np.random.default_rng(4)))["K2"]["verdict"] == "опровергнуто"

    better = dict(RISING, **{"M_L0.45": 0.5, "M_L0.6": 0.7, "M_L0.8": 0.9, "M_L1": 0.95})
    assert an.evaluate(_table(150, better, np.random.default_rng(5)))["K4"]["verdict"] == "мягче лучше"
    same = dict(RISING, **{m: RISING[d] for m, d in an.M_MID})
    assert an.evaluate(_table(400, same, np.random.default_rng(6)))["K4"]["verdict"] == "тяжесть не решает"


def test_small_world_at_fork_is_excluded(monkeypatch):
    """Семя, где к развилке меньше MIN_FORK_POP особей, даёт одну строку
    EXCLUDED, и в таблицу критериев она не попадает."""
    monkeypatch.setattr(n4, "MIN_FORK_POP", 10 ** 6)
    rows = n4.measure_seed(301, conds=["D_L0.1"], ticks=260, shift=200)
    assert len(rows) == 1 and rows[0]["label"] == "EXCLUDED" and rows[0]["rescued"] is None


def test_confirmatory_table_takes_first_valid_seeds_and_refuses_gaps():
    conds = ["A", "B"]
    def row(seed, label, resc=1):
        return dict(seed=seed, label=label, rescued=resc)
    rows = [row(s, c) for s in (401, 402, 404, 405, 406) for c in conds]
    rows.append(dict(seed=403, label="EXCLUDED", rescued=None))
    rows += [row(300, c) for c in conds]                  # пилотное семя не берётся
    table, info = an.confirmatory_table(rows, conds, 401, 4)
    assert sorted(table["A"]) == [401, 402, 404, 405] and info["excluded"] == [403]
    # не хватает семян
    assert an.confirmatory_table(rows, conds, 401, 6)[0] is None
    # пропуск: семя 403 не посчитано и не исключено
    rows2 = [r for r in rows if r["label"] != "EXCLUDED"]
    table2, info2 = an.confirmatory_table(rows2, conds, 401, 4)
    assert table2 is None and info2["gaps"] == [403]
    # недосчитанное семя не считается годным
    rows3 = rows + [row(407, "A")]
    assert an.confirmatory_table(rows3, conds, 401, 6)[0] is None


def test_next_seeds_fills_gaps_and_replaces_excluded():
    import n4_run as nr
    conds = ["A", "B"]
    full = lambda s: {f"A|seed{s}", f"B|seed{s}"}
    have = full(401) | full(402) | {"EXCLUDED|seed403", "A|seed405"} | full(300)
    # 401, 402 годны; 403 негодно; 404 не начато; 405 недосчитано
    assert nr.next_seeds(have, conds, 401, 4) == [404, 405]
    assert nr.next_seeds(have, conds, 401, 2) == []
    assert nr.next_seeds(set(), conds, 401, 3) == [401, 402, 403]
    done = have | full(404) | full(405)
    assert nr.next_seeds(done, conds, 401, 4) == []
    assert nr.next_seeds(done, conds, 401, 5) == [406]


def test_page_builds_in_every_state_without_leftover_placeholders():
    """Страница опыта: пять языков, числа подставлены, длинных тире нет."""
    import json
    import re
    import build_n4_page as bp
    y, _ = an.load_table(bp.PILOT)
    sh = bp.shares(y)
    att = json.load(open(bp.ROOT / "runs/n4/attainability.json"))
    for st in ("draft", "frozen"):
        html_text = bp.page(sh, att, st)
        assert html_text.count('<div class="langblock"') == 5
        assert not re.search(r"\{[a-z_0-9]+\}", html_text.split("<script>")[0].split("</style>")[1])
        assert "—" not in html_text
        assert html_text.count('<section id="results">') == 5
