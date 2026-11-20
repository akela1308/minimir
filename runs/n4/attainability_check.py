#!/usr/bin/env python3
"""Достижимость критериев протокола N4 (20 ноября 2026).

Урок протоколов A, B1 и черновиков A2, B2: четыре раза объявленный критерий не
мог пройти ни при каком исходе, и дважды абляция не могла провалиться. Поэтому
до заморозки каждый критерий N4 прогоняется на синтетических данных двух
сортов, и обе проверки публикуются вместе с предрегистрацией.

  1. Правдоподобный эффект. Семена пилота 2 пересэмплируются с возвращением до
     объёма подтверждающего прогона. Пары внутри семени сохраняются, значит
     сохраняется и настоящая зависимость условий между собой. Критерий должен
     проходить не реже чем в 80% таких наборов.
  2. Ноль по построению. Для каждого критерия строится набор, где эффекта нет
     по устройству данных. Критерий должен проходить не чаще чем в 5% наборов.

Число семян выбирается здесь же: наименьшее, при котором выполнены оба условия
для всех критериев.

  python runs/n4/attainability_check.py runs/n4/pilot/pilot2.jsonl
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runs"))
import n4_analyze as an                                     # noqa: E402

REPS = 400
SIZES = [60, 90, 120, 150]
an.N_BOOT = 2000          # в проверке меньше повторов, чем в чтении: считается сотни раз
an.N_PERM = 2000

PASS = {"K1": "подтверждено", "K2": "подтверждено", "K3": "подтверждено",
        "K4": "мягче хуже"}


def resample(y, seeds, n, rng):
    pick = rng.choice(seeds, size=n, replace=True)
    return {c: {i: col[s] for i, s in enumerate(pick)} for c, col in y.items()
            if all(s in col for s in seeds)}


def flip_symmetric(col, rate, rng):
    """Копия столбца с симметричными переворотами: доля единиц в среднем та же."""
    v = np.array(list(col.values()))
    p = v.mean()
    if p in (0.0, 1.0):
        return dict(col)
    a = rate                                  # 1 -> 0
    b = min(1.0, rate * p / (1 - p))          # 0 -> 1, чтобы среднее сохранилось
    u = rng.random(v.size)
    out = np.where(v == 1, (u >= a).astype(int), (u < b).astype(int))
    return {k: int(x) for k, x in zip(col.keys(), out)}


def null_for(name, y, rng):
    """Набор, где эффект критерия отсутствует по построению."""
    z = {c: dict(col) for c, col in y.items()}
    keys = list(next(iter(z.values())).keys())
    if name == "K1":      # дозы не различаются: каждая это независимый жребий с общей вероятностью
        p = float(np.mean([np.mean(list(z[c].values())) for c in an.D_ALL]))
        for c in an.D_ALL:
            z[c] = {k: int(rng.random() < p) for k in keys}
    elif name == "K2":    # резкий порог: до 0,8 не выживает никто, от 1,0 выживают все
        for c in an.D_ALL:
            dose = float(c.split("_L")[1])
            z[c] = {k: int(dose >= 1.0) for k in keys}
    elif name == "K3":    # sigma не влияет
        p = float(np.mean([np.mean(list(z[c].values())) for c in an.V_ALL]))
        for c in an.V_ALL:
            z[c] = {k: int(rng.random() < p) for k in keys}
    elif name == "K4":    # тяжесть яда не влияет: тот же столбец с симметричными переворотами
        for m, d in an.M_MID:
            z[m] = flip_symmetric(z[d], 0.15, rng)
    return z


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "runs/n4/pilot/pilot2.jsonl")
    y, rows = an.load_table(path)
    need = set(an.D_ALL + an.V_ALL + [c for p in an.M_MID for c in p] + [an.F_COND])
    seeds = sorted(set.intersection(*[set(y[c]) for c in need]))
    print(f"пилот: {path}, полных семян {len(seeds)}")
    print("доля спасённых в пилоте:")
    for c in sorted(need, key=lambda c: (c[0], float(c.split('_')[1][1:]))):
        print(f"  {c:9s} {np.mean([y[c][s] for s in seeds]):.2f}")
    print("\nвердикты на самом пилоте (не чтение, только проверка кода):")
    for k, r in an.evaluate({c: {s: y[c][s] for s in seeds} for c in need}).items():
        print(f"  {k}: {r['verdict']}")

    rng = np.random.default_rng(20261120)
    out = {}
    print(f"\nдоля наборов, где критерий проходит ({REPS} наборов на клетку):")
    print("  n    | " + " | ".join(f"{k}: эффект / ноль" for k in PASS))
    for n in SIZES:
        cells = []
        for name, want in PASS.items():
            hit_eff = hit_null = 0
            for _ in range(REPS):
                d = resample(y, seeds, n, rng)
                if an.CRITERIA[name](d)["verdict"] == want:
                    hit_eff += 1
                if an.CRITERIA[name](null_for(name, d, rng))["verdict"] == want:
                    hit_null += 1
            out[(n, name)] = (hit_eff / REPS, hit_null / REPS)
            cells.append(f"    {hit_eff / REPS:4.2f} / {hit_null / REPS:4.2f}   ")
        print(f"  {n:4d} | " + " | ".join(cells), flush=True)

    ok_n = [n for n in SIZES if all(out[(n, k)][0] >= 0.80 and out[(n, k)][1] <= 0.05 for k in PASS)]
    print("\nнаименьшее число семян, при котором все критерии и достижимы, и не проходят на нуле:",
          ok_n[0] if ok_n else "не найдено в сетке")
    weak = [(n, k, out[(n, k)]) for n in SIZES for k in PASS
            if out[(n, k)][0] < 0.80 or out[(n, k)][1] > 0.05]
    if weak:
        print("клетки, где условие не выполнено (n, критерий, (эффект, ноль)):")
        for w in weak:
            print("  ", w)
    json.dump({f"{n}|{k}": v for (n, k), v in out.items()},
              open(ROOT / "runs/n4/attainability.json", "w"), indent=1)


if __name__ == "__main__":
    main()
