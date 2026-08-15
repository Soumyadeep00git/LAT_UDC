"""End-to-end on the HIGH-FIDELITY stack: config -> coupled 6-model solve -> capability envelope ->
mission. v_max/a_max/mass now come from BEMT + real motor + sagging battery + load-sized structure,
not the first-order drone.py.

    python run_hifi.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "physics"))

from platform_solve import Config, solve, G
from mission import threat_field
from intercept import assess


class Spec:
    def __init__(self, v_max, a_max, mass):
        self.v_max = v_max; self.a_max = a_max; self.mass = mass


def evaluate(cfg, world):
    st = solve(cfg)
    J, fr, miss, en = assess(Spec(st.v_max, st.a_max, st.mass), world)
    return st, (J, fr, miss, en)


def main():
    world = threat_field(140)
    configs = [
        ("mid quad",   Config(D_in=13, pitch_in=6,  Kv=300, I_max=45, S=6,  cap_mAh=5000, C_rate=60, L_arm=0.30)),
        ("hi-pitch",   Config(D_in=15, pitch_in=13, Kv=350, I_max=55, S=10, cap_mAh=6000, C_rate=60, L_arm=0.35)),
        ("big/agile",  Config(D_in=18, pitch_in=10, Kv=190, I_max=60, S=10, cap_mAh=8000, C_rate=45, L_arm=0.45)),
    ]
    print("HIGH-FIDELITY config -> solve -> mission (140 threats):\n")
    for name, cfg in configs:
        t0 = time.time()
        st, (J, fr, miss, en) = evaluate(cfg, world)
        dt = time.time() - t0
        print(f"{name:10s} mass {st.mass:4.2f}kg | a_max {st.a_max/G:4.2f}g | v_max {st.v_max:4.1f} | "
              f"endur {st.endurance_s/60:4.1f}min  ->  win {(1-fr)*100:3.0f}%  miss {miss:4.2f}m  ({dt:.1f}s)")


if __name__ == "__main__":
    main()
