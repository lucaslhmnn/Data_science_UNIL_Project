"""Constantes et fonctions partagées par les scripts de Modeles/ (voir PROTOCOLE.md)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]          # racine du dépôt
MOD = ROOT / "Modeles"
RES, FIG, LOG = MOD / "resultats", MOD / "figures", MOD / "logs"

DS = ROOT / "EDA" / "ds_clean.csv"
ROLES = ROOT / "EDA" / "ds_clean_roles.json"
BUILD = ROOT / "EDA" / "build_ds_clean.py"
KEYNUM = ROOT / "EDA" / "figures" / "eda_key_numbers.json"
CLAIMS = ROOT / "Data_cleaning" / "clean" / "claims_clean.parquet"

SEED = 42
TRAIN, TEST = (2010, 2019), (2020, 2024)
FIT, VALID = (2010, 2017), (2018, 2019)               # validation interne de LightGBM
FEATURES = ["zone", "mean_coverage", "hist_per_1000", "county_hist_per_1000"]
TARGETS = {"payes": "n_claims", "tous": "n_all"}       # n_all : vérifié en V4
ZONES = ["V*", "A*", "X"]
ZONE_REF = "X"                                          # modalité de référence des GLM


def load_ds() -> pd.DataFrame:
    return pd.read_csv(DS, dtype={"county_id": str, "zone": str, "state": str})


def load_roles() -> dict:
    return json.loads(ROLES.read_text())


def prepare(ds: pd.DataFrame):
    """Lignes modélisables (PROTOCOLE § 3) : exposition > 0 et variables explicatives renseignées."""
    expo_ok = np.isfinite(ds["exposure_years"]) & (ds["exposure_years"] > 0)
    feat_ok = ds[FEATURES].notna().all(axis=1)
    keep = expo_ok & feat_ok
    info = {"lignes_total": len(ds), "exposition_nulle_ou_invalide": int((~expo_ok).sum()),
            "variable_manquante": int((expo_ok & ~feat_ok).sum()), "lignes_gardees": int(keep.sum()),
            "sinistres_payes_exclus": int(ds.loc[~keep, "n_claims"].sum()),
            "sinistres_tous_exclus": int(ds.loc[~keep, "n_all"].sum()),
            "exposition_exclue": float(ds.loc[~keep, "exposure_years"].sum())}
    d = ds[keep].copy().reset_index(drop=True)
    d["period"] = np.where(d["year"] <= TRAIN[1], "train", "test")
    d["log_e"] = np.log(d["exposure_years"])
    return d, info


def glm_design(d: pd.DataFrame) -> pd.DataFrame:
    """Matrice des GLM M2/M3 : constante, indicatrices de zone (réf. X), couverture en k$ nominaux,
    log1p des deux historiques (PROTOCOLE § 3)."""
    X = pd.DataFrame({"const": 1.0}, index=d.index)
    for z in ZONES:
        if z != ZONE_REF:
            X[f"zone_{z}"] = (d["zone"] == z).astype(float)
    X["couverture_k$"] = d["mean_coverage"] / 1000.0
    X["log1p_hist_per_1000"] = np.log1p(d["hist_per_1000"])
    X["log1p_county_hist_per_1000"] = np.log1p(d["county_hist_per_1000"])
    return X


def zone_design(d: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame({"const": 1.0}, index=d.index)
    for z in ZONES:
        if z != ZONE_REF:
            X[f"zone_{z}"] = (d["zone"] == z).astype(float)
    return X


def lgb_matrix(d: pd.DataFrame) -> pd.DataFrame:
    """Variables brutes de LightGBM ; zone en catégorielle (codes fixes)."""
    X = d[FEATURES].copy()
    X["zone"] = pd.Categorical(X["zone"], categories=ZONES)
    return X


def poisson_deviance(y, mu) -> np.ndarray:
    """Déviance de Poisson par observation : 2 [y log(y/mu) - (y - mu)], avec 0 log 0 = 0."""
    y = np.asarray(y, float)
    mu = np.asarray(mu, float)
    term = np.where(y > 0, y * np.log(np.where(y > 0, y, 1.0) / mu), 0.0)
    return 2.0 * (term - (y - mu))


def md_table(df: pd.DataFrame, floatfmt: str = "{:,.4g}") -> str:
    def f(v):
        if isinstance(v, (float, np.floating)):
            return "NA" if np.isnan(v) else floatfmt.format(v).replace(",", " ")
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}".replace(",", " ")
        return str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = ["| " + " | ".join(f(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])
