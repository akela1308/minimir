"""Калибровка прибора до первого платного вызова.

1. Нуль по построению: боты, у которых эффекта нет по устройству. Критерий
   не должен выдавать «подтверждён».
2. Посаженный эффект: в доле share семян агентом служит бот опыта, в остальных
   фоновый бот. Для каждой доли 300 воображаемых опытов по N семян: как часто
   критерий подтверждает, опровергает и оставляет без вердикта.
Вывод печатается и пишется в CALIBRATION.md.
"""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import run_seed
from analyze import contrasts, DELTA

POOL, NS, EXPERIMENTS = 400, (30, 60), 300
SHARES = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)


def pool(kind):
    return [{r["arm"]: r for r in run_seed(kind, 50000 + i)} for i in range(POOL)]


def main():
    out = [f"# Калибровка стенда 1.1\n\nПул: {POOL} семян на каждого бота. "
           f"Воображаемых опытов на строку: {EXPERIMENTS}. Наименьший эффект DELTA = {DELTA}.\n"]
    pools = {k: pool(k) for k in ("never", "random", "narrative", "experience")}
    out.append("## Средняя доля B на шагах 101-200 по рукавам\n\n| бот | рукав 1 | рукав 2 | рукав 3 | рукав 4 |\n|---|---|---|---|---|")
    for k, p in pools.items():
        m = [sum(q[a]["b_share_h2"] for q in p) / len(p) for a in (1, 2, 3, 4)]
        out.append(f"| {k} | " + " | ".join(f"{v:.3f}" for v in m) + " |")
    rng = random.Random(7)
    for N in NS:
      for contrast, bg in (("A", "random"), ("B", "narrative")):
        out.append(f"\n## Контраст {contrast}, {N} семян: бот опыта в доле семян, фон {bg}\n\n"
                   "| доля семян с ботом опыта | средняя разница | подтверждён | не определён | опровергнут |\n|---|---|---|---|---|")
        for share in SHARES:
            tally = {"подтверждён": 0, "не определён": 0, "опровергнут": 0, "прибор слеп": 0}
            means = []
            for _ in range(EXPERIMENTS):
                quad = {i: (rng.choice(pools["experience"]) if rng.random() < share else rng.choice(pools[bg]))
                        for i in range(N)}
                res = contrasts(quad, n_boot=1000, seed=rng.random())
                tally[res[contrast]["verdict"]] += 1
                means.append(res[contrast]["mean"])
            e = EXPERIMENTS
            out.append(f"| {share:.2f} | {sum(means)/e:+.3f} | {tally['подтверждён']/e:.2f} | "
                       f"{tally['не определён']/e:.2f} | {(tally['опровергнут']+tally['прибор слеп'])/e:.2f} |")
    text = "\n".join(out) + "\n"
    print(text)
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "CALIBRATION.md"), "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
