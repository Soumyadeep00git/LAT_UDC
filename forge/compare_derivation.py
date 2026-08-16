r"""Comparison — the dimensional KERNEL vs the LIBRARY, law by law.

For each law: what the Pi-engine derives from units alone (the FORM), vs what the library hard-codes (the
form + a calibrated constant). Shows precisely what decouples (structure) and what does not (the number).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import dimanalysis
import library


def lib_law(quantity):
    ids = library.CANON_BY_QUANTITY.get(quantity) or library.A.BY_QUANTITY.get(quantity) or []
    if not ids:
        return None, None
    n = library.node(ids[0])
    law = (getattr(n, "law", "") or "").encode("ascii", "replace").decode()
    return ids[0], law


CASES = [
    ("aerodynamic drag",  "drag",  ["density", "velocity", "area"],     "drag",   "1/2 * Cd"),
    ("rotor thrust",      "thrust", ["density", "area", "velocity"],    "thrust", "2 (momentum) / Ct (BEMT)"),
    ("hover power",       "power",  ["weight", "density", "area"],       "power",  "1/(FM*sqrt(2))"),
]


if __name__ == "__main__":
    print("KERNEL (units only) vs LIBRARY (form + constant)\n")
    for name, target, others, qty, const in CASES:
        form, groups = dimanalysis.derive(target, others)
        nid, law = lib_law(qty)
        print(f"  {name}")
        print(f"    kernel  : {form}")
        if nid:
            print(f"    library : [{nid}]  {law[:70]}")
        else:
            print(f"    library : (no single '{qty}' node — encoded inside a mechanism/closure)")
        print(f"    decouples: FORM (kernel derives it)   |   library's irreducible add: constant = {const}\n")
    print("  Verdict: the FORM is derivable from units (library demotable to a cache); the CONSTANT is the")
    print("  empirical residue the library must keep. That is exactly as far as decoupling can honestly go.")
