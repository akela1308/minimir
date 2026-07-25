#!/usr/bin/env python3
"""Чтение логов. Графики нужны не ради красоты, а как диагностика.

Главный вопрос, на который отвечает эта программа: вышла ли метрика на плато.
Если I(энергия; действие) на конце прогона всё ещё растёт, мы измеряем не
свойство популяции, а длину прогона — и сравнивать условия нельзя.

  python analyze.py list
  python analyze.py show 3
  python analyze.py plateau 3 4 5 --out runs/plateau.png
"""
import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np


def connect(db):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def cmd_list(con, args):
    rows = con.execute(
        "SELECT r.run_id, r.label, COUNT(t.tick) AS n, MAX(t.tick) AS last, "
        "       MAX(t.pop) AS peak_pop "
        "FROM runs r LEFT JOIN ticks t ON t.run_id = r.run_id "
        "GROUP BY r.run_id ORDER BY r.run_id").fetchall()
    print(f"{'id':>4} {'метка':>12} {'точек':>7} {'тиков':>8} {'пик поп.':>9}  условие")
    for r in rows:
        cfg = json.loads(con.execute(
            "SELECT config FROM runs WHERE run_id=?", (r["run_id"],)).fetchone()[0])
        cond = f"intero={cfg.get('intero_mode')} policy={cfg.get('policy')} " \
               f"regrowth={cfg.get('regrowth')}"
        print(f"{r['run_id']:>4} {str(r['label']):>12} {r['n'] or 0:>7} "
              f"{r['last'] or 0:>8} {r['peak_pop'] or 0:>9}  {cond}")


def series(con, run_id):
    rows = con.execute(
        "SELECT tick, pop, mean_E, resource, forage_accuracy, mi_window, coop_rate "
        "FROM ticks WHERE run_id=? ORDER BY tick", (run_id,)).fetchall()
    return {k: np.array([r[k] if r[k] is not None else np.nan for r in rows], float)
            for k in rows[0].keys()} if rows else {}


def sparkline(v, width=48):
    v = np.asarray(v, float)
    v = v[~np.isnan(v)]
    if v.size == 0:
        return "нет данных"
    idx = np.linspace(0, v.size - 1, min(width, v.size)).astype(int)
    v = v[idx]
    lo, hi = v.min(), v.max()
    if hi - lo < 1e-12:
        return "─" * v.size
    blocks = "▁▂▃▄▅▆▇█"
    q = ((v - lo) / (hi - lo) * (len(blocks) - 1)).round().astype(int)
    return "".join(blocks[i] for i in q)


def cmd_show(con, args):
    for rid in args.run_ids:
        s = series(con, rid)
        if not s:
            print(f"прогон {rid}: пусто")
            continue
        meta = con.execute("SELECT label, config FROM runs WHERE run_id=?", (rid,)).fetchone()
        print(f"\n=== прогон {rid} [{meta['label']}] ===")
        for key, name in (("pop", "популяция"), ("mean_E", "энергия"),
                          ("mi_window", "MI за окно"), ("forage_accuracy", "точность поиска")):
            v = s[key]
            fin = v[~np.isnan(v)]
            tail = f"{fin[-1]:.4f}" if fin.size else "—"
            print(f"  {name:>16} {sparkline(v)}  → {tail}")
        res = con.execute("SELECT key, value FROM results WHERE run_id=?", (rid,)).fetchall()
        for r in res:
            if r["key"] in ("energy_dependence", "switch_point"):
                print(f"  {r['key']}: {r['value'][:160]}")


def plateau_test(v, tail_frac=0.3):
    """Вышла ли кривая на плато: сравниваем наклон в хвосте с разбросом.

    Возвращает нормированный наклон — во сколько сигм за хвост меняется метрика.
    |наклон| < 1 считаем плато.
    """
    v = np.asarray(v, float)
    v = v[~np.isnan(v)]
    if v.size < 10:
        return None
    k = max(int(v.size * tail_frac), 5)
    tail = v[-k:]
    x = np.arange(k)
    slope = np.polyfit(x, tail, 1)[0] * k          # изменение за весь хвост
    sd = tail.std(ddof=1)
    return float(slope / sd) if sd > 0 else 0.0


def cmd_plateau(con, args):
    print(f"{'прогон':>7} {'метка':>12} {'наклон хвоста, σ':>18}  вердикт")
    curves = {}
    for rid in args.run_ids:
        s = series(con, rid)
        if not s:
            continue
        label = con.execute("SELECT label FROM runs WHERE run_id=?", (rid,)).fetchone()[0]
        v = s["mi_window"]
        curves[f"{rid} {label}"] = (s["tick"], v)
        sl = plateau_test(v)
        verdict = "—" if sl is None else ("плато" if abs(sl) < 1.0 else "ЕЩЁ РАСТЁТ" if sl > 0 else "падает")
        print(f"{rid:>7} {str(label):>12} {sl if sl is not None else float('nan'):>18.2f}  {verdict}")
    if args.out and curves:
        _plot(curves, args.out)


def _plot(curves, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не установлен — график пропущен")
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for name, (t, v) in curves.items():
        ok = ~np.isnan(v)
        if ok.sum() > 3:
            k = max(int(ok.sum() * 0.05), 1)
            sm = np.convolve(v[ok], np.ones(k) / k, mode="valid")
            ax.plot(t[ok][k - 1:], sm, label=name, lw=1.4)
    ax.set_xlabel("тик")
    ax.set_ylabel("I(энергия; действие), бит за окно")
    ax.set_title("Выход метрики на плато")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(f"график: {out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["list", "show", "plateau"])
    p.add_argument("run_ids", nargs="*", type=int)
    p.add_argument("--db", default="runs/minimir.db")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    con = connect(args.db)
    {"list": cmd_list, "show": cmd_show, "plateau": cmd_plateau}[args.cmd](con, args)


if __name__ == "__main__":
    main()
