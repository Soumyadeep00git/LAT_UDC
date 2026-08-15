"""Foundation gate: the System-graph solve must reproduce the hardcoded hi-fi solver (platform_solve).
If the explicit graph matches the implicit one, the spine is real and everything can re-point at it."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))

import platform_solve as PS
from solve import solve
from uav import build_uav, capabilities, G

CONFIGS = [
    ("mid", dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6, cap_mAh=5000, C_rate=60, L_arm=0.30)),
    ("hi-pitch", dict(D_in=15, pitch_in=13, Kv=350, I_max=55, S=10, cap_mAh=6000, C_rate=60, L_arm=0.35)),
    ("big/agile", dict(D_in=18, pitch_in=10, Kv=190, I_max=60, S=10, cap_mAh=8000, C_rate=45, L_arm=0.45)),
]

print("SYSTEM GRAPH:\n" + build_uav(CONFIGS[0][1]).describe() + "\n")
print(f"{'config':10s} {'':6s} {'mass':>16s} {'a_max(g)':>16s} {'v_max':>16s}")
print(f"{'':10s} {'':6s} {'system / hifi':>16s} {'system / hifi':>16s} {'system / hifi':>16s}")
ok = True
for name, cfg in CONFIGS:
    sysm = build_uav(cfg)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus)
    ref = PS.solve(PS.Config(**cfg))
    dm = abs(cap["mass"] - ref.mass) / ref.mass
    da = abs(cap["a_max"] - ref.a_max) / max(ref.a_max, 1e-6)
    dv = abs(cap["v_max"] - ref.v_max) / max(ref.v_max, 1e-6)
    ok = ok and dm < 0.05 and da < 0.08 and dv < 0.10
    print(f"{name:10s} {'':6s} "
          f"{cap['mass']:6.2f} / {ref.mass:5.2f}   "
          f"{cap['a_max']/G:6.2f} / {ref.a_max/G:5.2f}   "
          f"{cap['v_max']:6.1f} / {ref.v_max:5.1f}")
print("\n" + ("FOUNDATION GATE: PASS — system graph reproduces the hi-fi solver" if ok
             else "FOUNDATION GATE: FAIL — divergence too large"))
