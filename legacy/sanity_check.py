"""Sanity check of the whole sizing model. Each test prints PASS / SUSPECT / FAIL with the numbers, so
we can see WHERE the model is weak rather than trusting it. No claims, just probes."""
from __future__ import annotations

import math
import random

from drone import (Drone, KEYS, BOUNDS, G, RHO, IN2M, N_ROTORS,
                   MOTOR_KW_PER_KG, WH_PER_KG, C_BURST, ETA_MOTOR)
from mission import threat_field
from engagement import simulate


def line(tag, verdict, msg):
    print(f"  [{verdict:7s}] {tag}: {msg}")


# ---------------------------------------------------------------- 1. figure of merit
def check_figure_of_merit():
    """Blade-element thrust must NOT exceed the momentum-theory ideal for its power (FM <= 1).
    FM = P_ideal/P_actual = T^1.5 / (sqrt(2 rho A) * P). Real props: 0.5-0.8."""
    print("\n1) FIGURE OF MERIT  (thrust vs the physical max for the power drawn)")
    worst = 1.0
    for D, pitch in [(7, 4), (13, 6), (18, 12), (22, 14)]:
        d = Drone(D, pitch, 800, 6, 6000, 0.4, 2.0)
        n = d.rev_per_s(); D_m = D * IN2M
        T = d._ct() * RHO * n * n * D_m ** 4
        P = d._cp() * RHO * n ** 3 * D_m ** 5
        A = math.pi * (D_m / 2) ** 2
        fm = T ** 1.5 / (math.sqrt(2 * RHO * A) * P) if P > 0 else 0
        v = "PASS" if 0.4 <= fm <= 0.85 else ("SUSPECT" if fm <= 1.0 else "FAIL")
        line(f"prop {D}x{pitch}", v, f"FM = {fm:.2f}  (T={T:.0f}N P={P/1000:.1f}kW)")
        worst = min(worst, fm)
    return worst


# ---------------------------------------------------------------- 2. reproduce a real catalog drone
def check_catalog_drone():
    """Closest build to the catalog winner (Velox V2808 KV1500, 7x4E, 6S 1300). Catalog says
    T_rotor 65 N, a_max 3.78 g, v_max 59.7 m/s, AUW 2.39 kg. How close is the model? (payload differs:
    catalog 2.5 kg vs our 0.5 kg, so mass/a_max won't match — but T_rotor and v_max should be close)."""
    print("\n2) REPRODUCE CATALOG WINNER  (Velox V2808 KV1500, 7x4E, 6S 1300)")
    # pick P_motor to be a realistic small motor (~0.5 kW for a 2808)
    d = Drone(D_in=7, pitch_in=4, Kv=1500, S=6, cap_mAh=1300, L_arm=0.139, P_motor=0.5)
    T = d.thrust_per_rotor()
    line("T/rotor", "PASS" if 40 <= T <= 90 else "SUSPECT", f"model {T:.0f} N  vs catalog 65 N")
    line("v_max", "PASS" if 45 <= d.v_max <= 75 else "SUSPECT", f"model {d.v_max:.0f} m/s vs catalog 60 m/s")
    line("mass", "note", f"model {d.mass:.2f} kg vs catalog 2.39 kg (our payload 0.5 vs catalog 2.5)")
    line("a_max", "note", f"model {d.a_max/G:.2f} g vs catalog 3.78 g (mass-dependent, so expected to differ)")


# ---------------------------------------------------------------- 3. hover feasibility
def check_hover():
    """Every design in the search box should at least be able to hover (TWR > 1) or it's nonsense."""
    print("\n3) HOVER FEASIBILITY across the search box")
    rng = random.Random(0); lo=[BOUNDS[k][0] for k in KEYS]; hi=[BOUNDS[k][1] for k in KEYS]
    n_bad = 0; twrs = []
    for _ in range(2000):
        d = Drone.from_vector([rng.uniform(lo[i], hi[i]) for i in range(len(KEYS))]).repaired()
        twrs.append(d.TWR)
        if d.TWR < 1.0: n_bad += 1
    frac = n_bad / len(twrs)
    line("TWR<1 (can't lift off)", "PASS" if frac < 0.15 else "SUSPECT",
         f"{frac*100:.0f}% of sampled designs  (min TWR {min(twrs):.2f}, median {sorted(twrs)[len(twrs)//2]:.2f})")


