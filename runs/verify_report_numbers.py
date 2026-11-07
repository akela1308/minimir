"""Проверка чисел в отчётах по сырым данным.

Правило проекта с 7 ноября 2026: число попадает в текст отчёта, README или на
сайт только если его можно получить скриптом из репозитория. Этот файл и есть
такой скрипт для главных чисел протоколов A и B1. Каждое утверждение ниже
пересчитывается из сырых строк и сравнивается с тем, что написано в текстах.

Что проверяется для каждого утверждения:
  1. пересчитанное значение совпадает с опубликованным в пределах допуска
     (допуск отражает только округление при записи);
  2. опубликованная запись числа действительно стоит в перечисленных файлах
     (если текст переписали и число пропало или изменилось, это тоже ошибка).

Запуск из корня репозитория:
  python runs/verify_report_numbers.py          # все проверки, код выхода 1 при ошибке
  python runs/verify_report_numbers.py --list   # перечень утверждений без проверки текстов

Новое число в отчёте добавляется сюда отдельным утверждением, со ссылкой на
файл и запись, в которой оно стоит. Исторические числа, которые поправлены в
ERRATUM_2026-10-28.md (например, подпись 180 против 183), проверяются как
числа: значение верное, неверной была только подпись, и это записано рядом.
"""
import argparse
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

B_PATH = os.path.join(ROOT, "runs", "daily", "protocol_b.jsonl")
A_PATHS = [os.path.join(ROOT, "runs", "compare.jsonl"),
           os.path.join(ROOT, "runs", "daily", "compare_ext.jsonl")]

PILOT_SEEDS = {1, 2}          # PREREGISTRATION_B.md §9, ERRATUM 1.1
PILOT_SEEDS_WIDE = {1, 2, 3}  # заметка о состоянии от 9 сентября


# ---------------------------------------------------------------- данные

def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_b():
    by = defaultdict(dict)
    for r in read_jsonl(B_PATH):
        if r.get("protocol") == "B1-100k-v1" and not r.get("error"):
            by[r["label"]][r["seed"]] = r
    return by


def alive(r):
    return r.get("extinct") is None


def curve_at(r, tick):
    for p in r.get("curve", []):
        if p.get("tick") == tick:
            return p
    return None


# ---------------------------------------------------------------- тесты

