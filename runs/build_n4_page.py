#!/usr/bin/env python3
"""Сборка страницы docs/n4.html (20 ноября 2026).

Страница описывает протокол N4 на пяти языках. Текст лежит в runs/n4_texts.py,
все числа берутся из данных:
  * пилот: runs/n4/pilot/pilot2.jsonl (семена 301-330, не чтение);
  * достижимость: runs/n4/attainability.json;
  * подтверждающее чтение: runs/n4/reading_n4.json, если оно уже сделано.

У страницы три состояния, и определяются они файлами, а не флагом:
  draft   нет PREREGISTRATION_N4.md: черновик, результатов нет;
  frozen  предрегистрация заморожена, чтения ещё нет: идёт счёт;
  read    чтение записано: в последнем разделе вердикты и кривые.

  python runs/build_n4_page.py
"""
import html
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs"))
import n4_analyze as an                                     # noqa: E402
from n4_texts import T                                      # noqa: E402
from sim.protocol_n4 import DOSES, SIGMAS, SEED_FIRST, N_CONFIRM, conditions  # noqa: E402

LANGS = ["en", "ru", "de", "zh", "es"]          # порядок блоков, как на results-b.html
COMMA = {"ru", "de", "es"}                      # десятичная запятая
BASE = "https://minimir.ilinmaks.com"
GH = "https://github.com/akela1308/minimir/blob/main/"
PILOT = ROOT / "runs/n4/pilot/pilot2.jsonl"
READING = ROOT / "runs/n4/reading_n4.json"
CONFIRM = ROOT / "runs/n4/protocol_n4.jsonl"
FROZEN = ROOT / "PREREGISTRATION_N4.md"
SIG_ALL = [0.0] + SIGMAS
D_CONDS = [f"D_L{d:g}" for d in DOSES]
M_CONDS = [f"M_L{d:g}" for d in DOSES]
V_CONDS = ["D_L0.1"] + [f"V_s{s:g}" for s in SIGMAS]


def num(x, lang, nd=2):
    s = f"{x:.{nd}f}".replace("-", "−")
    return s.replace(".", ",") if lang in COMMA else s


def dose_label(d, lang):
    s = f"{d:g}" if d not in (1.0, 4.0) else f"{d:.1f}"
    return s.replace(".", ",") if lang in COMMA else s


def pct(x, lang):
    return f"{round(100 * x)}%" if lang != "es" else f"{round(100 * x)}%"


def shares(y):
    """Доли спасённых по трём рядам из таблицы y[условие][семя]."""
    mean = lambda c: float(np.mean(list(y[c].values())))
    return dict(D=[mean(c) for c in D_CONDS], M=[mean(c) for c in M_CONDS],
                V=[mean(c) for c in V_CONDS], n=len(y["D_L0.1"]),
                F=int(sum(y["F_s2"].values())),
                E={c: mean(c) for c in ("E_L0.6", "E_L1.5")})


def state():
    if READING.exists():
        return "read"
    return "frozen" if FROZEN.exists() else "draft"


# ------------------------------------------------------------------ рисунки
# Каждый рисунок собирается в двух размерах: широкий для экрана и узкий для
# телефона. При простом сжатии широкого подписи осей становились нечитаемыми.
class Dim:
    def __init__(self, w, h, kind):
        self.W, self.H, self.kind = w, h, kind
        self.ML, self.MR, self.MT, self.MB = 46, 18, 16, 46
        self.PW, self.PH = w - self.ML - self.MR, h - self.MT - self.MB

    def y(self, v):
        return self.MT + self.PH * (1 - v)


WIDE, NARROW = Dim(560, 300, "w"), Dim(360, 290, "n")
NARROW_DOSE_TICKS = (0.1, 0.3, 0.6, 1.0, 2.5, 4.0)     # на телефоне все девять подписей не помещаются


def sig_label(s, lang):
    return "0" if s == 0 else num(s, lang, 1)


