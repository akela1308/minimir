#!/usr/bin/env python3
"""Журнал протокола B2 (ЧЕРНОВИК 13 октября 2026, прогонов не было): статистика
по PREREGISTRATION_B2_черновик.md §4-§5, §8-§9 и страница docs/b2.html.

Читает runs/b2/protocol_b2.jsonl (раннер runs/daily_b2.py), пишет docs/b2.json и
docs/b2.html. Правило страницы то же, что у A2: чисел нет, пока не завершено
очередное объявленное чтение (10, 20, 40 seed'ов); до этого только счётчик
накопления и годность. Промежуточные значения не заявка и не показываются.

Три критерия H-B2.1, все обязательны (§4):
  1. направление: life против never по log10(медиана lr живых) в конце прогона,
     парный Уилкоксон, p < 0,05, не меньше 12 годных пар (§5), медиана парных
     разниц > 0;
  2. выше дрейфа на том же тике: на T_read (первая точка кривой с tick >=
     первая смена + 10 000) медиана по seed'ам D_lr = log10(lr/lr_init) в life
     больше 2σ по seed'ам D_marker = log10(marker/marker_init) в тех же мирах;
  3. абляция: life_frozen вымирает чаще life, точный Макнемар по расходящимся
     парам, p < 0,05, b > c, расходящихся пар не меньше 6 (§5).
Вердикты как в B1: все три = подтверждено; 1 и 2 без 3 = рост без пользы;
только 1 = сигнал внутри дрейфа; ничего = неотличимо. Границы провала §8:
больше половины life вымерли = мир не выдерживает; меньше 12 годных пар =
прибор слеп; маркер сам систематически сдвинут (знаковый тест p < 0,05) =
маркер не нейтрален; lr_at_ceiling в life выше 0,5 = цензура.
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
sys.path.insert(0, str(ROOT / "runs"))

from journal_b import read_jsonl, wilcoxon_p, mcnemar_exact  # noqa: E402

SRC = ROOT / "runs" / "b2" / "protocol_b2.jsonl"
OUT_JSON = ROOT / "docs" / "b2.json"
OUT_HTML = ROOT / "docs" / "b2.html"
FROZEN = ROOT / "PREREGISTRATION_B2.md"

CONDS = ["never", "slow", "life", "fast", "life_frozen", "never_frozen"]
CHECKPOINTS = [10, 20, 40]
READ_OFFSET = 10_000          # T_read = первая смена + 10 000 (черновик §0.5, §4)
MIN_PAIRS = 12                # §5
MIN_DISCORDANT = 6            # §5
P_PAIRED = 0.05               # §5
PROTOCOL = "B2-100k-draft"    # «draft» снимается при заморозке


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def alive(r):
    return not r.get("error") and r.get("extinct") is None


def log10_or_none(v):
    return math.log10(v) if (v is not None and v > 0) else None


def point_at_read(r):
    """Первая точка кривой с tick >= первая смена + READ_OFFSET; None, если смены
    не было или мир вымер раньше (тогда точки нет)."""
    fs = r.get("first_switch")
    if fs is None:
        return None
    t_read = fs + READ_OFFSET
    for p in r.get("curve") or []:
        if p.get("tick", -1) >= t_read:
            return p
    return None


def group(rows, seed_limit):
    by = {c: {} for c in CONDS}
    for r in rows:
        if r.get("label") in by and r.get("seed") is not None and not r.get("error"):
            if r["seed"] <= seed_limit:
                by[r["label"]][r["seed"]] = r
    return by


def completed_seeds(rows, limit=None):
    have = {}
    for r in rows:
        if r.get("error") or r.get("seed") is None:
            continue
        if limit is not None and r["seed"] > limit:
            continue
        have.setdefault(r["seed"], set()).add(r.get("label"))
    return sorted(s for s, cs in have.items() if set(CONDS) <= cs)


def analyse(rows, k):
    """Чтение на k seed'ах (1..k все шесть условий)."""
    by = group(rows, k)

    conds = {}
    for c in CONDS:
        rs = list(by[c].values())
        ok = [r for r in rs if alive(r)]
        ll = np.array([v for v in (log10_or_none(r.get("lr_median")) for r in ok) if v is not None])
        ceil = np.array([r["lr_at_ceiling"] for r in ok if r.get("lr_at_ceiling") is not None], float)
        conds[c] = dict(n_total=len(rs), n_alive=len(ok),
                        extinct=sum(1 for r in rs if r.get("extinct") is not None),
                        lr_median=(float(10 ** np.median(ll)) if ll.size else None),
                        lr_q25=(float(10 ** np.percentile(ll, 25)) if ll.size else None),
                        lr_q75=(float(10 ** np.percentile(ll, 75)) if ll.size else None),
                        lr_at_ceiling=(float(ceil.mean()) if ceil.size else None),
                        accuracy=(float(np.mean([r["eat_accuracy"] for r in ok if r.get("eat_accuracy") is not None]))
                                  if any(r.get("eat_accuracy") is not None for r in ok) else None))

    # критерий 1: направление, конец прогона, годные пары life/never
    pairs = [(log10_or_none(by["life"][s].get("lr_median")), log10_or_none(by["never"][s].get("lr_median")))
             for s in sorted(by["life"]) if s in by["never"] and alive(by["life"][s]) and alive(by["never"][s])]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if pairs:
        a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
        d = a - b
        p1 = wilcoxon_p(a, b) if len(pairs) >= MIN_PAIRS else None
        c1 = dict(n=len(pairs), enough_pairs=len(pairs) >= MIN_PAIRS, p=p1,
                  median_log_diff=float(np.median(d)), ratio=float(10 ** np.median(d)),
                  passed=bool(len(pairs) >= MIN_PAIRS and p1 is not None and p1 < P_PAIRED and np.median(d) > 0))
    else:
        c1 = dict(n=0, enough_pairs=False, p=None, median_log_diff=None, ratio=None, passed=False)

    # критерий 2: на T_read, в мирах life, доживших до T_read
    d_lr, d_mk, d_lr_end, d_mk_end, seeds_read = [], [], [], [], []
    for s, r in sorted(by["life"].items()):
        pt = point_at_read(r)
        lr0, mk0 = r.get("lr_init"), r.get("marker_init")
        if pt is None or not lr0 or not mk0:
            continue
        a, b = log10_or_none(pt.get("lr_median")), log10_or_none(pt.get("marker_median"))
        if a is None or b is None:
            continue
        d_lr.append(a - math.log10(lr0)); d_mk.append(b - math.log10(mk0)); seeds_read.append(s)
        if alive(r):
            a2, b2 = log10_or_none(r.get("lr_median")), log10_or_none(r.get("marker_median"))
            if a2 is not None and b2 is not None:
                d_lr_end.append(a2 - math.log10(lr0)); d_mk_end.append(b2 - math.log10(mk0))
    if len(d_lr) >= 2:
        dl, dm = np.array(d_lr), np.array(d_mk)
        two_sigma = float(2 * dm.std(ddof=1))
        c2 = dict(n=len(d_lr), median_d_lr=float(np.median(dl)), ratio_lr=float(10 ** np.median(dl)),
                  median_d_marker=float(np.median(dm)), two_sigma_marker=two_sigma,
                  passed=bool(np.median(dl) > two_sigma and np.median(dl) > 0),
                  # граница провала 3: маркер сам сдвинут (знаковый тест по seed'ам)
                  marker_sign_p=sign_test_p(dm))
    else:
        c2 = dict(n=len(d_lr), median_d_lr=None, ratio_lr=None, median_d_marker=None,
                  two_sigma_marker=None, passed=False, marker_sign_p=None)
    if len(d_lr_end) >= 2:
        dl, dm = np.array(d_lr_end), np.array(d_mk_end)
        c2["end_of_run"] = dict(n=len(d_lr_end), median_d_lr=float(np.median(dl)),
                                two_sigma_marker=float(2 * dm.std(ddof=1)),
                                exceeds=bool(np.median(dl) > 2 * dm.std(ddof=1)))
    else:
        c2["end_of_run"] = dict(n=len(d_lr_end))

    # критерий 3: абляция, life против life_frozen
    b_ = c_ = same = 0
    for s in sorted(by["life"]):
        if s not in by["life_frozen"]:
            continue
        a_ok, f_ok = alive(by["life"][s]), alive(by["life_frozen"][s])
        if a_ok and not f_ok:
            b_ += 1
        elif f_ok and not a_ok:
            c_ += 1
        else:
            same += 1
    p3 = mcnemar_exact(b_, c_)
    c3 = dict(b=b_, c=c_, concordant=same, n_discordant=b_ + c_, p=p3,
              passed=bool(p3 is not None and p3 < 0.05 and b_ > c_ and (b_ + c_) >= MIN_DISCORDANT))

    # описательно (§7, §0.3): погибшие против живых на окне первой смены в life
    dead_vs_alive = []
    for s, r in sorted(by["life"].items()):
        fs = r.get("first_switch")
        if fs is None:
            continue
        for p in r.get("curve") or []:
            if p.get("tick", -1) >= fs and p.get("dead_n") and p.get("lr_median") and p.get("dead_lr_median"):
                dead_vs_alive.append(math.log10(p["lr_median"]) - math.log10(p["dead_lr_median"]))
                break
    descriptive = dict(dead_vs_alive_n=len(dead_vs_alive),
                       alive_over_dead_lr_median=(float(10 ** np.median(dead_vs_alive)) if dead_vs_alive else None))

    ext_life = (conds["life"]["extinct"] / conds["life"]["n_total"]) if conds["life"]["n_total"] else None
    st = dict(k=k, conditions=conds, criterion1=c1, criterion2=c2, criterion3=c3,
              descriptive=descriptive, extinction_life=ext_life,
              other=dict(never_vs_never_frozen=paired_simple(by, "never", "never_frozen"),
                         life_vs_fast=paired_simple(by, "life", "fast")))
    st["verdict"] = verdict_key(st)
    return st


