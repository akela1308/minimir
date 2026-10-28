"""Журнал A2 (13 октября 2026, правило решения и seed'ы 28 октября 2026): на
синтетических строках страница собирается, промежуточных чисел не показывает,
при полном наборе объявленных seed'ов считает сравнения по правилу «ДИ выше
delta_min и p < 0,01», sham проверяется против SE, survival описательна."""
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


def test_seed_defaults_moved_away_from_protocol_a_and_pilot():
    """28.10.2026: объявленные seed'ы 201..220, не 1..56 протокола A и не 101-103 пилота."""
    j = _load()
    assert j.SEED_START == 201
    seeds = j.declared_seeds(20)
    assert seeds == list(range(201, 221))
    assert not set(seeds) & set(range(1, 57)) and not set(seeds) & {101, 102, 103}


def test_controls_incomplete_shows_no_numbers():
    j = _load()
    s0 = j.SEED_START
    rows = [_row(c, s, 0.01) for s in (s0, s0 + 1) for c in j.CONDS_1]
    st = j.analyse_controls(rows, target=5)
    assert st["complete"] is False and st["n_done"] == 2
    assert "comparisons" not in st and "conditions" not in st
    # seed'ы 1..5 старой нумерации объявленными не считаются
    old = [_row(c, s, 0.01) for s in range(1, 6) for c in j.CONDS_1]
    assert j.analyse_controls(old, target=5)["n_done"] == 0


def test_controls_complete_computes_paired_stats():
    j = _load()
    rng = np.random.default_rng(0)
    rows = []
    for s in j.declared_seeds(8):
        base = 0.02 + rng.normal(0, 0.002)
        rows += [_row("self", s, base + 0.02), _row("twin", s, base + 0.01),
                 _row("shuffled", s, base), _row("constant", s, base + 0.01), _row("off", s, base + 0.01)]
    st = j.analyse_controls(rows, target=8)
    assert st["complete"]
    c = st["comparisons"]["within_mi_200"]
    assert c["self_vs_twin"]["n"] == 8 and c["self_vs_twin"]["mean_diff"] > 0
    for key in ("se", "dz", "ci_low", "ci_high", "boot_ci_low", "boot_ci_high", "p", "cliffs", "verdict"):
        assert key in c["self_vs_twin"]
    assert c["twin_vs_shuffled"]["n"] == 8
    assert st["verdict"] in j.VERDICTS_1
    assert set(st["hypotheses"]) == {"H-A2.1", "H-A2.2", "H-A2.3"}


def test_decision_rule_confirmed_undetermined_refuted():
    """Правило 28.10.2026 на синтетических парных разницах (n = 20, sd 0,02):
    ДИ целиком выше delta_min -> подтверждено; ДИ накрывает delta_min -> не
    определено; ДИ целиком ниже delta_min -> опровергнуто."""
    j = _load()
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 0.02, 20)
    noise -= noise.mean()                      # ровно заданное среднее
    delta = j.DELTA_MIN["within_mi_200"]        # 0,005

    def run(effect):
        d = effect + noise
        p = j.wilcoxon_p(d, np.zeros_like(d))
        return j.paired_summary(d, delta, p)

    big = run(0.03)
    assert big["verdict"] == "confirmed" and big["ci_low"] > delta and big["p"] < j.P_CONFIRM
    assert big["boot_ci_low"] > delta
    mid = run(0.005)
    assert mid["verdict"] == "undetermined" and mid["ci_low"] < delta < mid["ci_high"]
    low = run(-0.02)
    assert low["verdict"] == "refuted" and low["ci_high"] < delta
    # значимо, но мало: p < 0,01 при ДИ, накрывающем delta_min, это «не определено»
    tiny_noise = rng.normal(0, 0.004, 20); tiny_noise -= tiny_noise.mean()
    small = j.paired_summary(0.004 + tiny_noise, delta, 0.001)
    assert small["p"] < j.P_CONFIRM and small["verdict"] == "undetermined"
    # эквивалентность для H-A2.3: ДИ внутри (-delta, +delta); по правилу это
    # «опровергнуто» (весь ДИ ниже delta_min) плюс флаг within_delta
    eq = j.paired_summary(0.0005 + tiny_noise * 0.5, delta, 0.5)
    assert eq["within_delta"] and eq["verdict"] == "refuted"
    assert not big["within_delta"] and not low["within_delta"]
    # бутстреп воспроизводим при фиксированном генераторе
    assert j.bootstrap_ci(noise) == j.bootstrap_ci(noise)


