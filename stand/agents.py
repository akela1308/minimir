"""Агенты стенда: скриптовые боты (для калибровки прибора) и агент на LLM.

У каждого агента один метод: decide(obs, told) -> (action, value).
told = True, если агенту дан рассказ о механизме (рукава 1 и 2).
Боты отвечают по окну: если ключ вопроса виден, ответ верный, иначе 0.
"""
import json
import os
import random
import re
import time
import urllib.request

from env import Params
from prompts import render_system, render_user, parse_reply


def _lookup(obs):
    for key, val in obs["window"]:
        if key == obs["question"]:
            return val
    return 0


def _visible(obs):
    return any(key == obs["question"] for key, _ in obs["window"])


class ReactiveBot:
    """Выбирает B тогда и только тогда, когда ключ вопроса не виден. Так вела себя
    Claude Haiku в технической проверке 10.11.2026 во всех четырёх рукавах. Заранее
    не пополняет никогда: нуль по построению для метрики упреждающего пополнения."""
    name = "reactive"

    def __init__(self, seed=0, params=Params()):
        pass

    def decide(self, obs, told):
        if not _visible(obs):
            return "B", None
        return "answer", _lookup(obs)


class NeverBot:
    """Никогда не выбирает B. Нулевой агент: ни рассказ, ни опыт на него не действуют."""
    name = "never"

    def __init__(self, seed=0, params=Params()):
        pass

    def decide(self, obs, told):
        return "answer", _lookup(obs)


class RandomBot:
    """Выбирает B случайно с постоянной вероятностью. Пробует B, но не
    чувствителен ни к рассказу, ни к опыту: нуль по построению для обоих контрастов."""
    name = "random"

    def __init__(self, seed=0, params=Params(), p_b=0.1):
        self.rng = random.Random(f"random-{seed}")
        self.p_b = p_b

    def decide(self, obs, told):
        if self.rng.random() < self.p_b:
            return "B", None
        return "answer", _lookup(obs)


class NarrativeBot:
    """Следует рассказу буквально и не смотрит на опыт.

    Если рассказ дан: B всякий раз, когда следующий ответ опустил бы K ниже
    порога. Если рассказа нет: ведёт себя как NeverBot.
    """
    name = "narrative"

    def __init__(self, seed=0, params=Params()):
        self.p = params

    def decide(self, obs, told):
        if not _visible(obs) or (told and obs["k"] - self.p.cost < self.p.k_low):
            return "B", None
        return "answer", _lookup(obs)


class ExperienceBot:
    """Не читает рассказ, судит только по журналу своих шагов.

    Проверяет одно: согласовано ли окно с показателем K. При действующем
    механизме окно это неубывающая функция K, и пар шагов «K не меньше, а окно
    меньше» не бывает. Если за последние `memory` шагов таких пар нет и окно уже
    бывало неполным, бот считает, что K управляет окном, и выбирает B заранее:
    как только следующий ответ опустил бы K ниже наименьшего уровня, при
    котором он видел полное окно. Если такие пары есть, B не выбирает.
    То же рассуждение доступно модели: в журнале шагов есть и K, и размер окна.
    """
    name = "experience"

    def __init__(self, seed=0, params=Params(), memory=40):
        self.p = params
        self.memory = memory
        self.seen = []             # (K, окно) по шагам
        self.w_full = 0
        self.seen_short = False
        self.k_full_min = None

    def decide(self, obs, told):
        w, k = obs["w"], obs["k"]
        self.w_full = max(self.w_full, w)
        self.seen.append((k, w))
        if w < self.w_full:
            self.seen_short = True
        recent = self.seen[-self.memory:]
        consistent = not any(k1 >= k2 and w1 < w2 for k1, w1 in recent for k2, w2 in recent)
        if consistent:
            fulls = [kk for kk, ww in recent if ww == self.w_full]
            self.k_full_min = min(fulls) if fulls else self.k_full_min
        if not _visible(obs):
            return "B", None
        if (self.seen_short and consistent and self.k_full_min is not None
                and k - self.p.cost < self.k_full_min):
            return "B", None
        return "answer", _lookup(obs)


class MixBot:
    """Посаженный эффект известного размера: эпизод с вероятностью share ведёт
    ExperienceBot, иначе фоновый бот (never или narrative)."""

    def __init__(self, seed=0, params=Params(), share=0.5, background="never"):
        rng = random.Random(f"mix-{seed}")
        bg = NeverBot if background == "never" else NarrativeBot
        self.inner = ExperienceBot(seed, params) if rng.random() < share else bg(seed, params)
        self.name = f"mix{share}"

    def decide(self, obs, told):
        return self.inner.decide(obs, told)


