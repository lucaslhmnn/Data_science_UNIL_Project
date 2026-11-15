"""Phase 4 : évaluation à origine glissante (ANALYSE COMPLÉMENTAIRE, non pré-enregistrée, ajoutée le
15/11/2026 après le premier jet). Les modèles M0 à M4 sont ceux de 02_modeles.py : mêmes formules, même
grille LightGBM, même offset (avenant n° 1 : init_score = log(e) + log(r)). Ce script change seulement :
  1. l'évaluation : ajuster sur 2010..t-1 et prédire t, pour t = 2016..2024, au lieu d'un seul
     ajustement 2010-2019 ; 2016-2019 sert de validation, 2020-2024 reste le test ;
  2. les variables : couverture en dollars constants (coverage_real de ds_clean) à la place de la
     couverture nominale, qui servait d'année déguisée ; variantes sans historique du comté, sans
     couverture, avec un historique récent ;
  3. les mesures : déviance brute et recalée par année (le OÙ sans le QUAND), indice de Gini,
     intervalles de confiance par rééchantillonnage des comtés ;
  4. une cible de sensibilité : sinistres payés hors des dix plus grands événements.
Le jeu de variables principal est A (les variables déclarées, couverture déflatée). Les autres jeux
sont des analyses de sensibilité : aucun n'est choisi d'après le test.
Les résultats sont aussi donnés pour la Floride et pour les sept autres États (RQ2).
Sorties : Modeles/resultats/glissant_*.csv et Modeles/figures/glissant_gain.png.
Usage, depuis la racine du dépôt : bash Modeles/run_all.sh (ou ce script seul, avec Modeles/.venv).
"""
import itertools
import sys
import warnings
from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402
from statsmodels.discrete.discrete_model import NegativeBinomial  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import FIG, RES, SEED, ZONES, load_ds, poisson_deviance, prepare, zone_design  # noqa: E402

np.random.seed(SEED)
LGB_BASE = {"objective": "poisson", "metric": "poisson", "verbose": -1, "seed": SEED, "deterministic": True,
            "num_threads": 1, "force_row_wise": True, "feature_pre_filter": False,
            "bagging_fraction": 1.0, "feature_fraction": 1.0}
GRID = {"learning_rate": [0.02, 0.05], "num_leaves": [7, 15], "min_data_in_leaf": [100, 300],
        "lambda_l2": [1.0, 10.0]}
MAX_ROUNDS, PATIENCE = 3000, 100
ORIGINS = list(range(2016, 2025))
VALID_YEARS, TEST_YEARS = [2016, 2017, 2018, 2019], [2020, 2021, 2022, 2023, 2024]
N_BOOT = 2000

# Jeux de variables. P = premier jet ; A = jeu principal de cette phase.
FEATURE_SETS = {
    "P": ["zone", "mean_coverage", "hist_per_1000", "county_hist_per_1000"],
    "A": ["zone", "coverage_real", "hist_per_1000", "county_hist_per_1000"],
    "B": ["zone", "coverage_real", "hist_per_1000"],
    "C": ["zone", "hist_per_1000"],
    "D": ["zone", "coverage_real", "hist_per_1000", "recent_per_1000"],
}
SET_LABEL = {"P": "premier jet : couverture nominale, historique, historique du comté",
             "A": "principal : couverture réelle, historique, historique du comté",
             "B": "couverture réelle, historique",
             "C": "historique seul (sans couverture)",
             "D": "couverture réelle, historique, historique récent"}
MAIN_SET = "A"
TARGETS = {"payes": "n_claims", "payes_hors_grands_evenements": "n_hors_majeurs"}
LOG1P = {"hist_per_1000", "county_hist_per_1000", "recent_per_1000"}


def add_features(d):
    """Historique récent : sinistres payés pour 1 000 contrats-années de la cellule sur 2010..t-1
    (0 en 2010). N'utilise que le passé de chaque année."""
    d = d.sort_values(["county_id", "zone", "year"]).reset_index(drop=True)
    g = d.groupby(["county_id", "zone"])
    cum_n = g["n_claims"].cumsum() - d["n_claims"]
    cum_e = g["exposure_years"].cumsum() - d["exposure_years"]
    d["recent_per_1000"] = np.where(cum_e > 0, 1000 * cum_n / cum_e.where(cum_e > 0, 1.0), 0.0)
    return d


