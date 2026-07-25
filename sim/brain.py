"""Геном = плоский набор весов MLP N_IN -> n_hidden (tanh) -> N_OUT (сейчас 25 -> 12 -> 12).

Никакой fitness-функции нет и не будет: размножение — следствие поведения,
а не оценка сверху. Отбор идёт сам, как в Avida.
"""
import numpy as np
from .config import N_IN, N_OUT, N_ACTIONS, A_FORWARD, A_EAT, A_GIVE, A_TAKE


class Brains:
    """Struct-of-arrays: для каждого слота популяции свой набор весов."""

    def __init__(self, cfg, rng):
        self.cfg = cfg
        self.rng = rng
        n, h = cfg.max_pop, cfg.n_hidden
        self.W1 = np.zeros((n, N_IN, h), dtype=np.float32)
        self.b1 = np.zeros((n, h), dtype=np.float32)
        self.W2 = np.zeros((n, h, N_OUT), dtype=np.float32)
        self.b2 = np.zeros((n, N_OUT), dtype=np.float32)
        # скорость пластичности закодирована в геноме и эволюционирует (как в Polyworld)
        self.lr = np.full(n, cfg.hebb_rate_init, dtype=np.float32)
        self.last_X = None
        self.last_hidden = None

    @property
    def n_weights(self) -> int:
        h = self.cfg.n_hidden
        return N_IN * h + h + h * N_OUT + N_OUT

    def randomize(self, slots, ancestor=None):
        k = len(slots)
        h, sg = self.cfg.n_hidden, self.cfg.init_weight_sigma
        if self.cfg.ancestor_mode == "clone":
            if ancestor is None:
                from .ancestry import find_viable_ancestor
                ancestor, self.ancestor_tries = find_viable_ancestor(self.cfg)
            W1, b1, W2, b2 = ancestor
            fs = self.cfg.founding_sigma
            self.W1[slots] = W1 + self.rng.normal(0, fs, (k, N_IN, h)).astype(np.float32)
            self.b1[slots] = b1 + self.rng.normal(0, fs, (k, h)).astype(np.float32)
            self.W2[slots] = W2 + self.rng.normal(0, fs, (k, h, N_OUT)).astype(np.float32)
            self.b2[slots] = b2 + self.rng.normal(0, fs, (k, N_OUT)).astype(np.float32)
            self.lr[slots] = self.cfg.hebb_rate_init
            return
        self.W1[slots] = self.rng.normal(0, sg, (k, N_IN, h)).astype(np.float32)
        self.b1[slots] = 0.0
        self.W2[slots] = self.rng.normal(0, sg, (k, h, N_OUT)).astype(np.float32)
        self.b2[slots] = 0.0
        if self.cfg.seed_ancestor:
            self.b2[slots, A_FORWARD] += 0.5
            self.b2[slots, A_EAT] += 0.5

    def inherit(self, parents, children):
        """Копия с мутацией. Мутируется доля весов, шум гауссов."""
        for arr in (self.W1, self.b1, self.W2, self.b2):
            arr[children] = arr[parents]
        self.lr[children] = np.abs(
            self.lr[parents]
            + self.rng.normal(0, self.cfg.hebb_rate_sigma, len(children))
        ).astype(np.float32)
        rate, sigma = self.cfg.mutation_rate, self.cfg.mutation_sigma
        for arr in (self.W1, self.b1, self.W2, self.b2):
            sub = arr[children]
            mask = self.rng.random(sub.shape) < rate
            noise = self.rng.normal(0, sigma, sub.shape).astype(np.float32)
            arr[children] = sub + mask * noise

    def forward(self, ids, X):
        """X: (k, N_IN) -> (k, N_OUT). Один einsum на всю живую популяцию."""
        h = np.matmul(X[:, None, :], self.W1[ids])[:, 0, :] + self.b1[ids]
        np.tanh(h, out=h)
        self.last_X = X
        self.last_hidden = h          # для стоимости мышления и пластичности
        out = np.matmul(h[:, None, :], self.W2[ids])[:, 0, :] + self.b2[ids]
        self.last_out = np.tanh(out)
        return out

    def hebbian_update(self, ids, modulator):
        """Пластичность внутри жизни: правило генетическое, эффект — прижизненный.

        Без изменений внутри жизни тест порядка развития невозможен: измерять
        было бы нечего. Модулятор — изменение внутреннего состояния. Это цена
        решения: мы больше не можем говорить «награды нет вообще», только
        «нет назначенной награды, есть эволюционирующее правило пластичности».
        """
        if self.last_X is None:
            return
        # шаг применения компенсируется масштабом: суммарная пластичность
        # за единицу времени остаётся сопоставимой
        lr = (self.lr[ids] * modulator * self.cfg.hebb_every).astype(np.float32)
        lr = lr[:, None, None]
        c = self.cfg.weight_clip
        if self.cfg.hebb_layers == "both":
            w1 = self.W1[ids] + lr * (self.last_X[:, :, None] * self.last_hidden[:, None, :])
            self.W1[ids] = np.clip(w1, -c, c)
        w2 = self.W2[ids] + lr * (self.last_hidden[:, :, None] * self.last_out[:, None, :])
        self.W2[ids] = np.clip(w2, -c, c)

    def genome_matrix(self, ids):
        """Плоские геномы (k, n_weights) — для анализа разнообразия и снапшотов."""
        k = len(ids)
        if k == 0:
            return np.zeros((0, self.n_weights), dtype=np.float32)
        return np.concatenate(
            [self.W1[ids].reshape(k, -1), self.b1[ids],
             self.W2[ids].reshape(k, -1), self.b2[ids]], axis=1)
