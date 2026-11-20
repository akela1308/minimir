#!/usr/bin/env python3
"""Прогон протокола N4 (20 ноября 2026).

На каждом семени один общий прогрев до тика смены и по одной развилке на
условие (sim/protocol_n4.py). Строки копятся в jsonl, по строке на пару
(семя, условие).

Подтверждающий прогон пишет в runs/n4/protocol_n4.jsonl и запускается только
после заморозки: без файла PREREGISTRATION_N4.md раннер отказывается писать
туда. Пилоты гоняются с --pilot: свои семена (301 и дальше), своя папка, и ни
одно число из пилота в подтверждающие данные не переносится.

  python runs/n4_run.py --pilot --seeds 301-312 --horizon 12000
  python runs/n4_run.py --confirm                  # только после заморозки

С --confirm семена берутся по порядку с SEED_FIRST, пока не наберётся N_CONFIRM
годных (правило годности в sim/protocol_n4.py). Прогон возобновляемый.
"""
import argparse
import json
import multiprocessing as mp
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.protocol_n4 import (PROTOCOL, SHIFT, HORIZON, SEED_FIRST, N_CONFIRM,  # noqa: E402
                              conditions, measure_seed)

OUT = ROOT / "runs" / "n4" / "protocol_n4.jsonl"
PILOT_DIR = ROOT / "runs" / "n4" / "pilot"
FROZEN = ROOT / "PREREGISTRATION_N4.md"


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def parse_seeds(text):
    seeds = []
    for part in text.split(","):
        if "-" in part:
            a, b = part.split("-")
            seeds.extend(range(int(a), int(b) + 1))
        else:
            seeds.append(int(part))
    return seeds


def done_keys(path):
    keys = set()
    if Path(path).exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        keys.add(json.loads(line)["key"])
                    except (json.JSONDecodeError, KeyError):
                        pass
    return keys


def _job(args):
    seed, conds, horizon, extra = args
    t0 = time.time()
    rows = measure_seed(seed, conds=conds, ticks=SHIFT + horizon, **extra)
    for r in rows:
        r.update(extra_overrides=extra)
    return seed, rows, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="", help="например 301-312 или 301,302,305")
    ap.add_argument("--confirm", action="store_true",
                    help="подтверждающий прогон: семена по порядку до N_CONFIRM годных")
    ap.add_argument("--horizon", type=int, default=HORIZON, help="тиков после смены")
    ap.add_argument("--conds", default="", help="через запятую; по умолчанию все")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count()))
    ap.add_argument("--set", action="append", default=[],
                    help="правка конфигурации прогрева, только для пилота: имя=значение")
    a = ap.parse_args()

    all_conds = list(conditions())
    conds = [c for c in a.conds.split(",") if c] or all_conds
    extra = {}
    for kv in a.set:
        k, v = kv.split("=")
        extra[k] = float(v) if "." in v or "e" in v else int(v)

    if a.pilot:
        out = Path(a.out) if a.out else PILOT_DIR / "pilot.jsonl"
    else:
        if not FROZEN.exists():
            sys.exit("PREREGISTRATION_N4.md не найден: протокол не заморожен, "
                     "подтверждающий прогон не запускается. Для пилота: --pilot.")
        if "draft" in PROTOCOL:
            sys.exit(f"PROTOCOL = {PROTOCOL}: слово draft не снято, прогон не запускается.")
        if extra or a.horizon != HORIZON or a.conds:
            sys.exit("в подтверждающем прогоне параметры не правятся с командной строки")
        out = Path(a.out) if a.out else OUT
    out.parent.mkdir(parents=True, exist_ok=True)

    if a.confirm:
        if a.pilot or a.seeds:
            sys.exit("--confirm не сочетается с --pilot и --seeds: семена задаёт протокол")
        for _ in range(6):                        # с запасом: каждый круг добирает недостающее
            seeds = next_seeds(done_keys(out), all_conds)
            if not seeds:
                print(f"годных семян {N_CONFIRM} из {N_CONFIRM}: подтверждающий прогон посчитан")
                return
            run_batch(seeds, all_conds, HORIZON, {}, out, a.workers, False)
        sys.exit("подтверждающий прогон не добран за шесть кругов: смотреть журнал")
    if not a.seeds:
        sys.exit("нужен --seeds (или --confirm после заморозки)")
    if not a.pilot and min(parse_seeds(a.seeds)) < SEED_FIRST:
        sys.exit(f"подтверждающие семена начинаются с {SEED_FIRST}; меньшие заняты пилотами")
    run_batch(parse_seeds(a.seeds), conds, a.horizon, extra, out, a.workers, a.pilot)


def seed_status(have, conds, seed_first=SEED_FIRST):
    """По ключам файла: семя -> valid (все условия), excluded, partial."""
    status = {}
    for key in have:
        name, tail = key.split("|seed")
        s = int(tail)
        if s < seed_first:
            continue
        if name == "EXCLUDED":
            status[s] = "excluded"
        elif status.get(s) != "excluded":
            status[s] = "partial"
    for s, st in status.items():
        if st == "partial" and all(f"{c}|seed{s}" in have for c in conds):
            status[s] = "valid"
    return status


def next_seeds(have, conds, seed_first=SEED_FIRST, n_confirm=N_CONFIRM):
    """Какие семена считать дальше: идём по порядку с seed_first, годные считаем,
    негодные пропускаем, остальные (не начатые и недосчитанные) берём в работу,
    пока годных вместе с взятыми не станет n_confirm. Пустой список значит, что
    первые n_confirm годных семян посчитаны без пропусков."""
    status = seed_status(have, conds, seed_first)
    todo, valid, s = [], 0, seed_first
    while valid + len(todo) < n_confirm:
        st = status.get(s)
        if st == "valid":
            valid += 1
        elif st != "excluded":
            todo.append(s)
        s += 1
    return todo


def run_batch(seeds, conds, horizon, extra, out, workers, pilot):
    have = done_keys(out)
    jobs = []
    for s in seeds:
        todo = [c for c in conds if f"{c}|seed{s}" not in have]
        if f"EXCLUDED|seed{s}" in have:
            continue                              # семя уже признано негодным
        if todo:
            jobs.append((s, todo, horizon, extra))
    print(f"{PROTOCOL}: семян к счёту {len(jobs)} из {len(seeds)}, условий {len(conds)}, "
          f"горизонт {horizon}, пишу в {out}", flush=True)
    if not jobs:
        return
    commit, stamp = git_commit(), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.time()
    with mp.Pool(workers) as pool, open(out, "a") as f:
        for n, (seed, rows, dt) in enumerate(pool.imap_unordered(_job, jobs), 1):
            for r in rows:
                r.update(run_date=stamp, commit=commit, pilot=bool(pilot), horizon=horizon)
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if rows[0]["label"] == "EXCLUDED":
                print(f"  семя {seed}: негодно ({rows[0]['reason']}) [{n}/{len(jobs)}]", flush=True)
                continue
            resc = sum(r["rescued"] for r in rows)
            print(f"  семя {seed}: {dt:.0f} с, спасено {resc} из {len(rows)} "
                  f"[{n}/{len(jobs)}, прошло {time.time() - t0:.0f} с]", flush=True)


if __name__ == "__main__":
    main()
