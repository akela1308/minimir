"""C.4: инфраструктура теста порядка развития (решающий критерий этапа 3).

Интернализация по Выготскому требует, чтобы у агента момент, когда его метки
начинают влиять на ДРУГИХ, наступал РАНЬШЕ момента, когда его собственные
метки начинают влиять на НЕГО САМОГО (STAGE3_DESIGN §3).

Меряем две кривые как функцию возраста агента:
  SELF(w)  = MI(агент на своей метке; его действие) в возрастном окне w
             — своя метка влияет на своё поведение;
  OTHER(w) = сдвиг поведения ДРУГИХ, стоящих на метке автора возраста w,
             относительно базовой линии (не на метке) — метки автора влияют
             на других.
Момент появления функции = первое окно, где MI устойчиво превышает контроль
подменой (перестановка on/off-метки).

ОБЯЗАТЕЛЬНЫЙ контроль на confound: порядок может определяться не развитием,
а тем, что в юности агент чаще встречает других. Считаем плотность контактов
по возрасту и проверяем, не объясняет ли она порядок.

Считаем и кросс-секционно (пул по возрастным окнам через всю популяцию),
и лонгитюдно (по долгоживущим агентам). База метки sparse -> вероятен провал
прибора (границы провала §9.5): сообщаем объёмы сэмплов честно.
"""
import json
import numpy as np
from sim import Config, Engine
from sim.metrics import mi_from_hist

SEED = 1
WARM = 20000          # фаза 0: учатся кормиться, знаки/социалка выключены
MEASURE = 40000       # фаза 1-2: знаки и социалка включены
WSIZE = 200           # размер возрастного окна, тиков
NW = 16               # число окон (до 3200 тиков)
MARK_COST = 0.5

cfg = Config(seed=SEED, signs=False, social=True, social_from_tick=WARM,
             hebbian=True, recognition=True, mark_cost=MARK_COST,
             action_noise=0.02, track_individual=False)
eng = Engine(cfg)
eng.run(WARM)
eng.cfg.signs = True                 # включаем знаки на выжившей популяции

# аккумуляторы (кросс-секционные)
self_on = np.zeros((NW, 8), dtype=np.int64)   # действие | на своей метке, возраст автора=свой
self_off = np.zeros((NW, 8), dtype=np.int64)  # действие | не на метке, тот же возраст
other_on = np.zeros((NW, 8), dtype=np.int64)  # действие читателя | на метке автора возраста w
other_off = np.zeros(8, dtype=np.int64)       # действие читателя | не на метке (общая база)
contact_sum = np.zeros(NW)                     # сумма соседей по возрасту
contact_cnt = np.zeros(NW)
agentticks = np.zeros(NW, dtype=np.int64)

# лонгитюдно: по агентам с длинной жизнью — своя метка -> действие по возрасту
self_by_agent = {}   # key (slot,birth) -> (NW,2,8): on/off × action

for _ in range(MEASURE):
    if not eng.step():
        break
    ids = eng._last_ids
    if ids.size == 0:
        continue
    act = eng._last_act
    age = eng.pop.age[ids]
    wbin = np.clip(age // WSIZE, 0, NW - 1)
    present = getattr(eng, "_ctx_present", None)
    if present is None:
        continue
    aid = eng._ctx_author_id
    aage = eng._ctx_author_age
    on_own = present & (aid == ids)
    on_other = present & (aid >= 0) & (aid != ids)
    off = ~present

    # плотность контактов по возрасту (соседи в 3x3 минус сам)
    dens = eng._density(ids) - 1
    np.add.at(contact_sum, wbin, dens)
    np.add.at(contact_cnt, wbin, 1)
    np.add.at(agentticks, wbin, 1)

    # SELF: своя метка -> действие, по возрасту читателя(=автора)
    np.add.at(self_on, (wbin[on_own], act[on_own]), 1)
    np.add.at(self_off, (wbin[off], act[off]), 1)

    # OTHER: метка автора возраста w -> действие ДРУГОГО читателя
    awin = np.clip((aage[on_other] // WSIZE).astype(np.int64), 0, NW - 1)
    np.add.at(other_on, (awin, act[on_other]), 1)
    np.add.at(other_off, act[off], 1)

    # лонгитюдно
    bt = eng.pop.birth_tick
    for j in np.flatnonzero(present | off).tolist():
        s = int(ids[j])
        key = (s, int(bt[s]))
        h = self_by_agent.get(key)
        if h is None:
            h = np.zeros((NW, 2, 8), dtype=np.int32)
            self_by_agent[key] = h
        wj = int(wbin[j])
        if on_own[j]:
            h[wj, 1, act[j]] += 1
        elif off[j]:
            h[wj, 0, act[j]] += 1


def curve_mi(on_rows, off_ref):
    """MI(on/off; действие) по каждому возрастному окну. off_ref — базовая
    строка (не на метке). Возвращает список mi_corrected или None."""
    out = []
    for w in range(NW):
        if on_rows.ndim == 2:
            row1 = on_rows[w]
            row0 = off_ref[w] if off_ref.ndim == 2 else off_ref
        h = np.stack([row0, row1]).astype(np.int64)
        r = mi_from_hist(h)
        out.append(dict(w=w, age=w * WSIZE, mi=r.get("mi_corrected_bits"),
                        samples=int(h.sum()), on_samples=int(row1.sum())))
    return out


self_curve = curve_mi(self_on, self_off)
other_curve = curve_mi(other_on, other_off)
contact = [float(contact_sum[w] / contact_cnt[w]) if contact_cnt[w] else None
           for w in range(NW)]


def first_onset(curve, thr=0.005, min_samples=1000):
    for c in curve:
        if c["mi"] is not None and c["on_samples"] >= min_samples and c["mi"] > thr:
            return c["age"]
    return None

onset_self = first_onset(self_curve)
onset_other = first_onset(other_curve)

print(f"агентов прослежено (лонгит.): {len(self_by_agent)}")
print(f"\n{'возраст':>8} {'SELF MI':>9} {'on N':>8} {'OTHER MI':>9} {'on N':>8} {'контакты':>9}")
for w in range(NW):
    s, o = self_curve[w], other_curve[w]
    sm = f"{s['mi']:.4f}" if s["mi"] is not None else "—"
    om = f"{o['mi']:.4f}" if o["mi"] is not None else "—"
    ct = f"{contact[w]:.2f}" if contact[w] is not None else "—"
    print(f"{w*WSIZE:>8} {sm:>9} {s['on_samples']:>8} {om:>9} {o['on_samples']:>8} {ct:>9}")

print(f"\nмомент появления SELF (влияние своей метки на себя): {onset_self}")
print(f"момент появления OTHER (влияние своей метки на других): {onset_other}")
if onset_self is not None and onset_other is not None:
    verdict = ("ИНТЕРНАЛИЗАЦИЯ (other раньше self)" if onset_other < onset_self
               else "инстинкт/одновременно" if onset_other == onset_self
               else "self раньше other (не интернализация)")
else:
    verdict = "ПОРЯДОК НЕИЗМЕРИМ (недостаточно сэмплов на метках) — границы провала §9.5"
print(f"вердикт: {verdict}")

out = dict(self_curve=self_curve, other_curve=other_curve,
           contact_by_age=contact, onset_self=onset_self, onset_other=onset_other,
           verdict=verdict, n_longitudinal=len(self_by_agent),
           total_mark_reads=int(self_on.sum() + other_on.sum()))
with open("runs/c4_devorder.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
