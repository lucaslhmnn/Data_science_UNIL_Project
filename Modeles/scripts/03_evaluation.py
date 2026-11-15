"""Phase 3 : évaluation sur le test 2020-2024 (PROTOCOLE.md § 5). Lit les prédictions de 02_modeles.py,
écrit les tableaux dans Modeles/resultats/ et les figures dans Modeles/figures/."""
import json
import sys
from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (FIG, RES, SEED, TARGETS, TEST, ZONES, lgb_matrix, load_ds, poisson_deviance,  # noqa: E402
                    prepare)

MODELS = ["M0", "M1", "M_oracle", "M2", "M3", "M4"]
LABEL = {"M0": "M0 nul", "M1": "M1 GLM zone", "M_oracle": "M_oracle (non prédictif)", "M2": "M2 GLM Poisson",
         "M3": "M3 GLM binomial négatif", "M4": "M4 LightGBM"}
COL = {"M0": "#8a8984", "M1": "#c9c8c2", "M_oracle": "#1baf7a", "M2": "#2a78d6", "M3": "#eda100", "M4": "#eb6834"}
TEST_YEARS = list(range(TEST[0], TEST[1] + 1))
N_BOOT, N_PERM = 1000, 20
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e5e1", "axes.axisbelow": True,
                     "axes.titlelocation": "left", "figure.facecolor": "white"})


def dev_table(p, code):
    rows = []
    sets = {"entraînement 2010-2019": p["period"] == "train", "test 2020-2024": p["period"] == "test",
            "test sans 2024": (p["period"] == "test") & (p["year"] != 2024)}
    for sname, m in sets.items():
        d0 = poisson_deviance(p.loc[m, "observe"], p.loc[m, "M0"]).sum()
        for mod in MODELS:
            dv = poisson_deviance(p.loc[m, "observe"], p.loc[m, mod])
            rows.append({"cible": code, "ensemble": sname, "modele": mod, "lignes": int(m.sum()),
                         "deviance_totale": dv.sum(), "deviance_moyenne_par_ligne": dv.mean(),
                         "gain_relatif_vs_M0": 1 - dv.sum() / d0,
                         "remarque": "oracle : ajusté sur cet ensemble" if mod == "M_oracle" else ""})
    return pd.DataFrame(rows)


def per_year(p, code):
    rows = []
    for y, g in p.groupby("year"):
        d0 = poisson_deviance(g["observe"], g["M0"]).sum()
        for mod in MODELS:
            dv = poisson_deviance(g["observe"], g[mod]).sum()
            rows.append({"cible": code, "annee": int(y), "periode": g["period"].iloc[0], "modele": mod,
                         "observe": g["observe"].sum(), "predit": g[mod].sum(),
                         "ratio_predit_observe": g[mod].sum() / g["observe"].sum(),
                         "deviance_totale": dv, "gain_relatif_vs_M0": 1 - dv / d0})
    return pd.DataFrame(rows)


def per_zone_test(p, code):
    t = p[p["period"] == "test"]
    rows = []
    for z, g in t.groupby("zone"):
        for mod in MODELS:
            rows.append({"cible": code, "zone": z, "modele": mod, "observe": g["observe"].sum(),
                         "predit": g[mod].sum(), "ratio_predit_observe": g[mod].sum() / g["observe"].sum()})
    return pd.DataFrame(rows)


def rescaled(p, code):
    """ANALYSE COMPLÉMENTAIRE NON PRÉ-ENREGISTRÉE (diagnostic) : chaque modèle est recalé, année par année,
    sur le total observé de l'année, ce qui retire l'erreur de niveau et ne laisse que la répartition entre
    cellules. Utilise le total observé du test : ce n'est pas une prédiction."""
    t = p[p["period"] == "test"].copy()
    rows = []
    for mod in MODELS:
        scale = t.groupby("year")["observe"].transform("sum") / t.groupby("year")[mod].transform("sum")
        mu = t[mod] * scale
        rows.append({"cible": code, "modele": mod, "deviance_test_recalee": poisson_deviance(t["observe"], mu).sum(),
                     "deviance_test_recalee_sans_2024": poisson_deviance(t.loc[t.year != 2024, "observe"],
                                                                          mu[t.year != 2024]).sum()})
    r = pd.DataFrame(rows)
    for c in ["deviance_test_recalee", "deviance_test_recalee_sans_2024"]:
        r[f"gain_vs_M0_{c.replace('deviance_test_', '')}"] = 1 - r[c] / r.loc[r.modele == "M0", c].iloc[0]
    r["statut"] = "diagnostic non pré-enregistré (utilise le total observé de chaque année de test)"
    return r


