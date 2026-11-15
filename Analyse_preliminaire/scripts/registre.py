"""Registre unique des chiffres et des résultats de l'analyse préliminaire (v0.1, 15/11/2026).

CHIFFRES : chaque clé est reliée à une cellule précise d'un fichier EXISTANT (CSV, JSON ou tableau Markdown).
Aucun chiffre n'est recalculé à partir des modèles ; seules quelques agrégations simples (rapport de deux
cellules, min/max) sont faites et décrites dans « derive ».
RESULTATS : registre R1..Rn (énoncé, clés, statut, condition pour changer de statut), repris dans
STATUT_RESULTATS.md et marqué dans section_modelisation.qmd par des commentaires <!-- Rk -->.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AP = ROOT / "Analyse_preliminaire"
M = "Modeles/resultats"
C = "Modeles/complements/resultats"
CLEAN_REPORT = "Data_cleaning/clean/cleaning_report.md"

# Étiquettes (français dans les fichiers du dossier, anglais dans la section du rapport, CLAUDE.md : English only)
STATUTS = {"E": ("[Établi]", "[Established]"),
           "P": ("[Provisoire, exploratoire]", "[Provisional, exploratory]"),
           "N": ("[Non démontré]", "[Not demonstrated]")}


# ----------------------------------------------------------------------------- lecteurs de sources
def _num(s: str) -> float:
    return float(s.replace(" ", "").replace(" ", "").replace(",", "."))


def read_csv(path, sel, col):
    df = pd.read_csv(ROOT / path, dtype={"annee": str, "year": str})
    for k, v in sel.items():
        df = df[df[k].astype(str) == str(v)]
    assert len(df) == 1, f"{path} {sel} -> {len(df)} lignes"
    return float(df[col].iloc[0])


def read_json(path, keys):
    v = json.loads((ROOT / path).read_text())
    for k in keys:
        v = v[k]
    return float(v)


def read_md_row(path, label, after=None, col=1):
    """Valeur de la colonne `col` de la première ligne de tableau Markdown dont la 1re cellule vaut `label`,
    en ne cherchant qu'après la ligne contenant `after` (si fourni)."""
    lines = (ROOT / path).read_text().splitlines()
    start = 0
    if after:
        start = next(i for i, ln in enumerate(lines) if after in ln)
    for ln in lines[start:]:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if ln.startswith("|") and cells and cells[0] == label:
            return _num(cells[col])
    raise KeyError(f"{path}: ligne « {label} » introuvable")


# ----------------------------------------------------------------------------- formats
def fmt(v, kind):
    return {"int": lambda: f"{v:,.0f}", "sint": lambda: f"{v:+,.0f}",
            "f1": lambda: f"{v:.1f}", "f2": lambda: f"{v:.2f}", "f3": lambda: f"{v:.3f}", "f4": lambda: f"{v:.4f}",
            "pct0": lambda: f"{100 * v:.0f}%", "pct1": lambda: f"{100 * v:.1f}%",
            "spct1": lambda: f"{100 * v:+.1f}%", "x2": lambda: f"x{v:.2f}", "sci1": lambda: f"{v:.1e}",
            "mio1": lambda: f"{v / 1e6:.1f} million", "r0": lambda: f"{v:.0f}"}[kind]()


# ----------------------------------------------------------------------------- chiffres
def dev(cible, modele, ens):
    return ("csv", f"{M}/deviance_par_modele.csv", {"cible": cible, "modele": modele, "ensemble": ens}, "gain_relatif_vs_M0")


def recal(cible, modele):
    return ("csv", f"{M}/diagnostic_deviance_recalee_par_annee.csv", {"cible": cible, "modele": modele}, "gain_vs_M0_recalee")


def abl(cible, modele, ens):
    return ("csv", f"{C}/ablation_deviance.csv", {"cible": cible, "modele": modele, "ensemble": ens}, "gain_vs_M0")


