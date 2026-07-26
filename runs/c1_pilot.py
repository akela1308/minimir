"""C.1: пилот на жизнеспособность знакового слоя и пластичности.

Стоимость метки и хеббовское обучение меняют физику мира — до всего
остального проверяем, что мир не рушится (STAGE3_DESIGN §10.1, граница
провала 6). Четыре условия × 5 seed × 15000 тиков:
  базовый | только знаки | только пластичность | знаки+пластичность
Проверка: не вымирает, не упирается в потолок, медиана жизни >= 400 тиков.
Дополнительно: куда эволюционирует генетически кодированная скорость обучения
lr (старт 0.002) — рост = пластичность полезна, падение к нулю = отбор её
отключает (и это тоже результат).
"""
import json
import numpy as np
from sim import Config, Engine

SEEDS = [1, 2, 3, 4, 5]
TICKS = 15000
CONDS = {
    "базовый": dict(signs=False, hebbian=False),
    "только_знаки": dict(signs=True, hebbian=False),
    "только_пластичность": dict(signs=False, hebbian=True),
    "знаки+пластичность": dict(signs=True, hebbian=True),
}

rows = []
for name, over in CONDS.items():
    for seed in SEEDS:
        cfg = Config(seed=seed, **over)
        eng = Engine(cfg)
        peak_box = [0]
        def rec(e, _p=peak_box):
            if e.pop.count > _p[0]: _p[0] = e.pop.count
        eng.run(TICKS, on_log=rec)
        peak = peak_box[0]
        ids = eng.pop.ids()
        lifespans = np.array(eng.pop.lifespans, float)
        med_life = float(np.median(lifespans)) if lifespans.size else 0.0
        lr_alive = eng.pop.brains.lr[ids]
        rows.append(dict(cond=name, seed=seed,
                         extinct=eng.extinct_at, pop=int(ids.size), peak_pop=peak,
                         hit_ceiling=bool(peak >= 0.95 * cfg.max_pop),
                         median_life=med_life, n_deaths=int(lifespans.size),
                         lr_mean=float(lr_alive.mean()) if ids.size else None,
                         lr_start=cfg.hebb_rate_init,
                         hebbian=over["hebbian"], signs=over["signs"]))
        r = rows[-1]
        lrs = f"{r['lr_mean']:.5f}" if r['lr_mean'] is not None else "—"
        print(f"{name:>22} seed{seed}: pop={r['pop']:>4} peak={peak:>4} "
              f"med_life={med_life:>6.0f} extinct={r['extinct']} "
              f"lr={lrs}" + ("" if not over["hebbian"] else " <hebb>"),
              flush=True)

with open("runs/c1_pilot.json", "w") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

# сводка годности
print("\n=== сводка C.1 ===")
for name in CONDS:
    rs = [r for r in rows if r["cond"] == name]
    ext = sum(1 for r in rs if r["extinct"] is not None)
    ceil = sum(1 for r in rs if r["hit_ceiling"])
    med = np.median([r["median_life"] for r in rs])
    lrm = np.mean([r["lr_mean"] for r in rs if r["lr_mean"] is not None])
    ok = "OK" if ext == 0 and ceil == 0 and med >= 400 else "ПРОВАЛ ГРАНИЦЫ"
    print(f"{name:>22}: вымерло {ext}/5, потолок {ceil}/5, "
          f"медиана жизни {med:.0f}, lr_сред {lrm:.5f}  -> {ok}")
