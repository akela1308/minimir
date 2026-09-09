#!/usr/bin/env python3
"""Журнал протокола B («Когда выгодно учиться»): статистика и HTML-секция.

Читает runs/daily/protocol_b.jsonl (суточный прогон runs/daily_b.py),
считает по всему накопленному то, что объявлено в PREREGISTRATION_B.md,
и отдаёт машинное состояние (docs/journal_b.json) плюс HTML-фрагмент,
который runs/journal.py вставляет в общую страницу журнала.

Главный результат: скорость обучения вкуса (ген, медиана по живым в конце
прогона) в мире со сменой правила раз в жизнь (life) против стационарного
мира (never), парно по seed'ам, на логарифмической шкале. Двойной критерий:
парный Уилкоксон p<0.01 И разница медиан log10 больше 2σ разброса log10
скорости в условии never_frozen (нейтральный дрейф гена, который ни на что
не влияет). Объявленные чтения: 10, 20, 40 seed'ов.
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "runs" / "daily" / "protocol_b.jsonl"
OUT_JSON = ROOT / "docs" / "journal_b.json"

CONDS = ["never", "slow", "life", "fast", "life_frozen", "never_frozen"]
COND_RU = dict(never="правило не меняется", slow="смена раз в ~5000 тиков",
               life="смена раз в ~600 тиков (одна жизнь)",
               fast="смена раз в ~150 тиков", life_frozen="смена раз в ~600, обучение отключено",
               never_frozen="не меняется, обучение отключено")
CHECKPOINTS = [10, 20, 40]
TARGET = 40
PROTOCOL = "B1-100k-v1"


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


def wilcoxon_p(a, b):
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


def log_lr(r):
    v = r.get("lr_median")
    if v is None or v <= 0:
        return None
    return math.log10(v)


def alive(r):
    return not r.get("error") and r.get("extinct") is None


def analyse(rows, seed_limit=None):
    by = {c: {} for c in CONDS}
    for r in rows:
        if r.get("label") in by and r.get("seed") is not None and not r.get("error"):
            if seed_limit is None or r["seed"] <= seed_limit:
                by[r["label"]][r["seed"]] = r

    conds = {}
    for c in CONDS:
        rs = list(by[c].values())
        ok = [r for r in rs if alive(r)]
        ll = np.array([log_lr(r) for r in ok if log_lr(r) is not None], float)
        acc = np.array([r["eat_accuracy"] for r in ok if r.get("eat_accuracy") is not None], float)
        dip = np.array([r["min_pop_after_switch"] for r in ok
                        if r.get("min_pop_after_switch") is not None], float)
        conds[c] = dict(
            n_total=len(rs), n_alive=len(ok),
            extinct=sum(1 for r in rs if r.get("extinct") is not None),
            lr_median=float(10 ** np.median(ll)) if ll.size else None,
            lr_q25=float(10 ** np.percentile(ll, 25)) if ll.size else None,
            lr_q75=float(10 ** np.percentile(ll, 75)) if ll.size else None,
            log_sd=float(ll.std(ddof=1)) if ll.size > 1 else None,
            accuracy=float(acc.mean()) if acc.size else None,
            min_pop_after_switch=float(dip.mean()) if dip.size else None,
            lr_init=(rs[0].get("lr_init") if rs else None),
        )

    drift_sd = conds["never_frozen"]["log_sd"]
    two_sigma = 2 * drift_sd if drift_sd else None

    def paired(a_c, b_c):
        pairs = [(log_lr(by[a_c][s]), log_lr(by[b_c][s]))
                 for s in sorted(by[a_c]) if s in by[b_c]
                 and alive(by[a_c][s]) and alive(by[b_c][s])
                 and log_lr(by[a_c][s]) is not None and log_lr(by[b_c][s]) is not None]
        if not pairs:
            return dict(n=0)
        a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
        p = wilcoxon_p(a, b)
        diff = float(np.median(a - b))
        exceeds = two_sigma is not None and abs(diff) > two_sigma
        return dict(n=len(pairs), p=p, median_log_diff=diff,
                    ratio=float(10 ** diff), exceeds_2sigma=bool(exceeds),
                    confirmed=bool(p is not None and p < 0.01 and exceeds and diff > 0))

    comparisons = {
        "life_vs_never": paired("life", "never"),
        "slow_vs_never": paired("slow", "never"),
        "never_vs_never_frozen": paired("never", "never_frozen"),
    }

    def ext_rate(c):
        s = conds[c]
        return (s["extinct"] / s["n_total"]) if s["n_total"] else None

    n_complete = len({s for s in by["life"]
                      if all(s in by[c] for c in CONDS)})
    return dict(protocol=PROTOCOL, n_seeds=n_complete, conditions=conds,
                two_sigma_log=two_sigma, comparisons=comparisons,
                extinction=dict(life=ext_rate("life"), life_frozen=ext_rate("life_frozen"),
                                fast=ext_rate("fast"), never=ext_rate("never")))


def verdict_key(st):
    c = st["comparisons"]["life_vs_never"]
    ext = st["extinction"].get("life")
    if not c.get("n"):
        return "nodata"
    if ext is not None and ext > 0.5:
        return "world_fails"
    if c.get("confirmed"):
        return "confirmed"
    if c.get("p") is not None and c["p"] < 0.01 and c.get("median_log_diff", 0) > 0:
        return "signal_within_noise"
    return "not_distinguishable"


VERDICTS = {
    "confirmed": ("подтверждено",
                  "Скорость обучения в мире со сменой правила раз в жизнь выше, чем "
                  "в стационарном, по обоим критериям сразу: p&lt;0.01 по парному тесту "
                  "И разница медиан больше 2σ нейтрального дрейфа гена."),
    "signal_within_noise": ("не подтверждено: сигнал внутри дрейфа",
                            "Парный тест значим, но разница медиан меньше 2σ разброса "
                            "гена скорости там, где он ни на что не влияет."),
    "not_distinguishable": ("неотличимо",
                            "Скорость обучения в меняющемся и стационарном мире "
                            "не расходится."),
    "world_fails": ("мир не выдерживает",
                    "Больше половины популяций в условии life вымерли: граница провала "
                    "§6.3 предрегистрации. Сравнивать скорости обучения не на чем."),
    "nodata": ("данных пока нет", "Завершённых seed'ов недостаточно."),
}


def mean_curves(rows):
    """Средняя по seed'ам траектория медианы скорости обучения, по условиям."""
    out = {}
    for c in CONDS:
        acc = {}
        for r in rows:
            if r.get("label") != c or r.get("error"):
                continue
            for pt in r.get("curve") or []:
                if pt.get("lr_median") and pt["lr_median"] > 0:
                    acc.setdefault(pt["tick"], []).append(math.log10(pt["lr_median"]))
        out[c] = [dict(tick=t, lr=float(10 ** np.mean(v)), n=len(v))
                  for t, v in sorted(acc.items())]
    return out


