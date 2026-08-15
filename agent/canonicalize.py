"""Canonicalization / curation pass — normalize the fragmented QUANTITY vocabulary the 30 independent
agents produced, so grounding and radicality crossings stop splitting one capability across many names.

This is BUILD-TIME curation (deterministic, reviewable), NOT runtime fuzzy matching. First cut: collapse
the ~15 'thrust'-family quantity strings to canonical 'thrust' (excluding genuinely different quantities
like thrust_coefficient, thrust_power, tsfc). Print every merge so it can be audited. Regenerate
physics_archive.py in place. A fuller pass (an expert agent building the whole canonical map) is the
production version; this makes the fragmentation visible and unblocks the prototype.
"""
import os
from collections import defaultdict

import physics_archive as A

DEST = os.path.join(os.path.dirname(__file__), "physics_archive.py")

# curated canonical map: predicate -> canonical quantity name
EXCLUDE_THRUST = ("coefficient", "power", "tsfc", "fuel", "vector", "ground", "loading", "specific_impulse")


def canon(q):
    ql = q.lower().replace(" ", "_")
    if "thrust" in ql and not any(x in ql for x in EXCLUDE_THRUST):
        return "thrust"
    return q


merges = defaultdict(set)
for n in A.ARCHIVE.values():
    c = canon(n.quantity)
    if c != n.quantity:
        merges[c].add(n.quantity)
    n.quantity = c

# regenerate the archive file with canonicalized quantities
lines = ['"""Agent-built MEGA physics archive (canonicalized). %d nodes. Generated; do not hand-edit."""' % len(A.ARCHIVE),
         "from dataclasses import dataclass", "", "@dataclass", "class ArcNode:",
         "    id: str", "    quantity: str", "    law: str", "    provenance: str", "    level: str",
         "    domain: str", "    requires: dict", "    points_to: list", "", "ARCHIVE = {"]
for nid in sorted(A.ARCHIVE):
    n = A.ARCHIVE[nid]
    lines.append("    %r: ArcNode(%r, %r, %r, %r, %r, %r, %r, %r)," % (
        nid, nid, n.quantity, n.law, n.provenance, n.level, n.domain, dict(n.requires), list(n.points_to)))
lines += ["}", "", "BY_QUANTITY = {}", "for _n in ARCHIVE.values():",
          "    BY_QUANTITY.setdefault(_n.quantity, []).append(_n.id)"]
open(DEST, "w", encoding="utf-8").write("\n".join(lines))

print("CANONICALIZATION pass (first cut, thrust family):")
for canonical, variants in merges.items():
    print(f"  '{canonical}' <- {len(variants)} variants: {sorted(variants)}")
import importlib
importlib.reload(A)
print(f"\n  'thrust' now has {len(A.BY_QUANTITY.get('thrust', []))} provider nodes (was fragmented).")
