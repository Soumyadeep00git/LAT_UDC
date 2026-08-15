r"""The layered design cascade — deterministic realization of Layers I..VII.

    FORWARD  (instantiate):  I design -> II architecture -> III physics -> IV objective
    BACKWARD (improve, reverse order):
        IV objective
          -> repair the DESIGN by gradient  (III->I, real Jacobian: diagnose.repair)
             if exhausted:
          -> V   modify PHYSICS      (which validity assumption is binding; name the generalization)
          -> VI  modify ARCHITECTURE (swap to another in-scope mechanism, which carries different physics)
          -> VII new DESIGN          (re-instantiate + re-solve under the chosen architecture + physics)

This is NOT gradient flow through every layer (physics/architecture changes are discrete). It is an
ordered cascade: gradient for the design, radicality-gated search for physics and architecture. Every
step is the real forge engine; the output is a new design WITH its provenance — which architecture and
which physics back it. Scope is MULTIROTOR: mechanisms {rotor, ducted_fan}; cross-class (wing) is gated
experimental (see [[specimenlab-cad-app]]).
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose
from uav import build_uav, capabilities, G, IN2M      # noqa: E402
from solve import solve                                # noqa: E402
try:
    import radicality                                  # noqa: E402
except Exception:
    radicality = None

# --- Layer II vocabulary: the in-scope architectures (mechanism -> physics node it grounds to) ---
MECH_NODE = {"rotor": "rotorcraft_bemt.rotor_thrust",
             "ducted_fan": "rotorcraft_bemt.actuator_disk_momentum"}
IN_SCOPE = ["rotor", "ducted_fan"]

# --- Layer III: physics validity envelope (assumptions behind the active law) ---
ENV = {"tip_mach": 0.70, "disk_loading": 250.0, "twr_min": 1.2}


@dataclass
class Design:
    cfg: dict
    mechanism: str = "rotor"
    caps: dict = field(default_factory=dict)
    gaps: dict = field(default_factory=dict)
    met: bool = False
    physics_flags: list = field(default_factory=list)
    log: list = field(default_factory=list)            # (layer, message) provenance trail


def _physics_flags(cfg, mechanism):
    """Layer III check: which validity assumptions of the active law are violated at this operating point."""
    sysm = build_uav(cfg, propulsion_mechanism=mechanism)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus)
    prop = sysm.by_name()["propulsion"]
    n = prop.params["n_rotors"]; R = prop.params["D_in"] * IN2M / 2
    rpm = prop.state.get("_rpm", 0.0)
    tip_mach = (rpm * 2 * math.pi / 60.0) * R / 343.0 if rpm else 0.0
    A = n * math.pi * R * R
    dl = cap["thrust"] / A if A > 0 else 0.0
    flags = []
    if tip_mach > ENV["tip_mach"]:
        flags.append(f"incompressibility violated (tip Mach {tip_mach:.2f}>{ENV['tip_mach']}) "
                     f"-> generalizes_to: compressible BEMT [not encoded]")
    if dl > ENV["disk_loading"]:
        flags.append(f"momentum-theory hover assumption strained (disk loading {dl:.0f} N/m2) "
                     f"-> generalizes_to: higher-fidelity wake model [not encoded]")
    if cap["TWR"] < ENV["twr_min"]:
        flags.append(f"insufficient control margin (TWR {cap['TWR']:.2f}<{ENV['twr_min']})")
    return flags, cap


# ------------------------------------------------------------------ FORWARD
def forward(cfg, mission, mechanism="rotor"):
    """I design -> II architecture(mechanism) -> III physics(grounding+validity) -> IV objective."""
    caps = diagnose.caps_of(cfg, mechanism)
    reqs = diagnose._reqs(mission)
    gaps = {m: caps[m] - reqs[m] for m in diagnose.METRICS}
    flags, _ = _physics_flags(cfg, mechanism)
    met = all(gaps[m] >= -1e-6 for m in diagnose.METRICS)
    d = Design(cfg=dict(cfg), mechanism=mechanism, caps=caps, gaps=gaps, met=met, physics_flags=flags)
    d.log.append(("I/design", "  ".join(f"{k}={cfg[k]:.1f}" for k in diagnose.PARAMS)))
    d.log.append(("II/arch", f"multirotor · propulsion mechanism = {mechanism} [{MECH_NODE[mechanism]}]"))
    d.log.append(("III/physics", "; ".join(flags) if flags else "all law assumptions valid in regime"))
    d.log.append(("IV/objective", f"{'MET' if met else 'UNMET'}  "
                  + " ".join(f"{m}:{caps[m]:.1f}/{reqs[m]:.0f}" for m in diagnose.METRICS)))
    return d


# ------------------------------------------------------------------ BACKWARD
def backward(cfg, mission, mechanism="rotor", allow_experimental=False):
    """Ordered improvement: gradient-repair the design; if exhausted, question physics (V) and swap
    architecture (VI) within scope, then re-instantiate the design (VII)."""
    log = []

    # IV -> VII inner: repair the DESIGN by the objective gradient (this is the III->I backprop)
    cfg1, met, ex, hist, info = diagnose.repair(cfg, mission, mechanism)
    log.append(("VII/design", f"gradient repair under '{mechanism}': "
                f"{'MET in ' + str(len(hist)-1) + ' null-space steps' if met else 'EXHAUSTED'}"))
    if met:
        return _finish(cfg1, mechanism, mission, log, "design tuned; architecture & physics unchanged")

    # V: modify PHYSICS — name the binding validity assumption that blocks further design tuning
    flags, _ = _physics_flags(cfg1, mechanism)
    log.append(("V/physics", "binding assumption: " + (flags[0] if flags
                else f"{info.get('failing','metric')} gradient collapsed (no valid encoded relaxation)")))

    # VI: modify ARCHITECTURE — try other in-scope mechanisms (each grounds to different physics),
    #     then re-repair the design under the new architecture.
    for mech in IN_SCOPE:
        if mech == mechanism:
            continue
        d = radicality.distance(MECH_NODE[mechanism], MECH_NODE[mech]) if radicality else "?"
        cfg2, met2, ex2, hist2, info2 = diagnose.repair(cfg1, mission, mech)
        log.append(("VI/arch", f"swap {mechanism}->{mech} (radicality d={d}); physics node "
                    f"{MECH_NODE[mechanism]}->{MECH_NODE[mech]}; re-repair: {'MET' if met2 else 'no'}"))
        if met2:
            return _finish(cfg2, mech, mission, log,
                           f"design re-derived on a NEW architecture ({mech}) backed by NEW physics "
                           f"({MECH_NODE[mech]})")

    # scope boundary: cross-class change would be needed
    log.append(("scope", "no in-scope architecture meets the objective — BEYOND THE MULTIROTOR ENVELOPE"))
    if allow_experimental:
        w = diagnose.wing_alternative(cfg1, mission)
        log.append(("VI/arch(exp)", f"[experimental, outside UAV scope] fixed wing: "
                    f"endurance {w['endurance_min']:.0f} min, meets={w['meets_endurance']}"))
    return _finish(cfg1, mechanism, mission, log, "objective NOT met within multirotor scope", met=False)


def _finish(cfg, mechanism, mission, log, summary, met=True):
    caps = diagnose.caps_of(cfg, mechanism)
    reqs = diagnose._reqs(mission)
    met = met and all(caps[m] >= reqs[m] - 1e-6 for m in diagnose.METRICS)
    flags, _ = _physics_flags(cfg, mechanism)
    d = Design(cfg=cfg, mechanism=mechanism, caps=caps,
               gaps={m: caps[m]-reqs[m] for m in diagnose.METRICS}, met=met,
               physics_flags=flags, log=log)
    d.log.append(("=summary", summary))
    return d


def cascade(cfg, mission, mechanism="rotor", allow_experimental=False):
    """Full pass: forward (instantiate) then backward (improve). Returns the new Design + provenance."""
    fwd = forward(cfg, mission, mechanism)
    out = backward(cfg, mission, mechanism, allow_experimental=allow_experimental)
    out.log = fwd.log + [("--", "BACKWARD ------------------------------")] + out.log
    return out


# ------------------------------------------------------------------ headless demo
if __name__ == "__main__":
    base = dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6, cap_mAh=5000,
                C_rate=60, L_arm=0.30, payload=0.6, n_rotors=4)

    def run(title, mission, exp=False):
        print("\n" + "=" * 76 + f"\n{title}\n  mission: {mission}")
        out = cascade(base, mission, allow_experimental=exp)
        for layer, msg in out.log:
            print(f"  {layer:14s} {msg}")
        print(f"  RESULT: {'MET' if out.met else 'NOT MET'}  mechanism={out.mechanism}  "
              f"mass={out.caps['mass']:.2f}kg  a={out.caps['a_max_g']:.2f}g  "
              f"v={out.caps['v_max']:.1f}  endur={out.caps['endurance_min']:.0f}min")

    run("A) tunable by DESIGN alone (agility)", {"a_req": 6.0, "v_req": 10.0, "endur_req": 15.0})
    run("B) needs an ARCHITECTURE change (high static thrust favors the duct)",
        {"a_req": 9.0, "v_req": 8.0, "endur_req": 10.0})
    run("C) beyond the multirotor envelope (endurance) -> scope boundary",
        {"a_req": 1.5, "v_req": 8.0, "endur_req": 200.0}, exp=True)
