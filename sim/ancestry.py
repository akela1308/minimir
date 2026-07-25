"""Поиск жизнеспособного предка.

Синтетической проверки «стоя на еде — ешь» оказалось недостаточно: геном
может проходить её и при этом не уметь искать еду, и тогда популяция клонов
гибнет целиком. Поэтому предок обязан доказать жизнеспособность в настоящей
мини-симуляции — вырастить популяцию, а не просто выглядеть разумно.
Ровно так устроен рукописный @ancestor в Avida: он проверен на самокопирование.

Отдельный генератор, засеянный только seed'ом, гарантирует, что для данного
seed'а предок один и тот же во всех условиях эксперимента. Иначе мы сравнивали
бы условия вместе с удачей основателей.
"""
import dataclasses
from pathlib import Path

import numpy as np

from .config import N_IN, N_OUT, N_ACTIONS, A_FORWARD, A_EAT, A_GIVE, A_TAKE

# Форма генома задаётся тройкой (N_IN, n_hidden, N_OUT). Имя кэша обязано
# содержать все три: раньше в нём был только N_IN, и при изменении числа
# выходов молча подхватывался несовместимый предок другой формы.



def _random_genome(rng, cfg):
    h, sg = cfg.n_hidden, cfg.init_weight_sigma
    W1 = rng.normal(0, sg, (N_IN, h)).astype(np.float32)
    b1 = np.zeros(h, dtype=np.float32)
    W2 = rng.normal(0, sg, (h, N_OUT)).astype(np.float32)
    b2 = np.zeros(N_OUT, dtype=np.float32)
    if cfg.seed_ancestor:
        b2[A_FORWARD] += 0.5
        b2[A_EAT] += 0.5
    return W1, b1, W2, b2


def _passes_synthetic(g):
    """Дешёвый предфильтр: отсекает заведомо безнадёжное до симуляции."""
    W1, b1, W2, b2 = g
    X = np.zeros((2, N_IN), dtype=np.float32)
    X[0, 18] = 0.8; X[0, 8] = 0.5; X[0, 13] = 1.0      # еда под собой
    X[1, 0] = 0.8;  X[1, 8] = 0.3; X[1, 13] = 1.0      # еда впереди
    out = np.tanh(X @ W1 + b1) @ W2 + b2
    logits = out[:, :N_ACTIONS].copy()
    logits[:, A_GIVE] = -np.inf
    logits[:, A_TAKE] = -np.inf
    act = np.argmax(logits, axis=1)
    return bool(act[0] == A_EAT and act[1] == A_FORWARD)


def _passes_simulation(cfg, g, ticks=3000):
    """Настоящий отбор: способна ли популяция клонов вырасти."""
    from .engine import Engine                    # локально: цикл импорта
    scr = dataclasses.replace(
        cfg, grid_h=48, grid_w=48, init_pop=24, max_pop=400,
        crowd_cost=0.0, season_period=0, social=False, signs=False, hebbian=False,
        intero_mode="self", interoception=True, policy="evolved",
        founding_sigma=0.05, log_every=10 ** 9)
    eng = Engine(scr, ancestor=g)
    eng.run(ticks)
    return eng.extinct_at is None and eng.pop.count >= 36   # выросла в 1.5 раза


def find_viable_ancestor(cfg, cache_dir="runs/ancestors", verbose=False):
    cache = Path(cache_dir) / f"seed{cfg.seed}_h{cfg.n_hidden}_in{N_IN}_out{N_OUT}.npz"
    if cache.exists():
        d = np.load(cache)
        g = (d["W1"], d["b1"], d["W2"], d["b2"])
        # страховка: форма кэша обязана совпасть с текущей формой генома
        if g[0].shape == (N_IN, cfg.n_hidden) and g[2].shape == (cfg.n_hidden, N_OUT):
            return g, int(d["tries"])

    rng = np.random.default_rng(cfg.seed * 1000003 + 7)
    synth = 0
    for attempt in range(1, cfg.ancestor_tries + 1):
        g = _random_genome(rng, cfg)
        if not _passes_synthetic(g):
            continue
        synth += 1
        if _passes_simulation(cfg, g):
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cache, W1=g[0], b1=g[1], W2=g[2], b2=g[3],
                                tries=attempt)
            if verbose:
                print(f"  seed {cfg.seed}: предок с {attempt}-й попытки "
                      f"({synth} прошли предфильтр)")
            return g, attempt
        if synth > 200:
            break
    raise RuntimeError(
        f"seed {cfg.seed}: жизнеспособный предок не найден. "
        "Мир, возможно, слишком беден — проверьте world.energy_budget().")
