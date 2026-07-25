"""C.3: калибровка метрик знака на рукописных политиках.

Без калибровки метрики результаты этапа 3 интерпретировать нельзя. Три
политики с заранее известным ответом (signs=True):
  * mark_always — метить всегда, содержание — шум: MI(состояние; содержание)
    должна быть ~0 (знак есть, смысла нет);
  * mark_when_hungry_follow_own — метить при голоде (содержание кодирует
    голод) и реагировать на свою метку: MI(состояние; содержание) высокая,
    самонаправленное использование задано руками — верхняя граница;
  * ignore_marks — метки игнорировать: нулевой уровень, меток нет.

Ручные политики не размножаются -> меряем в окне до вымирания основателей
(пропуск 300, окно 2500).
"""
import json
from sim import Config, Engine, metrics

SEED = 1
SKIP = 300
MEASURE = 2500
POLICIES = ["mark_always", "mark_when_hungry_follow_own", "ignore_marks"]

rows = []
for pol in POLICIES:
    cfg = Config(seed=SEED, signs=True, policy=pol, track_individual=True)
    eng = Engine(cfg)
    eng.run(SKIP)
    eng.reset_metrics(); eng.reset_individual()
    eng.run(MEASURE)
    sm = metrics.sign_metrics(eng)
    rows.append(dict(policy=pol, pop=eng.pop.count,
                     mark_rate=sm["mark_rate"], marks_made=sm["marks_made"],
                     mi_state_content=sm["mi_state_content_bits"],
                     mi_samples=sm["mi_samples"],
                     freshness=sm["own_mark_freshness"],
                     own_read_fraction=sm["own_read_fraction"]))
    r = rows[-1]
    print(f"{pol:>30}: mark_rate={r['mark_rate']:.4f} marks={r['marks_made']} "
          f"MI(s;c)={r['mi_state_content']} (N={r['mi_samples']}) "
          f"fresh={None if r['freshness'] is None else round(r['freshness'],1)} "
          f"own_read={r['own_read_fraction']}", flush=True)

with open("runs/c3_signcalib.json", "w") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

print("\nОжидание: mark_always MI≈0, mark_when_hungry MI>0 (верхняя граница), "
      "ignore_marks меток нет.")
