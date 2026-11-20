#!/usr/bin/env python3
"""Критерии протокола N4 как код (20 ноября 2026).

Единая точка правды по статистике: этот модуль читают и журнал, и проверка
достижимости (runs/n4/attainability_check.py). Каждый критерий это функция от
таблицы y[условие][семя] из нулей и единиц (1 = мир пережил смену) и возвращает
один из трёх вердиктов: «подтверждено», «опровергнуто», «не определено».

Общие правила:
  * единица анализа это семя; все сравнения парные по семени;
  * доверительные интервалы: перцентильный бутстреп по семенам, 95%, 10 000
    повторов, генератор с фиксированным зерном;
  * тренд: перестановочный тест внутри семени (метки условий переставляются в
    пределах одного семени), 20 000 перестановок, то же зерно;
  * пороги наименьшего интересного эффекта названы здесь числами и в
    предрегистрации теми же числами.

  python runs/n4_analyze.py runs/n4/pilot/pilot2.jsonl
"""
import json
import sys
from math import comb
from pathlib import Path

import numpy as np

RNG_SEED = 20261120
N_BOOT = 10000
N_PERM = 20000

# --- какие условия входят в какой критерий ---------------------------------
D_ALL = ["D_L0.1", "D_L0.3", "D_L0.45", "D_L0.6", "D_L0.8", "D_L1", "D_L1.5", "D_L2.5", "D_L4"]
D_LOW = ["D_L0.1", "D_L0.3"]
D_HIGH = ["D_L1", "D_L1.5", "D_L2.5", "D_L4"]
K2_LOW, K2_HIGH = "D_L0.6", "D_L1.5"    # порог у каждого мира свой: обе дозы внутри перехода
V_ALL = ["D_L0.1", "V_s0.5", "V_s1", "V_s1.5", "V_s2"]     # sigma 0 это D_L0.1
V_LO, V_HI = "D_L0.1", "V_s2"
E_PAIRS = [("E_L0.6", "D_L0.6"), ("E_L1.5", "D_L1.5")]   # только описательно
M_MID = [("M_L0.45", "D_L0.45"), ("M_L0.6", "D_L0.6"), ("M_L0.8", "D_L0.8"), ("M_L1", "D_L1")]
F_COND = "F_s2"

# --- пороги (наименьший интересный эффект) ----------------------------------
K1_MIN_DIFF = 0.20      # положительный контроль: высокие дозы минус низкие
K2_FLOOR = 0.10         # при меньшей дозе уже выживает больше каждого десятого мира
K2_CEILING = 0.90       # при большей (в 2,5 раза) всё ещё гибнет больше каждого десятого
K3_MIN_DIFF = 0.10      # изменчивость: sigma 2.0 минус sigma 0
K4_MIN_DIFF = 0.05      # мягкий яд: сдвиг доли спасённых на средних дозах
K4_EQUIV = 0.10         # мягкий яд: границы «тяжесть не решает»
ALPHA = 0.01


# ------------------------------------------------------------------ данные
def load_table(path):
    """jsonl -> (таблица y[условие][семя], строки)."""
    rows = [json.loads(l) for l in open(path) if l.strip()]
    y = {}
    for r in rows:
        if r["label"] == "EXCLUDED":
            continue
        y.setdefault(r["label"], {})[r["seed"]] = int(bool(r["rescued"]))
    return y, rows