def glm_X(d, feats):
    X = zone_design(d)
    for f in feats:
        if f == "zone":
            continue
        if f in LOG1P:
            X[f"log1p_{f}"] = np.log1p(d[f])
        else:
            X[f"{f}_k$"] = d[f] / 1000.0
    return X


def lgb_X(d, feats):
    X = d[feats].copy()
    X["zone"] = pd.Categorical(X["zone"], categories=ZONES)
    return X


def fit_nb(y, X, expo, start):
    nb = NegativeBinomial(y, X, loglike_method="nb2", exposure=expo)
    for method in ["newton", "bfgs"]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                r = nb.fit(start_params=np.r_[start, 1.0], method=method, maxiter=5000, disp=0)
            except Exception:
                continue
        if r.mle_retvals.get("converged", False) and np.isfinite(r.params).all():
            return r
    return None


def fit_lgb(tr, te, col, feats):
    """Procédure de Pablo appliquée à chaque origine : grille réglée sur les deux dernières années
    d'entraînement (arrêt anticipé), puis réajustement sur tout l'entraînement."""
    last = tr["year"].max()
    fit_p, val_p = tr[tr["year"] <= last - 2], tr[tr["year"] > last - 2]
    r_fit = fit_p[col].sum() / fit_p["exposure_years"].sum()
    best = None
    for lr, nl, mdl, l2 in itertools.product(*GRID.values()):
        params = {**LGB_BASE, "learning_rate": lr, "num_leaves": nl, "min_data_in_leaf": mdl, "lambda_l2": l2}
        dtr = lgb.Dataset(lgb_X(fit_p, feats), fit_p[col].to_numpy(float), init_score=fit_p["log_e"] + np.log(r_fit),
                          categorical_feature=["zone"], free_raw_data=False)
        dva = lgb.Dataset(lgb_X(val_p, feats), val_p[col].to_numpy(float), init_score=val_p["log_e"] + np.log(r_fit),
                          categorical_feature=["zone"], reference=dtr)
        b = lgb.train(params, dtr, MAX_ROUNDS, valid_sets=[dva], valid_names=["v"],
                      callbacks=[lgb.early_stopping(PATIENCE, verbose=False)])
        mu = np.exp(b.predict(lgb_X(val_p, feats), raw_score=True, num_iteration=b.best_iteration)
                    + val_p["log_e"] + np.log(r_fit))
        dev = poisson_deviance(val_p[col], mu).sum()
        if best is None or dev < best[0]:
            best = (dev, params, b.best_iteration)
    _, params, n_iter = best
    r_tr = tr[col].sum() / tr["exposure_years"].sum()
    dall = lgb.Dataset(lgb_X(tr, feats), tr[col].to_numpy(float), init_score=tr["log_e"] + np.log(r_tr),
                       categorical_feature=["zone"], free_raw_data=False)
    m = lgb.train(params, dall, max(n_iter, 1))
    hp = {k: params[k] for k in GRID} | {"iterations": int(n_iter)}
    return np.exp(m.predict(lgb_X(te, feats), raw_score=True) + te["log_e"] + np.log(r_tr)), hp


def predict_year(tr, te, col, feats):
    """Ajuste M0..M4 sur tr et renvoie les prédictions sur te."""
    y = tr[col].to_numpy(float)
    out = {}
    out["M0"] = (y.sum() / tr["exposure_years"].sum()) * te["exposure_years"].to_numpy()
    m1 = sm.GLM(y, zone_design(tr), family=sm.families.Poisson(), offset=tr["log_e"]).fit()
    out["M1"] = np.asarray(m1.predict(zone_design(te), offset=te["log_e"]))
    Xtr, Xte = glm_X(tr, feats), glm_X(te, feats)
    m2 = sm.GLM(y, Xtr, family=sm.families.Poisson(), offset=tr["log_e"]).fit()
    out["M2"] = np.asarray(m2.predict(Xte, offset=te["log_e"]))
    m3 = fit_nb(y, Xtr, tr["exposure_years"].to_numpy(), np.asarray(m2.params))
    out["M3"] = (np.asarray(m3.predict(Xte, exposure=te["exposure_years"].to_numpy())) if m3 is not None
                 else np.full(len(te), np.nan))
    mu4, hp = fit_lgb(tr, te, col, feats)
    out["M4"] = np.asarray(mu4)
    return out, hp


def gini(y, mu, e):
    """Gini ordonné : cellules triées par fréquence prédite, part cumulée d'exposition contre part
    cumulée de sinistres observés. 0 = pas de tri, plus haut = meilleur classement."""
    o = np.argsort(mu / e, kind="stable")
    cx = np.r_[0, np.cumsum(e[o]) / e.sum()]
    cy = np.r_[0, np.cumsum(y[o]) / y.sum()]
    return 1 - 2 * np.trapezoid(cy, cx)


