#!/usr/bin/env python3
"""Пилот B2, вторая порция: постепенная смена правила (switch_ramp_ticks 60 и 150)
при яде -0.5, условия life и life_frozen, seed'ы 101-103, 20k тиков. Не
подтверждающие данные; для решения §0.1 черновика B2."""
import sys, os, time
os.environ.setdefault("OMP_NUM_THREADS", "1")
REPO = "/home/claude/minimir"; sys.path.insert(0, REPO); os.chdir(REPO)
from experiments import run_series
from sim.protocol_b import SWITCH
jobs = []
for s in (101, 102, 103):
    for ramp in (60, 150):
        for c in ("life", "life_frozen"):
            ov = dict(toxic_factor=-0.5, marker_gene=True, marker_init=0.1, switch_ramp_ticks=ramp)
            jobs.append(dict(label=c, key=f"{c}/tox-0.5/ramp{ramp}|seed{s}", ticks=20000,
                             protocol="B", cfg=dict(seed=s), overrides=ov))
t0 = time.time()
run_series(jobs, "/home/claude/pilot/pilot_b2_ramp.jsonl", workers=2)
print(f"готово за {time.time()-t0:.0f}s", flush=True)
