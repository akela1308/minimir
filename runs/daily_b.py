#!/usr/bin/env python3
"""Суточный автономный прогон протокола B: «Когда выгодно учиться».

Шесть условий на ОДНИХ И ТЕХ ЖЕ seed'ах (см. sim/protocol_b.py), 100 000
тиков каждое, единый предок на seed. Копится в runs/daily/protocol_b.jsonl,
по строке на прогон, с датой, хешем коммита и версией протокола.

Объявленные чтения: 10, 20 и 40 seed'ов (PREREGISTRATION_B.md §7).
Сверх цели новых прогонов не запускается.

Запуск:
  python runs/daily_b.py                      # следующие 2 seed'а
  python runs/daily_b.py --seeds 1 --ticks 12000   # короткая проверка
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments import run_series          # noqa: E402
from sim.protocol_b import CONDS            # noqa: E402

OUT = ROOT / "runs" / "daily" / "protocol_b.jsonl"
PROTOCOL = "B1-100k-v1"


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def read_jsonl(path):
    rows = []
    if not Path(path).exists():
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def completed_seeds(rows):
    have = {}
    for r in rows:
        if r.get("error"):
            continue
        have.setdefault(r.get("seed"), set()).add(r.get("label"))
    return {s for s, cs in have.items() if set(CONDS) <= cs and s is not None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=2, help="сколько новых seed'ов за прогон")
    p.add_argument("--ticks", type=int, default=100000)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--target", type=int, default=40)
    args = p.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(OUT)
    done = completed_seeds(rows)
    started = {r.get("seed") for r in rows if r.get("seed") is not None}
    unfinished = sorted(started - done)
    if len(done) >= args.target:
        print(f"цель достигнута: {len(done)} seed'ов >= {args.target}. Новых прогонов не запускаю.")
        json.dump(dict(added=[], reason="target_reached", total=len(done)),
                  open(ROOT / "runs" / "daily" / "last_run_b.json", "w"),
                  ensure_ascii=False, indent=1)
        return

    next_seed = (max(done | started) + 1) if (done or started) else 1
    todo = unfinished[: args.seeds]
    while len(todo) < args.seeds and len(done) + len(todo) < args.target:
        todo.append(next_seed)
        next_seed += 1

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = git_commit()
    print(f"дата {stamp}, коммит {commit}, протокол {PROTOCOL}")
    print(f"уже готово seed'ов: {len(done)} (цель {args.target})")
    print(f"считаю seed'ы: {todo} × {CONDS} × {args.ticks} тиков")

    jobs = [dict(protocol="B", label=c, key=f"{c}|seed{s}", ticks=args.ticks,
                 cfg=dict(seed=s))
            for s in todo for c in CONDS]
    t0 = time.time()
    res = run_series(jobs, OUT, args.workers or None)
    elapsed = time.time() - t0

    stamped = []
    for r in read_jsonl(OUT):
        if "run_date" not in r:
            r["run_date"] = stamp
            r["commit"] = commit
            r["protocol"] = PROTOCOL
            r["ticks"] = args.ticks
        stamped.append(r)
    with open(OUT, "w") as f:
        for r in stamped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    now_done = completed_seeds(stamped)
    added = sorted(now_done - done)
    print(f"\nготово за {elapsed:.0f}s. Новых завершённых seed'ов: {added}")
    print(f"всего seed'ов: {len(now_done)} / {args.target}")
    json.dump(dict(date=stamp, commit=commit, protocol=PROTOCOL, ticks=args.ticks,
                   added=added, total=len(now_done), target=args.target,
                   elapsed_s=round(elapsed, 1),
                   errors=sum(1 for r in res if r.get("error"))),
              open(ROOT / "runs" / "daily" / "last_run_b.json", "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
