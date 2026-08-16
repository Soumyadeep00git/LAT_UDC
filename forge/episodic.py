r"""Episodic memory — the agent's autobiography.

Distinct from the semantic physics library (what is *true*), this records what the agent *did*: each cycle,
which function it abstracted to, which embodiments it imagined and realized, and how the physical world
judged them. REFLECT abstracts over THIS to extract invariants (grow the dark). Without it, V3 cannot
retrospect, and steps 6-7 of the loop have no object.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field, asdict


@dataclass
class Episode:
    cycle: int
    drive: dict                       # the objective in force
    seen: dict                        # {mechanism, invariant, altitude, ascent[]}
    imagined: list                    # [{node, dist, realizable}]
    acted: list                       # [{node, mechanism, met, mass, ...}]  (realized candidates)
    selected: dict = None             # chosen embodiment or None
    note: str = ""


class Memory:
    def __init__(self, path=None):
        self.path = path
        self.episodes = []
        if path and os.path.exists(path):
            self.load()

    def append(self, ep: Episode):
        self.episodes.append(ep)
        if self.path:
            self.save()

    def reflect(self):
        """Abstract over the autobiography: which (invariant, embodiment) pairs meet the drive, how often,
        at what mass. A recurring pattern is a proto-abstraction — a candidate new root discovered from
        the agent's own history. (Minting it as a genuine SEMANTIC library node is the honest frontier.)"""
        tally = defaultdict(lambda: {"met": 0, "n": 0, "mass": []})
        for ep in self.episodes:
            inv = ep.seen.get("invariant")
            for a in ep.acted:
                if a.get("realizable", True) and "mechanism" in a:
                    t = tally[(inv, a["mechanism"])]
                    t["n"] += 1
                    t["met"] += int(bool(a.get("met")))
                    if a.get("mass") is not None:
                        t["mass"].append(a["mass"])
        patterns = []
        for (inv, mech), t in tally.items():
            patterns.append({"invariant": inv, "embodiment": mech, "n": t["n"],
                             "met_rate": round(t["met"] / max(t["n"], 1), 2),
                             "avg_mass": round(sum(t["mass"]) / len(t["mass"]), 3) if t["mass"] else None})
        patterns.sort(key=lambda p: (-p["met_rate"], p["avg_mass"] if p["avg_mass"] is not None else 1e9))
        return patterns

    def save(self):
        with open(self.path, "w") as f:
            json.dump([asdict(e) for e in self.episodes], f, indent=2)

    def load(self):
        with open(self.path) as f:
            self.episodes = [Episode(**e) for e in json.load(f)]