def sign_test_p(d):
    """Двусторонний знаковый тест: сдвинут ли маркер систематически (нули не считаются)."""
    d = np.asarray(d, float)
    d = d[d != 0]
    if d.size == 0:
        return None
    from math import comb
    k = int(min((d > 0).sum(), (d < 0).sum())); n = int(d.size)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
    return min(1.0, 2.0 * tail)


def paired_simple(by, a_c, b_c):
    pairs = [(log10_or_none(by[a_c][s].get("lr_median")), log10_or_none(by[b_c][s].get("lr_median")))
             for s in sorted(by[a_c]) if s in by[b_c] and alive(by[a_c][s]) and alive(by[b_c][s])]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not pairs:
        return dict(n=0)
    a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
    return dict(n=len(pairs), p=wilcoxon_p(a, b), median_log_diff=float(np.median(a - b)),
                ratio=float(10 ** np.median(a - b)))


def verdict_key(st):
    c1, c2, c3 = st["criterion1"], st["criterion2"], st["criterion3"]
    ext = st["extinction_life"]
    if ext is not None and ext > 0.5:
        return "world_fails"
    # граница 3 проверяется раньше «слепоты»: на первом чтении (10 seed'ов) пар
    # меньше 12 по построению, а нейтральность маркера проверить уже можно
    if c2.get("marker_sign_p") is not None and c2["marker_sign_p"] < 0.05:
        return "marker_not_neutral"
    if not c1["enough_pairs"]:
        return "blind"
    if c1["passed"] and c2["passed"]:
        return "confirmed" if c3["passed"] else "growth_without_benefit"
    if c1["passed"]:
        return "signal_within_drift"
    return "not_distinguishable"


