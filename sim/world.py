"""Тор 128x128 (размер задаётся cfg.grid_h/grid_w). В каждой клетке ресурс r in [0, K(x,y)].

Ёмкость K — пятнистая: равномерная еда убивает эволюцию, нужен дефицит и поиск.
Отрост логистического типа, но к ёмкости, а не мультипликативный: клетка,
выеденная в ноль, способна восстановиться (r += g*(K-r)).
"""
import numpy as np


class World:
    def __init__(self, cfg, rng):
        self.cfg = cfg
        self.rng = rng
        self.H, self.W = cfg.grid_h, cfg.grid_w
        self.capacity = self._make_capacity()
        self.resource = (self.capacity * cfg.initial_fill).astype(np.float32)
        self.t = 0
        # поле знаков: содержание метки и «лицо» её автора.
        # Знак живёт во внешней форме и переживает момент — иначе это сигнал,
        # а не знак (и не работает конструкция «оставил, ушёл, вернулся, прочитал»).
        self.signs = np.zeros((self.H, self.W, 2), dtype=np.float32)
        self.sign_author = np.zeros((self.H, self.W, 3), dtype=np.float32)
        self.sign_age = np.zeros((self.H, self.W), dtype=np.float32)
        # для теста порядка развития (C.4): кто и в каком возрасте оставил метку
        self.sign_author_id = np.full((self.H, self.W), -1, dtype=np.int64)
        self.sign_author_age = np.zeros((self.H, self.W), dtype=np.float32)

        # --- этап B: два типа еды и смена правил ---
        # Тип клетки фиксирован на всю жизнь мира (это география), а вот
        # какой тип питателен, меняется. Моменты смены берутся из ОТДЕЛЬНОГО
        # генератора, засеянного только seed'ом: у всех условий с одним T
        # расписание смен одно и то же, и сравнение между условиями парное.
        self.food_type = np.zeros((self.H, self.W), dtype=np.int8)
        self.good_type = 1               # при старте питателен цвет +1 (см. предфильтр предка)
        self.switches = []               # тики, на которых менялось правило
        self.last_switch = 0
        self.next_switch = None
        if cfg.food_types == 2:
            self.food_type = self._make_types()
            self._switch_rng = np.random.default_rng(cfg.seed * 7919 + 13)
            if cfg.switch_mean > 0:
                self.next_switch = cfg.switch_from_tick + self._draw_interval()

    def _smooth_field(self, freq):
        """Низкочастотный шум в спектре (без зависимостей): основа для пятен."""
        noise = self.rng.standard_normal((self.H, self.W))
        fy = np.fft.fftfreq(self.H)[:, None]
        fx = np.fft.fftfreq(self.W)[None, :]
        radius = np.sqrt(fy ** 2 + fx ** 2)
        kernel = np.exp(-0.5 * (radius / freq) ** 2)
        smooth = np.real(np.fft.ifft2(np.fft.fft2(noise) * kernel))
        return (smooth - smooth.mean()) / (smooth.std() + 1e-9)

    def _make_capacity(self):
        """Пятна через низкочастотную фильтрацию белого шума в спектре (без зависимостей)."""
        smooth = self._smooth_field(self.cfg.patch_freq)
        cap = np.clip(smooth - self.cfg.patch_threshold, 0.0, None)
        if cap.max() > 0:
            cap /= cap.max()
        return cap.astype(np.float32)

    def _make_types(self):
        """Цвет клетки: знак второго, более мелкозернистого поля. Половина на половину."""
        field = self._smooth_field(self.cfg.type_patch_freq)
        return (field > np.median(field)).astype(np.int8)

    def _draw_interval(self):
        T, j = self.cfg.switch_mean, self.cfg.switch_jitter
        lo, hi = max(1, int(T * (1 - j))), max(2, int(T * (1 + j)))
        return self.t + int(self._switch_rng.integers(lo, hi + 1))

    def switch_rule(self):
        """Сменить правило: питательный тип становится ядовитым и наоборот."""
        self.good_type = 1 - self.good_type
        self.switches.append(self.t)
        self.last_switch = self.t

    def energy_factor(self, y, x):
        """Множитель энергии за съеденное в клетках (y, x): 1 или toxic_factor."""
        if self.cfg.food_types != 2:
            return 1.0
        good = self.food_type[y, x] == self.good_type
        return np.where(good, 1.0, self.cfg.toxic_factor).astype(np.float32)

    def color(self, y, x):
        """Цвет клетки как сенсорный сигнал: -1 / +1. Не говорит, какой съедобен."""
        return (self.food_type[y, x].astype(np.float32) * 2.0 - 1.0)

    @property
    def ticks_since_switch(self):
        return self.t - self.last_switch

    def season(self) -> float:
        if self.cfg.season_period <= 0:
            return 1.0
        phase = 2.0 * np.pi * self.t / self.cfg.season_period
        return 1.0 + self.cfg.season_amplitude * float(np.sin(phase))

    def step(self):
        g = self.cfg.regrowth * max(self.season(), 0.0)
        self.resource += g * (self.capacity - self.resource)
        np.clip(self.resource, 0.0, 1.0, out=self.resource)
        if self.cfg.signs:
            self.signs *= self.cfg.sign_decay
            self.sign_age += 1.0
        self.t += 1
        if self.next_switch is not None and self.t >= self.next_switch:
            self.switch_rule()
            self.next_switch = self._draw_interval()

    @property
    def fertile_fraction(self) -> float:
        return float((self.capacity > 0.01).mean())

    def total_resource(self) -> float:
        return float(self.resource.sum())

    def energy_budget(self):
        """Диагностика перед прогоном: сколько существ мир способен прокормить.

        Приток энергии за тик ≈ regrowth * суммарная ёмкость * энергия за ресурс.
        Расход одного агента ≈ базовый обмен + средняя стоимость действия.
        Если отношение меньше единицы, мир нежизнеспособен в принципе и
        любые «результаты» на нём — артефакт вымирания, а не эволюции.
        """
        cfg = self.cfg
        k_total = float(self.capacity.sum())
        inflow = cfg.regrowth * k_total * cfg.energy_per_resource
        if cfg.food_types == 2:
            # питательна в каждый момент только половина ёмкости
            inflow *= float((self.food_type == self.good_type).mean())
        per_agent = cfg.basal_cost + 0.6 * cfg.move_cost
        return dict(cells_fertile=self.fertile_fraction,
                    capacity_total=k_total,
                    inflow_energy_per_tick=inflow,
                    cost_per_agent_per_tick=per_agent,
                    sustainable_population=inflow / per_agent,
                    init_pop=cfg.init_pop,
                    headroom=inflow / per_agent / max(cfg.init_pop, 1))
