#!/usr/bin/env python3
"""Автономный прогон протокола B2 (ЧЕРНОВИК 13 октября 2026, прогонов не было).

Те же шесть условий на одних seed'ах (sim/protocol_b2.py, WORLD_B2: нейтральный
маркерный ген, запись погибших, параметры мира по решениям §0 черновика),
100 000 тиков, единый предок на seed. Копится в runs/b2/protocol_b2.jsonl, НОВЫЙ
файл: runs/daily/protocol_b.jsonl протокола B1 не трогается.

Объявленные чтения: 10, 20 и 40 seed'ов (PREREGISTRATION_B2 §9). Сверх цели
новых прогонов не запускается. Запускать только после заморозки: без файла
PREREGISTRATION_B2.md раннер отказывается писать в файл результатов (пилоты
гоняются с --seed_list и --out в другое место).

  python runs/daily_b2.py                              # следующие 2 seed'а
  python runs/daily_b2.py --seed_list 101 --ticks 20000 --out /tmp/b2_check.jsonl
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

from experiments import run_series             # noqa: E402
from sim.protocol_b2 import CONDS, PROTOCOL    # noqa: E402

OUT = ROOT / "runs" / "b2" / "protocol_b2.jsonl"
FROZEN = ROOT / "PREREGISTRATION_B2.md"


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
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
    p.add_argument("--out", default=str(OUT))
    p.add_argument("--seed_list", default="",
                   help="явный список seed'ов (пилоты и проверки кода вне объявленных 1..40); "
                        "вместе с --out вне runs/b2/protocol_b2.jsonl")
    args = p.parse_args()
    out = Path(args.out)

    if out.resolve() == OUT.resolve() and not FROZEN.exists():
        raise SystemExit("PREREGISTRATION_B2.md не найден: есть только черновик. Прогоны по протоколу "
                         "до заморозки не считаются; для пилота укажи --seed_list и другой --out.")
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(out)
    done = completed_seeds(rows)
    if args.seed_list:
        todo = [int(x) for x in args.seed_list.split(",") if x.strip()]
    else:
        started = {r.get("seed") for r in rows if r.get("seed") is not None}
        unfinished = sorted(started - done)
        if len(done) >= args.target:
            print(f"цель достигнута: {len(done)} seed'ов >= {args.target}. Новых прогонов не запускаю.")
            json.dump(dict(added=[], reason="target_reached", total=len(done)),
                      open(out.parent / "last_run_b2.json", "w"), ensure_ascii=False, indent=1)
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
    print(f"считаю seed'ы: {todo} × {CONDS} × {args.ticks} тиков -> {out}")

    jobs = [dict(protocol="B2", label=c, key=f"{c}|seed{s}", ticks=args.ticks, cfg=dict(seed=s))
            for s in todo for c in CONDS]
    t0 = time.time()
    res = run_series(jobs, out, args.workers or None)
    elapsed = time.time() - t0

    stamped = []
    for r in read_jsonl(out):
        if "run_date" not in r:
            r.update(run_date=stamp, commit=commit, protocol=PROTOCOL, ticks=args.ticks)
        stamped.append(r)
    with open(out, "w") as f:
        for r in stamped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    now_done = completed_seeds(stamped)
    added = sorted(now_done - done)
    print(f"\nготово за {elapsed:.0f}s. Новых завершённых seed'ов: {added}")
    print(f"всего seed'ов: {len(now_done)} / {args.target}")
    json.dump(dict(date=stamp, commit=commit, protocol=PROTOCOL, ticks=args.ticks, added=added,
                   total=len(now_done), target=args.target, elapsed_s=round(elapsed, 1),
                   errors=sum(1 for r in res if r.get("error"))),
              open(out.parent / "last_run_b2.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
