# -*- coding: utf-8 -*-
"""Собрать docs/ для GitHub Pages: страницы + SEO + разрешение ИИ-ботов.

- заворачивает самодостаточные фрагменты (about.html, minimir_viewer.html)
  в полноценный HTML-документ с богатым <head> (title, description, canonical,
  Open Graph, Twitter Card, favicon, JSON-LD schema.org);
- кросс-ссылки артефактов claude.ai заменяет на относительные пути;
- пишет robots.txt (явно разрешает поисковые и ИИ-краулеры), sitemap.xml,
  favicon.svg, og.png (карточка для соцсетей и предпросмотров).
"""
import re
from pathlib import Path

BASE = "https://akela1308.github.io/minimir"
GH = "https://github.com/akela1308/minimir"
ART_VIEWER = "https://claude.ai/code/artifact/e9a5c20f-0137-466d-8f7b-769b5a24db34"
ART_ABOUT = "https://claude.ai/code/artifact/7876772a-43f0-4fb5-b761-db802aa896a9"
LASTMOD = "2026-07-26"

docs = Path("docs")
docs.mkdir(exist_ok=True)

KEYWORDS = ("artificial life, ALife, evolutionary simulation, agent-based model, "
            "emergence of needs, interoception, cooperation, altruism, Vygotsky, "
            "Ilyenkov, internalization, sign, neural network agents, open research, "
            "мини-мир, искусственная жизнь")

JSONLD = ('{"@context":"https://schema.org","@graph":['
          '{"@type":"WebSite","@id":"%(base)s/#website","name":"mini-world",'
          '"alternateName":"мини-мир","url":"%(base)s/",'
          '"description":"%(desc)s","inLanguage":["en","ru","de","es","zh"],'
          '"keywords":"%(kw)s","sameAs":["%(gh)s"]},'
          '{"@type":"SoftwareSourceCode","name":"mini-world",'
          '"codeRepository":"%(gh)s","programmingLanguage":"Python",'
          '"about":"Artificial-life engine testing whether need-like behaviour '
          'emerges from selection alone, with no fitness function.",'
          '"url":"%(base)s/"}]}')


def head(title, desc, canonical, lang="en"):
    ld = JSONLD % dict(base=BASE, desc=desc.replace('"', "'"), kw=KEYWORDS, gh=GH)
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{KEYWORDS}">
<meta name="author" content="akela1308">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<meta property="og:type" content="website">
<meta property="og:site_name" content="mini-world">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{BASE}/og.png">
<script type="application/ld+json">{ld}</script>
</head>
<body>
"""


TAIL = "\n</body>\n</html>\n"


def wrap(src_text, url_replace, title, desc, canonical):
    body = src_text.replace(url_replace[0], url_replace[1])
    body = re.sub(r"^<title>.*?</title>\s*", "", body, count=1, flags=re.S)
    return head(title, desc, canonical) + body + TAIL


ABOUT_DESC = ("A tiny world of evolving creatures with no reward and no judge. "
              "We measure whether behaviour that looks like a need can emerge from "
              "selection alone — interoception, cooperation, and Vygotsky's sign. "
              "Open research: code, data, report.")
SIM_DESC = ("Watch a real recorded run of the mini-world: creatures coloured by "
            "energy, food, marks, and live charts of population, energy, mutual "
            "information and cooperation.")

(docs / "index.html").write_text(
    wrap(Path("about.html").read_text(encoding="utf-8"), (ART_VIEWER, "sim.html"),
         "mini·world — artificial life with no fitness function",
         ABOUT_DESC, BASE + "/"), encoding="utf-8")

(docs / "sim.html").write_text(
    wrap(Path("minimir_viewer.html").read_text(encoding="utf-8"), (ART_ABOUT, "index.html"),
         "mini·world — live simulation",
         SIM_DESC, BASE + "/sim.html"), encoding="utf-8")

# --- favicon (эмодзи-чашка Петри в SVG) ---
(docs / "favicon.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<text x="50" y="54" font-size="72" text-anchor="middle" '
    'dominant-baseline="central">\U0001F9EB</text></svg>', encoding="utf-8")

# --- robots.txt: явно приглашаем поисковые и ИИ-краулеры ---
ai_bots = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "Google-Extended",
           "PerplexityBot", "PerplexityBot/1.0", "ClaudeBot", "Claude-Web",
           "anthropic-ai", "Applebot-Extended", "Bytespider", "CCBot",
           "Amazonbot", "cohere-ai", "Meta-ExternalAgent", "Timpibot",
           "YouBot", "Diffbot"]
robots = "User-agent: *\nAllow: /\n\n"
for b in ai_bots:
    robots += f"User-agent: {b}\nAllow: /\n\n"
robots += f"Sitemap: {BASE}/sitemap.xml\n"
(docs / "robots.txt").write_text(robots, encoding="utf-8")

# --- sitemap.xml ---
sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
for loc, pr in ((BASE + "/", "1.0"), (BASE + "/sim.html", "0.8")):
    sm += (f"  <url><loc>{loc}</loc><lastmod>{LASTMOD}</lastmod>"
           f"<changefreq>weekly</changefreq><priority>{pr}</priority></url>\n")
sm += "</urlset>\n"
(docs / "sitemap.xml").write_text(sm, encoding="utf-8")

(docs / ".nojekyll").write_text("")

# --- og.png: карточка для соцсетей и предпросмотров ---
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(12, 6.3), dpi=100)
    fig.patch.set_facecolor("#0a0e11")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor("#0a0e11")
    ax.set_xlim(0, 1200); ax.set_ylim(0, 630); ax.axis("off")
    # дрейфующие точки цвета энергии
    import numpy as np
    rng = np.random.default_rng(1)
    for _ in range(120):
        t = rng.random()
        if t < .5:
            u = t / .5; r = 0xe8 + (0xd9 - 0xe8) * u; g = 0x73 + (0xc2 - 0x73) * u; b = 0x4a + (0x6a - 0x4a) * u
        else:
            u = (t - .5) / .5; r = 0xd9 + (0x46 - 0xd9) * u; g = 0xc2 + (0xc6 - 0xc2) * u; b = 0x6a + (0xd0 - 0x6a) * u
        ax.scatter(rng.uniform(0, 1200), rng.uniform(0, 630), s=rng.uniform(6, 60),
                   color=(r / 255, g / 255, b / 255), alpha=0.28, edgecolors="none")
    mono = {"family": "monospace"}
    ax.text(80, 400, "mini·world", color="#e9f1f2", fontsize=76, fontweight="bold", **mono)
    ax.text(84, 336, "искусственная жизнь · artificial life", color="#46c6d0",
            fontsize=22, **mono)
    ax.text(84, 250, "Can behaviour that looks like a need emerge from",
            color="#93a6ae", fontsize=25, **mono)
    ax.text(84, 212, "selection alone — with no reward and no judge?",
            color="#93a6ae", fontsize=25, **mono)
    ax.text(84, 96, "open research · code · data · report",
            color="#5b6f77", fontsize=19, **mono)
    ax.text(84, 60, "github.com/akela1308/minimir", color="#e6c14a", fontsize=19, **mono)
    fig.savefig(docs / "og.png", facecolor="#0a0e11")
    plt.close(fig)
    print("og.png создан")
except Exception as e:
    print("og.png пропущен:", e)

for f in ("index.html", "sim.html"):
    print(f"docs/{f}: {(docs/f).stat().st_size/1024:.0f} KB")
print("robots.txt, sitemap.xml, favicon.svg записаны")
