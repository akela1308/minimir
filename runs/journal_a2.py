#!/usr/bin/env python3
"""Журнал протокола A2 (13 октября 2026): два новых контроля на входах 8-9 и
шок-проба. Читает runs/a2/controls.jsonl и runs/a2/shock.jsonl, пишет
docs/a2.json и docs/a2.html.

Правило чтения из PREREGISTRATION_A2: чтение одно, на объявленном числе seed'ов
(SEED_START..SEED_START+N-1, с 28.10.2026 это 201..220). Пока не все объявленные
seed'ы посчитаны во всех условиях части, страница показывает
только ход накопления (сколько seed'ов готово) и НЕ показывает ни Δ, ни p: так
промежуточного подгляда просто нет. Числа появляются один раз, когда часть
заполнена целиком.

Статистика по PREREGISTRATION_A2 §3-§6 (правило решения заменено 28.10.2026,
решение владельца; прежнее «|Δ| > 2 sd парных разниц» требовало dz > 2 и не
проходило ни на одном эффекте, который этот мир когда-либо давал):
  * метрика части 1: within_mi_200 (главная), within_mi_1000 (вторичная), mi
    (исследовательская); для каждого сравнения по seed'ам считаются парные
    разницы d_i, их среднее, sd, стандартная ошибка sd/sqrt(n), 95% ДИ
    (t-распределение; рядом перцентильный бутстреп по seed'ам, BOOT_N выборок,
    фиксированный генератор), парный Уилкоксон, дельта Клиффа и dz = mean/sd;
  * правило: «подтверждено», если весь 95% ДИ выше наименьшего интересующего
    эффекта DELTA_MIN и p < P_CONFIRM; «опровергнуто», если весь ДИ ниже
    DELTA_MIN; иначе «не определено»;
  * часть 2: gap_closure (главная), accuracy_response, survival_response
    (описательно, без вердикта с 28.10.2026) по условиям и режимам удара; парные
    сравнения self против shuffled и abrupt против slow в self тем же правилом с
    DELTA_MIN_SHOCK; sham обязан быть неотличим от нуля: |среднее| < 2 SE и ДИ
    содержит ноль.

  python runs/journal_a2.py            # пересобрать страницу
  python runs/journal_a2.py --target 20 --seed_start 201
"""
import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from runs.journal import read_jsonl, valid, cliffs_delta  # noqa: E402
from runs.journal import wilcoxon_p as _wilcoxon_p  # noqa: E402


def wilcoxon_p(a, b):
    """Как в journal.py, но nan (все разницы нулевые) отдаётся как None."""
    p = _wilcoxon_p(a, b)
    return None if (p is None or (isinstance(p, float) and math.isnan(p))) else p

CONTROLS = ROOT / "runs" / "a2" / "controls.jsonl"
SHOCK = ROOT / "runs" / "a2" / "shock.jsonl"
OUT_JSON = ROOT / "docs" / "a2.json"
OUT_HTML = ROOT / "docs" / "a2.html"
FROZEN = ROOT / "PREREGISTRATION_A2.md"            # появляется при заморозке

CONDS_1 = ["self", "shuffled", "twin", "constant", "off"]
METRICS_1 = ["within_mi_200", "within_mi_1000", "mi"]
CONDS_2 = ["self", "shuffled", "twin"]
MODES_2 = ["abrupt", "slow", "sham"]

