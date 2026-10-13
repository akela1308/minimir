"""Журнал A2 (13 октября 2026): на синтетических строках страница собирается,
промежуточных чисел не показывает, при полном наборе seed'ов считает сравнения."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "runs"))
sys.path.insert(0, str(ROOT))


def _load():
    spec = importlib.util.spec_from_file_location("journal_a2", ROOT / "runs" / "journal_a2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row(label, seed, mi, shock=None):
    r = dict(label=label, seed=seed, extinct=None, hit_ceiling=False, occupied_deciles=8,
             within_mi_200=mi, within_mi_1000=mi * 0.9, mi=mi * 0.5,
             within_n_200=500, within_n_1000=300)
    if shock is not None:
        r["shock"] = shock
    return r


def test_controls_incomplete_shows_no_numbers():
    j = _load()
    rows = [_row(c, s, 0.01) for s in (1, 2) for c in j.CONDS_1]
    st = j.analyse_controls(rows, target=5)
    assert st["complete"] is False and st["n_done"] == 2
    assert "comparisons" not in st and "conditions" not in st


def test_controls_complete_computes_paired_stats():
    j = _load()
    rng = np.random.default_rng(0)
    rows = []
    for s in range(1, 9):
        base = 0.02 + rng.normal(0, 0.002)
        rows += [_row("self", s, base + 0.02), _row("twin", s, base + 0.01),
                 _row("shuffled", s, base), _row("constant", s, base + 0.01), _row("off", s, base + 0.01)]
    st = j.analyse_controls(rows, target=8)
    assert st["complete"]
    c = st["comparisons"]["within_mi_200"]
    assert c["self_vs_twin"]["n"] == 8 and c["self_vs_twin"]["mean_diff"] > 0
    assert c["twin_vs_shuffled"]["n"] == 8
    assert st["verdict"] in ("self_effect_and_control_damage", "self_effect_only",
                             "control_damage_only", "neither")


def test_shock_complete_and_render(tmp_path):
    j = _load()
    rng = np.random.default_rng(1)

    def sh(resp):
        return dict(events=100, mode="x", n_shocked=1000, n_control=1000,
                    forage_response=resp + rng.normal(0, 0.005),
                    survival_response=resp / 2 + rng.normal(0, 0.005))
    rows = []
    for s in range(1, 7):
        for c in j.CONDS_2:
            for m in j.MODES_2:
                resp = 0.1 if (c == "self" and m == "abrupt") else 0.0
                rows.append(_row(f"{c}/{m}", s, 0.01, shock=sh(resp)))
    st = j.analyse_shock(rows, target=6)
    assert st["complete"] and st["verdict"] in j.VERDICTS_2
    state = dict(built_at="t", commit="x", frozen=False, target=6,
                 controls=j.analyse_controls([], 6), shock=st)
    html = j.render(state)
    assert "не заморожена" in html and "Часть 2" in html and "<table>" in html
    json.dumps(state)
