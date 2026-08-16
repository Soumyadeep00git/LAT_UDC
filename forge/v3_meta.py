r"""V3 meta-requirements — when a field is OVER-CONSTRAINED, hint a MISSING DEGREE OF FREEDOM.

The seeker wall is not a bad parameter choice — it is a conserved-budget conflict: a fixed sensor's
space-bandwidth product (etendue) means resolution (detection range) and INSTANTANEOUS coverage trade
against each other. No static camera can have both long detection and wide coverage. V3 ascends to that
invariant (optics.space_bandwidth_product) and, finding the STATIC field infeasible, prescribes the
resolution: a NEW degree of freedom the field lacks — a temporal/scan DOF (angular motion).

Crucially this is DECOUPLED from hardware: the physics layer says "the field needs motion"; which actuator
supplies it (gimbal / rotating mount / electronic beam-steer) is architecture + hardware planning. V3
outputs the meta-requirement (a missing dimension), not the part.
"""
from __future__ import annotations

import math

TARGET_M = 0.35     # threat characteristic size
N_DET = 2.0         # Johnson detection pixels-on-target


def meta_requirement(cfg, need):
    """need = {detect_range_m, search_halfangle_deg, max_revisit_s}. Returns a physics-layer hint."""
    R = need["detect_range_m"]
    ifov_need = TARGET_M / (N_DET * R)                          # angular resolution required for detection at R
    n_lin = cfg["n_pixels"]                                     # linear pixel count
    fov_lin = n_lin * ifov_need                                 # instantaneous FOV at that resolution
    omega_inst = fov_lin ** 2                                   # instantaneous solid coverage (sr, small-angle)
    th = math.radians(need["search_halfangle_deg"])
    omega_req = 2 * math.pi * (1 - math.cos(th))                # required search solid angle (sr)

    if omega_inst >= omega_req:
        return {"static_feasible": True,
                "note": "a fixed sensor covers the search region at the required resolution — no new DOF needed"}

    tiles = omega_req / omega_inst
    tau = tiles / cfg["frame_rate_hz"]                          # revisit time to scan the whole region once
    return {
        "static_feasible": False,
        "conflict": (f"detection {R:.0f} m needs IFOV {ifov_need*1e3:.3f} mrad -> instantaneous FOV "
                     f"{math.degrees(fov_lin):.1f} deg (coverage {omega_inst:.3f} sr), but the mission needs "
                     f"{2*need['search_halfangle_deg']:.0f} deg cone ({omega_req:.2f} sr)."),
        "grounded_in": "optics.space_bandwidth_product (etendue): resolution x instantaneous coverage is fixed",
        "meta_requirement": "ADD A TEMPORAL / SCAN DEGREE OF FREEDOM to the seeker field (angular motion)",
        "coverage_sr": round(omega_req, 3), "inst_coverage_sr": round(omega_inst, 4),
        "tiles_to_scan": round(tiles, 1), "revisit_s": round(tau, 3),
        "scan_resolves": tau <= need["max_revisit_s"],
        "hardware": "TBD by architecture/hardware (gimbal | rotating mount | electronic beam-steering)",
    }


if __name__ == "__main__":
    cfg = dict(n_pixels=1920, focal_length_mm=38.0, pixel_pitch_um=3.0, frame_rate_hz=60.0)
    need = {"detect_range_m": 2500.0, "search_halfangle_deg": 30.0, "max_revisit_s": 1.5}
    print("V3 META-REQUIREMENT — the seeker wall, and the missing dimension it implies\n")
    print(f"  seeker: {cfg['n_pixels']} px, focal {cfg['focal_length_mm']:.0f} mm, {cfg['frame_rate_hz']:.0f} Hz")
    print(f"  need  : detect {need['detect_range_m']:.0f} m over a {2*need['search_halfangle_deg']:.0f} deg "
          f"search cone, revisit <= {need['max_revisit_s']} s\n")
    r = meta_requirement(cfg, need)
    if r["static_feasible"]:
        print("  " + r["note"])
    else:
        print(f"  CONFLICT   : {r['conflict']}")
        print(f"  grounded in: {r['grounded_in']}")
        print(f"  META-REQ   : {r['meta_requirement']}")
        print(f"               cover {r['coverage_sr']} sr in {r['tiles_to_scan']} tiles -> revisit "
              f"{r['revisit_s']} s  (resolves: {r['scan_resolves']})")
        print(f"  hardware   : {r['hardware']}")
        print(f"\n  -> V3 prescribed a MISSING DIMENSION (motion), grounded in physics, WITHOUT naming a gimbal.")
        print(f"     The physics layer says 'the field needs to move'; architecture picks the actuator.")
