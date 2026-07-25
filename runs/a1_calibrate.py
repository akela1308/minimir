"""A.1 (часть 1): калибровка ВНУТРИАГЕНТНОЙ метрики.

Популяционную метрику уже калибровали (threshold@40 -> 0.586, random -> 0).
Внутриагентная становится главной (правка A.2), поэтому её надо откалибровать
теми же контролями: threshold с порогами 20..70 (положительный, зависимость
от состояния встроена руками) и random (отрицательный, ноль).

Тонкость: ручные политики не размножаются (кормятся лишь до сытости, до
порога размножения 80 не дотягивают), поэтому основатели доживают до
max_age=3000 и разом вымирают. Меряем в окне ДО вымирания: пропускаем первые
300 тиков (транзиент расстановки) и меряем до 2800. Основатели живут всё окно,
набирая ~2500 решений каждый — выше порога отбора агентов.
"""
import json
import numpy as np
from sim import Config, Engine, metrics

SEED = 1
SKIP = 300
MEASURE = 2500

def run_policy(policy, threshold=None, signs=False):
    over = dict(seed=SEED, policy=policy, track_individual=True, signs=signs)
    if threshold is not None:
        over["policy_threshold"] = float(threshold)
    eng = Engine(Config(**over))
    eng.run(SKIP)
    eng.reset_metrics(); eng.reset_individual()
    eng.run(MEASURE)
    pop_mi = metrics.behaviour_depends_on_energy(eng)
    wa = metrics.within_agent_dependence(eng)
    occ = metrics.energy_occupancy(eng)
    return dict(policy=policy, threshold=threshold,
                pop_mi=pop_mi.get("mi_corrected_bits"),
                within_mi=wa.get("mean_mi_bits"), within_sd=wa.get("sd"),
                within_n=wa.get("n_agents"),
                occupied_deciles=occ["occupied_deciles"], pop=eng.pop.count)

rows = []
for thr in (20, 30, 40, 50, 60, 70):
    rows.append(run_policy("threshold", thr))
    print(f"threshold@{thr}: pop_MI={rows[-1]['pop_mi']}, "
          f"within_MI={rows[-1]['within_mi']} (n={rows[-1]['within_n']}, "
          f"занято дец. {rows[-1]['occupied_deciles']})", flush=True)
rows.append(run_policy("random"))
print(f"random: pop_MI={rows[-1]['pop_mi']}, within_MI={rows[-1]['within_mi']} "
      f"(n={rows[-1]['within_n']})", flush=True)
rows.append(run_policy("evolved"))
print(f"evolved: pop_MI={rows[-1]['pop_mi']}, within_MI={rows[-1]['within_mi']} "
      f"(n={rows[-1]['within_n']})", flush=True)

with open("runs/a1_calibrate.json", "w") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

# график чувствительности внутриагентной метрики
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    thr = [r for r in rows if r["policy"] == "threshold"]
    x = [r["threshold"] for r in thr]
    yw = [r["within_mi"] if r["within_mi"] is not None else np.nan for r in thr]
    yp = [r["pop_mi"] if r["pop_mi"] is not None else np.nan for r in thr]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, yw, marker="o", label="внутриагентная")
    ax.plot(x, yp, marker="s", label="популяционная")
    rnd = [r for r in rows if r["policy"] == "random"][0]
    ax.axhline(rnd["within_mi"] or 0, ls="--", c="gray", lw=1,
               label=f"random within={rnd['within_mi']:.3f}" if rnd["within_mi"] else "random")
    ax.set_xlabel("порог политики threshold, % энергии")
    ax.set_ylabel("MI(энергия; действие), бит")
    ax.set_title("A.1 калибровка: чувствительность метрик по порогу")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("runs/figures/a1_calibrate.png", dpi=130)
    print("график: runs/figures/a1_calibrate.png")
except Exception as e:
    print("график пропущен:", e)
