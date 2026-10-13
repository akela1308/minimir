#!/usr/bin/env python3
"""Пилотная проверка подмены twin, вторая версия (13 октября 2026): лаг-1
автокорреляция входа 8 по коротким окнам (200 тиков) и по всем агентам, прожившим
окно, а не только по долгожителям на 2000 тиков. Пять окон подряд после 600 тиков
прогрева. Seed'ы 101-103. Не подтверждающие данные."""
import sys, os, json
os.environ.setdefault("OMP_NUM_THREADS", "1")
REPO = "/home/claude/minimir"; sys.path.insert(0, REPO); os.chdir(REPO)
import numpy as np
from sim import Config, Engine

W, NWIN, WARM = 200, 5, 600
out = {}
for seed in (101, 102, 103):
    res = {}
    for mode in ("self", "twin", "shuffled", "constant"):
        eng = Engine(Config(seed=seed, intero_mode=mode))
        eng.run(WARM)
        lag1s, counts = [], []
        for _ in range(NWIN):
            ids0 = eng.pop.ids(); birth0 = eng.pop.birth_tick[ids0].copy()
            series = np.full((W, ids0.size), np.nan)
            for t in range(W):
                ids = eng.pop.ids()
                partner, _ = eng._nearest_partner(ids)
                e, _ = eng._interoceptive_signal(ids, partner)
                pos = np.clip(np.searchsorted(ids, ids0), 0, ids.size - 1)
                ok = (ids[pos] == ids0) & (eng.pop.birth_tick[ids0] == birth0)
                series[t, ok] = e[pos[ok]]
                eng.step()
            full = ~np.isnan(series).any(axis=0)
            s = series[:, full]
            if s.shape[1] >= 3:
                x, y = s[:-1], s[1:]
                xc, yc = x - x.mean(0), y - y.mean(0)
                den = np.sqrt((xc ** 2).sum(0) * (yc ** 2).sum(0))
                good = den > 1e-9           # у constant сигнал не меняется, r не определён
                if good.any():
                    r = (xc * yc).sum(0)[good] / den[good]
                    lag1s.append(float(np.mean(r)))
                    counts.append(int(good.sum()))
        res[mode] = dict(lag1_mean=(float(np.mean(lag1s)) if lag1s else None),
                         lag1_windows=lag1s, agents_per_window=counts)
    out[seed] = res
    print(seed, json.dumps({m: (round(v["lag1_mean"], 3) if v["lag1_mean"] is not None else None, v["agents_per_window"]) for m, v in res.items()}), flush=True)
json.dump(out, open("/home/claude/pilot/twin_check2.json", "w"), ensure_ascii=False, indent=1)
