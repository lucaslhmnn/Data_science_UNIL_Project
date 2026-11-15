"""Phase 2 des compléments : ajustement des modèles de la table d'ablation (PROTOCOLE_COMPLEMENTAIRE § 4).
Références M0, M1, M2, M4 recalculées ; GLM G1-G4 ; LightGBM L1-L6. Écrit les prédictions, les coefficients
des GLM, les modèles LightGBM et le contrôle de reproduction du premier jet dans complements/resultats/."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ccommun import (CRES, JET_RES, SEED, TARGETS, ZONES, fit_lgb_predict, load_ds, m4_params,  # noqa: E402
                     prepare)

np.random.seed(SEED)
ALL4 = ["zone", "mean_coverage", "hist_per_1000", "county_hist_per_1000"]
LGB_MODELS = {
    "M4": ALL4,
    "L1": ["zone", "hist_per_1000", "county_hist_per_1000"],
    "L2": ["zone", "mean_coverage", "hist_per_1000"],
    "L3": ["zone", "mean_coverage"],
    "L4": ["zone", "hist_per_1000"],
    "L5": ["zone"],
    "L6": ["zone", "rang_couverture_annee", "hist_per_1000", "county_hist_per_1000"],
}
GLM_MODELS = {   # composants de la matrice
    "M1": ["zone"],
    "M2": ["zone", "couv_k", "hist", "chist"],
    "G1": ["zone", "hist", "chist"],
    "G2": ["zone", "hist", "chist", "couv_tranches"],
    "G3": ["zone", "couv_k"],
    "G4": ["zone", "hist", "chist", "rang"],
    # HORS PROTOCOLE (ajouté après avoir vu les résultats, pour la question (a) du rapport) :
    # zone + couverture en tranches, sans historiques, à comparer à L3 (LightGBM zone + couverture)
    "G5_hp": ["zone", "couv_tranches"],
}


def add_features(d):
    tr = d[d["period"] == "train"]
    q = tr["mean_coverage"].quantile([0.2, 0.4, 0.6, 0.8]).to_numpy()
    edges = np.r_[-np.inf, q, np.inf]
    labels = [f"T{i}" for i in range(1, 6)]
    d["tranche_couverture"] = pd.cut(d["mean_coverage"], edges, labels=labels, right=True).astype(str)
    d["rang_couverture_annee"] = d.groupby("year")["mean_coverage"].rank(pct=True, method="average")
    info = {"bornes_quintiles_entrainement": [float(x) for x in q],
            "repartition_tranches": {p: d[d["period"] == p]["tranche_couverture"].value_counts(normalize=True)
                                     .sort_index().round(4).to_dict() for p in ["train", "test"]},
            "test_hors_bornes_bas": int(((d["period"] == "test") & (d["mean_coverage"] < tr["mean_coverage"].min())).sum()),
            "test_hors_bornes_haut": int(((d["period"] == "test") & (d["mean_coverage"] > tr["mean_coverage"].max())).sum())}
    return d, info


def design(d, comps):
    X = pd.DataFrame({"const": 1.0}, index=d.index)
    for z in ["V*", "A*"]:                                  # référence X, comme le premier jet
        X[f"zone_{z}"] = (d["zone"] == z).astype(float)
    if "couv_k" in comps:
        X["couverture_k$"] = d["mean_coverage"] / 1000.0
    if "hist" in comps:
        X["log1p_hist_per_1000"] = np.log1p(d["hist_per_1000"])
    if "chist" in comps:
        X["log1p_county_hist_per_1000"] = np.log1p(d["county_hist_per_1000"])
    if "couv_tranches" in comps:                            # référence T1 (tranche la plus basse)
        for t in ["T2", "T3", "T4", "T5"]:
            X[f"couverture_{t}"] = (d["tranche_couverture"] == t).astype(float)
    if "rang" in comps:
        X["rang_couverture_annee"] = d["rang_couverture_annee"]
    return X


def main():
    d, _ = prepare(load_ds())
    d, finfo = add_features(d)
    print("Variables construites :", json.dumps(finfo, indent=1, ensure_ascii=False))
    (CRES / "ablation_variables_construites.json").write_text(json.dumps(finfo, indent=1, ensure_ascii=False))
    tr = d[d["period"] == "train"]
    repro, coefs = [], []
    for code, col in TARGETS.items():
        out = d[["county_id", "zone", "year", "period", "exposure_years"]].copy()
        out["observe"] = d[col].to_numpy(float)
        rate = tr[col].sum() / tr["exposure_years"].sum()
        out["M0"] = rate * d["exposure_years"]
        for name, comps in GLM_MODELS.items():
            glm = sm.GLM(tr[col].to_numpy(float), design(tr, comps), family=sm.families.Poisson(), offset=tr["log_e"])
            r = glm.fit()
            if not r.converged:
                print(f"{code} {name} : NON CONVERGÉ")
                out[name] = np.nan
                continue
            out[name] = r.predict(design(d, comps), offset=d["log_e"])
            hc0 = glm.fit(cov_type="HC0")
            cl = glm.fit(cov_type="cluster", cov_kwds={"groups": tr["year"].to_numpy()})
            coefs.append(pd.DataFrame({"cible": code, "modele": name, "variable": r.params.index,
                                       "coefficient": r.params.values, "exp_coefficient": np.exp(r.params.values),
                                       "es_robuste_HC0": hc0.bse.values, "es_grappes_annee": cl.bse.values,
                                       "dispersion_pearson": float(np.sum(r.resid_pearson ** 2) / r.df_resid)}))
        params, n_iter = m4_params(code)
        for name, feats in LGB_MODELS.items():
            mu, booster, log_r = fit_lgb_predict(d, col, feats, params, n_iter)
            out[name] = mu
            booster.save_model(str(CRES / f"lgb_{name}_{code}.txt"))
        out.to_csv(CRES / f"ablation_predictions_{code}.csv", index=False)
        # Contrôle : les références recalculées reproduisent-elles le premier jet ?
        jet = pd.read_csv(JET_RES / f"predictions_{code}.csv", dtype={"county_id": str})
        for m in ["M0", "M1", "M2", "M4"]:
            rel = float(np.max(np.abs(out[m].to_numpy() - jet[m].to_numpy()) / jet[m].to_numpy()))
            repro.append({"cible": code, "modele": m, "ecart_relatif_max_vs_premier_jet": rel,
                          "reproduit": rel < 1e-9})
        print(f"{code} : {len(GLM_MODELS)} GLM et {len(LGB_MODELS)} LightGBM ajustés ; hyperparamètres "
              f"{ {k: params[k] for k in ['learning_rate', 'num_leaves', 'min_data_in_leaf', 'lambda_l2']} }, "
              f"{n_iter} itérations")
    pd.concat(coefs).to_csv(CRES / "ablation_coefficients_glm.csv", index=False)
    rp = pd.DataFrame(repro)
    rp.to_csv(CRES / "ablation_reproduction_premier_jet.csv", index=False)
    print("\nReproduction du premier jet :\n" + rp.to_string(index=False))


if __name__ == "__main__":
    main()