VERDICTS = {
    "confirmed": ("подтверждено", "Все три критерия: направление (p&lt;0,05, не меньше 12 пар), "
                  "рост выше 2σ дрейфа нейтрального маркера на том же тике, абляция даёт выигрыш в выживании."),
    "growth_without_benefit": ("не подтверждено: рост без пользы",
                               "Ген скорости вырос по критериям 1 и 2, но без обучения миры гибнут не чаще."),
    "signal_within_drift": ("не подтверждено: сигнал внутри дрейфа",
                            "Направление значимо, но рост lr не больше 2σ того, что сделал с нейтральным "
                            "маркером тот же мир и то же горлышко."),
    "not_distinguishable": ("неотличимо", "Скорость обучения в меняющемся и стационарном мире не расходится."),
    "world_fails": ("мир не выдерживает", "Больше половины life вымерли: граница провала §8.1, версия заменяется."),
    "blind": ("прибор слеп", "Годных пар life/never меньше 12 (§5): критерий 1 не считается до следующего чтения."),
    "marker_not_neutral": ("маркер не нейтрален", "Маркер сам систематически сдвинут по seed'ам "
                           "(§8.3): точкой отсчёта его использовать нельзя."),
    "accumulating": ("накопление", "Очередное объявленное чтение ещё не завершено; чисел страница не показывает."),
    "nodata": ("данных нет", "Прогонов по протоколу B2 ещё не было."),
}