def bootstrap(p, code):
    """Rééchantillonnage des 5 années de test avec remise (blocs = années). Indicatif."""
    t = p[p["period"] == "test"]
    D = pd.DataFrame({m: t.groupby("year").apply(lambda g, m=m: poisson_deviance(g["observe"], g[m]).sum(),
                                                 include_groups=False) for m in MODELS}).loc[TEST_YEARS]
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(TEST_YEARS), size=(N_BOOT, len(TEST_YEARS)))
    rows = []
    for a, b in [("M4", "M2"), ("M2", "M0"), ("M3", "M2"), ("M4", "M0")]:
        diff_y = (D[a] - D[b]).to_numpy()
        boot = diff_y[idx].sum(axis=1)
        loo = [diff_y.sum() - diff_y[i] for i in range(len(TEST_YEARS))]
        rows.append({"cible": code, "difference": f"{a} - {b}", "valeur_test": diff_y.sum(),
                     "boot_p2_5": np.percentile(boot, 2.5), "boot_p97_5": np.percentile(boot, 97.5),
                     "boot_part_negative": float((boot < 0).mean()),
                     "annees_ou_negative": ", ".join(str(y) for y, v in zip(TEST_YEARS, diff_y) if v < 0),
                     "sans_une_annee_min": min(loo), "sans_une_annee_max": max(loo),
                     "nb_tirages_distincts": int(len({tuple(sorted(r)) for r in idx}))})
    D.to_csv(RES / f"deviance_par_annee_test_matrice_{code}.csv")
    return pd.DataFrame(rows)


def permutation(code, d, col):
    t = d[d["period"] == "test"].reset_index(drop=True)
    b = lgb.Booster(model_file=str(RES / f"m4_{code}.txt"))
    tr = d[d["period"] == "train"]
    log_r = np.log(tr[col].sum() / tr["exposure_years"].sum())
    X = lgb_matrix(t)

    def dev(Xm):
        mu = np.exp(b.predict(Xm, raw_score=True) + t["log_e"].to_numpy() + log_r)
        return poisson_deviance(t[col], mu).sum()
    base = dev(X)
    rng = np.random.default_rng(SEED)
    rows = []
    for f in X.columns:
        incs = []
        for _ in range(N_PERM):
            Xp = X.copy()
            Xp[f] = X[f].to_numpy()[rng.permutation(len(X))]
            if f == "zone":
                Xp[f] = pd.Categorical(Xp[f], categories=ZONES)
            incs.append(dev(Xp) - base)
        rows.append({"cible": code, "variable": f, "hausse_deviance_test_moyenne": np.mean(incs),
                     "hausse_deviance_test_ecart_type": np.std(incs, ddof=1),
                     "hausse_relative": np.mean(incs) / base})
    return pd.DataFrame(rows), base