def test_verdict_mapping_on_full_reading():
    j = _load()
    rng = np.random.default_rng(7)

    def world(self_minus_twin, twin_minus_shuffled, n=20):
        rows = []
        for s in j.declared_seeds(n):
            base = 0.03 + rng.normal(0, 0.003)
            e1, e2 = rng.normal(0, 0.004), rng.normal(0, 0.004)
            rows += [_row("shuffled", s, base), _row("twin", s, base + twin_minus_shuffled + e2),
                     _row("self", s, base + twin_minus_shuffled + e2 + self_minus_twin + e1),
                     _row("constant", s, base + 0.002), _row("off", s, base + 0.002)]
        return j.analyse_controls(rows, target=n)

    both = world(0.03, 0.03)
    assert both["verdict"] == "self_effect_and_control_damage"
    assert both["hypotheses"]["H-A2.1"] == "confirmed" and both["hypotheses"]["H-A2.2"] == "confirmed"
    only1 = world(0.03, -0.02)
    assert only1["verdict"] == "self_effect_only" and only1["hypotheses"]["H-A2.2"] == "refuted"
    neither = world(-0.02, -0.02)
    assert neither["verdict"] == "neither"
    unsure = world(0.004, -0.02)
    assert unsure["verdict"] == "undetermined" and unsure["hypotheses"]["H-A2.1"] == "undetermined"


def test_shock_complete_and_render(tmp_path):
    j = _load()
    rng = np.random.default_rng(1)

    def sh(resp, sham=False):
        # у sham удара нет: дефицит в конце окна около нуля (пилот: -1,2…+0,8)
        return dict(events=100, mode="x", n_shocked=1000, n_control=1000,
                    forage_response=resp + rng.normal(0, 0.005),
                    survival_response=resp / 2 + rng.normal(0, 0.005),
                    gap_closure=resp * 3 + rng.normal(0, 0.01),
                    accuracy_response=resp / 4 + rng.normal(0, 0.005),
                    energy_gap_end=(rng.normal(0, 0.5) if sham else (20 - resp * 60) + rng.normal(0, 0.2)))
    rows = []
    for s in j.declared_seeds(8):
        for c in j.CONDS_2:
            for m in j.MODES_2:
                resp = 0.1 if (c == "self" and m == "abrupt") else 0.0
                rows.append(_row(f"{c}/{m}", s, 0.01, shock=sh(resp, sham=(m == "sham"))))
    st = j.analyse_shock(rows, target=8)
    assert st["complete"] and st["verdict"] == "self_responds"
    # sham: |среднее| < 2 SE и ДИ содержит ноль
    sham = st["responses"]["self/sham:accuracy_response"]
    assert sham["sham_passed"] is True and sham["ci_includes_zero"] and sham["within_2se_of_zero"]
    assert all(v for v in st["sham_checks"].values())
    # H-A2.7 описательна: вердикта нет
    surv = st["comparisons"]["self_vs_shuffled:abrupt:survival"]
    assert surv["verdict"] == "descriptive" and surv["confirmed"] is None and surv["n"] == 8
    gap = st["comparisons"]["self_vs_shuffled:abrupt:gap"]
    assert gap["verdict"] == "confirmed" and gap["delta_min"] == j.DELTA_MIN_SHOCK
    state = dict(built_at="t", commit="x", frozen=False, target=8,
                 controls=j.analyse_controls([], 8), shock=st)
    html = j.render(state)
    assert "не заморожена" in html and "Часть 2" in html and "<table>" in html
    assert "201..208" in html
    json.dumps(state)


def test_sham_check_fails_on_biased_procedure():
    j = _load()
    rng = np.random.default_rng(3)

    def sh(bias):
        return dict(events=100, mode="x", n_shocked=1000, n_control=1000,
                    forage_response=0.0, survival_response=0.0, gap_closure=0.0,
                    accuracy_response=bias + rng.normal(0, 0.001),
                    energy_gap_end=rng.normal(0, 0.5))
    rows = []
    for s in j.declared_seeds(8):
        for c in j.CONDS_2:
            for m in j.MODES_2:
                rows.append(_row(f"{c}/{m}", s, 0.01, shock=sh(0.05 if m == "sham" else 0.0)))
    st = j.analyse_shock(rows, target=8)
    assert st["responses"]["self/sham:accuracy_response"]["sham_passed"] is False
    assert st["verdict"] == "procedure_artifact"