def fmt(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def fmt_p(p):
    if p is None:
        return "—"
    return "&lt;0.0001" if p < 0.0001 else f"{p:.4f}"


def build_state():
    rows = read_jsonl(SRC)
    done = completed_seeds(rows)
    readings = {}
    for k in CHECKPOINTS:
        if completed_seeds(rows, k) == list(range(1, k + 1)):
            readings[str(k)] = analyse(rows, k)
    latest = max((int(k) for k in readings), default=None)
    validity = {}
    for c in CONDS:
        rs = [r for r in rows if r.get("label") == c]
        validity[c] = dict(n=len(rs), errors=sum(1 for r in rs if r.get("error")),
                           extinct=sum(1 for r in rs if not r.get("error") and r.get("extinct") is not None))
    return dict(built_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                commit=git_commit(), frozen=FROZEN.exists(), protocol=PROTOCOL,
                n_rows=len(rows), n_done=len(done), target=CHECKPOINTS[-1],
                next_checkpoint=next((k for k in CHECKPOINTS if k > (latest or 0)), None),
                latest_reading=latest, readings=readings, validity=validity)


def render(st):
    latest = st["latest_reading"]
    rd = st["readings"].get(str(latest)) if latest else None
    key = "nodata" if st["n_rows"] == 0 else ("accumulating" if rd is None else rd["verdict"])
    v = VERDICTS[key]
    nxt = st["next_checkpoint"]
    pct = min(100, round(100 * st["n_done"] / nxt)) if nxt else 100
    freeze_note = ("" if st["frozen"] else
                   '<p class="note"><b>Предрегистрация B2 не заморожена.</b> Файл '
                   '<span class="mono">PREREGISTRATION_B2.md</span> ещё не существует, есть только '
                   'черновик. Прогоны по протоколу до заморозки не считаются.</p>')
    val = "".join(f"<tr><td class=\"mono\">{c}</td><td>{x['n']}</td><td>{x['errors']}</td><td>{x['extinct']}</td></tr>"
                  for c, x in st["validity"].items())
    body = ""
    if rd:
        c1, c2, c3 = rd["criterion1"], rd["criterion2"], rd["criterion3"]
        conds = "".join(
            f"<tr><td class=\"mono\">{c}</td><td>{x['n_total']}</td><td>{x['n_alive']}</td><td>{x['extinct']}</td>"
            f"<td>{fmt(x['lr_median'])}</td><td>{fmt(x['lr_q25'])}…{fmt(x['lr_q75'])}</td>"
            f"<td>{fmt(x['lr_at_ceiling'], 2)}</td><td>{fmt(x['accuracy'])}</td></tr>"
            for c, x in rd["conditions"].items())

        def yn(b):
            return f'<td class="{"yes" if b else "no"}">{"да" if b else "нет"}</td>'
        crit = (f"<tr><td class=\"mono\">1. направление, life против never в конце прогона</td>"
                f"<td>пар {c1['n']}, ×{fmt(c1['ratio'], 2)}, p={fmt_p(c1['p'])}</td>{yn(c1['passed'])}</tr>"
                f"<tr><td class=\"mono\">2. выше дрейфа маркера на T_read</td>"
                f"<td>миров {c2['n']}, D_lr={fmt(c2['median_d_lr'])} (×{fmt(c2['ratio_lr'], 2)}), "
                f"2σ маркера={fmt(c2['two_sigma_marker'])}, маркер сдвинут p={fmt_p(c2['marker_sign_p'])}</td>{yn(c2['passed'])}</tr>"
                f"<tr><td class=\"mono\">3. абляция, life против life_frozen</td>"
                f"<td>b={c3['b']}, c={c3['c']}, согласных {c3['concordant']}, p={fmt_p(c3['p'])}</td>{yn(c3['passed'])}</tr>")
        eor = c2.get("end_of_run", {})
        extra = ""
        if eor.get("n", 0) >= 2:
            extra += (f"<p>Описательно, в конце прогона: D_lr={fmt(eor['median_d_lr'])}, 2σ маркера="
                      f"{fmt(eor['two_sigma_marker'])} ({'выше' if eor['exceeds'] else 'не выше'}); порог там "
                      f"растёт с длиной прогона, поэтому это не критерий.</p>")
        de = rd["descriptive"]
        if de["dead_vs_alive_n"]:
            extra += (f"<p>Описательно, окно первой смены в life: медиана lr живых к медиане lr погибших за то же окно "
                      f"×{fmt(de['alive_over_dead_lr_median'], 2)} (миров {de['dead_vs_alive_n']}).</p>")
        oth = rd["other"]
        for name, o in oth.items():
            if o.get("n"):
                extra += (f"<p class=\"muted\">{name.replace('_vs_', ' против ')}: пар {o['n']}, "
                          f"×{fmt(o['ratio'], 2)}, p={fmt_p(o['p'])}.</p>")
        body = (f"<h2>Чтение на {latest} seed'ах</h2>"
                f"<table><tr><th>условие</th><th>строк</th><th>живых</th><th>вымерло</th><th>lr медиана</th>"
                f"<th>q25…q75</th><th>у потолка</th><th>точность</th></tr>{conds}</table>"
                f"<h2>Критерии H-B2.1</h2><table><tr><th>критерий</th><th>числа</th><th>пройден</th></tr>{crit}</table>"
                f"{extra}")
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>mini·world: протокол B2</title>
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
<div class="eyebrow">mini·world · протокол B2</div>
<h1>Когда выгодно учиться, вторая версия: нейтральный маркер и мир, переживающий смену</h1>
<nav><a href="index.html">живой эксперимент</a><a href="results-b.html">эксперимент 2 (B1)</a><a href="journal.html">журнал</a><a href="a2.html">протокол A2</a><a href="about.html">о проекте</a></nav>
</header>
{freeze_note}
<p>Тот же вопрос, что в B1: включает ли отбор прижизненное обучение там, где мир меняет правила быстрее
поколений. B1 этот вопрос не решил: мир убил 32 популяции из 40 на первой смене, а порог критерия 2
рос с длиной прогона. В B2 рост гена скорости сравнивается с нейтральным маркерным геном в том же мире
на том же тике, а параметры мира выбраны так, чтобы первую смену переживало большинство популяций.
Протокол: <a href="https://github.com/akela1308/minimir/blob/main/PREREGISTRATION_B2_черновик.md">предрегистрация B2</a>.
Чтения на 10, 20 и 40 seed'ах; между ними страница чисел не показывает.</p>

<div class="card"><p class="big">{st["n_done"]} из {st["target"]} seed'ов{f", следующее чтение на {nxt}" if nxt else ""}</p>
<div class="bar"><i style="width:{pct}%"></i></div>
<p class="big">{v[0]}</p><p>{v[1]}</p></div>
<table><tr><th>условие</th><th>строк</th><th>ошибок</th><th>вымерло</th></tr>{val}</table>
{body}
<footer><p class="muted">Собрано {st["built_at"]} · код {st.get("commit") or "—"} · сырые числа:
<a href="https://github.com/akela1308/minimir/tree/main/runs/b2">runs/b2/</a></p></footer>
</div></body></html>'''


def build():
    st = build_state()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    json.dump(st, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    open(OUT_HTML, "w").write(render(st))
    print(f"B2: строк {st['n_rows']}, завершённых seed'ов {st['n_done']}, "
          f"чтений {sorted(int(k) for k in st['readings'])}, "
          f"вердикт последнего: {st['readings'][str(st['latest_reading'])]['verdict'] if st['latest_reading'] else 'нет'}")
    print(f"записано: {OUT_HTML}, {OUT_JSON}")
    return st


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    build()
