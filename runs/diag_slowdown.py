"""Блок 0.3: почему пилот 4×5×15000 не укладывался в 18 минут на 8 ядрах.

Гипотеза: в каком-то условии популяция разрастается к max_pop=2000 и тянет
скорость вниз (forward-pass, плотность, поиск соседа — всё растёт с числом
агентов). Проверяем траектории численности и скорость как функцию популяции.
"""
import json
import time
import numpy as np
from sim import Config, Engine

TICKS = 15000
SEEDS = [1, 2]
CONDS = [("self", dict(intero_mode="self", interoception=True)),
         ("shuffled", dict(intero_mode="shuffled", interoception=True)),
         ("neighbour", dict(intero_mode="neighbour", interoception=True)),
         ("off", dict(intero_mode="off", interoception=False))]

out = []
for seed in SEEDS:
    for name, over in CONDS:
        cfg = Config(seed=seed, **over)
        eng = Engine(cfg)
        traj = []
        t0 = time.time()
        # ручной цикл с замером скорости по сегментам
        seg = 500
        seg_times = []
        for start in range(0, TICKS, seg):
            ts = time.time()
            eng.run(seg)
            dt = time.time() - ts
            seg_times.append((eng.pop.count, seg / dt if dt > 0 else 0))
            traj.append(eng.pop.count)
            if eng.extinct_at is not None:
                break
        total = time.time() - t0
        peak = max(traj) if traj else 0
        rec = dict(seed=seed, cond=name, ticks=eng.tick, wall_s=round(total, 1),
                   peak_pop=peak, final_pop=eng.pop.count,
                   extinct=eng.extinct_at,
                   hit_ceiling=bool(peak >= 0.95 * cfg.max_pop),
                   traj=traj,
                   speed_by_pop=[(int(p), round(s)) for p, s in seg_times])
        out.append(rec)
        print(f"seed{seed} {name:>10}: peak_pop={peak:>5} final={eng.pop.count:>5} "
              f"wall={total:>5.1f}s ticks={eng.tick} "
              f"{'<<< CEILING' if rec['hit_ceiling'] else ''}", flush=True)

with open("runs/diag_slowdown.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# сводка скорости против популяции
print("\n--- скорость тик/с по децилям популяции (все условия вместе) ---")
allpts = [(p, s) for r in out for p, s in r["speed_by_pop"] if s > 0]
allpts.sort()
if allpts:
    ps = np.array([p for p, s in allpts]); ss = np.array([s for p, s in allpts])
    for lo in range(0, int(ps.max()) + 1, 250):
        m = (ps >= lo) & (ps < lo + 250)
        if m.any():
            print(f"  pop {lo:>4}-{lo+250:<4}: {ss[m].mean():>6.0f} тик/с  (n={m.sum()})")