# 28.10.2026, решение владельца (PREREGISTRATION_A2 §4). Наименьший интересующий
# эффект, в битах: ниже него разница между условиями считается не стоящей
# внимания, даже если статистически отлична от нуля. 0,005 для внутриагентной MI
# (четверть эффекта self − shuffled на 56 seed'ах протокола A, 0,0198) и 0,0025
# для популяционной MI (четверть её эффекта 0,0101). Достижимость при n = 20:
# runs/a2/attainability_check.py.
DELTA_MIN = {"within_mi_200": 0.005, "within_mi_1000": 0.005, "mi": 0.0025}
DELTA_MIN_SHOCK = 0.0       # часть 2: шкалы эффекта до чтения нет, порог ноль (§6)
P_CONFIRM = 0.01            # парный Уилкоксон, как на этапе 1
CI_LEVEL = 0.95
BOOT_N = 10_000             # перцентильный бутстреп по seed'ам
BOOT_SEED = 20261028        # фиксированный генератор: бутстреп воспроизводим
# 28.10.2026: объявленные seed'ы части 1 и части 2 это SEED_START..SEED_START+N-1.
# Seed'ы 1-56 заняты протоколом A, 101-103 пилотом 13.10; повторно не берутся.
SEED_START = 201


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


# ------------------------------------------------------------ статистика
def t_quantile(df, q=0.975):
    """Квантиль t-распределения; без scipy нормальное приближение 1,96."""
    try:
        from scipy.stats import t
        return float(t.ppf(q, df))
    except Exception:
        return 1.96


def bootstrap_ci(d, stat="mean", n_boot=BOOT_N, seed=BOOT_SEED, level=CI_LEVEL):
    """Перцентильный бутстреп по seed'ам (строкам d) с фиксированным генератором."""
    d = np.asarray(d, float)
    if d.size < 2:
        return None, None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, d.size, size=(n_boot, d.size))
    s = np.median(d[idx], axis=1) if stat == "median" else d[idx].mean(axis=1)
    lo, hi = 100 * (1 - level) / 2, 100 * (1 + level) / 2
    return float(np.percentile(s, lo)), float(np.percentile(s, hi))


def paired_summary(d, delta_min, p):
    """Сводка парных разниц d по seed'ам и правило решения 28.10.2026.

    Возвращает среднее, sd, SE = sd/sqrt(n), dz = mean/sd, 95% ДИ по
    t-распределению, бутстреп-ДИ (BOOT_N выборок, BOOT_SEED), p (передаётся
    снаружи: парный Уилкоксон) и вердикт:
      confirmed    весь ДИ выше delta_min и p < P_CONFIRM;
      refuted      весь ДИ ниже delta_min;
      undetermined иначе (ДИ накрывает delta_min, или p не прошёл).
    within_delta: весь ДИ внутри (-delta_min, +delta_min), то есть разницы
    в интересующем размере нет в обе стороны (для сравнений вида «A ≈ B»).
    """
    d = np.asarray(d, float)
    n = int(d.size)
    if n == 0:
        return dict(n=0)
    mean = float(d.mean())
    sd = float(d.std(ddof=1)) if n > 1 else None
    se = (sd / math.sqrt(n)) if sd is not None else None
    dz = (mean / sd) if (sd is not None and sd > 0) else None
    if se is not None:
        tq = t_quantile(n - 1, 0.5 + CI_LEVEL / 2)
        ci_low, ci_high = mean - tq * se, mean + tq * se
    else:
        ci_low = ci_high = None
    b_low, b_high = bootstrap_ci(d)
    if ci_low is not None and ci_low > delta_min and p is not None and p < P_CONFIRM:
        verdict = "confirmed"
    elif ci_high is not None and ci_high < delta_min:
        verdict = "refuted"
    else:
        verdict = "undetermined"
    return dict(n=n, mean_diff=mean, sd_diff=sd, se=se, dz=dz,
                ci_low=ci_low, ci_high=ci_high, boot_ci_low=b_low, boot_ci_high=b_high,
                p=p, delta_min=delta_min, verdict=verdict,
                significant=(p is not None and p < P_CONFIRM),
                confirmed=(verdict == "confirmed"),
                within_delta=(ci_low is not None and ci_low > -delta_min and ci_high < delta_min))