def mcnemar_exact(b, c):
    """Точный двусторонний тест Макнемара (биномиальный по расходящимся парам)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def wilcoxon_p(d):
    from scipy.stats import wilcoxon
    d = np.asarray(d, float)
    d = d[d != 0]
    if d.size == 0:
        return 1.0
    return float(wilcoxon(d, alternative="two-sided", method="exact"
                          if d.size <= 25 else "auto").pvalue)


def mannwhitney_greater(a, b):
    from scipy.stats import mannwhitneyu
    return float(mannwhitneyu(a, b, alternative="greater").pvalue)


# ---------------------------------------------------------------- утверждения
# Каждое: id, что утверждается, функция пересчёта, опубликованное значение,
# допуск, и где стоит запись числа: список (файл, точная подстрока).

def claims():
    by = load_b()
    life, frozen, never = by["life"], by["life_frozen"], by["never"]
    never_frozen, fast, slow = by["never_frozen"], by["fast"], by["slow"]
    surv = sorted(s for s, r in life.items() if alive(r))
    ext_life = [r for r in life.values() if not alive(r)]

    def n_extinct(c):
        return sum(1 for r in by[c].values() if not alive(r))

    def median_death(c):
        return float(np.floor(np.median([r["extinct"] for r in by[c].values()
                                         if not alive(r)])))

    def mcnemar_without(drop):
        seeds = [s for s in life if s in frozen and s not in drop]
        b = sum(1 for s in seeds if alive(life[s]) and not alive(frozen[s]))
        c = sum(1 for s in seeds if not alive(life[s]) and alive(frozen[s]))
        return mcnemar_exact(b, c)

    def lr_pairs(c1, c2):
        seeds = [s for s in by[c1] if s in by[c2] and alive(by[c1][s])
                 and alive(by[c2][s])]
        return np.array([math.log10(by[c1][s]["lr_median"])
                         - math.log10(by[c2][s]["lr_median"]) for s in seeds])

    def nf_threshold():
        v = np.array([math.log10(r["lr_median"] / r["lr_init"])
                      for r in never_frozen.values()])
        return 2 * float(v.std(ddof=1))

    taste_surv = np.array([life[s]["taste"] for s in surv])
    f10 = fast.get(10, {})

    def pop4000(rows):
        return float(np.median([curve_at(r, 4000)["pop"] for r in rows]))

    def lr4000(rows):
        return float(np.median([curve_at(r, 4000)["lr_median"] for r in rows]))

    surv_rows = [life[s] for s in surv]

    RB, RBE, RM = "REPORT_B.md", "REPORT_B_EN.md", "README.md"
    ER = "ERRATUM_2026-10-28.md"

    out = [
        ("B.extinct.life", "вымерло в life из 40", lambda: n_extinct("life"), 32, 0,
         [(RB, "32 / 40"), (RBE, "32 / 40"), (RM, "32 / 40")]),
        ("B.extinct.slow", "вымерло в slow из 40", lambda: n_extinct("slow"), 30, 0,
         [(RB, "30 / 40"), (RBE, "30 / 40"), (RM, "30 / 40")]),
        ("B.extinct.fast", "вымерло в fast из 40", lambda: n_extinct("fast"), 34, 0,
         [(RB, "34 / 40"), (RBE, "34 / 40"), (RM, "34 / 40")]),
        ("B.extinct.life_frozen", "вымерло в life_frozen из 40",
         lambda: n_extinct("life_frozen"), 40, 0,
         [(RB, "40 / 40"), (RBE, "40 / 40"), (RM, "40 / 40")]),
        ("B.extinct.never", "вымерло в never", lambda: n_extinct("never"), 0, 0, []),
        ("B.extinct.never_frozen", "вымерло в never_frozen",
         lambda: n_extinct("never_frozen"), 0, 0, []),
        ("B.death.slow", "медианный тик гибели slow", lambda: median_death("slow"),
         10741, 0, [(RB, "10 741")]),
        ("B.death.life", "медианный тик гибели life", lambda: median_death("life"),
         5986, 0, [(RB, "5 986")]),
        ("B.death.fast", "медианный тик гибели fast", lambda: median_death("fast"),
         5833, 0, [(RB, "5 833")]),
        ("B.death.life_frozen", "медианный тик гибели life_frozen",
         lambda: median_death("life_frozen"), 5983, 0, [(RB, "5 983")]),
        ("B.survivors", "семена, пережившие первую смену в life",
         lambda: surv, [1, 2, 3, 10, 18, 28, 35, 39], None,
         [(RB, "1, 2, 3, 10, 18, 28, 35, 39")]),
        ("B.mcnemar.all", "Макнемар life против life_frozen, все 40",
         lambda: mcnemar_without(set()), 0.0078, 0.00005,
         [(RB, "0,0078"), (RBE, "0.0078"), (RM, "0.0078")]),
        ("B.mcnemar.no12", "Макнемар без пилотных семян 1-2",
         lambda: mcnemar_without(PILOT_SEEDS), 0.031, 0.0005,
         [(ER, "p = 0,031"), (ER, "p = 0.031"), (RM, "0.031")]),
        ("B.mcnemar.no123", "Макнемар без семян 1-3",
         lambda: mcnemar_without(PILOT_SEEDS_WIDE), 0.0625, 0.00005,
         [(ER, "0,0625"), (ER, "0.0625")]),
        ("B.ratio.life_never", "отношение lr life/never по парам выживших",
         lambda: 10 ** float(np.median(lr_pairs("life", "never"))), 14.47, 0.005,
         [(RB, "14,5"), (RBE, "14.5")]),
        ("B.wilcoxon.life_never", "парный Уилкоксон lr life против never",
         lambda: wilcoxon_p(lr_pairs("life", "never")), 0.0078, 0.00005,
         [(RB, "0,0078")]),
        ("B.ratio.never_nf", "отношение lr never/never_frozen",
         lambda: 10 ** float(np.median(lr_pairs("never", "never_frozen"))), 1.38, 0.005,
         [(RB, "1,38")]),
        ("B.wilcoxon.never_nf", "парный Уилкоксон never против never_frozen",
         lambda: wilcoxon_p(lr_pairs("never", "never_frozen")), 0.115, 0.0005,
         [(RB, "0,115")]),
        ("B.crit2.effect", "эффект в log10 на 100 000-м тике (критерий 2)",
         lambda: float(np.median(lr_pairs("life", "never"))), 1.16, 0.005,
         [(RB, "1,16")]),
        ("B.crit2.threshold", "порог 2σ дрейфа never_frozen на 100 000-м тике",
         nf_threshold, 1.786, 0.0005, [(RB, "1,786"), (RBE, "1.786")]),
        ("B.q75.cap", "миров life, где 75-й процентиль lr стоит на потолке 4,0",
         lambda: sum(1 for r in surv_rows if abs(r["lr_q75"] - 4.0) < 1e-6), 8, 0,
         [(ER, "4,000")]),
        ("B.taste.median", "медиана фенотипа вкуса у выживших life",
         lambda: float(np.median(taste_surv)), -4.92, 0.005, [(RB, "4,92")]),
        ("B.taste.mean", "среднее фенотипа вкуса у выживших life",
         lambda: float(np.mean(taste_surv)), -2.04, 0.005, [(ER, "2,04")]),
        ("B.taste.positive", "выживших life с положительным вкусом на последнем тике",
         lambda: int((taste_surv > 0).sum()), 2, 0, []),
        ("B.fast10.switches", "fast, семя 10: пережито смен", lambda: f10.get("switches"),
         632, 0, [(ER, "632")]),
        ("B.fast10.lr", "fast, семя 10: медиана скорости обучения",
         lambda: f10.get("lr_median"), 0.0004, 0.00005, [(ER, "0,0004")]),
        ("B.fast10.acc", "fast, семя 10: точность еды", lambda: f10.get("eat_accuracy"),
         0.70, 0.005, [(ER, "0,70")]),
        ("B.first_switch.extinct", "медиана первой смены у вымерших миров life",
         lambda: float(np.median([r["first_switch"] for r in ext_life])), 5637, 0.5,
         [(RB, "5637")]),
        ("B.first_switch.all", "медиана первой смены по всем 40 мирам life",
         lambda: float(np.median([r["first_switch"] for r in life.values()])), 5553.5, 0,
         [(ER, "5553,5")]),
        ("B.pop4000.surv", "медиана численности на 4000-м тике, выжившие",
         lambda: pop4000(surv_rows), 180, 0.5, [(RB, "180 (142")]),
        ("B.pop4000.ext", "медиана численности на 4000-м тике, погибшие",
         lambda: pop4000(ext_life), 183, 0.5, [(RB, "183 (122")]),
        ("B.lr4000.surv", "медиана lr на 4000-м тике, выжившие",
         lambda: lr4000(surv_rows), 0.120, 0.0005, [(RB, "0,120")]),
        ("B.lr4000.ext", "медиана lr на 4000-м тике, погибшие",
         lambda: lr4000(ext_life), 0.103, 0.0005, [(RB, "0,103")]),
        ("B.mw.lr4000", "односторонний Манн-Уитни, lr выживших больше",
         lambda: mannwhitney_greater([curve_at(r, 4000)["lr_median"] for r in surv_rows],
                                     [curve_at(r, 4000)["lr_median"] for r in ext_life]),
         0.023, 0.0005, [(RB, "0,023")]),
        ("B.minpop.surv", "медиана минимума популяции после смены, выжившие",
         lambda: float(np.median([r["min_pop_after_switch"] for r in surv_rows])), 14, 0.5,
         [(RB, "**14**")]),
        ("B.minpop.ext", "медиана минимума популяции после смены, погибшие",
         lambda: float(np.median([r["min_pop_after_switch"] for r in ext_life])), 2, 0.5,
         [(RB, "**2**")]),
    ]

    # протокол A: тем же кодом, которым собирается журнал
    try:
        from runs import journal
        rows = []
        for p in A_PATHS:
            if os.path.exists(p):
                rows += read_jsonl(p)
        st = journal.analyse(rows)
        cmp_self = st["comparisons"]["self"]
        out += [
            ("A.self_shuffled.diff", "A: средняя парная разница self минус shuffled",
             lambda: cmp_self["mean_diff"], 0.0198, 0.00005, [(ER, "0,0198")]),
            ("A.self_shuffled.n", "A: число пар self/shuffled", lambda: cmp_self["n"], 54, 0,
             []),
            ("A.two_sigma", "A: порог 2σ межсидового разброса уровня",
             lambda: st["two_sigma"], 0.0519, 0.0001, [(ER, "0,052")]),
        ]
    except Exception as e:  # pragma: no cover
        out.append(("A.import", f"анализ протокола A не запустился: {e}",
                    lambda: None, "ok", None, []))
    return out


# ---------------------------------------------------------------- проверка

def check_value(val, expected, tol):
    if tol is None:
        return val == expected
    if val is None:
        return False
    return abs(float(val) - float(expected)) <= tol


def fmt(v):
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="только пересчитать значения")
    args = ap.parse_args(argv)

    texts = {}

    def text(path):
        if path not in texts:
            full = os.path.join(ROOT, path)
            texts[path] = open(full, encoding="utf-8").read() if os.path.exists(full) else None
        return texts[path]

    n_bad = 0
    for cid, what, fn, expected, tol, where in claims():
        try:
            val = fn()
        except Exception as e:
            val, err = None, e
        else:
            err = None
        ok = err is None and check_value(val, expected, tol)
        missing = []
        if not args.list:
            for path, needle in where:
                t = text(path)
                if t is None or needle not in t:
                    missing.append(f"{path}: нет записи «{needle}»")
        status = "ok " if ok and not missing else "ОШИБКА"
        if status != "ok ":
            n_bad += 1
        print(f"[{status}] {cid}: {what}: пересчитано {fmt(val)}, опубликовано {fmt(expected)}"
              + (f" (допуск {tol})" if tol else ""))
        if err is not None:
            print(f"         исключение: {err}")
        for m in missing:
            print(f"         {m}")
    print()
    print("всё сходится" if n_bad == 0 else f"расхождений: {n_bad}")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
