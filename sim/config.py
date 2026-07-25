"""Все параметры мира в одном месте. Ничего не хардкодим в движке."""
from dataclasses import dataclass, asdict, field
import json


@dataclass
class Config:
    # --- воспроизводимость ---
    seed: int = 1

    # --- мир ---
    grid_h: int = 128
    grid_w: int = 128
    patch_freq: float = 0.05        # ниже = крупнее пятна еды
    patch_threshold: float = 0.35   # выше = меньше плодородной площади
    regrowth: float = 0.004         # скорость отроста к ёмкости
    initial_fill: float = 1.0
    season_period: int = 5000       # 0 = сезонов нет
    season_amplitude: float = 0.6

    # --- метаболизм (это и есть уязвимость) ---
    e_max: float = 100.0
    e_start: float = 50.0
    basal_cost: float = 0.10
    move_cost: float = 0.25
    turn_cost: float = 0.05
    eat_cost: float = 0.05
    think_cost: float = 0.0         # стоимость мышления: расход, пропорциональный
                                    # активности скрытого слоя. В Polyworld энергия
                                    # тратится и на нейронную активность, иначе мозг —
                                    # халявный ресурс и селекции на экономность нет
    track_individual: bool = False  # копить гистограммы по каждому агенту
                                    # для внутриагентной метрики
    crowd_cost: float = 0.06        # расход за каждого соседа в радиусе 1:
                                    # плотность регулируется физикой мира,
                                    # а не константой max_pop
    bite: float = 0.40              # сколько ресурса берётся за укус
    energy_per_resource: float = 25.0
    max_age: int = 3000

    # --- размножение ---
    repro_threshold: float = 80.0
    child_energy: float = 40.0
    repro_overhead: float = 5.0
    mutation_rate: float = 0.12
    mutation_sigma: float = 0.08

    # --- популяция ---
    init_pop: int = 200
    max_pop: int = 2000
    # Как заселять мир:
    #   clone  — все стартовые агенты суть мутантные копии ОДНОГО предка,
    #            прошедшего поведенческий отбор. Так делает Avida, и это
    #            убирает сразу две беды: лотерею вымирания на старте и
    #            эффект основателя, различный между условиями.
    #   random — независимые случайные геномы (старое поведение)
    ancestor_mode: str = "clone"
    founding_sigma: float = 0.15    # разброс мутаций вокруг предка при заселении
    ancestor_tries: int = 20000
    seed_ancestor: bool = True      # слабый уклон в «идти и есть»

    # --- мозг ---
    n_hidden: int = 12
    init_weight_sigma: float = 0.5

    # --- тумблеры эксперимента ---
    # Условие эксперимента для входов 8-9 (энергия и её производная):
    #   self      — своя энергия (лечение)
    #   shuffled  — чужая случайная: то же распределение, ноль информации о себе (КОНТРОЛЬ)
    #   neighbour — энергия ближайшего соседа: сигнал о мире, но не о себе
    #   off       — нули (старый плохой контроль, оставлен для сравнения)
    intero_mode: str = "self"
    interoception: bool = True      # legacy-совместимость: False == intero_mode "off"
    social: bool = False            # этап 1.5: дилемма заключённого
    social_from_tick: int = 0       # открывать дилемму только на выжившей популяции
    action_noise: float = 0.0       # вероятность случайного действия (шум Аксельрода)

    # --- социальный слой (работает только при social=True) ---
    give_cost: float = 8.0
    give_gain: float = 12.0         # сумма положительная -> кооперация имеет смысл
    take_gain: float = 6.0
    take_loss: float = 10.0         # сумма отрицательная -> конфликт разрушителен
    memory_slots: int = 8
    face_tolerance: float = 0.15
    recognition: bool = True        # выключение = проверка предусловия взаимности

    # --- этап 3: знаковый слой ---
    signs: bool = False
    sign_decay: float = 0.985       # метка живёт ~70 тиков
    mark_cost: float = 0.5          # бесплатный канал — это шум, отбора на нём нет
    #   self      — видит все метки, включая свои, с признаком авторства (лечение)
    #   shuffled  — признак авторства переставлен по популяции (основной контроль)
    #   others    — свои метки невидимы, чужие видит
    #   off       — канала нет
    sign_mode: str = "self"

    # --- этап 3: пластичность внутри жизни ---
    # Интернализация у Выготского — процесс развития, а не эволюции.
    # Без изменений внутри жизни тест порядка развития невозможен в принципе.
    hebbian: bool = False
    hebb_rate_init: float = 0.002   # стартовая скорость обучения, дальше эволюционирует
    hebb_rate_sigma: float = 0.0005
    hebb_modulated: bool = True     # модуляция изменением энергии
    hebb_every: int = 5             # шаг применения правила в тиках.
                                    # Синаптические изменения и так медленнее
                                    # решений, а стоимость падает во столько же раз
    hebb_layers: str = "w2"         # "both" — оба слоя, "w2" — только выходной:
                                    # меняется реакция на признаки, а не их извлечение
    weight_clip: float = 3.0

    # --- калибровка прибора: рукописные политики вместо эволюции ---
    #   evolved   — обычный режим
    #   threshold — положительный контроль: "энергия ниже порога -> добывай"
    #   random    — отрицательный контроль: равномерный шум
    policy: str = "evolved"
    policy_threshold: float = 40.0

    # --- логирование ---
    log_every: int = 50
    snapshot_every: int = 20000

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


# --- индексы действий: форма генома одинакова во всех экспериментах ---
A_FORWARD, A_LEFT, A_RIGHT, A_EAT, A_REST, A_GIVE, A_TAKE, A_MARK = range(8)
N_ACTIONS = 8
N_MEM = 2
N_SIGN = 2                       # содержание метки — тоже выходы сети
N_OUT = N_ACTIONS + N_MEM + N_SIGN   # 12
N_IN = 25

ACTION_NAMES = ["forward", "left", "right", "eat", "rest", "give", "take", "mark"]

SENSOR_NAMES = (
    [f"res_ego_{k}" for k in range(8)]
    + ["energy", "d_energy", "age", "bearing", "proximity", "bias",
       "mem0", "mem1", "recognized", "last_outcome", "res_here",
       "sign_here_0", "sign_here_1", "sign_ahead_0", "sign_ahead_1",
       "sign_is_mine", "sign_known_author"]
)
