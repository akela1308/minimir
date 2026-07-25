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

    def _make_capacity(self):
        """Пятна через низкочастотную фильтрацию белого шума в спектре (без зависимостей)."""
        noise = self.rng.standard_normal((self.H, self.W))
        fy = np.fft.fftfreq(self.H)[:, None]
        fx = np.fft.fftfreq(self.W)[None, :]
        radius = np.sqrt(fy ** 2 + fx ** 2)
        kernel = np.exp(-0.5 * (radius / self.cfg.patch_freq) ** 2)
        smooth = np.real(np.fft.ifft2(np.fft.fft2(noise) * kernel))
        smooth = (smooth - smooth.mean()) / (smooth.std() + 1e-9)
        cap = np.clip(smooth - self.cfg.patch_threshold, 0.0, None)
        if cap.max() > 0:
            cap /= cap.max()
        return cap.astype(np.float32)

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
        per_agent = cfg.basal_cost + 0.6 * cfg.move_cost
        return dict(cells_fertile=self.fertile_fraction,
                    capacity_total=k_total,
                    inflow_energy_per_tick=inflow,
                    cost_per_agent_per_tick=per_agent,
                    sustainable_population=inflow / per_agent,
                    init_pop=cfg.init_pop,
                    headroom=inflow / per_agent / max(cfg.init_pop, 1))
