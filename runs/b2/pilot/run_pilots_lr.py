#!/usr/bin/env python3
"""Пилот B2, третья порция: стартовая скорость обучения как рычаг выживания первой
смены (REPORT_B.md §10 п. 2). Варианты: taste_lr_init 0.3; 0.5; 0.1 с посевом
распределением (init_sigma 1.0). Яд -0.5, смена мгновенная. Условия life и
life_frozen, seed'ы 101-103, 20k тиков. Пилот, не чтение."""
import sys, os, time
os.environ.setdefault("OMP_NUM_THREADS", "1")
REPO = "/home/claude/minimir"; sys.path.insert(0, REPO); os.chdir(REPO)
from experiments import run_series
jobs = []
variants = {"lr0.3": dict(taste_lr_init=0.3), "lr0.5": dict(taste_lr_init=0.5),
            "lr0.1sig1.0": dict(taste_lr_init=0.1, taste_lr_init_sigma=1.0)}
for s in (101, 102, 103):
    for name, extra in variants.items():
        for c in ("life", "life_frozen"):
            ov = dict(toxic_factor=-0.5, marker_gene=True, marker_init=0.1, **extra)
            jobs.append(dict(label=c, key=f"{c}/tox-0.5/{name}|seed{s}", ticks=20000,
                             protocol="B", cfg=dict(seed=s), overrides=ov))
t0 = time.time()
run_series(jobs, "/home/claude/pilot/pilot_b2_lr.jsonl", workers=2)
print(f"готово за {time.time()-t0:.0f}s", flush=True)
