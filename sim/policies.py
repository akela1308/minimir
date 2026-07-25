"""Калибровка прибора.

Прежде чем измерять неизвестное, детектор прогоняют по известному источнику.
Здесь два таких источника — политики, для которых мы ЗАРАНЕЕ знаем ответ:

  threshold — поведение полностью определяется внутренним состоянием.
              I(энергия; действие) обязана быть большой. Если метрика этого
              не показывает — метрика негодная, и все остальные измерения
              не имеют смысла.

  random    — поведение не зависит ни от чего. I обязана быть около нуля.
              Даёт нижнюю границу шума метрики при данном числе сэмплов.

Эволюция здесь не участвует: политика подменяет выход мозга целиком.
"""
import numpy as np
from .config import A_FORWARD, A_EAT, A_REST, N_ACTIONS


def threshold_policy(engine, ids, X):
    """Голоден — добывай: если под тобой еда, ешь, иначе иди. Сыт — стой.

    Верхняя граница того, что метрика вообще способна увидеть.
    """
    cfg = engine.cfg
    E = engine.pop.E[ids]
    res_here = X[:, 18]
    hungry = E < cfg.policy_threshold
    act = np.where(hungry,
                   np.where(res_here > 0.05, A_EAT, A_FORWARD),
                   A_REST)
    return act.astype(np.int64)


def random_policy(engine, ids, X):
    n = N_ACTIONS if engine.social_active else N_ACTIONS - 2
    return engine.rng.integers(0, n, ids.size)


REGISTRY = {
    "threshold": threshold_policy,
    "random": random_policy,
}


def get(name):
    if name == "evolved":
        return None
    if name not in REGISTRY:
        raise ValueError(f"неизвестная политика: {name}")
    return REGISTRY[name]
