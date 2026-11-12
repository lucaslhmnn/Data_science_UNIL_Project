"""
Construit claims_model.parquet à partir de claims_clean.parquet en appliquant
les corrections issues de l'EDA (v1), orientées vers l'objectif du projet :
modèle en deux parties (P(paiement), puis montant | paiement), GLM vs gradient
boosting + SHAP, variables de l'ensemble A uniquement pour la prédiction.

Corrections appliquées
  1. Colinéarité parfaite : foundation_type == "non renseigné" <=> rating_system
     == "ancien (1)". foundation_type est retiré des variables du modèle
     (gardé seulement sous forme `foundation_rr2`, renseigné pour RR2.0, pour
     une analyse sur ce sous-échantillon).
  2. Valeurs impossibles -> NA : flood_duration = 999 (sentinelle),
     building_age > 150, buildingPropertyValue = 0.
  3. Manques non aléatoires (dépendants de l'époque) : indicatrices *_missing
     pour les variables de l'ensemble A, et catégorie explicite "inconnu" pour
     les catégorielles (au lieu de NA, qui disparaît dans un GLM).
  4. Effet d'époque : variable `era` (régimes de couverture/tarification).
  5. Plafond de couverture : `coverage_ratio` (payé / couverture) et `at_cap`.
  6. Événements extrêmes : conservés. Ajout de `event_group` (événement nommé,
     sinon mois du sinistre) pour une validation groupée, de `major_event`,
     et d'un découpage temporel `split` (train <= 2016, valid 2017-2020,
     test >= 2021) pour une évaluation sans fuite entre événements.
  7. Rôles explicites : listes FEATURES_A / FEATURES_B / TARGETS exportées
     dans un JSON à côté du parquet.

Non fait (fichier brut NfipClaimsV3_SE.parquet absent localement) : ajout de
elevationDifference, postFIRMConstructionIndicator, crsClassCode, latitude,
longitude (candidats ensemble A). Voir add_raw_columns() pour l'emplacement.

Lancer depuis la racine : python EDA/dsEDA.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Data_cleaning" / "clean" / "claims_clean.parquet"
RAW = ROOT / "Data_cleaning" / "NfipClaimsV3_SE.parquet"
OUT_DIR = ROOT / "EDA" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "claims_model.parquet"

TARGETS = ["paid_flag", "paid_building_real"]
FEATURES_A = ["building_coverage_real", "deductible_amount_real", "flood_zone_group",
              "elevated_building", "building_age", "n_floors", "primary_residence",
              "county_fips", "state", "loss_year",
              "building_age_missing", "deductible_missing", "primary_residence_missing"]
FEATURES_B = ["water_depth", "flood_duration"]          # ex post : jamais en prédiction
# rating_system et era : retirés des variables du modèle (voir § 8 de main()).
# Gardés comme contrôles pour les tests de robustesse et la stratification.
CONTROLS = ["building_value_real", "foundation_rr2", "rating_system", "era",
            "recent_claim", "paid_gt_cov", "paid_na_to_zero"]
RECENT_FROM = 2025          # sinistres dont les dossiers peuvent être encore ouverts
PRIMARY_RES_FROM = 2000     # avant : indicateur résidence principale non saisi (part ~0 %)
N_FOLDS = 5

RAW_COLS = ["elevationDifference", "postFIRMConstructionIndicator", "crsClassCode",
            "latitude", "longitude"]


def add_raw_columns(df, log):
    """Ajoute des candidats ensemble A depuis le fichier brut, s'il est présent."""
    if not RAW.exists():
        log.append(f"Fichier brut absent ({RAW.name}) : colonnes {RAW_COLS} non ajoutées.")
        return df
    raw = pd.read_parquet(RAW, columns=["id"] + RAW_COLS)
    df = df.merge(raw, on="id", how="left", validate="one_to_one")
    FEATURES_A.extend(RAW_COLS)
    log.append(f"Colonnes brutes ajoutées : {RAW_COLS}")
    return df