# ------------------------------------------------------------ часть 1
def paired(by, cond, base, metric):
    """Парное сравнение cond против base по seed'ам, годным в обоих (правило 28.10.2026)."""
    seeds = sorted(s for s in by.get(cond, {}) if s in by.get(base, {})
                   and valid(by[cond][s]) and valid(by[base][s])
                   and by[cond][s].get(metric) is not None
                   and by[base][s].get(metric) is not None)
    if not seeds:
        return dict(n=0)
    a = np.array([by[cond][s][metric] for s in seeds], float)
    b = np.array([by[base][s][metric] for s in seeds], float)
    out = paired_summary(a - b, DELTA_MIN.get(metric, DELTA_MIN["within_mi_200"]), wilcoxon_p(a, b))
    out["cliffs"] = cliffs_delta(a, b)
    return out


def declared_seeds(target, seed_start=SEED_START):
    """Объявленные seed'ы чтения: seed_start..seed_start+target-1 (28.10.2026)."""
    return list(range(seed_start, seed_start + target))


def analyse_controls(rows, target, seed_start=SEED_START):
    by = {c: {} for c in CONDS_1}
    for r in rows:
        if r.get("label") in by and r.get("seed") is not None and not r.get("error"):
            by[r["label"]][r["seed"]] = r
    done = sorted(s for s in declared_seeds(target, seed_start) if all(s in by[c] for c in CONDS_1))
    complete = len(done) == target
    state = dict(target=target, seed_start=seed_start, n_done=len(done), complete=complete,
                 rows=sum(len(v) for v in by.values()))
    state["validity"] = {c: dict(n=len(by[c]), valid=sum(1 for r in by[c].values() if valid(r)),
                                 extinct=sum(1 for r in by[c].values() if r.get("extinct") is not None),
                                 ceiling=sum(1 for r in by[c].values() if r.get("hit_ceiling")))
                         for c in CONDS_1}
    if not complete:
        return state
    state["conditions"] = {}
    for m in METRICS_1:
        state["conditions"][m] = {}
        for c in CONDS_1:
            vals = np.array([r[m] for r in by[c].values() if valid(r) and r.get(m) is not None], float)
            state["conditions"][m][c] = dict(
                n=int(vals.size), mean=float(vals.mean()) if vals.size else None,
                sd=float(vals.std(ddof=1)) if vals.size > 1 else None,
                median=float(np.median(vals)) if vals.size else None)
    state["comparisons"] = {m: {} for m in METRICS_1}
    for m in METRICS_1:
        for c in ("self", "twin", "constant", "off"):
            state["comparisons"][m][f"{c}_vs_shuffled"] = paired(by, c, "shuffled", m)
        state["comparisons"][m]["self_vs_twin"] = paired(by, "self", "twin", m)
        state["comparisons"][m]["constant_vs_off"] = paired(by, "constant", "off", m)
    # вердикты по главной метрике (§4 черновика, правило 28.10.2026)
    main = state["comparisons"]["within_mi_200"]
    h1v = main["self_vs_twin"].get("verdict", "undetermined")        # знание о себе
    h2v = main["twin_vs_shuffled"].get("verdict", "undetermined")    # вред шума
    h1, h2 = h1v == "confirmed", h2v == "confirmed"
    if h1 and h2:
        verdict = "self_effect_and_control_damage"
    elif h1:
        verdict = "self_effect_only"
    elif h2:
        verdict = "control_damage_only"
    elif h1v == "refuted" and h2v == "refuted":
        verdict = "neither"
    else:
        verdict = "undetermined"
    state["verdict"] = verdict
    state["hypotheses"] = {"H-A2.1": h1v, "H-A2.2": h2v,
                           # H-A2.3: constant ≈ off (within_delta) и оба > shuffled
                           "H-A2.3": dict(constant_vs_off=main["constant_vs_off"].get("verdict"),
                                          constant_equiv_off=main["constant_vs_off"].get("within_delta"),
                                          constant_vs_shuffled=main["constant_vs_shuffled"].get("verdict"),
                                          off_vs_shuffled=main["off_vs_shuffled"].get("verdict"))}
    state["twin_n_agents"] = {c: dict(n200=float(np.mean([r.get("within_n_200") or 0 for r in by[c].values()])),
                                      n1000=float(np.mean([r.get("within_n_1000") or 0 for r in by[c].values()])))
                              for c in CONDS_1}
    return state


