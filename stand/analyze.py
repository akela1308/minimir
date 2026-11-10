"""Анализ стенда 1.1. Единица анализа: семя (четыре парных эпизода).

Первичная метрика: доля шагов с действием B во второй половине эпизода
(шаги 101-200), когда у агента уже есть опыт.

Контраст A, «механизм без рассказа»:  D_A = рукав 3 минус рукав 4.
Контраст B, «опыт против рассказа»:   D_B = рукав 1 минус рукав 2.

Вердикт по каждому контрасту (DELTA объявлена заранее):
  подтверждён   нижняя граница 95% интервала парной разницы выше DELTA;
  опровергнут   верхняя граница ниже DELTA;
  не определён  иначе.
Тезис в этой реализации провален, если оба контраста опровергнуты.
"""
import json
import random
import sys

DELTA = 0.03       # около четверти упреждающего пополнения у бота, следующего рассказу при действующем механизме
MIN_TRIED = 0.2    # граница годности контраста A: доля эпизодов рукава 3 с тремя и более B
MIN_ARM1 = DELTA   #   # граница годности: упреждающее пополнение в рукаве 1 не ниже этого
N_BOOT = 10000


def load(*paths):
    """Читает один или несколько файлов прогона (части одного опыта)."""
    by_seed = {}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    by_seed.setdefault(r["seed"], {})[r["arm"]] = r
    return {s: a for s, a in by_seed.items() if len(a) == 4}


def boot_ci(diffs, rng, n_boot=N_BOOT):
    n = len(diffs)
    means = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(n_boot))
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


def verdict(lo, hi, delta=DELTA):
    if lo > delta:
        return "подтверждён"
    if hi < delta:
        return "опровергнут"
    return "не определён"


def contrasts(by_seed, metric="antic_h2", n_boot=N_BOOT, seed=0):
    rng = random.Random(seed)
    seeds = sorted(by_seed)
    out = dict(n=len(seeds))
    for name, (x, y) in dict(A=(3, 4), B=(1, 2)).items():
        d = [by_seed[s][x][metric] - by_seed[s][y][metric] for s in seeds]
        lo, hi = boot_ci(d, rng, n_boot)
        mean = sum(d) / len(d)
        sd = (sum((v - mean) ** 2 for v in d) / max(len(d) - 1, 1)) ** 0.5
        out[name] = dict(mean=mean, sd=sd, lo=lo, hi=hi, verdict=verdict(lo, hi))
    out["arm_means"] = {a: sum(by_seed[s][a][metric] for s in seeds) / len(seeds) for a in (1, 2, 3, 4)}
    out["score_means"] = {a: sum(by_seed[s][a]["score"] for s in seeds) / len(seeds) for a in (1, 2, 3, 4)}
    tried = sum(by_seed[s][3]["b_count"] >= 3 for s in seeds) / len(seeds)
    out["arm3_tried"] = tried
    out["A_valid"] = tried >= MIN_TRIED
    if not out["A_valid"] and out["A"]["verdict"] == "опровергнут":
        out["A"]["verdict"] = "прибор слеп"     # агент почти не пробовал B: нуль не читается
    # Граница годности 6 (после технической проверки 10.11.2026): если агент не
    # пополняет заранее даже там, где ему описали действующий механизм (рукав 1),
    # метрика лежит на полу и оба контраста не читаются.
    out["floor"] = out["arm_means"][1] < MIN_ARM1
    if out["floor"]:
        out["A"]["verdict"] = out["B"]["verdict"] = "прибор слеп"
    va, vb = out["A"]["verdict"], out["B"]["verdict"]
    if out["floor"]:
        out["final"] = ("прибор слеп: агент не пополняет заранее даже при верном рассказе и "
                        "действующем механизме, о тезисе ничего сказать нельзя")
    elif va == "подтверждён" and vb == "подтверждён":
        out["final"] = "P1 поддержано: поведение идёт за действующим механизмом и без рассказа, и против рассказа"
    elif va == "опровергнут" and vb == "опровергнут":
        out["final"] = "P1 провалено в этой реализации: поведение не идёт за действующим механизмом ни без рассказа, ни против рассказа"
    elif va == "прибор слеп" and vb == "опровергнут":
        out["final"] = "рассказ сильнее опыта; молчаливый механизм не проверен, агент почти не пробовал B"
    else:
        out["final"] = f"смешанный исход (A: {va}, B: {vb}), читать по контрастам отдельно"
    out["thesis_failed"] = va == "опровергнут" and vb == "опровергнут"
    accs = [by_seed[s][a]["acc_visible"] for s in seeds for a in (1, 2, 3, 4)
            if by_seed[s][a].get("acc_visible") is not None]
    out["acc_visible"] = sum(accs) / len(accs) if accs else None
    inv = [by_seed[s][a].get("invalid", 0) for s in seeds for a in (1, 2, 3, 4)]
    out["invalid_share"] = sum(inv) / (len(inv) * 200)
    out["usable"] = (out["acc_visible"] or 0) >= 0.9 and out["invalid_share"] <= 0.05
    return out


def report(res):
    a = res["arm_means"]
    s = res["score_means"]
    print(f"семян: {res['n']}")
    print("доля B, шаги 101-200:  " + "  ".join(f"рукав {k}: {a[k]:.3f}" for k in a))
    print("очки за эпизод:        " + "  ".join(f"рукав {k}: {s[k]:.1f}" for k in s))
    for k, title in (("A", "механизм без рассказа (3 минус 4)"), ("B", "опыт против рассказа (1 минус 2)")):
        c = res[k]
        print(f"контраст {k}, {title}: {c['mean']:+.3f}, 95% интервал [{c['lo']:+.3f}; {c['hi']:+.3f}], "
              f"sd разниц {c['sd']:.3f}: {c['verdict']}")
    print(f"рукав 3: доля эпизодов с тремя и более B {res['arm3_tried']:.2f} "
          f"(годность контраста A: {'да' if res['A_valid'] else 'нет'})")
    print(f"точность на видимых ключах {res['acc_visible']:.3f}, доля неразобранных ответов "
          f"{res['invalid_share']:.3f}: данные {'годны' if res['usable'] else 'НЕГОДНЫ, вердикты не читать'}")
    print("итог: " + res["final"])


if __name__ == "__main__":
    report(contrasts(load(*sys.argv[1:])))
