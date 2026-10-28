#!/usr/bin/env python3
"""Журнал протокола A2 (13 октября 2026): два новых контроля на входах 8-9 и
шок-проба. Читает runs/a2/controls.jsonl и runs/a2/shock.jsonl, пишет
docs/a2.json и docs/a2.html.

Правило чтения из PREREGISTRATION_A2: чтение одно, на объявленном числе seed'ов.
Пока не все seed'ы 1..N посчитаны во всех условиях части, страница показывает
только ход накопления (сколько seed'ов готово) и НЕ показывает ни Δ, ни p: так
промежуточного подгляда просто нет. Числа появляются один раз, когда часть
заполнена целиком.

Статистика по PREREGISTRATION_A2 §3-§6:
  * метрика части 1: within_mi_200 (главная), within_mi_1000 (вторичная), mi
    (исследовательская); парный Уилкоксон по seed'ам против shuffled, дельта
    Клиффа, 2σ ПАРНЫХ разниц (не разброс уровней);
  * часть 2: forage_response и survival_response по условиям и режимам удара,
    парные тесты self против shuffled и abrupt против slow в self; sham обязан
    быть неотличим от нуля.

  python runs/journal_a2.py            # пересобрать страницу
  python runs/journal_a2.py --target 20
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


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


# ------------------------------------------------------------ часть 1
def paired(by, cond, base, metric):
    """Парное сравнение cond против base по seed'ам, годным в обоих."""
    seeds = sorted(s for s in by.get(cond, {}) if s in by.get(base, {})
                   and valid(by[cond][s]) and valid(by[base][s])
                   and by[cond][s].get(metric) is not None
                   and by[base][s].get(metric) is not None)
    if not seeds:
        return dict(n=0)
    a = np.array([by[cond][s][metric] for s in seeds], float)
    b = np.array([by[base][s][metric] for s in seeds], float)
    d = a - b
    sd_d = float(d.std(ddof=1)) if d.size > 1 else None
    p = wilcoxon_p(a, b)
    two_sigma = 2 * sd_d if sd_d is not None else None
    return dict(n=int(d.size), mean_diff=float(d.mean()), p=p,
                cliffs=cliffs_delta(a, b), two_sigma_paired=two_sigma,
                exceeds=(two_sigma is not None and abs(float(d.mean())) > two_sigma),
                significant=(p is not None and p < 0.01),
                confirmed=(p is not None and p < 0.01 and two_sigma is not None
                           and abs(float(d.mean())) > two_sigma))