def accumulation_curve(rows):
    seeds = sorted({r["seed"] for r in rows if r.get("seed") is not None and not r.get("error")})
    curve = []
    for n in seeds:
        if n < 5:
            continue
        s = analyse(rows, seed_limit=n)
        c = s["comparisons"]["life_vs_never"]
        if not c.get("n"):
            continue
        curve.append(dict(n_seeds=s["n_seeds"], median_log_diff=c.get("median_log_diff"),
                          p=c.get("p"), two_sigma=s.get("two_sigma_log"),
                          confirmed=c.get("confirmed")))
    return curve


def build_state():
    rows = read_jsonl(SRC)
    st = analyse(rows)
    st["verdict"] = verdict_key(st)
    st["target"] = TARGET
    st["checkpoints"] = CHECKPOINTS
    st["curve"] = accumulation_curve(rows)
    st["trajectories"] = mean_curves(rows)
    dates = {}
    for r in rows:
        d = (r.get("run_date") or "")[:10]
        if d and r.get("seed") is not None:
            dates.setdefault(d, set()).add(r["seed"])
    entries = []
    seen = []
    for d in sorted(dates):
        seen += [r for r in rows if (r.get("run_date") or "")[:10] == d]
        s = analyse(seen)
        c = s["comparisons"]["life_vs_never"]
        entries.append(dict(date=d, seeds=sorted(dates[d]), n_seeds=s["n_seeds"],
                            ratio=c.get("ratio"), p=c.get("p"),
                            two_sigma=s.get("two_sigma_log"), verdict=verdict_key(s)))
    st["entries"] = entries
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    return st


# ------------------------------------------------------------------ страница
def fmt(x, digits=3):
    return "—" if x is None else f"{x:.{digits}f}"


def fmt_p(p):
    if p is None:
        return "—"
    if p < 0.0001:
        return "&lt;0.0001"
    return f"{p:.4f}"


