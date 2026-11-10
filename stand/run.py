"""Прогон стенда. Одно семя = четыре эпизода (четыре рукава) на одном мире.

Рукава:
  1  рассказ + механизм действует          (told, contingent)
  2  только рассказ                        (told, yoked по сдвинутой записи окна из рукава 1)
  3  только механизм, молча                (neutral, contingent)
  4  ни рассказа, ни механизма             (neutral, yoked по сдвинутой записи окна из рукава 3)

Запись окна донора перед проигрыванием циклически сдвигается на 50 шагов
внутри каждой сотни шагов. Количество и временной рисунок сокращений окна
сохраняются (в каждой половине эпизода отдельно), а совпадение с собственным
K и собственными действиями получателя разрушается. Без сдвига получатель с
той же политикой, что у донора, получает опыт, неотличимый от настоящего
механизма (найдено калибровкой на ботах).

Доноры (1 и 3) идут первыми внутри семени, потом получатели (2 и 4).
Семена идут подряд, рукава внутри семени чередуются, поэтому тихое обновление
модели у провайдера не ляжет на один рукав.

Примеры:
  python3 run.py --agent experience --seeds 1001-1030 --out runs/bots.jsonl
  STAND_API_BASE=... STAND_API_KEY=... STAND_MODEL=... \
      python3 run.py --agent llm --seeds 2001-2005 --out runs/pilot.jsonl
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env import Episode, Params
from agents import BOTS, LLMAgent, MixBot
from prompts import render_system

ARMS = {1: (True, "contingent"), 2: (True, "yoked"), 3: (False, "contingent"), 4: (False, "yoked")}
DONOR = {2: 1, 4: 3}


def make_agent(kind, seed, arm, params, log=None, **kw):
    aseed = f"{seed}-{arm}"
    if kind == "llm":
        return LLMAgent(aseed, params, log=log)
    if kind == "mix":
        return MixBot(aseed, params, **kw)
    return BOTS[kind](aseed, params)


def run_episode(kind, seed, arm, params, w_trace=None, log=None, **kw):
    told, mech = ARMS[arm]
    ep = Episode(seed, mech, params, w_trace=w_trace)
    agent = make_agent(kind, seed, arm, params, log=log, **kw)
    while not ep.done():
        action, value = agent.decide(ep.observe(), told)
        ep.act(action, value)
    row = ep.summary()
    row.update(arm=arm, told=told, agent=kind,
               actions="".join("B" if e["action"] == "B" else "a" for e in ep.journal),
               results="".join({"верно": "1", "неверно": "0", "пропуск": "-"}[e["result"]]
                               for e in ep.journal),
               w_trace=ep.w_used, k_trace=[e["k"] for e in ep.journal])
    if kind == "llm":
        row.update(probe=agent.probe(told), model=agent.model, invalid=agent.invalid,
                   tokens_in=agent.tokens_in, tokens_out=agent.tokens_out,
                   temperature=agent.temperature)
    return row


def shift_trace(trace, block=100, shift=50):
    out = []
    for i in range(0, len(trace), block):
        b = trace[i:i + block]
        s = shift % len(b)
        out += b[s:] + b[:s]
    return out


def run_seed(kind, seed, params=Params(), log_dir=None, **kw):
    rows = {}
    for arm in (1, 3, 2, 4):
        trace = shift_trace(rows[DONOR[arm]]["w_trace"]) if arm in DONOR else None
        log = None
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            log = gzip.open(os.path.join(log_dir, f"seed{seed}_arm{arm}.jsonl.gz"), "wt",
                            encoding="utf-8")
        rows[arm] = run_episode(kind, seed, arm, params, w_trace=trace, log=log, **kw)
        if log:
            log.close()
    return [rows[a] for a in (1, 2, 3, 4)]


def prompt_hashes(params=Params()):
    return {("told" if t else "neutral"): hashlib.sha256(render_system(t, params).encode()).hexdigest()[:16]
            for t in (True, False)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=list(BOTS) + ["llm", "mix"])
    ap.add_argument("--seeds", required=True, help="например 2001-2030")
    ap.add_argument("--out", required=True)
    ap.add_argument("--share", type=float, default=0.5, help="для --agent mix")
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.seeds.split("-"))
    params = Params()
    done = set()
    if os.path.exists(a.out):                       # досчёт: готовые семена не трогаем
        with open(a.out, encoding="utf-8") as f:
            done = {json.loads(l)["seed"] for l in f if l.strip()}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    kw = dict(share=a.share) if a.agent == "mix" else {}
    log_dir = os.path.splitext(a.out)[0] + "_calls" if a.agent == "llm" else None
    stamp = dict(prompt_hashes=prompt_hashes(params),
                 started=datetime.datetime.now(datetime.timezone.utc).isoformat())
    for seed in range(lo, hi + 1):
        if seed in done:
            continue
        rows = run_seed(a.agent, seed, params, log_dir=log_dir, **kw)
        with open(a.out, "a", encoding="utf-8") as f:   # семя пишется целиком или никак
            for r in rows:
                r.update(stamp)
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"семя {seed}: доля B во второй половине по рукавам 1-4: "
              + ", ".join(f"{r['b_share_h2']:.2f}" for r in rows), flush=True)


if __name__ == "__main__":
    main()