def analyse_controls(rows, target):
    by = {c: {} for c in CONDS_1}
    for r in rows:
        if r.get("label") in by and r.get("seed") is not None and not r.get("error"):
            by[r["label"]][r["seed"]] = r
    done = sorted(s for s in range(1, target + 1) if all(s in by[c] for c in CONDS_1))
    complete = len(done) == target
    state = dict(target=target, n_done=len(done), complete=complete,
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
    # вердикты по главной метрике (§4 черновика)
    main = state["comparisons"]["within_mi_200"]
    h1 = main["self_vs_twin"].get("confirmed", False)          # знание о себе
    h2 = main["twin_vs_shuffled"].get("confirmed", False)      # вред шума
    if h1 and h2:
        verdict = "self_effect_and_control_damage"
    elif h1:
        verdict = "self_effect_only"
    elif h2:
        verdict = "control_damage_only"
    else:
        verdict = "neither"
    state["verdict"] = verdict
    state["twin_n_agents"] = {c: dict(n200=float(np.mean([r.get("within_n_200") or 0 for r in by[c].values()])),
                                      n1000=float(np.mean([r.get("within_n_1000") or 0 for r in by[c].values()])))
                              for c in CONDS_1}
    return state


# ------------------------------------------------------------ часть 2
def analyse_shock(rows, target):
    by = {}
    for r in rows:
        if r.get("error") or r.get("seed") is None or not r.get("shock"):
            continue
        by.setdefault(r["label"], {})[r["seed"]] = r
    labels = [f"{c}/{m}" for c in CONDS_2 for m in MODES_2]
    present = [l for l in labels if l in by]
    done = sorted(s for s in range(1, target + 1) if all(s in by.get(l, {}) for l in present)) if present else []
    complete = bool(present) and len(done) == target
    state = dict(target=target, n_done=len(done), complete=complete, labels=present,
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
            state["responses"][f"{l}:{key}"] = dict(
                n=int(v.size), mean=float(v.mean()) if v.size else None,
                sd=float(v.std(ddof=1)) if v.size > 1 else None,
                # sham и любые «нулевые» ожидания: |среднее| против 2σ по seed'ам
                within_2sd_of_zero=(bool(abs(v.mean()) < 2 * v.std(ddof=1)) if v.size > 1 else None))

    def pair(l1, l2, key):
        a, b = vals(l1, key), vals(l2, key)
        seeds = sorted(set(a) & set(b))
        if not seeds:
            return dict(n=0)
        x = np.array([a[s] for s in seeds]); y = np.array([b[s] for s in seeds])
        d = x - y
        two = 2 * float(d.std(ddof=1)) if d.size > 1 else None
        p = wilcoxon_p(x, y)
        return dict(n=int(d.size), mean_diff=float(d.mean()), p=p, two_sigma_paired=two,
                    confirmed=(p is not None and p < 0.01 and two is not None and abs(float(d.mean())) > two))

    cmp = {}
    for m in MODES_2:
        for key, short in (("gap_closure", "gap"), ("accuracy_response", "accuracy"),
                           ("survival_response", "survival"), ("forage_response", "forage")):
            if f"self/{m}" in by and f"shuffled/{m}" in by:
                cmp[f"self_vs_shuffled:{m}:{short}"] = pair(f"self/{m}", f"shuffled/{m}", key)
            if f"twin/{m}" in by and f"shuffled/{m}" in by:
                cmp[f"twin_vs_shuffled:{m}:{short}"] = pair(f"twin/{m}", f"shuffled/{m}", key)
    if "self/abrupt" in by and "self/slow" in by:
        cmp["self:abrupt_vs_slow:gap"] = pair("self/abrupt", "self/slow", "gap_closure")
        cmp["self:abrupt_vs_slow:accuracy"] = pair("self/abrupt", "self/slow", "accuracy_response")
    state["comparisons"] = cmp

    # вердикты части 2 (§6 черновика): sham по energy_gap_end и accuracy_response
    # должен быть неотличим от нуля; главная реакция gap_closure
    sham_ok = all(state["responses"].get(f"{c}/sham:{k}", {}).get("within_2sd_of_zero", True)
                  for c in CONDS_2 if f"{c}/sham" in by
                  for k in ("energy_gap_end", "accuracy_response"))
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
    "neither": ("ни эффекта, ни вреда контролю", "Ни одно из двух сравнений не прошло двойной критерий."),
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
                cls = "yes" if cc.get("confirmed") else "no"
                cmp1 += (f"<tr><td class=\"mono\">{m}</td><td class=\"mono\">{name.replace('_vs_', ' vs ')}</td>"
                         f"<td>{fmt(cc['mean_diff'])}</td><td>{fmt_p(cc['p'])}</td><td>{fmt(cc.get('cliffs'), 3)}</td>"
                         f"<td>{fmt(cc.get('two_sigma_paired'))}</td>"
                         f"<td class=\"{cls}\">{'да' if cc.get('confirmed') else 'нет'}</td><td>{cc['n']}</td></tr>")
    else:
        cmp1 = ""
    val1 = "".join(f"<tr><td class=\"mono\">{c}</td><td>{v['n']}</td><td>{v['valid']}</td>"
                   f"<td>{v['extinct']}</td><td>{v['ceiling']}</td></tr>" for c, v in c1["validity"].items())

    rows2 = ""
    cmp2 = ""
    if c2["complete"]:
        for k, s in c2["responses"].items():
            rows2 += (f"<tr><td class=\"mono\">{k}</td><td>{fmt(s['mean'])}</td><td>{fmt(s['sd'])}</td>"
                      f"<td>{'' if s['within_2sd_of_zero'] is None else ('да' if s['within_2sd_of_zero'] else 'нет')}</td>"
                      f"<td>{s['n']}</td></tr>")
        for k, cc in c2["comparisons"].items():
            if not cc.get("n"):
                continue
            cls = "yes" if cc.get("confirmed") else "no"
            cmp2 += (f"<tr><td class=\"mono\">{k}</td><td>{fmt(cc['mean_diff'])}</td><td>{fmt_p(cc['p'])}</td>"
                     f"<td>{fmt(cc.get('two_sigma_paired'))}</td>"
                     f"<td class=\"{cls}\">{'да' if cc.get('confirmed') else 'нет'}</td><td>{cc['n']}</td></tr>")
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
Чтение одно, промежуточных чисел страница не показывает.</p>

<h2>Часть 1: контроли</h2>
<div class="card">{bar(c1["n_done"], c1["target"])}
<p class="big">{v1[0]}</p><p>{v1[1]}</p></div>
<table><tr><th>условие</th><th>строк</th><th>годных</th><th>вымерло</th><th>потолок</th></tr>{val1}</table>
{"<h2>Условия</h2><table><tr><th>метрика</th><th>условие</th><th>среднее</th><th>sd</th><th>n</th></tr>" + rows1 + "</table>" if c1["complete"] else ""}
{"<h2>Парные сравнения</h2><table><tr><th>метрика</th><th>сравнение</th><th>Δ</th><th>p</th><th>Клифф</th><th>2σ парных</th><th>подтв.</th><th>пар</th></tr>" + cmp1 + "</table>" if c1["complete"] else ""}

<h2>Часть 2: шок-проба</h2>
<div class="card">{bar(c2["n_done"], c2["target"])}
<p class="big">{v2[0]}</p><p>{v2[1]}</p></div>
<table><tr><th>условие / удар</th><th>строк</th><th>годных</th><th>вымерло</th></tr>{val2}</table>
{"<h2>Реакции</h2><table><tr><th>условие / удар : метрика</th><th>среднее</th><th>sd</th><th>в 2σ от нуля</th><th>n</th></tr>" + rows2 + "</table>" if c2["complete"] else ""}
{"<h2>Парные сравнения</h2><table><tr><th>сравнение</th><th>Δ</th><th>p</th><th>2σ парных</th><th>подтв.</th><th>пар</th></tr>" + cmp2 + "</table>" if c2["complete"] else ""}

<footer><p class="muted">Собрано {st["built_at"]} · код {st.get("commit") or "·"} · сырые числа:
<a href="https://github.com/akela1308/minimir/tree/main/runs/a2">runs/a2/</a></p></footer>
</div></body></html>'''


def build(target):
    rows_c = read_jsonl(CONTROLS)
    rows_s = read_jsonl(SHOCK)
    state = dict(built_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 commit=git_commit(), frozen=FROZEN.exists(), target=target,
                 controls=analyse_controls(rows_c, target),
                 shock=analyse_shock(rows_s, target))
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
    args = p.parse_args()
    build(args.target)