def main():
    log = []
    df = pd.read_parquet(SRC)
    n0 = len(df)
    log.append(f"Source : {SRC.name}, {n0:,} lignes, {df.shape[1]} colonnes")

    # 1. Colinéarité foundation_type / rating_system ------------------------
    unknown = df["foundation_type"].astype(str) == "non renseigné"
    ancien = df["rating_system"].astype(str) == "ancien (1)"
    identical = bool((unknown == ancien).all())
    log.append(f"foundation 'non renseigné' == rating 'ancien' sur toutes les lignes : {identical}")
    df["foundation_rr2"] = df["foundation_type"].astype("object").where(~unknown)
    df["foundation_rr2"] = df["foundation_rr2"].astype("category")
    df = df.drop(columns=["foundation_type"])

    # 2. Valeurs impossibles -> NA ------------------------------------------
    for col, mask, why in [
        ("flood_duration", df["flood_duration"] == 999, "sentinelle 999"),
        ("building_age", df["building_age"] > 150, "> 150 ans"),
        ("buildingPropertyValue", df["buildingPropertyValue"] == 0, "valeur nulle"),
        # 99 : valeur anormalement fréquente (5 761 lignes, 7e valeur la plus courante,
        # juste après 1 à 6) -> code de remplissage. L'unité reste mixte (pieds/pouces).
        ("water_depth", df["water_depth"] == 99, "code de remplissage 99"),
    ]:
        k = int(mask.fillna(False).sum())
        df.loc[mask.fillna(False), col] = pd.NA
        log.append(f"{col} : {k:,} valeurs mises à NA ({why})")

    # 2b. Valeur du bâtiment revalorisée (même facteur CPI que la couverture) --
    #     buildingPropertyValue est nominale : sa corrélation avec l'année (0,63)
    #     venait surtout de l'inflation.
    cov_nom = pd.to_numeric(df["building_coverage"], errors="coerce").where(lambda s: s > 0)
    factor = pd.to_numeric(df["building_coverage_real"], errors="coerce") / cov_nom
    factor = factor.fillna(factor.groupby(df["loss_month_period"]).transform("median"))
    df["building_value_real"] = (pd.to_numeric(df["buildingPropertyValue"], errors="coerce")
                                 * factor).astype("Float64")
    df = df.drop(columns=["buildingPropertyValue"])
    log.append("buildingPropertyValue -> building_value_real (revalorisée, $ d'octobre 2026)")

    # 2c. Résidence principale : non saisie avant 2000 -------------------------
    early = df["loss_year"].astype(int) < PRIMARY_RES_FROM
    share_early = df.loc[early, "primary_residence"].mean()
    df["primary_residence"] = df["primary_residence"].astype("boolean").mask(early)
    df["primary_residence_missing"] = df["primary_residence"].isna()
    log.append(f"primary_residence : NA avant {PRIMARY_RES_FROM} ({early.sum():,} lignes, "
               f"part 'oui' avant cette date {share_early:.0%} contre "
               f"{df.loc[~early, 'primary_residence'].mean():.0%} après)")

    # 2d. Signalements (lignes conservées) ---------------------------------------
    df["recent_claim"] = df["loss_year"].astype(int) >= RECENT_FROM
    p = pd.to_numeric(df["paid_building_real"], errors="coerce")
    c = pd.to_numeric(df["building_coverage_real"], errors="coerce")
    df["paid_gt_cov"] = (p > c * 1.01).fillna(False)
    incoh = df["paid_flag"].astype(bool) & p.isna()
    log.append(f"recent_claim (>= {RECENT_FROM}, dossiers possiblement ouverts) : "
               f"{df['recent_claim'].sum():,} lignes")
    log.append(f"paid_gt_cov (payé > couverture) : {df['paid_gt_cov'].sum():,} lignes ; "
               f"payé sans montant : {incoh.sum():,} lignes")

    # 3. Manques -> indicatrices et catégorie "inconnu" ---------------------
    df["building_age_missing"] = df["building_age"].isna()
    df["deductible_missing"] = df["deductible_amount_real"].isna()
    for c in ["flood_zone_group", "n_floors", "county_fips"]:
        k = int(df[c].isna().sum())
        df[c] = df[c].cat.add_categories("inconnu").fillna("inconnu")
        log.append(f"{c} : {k:,} NA -> catégorie 'inconnu'")
    # D et 'autre' : effectifs minuscules (769 et 3) -> regroupés
    df["flood_zone_group"] = df["flood_zone_group"].astype(str).replace(
        {"autre": "inconnu"}).astype("category")

    # 4. Époque ---------------------------------------------------------------
    bins = [1977, 1993, 2004, 2012, 2020, 2100]
    labels = ["1978-1993", "1994-2004", "2005-2012", "2013-2020", "2021+"]
    df["era"] = pd.cut(df["loss_year"].astype(int), bins=bins, labels=labels)

    # 5. Plafond ---------------------------------------------------------------
    paid = pd.to_numeric(df["paid_building_real"], errors="coerce")
    cov = pd.to_numeric(df["building_coverage_real"], errors="coerce").where(lambda s: s > 0)
    df["coverage_ratio"] = (paid / cov).astype("Float64")
    df["at_cap"] = (df["coverage_ratio"] >= 0.99).astype("boolean")
    df.loc[paid.isna(), "at_cap"] = pd.NA

    # 6. Événements, découpage ------------------------------------------------
    ev = df["floodEvent"].astype("object")
    ev = ev.where(ev.notna() & (ev.astype(str).str.lower() != "flooding"))
    df["event_group"] = ev.fillna("mois " + df["loss_month_period"].astype(str)).astype("category")
    top3 = df["floodEvent"].astype("object").dropna()
    top3 = top3[top3.str.lower() != "flooding"].value_counts().head(3).index
    df["major_event"] = df["floodEvent"].astype("object").isin(top3)
    log.append(f"major_event = {list(top3)} ({df['major_event'].mean():.1%} des lignes)")
    yr = df["loss_year"].astype(int)
    df["split"] = pd.Categorical(np.select([yr <= 2016, yr <= 2020], ["train", "valid"], "test"),
                                 categories=["train", "valid", "test"])

    # 7. Validation principale : plis groupés par événement --------------------
    # Tous les sinistres d'un même event_group tombent dans le même pli : pas de
    # fuite entre apprentissage et test au sein d'un ouragan. Affectation
    # gloutonne (groupes du plus gros au plus petit, vers le pli le moins rempli)
    # pour des plis de taille comparable malgré Helene/Katrina/Ian.
    sizes = df["event_group"].value_counts()
    fill = np.zeros(N_FOLDS)
    fold_of = {}
    for g, n in sizes.items():
        k = int(fill.argmin())
        fold_of[g] = k
        fill[k] += n
    df["fold"] = df["event_group"].map(fold_of).astype("int8")
    log.append("Plis groupés par événement : " + ", ".join(
        f"{k}: {int(n):,}" for k, n in enumerate(fill)))

    # 8. rating_system : diagnostic puis retrait des variables du modèle -------
    # À année égale, RR2.0 ne relève le taux de paiement que de quelques points ;
    # l'écart brut (81 % vs 69 %) est surtout un effet d'époque. La variable code
    # le format de l'enregistrement, pas un risque connu à la souscription ; elle
    # est colinéaire avec foundation_type (parfaitement) et avec l'époque, et
    # quasi constante dans le train du découpage temporel. Idem pour `era`, dont
    # le niveau 2021+ est absent du train. L'effet temporel passe par loss_year.
    yr_rs = (df.groupby([df["loss_year"].astype(int), "rating_system"], observed=True)
               ["paid_flag"].mean().unstack())
    both = yr_rs.dropna()
    gap = (both.iloc[:, 1] - both.iloc[:, 0]) if both.shape[1] == 2 else pd.Series(dtype=float)
    log.append(f"rating_system : écart brut de taux de paiement "
               f"{df.groupby('rating_system', observed=True)['paid_flag'].mean().diff().iloc[-1]:+.1%}, "
               f"écart moyen à année égale ({len(both)} années communes) {gap.mean():+.1%}")
    rr2_train = (df.loc[df["split"] == "train", "rating_system"].astype(str) != "ancien (1)").mean()
    log.append(f"rating_system : part RR2.0 dans le train temporel {rr2_train:.1%} "
               "-> retiré des variables du modèle (gardé en contrôle)")

    df = add_raw_columns(df, log)

    # Contrôles finaux --------------------------------------------------------
    assert len(df) == n0, "le nombre de lignes a changé"
    assert df["id"].is_unique
    for c in FEATURES_A + FEATURES_B + TARGETS + CONTROLS:
        assert c in df.columns, c

    df.to_parquet(OUT, index=False)
    roles = {"targets": TARGETS, "features_A": FEATURES_A, "features_B": FEATURES_B,
             "controls": CONTROLS,
             "validation": {"principale": "fold (5 plis groupés par event_group)",
                            "robustesse": "split (train <= 2016, valid 2017-2020, test >= 2021)"},
             "grouping": ["event_group", "fold", "split", "major_event"]}
    (OUT_DIR / "claims_model_roles.json").write_text(json.dumps(roles, indent=2, ensure_ascii=False))
    split_tab = df.groupby("split", observed=True).agg(n=("id", "size"),
                                                       paid_rate=("paid_flag", "mean"))
    log.append("Découpage :\n" + split_tab.to_string())

    print("\n".join(log))
    print(f"\n-> {OUT.relative_to(ROOT)} ({len(df):,} lignes, {df.shape[1]} colonnes)")


if __name__ == "__main__":
    main()
