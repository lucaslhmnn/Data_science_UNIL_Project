"""HORS PROTOCOLE (ajouté après lecture des résultats de l'ablation, pour éclairer la question (a)).
Tableau descriptif, sans nouveau modèle : taux observé et taux prédit (L3, G5_hp, M1) par tranche de
couverture (quintiles de l'entraînement) et par période. Aucune conclusion causale."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ccommun import CRES, TARGETS, load_ds, prepare  # noqa: E402
from c2_ablation_modeles import add_features  # noqa: E402


def main():
    d, _ = prepare(load_ds())
    d, _ = add_features(d)
    rows = []
    for code in TARGETS:
        p = pd.read_csv(CRES / f"ablation_predictions_{code}.csv", dtype={"county_id": str})
        p["tranche"] = d["tranche_couverture"].to_numpy()
        g = p.groupby(["period", "tranche"])[["exposure_years", "observe", "M1", "G5_hp", "L3"]].sum()
        for m in ["observe", "M1", "G5_hp", "L3"]:
            g[f"taux_{m}_1000"] = 1000 * g[m] / g["exposure_years"]
        g["part_exposition_periode"] = g["exposure_years"] / g.groupby(level=0)["exposure_years"].transform("sum")
        g = g.reset_index()
        g.insert(0, "cible", code)
        rows.append(g)
    t = pd.concat(rows)
    t["statut"] = "hors protocole, descriptif"
    t.to_csv(CRES / "hp_taux_par_tranche_couverture.csv", index=False)
    pd.set_option("display.width", 220)
    print(t[["cible", "period", "tranche", "part_exposition_periode", "taux_observe_1000", "taux_M1_1000",
             "taux_G5_hp_1000", "taux_L3_1000"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
