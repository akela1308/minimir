"""Протокол B2 (ЧЕРНОВИК, 13 октября 2026): конфигурация для следующей версии
эксперимента «Когда выгодно учиться». Не заморожен, прогонов по нему не было.

Что здесь уже решено (ИДЕИ_2026-10-13.md §2.5, §5.6, §5.7; REPORT_B.md §10):
  * нейтральный маркерный ген marker_gene=True во всех условиях: второй
    мультипликативный ген с тем же ядром мутации и без функции. Критерий 2
    сравнивает log(lr / marker) в том же мире на том же тике, а не lr против
    разброса lr в never_frozen, который рос с длиной прогона;
  * доля агентов у потолка taste_lr_max пишется отдельной метрикой
    (lr_at_ceiling), потому что в B1 медианы упёрлись в 4,0.

Что здесь НЕ решено и ждёт решения владельца до заморозки (REPORT_B.md §10,
пункты 1-2, 4-5): как мир переживает первую смену правила (мягче яд, или
постепенная смена, или посев распределения стартовых скоростей), отдельное
условие на градиент частоты, запись скорости обучения погибших. Ниже эти
параметры оставлены равными B1 и помечены TODO; их значения в предрегистрации
B2 задаются явно, иначе это тот же мир, который убил 32 из 40 популяций.

Единая точка правды по условиям, как в protocol_b.py. Раннер и файл результатов
для B2 создаются после заморозки предрегистрации (новый файл, не
runs/daily/protocol_b.jsonl).
"""
from .config import Config
from .protocol_b import CONDS, SWITCH, PLASTIC, WORLD_B, measure_b

PROTOCOL = "B2-черновик"

WORLD_B2 = dict(WORLD_B,
                marker_gene=True, marker_init=0.1,
                # TODO (решение владельца до заморозки): toxic_factor -0.5 в B1
                # убивал мир на первой смене; REPORT_B §10 предлагал -0.2…-0.25
                # или постепенную смену. Пилот 13.10.2026 (seed'ы 101-103,
                # runs/b2/pilot/PILOT_2026-10-13.md): ни то, ни другое мир не
                # спасает; спасает стартовая скорость обучения taste_lr_init=0.5
                # (life 3/3 живы, life_frozen 0/3). Предложение: менять только её.
                toxic_factor=WORLD_B["toxic_factor"],
                # TODO (решение владельца): taste_lr_init 0.1 в B1; пилот
                # рекомендует 0.5 (см. выше). Пока оставлено как в B1.
                taste_lr_init=WORLD_B.get("taste_lr_init", 0.1),
                # TODO (решение владельца): посев стартовых скоростей
                # лог-нормальным разбросом (Config.taste_lr_init_sigma,
                # реализовано 13.10.2026); 0 = как в B1. Пилот: при 0.1 и
                # sigma 1.0 выжил 1 из 3, слабее, чем просто 0.5.
                taste_lr_init_sigma=0.0,
                # TODO: taste_lr_max 4.0 цензурировал эффект в B1 (§5.7)
                taste_lr_max=4.0,
                # TODO (решение владельца): постепенная смена правила, тиков на
                # переход (Config.switch_ramp_ticks, реализовано 13.10.2026);
                # 0 = мгновенно, как в B1. Пилот на seed'ах 101-103: см.
                # runs/b2/pilot/PILOT_2026-10-13.md
                switch_ramp_ticks=0)


def config_b2(seed, cond, **overrides):
    if cond not in CONDS:
        raise ValueError(f"неизвестное условие протокола B2: {cond}")
    kw = dict(WORLD_B2, seed=seed, switch_mean=SWITCH[cond])
    if not PLASTIC[cond]:
        kw.update(taste_learning=False)
    kw.update(overrides)
    return Config(**kw)


def measure_b2(job):
    """Тот же замер, что measure_b, плюс поля маркера (их пишет сам measure_b,
    когда в конфиге marker_gene=True). Конфигурацию берём из config_b2."""
    job = dict(job)
    job.setdefault("overrides", {})
    job["overrides"] = dict(WORLD_B2, **job["overrides"])
    # measure_b строит конфигурацию через config_b(seed, label, **overrides);
    # overrides поверх WORLD_B дают ровно WORLD_B2 плюс явные правки задания
    row = measure_b(job)
    row["protocol"] = PROTOCOL
    return row
