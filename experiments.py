#!/usr/bin/env python3
"""Экспериментальный раннер: калибровка, уровень шума, сравнение условий.

  python experiments.py calibrate                    # кривая чувствительности метрики
  python experiments.py noise --seeds 10             # разброс одного условия
  python experiments.py compare --seeds 20           # self vs shuffled vs neighbour vs off

Устойчивый к падениям раннер (блок 0.1):
  * результаты пишутся ИНКРЕМЕНТАЛЬНО в JSONL после каждого прогона;
  * при повторном запуске уже посчитанные (условие, seed) пропускаются —
    возобновляемость по файлу результатов;
  * прогресс печатается в stderr с оценкой оставшегося времени;
  * --workers, по умолчанию cpu_count() - 1;
  * аварийный прогон не роняет серию: исключение ловится и пишется как
    {"error": ...}, серия продолжается.

Главную метрику считаем на СТАЦИОНАРНОМ участке (по умолчанию последняя
четверть тиков), с блочным усреднением по блокам 15 000 тиков там, где это
запрошено (preregistration §4: мгновенное MI следует за фазой колебания
численности, а не за эволюцией).
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from sim import Config, Engine, metrics

BLOCK_TICKS = 15000   # размер измерительного блока (preregistration §4)


# --------------------------------------------------------------------- прогон
def _pop_recorder():
    """Замыкание: коллбэк логирования, следящий за пиком численности.

    Пик нужен для критерия невалидности прогона: если популяция достигает
    95% от max_pop, плотность регулируется предохранителем, а не едой.
    """
    state = {"peak": 0}

    def rec(engine):
        p = engine.pop.count
        if p > state["peak"]:
            state["peak"] = p
    return state, rec


def measure(job):
    """Один прогон -> словарь чисел. Всё, что нужно воркеру, лежит в job.

    Исключение внутри прогона не пробрасывается наружу, а возвращается как
    поле "error", чтобы pool не падал и серия продолжалась.
    """
    try:
        return _measure_inner(job)
    except Exception as e:                                    # noqa: BLE001
        return dict(key=job.get("key"), label=job.get("label"),
                    seed=job.get("cfg", {}).get("seed"),
                    error=f"{type(e).__name__}: {e}",
                    traceback=traceback.format_exc())


def _measure_inner(job):
    cfg = Config(**job["cfg"])
    ticks = job["ticks"]
    track = job.get("track_individual", False)
    block_avg = job.get("block_avg", False)
    if "warm_ticks" in job:
        warm = int(job["warm_ticks"])
    elif block_avg and ticks >= 3 * BLOCK_TICKS:
        # ровно 5 измерительных блоков после прогрева (preregistration §4),
        # но не меньше трети прогона на прогрев
        want = ticks - 5 * BLOCK_TICKS
        warm = max(want, int(ticks * 0.35))
    else:
        warm = int(ticks * job.get("warm_frac", 0.75))
    warm = max(0, min(warm, ticks))

    state, rec = _pop_recorder()
    eng = Engine(cfg)
    eng.run(warm, on_log=rec)

    # измерительный участок: обнуляем накопители, меряем стационар
    eng.reset_metrics()
    if track:
        eng.reset_individual()                               # только измерительное окно

    measure_ticks = ticks - warm
    block_mis = []
    if block_avg and measure_ticks >= BLOCK_TICKS:
        nblocks = measure_ticks // BLOCK_TICKS
        for i in range(nblocks):
            eng.run(BLOCK_TICKS, on_log=rec)
            r = metrics.behaviour_depends_on_energy(eng)
            block_mis.append(r.get("mi_corrected_bits"))
            # обнуляем популяционные накопители ПЕРЕД следующим блоком, но
            # НЕ после последнего: occupancy/switch/итоговое MI должны считаться
            # по данным последнего блока, а не по пустой гистограмме.
            # individual_hist не трогаем — он копится за всё окно.
            if i < nblocks - 1:
                eng.energy_action_hist[:] = 0
                eng.window_hist[:] = 0
                eng.action_counts[:] = 0
                eng.forage_hits = eng.forage_moves = 0
                eng.coop_events = eng.defect_events = 0
        # хвост (обычно 0 тиков) досчитываем в накопители последнего блока
        eng.run(measure_ticks - nblocks * BLOCK_TICKS, on_log=rec)
    else:
        eng.run(measure_ticks, on_log=rec)

    st = eng.stats()
    mi = metrics.behaviour_depends_on_energy(eng)
    occ = metrics.energy_occupancy(eng)
    sw = metrics.switch_point(eng)

    clean = [m for m in block_mis if m is not None]
    row = dict(
        key=job["key"], label=job["label"], seed=cfg.seed,
        mi=(float(np.mean(clean)) if clean else mi.get("mi_corrected_bits")),
        mi_last_block=mi.get("mi_corrected_bits"),
        mi_raw=mi.get("mutual_information_bits"),
        chance=mi.get("chance_level_bits"),
        samples=mi.get("samples"),
        block_mis=block_mis if block_mis else None,
        block_sem=(float(np.std(clean, ddof=1) / np.sqrt(len(clean)))
                   if len(clean) > 1 else None),
        occupancy_bits=occ["entropy_bits"],
        occupied_deciles=occ["occupied_deciles"],
        switch_energy=sw["switch_energy"],
        amplitude=sw["amplitude"],
        pop=st["pop"], peak_pop=state["peak"],
        max_pop=cfg.max_pop,
        hit_ceiling=bool(state["peak"] >= 0.95 * cfg.max_pop),
        extinct=eng.extinct_at,
        forage_accuracy=st["forage_accuracy"],
        coop_rate=st["coop_rate"],
    )
    if track:
        wa = metrics.within_agent_dependence(eng)
        row["within_mi"] = wa.get("mean_mi_bits")
        row["within_sd"] = wa.get("sd")
        row["within_median"] = wa.get("median")
        row["within_n_agents"] = wa.get("n_agents")
    return row


# ------------------------------------------------------- устойчивый run_series
def _load_done(path):
    """Ключи уже посчитанных прогонов (для возобновляемости)."""
    done = {}
    if not Path(path).exists():
        return done
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = r.get("key")
            if k is not None:
                done[k] = r
    return done


def run_series(jobs, out_path, workers=None, resume=True):
    """Прогоняет jobs, инкрементально дописывая JSONL, с возобновляемостью.

    Возвращает список всех строк-результатов (включая уже посчитанные ранее).
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = _load_done(out) if resume else {}
    pending = [j for j in jobs if j["key"] not in done]
    results = list(done.values())

    total = len(jobs)
    already = total - len(pending)
    if already:
        print(f"[resume] {already}/{total} уже посчитано в {out}, "
              f"осталось {len(pending)}", file=sys.stderr)
    if not pending:
        return results

    if workers is None:
        workers = max(1, (os.cpu_count() or 2) - 1)
    workers = min(workers, len(pending))

    t0 = time.time()
    done_n = 0

    def emit(r):
        nonlocal done_n
        with open(out, "a") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        results.append(r)
        done_n += 1
        elapsed = time.time() - t0
        rate = done_n / elapsed if elapsed > 0 else 0
        remain = (len(pending) - done_n) / rate if rate > 0 else float("inf")
        tag = "ERR " if r.get("error") else ""
        print(f"[{done_n}/{len(pending)}] {tag}{r.get('label')} "
              f"seed={r.get('seed')} — {elapsed:.0f}s прошло, "
              f"~{remain:.0f}s осталось", file=sys.stderr)

    if workers <= 1:
        for j in pending:
            emit(measure(j))
    else:
        with mp.Pool(workers) as pool:
            for r in pool.imap_unordered(measure, pending):
                emit(r)
    return results


