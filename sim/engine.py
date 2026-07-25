"""Тик мира. Порядок строгий и детерминированный.

1. сенсоры -> 2. forward-pass -> 3. действия -> 4. метаболизм
-> 5. смерть -> 6. размножение -> 7. отрост ресурса
"""
import numpy as np
from .config import (N_IN, N_ACTIONS, N_MEM, N_SIGN, A_FORWARD, A_LEFT, A_RIGHT,
                     A_EAT, A_REST, A_GIVE, A_TAKE, A_MARK)
from .world import World
from .population import Population
from . import policies

# 8 направлений по часовой от «вперёд» = (dy=-1, dx=0)
OFF_Y = np.array([-1, -1, 0, 1, 1, 1, 0, -1], dtype=np.int64)
OFF_X = np.array([0, 1, 1, 1, 0, -1, -1, -1], dtype=np.int64)

# смещения для поиска соседа, отсортированные по расстоянию
_R = 2
_cells = [(dy, dx) for dy in range(-_R, _R + 1) for dx in range(-_R, _R + 1)
          if not (dy == 0 and dx == 0)]
_cells.sort(key=lambda c: c[0] ** 2 + c[1] ** 2)
NB_Y = np.array([c[0] for c in _cells], dtype=np.int64)
NB_X = np.array([c[1] for c in _cells], dtype=np.int64)
NB_D = np.hypot(NB_Y, NB_X).astype(np.float32)


