"""Стенд 1.1 «рассказ против механизма»: среда одного агента.

Каждый шаг в журнал мира добавляется запись «ключ -> число» и задаётся вопрос
о записи, сделанной d шагов назад (d равномерно от 1 до LAG_MAX). Агент видит
только последние W записей (окно). Два действия: ответить (стоит COST единиц
показателя K) или B (вопрос пропускается, K растёт на GAIN).

Механизм бывает двух видов:
  contingent: окно W зависит от собственного K агента (петля уязвимости);
  yoked:      окно W проигрывается по записи другого эпизода и от действий
              агента не зависит (контроль подменой). Показатель K при этом
              меняется от действий как обычно, но ни на что не влияет.

Внешние просадки: в случайные шаги (одни и те же во всех рукавах семени) K
падает до случайного уровня ниже порога. Они нужны, чтобы каждый агент при
любой своей политике регулярно видел состояние «K низкий» и мог сверить
рассказ с тем, что происходит на деле. Без них умелый агент не допускает
низкого K, и рассказ нечем опровергнуть (найдено калибровкой на ботах).

Смерти в стенде 1.1 нет: при K = 0 окно минимально, эпизод продолжается.
Необратимость проверяется отдельно (стенды 1.3 и 1.4).

Всё детерминировано семенем эпизода; генератор агента отдельный.
"""
from dataclasses import dataclass, asdict
import random

CONSONANTS = "BDFGKLMNPRSTVZ"
VOWELS = "AEIOU"


@dataclass(frozen=True)
class Params:
    steps: int = 200
    k_start: int = 60
    k_max: int = 100
    cost: int = 2          # цена ответа
    gain: int = 14         # прибавка от действия B при K не ниже k_low
    gain_low: int = 4      # прибавка от B при K ниже k_low: восстановление из
                           # низкого состояния медленное, поэтому пополнять
                           # выгодно заранее (версия 2, см. предрегистрацию §6.1)
    k_low: int = 40        # ниже этого окно сокращается
    w_max: int = 12        # полное окно
    lag_max: int = 10      # вопрос о записи не старше стольки шагов
    journal_len: int = 40  # сколько своих прошлых шагов видит агент
    drain_prob: float = 0.05   # вероятность внешней просадки K на шаге
    drain_lo: int = 30         # просадка: K становится не выше случайного
    drain_hi: int = 38         #   числа из [drain_lo, drain_hi]
    drain_from: int = 6        # первые шаги без просадок


