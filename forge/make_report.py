r"""LAT_UDC Study Report — a serious DARK-themed multi-page PDF (matplotlib).

Cover · Contents/Summary · Architecture (hourglass) · Grounding & library search ·
How the sanctuary is built · Decoupling (kernel) · Optimizer flowchart (V1-V3) ·
the four V3 modes · the seeker case · backend pipeline · files · comparison ·
On abstraction (the thesis) · Honest scope.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch, Rectangle

plt.rcParams["font.family"] = "DejaVu Sans"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LAT_UDC_report.pdf")
DATE = "2026-08-17"
TOTAL = 14

# ---- dark design system ----
BG   = "#0d1521"   # page ground
BG2  = "#151f2d"   # surface / panel
BG3  = "#1c2a3a"   # raised surface
HEAD = "#182636"   # header band
INK  = "#e7edf4"   # primary text
MUT  = "#8b99ac"   # muted text
RULE = "#2a3a4e"   # hairline
ACC  = "#4aa3df"   # steel-blue accent
TEAL = "#35c2a5"
GOLD = "#e0a94a"
HW   = "#8b93e6"; ARCH = "#4aa3df"; PHY = "#35c2a5"; OBJ = "#e0a94a"
V1C  = "#93a1b2"; V2C = "#5bb4e8"; V3C = "#e07aa6"
GOOD = "#4cc38a"; BAD = "#e0685f"; WARN = "#e0a94a"
CREDIT = "#5f7a8b"

_S = {"pg": 0}


def _new():
    fig = plt.figure(figsize=(8.5, 11)); fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 100, 100, color=BG, zorder=0))
    return fig, ax


def _footer(ax):
    ax.plot([5, 95], [4.6, 4.6], color=RULE, lw=0.8)
    ax.text(5, 3.1, "LAT_UDC  —  Physics-Grounded Generative UAV Design   ·   Study Report",
            fontsize=7.5, color=MUT, va="center")
    ax.text(95, 3.1, f"page {_S['pg']} of {TOTAL}", fontsize=7.5, color=MUT, va="center", ha="right")


def page(sec, title, subtitle=""):
    _S["pg"] += 1
    fig, ax = _new()
    ax.add_patch(Rectangle((0, 92.5), 100, 7.5, color=HEAD, zorder=1))
    ax.add_patch(Rectangle((0, 92.2), 100, 0.35, color=ACC, zorder=1))
    if sec:
        ax.add_patch(FancyBboxPatch((5, 94.4), 6.6, 3.4, boxstyle="round,pad=0.1,rounding_size=0.5",
                                    fc=ACC, ec="none", zorder=2))
        ax.text(8.3, 96.1, sec, color="#08131f", fontsize=12, fontweight="bold", ha="center", va="center", zorder=3)
        tx = 14
    else:
        tx = 5
    ax.text(tx, 96.4, title, color=INK, fontsize=15.5, fontweight="bold", va="center")
    ax.text(95, 96.4, "LAT_UDC", color="#6f86a4", fontsize=10, fontweight="bold", va="center", ha="right")
    if subtitle:
        ax.text(tx, 90.1, subtitle, color=MUT, fontsize=9.6, va="center")
    _footer(ax)
    return fig, ax


def panel(ax, x, y, w, h, fc=BG2, ec=RULE, lw=1.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1", fc=fc, ec=ec, lw=lw, zorder=1))


def box(ax, x, y, w, h, text, fc=BG2, ec=RULE, tc=INK, fs=9, bold=False, align="center", lw=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15,rounding_size=0.7",
                                fc=fc, ec=ec, lw=lw, zorder=2))
    hx = x + w / 2 if align == "center" else x + 1.3
    ax.text(hx, y + h / 2, text, ha=("center" if align == "center" else "left"), va="center",
            fontsize=fs, color=tc, fontweight="bold" if bold else "normal", zorder=3, linespacing=1.3)


def diamond(ax, cx, cy, w, h, text, ec=OBJ, fs=8):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)],
                         closed=True, fc=BG3, ec=ec, lw=1.4, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=INK, zorder=3, linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color=MUT, lw=1.6, style="-|>", label=None, ltc=None):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12,
                                 color=color, lw=lw, zorder=2))
    if label:
        ax.text((x1 + x2) / 2 + 1.5, (y1 + y2) / 2, label, fontsize=7.5, color=ltc or color, va="center")


def para(ax, x, y, text, fs=9.5, tc=INK, ls=1.55):
    ax.text(x, y, text, fontsize=fs, color=tc, va="top", linespacing=ls)


def head(ax, x, y, text, c=INK, fs=12):
    ax.text(x, y, text, fontsize=fs, fontweight="bold", color=c, va="center")
    ax.plot([x, x + 2.4], [y - 1.7, y - 1.7], color=ACC, lw=2)


def bullets(ax, x, y, items, dy=3.1, fs=9.3, tc=INK):
    for i, t in enumerate(items):
        ax.text(x, y - i * dy, "—", fontsize=fs, color=ACC, va="top")
        ax.text(x + 2.4, y - i * dy, t, fontsize=fs, color=tc, va="top")


def save(pdf, fig):
    pdf.savefig(fig, facecolor=BG); plt.close(fig)


# ================================================================ 1  COVER
def p_cover(pdf):
    _S["pg"] += 1
    fig, ax = _new()
    ax.add_patch(Rectangle((0, 63), 100, 0.35, color=ACC))
    ax.add_patch(Rectangle((0, 62.4), 40, 0.12, color=TEAL))
    ax.text(10, 81, "LAT_UDC", color=INK, fontsize=42, fontweight="bold")
    ax.text(10.5, 74, "Physics-Grounded Generative UAV Design", color=ACC, fontsize=16)
    ax.text(10, 56, "Study Report", color=INK, fontsize=20, fontweight="bold")
    ax.text(10, 51,
            "Architecture · grounding & the physics sanctuary · how the sanctuary is\n"
            "built · the V1–V3 optimizer and the four modes of V3 · backends & artifacts\n"
            "· the abstraction thesis · and an honest account of what it can and cannot do.",
            color="#b6c3d4", fontsize=11.5, va="top", linespacing=1.7)
    cx = 80
    ax.add_patch(Polygon([(cx - 8, 34), (cx + 8, 34), (cx + 2, 25.5), (cx - 2, 25.5)], closed=True, fc=BG3, ec=ACC, lw=1.4))
    ax.add_patch(Polygon([(cx - 2, 24.5), (cx + 2, 24.5), (cx + 8, 16), (cx - 8, 16)], closed=True, fc=BG3, ec=TEAL, lw=1.4))
    ax.text(10, 14, f"Date: {DATE}", color="#7c90ab", fontsize=10)
    ax.text(10, 10.5, "Repository: github.com/Soumyadeep00git/LAT_UDC", color="#7c90ab", fontsize=10)
    ax.text(10, 7, "Prepared with Claude (Opus)  ·  every figure regenerated from the codebase", color=CREDIT, fontsize=8.5)
    save(pdf, fig)


# ================================================================ 2  CONTENTS + SUMMARY
def p_contents(pdf):
    fig, ax = page("", "Contents & Executive Summary")
    toc = [("§1", "Architecture — the hourglass", 3), ("§2", "Grounding & the physics library", 4),
           ("§3", "How the sanctuary is built", 5), ("§4", "Decoupling — the dimensional kernel", 6),
           ("§5", "The optimizer — V1 to V3 (flowchart)", 7), ("§6", "The four modes of V3", 8),
           ("§7", "The seeker case — meta-requirement & decoupling", 9), ("§8", "Backend pipeline & wiring", 10),
           ("§9", "The files produced", 11), ("§10", "Algorithm comparison", 12),
           ("§11", "On abstraction — the thesis", 13), ("§12", "Honest scope — can / can't", 14)]
    head(ax, 6, 86, "Contents")
    for i, (s, t, p) in enumerate(toc):
        y = 81.5 - i * 2.85
        ax.text(6, y, s, fontsize=9.3, color=ACC, fontweight="bold", va="center")
        ax.text(12.5, y, t, fontsize=9.6, color=INK, va="center")
        ax.text(92, y, str(p), fontsize=9.3, color=MUT, va="center", ha="right")
        ax.plot([12.5, 90], [y - 1.05, y - 1.05], color="#1c2836", lw=0.6)

    head(ax, 6, 42, "Executive summary")
    para(ax, 6, 37,
         "LAT_UDC turns a mission into a buildable vehicle and back: it encodes a concrete design down to\n"
         "intent, then decodes intent into a new design. Physics is not hard-coded per part — each design\n"
         "quantity is GROUNDED to a curated law, and law forms can even be re-derived from first principles.\n"
         "A three-tier optimizer tunes params (V1), rearranges structure (V2), and abstracts the function\n"
         "itself (V3). The engine is domain-general; the counter-UAS interceptor is instance one.")
    panel(ax, 6, 8.5, 88, 15)
    ax.text(9, 21, "Headline result (this run, headless, validation PASS 8/8):", fontsize=10.5, fontweight="bold", color=INK)
    ax.text(9, 17, "6-rotor · electric · propeller · ArduPilot/CubeOrange   —   a_max 6.6 g · v_max 100 m/s · 59 min",
            fontsize=9.5, color=INK)
    ax.text(9, 13.6, "MAX INTERCEPT HITS = 7 / 12 (from baseline 1).  The wall is the SEEKER, not thrust —", fontsize=9.5, color=INK)
    ax.text(9, 10.6, "every airframe tier plateaus at 7/12; the binding limit is sensing.", fontsize=9.5, color=INK)
    save(pdf, fig)


# ================================================================ 3  HOURGLASS
def p_hourglass(pdf):
    fig, ax = page("§1", "Architecture — the Hourglass",
                   "ENCODE abstracts a concrete vehicle down to intent; DECODE regenerates one from intent")
    cx = 50
    ax.add_patch(Polygon([(22, 84), (78, 84), (55, 51), (45, 51)], closed=True, fc=BG2, ec=RULE, lw=1.2))
    ax.add_patch(Polygon([(45, 49), (55, 49), (78, 16), (22, 16)], closed=True, fc=BG2, ec=RULE, lw=1.2))
    ax.text(cx, 50, "OBJECTIVE", ha="center", va="center", fontsize=11, fontweight="bold", color=OBJ)
    ax.text(cx, 47, "pure intent — lowest fidelity, most abstract", ha="center", va="center", fontsize=7.6, color=MUT)
    for name, y, c in [("I   hardware", 80, HW), ("II   architecture", 73, ARCH),
                       ("III   physics fields", 66, PHY), ("IV   objective", 59, OBJ)]:
        ax.text(cx, y, name, ha="center", fontsize=10, color=c, fontweight="bold")
    for name, y, c in [("V   physics", 41, PHY), ("VI   architecture", 34, ARCH), ("VII   hardware", 27, HW)]:
        ax.text(cx, y, name, ha="center", fontsize=10, color=c, fontweight="bold")
    arrow(ax, 14, 82, 14, 51, color=ARCH, lw=2)
    ax.text(11.3, 66, "ENCODE", rotation=90, ha="center", va="center", color=ARCH, fontsize=10, fontweight="bold")
    arrow(ax, 86, 49, 86, 18, color=PHY, lw=2)
    ax.text(88.7, 33, "DECODE", rotation=90, ha="center", va="center", color=PHY, fontsize=10, fontweight="bold")
    ax.text(22, 86, "highest fidelity — the real object", fontsize=8, color=MUT)
    ax.text(22, 13.5, "highest fidelity — the new object", fontsize=8, color=MUT)
    para(ax, 6, 10.3,
         "Two worlds run through the machine: the DARK (abstraction / law space — infinite, where it imagines)\n"
         "and the LIGHT (the coupled solve — definite, where reality answers yes or no). V3 is the traffic\n"
         "between them; fidelity is highest at the two ends and lowest at the objective, the narrow waist.",
         fs=9.2)
    save(pdf, fig)


# ================================================================ 4  GROUNDING & LIBRARY SEARCH
def p_grounding(pdf):
    fig, ax = page("§2", "Grounding & the Physics Library",
                   "attaching real physics to a design quantity — and how the library is searched")
    head(ax, 6, 87, "What grounding is")
    para(ax, 6, 83,
         "Grounding binds a design quantity (a subsystem's function, e.g. \"thrust\") to a NODE in the physics\n"
         "library — a specific law, with the variables it needs, a validity envelope, and a descent to\n"
         "fundamentals. Once grounded, a design is no longer numbers: it is a graph of real physics with a\n"
         "traceable chain to conservation laws. Grounding is what makes the whole engine falsifiable.")
    panel(ax, 6, 63.5, 88, 8.5)
    ax.text(9, 69.5, "Namespace discipline (no fuzzy matching):", fontsize=10, fontweight="bold", color=INK)
    ax.text(9, 66, "a name is PHYSICS only if it (or its canonical form) is in the library vocabulary; otherwise it is a\n"
            "\"math\" parameter to be solved. That hard boundary — library.classify() — is why nothing is invented.",
            fontsize=9, color=INK, va="top")

    head(ax, 6, 58, "How the library is searched  (library.ground_quantity)")
    steps = [("1  canonicalize", "vocabulary.canonical(name): collapse synonyms  (rotor_thrust -> thrust)", TEAL),
             ("2  look up", "CANON_BY_QUANTITY[canonical]  -> candidate ids   (fallback A.BY_QUANTITY[name])", ACC),
             ("3  disambiguate", "polysemy (rotor vs jet vs rocket thrust): pick the node whose required variables\n"
              "         best OVERLAP the subsystem's own physics_vars -- exact overlap, no fuzzing", GOLD),
             ("4  descend", "library.descent(node): trace to fundamental roots -- the validation chain", PHY),
             ("5  neighbours", "radicality.alternatives(quantity, node, radius): sibling embodiments within a\n"
              "         crossing budget -- the candidates V2/V3 may cross to", V3C)]
    y = 53
    for tag, desc, c in steps:
        box(ax, 6, y - 1.2, 20, 5.2, tag, fc=BG3, ec=c, tc=INK, fs=8.6, bold=True)
        ax.text(28, y + 1.4, desc, fontsize=8.6, color=INK, va="center", linespacing=1.35)
        y -= 6.4

    panel(ax, 6, 8.5, 88, 9.5, fc="#122421", ec=PHY)
    ax.text(9, 15.3, "Worked example — grounding \"thrust\" on the propulsion subsystem:", fontsize=9.5, fontweight="bold", color=INK)
    ax.text(9, 11.6, "canonical(rotor_thrust)=thrust -> candidates {rotor, actuator-disk, jet, rocket, nozzle ...} ->\n"
            "physics_vars {air_density, disk_area, induced_velocity} overlap  ==>  rotorcraft_bemt.rotor_thrust.",
            fontsize=8.7, color=INK, va="top")
    save(pdf, fig)


# ================================================================ 5  HOW THE SANCTUARY IS BUILT
def p_sanctuary(pdf):
    fig, ax = page("§3", "How the Sanctuary is Built",
                   "the physics library, low level to high level — and how the algorithm links to it")
    head(ax, 6, 87, "Low level — one node")
    ax.text(6, 83.2, "1,069 nodes. Each is an immutable ArcNode (physics_archive.py):", fontsize=9, color=MUT)
    fields = [("id", "aerodynamics.aircraft_range", ACC),
              ("quantity", "range   (indexed by canonical() )", TEAL),
              ("law", "Breguet: R = (V/gSFC)(L/D) ln(Wi/Wf)", INK),
              ("provenance", "fundamental | derived | model", GOLD),
              ("level", "system|high|mid|low|fundamental", V2C),
              ("domain", "aerodynamics, classical_mechanics ...", HW),
              ("requires", "{ variable : exponent }  (units fingerprint)", PHY),
              ("points_to", "[ parent ids it rests on ]  (the edges)", V3C)]
    panel(ax, 6, 61.5, 44, 19.5)
    for i, (k, v, c) in enumerate(fields):
        yy = 78.6 - i * 2.15
        ax.text(8.5, yy, k, fontsize=8.0, color=c, fontweight="bold", va="center", family="monospace")
        ax.text(21, yy, v, fontsize=7.2, color=INK, va="center")
    head(ax, 54, 87, "High level — organization")
    bullets(ax, 54, 82.5, [
        "5 LEVELS: system -> high -> mid ->\n   low -> fundamental (descent depth)",
        "grouped by DOMAIN (aero, mechanics,\n   electro-optics, thermo, materials ...)",
        "one CANONICAL vocabulary collapses\n   synonyms (vocabulary.canonical)",
        "three indices built at import:\n   CANON_BY_QUANTITY, BY_QUANTITY,\n   VARIABLE_VOCAB  (the known names)",
    ], dy=4.7, fs=8.5)

    head(ax, 6, 57, "How it is connected")
    box(ax, 8, 46, 26, 6.5, "points_to  = a DAG\n(law -> laws it rests on)", fc=BG3, ec=PHY, fs=8.1, bold=True)
    box(ax, 40, 46, 24, 6.5, "descent()\ntrace to fundamentals\n= the validation tree", fc=BG3, ec=PHY, fs=8.0, bold=True)
    box(ax, 70, 46, 24, 6.5, "ADJ = undirected\ngraph -> radicality\ndistance (the leash)", fc=BG3, ec=V3C, fs=8.0, bold=True)
    arrow(ax, 34, 49.2, 40, 49.2); arrow(ax, 64, 49.2, 70, 49.2)
    ax.text(6, 41.3, "Same edges, two readings: DOWN (points_to) validates; ACROSS (undirected) measures how far a swap crosses.",
            fontsize=8.3, color=MUT)

    head(ax, 6, 36, "How the algorithm links to it")
    links = [("classify(name)", "physics vs math — the hard boundary", TEAL),
             ("ground_quantity(name, vars)", "bind a subsystem's function to a node (canonical + overlap)", ACC),
             ("descent(node)", "V3d / validation — trace the law to its roots", PHY),
             ("alternatives(qty, node, r)", "V2 / V3 imagine — siblings within the radicality budget", V3C)]
    y = 31.5
    for fn, desc, c in links:
        ax.text(8, y, fn, fontsize=8.5, color=c, family="monospace", va="center", fontweight="bold")
        ax.text(46, y, desc, fontsize=8.5, color=INK, va="center")
        y -= 3.4
    panel(ax, 6, 8.5, 88, 8.5, fc="#122421", ec=PHY)
    ax.text(9, 14.3, "Built by agents, curated, then frozen:", fontsize=9.4, fontweight="bold", color=INK)
    ax.text(9, 10.7, "a swarm proposed nodes; smoke-tests gap-filled bindings (bindings_patch.py); the result is a fixed,\n"
            "generated archive — no runtime fuzzy matching. New physics is ADDED as nodes, never guessed at.",
            fontsize=8.6, color=INK, va="top")
    save(pdf, fig)


# ================================================================ 6  DECOUPLING (KERNEL)
def p_kernel(pdf):
    fig, ax = page("§4", "Decoupling — the Dimensional Kernel",
                   "the library holds law forms; but forms are derivable from first principles — only constants aren't")
    head(ax, 6, 87, "Physics without the library (V3d)")
    box(ax, 8, 76, 24, 6.5, "DIMENSIONAL KERNEL\nBuckingham-Pi (units only)", fc=BG3, ec=V3C, fs=8.6, bold=True)
    box(ax, 39, 76, 22, 6.5, "resolved FIELD\nCFD / FEM", fc=BG3, ec=V3C, fs=8.6, bold=True)
    box(ax, 68, 76, 24, 6.5, "complete LAW\n(no library node)", fc="#2a1622", ec=V3C, fs=8.6, bold=True)
    arrow(ax, 32, 79.2, 39, 79.2, label="FORM"); arrow(ax, 61, 79.2, 68, 79.2, label="constant C")
    para(ax, 6, 71,
         "From the units of the variables alone, the kernel derives the FORM of a law — the only dimensionally\n"
         "legal way the quantities can combine. A resolved field solve then supplies the one thing units cannot:\n"
         "the constant. Together they assemble a complete law with the physics library never touched.")
    panel(ax, 6, 44, 88, 20)
    ax.text(9, 61, "Derived from units alone (verified):", fontsize=10, fontweight="bold", color=INK)
    for i, (lab, law) in enumerate([("rotor thrust", "T = C · rho · D^4 · Omega^2"),
                                    ("aerodynamic drag", "F = C · rho · v^2 · A"),
                                    ("hover power (momentum)", "P = C · W^1.5 · (rho A)^-0.5")]):
        ax.text(9, 56.5 - i * 3.2, lab, fontsize=9.2, color=MUT, va="center")
        ax.text(42, 56.5 - i * 3.2, law, fontsize=9.6, color=INK, va="center", fontweight="bold")
    ax.text(9, 47, "V3d proven end-to-end for drag:  form (units) + Cd = 0.48 (CFD, 27k cells)  ->  drag = 0.2414 · rho v^2 A",
            fontsize=9.2, color=INK)
    head(ax, 6, 39, "The honest boundary")
    bullets(ax, 6, 34.5, [
        "Dimensional analysis gives the FORM/scaling — never the constant C or a function f(Re, ...).",
        "The constant comes from a field solve, which itself rests on measured MATERIAL constants",
        "   (viscosity, moduli): the residue does not vanish — it descends to the few properties of matter.",
        "A full law is C(Re): a sweep of solves; only an exact (DNS) solve is purely first-principles.",
        "So the library demotes to a CACHE of constants; the forms are generated on demand.",
    ], dy=3.0)
    save(pdf, fig)


# ================================================================ 7  OPTIMIZER FLOWCHART
def p_flow(pdf):
    fig, ax = page("§5", "The Optimizer — V1 to V3",
                   "one escalating loop: each tier fires only when the previous one is exhausted")
    box(ax, 38, 85, 24, 5, "design cfg + mission", fc=HEAD, ec=ACC, tc=INK, fs=9, bold=True)
    box(ax, 30, 76, 40, 5.5, "V1  Jacobian null-space repair  (tune param values)", fc=BG2, ec=V1C, fs=9, bold=True)
    arrow(ax, 50, 85, 50, 81.5)
    diamond(ax, 50, 69.5, 26, 8, "mission met?")
    arrow(ax, 50, 76, 50, 73.5)
    box(ax, 78, 66.5, 18, 6, "DONE\n(V1)", fc="#12251b", ec=GOOD, fs=8.5, bold=True, tc=GOOD)
    arrow(ax, 63, 69.5, 78, 69.5, label="yes", ltc=GOOD)
    box(ax, 30, 57, 40, 5.5, "V2  for each rotor count: run V1, keep best  (rearrange structure)",
        fc=BG2, ec=V2C, fs=8.7, bold=True)
    arrow(ax, 50, 65.5, 50, 62.5, label="no / null-space collapsed", ltc=BAD)
    diamond(ax, 50, 50, 26, 8, "mission met?")
    arrow(ax, 50, 57, 50, 54)
    box(ax, 78, 47, 18, 6, "DONE\n(V2)", fc="#12251b", ec=GOOD, fs=8.5, bold=True, tc=GOOD)
    arrow(ax, 63, 50, 78, 50, label="yes", ltc=GOOD)
    box(ax, 26, 37.5, 48, 5.5, "V3  SEE ascend to invariant  ->  IMAGINE alternatives (radicality)",
        fc=BG2, ec=V3C, fs=8.6, bold=True)
    arrow(ax, 50, 46, 50, 43, label="no / exhausted", ltc=BAD)
    diamond(ax, 50, 30.5, 30, 8, "realizable\nembodiment meets?")
    arrow(ax, 50, 37.5, 50, 34.5)
    box(ax, 78, 27.5, 18, 6, "DONE\n(V3a/b)", fc="#12251b", ec=GOOD, fs=8.2, bold=True, tc=GOOD)
    arrow(ax, 65, 30.5, 78, 30.5, label="yes", ltc=GOOD)
    box(ax, 14, 16.5, 34, 6, "V3b generative — reshape field -> new form\nV3c meta — prescribe a missing DOF\nV3d — derive law form + solve constant",
        fc=BG2, ec=V3C, fs=7.5, align="left")
    arrow(ax, 50, 26.5, 31, 22.5, label="no", ltc=BAD)
    box(ax, 56, 17.5, 30, 5, "REFLECT -> episodic memory", fc="#1d1830", ec="#a07fd0", fs=8.4, bold=True)
    arrow(ax, 48, 19.5, 56, 20)
    para(ax, 6, 10.5,
         "One metric — radicality — measures how far each tier moves (0 for V1; graph distance for V2; ascent\n"
         "altitude for V3). Escalation is triggered by exhaustion: when the null space collapses, climb a tier.",
         fs=9.0)
    save(pdf, fig)


# ================================================================ 8  V3 MODES
def p_v3modes(pdf):
    fig, ax = page("§6", "The Four Modes of V3", "select · generate · prescribe · derive — with their motivation and status")
    modes = [
        ("V3a  compositional", "select an existing embodiment from the library", "collapses to V2 (only realizes registered models)", WARN, "real"),
        ("V3b  generative", "dissolve to a field, reshape it, RE-EMBODY a new form", "produced the ducted ring — a new form, UNVALIDATED", WARN, "prototype"),
        ("V3c  meta-requirement", "over-constrained field -> prescribe a MISSING DIMENSION", "\"seeker needs a scan DOF\" — decoupled from the gimbal", GOOD, "real (hint)"),
        ("V3d  decoupling", "derive the law FORM from units + constant from a solve", "a complete library-free drag law", GOOD, "real (drag)"),
    ]
    y = 84
    for name, mot, res, c, st in modes:
        panel(ax, 6, y - 12, 88, 12, fc=BG2)
        ax.add_patch(Rectangle((6, y - 12), 1.6, 12, color=c))
        ax.text(10, y - 2.4, name, fontsize=11.5, fontweight="bold", color=INK)
        ax.text(88, y - 2.4, st, fontsize=8.6, color=c, ha="right", fontweight="bold")
        ax.text(10, y - 6.3, "motivation:  " + mot, fontsize=9.2, color=INK)
        ax.text(10, y - 9.4, "result:  " + res, fontsize=9.0, color=MUT)
        y -= 14
    para(ax, 6, 24,
         "V3 is not one thing. As a design-point optimizer it folds into V2 unless it invents (V3b) — and its\n"
         "inventions are not yet validated. As an abstraction engine it genuinely exceeds V1/V2: it generates\n"
         "new forms, prescribes missing dimensions, and derives physics from first principles.")
    save(pdf, fig)


# ================================================================ 9  SEEKER CASE
def p_seeker(pdf):
    fig, ax = page("§7", "The Seeker Case — Meta-Requirement & Decoupling",
                   "when a field is over-constrained, prescribe a missing DIMENSION — separate from the hardware")
    head(ax, 6, 87, "Two things 'decoupling' means")
    box(ax, 6, 76, 42, 8, "physics  vs  library   (V3d)\nform from units; constant from a solve;\nlibrary -> a cache of constants",
        fc="#2a2312", ec=OBJ, fs=8.7, align="left")
    box(ax, 52, 76, 42, 8, "physics-requirement  vs  hardware   (V3c)\nthe field needs a new DIMENSION (motion);\nthe actuator that supplies it is a separate choice",
        fc="#2a1622", ec=V3C, fs=8.7, align="left")
    head(ax, 6, 70, "The seeker wall — why interception plateaus at 7/12")
    para(ax, 6, 66,
         "A fixed camera obeys a conserved budget (space-bandwidth / etendue): detection range x instantaneous\n"
         "coverage is fixed. It cannot have both long detection AND a wide field of view.", fs=9.3)
    box(ax, 10, 55, 36, 5.5, "detect 2500 m -> needs 7.7 deg FOV", fc=BG2, ec=RULE, fs=9)
    box(ax, 54, 55, 36, 5.5, "mission needs a 60 deg search cone", fc=BG2, ec=RULE, fs=9)
    ax.text(50, 52, "static camera: OVER-CONSTRAINED (infeasible)", ha="center", color=BAD, fontsize=9.3, fontweight="bold")
    head(ax, 6, 46, "What V3c did — grounded, then decoupled")
    box(ax, 8, 36, 24, 6.5, "SEE\nascend to\nspace_bandwidth_product", fc="#122421", ec=PHY, fs=7.7, bold=True)
    box(ax, 38, 36, 24, 6.5, "DETECT\nstatic field\nover-constrained", fc=BG2, ec=BAD, fs=7.8, bold=True)
    box(ax, 68, 36, 24, 6.5, "PRESCRIBE\nadd a SCAN DOF\n(revisit 0.78 s)", fc="#2a1622", ec=V3C, fs=7.8, bold=True)
    arrow(ax, 32, 39.2, 38, 39.2); arrow(ax, 62, 39.2, 68, 39.2)
    box(ax, 18, 24, 26, 6.5, "PHYSICS says\n\"the field needs MOTION\"", fc="#122421", ec=PHY, fs=8.3, bold=True)
    box(ax, 54, 24, 30, 6.5, "HARDWARE picks the actuator\ngimbal | rotating mount | e-steer", fc=BG3, ec=HW, fs=7.9, bold=True)
    ax.add_patch(FancyArrowPatch((44, 27.2), (54, 27.2), arrowstyle="<->", mutation_scale=12, color=MUT, lw=1.6))
    ax.text(49, 29.6, "decoupled", ha="center", color=MUT, fontsize=8, style="italic")
    para(ax, 6, 18,
         "V3 discovered a missing DIMENSION (motion), grounded in etendue, and prescribed it WITHOUT naming a\n"
         "gimbal — the difference from V1 (a missing value) and V3b (a missing form). Honest: this is the right\n"
         "question, decoupled — a hint, not a built scanning seeker; realizing it and re-scoring 7/12 is next.", fs=9.1)
    save(pdf, fig)


# ================================================================ 10  BACKEND PIPELINE
def p_pipeline(pdf):
    fig, ax = page("§8", "Backend Pipeline & Wiring", "mission -> encode -> optimize -> decode -> backends -> files")
    box(ax, 4, 84, 16, 6.5, "MISSION\n+ objective", fc="#2a2312", ec=OBJ, fs=8.4, bold=True)
    for i, (f, r) in enumerate([("parts.py", "hardware"), ("bondgraph.py", "system"),
                                ("fields.py", "physics"), ("objectives.py", "objective")]):
        box(ax, 24 + i * 17, 84, 15.5, 6.5, f + "\n" + r, fc="#122421", ec=PHY, fs=7.6)
    arrow(ax, 20, 87.2, 24, 87.2)
    ax.text(50, 80, "ENCODE — inference; reproduces the build_uav baseline at 0.0 err", ha="center", fontsize=8.2, color=MUT)
    box(ax, 28, 70, 44, 6.5, "OPTIMIZE   diagnose (V1) · physics_adapt (V2) · v3* (V3)   over   solve.py",
        fc=BG2, ec=V2C, fs=8.4, bold=True)
    arrow(ax, 50, 84, 50, 76.5)
    box(ax, 28, 60, 44, 6, "DECODE   cascade.py / optimize.py  ->  new design", fc=BG2, ec=V3C, fs=8.4, bold=True)
    arrow(ax, 50, 70, 50, 66)
    ax.text(50, 54, "BACKENDS  (real toolchain)", ha="center", fontsize=11, fontweight="bold", color=INK)
    for i, (f, r, c) in enumerate([("cadgen.py", "CadQuery -> STL/STEP", HW),
                                   ("openfoam_runner", "OpenFOAM (WSL) -> CFD", ARCH),
                                   ("fea.py", "CalculiX/gmsh -> FEA", PHY),
                                   ("ardupilot_gen", ".param + .apj", OBJ),
                                   ("fdm.py / json", "6-DOF + SITL bridge", V3C)]):
        x = 4 + i * 18.6
        box(ax, x, 44, 18, 6.5, f + "\n" + r, fc=BG2, ec=c, fs=7.1, bold=True)
        arrow(ax, x + 9, 60, x + 9, 50.5, color=RULE, lw=1.0)
    head(ax, 6, 37, "Deficit-driven dispatch")
    para(ax, 6, 33,
         "A field inside its reduced-model validity uses the fast model; when it leaves validity (tip-Mach,\n"
         "disk-loading), it is handed to the external solver. The radicality leash is a proxy for validation\n"
         "strength — it lengthens exactly as far as the solve can be trusted.", fs=9.1)
    save(pdf, fig)


# ================================================================ 11  FILES
def p_files(pdf):
    fig, ax = page("§9", "The Files Produced", "one command (validate_pipeline.py) -> a complete buildable package")
    rows = [("build_interceptor/", "", INK, True),
            ("  hardware/  specimen.step, specimen.stl", "CAD B-rep + mesh", HW, False),
            ("  cfd/of_flow_case/", "OpenFOAM: system · constant/polyMesh (27k cells) · 0/ + results", ARCH, False),
            ("  fea/  arm.inp, arm.msh, arm_result.json", "CalculiX deck + gmsh mesh + solved beam FE", PHY, False),
            ("  ardupilot/  specimen.param", "41 generated params (frame, battery, ESC, seeker, failsafes)", OBJ, False),
            ("  ardupilot/  arducopter.apj  (1.50 MB)", "official CubeOrange firmware (downloaded, sha256)", OBJ, False),
            ("  ardupilot/  firmware_manifest.json", "board id, git id, source URL, checksum", OBJ, False),
            ("  MANIFEST.json", "design + capabilities + per-artifact provenance", INK, False)]
    y = 85
    for name, desc, c, hdr in rows:
        ax.text(6, y, name, fontsize=9.4 if hdr else 9.0, color=c, family="monospace",
                fontweight="bold" if hdr else "normal")
        if desc:
            ax.text(58, y, desc, fontsize=8.1, color=MUT, va="center")
        y -= 4.4
    panel(ax, 6, 30, 88, 15)
    ax.text(9, 42, "Provenance is tagged per artifact — nothing fabricated:", fontsize=10, fontweight="bold", color=INK)
    bullets(ax, 9, 38.5, [
        "generated:  STL/STEP (CadQuery), .param (from the design), the FEA deck + mesh",
        "solved:  CFD drag (OpenFOAM RANS), beam-FE stress",
        "official release:  the .apj (real ArduCopter firmware — not tool-authored; cannot compile here)",
    ], dy=3.1)
    save(pdf, fig)


# ================================================================ 12  COMPARISON
def p_comparison(pdf):
    fig, ax = page("§10", "Algorithm Comparison", "same mission; what each tier changes, its mechanism, result & status")
    cols = ["tier", "changes", "mechanism", "result (a>=5g,v>=26,e>=16)", "status"]
    rows = [
        ["baseline", "-", "-", "UNMET (2.54 g)", "-"],
        ["V1", "param values", "Jacobian null-space repair", "MET · 3.49 kg (4 rotors)", "real"],
        ["V2", "+ rotor count", "discrete search wrapping V1", "MET · 3.04 kg (3 rotors)", "real"],
        ["V3a compositional", "+ select embodiment", "ascend->imagine->select", "= V2 (collapses)", "real"],
        ["V3b generative", "+ generate embodiment", "reshape field -> re-embody", "8.4g/73min/2.1kg", "PROTOTYPE"],
        ["V3c meta-req", "+ a missing DOF", "over-constraint -> etendue", "seeker: 'add scan DOF'", "real (hint)"],
        ["V3d decoupling", "+ derive the physics", "dim. kernel + field solve", "drag = 0.24·rho v^2 A", "real (drag)"],
    ]
    tab = ax.table(cellText=rows, colLabels=cols, loc="center",
                   colWidths=[0.19, 0.18, 0.24, 0.25, 0.12], bbox=[0.03, 0.44, 0.94, 0.44])
    tab.auto_set_font_size(False); tab.set_fontsize(8.0)
    for (r, c), cell in tab.get_celld().items():
        cell.set_edgecolor(RULE); cell.set_linewidth(0.8)
        if r == 0:
            cell.set_facecolor(HEAD); cell.get_text().set_color(INK); cell.get_text().set_fontweight("bold")
        else:
            proto = rows[r - 1][-1] == "PROTOTYPE"
            cell.set_facecolor("#2a2312" if proto else BG2)
            cell.get_text().set_color(GOLD if proto else INK)
            if c == 0:
                cell.get_text().set_fontweight("bold")
    head(ax, 6, 38, "Reading it")
    bullets(ax, 6, 33.5, [
        "V1 does the real lifting; V2 beats it (lighter, feasible) by adding count on top of tuning.",
        "V3a folds into V2 — pure selection is not new. V3b/c/d are where V3 exceeds V2 (new form,",
        "   new dimension, derived physics), but V3b is unvalidated and V3c is a hint, not a built part.",
        "On the interception score every airframe tier plateaus at 7/12 — the wall is the seeker, not thrust.",
    ], dy=3.0)
    save(pdf, fig)


# ================================================================ 13  ON ABSTRACTION
def p_abstraction(pdf):
    fig, ax = page("§11", "On Abstraction — the Thesis",
                   "the idea the whole engine is reaching for, and why V3 is built the way it is")
    para(ax, 6, 88,
         "Two worlds. The PHYSICAL is what exists — finite, definite, the LIGHT where reality answers. The\n"
         "ABSTRACT is what could otherwise be — infinite, open, the DARK where a mind imagines. Abstraction is\n"
         "parasitic on the physical: you cannot abstract from nothing. Creation lives in the dark; correction\n"
         "lives in the light; and neither alone is enough — untethered imagination is only fantasy.", fs=9.5)
    panel(ax, 6, 60, 88, 16)
    ax.text(9, 73, "Abstraction = free the FUNCTION from its FORM  (\"free life from living\").", fontsize=10.5, fontweight="bold", color=INK)
    para(ax, 9, 69.5,
         "To abstract a rotor is to ascend from \"this rotor\" to \"produce reaction force by accelerating mass\" —\n"
         "the invariant, embodiment-free. Once you hold the function, you are free to re-embody it as anything\n"
         "physics permits. The \"One\" the engine reaches for is not a final equation but a VERB: the operation\n"
         "of abstraction <-> embodiment itself. Building V3 is an attempt to instantiate that verb.", fs=9.2)
    head(ax, 6, 55, "The ladder, in one line each")
    for i, (t, d, c) in enumerate([
            ("V1  change the value", "move x within a fixed function f — tune params", V1C),
            ("V2  rewire the entities", "change the number/links — the structure of f", V2C),
            ("V3  rewrite the function", "reshape the field / add a dimension / derive the law — change f itself", V3C)]):
        ax.text(8, 50 - i * 4, t, fontsize=9.8, color=c, fontweight="bold", va="center")
        ax.text(40, 50 - i * 4, d, fontsize=9.2, color=INK, va="center")
    head(ax, 6, 34, "Toward forming abstractions (not only traversing them)")
    para(ax, 6, 30,
         "The library is traversed; true abstraction FORMS new invariants. The loop is abstract -> invent ->\n"
         "reflect: retrospect over an episodic memory, extract an invariant nobody encoded, mint it. A drive\n"
         "stays fixed; the METHOD becomes revisable — the agent learns to mend its own way of seeing. Meta-\n"
         "requirements (a missing dimension, like the seeker's motion) are this faculty finding not a better\n"
         "value or form, but a needed axis the design did not have.", fs=9.2)
    panel(ax, 6, 6.5, 88, 9, fc="#122421", ec=PHY)
    ax.text(9, 13, "The honest ceiling", fontsize=10, fontweight="bold", color=INK)
    ax.text(9, 9.4, "Imagination is free; realization is the wall. But validation propagates UP a sound derivation —\n"
            "validate the small physics and the higher inherits it — so the leash lengthens exactly as far as the\n"
            "derivation stays sound and in-envelope. Freedom is earned by grounding, not by removing the leash.",
            fontsize=8.9, color=INK, va="top", linespacing=1.45)
    save(pdf, fig)


# ================================================================ 14  HONEST SCOPE
def p_honest(pdf):
    fig, ax = page("§12", "Honest Scope — What It Does, What It Doesn't",
                   "the line between validated, prototype, and frontier")
    ax.text(7, 88, "CAN  (real & verified)", fontsize=12, fontweight="bold", color=GOOD)
    can = ["mission -> buildable package, end to end (STL/CFD/FEA/.param/.apj); 8/8 validation",
           "V1 params + V2 count: genuinely different, V2-dominant results",
           "encode inference reproduces the hand-built baseline exactly (0.0 err)",
           "reduced physics for 6 disciplines incl. a modeled EO/IR seeker",
           "CFD (OpenFOAM/WSL) for airframe drag; FEA deck + solved beam; 6-DOF FDM + SITL bridge",
           "V3: imagine alternatives, reshape a 2-D field, hint a missing DOF, derive law forms from units",
           "V3d: a complete library-free drag law (form from units + constant from CFD)"]
    for i, t in enumerate(can):
        ax.text(7, 84 - i * 3.2, "+", color=GOOD, fontsize=11, va="top", fontweight="bold")
        ax.text(10, 84 - i * 3.2, t, color=INK, fontsize=9.0, va="top")
    ax.text(7, 57, "CAN'T / DOESN'T (yet)  —  flagged, not hidden", fontsize=12, fontweight="bold", color=BAD)
    cant = ["validate V3's invented embodiments — the ducted ring is an UNVALIDATED deficit model",
            "rotor-thrust CFD (only body drag); solve arm.inp with ccx (1-D beam); compile the .apj (no ARM toolchain)",
            "fly live SITL (bridge verified in loopback only); fold CFD drag back into the caps",
            "V3 RESCUE a mission — it folds into V2 unless it invents, and inventions aren't trusted",
            "choose its own objective; invent unencoded physics/embodiments; C(Re) sweeps",
            "other platforms/powertrains; disciplines thermal / RF / radar / guidance-miss / wind"]
    for i, t in enumerate(cant):
        ax.text(7, 53 - i * 3.2, "x", color=BAD, fontsize=11, va="top", fontweight="bold")
        ax.text(10, 53 - i * 3.2, t, color=INK, fontsize=9.0, va="top")
    panel(ax, 6, 12, 88, 15)
    ax.text(9, 24, "The one honest throughline", fontsize=11, fontweight="bold", color=INK)
    ax.text(9, 20,
            "Imagination is free; realization is the wall. V3 can abstract, reshape, and derive — but a form is\n"
            "only trustworthy when a validated model or solve backs it. Because validation propagates up a sound\n"
            "derivation, validating the small physics validates the higher; the leash lengthens exactly as far as\n"
            "the derivation stays sound and in-envelope. That boundary is the real remaining work.",
            fontsize=9.1, color=INK, va="top", linespacing=1.5)
    save(pdf, fig)


def main():
    with PdfPages(OUT) as pdf:
        p_cover(pdf); p_contents(pdf); p_hourglass(pdf); p_grounding(pdf); p_sanctuary(pdf)
        p_kernel(pdf); p_flow(pdf); p_v3modes(pdf); p_seeker(pdf); p_pipeline(pdf)
        p_files(pdf); p_comparison(pdf); p_abstraction(pdf); p_honest(pdf)
    print("wrote", os.path.abspath(OUT), "-", round(os.path.getsize(OUT) / 1024, 1), "KB,", _S["pg"], "pages")


if __name__ == "__main__":
    main()