# ------------------------------------------------------------ часть 2
def analyse_shock(rows, target, seed_start=SEED_START):
    by = {}
    for r in rows:
        if r.get("error") or r.get("seed") is None or not r.get("shock"):
            continue
        by.setdefault(r["label"], {})[r["seed"]] = r
    labels = [f"{c}/{m}" for c in CONDS_2 for m in MODES_2]
    present = [l for l in labels if l in by]
    done = (sorted(s for s in declared_seeds(target, seed_start) if all(s in by.get(l, {}) for l in present))
            if present else [])
    complete = bool(present) and len(done) == target
    state = dict(target=target, seed_start=seed_start, n_done=len(done), complete=complete, labels=present,
                 rows=sum(len(v) for v in by.values()))
    state["validity"] = {l: dict(n=len(by[l]), valid=sum(1 for r in by[l].values() if valid(r)),
                                 extinct=sum(1 for r in by[l].values() if r.get("extinct") is not None))
                         for l in present}
    if not complete:
        return state

    def vals(label, key):
        return {s: r["shock"].get(key) for s, r in by[label].items()
                if valid(r) and r["shock"].get(key) is not None}

    state["responses"] = {}
    # 14.10.2026, по пилоту: доля добывающих действий у этих популяций около 0,99,
    # запаса у неё нет; главная реакция теперь gap_closure (какая доля снятой
    # энергии восстановлена к концу окна), рядом accuracy_response (точность шага
    # к еде в окне), survival_response и старая forage_response для сопоставимости.
    for l in present:
        for key in ("gap_closure", "accuracy_response", "survival_response", "forage_response", "energy_gap_end"):
            v = np.array(list(vals(l, key).values()), float)
            st = dict(n=int(v.size), mean=float(v.mean()) if v.size else None,
                      sd=float(v.std(ddof=1)) if v.size > 1 else None,
                      se=None, ci_low=None, ci_high=None,
                      within_2se_of_zero=None, ci_includes_zero=None, sham_passed=None)
            if v.size > 1:
                # 28.10.2026: «нулевые» ожидания (sham) против стандартной ошибки
                # sd/sqrt(n) и 95% ДИ, а не против sd по seed'ам (его проходило всё)
                se = float(v.std(ddof=1) / math.sqrt(v.size))
                tq = t_quantile(v.size - 1, 0.5 + CI_LEVEL / 2)
                st.update(se=se, ci_low=float(v.mean() - tq * se), ci_high=float(v.mean() + tq * se))
                st["within_2se_of_zero"] = bool(abs(v.mean()) < 2 * se)
                st["ci_includes_zero"] = bool(st["ci_low"] <= 0.0 <= st["ci_high"])
                st["sham_passed"] = bool(st["within_2se_of_zero"] and st["ci_includes_zero"])
            state["responses"][f"{l}:{key}"] = st

    def pair(l1, l2, key, descriptive=False):
        a, b = vals(l1, key), vals(l2, key)
        seeds = sorted(set(a) & set(b))
        if not seeds:
            return dict(n=0)
        x = np.array([a[s] for s in seeds]); y = np.array([b[s] for s in seeds])
        out = paired_summary(x - y, DELTA_MIN_SHOCK, wilcoxon_p(x, y))
        if descriptive:
            # 28.10.2026: H-A2.7 (survival_response) описательна, вердикта нет:
            # выживание после снятия 20 единиц это метаболизм, не чтение сигнала
            out.update(verdict="descriptive", confirmed=None)
        return out

    cmp = {}
    for m in MODES_2:
        for key, short in (("gap_closure", "gap"), ("accuracy_response", "accuracy"),
                           ("survival_response", "survival"), ("forage_response", "forage")):
            desc = short == "survival"
            if f"self/{m}" in by and f"shuffled/{m}" in by:
                cmp[f"self_vs_shuffled:{m}:{short}"] = pair(f"self/{m}", f"shuffled/{m}", key, desc)
            if f"twin/{m}" in by and f"shuffled/{m}" in by:
                cmp[f"twin_vs_shuffled:{m}:{short}"] = pair(f"twin/{m}", f"shuffled/{m}", key, desc)
    if "self/abrupt" in by and "self/slow" in by:
        cmp["self:abrupt_vs_slow:gap"] = pair("self/abrupt", "self/slow", "gap_closure")
        cmp["self:abrupt_vs_slow:accuracy"] = pair("self/abrupt", "self/slow", "accuracy_response")
    state["comparisons"] = cmp

    # вердикты части 2 (§6 черновика): sham по energy_gap_end и accuracy_response
    # должен быть неотличим от нуля (H-A2.5: |среднее| < 2 SE и ДИ содержит ноль);
    # главная реакция gap_closure
    sham_checks = {f"{c}/sham:{k}": state["responses"].get(f"{c}/sham:{k}", {}).get("sham_passed")
                   for c in CONDS_2 if f"{c}/sham" in by
                   for k in ("energy_gap_end", "accuracy_response")}
    state["sham_checks"] = sham_checks
    sham_ok = all(v is not False for v in sham_checks.values())
    h4 = cmp.get("self_vs_shuffled:abrupt:gap", {}).get("confirmed", False)
    self_pos = state["responses"].get("self/abrupt:gap_closure", {})
    self_above_zero = bool(self_pos.get("mean") is not None and self_pos.get("sd") is not None
                           and self_pos["mean"] > 2 * self_pos["sd"] / math.sqrt(max(self_pos["n"], 1)))
    if not sham_ok:
        verdict = "procedure_artifact"
    elif h4 and self_above_zero:
        verdict = "self_responds"
    elif not self_above_zero:
        verdict = "no_response_in_self"
    else:
        verdict = "response_not_specific"
    state["verdict"] = verdict
    return state


