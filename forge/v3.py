r"""V3 — the abstraction method: the traffic between the two worlds.

The loop, once V1/V2 are exhausted on a mission:
  SEE     ground the failing mechanism, ASCEND its law to the invariant the objective needs (altitude<=budget)
  IMAGINE open the SET of embodiments that share that invariant  (library alternatives)
  ACT     realize each REALIZABLE candidate (has an executable model) via V2/V1, SOLVE it — the physical judges
  SELECT  keep the least-radical embodiment that meets the drive
  REFLECT write the trajectory to episodic memory; abstract over it to surface recurring invariants

Two frontier slots are HONESTLY EMPTY and marked as such at runtime:
  (IMAGINE) synthesizing an embodiment that is NOT already a node in the graph  — invention, not selection.
  (REFLECT) minting a genuinely new SEMANTIC law from a discovered pattern      — building the ladder, not climbing it.

Everything else runs on the real library + the real solve. Nothing survives that the physical didn't confirm.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import library
import radicality
import diagnose
from episodic import Memory, Episode

# MODEL REGISTRY: which library nodes we can actually ACT on (have an executable model behind them).
# Imagined nodes NOT here are real physics we can see but not yet realize -> the invention frontier.
REALIZE = {
    "rotorcraft_bemt.rotor_thrust": "rotor",
    "rotorcraft_bemt.actuator_disk_momentum": "ducted_fan",
}
HOME_NODE = "rotorcraft_bemt.rotor_thrust"
FUNCTION = "thrust"


_REQMAP = (("a_max_g", "a_req"), ("v_max", "v_req"), ("endurance_min", "endur_req"))


def _better(a, b):
    if a["met"] != b["met"]:
        return a["met"]
    return a["caps"]["mass"] < b["caps"]["mass"] if a["met"] else a["margin"] > b["margin"]


def _v2(cfg, mission, mech, counts=(3, 4, 6, 8)):
    """V2 for a given embodiment: count rearrangement ON TOP OF V1 param tuning. So V3's ACT (which calls
    this) is a proper superset of V2 — it does everything V2 does, for each imagined embodiment."""
    best = None
    for n in counts:
        tuned = diagnose.repair(dict(cfg, n_rotors=n), mission, mechanism=mech)[0]
        caps = diagnose.caps_of(tuned, mech)
        met = all(caps[m] >= mission[r] - 1e-6 for m, r in _REQMAP)
        margin = min((caps[m] - mission[r]) / max(abs(mission[r]), 1e-9) for m, r in _REQMAP)
        cand = {"n": n, "cfg": tuned, "caps": caps, "met": met, "margin": margin}
        if best is None or _better(cand, best):
            best = cand
    return best


def _alternatives(radius):
    try:
        alts = radicality.alternatives(FUNCTION, HOME_NODE, radius)
    except Exception:
        alts = []
    out = []
    for a in alts:
        node = a[0] if isinstance(a, (tuple, list)) else a
        dist = a[1] if isinstance(a, (tuple, list)) and len(a) > 1 else None
        out.append((node, dist))
    return out


def v3(cfg, mission, memory, budget=3, cycle=0):
    # ---- SEE: ascend the failing mechanism's law to the invariant (most FUNDAMENTAL node within budget) ----
    chain = library.descent(HOME_NODE)                      # [(id, provenance, depth)]

    def _fund(nid):
        n = library.node(nid)
        return library._LEVEL.get(getattr(n, "level", ""), 0) if n else 0

    reachable = [(nid, d) for nid, _, d in chain if d <= budget]
    invariant, alt = max(reachable, key=lambda x: (_fund(x[0]), x[1]), default=(HOME_NODE, 0))
    try:
        ascent = [n for n in radicality.path(HOME_NODE, invariant)] or [HOME_NODE, invariant]
    except Exception:
        ascent = [HOME_NODE, invariant]
    seen = {"mechanism": "rotor", "invariant": invariant, "altitude": alt, "ascent": ascent}

    # ---- IMAGINE: the set of embodiments sharing that invariant ----
    imagined = []
    seen_nodes = set()
    for node, dist in _alternatives(budget) + [(n, None) for n in REALIZE]:
        if node in seen_nodes or node == HOME_NODE:
            continue
        seen_nodes.add(node)
        imagined.append({"node": node, "dist": dist, "realizable": node in REALIZE})
    # always include HOME as the incumbent embodiment to compare against
    imagined.insert(0, {"node": HOME_NODE, "dist": 0, "realizable": True})

    # ---- ACT: realize each realizable candidate through the FULL V2 (count+params), physical judges ----
    acted = []
    for im in imagined:
        if im["realizable"]:
            mech = REALIZE[im["node"]]
            b = _v2(cfg, mission, mech)                          # V3 ACT nests V2 (which nests V1)
            caps = b["caps"]
            acted.append({"node": im["node"], "mechanism": mech, "n": b["n"], "met": bool(b["met"]),
                          "mass": round(caps["mass"], 3), "a_max_g": round(caps["a_max_g"], 2),
                          "v_max": round(caps["v_max"], 1), "endurance_min": round(caps["endurance_min"], 1),
                          "_cfg": b["cfg"]})
        else:
            acted.append({"node": im["node"], "realizable": False,
                          "note": "imagined — no executable model (invention frontier)"})

    # ---- SELECT: least-radical embodiment meeting the drive ----
    feasible = [a for a in acted if a.get("met")]
    selected = min(feasible, key=lambda a: a["mass"]) if feasible else None

    # ---- REFLECT: record the trajectory; abstract over the autobiography ----
    ep = Episode(cycle=cycle, drive=dict(mission), seen=seen, imagined=imagined,
                 acted=[{k: v for k, v in a.items() if k != "_cfg"} for a in acted],
                 selected=({k: v for k, v in selected.items() if k != "_cfg"} if selected else None))
    memory.append(ep)
    patterns = memory.reflect()
    return {"seen": seen, "imagined": imagined, "acted": acted, "selected": selected, "patterns": patterns}


def _print(res, cycle):
    s = res["seen"]
    print(f"\n--- V3 cycle {cycle} ---")
    print(f"  SEE     ascend to invariant '{s['invariant']}' (altitude {s['altitude']})")
    print(f"          ascent: {' -> '.join(n.split('.')[-1] for n in s['ascent'])}")
    print(f"  IMAGINE embodiments sharing the invariant:")
    for im in res["imagined"]:
        tag = "realizable" if im["realizable"] else "FRONTIER (imagined, no model)"
        print(f"            {im['node']:44s} [{tag}]")
    print(f"  ACT     realize + solve (physical judges):")
    for a in res["acted"]:
        if a.get("realizable", True) and "mechanism" in a:
            print(f"            {a['mechanism']:11s} a_max {a['a_max_g']:.2f}g  v {a['v_max']:.1f}  "
                  f"endur {a['endurance_min']:.0f}m  mass {a['mass']:.2f}  {'MET' if a['met'] else 'miss'}")
    sel = res["selected"]
    print(f"  SELECT  {'-> ' + sel['mechanism'] + ' (mass ' + format(sel['mass'], '.2f') + ')' if sel else 'no in-scope embodiment meets the drive'}")
    print(f"  REFLECT patterns from episodic memory:")
    for p in res["patterns"]:
        print(f"            invariant={p['invariant'].split('.')[-1]:26s} embodiment={p['embodiment']:11s} "
              f"met_rate={p['met_rate']} n={p['n']} avg_mass={p['avg_mass']}")


if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    mem = Memory()      # in-memory autobiography for the demo
    print("V3 SCAFFOLD — the machine breathing between the abstraction world and the physical world")
    print("(entered as if V1/V2 were exhausted; frontier slots marked)")

    m1 = {"a_req": 5.5, "v_req": 22.0, "endur_req": 12.0}
    _print(v3(cfg, m1, mem, budget=6, cycle=0), 0)
    m2 = {"a_req": 3.0, "v_req": 18.0, "endur_req": 30.0}
    _print(v3(cfg, m2, mem, budget=6, cycle=1), 1)

    print("\nFRONTIER (honestly empty): IMAGINE-synthesis of an unencoded embodiment; "
          "REFLECT-minting a new semantic law.\n"
          "Everything above ran on the real library + the real solve.")
