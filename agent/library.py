"""The physics library interface (stage 5), backed by the agent-built physics_archive.

Enforces the NAMESPACE DISCIPLINE: the library owns a fixed vocabulary of physical quantities and
variables. A code symbol is 'physics' ONLY if its name is literally in that vocabulary — no fuzzy
matching, no guessing. If a name is not in the library, the agent does not invent a meaning for it; it
is a 'math' parameter to be solved. This is the hard boundary between the math track and the physics
track, drawn at the variable level.
"""
import physics_archive as A

# merge curated bindings (gap-fills from smoke tests) into the archive before computing vocab
try:
    from bindings_patch import PATCH as _PATCH
    for _nid, _d in _PATCH.items():
        if _nid not in A.ARCHIVE:
            A.ARCHIVE[_nid] = A.ArcNode(_nid, _d["quantity"], _d["law"], _d["provenance"],
                                        _d["level"], _d["domain"], _d["requires"], _d["points_to"])
            A.BY_QUANTITY.setdefault(_d["quantity"], []).append(_nid)
except ImportError:
    pass

from vocabulary import canonical  # the enforced naming standard

# index the whole library by CANONICAL quantity name — collapses fragmented names (thrust variants etc.)
CANON_BY_QUANTITY = {}
for _n in A.ARCHIVE.values():
    CANON_BY_QUANTITY.setdefault(canonical(_n.quantity), []).append(_n.id)

# vocabulary the library actually knows
VARIABLE_VOCAB = set()
for _n in A.ARCHIVE.values():
    VARIABLE_VOCAB.update(_n.requires.keys())
import vocabulary as _V
QUANTITY_VOCAB = set(A.BY_QUANTITY) | set(CANON_BY_QUANTITY) | _V.CANONICAL
KNOWN = VARIABLE_VOCAB | QUANTITY_VOCAB

_LEVEL = {"system": 0, "high": 1, "mid": 2, "low": 3, "fundamental": 4}


def classify(name):
    """'physics' if the name (or its canonical form) is in the library vocabulary, else 'math'."""
    return "physics" if (name in KNOWN or canonical(name) in KNOWN) else "math"


def ground_quantity(name, context_vars=None):
    """Bind a quantity name to a node. A quantity can be polysemous (rotor thrust vs jet thrust vs rocket
    thrust). Disambiguate by EXACT overlap between a candidate law's required variables and the model's
    own physics variables — no fuzzy matching. Fall back to the richest fingerprint if no context."""
    ids = CANON_BY_QUANTITY.get(canonical(name), []) or A.BY_QUANTITY.get(name, [])
    if not ids:
        return None
    ctx = set(context_vars or [])
    if ctx:
        def overlap(i):
            return len(set(A.ARCHIVE[i].requires) & ctx)
        best = sorted(ids, key=lambda i: (-overlap(i), len(A.ARCHIVE[i].requires), _LEVEL[A.ARCHIVE[i].level]))
        if overlap(best[0]) > 0:
            return best[0]
    return sorted(ids, key=lambda i: (-len(A.ARCHIVE[i].requires), _LEVEL[A.ARCHIVE[i].level]))[0]


def node(nid):
    return A.ARCHIVE.get(nid)


def descent(nid, max_depth=6):
    """Trace a node down to its fundamental roots (list of (id, provenance, depth))."""
    out, seen = [], set()
    def go(x, d):
        if x in seen or d > max_depth or x not in A.ARCHIVE:
            return
        seen.add(x)
        n = A.ARCHIVE[x]
        out.append((x, n.provenance, d))
        if n.provenance != "fundamental":
            for p in n.points_to:
                go(p, d + 1)
    go(nid, 0)
    return out