def ratio_tot(cible, modele):
    return ("csv", f"{M}/calibration_totale_par_periode.csv", {"cible": cible, "period": "test", "modele": modele},
            "ratio_predit_observe")


def ratio_year(cible, modele, annee):
    return ("csv", f"{M}/par_annee_calibration_deviance.csv", {"cible": cible, "modele": modele, "annee": annee},
            "ratio_predit_observe")


CHIFFRES = {
    # Données et nettoyage (cleaning_report.md)
    "raw_claims": (("md", CLEAN_REPORT, "Fichier brut", None), "int"),
    "single_family": (("md", CLEAN_REPORT, "occupancyType ∈ [1, 11]", None), "int"),
    "anomalies": (("md", CLEAN_REPORT, "Lignes écartées (anomalies)", None), "int"),
    "clean_claims": (("md", CLEAN_REPORT, "**claims_clean.parquet**", None), "int"),
    "anom_neg_age": (("md", CLEAN_REPORT, "âge négatif", "| motif | lignes |"), "int"),
    "anom_duplicate": (("md", CLEAN_REPORT, "doublon exact", "| motif | lignes |"), "int"),
    "anom_paid_nocov": (("md", CLEAN_REPORT, "paiement sans couverture", "| motif | lignes |"), "int"),
    "anom_neg_paid": (("md", CLEAN_REPORT, "paiement négatif", "| motif | lignes |"), "int"),
    "anom_two_reasons": (("md", CLEAN_REPORT, "âge négatif; paiement sans couverture", "Combinaisons de motifs"), "int"),
    # Table d'analyse
    "ds_rows": (("json", "EDA/ds_clean_roles.json", ["rows"]), "int"),
    "ds_counties": (("json", "EDA/ds_clean_roles.json", ["counties"]), "int"),
    "policy_years": (("json", "EDA/figures/eda_key_numbers.json", ["policy_years"]), "mio1"),
    "rows_used": (("json", f"{M}/preparation.json", ["lignes_gardees"]), "int"),
    "rows_excluded": (("json", f"{M}/preparation.json", ["variable_manquante"]), "int"),
    "rows_train": (("json", f"{M}/ajustement_payes.json", ["lignes_train"]), "int"),
    "rows_test": (("json", f"{M}/ajustement_payes.json", ["lignes_test"]), "int"),
    "claims_train_paid": (("json", f"{M}/ajustement_payes.json", ["sinistres_train"]), "int"),
    "claims_test_paid": (("json", f"{M}/ajustement_payes.json", ["sinistres_test"]), "int"),
    "claims_train_all": (("json", f"{M}/ajustement_tous.json", ["sinistres_train"]), "int"),
    "claims_test_all": (("json", f"{M}/ajustement_tous.json", ["sinistres_test"]), "int"),
    "freq_train": (("json", "EDA/figures/eda_key_numbers.json", ["freq_train"]), "f2"),
    "freq_test": (("json", "EDA/figures/eda_key_numbers.json", ["freq_test"]), "f2"),
    "share_2024_test": (("derive", "share_2024"), "pct1"),
    "excl13_dev_effect": (("derive", "vc4_max"), "sci1"),
    # Ajustement et contrôles techniques
    "m2_pearson_disp": (("json", f"{M}/ajustement_payes.json", ["M2_dispersion_pearson"]), "f1"),
    "m2_aic": (("json", f"{M}/ajustement_payes.json", ["M2_AIC_train"]), "int"),
    "m3_aic": (("json", f"{M}/ajustement_payes.json", ["M3_AIC_train"]), "int"),
    "m3_alpha": (("json", f"{M}/ajustement_payes.json", ["M3_alpha"]), "f2"),
    "m3_train_ratio": (("csv", f"{M}/calibration_totale_par_periode.csv", {"cible": "payes", "period": "train", "modele": "M3"}, "ratio_predit_observe"), "f2"),
    "nb_const_ratio": (("csv", f"{C}/vc2_binomial_negatif.csv", {"cible": "payes"}, "ratio_somme_mu_somme_y_constante_seule"), "f2"),
    "vc2_coef_diff": (("csv", f"{C}/vc2_binomial_negatif.csv", {"cible": "payes"}, "ecart_max_coef_GLM_vs_M3"), "sci1"),
    "vc1_metric_diff": (("csv", f"{C}/vc1_synthese.csv", {"cible": "payes"}, "ecart_max_metrique_lgb_vs_main"), "sci1"),
    "m4_iters": (("json", f"{M}/ajustement_payes.json", ["M4_iterations"]), "int"),
    "m4_nonreg": (("json", f"{M}/ajustement_payes.json", ["M4_nonregression_ratio_train"]), "f4"),
    "se_ratio_vzone": (("derive", "se_ratio"), "r0"),
    "boot_distinct": (("csv", f"{M}/bootstrap_annees_test.csv", {"cible": "payes", "difference": "M4 - M2"}, "nb_tirages_distincts"), "int"),
    # Gains de déviance (premier jet)
    **{f"gain_test_{m}_{c}": (dev(c, m, "test 2020-2024"), "spct1") for m in ["M1", "M2", "M3", "M4", "M_oracle"] for c in ["payes", "tous"]},
    **{f"gain_recal_{m}_{c}": (recal(c, m), "spct1") for m in ["M1", "M2", "M3", "M4"] for c in ["payes", "tous"]},
    "zone_share_m4": (("derive", "zone_share_m4"), "pct0"),
    "zone_share_l2": (("derive", "zone_share_l2"), "pct0"),
    # Calibration
    **{f"ratio_test_{m}": (ratio_tot("payes", m), "f2") for m in ["M0", "M2", "M3", "M4"]},
    "ratio_2021_M4": (ratio_year("payes", "M4", "2021"), "f2"),
    "ratio_2022_M4": (ratio_year("payes", "M4", "2022"), "f2"),
    "ratio_2024_M4": (ratio_year("payes", "M4", "2024"), "f2"),
    # Ablation (compléments)
    **{f"abl_{m}_{e}": (abl("payes", m, ens), "spct1") for m in ["G1", "G3", "G5_hp", "L1", "L2", "L3", "L5", "L6"]
       for e, ens in [("raw", "test"), ("rec", "test_recale")]},
    "abl_L5_train": (abl("payes", "L5", "train"), "spct1"),
    "abl_M1_train": (abl("payes", "M1", "train"), "spct1"),
    # Déplacement des taux par zone (descriptif)
    **{f"mult_{k}": (("csv", f"{C}/vc3_multiplicateur_zone.csv", {"zone": z}, "multiplicateur_payes"), "x2")
       for k, z in [("A", "A*"), ("V", "V*"), ("X", "X")]},
    "x_claims_share_2021": (("csv", f"{C}/vc3_zone_annee.csv", {"year": "2021", "zone": "X"}, "part_payes"), "pct1"),
    "x_claims_share_2022": (("csv", f"{C}/vc3_zone_annee.csv", {"year": "2022", "zone": "X"}, "part_payes"), "pct1"),
    "x_expo_share_min": (("derive", "x_expo_min"), "pct1"),
    "x_expo_share_max": (("derive", "x_expo_max"), "pct1"),
    # Couverture : tranche haute (descriptif hors protocole) et répartition du test
    "t5_expo_train": (("csv", f"{C}/hp_taux_par_tranche_couverture.csv", {"cible": "payes", "period": "train", "tranche": "T5"}, "part_exposition_periode"), "pct1"),
    "t5_expo_test": (("csv", f"{C}/hp_taux_par_tranche_couverture.csv", {"cible": "payes", "period": "test", "tranche": "T5"}, "part_exposition_periode"), "pct1"),
    "t5_rate_train": (("csv", f"{C}/hp_taux_par_tranche_couverture.csv", {"cible": "payes", "period": "train", "tranche": "T5"}, "taux_observe_1000"), "f2"),
    "t5_rate_test": (("csv", f"{C}/hp_taux_par_tranche_couverture.csv", {"cible": "payes", "period": "test", "tranche": "T5"}, "taux_observe_1000"), "f2"),
    "t5_rows_test": (("json", f"{C}/ablation_variables_construites.json", ["repartition_tranches", "test", "T5"]), "pct1"),
    # Variables
    "perm_zone": (("csv", f"{M}/importance_permutation_test_m4.csv", {"cible": "payes", "variable": "zone"}, "hausse_deviance_test_moyenne"), "sint"),
    "perm_cov": (("csv", f"{M}/importance_permutation_test_m4.csv", {"cible": "payes", "variable": "mean_coverage"}, "hausse_deviance_test_moyenne"), "sint"),
    "perm_chist": (("csv", f"{M}/importance_permutation_test_m4.csv", {"cible": "payes", "variable": "county_hist_per_1000"}, "hausse_deviance_test_moyenne"), "sint"),
    "gain_share_chist": (("csv", f"{M}/importance_gain_payes.csv", {"variable": "county_hist_per_1000"}, "part_gain"), "pct0"),
}

