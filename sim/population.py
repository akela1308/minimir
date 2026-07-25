"""Состояния агентов как struct-of-arrays с переиспользованием слотов.

Смерть необратима: слот освобождается, геном исчезает. Никакого респавна.
"""
import numpy as np
from .config import N_MEM
from .brain import Brains


class Population:
    def __init__(self, cfg, rng, world, ancestor=None):
        self.ancestor = ancestor
        self.cfg, self.rng, self.world = cfg, rng, world
        n = cfg.max_pop
        self.alive = np.zeros(n, dtype=bool)
        self.y = np.zeros(n, dtype=np.int64)
        self.x = np.zeros(n, dtype=np.int64)
        self.heading = np.zeros(n, dtype=np.int64)
        self.E = np.zeros(n, dtype=np.float32)
        self.E_lag = np.zeros(n, dtype=np.float32)   # экспоненциальное сглаживание ~10 тиков
        self.age = np.zeros(n, dtype=np.int64)
        self.mem = np.zeros((n, N_MEM), dtype=np.float32)
        self.lineage = np.zeros(n, dtype=np.int64)   # id рода, для филогении
        self.birth_tick = np.zeros(n, dtype=np.int64)

        # социальный слой
        self.face = np.zeros((n, 3), dtype=np.float32)
        self.mem_faces = np.zeros((n, cfg.memory_slots, 3), dtype=np.float32)
        self.mem_valid = np.zeros((n, cfg.memory_slots), dtype=bool)
        self.mem_out = np.zeros((n, cfg.memory_slots), dtype=np.float32)
        self.mem_ptr = np.zeros(n, dtype=np.int64)

        self.brains = Brains(cfg, rng)
        self._free = list(range(n - 1, -1, -1))
        self._next_lineage = 0
        self.births = 0
        self.deaths = 0
        self.lifespans = []      # возраст на момент смерти — для теста порядка развития

    # ---------- слоты ----------
    def _take_slots(self, k):
        k = min(k, len(self._free))
        return [self._free.pop() for _ in range(k)]

    def ids(self):
        return np.flatnonzero(self.alive)

    @property
    def count(self):
        return int(self.alive.sum())

    # ---------- заселение ----------
    def seed_initial(self):
        slots = self._take_slots(self.cfg.init_pop)
        slots = np.asarray(slots, dtype=np.int64)
        self._place_random(slots)
        self.alive[slots] = True
        self.E[slots] = self.cfg.e_start
        self.E_lag[slots] = self.cfg.e_start
        self.age[slots] = 0
        self.mem[slots] = 0.0
        self.mem_valid[slots] = False
        self.face[slots] = self.rng.random((len(slots), 3)).astype(np.float32)
        self.lineage[slots] = np.arange(len(slots))
        self._next_lineage = len(slots)
        self.brains.randomize(slots, self.ancestor)

    def _place_random(self, slots):
        self.y[slots] = self.rng.integers(0, self.world.H, len(slots))
        self.x[slots] = self.rng.integers(0, self.world.W, len(slots))
        self.heading[slots] = self.rng.integers(0, 8, len(slots))

    # ---------- размножение и смерть ----------
    def reproduce(self, tick):
        cand = np.flatnonzero(self.alive & (self.E >= self.cfg.repro_threshold))
        if cand.size == 0:
            return 0
        slots = self._take_slots(cand.size)
        if not slots:
            return 0
        children = np.asarray(slots, dtype=np.int64)
        parents = cand[: children.size]

        cost = self.cfg.child_energy + self.cfg.repro_overhead
        self.E[parents] -= cost
        self.E_lag[parents] = self.E[parents]

        self.alive[children] = True
        self.E[children] = self.cfg.child_energy
        self.E_lag[children] = self.cfg.child_energy
        self.age[children] = 0
        self.mem[children] = 0.0
        self.mem_valid[children] = False
        self.mem_ptr[children] = 0
        self.y[children] = self.y[parents]
        self.x[children] = self.x[parents]
        self.heading[children] = self.rng.integers(0, 8, children.size)
        self.lineage[children] = self.lineage[parents]
        self.birth_tick[children] = tick
        # лицо наследуется с дрейфом — родство узнаваемо, но не абсолютно
        drift = self.rng.normal(0, 0.02, (children.size, 3)).astype(np.float32)
        self.face[children] = np.clip(self.face[parents] + drift, 0.0, 1.0)
        self.brains.inherit(parents, children)
        self.births += children.size
        return children.size

    def cull(self):
        dead = np.flatnonzero(self.alive & ((self.E <= 0.0) | (self.age > self.cfg.max_age)))
        if dead.size:
            self.lifespans.extend(self.age[dead].tolist())
            self.alive[dead] = False
            for s in dead.tolist():
                self._free.append(s)
            self.deaths += dead.size
        return dead.size
