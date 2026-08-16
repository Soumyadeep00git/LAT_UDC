r"""Generate the LAT_UDC study report — a graphic multi-page PDF (matplotlib).

Pages: overview + end-to-end result | the hourglass architecture | the physics sanctuary (library +
dimensional kernel) | the optimizer V1/V2/V3 (+ V3 types & motivation) | backend pipeline & wiring |
the files produced | algorithm comparison table | honest can / can't.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LAT_UDC_report.pdf")

INK = "#111826"; MUT = "#5b6472"; PANEL = "#f6f8fb"; EDGE = "#c3ccd8"
C_HW = "#6366f1"; C_ARCH = "#0ea5e9"; C_PHY = "#10b981"; C_OBJ = "#f59e0b"
C_V1 = "#94a3b8"; C_V2 = "#38bdf8"; C_V3 = "#ec4899"
GOOD = "#16a34a"; WARN = "#d98a09"; BAD = "#dc2626"


def page(title, subtitle=""):
    fig = plt.figure(figsize=(8.5, 11)); ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 96.2), 100, 3.8, color=INK, zorder=1))
    ax.text(5, 98.1, title, color="white", fontsize=17, fontweight="bold", va="center")
    ax.text(95, 98.1, "LAT_UDC", color="#8aa0c8", fontsize=11, fontweight="bold", va="center", ha="right")
    if subtitle:
        ax.text(5, 93.6, subtitle, color=MUT, fontsize=10.5, va="center")
    return fig, ax


def box(ax, x, y, w, h, text, fc="white", ec=EDGE, tc=INK, fs=9, bold=False, align="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15,rounding_size=0.8",
                                fc=fc, ec=ec, lw=1.2, zorder=2))
    hx = x + w / 2 if align == "center" else x + 1.2
    ha = "center" if align == "center" else "left"
    ax.text(hx, y + h / 2, text, ha=ha, va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal", zorder=3, wrap=True)


def arrow(ax, x1, y1, x2, y2, color=MUT, lw=1.6, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13,
                                 color=color, lw=lw, zorder=2))


def bullets(ax, x, y, items, dy=3.1, fs=9.5, tc=INK, mark="•"):
    for i, it in enumerate(items):
        m, t = (it if isinstance(it, tuple) else (mark, it))
        ax.text(x, y - i * dy, m, fontsize=fs, color=t if False else MUT, va="top")
        ax.text(x + 2.4, y - i * dy, t, fontsize=fs, color=tc, va="top")


# ---------------------------------------------------------------- page 1: overview + result
def p_overview(pdf):
    fig, ax = page("LAT_UDC — Physics-Grounded Generative UAV Design",
                   "A study report: architecture, physics library, optimizer (V1/V2/V3), backends, and honest limits")
    ax.text(5, 89, "What it is", fontsize=13, fontweight="bold", color=INK)
    ax.text(5, 82.5,
            "You give it a MISSION (agility, speed, endurance, sensing) and it produces a BUILDABLE vehicle —\n"
            "geometry, a subsystem architecture, a physics model, and the flight-controller config — plus a\n"
            "three-tier optimizer that can tune it, rearrange it, and (in prototype) invent past it. Every number\n"
            "is the real coupled physics solve; nothing is a fitted proxy. The engine is domain-general; the UAV\n"
            "is instance one and the domain we can check.", fontsize=10.5, color=INK, va="top", linespacing=1.5)

    ax.add_patch(FancyBboxPatch((5, 46), 90, 26, boxstyle="round,pad=0.3,rounding_size=1",
                                fc=PANEL, ec=EDGE, lw=1.3))
    ax.text(9, 68.5, "End-to-end result  —  counter-UAS interceptor (headless, this run)",
            fontsize=12, fontweight="bold", color=INK)
    ax.text(9, 64.5, "mission: interception   ·   score: max intercept hits   ·   validation: PASS (8/8 checks)",
            fontsize=10, color=MUT)
    stats = [("platform", "6-rotor · electric · propeller · ArduPilot/CubeOrange"),
             ("capabilities", "a_max 6.64 g   ·   v_max 100 m/s   ·   endurance 59 min"),
             ("seeker (EO/IR)", "detect 2244 m   ·   FOV 18.3°   ·   track 104 Hz"),
             ("SCORE", "MAX INTERCEPT HITS = 7 / 12   (from baseline 1)"),
             ("package", "STL · STEP · OpenFOAM CFD · CalculiX/gmsh FEA · .param · arducopter.apj")]
    for i, (k, v) in enumerate(stats):
        yy = 60 - i * 3.0
        ax.text(9, yy, k, fontsize=10, color=MUT, va="center")
        ax.text(30, yy, v, fontsize=10.2, color=INK, va="center",
                fontweight="bold" if k == "SCORE" else "normal")

    ax.text(5, 40, "The honest thesis", fontsize=13, fontweight="bold", color=INK)
    ax.text(5, 34,
            "The pipeline reaches 7/12 and every airframe tier plateaus there — because the binding limit is the\n"
            "SEEKER, not thrust. That finding, and the clear separation of what is validated vs prototype vs\n"
            "frontier, is the point of this report: an engine that states what it grounds AND what it can't.",
            fontsize=10.5, color=INK, va="top", linespacing=1.5)
    ax.text(50, 4, "page 1 / 9", ha="center", color=MUT, fontsize=8)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 2: the hourglass
def p_hourglass(pdf):
    fig, ax = page("Architecture — the Hourglass",
                   "ENCODE abstracts a concrete vehicle down to intent; DECODE regenerates a vehicle from intent")
    cx = 50
    # hourglass polygons
    ax.add_patch(Polygon([(20, 88), (80, 88), (56, 52), (44, 52)], closed=True, fc="#eef2ff", ec=EDGE, lw=1.2))
    ax.add_patch(Polygon([(44, 48), (56, 48), (80, 12), (20, 12)], closed=True, fc="#eef7f2", ec=EDGE, lw=1.2))
    ax.text(cx, 50, "OBJECTIVE", ha="center", va="center", fontsize=11, fontweight="bold", color=C_OBJ)
    ax.text(cx, 46.6, "(pure intent — lowest fidelity, most abstract)", ha="center", va="center", fontsize=8, color=MUT)

    enc = [("I  hardware", 84, C_HW), ("II  architecture", 76, C_ARCH), ("III  physics fields", 68, C_PHY),
           ("IV  objective", 60, C_OBJ)]
    for name, y, c in enc:
        ax.text(cx, y, name, ha="center", va="center", fontsize=10, color=c, fontweight="bold")
    dec = [("V  physics", 40, C_PHY), ("VI  architecture", 32, C_ARCH), ("VII  hardware", 24, C_HW)]
    for name, y, c in dec:
        ax.text(cx, y, name, ha="center", va="center", fontsize=10, color=c, fontweight="bold")

    arrow(ax, 12, 84, 12, 52, color=C_ARCH, lw=2); ax.text(9.5, 68, "ENCODE", rotation=90, ha="center",
                                                           va="center", color=C_ARCH, fontsize=10, fontweight="bold")
    arrow(ax, 88, 48, 88, 16, color=C_PHY, lw=2); ax.text(90.5, 32, "DECODE", rotation=90, ha="center",
                                                          va="center", color=C_PHY, fontsize=10, fontweight="bold")
    ax.text(20, 90.5, "highest fidelity (the real object)", fontsize=8.5, color=MUT)
    ax.text(20, 9.5, "highest fidelity (the new object)", fontsize=8.5, color=MUT)

    ax.text(5, 6.5,
            "Two worlds: the DARK (abstraction / law space — infinite, where it imagines) and the LIGHT (the\n"
            "coupled solve — definite, where reality says yes or no). V3 is the traffic between them.",
            fontsize=9.5, color=INK, va="top", linespacing=1.5)
    ax.text(50, 1.8, "page 2 / 9", ha="center", color=MUT, fontsize=8)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 3: physics sanctuary
def p_library(pdf):
    fig, ax = page("The Physics Sanctuary — the library, and how to leave it",
                   "Grounding to a curated law graph; and deriving law FORMS from first principles instead")
    box(ax, 6, 80, 40, 10, "PHYSICS LIBRARY (semantic memory)\n~1000+ law nodes, grounded, curated",
        fc="#eef7f2", ec=C_PHY, fs=9.5, bold=True)
    box(ax, 54, 80, 40, 10, "each node: quantity · law · requires · points_to\n+ assumptions (validity envelope)",
        fc=PANEL, fs=9)
    ax.text(6, 74, "Descent to fundamentals = a validation tree:", fontsize=10, color=INK, fontweight="bold")
    chain = ["rotor_thrust", "actuator_disk", "conservation_of_momentum", "navier_stokes"]
    xx = 8
    for i, n in enumerate(chain):
        box(ax, xx, 66, 20, 5, n, fc="white", fs=8)
        if i < len(chain) - 1:
            arrow(ax, xx + 20, 68.5, xx + 21.5, 68.5)
        xx += 21.5
    ax.text(6, 61, "If the ROOTS are validated and each derivation edge is sound, every node inherits validity.",
            fontsize=9.3, color=MUT)

    ax.add_patch(FancyBboxPatch((6, 30), 88, 27, boxstyle="round,pad=0.3,rounding_size=1",
                                fc="#fff8ec", ec=C_OBJ, lw=1.3))
    ax.text(10, 53.5, "Decoupling: physics WITHOUT the library (V3d)", fontsize=12, fontweight="bold", color=INK)
    box(ax, 10, 44, 24, 6, "DIMENSIONAL KERNEL\n(Buckingham-Pi)", fc="white", ec=C_V3, fs=8.5, bold=True)
    box(ax, 40, 44, 22, 6, "resolved FIELD\n(CFD / FEM)", fc="white", ec=C_V3, fs=8.5, bold=True)
    box(ax, 68, 44, 22, 6, "complete LAW\n(no library)", fc="#fdeaf3", ec=C_V3, fs=8.5, bold=True)
    arrow(ax, 34, 47, 40, 47); arrow(ax, 62, 47, 68, 47)
    ax.text(10, 39.5, "FORM  from units alone:   drag = C · ρ · v² · A      (thrust = C · ρ · D⁴ · Ω²)",
            fontsize=9.6, color=INK)
    ax.text(10, 36, "CONSTANT from the solve:   Cd = 0.48 (CFD, 27k cells)  →  drag = 0.2414 · ρ · v² · A",
            fontsize=9.6, color=INK)
    ax.text(10, 32.4, "→ library demotes to a CACHE of the few empirical constants; the forms are generated.",
            fontsize=9.4, color=MUT)

    ax.text(6, 25, "Honest boundary", fontsize=11, fontweight="bold", color=INK)
    bullets(ax, 6, 21.5, [
        "Dimensional analysis gives the FORM/scaling, never the constant C or f(Re,…).",
        "The constant comes from a resolved field — which itself rests on measured MATERIAL constants",
        "   (viscosity, moduli): the residue descends, it does not vanish.",
        "A full law is C(Re): a SWEEP of solves; and only an exact (DNS) solve is purely first-principles.",
    ])
    ax.text(50, 2, "page 3 / 9", ha="center", color=MUT, fontsize=8)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 4: optimizer
def p_optimizer(pdf):
    fig, ax = page("The Optimizer — V1 ⊂ V2 ⊂ V3", "A nested ladder of design freedom; each frees what the one below holds fixed")
    ax.add_patch(FancyBboxPatch((10, 60), 80, 30, boxstyle="round,pad=0.3,rounding_size=1", fc="#fdeaf3", ec=C_V3, lw=1.4))
    ax.text(13, 87, "V3  — change the EMBODIMENT / add a DIMENSION (abstraction)", color=C_V3, fontsize=11, fontweight="bold")
    ax.add_patch(FancyBboxPatch((16, 64), 68, 18, boxstyle="round,pad=0.3,rounding_size=1", fc="#e8f6fe", ec=C_V2, lw=1.4))
    ax.text(19, 79, "V2  — change #entities & linkages (count)", color="#0284c7", fontsize=11, fontweight="bold")
    ax.add_patch(FancyBboxPatch((22, 67.5), 56, 9.5, boxstyle="round,pad=0.3,rounding_size=1", fc="#eef1f5", ec=C_V1, lw=1.4))
    ax.text(25, 72.2, "V1  — change param VALUES (Jacobian null-space repair)", color="#475569", fontsize=11, fontweight="bold")

    ax.text(10, 56, "The four V3 modes (and their motivation):", fontsize=12, fontweight="bold", color=INK)
    modes = [
        ("V3a  compositional", "select an existing embodiment from the library", "collapses to V2 (only realizes registered models)", WARN),
        ("V3b  generative", "dissolve to a field, reshape it, RE-EMBODY a new form", "produces the ducted ring — NEW form, but UNVALIDATED", WARN),
        ("V3c  meta-requirement", "over-constrained field → prescribe a MISSING DOF", "'seeker needs a scan DOF' — decoupled from the gimbal", GOOD),
        ("V3d  decoupling", "derive the law FORM from units + constant from a solve", "a complete library-free drag law (proven)", GOOD),
    ]
    for i, (n, what, res, c) in enumerate(modes):
        y = 49 - i * 8.5
        box(ax, 8, y, 26, 6.5, n, fc="white", ec=c, tc=INK, fs=9.5, bold=True)
        ax.text(37, y + 4.3, "motivation: " + what, fontsize=9.2, color=INK, va="center")
        ax.text(37, y + 1.7, "result: " + res, fontsize=9.0, color=MUT, va="center")
    ax.text(8, 5.5, "Escalation: V1 fires first; on exhaustion (null space collapses) V2; then V3. "
            "One metric — radicality — measures how far each moves.", fontsize=9.3, color=INK, va="top")
    ax.text(50, 1.8, "page 4 / 9", ha="center", color=MUT, fontsize=8)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 5: the seeker case (decoupling)
def p_seeker(pdf):
    fig, ax = page("The Seeker Case — meta-requirements & decoupling",
                   "when a field is over-constrained, prescribe a missing DIMENSION — separate from the hardware")
    # two senses of decoupling
    ax.text(6, 90, "Two things 'decoupling' means here", fontsize=12, fontweight="bold", color=INK)
    box(ax, 6, 79, 42, 8.5, "1)  physics  vs  library   (V3d)\nlaw FORM from units; constant from a solve;\nlibrary becomes a cache of constants",
        fc="#fff8ec", ec=C_OBJ, fs=8.8, align="left")
    box(ax, 52, 79, 42, 8.5, "2)  physics-requirement  vs  hardware  (V3c)\nthe field needs a new DIMENSION (motion);\nwhich actuator supplies it is a separate choice",
        fc="#fdeaf3", ec=C_V3, fs=8.8, align="left")

    ax.text(6, 73, "The seeker wall — why interception plateaus at 7/12", fontsize=12, fontweight="bold", color=INK)
    ax.text(6, 68.5,
            "A fixed camera obeys a conserved budget (space-bandwidth / étendue): detection range ×\n"
            "instantaneous coverage is fixed. It cannot have BOTH long detection AND wide field of view.",
            fontsize=9.6, color=INK, va="top", linespacing=1.5)
    box(ax, 10, 57, 36, 6, "detect 2500 m  →  needs 7.7° FOV", fc="white", ec=EDGE, fs=9)
    box(ax, 54, 57, 36, 6, "mission needs a 60° search cone", fc="white", ec=EDGE, fs=9)
    ax.text(50, 54.2, "static camera: OVER-CONSTRAINED (infeasible)", ha="center", color=BAD, fontsize=9.5, fontweight="bold")

    ax.text(6, 49, "What V3c did (grounded, then decoupled)", fontsize=12, fontweight="bold", color=INK)
    box(ax, 8, 39, 24, 7, "SEE\nascend to\nspace_bandwidth_product", fc="#eef7f2", ec=C_PHY, fs=8, bold=True)
    box(ax, 38, 39, 24, 7, "DETECT\nstatic field\nover-constrained", fc="white", ec=BAD, fs=8, bold=True)
    box(ax, 68, 39, 24, 7, "PRESCRIBE\nadd a SCAN DOF\n(revisit 0.78 s)", fc="#fdeaf3", ec=C_V3, fs=8, bold=True)
    arrow(ax, 32, 42.5, 38, 42.5); arrow(ax, 62, 42.5, 68, 42.5)

    # the decoupling: physics DOF vs hardware actuator
    box(ax, 20, 26, 26, 7, "PHYSICS says\n\"the field needs MOTION\"", fc="#eef7f2", ec=C_PHY, fs=8.5, bold=True)
    box(ax, 54, 26, 30, 7, "HARDWARE picks the actuator\ngimbal | rotating mount | e-beam-steer", fc="#eef2ff", ec=C_HW, fs=8, bold=True)
    ax.add_patch(FancyArrowPatch((46, 29.5), (54, 29.5), arrowstyle="<->", mutation_scale=13, color=MUT, lw=1.6))
    ax.text(50, 32, "decoupled", ha="center", color=MUT, fontsize=8.5, style="italic")

    ax.text(6, 20,
            "The result: V3 discovered a missing DIMENSION (motion), grounded in étendue, and prescribed it\n"
            "WITHOUT naming a gimbal. That is the difference from V1 (a missing value) and V3b (a missing form).",
            fontsize=9.5, color=INK, va="top", linespacing=1.5)
    ax.text(6, 12.5, "Honest: this is a HINT / requirement, not a built scanning seeker. Realizing it — and re-scoring the\n"
            "7/12 with a scanning sensor — is the next step. What V3c delivers is the *right question*, decoupled.",
            fontsize=9.2, color=MUT, va="top", linespacing=1.5)
    ax.text(50, 3, "page 5 / 9", ha="center", color=MUT, fontsize=8)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 6: backend pipeline & wiring
def p_pipeline(pdf):
    fig, ax = page("Backend Pipeline — how everything is wired", "mission → encode → optimize → decode → backends → files")
    box(ax, 4, 86, 18, 7, "MISSION\n+ objective", fc="#fff8ec", ec=C_OBJ, fs=9, bold=True)
    enc = [("parts.py", "hardware"), ("bondgraph.py", "system"), ("fields.py", "physics"), ("objectives.py", "objective")]
    xx = 26
    for f, r in enc:
        box(ax, xx, 86, 16, 7, f + "\n" + r, fc="#eef7f2", ec=C_PHY, fs=8)
        xx += 17
    arrow(ax, 22, 89.5, 26, 89.5)
    ax.text(50, 82, "ENCODE  (inference; reproduces build_uav baseline at 0.0 err)", ha="center", fontsize=8.5, color=MUT)

    box(ax, 30, 71, 40, 7, "OPTIMIZE   diagnose(V1) · physics_adapt(V2) · v3*(V3)\nsolve.py  (coupled fixed-point)",
        fc="#e8f6fe", ec=C_V2, fs=8.5, bold=True)
    arrow(ax, 50, 86, 50, 78)
    box(ax, 30, 60, 40, 6.5, "DECODE   cascade.py / optimize.py  → new design", fc="#fdeaf3", ec=C_V3, fs=8.5, bold=True)
    arrow(ax, 50, 71, 50, 66.5)

    ax.text(50, 55, "BACKENDS  (real toolchain)", ha="center", fontsize=11, fontweight="bold", color=INK)
    be = [("cadgen.py", "CadQuery → STL/STEP", C_HW),
          ("openfoam_runner.py", "OpenFOAM (WSL) → CFD", C_ARCH),
          ("fea.py", "CalculiX/gmsh → FEA", C_PHY),
          ("ardupilot_gen.py", ".param + .apj", C_OBJ),
          ("fdm.py / fdm_json.py", "6-DOF + SITL bridge", C_V3)]
    xx = 4
    for f, r, c in be:
        box(ax, xx, 45, 18, 7, f + "\n" + r, fc="white", ec=c, fs=7.6, bold=True)
        arrow(ax, xx + 9, 60, xx + 9, 52, color=EDGE, lw=1.1)
        xx += 18.6
    ax.text(50, 3, "page 6 / 9", ha="center", color=MUT, fontsize=8)

    ax.text(4, 39, "Deficit-driven dispatch:", fontsize=10, fontweight="bold", color=INK)
    ax.text(4, 35.5, "a field inside its reduced-model validity uses the fast model; when it leaves validity\n"
            "(tip-Mach, disk-loading), it is handed to the external solver — the leash is a proxy for validation.",
            fontsize=9.2, color=MUT, va="top", linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 6: files
def p_files(pdf):
    fig, ax = page("The Files Produced", "one command (validate_pipeline.py) → a complete buildable package")
    tree = [
        ("build_interceptor/", "", INK, True),
        ("  hardware/  specimen.step, specimen.stl", "CAD B-rep + mesh", C_HW, False),
        ("  cfd/of_flow_case/", "OpenFOAM case: system/ constant/polyMesh (27k cells) 0/ + results", C_ARCH, False),
        ("     system/*Dict, constant/turbulenceProperties, postProcessing/forceCoeffs", "", C_ARCH, False),
        ("  fea/  arm.inp, arm.msh, arm_result.json", "CalculiX deck + gmsh mesh + solved beam FE", C_PHY, False),
        ("  ardupilot/  specimen.param", "41 generated params (frame, battery, ESC, seeker mount, failsafes)", C_OBJ, False),
        ("  ardupilot/  arducopter.apj  (1.50 MB)", "official CubeOrange firmware (downloaded, sha256, provenance)", C_OBJ, False),
        ("  ardupilot/  firmware_manifest.json", "board_id, git id, source URL, checksum", C_OBJ, False),
        ("  MANIFEST.json", "design + capabilities + per-artifact provenance", INK, False),
    ]
    y = 86
    for name, desc, c, hdr in tree:
        ax.text(6, y, name, fontsize=10 if hdr else 9.3, color=c, fontweight="bold" if hdr else "normal",
                family="monospace")
        if desc:
            ax.text(60, y, desc, fontsize=8.4, color=MUT, va="center")
        y -= 4.2
    ax.add_patch(FancyBboxPatch((6, 30), 88, 14, boxstyle="round,pad=0.3,rounding_size=1", fc=PANEL, ec=EDGE, lw=1.2))
    ax.text(9, 41, "Provenance is tagged per artifact — nothing fabricated:", fontsize=10, fontweight="bold", color=INK)
    bullets(ax, 9, 37.5, [
        ("generated", "STL/STEP (CadQuery), .param (from the design), FEA deck+mesh"),
        ("solved", "CFD drag (OpenFOAM RANS), beam-FE stress"),
        ("official release", ".apj (real ArduCopter firmware, not tool-authored — cannot compile here)"),
    ], dy=3.0)
    ax.text(50, 3, "page 7 / 9", ha="center", color=MUT, fontsize=8)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 8: comparison table
def p_comparison(pdf):
    fig, ax = page("Algorithm Comparison", "same mission; what each tier changes, what it returns, its cost & status")
    cols = ["tier", "what it changes", "mechanism", "result (a≥5g,v≥26,e≥16)", "status"]
    rows = [
        ["baseline", "—", "—", "UNMET (2.54 g)", "—"],
        ["V1", "param values", "Jacobian null-space repair", "MET · 3.49 kg (4 rotors)", "real"],
        ["V2", "+ rotor count / linkage", "discrete search wrapping V1", "MET · 3.04 kg (3 rotors)", "real"],
        ["V3a compositional", "+ select embodiment", "ascend→imagine→select (library)", "= V2 (collapses)", "real"],
        ["V3b generative", "+ generate embodiment", "reshape field → re-embody (ring)", "8.4 g/73 min/2.11 kg", "PROTOTYPE"],
        ["V3c meta-req", "+ prescribe a missing DOF", "over-constraint → étendue", "seeker: 'add scan DOF'", "real (hint)"],
        ["V3d decoupling", "+ derive the physics", "dim. kernel + field solve", "drag = 0.24·ρv²A (no lib)", "real (drag)"],
    ]
    tab = ax.table(cellText=rows, colLabels=cols, loc="center",
                   colWidths=[0.17, 0.19, 0.24, 0.24, 0.12], bbox=[0.03, 0.42, 0.94, 0.46])
    tab.auto_set_font_size(False); tab.set_fontsize(8.2)
    for (r, c), cell in tab.get_celld().items():
        cell.set_edgecolor(EDGE)
        if r == 0:
            cell.set_facecolor(INK); cell.get_text().set_color("white"); cell.get_text().set_fontweight("bold")
        else:
            st = rows[r - 1][-1]
            cell.set_facecolor("#fbf3e6" if st == "PROTOTYPE" else "white")
            if c == 0:
                cell.get_text().set_fontweight("bold")
    ax.text(5, 37, "Reading it:", fontsize=11, fontweight="bold", color=INK)
    bullets(ax, 5, 33.5, [
        "V1 does the real lifting; V2 beats it (lighter, feasible) by adding rotor count on top of tuning.",
        "V3a folds into V2 — pure selection isn't new. V3b/c/d are where V3 exceeds V2 (new form / new",
        "   dimension / derived physics), but V3b is an unvalidated model and V3c is a hint, not a built part.",
        "On the interception score every airframe tier plateaus at 7/12 — the wall is the SEEKER, not thrust.",
    ])
    ax.text(50, 3, "page 8 / 9", ha="center", color=MUT, fontsize=8)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 9: honest can / can't
def p_honest(pdf):
    fig, ax = page("Honest Scope — what it does, what it doesn't", "the line between validated, prototype, and frontier")
    ax.text(7, 90, "CAN (real & verified)", fontsize=12, fontweight="bold", color=GOOD)
    can = [
        "mission → buildable package, end to end (STL/CFD/FEA/.param/.apj), 8/8 validation",
        "V1 params + V2 count: genuinely different, V2-dominant results",
        "encode inference reproduces the hand-built baseline exactly (0.0 err)",
        "reduced physics for 6 disciplines incl. a modeled EO/IR seeker",
        "CFD (OpenFOAM/WSL) for airframe drag; FEA deck + solved beam; 6-DOF FDM + SITL bridge",
        "V3: imagine alternatives, reshape a 2-D field, hint a missing DOF, derive law FORMS from units",
        "V3d: a complete library-free drag law (form from units + constant from CFD)",
    ]
    for i, t in enumerate(can):
        ax.text(7, 86 - i * 3.3, "✓", color=GOOD, fontsize=10, va="top")
        ax.text(10, 86 - i * 3.3, t, color=INK, fontsize=9.2, va="top")

    ax.text(7, 58, "CAN'T / DOESN'T (yet) — flagged, not hidden", fontsize=12, fontweight="bold", color=BAD)
    cant = [
        "validate V3's invented embodiments — the ducted ring is an UNVALIDATED deficit model",
        "rotor-thrust CFD (only body drag); solve arm.inp (no ccx → 1-D beam); compile the .apj (no ARM toolchain)",
        "fly live SITL (bridge verified in loopback only); fold CFD drag back into the caps",
        "V3 RESCUE a mission — it folds into V2 unless it invents, and inventions aren't trusted",
        "choose its own objective; invent unencoded physics / embodiments; C(Re) sweeps",
        "other platforms/powertrains, and disciplines thermal / RF / radar / guidance-miss / wind",
    ]
    for i, t in enumerate(cant):
        ax.text(7, 54 - i * 3.3, "✗", color=BAD, fontsize=10, va="top")
        ax.text(10, 54 - i * 3.3, t, color=INK, fontsize=9.2, va="top")

    ax.add_patch(FancyBboxPatch((6, 12), 88, 16, boxstyle="round,pad=0.3,rounding_size=1", fc=PANEL, ec=EDGE, lw=1.2))
    ax.text(9, 25, "The one honest throughline", fontsize=11, fontweight="bold", color=INK)
    ax.text(9, 21,
            "Imagination is free; realization is the wall. V3 can abstract, reshape, and derive — but a form is\n"
            "only trustworthy when a validated model or solve backs it. Validation propagates UP a sound\n"
            "derivation, so validating the small physics validates the higher — the leash lengthens exactly as\n"
            "far as the derivation stays sound and in-envelope. That boundary is the real remaining work.",
            fontsize=9.4, color=INK, va="top", linespacing=1.5)
    ax.text(50, 3, "page 9 / 9", ha="center", color=MUT, fontsize=8)
    pdf.savefig(fig); plt.close(fig)


def main():
    with PdfPages(OUT) as pdf:
        p_overview(pdf); p_hourglass(pdf); p_library(pdf); p_optimizer(pdf); p_seeker(pdf)
        p_pipeline(pdf); p_files(pdf); p_comparison(pdf); p_honest(pdf)
    print("wrote", os.path.abspath(OUT), "-", round(os.path.getsize(OUT) / 1024, 1), "KB")


if __name__ == "__main__":
    main()