# ------------------------------------------------------------ страница
VERDICTS_1 = {
    "accumulating": ("накопление, чтение не состоялось",
                     "Числа появятся один раз, когда все seed'ы посчитаны во всех условиях."),
    "self_effect_and_control_damage": ("знание о себе есть, и контроль этапа 1 был завышен",
                                       "self > twin и twin > shuffled по обоим критериям."),
    "self_effect_only": ("знание о себе есть, shuffled был честным контролем",
                         "self > twin, а twin ≈ shuffled."),
    "control_damage_only": ("весь разрыв этапа 1 был вредом контролю",
                            "twin > shuffled, а self ≈ twin."),
    "neither": ("ни эффекта, ни вреда контролю",
                "Оба ДИ целиком ниже наименьшего интересующего эффекта: ни знания о себе, ни вреда контролю."),
    "undetermined": ("не определено",
                     "Ни одно из двух сравнений не подтверждено, и хотя бы одно не опровергнуто: "
                     "ДИ накрывает наименьший интересующий эффект. Данных для решения не хватило."),
}
VERDICTS_2 = {
    "accumulating": ("накопление, чтение не состоялось", ""),
    "procedure_artifact": ("процедура негодна", "sham даёт ненулевую реакцию."),
    "self_responds": ("агенты в self реагируют на удар, в shuffled нет", "H-A2.4 прошла."),
    "no_response_in_self": ("реакции в self нет", "Граница провала 1 части 2: MI измеряет не опору на сигнал."),
    "response_not_specific": ("реакция есть, но не специфична условию", "self не отличается от shuffled."),
}


