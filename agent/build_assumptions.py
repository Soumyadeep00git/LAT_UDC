"""Assemble the annotation workflow's output into assumption_cards.py (loaded by assumptions.py).
Reconciles each card's node_id to a real library node where possible (exact id, else by quantity name)."""
import html
import json
import sys

import physics_archive as A

res = json.load(open(sys.argv[1], encoding="utf-8"))["result"]
cards = res["cards"]

def clean(s):                                            # agents HTML-escaped operators (&lt; &gt;)
    return html.unescape(s) if isinstance(s, str) else s
for c in cards:
    c["law"] = clean(c["law"])
    for a in c["assumptions"]:
        for k in a:
            a[k] = clean(a[k])

matched = unmatched = 0
lines = ['"""Generated assumption cards (do not hand-edit). {node_id: {law, assumptions[...]}}."""',
         "CARDS = {"]
for c in cards:
    nid = c["node_id"]
    if nid not in A.ARCHIVE:                              # try to reconcile to a real node by concept suffix
        concept = nid.split(".", 1)[-1]
        cand = [x for x in A.ARCHIVE if x.split(".", 1)[-1] == concept]
        if cand:
            nid = cand[0]; matched += 1
        else:
            unmatched += 1                                # keep the agent's id; it's a "needs node" marker
    else:
        matched += 1
    lines.append(f"    {nid!r}: {{")
    lines.append(f"        {'law'!r}: {c['law']!r},")
    lines.append(f"        {'assumptions'!r}: [")
    for a in c["assumptions"]:
        lines.append("            {"
                     f"'name': {a['name']!r}, 'regime_variable': {a['regime_variable']!r}, "
                     f"'valid_when': {a['valid_when']!r}, 'error_when_violated': {a['error_when_violated']!r}, "
                     f"'generalizes_to': {a['generalizes_to']!r}, 'why': {a['why']!r}"
                     "},")
    lines.append("        ],")
    lines.append("    },")
lines.append("}")
open("assumption_cards.py", "w", encoding="utf-8").write("\n".join(lines))

print(f"assumption_cards.py: {len(cards)} cards ({matched} matched to library nodes, {unmatched} unmatched->need-node)")
n_asm = sum(len(c["assumptions"]) for c in cards)
print(f"  {n_asm} assumptions total")
