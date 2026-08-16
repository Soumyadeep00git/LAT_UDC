r"""Unified escalating optimizer (Step 2): V1 -> V2 -> V3-generative, each firing when the last exhausts.

  V1  tune params (diagnose.repair)
  V2  count/field rearrangement ON TOP of V1 (physics_adapt.adapt)
  V3  when V1/V2 can't meet it: dissolve to the actuator field, reshape it (v3_spatial), quantify the
      transcendent form's PROMISE, and realize it if a model exists — else flag the invention frontier
      with a quantified target (honest: the beneficial ring/duct embodiment needs a manufacturable model).

This is the ladder wired as ONE call, so "which tier" is a result, not three code paths.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

import diagnose
import physics_adapt
import v3_spatial
from uav import build_uav, capabilities, G
from solve import solve

SEED = {"current": 0.0, "total_mass": 4.0}
_REQMAP = (("a_max_g", "a_req"), ("v_max", "v_req"), ("endurance_min", "endur_req"))


def _met(caps, mission):
    return all(caps[m] >= mission[r] - 1e-6 for m, r in _REQMAP)


def escalate(cfg, mission):
    log = []

    # V1 --------------------------------------------------------------
    c1 = diagnose.repair(cfg, mission)[0]
    caps1 = diagnose.caps_of(c1)
    log.append(("V1  params", _met(caps1, mission), caps1))
    if _met(caps1, mission):
        return "V1", c1, caps1, log

    # V2 --------------------------------------------------------------
    b2, _, _ = physics_adapt.adapt(cfg, mission)
    caps2 = b2["caps"]
    log.append((f"V2  count({b2['n']})+params", b2["feasible"], caps2))
    if b2["feasible"]:
        return "V2", b2["cfg"], caps2, log

    # V3 generative ---------------------------------------------------
    base = b2["cfg"]
    g = v3_spatial._grid(base)
    sysm = build_uav(base); bus = solve(sysm, seed=dict(SEED)); cap = capabilities(sysm, bus)
    T, E_J = cap["mass"] * G, bus.get("usable_energy", 0.0)
    e_field = E_J / v3_spatial._power(T, g["A_feas"]) / 60.0        # if the full feasible field were realized
    emb = v3_spatial.re_embody(g)
    log.append((f"V3  reshape field -> {emb['k']} rotors / ducted-annular",
                False, {"potential_endurance_min": round(e_field, 1),
                        "over_V2": round(e_field - caps2["endurance_min"], 1),
                        "A_used->A_feasible": f"{g['A_used']:.2f}->{g['A_feas']:.2f} m^2"}))

    # realize the transcendent form with the best model we have (ducted-annular proxy)
    c3 = diagnose.repair(base, mission, mechanism="ducted_fan")[0]
    caps3 = diagnose.caps_of(c3, "ducted_fan")
    if _met(caps3, mission):
        log.append(("V3  realized (ducted proxy)", True, caps3))
        return "V3", c3, caps3, log

    log.append(("V3  frontier", False,
                {"note": "field wants a ducted-annular propulsor; no manufacturable-ring model to realize it",
                 "target_endurance_min": round(e_field, 1)}))
    return "beyond-realizable", base, caps2, log


def _run(title, cfg, mission):
    tier, cfgw, caps, log = escalate(cfg, mission)
    print(f"\n### {title}\n  mission {mission}")
    for name, met, c in log:
        cap = (f"a {c['a_max_g']:.2f}g v {c['v_max']:.1f} endur {c['endurance_min']:.0f}m mass {c['mass']:.2f}kg"
               if "a_max_g" in c else str(c))
        print(f"    {name:34s} {'MET' if met else '... ':4s} {cap}")
    print(f"  -> solved by {tier}")


if __name__ == "__main__":
    cfg = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000,
               C_rate=25, L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0)
    print("UNIFIED ESCALATION: V1 -> V2 -> V3-generative (fires only when the last exhausts)")
    _run("easy (V1 handles it)",   cfg, {"a_req": 4.0, "v_req": 22.0, "endur_req": 14.0})
    _run("harder (needs V2)",      cfg, {"a_req": 8.0, "v_req": 26.0, "endur_req": 12.0})
    _run("beyond discrete (V3)",   cfg, {"a_req": 12.0, "v_req": 30.0, "endur_req": 10.0})