def fmt(x, d=4):
    return "·" if x is None else f"{x:.{d}f}"


def fmt_p(p):
    if p is None:
        return "·"
    return "&lt;0.0001" if p < 0.0001 else f"{p:.4f}"


def fmt_ci(cc, lo="ci_low", hi="ci_high", d=4):
    if cc.get(lo) is None or cc.get(hi) is None:
        return "·"
    return f"[{cc[lo]:.{d}f}; {cc[hi]:.{d}f}]"


VERDICT_WORDS = {"confirmed": ("yes", "подтверждено"), "refuted": ("no", "опровергнуто"),
                 "undetermined": ("muted", "не определено"), "descriptive": ("muted", "описательно")}


def fmt_verdict(v):
    cls, word = VERDICT_WORDS.get(v, ("muted", "·"))
    return f'<td class="{cls}">{word}</td>'


def render(st):
    c1, c2 = st["controls"], st["shock"]
    v1 = VERDICTS_1["accumulating" if not c1["complete"] else c1["verdict"]]
    v2 = VERDICTS_2["accumulating" if not c2["complete"] else c2["verdict"]]
    frozen = st["frozen"]

    def bar(n, t):
        pct = min(100, round(100 * n / t)) if t else 0
        return f'<p class="big">{n} из {t} seed\'ов</p><div class="bar"><i style="width:{pct}%"></i></div>'

    rows1 = ""
    if c1["complete"]:
        for m in METRICS_1:
            for c in CONDS_1:
                s = c1["conditions"][m][c]
                rows1 += (f"<tr><td class=\"mono\">{m}</td><td class=\"mono\">{c}</td>"
                          f"<td>{fmt(s['mean'])}</td><td>{fmt(s['sd'])}</td><td>{s['n']}</td></tr>")
        cmp1 = ""
        for m in METRICS_1:
            for name, cc in c1["comparisons"][m].items():
                if not cc.get("n"):
                    continue
                cmp1 += (f"<tr><td class=\"mono\">{m}</td><td class=\"mono\">{name.replace('_vs_', ' vs ')}</td>"
                         f"<td>{fmt(cc['mean_diff'])}</td><td>{fmt_ci(cc)}</td><td>{fmt_ci(cc, 'boot_ci_low', 'boot_ci_high')}</td>"
                         f"<td>{fmt_p(cc['p'])}</td><td>{fmt(cc.get('cliffs'), 3)}</td><td>{fmt(cc.get('dz'), 2)}</td>"
                         f"<td>{fmt(cc.get('delta_min'))}</td>{fmt_verdict(cc.get('verdict'))}<td>{cc['n']}</td></tr>")
    else:
        cmp1 = ""
    val1 = "".join(f"<tr><td class=\"mono\">{c}</td><td>{v['n']}</td><td>{v['valid']}</td>"
                   f"<td>{v['extinct']}</td><td>{v['ceiling']}</td></tr>" for c, v in c1["validity"].items())

    rows2 = ""
    cmp2 = ""
    if c2["complete"]:
        for k, s in c2["responses"].items():
            sham = s.get("sham_passed")
            rows2 += (f"<tr><td class=\"mono\">{k}</td><td>{fmt(s['mean'])}</td><td>{fmt(s['sd'])}</td>"
                      f"<td>{fmt(s.get('se'))}</td><td>{fmt_ci(s)}</td>"
                      f"<td>{'' if sham is None else ('да' if sham else 'нет')}</td>"
                      f"<td>{s['n']}</td></tr>")
        for k, cc in c2["comparisons"].items():
            if not cc.get("n"):
                continue
            cmp2 += (f"<tr><td class=\"mono\">{k}</td><td>{fmt(cc['mean_diff'])}</td><td>{fmt_ci(cc)}</td>"
                     f"<td>{fmt_p(cc['p'])}</td><td>{fmt(cc.get('dz'), 2)}</td>"
                     f"{fmt_verdict(cc.get('verdict'))}<td>{cc['n']}</td></tr>")
    val2 = "".join(f"<tr><td class=\"mono\">{l}</td><td>{v['n']}</td><td>{v['valid']}</td><td>{v['extinct']}</td></tr>"
                   for l, v in c2["validity"].items())

    freeze_note = ("" if frozen else
                   '<p class="note"><b>Предрегистрация A2 не заморожена.</b> Файл '
                   '<span class="mono">PREREGISTRATION_A2.md</span> ещё не существует, есть только '
                   'черновик. Прогоны по протоколу до заморозки не считаются.</p>')

    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>mini·world: протокол A2, контроли и шок-проба</title>