MODELS = ["M0", "M1", "M2", "M3", "M4"]


def recal(p, mod):
    return p[mod] * p.groupby("year")["y"].transform("sum") / p.groupby("year")[mod].transform("sum")


def summarise(p, years):
    t = p[p["year"].isin(years)]
    rows = {}
    d0 = poisson_deviance(t["y"], t["M0"]).sum()
    d0r = poisson_deviance(t["y"], recal(t, "M0")).sum()
    for mod in MODELS:
        if t[mod].isna().any():
            rows[mod] = {"gain_brut": np.nan, "gain_recale": np.nan, "gini": np.nan, "predit_sur_observe": np.nan}
            continue
        gy = [(g["y"].sum(), gini(g["y"].to_numpy(), g[mod].to_numpy(), g["e"].to_numpy()))
              for _, g in t.groupby("year") if g["y"].sum() > 0]
        rows[mod] = {"gain_brut": 1 - poisson_deviance(t["y"], t[mod]).sum() / d0,
                     "gain_recale": 1 - poisson_deviance(t["y"], recal(t, mod)).sum() / d0r,
                     # M0 prédit la même fréquence partout : il ne classe rien, Gini non défini
                     "gini": np.nan if mod == "M0" else float(np.average([g for _, g in gy], weights=[w for w, _ in gy])),
                     "predit_sur_observe": t[mod].sum() / t["y"].sum()}
    return pd.DataFrame(rows).T


def boot_counties(p, years, a, b, rng):
    """IC à 95 % de l'écart de gain recalé (a moins b, en points de M0 recalé) par rééchantillonnage
    des comtés. Mesure l'incertitude sur le OÙ, à années données."""
    t = p[p["year"].isin(years)].copy()
    for mod in ["M0", a, b]:
        t[f"d_{mod}"] = poisson_deviance(t["y"], recal(t, mod))
    c = t.groupby("county_id")[["d_M0", f"d_{a}", f"d_{b}"]].sum().to_numpy()
    idx = rng.integers(0, len(c), size=(N_BOOT, len(c)))
    s = c[idx].sum(axis=1)
    diff = (s[:, 2] - s[:, 1]) / s[:, 0]
    point = (c[:, 2].sum() - c[:, 1].sum()) / c[:, 0].sum()
    return point, *np.percentile(diff, [2.5, 97.5])


def frame(te, col, pr):
    o = te[["county_id", "zone", "year", "state"]].copy()
    o["e"], o["y"] = te["exposure_years"].to_numpy(), te[col].to_numpy(float)
    for k, v in pr.items():
        o[k] = v
    return o


def rolling(d, col, feats):
    parts, hps = [], []
    for t in ORIGINS:
        tr, te = d[d["year"] < t], d[d["year"] == t]
        pr, hp = predict_year(tr, te, col, feats)
        parts.append(frame(te, col, pr))
        hps.append({"annee_predite": t, **hp})
    return pd.concat(parts, ignore_index=True), pd.DataFrame(hps)


def fixed(d, col, feats):
    tr, te = d[d["year"] <= 2019], d[d["year"] >= 2020]
    pr, _ = predict_year(tr, te, col, feats)
    return frame(te, col, pr)


def by_year(p):
    rows = []
    for y, g in p.groupby("year"):
        d0 = poisson_deviance(g["y"], recal(g, "M0")).sum()
        for mod in MODELS:
            if g[mod].isna().any():
                continue
            rows.append({"annee": int(y), "modele": mod, "observe": g["y"].sum(), "predit": g[mod].sum(),
                         "predit_sur_observe": g[mod].sum() / g["y"].sum(),
                         "gain_recale": 1 - poisson_deviance(g["y"], recal(g, mod)).sum() / d0})
    return pd.DataFrame(rows)


