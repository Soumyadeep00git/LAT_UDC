r"""FULL PIPELINE VALIDATION — a counter-UAS interceptor.

Vehicle class: multirotor copter, electric powertrain, propeller-driven, ArduPilot autopilot.
Mission: interception (defend an asset against incoming small-UAS threats).
Score: MAX INTERCEPT HITS.

Runs the whole stack end to end:
  1. MISSION   define the threat set + the physics-based interception scorer (continuous, not boolean —
               so the optimizer has gradient; this is the project's own max-margin lesson).
  2. ENCODE    parts -> bond graph -> fields -> objective.
  3. OPTIMIZE  V1 (tune the design for max hits) then V2 (rearrange the rotor field) — keep the best.
  4. PRODUCE   the buildable package for the winner: STL/STEP, FEA, ArduPilot .param + firmware (+CFD w/ --cfd).
  5. VALIDATE  consistency checks + final report.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose
import bondgraph
import parts as P
import cadgen
import fea
import ardupilot_gen
from uav import build_uav, capabilities, G, IN2M
from solve import solve

OUT = os.path.join(HERE, "build_interceptor")
BOARD = "CubeOrange"
SEED = {"current": 0.0, "total_mass": 4.0}

# ---- 1. MISSION: counter-UAS threat set (range km, threat speed m/s, crossing 0=head-on..1=beam) ----
SCENARIOS = [
    ("slow-near-headon", 1.2, 12, 0.0), ("slow-near-cross", 1.5, 14, 0.4),
    ("med-headon",       2.5, 20, 0.0), ("med-cross",       2.5, 22, 0.5),
    ("med-fast",         3.0, 26, 0.2), ("fast-headon",     3.5, 30, 0.0),
    ("fast-cross",       3.0, 30, 0.7), ("fast-far",        4.5, 32, 0.1),
    ("vfast-headon",     4.0, 38, 0.0), ("vfast-cross",     3.5, 36, 0.8),
    ("beam-runner",      2.8, 28, 1.0), ("sprinter",        5.0, 42, 0.3),
]
KEEPOUT = 500.0     # m, asset defense radius


def intercept_score(caps):
    """Physics-based interception feasibility per threat. Returns (hits, continuous_score, margins).
    A threat is intercepted if speed, acceleration, reach, and endurance margins are all >= 0.
    The continuous score (sum of sigmoids of the worst margin) gives the optimizer gradient even on misses."""
    v, a, e = caps["v_max"], caps["a_max_g"], caps["endurance_min"]
    hits, score, margins = 0, 0.0, []
    for _name, R_km, vt, cross in SCENARIOS:
        R = R_km * 1000.0
        t_avail = max((R - KEEPOUT) / vt, 1e-3)                 # s until threat reaches the keep-out
        need = R - KEEPOUT
        m_reach = (v * t_avail - need) / max(need, 1.0)          # can it cover the gap in time?
        m_speed = (v - vt * (1.0 + 0.3 * cross)) / max(vt, 1.0)  # speed advantage (more vs crossers)
        a_req = 2.0 + 4.0 * cross + vt / 22.0                    # crossing/fast targets need more g
        m_accel = (a - a_req) / max(a_req, 1.0)
        m_endur = (e - (t_avail / 60.0 + 2.0)) / 5.0             # must be on-station long enough
        m = min(m_speed, m_accel, m_reach, m_endur)
        margins.append(m)
        if m >= 0:
            hits += 1
        score += 1.0 / (1.0 + math.exp(-4.0 * m))               # smooth credit -> gradient
    return hits, score, margins


def _caps(cfg):
    return diagnose.caps_of(cfg)


def maximize(cfg0, iters=16):
    """V1: coordinate hill-climb of the design (incl. chemistry) to MAXIMIZE the continuous intercept score."""
    keys = ["D_in", "pitch_in", "Kv", "I_max", "S", "cap_mAh", "L_arm", "wh_per_kg"]
    bounds = dict(diagnose.BOUNDS); bounds["wh_per_kg"] = (200, 450)
    cfg = dict(cfg0)
    cfg.setdefault("wh_per_kg", 300.0)
    best = intercept_score(_caps(cfg))[1]
    step = {k: (hi - lo) * 0.2 for k, (lo, hi) in bounds.items()}
    for _ in range(iters):
        improved = False
        for k, (lo, hi) in bounds.items():
            if k not in keys:
                continue
            for d in (+1, -1):
                trial = dict(cfg); trial[k] = min(hi, max(lo, cfg[k] + d * step[k]))
                sc = intercept_score(_caps(trial))[1]
                if sc > best + 1e-9:
                    cfg, best = trial, sc; improved = True
        if not improved:
            for k in step:
                step[k] *= 0.5
    caps = _caps(cfg)
    hits, sc, _ = intercept_score(caps)
    return cfg, caps, hits, sc


def banner(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


def main(do_cfd=False):
    os.makedirs(OUT, exist_ok=True)
    banner("1. MISSION — counter-UAS interception")
    print(f"  {len(SCENARIOS)} incoming threats (speeds {min(s[2] for s in SCENARIOS)}-"
          f"{max(s[2] for s in SCENARIOS)} m/s, ranges {min(s[1] for s in SCENARIOS)}-"
          f"{max(s[1] for s in SCENARIOS)} km); asset keep-out {KEEPOUT:.0f} m.  Score = intercept hits.")

    cfg0 = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
                C_rate=25, L_arm=0.33, payload=0.6, n_rotors=4, wh_per_kg=300.0)

    banner("2. ENCODE — hardware -> system -> physics -> objective")
    system, meta = bondgraph.infer_system(P.quad_parts(cfg0), cfg0)
    print(f"  inferred: {meta['n_rotors']} rotors, subsystems "
          f"{[s.name for s in system.subsystems]}")
    for b in bondgraph.describe_bonds(meta)[:4]:
        print("    bond: " + b)
    cb = _caps(cfg0); h0, s0, _ = intercept_score(cb)
    print(f"  baseline caps: a_max {cb['a_max_g']:.2f} g | v_max {cb['v_max']:.1f} m/s | "
          f"endurance {cb['endurance_min']:.0f} min  ->  HITS {h0}/{len(SCENARIOS)}")

    banner("3. OPTIMIZE — maximize intercept hits (V1 then V2)")
    # V1: tune the design (params + chemistry) at the inferred 4-rotor form
    c1, caps1, h1, s1 = maximize(cfg0)
    print(f"  V1 (params): a_max {caps1['a_max_g']:.2f} g | v_max {caps1['v_max']:.1f} | "
          f"endur {caps1['endurance_min']:.0f} min  ->  HITS {h1}/{len(SCENARIOS)}  (score {s1:.2f})")
    # V2: rearrange the rotor field (count), re-optimize each, keep best hits
    best = (4, c1, caps1, h1, s1)
    for n in (6, 8):
        cn = dict(c1, n_rotors=n)
        c2, caps2, h2, s2 = maximize(cn)
        print(f"  V2 (n={n} rotors): a_max {caps2['a_max_g']:.2f} g | v_max {caps2['v_max']:.1f} | "
              f"endur {caps2['endurance_min']:.0f} min  ->  HITS {h2}/{len(SCENARIOS)}  (score {s2:.2f})")
        if (h2, s2) > (best[3], best[4]):
            best = (n, c2, caps2, h2, s2)
    n_win, cfg_win, caps_win, hits_win, score_win = best
    print(f"  WINNER: {n_win} rotors, HITS {hits_win}/{len(SCENARIOS)}")

    banner("4. PRODUCE — buildable package for the winner")
    cfg_win = dict(cfg_win); cfg_win["n_rotors"] = n_win
    hw = cadgen.generate_vehicle(cfg_win, os.path.join(OUT, "hardware"), "interceptor")
    print(f"  [CAD]  interceptor.step + .stl  (span {hw['span_mm']:.0f} mm)")
    sysw = build_uav(cfg_win); capw = capabilities(sysw, solve(sysw, seed=dict(SEED)))
    per_rotor = capw["thrust"] / n_win
    fe = fea.run(cfg_win, os.path.join(OUT, "fea"), thrust_per_rotor_N=per_rotor * max(caps_win["a_max_g"], 1))
    print(f"  [FEA]  arm.inp + arm.msh + result  (stress {fe['max_bending_stress_MPa']:.0f} MPa, SF {fe['safety_factor']:.1f})")
    cfg_ap = dict(cfg_win); cfg_ap["_TWR"] = capw["TWR"]
    pp, npar = ardupilot_gen.gen_param(cfg_ap, os.path.join(OUT, "ardupilot"), board=BOARD, vehicle="counter-UAS interceptor")
    fw = ardupilot_gen.fetch_firmware(os.path.join(OUT, "ardupilot"), board=BOARD)
    print(f"  [ArduPilot]  interceptor.param ({npar} params) + "
          + (f"arducopter.apj ({fw['bytes']:,} B, {fw.get('git_identity','')})" if fw.get("ok") else f"apj MISS ({fw.get('reason')})"))
    cfd = None
    if do_cfd:
        try:
            import openfoam_runner as ofr
            aref = (hw["height_mm"] * hw["span_mm"] * 0.25) / 1e6
            cfd = ofr.flow_drag(hw["stl"], caps_win["v_max"], os.path.join(OUT, "cfd"),
                                aref=aref, lref=hw["span_mm"] / 1000.0, iters=180, timeout=520)
            print(f"  [CFD]  " + (f"drag {cfd['drag_N']:.2f} N @ {caps_win['v_max']:.0f} m/s, {cfd['cells']} cells"
                                  if cfd.get("ok") else f"did not complete ({cfd.get('reason')})"))
        except Exception as ex:
            print(f"  [CFD]  skipped ({type(ex).__name__})")

    banner("5. VALIDATE — end-to-end checks")
    bus = solve(sysw, seed=dict(SEED))
    leaf = sum(lf.state.get("mass", 0.0) for s in sysw.subsystems for lf in s.leaves())
    inf_sys, _ = bondgraph.infer_system(P.quad_parts(cfg0), cfg0)
    inf_mass = capabilities(inf_sys, solve(inf_sys, seed=dict(SEED)))["mass"]
    base_sys = build_uav(cfg0); base_mass = capabilities(base_sys, solve(base_sys, seed=dict(SEED)))["mass"]
    checks = [
        ("encode inference == baseline solve", abs(inf_mass - base_mass) < 1e-6),
        ("coupled solve converged", bus.get("converged") is True),
        ("mass == sum of leaf masses", abs(bus["total_mass"] - leaf) < 1e-2),
        ("optimization improved hits", hits_win >= h0),
        ("CAD artifacts exist", os.path.exists(hw["step"]) and os.path.exists(hw["stl"])),
        ("FEA deck exists", os.path.exists(os.path.join(OUT, "fea", "arm.inp"))),
        ("ArduPilot param + firmware exist", os.path.exists(pp) and fw.get("ok")),
        ("structure not overstressed (SF>1)", fe["safety_factor"] > 1.0),
    ]
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    allok = all(ok for _, ok in checks)

    banner("RESULT")
    print(f"  vehicle : counter-UAS interceptor, {n_win} rotors, electric, propeller, ArduPilot/{BOARD}")
    print(f"  design  : " + ", ".join(f"{k}={cfg_win[k]:.0f}" if k not in ('L_arm',) else f"{k}={cfg_win[k]:.2f}"
                                       for k in ['D_in', 'pitch_in', 'Kv', 'I_max', 'S', 'cap_mAh', 'L_arm', 'wh_per_kg']))
    print(f"  caps    : a_max {caps_win['a_max_g']:.2f} g | v_max {caps_win['v_max']:.1f} m/s | endurance {caps_win['endurance_min']:.0f} min")
    print(f"  SCORE   : MAX INTERCEPT HITS = {hits_win} / {len(SCENARIOS)}   (baseline {h0})")
    print(f"  package : build_interceptor/  (STL, FEA, ArduPilot{' , CFD' if cfd and cfd.get('ok') else ''})")
    print(f"  PIPELINE VALIDATION: {'PASS' if allok else 'FAIL'}")
    return allok


if __name__ == "__main__":
    ok = main(do_cfd="--cfd" in sys.argv)
    sys.exit(0 if ok else 1)