def _frame(g, xs_px, xlabels, xtitle):
    o = [f'<svg viewBox="0 0 {g.W} {g.H}" role="img" class="chart {g.kind}" xmlns="http://www.w3.org/2000/svg">']
    for t in (0, .25, .5, .75, 1):
        y = g.y(t)
        o.append(f'<line x1="{g.ML}" x2="{g.W - g.MR}" y1="{y:.1f}" y2="{y:.1f}" class="g"/>')
        o.append(f'<text x="{g.ML - 8}" y="{y + 4:.1f}" class="ax" text-anchor="end">{round(t * 100)}%</text>')
    for x, lab in zip(xs_px, xlabels):
        if lab:
            o.append(f'<text x="{x:.1f}" y="{g.MT + g.PH + 18}" class="ax" text-anchor="middle">{lab}</text>')
    o.append(f'<text x="{g.ML + g.PW / 2:.1f}" y="{g.H - 6}" class="axt" text-anchor="middle">{html.escape(xtitle)}</text>')
    return o


def _series(g, xs_px, vals, cls, tips):
    ys = [g.y(v) for v in vals]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs_px, ys))
    o = [f'<polyline points="{pts}" class="ln {cls}"/>']
    for x, y, tip in zip(xs_px, ys, tips):
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" class="pt {cls}"><title>{html.escape(tip)}</title></circle>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" class="hit"><title>{html.escape(tip)}</title></circle>')
    return o, ys


def _chart_dose(g, sh, t, lang):
    lo, hi = math.log10(DOSES[0]), math.log10(DOSES[-1])
    xs = [g.ML + g.PW * (math.log10(d) - lo) / (hi - lo) for d in DOSES]
    labs = [dose_label(d, lang) if (g.kind == "w" or d in NARROW_DOSE_TICKS) else "" for d in DOSES]
    o = _frame(g, xs, labs, t["c1_x"])
    tip = lambda name, d, v: f"{name}, {dose_label(d, lang)}: {pct(v, lang)}"
    b, yb = _series(g, xs, sh["M"], "b", [tip(t["c1_b"], d, v) for d, v in zip(DOSES, sh["M"])])
    a, ya = _series(g, xs, sh["D"], "a", [tip(t["c1_a"], d, v) for d, v in zip(DOSES, sh["D"])])
    o += b + a
    i = DOSES.index(0.6)                      # подписи там, где ряды разошлись сильнее всего
    o.append(f'<text x="{xs[i] - 10:.1f}" y="{ya[i] - 10:.1f}" class="lab" text-anchor="end">{html.escape(t["c1_a"])}</text>')
    o.append(f'<text x="{xs[i] + 12:.1f}" y="{yb[i] + 16:.1f}" class="lab">{html.escape(t["c1_b"])}</text>')
    o.append("</svg>")
    return "".join(o)


def _chart_var(g, sh, t, lang):
    xs = [g.ML + g.PW * s / SIG_ALL[-1] for s in SIG_ALL]
    labs = [sig_label(s, lang) for s in SIG_ALL]
    o = _frame(g, xs, labs, t["c2_x"] if g.kind == "w" else t["tab_spread"])
    a, ya = _series(g, xs, sh["V"], "a", [f"{lab}: {pct(v, lang)}" for lab, v in zip(labs, sh["V"])])
    o += a
    for i in (0, len(xs) - 1):
        o.append(f'<text x="{xs[i]:.1f}" y="{ya[i] - 11:.1f}" class="lab" text-anchor="{"start" if i == 0 else "end"}">{pct(sh["V"][i], lang)}</text>')
    o.append("</svg>")
    return "".join(o)


def chart_dose(sh, t, lang):
    return _chart_dose(WIDE, sh, t, lang) + _chart_dose(NARROW, sh, t, lang)


def chart_var(sh, t, lang):
    return _chart_var(WIDE, sh, t, lang) + _chart_var(NARROW, sh, t, lang)


def legend(t):
    return (f'<div class="lg"><span><i class="sw a"></i>{html.escape(t["c1_a"])}</span>'
            f'<span><i class="sw b"></i>{html.escape(t["c1_b"])}</span></div>')


