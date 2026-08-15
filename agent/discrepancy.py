"""Audit a code model against the grounded node's required sensitivity FINGERPRINT.

For each variable the physics says the quantity must respond to, perturb it and measure the model's
actual response. If the model is insensitive to a required variable, or responds with the wrong sign,
the model contradicts the physics it claims to represent — and the agent raises that as a question.
Deterministic, zero-LLM: questions come from a fixed sentence template.
"""
REL = 0.15        # relative perturbation
TOL = 0.02        # |relative sensitivity| below this = model is insensitive


def sensitivity(model, base, var):
    """Relative sensitivity d(ln y)/d(ln var) of the model's output to one input, or None if absent."""
    if var not in base:
        return None
    y0 = model(**base)
    b = dict(base)
    b[var] = b[var] * (1 + REL) if b[var] != 0 else REL
    y1 = model(**b)
    if y0 == 0:
        return 0.0
    return (y1 - y0) / abs(y0) / REL


def audit(model, base, node):
    """Return a list of findings where the model violates the node's required fingerprint."""
    findings = []
    for var, req in node.requires.items():
        s = sensitivity(model, base, var)
        if s is None:
            findings.append(("absent_input", var, req, None))
        elif abs(s) < TOL:
            findings.append(("insensitive", var, req, s))
        elif (s > 0) != (req > 0):
            findings.append(("wrong_sign", var, req, s))
    return findings


def question(symbol, node, finding):
    kind, var, req, s = finding
    d = "increase" if req and req > 0 else "decrease"
    if kind == "insensitive":
        return (f"Q  '{symbol}' is grounded to [{node.id}] ({node.law}).\n"
                f"   That law requires {node.quantity} to {d} with {var} — but your model is INSENSITIVE "
                f"to {var} (sensitivity {s:+.3f}).\n"
                f"   Consequence: {symbol} is wrong wherever {var} varies; the design is optimizing a "
                f"quantity that does not obey its own physics.")
    if kind == "wrong_sign":
        return (f"Q  '{symbol}' must {d} with {var} per [{node.id}], but your model moves it the OPPOSITE "
                f"way (sensitivity {s:+.3f}). Sign error against the governing law.")
    if kind == "absent_input":
        return (f"Q  the governing law [{node.id}] says {node.quantity} depends on {var}, but your model "
                f"takes no such input. A whole physical dependence is missing from the design's world.")
    return ""
