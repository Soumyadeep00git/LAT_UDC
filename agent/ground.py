"""point_to_physics — bind a code SYMBOL to the physical QUANTITY it represents, and hence to the
governing node whose fingerprint the model must honor.

This is the semantic step the whole architecture rests on: `thrust` in the code is not just a float, it
is a claim to BE the physical quantity thrust (momentum flux). Once bound, the physics graph knows what
the variable must do, independent of how the code happened to compute it.
"""
from physics_graph import GRAPH, GROUND_OF, SPECIALIZES

# code-symbol synonyms -> physical quantity
SYNONYMS = {
    "thrust": ["thrust", "t", "t_rotor", "t_total", "lift", "force_up", "f_thrust"],
    "energy": ["energy", "e", "e_wh", "wh", "e_j", "usable_j"],
    "stress": ["stress", "sigma", "load_stress"],
    "force":  ["force", "f"],
}


def point_to_physics(symbol):
    """Return (quantity, fundamental_node, specialization_node_or_None) for a code symbol, or (None,)*3."""
    s = symbol.strip().lower()
    for quantity, names in SYNONYMS.items():
        if s in names:
            nid = GROUND_OF[quantity]
            spec = GRAPH.get(SPECIALIZES.get(nid))
            return quantity, GRAPH[nid], spec
    return None, None, None
