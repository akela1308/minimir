"""Блок B: валидация движка чужим предсказанием (Requejo & Camacho, 1312.3450).

Аналитическое предсказание: при изобилии ресурса популяция однородно
предательская, при падении ресурса ниже порога выживают безусловные
кооператоры — у агентов БЕЗ памяти и БЕЗ узнавания (recognition=False).
Ищем РЕЗКИЙ переход доли кооперации по изобилию, а не плавный тренд.

Свип по regrowth (8 значений от дефицита к изобилию) × 5 seed'ов,
social=True, recognition=False, социальный слой включается на выжившей
популяции (social_from_tick=WARM).

Дополнительно закрываем confound: доля кооперации по децилям энергии по
популяции обогащена «отнимающими» (take сам поднимает энергию). Считаем
корреляцию ВНУТРИ агента во времени и сравниваем с популяционной.

Инкрементальный JSONL + возобновляемость + пул воркеров.
"""
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np

from sim import Config, Engine, metrics

OUT = "runs/b_sweep.jsonl"
REGROWTHS = [0.0018, 0.0022, 0.0028, 0.0035, 0.0045, 0.0060, 0.0080, 0.0110]
SEEDS = [1, 2, 3, 4, 5]
WARM = 40000
SOCIAL = 40000


def one(job):
    try:
        r, seed = job["regrowth"], job["seed"]
        cfg = Config(seed=seed, regrowth=r, social=True, recognition=False,
                     social_from_tick=WARM, action_noise=0.02,
                     track_individual=True)
        eng = Engine(cfg)
        budget = eng.world.energy_budget()
        peak = 0
        def rec(e):
            nonlocal peak
            if e.pop.count > peak:
                peak = e.pop.count
        eng.run(WARM, on_log=rec)
        eng.reset_metrics()
        eng.reset_individual()
        eng.run(SOCIAL, on_log=rec)
        st = eng.stats()
        coop_total = eng.coop_events + eng.defect_events
        pop_hvc = metrics.hunger_vs_cooperation(eng)
        wa_hvc = metrics.within_agent_hunger_vs_cooperation(eng)
        ap = metrics.action_profile(eng)
        return dict(key=job["key"], regrowth=r, seed=seed,
                    sustainable_pop=budget["sustainable_population"],
                    coop_events=eng.coop_events, defect_events=eng.defect_events,
                    social_events=int(coop_total),
                    coop_rate=(eng.coop_events / coop_total) if coop_total else None,
                    give_frac=ap["give"], take_frac=ap["take"],
                    pop=st["pop"], peak_pop=peak,
                    hit_ceiling=bool(peak >= 0.95 * cfg.max_pop),
                    extinct=eng.extinct_at,
                    pop_corr_energy=pop_hvc["correlation_with_energy"],
                    within_corr_energy=wa_hvc["mean_correlation"],
                    within_n_agents=wa_hvc["n_agents"],
                    mean_E=st["mean_E"])
    except Exception as e:
        return dict(key=job.get("key"), error=f"{type(e).__name__}: {e}")


def main():
    Path("runs").mkdir(exist_ok=True)
    done = set()
    if Path(OUT).exists():
        with open(OUT) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["key"])
                except Exception:
                    pass
    jobs = []
    for r in REGROWTHS:
        for s in SEEDS:
            key = f"r{r}|seed{s}"
            if key not in done:
                jobs.append(dict(key=key, regrowth=r, seed=s))
    print(f"[B] {len(done)} готово, {len(jobs)} осталось", file=sys.stderr)
    if not jobs:
        return
    # 2 воркера = 2 физических ядра машины: без oversubscription BLAS/потоков
    workers = min(2, len(jobs))
    t0 = time.time(); n = 0
    with mp.Pool(workers) as pool:
        for res in pool.imap_unordered(one, jobs):
            with open(OUT, "a") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            n += 1
            el = time.time() - t0
            rate = n / el if el else 0
            rem = (len(jobs) - n) / rate if rate else float("inf")
            print(f"[B {n}/{len(jobs)}] {res.get('key')} "
                  f"coop={res.get('coop_rate')} — {el:.0f}s, ~{rem:.0f}s осталось",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