def figures(sh, t, lang, cap1, cap2):
    """Два рисунка и таблица тех же чисел под ними."""
    o = [f'<figure><figcaption class="ct">{html.escape(t["c1_title"])}</figcaption>{legend(t)}'
         f'{chart_dose(sh, t, lang)}<p class="cap">{cap1}</p></figure>']
    rows = "".join(
        f'<tr><td class="k">{html.escape(name)}</td>' + "".join(f"<td>{num(v, lang)}</td>" for v in vals) + "</tr>"
        for name, vals in ((t["tab_d"], sh["D"]), (t["tab_m"], sh["M"])))
    o.append(f'<div class="tw"><table><tr><th>{html.escape(t["tab_rate"])}</th>'
             + "".join(f"<th>{dose_label(d, lang)}</th>" for d in DOSES) + f"</tr>{rows}</table></div>")
    o.append(f'<figure><figcaption class="ct">{html.escape(t["c2_title"])}</figcaption>'
             f'{chart_var(sh, t, lang)}<p class="cap">{cap2}</p></figure>')
    o.append(f'<div class="tw"><table><tr><th>{html.escape(t["tab_spread"])}</th>'
             + "".join(f"<th>{sig_label(s, lang)}</th>" for s in SIG_ALL)
             + f'</tr><tr><td class="k">{html.escape(t["tab_v"])}</td>'
             + "".join(f"<td>{num(v, lang)}</td>" for v in sh["V"]) + "</tr></table></div>")
    return "\n    ".join(o)


# ------------------------------------------------------------------ разделы
def table(head, rows):
    h = "".join(f"<th>{html.escape(x)}</th>" for x in head)
    b = "".join("<tr>" + f'<td class="k">{r[0]}</td>' + "".join(f'<td class="d">{x}</td>' for x in r[1:]) + "</tr>"
                for r in rows)
    return f'<div class="tw"><table><tr>{h}</tr>{b}</table></div>'


def attain_table(att, t, lang):
    head = f'<tr><th>{html.escape(t["att_head"])}</th>' + "".join(f"<th>{k}</th>" for k in ("K1", "K2", "K3", "K4")) + "</tr>"
    rows = ""
    for n in (60, 90, 120, 150):
        cells = "".join(f"<td>{num(att[f'{n}|{k}'][0], lang)} / {num(att[f'{n}|{k}'][1], lang)}</td>"
                        for k in ("K1", "K2", "K3", "K4"))
        rows += f'<tr><td class="k">{n}</td>{cells}</tr>'
    return f'<div class="tw"><table>{head}{rows}</table></div>'


def results(t, lang, st):
    name, h3 = t["s9"]
    if st != "read":
        return f'<section id="results"><h2>{name}</h2><h3>{h3}</h3><p>{t["res_wait"][st]}</p></section>'
    rd = json.load(open(READING))
    cr, w = rd["criteria"], t["res_words"]
    ci = lambda v: f'[{num(v[0], lang)}; {num(v[1], lang)}]'
    cells = {
        "K1": f'{w["diff"]} {num(cr["K1"]["diff"], lang)}, {w["ci"]} {ci(cr["K1"]["ci"])}',
        "K2": (f'{w["at"]} {dose_label(0.6, lang)}: {num(cr["K2"]["s_low"], lang)} {ci(cr["K2"]["ci_low"])}; '
               f'{w["at"]} {dose_label(1.5, lang)}: {num(cr["K2"]["s_high"], lang)} {ci(cr["K2"]["ci_high"])}'),
        "K3": f'{w["diff"]} {num(cr["K3"]["diff"], lang)}, {w["ci"]} {ci(cr["K3"]["ci"])}',
        "K4": f'{w["diff"]} {num(cr["K4"]["diff"], lang)}, {w["ci"]} {ci(cr["K4"]["ci"])}',
        "F": f'{cr["F"]["rescued"]} {w["of"]} {cr["F"]["n"]}',
    }
    claim = {c[0]: c[1] for c in t["crit"]}
    rows = [(f"{k} · {claim[k]}", f'<b>{t["verdicts"].get(cr[k]["verdict"], cr[k]["verdict"])}</b>', cells[k])
            for k in ("K1", "K2", "K3", "K4", "F")]
    rows_all = [json.loads(l) for l in open(CONFIRM) if l.strip()]
    y, _ = an.confirmatory_table(rows_all, list(conditions()), SEED_FIRST, N_CONFIRM)
    sh = shares(y)
    cap = t["res_c1_cap"].format(n=sh["n"])
    return (f'<section id="results"><h2>{name}</h2><h3>{h3}</h3>{table(t["res_head"], rows)}'
            f'<p class="cap">{t["res_cap"].format(n=sh["n"])}</p>\n    {figures(sh, t, lang, cap, cap)}</section>')