COLORS = dict(never="#93a6ae", slow="#46c6d0", life="#4fd08a", fast="#e8734a",
              life_frozen="#e8734a", never_frozen="#5b6f77")
DASH = dict(life_frozen="4 3", never_frozen="4 3")


def svg_trajectories(traj):
    """Медиана скорости обучения по тикам, среднее по seed'ам, лог-шкала."""
    series = {c: v for c, v in traj.items() if len(v) >= 2}
    if not series:
        return '<p class="muted">Кривые появятся после первых прогонов.</p>'
    W, H = 720, 280
    pl, pr, pt, pb = 56, 16, 18, 34
    xmax = max(p["tick"] for v in series.values() for p in v)
    vals = [math.log10(p["lr"]) for v in series.values() for p in v]
    ymin, ymax = min(vals) - 0.2, max(vals) + 0.2

    def X(t):
        return pl + t / max(1, xmax) * (W - pl - pr)

    def Y(v):
        return pt + (ymax - v) / (ymax - ymin) * (H - pt - pb)

    lines = ""
    for c, v in series.items():
        pts = " ".join(f"{X(p['tick']):.1f},{Y(math.log10(p['lr'])):.1f}" for p in v)
        dash = f' stroke-dasharray="{DASH[c]}"' if c in DASH else ""
        lines += (f'<polyline points="{pts}" fill="none" stroke="{COLORS[c]}" '
                  f'stroke-width="1.6"{dash}/>')
        # подпись серии у правого края: если не помещается, выравниваем по правому
        last = v[-1]
        lx = X(last["tick"]) + 4
        anchor = "end" if lx > W - 62 else "start"
        if anchor == "end":
            lx = W - 2
        lines += (f'<text x="{lx:.1f}" y="{Y(math.log10(last["lr"])) - 4:.1f}" '
                  f'class="ax" text-anchor="{anchor}" fill="{COLORS[c]}">{c}</text>')
    yt = ""
    for e in range(int(math.floor(ymin)), int(math.ceil(ymax)) + 1):
        if ymin <= e <= ymax:
            yt += (f'<line x1="{pl}" y1="{Y(e):.1f}" x2="{W - pr}" y2="{Y(e):.1f}" class="zero"/>'
                   f'<text x="6" y="{Y(e) + 3:.1f}" class="ax">{10 ** e:g}</text>')
    xt = ""
    for t in range(0, xmax + 1, max(10000, (xmax // 8) // 10000 * 10000 or 10000)):
        xt += f'<text x="{X(t):.1f}" y="{H - 12}" class="ax" text-anchor="middle">{t // 1000}k</text>'
    return f'''<svg viewBox="0 0 {W} {H}" class="chart" role="img">
  {yt}{lines}{xt}
  <text x="{W - pr}" y="{H - 2}" class="ax" text-anchor="end">тики</text>
</svg>'''


def render_section(st):
    if not st["n_seeds"]:
        # пустое состояние: первый суточный прогон ещё не отработал
        return ('<div class="card"><p class="big">первый прогон ещё не отработал</p>'
                '<p class="muted">Протокол заморожен ' + PROTOCOL + ', суточный прогон '
                'добавляет по два seed\'а в сутки, шесть условий на каждом. Первые числа '
                'появятся здесь после ближайшего ночного запуска. Что именно будет '
                'измеряться и по каким критериям объявлено заранее: '
                '<a href="https://github.com/akela1308/minimir/blob/main/PREREGISTRATION_B.md">'
                'PREREGISTRATION_B.md</a>.</p></div>')
    c = st["comparisons"]["life_vs_never"]
    vlabel, vtext = VERDICTS[st["verdict"]]
    n = st["n_seeds"]
    pct = min(100, round(100 * n / st["target"]))
    interim = n not in CHECKPOINTS and n < st["target"]
    lr0 = st["conditions"]["never"].get("lr_init")

    rows_cond = ""
    for cond in CONDS:
        s = st["conditions"][cond]
        rows_cond += (
            f"<tr><td class=\"mono\">{cond}</td><td class=\"dimtd\">{COND_RU[cond]}</td>"
            f"<td>{fmt(s['lr_median'])}</td>"
            f"<td>{fmt(s['lr_q25'])}…{fmt(s['lr_q75'])}</td>"
            f"<td>{fmt(s['accuracy'], 2)}</td>"
            f"<td>{s['extinct']}/{s['n_total']}</td></tr>")

    rows_cmp = ""
    for key, name in (("life_vs_never", "life vs never"),
                      ("slow_vs_never", "slow vs never"),
                      ("never_vs_never_frozen", "never vs never_frozen")):
        cc = st["comparisons"][key]
        if not cc.get("n"):
            continue
        rows_cmp += (
            f"<tr><td class=\"mono\">{name}</td>"
            f"<td>×{fmt(cc.get('ratio'), 2)}</td><td>{fmt_p(cc.get('p'))}</td>"
            f"<td>{'&gt;2σ' if cc.get('exceeds_2sigma') else '&lt;2σ'}</td>"
            f"<td class=\"{'yes' if cc.get('confirmed') else 'no'}\">"
            f"{'да' if cc.get('confirmed') else 'нет'}</td><td>{cc['n']}</td></tr>")

    rows_j = ""
    for e in reversed(st["entries"]):
        vl = VERDICTS.get(e.get("verdict", "nodata"), ("—", ""))[0]
        seeds = e.get("seeds") or []
        srange = (f"{min(seeds)}–{max(seeds)}" if len(seeds) > 1
                  else (str(seeds[0]) if seeds else "—"))
        rows_j += (f"<tr><td class=\"mono\">{e['date']}</td><td>{srange}</td>"
                   f"<td>{e.get('n_seeds', '—')}</td><td>×{fmt(e.get('ratio'), 2)}</td>"
                   f"<td>{fmt_p(e.get('p'))}</td><td>{vl}</td></tr>")

    ext = st["extinction"]
    return f'''
<div class="card">
  <p class="big">{n} из {st['target']} seed'ов</p>
  <div class="bar"><i style="width:{pct}%"></i></div>
  <p class="muted">Измеряется ген скорости обучения «вкуса» (единственной пластичной
  связи цвет → есть). Стартовое значение у всех {fmt(lr0, 2) if lr0 else '—'}. Шесть условий
  на одних и тех же seed'ах и с одним предком: см. таблицу ниже.</p>
</div>

<h2>Текущее чтение</h2>
<div class="card">
  <p class="big">{vlabel}</p>
  <p>{vtext}</p>
  <p class="muted">Скорость обучения life / never = <b>×{fmt(c.get('ratio'), 2)}</b>
  (медиана по парам), p = <b>{fmt_p(c.get('p'))}</b>, 2σ нейтрального дрейфа
  (в log10) = <b>{fmt(st.get('two_sigma_log'))}</b>, пар: {c.get('n', 0)}.
  Вымирания: life {fmt(ext.get('life'), 2)}, без обучения (life_frozen)
  {fmt(ext.get('life_frozen'), 2)}, слишком частая смена (fast) {fmt(ext.get('fast'), 2)}.</p>
</div>
{'<p class="note"><b>Это промежуточное чтение, а не результат.</b> Заранее объявлено, что подтверждающих чтения три: на 10, 20 и 40 seed’ах. Промежуточные значения показаны ради прозрачности и ничего не заявляют.</p>' if interim else ''}

<h2>Как эволюционирует скорость обучения</h2>
{svg_trajectories(st.get('trajectories', {}))}
<p class="muted">Медиана гена скорости по живым агентам, усреднённая по seed'ам,
логарифмическая шкала. Правило начинает меняться с 5000-го тика. Пунктиром
условия, где ген есть, но обучение не применяется.</p>

<h2>Условия сейчас</h2>
<table>
<tr><th>условие</th><th>что это</th><th>скорость, медиана</th><th>квартили</th>
<th>точность еды</th><th>вымерло</th></tr>
{rows_cond}
</table>

<h2>Парные сравнения</h2>
<table>
<tr><th>сравнение</th><th>отношение медиан</th><th>p</th><th>против 2σ</th>
<th>подтв.</th><th>пар</th></tr>
{rows_cmp}
</table>

<h2>Журнал прогонов</h2>
<table>
<tr><th>дата</th><th>seed'ы</th><th>всего</th><th>life/never</th><th>p</th><th>чтение</th></tr>
{rows_j}
</table>
<p class="muted">Сырые числа:
<a href="https://github.com/akela1308/minimir/blob/main/runs/daily/protocol_b.jsonl">runs/daily/protocol_b.jsonl</a>,
протокол {PROTOCOL}, критерии:
<a href="https://github.com/akela1308/minimir/blob/main/PREREGISTRATION_B.md">PREREGISTRATION_B.md</a>.</p>
'''


if __name__ == "__main__":
    s = build_state()
    print(f"протокол B: seed'ов {s['n_seeds']}/{TARGET}, вердикт {s['verdict']}")
