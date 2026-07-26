"""Собрать версии страниц для GitHub Pages в docs/.

Берёт самодостаточные фрагменты (minimir_viewer.html, about.html — это тело
без обёртки), заворачивает в полноценный HTML-документ и заменяет
кросс-ссылки с URL артефактов claude.ai на относительные пути, чтобы всё
работало на статике Pages независимо от Claude.

  docs/index.html  <- about.html      (лендинг «о проекте»)
  docs/sim.html    <- minimir_viewer  (живая симуляция)
"""
from pathlib import Path

ART_VIEWER = "https://claude.ai/code/artifact/e9a5c20f-0137-466d-8f7b-769b5a24db34"
ART_ABOUT = "https://claude.ai/code/artifact/7876772a-43f0-4fb5-b761-db802aa896a9"

HEAD = ('<!doctype html>\n<html lang="ru">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '</head>\n<body>\n')
TAIL = '\n</body>\n</html>\n'

docs = Path("docs")
docs.mkdir(exist_ok=True)

# лендинг: about, ссылка на симуляцию -> sim.html
about = Path("about.html").read_text().replace(ART_VIEWER, "sim.html")
(docs / "index.html").write_text(HEAD + about + TAIL)

# симуляция: viewer, ссылка «о проекте» -> index.html
viewer = Path("minimir_viewer.html").read_text().replace(ART_ABOUT, "index.html")
(docs / "sim.html").write_text(HEAD + viewer + TAIL)

# .nojekyll — чтобы Pages не пытался обрабатывать через Jekyll
(docs / ".nojekyll").write_text("")

for f in ("index.html", "sim.html"):
    print(f"docs/{f}: {(docs/f).stat().st_size/1024:.0f} KB")
