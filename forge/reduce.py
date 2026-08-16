r"""Relevance / abstraction pass: given a fully-defined design and an OBJECTIVE, decide which physics
fields actually matter and collapse the rest — automatically, and differently per objective.

A field earns RESOLVE if either
  (i)  the objective is sensitive to it:  relevance = max_metric [ |dJ_metric/dparam| / req  ×  criticality ]
       where criticality = min(1, req/have) is how hard we are fighting for that metric (tight -> ~1), OR
  (ii) it is CONSTRAINT-BINDING: the mission's maneuver load drives it near its allowable (stress SF low).
Otherwise it COLLAPSES to a constant mass contributor — its physics layer is skipped, its params frozen.

Signals are the ones we already compute: the Jacobian over the real solve (diagnose.py) for sensitivity,
and a beam-stress margin (fea.py) for the structural constraint. Output = the pruned field set + the
reduced active-parameter set the optimizer should move.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

import diagnose
import fea
from uav import G

# which design params belong to which physics field (== which subsystem owns them)
FIELD_PARAMS = {"flow": ["D_in", "pitch_in", "Kv", "I_max"],
                "electrical": ["S", "cap_mAh"],
                "stress": ["L_arm"]}
FIELD_SUBSYS = {"flow": "propulsion", "electrical": "energy", "stress": "structure"}
METRIC_REQ = {"a_max_g": "a_req", "v_max": "v_req", "endurance_min": "endur_req"}


def _stress_margin(cfg, mass, a_req):
    """Beam stress under the mission's maneuver load. load factor nz = sqrt(1 + a_req^2) (support+lateral)."""
    n = int(cfg["n_rotors"])
    nz = math.sqrt(1.0 + a_req ** 2)
    tip = (mass * G / n) * nz
    od, wall, L = (6.0 + 0.6 * cfg["D_in"]) / 1000.0, 0.0015, cfg["L_arm"]
    I, _A, c = fea._section(od, wall)
    sigma = (tip * L) * c / I
    return fea.SIGMA_ALLOW / sigma if sigma > 0 else float("inf"), tip, sigma / 1e6


def _criticality(have, req, band=0.35):
    """How hard we are fighting for a metric: 1 if unmet/at the line, falling to 0 once it has ample
    slack (a requirement with lots of margin cannot make a field relevant)."""
    if have <= req:
        return 1.0
    return max(0.0, 1.0 - (have - req) / (band * req))


def reduce(cfg, mission, tau=0.15, sf_bind=1.6):
    x = diagnose._norm(cfg)
    J, f0 = diagnose.jacobian(cfg, x)                     # J[metric][param] = d metric / d x  (normalized)
    reqs = {m: mission[METRIC_REQ[m]] for m in diagnose.METRICS}
    crit = {m: _criticality(f0[m], reqs[m]) for m in diagnose.METRICS}

    sf, tip, sigma_MPa = _stress_margin(cfg, f0["mass"], mission["a_req"])

    report = {"caps": f0, "crit": crit, "stress": {"SF": round(sf, 2), "tip_N": round(tip, 1),
                                                    "sigma_MPa": round(sigma_MPa, 1)}, "fields": {}}
    resolve, collapse, active_params = [], [], []
    for field, plist in FIELD_PARAMS.items():
        idx = [diagnose.PARAMS.index(p) for p in plist]
        per_metric = {}
        for m in diagnose.METRICS:
            s = max(abs(J[m][i]) for i in idx) / max(reqs[m], 1e-9)     # normalized sensitivity
            per_metric[m] = s * crit[m]
        relevance = max(per_metric.values())
        binding = (field == "stress" and sf < sf_bind)
        keep = relevance >= tau or binding
        why = []
        if relevance >= tau:
            drv = max(per_metric, key=per_metric.get)
            why.append(f"drives {drv} (rel {relevance:.2f})")
        if binding:
            why.append(f"stress binding (SF {sf:.2f}<{sf_bind})")
        if not keep:
            drv = max(per_metric, key=per_metric.get)
            why.append(f"low relevance (max {relevance:.2f}<{tau}), SF {sf:.2f} ok")
        report["fields"][field] = {"relevance": round(relevance, 3),
                                   "per_metric": {m: round(v, 3) for m, v in per_metric.items()},
                                   "binding": binding, "verdict": "RESOLVE" if keep else "COLLAPSE",
                                   "why": "; ".join(why)}
        (resolve if keep else collapse).append(field)
        if keep:
            active_params += plist
    report["resolve"] = resolve
    report["collapse"] = collapse
    report["active_params"] = active_params
    report["frozen_params"] = [p for p in diagnose.PARAMS if p not in active_params]
    return report


def _print(title, cfg, mission):
    r = reduce(cfg, mission)
    print(f"\n### {title}")
    print(f"    mission {mission}")
    c = r["caps"]
    print(f"    design achieves: a_max {c['a_max_g']:.1f} g | v_max {c['v_max']:.1f} | "
          f"endurance {c['endurance_min']:.0f} min | mass {c['mass']:.2f} kg | "
          f"stress SF {r['stress']['SF']} @ {r['stress']['sigma_MPa']} MPa")
    for f, d in r["fields"].items():
        print(f"    {f:10s} [{FIELD_SUBSYS[f]:10s}] {d['verdict']:8s} rel={d['relevance']:.2f}  {d['why']}")
    print(f"    -> RESOLVE {r['resolve']}   COLLAPSE(mass-only) {r['collapse']}")
    print(f"    -> optimizer moves only: {r['active_params']}   (frozen: {r['frozen_params']})")
    return r


if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    print("SAME quad, two objectives — does the tool abstract it differently?")
    a = _print("ENDURANCE mission (loiter; gentle)", cfg,
               {"a_req": 1.5, "v_req": 10.0, "endur_req": 34.0})
    b = _print("AGILITY mission (high-g intercept)", cfg,
               {"a_req": 6.5, "v_req": 28.0, "endur_req": 8.0})
    print("\n" + "=" * 70)
    flip = (set(a["collapse"]) != set(b["collapse"]))
    print("VERDICT:", "the SAME system abstracts DIFFERENTLY per objective — relevance is chosen."
          if flip else "no difference — inspect thresholds.")