# ---------------------------------------------------------------- 4. monotonic trends
def check_trends():
    print("\n4) MONOTONIC TRENDS  (does raising a feature move dynamics the physical way?)")
    base = Drone(13, 6, 600, 6, 5000, 0.30, 1.5)
    def probe(field, k, mul):
        from dataclasses import replace
        d2 = replace(base, **{k: getattr(base, k) * mul}).repaired()
        return getattr(d2, field)
    tests = [
        ("P_motor up -> thrust up", base.thrust_per_rotor(), probe("thrust_per_rotor", "P_motor", 1.5) if False else Drone(13,6,600,6,5000,0.30,2.25).thrust_per_rotor(), ">"),
        ("S up -> thrust up", base.thrust_per_rotor(), Drone(13,6,600,9,5000,0.30,1.5).thrust_per_rotor(), ">"),
        ("D up -> thrust up", base.thrust_per_rotor(), Drone(18,6,600,6,5000,0.30,1.5).thrust_per_rotor(), ">"),
        ("pitch up -> v_max up", base.v_max, Drone(13,10,600,6,5000,0.30,1.5).v_max, ">"),
        ("P_motor up -> mass up", base.mass, Drone(13,6,600,6,5000,0.30,2.25).mass, ">"),
    ]
    for name, a, b, op in tests:
        ok = (b > a) if op == ">" else (b < a)
        line(name, "PASS" if ok else "FAIL", f"{a:.1f} -> {b:.1f}")


# ---------------------------------------------------------------- 5. v_max regime & realism
def check_vmax():
    print("\n5) v_max REGIME  (is pitch-limit or drag-limit binding, and is the value realistic?)")
    rng = random.Random(1); lo=[BOUNDS[k][0] for k in KEYS]; hi=[BOUNDS[k][1] for k in KEYS]
    vmaxes = []; pitch_bound = 0
    for _ in range(1500):
        d = Drone.from_vector([rng.uniform(lo[i], hi[i]) for i in range(len(KEYS))]).repaired()
        n = d.rev_per_s()
        v_pitch = d.pitch_in * IN2M * n * 0.85
        vmaxes.append(d.v_max)
        if abs(d.v_max - v_pitch) < 0.5: pitch_bound += 1
    vmaxes.sort()
    line("v_max spread", "note", f"p10 {vmaxes[150]:.0f}  median {vmaxes[750]:.0f}  p90 {vmaxes[1350]:.0f} m/s "
                                 f"(real interceptor quads ~40-60)")
    line("pitch-limited fraction", "note", f"{pitch_bound/len(vmaxes)*100:.0f}% of designs are pitch-speed limited")


# ---------------------------------------------------------------- 6. endurance realism
def check_endurance():
    print("\n6) HOVER ENDURANCE  (battery energy / hover power — should be minutes)")
    for d in [Drone(13,6,600,6,5000,0.30,1.5), Drone(18,8,450,8,8000,0.45,2.5)]:
        # momentum-theory hover power: P = (m g)^1.5 / (N * sqrt(2 rho A))
        A = math.pi * (d.D_in*IN2M/2)**2
        P_hover = (d.mass*G)**1.5 / (math.sqrt(N_ROTORS) * math.sqrt(2*RHO*A))
        t_min = d.usable_energy_J / P_hover / 60.0
        v = "PASS" if 2 <= t_min <= 60 else "SUSPECT"
        line(f"{d.D_in:.0f}x{d.pitch_in:.0f} {d.S:.0f}S {d.cap_mAh:.0f}mAh", v,
             f"hover {t_min:.1f} min  (P_hover {P_hover/1000:.2f} kW, {d.energy_Wh:.0f} Wh)")


# ---------------------------------------------------------------- 7. engagement responds to agility
def check_engagement():
    print("\n7) ENGAGEMENT  (does more agility actually reduce miss? does an immobile drone fail?)")
    world = threat_field(20)
    from drone import _Spec
    weak = _Spec(v_max=30, a_max=20, mass=3.0); agile = _Spec(v_max=30, a_max=120, mass=3.0)
    mw = sum(simulate(weak, t).miss for t in world)/len(world)
    ma = sum(simulate(agile, t).miss for t in world)/len(world)
    line("more a_max -> smaller miss", "PASS" if ma < mw else "FAIL", f"miss {mw:.1f} -> {ma:.1f} m")
    dead = _Spec(v_max=0.01, a_max=100, mass=3.0)
    hits = sum(1 for t in world if simulate(dead, t).intercepted)
    line("immobile drone fails all", "PASS" if hits == 0 else "FAIL", f"{hits}/{len(world)} intercepted")


if __name__ == "__main__":
    print("=" * 74)
    print("SANITY CHECK — SpecimenLab sizing model")
    print("=" * 74)
    check_figure_of_merit()
    check_catalog_drone()
    check_hover()
    check_trends()
    check_vmax()
    check_endurance()
    check_engagement()
    print("\n" + "=" * 74)