def confirmatory_table(rows, conds, seed_first, n_confirm):
    """Таблица подтверждающего чтения: первые n_confirm годных семян по порядку,
    начиная с seed_first. Годное семя это семя, по которому посчитаны все
    условия; негодные (строка EXCLUDED) пропускаются и заменяются следующими.
    Возвращает (таблица или None, сводка)."""
    excluded = sorted(r["seed"] for r in rows if r["label"] == "EXCLUDED" and r["seed"] >= seed_first)
    by = {}
    for r in rows:
        if r["label"] != "EXCLUDED" and r["seed"] >= seed_first:
            by.setdefault(r["seed"], {})[r["label"]] = int(bool(r["rescued"]))
    full = sorted(s for s, d in by.items() if all(c in d for c in conds))
    partial = sorted(s for s, d in by.items() if not all(c in d for c in conds))
    take = full[:n_confirm]
    # дыр быть не должно: каждое семя до последнего взятого либо годно, либо исключено
    gaps = []
    if take:
        known = set(full) | set(excluded)
        gaps = [s for s in range(seed_first, take[-1] + 1) if s not in known]
    info = dict(valid=len(full), taken=len(take), excluded=excluded, partial=partial, gaps=gaps,
                last_seed=(take[-1] if take else None))
    if len(take) < n_confirm or gaps:
        return None, info
    return {c: {s: by[s][c] for s in take} for c in conds}, info


def matrix(y, conds):
    """Матрица семена x условия по семенам, где посчитаны все условия."""
    seeds = sorted(set.intersection(*[set(y.get(c, {})) for c in conds])) if conds else []
    m = np.array([[y[c][s] for c in conds] for s in seeds], dtype=float).reshape(len(seeds), len(conds))
    return seeds, m