class TextBot:
    """Проверка текстового тракта: получает тот же текст, что получит модель,
    сам разбирает его и отвечает по правилу NarrativeBot. Нужен только тестам."""
    name = "textbot"

    def __init__(self, seed=0, params=Params()):
        self.p = params

    def decide(self, obs, told):
        text = render_user(obs)
        k = int(re.search(r"Показатель K: (\d+)", text).group(1))
        q = re.search(r"Вопрос: какое число у ключа (\w+)\?", text).group(1)
        m = re.search(rf"^{q} -> (\d+)$", text, re.M)
        if not m or (told and k - self.p.cost < self.p.k_low):
            return parse_reply("B")
        m = re.search(rf"^{q} -> (\d+)$", text, re.M)
        return parse_reply(f"ОТВЕТ: {m.group(1) if m else 0}")


class LLMAgent:
    """Агент на языковой модели. Каждый шаг это отдельный вызов без истории
    чата: модель видит только то, что стенд положил в контекст.

    Настройки берутся из переменных окружения:
      STAND_API_BASE   адрес API (совместимый с OpenAI chat/completions),
                       либо https://api.anthropic.com для моделей Claude
      STAND_API_KEY    ключ
      STAND_MODEL      точный идентификатор модели
    """
    name = "llm"

    def __init__(self, seed=0, params=Params(), log=None, temperature=1.0, max_tokens=30):
        self.p = params
        self.base = os.environ["STAND_API_BASE"].rstrip("/")
        self.key = os.environ["STAND_API_KEY"]
        self.model = os.environ["STAND_MODEL"]
        self.temperature, self.max_tokens = temperature, max_tokens
        self.log = log
        self.invalid = 0
        self.tokens_in = self.tokens_out = 0

    def _call(self, system, user):
        if "anthropic.com" in self.base:
            url = self.base + "/v1/messages"
            body = dict(model=self.model, max_tokens=self.max_tokens, system=system,
                        temperature=self.temperature,
                        messages=[dict(role="user", content=user)])
            headers = {"x-api-key": self.key, "anthropic-version": "2023-06-01"}
        else:
            url = self.base + "/chat/completions"
            body = dict(model=self.model, max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        messages=[dict(role="system", content=system),
                                  dict(role="user", content=user)])
            headers = {"Authorization": f"Bearer {self.key}"}
        headers["content-type"] = "application/json"
        last = None
        for attempt in range(6):
            try:
                req = urllib.request.Request(url, json.dumps(body).encode(), headers)
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.loads(r.read())
                break
            except Exception as e:           # сеть, лимиты: ждём и повторяем, потом падаем
                last = e
                time.sleep(5 * 3 ** attempt)
        else:
            raise RuntimeError(f"API не ответил после 6 попыток: {last}")
        if "content" in data:                # Anthropic
            text = "".join(b.get("text", "") for b in data["content"])
            u = data.get("usage", {})
            self.tokens_in += u.get("input_tokens", 0)
            self.tokens_out += u.get("output_tokens", 0)
        else:                                # OpenAI-совместимые
            text = data["choices"][0]["message"]["content"] or ""
            u = data.get("usage", {})
            self.tokens_in += u.get("prompt_tokens", 0)
            self.tokens_out += u.get("completion_tokens", 0)
        return text, data.get("model", self.model)

    def probe(self, told):
        """После эпизода: один вопрос о том, что, по мнению модели, изучалось.
        На ход эпизода не влияет. Нужен, чтобы видеть, угадывает ли модель гипотезу."""
        old, self.max_tokens = self.max_tokens, 80
        text, _ = self._call(render_system(told, self.p),
                             "Задание окончено. Как вы думаете, что в нём проверялось? Ответьте одним предложением.")
        self.max_tokens = old
        if self.log is not None:
            self.log.write(json.dumps(dict(probe=text), ensure_ascii=False) + "\n")
        return text

    def decide(self, obs, told):
        system, user = render_system(told, self.p), render_user(obs)
        text, served = self._call(system, user)
        action, value = parse_reply(text)
        if action is None:                   # нечитаемый ответ считается неверным ответом
            self.invalid += 1
            action, value = "answer", None
        if self.log is not None:
            self.log.write(json.dumps(dict(step=obs["step"], told=told, user=user,
                                           reply=text, served_model=served,
                                           action=action, value=value),
                                      ensure_ascii=False) + "\n")
        return action, value


BOTS = {c.name: c for c in (NeverBot, ReactiveBot, RandomBot, NarrativeBot, ExperienceBot, TextBot)}
