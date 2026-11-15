"""Outils des compléments (PROTOCOLE_COMPLEMENTAIRE.md). Réutilise Modeles/scripts/commun.py par import,
sans le modifier. Toutes les sorties vont dans Modeles/complements/."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))          # Modeles/scripts
from commun import (CLAIMS, FIT, MOD, ROOT, SEED, TARGETS, TEST, TRAIN, VALID, ZONES,  # noqa: E402,F401
                    glm_design, load_ds, md_table, poisson_deviance, prepare, zone_design)

COMP = MOD / "complements"
CRES, CFIG, CLOG = COMP / "resultats", COMP / "figures", COMP / "logs"
JET_RES = MOD / "resultats"                                   # résultats du premier jet (lecture seule)
TEST_YEARS = list(range(TEST[0], TEST[1] + 1))
LGB_BASE = {"objective": "poisson", "metric": "poisson", "verbose": -1, "seed": SEED, "deterministic": True,
            "num_threads": 1, "force_row_wise": True, "feature_pre_filter": False,
            "bagging_fraction": 1.0, "feature_fraction": 1.0}


def jet_info(code: str) -> dict:
    return json.loads((JET_RES / f"ajustement_{code}.json").read_text())


def m4_params(code: str):
    info = jet_info(code)
    return {**LGB_BASE, **info["M4_hyperparametres"]}, int(info["M4_iterations"])


def lgb_X(d: pd.DataFrame, feats: list) -> pd.DataFrame:
    X = d[feats].copy()
    if "zone" in X:
        X["zone"] = pd.Categorical(X["zone"], categories=ZONES)
    return X


def fit_lgb_predict(d: pd.DataFrame, col: str, feats: list, params: dict, n_iter: int):
    """LightGBM Poisson ajusté sur l'entraînement 2010-2019 ; offset de l'avenant n° 1 :
    init_score = log(e) + log(r_train) ; prédiction exp(raw + log(e) + log(r_train))."""
    import lightgbm as lgb
    tr = d[d["period"] == "train"]
    log_r = np.log(tr[col].sum() / tr["exposure_years"].sum())
    cat = ["zone"] if "zone" in feats else "auto"
    ds = lgb.Dataset(lgb_X(tr, feats), tr[col].to_numpy(float), init_score=tr["log_e"] + log_r,
                     categorical_feature=cat, free_raw_data=False)
    b = lgb.train(params, ds, n_iter)
    mu = np.exp(b.predict(lgb_X(d, feats), raw_score=True) + d["log_e"].to_numpy() + log_r)
    return mu, b, log_r


def rescale_by_year(t: pd.DataFrame, pred_col: str) -> pd.Series:
    """Recalage annuel (diagnostic, § 5.4 du premier jet) : utilise le total OBSERVÉ de chaque année."""
    return t[pred_col] * t.groupby("year")["observe"].transform("sum") / t.groupby("year")[pred_col].transform("sum")
