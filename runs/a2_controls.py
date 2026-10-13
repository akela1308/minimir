#!/usr/bin/env python3
"""Протокол A2, часть 1 (ЧЕРНОВИК 13 октября 2026, прогонов не было): два новых
контроля на входах 8-9, константа и «близнец», рядом с self и shuffled.

Основание: ИДЕИ_2026-10-13.md §2.1 и §5.2, REPORT.md §6 пункт 3. shuffled
берёт энергию нового случайного агента каждый тик и потому разрушает не только
знание о себе, но и временную структуру сигнала (белый шум на входе); аномалия
off > shuffled этого и ждёт. twin сохраняет распределение И автокорреляцию,
constant даёт ненулевой вход без информации и без шума.

Процедура та же, что у A5 и суточного прогона: 120 000 тиков, блочное усреднение
(5 блоков по 15 000 после прогрева), track_individual. Метрика пишется при обоих
порогах (within_mi_200, within_mi_1000), см. REPORT.md §4 поправку от 13.10.2026.
Контролем в парных сравнениях остаётся shuffled.

Файл результатов НОВЫЙ, runs/a2/controls.jsonl: старые compare.jsonl и
compare_ext.jsonl не трогаются. Запускать только после заморозки
PREREGISTRATION_A2.md:

  python runs/a2_controls.py --seeds 20 --ticks 120000 --workers 2
  python runs/a2_controls.py --seeds 1 --ticks 20000      # короткая проверка кода
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

from experiments import run_series, wilcoxon_paired, effect_size, summarize  # noqa: E402

CONDS = ["self", "shuffled", "twin", "constant", "off"]
OUT = ROOT / "runs" / "a2" / "controls.jsonl"
PROTOCOL = "A2-controls-120k-blockavg-draft"      # «draft» снимается при заморозке


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
    p.add_argument("--seeds", type=int, default=20, help="seed'ы 1..N, объявляются в предрегистрации")
    p.add_argument("--ticks", type=int, default=120000)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--conds", default=",".join(CONDS))
    p.add_argument("--out", default=str(OUT))
    args = p.parse_args()
    conds = [c for c in args.conds.split(",") if c]
    if "shuffled" not in conds:
        raise SystemExit("контроль shuffled обязателен")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = git_commit()
    print(f"дата {stamp}, коммит {commit}, протокол {PROTOCOL}")
    print(f"считаю seed'ы 1..{args.seeds} × {conds} × {args.ticks} тиков -> {args.out}")

    jobs = []
    for s in range(1, args.seeds + 1):
        for c in conds:
            jobs.append(dict(label=c, key=f"{c}|seed{s}", ticks=args.ticks,
                             block_avg=True, track_individual=True,
                             cfg=dict(seed=s, intero_mode=c, interoception=(c != "off"),
                                      track_individual=True)))
    t0 = time.time()
    rows = run_series(jobs, args.out, args.workers or None)
    elapsed = time.time() - t0

    stamped = []
    for r in read_jsonl(args.out):
        if "run_date" not in r:
            r.update(run_date=stamp, commit=commit, protocol=PROTOCOL, ticks=args.ticks)
        stamped.append(r)
    with open(args.out, "w") as f:
        for r in stamped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # сводка в консоль: обе метрики, парно против shuffled, и аномалия off
    good = {c: {r["seed"]: r for r in stamped
                if r.get("label") == c and not r.get("error") and r.get("extinct") is None
                and not r.get("hit_ceiling") and (r.get("occupied_deciles") or 0) >= 4}
            for c in conds}
    for metric in ("within_mi_200", "within_mi_1000", "mi"):
        print(f"\nметрика {metric}")
        for c in conds:
            st = summarize(list(good[c].values()), key=metric)
            if st.get("n"):
                print(f"  {c:>9}: среднее {st['mean']:.4f}, sd {st['sd']:.4f}, n={st['n']}")
        base = good["shuffled"]
        for c in conds:
            if c == "shuffled":
                continue
            pairs = [(good[c][s].get(metric), base[s].get(metric))
                     for s in good[c] if s in base
                     and good[c][s].get(metric) is not None and base[s].get(metric) is not None]
            if not pairs:
                continue
            a, b = [x for x, _ in pairs], [y for _, y in pairs]
            w = wilcoxon_paired(a, b)
            d = [x - y for x, y in pairs]
            sd_d = (sum((x - sum(d) / len(d)) ** 2 for x in d) / max(len(d) - 1, 1)) ** 0.5
            print(f"  {c:>9} vs shuffled: Δ={sum(d)/len(d):+.4f}, 2σ парных разниц={2*sd_d:.4f}, "
                  f"p={w.get('p')}, Клифф={effect_size(a, b)}, n={w['n']}")
    print(f"\nготово за {elapsed:.0f}s; строк в файле: {len(stamped)}")


if __name__ == "__main__":
    main()
