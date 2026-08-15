"""Battery model — a voltage source with internal resistance (sag) and a mass from energy density.

The pack holds open-circuit voltage V_oc = S * V_cell, but under a current draw it sags:
    V_bus = V_oc - I_total * R_pack
That sag feeds straight back into the motor (less bus voltage -> less rpm -> less thrust), which is one
of the couplings that make the platform a fixed point. Internal resistance falls with the pack's current
capability (capacity x C-rate), so high-C packs sag less. Mass comes from energy density (your 400 Wh/kg).
"""
from __future__ import annotations

from dataclasses import dataclass

V_CELL = 3.7            # nominal Li-ion/LiPo cell voltage
DOD = 0.85             # usable depth of discharge
R_COEF = 0.44          # internal-resistance scale (calibrated: ~8% sag near burst on a 6S 5Ah 60C pack)


@dataclass
class Battery:
    S: float            # cells in series
    cap_mAh: float
    C_rate: float
    wh_per_kg: float = 400.0

    @property
    def cap_Ah(self):
        return self.cap_mAh / 1000.0

    @property
    def V_oc(self):
        return self.S * V_CELL

    @property
    def R_pack(self):
        return self.S * R_COEF / max(self.cap_Ah * self.C_rate, 1e-6)

    @property
    def I_burst(self):
        return self.C_rate * self.cap_Ah        # max sustained current [A]

    @property
    def energy_Wh(self):
        return self.S * self.cap_Ah * V_CELL

    @property
    def usable_J(self):
        return self.energy_Wh * 3600.0 * DOD

    @property
    def mass(self):
        return self.energy_Wh / self.wh_per_kg

    def v_bus(self, I_total):
        """Bus voltage under a total current draw [A] (sag). Clamped non-negative."""
        return max(self.V_oc - I_total * self.R_pack, 0.0)


if __name__ == "__main__":
    print("Battery check (sag, energy, mass):")
    for S, cap, C in [(6, 5000, 60), (10, 8000, 45), (12, 16000, 30)]:
        b = Battery(S, cap, C)
        print(f"  {S}S {cap}mAh {C}C: V_oc={b.V_oc:4.1f}  R={b.R_pack*1000:4.1f}mOhm  "
              f"I_burst={b.I_burst:4.0f}A  sag@burst={ (b.V_oc-b.v_bus(b.I_burst))/b.V_oc*100:3.0f}%  "
              f"E={b.energy_Wh:4.0f}Wh  m={b.mass:4.2f}kg")
