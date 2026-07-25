"""A.4: выход главной метрики на плато.

3 seed'а × 400 000 тиков. Плато проверяем на БЛОЧНЫХ СРЕДНИХ по блокам
15 000 тиков (preregistration §4: мгновенное MI следует за фазой колебания
численности «выел пятно — обвал — отрост», а не за эволюцией). Для этого
пишем лог с log_every=15000, так что каждое значение mi_window — это уже
блочное среднее MI за 15 000 тиков.

Вердикт плато: нормированный наклон хвоста (последние 30% блоков) < 1σ.
Если к 400k плато нет — сообщаем и НЕ увеличиваем длину молча.
"""
import json
import numpy as np
from sim import Config, Engine
from sim.metrics import mi_from_hist

SEEDS = [1, 2, 3]
TICKS = 400000
BLOCK = 15000

def plateau_slope(v, tail_frac=0.3):
    v = np.asarray([x for x in v if x is not None], float)
    if v.size < 6:
        return None
    k = max(int(v.size * tail_frac), 4)
    tail = v[-k:]
    x = np.arange(k)
    slope = np.polyfit(x, tail, 1)[0] * k
    sd = tail.std(ddof=1)
    return float(slope / sd) if sd > 0 else 0.0

results = {}
curves = {}
for seed in SEEDS:
    cfg = Config(seed=seed)
    eng = Engine(cfg)
    block_mis = []
    ticks_axis = []
    pops = []
    done = 0
    while done < TICKS:
        step = min(BLOCK, TICKS - done)
        eng.window_hist[:] = 0
        # накапливаем ровно один блок
        alive = True
        for _ in range(step):
            if not eng.step():
                alive = False
                break
            # window_hist накапливается в engine.step через np.add.at
        r = mi_from_hist(eng.window_hist)
        block_mis.append(r.get("mi_corrected_bits"))
        done += step
        ticks_axis.append(done)
        pops.append(eng.pop.count)
        if not alive:
            break
    sl = plateau_slope(block_mis)
    verdict = ("плато" if sl is not None and abs(sl) < 1.0
               else "ЕЩЁ РАСТЁТ" if sl and sl > 0 else "падает" if sl else "—")
    peak = max(pops) if pops else 0
    results[seed] = dict(seed=seed, ticks=done, n_blocks=len(block_mis),
                         tail_slope_sigma=sl, verdict=verdict,
                         extinct=eng.extinct_at, peak_pop=peak,
                         hit_ceiling=bool(peak >= 0.95 * cfg.max_pop),
                         block_mis=block_mis)
    curves[seed] = (ticks_axis, block_mis)
    print(f"seed {seed}: блоков {len(block_mis)}, наклон хвоста "
          f"{sl if sl is not None else float('nan'):.2f}σ -> {verdict}, "
          f"пик поп. {peak}{' CEILING' if results[seed]['hit_ceiling'] else ''}",
          flush=True)

with open("runs/a4_plateau.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)

# график
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for seed, (t, v) in curves.items():
        vv = [x if x is not None else np.nan for x in v]
        ax.plot(np.array(t) / 1000, vv, marker="o", ms=3, lw=1.2, label=f"seed {seed}")
    ax.set_xlabel("тик, тыс.")
    ax.set_ylabel("MI(энергия; действие), бит за блок 15k")
    ax.set_title("A.4 выход на плато по блочным средним (400k тиков)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("runs/figures/a4_plateau.png", dpi=130)
    print("график: runs/figures/a4_plateau.png")
except Exception as e:
    print("график пропущен:", e)
