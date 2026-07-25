"""Анализ блока B: фазовый переход кооперации по изобилию + confound.

Читает runs/b_sweep.jsonl. Строит долю кооперации как функцию regrowth
(ищем РЕЗКИЙ переход, а не плавный тренд, Requejo & Camacho). Сравнивает
популяционную и внутриагентную корреляцию «голод vs кооперация».
"""
import json
import numpy as np

rows = []
with open("runs/b_sweep.jsonl") as f:
    for line in f:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

regrowths = sorted(set(r["regrowth"] for r in rows if not r.get("error")))
print(f"{'regrowth':>9} {'coop_rate':>10} {'sd':>7} {'give_fr':>8} {'take_fr':>8} "
      f"{'pop_corr':>9} {'within_corr':>11} {'годных':>7} {'вымерло':>8} {'потолок':>8}")
agg = []
for r in regrowths:
    rs = [x for x in rows if x.get("regrowth") == r and not x.get("error")]
    valid = [x for x in rs if x.get("extinct") is None and not x.get("hit_ceiling")]
    ext = sum(1 for x in rs if x.get("extinct") is not None)
    ceil = sum(1 for x in rs if x.get("hit_ceiling"))
    crs = [x["coop_rate"] for x in valid if x.get("coop_rate") is not None]
    gv = [x["give_frac"] for x in valid]
    tk = [x["take_frac"] for x in valid]
    pc = [x["pop_corr_energy"] for x in valid if x.get("pop_corr_energy") is not None]
    wc = [x["within_corr_energy"] for x in valid if x.get("within_corr_energy") is not None]
    row = dict(regrowth=r, coop_rate=float(np.mean(crs)) if crs else None,
               coop_sd=float(np.std(crs)) if len(crs) > 1 else 0.0,
               give_frac=float(np.mean(gv)) if gv else None,
               take_frac=float(np.mean(tk)) if tk else None,
               pop_corr=float(np.mean(pc)) if pc else None,
               within_corr=float(np.mean(wc)) if wc else None,
               n_valid=len(valid), extinct=ext, ceiling=ceil)
    agg.append(row)
    cr = f"{row['coop_rate']:.3f}" if row["coop_rate"] is not None else "—"
    sd = f"{row['coop_sd']:.3f}"
    gf = f"{row['give_frac']:.4f}" if row["give_frac"] is not None else "—"
    tf = f"{row['take_frac']:.4f}" if row["take_frac"] is not None else "—"
    pcs = f"{row['pop_corr']:+.3f}" if row["pop_corr"] is not None else "—"
    wcs = f"{row['within_corr']:+.3f}" if row["within_corr"] is not None else "—"
    print(f"{r:>9} {cr:>10} {sd:>7} {gf:>8} {tf:>8} {pcs:>9} {wcs:>11} "
          f"{row['n_valid']:>7} {ext:>8} {ceil:>8}")

with open("runs/analyze_b.json", "w") as f:
    json.dump(agg, f, ensure_ascii=False, indent=1)

# резкость перехода: максимальный скачок coop_rate между соседними regrowth
crv = [(a["regrowth"], a["coop_rate"]) for a in agg if a["coop_rate"] is not None]
if len(crv) >= 2:
    jumps = [(crv[i][0], crv[i+1][0], crv[i+1][1]-crv[i][1]) for i in range(len(crv)-1)]
    biggest = max(jumps, key=lambda j: abs(j[2]))
    print(f"\nмаксимальный скачок coop_rate: {biggest[2]:+.3f} между regrowth "
          f"{biggest[0]} и {biggest[1]}")
    print("резкий переход" if abs(biggest[2]) > 0.2 else
          "плавный тренд или отсутствие перехода")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = [a["regrowth"] for a in agg]
    cr = [a["coop_rate"] if a["coop_rate"] is not None else np.nan for a in agg]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(x, cr, "o-", color="#37b")
    ax1.axhline(0.5, ls="--", c="gray", lw=1)
    ax1.set_xlabel("regrowth (изобилие ->)"); ax1.set_ylabel("доля кооперации (give)")
    ax1.set_title("B: фазовый переход кооперации по изобилию")
    ax1.grid(alpha=0.3)
    pc = [a["pop_corr"] if a["pop_corr"] is not None else np.nan for a in agg]
    wc = [a["within_corr"] if a["within_corr"] is not None else np.nan for a in agg]
    ax2.plot(x, pc, "s-", label="популяционная corr")
    ax2.plot(x, wc, "o-", label="внутриагентная corr")
    ax2.axhline(0, ls="--", c="gray", lw=1)
    ax2.set_xlabel("regrowth"); ax2.set_ylabel("corr(энергия; доля give)")
    ax2.set_title("B: голод vs кооперация — confound")
    ax2.legend(fontsize=8); ax2.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("runs/figures/b_phase.png", dpi=130)
    print("график: runs/figures/b_phase.png")
except Exception as e:
    print("график пропущен:", e)
