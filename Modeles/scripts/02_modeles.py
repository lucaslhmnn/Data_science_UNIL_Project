"""Phase 2 : ajustement des modèles M0, M1, M_oracle, M2, M3, M4 pour chaque cible (PROTOCOLE.md et
avenant n° 1). Écrit les prédictions de toutes les lignes et les éléments d'ajustement dans
Modeles/resultats/. Aucun réglage sur le test."""
import itertools
import json
import sys
import time
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import NegativeBinomial

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import (FIT, RES, SEED, TARGETS, TRAIN, VALID, ZONES, glm_design, lgb_matrix, load_ds,  # noqa: E402
                    poisson_deviance, prepare, zone_design)

np.random.seed(SEED)
LGB_BASE = {"objective": "poisson", "metric": "poisson", "verbose": -1, "seed": SEED, "deterministic": True,
            "num_threads": 1, "force_row_wise": True, "feature_pre_filter": False,
            "bagging_fraction": 1.0, "feature_fraction": 1.0}
GRID = {"learning_rate": [0.02, 0.05], "num_leaves": [7, 15], "min_data_in_leaf": [100, 300],
        "lambda_l2": [1.0, 10.0]}
MAX_ROUNDS, PATIENCE = 3000, 100


def coef_table(res_model, res_hc0, res_cl, names):
    p = np.asarray(res_model.params)
    expo = np.where(np.asarray(names) == "alpha", np.nan, np.exp(p))   # exp(alpha) n'a pas de sens
    return pd.DataFrame({"variable": names, "coefficient": p, "exp_coefficient": expo,
                         "es_modele": np.asarray(res_model.bse), "es_robuste_HC0": np.asarray(res_hc0.bse),
                         "es_grappes_annee": np.asarray(res_cl.bse)})


def fit_lgb(Xf, yf, initf, Xv, yv, initv, params, rounds=None):
    dtr = lgb.Dataset(Xf, yf, init_score=initf, categorical_feature=["zone"], free_raw_data=False)
    if rounds is not None:
        return lgb.train(params, dtr, rounds)
    dva = lgb.Dataset(Xv, yv, init_score=initv, categorical_feature=["zone"], reference=dtr)
    return lgb.train(params, dtr, MAX_ROUNDS, valid_sets=[dva], valid_names=["validation"],
                     callbacks=[lgb.early_stopping(PATIENCE, verbose=False)])


