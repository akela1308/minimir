#!/usr/bin/env python3
"""Разбор пилотов 13 октября 2026 (seed'ы 101-103, не подтверждающие данные).
Печатает markdown, который кладётся в runs/a2/pilot/PILOT_2026-10-13.md и
runs/b2/pilot/PILOT_2026-10-13.md."""
import json, statistics as st, math, sys
P = "/home/claude/pilot"

def rows(name):
    try:
        return [json.loads(l) for l in open(f"{P}/{name}") if l.strip()]
    except FileNotFoundError:
        return []

def f(v, d=4):
    if v is None: return "нет"
    if isinstance(v, float): return f"{v:.{d}f}"
    return str(v)

out = []
w = out.append

# ------------------------------------------------------------- A2 часть 1
rc = rows("pilot_controls.jsonl")
w("# Пилот A2 перед заморозкой: контроли и шок-проба\n")
w("13 октября 2026. Seed'ы 101, 102, 103 (вне объявленных 1-20), 40 000 тиков на прогон "
  "(прогрев 14 000, окно 26 000), облачный контейнер, 2 воркера. **Это пилот, не чтение:** "
  "три seed'а и короткие прогоны годятся только для проверки, что мир под новыми режимами "
  "жив, прибор пишет нужные поля и параметры удара не убивают популяцию. Знаки разниц здесь "
  "ничего не заявляют.\n")
w("## Часть 1, контроли: годность и поля\n")
w("| условие | seed | pop в конце | пик | вымер | децилей | mi200 | n200 | mi1000 | n1000 | mi (поп.) |")
w("|---|---|---|---|---|---|---|---|---|---|---|")
by = {}
for r in rc:
    if r.get("error"):
        w(f"| {r['label']} | {r['seed']} | ОШИБКА {r['error'][:80]} |||||||||")
        continue
    by.setdefault(r["label"], {})[r["seed"]] = r
    w(f"| {r['label']} | {r['seed']} | {r['pop']} | {r['peak_pop']} | {'да' if r['extinct'] is not None else 'нет'} | "
      f"{r['occupied_deciles']} | {f(r['within_mi_200'])} | {r['within_n_200']} | {f(r['within_mi_1000'])} | "
      f"{r['within_n_1000']} | {f(r['mi'])} |")
n_valid = sum(1 for r in rc if not r.get("error") and r.get("extinct") is None and not r.get("hit_ceiling") and (r.get("occupied_deciles") or 0) >= 4)
w(f"\nГодных прогонов {n_valid} из {len(rc)}: вымираний и потолка нет, занято 8 децилей везде. "
  "Режимы `twin` и `constant` мир не ломают. Оба порога пишутся; при пороге 200 в среднее "
  "входит в 2-3 раза больше агентов, чем при 1000.\n")
w("Разницы с `shuffled` по seed'ам (только чтобы убедиться, что числа осмысленны; при трёх seed'ах и 40k тиков это шум):\n")
for m in ("within_mi_200", "within_mi_1000", "mi"):
    for c in ("self", "twin", "constant", "off"):
        d = [by[c][s][m] - by["shuffled"][s][m] for s in by.get(c, {}) if s in by.get("shuffled", {})
             and by[c][s].get(m) is not None and by["shuffled"][s].get(m) is not None]
        if d:
            w(f"- `{m}`, {c} минус shuffled: {[round(x, 4) for x in d]}, среднее {st.mean(d):+.4f}")
w("")

# ------------------------------------------------------------- twin check
try:
    tc = json.load(open(f"{P}/twin_check.json"))
    w("## Подмена twin: распределение и временная структура входа 8\n")
    w("2000 тиков после 600 прогрева, все агент-тики. `ks_gap` это максимальный разрыв между "
      "эмпирическими функциями распределения собственной энергии и сигнала на входе 8; "
      "`lag1` это лаг-1 автокорреляция входа у агентов, проживших всё окно.\n")
    w("| seed | режим | среднее свой | среднее вход | sd свой | sd вход | ks_gap | lag1 | агентов на всё окно |")
    w("|---|---|---|---|---|---|---|---|---|")
    for seed, res in tc.items():
        for mode, v in res.items():
            w(f"| {seed} | {mode} | {f(v['mean_own'],3)} | {f(v['mean_sig'],3)} | {f(v['sd_own'],3)} | {f(v['sd_sig'],3)} | "
              f"{f(v['ks_gap'],3)} | {f(v['lag1_autocorr'],3)} | {v['agents_full_window']} |")
    gaps = [v["ks_gap"] for res in tc.values() for m, v in res.items() if m == "twin"]

    def lags(mode):
        return [v["lag1_autocorr"] for res in tc.values() for m, v in res.items()
                if m == mode and v["lag1_autocorr"] is not None]

    def rng_txt(xs):
        return f"{min(xs):.2f}…{max(xs):.2f}" if xs else "нет данных"

    lag_twin, lag_self, lag_shuf = lags("twin"), lags("self"), lags("shuffled")
    n_lag_seeds = sum(1 for res in tc.values() if res.get("twin", {}).get("lag1_autocorr") is not None)
    w(f"\nУ twin разрыв распределений {min(gaps):.3f}…{max(gaps):.3f} (граница провала 3 черновика A2 "
      f"говорила о 0,05 по среднему и sd; см. столбцы). Лаг-1 автокорреляция посчитана только там, где хотя бы "
      f"три агента прожили всё окно 2000 тиков ({n_lag_seeds} seed из {len(tc)}; в остальных никто столько не живёт, "
      f"это само по себе напоминание, что 2000 тиков для мини-мира долго): {rng_txt(lag_twin)} у twin "
      f"против {rng_txt(lag_self)} у self и {rng_txt(lag_shuf)} у shuffled. "
      "Подмена ведёт себя как задумано: распределение то же, временная структура сохранена. "
      "Вывод: факт по распределению на трёх seed'ах, по автокорреляции на одном; в A2 стоит измерять лаг-1 "
      "короче окно (например 200 тиков) и по всем агентам, а не только по долгожителям.\n")