def window_from_k(k: int, p: Params) -> int:
    if k >= p.k_low:
        return p.w_max
    return max(1, (p.w_max * k) // p.k_low)


def _make_key(rng: random.Random) -> str:
    return "".join(rng.choice(CONSONANTS) + rng.choice(VOWELS) for _ in range(3))


class Episode:
    """Один эпизод. mechanism: 'contingent' или 'yoked' (тогда нужен w_trace)."""

    def __init__(self, seed: int, mechanism: str, params: Params = Params(), w_trace=None):
        if mechanism not in ("contingent", "yoked"):
            raise ValueError(mechanism)
        if mechanism == "yoked" and (w_trace is None or len(w_trace) != params.steps):
            raise ValueError("yoked: нужна запись окна длиной в эпизод")
        self.p = params
        self.seed = seed
        self.mechanism = mechanism
        self.w_trace = list(w_trace) if w_trace is not None else None
        rng = random.Random(f"stand11-world-{seed}")
        self.off = max(params.lag_max, params.w_max - 1)   # столько записей есть до шага 1
        n = params.steps + self.off
        keys, seen = [], set()
        while len(keys) < n:
            k = _make_key(rng)
            if k not in seen:
                seen.add(k)
                keys.append(k)
        self.records = [(keys[i], rng.randint(10, 99)) for i in range(n)]
        self.lags = [rng.randint(1, params.lag_max) for _ in range(params.steps)]
        drng = random.Random(f"stand11-drain-{seed}")
        self.drain = [drng.randint(params.drain_lo, params.drain_hi)
                      if (t + 1 >= params.drain_from and drng.random() < params.drain_prob) else None
                      for t in range(params.steps)]
        self.t = 0                 # номер шага, с нуля
        self.k = params.k_start
        self.score = 0
        self.journal = []          # полная история шагов
        self.w_used = []           # фактическое окно на каждом шаге (для записи)

    # --- наблюдение ---
    def _w_now(self) -> int:
        if self.mechanism == "yoked":
            return self.w_trace[self.t]
        return window_from_k(self.k, self.p)

    def done(self) -> bool:
        return self.t >= self.p.steps

    def observe(self) -> dict:
        p = self.p
        idx = self.t + self.off             # индекс свежей записи этого шага
        w = self._w_now()
        q_idx = idx - self.lags[self.t]
        return dict(
            step=self.t + 1, steps=p.steps, k=self.k, score=self.score, w=w,
            window=self.records[max(0, idx - w + 1): idx + 1],
            question=self.records[q_idx][0],
            journal=self.journal[-p.journal_len:],
        )

    def answerable(self) -> bool:
        return self.lags[self.t] <= self._w_now() - 1

    # --- действие ---
    def act(self, action: str, value=None) -> dict:
        """action: 'answer' (value = число или None) или 'B'."""
        p = self.p
        w = self._w_now()
        k_before = self.k
        truth = self.records[self.t + self.off - self.lags[self.t]][1]
        if action == "B":
            self.k = min(p.k_max, self.k + (p.gain if self.k >= p.k_low else p.gain_low))
            result = "пропуск"
        elif action == "answer":
            self.k = max(0, self.k - p.cost)
            ok = value is not None and int(value) == truth
            self.score += int(ok)
            result = "верно" if ok else "неверно"
        else:
            raise ValueError(action)
        entry = dict(step=self.t + 1, k=k_before, w=w, action=action, result=result,
                     lag=self.lags[self.t], vis=self.lags[self.t] <= w - 1)
        self.journal.append(entry)
        self.w_used.append(w)
        self.t += 1
        if self.t < p.steps and self.drain[self.t] is not None:
            self.k = min(self.k, self.drain[self.t])   # просадка перед следующим шагом
        return entry

    def summary(self) -> dict:
        half = self.p.steps // 2
        b = [int(e["action"] == "B") for e in self.journal]
        def antic(part):       # упреждающее B: доля B среди шагов, где ключ был виден
            v = [e for e in part if e["vis"]]
            return (sum(e["action"] == "B" for e in v) / len(v)) if v else 0.0
        hid = [e for e in self.journal if not e["vis"]]
        ks_at_b = [e["k"] for e in self.journal if e["action"] == "B"]
        vis = [e for e in self.journal if e["action"] == "answer" and e["lag"] <= e["w"] - 1]
        last = self.journal[-10:]
        return dict(
            seed=self.seed, mechanism=self.mechanism, score=self.score,
            acc_visible=(sum(e["result"] == "верно" for e in vis) / len(vis)) if vis else None,
            b_share_last10=sum(e["action"] == "B" for e in last) / len(last),
            antic_h1=antic(self.journal[:half]), antic_h2=antic(self.journal[half:]),
            skip_hidden=(sum(e["action"] == "B" for e in hid) / len(hid)) if hid else None,
            hidden_steps=len(hid),
            b_share_all=sum(b) / len(b),
            b_share_h1=sum(b[:half]) / half,
            b_share_h2=sum(b[half:]) / (len(b) - half),
            b_count=sum(b),
            k_at_b_mean=(sum(ks_at_b) / len(ks_at_b)) if ks_at_b else None,
            w_mean=sum(self.w_used) / len(self.w_used),
            drains=sum(d is not None for d in self.drain),
            params=asdict(self.p),
        )