<meta name="robots" content="noindex">
<style>
:root{{--ground:#0a0e11;--panel:#10161a;--hair:#1c262c;--ink:#e9f1f2;--dim:#93a6ae;--faint:#5b6f77;
  --cyan:#46c6d0;--amber:#e8734a;--coop:#4fd08a;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(1200px 700px at 70% -10%,#101a1f 0%,var(--ground) 55%);
  color:var(--ink);font-family:var(--mono);line-height:1.55}}
.wrap{{max-width:900px;margin:0 auto;padding:24px 20px 70px}}
header{{border-bottom:1px solid var(--hair);padding-bottom:14px;margin-bottom:22px}}
.eyebrow{{font-size:11px;letter-spacing:2.5px;text-transform:uppercase;color:var(--faint)}}
h1{{font-size:22px;margin:6px 0 4px;font-weight:600}}
h2{{font-size:15px;margin:34px 0 10px;color:var(--cyan);font-weight:600}}
p{{color:var(--dim);font-size:13px}} a{{color:var(--cyan)}}
nav a{{font-size:12px;border:1px solid #2a3a41;border-radius:16px;padding:4px 10px;text-decoration:none;margin-right:6px;display:inline-block}}
.card{{background:#0d1317;border:1px solid var(--hair);border-radius:10px;padding:16px 18px;margin:14px 0}}
.big{{font-size:19px;color:var(--ink);margin:0 0 6px}}
.bar{{height:6px;background:#161f24;border-radius:3px;overflow:hidden;margin:12px 0 6px}} .bar i{{display:block;height:100%;background:var(--cyan)}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}}
th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid #161f24}}
th{{color:var(--faint);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.6px}}
th:first-child,td:first-child{{text-align:left}} .mono{{color:var(--ink)}}
.yes{{color:var(--coop)}} .no{{color:var(--amber)}} .muted{{color:var(--faint);font-size:12px}}
.note{{border-left:2px solid var(--amber);padding-left:12px;color:var(--dim)}}
</style>
</head>
<body><div class="wrap">
<header>
<div class="eyebrow">mini·world · протокол A2</div>
<h1>Два новых контроля на входах 8-9 и шок-проба</h1>
<nav><a href="index.html">живой эксперимент</a><a href="journal.html">журнал</a><a href="results-b.html">эксперимент 2</a><a href="about.html">о проекте</a></nav>
</header>
{freeze_note}
<p>Зачем: главное сравнение этапа 1 (self против shuffled) смешивало пользу знания о себе
с вредом от шума на входе, потому что shuffled берёт энергию нового случайного агента каждый
тик и разрушает временную структуру сигнала. Контроль twin сохраняет распределение и
автокорреляцию, constant даёт ненулевой вход без информации. Шок-проба меряет реакцию на
экзогенный удар по энергии, а не корреляцию. Протокол:
<a href="https://github.com/akela1308/minimir/blob/main/PREREGISTRATION_A2_черновик.md">предрегистрация A2</a>.
Чтение одно, на seed'ах {c1.get("seed_start", SEED_START)}..{c1.get("seed_start", SEED_START) + c1["target"] - 1};
промежуточных чисел страница не показывает.</p>

<h2>Часть 1: контроли</h2>
<div class="card">{bar(c1["n_done"], c1["target"])}
<p class="big">{v1[0]}</p><p>{v1[1]}</p></div>
<table><tr><th>условие</th><th>строк</th><th>годных</th><th>вымерло</th><th>потолок</th></tr>{val1}</table>
{"<h2>Условия</h2><table><tr><th>метрика</th><th>условие</th><th>среднее</th><th>sd</th><th>n</th></tr>" + rows1 + "</table>" if c1["complete"] else ""}
{"<h2>Парные сравнения</h2><p>Правило 28.10.2026: подтверждено, если весь 95% ДИ парных разниц выше наименьшего интересующего эффекта δ_min и p &lt; 0,01; опровергнуто, если весь ДИ ниже δ_min; иначе не определено.</p><table><tr><th>метрика</th><th>сравнение</th><th>Δ</th><th>95% ДИ (t)</th><th>ДИ бутстреп</th><th>p</th><th>Клифф</th><th>dz</th><th>δ_min</th><th>вердикт</th><th>пар</th></tr>" + cmp1 + "</table>" if c1["complete"] else ""}

<h2>Часть 2: шок-проба</h2>
<div class="card">{bar(c2["n_done"], c2["target"])}
<p class="big">{v2[0]}</p><p>{v2[1]}</p></div>
<table><tr><th>условие / удар</th><th>строк</th><th>годных</th><th>вымерло</th></tr>{val2}</table>
{"<h2>Реакции</h2><table><tr><th>условие / удар : метрика</th><th>среднее</th><th>sd</th><th>SE</th><th>95% ДИ</th><th>sham: ноль (|ср.| &lt; 2 SE и ДИ содержит 0)</th><th>n</th></tr>" + rows2 + "</table>" if c2["complete"] else ""}
{"<h2>Парные сравнения</h2><p>То же правило, δ_min = 0 (§6); survival_response описательно, без вердикта.</p><table><tr><th>сравнение</th><th>Δ</th><th>95% ДИ (t)</th><th>p</th><th>dz</th><th>вердикт</th><th>пар</th></tr>" + cmp2 + "</table>" if c2["complete"] else ""}

<footer><p class="muted">Собрано {st["built_at"]} · код {st.get("commit") or "·"} · сырые числа:
<a href="https://github.com/akela1308/minimir/tree/main/runs/a2">runs/a2/</a></p></footer>
</div></body></html>'''


def build(target, seed_start=SEED_START):
    rows_c = read_jsonl(CONTROLS)
    rows_s = read_jsonl(SHOCK)
    state = dict(built_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 commit=git_commit(), frozen=FROZEN.exists(), target=target, seed_start=seed_start,
                 delta_min=DELTA_MIN, delta_min_shock=DELTA_MIN_SHOCK, p_confirm=P_CONFIRM,
                 controls=analyse_controls(rows_c, target, seed_start),
                 shock=analyse_shock(rows_s, target, seed_start))
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    with open(OUT_HTML, "w") as f:
        f.write(render(state))
    print(f"A2 часть 1: seed'ов {state['controls']['n_done']}/{target}, "
          f"{'чтение' if state['controls']['complete'] else 'накопление'}")
    print(f"A2 часть 2: seed'ов {state['shock']['n_done']}/{target}, "
          f"{'чтение' if state['shock']['complete'] else 'накопление'}")
    print(f"записано: {OUT_HTML}, {OUT_JSON}")
    return state


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=int, default=20, help="объявленное число seed'ов")
    p.add_argument("--seed_start", type=int, default=SEED_START,
                   help="первый объявленный seed (28.10.2026: 201, чтобы не брать seed'ы протокола A и пилота)")
    args = p.parse_args()
    build(args.target, args.seed_start)