# ------------------------------------------------------------------ статистика
def wilcoxon_paired(a, b):
    """Парный тест Уилкоксона по seed'ам. scipy если есть, иначе руками."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    if a.size < 5:
        return dict(n=int(a.size), p=None, note="слишком мало пар")
    try:
        from scipy.stats import wilcoxon
        stat, p = wilcoxon(a, b)
        return dict(n=int(a.size), statistic=float(stat), p=float(p))
    except Exception:
        d = a - b
        d = d[d != 0]
        if d.size == 0:
            return dict(n=0, p=None, note="все пары равны")
        r = np.argsort(np.argsort(np.abs(d))) + 1
        w = min(r[d > 0].sum(), r[d < 0].sum())
        n = d.size
        mu = n * (n + 1) / 4
        sd = np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
        z = (w - mu) / sd if sd else 0.0
        from math import erfc, sqrt
        return dict(n=int(n), statistic=float(w), z=float(z),
                    p=float(erfc(abs(z) / sqrt(2))))


def effect_size(a, b):
    """Величина эффекта Клиффа: доля пар, где a > b, минус обратная."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    if a.size == 0 or b.size == 0:
        return None
    gt = (a[:, None] > b[None, :]).sum()
    lt = (a[:, None] < b[None, :]).sum()
    return float((gt - lt) / (a.size * b.size))