DERIVES = {
    "share_2024": "observé 2024 / somme des observés 2020-2024 (payés, modèle M0) dans par_annee_calibration_deviance.csv",
    "vc4_max": "maximum de |ecart_relatif| dans vc4_lignes_exclues.csv",
    "se_ratio": "es_robuste_HC0 / es_modele de zone_V* (M2, payés) dans coefficients_payes.csv",
    "zone_share_m4": "gain recalé de M1 / gain recalé de M4 (payés), diagnostic_deviance_recalee_par_annee.csv",
    "zone_share_l2": "gain recalé de M1 / gain recalé de L2 (payés), ablation_deviance.csv (test_recale)",
    "x_expo_min": "minimum de part_exposition de la zone X sur 2018-2024 dans vc3_zone_annee.csv",
    "x_expo_max": "maximum de part_exposition de la zone X sur 2018-2024 dans vc3_zone_annee.csv",
}


def derive(name):
    if name == "share_2024":
        df = pd.read_csv(ROOT / f"{M}/par_annee_calibration_deviance.csv")
        t = df[(df.cible == "payes") & (df.modele == "M0") & (df.periode == "test")]
        return float(t.loc[t.annee == 2024, "observe"].iloc[0] / t["observe"].sum())
    if name == "vc4_max":
        return float(pd.read_csv(ROOT / f"{C}/vc4_lignes_exclues.csv")["ecart_relatif"].abs().max())
    if name == "se_ratio":
        df = pd.read_csv(ROOT / f"{M}/coefficients_payes.csv")
        r = df[(df.modele == "M2") & (df.variable == "zone_V*")].iloc[0]
        return float(r.es_robuste_HC0 / r.es_modele)
    if name == "zone_share_m4":
        return read_csv(*recal("payes", "M1")[1:]) / read_csv(*recal("payes", "M4")[1:])
    if name == "zone_share_l2":
        return read_csv(*recal("payes", "M1")[1:]) / read_csv(*abl("payes", "L2", "test_recale")[1:])
    if name in ("x_expo_min", "x_expo_max"):
        df = pd.read_csv(ROOT / f"{C}/vc3_zone_annee.csv")
        s = df[(df.zone == "X") & df.year.between(2018, 2024)]["part_exposition"]
        return float(s.min() if name.endswith("min") else s.max())
    raise KeyError(name)


