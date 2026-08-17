r"""PHYSICS RESOLVER — given a FIXED topology + a mission, resolve the physics to its best.

No topology generation. The quadcopter/UAV-seeker subsystems are defined and linked (uav_seeker_pack).
This asks the only question left at the physics layer: within this topology, what is the BEST the physics
can do for the mission, what is the reachable envelope, and what wall caps it?

  1. RESOLVE  search the design DOFs for the design of maximum WORST-CASE MARGIN (the project's origin
              metric: a design is only as good as its weakest satisfied requirement).
  2. ENVELOPE trace the reachable frontier the physics permits (here: the seeker etendue trade), so you
              can SEE what the topology can and cannot reach.
  3. WALL     name the binding requirement - the physics ceiling. If it is a conserved budget, that is a
              missing-dimension (realization is a separate class of problem, deliberately not attempted).
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import physics_adapt
import uav_seeker_pack as U
from uav import G, SEEKER_DEFAULTS

TARGET_M, N_DET = 0.35, 2.0


def _seeker(focal_mm, n_pixels, pixel_pitch_um):
    ifov = (pixel_pitch_um * 1e-6) / (focal_mm / 1000.0)
    detection = TARGET_M / (N_DET * ifov)
    fov = n_pixels * ifov
    return detection, math.degrees(fov), fov ** 2          # m, deg, sr


def resolve(base, mission):
    a_req, v_req, e_req = mission["a_req"], mission["v_req"], mission["endur_req"]
    R_req = mission["detect_range_m"]
    cone_sr = 2 * math.pi * (1 - math.cos(math.radians(mission["search_halfangle_deg"])))

    # 1. RESOLVE the airframe: best worst-case margin over count + params (V2 wraps V1)
    best, cands, rule = physics_adapt.adapt(base, {"a_req": a_req, "v_req": v_req, "endur_req": e_req})
    cfg, caps = best["cfg"], best["caps"]
    m_air = {"a_max": (caps["a_max_g"] - a_req) / a_req,
             "v_max": (caps["v_max"] - v_req) / v_req,
             "endurance": (caps["endurance_min"] - e_req) / e_req}

    # 2. ENVELOPE the seeker etendue frontier (fixed n_pixels), and the best-balanced point
    npx = cfg.get("n_pixels", SEEKER_DEFAULTS["n_pixels"])
    pp = cfg.get("pixel_pitch_um", SEEKER_DEFAULTS["pixel_pitch_um"])
    frontier, best_focal, best_bal = [], None, -1e9
    for focal in (8, 12, 18, 25, 35, 50, 75, 110, 160, 220):
        det, fov_deg, cov = _seeker(focal, npx, pp)
        det_m = (det - R_req) / R_req
        cov_m = (cov - cone_sr) / cone_sr
        bal = min(det_m, cov_m)                              # worst of the two seeker demands
        frontier.append((focal, det, fov_deg, cov, det_m, cov_m))
        if bal > best_bal:
            best_bal, best_focal = bal, focal

    m_seek = best_bal                                        # best achievable seeker margin (static)
    margins = dict(m_air, seeker=m_seek)
    binding = min(margins, key=margins.get)
    return {"cfg": cfg, "caps": caps, "rule": rule, "margins": margins, "worst": margins[binding],
            "binding": binding, "frontier": frontier, "best_focal": best_focal,
            "cone_sr": cone_sr, "R_req": R_req}


if __name__ == "__main__":
    base = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
                L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0,
                focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)
    mission = dict(a_req=5.0, v_req=26.0, endur_req=16.0, detect_range_m=2500.0, search_halfangle_deg=30.0)
    r = resolve(base, mission)
    c, caps = r["cfg"], r["caps"]

    print("=" * 84)
    print("PHYSICS RESOLVER  -  best of a FIXED topology (quad + EO seeker) for the interceptor mission")
    print("=" * 84)
    print(f"mission: a>={mission['a_req']}g  v>={mission['v_req']}m/s  endur>={mission['endur_req']}min  "
          f"detect>={mission['detect_range_m']:.0f}m over a {2*mission['search_halfangle_deg']:.0f}deg cone")

    print(f"\n1. BEST DESIGN the physics resolves to ({r['rule']}):")
    print(f"   {c['n_rotors']} rotors, D {c['D_in']:.1f}in, pitch {c['pitch_in']:.1f}, Kv {c['Kv']:.0f}, "
          f"I_max {c['I_max']:.0f}, {c['S']:.1f}S {c['cap_mAh']:.0f}mAh   (S relaxed continuous by the optimizer)")
    print(f"   -> a_max {caps['a_max_g']:.2f} g | v_max {caps['v_max']:.1f} m/s | "
          f"endurance {caps['endurance_min']:.0f} min | mass {caps['mass']:.2f} kg")
    print("   margins (fraction over requirement):")
    for k in ("a_max", "v_max", "endurance", "seeker"):
        print(f"     {k:10s} {r['margins'][k]:+.2f}")

    print(f"\n2. REACHABLE ENVELOPE - the seeker etendue frontier (n_pixels={c.get('n_pixels',1920)}, "
          f"cone needs {r['cone_sr']:.2f} sr):")
    print(f"   {'focal':>6} {'detect(m)':>10} {'FOV(deg)':>9} {'cover(sr)':>10}  detect_marg  cover_marg")
    for focal, det, fov_deg, cov, dm, cm in r["frontier"]:
        flag = "  <= best-balanced" if focal == r["best_focal"] else ""
        print(f"   {focal:>6} {det:>10.0f} {fov_deg:>9.1f} {cov:>10.3f}  {dm:>+10.2f}  {cm:>+9.2f}{flag}")

    print(f"\n3. THE WALL - binding requirement: {r['binding'].upper()}  (worst-case margin {r['worst']:+.2f})")
    if r["binding"] == "seeker":
        print("   The airframe is resolved with margin to spare; the physics ceiling is the SEEKER etendue:")
        print("   detection range x instantaneous coverage is a conserved budget - no static focal length")
        print("   reaches the detection range AND the search cone. The best the physics can do on this")
        print("   topology is bounded here. Passing it needs a NEW DIMENSION (a scan DOF) - which is")
        print("   realization, a separate class of problem, deliberately not attempted.")
    else:
        print("   The airframe itself is the limit; parametric/structural room is exhausted on this metric.")
    print("\n   This is the physics at its best for the given topology: a resolved design, its reachable")
    print("   frontier, and the exact wall - all from the linked physics, no topology generated.")