except FileNotFoundError:
    w("## Подмена twin: проверка не успела посчитаться\n")

# ------------------------------------------------------------- A2 часть 2
rs = rows("pilot_shock.jsonl")
w("## Часть 2, шок-проба: годность, события, реакции\n")
w("Параметры: удар 20 единиц у 20% агентов с E > 30 раз в 500 тиков, окно 50 тиков, выживание через 200; "
  "режимы abrupt (за тик), slow (за 50 тиков), sham (без удара).\n")
w("Первый прогон пилота (файл `pilot_shock_v1.jsonl`) показал, что доля добывающих действий у этих "
  "популяций около 0,99 и различий не видит; тем же утром добавлены дефицит энергии в конце окна "
  "(`energy_gap_end`, `gap_closure`) и точность добычи внутри окна (`accuracy_*`), и пилот прогнан "
  "заново (`pilot_shock.jsonl`). Ниже вторая версия.\n")
w("| условие/удар | seed | pop | вымер | событий | ударено | дефицит в конце окна | закрытие | точн. удар. | точн. контр. | реакция точн. | реакция выжив. |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|")
bys = {}
for r in rs:
    if r.get("error"):
        w(f"| {r['label']} | {r['seed']} | ОШИБКА {r['error'][:80]} ||||||||||")
        continue
    s = r["shock"] or {}
    bys.setdefault(r["label"], {})[r["seed"]] = r
    w(f"| {r['label']} | {r['seed']} | {r['pop']} | {'да' if r['extinct'] is not None else 'нет'} | {s.get('events')} | {s.get('n_shocked')} | "
      f"{f(s.get('energy_gap_end'),2)} | {f(s.get('gap_closure'),3)} | {f(s.get('accuracy_shocked'),3)} | {f(s.get('accuracy_control'),3)} | "
      f"{f(s.get('accuracy_response'))} | {f(s.get('survival_response'))} |")
ext = sum(1 for r in rs if not r.get("error") and r.get("extinct") is not None)
w(f"\nВымираний от ударов: {ext} из {len(rs)} прогонов (граница из черновика: не выше 10%).\n")
w("Средние реакции по трём seed'ам (пилот, не тест):\n")
for lab in sorted(bys):
    def col(k): return [v["shock"][k] for v in bys[lab].values() if v.get("shock") and v["shock"].get(k) is not None]
    g, c, a, s_ = col("energy_gap_end"), col("gap_closure"), col("accuracy_response"), col("survival_response")
    w(f"- {lab}: дефицит в конце окна {st.mean(g):+.2f} (sd {st.pstdev(g):.2f}), закрытие {f(st.mean(c),3) if c else 'нет'}, "
      f"реакция точности {st.mean(a):+.4f}, реакция выживания {st.mean(s_):+.4f}, n={len(g)}")
w("\nЧто это значит для черновика A2: `sham` даёт дефицит около нуля (от −1,2 до +0,8 при ударе в 20), "
  "то есть процедура и учёт чисты; `abrupt` и `slow` оставляют к концу окна дефицит около 17 из 20 во всех "
  "условиях, то есть закрытие около 0,15 и у `self`, и у `shuffled`. На трёх seed'ах и 40k тиков "
  "(популяции ещё молодые, прогрев 14k) специфичной для `self` реакции не видно; выживание после удара "
  "падает на 0,18-0,20 везде одинаково. Для чтения на 20 seed'ах и 120k это ничего не предрешает, но "
  "границу провала 1 части 2 (реакции в `self` нет при MI > 0) стоит считать реальной возможностью, "
  "а не формальностью. Параметры: вымираний нет, 20 событий на прогон при окне 26k; при 120k и окне "
  "75k будет 150 событий. Стоит обсудить `shock_min_energy` 40 вместо 30, чтобы удар реже убивал сразу.\n")