def block(lang, sh, att, st):
    t = T[lang]
    f = dict(v_max=pct(max(sh["V"]), lang), n=sh["n"],
             m_mid=pct(np.mean([sh["M"][DOSES.index(d)] for d in (0.45, 0.6, 0.8, 1.0)]), lang),
             d_mid=pct(np.mean([sh["D"][DOSES.index(d)] for d in (0.45, 0.6, 0.8, 1.0)]), lang),
             e15=num(sh["E"]["E_L1.5"], lang), d15=num(sh["D"][DOSES.index(1.5)], lang),
             e06=num(sh["E"]["E_L0.6"], lang), d06=num(sh["D"][DOSES.index(0.6)], lang))
    prereg = GH + ("PREREGISTRATION_N4.md" if st != "draft" else "PREREGISTRATION_N4_черновик.md")
    ext = 'target="_blank" rel="noopener"'
    paras = lambda ps: "".join(f"\n    <p>{p.format(**f)}</p>" for p in ps)
    sec = lambda s, body: f'\n  <section><h2>{s[0]}</h2><h3>{s[1]}</h3>{body}</section>'
    o = [f'<div class="langblock" data-lang="{lang}" lang="{lang}">',
         f'  <h1>{t["h1"]}</h1>',
         f'  <div class="eyebrow">{t["eye"][st]}</div>',
         f'  <div class="byline"><b>MAKSIM ILIN</b> · {t["role"]}</div>',
         f'  <p class="lede">{t["lede"]}</p>',
         f'  <div class="cta"><a class="btn" href="{prereg}" {ext}>{t["cta"][0]}</a>'
         f'<a class="btn ghost" href="https://github.com/akela1308/minimir/tree/main/runs/n4" {ext}>{t["cta"][1]}</a>'
         f'<a class="btn ghost" href="results-b.html">{t["cta"][2]}</a>'
         f'<a class="btn ghost" href="notes.html">{t["cta"][3]}</a></div>',
         f'  <div class="callout{"" if st == "read" else " warn"}">{t["status"][st]}</div>']
    o.append(sec(t["s1"], paras(t["s1"][2])))
    o.append(sec(t["s2"], paras(t["s2"][2]) + "\n    " + table(t["parts_head"], t["parts"])
                 + f'\n    <p class="cap">{t["parts_cap"]}</p>'))
    o.append(sec(t["s3"], f'\n    <p>{t["s3"][2]}</p>\n    ' + table(t["crit_head"], t["crit"])
                 + f'\n    <p>{t["crit_after"]}</p>'))
    o.append(sec(t["s4"], paras(t["s4"][2]) + "\n    " + attain_table(att, t, lang)
                 + f'\n    <p class="cap">{t["att_cap"]}</p>\n    <p>{t["att_after"]}</p>'))
    fig = figures(sh, t, lang, t["c1_cap"], t["c2_cap"])
    a, b = fig.split("<figure>", 2)[1:]       # между рисунками идёт абзац о дозе
    o.append(sec(t["s5"], f'\n    <div class="callout warn">{t["pilot_warn"]}</div>\n    <figure>{a}'
                 f'<p>{t["p_dose"]}</p>\n    <figure>{b}\n    <p>{t["p_var"].format(**f)}</p>'
                 f'\n    <p>{t["p_rest"].format(**f)}</p>'))
    o.append(sec(t["s6"], paras(t["s6"][2])))
    o.append(sec(t["s7"], "\n    <ul>" + "".join(f"<li>{x}</li>" for x in t["s7"][2]) + "</ul>"))
    o.append(sec(t["s8"], paras(t["s8"][2])))
    o.append("\n  " + results(t, lang, st))
    fl = t["foot_links"]
    o.append(
        f'\n  <footer>{t["foot_a"]}: <a href="https://www.ilinmaks.com/" {ext}>Maksim Ilin</a>, {t["foot_role"]} · '
        f'<a href="https://www.linkedin.com/in/ilinmaks/" {ext}>LinkedIn</a><br>{t["foot_b"]}: '
        f'<a href="https://github.com/akela1308/minimir" {ext}>github.com/akela1308/minimir</a> · '
        f'<a href="{prereg}" {ext}>{fl[0]}</a> · <a href="{GH}runs/n4_analyze.py" {ext}>{fl[1]}</a> · '
        f'<a href="results-b.html">{fl[2]}</a> · <a href="journal.html">{fl[3]}</a><br>{t["foot_src"]}: '
        'R. Gomulkiewicz, R. D. Holt, “When does evolution by natural selection prevent extinction?”, Evolution, 1995; '
        'G. Bell, A. Gonzalez, “Evolutionary rescue can prevent extinction following environmental change”, '
        'Ecology Letters, 2009; L.-M. Chevin, R. Lande, G. M. Mace, “Adaptation, plasticity, and extinction in a '
        'changing environment”, PLoS Biology, 2010; G. E. Hinton, S. J. Nowlan, “How learning can guide evolution”, '
        f'Complex Systems, 1987.<span class="cite">{t["foot_contact"]}: '
        f'<a href="https://github.com/akela1308/minimir/issues" {ext}>GitHub issues</a> · '
        f'<a href="https://www.ilinmaks.com/" {ext}>www.ilinmaks.com</a></span></footer>\n</div>')
    return "\n".join(o)


