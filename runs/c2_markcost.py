"""C.2: осмысленность метки и подбор mark_cost.

Проверяем, что канал знаков не вырождается ни в молчание, ни в равномерную
кашу. Свип mark_cost 0.1..2.0 (STAGE3_DESIGN §5.3, C.2), evolved-популяция,
signs=True. Меряем:
  * mark_rate — доля действий MARK;
  * MI(состояние; содержание метки) — метка о чём-то?
  * свежесть читаемых своих меток (возраст ~1 = обход к рекуррентности);
  * заполненность поля знаков (доля помеченных клеток) — «каша» при насыщении.
Цель: mark_cost, при котором метки ставятся, но поле не насыщается.
"""
import json
import numpy as np
from sim import Config, Engine, metrics

SEEDS = [1, 2, 3]
MARK_COSTS = [0.1, 0.25, 0.5, 1.0, 1.5, 2.0]
WARM = 8000
MEASURE = 8000

rows = []
for mc in MARK_COSTS:
    for seed in SEEDS:
        cfg = Config(seed=seed, signs=True, mark_cost=mc, track_individual=True)
        eng = Engine(cfg)
        eng.run(WARM)
        eng.reset_metrics(); eng.reset_individual()
        eng.run(MEASURE)
        sm = metrics.sign_metrics(eng)
        # заполненность поля: доля клеток с заметной меткой
        field = np.abs(eng.world.signs).sum(axis=2)
        filled = float((field > 1e-2).mean())
        rows.append(dict(mark_cost=mc, seed=seed, pop=eng.pop.count,
                         extinct=eng.extinct_at,
                         mark_rate=sm["mark_rate"], marks_made=sm["marks_made"],
                         mi_state_content=sm["mi_state_content_bits"],
                         freshness=sm["own_mark_freshness"],
                         own_read_fraction=sm["own_read_fraction"],
                         field_filled=filled))
        r = rows[-1]
        print(f"mark_cost={mc:>4}: seed{seed} mark_rate={r['mark_rate']:.4f} "
              f"MI(s;c)={r['mi_state_content']} fill={filled:.3f} "
              f"fresh={None if r['freshness'] is None else round(r['freshness'],1)}",
              flush=True)

with open("runs/c2_markcost.json", "w") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

print("\n=== сводка C.2 по mark_cost ===")
for mc in MARK_COSTS:
    rs = [r for r in rows if r["mark_cost"] == mc and r["extinct"] is None]
    if not rs:
        print(f"mark_cost={mc}: все вымерли"); continue
    mr = np.mean([r["mark_rate"] for r in rs])
    fill = np.mean([r["field_filled"] for r in rs])
    mis = [r["mi_state_content"] for r in rs if r["mi_state_content"] is not None]
    mi = np.mean(mis) if mis else None
    print(f"mark_cost={mc:>4}: mark_rate {mr:.4f}, поле {fill:.3f} заполнено, "
          f"MI(s;c) {mi if mi is None else round(mi,4)}")

# график
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = MARK_COSTS
    mr = [np.mean([r["mark_rate"] for r in rows if r["mark_cost"]==mc]) for mc in x]
    fill = [np.mean([r["field_filled"] for r in rows if r["mark_cost"]==mc]) for mc in x]
    fig, ax = plt.subplots(figsize=(8,4.5))
    ax.plot(x, mr, "o-", label="доля MARK")
    ax.plot(x, fill, "s-", label="заполненность поля")
    ax.set_xlabel("mark_cost"); ax.set_ylabel("доля")
    ax.set_title("C.2 метка vs стоимость: частота и насыщение поля")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("runs/figures/c2_markcost.png", dpi=130)
    print("график: runs/figures/c2_markcost.png")
except Exception as e:
    print("график пропущен:", e)
