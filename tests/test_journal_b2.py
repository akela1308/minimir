"""Журнал B2 (13 октября 2026): на синтетических строках страница собирается,
чисел до завершённого чтения не показывает, при полном чтении считает три
критерия и вердикт по PREREGISTRATION_B2_черновик.md §4-§5."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "runs"))
sys.path.insert(0, str(ROOT))


def _load():
    spec = importlib.util.spec_from_file_location("journal_b2", ROOT / "runs" / "journal_b2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row(label, seed, lr_end, marker_end, lr_read, marker_read, extinct=None, first_switch=5600,
         dead_lr=0.1, ceiling=0.1):
    curve = []
    for t in range(2000, 100001, 2000):
        at_read = t >= first_switch + 10_000
        curve.append(dict(tick=t, pop=200, lr_median=(lr_read if at_read else 0.1),
                          marker_median=(marker_read if at_read else 0.1),
                          dead_n=50, dead_lr_median=dead_lr, dead_age_median=300.0, dead_marker_median=0.1))
        if extinct is not None and t >= extinct:
            break
    return dict(label=label, seed=seed, extinct=extinct, first_switch=first_switch,
                lr_median=lr_end, marker_median=marker_end, lr_init=0.1, marker_init=0.1,
                lr_at_ceiling=ceiling, eat_accuracy=0.9, curve=curve)


def _world(rng, n, effect=True, benefit=True):
    rows = []
    for s in range(1, n + 1):
        drift = float(np.exp(rng.normal(0, 0.15)))          # маркер гуляет вокруг 0,1
        never = 0.1 * float(np.exp(rng.normal(0, 0.2)))
        life_lr = (3.0 if effect else 0.1) * float(np.exp(rng.normal(0, 0.1)))
        # без пользы обучения life_frozen выживает так же, как life (расходящихся пар нет)
        frozen_dead = benefit and s % 2 == 0
        rows += [
            _row("never", s, never, 0.1 * drift, never, 0.1 * drift),
            _row("slow", s, never * 1.1, 0.1 * drift, never, 0.1 * drift),
            _row("fast", s, never, 0.1 * drift, never, 0.1 * drift, extinct=(6000 if s % 3 == 0 else None)),
            _row("life", s, life_lr, 0.1 * drift, life_lr, 0.1 * drift, dead_lr=0.05),
            _row("life_frozen", s, 0.1, 0.1 * drift, 0.1, 0.1 * drift, extinct=(6000 if frozen_dead else None)),
            _row("never_frozen", s, 0.1 * drift, 0.1 * drift, 0.1 * drift, 0.1 * drift),
        ]
    return rows


def test_incomplete_reading_shows_no_numbers(tmp_path):
    j = _load()
    rows = _world(np.random.default_rng(0), 7)
    j.SRC = tmp_path / "x.jsonl"
    with open(j.SRC, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    st = j.build_state()
    assert st["n_done"] == 7 and st["readings"] == {} and st["latest_reading"] is None
    html = j.render(st)
    assert "накопление" in html and "Критерии H-B2.1" not in html and "не заморожена" in html
    json.dumps(st)


def test_complete_reading_confirmed_and_verdicts():
    j = _load()
    rows = _world(np.random.default_rng(1), 20)
    st = j.analyse(rows, 20)
    assert st["criterion1"]["n"] >= 12 and st["criterion1"]["passed"]
    assert st["criterion2"]["n"] == 20 and st["criterion2"]["passed"]
    assert st["criterion3"]["b"] == 10 and st["criterion3"]["c"] == 0 and st["criterion3"]["passed"]
    assert st["verdict"] == "confirmed"
    assert st["descriptive"]["alive_over_dead_lr_median"] > 1

    no_benefit = j.analyse(_world(np.random.default_rng(2), 20, benefit=False), 20)
    assert no_benefit["verdict"] == "growth_without_benefit"

    no_effect = j.analyse(_world(np.random.default_rng(3), 20, effect=False), 20)
    assert no_effect["verdict"] in ("not_distinguishable", "signal_within_drift")

    small = j.analyse(_world(np.random.default_rng(4), 10), 10)
    # 10 seed'ов: пар life/never ровно 10 < 12, критерий 1 не считается
    assert small["verdict"] == "blind"


def test_render_with_reading(tmp_path):
    j = _load()
    rows = _world(np.random.default_rng(5), 20)
    j.SRC = tmp_path / "x.jsonl"
    with open(j.SRC, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    st = j.build_state()
    assert st["latest_reading"] == 20 and sorted(st["readings"]) == ["10", "20"]
    html = j.render(st)
    assert "Чтение на 20 seed'ах" in html and "Критерии H-B2.1" in html and "<table>" in html
