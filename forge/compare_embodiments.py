r"""Comparison — candidate embodiments on the SAME counter-UAS interception mission (score = hits/12).

Baseline quad vs V1-tuned quad vs V2 (count+params) vs the ducted-annular ring. Same battery, same seeker.
Honest: the ring is an UNVALIDATED model (see ducted_ring.py) — shown for comparison, flagged.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

from validate_pipeline import intercept_score, maximize, _caps, SCENARIOS
import ducted_ring

N = len(SCENARIOS)


def hits(caps):
    return intercept_score(caps)[0]


def row(name, caps, validated=True):
    print(f"  {name:26s} {caps['a_max_g']:5.2f}g {caps['v_max']:6.1f} {caps['endurance_min']:6.0f}m "
          f"{caps['mass']:6.2f}kg   {hits(caps):>2d}/{N}   {'yes' if validated else 'NO (deficit)'}")


if __name__ == "__main__":
    cfg0 = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000, C_rate=25, L_arm=0.33,
                payload=0.6, n_rotors=4, wh_per_kg=300.0,
                focal_length_mm=25.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)

    print("COMPARISON — counter-UAS interception (same battery + seeker)\n")
    print(f"  {'embodiment':26s} {'a_max':>6s} {'v_max':>6s} {'endur':>7s} {'mass':>8s}   hits   validated")

    row("baseline quad (untuned)", _caps(cfg0))

    c1, caps1, h1, s1 = maximize(dict(cfg0, n_rotors=4))
    row("V1  quad (params)", caps1)

    best = (4, caps1, h1, s1)
    for n in (3, 6, 8):
        _c, capsN, hN, sN = maximize(dict(cfg0, n_rotors=n))
        if (hN, sN) > (best[2], best[3]):
            best = (n, capsN, hN, sN)
    row(f"V2  quad ({best[0]} rotors)", best[1])

    # ducted ring: thrust grounded in the tuned quad's BEMT thrust; shares the same seeker + turn estimate
    qc = _caps(c1)
    ring = ducted_ring.ducted_ring_caps(c1, qc["thrust"], qc["v_max"])
    ring_full = {**ring, "detection_range": qc["detection_range"], "seeker_fov_deg": qc["seeker_fov_deg"],
                 "track_rate_hz": qc["track_rate_hz"], "turn_alpha": qc["turn_alpha"]}
    row("ducted ring (V3 form)", ring_full, validated=False)

    print("\n  note: the ring's endurance edge is an artifact of an unvalidated model (underestimated duct")
    print("  mass; ducts don't actually beat large open rotors on hover). Trust needs CFD/constrained duct")
    print("  physics. On thrust-grounded a_max/v_max it is comparable to the tuned quad.")
