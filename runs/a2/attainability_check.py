#!/usr/bin/env python3
"""Достижимость критерия протокола A2 (28 октября 2026).

Что проверяется. Прежнее правило черновика A2 («|средняя парная разница| >
2 sd парных разниц и p < 0,01») требовало стандартизованного парного эффекта
dz = mean/sd > 2; dz не уменьшается с числом seed'ов, и ни один эффект, который
этот мир когда-либо давал, его не проходит. Новое правило (PREREGISTRATION_A2
§4, runs/journal_a2.py): 95% ДИ парных разниц целиком выше наименьшего
интересующего эффекта delta_min (0,005 бит для внутриагентной MI, 0,0025 для
популяционной) и парный Уилкоксон p < 0,01.

Данные: 56 seed'ов протокола A (runs/compare.jsonl + runs/daily/compare_ext.jsonl,
только чтение). Для каждого сравнения печатаются n, среднее, sd, dz, SE, 95% ДИ
(t) и бутстреп-ДИ, p, вердикт старого и нового правила на этих 56 seed'ах, и
проекция на n = 20: ожидаемая полуширина ДИ t(0,975; 19) * sd / sqrt(20) и
проходит ли при такой ширине эффект 0,02 и эффект 0,005.

Основано на /science/check_a2_criterion.py (рецензент, 28.10.2026). Запуск из
корня репозитория:

  python runs/a2/attainability_check.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs"))

from journal import wilcoxon_p                                   # noqa: E402
import journal_a2 as ja                                          # noqa: E402

FILES = ("runs/compare.jsonl", "runs/daily/compare_ext.jsonl")
N_PLANNED = 20
PROBE_EFFECTS = (0.02, 0.005)


def load_rows():
    rows = []
    for f in FILES:
        p = ROOT / f
        if not p.exists():
            continue
        for line in open(p):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def valid(r):
    return (r.get("extinct") is None and not r.get("hit_ceiling")
            and (r.get("occupied_deciles") or 0) >= 4 and r.get("within_mi") is not None)


def contrast(by, a, b, metric):
    seeds = sorted(set(by[a]) & set(by[b]))
    x = np.array([by[a][s][metric] for s in seeds], float)
    y = np.array([by[b][s][metric] for s in seeds], float)
    d = x - y
    p = wilcoxon_p(x, y)
    key = "within_mi_200" if metric == "within_mi" else "mi"
    st = ja.paired_summary(d, ja.DELTA_MIN[key], p)
    st["old_rule_pass"] = bool(abs(st["mean_diff"]) > 2 * st["sd_diff"] and p is not None and p < 0.01)
    st["old_rule_needs"] = 2 * st["sd_diff"]
    return st


def main():
    rows = load_rows()
    by = {}
    for r in rows:
        if valid(r):
            by.setdefault(r["label"], {})[r["seed"]] = r
    print("годных строк по условиям:", {k: len(v) for k, v in by.items()})
    print(f"delta_min: {ja.DELTA_MIN}; p < {ja.P_CONFIRM}; бутстреп {ja.BOOT_N} выборок, seed {ja.BOOT_SEED}")
    tq = ja.t_quantile(N_PLANNED - 1)
    print(f"t(0.975; {N_PLANNED - 1}) = {tq:.3f}")
    for metric, name in (("within_mi", "внутриагентная MI (порог 1000 на этапе 1; в A2 главный порог 200)"),
                         ("mi", "популяционная MI")):
        key = "within_mi_200" if metric == "within_mi" else "mi"
        dmin = ja.DELTA_MIN[key]
        print(f"\n== {name}, delta_min = {dmin} ==")
        for a, b in (("self", "shuffled"), ("self", "off"), ("off", "shuffled"),
                     ("self", "neighbour"), ("neighbour", "shuffled")):
            c = contrast(by, a, b, metric)
            half20 = tq * c["sd_diff"] / math.sqrt(N_PLANNED)
            probes = ", ".join(f"эффект {e}: ДИ [{e - half20:+.4f}; {e + half20:+.4f}] -> "
                               f"{'проходит' if e - half20 > dmin else 'не проходит'}" for e in PROBE_EFFECTS)
            print(f"{a:>9} - {b:<9} n={c['n']:2d} mean={c['mean_diff']:+.4f} sd={c['sd_diff']:.4f} "
                  f"dz={c['dz']:+.2f} SE={c['se']:.4f} CI95=[{c['ci_low']:+.4f}; {c['ci_high']:+.4f}] "
                  f"boot=[{c['boot_ci_low']:+.4f}; {c['boot_ci_high']:+.4f}] p={c['p']:.1e}")
            print(f"{'':22}старое правило (dz>2 & p<.01): {'проходит' if c['old_rule_pass'] else 'НЕ проходит'} "
                  f"(нужно |mean| > {c['old_rule_needs']:.4f}); новое правило на 56 seed'ах: {c['verdict']}")
            print(f"{'':22}при n = {N_PLANNED}: полуширина ДИ {half20:.4f}; {probes}")
    c = contrast(by, "self", "shuffled", "within_mi")
    half20 = tq * c["sd_diff"] / math.sqrt(N_PLANNED)
    print(f"\nИтог: self - shuffled (внутриагентная MI) mean {c['mean_diff']:.4f}, sd {c['sd_diff']:.4f}, "
          f"dz {c['dz']:.2f}; при n = {N_PLANNED} полуширина ДИ около {half20:.3f}: эффект 0,02 проходит "
          f"delta_min = {ja.DELTA_MIN['within_mi_200']}, эффект 0,005 не проходит (ДИ накрывает delta_min, "
          f"вердикт «не определено»). Старое правило требовало {c['old_rule_needs']:.4f}, "
          f"в {c['old_rule_needs'] / c['mean_diff']:.1f} раза больше наблюдённого.")


if __name__ == "__main__":
    main()
