#!/usr/bin/env python3
"""Журнал наблюдений: пересчёт статистики по всему накопленному и сборка страницы.

Читает замороженный датасет отчёта (runs/compare.jsonl, 12 seed'ов) плюс всё,
что накопил суточный прогон (runs/daily/compare_ext.jsonl), применяет те же
критерии годности и тот же двойной критерий подтверждения, что и
runs/analyze_compare.py, и пишет:

  runs/daily/journal.jsonl — по строке на дату прогона: что добавилось,
                             сколько стало, какие числа получились;
  docs/journal.json        — машинное состояние на текущий момент;
  docs/journal.html        — человеческая страница журнала.

О честности промежуточных чтений. Данные копятся, и статистику соблазнительно
пересчитывать каждый день — но многократный подгляд с остановкой «как только
стало значимо» завышает долю ложных срабатываний. Поэтому объявлено заранее:
подтверждающих чтения два — на 20 seed'ах (объём предрегистрации по числу
seed'ов) и на 40 (пункт 2а из REPORT.md §6). Все прочие значения на странице
помечены как промежуточные и заявкой не являются.
"""
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FROZEN = ROOT / "runs" / "compare.jsonl"
EXT = ROOT / "runs" / "daily" / "compare_ext.jsonl"
JOURNAL = ROOT / "runs" / "daily" / "journal.jsonl"
OUT_JSON = ROOT / "docs" / "journal.json"
OUT_HTML = ROOT / "docs" / "journal.html"

CONDS = ["self", "shuffled", "neighbour", "off"]
CHECKPOINTS = [20, 40]
TARGET = 40
FROZEN_DATE = "2026-07-26"     # ночная сессия, из которой взяты первые 12 seed'ов
METRIC = "within_mi"           # главная метрика: внутриагентная


# ------------------------------------------------------------------ утилиты
def read_jsonl(path):
    rows = []
    if not Path(path).exists():
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def valid(r):
    return (not r.get("error") and r.get("extinct") is None
            and not r.get("hit_ceiling") and (r.get("occupied_deciles") or 0) >= 4)