# -------------------------------------------------------------- статистика
def boot_ci(per_seed, rng=None, n_boot=None):
    """95% перцентильный бутстреп среднего по семенам."""
    v = np.asarray(per_seed, dtype=float)
    if v.size == 0:
        return None, None, None
    n_boot = n_boot or N_BOOT
    rng = rng or np.random.default_rng(RNG_SEED)
    idx = rng.integers(0, v.size, (n_boot, v.size))
    means = v[idx].mean(axis=1)
    return float(v.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def perm_trend(m, rng=None, n_perm=None):
    """Перестановочный тест тренда. m: семена x уровни (по возрастанию).
    Статистика: сумма по семенам скалярного произведения центрированных рангов
    уровня на исход. Нулевое распределение: перестановки уровней внутри семени.
    Двусторонний p."""
    n, k = m.shape
    if n == 0 or k < 2:
        return None, None
    n_perm = n_perm or N_PERM
    rng = rng or np.random.default_rng(RNG_SEED)
    w = np.arange(k, dtype=float) - (k - 1) / 2.0
    obs = float((m @ w).sum())
    # у семени, где исход одинаков на всех уровнях, вклад нулевой при любой перестановке
    var_rows = m[m.std(axis=1) > 0]
    if var_rows.shape[0] == 0:
        return obs, 1.0
    count = 0
    r = var_rows.shape[0]
    chunk = max(1, 200000 // max(1, r * k))
    done = 0
    while done < n_perm:
        b = min(chunk, n_perm - done)
        perm = np.argsort(rng.random((b, r, k)), axis=2)
        stat = (np.take_along_axis(np.broadcast_to(var_rows, (b, r, k)), perm, axis=2) @ w).sum(axis=1)
        count += int((np.abs(stat) >= abs(obs) - 1e-12).sum())
        done += b
    return obs, (count + 1) / (n_perm + 1)


def mcnemar_exact(b, c):
    """Точный двусторонний тест Макнемара по расходящимся парам."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)


def verdict3(confirmed, refuted):
    return "подтверждено" if confirmed else ("опровергнуто" if refuted else "не определено")


# ---------------------------------------------------------------- критерии
def k1_dose_control(y):
    """Положительный контроль: прибор видит зависимость от дозы."""
    seeds, m = matrix(y, D_ALL)
    if not seeds:
        return dict(n=0, verdict="нет данных")
    stat, p = perm_trend(m)
    _, lo_m = matrix({c: {s: y[c][s] for s in seeds} for c in D_LOW}, D_LOW)
    _, hi_m = matrix({c: {s: y[c][s] for s in seeds} for c in D_HIGH}, D_HIGH)
    diff = hi_m.mean(axis=1) - lo_m.mean(axis=1)
    mean, lo, hi = boot_ci(diff)
    ok = p < ALPHA and lo > K1_MIN_DIFF
    return dict(n=len(seeds), curve={c: float(m[:, i].mean()) for i, c in enumerate(D_ALL)},
                p_trend=p, diff=mean, ci=[lo, hi], threshold=K1_MIN_DIFF,
                verdict=verdict3(ok, hi < K1_MIN_DIFF))


def k2_heterogeneity(y):
    """Порог у каждого мира свой: переход от «не выживает никто» к «выживают
    все» растянут по дозе. Проверяется на двух дозах, различающихся в 2,5 раза:
    при меньшей уже спасается заметная доля миров, при большей ещё не все.
    Опровергается, если переход резкий: при меньшей дозе почти никто, либо при
    большей почти все."""
    seeds, m = matrix(y, [K2_LOW, K2_HIGH])
    if not seeds:
        return dict(n=0, verdict="нет данных")
    rng = np.random.default_rng(RNG_SEED)
    s_lo, lo_lo, lo_hi = boot_ci(m[:, 0], rng)
    s_hi, hi_lo, hi_hi = boot_ci(m[:, 1], rng)
    ok = lo_lo > K2_FLOOR and hi_hi < K2_CEILING
    sharp = lo_hi < K2_FLOOR or hi_lo > K2_CEILING
    return dict(n=len(seeds), s_low=s_lo, ci_low=[lo_lo, lo_hi], s_high=s_hi,
                ci_high=[hi_lo, hi_hi], floor=K2_FLOOR, ceiling=K2_CEILING,
                verdict=verdict3(ok, sharp))


def describe_noise(y):
    """Часть E, описательно: парное сравнение дозы с шумом и без. Критерием не
    является: по пилоту 2 прибавка при дозе 1,5 около десяти пунктов, то есть
    на самой границе наименьшего интересного эффекта, а при дозе 0,6 знак
    обратный. Критерий на такой величине был бы лотереей."""
    out = {}
    for e, d in E_PAIRS:
        seeds, m = matrix(y, [e, d])
        if not seeds:
            continue
        gain = int(((m[:, 0] == 1) & (m[:, 1] == 0)).sum())
        loss = int(((m[:, 0] == 0) & (m[:, 1] == 1)).sum())
        mean, lo, hi = boot_ci(m[:, 0] - m[:, 1])
        out[e] = dict(n=len(seeds), s_noise=float(m[:, 0].mean()), s_plain=float(m[:, 1].mean()),
                      gain=gain, loss=loss, p_mcnemar=mcnemar_exact(gain, loss),
                      diff=mean, ci=[lo, hi])
    return out


def k3_variation(y):
    """Стоячая изменчивость спасает: доля спасённых растёт с sigma."""
    seeds, m = matrix(y, V_ALL)
    if not seeds:
        return dict(n=0, verdict="нет данных")
    stat, p = perm_trend(m)
    diff = m[:, V_ALL.index(V_HI)] - m[:, V_ALL.index(V_LO)]
    mean, lo, hi = boot_ci(diff)
    ok = p < ALPHA and lo > K3_MIN_DIFF
    return dict(n=len(seeds), curve={c: float(m[:, i].mean()) for i, c in enumerate(V_ALL)},
                p_trend=p, diff=mean, ci=[lo, hi], threshold=K3_MIN_DIFF,
                verdict=verdict3(ok, hi < K3_MIN_DIFF))


def k4_severity(y):
    """Мягкий яд на средних дозах. Теория спасения ждёт, что более мягкая
    перемена переживается чаще. Пилот 2 показал обратное: при мягком яде
    спасённых меньше, потому что слабый яд это ещё и слабый урок. Объявленное
    предсказание: «мягче хуже». Исходов четыре, и каждый содержателен."""
    conds = [c for pair in M_MID for c in pair]
    seeds, m = matrix(y, conds)
    if not seeds:
        return dict(n=0, verdict="нет данных")
    mild = m[:, 0::2].mean(axis=1)
    harsh = m[:, 1::2].mean(axis=1)
    mean, lo, hi = boot_ci(mild - harsh)
    if hi < -K4_MIN_DIFF:
        v = "мягче хуже"
    elif lo > K4_MIN_DIFF:
        v = "мягче лучше"
    elif lo > -K4_EQUIV and hi < K4_EQUIV:
        v = "тяжесть не решает"
    else:
        v = "не определено"
    return dict(n=len(seeds), s_mild=float(mild.mean()), s_harsh=float(harsh.mean()),
                diff=mean, ci=[lo, hi], min_diff=K4_MIN_DIFF, equiv=K4_EQUIV,
                predicted="мягче хуже", verdict=v)


def check_frozen(y):
    """Проверка F: без обучения спасения нет. Не гипотеза, а условие годности."""
    col = y.get(F_COND, {})
    k = int(sum(col.values()))
    return dict(n=len(col), rescued=k,
                verdict=("чисто" if k == 0 else "есть спасение без обучения: отдельная находка"))


CRITERIA = dict(K1=k1_dose_control, K2=k2_heterogeneity, K3=k3_variation,
                K4=k4_severity, F=check_frozen)


def evaluate(y):
    return {name: fn(y) for name, fn in CRITERIA.items()}


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_fmt(x)}" for k, x in v.items()) + "}"
    return str(v)


def _report(y, rows, path):
    print(f"{path}: строк {len(rows)}, семян в таблице {len(next(iter(y.values()))) if y else 0}")
    print("доля спасённых по условиям:")
    for c in sorted(y, key=lambda c: (c[0], float(c.split('_')[1][1:]))):
        col = y[c]
        print(f"  {c:9s} {sum(col.values()):3d}/{len(col):3d} = {sum(col.values()) / len(col):.2f}")
    res_all = evaluate(y)
    for name, res in res_all.items():
        print(f"\n{name}: {res.get('verdict')}")
        for k, v in res.items():
            if k != "verdict":
                print(f"    {k}: {_fmt(v)}")
    noise = describe_noise(y)
    print("\nчасть E (описательно):")
    for name, res in noise.items():
        print(f"  {name}: {_fmt(res)}")
    return res_all, noise


def main():
    """Без флагов: описательный разбор любого файла (пилот). С --confirm:
    единственное подтверждающее чтение. Оно выполняется, только когда протокол
    заморожен и посчитаны все N_CONFIRM годных семян, и пишет вердикты в
    runs/n4/reading_n4.json; второй раз поверх не пишет."""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    confirm = "--confirm" in sys.argv
    root = Path(__file__).resolve().parent.parent
    path = args[0] if args else str(root / "runs/n4/protocol_n4.jsonl")
    if not Path(path).exists():
        sys.exit(f"нет файла данных: {path}")
    y, rows = load_table(path)
    if not confirm:
        _report(y, rows, path)
        return
    sys.path.insert(0, str(root))
    from sim.protocol_n4 import PROTOCOL, SEED_FIRST, N_CONFIRM, conditions
    reading = root / "runs/n4/reading_n4.json"
    if "draft" in PROTOCOL or not (root / "PREREGISTRATION_N4.md").exists():
        sys.exit("протокол не заморожен: подтверждающее чтение не выполняется")
    if reading.exists():
        sys.exit(f"чтение уже выполнено: {reading}. Второго чтения протокол не допускает.")
    table, info = confirmatory_table(rows, list(conditions()), SEED_FIRST, N_CONFIRM)
    print(f"годных семян {info['valid']}, нужно {N_CONFIRM}; исключены {info['excluded']}; "
          f"недосчитаны {info['partial']}; пропуски {info['gaps']}")
    if table is None:
        sys.exit("чтение не выполняется: данных меньше, чем объявлено")
    res_all, noise = _report(table, rows, path)
    json.dump(dict(protocol=PROTOCOL, seeds=info, criteria=res_all, noise=noise),
              open(reading, "w"), ensure_ascii=False, indent=1)
    print(f"\nчтение записано: {reading}")


if __name__ == "__main__":
    main()
