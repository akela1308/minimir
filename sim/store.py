"""Логи в SQLite, геномы в npz. Один seed -> один воспроизводимый прогон."""
import json
import sqlite3
import time
from pathlib import Path
import numpy as np


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT, started REAL, config TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS ticks (
    run_id INTEGER, tick INTEGER, pop INTEGER, mean_E REAL, mean_age REAL,
    max_age INTEGER, births INTEGER, deaths INTEGER, resource REAL,
    lineages INTEGER, forage_accuracy REAL, coop_rate REAL, mi_window REAL
);
CREATE INDEX IF NOT EXISTS ix_ticks ON ticks(run_id, tick);
CREATE TABLE IF NOT EXISTS results (
    run_id INTEGER, key TEXT, value TEXT
);
"""


class Store:
    def __init__(self, path="runs/minimir.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path)
        self.con.executescript(SCHEMA)
        self.con.commit()
        self.run_id = None

    def start_run(self, cfg, label="", notes=""):
        cur = self.con.execute(
            "INSERT INTO runs (label, started, config, notes) VALUES (?,?,?,?)",
            (label, time.time(), cfg.to_json(), notes))
        self.con.commit()
        self.run_id = cur.lastrowid
        return self.run_id

    def log(self, engine):
        """Пишем срез и считаем MI за окно — чтобы видеть выход на плато."""
        from .metrics import mi_from_hist
        s = engine.stats()
        w = mi_from_hist(engine.window_hist)
        engine.window_hist[:] = 0
        self.con.execute(
            "INSERT INTO ticks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (self.run_id, s["tick"], s["pop"], s["mean_E"], s["mean_age"],
             s["max_age"], s["births"], s["deaths"], s["resource"],
             s["lineages"], s["forage_accuracy"], s["coop_rate"],
             w.get("mi_corrected_bits")))

    def result(self, key, value):
        self.con.execute("INSERT INTO results VALUES (?,?,?)",
                         (self.run_id, key, json.dumps(value)))
        self.con.commit()

    def snapshot(self, engine, tag):
        ids = engine.pop.ids()
        out = self.path.parent / f"run{self.run_id}_{tag}.npz"
        np.savez_compressed(
            out,
            genomes=engine.pop.brains.genome_matrix(ids),
            energy=engine.pop.E[ids], age=engine.pop.age[ids],
            lineage=engine.pop.lineage[ids], face=engine.pop.face[ids],
            capacity=engine.world.capacity)
        return out

    def close(self):
        self.con.commit()
        self.con.close()
