"""Train the learnable, read out what features win, and let it pick a design without sweeping 140.

    python run_learn.py
"""
from __future__ import annotations

import numpy as np

from specimen import Specimen
from mission import threat_field, evaluate
import learnable as L


def main():
    # ---- train the win-model on sampled engagements (each row = one sim) ----
    Xtr, ytr, _ = L.sample_dataset(n=2200, seed=0)
    Xte, yte, _ = L.sample_dataset(n=600, seed=1)
    model = L.WinModel().fit(Xtr, ytr)

    acc = float(((model.proba(Xte) > 0.5) == (yte > 0.5)).mean())
    base_rate = float(max(yte.mean(), 1 - yte.mean()))
    print(f"LEARNABLE trained on {len(ytr)} engagements.")
    print(f"   held-out win-prediction accuracy: {acc*100:.1f}%   (majority-class baseline {base_rate*100:.1f}%)\n")

    print("GLOBAL — what decides winning (standardized coefficients, +raises P(win), -lowers it):")
    for name, coef in model.importance():
        bar = "#" * int(abs(coef) * 6)
        print(f"   {name:16s} {coef:+6.2f}  {bar}")

    # ---- per-threat feature need at the CURRENT design ----
    field = threat_field(140)
    spec1 = Specimen(v_max=60.0, a_max=100.0)
    needs = [L.feature_need(model, t, spec1) for t in field]
    n_speed = sum(1 for _, _, lab in needs if lab == "speed")
    n_agil = len(needs) - n_speed
    print(f"\nPER-THREAT NEED at the current design (v{spec1.v_max:.0f}/a{spec1.a_max:.0f}):")
    print(f"   {n_speed:3d}/140 threats demand SPEED first, {n_agil:3d}/140 demand AGILITY first.")
    dom = "SPEED (v_max)" if n_speed >= n_agil else "AGILITY (a_max)"
    print(f"   -> to maximize win from here, invest in {dom}.")

    # ---- use the surrogate to pick a max-win design with ZERO new sims, then validate once ----
    pick, pred = L.best_design_by_surrogate(model, field)
    print(f"\nSURROGATE-PICKED design (argmax predicted win over 140 threats, no new sims):")
    print(f"   v{pick.v_max:.0f}/a{pick.a_max:.0f}  mass {pick.mass:.2f} kg   predicted win {pred*100:.0f}%")

    # honest check: run BOTH on the real simulator over the full field
    ov_pick = evaluate(pick, field)
    ov_base = evaluate(spec1, field)
    print(f"\nVALIDATION on the real simulator (full 140):")
    print(f"   specimen 1  v60/a100 :  real win {(1-ov_base[0])*100:.0f}%   time {ov_base[1]:.1f}s  energy {ov_base[2]/1e3:.1f}k")
    print(f"   surrogate pick        :  real win {(1-ov_pick[0])*100:.0f}%   time {ov_pick[1]:.1f}s  energy {ov_pick[2]/1e3:.1f}k")
    print(f"\n   the surrogate steered design selection from ~{len(ytr)} sims of learning,")
    print(f"   then only 140 sims to confirm — not 140 x every candidate.")


if __name__ == "__main__":
    main()