def figure(res):
    """Gain de déviance recalé, jeu principal, cible payés. Libellés en anglais : figure du rapport."""
    t = res[(res["cible"] == "payes") & (res["variables"] == MAIN_SET) & (res["modele"] != "M0")]
    lab = {"M1": "Poisson GLM,\nzone only", "M2": "Poisson GLM", "M3": "Negative\nbinomial GLM", "M4": "LightGBM"}
    col = {"validation 2016-2019": "#8a8984", "test 2020-2024": "#2a78d6"}
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#e6e5e1", "axes.axisbelow": True,
                         "figure.facecolor": "white"})
    fig, ax = plt.subplots(figsize=(7.5, 4), layout="constrained")
    x = np.arange(4)
    for i, (per, c) in enumerate(col.items()):
        v = t[t["periode"] == per].set_index("modele").loc[list(lab), "gain_recale"] * 100
        bars = ax.bar(x + (i - 0.5) * 0.38, v, 0.36, color=c, label=per.replace("validation", "Validation")
                      .replace("test", "Test").replace("-", " to "))
        ax.bar_label(bars, fmt="%+.1f", fontsize=8.5, padding=2)
    ax.axhline(0, color="#3d3d3a", lw=0.8)
    ax.set_xticks(x, list(lab.values()))
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Deviance gain over the null model (%)")
    ax.legend(frameon=False)
    fig.savefig(FIG / "glissant_gain.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    d, _ = prepare(load_ds())
    d = add_features(d)
    d["log_e"] = np.log(d["exposure_years"])
    d["n_hors_majeurs"] = d["n_claims"] - d["n_major"]
    rng = np.random.default_rng(SEED)
    pd.set_option("display.width", 200, "display.float_format", lambda v: f"{v:.3f}")

    print("0. Reproduction du premier jet (ajustement unique 2010-2019, test 2020-2024, jeu P)")
    rep0 = summarise(fixed(d, "n_claims", FEATURE_SETS["P"]), TEST_YEARS).reset_index(names="modele")
    rep0.to_csv(RES / "glissant_reproduction_premier_jet.csv", index=False)
    print(rep0.to_string(index=False))

    all_rows, ci_rows, year_rows, hp_rows, reg_rows = [], [], [], [], []
    for target, col in TARGETS.items():
        for name, feats in FEATURE_SETS.items():
            p, hp = rolling(d, col, feats)
            ident = {"cible": target, "variables": name}
            hp_rows.append(hp.assign(**ident))
            year_rows.append(by_year(p).assign(**ident))
            for per, years in {"validation 2016-2019": VALID_YEARS, "test 2020-2024": TEST_YEARS}.items():
                s = summarise(p, years).reset_index(names="modele").assign(**ident, periode=per)
                all_rows.append(s)
                # Floride contre les sept autres États (RQ2) ; recalage annuel à l'intérieur du groupe
                for reg, part in {"Floride": p[p["state"] == "FL"], "sept autres États": p[p["state"] != "FL"]}.items():
                    reg_rows.append(summarise(part, years).reset_index(names="modele")
                                    .assign(**ident, periode=per, region=reg))
                for a, b in [("M4", "M2"), ("M4", "M1"), ("M2", "M1")]:
                    pt, lo, hi = boot_counties(p, years, a, b, rng)
                    ci_rows.append({**ident, "periode": per, "ecart": f"{a} - {b}",
                                    "ecart_gain_recale": pt, "ic95_bas": lo, "ic95_haut": hi})
    first = ["cible", "variables", "periode", "modele"]
    res = pd.concat(all_rows, ignore_index=True)
    res = res[first + [c for c in res.columns if c not in first]]
    res.insert(2, "description_variables", res["variables"].map(SET_LABEL))
    ci = pd.DataFrame(ci_rows)
    res.to_csv(RES / "glissant_resultats.csv", index=False)
    ci.to_csv(RES / "glissant_intervalles.csv", index=False)
    pd.concat(year_rows, ignore_index=True).to_csv(RES / "glissant_par_annee.csv", index=False)
    pd.concat(hp_rows, ignore_index=True).to_csv(RES / "glissant_hyperparametres.csv", index=False)
    reg = pd.concat(reg_rows, ignore_index=True)
    reg[first[:3] + ["region", "modele"] + [c for c in reg.columns if c not in first + ["region"]]].to_csv(
        RES / "glissant_par_region.csv", index=False)
    figure(res)

    for target in TARGETS:
        for metric in ["gain_brut", "gain_recale", "gini", "predit_sur_observe"]:
            print(f"\nCible : {target} | {metric} (origine glissante)")
            t = res[res["cible"] == target].pivot_table(index=["variables", "modele"], columns="periode",
                                                        values=metric, sort=False, dropna=False)
            print(t[["validation 2016-2019", "test 2020-2024"]])
    print("\nIntervalles de confiance à 95 % (bootstrap des comtés), écart de gain recalé")
    print(ci.to_string(index=False))


if __name__ == "__main__":
    main()
