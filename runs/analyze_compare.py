"""Анализ A.5 (главное сравнение) + A.3 (2σ шума из self-прогонов).

Читает runs/compare.jsonl. Применяет критерии годности (вымирание, потолок,
занято <4 децилей). Считает по обеим метрикам (внутриагентная — главная,
популяционная — исследовательская): среднее/sd/медиана, парный Уилкоксон
self vs shuffled (и neighbour/off), дельту Клиффа. 2σ межсидового разброса
берём из self-прогонов (A.3 выведен из тех же self-прогонов, а не отдельной
серией — экономия счёта на 2-ядерной машине; условие и длина те же).

Заявка подтверждается только при p<0.01 И превышении 2σ.
"""
import json
import sys
import numpy as np

PATH = sys.argv[1] if len(sys.argv) > 1 else "runs/compare.jsonl"
CONDS = ["self", "shuffled", "neighbour", "off"]

rows = []
with open(PATH) as f:
    for line in f:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

def valid(r):
    return (not r.get("error") and r.get("extinct") is None
            and not r.get("hit_ceiling") and (r.get("occupied_deciles") or 0) >= 4)

by = {c: sorted([r for r in rows if r.get("label") == c], key=lambda r: r["seed"])
      for c in CONDS}

# отчёт по годности
print("=== годность прогонов ===")
excl = {}
for c in CONDS:
    tot = len(by[c])
    ext = sum(1 for r in by[c] if r.get("extinct") is not None)
    ceil = sum(1 for r in by[c] if r.get("hit_ceiling"))
    occ = sum(1 for r in by[c] if (r.get("occupied_deciles") or 0) < 4 and r.get("extinct") is None)
    err = sum(1 for r in by[c] if r.get("error"))
    v = sum(1 for r in by[c] if valid(r))
    excl[c] = dict(total=tot, valid=v, extinct=ext, ceiling=ceil, low_occ=occ, error=err)
    print(f"  {c:>10}: годных {v}/{tot} (вымерло {ext}, потолок {ceil}, "
          f"мало децилей {occ}, ошибок {err})")

def stat(vals):
    v = np.array([x for x in vals if x is not None], float)
    if v.size == 0: return None
    return dict(n=int(v.size), mean=float(v.mean()),
                sd=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                median=float(np.median(v)))

def wilcoxon(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b)); a, b = a[ok], b[ok]
    if a.size < 5: return dict(n=int(a.size), p=None)
    try:
        from scipy.stats import wilcoxon as wx
        s, p = wx(a, b); return dict(n=int(a.size), stat=float(s), p=float(p))
    except Exception:
        return dict(n=int(a.size), p=None)

def cliffs(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b)); a, b = a[ok], b[ok]
    if not a.size or not b.size: return None
    gt = (a[:, None] > b[None, :]).sum(); lt = (a[:, None] < b[None, :]).sum()
    return float((gt - lt) / (a.size * b.size))

report = dict(exclusions=excl)
for metric in ("within_mi", "mi"):
    tag = "ВНУТРИАГЕНТНАЯ (главная)" if metric == "within_mi" else "популяционная (исслед.)"
    print(f"\n=== метрика: {metric} — {tag} ===")
    valid_by = {c: [r for r in by[c] if valid(r)] for c in CONDS}
    summ = {}
    for c in CONDS:
        s = stat([r.get(metric) for r in valid_by[c]])
        summ[c] = s
        if s:
            print(f"  {c:>10}: mean {s['mean']:.4f}  sd {s['sd']:.4f}  "
                  f"median {s['median']:.4f}  n={s['n']}")
    # 2σ из self
    self_sd = summ["self"]["sd"] if summ.get("self") else None
    two_sigma = 2 * self_sd if self_sd is not None else None
    print(f"  2σ межсидового разброса (из self): "
          f"{two_sigma:.4f}" if two_sigma is not None else "  2σ: н/д")
    # парные сравнения на ОБЩИХ валидных seed'ах
    base = {r["seed"]: r.get(metric) for r in valid_by["shuffled"]}
    cmp = {}
    for c in ("self", "neighbour", "off"):
        pairs = [(r.get(metric), base[r["seed"]]) for r in valid_by[c]
                 if r["seed"] in base and r.get(metric) is not None and base[r["seed"]] is not None]
        a = [p[0] for p in pairs]; b = [p[1] for p in pairs]
        w = wilcoxon(a, b); d = cliffs(a, b)
        diff = (np.mean(a) - np.mean(b)) if a else None
        exceeds = (two_sigma is not None and diff is not None and abs(diff) > two_sigma)
        confirmed = (w.get("p") is not None and w["p"] < 0.01 and exceeds)
        cmp[c] = dict(n=w["n"], p=w.get("p"), cliffs=d, mean_diff=diff,
                      exceeds_2sigma=bool(exceeds), confirmed=bool(confirmed))
        ps = f"p={w['p']:.4f}" if w.get("p") is not None else "p=н/д"
        print(f"  {c:>10} vs shuffled: {ps}, дельта Клиффа "
              f"{d:+.3f} " if d is not None else "", end="")
        print(f"| Δсред {diff:+.4f} {'>2σ' if exceeds else '<2σ'} "
              f"-> {'ПОДТВЕРЖДЕНО' if confirmed else 'не подтверждено'}"
              if diff is not None else "нет данных")
    report[metric] = dict(summary=summ, two_sigma=two_sigma, comparisons=cmp)

with open("runs/analyze_compare.json", "w") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)

# графики
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for metric in ("within_mi", "mi"):
        valid_by = {c: [r for r in by[c] if valid(r)] for c in CONDS}
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
        means = [np.nanmean([r.get(metric) for r in valid_by[c]] or [np.nan]) for c in CONDS]
        sds = [np.nanstd([r.get(metric) for r in valid_by[c]] or [np.nan]) for c in CONDS]
        ax1.bar(CONDS, means, yerr=sds, capsize=4,
                color=["#3b7", "#888", "#37b", "#ccc"])
        ax1.set_ylabel(f"MI, бит ({metric})")
        ax1.set_title(f"A.5 условия — {metric}")
        ax1.grid(alpha=0.3, axis="y")
        # парные линии self vs shuffled
        base = {r["seed"]: r.get(metric) for r in valid_by["shuffled"]}
        for r in valid_by["self"]:
            if r["seed"] in base and r.get(metric) is not None and base[r["seed"]] is not None:
                ax2.plot([0, 1], [base[r["seed"]], r.get(metric)], "o-", color="#37b", alpha=0.5)
        ax2.set_xticks([0, 1]); ax2.set_xticklabels(["shuffled", "self"])
        ax2.set_ylabel(f"MI, бит ({metric})")
        ax2.set_title("парные seed'ы: shuffled -> self")
        ax2.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fig.savefig(f"runs/figures/a5_compare_{metric}.png", dpi=130)
        print(f"график: runs/figures/a5_compare_{metric}.png")
except Exception as e:
    print("график пропущен:", e)
