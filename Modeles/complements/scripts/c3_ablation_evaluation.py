"""Phase 2 (suite) : évaluation de la table d'ablation (PROTOCOLE_COMPLEMENTAIRE § 5). Écrit
ablation_deviance.csv, ablation_calibration_annee.csv, ablation_diff_par_annee.csv, les importances des
LightGBM et les figures ablation_gain_brut.png / ablation_gain_recale.png."""
import sys
from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ccommun import (CFIG, CRES, SEED, TARGETS, TEST_YEARS, ZONES, lgb_X, load_ds, poisson_deviance,  # noqa: E402
                     prepare, rescale_by_year)
from c2_ablation_modeles import LGB_MODELS, add_features  # noqa: E402

MODELS = ["M0", "M1", "M2", "G1", "G2", "G3", "G4", "G5_hp", "M4", "L1", "L2", "L3", "L4", "L5", "L6"]
DESC = {"M0": "nul", "M1": "GLM zone", "M2": "GLM zone + couverture + historiques",
        "G1": "GLM sans couverture", "G2": "GLM couverture en tranches", "G3": "GLM zone + couverture",
        "G4": "GLM rang de couverture dans l'année",
        "G5_hp": "GLM zone + couverture en tranches (HORS PROTOCOLE)", "M4": "LightGBM 4 variables",
        "L1": "LightGBM sans couverture", "L2": "LightGBM sans historique du comté",
        "L3": "LightGBM sans historiques", "L4": "LightGBM zone + historique de la cellule",
        "L5": "LightGBM zone seule", "L6": "LightGBM rang de couverture dans l'année"}
REF = {**{m: "M2" for m in ["G1", "G2", "G3", "G4", "G5_hp"]},
       **{m: "M4" for m in ["L1", "L2", "L3", "L4", "L5", "L6"]}}
N_PERM = 20


def evaluate(p, code):
    dev_rows, cal_rows, diff_rows = [], [], []
    tr, te = p[p["period"] == "train"], p[p["period"] == "test"].copy()
    te_no24 = te["year"] != 2024
    rec = {m: rescale_by_year(te, m) for m in MODELS}
    d0 = {"train": poisson_deviance(tr["observe"], tr["M0"]).sum(),
          "test": poisson_deviance(te["observe"], te["M0"]).sum(),
          "test_sans_2024": poisson_deviance(te.loc[te_no24, "observe"], te.loc[te_no24, "M0"]).sum(),
          "test_recale": poisson_deviance(te["observe"], rec["M0"]).sum(),
          "test_sans_2024_recale": poisson_deviance(te.loc[te_no24, "observe"], rec["M0"][te_no24]).sum()}
    for m in MODELS:
        dv = {"train": poisson_deviance(tr["observe"], tr[m]),
              "test": poisson_deviance(te["observe"], te[m]),
              "test_sans_2024": poisson_deviance(te.loc[te_no24, "observe"], te.loc[te_no24, m]),
              "test_recale": poisson_deviance(te["observe"], rec[m]),
              "test_sans_2024_recale": poisson_deviance(te.loc[te_no24, "observe"], rec[m][te_no24])}
        for s, v in dv.items():
            dev_rows.append({"cible": code, "modele": m, "description": DESC[m], "ensemble": s,
                             "deviance_totale": v.sum(), "deviance_par_ligne": v.mean(),
                             "gain_vs_M0": 1 - v.sum() / d0[s],
                             "mise_en_garde": "recalage : utilise les totaux observés du test" if "recale" in s else ""})
        for y in TEST_YEARS + ["total"]:
            g = te if y == "total" else te[te["year"] == y]
            dvy = poisson_deviance(g["observe"], g[m]).sum()
            d0y = poisson_deviance(g["observe"], g["M0"]).sum()
            cal_rows.append({"cible": code, "modele": m, "annee": y, "observe": g["observe"].sum(),
                             "predit": g[m].sum(), "ratio_predit_observe": g[m].sum() / g["observe"].sum(),
                             "deviance": dvy, "gain_vs_M0": 1 - dvy / d0y})
        if m in REF:
            r = REF[m]
            for y in TEST_YEARS:
                g = te[te["year"] == y]
                a, b = poisson_deviance(g["observe"], g[m]).sum(), poisson_deviance(g["observe"], g[r]).sum()
                diff_rows.append({"cible": code, "modele": m, "reference": r, "annee": y, "deviance_modele": a,
                                  "deviance_reference": b, "difference_modele_moins_reference": a - b})
    return pd.DataFrame(dev_rows), pd.DataFrame(cal_rows), pd.DataFrame(diff_rows)


