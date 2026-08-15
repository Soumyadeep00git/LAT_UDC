"""Assemble the agent-built physics library into physics_archive.py, and print the verify report."""
import json
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else None
DEST = os.path.join(os.path.dirname(__file__), "physics_archive.py")

with open(OUT, "r", encoding="utf-8") as f:
    raw = json.load(f)

data = raw.get("result", raw)
if isinstance(data, str):
    data = json.loads(data)
nodes = data["nodes"]
report = data.get("report", {})
by_id = {}
for n in nodes:
    by_id.setdefault(n["id"], n)          # dedup (first wins)
ids = set(by_id)

# ---- integrity pass (independent of the verify agent) ----
dangling = {}
for nid, n in by_id.items():
    miss = [p for p in n.get("points_to", []) if p not in ids]
    if miss:
        dangling[nid] = miss
# descent to a fundamental
def descends(nid, seen=None):
    seen = seen or set()
    if nid in seen:
        return False
    seen.add(nid)
    n = by_id.get(nid)
    if not n:
        return False
    if n["provenance"] == "fundamental":
        return True
    return any(descends(p, seen) for p in n.get("points_to", []) if p in ids)
orphans = [nid for nid, n in by_id.items() if n["provenance"] != "fundamental" and not descends(nid)]

# per-domain counts
dom = {}
for n in by_id.values():
    dom[n["domain"]] = dom.get(n["domain"], 0) + 1

# ---- emit physics_archive.py ----
def dir_map(reqs):
    return {r["variable"]: (1 if r["direction"] == "+" else -1 if r["direction"] == "-" else 0) for r in reqs}

lines = ['"""Agent-built physics archive — %d nodes, %d domains. Generated; do not hand-edit.' % (len(by_id), len(dom)),
         'Each node: quantity, law, provenance, level, domain, requires (fingerprint {var:+1/-1/0}), points_to."""',
         "from dataclasses import dataclass, field", "", "@dataclass", "class ArcNode:",
         "    id: str", "    quantity: str", "    law: str", "    provenance: str", "    level: str",
         "    domain: str", "    requires: dict", "    points_to: list", "", "ARCHIVE = {"]
for nid in sorted(by_id):
    n = by_id[nid]
    lines.append("    %r: ArcNode(%r, %r, %r, %r, %r, %r, %r, %r)," % (
        nid, nid, n["quantity"], n["law"], n["provenance"], n["level"], n["domain"],
        dir_map(n.get("requires", [])), n.get("points_to", [])))
lines.append("}")
lines.append("")
lines.append("# quantity -> node ids that define it (for grounding). Prefer the most fundamental.")
lines.append("BY_QUANTITY = {}")
lines.append("for _n in ARCHIVE.values():")
lines.append("    BY_QUANTITY.setdefault(_n.quantity, []).append(_n.id)")
with open(DEST, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# ---- report ----
print(f"ASSEMBLED physics_archive.py : {len(by_id)} unique nodes")
print("per-domain:", ", ".join(f"{k} {v}" for k, v in sorted(dom.items())))
print(f"\nINTEGRITY (independent check):")
print(f"  dangling pointers: {sum(len(v) for v in dangling.values())} across {len(dangling)} nodes")
print(f"  orphan nodes (no descent to a fundamental): {len(orphans)}")
if dangling:
    ex = list(dangling.items())[:5]
    for nid, miss in ex:
        print(f"    {nid} -> missing {miss[:3]}")
print(f"\nVERIFY AGENT REPORT:")
print(f"  dangling(agent): {len(report.get('dangling', []))}  orphans(agent): {len(report.get('orphans', []))}")
print(f"  corrections flagged: {len(report.get('corrections', []))}")
for c in report.get("corrections", [])[:8]:
    print(f"    [{c.get('id')}] {c.get('issue')}  -> fix: {c.get('fix')}")
print(f"\n  summary: {report.get('summary', '')[:600]}")
