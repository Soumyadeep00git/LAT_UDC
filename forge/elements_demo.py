r"""ELEMENTS DEMONSTRATOR - define physics on the elements, let the architecture assemble the rest.

Two designs in two domains, built from the SAME element library. In neither case is a conservation law
written by hand: the wiring generates them. The only physics authored is each element type's constitutive
law, defined once and reused (the SAME 'effort_source' is a battery and a pump; the SAME 'linear_resistance'
is a resistor and a pipe). Then the ordinary field solver runs it.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import field
from elements import Network, SOURCE, RESISTANCE, ORIFICE


def show(net, seed):
    s, knowns, stats = net.assemble()
    print(f"  architecture -> conservation linkages generated: {stats['conservation_from_architecture']} "
          f"(hand-written: 0)")
    print(f"  elements     -> constitutive linkages: {stats['constitutive_from_elements']} "
          f"from {stats['distinct_element_types']} type(s), each defined once")
    return field.solve_field(s, knowns, seed=seed)


def main():
    print("=" * 84)
    print("ELEMENTS - physics defined on the element types; the architecture assembles conservation")
    print("=" * 84)

    print("\n" + "-" * 84)
    print("DESIGN A - an electrical divider under load   (SOURCE + RESISTANCE x2)")
    net = Network("gnd", effort_scale=10.0, flow_scale=0.05)
    net.add("src", SOURCE, "vin", "gnd", value=12.0)
    net.add("R1", RESISTANCE, "vin", "vout", R=100.0)
    net.add("R2", RESISTANCE, "vout", "gnd", R=200.0)
    r = show(net, seed={"e_vin": 12, "e_vout": 6, "f_src": -0.04, "f_R1": 0.04, "f_R2": 0.04})
    v = r.values
    print(f"  SOLVE status={r.status}:  Vout={v['e_vout']:.2f} V   I={v['f_R1']*1000:.1f} mA"
          f"   (hand check: Vout=12*200/300=8.00 V, I=40 mA)")

    print("\n" + "-" * 84)
    print("DESIGN B - a fluid line: pump -> pipe -> nonlinear orifice   (SAME SOURCE & RESISTANCE types)")
    net = Network("tank", effort_scale=5e4, flow_scale=1e-3)
    net.add("pump", SOURCE, "p1", "tank", value=5e4)       # 50 kPa - SOURCE reused as a pump
    net.add("pipe", RESISTANCE, "p1", "p2", R=2e7)          # laminar pipe - RESISTANCE reused
    net.add("orifice", ORIFICE, "p2", "tank", C=5e-6)       # nonlinear element
    r = show(net, seed={"e_p1": 5e4, "e_p2": 2.5e4, "f_pump": 1.2e-3, "f_pipe": 1.2e-3, "f_orifice": 1.2e-3})
    v = r.values
    print(f"  SOLVE status={r.status}:  P1={v['e_p1']/1000:.1f} kPa  P2={v['e_p2']/1000:.1f} kPa  "
          f"Q={v['f_pipe']*1e3:.3f} L/s")

    print("\n" + "=" * 84)
    print("READING IT")
    print("  Neither design wrote a conservation law - the wiring did. The only physics authored is each")
    print("  element type's constitutive law, defined ONCE: 'effort_source' served as both a battery and a")
    print("  pump; 'linear_resistance' as both a resistor and a pipe. Architecture supplies conservation;")
    print("  elements supply constitution; the field solver runs the assembly. No physics tree to bridge,")
    print("  no equation retyped. A design is now just: choose element types, wire them.")


if __name__ == "__main__":
    main()
