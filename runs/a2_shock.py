#!/usr/bin/env python3
"""Протокол A2, часть 2 (ЧЕРНОВИК 13 октября 2026, прогонов не было): шок-проба.

Основание: ИДЕИ_2026-10-13.md §2.2. В измерительном окне раз в shock_every тиков
у случайной доли агентов отнимается энергия напрямую, минуя еду; такая же группа
неударенных того же тика служит парным контролем. Метрика событийная: доля
добывающих действий (forward + eat) в следующие shock_window тиков у ударенных
минус у контроля (forage_response) и разница выживаемости через
shock_survival_ticks (survival_response). Моменты и выбор агентов идут из
отдельного генератора, поэтому прогрев бит в бит совпадает с прогоном без шока.

Условия: эволюция под self / shuffled / twin × режим удара abrupt / slow / sham.
sham обязан дать нулевую реакцию (проверка процедуры). У shuffled реакция ноль
по построению (агент не видит своей энергии), поэтому разница
self − shuffled это и есть мера использования сигнала о себе, независимая от
стационарности MI (REPORT.md A.4).

Файл результатов НОВЫЙ, runs/a2/shock.jsonl. Запускать только после заморозки
PREREGISTRATION_A2.md:

  python runs/a2_shock.py --seeds 20 --ticks 120000 --workers 2
  python runs/a2_shock.py --seeds 1 --ticks 20000 --modes abrupt,sham --conds self,shuffled
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

from experiments import run_series, wilcoxon_paired  # noqa: E402

OUT = ROOT / "runs" / "a2" / "shock.jsonl"
PROTOCOL = "A2-shock-120k-draft"
SHOCK = dict(shock_every=500, shock_frac=0.2, shock_amount=20.0, shock_min_energy=30.0,
             shock_slow_ticks=50, shock_window=50, shock_survival_ticks=200)


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def read_jsonl(path):
    rows = []
    if Path(path).exists():
        for line in open(path):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--ticks", type=int, default=120000)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--conds", default="self,shuffled,twin")
    p.add_argument("--modes", default="abrupt,slow,sham")
    p.add_argument("--out", default=str(OUT))
    args = p.parse_args()
    conds = [c for c in args.conds.split(",") if c]
    modes = [m for m in args.modes.split(",") if m]

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = git_commit()
    print(f"дата {stamp}, коммит {commit}, протокол {PROTOCOL}")
    print(f"считаю seed'ы 1..{args.seeds} × {conds} × {modes} × {args.ticks} тиков -> {args.out}")

    jobs = []
    for s in range(1, args.seeds + 1):
        for c in conds:
            for m in modes:
                jobs.append(dict(label=f"{c}/{m}", key=f"{c}/{m}|seed{s}", ticks=args.ticks,
                                 block_avg=True, track_individual=False,
                                 cfg=dict(seed=s, intero_mode=c, interoception=(c != "off"),
                                          shock_mode=m, **SHOCK)))
    t0 = time.time()
    rows = run_series(jobs, args.out, args.workers or None)
    elapsed = time.time() - t0

    stamped = []
    for r in read_jsonl(args.out):
        if "run_date" not in r:
            r.update(run_date=stamp, commit=commit, protocol=PROTOCOL, ticks=args.ticks,
                     shock_params=SHOCK)
        stamped.append(r)
    with open(args.out, "w") as f:
        for r in stamped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # сводка: реакция по условиям и парно self против shuffled в каждом режиме
    good = [r for r in stamped if not r.get("error") and r.get("extinct") is None
            and not r.get("hit_ceiling") and r.get("shock")]
    for m in modes:
        print(f"\nрежим удара {m}")
        by = {}
        for r in good:
            c, mm = r["label"].split("/")
            if mm == m:
                by.setdefault(c, {})[r["seed"]] = r["shock"]
        for c in conds:
            vals = [v.get("forage_response") for v in by.get(c, {}).values()
                    if v.get("forage_response") is not None]
            surv = [v.get("survival_response") for v in by.get(c, {}).values()
                    if v.get("survival_response") is not None]
            if vals:
                print(f"  {c:>9}: реакция (доля добычи) {sum(vals)/len(vals):+.4f}, "
                      f"выживание {sum(surv)/len(surv) if surv else float('nan'):+.4f}, n={len(vals)}")
        if "self" in by and "shuffled" in by:
            common = sorted(set(by["self"]) & set(by["shuffled"]))
            a = [by["self"][s].get("forage_response") for s in common]
            b = [by["shuffled"][s].get("forage_response") for s in common]
            ok = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
            if ok:
                w = wilcoxon_paired([x for x, _ in ok], [y for _, y in ok])
                print(f"  self vs shuffled: p={w.get('p')}, n={w['n']}")
    print(f"\nготово за {elapsed:.0f}s; строк в файле: {len(stamped)}")


if __name__ == "__main__":
    main()