def wilcoxon_p(a, b):
    """Парный Уилкоксон. scipy если есть, иначе нормальное приближение."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    if a.size < 5:
        return None
    try:
        from scipy.stats import wilcoxon
        return float(wilcoxon(a, b)[1])
    except Exception:
        d = a - b
        d = d[d != 0]
        if d.size == 0:
            return None
        r = np.argsort(np.argsort(np.abs(d))) + 1
        w = min(r[d > 0].sum(), r[d < 0].sum())
        n = d.size
        mu = n * (n + 1) / 4
        sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
        z = (w - mu) / sd if sd else 0.0
        return float(math.erfc(abs(z) / math.sqrt(2)))


def cliffs_delta(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not a.size or not b.size:
        return None
    gt = (a[:, None] > b[None, :]).sum()
    lt = (a[:, None] < b[None, :]).sum()
    return float((gt - lt) / (a.size * b.size))


def analyse(rows, metric=METRIC, seed_limit=None):
    """Полная статистика по набору строк. seed_limit — считать только seed<=N."""
    by = {c: {} for c in CONDS}
    for r in rows:
        if r.get("label") in by and r.get("seed") is not None:
            if seed_limit is None or r["seed"] <= seed_limit:
                by[r["label"]][r["seed"]] = r

    stats = {}
    for c in CONDS:
        good = [r for r in by[c].values() if valid(r)]
        vals = np.array([r.get(metric) for r in good
                         if r.get(metric) is not None], float)
        stats[c] = dict(
            n_total=len(by[c]), n_valid=len(good),
            mean=float(vals.mean()) if vals.size else None,
            sd=float(vals.std(ddof=1)) if vals.size > 1 else None,
            median=float(np.median(vals)) if vals.size else None,
            extinct=sum(1 for r in by[c].values() if r.get("extinct") is not None),
            ceiling=sum(1 for r in by[c].values() if r.get("hit_ceiling")),
        )

    two_sigma = 2 * stats["self"]["sd"] if stats["self"]["sd"] else None

    # парные сравнения на seed'ах, годных в ОБОИХ условиях
    comparisons = {}
    ctrl = {s: r for s, r in by["shuffled"].items() if valid(r)}
    for c in ("self", "neighbour", "off"):
        pairs = [(by[c][s].get(metric), ctrl[s].get(metric))
                 for s in sorted(by[c])
                 if s in ctrl and valid(by[c][s])
                 and by[c][s].get(metric) is not None
                 and ctrl[s].get(metric) is not None]
        if not pairs:
            comparisons[c] = dict(n=0)
            continue
        a = [p[0] for p in pairs]
        b = [p[1] for p in pairs]
        p = wilcoxon_p(a, b)
        diff = float(np.mean(a) - np.mean(b))
        exceeds = two_sigma is not None and abs(diff) > two_sigma
        comparisons[c] = dict(
            n=len(pairs), p=p, mean_diff=diff,
            cliffs=cliffs_delta(np.array(a), np.array(b)),
            exceeds_2sigma=bool(exceeds),
            confirmed=bool(p is not None and p < 0.01 and exceeds))

    n_complete = len({s for s in by["self"]
                      if all(s in by[c] and not by[c][s].get("error") for c in CONDS)})
    return dict(metric=metric, n_seeds=n_complete, conditions=stats,
                two_sigma=two_sigma, comparisons=comparisons)


def verdict_key(state):
    """Один из четырёх исходов главного сравнения self vs shuffled."""
    c = state["comparisons"].get("self", {})
    if not c.get("n"):
        return "nodata"
    if c.get("confirmed"):
        return "confirmed"
    if c.get("p") is not None and c["p"] < 0.01:
        return "signal_within_noise"   # парный сигнал есть, но не выше 2σ
    return "not_distinguishable"


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=ROOT, stderr=subprocess.DEVNULL
                                       ).decode().strip()
    except Exception:
        return None


# --------------------------------------------------------------- построение
def build():
    frozen = read_jsonl(FROZEN)
    ext = read_jsonl(EXT)
    allrows = frozen + ext

    state = analyse(allrows)
    state_pop = analyse(allrows, metric="mi")
    state["verdict"] = verdict_key(state)
    state["target"] = TARGET
    state["checkpoints"] = CHECKPOINTS
    state["built_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["commit"] = git_commit()
    state["population_metric"] = state_pop

    # кривая накопления: как менялись Δ и p по мере роста N
    seeds_done = sorted({r["seed"] for r in allrows
                         if r.get("seed") is not None and not r.get("error")})
    curve = []
    for n in seeds_done:
        if n < 5:
            continue
        s = analyse(allrows, seed_limit=n)
        c = s["comparisons"].get("self", {})
        if not c.get("n"):
            continue
        curve.append(dict(n_seeds=s["n_seeds"], mean_diff=c.get("mean_diff"),
                          p=c.get("p"), two_sigma=s.get("two_sigma"),
                          confirmed=c.get("confirmed")))
    state["curve"] = curve

    # журнал по датам
    dates = {}
    for r in ext:
        d = (r.get("run_date") or "")[:10]
        if d:
            dates.setdefault(d, set()).add(r.get("seed"))
    entries = [dict(date=FROZEN_DATE, seeds=sorted({r["seed"] for r in frozen
                                                    if r.get("seed") is not None}),
                    source="ночная сессия (REPORT.md, блок A.5)")]
    seen = list(frozen)
    for d in sorted(dates):
        seen += [r for r in ext if (r.get("run_date") or "")[:10] == d]
        s = analyse(seen)
        c = s["comparisons"].get("self", {})
        entries.append(dict(date=d, seeds=sorted(x for x in dates[d] if x is not None),
                            source="автоматический суточный прогон",
                            n_seeds=s["n_seeds"], mean_diff=c.get("mean_diff"),
                            p=c.get("p"), two_sigma=s.get("two_sigma"),
                            verdict=verdict_key(s)))
    # дополним первую запись числами
    s0 = analyse(frozen)
    c0 = s0["comparisons"].get("self", {})
    entries[0].update(n_seeds=s0["n_seeds"], mean_diff=c0.get("mean_diff"),
                      p=c0.get("p"), two_sigma=s0.get("two_sigma"),
                      verdict=verdict_key(s0))
    state["entries"] = entries

    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)

    html = render(state)
    with open(OUT_HTML, "w") as f:
        f.write(html)
    print(f"seed'ов: {state['n_seeds']}/{TARGET}, вердикт: {state['verdict']}")
    print(f"записано: {OUT_HTML}, {OUT_JSON}, {JOURNAL}")
    return state


# ------------------------------------------------------------------ страница
def fmt(x, digits=4):
    return "—" if x is None else f"{x:.{digits}f}"


def fmt_p(p):
    if p is None:
        return "—"
    if p < 0.0001:
        return "&lt;0.0001"
    return f"{p:.4f}"


def svg_curve(curve, target):
    """Накопление: Δ(self − shuffled) и коридор ±2σ по мере роста N."""
    if len(curve) < 2:
        return '<p class="muted">Кривая появится, когда наберётся больше точек.</p>'
    W, H = 720, 260
    pad_l, pad_r, pad_t, pad_b = 56, 16, 18, 34
    ns = [c["n_seeds"] for c in curve]
    xmin, xmax = min(ns), max(max(ns), target)
    vals = []
    for c in curve:
        if c["mean_diff"] is not None:
            vals.append(c["mean_diff"])
        if c["two_sigma"]:
            vals += [c["two_sigma"], -c["two_sigma"]]
    if not vals:
        return ""
    ymax = max(abs(v) for v in vals) * 1.25 or 1e-6
    ymin = -ymax

    def X(n):
        return pad_l + (n - xmin) / max(1, xmax - xmin) * (W - pad_l - pad_r)

    def Y(v):
        return pad_t + (ymax - v) / (ymax - ymin) * (H - pad_t - pad_b)

    band = []
    for c in curve:
        if c["two_sigma"]:
            band.append((X(c["n_seeds"]), Y(c["two_sigma"])))
    band_lo = []
    for c in reversed(curve):
        if c["two_sigma"]:
            band_lo.append((X(c["n_seeds"]), Y(-c["two_sigma"])))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in band + band_lo)

    line = " ".join(f"{X(c['n_seeds']):.1f},{Y(c['mean_diff']):.1f}"
                    for c in curve if c["mean_diff"] is not None)
    dots = "".join(
        f'<circle cx="{X(c["n_seeds"]):.1f}" cy="{Y(c["mean_diff"]):.1f}" r="3.2" '
        f'fill="{"#4fd08a" if c.get("confirmed") else "#46c6d0"}"/>'
        for c in curve if c["mean_diff"] is not None)

    ticks = ""
    step = max(2, (xmax - xmin) // 8 or 1)
    for n in range(xmin, xmax + 1, step):
        ticks += (f'<text x="{X(n):.1f}" y="{H - 12}" class="ax" '
                  f'text-anchor="middle">{n}</text>')
    cps = ""
    for cp in CHECKPOINTS:
        if xmin <= cp <= xmax:
            near_edge = X(cp) > W - pad_r - 70
            anchor = "end" if near_edge else "middle"
            tx = X(cp) - 4 if near_edge else X(cp)
            cps += (f'<line x1="{X(cp):.1f}" y1="{pad_t}" x2="{X(cp):.1f}" '
                    f'y2="{H - pad_b}" class="cp"/>'
                    f'<text x="{tx:.1f}" y="{pad_t + 10}" class="ax cpl" '
                    f'text-anchor="{anchor}">чтение N={cp}</text>')

    return f'''<svg viewBox="0 0 {W} {H}" class="chart" role="img">
  <polygon points="{poly}" fill="#46c6d022" stroke="none"/>
  <line x1="{pad_l}" y1="{Y(0):.1f}" x2="{W - pad_r}" y2="{Y(0):.1f}" class="zero"/>
  {cps}
  <polyline points="{line}" fill="none" stroke="#46c6d0" stroke-width="1.6"/>
  {dots}
  <text x="6" y="{pad_t + 8}" class="ax">{ymax:+.3f}</text>
  <text x="6" y="{Y(0) + 4:.1f}" class="ax">0</text>
  <text x="6" y="{H - pad_b:.1f}" class="ax">{ymin:+.3f}</text>
  {ticks}
</svg>'''


VERDICTS = {
    "confirmed": ("подтверждено",
                  "Разрыв между self и shuffled прошёл оба критерия сразу: "
                  "p&lt;0.01 по парному тесту И превышение 2σ межсидового шума."),
    "signal_within_noise": ("не подтверждено — сигнал внутри шума",
                            "Внутри каждого seed'а self стабильно выше контроля "
                            "(парный тест значим), но разрыв меньше 2σ разброса "
                            "между seed'ами. По объявленному двойному критерию "
                            "это не заявка."),
    "not_distinguishable": ("неотличимо от контроля",
                            "Ни парный тест, ни размер разрыва не выделяют self "
                            "на фоне подменённого сигнала."),
    "nodata": ("данных пока нет", "Годных парных прогонов недостаточно."),
}


def render(st):
    c = st["comparisons"].get("self", {})
    vlabel, vtext = VERDICTS[st["verdict"]]
    n = st["n_seeds"]
    pct = min(100, round(100 * n / st["target"]))
    interim = n not in CHECKPOINTS and n < st["target"]

    rows_cond = ""
    for cond in CONDS:
        s = st["conditions"][cond]
        rows_cond += (
            f"<tr><td class=\"mono\">{cond}</td><td>{fmt(s['mean'])}</td>"
            f"<td>{fmt(s['sd'])}</td><td>{fmt(s['median'])}</td>"
            f"<td>{s['n_valid']}/{s['n_total']}</td></tr>")

    rows_cmp = ""
    for cond in ("self", "neighbour", "off"):
        cc = st["comparisons"].get(cond, {})
        if not cc.get("n"):
            continue
        mark = "да" if cc.get("confirmed") else "нет"
        cls = "yes" if cc.get("confirmed") else "no"
        rows_cmp += (
            f"<tr><td class=\"mono\">{cond} vs shuffled</td>"
            f"<td>{fmt(cc.get('mean_diff'))}</td><td>{fmt_p(cc.get('p'))}</td>"
            f"<td>{fmt(cc.get('cliffs'), 3)}</td>"
            f"<td>{'&gt;2σ' if cc.get('exceeds_2sigma') else '&lt;2σ'}</td>"
            f"<td class=\"{cls}\">{mark}</td><td>{cc['n']}</td></tr>")

    rows_j = ""
    for e in reversed(st["entries"]):
        vl = VERDICTS.get(e.get("verdict", "nodata"), ("—", ""))[0]
        seeds = e.get("seeds") or []
        srange = (f"{min(seeds)}–{max(seeds)}" if len(seeds) > 1
                  else (str(seeds[0]) if seeds else "—"))
        rows_j += (
            f"<tr><td class=\"mono\">{e['date']}</td><td>{srange}</td>"
            f"<td>{e.get('n_seeds', '—')}</td>"
            f"<td>{fmt(e.get('mean_diff'))}</td><td>{fmt_p(e.get('p'))}</td>"
            f"<td>{fmt(e.get('two_sigma'))}</td><td>{vl}</td></tr>")

    chart = svg_curve(st["curve"], st["target"])
    pop = st["population_metric"]["comparisons"].get("self", {})

    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>mini·world — журнал наблюдений</title>
<meta name="description" content="Автономный накопительный эксперимент mini·world:
суточные прогоны, статистика по мере накопления seed'ов, объявленные заранее
контрольные чтения.">
<link rel="icon" href="favicon.svg">
<style>
:root{{--ground:#0a0e11;--panel:#10161a;--hair:#1c262c;--ink:#e9f1f2;
  --dim:#93a6ae;--faint:#5b6f77;--cyan:#46c6d0;--amber:#e8734a;--coop:#4fd08a;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(1200px 700px at 70% -10%,#101a1f 0%,var(--ground) 55%);
  color:var(--ink);font-family:var(--mono);line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:900px;margin:0 auto;padding:24px 20px 70px}}
header{{border-bottom:1px solid var(--hair);padding-bottom:14px;margin-bottom:22px}}
.eyebrow{{font-size:11px;letter-spacing:2.5px;text-transform:uppercase;color:var(--faint)}}
h1{{font-size:22px;margin:6px 0 4px;font-weight:600}}
h2{{font-size:15px;margin:34px 0 10px;color:var(--cyan);font-weight:600;
  letter-spacing:.3px}}
p{{color:var(--dim);font-size:13px}}
a{{color:var(--cyan)}}
nav a{{font-size:12px;border:1px solid #2a3a41;border-radius:16px;
  padding:4px 10px;text-decoration:none;margin-right:6px;display:inline-block}}
.card{{background:#0d1317;border:1px solid var(--hair);border-radius:10px;
  padding:16px 18px;margin:14px 0}}
.big{{font-size:19px;color:var(--ink);margin:0 0 6px}}
.bar{{height:6px;background:#161f24;border-radius:3px;overflow:hidden;margin:12px 0 6px}}
.bar i{{display:block;height:100%;background:var(--cyan)}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}}
th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid #161f24}}
th{{color:var(--faint);font-weight:500;font-size:11px;text-transform:uppercase;
  letter-spacing:.6px}}
th:first-child,td:first-child{{text-align:left}}
.mono{{color:var(--ink)}}
.yes{{color:var(--coop)}} .no{{color:var(--amber)}}
.muted{{color:var(--faint);font-size:12px}}
.note{{border-left:2px solid var(--amber);padding-left:12px;color:var(--dim);
  font-size:12.5px}}
.chart{{width:100%;height:auto;margin:8px 0 4px}}
.ax{{fill:var(--faint);font-size:9px;font-family:var(--mono)}}
.zero{{stroke:#2a3a41;stroke-width:1}}
.cp{{stroke:#e8734a55;stroke-width:1;stroke-dasharray:3 3}}
.cpl{{fill:#e8734a99}}
footer{{margin-top:40px;border-top:1px solid var(--hair);padding-top:14px;
  font-size:11.5px;color:var(--faint)}}
</style>
</head>
<body><div class="wrap">
<header>
  <div class="eyebrow">искусственная жизнь · журнал наблюдений</div>
  <h1>mini·world — что накопилось</h1>
  <nav style="margin-top:10px">
    <a href="index.html">живой эксперимент</a>
    <a href="sim.html">записанный прогон</a>
    <a href="about.html">о проекте</a>
    <a href="https://github.com/akela1308/minimir">исходники</a>
  </nav>
</header>

<p>Эта страница собирается машиной. Раз в сутки на серверах GitHub запускается
движок мира, добавляет новые независимые прогоны к главному сравнению и
пересчитывает статистику по всему накопленному. Никто при этом не должен
сидеть с открытой вкладкой: <a href="index.html">живой эксперимент</a> на
главной — это то, что считается у вас в браузере и исчезает вместе с ним,
а здесь — то, что остаётся.</p>

<div class="card">
  <p class="big">{n} из {st['target']} seed'ов</p>
  <div class="bar"><i style="width:{pct}%"></i></div>
  <p class="muted">Главная метрика — внутриагентная взаимная информация между
  энергией и действием. Условия: <b>self</b> (агент видит свои энергию и
  возраст), <b>shuffled</b> (те же входы, подменённые от чужого агента),
  <b>neighbour</b> (входы соседа), <b>off</b> (входы занулены).</p>
</div>

<h2>Текущее чтение</h2>
<div class="card">
  <p class="big">{vlabel}</p>
  <p>{vtext}</p>
  <p class="muted">Δ(self − shuffled) = <b>{fmt(c.get('mean_diff'))}</b> бит,
  p = <b>{fmt_p(c.get('p'))}</b>, 2σ межсидового шума =
  <b>{fmt(st.get('two_sigma'))}</b>, пар: {c.get('n', 0)}.
  По исследовательской популяционной метрике: Δ = {fmt(pop.get('mean_diff'))},
  p = {fmt_p(pop.get('p'))}.</p>
</div>
{'<p class="note"><b>Это промежуточное чтение, а не результат.</b> Заранее объявлено, что подтверждающих чтения два — на 20 и на 40 seed’ах. Пересчёт после каждой добавленной порции показан ради прозрачности: если остановиться в момент, когда цифра случайно понравилась, доля ложных срабатываний вырастет. Поэтому промежуточные значения ничего не заявляют.</p>' if interim else ''}

<h2>Как менялся разрыв по мере накопления</h2>
{chart}
<p class="muted">Линия — разница средних между self и контролем. Полоса —
коридор ±2σ разброса между seed'ами: пока линия внутри полосы, разрыв
неотличим от того, насколько миры отличаются друг от друга просто по
случайности старта. Пунктиром — объявленные контрольные чтения.</p>

<h2>Условия сейчас</h2>
<table>
<tr><th>условие</th><th>среднее</th><th>sd</th><th>медиана</th><th>годных</th></tr>
{rows_cond}
</table>
<p class="muted">Прогон считается негодным, если популяция вымерла, упёрлась в
потолок численности или заняла меньше четырёх энергетических децилей —
критерии заданы до прогонов и применяются автоматически.</p>

<h2>Парные сравнения с контролем</h2>
<table>
<tr><th>сравнение</th><th>Δ средних</th><th>p</th><th>Клифф</th><th>против 2σ</th>
<th>подтв.</th><th>пар</th></tr>
{rows_cmp}
</table>

<h2>Журнал прогонов</h2>
<table>
<tr><th>дата</th><th>seed'ы</th><th>всего</th><th>Δ</th><th>p</th><th>2σ</th>
<th>чтение</th></tr>
{rows_j}
</table>
<p class="muted">Сырые числа по каждому прогону лежат в репозитории:
<a href="https://github.com/akela1308/minimir/blob/main/runs/daily/compare_ext.jsonl">runs/daily/compare_ext.jsonl</a>
(новые seed'ы) и
<a href="https://github.com/akela1308/minimir/blob/main/runs/compare.jsonl">runs/compare.jsonl</a>
(замороженные двенадцать из ночной сессии). Каждая строка несёт дату, хеш
коммита и seed — любой прогон воспроизводится этими тремя числами.</p>

<footer>
Собрано {st['built_at']} · код {st.get('commit') or '—'} ·
протокол A5-120k-blockavg-v1 · метод и критерии —
<a href="https://github.com/akela1308/minimir/blob/main/PREREGISTRATION.md">предрегистрация</a>,
<a href="https://github.com/akela1308/minimir/blob/main/REPORT.md">отчёт ночной сессии</a>
</footer>
</div></body></html>
'''


if __name__ == "__main__":
    build()
