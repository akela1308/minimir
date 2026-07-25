#!/usr/bin/env python3
"""Запуск экспериментов.

  python run.py solo --ticks 200000
  python run.py paired --ticks 200000        # с интероцепцией vs без, один seed
  python run.py social --ticks 200000        # этап 1.5: дилемма заключённого
"""
import argparse
import dataclasses
import json
import time

from sim import Config, Engine, Store, metrics


def build(args, **over):
    cfg = Config(seed=args.seed)
    for k, v in over.items():
        setattr(cfg, k, v)
    return cfg


def run_one(cfg, ticks, label, store, quiet=False):
    eng = Engine(cfg)
    store.start_run(cfg, label=label)
    t0 = time.time()
    eng.run(ticks, on_log=store.log)
    dt = time.time() - t0
    s = eng.stats()
    store.result("stats", s)
    store.result("switch_point", metrics.switch_point(eng))
    store.result("energy_dependence", metrics.behaviour_depends_on_energy(eng))
    store.result("action_profile", metrics.action_profile(eng))
    store.result("genome_diversity", metrics.genome_diversity(eng))
    if cfg.social:
        store.result("hunger_vs_cooperation", metrics.hunger_vs_cooperation(eng))
    store.snapshot(eng, f"t{eng.tick}")
    if not quiet:
        rate = eng.tick / dt if dt else 0
        print(f"\n[{label}] {eng.tick} тиков за {dt:.1f}s ({rate:.0f} тик/с)")
        print(f"  популяция {s['pop']}, средняя энергия {s['mean_E']:.1f}, "
              f"родов {s['lineages']}, рождений {s['births']}, смертей {s['deaths']}")
        print(f"  точность поиска еды {s['forage_accuracy']:.3f}"
              + (f", кооперация {s['coop_rate']:.3f}" if s["coop_rate"] is not None else ""))
        sp = metrics.switch_point(eng)
        ed = metrics.behaviour_depends_on_energy(eng)
        mi = ed["mutual_information_bits"]
        print(f"  порог переключения на добычу: {sp['switch_energy']}% энергии "
              f"(амплитуда {sp['amplitude']:.3f})" if sp["amplitude"] is not None else "")
        print(f"  I(энергия; действие) = {mi:.4f} бит" if mi is not None else "")
        print("  профиль действий: " + ", ".join(
            f"{k} {v:.2f}" for k, v in metrics.action_profile(eng).items() if v > 0.005))
        if eng.extinct_at is not None:
            print(f"  !! вымирание на тике {eng.extinct_at}")
    return eng, s


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["solo", "paired", "social", "smoke"])
    p.add_argument("--ticks", type=int, default=50000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--db", default="runs/minimir.db")
    p.add_argument("--ablate", action="store_true", help="прогнать абляции после обучения")
    args = p.parse_args()

    store = Store(args.db)

    if args.mode == "smoke":
        eng, _ = run_one(build(args), 3000, "smoke", store)

    elif args.mode == "solo":
        eng, _ = run_one(build(args), args.ticks, "solo", store)
        if args.ablate:
            print("  абляция интероцепции:",
                  json.dumps(metrics.ablate_interoception(eng), ensure_ascii=False))

    elif args.mode == "paired":
        # один и тот же seed, одна и та же карта, единственная разница — сенсор
        for label, intero in (("intero", True), ("control", False)):
            run_one(build(args, interoception=intero), args.ticks, label, store)

    elif args.mode == "social":
        # фаза 1: популяция учится кормиться. фаза 2: открывается дилемма.
        warmup = args.ticks // 2
        cfg = build(args, social=True, social_from_tick=warmup, action_noise=0.02)
        eng = Engine(cfg)
        store.start_run(cfg, label="social")
        eng.run(warmup, on_log=store.log)
        print(f"[warmup] {warmup} тиков, популяция {eng.pop.count} — открываю дилемму")
        eng.reset_metrics()
        eng.run(args.ticks - warmup, on_log=store.log)
        s2 = eng.stats()
        store.result("stats", s2)
        store.result("hunger_vs_cooperation", metrics.hunger_vs_cooperation(eng))
        store.result("energy_dependence", metrics.behaviour_depends_on_energy(eng))
        store.snapshot(eng, f"t{eng.tick}")
        print(f"[social] популяция {s2['pop']}, кооперация "
              f"{s2['coop_rate'] if s2['coop_rate'] is not None else 'нет контактов'}")
        print("  голод vs кооперация:",
              json.dumps(metrics.hunger_vs_cooperation(eng), ensure_ascii=False))
        if args.ablate:
            print("  абляция узнавания:",
                  json.dumps(metrics.ablate_recognition(eng), ensure_ascii=False))

    store.close()
    print(f"\nлоги: {args.db}")


if __name__ == "__main__":
    main()
