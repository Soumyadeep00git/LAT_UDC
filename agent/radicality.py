"""RADICALITY — how far a design is allowed to cross, measured as distance in the physics graph.

Two mechanisms that provide the same capability are CLOSE if they share their governing structure and
differ by a hop (a prop and a ducted fan both rest on the actuator disk); they are FAR if reaching one
from the other means climbing to a shared fundamental and coming back down a different branch (a prop
and a jet only reconnect at 'conservation of momentum', then the jet dives into combustion/thermo).

Radicality(A, B) = shortest-path length between mechanism nodes A and B through the (undirected)
points_to graph. The user sets a RADIUS = the largest crossing allowed. Small radius -> only variations
on the same mechanism. Large radius -> a different mechanism entirely. This is the leash on generation:
you can rewrite the platform, but only out to the radicality budget, and the metric tells you exactly
what you are swapping.
"""
from collections import defaultdict, deque

import physics_archive as A

# undirected adjacency over points_to (a law and the laws it rests on are neighbours)
ADJ = defaultdict(set)
for _nid, _n in A.ARCHIVE.items():
    for _p in _n.points_to:
        if _p in A.ARCHIVE:
            ADJ[_nid].add(_p)
            ADJ[_p].add(_nid)

_LEVEL = {"system": 0, "high": 1, "mid": 2, "low": 3, "fundamental": 4}


def path(a, b):
    """Shortest path (list of node ids) from a to b through the graph, or [] if disconnected."""
    if a == b:
        return [a]
    prev = {a: None}
    q = deque([a])
    while q:
        x = q.popleft()
        for y in ADJ[x]:
            if y not in prev:
                prev[y] = x
                if y == b:
                    out = [b]
                    while prev[out[-1]] is not None:
                        out.append(prev[out[-1]])
                    return list(reversed(out))
                q.append(y)
    return []


def distance(a, b):
    p = path(a, b)
    return (len(p) - 1) if p else float("inf")


def alternatives(quantity, current, radius):
    """Other providers of `quantity` reachable within the radicality radius, nearest first."""
    out = []
    for nid in A.BY_QUANTITY.get(quantity, []):
        if nid == current:
            continue
        d = distance(current, nid)
        if d <= radius:
            out.append((nid, d))
    return sorted(out, key=lambda t: t[1])


def descent(nid, seen=None):
    """All laws a node transitively rests on (its full physical foundation)."""
    seen = set() if seen is None else seen
    for p in A.ARCHIVE[nid].points_to:
        if p in A.ARCHIVE and p not in seen:
            seen.add(p)
            descent(p, seen)
    return seen


def swap_report(a, b):
    """Explain the crossing A->B along three honest axes: the connecting PATH, how FUNDAMENTAL the shared
    pivot is (the real radicality tier), and the DIVERGENT PHYSICS the new mechanism drags in."""
    p = path(a, b)
    if not p:
        return {"reachable": False}
    pivot = max(p, key=lambda nid: _LEVEL[A.ARCHIVE[nid].level])
    lvl = A.ARCHIVE[pivot].level
    # the divergent-physics volume: laws B needs that A did not (the true cost of the swap)
    new_physics = sorted((descent(b) | {b}) - (descent(a) | {a}))
    tier = ("CROSS-FUNDAMENTAL (radical: you climb to an axiom and rebuild a different branch)"
            if lvl == "fundamental" else
            "VARIATION (same mechanism family — differs by a hop / boundary condition)")
    return {"reachable": True, "radicality": len(p) - 1, "path": p, "pivot": pivot,
            "pivot_level": lvl, "tier": tier, "new_physics": new_physics}


if __name__ == "__main__":
    current = "propulsion.actuator_disk_thrust"
    print(f"MECHANISM IN HAND: {current}  ('{A.ARCHIVE[current].law[:60]}...')\n")

    print("thrust providers, ranked by radicality (graph distance) from the prop:")
    for nid, d in alternatives("thrust", current, radius=99):
        print(f"   d={d}  {nid}")

    print("\nwhat each radius budget unlocks:")
    for R in (2, 4, 6):
        allowed = [nid for nid, d in alternatives("thrust", current, R)]
        print(f"   radius {R}: {allowed}")

    for target, name in [("propulsion.ducted_fan_thrust", "ducted fan"),
                         ("propulsion.airbreathing_thrust", "jet (airbreathing)")]:
        r = swap_report(current, target)
        print(f"\nSWAP REPORT  prop -> {name}:")
        print(f"   distance {r['radicality']}  |  pivot [{r['pivot']}] ({r['pivot_level']})")
        print(f"   tier: {r['tier']}")
        print(f"   new physics dragged in: {r['new_physics'] if r['new_physics'] else '(none — same foundation)'}")