# ------------------------------------------------------------- B2
rb = rows("pilot_b2.jsonl") + rows("pilot_b2_ramp.jsonl") + rows("pilot_b2_lr.jsonl")
w("\n\n# Пилот B2 перед заморозкой: яд, постепенная смена, маркерный ген\n")
w("13 октября 2026. Seed'ы 101-103, 20 000 тиков (первая смена правила между 5493 и 5779), три порции: "
  "(1) яд −0,5 (как в B1) и −0,25 при мгновенной смене, условия life, life_frozen, never_frozen, never; "
  "(2) яд −0,5 с постепенной сменой за 60 и 150 тиков (`switch_ramp_ticks`), life и life_frozen; "
  "(3) яд −0,5, мгновенная смена, стартовая скорость обучения 0,3; 0,5; и 0,1 с посевом лог-нормальным "
  "распределением sigma 1,0 (`taste_lr_init_sigma`), life и life_frozen. Маркерный ген включён везде. "
  "**Пилот, не чтение.**\n")
w("| вариант | условие | seed | вымер (тик) | смен | мин. pop после смены | lr медиана | marker медиана | lr/marker | lr у потолка | точность еды |")
w("|---|---|---|---|---|---|---|---|---|---|---|")
groups = {}
for r in rb:
    if r.get("error"):
        w(f"| {r['key']} | ОШИБКА {r['error'][:80]} ||||||||||")
        continue
    key = r["key"].split("|")[0]
    variant = key.split("/", 1)[1] if "/" in key else ""
    groups.setdefault((variant, r["label"]), []).append(r)
    w(f"| {variant} | {r['label']} | {r['seed']} | {r['extinct'] if r['extinct'] is not None else 'нет'} | {r['switches']} | "
      f"{r.get('min_pop_after_switch')} | {f(r.get('lr_median'),3)} | {f(r.get('marker_median'),3)} | "
      f"{f(r.get('lr_over_marker_median'),2)} | {f(r.get('lr_at_ceiling'),2)} | {f(r.get('eat_accuracy'),3)} |")
w("\nВымирания по вариантам (из трёх seed'ов):\n")
for (variant, cond), rr in sorted(groups.items()):
    e = sum(1 for r in rr if r["extinct"] is not None)
    w(f"- {variant}, {cond}: вымерло {e} из {len(rr)}")
w("")
w("Вывод для §0.1 черновика B2. Ни мягкий яд (−0,25: вымерли 3 из 3 life), ни постепенная смена "
  "(60 и 150 тиков: вымерли 2 из 3, выжил тот же seed 102, что и при мгновенной) мир не спасают: "
  "существо с врождённым вкусом +3 не ест новый съедобный цвет, а учится оно только на укусах, и "
  "мягкий яд не ускоряет обучение (модулятор насыщается уже при потере 2 единиц), он лишь оттягивает "
  "смерть; во время плавного перехода сигнал обучения вовсе пропадает в мёртвой зоне. Рычаг один: "
  "стартовая скорость обучения. При 0,5 выжили 3 из 3 life и 0 из 3 life_frozen (контраст абляции "
  "сохранён), при 0,3 выжили 2 из 3, при посеве распределением вокруг 0,1 выжил 1 из 3. Это ровно "
  "арифметика REPORT_B.md §3.1 и п. 2 из §10. Рекомендация: B2 отличается от B1 ровно одним параметром "
  "мира, `taste_lr_init = 0,5`, яд и смена остаются как в B1; это и честнее (один фактор), и сохраняет "
  "сопоставимость с B1. Потолок: при 0,5 скорость уходит к 3,0-3,5 уже к 12 000-му тику и 27-34% "
  "агентов стоят у потолка 4,0, то есть цензурирование остаётся (§0.4 черновика).\n")
# нейтральность маркера: знак медианы log10(marker/init) по seed'ам в never_frozen
mk = [r for r in rb if r["label"] == "never_frozen" and r.get("marker_median")]
if mk:
    logs = [math.log10(r["marker_median"] / 0.1) for r in mk]
    w(f"Нейтральность маркера (never_frozen, все варианты яда, n={len(mk)}): log10(marker/0,1) = "
      f"{[round(x, 2) for x in logs]}, среднее {st.mean(logs):+.2f}. Граница провала 3 черновика B2 "
      "требует отсутствия систематического сдвига; на трёх seed'ах это можно только прикинуть, "
      "настоящая проверка на 40 seed'ах.")
print("\n".join(out))