class Engine:
    def __init__(self, cfg, ancestor=None):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.world = World(cfg, self.rng)
        self.pop = Population(cfg, self.rng, self.world, ancestor)
        self.pop.seed_initial()
        self.tick = 0
        # накопители метрик
        self.energy_action_hist = np.zeros((10, N_ACTIONS), dtype=np.int64)
        self.window_hist = np.zeros((10, N_ACTIONS), dtype=np.int64)
        self.policy_fn = policies.get(cfg.policy)
        self.individual_hist = {} if cfg.track_individual else None
        self.last_hidden_cost = None
        self.forage_hits = 0
        self.forage_moves = 0
        self.coop_events = 0
        self.defect_events = 0
        self.marks_made = 0
        self.sign_content = None
        self.action_counts = np.zeros(N_ACTIONS, dtype=np.int64)
        self.extinct_at = None

    @property
    def social_active(self) -> bool:
        return self.cfg.social and self.tick >= self.cfg.social_from_tick

    def reset_metrics(self):
        self.energy_action_hist[:] = 0
        self.window_hist[:] = 0
        self.action_counts[:] = 0
        self.forage_hits = self.forage_moves = 0
        self.coop_events = self.defect_events = 0

    # ------------------------------------------------------------------ сенсоры
    def _neighbourhood(self, ids):
        """8 клеток вокруг, повёрнутые по курсу агента: сенсор эгоцентричен."""
        H, W = self.world.H, self.world.W
        y, x, h = self.pop.y[ids], self.pop.x[ids], self.pop.heading[ids]
        d = (h[:, None] + np.arange(8)[None, :]) % 8          # (k, 8)
        yy = (y[:, None] + OFF_Y[d]) % H
        xx = (x[:, None] + OFF_X[d]) % W
        return self.world.resource[yy, xx]

    def _density(self, ids):
        """Число агентов в окне 3x3 вокруг каждого, включая себя.

        Считается через карту занятости, поэтому стоимость не зависит
        от числа агентов — только от размера сетки.
        """
        H, W = self.world.H, self.world.W
        counts = np.zeros((H, W), dtype=np.int32)
        np.add.at(counts, (self.pop.y[ids], self.pop.x[ids]), 1)
        local = np.zeros_like(counts)
        for dy in (-1, 0, 1):
            rolled = np.roll(counts, dy, axis=0)
            for dx in (-1, 0, 1):
                local += np.roll(rolled, dx, axis=1)
        return local[self.pop.y[ids], self.pop.x[ids]]

    def _nearest_partner(self, ids):
        """Ближайший сосед в радиусе 3 через сетку занятости, одним проходом.

        NB_* отсортированы по расстоянию, поэтому первое попадание = ближайшее.
        """
        H, W = self.world.H, self.world.W
        occ = np.full((H, W), -1, dtype=np.int64)
        occ[self.pop.y[ids], self.pop.x[ids]] = ids            # при коллизии — последний
        yy = (self.pop.y[ids][:, None] + NB_Y[None, :]) % H    # (k, 48)
        xx = (self.pop.x[ids][:, None] + NB_X[None, :]) % W
        found = occ[yy, xx]
        ok = (found >= 0) & (found != ids[:, None])
        first = np.argmax(ok, axis=1)
        any_ok = ok[np.arange(ids.size), first]
        best = np.where(any_ok, found[np.arange(ids.size), first], -1)
        best_d = np.where(any_ok, NB_D[first], np.inf).astype(np.float32)
        return best, best_d

    def _recognition(self, ids, partner):
        """Узнаём ли партнёра и чем кончился прошлый контакт с ним."""
        cfg = self.cfg
        recognized = np.zeros(ids.size, dtype=np.float32)
        last = np.zeros(ids.size, dtype=np.float32)
        if not (self.social_active and cfg.recognition):
            return recognized, last
        has = partner >= 0
        if not has.any():
            return recognized, last
        sub = np.flatnonzero(has)
        me = ids[sub]
        pf = self.pop.face[partner[sub]]                     # (m,3)
        stored = self.pop.mem_faces[me]                      # (m,K,3)
        dist = np.abs(stored - pf[:, None, :]).sum(axis=2)   # (m,K)
        dist = np.where(self.pop.mem_valid[me], dist, np.inf)
        j = np.argmin(dist, axis=1)
        dmin = dist[np.arange(me.size), j]
        ok = dmin < cfg.face_tolerance
        recognized[sub] = ok.astype(np.float32)
        last[sub] = np.where(ok, self.pop.mem_out[me, j], 0.0)
        return recognized, last

    def _interoceptive_signal(self, ids, partner):
        """Вход 8-9 по условию эксперимента.

        Ключевое отличие от первой версии: контроль — это ПОДМЕНА, а не
        зануление. Зануление меняет и информацию, и статистику входа сразу;
        тогда непонятно, что именно вызвало разницу. Перестановка энергии
        между агентами сохраняет распределение бит в бит и убирает ровно
        одно — знание о себе.
        """
        cfg, pop = self.cfg, self.pop
        k = ids.size
        mode = cfg.intero_mode if cfg.interoception else "off"
        zeros = np.zeros(k, dtype=np.float32)
        if mode == "off" or k == 0:
            return zeros, zeros

        e = (pop.E[ids] / cfg.e_max).astype(np.float32)
        de = np.clip((pop.E[ids] - pop.E_lag[ids]) / 5.0, -1.0, 1.0).astype(np.float32)

        if mode == "self":
            return e, de
        if mode == "shuffled":
            # циклический сдвиг на случайную ненулевую величину:
            # распределение то же, неподвижных точек нет
            if k < 2:
                return zeros, zeros
            shift = int(self.rng.integers(1, k))
            idx = (np.arange(k) + shift) % k
            return e[idx], de[idx]
        if mode == "neighbour":
            has = partner >= 0
            src = np.where(has, partner, ids)
            e_n = (pop.E[src] / cfg.e_max).astype(np.float32)
            de_n = np.clip((pop.E[src] - pop.E_lag[src]) / 5.0, -1.0, 1.0).astype(np.float32)
            if k >= 2 and (~has).any():
                # без соседа берём случайного другого, чтобы не подсунуть себя
                shift = int(self.rng.integers(1, k))
                idx = (np.arange(k) + shift) % k
                e_n = np.where(has, e_n, e[idx])
                de_n = np.where(has, de_n, de[idx])
            return e_n.astype(np.float32), de_n.astype(np.float32)
        raise ValueError(f"неизвестный intero_mode: {mode}")

    def _sense_signs(self, ids, X):
        """Входы 19-24: метка под собой, метка впереди, чьё авторство."""
        cfg, pop, w = self.cfg, self.pop, self.world
        H, W = w.H, w.W
        y, x, h = pop.y[ids], pop.x[ids], pop.heading[ids]
        X[:, 19:21] = w.signs[y, x]
        ay = (y + OFF_Y[h]) % H
        ax = (x + OFF_X[h]) % W
        X[:, 21:23] = w.signs[ay, ax]

        mode = cfg.sign_mode
        if mode == "off":
            return
        author = w.sign_author[y, x]
        present = np.abs(w.signs[y, x]).sum(axis=1) > 1e-3
        mine = (np.abs(author - pop.face[ids]).sum(axis=1) < cfg.face_tolerance) & present

        if mode == "others":
            # свои метки для агента невидимы: гасим содержание там, где метка своя
            X[mine, 19:21] = 0.0
            return
        if mode == "shuffled":
            # признак авторства переставлен: распределение то же, информации нет
            k = ids.size
            if k >= 2:
                shift = int(self.rng.integers(1, k))
                mine = mine[(np.arange(k) + shift) % k]
        X[:, 23] = mine.astype(np.float32)
        # знакомый ли автор чужой метки — из памяти контактов
        if cfg.social:
            stored = pop.mem_faces[ids]
            dist = np.abs(stored - author[:, None, :]).sum(axis=2)
            dist = np.where(pop.mem_valid[ids], dist, np.inf)
            known = (dist.min(axis=1) < cfg.face_tolerance) & present & ~mine
            X[:, 24] = known.astype(np.float32)

    def _sense(self, ids, partner, partner_d):
        cfg, pop = self.cfg, self.pop
        X = np.zeros((ids.size, N_IN), dtype=np.float32)
        X[:, 0:8] = self._neighbourhood(ids)
        X[:, 18] = self.world.resource[pop.y[ids], pop.x[ids]]   # клетка под собой
        e_sig, de_sig = self._interoceptive_signal(ids, partner)
        X[:, 8] = e_sig
        X[:, 9] = de_sig
        X[:, 10] = np.minimum(pop.age[ids] / 1000.0, 3.0)

        has = partner >= 0
        if has.any():
            sub = np.flatnonzero(has)
            H, W = self.world.H, self.world.W
            dy = ((pop.y[partner[sub]] - pop.y[ids[sub]] + H // 2) % H) - H // 2
            dx = ((pop.x[partner[sub]] - pop.x[ids[sub]] + W // 2) % W) - W // 2
            ang = np.arctan2(dx, -dy)                       # компасный угол
            rel = ang - pop.heading[ids[sub]] * (np.pi / 4)
            rel = (rel + np.pi) % (2 * np.pi) - np.pi
            X[sub, 11] = rel / np.pi
            X[sub, 12] = 1.0 / (1.0 + partner_d[sub])
        if cfg.signs:
            self._sense_signs(ids, X)
        X[:, 13] = 1.0                                       # bias
        X[:, 14:16] = pop.mem[ids]
        rec, last = self._recognition(ids, partner)
        X[:, 16] = rec
        X[:, 17] = last
        return X

    # ------------------------------------------------------------------ действия
    def _choose(self, ids, out, X=None):
        if self.policy_fn is not None:
            return self.policy_fn(self, ids, X)
        logits = out[:, :N_ACTIONS].copy()
        if not self.cfg.signs:
            logits[:, A_MARK] = -np.inf
        if not self.social_active:
            logits[:, A_GIVE] = -np.inf
            logits[:, A_TAKE] = -np.inf
        act = np.argmax(logits, axis=1)
        if self.cfg.action_noise > 0:
            flip = self.rng.random(ids.size) < self.cfg.action_noise
            k = N_ACTIONS if self.social_active else N_ACTIONS - 3
            act = np.where(flip, self.rng.integers(0, k, ids.size), act)
        return act

    def _apply(self, ids, act, partner, crowd=None):
        cfg, pop, w = self.cfg, self.pop, self.world
        H, W = w.H, w.W
        cost = np.full(ids.size, cfg.basal_cost, dtype=np.float32)
        if cfg.crowd_cost > 0 and crowd is not None:
            cost += cfg.crowd_cost * np.maximum(crowd - 1, 0).astype(np.float32)
        if cfg.think_cost > 0:
            hid = getattr(pop.brains, "last_hidden", None)
            if hid is not None and hid.shape[0] == ids.size:
                cost += cfg.think_cost * np.abs(hid).mean(axis=1).astype(np.float32)

        # поворот
        m = act == A_LEFT
        pop.heading[ids[m]] = (pop.heading[ids[m]] - 1) % 8
        cost[m] += cfg.turn_cost
        m = act == A_RIGHT
        pop.heading[ids[m]] = (pop.heading[ids[m]] + 1) % 8
        cost[m] += cfg.turn_cost

        # движение вперёд + учёт «попал ли в еду»
        m = act == A_FORWARD
        if m.any():
            sub = ids[m]
            d = pop.heading[sub]
            ny = (pop.y[sub] + OFF_Y[d]) % H
            nx = (pop.x[sub] + OFF_X[d]) % W
            ahead = w.resource[ny, nx]
            here = w.resource[pop.y[sub], pop.x[sub]]
            self.forage_moves += sub.size
            self.forage_hits += int((ahead > here).sum())
            pop.y[sub], pop.x[sub] = ny, nx
            cost[m] += cfg.move_cost

        # еда
        m = act == A_EAT
        if m.any():
            sub = ids[m]
            cell_y, cell_x = pop.y[sub], pop.x[sub]
            take = np.minimum(w.resource[cell_y, cell_x], cfg.bite)
            # несколько агентов в одной клетке: списываем через add.at, честно
            np.add.at(w.resource, (cell_y, cell_x), -take)
            np.clip(w.resource, 0.0, 1.0, out=w.resource)
            pop.E[sub] += take * cfg.energy_per_resource
            cost[m] += cfg.eat_cost

        # оставить метку: запись во внешнюю форму, переживающую момент
        if cfg.signs:
            m = act == A_MARK
            if m.any():
                sub = ids[m]
                cy, cx = pop.y[sub], pop.x[sub]
                w.signs[cy, cx] = self.sign_content[m]
                w.sign_author[cy, cx] = pop.face[sub]
                w.sign_age[cy, cx] = 0.0
                cost[m] += cfg.mark_cost
                self.marks_made += sub.size

        # социальные действия: только при наличии смежного партнёра
        if self.social_active:
            adjacent = (partner >= 0)
            self._interact(ids, act, partner, adjacent)

        pop.E[ids] -= cost
        np.clip(pop.E, -1.0, cfg.e_max, out=pop.E)
        pop.E_lag[ids] += 0.1 * (pop.E[ids] - pop.E_lag[ids])
        pop.age[ids] += 1

    def _interact(self, ids, act, partner, adjacent):
        """Дилемма вырастает из метаболизма, а не из матрицы выигрышей."""
        cfg, pop = self.cfg, self.pop
        for kind, sign in ((A_GIVE, 1.0), (A_TAKE, -1.0)):
            m = (act == kind) & adjacent
            if not m.any():
                continue
            actor = ids[m]
            target = partner[m]
            if kind == A_GIVE:
                pop.E[actor] -= cfg.give_cost
                np.add.at(pop.E, target, cfg.give_gain)
                self.coop_events += actor.size
            else:
                np.add.at(pop.E, actor, cfg.take_gain)
                np.add.at(pop.E, target, -cfg.take_loss)
                self.defect_events += actor.size
            self._remember(actor, target, sign)
            self._remember(target, actor, sign)

    def _remember(self, who, whom, outcome):
        """Кладём лицо контрагента и исход в кольцевую память."""
        K = self.cfg.memory_slots
        p = self.pop.mem_ptr[who] % K
        self.pop.mem_faces[who, p] = self.pop.face[whom]
        self.pop.mem_out[who, p] = outcome
        self.pop.mem_valid[who, p] = True
        self.pop.mem_ptr[who] = (p + 1) % K

    # ------------------------------------------------------------------ тик
    def step(self):
        pop = self.pop
        ids = pop.ids()
        if ids.size == 0:
            if self.extinct_at is None:
                self.extinct_at = self.tick
            return False

        crowd = self._density(ids) if self.cfg.crowd_cost > 0 else None
        partner, partner_d = self._nearest_partner(ids)
        adj = partner_d <= 1.5
        partner_adj = np.where(adj, partner, -1)

        X = self._sense(ids, partner, partner_d)
        out = self.pop.brains.forward(ids, X)
        pop.mem[ids] = np.tanh(out[:, N_ACTIONS:N_ACTIONS + N_MEM])
        self.sign_content = np.tanh(out[:, N_ACTIONS + N_MEM:N_ACTIONS + N_MEM + N_SIGN])
        act = self._choose(ids, out, X)

        # метрики: что агент делает при каком уровне энергии
        bins = np.clip((pop.E[ids] / self.cfg.e_max * 10).astype(np.int64), 0, 9)
        np.add.at(self.energy_action_hist, (bins, act), 1)
        np.add.at(self.window_hist, (bins, act), 1)
        if self.individual_hist is not None:
            for i, aid in enumerate(ids.tolist()):
                key = (aid, int(pop.birth_tick[aid]))
                h = self.individual_hist.get(key)
                if h is None:
                    h = np.zeros((10, N_ACTIONS), dtype=np.int32)
                    self.individual_hist[key] = h
                h[bins[i], act[i]] += 1
        np.add.at(self.action_counts, act, 1)

        e_before = pop.E[ids].copy()
        self._apply(ids, act, partner_adj, crowd)
        if self.cfg.hebbian and self.tick % self.cfg.hebb_every == 0:
            mod = np.ones(ids.size, dtype=np.float32)
            if self.cfg.hebb_modulated:
                mod = np.clip((pop.E[ids] - e_before) / 2.0, -1.0, 1.0).astype(np.float32)
            pop.brains.hebbian_update(ids, mod)
        pop.cull()
        pop.reproduce(self.tick)
        self.world.step()
        self.tick += 1
        return True

    def run(self, ticks, on_log=None):
        for _ in range(ticks):
            if not self.step():
                break
            if on_log and self.tick % self.cfg.log_every == 0:
                on_log(self)
        return self

    # ------------------------------------------------------------------ сводка
    def stats(self):
        ids = self.pop.ids()
        n = ids.size
        coop_total = self.coop_events + self.defect_events
        return dict(
            tick=self.tick,
            pop=n,
            mean_E=float(self.pop.E[ids].mean()) if n else 0.0,
            mean_age=float(self.pop.age[ids].mean()) if n else 0.0,
            max_age=int(self.pop.age[ids].max()) if n else 0,
            births=self.pop.births,
            deaths=self.pop.deaths,
            resource=self.world.total_resource(),
            lineages=int(np.unique(self.pop.lineage[ids]).size) if n else 0,
            forage_accuracy=(self.forage_hits / self.forage_moves) if self.forage_moves else 0.0,
            coop_rate=(self.coop_events / coop_total) if coop_total else None,
        )
