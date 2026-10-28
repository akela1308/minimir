#!/usr/bin/env python3
"""Достижимость критерия 2 протокола B2 (28 октября 2026).

Прежнее правило черновика («медиана по мирам D_lr = log10(lr_median/lr_init)
больше 2σ по мирам D_marker = log10(marker_median/marker_init)») было
недостижимо по построению: при taste_lr_max 4,0 и lr_init 0,5 потолок D_lr
равен log10(8) = 0,903, а 2σ маркера по мирам life, пережившим горлышко, на
пилоте 0,96 (lr 0,5) и 1,57 (все варианты); даже дрейф без горлышка (never,
never_frozen) даёт 0,7-1,2 к 16 000-му тику.

Новое правило (PREREGISTRATION_B2 §4 критерий 2, runs/journal_b2.py): в каждом
мире life, дожившем до T_read = первая смена + 10 000, R_i = log10(lr_median /
marker_median); проходит, если одновыборочный Уилкоксон R против нуля даёт
p < 0,05 при не меньше 6 мирах и 95% бутстреп-ДИ среднего R целиком выше
R_MIN = 0,30 (фактор 2). Потолок R: log10(8) минус дрейф маркера D_marker, то
есть до 0,9 и выше, если маркер ушёл вниз.

Этот скрипт считает R из пилота (runs/b2/pilot/pilot_b2_lr.jsonl, seed'ы
101-103, 20 000 тиков, не чтение) для выживших life при lr_init 0,5 и 0,3, и
дрейф маркера в never / never_frozen на тике 16 000 по всем трём порциям
пилота (pilot_b2.jsonl, pilot_b2_lr.jsonl, pilot_b2_ramp.jsonl). Запуск из корня:

  python runs/b2/attainability_check.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runs"))
import journal_b2 as jb                                     # noqa: E402

PILOT = ROOT / "runs" / "b2" / "pilot" / "pilot_b2_lr.jsonl"
PILOT_ALL = [PILOT, ROOT / "runs" / "b2" / "pilot" / "pilot_b2.jsonl",
             ROOT / "runs" / "b2" / "pilot" / "pilot_b2_ramp.jsonl"]
CAP = 4.0


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def point_at(r, tick):
    for p in r["curve"]:
        if p["tick"] >= tick:
            return p
    return None


def main():
    rows = load(PILOT)
    print(f"пилот: {PILOT.relative_to(ROOT)}, строк {len(rows)}; R_MIN = {jb.R_MIN}, "
          f"минимум миров {jb.MIN_WORLDS_R}, бутстреп {jb.BOOT_N} (seed {jb.BOOT_SEED})")
    for lr0 in (0.5, 0.3):
        print(f"\n== life, lr_init {lr0}, выжившие до T_read = первая смена + {jb.READ_OFFSET} ==")
        print(f"потолок D_lr = log10({CAP}/{lr0}) = {math.log10(CAP / lr0):.3f}; "
              f"потолок R = {math.log10(CAP / lr0):.3f} - D_marker")
        R, d_lr, d_mk = [], [], []
        for r in rows:
            if r["label"] != "life" or r.get("lr_init") != lr0 or r["extinct"] is not None:
                continue
            pt = point_at(r, r["first_switch"] + jb.READ_OFFSET)
            if pt is None or not pt.get("lr_median") or not pt.get("marker_median"):
                continue
            a = math.log10(pt["lr_median"] / r["lr_init"])
            b = math.log10(pt["marker_median"] / r["marker_init"])
            R.append(a - b); d_lr.append(a); d_mk.append(b)
            print(f"  seed {r['seed']}: tick {pt['tick']}, lr_median {pt['lr_median']:.3f}, "
                  f"marker_median {pt['marker_median']:.3f}, D_lr={a:+.3f}, D_marker={b:+.3f}, "
                  f"R = D_lr - D_marker = {a - b:+.3f} (фактор {10 ** (a - b):.2f})")
        c2 = jb.criterion2_from_R(R, d_lr, d_mk)
        print(f"  n={c2['n']}: R среднее {c2['mean_R']:+.3f}, медиана {c2['median_R']:+.3f}, "
              f"ДИ среднего [{c2['ci_mean_low']:+.3f}; {c2['ci_mean_high']:+.3f}]; "
              f"критерий 2 на пилоте: {'пройден' if c2['passed'] else 'не считается или не пройден'} "
              f"(миров меньше {jb.MIN_WORLDS_R}: Уилкоксон не считается)")
        if len(d_mk) > 1:
            print(f"  старое правило: медиана D_lr {np.median(d_lr):.3f} против 2σ(D_marker) "
                  f"{2 * np.std(d_mk, ddof=1):.3f}: {'проходит' if np.median(d_lr) > 2 * np.std(d_mk, ddof=1) else 'НЕ проходит'}")

    print("\n== дрейф маркера без горлышка (never, never_frozen) на тике 16 000, все три порции пилота ==")
    allrows = [r for f in PILOT_ALL if f.exists() for r in load(f)]
    for lab in ("never", "never_frozen"):
        vals = []
        for r in allrows:
            if r["label"] != lab or r["extinct"] is not None:
                continue
            pt = point_at(r, 16000)
            if pt and pt.get("marker_median"):
                vals.append((r["seed"], r.get("lr_init"), math.log10(pt["marker_median"] / r["marker_init"])))
        v = np.array([x[2] for x in vals])
        worst = max(vals, key=lambda x: abs(x[2]))
        print(f"  {lab:13s} n={v.size} D_marker среднее {v.mean():+.3f}, sd {v.std(ddof=1):.3f}, "
              f"2σ {2 * v.std(ddof=1):.3f}, от {v.min():+.3f} до {v.max():+.3f}; "
              f"самый большой сдвиг seed {worst[0]} (lr_init {worst[1]}): {worst[2]:+.3f}, фактор {10 ** abs(worst[2]):.0f}")
    print("\nВывод: при lr_init 0,5 выжившие life дают R = 0,34, 1,27, 0,71, то есть фактор 2,2-18 над "
          "нейтральным маркером в том же мире; R_MIN = 0,30 достижим, а нейтральный дрейф медианы "
          "популяции за 16k тиков доходит до фактора 20 (never, яд -0,25, seed 101: D_marker -1,32; "
          "рецензия 28.10 приписала это seed'у 102), поэтому знаковый тест "
          "маркера (§8.3) при 40 seed'ах маломощен.")


if __name__ == "__main__":
    main()
