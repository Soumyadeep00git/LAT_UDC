r"""Adaptive physics layer: the rotor FIELD ARRANGEMENT is a degree of freedom.

The propulsion physics is N actuator-disk (rotor) fields partitioning a total disk area. That partition is
not fixed at 4 — the physics layer can REARRANGE it (change rotor count, resize each), re-infer the
architecture, and RE-SOLVE, keeping the arrangement that best serves the objective. Two rearrangement
modes:
  - fixed  : keep per-rotor size, change count            (total disk area scales with N)
  - area   : conserve total disk area, repartition into N  (Dᵢ = D₀·√(N₀/N))

This is where architecture and physics TALK: changing N is an architecture edit (parts/bonds); the fields
(N rotor disks, disk loading, thrust) and the coupled solve follow from it. `test_talk()` checks that
round-trip both ways. Scope: electric multirotor (cross-class morph is the gated mechanism, not here).
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

import bondgraph
import parts as P
from solve import solve
from uav import capabilities, G, IN2M

SEED = {"current": 0.0, "total_mass": 4.0}
METRIC_REQ = {"a_max_g": "a_req", "v_max": "v_req", "endurance_min": "endur_req"}


def _eval(cfgn):
    system, meta = bondgraph.infer_system(P.quad_parts(cfgn), cfgn)
    bus = solve(system, seed=dict(SEED))
    cap = capabilities(system, bus)
    caps = {"a_max_g": cap["a_max"] / G, "v_max": cap["v_max"],
            "endurance_min": cap["endurance"] / 60.0, "mass": cap["mass"], "thrust": cap["thrust"]}
    n = int(cfgn["n_rotors"]); R = cfgn["D_in"] * IN2M / 2
    caps["disk_loading"] = cap["thrust"] / (n * math.pi * R * R) if R > 0 else 0.0
    return system, meta, bus, cap, caps


def arrangements(cfg, counts=(3, 4, 6, 8)):
    D0, n0 = cfg["D_in"], int(cfg["n_rotors"])
    out = []
    for n in counts:
        out.append(("fixed", n, dict(cfg, n_rotors=n)))
        Dn = round(min(22.0, max(8.0, D0 * math.sqrt(n0 / n))), 2)
        out.append(("area", n, dict(cfg, n_rotors=n, D_in=Dn)))
    return out


def _score(caps, mission):
    reqs = {m: mission[METRIC_REQ[m]] for m in METRIC_REQ}
    margins = {m: (caps[m] - reqs[m]) / max(reqs[m], 1e-9) for m in reqs}
    feasible = all(v >= -1e-6 for v in margins.values())
    return feasible, min(margins.values())


def adapt(cfg, mission):
    """Search rotor-field arrangements; return the best for the objective + the full candidate table."""
    cands = []
    for mode, n, cfgn in arrangements(cfg):
        _s, _m, _b, _c, caps = _eval(cfgn)
        feasible, worst = _score(caps, mission)
        cands.append({"mode": mode, "n": n, "cfg": cfgn, "caps": caps,
                      "feasible": feasible, "worst_margin": worst})
    feas = [c for c in cands if c["feasible"]]
    if feas:
        best = min(feas, key=lambda c: c["caps"]["mass"])          # feasible -> lightest
        rule = "lightest feasible"
    else:
        best = max(cands, key=lambda c: c["worst_margin"])         # else -> best worst-margin
        rule = "max worst-margin (none feasible)"
    return best, cands, rule


def _demo(title, cfg, mission):
    best, cands, rule = adapt(cfg, mission)
    print(f"\n### {title}   (rule: {rule})")
    print(f"    mission {mission}")
    print(f"    {'mode':6s} {'N':>2s} {'D(in)':>6s} {'a_max':>6s} {'v_max':>6s} {'endur':>6s} "
          f"{'mass':>6s} {'DL':>5s} feasible")
    for c in cands:
        cp = c["caps"]; star = "  <= BEST" if c is best else ""
        print(f"    {c['mode']:6s} {c['n']:>2d} {c['cfg']['D_in']:>6.1f} {cp['a_max_g']:>6.2f} "
              f"{cp['v_max']:>6.1f} {cp['endurance_min']:>6.1f} {cp['mass']:>6.2f} "
              f"{cp['disk_loading']:>5.0f} {'yes' if c['feasible'] else 'no '}{star}")
    b = best["caps"]
    print(f"    -> physics rearranged 4 rotors -> {best['n']} ({best['mode']}), D={best['cfg']['D_in']:.1f}in: "
          f"mass {b['mass']:.2f} kg, endurance {b['endurance_min']:.0f} min, a_max {b['a_max_g']:.2f} g")
    return best


def test_talk(cfg):
    """Goal 2: architecture <-> physics round-trip."""
    print("\n" + "=" * 66 + "\nARCHITECTURE <-> PHYSICS talk test")
    ok = True

    # (i) architecture edit (rotor count 4 -> 6) must propagate to the physics fields + solve
    s4, m4, b4, c4, caps4 = _eval(dict(cfg, n_rotors=4))
    s6, m6, b6, c6, caps6 = _eval(dict(cfg, n_rotors=6))
    n_thrust_bonds_4 = sum(1 for (a, bnd, d, q) in m4["bonds"] if q == "thrust")
    n_thrust_bonds_6 = sum(1 for (a, bnd, d, q) in m6["bonds"] if q == "thrust")
    prop6_n = s6.by_name()["propulsion"].params["n_rotors"]
    check1 = (prop6_n == 6 and caps6["thrust"] > caps4["thrust"] and caps6["mass"] > caps4["mass"])
    print(f"  (i) arch N: 4->6  =>  inferred propulsion.n_rotors={prop6_n}, "
          f"thrust {caps4['thrust']:.0f}->{caps6['thrust']:.0f} N, mass {caps4['mass']:.2f}->{caps6['mass']:.2f} kg, "
          f"disk-loading {caps4['disk_loading']:.0f}->{caps6['disk_loading']:.0f}  [{'OK' if check1 else 'FAIL'}]")
    ok &= check1

    # (ii) physics-only edit (rotor size) must NOT change the architecture topology (same subsystems/bonds)
    sA, mA, *_ = _eval(dict(cfg, D_in=cfg["D_in"] + 3))
    same_subs = [x.name for x in sA.subsystems] == [x.name for x in s4.subsystems]
    same_bonds = set((a, bnd, q) for (a, bnd, d, q) in mA["bonds"]) == \
                 set((a, bnd, q) for (a, bnd, d, q) in m4["bonds"])
    print(f"  (ii) physics D_in +3in  =>  architecture topology unchanged: "
          f"subs {same_subs}, bonds {same_bonds}  [{'OK' if same_subs and same_bonds else 'FAIL'}]")
    ok &= same_subs and same_bonds

    # (iii) conservation: mass == sum of leaf masses, thrust scales ~ with N (physics stays consistent)
    leaf_sum = sum(lf.state.get("mass", 0.0) for s in s6.subsystems for lf in s.leaves())
    check3 = abs(b6["total_mass"] - leaf_sum) < 1e-2 and b6.get("converged")
    print(f"  (iii) coupled solve consistent: total_mass {b6['total_mass']:.3f} == sum(leaf) {leaf_sum:.3f}, "
          f"converged={b6.get('converged')}  [{'OK' if check3 else 'FAIL'}]")
    ok &= check3
    print(f"  -> {'PASS — architecture and physics talk both ways' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    print("ADAPTIVE PHYSICS — the rotor field rearranges itself for the objective")
    e = _demo("ENDURANCE mission (loiter)", cfg, {"a_req": 2.0, "v_req": 12.0, "endur_req": 38.0})
    a = _demo("AGILITY mission (high-g)", cfg, {"a_req": 4.4, "v_req": 22.0, "endur_req": 10.0})
    print(f"\nsame quad, endurance -> {e['n']} rotors ({e['mode']}) | agility -> {a['n']} rotors ({a['mode']})")
    test_talk(cfg)
