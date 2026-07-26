"""Записать настоящий прогон движка в компактный JSON для веб-проигрывателя.

Пишет позиции/энергию агентов, поле ресурса (даунсемпл), метки и живые
метрики покадрово. Байты пакуются в base64, чтобы страница-артефакт была
самодостаточной (без внешних запросов).
"""
import base64
import json
import numpy as np
from sim import Config, Engine, metrics

SEED = 1
TICKS = 1500
STRIDE = 5           # кадр каждые N тиков
RES_DS = 2           # даунсемпл ресурса 128->64
RES_EVERY = 4        # снимок ресурса каждые N кадров
MI_EVERY = 10        # пересчёт MI каждые N кадров

cfg = Config(seed=SEED, signs=True, mark_cost=0.3, social=True,
             social_from_tick=200, hebbian=True, action_noise=0.02)
eng = Engine(cfg)
H, W = eng.world.H, eng.world.W
rH, rW = H // RES_DS, W // RES_DS

cap = eng.world.capacity
cap_ds = cap.reshape(rH, RES_DS, rW, RES_DS).max(axis=(1, 3))
cap_b64 = base64.b64encode((np.clip(cap_ds, 0, 1) * 255).astype(np.uint8).tobytes()).decode()

agent_bytes = bytearray()
agent_counts = []
mark_bytes = bytearray()
mark_counts = []
res_snaps = bytearray()
res_frames = []
pop_s, meanE_s, coop_s, marks_s, mi_s = [], [], [], [], []

frame = 0
mi_val = 0.0
eng.window_hist[:] = 0
for t in range(TICKS):
    alive = eng.step()
    if not alive:
        break
    if t % STRIDE != 0:
        continue
    ids = eng.pop.ids()
    xs = eng.pop.x[ids].astype(np.uint8)
    ys = eng.pop.y[ids].astype(np.uint8)
    es = np.clip(eng.pop.E[ids] / cfg.e_max * 255, 0, 255).astype(np.uint8)
    packed = np.empty(ids.size * 3, dtype=np.uint8)
    packed[0::3] = xs; packed[1::3] = ys; packed[2::3] = es
    agent_bytes += packed.tobytes()
    agent_counts.append(int(ids.size))

    # активные метки в поле знаков
    field = np.abs(eng.world.signs).sum(axis=2)
    my, mx = np.where(field > 0.02)
    mk = np.empty(my.size * 2, dtype=np.uint8)
    mk[0::2] = mx.astype(np.uint8); mk[1::2] = my.astype(np.uint8)
    mark_bytes += mk.tobytes()
    mark_counts.append(int(my.size))

    # снимок ресурса
    if frame % RES_EVERY == 0:
        r = eng.world.resource
        r_ds = r.reshape(rH, RES_DS, rW, RES_DS).max(axis=(1, 3))
        res_snaps += (np.clip(r_ds, 0, 1) * 255).astype(np.uint8).tobytes()
        res_frames.append(frame)

    # метрики
    st = eng.stats()
    pop_s.append(st["pop"])
    meanE_s.append(round(st["mean_E"], 1))
    coop_s.append(int(eng.coop_events))
    marks_s.append(int(eng.marks_made))
    if frame % MI_EVERY == 0 and frame > 0:
        r = metrics.mi_from_hist(eng.window_hist)
        v = r.get("mi_corrected_bits")
        mi_val = round(float(v), 4) if v is not None else mi_val
        eng.window_hist[:] = 0
    mi_s.append(mi_val)
    frame += 1

out = dict(
    meta=dict(W=W, H=H, rW=rW, rH=rH, resDS=RES_DS, stride=STRIDE,
              nFrames=frame, resEvery=RES_EVERY, socialFrom=cfg.social_from_tick // STRIDE,
              eMax=cfg.e_max, seed=SEED,
              cond="этап 3: интероцепция + социальный слой + знаки + пластичность"),
    cap=cap_b64,
    agents=base64.b64encode(bytes(agent_bytes)).decode(),
    agentCounts=agent_counts,
    marks=base64.b64encode(bytes(mark_bytes)).decode(),
    markCounts=mark_counts,
    res=base64.b64encode(bytes(res_snaps)).decode(),
    resFrames=res_frames,
    pop=pop_s, meanE=meanE_s, coop=coop_s, marksMade=marks_s, mi=mi_s,
)
with open("runs/recording.json", "w") as f:
    json.dump(out, f, separators=(",", ":"))

import os
sz = os.path.getsize("runs/recording.json")
print(f"кадров {frame}, агент-байт {len(agent_bytes)}, метки-байт {len(mark_bytes)}, "
      f"ресурс-снимков {len(res_frames)}")
print(f"recording.json: {sz/1024:.0f} KB")
print(f"финальная популяция {eng.pop.count}, кооп-событий {eng.coop_events}, "
      f"меток {eng.marks_made}")