def value(key):
    src, _ = CHIFFRES[key]
    if src[0] == "csv":
        return read_csv(src[1], src[2], src[3])
    if src[0] == "json":
        return read_json(src[1], src[2])
    if src[0] == "md":
        return read_md_row(src[1], src[2], after=src[3])
    if src[0] == "derive":
        return derive(src[1])
    raise ValueError(src)


def source_text(key):
    src, kind = CHIFFRES[key]
    if src[0] == "csv":
        sel = ", ".join(f"{k} = {v}" for k, v in src[2].items())
        return f"`{src[1]}`", f"ligne ({sel}), colonne `{src[3]}`"
    if src[0] == "json":
        return f"`{src[1]}`", "clé " + " → ".join(f"`{k}`" for k in src[2])
    if src[0] == "md":
        return f"`{src[1]}`", f"ligne de tableau « {src[2]} »" + (f" (après « {src[3]} »)" if src[3] else "")
    return "agrégation", DERIVES[src[1]]


# ----------------------------------------------------------------------------- résultats (registre)
RESULTATS = [
    ("R1", "Volumes du nettoyage : sinistres bruts, maisons individuelles, anomalies écartées, sinistres propres",
     ["raw_claims", "single_family", "anomalies", "clean_claims"], "E",
     "Change seulement si les règles de nettoyage ou les fichiers bruts changent."),
    ("R2", "Motifs des anomalies écartées (une ligne peut cumuler deux motifs)",
     ["anom_neg_age", "anom_duplicate", "anom_paid_nocov", "anom_neg_paid", "anom_two_reasons"], "E",
     "Idem R1."),
    ("R3", "Table d'analyse comté × zone × année : lignes, comtés, polices-années ; 13 lignes exclues sans effet notable",
     ["ds_rows", "ds_counties", "policy_years", "rows_used", "rows_excluded", "excl13_dev_effect"], "E",
     "Change si build_ds_clean.py ou l'unité d'analyse (secteur) change."),
    ("R4", "Découpage entraînement 2010-2019 / test 2020-2024 : lignes et sinistres",
     ["rows_train", "rows_test", "claims_train_paid", "claims_test_paid", "claims_train_all", "claims_test_all"], "E",
     "Change si le découpage temporel change."),
    ("R5", "Fréquence observée entraînement vs test et poids de 2024 dans les sinistres payés du test",
     ["freq_train", "freq_test", "share_2024_test"], "E", "Constat descriptif ; change si la période de test change."),
    ("R6", "Vérifications techniques réussies (V1-V8, VC1, VC2, VC4) et reproduction exacte des références",
     ["vc1_metric_diff", "vc2_coef_diff", "m4_nonreg"], "E",
     "Devient caduc si les scripts ou les données d'entrée changent (relancer les vérifications)."),
    ("R7", "L'offset de LightGBM par init_score = log(exposition) seul est incorrect (boost_from_average désactivé) ; "
           "la procédure avec log(taux moyen) ajouté reproduit les totaux d'entraînement",
     ["m4_nonreg", "m4_iters"], "E", "Constat technique sur LightGBM 4.7.0 ; à revérifier si la version change."),
    ("R8", "Surdispersion forte et erreurs standard du modèle sous-estimées ; AIC du binomial négatif bien plus bas",
     ["m2_pearson_disp", "se_ratio_vzone", "m2_aic", "m3_aic", "m3_alpha"], "E",
     "Calculs d'ajustement sur l'entraînement ; changent avec les variables ou l'unité."),
    ("R9", "Le binomial négatif (NB2) prédit un total d'entraînement supérieur à l'observé, déjà avec la constante seule",
     ["m3_train_ratio", "nb_const_ratio"], "E", "Calcul vérifié (VC2) ; changerait avec une autre spécification NB."),
    ("R10", "Gains bruts de déviance de test par rapport au modèle nul (premier jet)",
     [f"gain_test_{m}_{c}" for m in ["M1", "M2", "M3", "M4", "M_oracle"] for c in ["payes", "tous"]], "P",
     "Confirmé si une évaluation glissante (par exemple 2016-2024) donne le même ordre ; infirmé sinon."),
    ("R11", "Gains après recalage annuel (diagnostic) : la zone seule porte l'essentiel du gain de classement",
     [f"gain_recal_{m}_{c}" for m in ["M1", "M2", "M3", "M4"] for c in ["payes", "tous"]] + ["zone_share_m4", "zone_share_l2"], "P",
     "Confirmé si un recalage par année × zone et un Gini avec offset donnent la même lecture."),
    ("R12", "Calibration : sous-prédiction du total du test, surprédiction de 2021, forte sous-prédiction en 2022 et 2024",
     ["ratio_test_M0", "ratio_test_M2", "ratio_test_M3", "ratio_test_M4", "ratio_2021_M4", "ratio_2022_M4", "ratio_2024_M4"], "P",
     "Dépend de la fenêtre de test ; à refaire en évaluation glissante."),
    ("R13", "Ablation : l'avantage de LightGBM disparaît sans couverture nominale ; retirer l'historique du comté l'améliore ; "
            "le rang de couverture dans l'année ne reproduit pas l'effet",
     [f"abl_{m}_{e}" for m in ["L1", "L2", "L3", "L5", "L6", "G5_hp"] for e in ["raw", "rec"]]
     + ["abl_L5_train", "abl_M1_train"], "P",
     "Variantes évaluées sur le même test (sélection sur le test) : à confirmer en évaluation glissante, avec itérations réoptimisées par variante."),
    ("R14", "Les historiques 1990-2008 n'apportent rien aux GLM hors période ; l'historique du comté dégrade LightGBM",
     ["abl_G1_raw", "abl_G1_rec", "abl_G3_raw", "abl_G3_rec", "perm_chist", "gain_share_chist"], "P",
     "Confirmé si l'effet persiste en évaluation glissante et au niveau secteur."),
    ("R15", "Importance des variables de M4 : zone et couverture en tête en permutation sur le test",
     ["perm_zone", "perm_cov"], "P", "Importance par permutation (variables corrélées) ; indicative."),
    ("R16", "Déplacement des taux observés par zone entre entraînement et test (A*, V* en hausse ; X en légère baisse) ; "
            "part de X dans les sinistres en chute après 2021 alors que sa part d'exposition reste stable",
     ["mult_A", "mult_V", "mult_X", "x_claims_share_2021", "x_claims_share_2022", "x_expo_share_min", "x_expo_share_max"], "E",
     "Constat descriptif sur la période ; sa cause relève de R18."),
    ("R17", "Tranche haute de couverture : sa part d'exposition et son taux observé augmentent du train au test",
     ["t5_expo_train", "t5_expo_test", "t5_rate_train", "t5_rate_test", "t5_rows_test"], "E",
     "Constat descriptif (tableau hors protocole) ; son lien avec le gain de LightGBM relève de R19."),
    ("R18", "Cause du déplacement des taux A*/X (géographie des événements ou changement de codage des zones avec Risk Rating 2.0)",
     [], "N", "Démontrable par un contrôle du codage de la zone côté polices avant/après 2021 et une analyse par événement."),
    ("R19", "Mécanisme par lequel la couverture nominale aide LightGBM (composante temporelle possible)",
     [], "N", "Testable en déflatant la couverture, en évaluation glissante, et en comparant à une couverture réelle par année."),
    ("R20", "Rôle propre de la valeur de alpha dans le niveau des prédictions du binomial négatif",
     [], "N", "Testable en comparant des NB à alpha fixé à plusieurs valeurs."),
    ("R21", "Codage de la zone côté polices (exposition) avant et après 2021",
     [], "N", "Non vérifié : contrôle des codes bruts de ratedFloodZone dans le fichier des polices."),
    ("R22", "Exposition des petites cellules (faible nombre de polices-années) non validée",
     [], "N", "Démontrable par un taux observé par décile d'exposition et un contrôle des transactions."),
    ("R23", "Avec 5 années de test, le bootstrap par année du premier jet ne produit que peu de combinaisons distinctes : "
            "aucune incertitude fiable n'est disponible",
     ["boot_distinct"], "E", "Change seulement avec une évaluation sur davantage d'années (évaluation glissante)."),
]