CSS = """
  .byline{font-family:var(--mono);font-size:12px;color:var(--dim);letter-spacing:.04em;margin:6px 0 0}
  .byline b{color:var(--ink);font-weight:500}
  table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:12.5px}
  th,td{text-align:right;padding:6px 10px;border-bottom:1px solid var(--hair);white-space:nowrap}
  th{color:var(--faint);font-weight:500;font-size:10.5px;text-transform:uppercase;letter-spacing:.07em}
  th:first-child,td:first-child{text-align:left}
  td.k{color:var(--ink)}
  td.d{color:var(--dim);text-align:left;white-space:normal;font-family:var(--sans);font-size:13px}
  td.d b{color:var(--ink);font-weight:500}
  .cap{font-family:var(--mono);font-size:11.5px;color:var(--faint);margin:0;max-width:64ch;line-height:1.5}
  figure{margin:22px 0 10px;max-width:640px}
  .ct{font-family:var(--sans);font-size:14px;font-weight:500;color:var(--ink);margin:0 0 6px}
  .lg{display:flex;gap:18px;flex-wrap:wrap;font-family:var(--mono);font-size:11.5px;color:var(--dim);margin:0 0 4px}
  .lg span{display:inline-flex;align-items:center;gap:7px}
  .sw{display:inline-block;width:14px;height:3px;border-radius:2px}
  .sw.a{background:var(--cyan)} .sw.b{background:var(--amber)}
  .chart{display:block;width:100%;height:auto;overflow:visible}
  .chart.n{display:none}
  @media(max-width:560px){.chart.w{display:none}.chart.n{display:block}}
  .chart .g{stroke:var(--hair);stroke-width:1}
  .chart .ax{font-family:var(--mono);font-size:11px;fill:var(--faint)}
  .chart .axt{font-family:var(--mono);font-size:11px;fill:var(--dim)}
  .chart .lab{font-family:var(--sans);font-size:12px;fill:var(--ink)}
  .chart .ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
  .chart .ln.a{stroke:var(--cyan)} .chart .ln.b{stroke:var(--amber)}
  .chart .pt{stroke:var(--ground);stroke-width:2}
  .chart .pt.a{fill:var(--cyan)} .chart .pt.b{fill:var(--amber)}
  .chart .hit{fill:transparent}
  section ul{margin:0;padding-left:20px;max-width:70ch} section li{margin:0 0 8px}
"""

