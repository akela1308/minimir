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
from .config import A_FORWARD, A_EAT, A_REST, A_MARK, N_ACTIONS


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


# ---- калибровочные политики знакового слоя (этап 3, пункт C.3) ----
# Запускать с cfg.signs=True. Политика может переопределить engine.sign_content,
# которое _apply запишет в клетку при действии MARK.

def mark_always_policy(engine, ids, X):
    """Метить всегда (когда не кормится срочно). Содержание — случайный шум,
    не зависящий от состояния: знак есть, смысла нет, MI(состояние; содержание)
    обязана быть около нуля. Нижняя граница осмысленности."""
    cfg = engine.cfg
    E = engine.pop.E[ids]
    res_here = X[:, 18]
    hungry = E < cfg.policy_threshold
    engine.sign_content = engine.rng.uniform(-1, 1, (ids.size, 2)).astype(np.float32)
    act = np.where(hungry,
                   np.where(res_here > 0.05, A_EAT, A_FORWARD),
                   A_MARK)
    return act.astype(np.int64)


def mark_when_hungry_follow_own_policy(engine, ids, X):
    """Метить при голоде (содержание кодирует голод) и реагировать на свою
    метку. Интернализация задана руками: MI(состояние; содержание) высокая,
    и поведение зависит от собственной метки. Верхняя граница того, что
    метрика вообще способна увидеть."""
    cfg = engine.cfg
    E = engine.pop.E[ids]
    res_here = X[:, 18]
    sign_here_mine = X[:, 23] > 0.5
    hungry = E < cfg.policy_threshold
    val = np.where(hungry, 1.0, -1.0).astype(np.float32)   # голод -> +1, сытость -> -1
    content = np.repeat(val[:, None], 2, axis=1)           # (k, 2)
    engine.sign_content = content
    act = np.where(hungry,
                   np.where(res_here > 0.05, A_EAT, A_MARK),
                   np.where(sign_here_mine, A_FORWARD, A_REST))
    return act.astype(np.int64)


def ignore_marks_policy(engine, ids, X):
    """Кормиться по голоду, метки не ставить и не учитывать. Нулевой уровень
    для метрик знака."""
    cfg = engine.cfg
    E = engine.pop.E[ids]
    res_here = X[:, 18]
    hungry = E < cfg.policy_threshold
    act = np.where(hungry, np.where(res_here > 0.05, A_EAT, A_FORWARD), A_REST)
    return act.astype(np.int64)


REGISTRY = {
    "threshold": threshold_policy,
    "random": random_policy,
    "mark_always": mark_always_policy,
    "mark_when_hungry_follow_own": mark_when_hungry_follow_own_policy,
    "ignore_marks": ignore_marks_policy,
}


def get(name):
    if name == "evolved":
        return None
    if name not in REGISTRY:
        raise ValueError(f"неизвестная политика: {name}")
    return REGISTRY[name]