def run_target(code, col, d):
    t0 = time.time()
    tr, te = d[d["period"] == "train"], d[d["period"] == "test"]
    y_tr = tr[col].to_numpy(float)
    out = d[["county_id", "zone", "year", "state", "period", "exposure_years"]].copy()
    out["observe"] = d[col].to_numpy(float)
    info = {"cible": code, "colonne": col, "lignes_train": len(tr), "lignes_test": len(te),
            "sinistres_train": int(y_tr.sum()), "sinistres_test": int(te[col].sum())}

    # M0 : taux moyen d'entraînement
    rate = y_tr.sum() / tr["exposure_years"].sum()
    out["M0"] = rate * d["exposure_years"]
    info["M0_taux_pour_1000"] = 1000 * rate

    # M1 : GLM Poisson, zone seule
    m1 = sm.GLM(y_tr, zone_design(tr), family=sm.families.Poisson(), offset=tr["log_e"]).fit()
    out["M1"] = m1.predict(zone_design(d), offset=d["log_e"])
    info["M1_converge"] = bool(m1.converged)

    # M_oracle : zone + facteur année, ajusté sur chaque période elle-même (non prédictif)
    def oracle_fit(part):
        X = zone_design(part).join(pd.get_dummies(part["year"], prefix="annee", drop_first=True, dtype=float))
        r = sm.GLM(part[col].to_numpy(float), X, family=sm.families.Poisson(), offset=part["log_e"]).fit()
        return r.fittedvalues, bool(r.converged)
    fv_tr, c1 = oracle_fit(tr)
    fv_te, c2 = oracle_fit(te)
    out["M_oracle"] = pd.concat([fv_tr, fv_te]).reindex(d.index)
    info["M_oracle_converge"] = c1 and c2

    # M2 : GLM Poisson principal
    Xtr, Xall = glm_design(tr), glm_design(d)
    glm = sm.GLM(y_tr, Xtr, family=sm.families.Poisson(), offset=tr["log_e"])
    m2 = glm.fit()
    m2_hc0 = glm.fit(cov_type="HC0")
    m2_cl = glm.fit(cov_type="cluster", cov_kwds={"groups": tr["year"].to_numpy()})
    out["M2"] = m2.predict(Xall, offset=d["log_e"])
    pearson = float(np.sum(m2.resid_pearson ** 2))
    info.update({"M2_converge": bool(m2.converged), "M2_pearson_chi2": pearson, "M2_ddl_residus": float(m2.df_resid),
                 "M2_dispersion_pearson": pearson / float(m2.df_resid), "M2_AIC_train": float(m2.aic),
                 "M2_loglik_train": float(m2.llf)})
    coefs = [coef_table(m2, m2_hc0, m2_cl, list(Xtr.columns)).assign(modele="M2")]

    # M3 : binomial négatif NB2, alpha par maximum de vraisemblance
    # Valeurs de départ explicites : coefficients de M2 et alpha = 1. Les valeurs par défaut de statsmodels
    # mènent à des paramètres NaN tout en signalant « converged » (constaté le 15/11/2026, voir rapport).
    nb = NegativeBinomial(y_tr, Xtr, loglike_method="nb2", exposure=tr["exposure_years"].to_numpy())
    start = np.r_[np.asarray(m2.params), 1.0]
    fits = {}
    for method in ["newton", "bfgs"]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = nb.fit(start_params=start, method=method, maxiter=5000, disp=0)
        if r.mle_retvals.get("converged", False) and np.isfinite(r.params).all() and np.isfinite(r.llf):
            fits[method] = r
    m3 = fits.get("newton") or fits.get("bfgs")
    if m3 is not None:
        info["M3_methode"] = "newton" if "newton" in fits else "bfgs"
        if len(fits) == 2:
            info["M3_ecart_loglik_newton_bfgs"] = float(abs(fits["newton"].llf - fits["bfgs"].llf))
    if m3 is None:
        info["M3_echec"] = "non-convergence ou paramètres non finis (newton et bfgs)"
        out["M3"] = np.nan
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m3_hc0 = nb.fit(start_params=m3.params, method=info["M3_methode"], maxiter=5000, disp=0, cov_type="HC0")
            m3_cl = nb.fit(start_params=m3.params, method=info["M3_methode"], maxiter=5000, disp=0,
                           cov_type="cluster", cov_kwds={"groups": tr["year"].to_numpy()})
        out["M3"] = m3.predict(Xall, exposure=d["exposure_years"].to_numpy())
        info.update({"M3_converge": True, "M3_alpha": float(m3.params.iloc[-1]), "M3_AIC_train": float(m3.aic),
                     "M3_loglik_train": float(m3.llf)})
        coefs.append(coef_table(m3, m3_hc0, m3_cl, list(Xtr.columns) + ["alpha"]).assign(modele="M3"))
    pd.concat(coefs).to_csv(RES / f"coefficients_{code}.csv", index=False)

    # M4 : LightGBM Poisson ; réglage 2010-2017 -> validation 2018-2019 ; avenant n° 1 pour l'offset
    fit_part = tr[tr["year"].between(*FIT)]
    val_part = tr[tr["year"].between(*VALID)]
    r_fit = fit_part[col].sum() / fit_part["exposure_years"].sum()
    rows = []
    for lr, nl, mdl, l2 in itertools.product(*GRID.values()):
        params = {**LGB_BASE, "learning_rate": lr, "num_leaves": nl, "min_data_in_leaf": mdl, "lambda_l2": l2}
        b = fit_lgb(lgb_matrix(fit_part), fit_part[col].to_numpy(float), fit_part["log_e"] + np.log(r_fit),
                    lgb_matrix(val_part), val_part[col].to_numpy(float), val_part["log_e"] + np.log(r_fit), params)
        mu_v = np.exp(b.predict(lgb_matrix(val_part), raw_score=True, num_iteration=b.best_iteration)
                      + val_part["log_e"] + np.log(r_fit))
        rows.append({"learning_rate": lr, "num_leaves": nl, "min_data_in_leaf": mdl, "lambda_l2": l2,
                     "meilleure_iteration": b.best_iteration,
                     "poisson_nll_validation": b.best_score["validation"]["poisson"],
                     "deviance_validation": float(poisson_deviance(val_part[col], mu_v).sum())})
    grid = pd.DataFrame(rows).sort_values("deviance_validation").reset_index(drop=True)
    grid.to_csv(RES / f"lgb_grille_{code}.csv", index=False)
    best = grid.iloc[0]
    params = {**LGB_BASE, "learning_rate": float(best.learning_rate), "num_leaves": int(best.num_leaves),
              "min_data_in_leaf": int(best.min_data_in_leaf), "lambda_l2": float(best.lambda_l2)}
    n_iter = int(best.meilleure_iteration)
    r_tr = rate
    m4 = fit_lgb(lgb_matrix(tr), y_tr, tr["log_e"] + np.log(r_tr), None, None, None, params, rounds=n_iter)
    m4.save_model(str(RES / f"m4_{code}.txt"))
    out["M4"] = np.exp(m4.predict(lgb_matrix(d), raw_score=True) + d["log_e"] + np.log(r_tr))
    nonreg = out.loc[out["period"] == "train", "M4"].sum() / y_tr.sum()
    info.update({"M4_hyperparametres": {k: params[k] for k in GRID}, "M4_iterations": n_iter,
                 "M4_iteration_max_atteinte": n_iter >= MAX_ROUNDS, "M4_log_taux_init": float(np.log(r_tr)),
                 "M4_nonregression_ratio_train": float(nonreg), "M4_nonregression_ok": bool(abs(nonreg - 1) < 0.01)})
    imp = pd.DataFrame({"variable": m4.feature_name(), "gain": m4.feature_importance("gain"),
                        "nb_coupures": m4.feature_importance("split")})
    imp["part_gain"] = imp["gain"] / imp["gain"].sum()
    imp.to_csv(RES / f"importance_gain_{code}.csv", index=False)

    out.to_csv(RES / f"predictions_{code}.csv", index=False)
    info["duree_s"] = round(time.time() - t0, 1)
    (RES / f"ajustement_{code}.json").write_text(json.dumps(info, indent=1, ensure_ascii=False))
    print(json.dumps(info, indent=1, ensure_ascii=False))
    return info


def main():
    d, prep = prepare(load_ds())
    print("Préparation :", prep)
    (RES / "preparation.json").write_text(json.dumps(prep, indent=1, ensure_ascii=False))
    assert set(d["zone"]) <= set(ZONES) and d["year"].between(TRAIN[0], 2024).all()
    for code, col in TARGETS.items():
        print(f"\n===== Cible « {code} » ({col}) =====")
        run_target(code, col, d)


if __name__ == "__main__":
    main()
