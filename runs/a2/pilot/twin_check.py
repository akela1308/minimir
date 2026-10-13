#!/usr/bin/env python3
"""Пилотная проверка подмены twin (граница провала 3 части 1 черновика A2):
распределение входа 8 у twin против собственной энергии агентов, лаг-1
автокорреляция входа у self / twin / shuffled / constant. Seed'ы 101-103,
2000 тиков после 600 прогрева. Не подтверждающие данные."""
import sys, os, json
os.environ.setdefault("OMP_NUM_THREADS", "1")
REPO = "/home/claude/minimir"; sys.path.insert(0, REPO); os.chdir(REPO)
import numpy as np
from sim import Config, Engine

out = {}
for seed in (101, 102, 103):
    res = {}
    for mode in ("self", "twin", "shuffled", "constant"):
        eng = Engine(Config(seed=seed, intero_mode=mode))
        eng.run(600)
        own, sig = [], []
        ids0 = eng.pop.ids(); birth0 = eng.pop.birth_tick[ids0].copy()
        T = 2000
        series = np.full((T, ids0.size), np.nan)
        for t in range(T):
            ids = eng.pop.ids()
            partner, _ = eng._nearest_partner(ids)
            e, _ = eng._interoceptive_signal(ids, partner)
            own.append(eng.pop.E[ids] / eng.cfg.e_max); sig.append(e)
            pos = np.clip(np.searchsorted(ids, ids0), 0, ids.size - 1)
            ok = (ids[pos] == ids0) & (eng.pop.birth_tick[ids0] == birth0)
            series[t, ok] = e[pos[ok]]
            eng.step()
        own = np.concatenate(own); sig = np.concatenate(sig)
        # лаг-1 автокорреляция по агентам, дожившим всё окно
        full = ~np.isnan(series).any(axis=0)
        s = series[:, full]
        if s.shape[1] >= 3:
            x, y = s[:-1], s[1:]
            xc, yc = x - x.mean(0), y - y.mean(0)
            r = (xc * yc).sum(0) / np.sqrt((xc ** 2).sum(0) * (yc ** 2).sum(0) + 1e-12)
            lag1 = float(np.nanmean(r))
        else:
            lag1 = None
        # максимальный разрыв эмпирических функций распределения (как у Колмогорова)
        grid = np.linspace(0, 1, 101)
        F_own = np.searchsorted(np.sort(own), grid) / own.size
        F_sig = np.searchsorted(np.sort(sig), grid) / sig.size
        res[mode] = dict(mean_own=float(own.mean()), mean_sig=float(sig.mean()),
                         sd_own=float(own.std()), sd_sig=float(sig.std()),
                         ks_gap=float(np.abs(F_own - F_sig).max()),
                         lag1_autocorr=lag1, agents_full_window=int(full.sum()),
                         agent_ticks=int(own.size))
    out[seed] = res
    print(seed, json.dumps(res, ensure_ascii=False), flush=True)
json.dump(out, open("/home/claude/pilot/twin_check.json", "w"), ensure_ascii=False, indent=1)
