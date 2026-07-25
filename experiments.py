#!/usr/bin/env python3
"""Экспериментальный раннер: калибровка, уровень шума, сравнение условий.

  python experiments.py calibrate                    # кривая чувствительности метрики
  python experiments.py noise --seeds 10             # разброс одного условия
  python experiments.py compare --seeds 20           # self vs shuffled vs neighbour vs off

Считает главную метрику на СТАЦИОНАРНОМ участке: первые 75% тиков — прогрев
и эволюция, метрики обнуляются, измерение идёт по последней четверти.
"""
import argparse
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np

from sim import Config, Engine, metrics


# --------------------------------------------------------------------- прогон
def measure(job):
    """Один прогон -> словарь чисел. Всё, что нужно воркеру, лежит в job."""
    cfg = Config(**job["cfg"])
    ticks = job["ticks"]
    warm = int(ticks * 0.75)
    eng = Engine(cfg)
    eng.run(warm)
    eng.reset_metrics()                    # измеряем только стационар
    eng.run(ticks - warm)
    st = eng.stats()
    mi = metrics.behaviour_depends_on_energy(eng)
    occ = metrics.energy_occupancy(eng)
    sw = metrics.switch_point(eng)
    return dict(
        label=job["label"], seed=cfg.seed,
        mi=mi.get("mi_corrected_bits"),
        mi_raw=mi.get("mutual_information_bits"),
        chance=mi.get("chance_level_bits"),
        samples=mi.get("samples"),
        occupancy_bits=occ["entropy_bits"],
        occupied_deciles=occ["occupied_deciles"],
        switch_energy=sw["switch_energy"],
        amplitude=sw["amplitude"],
        pop=st["pop"], extinct=eng.extinct_at,
        forage_accuracy=st["forage_accuracy"],
    )


def run_jobs(jobs, workers=None):
    workers = workers or min(mp.cpu_count(), len(jobs))
    if workers <= 1:
        return [measure(j) for j in jobs]
    with mp.Pool(workers) as pool:
        return pool.map(measure, jobs)


# ------------------------------------------------------------------ статистика
def wilcoxon_paired(a, b):
    """Парный тест Уилкоксона по seed'ам. scipy если есть, иначе руками."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    if a.size < 5:
        return dict(n=int(a.size), p=None, note="слишком мало пар")
    try:
        from scipy.stats import wilcoxon
        stat, p = wilcoxon(a, b)
        return dict(n=int(a.size), statistic=float(stat), p=float(p))
    except Exception:
        d = a - b
        d = d[d != 0]
        r = np.argsort(np.argsort(np.abs(d))) + 1
        w = min(r[d > 0].sum(), r[d < 0].sum())
        n = d.size
        mu = n * (n + 1) / 4
        sd = np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
        z = (w - mu) / sd if sd else 0.0
        from math import erfc, sqrt
        return dict(n=int(n), statistic=float(w), z=float(z),
                    p=float(erfc(abs(z) / sqrt(2))))


def effect_size(a, b):
    """Величина эффекта Клиффа: доля пар, где a > b, минус обратная."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    if a.size == 0:
        return None
    gt = (a[:, None] > b[None, :]).sum()
    lt = (a[:, None] < b[None, :]).sum()
    return float((gt - lt) / (a.size * b.size))


def summarize(rows, key="mi"):
    vals = np.array([r[key] for r in rows if r[key] is not None], float)
    if vals.size == 0:
        return dict(n=0)
    return dict(n=int(vals.size), mean=float(vals.mean()), sd=float(vals.std(ddof=1)) if vals.size > 1 else 0.0,
                min=float(vals.min()), max=float(vals.max()),
                median=float(np.median(vals)))


