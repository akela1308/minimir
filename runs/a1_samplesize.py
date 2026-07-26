"""A.1 (часть 2): сколько решений на агента нужно для устойчивой оценки MI.

Записываем упорядоченные по времени решения (дециль энергии; действие) для
долгоживущих агентов и считаем внутриагентную MI по ПЕРВЫМ N решениям при
N = 100, 200, 400, 800. Ищем минимальное N, при котором оценка перестаёт
зависеть от N — это войдёт в критерий отбора агентов.
"""
import json
import numpy as np
from sim import Config, Engine


def mi_corrected_small(h):
    """MI с поправкой на смещение БЕЗ порога n>=1000 из mi_from_hist:
    здесь весь смысл — поведение оценки при малых N (100..800)."""
    h = np.asarray(h, dtype=np.float64)
    n = h.sum()
    if n < 20:
        return None
    p = h / n
    pe = p.sum(axis=1, keepdims=True)
    pa = p.sum(axis=0, keepdims=True)
    denom = pe * pa
    nz = (p > 0) & (denom > 0)
    mi = float((p[nz] * np.log2(p[nz] / denom[nz])).sum())
    r = int((h.sum(axis=1) > 0).sum())
    c = int((h.sum(axis=0) > 0).sum())
    chance = (r - 1) * (c - 1) / (2 * n * np.log(2)) if r > 1 and c > 1 else 0.0
    return float(mi - chance)

SEED = 1
WARM = 40000          # прогрев/эволюция
MEASURE = 60000       # окно записи решений
NEED = 800            # максимум решений на агента (нам нужны первые 800)
NS = [100, 200, 400, 800]

cfg = Config(seed=SEED, track_individual=True)
eng = Engine(cfg)
eng.run(WARM)

# упорядоченные решения по агентам: ключ (slot, birth_tick) -> list of (bin, act)
streams = {}
for _ in range(MEASURE):
    if not eng.step():
        break
    ids = eng._last_ids; bins = eng._last_bins; act = eng._last_act
    bt = eng.pop.birth_tick
    for i in range(ids.size):
        s = int(ids[i])
        key = (s, int(bt[s]))
        lst = streams.get(key)
        if lst is None:
            lst = []
            streams[key] = lst
        if len(lst) < NEED:
            lst.append((int(bins[i]), int(act[i])))

# берём агентов, доживших до >= NEED решений
long_lived = [v for v in streams.values() if len(v) >= NEED]
print(f"агентов с >= {NEED} решений: {len(long_lived)} "
      f"(всего прослежено {len(streams)})", flush=True)

def mi_first_n(stream, n):
    h = np.zeros((10, 8), dtype=np.int64)
    for b, a in stream[:n]:
        h[b, a] += 1
    return mi_corrected_small(h)

rows = {}
for n in NS:
    vals = [mi_first_n(s, n) for s in long_lived]
    vals = [v for v in vals if v is not None]
    v = np.array(vals, float)
    rows[n] = dict(n_samples=n, n_agents=int(v.size),
                   mean=float(v.mean()), sd=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                   median=float(np.median(v)),
                   sem=float(v.std(ddof=1)/np.sqrt(v.size)) if v.size > 1 else 0.0)

print(f"\n{'N решений':>10} {'агентов':>8} {'MI сред.':>10} {'sd':>8} {'SEM':>8}")
prev = None
for n in NS:
    r = rows[n]
    delta = "" if prev is None else f"  Δ к N/2: {r['mean']-prev:+.4f}"
    print(f"{n:>10} {r['n_agents']:>8} {r['mean']:>10.4f} {r['sd']:>8.4f} {r['sem']:>8.4f}{delta}")
    prev = r["mean"]

# критерий: минимальное N, при котором |MI(N) - MI(N/2)| < SEM(N)
stable_n = None
for i in range(1, len(NS)):
    n = NS[i]
    if abs(rows[n]["mean"] - rows[NS[i-1]]["mean"]) < rows[n]["sem"] + 1e-9:
        stable_n = n
        break
print(f"\nоценка стабилизируется к N = {stable_n} "
      f"(|ΔMI| < SEM). Порог отбора агентов = min_samples {stable_n or NS[-1]}.")

with open("runs/a1_samplesize.json", "w") as f:
    json.dump(dict(rows=rows, stable_n=stable_n, n_long_lived=len(long_lived)),
              f, ensure_ascii=False, indent=1)
