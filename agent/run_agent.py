"""THE SPINE, RUN.  Ground the code's `thrust`, then let the agent audit two thrust models against the
physics it is grounded to, and raise the question where the model contradicts its own physics.

  model T1 = the first-order drone.py style: T = Ct*rho*n^2*D^4  (no airspeed term)
  model T2 = the BEMT prop model (physics/prop.py): thrust from blade-element + momentum inflow

The agent does not know which is "right" a priori. It knows what THRUST must do (from the actuator-disk
node) and checks each model against that. Zero-LLM.

    python run_agent.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))

from ground import point_to_physics
from discrepancy import audit, question
import prop

IN2M = 0.0254


# --- model T1: first-order, drone.py-style. Static blade-element, NO airspeed dependence ---
def T1_firstorder(rpm, diameter, rho, airspeed, pitch):
    Ct = 0.10 + 0.06 * (pitch / diameter)
    n = rpm / 60.0
    return Ct * rho * n * n * (diameter * IN2M) ** 4          # airspeed never enters


# --- model T2: BEMT (the real physics module) ---
def T2_bemt(rpm, diameter, rho, airspeed, pitch):
    T, _ = prop.thrust_torque(diameter, pitch, 2, rpm, airspeed, rho)
    return T


def main():
    base = dict(rpm=6000.0, diameter=13.0, rho=1.225, airspeed=15.0, pitch=6.0)

    quantity, node, spec = point_to_physics("thrust")
    print("point_to_physics:  code symbol 'thrust'  ->  physical quantity '%s'" % quantity)
    print("   grounded to [%s] (%s): %s" % (node.id, node.provenance, node.law))
    if spec:
        print("   realized in this world by [%s]: %s" % (spec.id, spec.law))
    print("   the law requires thrust to respond to: " +
          ", ".join(f"{v}({'+' if d > 0 else '-'})" for v, d in node.requires.items()))
    print()

    for label, model in [("USER model  T1  (first-order, drone.py style)", T1_firstorder),
                         ("PHYSICS model T2  (BEMT, physics/prop.py)", T2_bemt)]:
        findings = audit(model, base, node)
        print("=" * 88)
        print(label)
        if not findings:
            print("   consistent with the [%s] fingerprint — every required dependence is present and "
                  "correctly signed." % node.id)
        else:
            for f in findings:
                print(question("thrust", node, f))
        print()


if __name__ == "__main__":
    main()
