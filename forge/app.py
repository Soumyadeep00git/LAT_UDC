r"""SpecimenLab — local visual app over the REAL forge engine.

Zero dependencies (Python stdlib only). It imports the actual system graph, the coupled solver, the
capability envelope and the grounding — so every number the browser shows is the engine's number, not a
JavaScript re-implementation. Run it, open the browser, and the device becomes tangible:

    python app.py            # then open http://127.0.0.1:8765

Pages (served from ui.html):
  1. Architecture  — subsystems, coupling edges (the physics), grounding to the library, permitted crossings
  2. Viz           — a to-scale top-down drawing of the drone from the real params
  3. Sim           — sliders -> real coupled solve -> capability envelope + mass breakdown + mission check
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

from uav import build_uav, capabilities, G   # noqa: E402
from solve import solve                       # noqa: E402

try:
    from agent import ground_system           # optional: grounding to the physics library
except Exception:                             # keep the app alive even if the library import hiccups
    ground_system = None

PORT = 8765

DEFAULT_CFG = dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6,
                   cap_mAh=5000, C_rate=60, L_arm=0.30, payload=0.6, n_rotors=4)

# (lo, hi, step, label, unit) — drives the slider panel
BOUNDS = {
    "D_in":    (8, 22, 0.5, "Prop diameter", "in"),
    "pitch_in": (4, 14, 0.5, "Prop pitch", "in"),
    "Kv":      (150, 450, 10, "Motor Kv", "rpm/V"),
    "I_max":   (20, 90, 1, "Motor current cap", "A"),
    "S":       (4, 12, 1, "Battery cells", "S"),
    "cap_mAh": (2000, 16000, 250, "Battery capacity", "mAh"),
    "C_rate":  (20, 120, 5, "Battery C-rate", "C"),
    "L_arm":   (0.15, 0.60, 0.01, "Arm length", "m"),
    "payload": (0.0, 2.0, 0.05, "Payload", "kg"),
}


def _spec(cfg):
    """The system graph + grounding, as plain JSON."""
    sysm = build_uav(cfg)
    grounded = {}
    if ground_system is not None:
        try:
            for _depth, name, func, nid, descent, alts in ground_system(sysm):
                grounded[name] = {"node": nid, "descent": descent,
                                  "alts": [[a, d] for a, d in alts]}
        except Exception:
            grounded = {}
    subs = []

    def add(s, parent):
        subs.append({
            "name": s.name, "function": s.function, "parent": parent,
            "requires": list(s.requires), "provides": list(s.provides),
            "mechanism": s.mechanism, "mechanisms": list(s.mechanisms.keys()),
            "node": s.node, "radicality_budget": s.radicality_budget, "owns": list(s.owns),
            "params": {k: v for k, v in s.params.items()},
            "grounding": grounded.get(s.name, {}),
        })
        for c in s.children:
            add(c, s.name)

    for s in sysm.subsystems:
        add(s, None)
    return {"name": sysm.name, "subsystems": subs, "edges": sysm.edges()}


def _run_solve(cfg):
    """Run the REAL coupled solve and return the capability envelope + mass breakdown."""
    sysm = build_uav(cfg)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus)
    breakdown, children = {}, {}
    for s in sysm.subsystems:
        breakdown[s.name] = round(s.state.get("mass", 0.0), 4)
        for c in s.children:
            children[c.name] = round(c.state.get("mass", 0.0), 4)
    return {
        "converged": bool(bus.get("converged")),
        "mass": round(cap["mass"], 4),
        "TWR": round(cap["TWR"], 4),
        "a_max_g": round(cap["a_max"] / G, 4),
        "v_max": round(cap["v_max"], 3),
        "endurance_min": round(cap["endurance"] / 60.0, 3),
        "thrust": round(cap["thrust"], 3),
        "struct_mass": round(cap["struct_mass"], 4),
        "breakdown": breakdown, "children": children, "cfg": cfg,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):        # quiet console
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj))

    def _read_cfg(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        cfg = dict(DEFAULT_CFG)
        try:
            cfg.update(json.loads(raw or b"{}"))
        except Exception:
            pass
        return cfg

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "ui.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "ui.html not found", "text/plain")
        elif path == "/api/config":
            self._json({"cfg": DEFAULT_CFG, "bounds": BOUNDS})
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        path = urlparse(self.path).path
        cfg = self._read_cfg()
        try:
            if path == "/api/spec":
                self._json(_spec(cfg))
            elif path == "/api/solve":
                self._json(_run_solve(cfg))
            else:
                self._send(404, "not found", "text/plain")
        except Exception as e:
            self._json({"error": str(e), "type": type(e).__name__}, code=500)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"SpecimenLab app running -> http://127.0.0.1:{PORT}")
    print("  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