def summarize(rows, key="mi"):
    vals = np.array([r[key] for r in rows
                     if r.get(key) is not None and not r.get("error")], float)
    if vals.size == 0:
        return dict(n=0)
    return dict(n=int(vals.size), mean=float(vals.mean()),
                sd=float(vals.std(ddof=1)) if vals.size > 1 else 0.0,
                min=float(vals.min()), max=float(vals.max()),
                median=float(np.median(vals)))


# -------------------------------------------------------------------- режимы
def cmd_calibrate(args):
    """Кривая чувствительности: где должен стоять порог, чтобы метрика его увидела."""
    jobs = []
    for thr in (20, 30, 40, 50, 60, 70, 85):
        jobs.append(dict(label=f"threshold@{thr}", key=f"threshold@{thr}|seed{args.seed}",
                         ticks=args.ticks, track_individual=args.track,
                         cfg=dict(seed=args.seed, policy="threshold",
                                  policy_threshold=float(thr),
                                  track_individual=args.track)))
    jobs.append(dict(label="random", key=f"random|seed{args.seed}", ticks=args.ticks,
                     track_individual=args.track,
                     cfg=dict(seed=args.seed, policy="random", track_individual=args.track)))
    jobs.append(dict(label="evolved", key=f"evolved|seed{args.seed}", ticks=args.ticks,
                     track_individual=args.track,
                     cfg=dict(seed=args.seed, track_individual=args.track)))
    rows = run_series(jobs, args.out, args.workers)
    rows = [r for r in rows if not r.get("error")]
    order = {j["key"]: i for i, j in enumerate(jobs)}
    rows.sort(key=lambda r: order.get(r["key"], 1e9))
    hdr = f"\n{'условие':>14} {'MI, бит':>9} {'случайн.':>9} {'занято дец.':>12} {'популяция':>10}"
    if args.track:
        hdr += f" {'внутриаг.MI':>12} {'агентов':>8}"
    print(hdr)
    for r in rows:
        mi = f"{r['mi']:.4f}" if r["mi"] is not None else "мало данных"
        ch = f"{r['chance']:.5f}" if r["chance"] is not None else "—"
        line = (f"{r['label']:>14} {mi:>9} {ch:>9} "
                f"{r['occupied_deciles']:>12} {r['pop']:>10}")
        if args.track:
            wm = f"{r['within_mi']:.4f}" if r.get("within_mi") is not None else "—"
            line += f" {wm:>12} {r.get('within_n_agents', 0):>8}"
        print(line)
    return rows


