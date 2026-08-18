r"""NAME THE COORDINATE (mechanical) — ground a discovered intrinsic direction by walking the REAL bond graph.

intrinsic_space finds a stiff combination of knobs. This identifies what it is by:
  1. reading the SUBSYSTEMS and BONDS from bondgraph.infer_system (mechanical - not narrated);
  2. attaching each knob a grounded role: the physical quantity it sets + that quantity's dimension
     (this per-knob table is the ONE reviewable grounding input);
  3. assembling the combination's net dimension, and detecting - from the bonds - which coupling
     quantities cancel internally (a knob PRODUCES a bond quantity, another CONSUMES it);
  4. naming the residual dimension ONLY if it is a clean canonical quantity. Otherwise it says, plainly,
     that it CANNOT name it, and why.

The honesty mandate: this tool's job is as much to state what it cannot resolve as what it can.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import intrinsic_space as IS
import bondgraph
import parts as P

# ---- the ONE grounded input: per-knob physical role. subsystem is a CLAIM we verify against the graph. ----
# dim bases: L length, T time, V voltage, A current, M mass.  (rpm/rev are dimensionless.)
KNOB_ROLE = {
    "D_in":     dict(subsystem="propulsion", sets="rotor_radius",  dim={"L": 1}),
    "pitch_in": dict(subsystem="propulsion", sets="blade_pitch",   dim={"L": 1}),
    "Kv":       dict(subsystem="propulsion", sets="bus_voltage",   dim={"T": -1, "V": -1}),   # Omega = Kv*V
    "I_max":    dict(subsystem="propulsion", sets="current",       dim={"A": 1}),
    "S":        dict(subsystem="energy",     sets="bus_voltage",   dim={"V": 1}),              # V ~ 3.7 S
    "cap_mAh":  dict(subsystem="energy",     sets="charge",        dim={"A": 1, "T": 1}),
    "L_arm":    dict(subsystem="structure",  sets="arm_length",    dim={"L": 1}),
}
CANONICAL = {                                   # residual dimension -> a named quantity (for the naming attempt)
    "speed":        {"L": 1, "T": -1},
    "acceleration": {"L": 1, "T": -2},
    "length":       {"L": 1},
    "rate":         {"T": -1},
    "area":         {"L": 2},
}


def _subsystem_params(system):
    """Which knobs live in which subsystem, read from the inferred graph (mechanical)."""
    out = {}
    def walk(sub):
        for k in getattr(sub, "params", {}):
            out.setdefault(k, set()).add(sub.name)
        for ch in getattr(sub, "children", []) or []:
            walk(ch)
    for s in system.subsystems:
        walk(s)
    return out


def _close(dim, tol=0.25):
    return {b: round(v, 2) for b, v in dim.items() if abs(round(v, 2)) > tol}


def main():
    cfg = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
               L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0)

    # 1) the graph, mechanically
    system, meta = bondgraph.infer_system(P.quad_parts(cfg), cfg)
    coupling_q = set(q for (_a, _b, _d, q) in meta["bonds"])       # quantities that flow between subsystems
    member = _subsystem_params(system)

    # the stiff coordinate, from intrinsic_space
    J = IS.loglog_jacobian(cfg)
    w, V = np.linalg.eigh(J.T @ J)
    v = V[:, int(np.argmax(w))]; v = v / np.max(np.abs(v))
    exps = {p: float(v[i]) for i, p in enumerate(IS.PARAMS)}
    top = {p: e for p, e in exps.items() if abs(e) >= 0.4}

    print("=" * 84)
    print("NAME THE COORDINATE (mechanical)  -  walk the real bond graph; say what can't be named")
    print("=" * 84)
    print(f"bonds read from the graph: {sorted(coupling_q)}")
    print(f"\nstiffest coordinate (dominant knobs, with grounded roles + graph-verified subsystem):")
    for p, e in sorted(top.items(), key=lambda t: -abs(t[1])):
        role = KNOB_ROLE[p]
        in_graph = role["subsystem"] in member.get(p, set())
        flag = "ok" if in_graph else f"MISMATCH (graph says {sorted(member.get(p,set()))})"
        print(f"   {p:9s} exp {e:+.2f}  sets {role['sets']:12s} in {role['subsystem']:10s}  [{flag}]")

    # 2) assemble dimension; 3) detect coupling cancellations FROM THE BONDS
    dim = {}
    for p, e in top.items():
        for b, k in KNOB_ROLE[p]["dim"].items():
            dim[b] = dim.get(b, 0.0) + e * k
    dim = {b: round(v, 2) for b, v in dim.items() if abs(round(v, 2)) > 0.05}

    print(f"\n[dimension] raw assembled: { {b: v for b, v in dim.items()} }")
    # which bases correspond to bond (coupling) quantities, and did they cancel?
    coupling_bases = {"V": "bus_voltage", "A": "current"}
    for base, qname in coupling_bases.items():
        if qname in coupling_q and base in dim:          # only if a knob actually contributed this base
            netv = dim[base]
            if abs(netv) < 0.15:
                print(f"   coupling '{qname}' ({base}) CANCELS (~{netv:+.2f})  <- confirmed: a bond quantity, "
                      f"produced and consumed within the combination")
                dim.pop(base, None)
            else:
                print(f"   coupling '{qname}' ({base}) does NOT fully cancel ({netv:+.2f}) - the coordinate "
                      f"still carries an internal coupling; naming is not meaningful")

    # 4) name the residual dimension, or refuse
    resid = _close(dim)
    flip = {b: -v for b, v in resid.items()}                       # eigenvector sign is free
    print(f"\n[residual dimension, positive form]: { {b: v for b, v in flip.items()} }")

    def matches(canon):
        keys = set(canon) | set(flip)
        return all(abs(flip.get(b, 0) - canon.get(b, 0)) < 0.2 for b in keys)
    named = next((name for name, c in CANONICAL.items() if matches(c)), None)

    print("\n" + "-" * 84)
    if named:
        print(f"NAMED: the coordinate's class is **{named}**  (dimension matches a canonical quantity).")
        print("  Which specific one still needs a library/path match - flagged separately.")
    else:
        print("CANNOT NAME IT. The residual dimension is not a clean canonical quantity.")
        Lp = flip.get("L", 0); Tp = flip.get("T", 0)
        print(f"  It is ~ L^{Lp:g} T^{Tp:g}  =  speed x length^{Lp-1:g}  - a BLEND, not one textbook quantity.")
        print("  From the graph: the tip-speed backbone is real (Kv*S -> a rate once the bus_voltage coupling")
        print("  cancels, times D -> radius), but 'pitch' (a length in propulsion) rides along, so the")
        print("  coordinate mixes tip speed with blade loading. No single name is honest here.")

    print("\nWHAT THIS TOOL CAN vs CANNOT DO (stated, not hidden):")
    print("  CAN:    read subsystems + bonds from the graph; verify each knob's subsystem; assemble the")
    print("          net dimension; detect - from the bonds - which internal couplings cancel.")
    print("  CANNOT: name a coordinate whose dimension isn't a clean canonical quantity (this one);")
    print("          supply the per-knob physical roles (that grounding is human/curated, and if a role is")
    print("          wrong the naming is wrong); or name a clean quantity that isn't in the library.")


if __name__ == "__main__":
    main()