def importances(code, col, d):
    te = d[d["period"] == "test"].reset_index(drop=True)
    tr = d[d["period"] == "train"]
    log_r = np.log(tr[col].sum() / tr["exposure_years"].sum())
    rng = np.random.default_rng(SEED)
    rows = []
    for name, feats in LGB_MODELS.items():
        b = lgb.Booster(model_file=str(CRES / f"lgb_{name}_{code}.txt"))
        X = lgb_X(te, feats)

        def dev(Xm):
            return poisson_deviance(te[col], np.exp(b.predict(Xm, raw_score=True) + te["log_e"].to_numpy() + log_r)).sum()
        base = dev(X)
        gain = dict(zip(b.feature_name(), b.feature_importance("gain")))
        tot = sum(gain.values())
        for f in feats:
            incs = []
            for _ in range(N_PERM):
                Xp = X.copy()
                Xp[f] = X[f].to_numpy()[rng.permutation(len(X))]
                if f == "zone":
                    Xp[f] = pd.Categorical(Xp[f], categories=ZONES)
                incs.append(dev(Xp) - base)
            rows.append({"cible": code, "modele": name, "variable": f, "part_gain_entrainement": gain[f] / tot if tot else np.nan,
                         "permutation_hausse_deviance_test": np.mean(incs),
                         "permutation_ecart_type": np.std(incs, ddof=1)})
    return pd.DataFrame(rows)


def figure(dev, which, fname, title):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5), sharey=True, layout="constrained")
    order = [m for m in MODELS if m != "M0"]
    for ax, code, lab in zip(axes, ["payes", "tous"], ["sinistres payés", "tous les sinistres"]):
        t = dev[(dev["cible"] == code) & (dev["ensemble"] == which)].set_index("modele").reindex(order)
        colors = ["#8a8984" if m in ("M1", "M2", "M4") else ("#c9c8c2" if m.endswith("_hp") else
                  ("#2a78d6" if m.startswith("G") else "#eb6834")) for m in order]
        y = np.arange(len(order))[::-1]
        ax.barh(y, 100 * t["gain_vs_M0"], color=colors, height=0.65)
        for yi, v in zip(y, 100 * t["gain_vs_M0"]):
            ax.text(v + (0.4 if v >= 0 else -0.4), yi, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right",
                    fontsize=8.5)
        ax.axvline(0, color="#0b0b0b", lw=1)
        vals = 100 * t["gain_vs_M0"]
        ax.set_xlim(min(0.0, vals.min()) - 5, max(0.0, vals.max()) + 4)   # place pour les étiquettes
        ax.set_yticks(y, [f"{m}  {DESC[m]}" for m in order], fontsize=9)
        ax.set_xlabel("Gain de déviance de Poisson par rapport à M0 (%)")
        ax.set_title(lab)
        ax.grid(axis="x", color="#e6e5e1")
    fig.suptitle(title, x=0.01, ha="left", fontsize=12)
    fig.savefig(CFIG / fname, dpi=200)
    plt.close(fig)


def main():
    d, _ = prepare(load_ds())
    d, _ = add_features(d)
    devs, cals, diffs, imps = [], [], [], []
    for code, col in TARGETS.items():
        p = pd.read_csv(CRES / f"ablation_predictions_{code}.csv", dtype={"county_id": str})
        assert len(p) == len(d) and p[MODELS].notna().all().all(), f"prédictions incomplètes ({code})"
        a, b, c = evaluate(p, code)
        devs.append(a)
        cals.append(b)
        diffs.append(c)
        imps.append(importances(code, col, d))
    dev = pd.concat(devs)
    dev.to_csv(CRES / "ablation_deviance.csv", index=False)
    pd.concat(cals).to_csv(CRES / "ablation_calibration_annee.csv", index=False)
    pd.concat(diffs).to_csv(CRES / "ablation_diff_par_annee.csv", index=False)
    pd.concat(imps).to_csv(CRES / "ablation_importance_lgb.csv", index=False)
    figure(dev, "test", "ablation_gain_brut.png", "Ablation : gain de déviance brut sur le test 2020-2024")
    figure(dev, "test_recale", "ablation_gain_recale.png",
           "Ablation : gain de déviance après recalage annuel sur le test 2020-2024 "
           "(diagnostic : utilise les totaux observés de chaque année)")
    pd.set_option("display.width", 220)
    piv = dev.pivot_table(index=["cible", "modele"], columns="ensemble", values="gain_vs_M0").reindex(
        columns=["train", "test", "test_sans_2024", "test_recale", "test_sans_2024_recale"])
    piv = piv.reindex([(c, m) for c in TARGETS for m in MODELS])
    print("Gain relatif par rapport à M0 :\n" + (100 * piv).round(2).to_string())
    tot = pd.concat(cals)
    print("\nRatio prédit / observé (test) :\n" + tot.pivot_table(index=["cible", "modele"], columns="annee",
                                                                    values="ratio_predit_observe", aggfunc="first")
          .reindex([(c, m) for c in TARGETS for m in MODELS]).round(3).to_string())
    dd = pd.concat(diffs)
    print("\nDifférence de déviance avec la référence, par année :\n" + dd.pivot_table(
        index=["cible", "modele", "reference"], columns="annee", values="difference_modele_moins_reference")
          .round(0).to_string())
    print("\nImportances LightGBM :\n" + pd.concat(imps).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