def cmd_noise(args):
    """Уровень шума: одно и то же условие на разных seed'ах."""
    jobs = [dict(label="self", key=f"self|seed{s}", ticks=args.ticks,
                 block_avg=True, cfg=dict(seed=s))
            for s in range(1, args.seeds + 1)]
    rows = run_series(jobs, args.out, args.workers)
    valid = [r for r in rows if not r.get("error") and r.get("extinct") is None
             and not r.get("hit_ceiling")]
    st = summarize(valid)
    print(f"\nодно условие 'self', {st.get('n', 0)} валидных seed'ов, {args.ticks} тиков")
    if st.get("n"):
        print(f"  MI: среднее {st['mean']:.4f}, sd {st['sd']:.4f}, "
              f"размах {st['min']:.4f}..{st['max']:.4f}")
        print(f"  значения: {sorted(round(r['mi'], 4) for r in valid if r['mi'] is not None)}")
        print(f"\n  2σ = {2*st['sd']:.4f} бит — порог значимости для сравнения условий.")
    print(f"  вымерло: {sum(1 for r in rows if r.get('extinct') is not None)}, "
          f"упёрлось в потолок: {sum(1 for r in rows if r.get('hit_ceiling'))}, "
          f"ошибок: {sum(1 for r in rows if r.get('error'))}")
    return rows


def cmd_compare(args):
    """Главный эксперимент: четыре условия на одних и тех же seed'ах."""
    conds = ["self", "shuffled", "neighbour", "off"]
    jobs = []
    for s in range(1, args.seeds + 1):
        for c in conds:
            jobs.append(dict(label=c, key=f"{c}|seed{s}", ticks=args.ticks,
                             block_avg=True, track_individual=args.track,
                             cfg=dict(seed=s, intero_mode=c,
                                      interoception=(c != "off"),
                                      track_individual=args.track)))
    rows = run_series(jobs, args.out, args.workers)
    by = {c: [r for r in rows if r.get("label") == c and not r.get("error")]
          for c in conds}
    for c in conds:
        by[c].sort(key=lambda r: r["seed"])

    metric_key = "within_mi" if args.track else "mi"
    print(f"\nглавная метрика: {'внутриагентная' if args.track else 'популяционная'} MI")
    print(f"{'условие':>10} {'MI сред.':>9} {'sd':>8} {'медиана':>9} {'выжило':>8} {'потолок':>8}")
    valid = {}
    for c in conds:
        good = [r for r in by[c] if r.get("extinct") is None and not r.get("hit_ceiling")
                and (r.get("occupied_deciles") or 0) >= 4]
        valid[c] = good
        st = summarize(good, key=metric_key)
        alive = sum(1 for r in by[c] if r.get("extinct") is None)
        ceil = sum(1 for r in by[c] if r.get("hit_ceiling"))
        if st["n"] == 0:
            print(f"{c:>10} {'нет данных':>9} {'':>8} {'':>9} {alive:>4}/{len(by[c])} {ceil:>8}")
            continue
        print(f"{c:>10} {st['mean']:>9.4f} {st['sd']:>8.4f} "
              f"{st['median']:>9.4f} {alive:>4}/{len(by[c])} {ceil:>8}")

    print("\nпарные сравнения с контролем (Уилкоксон по seed'ам, метрика "
          f"{metric_key}):")
    # общие валидные seed'ы для парности
    base_by_seed = {r["seed"]: r.get(metric_key) for r in valid["shuffled"]}
    for c in ("self", "neighbour", "off"):
        pairs = [(r.get(metric_key), base_by_seed[r["seed"]])
                 for r in valid[c] if r["seed"] in base_by_seed]
        vals = [p[0] for p in pairs]
        base = [p[1] for p in pairs]
        w = wilcoxon_paired(vals, base)
        d = effect_size(vals, base)
        pstr = f"p={w['p']:.4f}" if w.get("p") is not None else w.get("note", "—")
        dstr = f"{d:+.3f}" if d is not None else "—"
        print(f"  {c:>10} vs shuffled: {pstr}, дельта Клиффа {dstr}, n={w['n']}")
    print(f"\nсырые числа: {args.out}")
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["calibrate", "noise", "compare"])
    p.add_argument("--ticks", type=int, default=80000)
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--track", action="store_true",
                   help="track_individual: считать и внутриагентную метрику")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    args.workers = args.workers or None
    if args.out is None:
        args.out = f"runs/{args.mode}.jsonl"
    {"calibrate": cmd_calibrate, "noise": cmd_noise, "compare": cmd_compare}[args.mode](args)


if __name__ == "__main__":
    main()