# -------------------------------------------------------------------- режимы
def cmd_calibrate(args):
    """Кривая чувствительности: где должен стоять порог, чтобы метрика его увидела."""
    jobs = []
    for thr in (20, 30, 40, 50, 60, 70, 85):
        jobs.append(dict(label=f"threshold@{thr}", ticks=args.ticks,
                         cfg=dict(seed=args.seed, policy="threshold",
                                  policy_threshold=float(thr))))
    jobs.append(dict(label="random", ticks=args.ticks,
                     cfg=dict(seed=args.seed, policy="random")))
    jobs.append(dict(label="evolved", ticks=args.ticks, cfg=dict(seed=args.seed)))
    rows = run_jobs(jobs, args.workers)
    print(f"\n{'условие':>14} {'MI, бит':>9} {'случайн.':>9} {'занято дец.':>12} "
          f"{'H(энергия)':>11} {'популяция':>10}")
    for r in rows:
        mi = f"{r['mi']:.4f}" if r["mi"] is not None else "мало данных"
        ch = f"{r['chance']:.5f}" if r["chance"] is not None else "—"
        print(f"{r['label']:>14} {mi:>9} {ch:>9} "
              f"{r['occupied_deciles']:>12} {r['occupancy_bits']:>11.2f} {r['pop']:>10}")
    print("\nЧитается так: метрика видит зависимость только там, где порог попадает")
    print("внутрь диапазона энергий, который популяция реально занимает.")
    return rows


def cmd_noise(args):
    """Уровень шума: одно и то же условие на разных seed'ах."""
    jobs = [dict(label="self", ticks=args.ticks, cfg=dict(seed=s))
            for s in range(1, args.seeds + 1)]
    rows = run_jobs(jobs, args.workers)
    st = summarize(rows)
    print(f"\nодно условие, {st['n']} seed'ов, {args.ticks} тиков")
    print(f"  MI: среднее {st['mean']:.4f}, sd {st['sd']:.4f}, "
          f"размах {st['min']:.4f}..{st['max']:.4f}")
    print(f"  значения: {[round(r['mi'], 4) for r in rows if r['mi'] is not None]}")
    print(f"  вымерло прогонов: {sum(1 for r in rows if r['extinct'] is not None)}")
    print(f"\n  ЛЮБАЯ разница между условиями меньше {2*st['sd']:.4f} бит "
          f"неотличима от шума при таком числе seed'ов.")
    return rows


def cmd_compare(args):
    """Главный эксперимент: четыре условия на одних и тех же seed'ах."""
    conds = ["self", "shuffled", "neighbour", "off"]
    jobs = []
    for s in range(1, args.seeds + 1):
        for c in conds:
            jobs.append(dict(label=c, ticks=args.ticks,
                             cfg=dict(seed=s, intero_mode=c,
                                      interoception=(c != "off"))))
    rows = run_jobs(jobs, args.workers)
    by = {c: [r for r in rows if r["label"] == c] for c in conds}
    for c in conds:
        by[c].sort(key=lambda r: r["seed"])

    print(f"\n{'условие':>10} {'MI сред.':>9} {'sd':>8} {'медиана':>9} {'выжило':>8}")
    for c in conds:
        st = summarize(by[c])
        alive = sum(1 for r in by[c] if r["extinct"] is None)
        if st["n"] == 0:
            print(f"{c:>10} {'нет данных':>9} {'':>8} {'':>9} {alive:>4}/{len(by[c])}")
            continue
        print(f"{c:>10} {st['mean']:>9.4f} {st['sd']:>8.4f} "
              f"{st['median']:>9.4f} {alive:>4}/{len(by[c])}")

    print("\nпарные сравнения с контролем (Уилкоксон по seed'ам):")
    base = [r["mi"] for r in by["shuffled"]]
    for c in ("self", "neighbour", "off"):
        vals = [r["mi"] for r in by[c]]
        w = wilcoxon_paired(vals, base)
        d = effect_size(vals, base)
        pstr = f"p={w['p']:.4f}" if w.get("p") is not None else w.get("note", "—")
        print(f"  {c:>10} vs shuffled: {pstr}, дельта Клиффа {d:+.3f}, n={w['n']}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"\nсырые числа: {out}")
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["calibrate", "noise", "compare"])
    p.add_argument("--ticks", type=int, default=80000)
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--out", default="runs/compare.json")
    args = p.parse_args()
    args.workers = args.workers or None
    {"calibrate": cmd_calibrate, "noise": cmd_noise, "compare": cmd_compare}[args.mode](args)


if __name__ == "__main__":
    main()
