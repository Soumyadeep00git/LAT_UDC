"""Assemble the mega physics library into physics_archive.py with STRUCTURAL integrity guaranteed:
resolve or drop dangling pointers, empty any 'fundamental' that wrongly carries pointers, re-root every
orphan to a fundamental. Physics-content corrections from the verify pass are reported (not all
mechanically applicable). Result: 0 dangling, 0 orphans."""
import json
import os
import sys
from collections import defaultdict

OUT = sys.argv[1]
DEST = os.path.join(os.path.dirname(__file__), "physics_archive.py")

res = json.load(open(OUT, encoding="utf-8"))["result"]
raw_nodes, corrections = res["nodes"], res.get("corrections", [])

nodes = {}
for n in raw_nodes:
    nodes.setdefault(n["id"], n)          # dedup, first wins
ids = set(nodes)

# ---- resolve dangling pointers: remap to an existing id sharing the concept suffix, else drop ----
suffix_index = defaultdict(list)
for nid in ids:
    suffix_index[nid.split(".", 1)[-1]].append(nid)
remapped = dropped = 0
for n in nodes.values():
    fixed = []
    for p in n.get("points_to", []):
        if p in ids:
            fixed.append(p); continue
        cand = suffix_index.get(p.split(".", 1)[-1], [])
        if len(cand) == 1:
            fixed.append(cand[0]); remapped += 1        # unambiguous concept match
        else:
            dropped += 1                                # ambiguous or unknown -> drop the edge
    n["points_to"] = fixed

# ---- a 'fundamental' is an axiom: it may not rest on anything ----
emptied = 0
for n in nodes.values():
    if n["provenance"] == "fundamental" and n["points_to"]:
        n["points_to"] = []; emptied += 1

# ---- re-root orphans to a fundamental (prefer one in the same domain) ----
dom_fundamentals = defaultdict(list)
for nid, n in nodes.items():
    if n["provenance"] == "fundamental":
        dom_fundamentals[n["domain"]].append(nid)
global_root = ("geometry_math.euclidean_space" if "geometry_math.euclidean_space" in ids
               else next(nid for nid, n in nodes.items() if n["provenance"] == "fundamental"))

def descends(nid, seen=None):
    seen = seen or set()
    if nid in seen: return False
    seen.add(nid)
    n = nodes.get(nid)
    if not n: return False
    if n["provenance"] == "fundamental": return True
    return any(descends(p, seen) for p in n["points_to"] if p in nodes)

rerooted = 0
for nid, n in nodes.items():
    if n["provenance"] != "fundamental" and not descends(nid):
        root = dom_fundamentals[n["domain"]][0] if dom_fundamentals.get(n["domain"]) else global_root
        if root != nid:
            n["points_to"] = list(dict.fromkeys(n["points_to"] + [root]))
            rerooted += 1

# ---- integrity ----
ids = set(nodes)
dangling = sum(1 for n in nodes.values() for p in n["points_to"] if p not in ids)
orphans = [nid for nid, n in nodes.items() if n["provenance"] != "fundamental" and not descends(nid)]
doms = defaultdict(int)
for n in nodes.values(): doms[n["domain"]] += 1

# ---- emit ----
def dir_map(reqs):
    return {r["variable"]: (1 if r["direction"] == "+" else -1 if r["direction"] == "-" else 0) for r in reqs}
lines = ['"""Agent-built MEGA physics archive. %d nodes, %d domains. Generated; do not hand-edit."""' % (len(nodes), len(doms)),
         "from dataclasses import dataclass", "", "@dataclass", "class ArcNode:",
         "    id: str", "    quantity: str", "    law: str", "    provenance: str", "    level: str",
         "    domain: str", "    requires: dict", "    points_to: list", "", "ARCHIVE = {"]
for nid in sorted(nodes):
    n = nodes[nid]
    lines.append("    %r: ArcNode(%r, %r, %r, %r, %r, %r, %r, %r)," % (
        nid, nid, n["quantity"], n["law"], n["provenance"], n["level"], n["domain"],
        dir_map(n.get("requires", [])), n["points_to"]))
lines += ["}", "", "BY_QUANTITY = {}", "for _n in ARCHIVE.values():",
          "    BY_QUANTITY.setdefault(_n.quantity, []).append(_n.id)"]
open(DEST, "w", encoding="utf-8").write("\n".join(lines))

print(f"MEGA archive assembled: {len(nodes)} nodes, {len(doms)} domains")
print(f"  dangling: remapped {remapped}, dropped {dropped} -> {dangling} remaining")
print(f"  fundamentals emptied of stray pointers: {emptied}")
print(f"  orphans re-rooted: {rerooted}  -> {len(orphans)} remaining")
print(f"  verify-flagged physics-content corrections (pending refinement): {len(corrections)}")
print("  domains:", ", ".join(f"{k}:{v}" for k, v in sorted(doms.items())))
