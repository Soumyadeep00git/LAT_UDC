r"""V3 LEASHLESS — drop the radicality budget and let abstraction cross as far as physics allows.

Context: the interception ceiling (~20%) is a TOPOLOGY wall - a quad's rotor thrust can't reach the speeds
that catch fast threats, no matter how V1/V2 tune it. V3's job is to abstract past that. The LEASH
(radicality budget) normally holds it to nearby mechanisms; leashless removes it.

Ascend the binding quantity (thrust) to its invariant, then enumerate EVERY mechanism the physics graph
offers, at any distance. For each crossing report, honestly:
  - radicality distance      how far the leash had to stretch (graph hops)
  - tier                     VARIATION (same family) vs CROSS-FUNDAMENTAL (climb to an axiom, new branch)
  - divergent physics        the laws the new mechanism drags in that the rotor never needed (the real cost)
  - realizable?              is there a built model, or is this pure FRONTIER (imagined, unvalidated)

Leashed V3 stays in the rotorcraft family (no speed breakout). Leashless V3 reaches jet/rocket - the
mechanisms that COULD break the wall - but every one is unrealized. Imagination is free; realization is
the wall. This is V3's true reach, stated without overselling it.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import library as L
import radicality as R
from vocabulary import canonical

A = L.A.ARCHIVE
CURRENT = "rotorcraft_bemt.rotor_thrust"          # the quad's propulsion mechanism (the ceiling)
# mechanisms with a BUILT forge model (everything else is frontier)
REALIZABLE = {"rotorcraft_bemt.rotor_thrust", "rotorcraft_bemt.actuator_disk_momentum"}


def alternatives(quantity="thrust", current=CURRENT, radius=float("inf")):
    out = []
    for nid, n in A.items():
        if nid == current or canonical(n.quantity) != quantity:
            continue
        d = R.distance(current, nid)
        if d <= radius:
            out.append((nid, d))
    return sorted(out, key=lambda t: (t[1] == float("inf"), t[1]))


def report(nid):
    rep = R.swap_report(CURRENT, nid)
    fam = nid.split(".")[0]
    return {
        "node": nid, "family": fam,
        "distance": rep.get("radicality") if rep.get("reachable") else None,
        "tier": rep.get("tier", "DISCONNECTED (no graph path - needs a new shared pivot)"),
        "new_physics": len(rep.get("new_physics", [])) if rep.get("reachable") else None,
        "realizable": nid in REALIZABLE,
    }


if __name__ == "__main__":
    print("=" * 88)
    print("V3 LEASHLESS  -  abstraction let loose on the interception ceiling (binding quantity: thrust)")
    print("=" * 88)
    print(f"current mechanism (the quad's ceiling): {CURRENT}")

    leashed = alternatives(radius=2)               # the rotor's normal radicality budget
    print(f"\nLEASHED (radius=2, the rotor's budget): {len(leashed)} reachable mechanism(s)")
    for nid, d in leashed:
        r = report(nid)
        tier = "cross-fundamental" if "CROSS" in r["tier"] else ("variation" if "VARIATION" in r["tier"] else "disconnected")
        print(f"   d={d}  {nid:42s} [{'realizable' if r['realizable'] else 'FRONTIER'}]  {tier}")

    allm = alternatives(radius=float("inf"))
    print(f"\nLEASHLESS (radius=inf): {len(allm)} mechanism(s) physics offers for thrust")
    print(f"   {'dist':>5} {'realizable':>10}  {'new-physics':>11}  mechanism / tier")
    for nid, d in allm:
        r = report(nid)
        ds = "inf" if d == float("inf") else str(int(d))
        rz = "yes" if r["realizable"] else "FRONTIER"
        npy = "-" if r["new_physics"] is None else str(r["new_physics"])
        tier = "cross-fundamental" if "CROSS" in r["tier"] else ("variation" if "VARIATION" in r["tier"] else "disconnected")
        print(f"   {ds:>5} {rz:>10}  {npy:>11}  {nid.split('.')[-1]:24s} ({r['family']}, {tier})")

    real = [nid for nid, _ in allm if nid in REALIZABLE]
    front = [nid for nid, _ in allm if nid not in REALIZABLE]
    print("\n" + "-" * 88)
    print(f"REALIZABLE (has a built model): {len(real)}  -> {[n.split('.')[-1] for n in real]}")
    print(f"FRONTIER (imagined, no model):  {len(front)}  -> jet / rocket / nozzle families")
    print("\nHONEST READ: leashed, V3 sees only the rotorcraft family - no way past the speed wall. Leashless,")
    print("it reaches the airbreathing/rocket mechanisms that COULD break it - but each is a cross-fundamental")
    print("crossing that drags in combustion/thermo/nozzle physics, and NONE is realizable here. V3's true")
    print("reach is to name the platform class that wins and price the leap; building it is the wall.")
