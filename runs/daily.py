#!/usr/bin/env python3
"""Суточный автономный прогон: добавляет новые seed'ы к главному сравнению A.5.

Процедура ровно та же, что в блоке A.5 ночной сессии (см. REPORT.md §2, блок A):
четыре условия — self / shuffled / neighbour / off — на ОДНИХ И ТЕХ ЖЕ seed'ах,
120 000 тиков, блочное усреднение (5 блоков × 15 000 после прогрева),
главная метрика — внутриагентная (track_individual).

Длина 120k выбрана не «покороче», а чтобы новые seed'ы были СОПОСТАВИМЫ с уже
имеющимися двенадцатью. Смешивать в одном пуле прогоны разной длины нельзя:
длина влияет и на стационарность, и на число измерительных блоков.

Что копится:
  runs/daily/compare_ext.jsonl — новые seed'ы (13, 14, ...), по строке на прогон.
  Исходный runs/compare.jsonl НЕ трогается: это замороженный датасет отчёта.

Каждая строка дополнительно несёт происхождение: дату UTC, хеш коммита кода,
длину прогона и версию протокола. Это то, что делает журнал проверяемым:
любую строку можно воспроизвести, зная (commit, seed, условие, ticks).

Запуск:
  python runs/daily.py                 # следующие 4 seed'а
  python runs/daily.py --seeds 2 --ticks 20000   # короткая проверка
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments import run_series  # noqa: E402

CONDS = ["self", "shuffled", "neighbour", "off"]
FROZEN = ROOT / "runs" / "compare.jsonl"          # 12 seed'ов ночной сессии
EXT = ROOT / "runs" / "daily" / "compare_ext.jsonl"  # то, что копится дальше
PROTOCOL = "A5-120k-blockavg-v1"


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
    """seed'ы, у которых посчитаны все четыре условия без ошибок."""
    have = {}
    for r in rows:
        if r.get("error"):
            continue
        have.setdefault(r.get("seed"), set()).add(r.get("label"))
    return {s for s, cs in have.items() if set(CONDS) <= cs and s is not None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=4, help="сколько новых seed'ов за прогон")
    p.add_argument("--ticks", type=int, default=120000)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--target", type=int, default=40,
                   help="объявленная цель по числу seed'ов; сверх неё не считаем")
    args = p.parse_args()

    EXT.parent.mkdir(parents=True, exist_ok=True)

    frozen = read_jsonl(FROZEN)
    ext = read_jsonl(EXT)
    done = completed_seeds(frozen) | completed_seeds(ext)
    # плюс seed'ы, начатые но не дописанные в ext — их доведём в первую очередь
    started_ext = {r.get("seed") for r in ext if r.get("seed") is not None}
    unfinished = sorted(started_ext - done)

    if len(done) >= args.target:
        print(f"цель достигнута: {len(done)} seed'ов >= {args.target}. "
              f"Новых прогонов не запускаю.")
        json.dump(dict(added=[], reason="target_reached", total=len(done)),
                  open(ROOT / "runs" / "daily" / "last_run.json", "w"),
                  ensure_ascii=False, indent=1)
        return

    next_seed = (max(done | started_ext) + 1) if (done or started_ext) else 1
    budget = args.seeds
    todo = unfinished[:budget]
    while len(todo) < budget and len(done) + len(todo) < args.target:
        todo.append(next_seed)
        next_seed += 1

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = git_commit()
    print(f"дата {stamp}, коммит {commit}, протокол {PROTOCOL}")
    print(f"уже готово seed'ов: {len(done)} (цель {args.target})")
    print(f"считаю seed'ы: {todo} × {CONDS} × {args.ticks} тиков")

    jobs = []
    for s in todo:
        for c in CONDS:
            jobs.append(dict(
                label=c, key=f"{c}|seed{s}", ticks=args.ticks,
                block_avg=True, track_individual=True,
                cfg=dict(seed=s, intero_mode=c, interoception=(c != "off"),
                         track_individual=True)))

    t0 = time.time()
    # run_series сам дописывает JSONL после каждого прогона и умеет
    # возобновляться: упавший прогон не теряет уже посчитанное.
    rows = run_series(jobs, EXT, args.workers or None)
    elapsed = time.time() - t0

    # дописываем происхождение тем строкам, у которых его ещё нет
    stamped = []
    for r in read_jsonl(EXT):
        if "run_date" not in r:
            r["run_date"] = stamp
            r["commit"] = commit
            r["protocol"] = PROTOCOL
            r["ticks"] = args.ticks
        stamped.append(r)
    with open(EXT, "w") as f:
        for r in stamped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    now_done = completed_seeds(frozen) | completed_seeds(stamped)
    added = sorted(now_done - done)
    print(f"\nготово за {elapsed:.0f}s. Новых завершённых seed'ов: {added}")
    print(f"всего seed'ов: {len(now_done)} / {args.target}")

    json.dump(dict(date=stamp, commit=commit, protocol=PROTOCOL,
                   ticks=args.ticks, added=added, total=len(now_done),
                   target=args.target, elapsed_s=round(elapsed, 1),
                   errors=sum(1 for r in rows if r.get("error"))),
              open(ROOT / "runs" / "daily" / "last_run.json", "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
