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
        # этап B: своя скорость на каждом синапсе выходного слоя
        self.per_syn = bool(cfg.hebb_per_synapse)
        if self.per_syn:
            self.lr2 = np.full((n, h, N_OUT), cfg.hebb_rate_init, dtype=np.float32)
        # Геном отдельно от фенотипа (барьер Вейсмана). W1/W2 — рабочие веса,
        # которые меняет прижизненное обучение; G1/G2 — то, что наследуется.
        # Без пластичности они всегда совпадают, и память тратится зря, но
        # зато нет двух путей кода. При lamarck=True наследуются W, как в C.1.
        self.G1 = np.zeros((n, N_IN, h), dtype=np.float32)
        self.G2 = np.zeros((n, h, N_OUT), dtype=np.float32)
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
            if self.per_syn:
                self.lr2[slots] = self.cfg.hebb_rate_init
            self.G1[slots] = self.W1[slots]
            self.G2[slots] = self.W2[slots]
            return
        self.W1[slots] = self.rng.normal(0, sg, (k, N_IN, h)).astype(np.float32)
        self.b1[slots] = 0.0
        self.W2[slots] = self.rng.normal(0, sg, (k, h, N_OUT)).astype(np.float32)
        self.b2[slots] = 0.0
        if self.cfg.seed_ancestor:
            self.b2[slots, A_FORWARD] += 0.5
            self.b2[slots, A_EAT] += 0.5
        self.G1[slots] = self.W1[slots]
        self.G2[slots] = self.W2[slots]

    def inherit(self, parents, children):
        """Копия с мутацией. Мутируется доля весов, шум гауссов.

        Наследуется геном (G), а не выученные веса (W): барьер Вейсмана.
        Порядок обращений к генератору тот же, что и раньше, поэтому прогоны
        без пластичности воспроизводятся бит в бит.
        """
        src1 = self.W1 if self.cfg.lamarck else self.G1
        src2 = self.W2 if self.cfg.lamarck else self.G2
        self.G1[children] = src1[parents]
        self.b1[children] = self.b1[parents]
        self.G2[children] = src2[parents]
        self.b2[children] = self.b2[parents]
        self.lr[children] = self._mutate_rate(self.lr[parents], (len(children),))
        if self.per_syn:
            self.lr2[children] = self._mutate_rate(
                self.lr2[parents], (len(children), self.cfg.n_hidden, N_OUT))
        rate, sigma = self.cfg.mutation_rate, self.cfg.mutation_sigma
        for arr in (self.G1, self.b1, self.G2, self.b2):
            sub = arr[children]
            mask = self.rng.random(sub.shape) < rate
            noise = self.rng.normal(0, sigma, sub.shape).astype(np.float32)
            arr[children] = sub + mask * noise
        # фенотип при рождении равен геному; учиться ребёнок будет сам
        self.W1[children] = self.G1[children]
        self.W2[children] = self.G2[children]

    def _mutate_rate(self, parent, shape):
        cfg = self.cfg
        if cfg.hebb_rate_log:
            child = parent * np.exp(self.rng.normal(0, cfg.hebb_rate_sigma, shape))
        else:
            child = np.abs(parent + self.rng.normal(0, cfg.hebb_rate_sigma, shape))
        return np.clip(child, 0.0, cfg.hebb_rate_max).astype(np.float32)

    def rate_summary(self, ids):
        """Сводка по скоростям обучения живых: среднее, медиана, максимум."""
        if ids.size == 0:
            return dict(lr_mean=None, lr_median=None, lr_max=None)
        r = self.lr2[ids] if self.per_syn else self.lr[ids]
        return dict(lr_mean=float(r.mean()), lr_median=float(np.median(r)),
                    lr_max=float(r.max()))

    def rate_map(self, ids):
        """Средняя по популяции скорость на каждом синапсе выходного слоя (h, N_OUT)."""
        if not self.per_syn or ids.size == 0:
            return None
        return self.lr2[ids].mean(axis=0)

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
        if self.per_syn:
            lr = (self.lr2[ids] * (modulator * self.cfg.hebb_every)[:, None, None]).astype(np.float32)
        w2 = self.W2[ids] + lr * (self.last_hidden[:, :, None] * self.last_out[:, None, :])
        self.W2[ids] = np.clip(w2, -c, c)

    def genome_matrix(self, ids):
        """Плоские геномы (k, n_weights) — для анализа разнообразия и снапшотов."""
        k = len(ids)
        if k == 0:
            return np.zeros((0, self.n_weights), dtype=np.float32)
        return np.concatenate(
            [self.G1[ids].reshape(k, -1), self.b1[ids],
             self.G2[ids].reshape(k, -1), self.b2[ids]], axis=1)

    def learned_drift(self, ids):
        """Насколько фенотип ушёл от генома за жизнь: средний |W2 - G2|."""
        if ids.size == 0:
            return 0.0
        return float(np.abs(self.W2[ids] - self.G2[ids]).mean())
