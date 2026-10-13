#!/usr/bin/env python3
"""Пилоты 13-14 октября 2026 (НЕ подтверждающие данные): seed'ы 101-103, вне
объявленных 1-20/1-40. Считаются в облачном контейнере, результаты потом
копируются в репозиторий с пометкой pilot. Цель: проверить предпосылки до
заморозки предрегистраций A2 и B2 (ИДЕИ_2026-10-13.md §2.1, §2.2, §2.5)."""
import sys, json, time, os
os.environ.setdefault("OMP_NUM_THREADS", "1")
REPO = "/home/claude/minimir"
sys.path.insert(0, REPO)
os.chdir(REPO)                      # кэш предков runs/ancestors (gitignored)
from experiments import run_series
from sim.protocol_b import WORLD_B, SWITCH, PLASTIC

OUT = "/home/claude/pilot"
SEEDS = [101, 102, 103]
TICKS_A = 40000
TICKS_B = 20000
which = sys.argv[1] if len(sys.argv) > 1 else "all"
t0 = time.time()

def log(msg):
    print(f"[{time.time()-t0:7.0f}s] {msg}", flush=True)

if which in ("controls", "all"):
    jobs = []
    for s in SEEDS:
        for c in ("self", "shuffled", "twin", "constant", "off"):
            jobs.append(dict(label=c, key=f"{c}|seed{s}", ticks=TICKS_A, block_avg=True,
                             track_individual=True,
                             cfg=dict(seed=s, intero_mode=c, interoception=(c != "off"),
                                      track_individual=True)))
    log(f"controls: {len(jobs)} прогонов × {TICKS_A}")
    run_series(jobs, f"{OUT}/pilot_controls.jsonl", workers=2)
    log("controls готово")

if which in ("shock", "all"):
    SHOCK = dict(shock_every=500, shock_frac=0.2, shock_amount=20.0, shock_min_energy=30.0,
                 shock_slow_ticks=50, shock_window=50, shock_survival_ticks=200)
    jobs = []
    for s in SEEDS:
        for c in ("self", "shuffled", "twin"):
            for m in ("abrupt", "slow", "sham"):
                jobs.append(dict(label=f"{c}/{m}", key=f"{c}/{m}|seed{s}", ticks=TICKS_A,
                                 block_avg=True, track_individual=False,
                                 cfg=dict(seed=s, intero_mode=c, shock_mode=m, **SHOCK)))
    log(f"shock: {len(jobs)} прогонов × {TICKS_A}")
    run_series(jobs, f"{OUT}/pilot_shock_v2.jsonl", workers=2)
    log("shock готово")

if which in ("b2", "all"):
    jobs = []
    for s in SEEDS:
        for tox in (-0.5, -0.25):
            for c in ("life", "life_frozen", "never_frozen", "never"):
                ov = dict(toxic_factor=tox, marker_gene=True, marker_init=0.1)
                # label = условие (так ждёт measure_b), вариант яда в ключе и в overrides
                jobs.append(dict(label=c, key=f"{c}/tox{tox}|seed{s}", ticks=TICKS_B,
                                 protocol="B", cfg=dict(seed=s), overrides=ov))
    log(f"b2: {len(jobs)} прогонов × {TICKS_B}")
    run_series(jobs, f"{OUT}/pilot_b2.jsonl", workers=2)
    log("b2 готово")
log("всё готово")