def page(sh, att, st):
    t = T["en"]
    plain = lambda s: s.replace("<br>", " ")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "headline": plain(t["h1"]), "inLanguage": ["en", "ru", "de", "es", "zh"],
         "datePublished": "2026-11-20", "url": f"{BASE}/n4.html",
         "author": {"@id": f"{BASE}/#author"}, "publisher": {"@id": f"{BASE}/#author"},
         "isPartOf": {"@id": f"{BASE}/#website"}},
        {"@type": "Person", "@id": f"{BASE}/#author", "name": "Maksim Ilin", "alternateName": "Максим Ильин",
         "jobTitle": "AI consultant, independent researcher", "url": "https://www.ilinmaks.com/",
         "sameAs": ["https://www.ilinmaks.com/", "https://www.linkedin.com/in/ilinmaks/"]},
        {"@type": "WebSite", "@id": f"{BASE}/#website", "name": "mini-world", "url": f"{BASE}/"}]}
    e = lambda s: html.escape(s, quote=True)
    head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(t["title"])}</title>
<meta name="description" content="{e(t["desc"])}">
<meta name="keywords" content="evolutionary rescue, evolution of learning, lifetime plasticity, standing variation, preregistration, artificial life, ALife, эволюционное спасение, эволюция обучения, предрегистрация">
<meta name="author" content="Maksim Ilin">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="canonical" href="{BASE}/n4.html">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<meta property="og:type" content="article">
<meta property="og:site_name" content="mini-world">
<meta property="og:title" content="{e(t["title"])}">
<meta property="og:description" content="{e(t["desc"])}">
<meta property="og:url" content="{BASE}/n4.html">
<meta property="og:image" content="{BASE}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(t["title"])}">
<meta name="twitter:description" content="{e(t["desc"])}">
<meta name="twitter:image" content="{BASE}/og.png">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, separators=(",", ":"))}</script>
<link rel="preload" href="fonts/ibm-plex-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="site.css">
<style>{CSS}</style>
</head>
<body>
<canvas id="amb"></canvas>
<div class="langbar" role="group" aria-label="language"><a class="brand" href="index.html">mini<span class="dot">·</span>world</a><div class="langs"><button data-set="en">EN</button><button data-set="ru">RU</button><button data-set="de">DE</button><button data-set="es">ES</button><button data-set="zh">中文</button></div></div>
<div class="wrap">
"""
    body = "\n".join(block(l, sh, att, st) for l in LANGS)
    titles = json.dumps({l: T[l]["title"] for l in LANGS}, ensure_ascii=False)
    descs = json.dumps({l: T[l]["desc"] for l in LANGS}, ensure_ascii=False)
    # скрипт языков и фона берётся со страницы результатов B, чтобы поведение совпадало
    src = (ROOT / "docs/results-b.html").read_text(encoding="utf-8")
    amb = src[src.index("// ненавязчивая «чашка Петри»"):src.rindex("</script>")]
    script = f"""
</div>

<script>
(function(){{
  const KEY='minimir_lang', DEF='en';
  const TITLES={titles};
  const DESCS={descs};
  const blocks=[...document.querySelectorAll('.langblock')];
  const btns=[...document.querySelectorAll('.langbar button')];
  function apply(l){{
    if(!blocks.some(b=>b.dataset.lang===l))l=DEF;
    blocks.forEach(b=>b.classList.toggle('on',b.dataset.lang===l));
    btns.forEach(b=>b.classList.toggle('on',b.dataset.set===l));
    document.documentElement.lang=l;
    if(TITLES[l])document.title=TITLES[l];
    const md=document.querySelector('meta[name=description]');if(md&&DESCS[l])md.setAttribute('content',DESCS[l]);
    try{{localStorage.setItem(KEY,l)}}catch(e){{}}
  }}
  btns.forEach(b=>b.onclick=()=>apply(b.dataset.set));
  let saved=DEF; try{{saved=localStorage.getItem(KEY)||DEF}}catch(e){{}}
  apply(saved);
}})();
{amb}</script>

</body>
</html>
"""
    return head + body + script


def main():
    y, _ = an.load_table(PILOT)
    sh = shares(y)
    att = json.load(open(ROOT / "runs/n4/attainability.json"))
    st = state()
    out = ROOT / "docs/n4.html"
    out.write_text(page(sh, att, st), encoding="utf-8")
    print(f"docs/n4.html: состояние {st}, {out.stat().st_size} байт")


if __name__ == "__main__":
    main()
