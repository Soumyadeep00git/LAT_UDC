r"""V3 generative core (prototype): dissolve the design into its FIELD, reshape the field with the
embodiment gone but the essence kept, then re-embody a new physical form.

Not composition (selecting rotor vs ducted from a library) — GENERATION. The discrete rotors are
dissolved into the actuator/momentum field over the airframe planform; the field is reshaped under its
invariant (momentum theory) free of any rotor; then the reshaped field is re-embodied as whatever
physical form produces it — which, when the field fills the planform, is NOT a quad.

Scope of this prototype: the propulsion momentum field, at momentum-theory fidelity (the invariant is
algebraic: P = T^1.5 / (FM*sqrt(2*rho*A))). The deep frontier remains: spatial CFD-level field topology
optimization, and manufacturable synthesis of the re-embodied form.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

from uav import build_uav, capabilities, G, IN2M
from solve import solve

RHO, FM = 1.225, 0.70


def reduce_to_field(cfg):
    """Step 1 — dissolve V1/V2 into field variables. The rotor COUNT and DIAMETER stop being the design;
    what remains is the actuator field over the airframe planform: the area it could occupy vs the area
    the discrete rotors actually use."""
    n = int(cfg["n_rotors"]); R_rot = cfg["D_in"] * IN2M / 2; L = cfg["L_arm"]
    R_frame = L + R_rot                                  # airframe outer radius (rotor tips)
    R_hub = max(0.04, 0.28 * L)                          # central keep-out (payload / avionics)
    A_avail = math.pi * (R_frame ** 2 - R_hub ** 2)      # planform the actuator field COULD fill
    A_used = n * math.pi * R_rot ** 2                    # what the discrete rotors DO use
    return {"n": n, "R_rot": R_rot, "R_frame": R_frame, "R_hub": R_hub,
            "A_avail": A_avail, "A_used": A_used, "fill": A_used / A_avail if A_avail else 0.0}


def reshape_field(field, T_req, energy_J):
    """Step 2 — modify the whole field. Essence kept (momentum theory), embodiment gone: the momentum-
    OPTIMAL distribution spreads the required thrust over the MAXIMUM available planform (min disk loading
    -> min power). This is the convex optimum of min integral(d^1.5) s.t. integral(d)=T: uniform d over
    all available area. No rotor is assumed."""
    A = field["A_avail"]
    P = T_req ** 1.5 / (FM * math.sqrt(2 * RHO * A)) if A > 0 else 1e9
    return {"A_field": A, "disk_loading": T_req / A if A else 0.0,
            "power_W": P, "endurance_min": energy_J / P / 60.0 if P > 0 else 0.0}


def _power(T, A):
    return T ** 1.5 / (FM * math.sqrt(2 * RHO * A)) if A > 0 else 1e9


def re_embody(field, reshaped):
    """Step 3 — recreate physicality. The optimal field is a FILLED ANNULUS. Discrete circular rotors
    cannot fill a planform (they leave gaps or overlap), so the form that produces this field is a
    DUCTED ANNULAR propulsor (a continuous ring), not a rotorcraft — a genuinely new embodiment generated
    from the field. We also report the closest discrete approximation for buildability."""
    A = reshaped["A_field"]; R_frame, R_hub = field["R_frame"], field["R_hub"]
    r_m = 0.5 * (R_frame + R_hub); circ = 2 * math.pi * r_m
    # closest discrete tiling: k rotors of diameter D around the mean radius, k*D ~ circ, k*pi D^2/4 ~ A
    D_ring = 4 * A / (math.pi * circ) if circ else 0.0
    k = max(3, round(circ / D_ring)) if D_ring else 0
    return {"form": "ducted annular propulsor (continuous ring)", "effective_area_m2": round(A, 3),
            "ring_mean_radius_m": round(r_m, 3),
            "discrete_approx": f"{k} x {D_ring/IN2M:.1f} in rotors (near-touching)",
            "why": "discrete circular rotors cannot fill the planform -> the field wants a ring/duct"}


def demo():
    # a sane, non-overlapping quad to start from
    cfg = dict(D_in=12, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0)
    sysm = build_uav(cfg); bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus)
    W = cap["mass"] * G
    E_J = bus.get("usable_energy", 0.0)

    print("V3 GENERATIVE CORE (prototype) — dissolve -> reshape field -> re-embody\n")
    print(f"start (discrete quad): mass {cap['mass']:.2f} kg, {cfg['n_rotors']} x {cfg['D_in']}in rotors")

    f = reduce_to_field(cfg)
    print(f"\n[1] REDUCE to field variables:")
    print(f"    planform available A_avail = {f['A_avail']:.3f} m^2   (annulus R {f['R_hub']:.2f}..{f['R_frame']:.2f} m)")
    print(f"    discrete rotors use A_used = {f['A_used']:.3f} m^2   -> they fill only {f['fill']*100:.0f}% of the planform")

    r = reshape_field(f, W, E_J)
    e_discrete = E_J / _power(W, f["A_used"]) / 60.0
    print(f"\n[2] MODIFY the field (essence = momentum theory, embodiment gone):")
    print(f"    spread thrust over the full planform -> disk loading {r['disk_loading']:.0f} N/m^2, "
          f"power {r['power_W']:.0f} W")
    print(f"    endurance:  discrete {e_discrete:.1f} min  ->  field {r['endurance_min']:.1f} min  "
          f"(x{r['endurance_min']/e_discrete:.2f}, from using {1/f['fill']:.1f}x the area)")

    emb = re_embody(f, r)
    print(f"\n[3] RE-EMBODY the reshaped field into a new physical form:")
    print(f"    form: {emb['form']}  (effective disk area {emb['effective_area_m2']} m^2)")
    print(f"    why : {emb['why']}")
    print(f"    closest buildable discrete approx: {emb['discrete_approx']}")
    print(f"\n-> V3 generated a NON-QUAD embodiment (a ring/ducted annulus) from the field itself — outside")
    print(f"   the (count, diameter) space V1/V2 can reach. Essence kept (momentum), embodiment regenerated.")
    print(f"\nHONEST: momentum-theory fidelity + a simplified re-embodiment. The deep frontier is spatial CFD")
    print(f"   field-topology optimization and manufacturable synthesis of the ring/duct.")


if __name__ == "__main__":
    demo()