def figures(code, py, pz):
    lab = "sinistres payés" if code == "payes" else "tous les sinistres"
    # 1. Prédit contre observé par année
    fig, ax = plt.subplots(figsize=(11, 4.8), layout="constrained")
    obs = py[py["modele"] == "M0"].set_index("annee")["observe"]
    ax.bar(obs.index, obs.values, 0.7, color="#efeeea", edgecolor="#c9c8c2", label="observé")
    for m in ["M0", "M2", "M3", "M4"]:
        s = py[py["modele"] == m].set_index("annee")["predit"]
        ax.plot(s.index, s.values, "-o", ms=4, lw=1.8, color=COL[m], label=f"prédit : {LABEL[m]}")
    ax.axvspan(TEST[0] - 0.5, TEST[1] + 0.5, color="#2a78d6", alpha=0.06, lw=0)
    ax.text(TEST[0] - 0.3, ax.get_ylim()[1] * 0.97, "test", va="top", style="italic")
    ax.set_xticks(obs.index)
    ax.set_ylabel(f"Nombre de {lab}")
    ax.set_title(f"Sinistres prédits et observés par année ({lab}) ; modèles ajustés sur 2010-2019")
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    fig.savefig(FIG / f"predit_observe_par_annee_{code}.png", dpi=200)
    plt.close(fig)
    # 2. Calibration par zone (test)
    fig, ax = plt.subplots(figsize=(9, 4.6), layout="constrained")
    mods = ["M0", "M1", "M2", "M3", "M4"]
    x = np.arange(len(ZONES))
    for k, m in enumerate(mods):
        r = pz[pz["modele"] == m].set_index("zone").reindex(ZONES)["ratio_predit_observe"]
        ax.bar(x + (k - 2) * 0.16, r.values, 0.15, color=COL[m], label=LABEL[m])
    ax.axhline(1, color="#0b0b0b", lw=1, ls=":")
    ax.set_xticks(x, ZONES)
    ax.set_xlabel("Zone d'inondation")
    ax.set_ylabel("Ratio prédit / observé (1 = calibré)")
    ax.set_title(f"Calibration par zone sur le test 2020-2024 ({lab})")
    ax.legend(fontsize=8.5, frameon=False, ncol=3)
    fig.savefig(FIG / f"calibration_zone_test_{code}.png", dpi=200)
    plt.close(fig)
    # 3. Gain de déviance par rapport à M0, par année de test
    fig, ax = plt.subplots(figsize=(10, 4.6), layout="constrained")
    t = py[(py["periode"] == "test") & py["modele"].isin(["M1", "M2", "M3", "M4", "M_oracle"])]
    mods = ["M1", "M2", "M3", "M4", "M_oracle"]
    for k, m in enumerate(mods):
        s = t[t["modele"] == m].set_index("annee").reindex(TEST_YEARS)["gain_relatif_vs_M0"]
        ax.bar(np.arange(len(TEST_YEARS)) + (k - 2) * 0.16, 100 * s.values, 0.15, color=COL[m], label=LABEL[m])
    ax.axhline(0, color="#0b0b0b", lw=1)
    ax.set_xticks(np.arange(len(TEST_YEARS)), TEST_YEARS)
    ax.set_ylabel("Gain de déviance par rapport à M0 (%)")
    ax.set_title(f"Déviance de Poisson par année de test : gain relatif par rapport au modèle nul ({lab})")
    ax.legend(fontsize=8.5, frameon=False, ncol=3)
    fig.savefig(FIG / f"gain_deviance_par_annee_{code}.png", dpi=200)
    plt.close(fig)


def main():
    d, _ = prepare(load_ds())
    all_dev, all_year, all_zone, all_boot, all_perm, all_resc = [], [], [], [], [], []
    for code, col in TARGETS.items():
        p = pd.read_csv(RES / f"predictions_{code}.csv", dtype={"county_id": str})
        assert len(p) == len(d) and p[MODELS].notna().all().all(), f"prédictions incomplètes ({code})"
        all_dev.append(dev_table(p, code))
        py = per_year(p, code)
        pz = per_zone_test(p, code)
        all_year.append(py)
        all_zone.append(pz)
        all_boot.append(bootstrap(p, code))
        all_resc.append(rescaled(p, code))
        tot = p.groupby("period")[["observe"] + MODELS].sum()
        tot = tot[MODELS].div(tot["observe"], axis=0).reset_index().melt(id_vars="period", var_name="modele",
                                                                          value_name="ratio_predit_observe")
        tot.insert(0, "cible", code)
        all_tot = tot if code == "payes" else pd.concat([all_tot, tot])
        perm, base = permutation(code, d, col)
        all_perm.append(perm)
        figures(code, py, pz)
    pd.concat(all_dev).to_csv(RES / "deviance_par_modele.csv", index=False)
    pd.concat(all_year).to_csv(RES / "par_annee_calibration_deviance.csv", index=False)
    pd.concat(all_zone).to_csv(RES / "calibration_par_zone_test.csv", index=False)
    pd.concat(all_boot).to_csv(RES / "bootstrap_annees_test.csv", index=False)
    pd.concat(all_perm).to_csv(RES / "importance_permutation_test_m4.csv", index=False)
    pd.concat(all_resc).to_csv(RES / "diagnostic_deviance_recalee_par_annee.csv", index=False)
    all_tot.to_csv(RES / "calibration_totale_par_periode.csv", index=False)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    for name in ["deviance_par_modele", "bootstrap_annees_test", "importance_permutation_test_m4",
                 "calibration_par_zone_test", "diagnostic_deviance_recalee_par_annee",
                 "calibration_totale_par_periode"]:
        print(f"\n=== {name} ===\n" + pd.read_csv(RES / f"{name}.csv").round(4).to_string(index=False))
    py = pd.concat(all_year)
    print("\n=== ratio prédit / observé par année (test) ===")
    print(py[py["periode"] == "test"].pivot_table(index=["cible", "annee"], columns="modele",
                                                  values="ratio_predit_observe").round(3).to_string())
    print("\n=== gain relatif vs M0 par année (test) ===")
    print(py[py["periode"] == "test"].pivot_table(index=["cible", "annee"], columns="modele",
                                                  values="gain_relatif_vs_M0").round(3).to_string())


if __name__ == "__main__":
    main()
