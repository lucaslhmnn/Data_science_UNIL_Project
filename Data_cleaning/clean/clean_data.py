"""Nettoyage des sinistres NFIP (OpenFEMA v3), Région IV de FEMA.

Usage (depuis la racine du dépôt, avec l'environnement virtuel ; Python 3.12 ou plus) :
    .venv/bin/python Data_cleaning/clean/clean_data.py audit      # 1. audit (lecture seule)
    .venv/bin/python Data_cleaning/clean/clean_data.py sentinels  # 2. diagnostic des sentinelles
    .venv/bin/python Data_cleaning/clean/clean_data.py clean      # 3. nettoyage complet

Tous les chemins sont relatifs à l'emplacement de ce fichier : le script fonctionne depuis
n'importe quel clone, quel que soit le dossier courant. Fichiers d'entrée attendus dans
Data_cleaning/ (voir Data_cleaning/README.md) ; sorties écrites dans Data_cleaning/clean/.

Les fichiers bruts ne sont jamais modifiés : DuckDB les lit en ne chargeant que
les colonnes nécessaires, et seuls des agrégats reviennent en mémoire.
"""
import argparse
import sys
from pathlib import Path

import duckdb
import openpyxl
import pandas as pd
import pyarrow.parquet as pq

# =============================================================================
# CONFIG
# =============================================================================
HERE = Path(__file__).resolve().parent
DATA = HERE.parent

CONFIG = {
    "claims_file": DATA / "NfipClaimsV3_SE.parquet",
    "policies_file": DATA / "NfipPoliciesV3_SE.parquet",
    "cpi_file": DATA / "CPI_1978_2026.xlsx",
    "out_dir": HERE,

    # Région IV de FEMA et codes FIPS d'État correspondants
    "region_iv": {"AL": "01", "FL": "12", "GA": "13", "KY": "21",
                  "MS": "28", "NC": "37", "SC": "45", "TN": "47"},
    # Boîtes englobantes approximatives des États (lat_min, lat_max, lon_min, lon_max).
    # Contrôle grossier : les coordonnées OpenFEMA sont arrondies à 0,1°.
    "state_bbox": {
        "AL": (30.14, 35.01, -88.47, -84.89), "FL": (24.40, 31.00, -87.63, -79.97),
        "GA": (30.36, 35.00, -85.61, -80.84), "KY": (36.50, 39.15, -89.57, -81.96),
        "MS": (30.17, 35.00, -91.66, -88.10), "NC": (33.84, 36.59, -84.32, -75.46),
        "SC": (32.03, 35.22, -83.35, -78.54), "TN": (34.98, 36.68, -90.31, -81.65),
    },
    "bbox_tolerance_deg": 0.1,

    # Filtre bâtiment : maisons individuelles
    "occupancy_keep": [1, 11],

    # Franchise bâtiment : code -> dollars (H = polices de groupe uniquement)
    "deductible_map": {"0": 500, "1": 1000, "2": 2000, "3": 3000, "4": 4000, "5": 5000,
                       "9": 750, "A": 10000, "B": 15000, "C": 20000, "D": 25000,
                       "E": 50000, "F": 1250, "G": 1500, "H": 200},
    # Tables de codes catégoriels (codes attendus)
    "foundation_codes": {"1": "dalle", "2": "sous-sol", "3": "vide sanitaire",
                         "4": "surélevé", "5": "surélevé", "6": "surélevé"},
    "floors_codes": {"1": "1 étage", "2": "2 étages", "3": "3 étages ou plus",
                     "4": "split-level", "5": "mobil-home sur fondation",
                     "6": "maison en rangée 3+ étages"},

    "elevation_missing_code": 9999,   # utilisé par l'audit uniquement (variable abandonnée, décision 10)

    # ---- Décisions validées après l'audit (phase 1) ----
    # (1) Système de tarification déduit d'occupancyType (dictionnaire v3 : les codes à
    #     2 chiffres sont ceux de Risk Rating 2.0) ; foundationType "0" = non renseigné
    #     (la fondation n'existe que dans le codage Risk Rating 2.0).
    "rating_system_map": {1: "ancien (1)", 11: "Risk Rating 2.0 (11)"},
    "foundation_missing_code": "0",
    "missing_label": "non renseigné",
    # (2) paiement NA et paiement net nul => dossier clos sans paiement => paid_flag = 0
    "paid_na_net_zero_is_unpaid": True,
    # (3) Zone de tarification (ratedFloodZone) au lieu de floodZoneCurrent, pour les
    #     sinistres comme pour les polices. Tout code non NA absent de ces listes -> "autre".
    "flood_zone_column_claims": "ratedFloodZone",
    "flood_zone_column_policies": "ratedFloodZone",
    "flood_zone_groups": {
        "A*": ["A", "AE", "A99", "AH", "AHB", "AO", "AOB", "AR", "ARE", "ARH", "ARO", "ARA"]
              + [f"A{i}" for i in range(1, 31)] + [f"A{i:02d}" for i in range(1, 10)],
        "V*": ["V", "VE"] + [f"V{i}" for i in range(1, 31)] + [f"V{i:02d}" for i in range(1, 10)],
        "X": ["X", "B", "C"],   # B et C : anciennes appellations des zones X (dictionnaire v3)
        "D": ["D"],
    },
    "flood_zone_other": "autre",
    # (4) Mois sans CPI tolérés : paid_building_real reste NA pour ces sinistres (pas d'interpolation)
    "cpi_months_missing_ok": ["2025-10"],
    # (5) Dates de construction inutilisables -> building_age NA (lignes conservées)
    "construction_sentinels": ["1492-10-12"],
    "construction_min_year": 1700,
    # (6)-(9) Lignes écartées vers claims_anomalies.parquet : âge négatif, paiement négatif,
    #     doublon exact (on garde le plus petit id), paiement > 0 avec couverture nulle,
    #     code hors table.
    # (10) elevationDifference abandonnée (58 % de NA).

    # ---- Valeurs sentinelles (diagnostic : sentinel_report.md) ----
    # ATTENTION : chaque règle ci-dessous est une HYPOTHÈSE NON DOCUMENTÉE PAR FEMA.
    # Les valeurs visées sont remplacées par NA ; aucune ligne n'est supprimée.
    "sentinel_to_na": {
        "waterDepth": [-999],          # hypothèse : -999 = « non renseigné » (pouces ; unité mixte possible)
        "floodWaterDuration": [999],   # hypothèse : 999 = « non renseigné » (heures)
    },
    # Règles appliquées seulement si le code apparaît au moins `min_rows` fois (sinon signalé, non appliqué).
    "sentinel_to_na_if_frequent": {
        # hypothèse : 2 147 483 647 = maximum d'un entier signé 32 bits (code ou dépassement)
        "buildingPropertyValue": {"codes": [2147483647], "min_rows": 10},
    },
    # Seuil des valeurs extrêmes de buildingPropertyValue (validé) : valeurs > seuil -> NA.
    # HYPOTHÈSE NON DOCUMENTÉE PAR FEMA : au-delà de 10 M$, le rapport valeur / couverture explose
    # (≈ 90 à ≈ 7 000) et les valeurs >= 100 M$ (1998-2001, multiples de 100) évoquent une erreur
    # d'unité. Valeurs mises en NA, lignes conservées. None = pas de seuil.
    "property_value_max": 10_000_000,

    # Mois de base du CPI (None = dernier mois disponible)
    "cpi_base": None,
}

# Colonnes requises pour le dataset final (noms bruts du dictionnaire v3)
CLAIMS_REQUIRED = [
    "id", "state", "dateOfLoss", "yearOfLoss", "occupancyType",
    "amountPaidOnBuildingClaim", "totalBuildingInsuranceCoverage", "buildingDeductibleCode",
    "floodZoneCurrent", "elevationDifference", "foundationType", "elevatedBuildingIndicator",
    "originalConstructionDate", "numberOfFloorsInTheInsuredBuilding",
    "primaryResidenceIndicator", "countyCode", "waterDepth", "floodWaterDuration",
    "floodEvent", "buildingPropertyValue",
]
# Lues uniquement pour les contrôles d'audit (n'entrent pas dans le dataset)
CLAIMS_AUDIT_ONLY = ["latitude", "longitude", "asOfDate", "ratedFloodZone",
                     "netBuildingPaymentAmount", "nonPaymentReasonBuilding", "mostRecentPaymentDate"]

POLICIES_REQUIRED = [
    "id", "propertyState", "censusGeoid", "occupancyType", "floodZoneCurrent",
    "policyEffectiveDate", "policyTerminationDate", "policyCount",
    "totalBuildingInsuranceCoverage", "totalInsurancePremiumOfThePolicy",
]
POLICIES_AUDIT_ONLY = ["latitude", "longitude", "asOfDate", "policyTermIndicator",
                       "endorsementEffectiveDate", "cancellationDateOfFloodPolicy",
                       "originalNBDate", "originalConstructionDate", "ratedFloodZone"]

# Expression SQL du filtre bâtiment, robuste à un occupancyType lu en texte ou en entier
OCC_INT = "TRY_CAST(trim(CAST(occupancyType AS VARCHAR)) AS INTEGER)"
OCC_FILTER = f"{OCC_INT} IN ({', '.join(map(str, CONFIG['occupancy_keep']))})"


# =============================================================================
# Outils
# =============================================================================
def md_table(df: pd.DataFrame) -> str:
    """Tableau markdown sans dépendance externe."""
    def fmt(v):
        if pd.isna(v):
            return "NA"
        if isinstance(v, float):
            return f"{v:,.2f}".replace(",", " ")
        if isinstance(v, int):  # séparateur de milliers seulement à partir de 10 000 (pas pour les années)
            return f"{v:,}".replace(",", " ") if abs(v) >= 10_000 else str(v)
        return str(v).replace("|", "\\|")
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def n(x) -> str:
    return f"{int(x):,}".replace(",", " ")


def pct(a, b) -> str:
    return "NA" if not b else f"{100 * a / b:.2f} %"


def zone_group_sql(col: str) -> str:
    """CASE SQL du regroupement des zones, construit depuis CONFIG (même règle partout)."""
    whens = " ".join(
        f"WHEN {col} IN ({', '.join(repr(z) for z in zones)}) THEN '{g}'"
        for g, zones in CONFIG["flood_zone_groups"].items())
    return f"CASE WHEN {col} IS NULL THEN NULL {whens} ELSE '{CONFIG['flood_zone_other']}' END"


def load_cpi(path: Path):
    """Lit l'Excel BLS (format large : années en lignes, mois en colonnes) et le passe
    en format long : une ligne par mois. Les cellules non numériques deviennent NA."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    meta = {str(r[0]).rstrip(":"): r[1] for r in rows[:11] if r[0] is not None}
    hdr_i = next(i for i, r in enumerate(rows) if r[0] == "Year")
    hdr = list(rows[hdr_i])
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    long = []
    for r in rows[hdr_i + 1:]:
        if r[0] is None:
            continue
        for m, name in enumerate(months, start=1):
            v = r[hdr.index(name)]
            long.append((pd.Period(year=int(r[0]), month=m, freq="M"),
                         float(v) if isinstance(v, (int, float)) else None, repr(v)))
    cpi = pd.DataFrame(long, columns=["mois", "cpi", "brut"])
    cpi["cpi"] = cpi["cpi"].astype("Float64")
    return cpi, meta, wb.sheetnames, hdr, hdr_i


INPUT_SOURCES = {
    "claims_file": "OpenFEMA, FIMA NFIP Redacted Claims v3 (NfipClaims), filtré sur les États de la Région IV",
    "policies_file": "OpenFEMA, FIMA NFIP Redacted Policies v3 (NfipPolicies), filtré sur les États de la Région IV",
    "cpi_file": "BLS, CPI-U série CUUR0000SA0 (export Excel mensuel 1978-2026)",
}


def check_inputs(keys):
    """Arrête le script avec un message lisible si un fichier d'entrée manque (pas de trace Python)."""
    root = HERE.parent.parent
    missing = [k for k in keys if not CONFIG[k].exists()]
    if missing:
        lines = ["", "ERREUR : fichier(s) d'entrée introuvable(s). Placez-les à ces emplacements :", ""]
        for k in missing:
            p = CONFIG[k]
            lines += [f"  - {p.relative_to(root)}", f"      (chemin complet attendu : {p})",
                      f"      source : {INPUT_SOURCES[k]}"]
        lines += ["", "Procédure et lien de téléchargement : voir Data_cleaning/README.md.", ""]
        sys.exit("\n".join(lines))


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET memory_limit='6GB'")
    return con


def check_columns(con, path: Path, required: list, audit_only: list) -> pd.DataFrame:
    """Échoue explicitement si une colonne requise manque ; renvoie le schéma utile."""
    schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").df()
    present = set(schema["column_name"])
    missing = [c for c in required + audit_only if c not in present]
    if missing:
        raise ValueError(f"{path.name} : colonnes requises absentes : {missing}")
    return schema.set_index("column_name").loc[required + audit_only, ["column_type"]]


def na_profile(con, view: str, cols: list, types: pd.DataFrame) -> pd.DataFrame:
    """Type et % de NA de chaque colonne, en un seul passage."""
    total = con.execute(f"SELECT count(*) FROM {view}").fetchone()[0]
    exprs = ", ".join(f'count("{c}")' for c in cols)
    counts = con.execute(f"SELECT {exprs} FROM {view}").fetchone()
    return pd.DataFrame({
        "colonne": cols,
        "type": [types.loc[c, "column_type"] for c in cols],
        "NA": [total - k for k in counts],
        "% NA": [round(100 * (total - k) / total, 2) for k in counts],
    })


# =============================================================================
# PHASE 1 : AUDIT
# =============================================================================
def audit():
    check_inputs(["claims_file", "policies_file", "cpi_file"])
    cfg = CONFIG
    con = connect()
    out = []
    w = out.append
    issues = []          # anomalies significatives -> décision requise avant phase 2

    # ---------------------------------------------------------------- 1. colonnes
    ctypes = check_columns(con, cfg["claims_file"], CLAIMS_REQUIRED, CLAIMS_AUDIT_ONLY)
    ptypes = check_columns(con, cfg["policies_file"], POLICIES_REQUIRED, POLICIES_AUDIT_ONLY)
    ccols = CLAIMS_REQUIRED + CLAIMS_AUDIT_ONLY
    pcols = POLICIES_REQUIRED + POLICIES_AUDIT_ONLY
    con.execute(f"CREATE VIEW claims AS SELECT {', '.join(map(lambda c: f'\"{c}\"', ccols))} "
                f"FROM read_parquet('{cfg['claims_file']}')")
    con.execute(f"CREATE VIEW policies AS SELECT {', '.join(map(lambda c: f'\"{c}\"', pcols))} "
                f"FROM read_parquet('{cfg['policies_file']}')")
    con.execute(f"CREATE VIEW claims_f AS SELECT * FROM claims WHERE {OCC_FILTER}")
    con.execute(f"CREATE VIEW policies_f AS SELECT * FROM policies WHERE {OCC_FILTER}")
    q1 = lambda s: con.execute(s).fetchone()
    qdf = lambda s: con.execute(s).df()

    nc = q1("SELECT count(*) FROM claims")[0]
    ncf = q1("SELECT count(*) FROM claims_f")[0]
    np_ = q1("SELECT count(*) FROM policies")[0]
    npf = q1("SELECT count(*) FROM policies_f")[0]
    # asOfDate est un horodatage avec fuseau : conversion en UTC côté SQL
    utc = "CAST(timezone('UTC', {f}(asOfDate)) AS VARCHAR) || ' UTC'"
    as_of_c = q1(f"SELECT {utc.format(f='min')}, {utc.format(f='max')} FROM claims")
    as_of_p = q1(f"SELECT {utc.format(f='min')}, {utc.format(f='max')} FROM policies")
    extraction = pd.Timestamp(as_of_p[1].removesuffix(" UTC")).normalize()

    w("# Rapport d'audit (phase 1) : sinistres et polices NFIP, Région IV\n")
    w("> Lecture seule. Généré par `clean_data.py audit`. Aucune ligne n'a été modifiée ni supprimée.\n")
    w(f"- Sinistres : `{cfg['claims_file'].name}` : {n(nc)} lignes")
    w(f"- Polices : `{cfg['policies_file'].name}` : {n(np_)} lignes")
    w(f"- Date d'extraction (`asOfDate`) : sinistres {as_of_c[0]} ; polices {as_of_p[0]}"
      f"{'' if as_of_p[0] == as_of_p[1] else ' → ' + str(as_of_p[1])}")
    w("- Sauf mention contraire, les contrôles 4 à 8 et 10 portent sur la population filtrée "
      f"`occupancyType ∈ {cfg['occupancy_keep']}` ({n(ncf)} sinistres).\n")

    w("## 1. Colonnes requises, types, valeurs manquantes, dates\n")
    w("Toutes les colonnes requises sont présentes dans les deux fichiers. "
      "Les colonnes marquées *(audit)* sont lues uniquement pour les contrôles.\n")
    prof = na_profile(con, "claims", ccols, ctypes)
    prof["colonne"] = [c + (" *(audit)*" if c in CLAIMS_AUDIT_ONLY else "") for c in ccols]
    w("### Sinistres (fichier complet)\n"); w(md_table(prof)); w("")
    prof = na_profile(con, "policies", pcols, ptypes)
    prof["colonne"] = [c + (" *(audit)*" if c in POLICIES_AUDIT_ONLY else "") for c in pcols]
    w("### Polices (fichier complet)\n"); w(md_table(prof)); w("")
    d = q1("SELECT min(dateOfLoss), max(dateOfLoss), min(originalConstructionDate), "
           "max(originalConstructionDate) FROM claims")
    w(f"- Sinistres : `dateOfLoss` de {d[0]} à {d[1]} ; `originalConstructionDate` de {d[2]} à {d[3]}.")
    d = q1("SELECT min(policyEffectiveDate), max(policyEffectiveDate), "
           "min(policyTerminationDate), max(policyTerminationDate) FROM policies")
    w(f"- Polices : `policyEffectiveDate` de {d[0]} à {d[1]} ; "
      f"`policyTerminationDate` de {d[2]} à {d[3]}.\n")

    # ---------------------------------------------------------------- 2. Région IV
    w("## 2. Région IV : États, FIPS, coordonnées\n")
    expected = set(cfg["region_iv"])
    region_ok = True
    for label, view, scol, total in [("Sinistres", "claims", "state", nc),
                                     ("Polices", "policies", "propertyState", np_)]:
        st = qdf(f"SELECT {scol} AS etat, count(*) AS lignes FROM {view} GROUP BY 1 ORDER BY 2 DESC")
        st["part"] = (100 * st["lignes"] / total).round(2).astype(str) + " %"
        st["Région IV"] = st["etat"].isin(expected).map({True: "oui", False: "**non**"})
        present = set(st["etat"].dropna())
        absent, extra = sorted(expected - present), sorted(present - expected)
        n_extra = int(st.loc[st["etat"].isin(extra), "lignes"].sum())
        n_na = int(st["lignes"][st["etat"].isna()].sum())
        region_ok &= not absent and not extra and n_na == 0
        w(f"### {label} (`{scol}`)\n"); w(md_table(st)); w("")
        w(f"- (a) Attendus absents : {absent or 'aucun'}")
        w(f"- (b) Présents hors Région IV : {extra or 'aucun'}")
        w(f"- (c) Lignes concernées par (b) : {n(n_extra)} ; État manquant : {n(n_na)}\n")

    # Cohérence État ↔ FIPS (2 premiers caractères)
    fips_case = "CASE " + " ".join(f"WHEN {{s}}='{k}' THEN '{v}'" for k, v in cfg["region_iv"].items()) + " END"
    for label, view, scol, gcol in [("Sinistres", "claims", "state", "countyCode"),
                                    ("Polices", "policies", "propertyState", "censusGeoid")]:
        r = q1(f"SELECT count(*) FILTER (WHERE {gcol} IS NULL), "
               f"count(*) FILTER (WHERE {gcol} IS NOT NULL AND left({gcol},2) <> {fips_case.format(s=scol)}) "
               f"FROM {view}")
        w(f"- {label} : `{gcol}` manquant : {n(r[0])} ; préfixe FIPS incohérent avec `{scol}` : {n(r[1])}.")
        if r[1]:
            ex = qdf(f"SELECT {scol}, left({gcol},2) AS prefixe, count(*) AS lignes FROM {view} "
                     f"WHERE {gcol} IS NOT NULL AND left({gcol},2) <> {fips_case.format(s=scol)} "
                     f"GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10")
            w(""); w(md_table(ex)); w("")

    # Coordonnées hors de la boîte englobante de l'État déclaré
    tol = cfg["bbox_tolerance_deg"]
    out_cond = " OR ".join(
        f"({{s}}='{s}' AND (latitude NOT BETWEEN {a - tol} AND {b + tol} "
        f"OR longitude NOT BETWEEN {c - tol} AND {d + tol}))"
        for s, (a, b, c, d) in cfg["state_bbox"].items())
    w("")
    for label, view, scol in [("Sinistres", "claims", "state"), ("Polices", "policies", "propertyState")]:
        r = q1(f"SELECT count(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL), "
               f"count(*) FILTER (WHERE {out_cond.format(s=scol)}) FROM {view}")
        w(f"- {label} : coordonnées manquantes {n(r[0])} ; hors de la boîte englobante de l'État "
          f"déclaré (± {tol}°) : {n(r[1])} ({pct(r[1], nc if view == 'claims' else np_)}).")
    w("\n*Contrôle approximatif (boîtes rectangulaires, coordonnées arrondies à 0,1°) : "
      "un point dans la boîte n'est pas forcément dans l'État.*\n")

    # ---------------------------------------------------------------- 3. types / texte
    w("## 3. Types : numériques en texte, espaces parasites, booléens\n")
    rows = []
    for label, view, types, cols in [("sinistres", "claims", ctypes, CLAIMS_REQUIRED),
                                     ("polices", "policies", ptypes, POLICIES_REQUIRED)]:
        txt = [c for c in cols if types.loc[c, "column_type"] == "VARCHAR"]
        exprs = []
        for c in txt:
            exprs += [f'count("{c}")', f'count(TRY_CAST(trim("{c}") AS DOUBLE))',
                      f'count(*) FILTER (WHERE "{c}" <> trim("{c}"))',
                      f"count(*) FILTER (WHERE trim(\"{c}\") = '')"]
        r = q1(f"SELECT {', '.join(exprs)} FROM {view}")
        for i, c in enumerate(txt):
            nn, num, sp, empty = r[4 * i:4 * i + 4]
            rows.append([label, c, nn, num, sp, empty])
    w("Colonnes texte (VARCHAR) parmi les colonnes requises, fichiers complets :\n")
    w(md_table(pd.DataFrame(rows, columns=["fichier", "colonne", "non NA", "convertibles en nombre",
                                           "avec espaces en début/fin", "vides"])))
    bool_cols = {"sinistres": [c for c in CLAIMS_REQUIRED if ctypes.loc[c, "column_type"] == "BOOLEAN"]}
    w(f"\n- Booléens : `elevatedBuildingIndicator` et `primaryResidenceIndicator` sont de type "
      f"{ctypes.loc['elevatedBuildingIndicator', 'column_type']} / "
      f"{ctypes.loc['primaryResidenceIndicator', 'column_type']} dans le Parquet "
      "(pas de texte \"true\"/\"1\" à convertir).")
    w(f"- `occupancyType` : type {ctypes.loc['occupancyType', 'column_type']} (sinistres), "
      f"{ptypes.loc['occupancyType', 'column_type']} (polices). Le filtre utilise "
      "`TRY_CAST(trim(CAST(occupancyType AS VARCHAR)) AS INTEGER)`, valable en texte comme en entier.\n")
    if bool_cols["sinistres"] != ["elevatedBuildingIndicator", "primaryResidenceIndicator"]:
        issues.append("Les colonnes booléennes ne sont pas du type attendu (voir § 3).")

    # ---------------------------------------------------------------- 4. codes
    w("## 4. Valeurs distinctes des colonnes codées\n")
    occ = qdf(f"SELECT CAST(occupancyType AS VARCHAR) AS occupancyType, count(*) AS lignes "
              f"FROM claims GROUP BY 1 ORDER BY 2 DESC")
    w("### `occupancyType` (sinistres, fichier complet)\n"); w(md_table(occ)); w("")
    tables = {
        "buildingDeductibleCode": set(cfg["deductible_map"]),
        "foundationType": set(cfg["foundation_codes"]),
        "numberOfFloorsInTheInsuredBuilding": set(cfg["floors_codes"]),
        "elevatedBuildingIndicator": None, "primaryResidenceIndicator": None,
        "floodZoneCurrent": None,  # traité au § 7
    }
    out_of_table = {}
    for c, allowed in tables.items():
        if c == "floodZoneCurrent":
            continue
        v = qdf(f'SELECT CAST("{c}" AS VARCHAR) AS valeur, count(*) AS lignes FROM claims_f '
                f"GROUP BY 1 ORDER BY 1")
        if allowed is not None:
            v["dans la table"] = v["valeur"].map(lambda x: "NA" if pd.isna(x) else
                                                 ("oui" if x in allowed else "**non**"))
            bad = v[v["dans la table"] == "**non**"]
            out_of_table[c] = int(bad["lignes"].sum())
        w(f"### `{c}`\n"); w(md_table(v)); w("")
    w("Codes hors table (population filtrée) : " +
      "; ".join(f"`{k}` : {n(v)} lignes" for k, v in out_of_table.items()) + "\n")
    # Le code 0 de foundationType dépend-il du code d'occupation (ancien / nouveau système) ?
    fo = qdf("SELECT CAST(occupancyType AS VARCHAR) AS occupancyType, foundationType, count(*) AS lignes, "
             "min(dateOfLoss) AS premier_sinistre, max(dateOfLoss) AS dernier_sinistre "
             "FROM claims_f GROUP BY 1, 2 ORDER BY 1, 2")
    w("`foundationType` × `occupancyType` :\n"); w(md_table(fo)); w("")
    f0_occ1 = q1("SELECT count(*) FILTER (WHERE foundationType = '0' AND occupancyType = 1), "
                 "count(*) FILTER (WHERE foundationType = '0'), count(*) FILTER (WHERE occupancyType = 1) "
                 "FROM claims_f")
    w(f"- Le code `0` (hors table) concerne {n(f0_occ1[1])} lignes, dont {n(f0_occ1[0])} avec "
      f"`occupancyType` = 1 (qui compte {n(f0_occ1[2])} lignes au total). Lecture : `occupancyType` 1 est "
      "l'ancien code « maison individuelle », 11 celui de Risk Rating 2.0, et la fondation n'est "
      "renseignée que dans le nouveau système. Le code 0 signifie donc vraisemblablement « non renseigné », "
      "pas une erreur de saisie.\n")
    for k, v in out_of_table.items():
        if not v:
            continue
        if k == "foundationType" and f0_occ1[0] == v == f0_occ1[2]:
            issues.append(f"`foundationType` = 0 (hors table) pour {n(v)} lignes ({pct(v, ncf)}), "
                          "soit exactement tous les sinistres `occupancyType` = 1 (ancien système). "
                          "Les écarter par défaut supprimerait 71 % du jeu : traiter 0 comme "
                          "« non renseigné » ?")
        else:
            issues.append(f"Codes hors table : {k} ({n(v)} lignes).")

    cc = qdf("SELECT length(countyCode) AS longueur, "
             "count(*) FILTER (WHERE left(countyCode,1)='0') AS commence_par_0, "
             "count(*) FILTER (WHERE NOT regexp_full_match(countyCode, '[0-9]+')) AS non_numerique, "
             "count(*) AS lignes FROM claims_f GROUP BY 1 ORDER BY 1")
    w("### `countyCode` : longueur et zéros initiaux\n"); w(md_table(cc))
    w("\n*Les comtés d'Alabama (FIPS 01) doivent commencer par 0 : un countyCode de 4 caractères "
      "signalerait un zéro initial perdu.*\n")

    # ---------------------------------------------------------------- 5. paiement
    w("## 5. `amountPaidOnBuildingClaim`\n")
    r = q1("SELECT count(*) FILTER (WHERE amountPaidOnBuildingClaim IS NULL), "
           "count(*) FILTER (WHERE amountPaidOnBuildingClaim = 0), "
           "count(*) FILTER (WHERE amountPaidOnBuildingClaim < 0), "
           "count(*) FILTER (WHERE amountPaidOnBuildingClaim > 0), "
           "min(amountPaidOnBuildingClaim), max(amountPaidOnBuildingClaim), "
           "median(amountPaidOnBuildingClaim) FILTER (WHERE amountPaidOnBuildingClaim > 0) FROM claims_f")
    w(f"- NA : {n(r[0])} ({pct(r[0], ncf)}) ; zéros : {n(r[1])} ({pct(r[1], ncf)}) ; "
      f"négatifs : {n(r[2])} ; > 0 : {n(r[3])} ({pct(r[3], ncf)})")
    w(f"- Min {r[4]} ; max {r[5]} ; médiane des paiements > 0 : {r[6]}\n")
    n_neg, n_paid_na = r[2], r[0]
    if n_neg:
        issues.append(f"{n(n_neg)} montants payés négatifs.")
    na_ex = qdf("""SELECT (netBuildingPaymentAmount = 0) AS net_nul,
                          (nonPaymentReasonBuilding IS NOT NULL) AS motif_non_paiement,
                          (mostRecentPaymentDate IS NULL) AS sans_date_paiement, count(*) AS lignes
                   FROM claims_f WHERE amountPaidOnBuildingClaim IS NULL GROUP BY ALL ORDER BY 4 DESC""")
    w("Que sont les paiements NA ? Colonnes lues pour l'audit seulement "
      "(`netBuildingPaymentAmount`, `nonPaymentReasonBuilding`, `mostRecentPaymentDate`) :\n")
    w(md_table(na_ex)); w("")
    n_na_reason = int(na_ex.loc[na_ex["motif_non_paiement"] == True, "lignes"].sum())
    n_na_net0 = int(na_ex.loc[na_ex["net_nul"] == True, "lignes"].sum())
    n_na_date = int(na_ex.loc[na_ex["sans_date_paiement"] == False, "lignes"].sum())
    w(f"- {n(n_na_reason)} des {n(n_paid_na)} NA ont un motif de non-paiement, {n(n_na_net0)} un paiement "
      f"net nul, et {n(n_na_date)} ont une date de paiement : ce sont très vraisemblablement des dossiers "
      "clos sans paiement.\n")
    if n_paid_na:
        issues.append(f"{n(n_paid_na)} `amountPaidOnBuildingClaim` NA ({pct(n_paid_na, ncf)}). Selon la "
                      "consigne, paid_flag = NA, ce qui retire du modèle logistique la quasi-totalité des "
                      f"sinistres non payés ({n(n_paid_na)} NA contre {n(r[1])} zéros). Or {n(n_na_reason)} "
                      "de ces NA portent un motif de non-paiement : les traiter comme paid_flag = 0 ?")
    n_paid_nocov = q1("SELECT count(*) FROM claims_f WHERE amountPaidOnBuildingClaim > 0 "
                      "AND totalBuildingInsuranceCoverage = 0")[0]
    if n_paid_nocov:
        issues.append(f"{n(n_paid_nocov)} sinistres payés avec une couverture bâtiment nulle.")
    ct = qdf("""SELECT CASE WHEN amountPaidOnBuildingClaim IS NULL THEN 'NA'
                            WHEN amountPaidOnBuildingClaim > 0 THEN '> 0' ELSE '<= 0' END AS paiement,
                       count(*) FILTER (WHERE totalBuildingInsuranceCoverage > 0) AS "couverture > 0",
                       count(*) FILTER (WHERE totalBuildingInsuranceCoverage = 0) AS "couverture = 0",
                       count(*) FILTER (WHERE totalBuildingInsuranceCoverage < 0) AS "couverture < 0",
                       count(*) FILTER (WHERE totalBuildingInsuranceCoverage IS NULL) AS "couverture NA"
                FROM claims_f GROUP BY 1 ORDER BY 1""")
    w("Tableau croisé paiement × `totalBuildingInsuranceCoverage` :\n"); w(md_table(ct)); w("")
    # Le NA du paiement est-il un « pas de paiement » ? (information)
    r = q1("SELECT count(*) FILTER (WHERE buildingPropertyValue IS NULL) FROM claims_f "
           "WHERE amountPaidOnBuildingClaim IS NULL")
    w(f"- Parmi les paiements NA, `buildingPropertyValue` est aussi NA pour {n(r[0])} lignes "
      f"({pct(r[0], n_paid_na)}).\n")

    # ---------------------------------------------------------------- 6. élévation
    w("## 6. `elevationDifference`\n")
    code = cfg["elevation_missing_code"]
    r = q1(f"SELECT count(*) FILTER (WHERE elevationDifference = {code}), "
           f"count(*) FILTER (WHERE elevationDifference IS NULL), "
           f"count(*) FILTER (WHERE abs(elevationDifference) >= 999 AND elevationDifference <> {code}) "
           f"FROM claims_f")
    w(f"- Code {code} : {n(r[0])} ({pct(r[0], ncf)}) ; NA : {n(r[1])} ({pct(r[1], ncf)}) ; "
      f"autres valeurs |x| ≥ 999 : {n(r[2])}")
    ext = q1(f"SELECT count(*) FILTER (WHERE elevationDifference < -50), "
             f"count(*) FILTER (WHERE elevationDifference > 50 AND elevationDifference <> {code}) FROM claims_f")
    w(f"- Valeurs extrêmes (implausibles pour une maison) : < −50 pieds : {n(ext[0])} ; > 50 pieds : {n(ext[1])}. "
      "Elles tombent dans les classes extrêmes sans être corrigées.")
    if r[0] == 0:
        w(f"- Le code {code} n'apparaît pas dans ce fichier : les valeurs manquantes sont déjà des NA.")
    qs = q1(f"SELECT min(e), quantile_cont(e, [0.01,0.05,0.10,0.25,0.5,0.75,0.90,0.95,0.99]), max(e), count(e) "
            f"FROM (SELECT elevationDifference e FROM claims_f WHERE elevationDifference <> {code})")
    w(f"- Hors {code} ({n(qs[3])} valeurs) : min {qs[0]} ; "
      f"P1/P5/P10/P25/P50/P75/P90/P95/P99 = {' / '.join(f'{x:g}' for x in qs[1])} ; max {qs[2]}")
    hist = qdf(f"SELECT elevationDifference AS valeur, count(*) AS lignes FROM claims_f "
               f"WHERE elevationDifference BETWEEN -10 AND 20 GROUP BY 1 ORDER BY 1")
    w("\nEffectifs par valeur entre −10 et 20 (pieds, au-dessus (+) ou au-dessous (−) de la BFE) :\n")
    w(md_table(hist))
    proposed = [-float("inf"), -2, 0, 2, 4, 8, float("inf")]
    band = qdf(f"""SELECT CASE WHEN e IS NULL OR e = {code} THEN 'non renseigné'
                               WHEN e < -2 THEN '1. < -2' WHEN e < 0 THEN '2. [-2, 0)'
                               WHEN e < 2 THEN '3. [0, 2)' WHEN e < 4 THEN '4. [2, 4)'
                               WHEN e < 8 THEN '5. [4, 8)' ELSE '6. >= 8' END AS classe,
                          count(*) AS lignes
                   FROM (SELECT elevationDifference e FROM claims_f) GROUP BY 1 ORDER BY 1""")
    band["part"] = (100 * band["lignes"] / ncf).round(2).astype(str) + " %"
    w(f"\n**Bornes proposées** `{proposed}` (pieds ; 0 = plancher au niveau de la BFE) :\n")
    w(md_table(band)); w("")
    if r[0] + r[1] > 0.5 * ncf:
        issues.append(f"`elevationDifference` non renseignée (9999 ou NA) pour "
                      f"{pct(r[0] + r[1], ncf)} des sinistres.")

    # ---------------------------------------------------------------- 7. zones
    w("## 7. `floodZoneCurrent`\n")
    fz = qdf("SELECT floodZoneCurrent AS zone, count(*) AS lignes FROM claims_f GROUP BY 1 ORDER BY 2 DESC")
    group_sql = """CASE WHEN z IS NULL THEN 'NA'
                        WHEN z IN ('X', 'B', 'C') THEN 'X'
                        WHEN z = 'D' THEN 'D'
                        WHEN z LIKE 'V%' THEN 'V*'
                        WHEN z LIKE 'A%' THEN 'A*'
                        ELSE 'autre' END"""
    fz["groupe proposé"] = [con.execute(f"SELECT {group_sql} FROM (SELECT ?::VARCHAR z)", [z]).fetchone()[0]
                            for z in fz["zone"]]
    w(md_table(fz)); w("")
    g = qdf(f"SELECT {group_sql} AS groupe, count(*) AS lignes FROM "
            f"(SELECT floodZoneCurrent z FROM claims_f) GROUP BY 1 ORDER BY 2 DESC")
    g["part"] = (100 * g["lignes"] / ncf).round(2).astype(str) + " %"
    w("**Regroupement proposé** : A* = zones commençant par A (A, AE, A01–A30, AH, AO, A99, AR…) ; "
      "V* = V, VE, V01–V30 ; X = X, B, C (B et C sont les anciennes appellations des zones à risque "
      "modéré ou minimal, devenues X) ; D ; autre = tout le reste.\n")
    w(md_table(g)); w("")
    r = q1("SELECT count(*) FILTER (WHERE floodZoneCurrent IS NULL), "
           "count(*) FILTER (WHERE ratedFloodZone IS NULL), "
           "count(*) FILTER (WHERE floodZoneCurrent IS NULL AND ratedFloodZone IS NOT NULL) FROM claims_f")
    w(f"- `floodZoneCurrent` NA : {n(r[0])} ({pct(r[0], ncf)}). Pour comparaison, `ratedFloodZone` "
      f"(zone de tarification au moment de la police, *non retenue dans la liste*) : "
      f"NA {n(r[1])} ({pct(r[1], ncf)}).")
    yz = qdf("SELECT yearOfLoss // 10 * 10 AS decennie, round(100 * avg((floodZoneCurrent IS NULL)::INT), 1) "
             "AS \"% NA floodZoneCurrent\", round(100 * avg((ratedFloodZone IS NULL)::INT), 1) "
             "AS \"% NA ratedFloodZone\", count(*) AS lignes FROM claims_f GROUP BY 1 ORDER BY 1")
    w("\nTaux de NA par décennie de sinistre :\n"); w(md_table(yz)); w("")
    pz = q1("SELECT count(*) FILTER (WHERE floodZoneCurrent IS NULL), count(*) FROM policies_f")
    w(f"- Polices filtrées : `floodZoneCurrent` NA {n(pz[0])} ({pct(pz[0], pz[1])}).\n")
    if r[0] > 0.2 * ncf:
        issues.append(f"`floodZoneCurrent` est NA pour {pct(r[0], ncf)} des sinistres filtrés "
                      f"(contre {pct(r[1], ncf)} pour `ratedFloodZone`) : flood_zone_group serait "
                      "majoritairement manquant.")

    # ---------------------------------------------------------------- 8. dates, doublons
    w("## 8. Dates, âge du bâtiment, doublons, effectifs\n")
    r = q1("SELECT count(*) FILTER (WHERE dateOfLoss IS NULL), "
           "count(*) FILTER (WHERE yearOfLoss IS NULL), "
           "count(*) FILTER (WHERE yearOfLoss <> year(dateOfLoss)) FROM claims_f")
    w(f"- `dateOfLoss` : type {ctypes.loc['dateOfLoss', 'column_type']} ; NA {n(r[0])} ; "
      f"`yearOfLoss` NA {n(r[1])} ; `yearOfLoss` ≠ année de `dateOfLoss` : {n(r[2])}.")
    if r[0] > 0.001 * ncf:
        issues.append(f"{n(r[0])} `dateOfLoss` manquantes.")
    r = q1("SELECT count(*) FILTER (WHERE originalConstructionDate IS NULL), "
           "count(*) FILTER (WHERE year(originalConstructionDate) > yearOfLoss), "
           "count(*) FILTER (WHERE year(originalConstructionDate) < 1800), "
           "count(*) FILTER (WHERE year(originalConstructionDate) = yearOfLoss) FROM claims_f")
    w(f"- `originalConstructionDate` : NA {n(r[0])} ; année > `yearOfLoss` (âge négatif) : {n(r[1])} ; "
      f"année < 1800 (implausible) : {n(r[2])} ; âge = 0 : {n(r[3])}.")
    if r[1]:
        issues.append(f"{n(r[1])} âges négatifs (construction postérieure au sinistre).")
    if r[2]:
        issues.append(f"{n(r[2])} dates de construction antérieures à 1800, dont la sentinelle 1492-10-12 : "
                      "building_age serait d'environ 500 ans. À mettre en NA (et compter) ou écarter ?")
    neg = qdf("SELECT yearOfLoss - year(originalConstructionDate) AS age, count(*) AS lignes FROM claims_f "
              "WHERE year(originalConstructionDate) > yearOfLoss GROUP BY 1 ORDER BY 1 DESC LIMIT 10")
    if len(neg):
        w("\nÂges négatifs les plus fréquents :\n"); w(md_table(neg))
    old = qdf("SELECT originalConstructionDate, count(*) AS lignes FROM claims_f "
              "WHERE year(originalConstructionDate) < 1800 GROUP BY 1 ORDER BY 1")
    if len(old):
        w("\nDates de construction < 1800 :\n"); w(md_table(old))
        s1492 = q1("SELECT count(*), count(*) FILTER (WHERE occupancyType = 1) FROM claims_f "
                   "WHERE originalConstructionDate = DATE '1492-10-12'")
        w(f"\n- 12/10/1492 ({n(s1492[0])} lignes, dont {n(s1492[1])} en `occupancyType` = 1) est une "
          "valeur sentinelle (« date inconnue »), pas une vraie date.")

    all_cols = [c for c in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{cfg['claims_file']}')")
                .df()["column_name"] if c != "id"]
    raw_f = f"(SELECT * FROM read_parquet('{cfg['claims_file']}') WHERE {OCC_FILTER})"
    r_id = q1(f"SELECT count(*) - count(DISTINCT id), count(*) FILTER (WHERE id IS NULL) FROM claims_f")
    group_all = ", ".join(f'"{c}"' for c in all_cols)
    r_full = q1(f"SELECT coalesce(sum(k - 1), 0), count(*) FROM (SELECT count(*) k FROM {raw_f} "
                f"GROUP BY {group_all} HAVING k > 1)")
    r_key = q1("SELECT coalesce(sum(k - 1), 0) FROM (SELECT count(*) k FROM claims_f GROUP BY dateOfLoss, "
               "countyCode, amountPaidOnBuildingClaim, totalBuildingInsuranceCoverage, originalConstructionDate, "
               "buildingPropertyValue HAVING k > 1 AND min(amountPaidOnBuildingClaim) > 0)")
    w(f"\n- Doublons d'`id` : {n(r_id[0])} ; `id` NA : {n(r_id[1])}.")
    w(f"- Lignes identiques sur les {len(all_cols)} autres colonnes du fichier brut : "
      f"{n(r_full[0])} lignes en trop ({n(r_full[1])} groupes).")
    w(f"- Indicatif : lignes payées partageant date, comté, montant payé, couverture, date de construction "
      f"et valeur du bien : {n(r_key[0])} en trop (doublons possibles, non certains).")
    if r_full[0]:
        issues.append(f"{n(r_full[0])} sinistres en double exact (hors `id`).")
    w(f"\n**Effectifs** : {n(nc)} sinistres dans le fichier → {n(ncf)} après "
      f"`occupancyType ∈ {cfg['occupancy_keep']}` ({pct(ncf, nc)}). "
      f"`occupancyType` NA ou non entier : {n(q1(f'SELECT count(*) FROM claims WHERE {OCC_INT} IS NULL')[0])}.\n")

    # ---------------------------------------------------------------- 9. polices
    w("## 9. Polices : nature des lignes, exposition\n")
    r = q1("SELECT count(*), count(DISTINCT id), count(*) FILTER (WHERE policyCount > 1), sum(policyCount), "
           "count(*) FILTER (WHERE policyCount IS NULL OR policyCount <= 0), "
           "count(*) FILTER (WHERE endorsementEffectiveDate IS NOT NULL), "
           "count(*) FILTER (WHERE cancellationDateOfFloodPolicy IS NOT NULL) FROM policies_f")
    w(f"- Après filtre bâtiment : {n(npf)} lignes sur {n(np_)} ({pct(npf, np_)}) ; `id` distincts : {n(r[1])}.")
    w(f"- `policyCount` > 1 : {n(r[2])} lignes ; somme de `policyCount` : {n(r[3])} ; "
      f"`policyCount` NA ou ≤ 0 : {n(r[4])}.")
    w(f"- `endorsementEffectiveDate` renseignée : {n(r[5])} ({pct(r[5], npf)}) ; "
      f"`cancellationDateOfFloodPolicy` renseignée : {n(r[6])} ({pct(r[6], npf)}).")
    dur = qdf("""SELECT CASE WHEN policyTerminationDate IS NULL OR policyEffectiveDate IS NULL THEN 'date NA'
                             WHEN policyTerminationDate <= policyEffectiveDate THEN 'fin <= début'
                             WHEN date_diff('day', policyEffectiveDate, policyTerminationDate) <= 366 THEN '<= 1 an'
                             WHEN date_diff('day', policyEffectiveDate, policyTerminationDate) <= 1096 THEN '1 à 3 ans'
                             ELSE '> 3 ans' END AS duree, count(*) AS lignes
                 FROM policies_f GROUP BY 1 ORDER BY 2 DESC""")
    w("\nDurée `policyTerminationDate − policyEffectiveDate` :\n"); w(md_table(dur))
    term = qdf("SELECT policyTermIndicator, count(*) AS lignes FROM policies_f GROUP BY 1 ORDER BY 2 DESC")
    w("\n`policyTermIndicator` :\n"); w(md_table(term))
    # Chevauchements : même bien probable (clé approchée) avec périodes qui se recouvrent
    ov = q1("""SELECT count(*) FILTER (WHERE prev_end > policyEffectiveDate), count(*) FROM (
                 SELECT policyEffectiveDate, lag(policyTerminationDate) OVER (
                   PARTITION BY censusGeoid, latitude, longitude, originalNBDate, originalConstructionDate,
                                ratedFloodZone, totalBuildingInsuranceCoverage
                   ORDER BY policyEffectiveDate, policyTerminationDate) AS prev_end
                 FROM policies_f)""")
    same = q1("""SELECT coalesce(sum(k - 1), 0) FROM (SELECT count(*) k FROM policies_f
                 GROUP BY censusGeoid, latitude, longitude, originalNBDate, originalConstructionDate,
                          ratedFloodZone, totalBuildingInsuranceCoverage, policyEffectiveDate, policyTerminationDate
                 HAVING k > 1)""")
    w(f"\n- Double comptage potentiel (clé approchée : bloc de recensement, coordonnées, date de 1re souscription, "
      f"date de construction, zone tarifée, couverture) : lignes avec mêmes dates de début et de fin : "
      f"{n(same[0])} en trop ; périodes qui chevauchent la ligne précédente du même bien : {n(ov[0])} "
      f"({pct(ov[0], ov[1])}).")
    w("  *Sans identifiant de police (caviardé), ce contrôle ne peut être qu'indicatif : deux maisons "
      "voisines peuvent partager la clé.*")
    ey = qdf(f"""SELECT year(policyEffectiveDate) AS annee_effet, count(*) AS lignes,
                        count(*) FILTER (WHERE policyTerminationDate > DATE '{extraction.date()}') AS fin_apres_extraction
                 FROM policies_f GROUP BY 1 ORDER BY 1""")
    w("\nLignes par année de prise d'effet :\n"); w(md_table(ey))
    r = q1(f"SELECT count(*) FILTER (WHERE policyEffectiveDate > DATE '{extraction.date()}'), "
           f"count(*) FILTER (WHERE policyTerminationDate > DATE '{extraction.date()}') FROM policies_f")
    w(f"\n- Date d'extraction : {extraction.date()}. Prises d'effet postérieures : {n(r[0])} ; "
      f"fins postérieures : {n(r[1])}. Les années {extraction.year - 1} et {extraction.year} "
      "(et au-delà) sont donc partielles en exposition, sous réserve du délai de saisie.\n")

    # ---------------------------------------------------------------- 10. valeur du bien
    w("## 10. `buildingPropertyValue` (information)\n")
    bp = qdf("""SELECT CASE WHEN amountPaidOnBuildingClaim IS NULL THEN 'paiement NA'
                            WHEN amountPaidOnBuildingClaim > 0 THEN 'payé' ELSE 'non payé (0)' END AS statut,
                       count(*) AS lignes,
                       round(100 * avg((buildingPropertyValue IS NULL)::INT), 2) AS "% NA valeur",
                       median(buildingPropertyValue) AS "valeur médiane"
                FROM claims_f GROUP BY 1 ORDER BY 1""")
    r = q1("SELECT count(*) FILTER (WHERE buildingPropertyValue IS NULL) FROM claims_f")
    w(f"- NA global : {n(r[0])} ({pct(r[0], ncf)}).\n"); w(md_table(bp))
    w("\n*Si les NA de la valeur du bien coïncident avec les dossiers non payés, la variable "
      "est renseignée par l'expert lors du sinistre (risque de fuite), ce que le test prévu devra trancher.*\n")

    # ---------------------------------------------------------------- 11. CPI
    w("## 11. Fichier CPI (`" + cfg["cpi_file"].name + "`)\n")
    cpi, meta, sheets, hdr, hdr_i = load_cpi(cfg["cpi_file"])
    w(f"- Feuilles : {sheets}")
    w(f"- En-têtes de métadonnées : " + "; ".join(f"{k} = {v}" if v is not None else k for k, v in meta.items()))
    w(f"- Ligne d'en-tête du tableau (ligne {hdr_i + 1}) : {hdr}")
    w("- Format **large** : une ligne par année, une colonne par mois (+ moyennes semestrielles HALF1/HALF2, "
      "à ignorer).")
    w("- Unité : indice, base 1982-84 = 100 (pas un taux d'inflation).")
    avail = cpi.dropna(subset=["cpi"])
    first, last = avail["mois"].min(), avail["mois"].max()
    inside = cpi[(cpi["mois"] >= first) & (cpi["mois"] <= last) & cpi["cpi"].isna()]
    w(f"- Premier mois : {first} ; dernier mois : {last} (CPI = {avail.set_index('mois').loc[last, 'cpi']}).")
    w(f"- Mois manquants entre le premier et le dernier : "
      f"{', '.join(f'{m} (valeur brute {b})' for m, b in zip(inside['mois'], inside['brut'])) or 'aucun'}.")
    gap_claims = q1("SELECT count(*) FROM claims_f WHERE " + (" OR ".join(
        f"(year(dateOfLoss)={m.year} AND month(dateOfLoss)={m.month})" for m in inside["mois"]) or "FALSE"))[0]
    after = q1(f"SELECT count(*) FROM claims_f WHERE dateOfLoss > DATE '{last.end_time.date()}'")[0]
    before = q1(f"SELECT count(*) FROM claims_f WHERE dateOfLoss < DATE '{first.start_time.date()}'")[0]
    w(f"- Sinistres filtrés dont le mois de `dateOfLoss` n'a pas de CPI : {n(gap_claims)} "
      f"(mois manquants) + {n(before)} (avant {first}) + {n(after)} (après {last}).\n")
    if not inside.empty:
        issues.append(f"CPI manquant pour {', '.join(map(str, inside['mois']))} : "
                      f"{n(gap_claims)} sinistres concernés ; l'assert « tous les mois trouvés » échouerait.")

    # ---------------------------------------------------------------- conclusion
    w("## Conclusion\n")
    if region_ok:
        w("**Les données correspondent à la Région IV** : les deux fichiers contiennent exactement "
          "AL, FL, GA, KY, MS, NC, SC, TN, sans État hors Région IV ni État manquant.\n")
    else:
        w("**Les données ne correspondent pas à la Région IV** : voir § 2.\n")
        issues.insert(0, "Les États présents ne correspondent pas exactement à la Région IV.")
    if issues:
        w("### Points nécessitant une décision avant la phase 2\n")
        for i, s in enumerate(issues, 1):
            w(f"{i}. {s}")
    else:
        w("Aucune anomalie significative.")
    w("")

    path = cfg["out_dir"] / "audit_report.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"Rapport écrit : {path}")
    print(f"Sinistres {n(nc)} → {n(ncf)} après filtre ; polices {n(np_)} → {n(npf)}")
    print("Région IV :", "OK" if region_ok else "ÉCART")
    for s in issues:
        print(" -", s)


# =============================================================================
# PHASE 2 : NETTOYAGE (à écrire après validation de l'audit)
# =============================================================================
# Colonnes finales : (nom, colonne(s) brute(s), transformation, famille, rôle).
# L'ordre de cette liste est l'ordre des colonnes de claims_clean.parquet.
FINAL_SPEC = [
    ("paid_flag", "amountPaidOnBuildingClaim, netBuildingPaymentAmount",
     "> 0 → vrai ; = 0 → faux ; NA avec paiement net = 0 → faux (dossier clos sans paiement) ; sinon NA",
     "paiements", "cible"),
    ("paid_building_real", "amountPaidOnBuildingClaim, dateOfLoss",
     "montant × CPI_base / CPI(mois du sinistre) si paid_flag vrai, sinon NA", "paiements", "cible"),
    ("building_coverage", "totalBuildingInsuranceCoverage", "aucune (dollars nominaux)",
     "couverture et franchise", "ensemble A"),
    ("deductible_amount", "buildingDeductibleCode", "code → dollars (CONFIG deductible_map)",
     "couverture et franchise", "ensemble A"),
    ("flood_zone_group", "ratedFloodZone", "regroupement A*, V*, X (X, B, C), D, autre (CONFIG flood_zone_groups)",
     "zone d'inondation", "ensemble A"),
    ("foundation_type", "foundationType", "code catégoriel ; 0 → « non renseigné »", "bâtiment", "ensemble A"),
    ("elevated_building", "elevatedBuildingIndicator", "booléen nullable", "bâtiment", "ensemble A"),
    ("building_age", "yearOfLoss, originalConstructionDate",
     "yearOfLoss − année de construction ; NA si date manquante, sentinelle 1492-10-12 ou année < 1700",
     "bâtiment", "ensemble A"),
    ("n_floors", "numberOfFloorsInTheInsuredBuilding", "code catégoriel (pas un nombre)", "bâtiment", "ensemble A"),
    ("primary_residence", "primaryResidenceIndicator", "booléen nullable", "bâtiment", "ensemble A"),
    ("county_fips", "countyCode", "texte de 5 caractères, zéros initiaux conservés", "géographie", "ensemble A"),
    ("loss_year", "yearOfLoss", "aucune", "événement", "ensemble A"),
    ("rating_system", "occupancyType", "1 → ancien (1) ; 11 → Risk Rating 2.0 (11)", "tarification", "ensemble A"),
    ("water_depth", "waterDepth",
     "-999 → NA (valeur sentinelle supposée, non documentée) ; autres valeurs négatives conservées ; "
     "unité mixte possible (pouces ou pieds selon le dossier, d'après le dictionnaire v3), non convertie",
     "événement", "ensemble B"),
    ("flood_duration", "floodWaterDuration",
     "999 → NA (valeur sentinelle supposée, non documentée) ; zéros conservés", "événement", "ensemble B"),
    ("floodEvent", "floodEvent", "aucune", "événement", "groupe"),
    ("building_coverage_real", "totalBuildingInsuranceCoverage, dateOfLoss",
     "× CPI_base / CPI(mois du sinistre)", "couverture et franchise", "ensemble A"),
    ("deductible_amount_real", "buildingDeductibleCode, dateOfLoss",
     "deductible_amount × CPI_base / CPI(mois du sinistre)", "couverture et franchise", "ensemble A"),
    ("buildingPropertyValue", "buildingPropertyValue", "aucune (candidat ensemble A, en attente d'un test)",
     "expertise", "contrôle"),
    ("state", "state", "aucune", "géographie", "contrôle"),
    ("loss_month_period", "dateOfLoss", "mois de dateOfLoss (période mensuelle, clé du CPI)", "événement", "contrôle"),
    ("id", "id", "aucune", "administratif", "contrôle"),
    ("paid_na_to_zero", "amountPaidOnBuildingClaim, netBuildingPaymentAmount",
     "vrai si paid_flag a été mis à faux à partir d'un paiement NA", "paiements", "contrôle"),
]
FINAL_COLUMNS = [s[0] for s in FINAL_SPEC]

ZONE_YEAR_SPEC = [
    ("flood_zone_group", "ratedFloodZone", "même regroupement que les sinistres", "zone d'inondation", "clé"),
    ("county_fips", "censusGeoid", "5 premiers caractères", "géographie", "clé"),
    ("year", "policyEffectiveDate, policyTerminationDate", "année civile couverte", "période", "clé"),
    ("policy_years", "policyCount, policyEffectiveDate, policyTerminationDate",
     "Σ policyCount × jours couverts dans l'année / 365,25", "exposition", "exposition"),
    ("building_coverage_years", "totalBuildingInsuranceCoverage",
     "Σ couverture × jours couverts dans l'année / 365,25 (dollars-années)", "exposition", "exposition"),
    ("premium_earned", "totalInsurancePremiumOfThePolicy",
     "Σ prime × jours couverts dans l'année / durée du contrat (prime acquise)", "prime", "exposition"),
    ("n_policy_rows", "id", "nombre de lignes de police touchant l'année", "exposition", "contrôle"),
    ("partial_year", "policyEffectiveDate, asOfDate", "année à exposition incomplète", "période", "contrôle"),
    ("partial_reason", "policyEffectiveDate, asOfDate", "motif de l'incomplétude", "période", "contrôle"),
]


def load_claims(con):
    """Lit les sinistres filtrés (maisons individuelles), repère les anomalies et calcule paid_flag.
    Partagé par la phase de nettoyage et par le diagnostic des sentinelles, pour qu'ils portent
    exactement sur les mêmes lignes. Les valeurs renvoyées dans `m` sont brutes (avant sentinelles)."""
    from types import SimpleNamespace
    cfg = CONFIG
    raw_c = f"read_parquet('{cfg['claims_file']}')"
    zc = cfg["flood_zone_column_claims"]
    q1 = lambda s: con.execute(s).fetchone()
    raw_cols = con.execute(f"DESCRIBE SELECT * FROM {raw_c}").df()["column_name"].tolist()
    part_all = ", ".join(f'"{c}"' for c in raw_cols if c != "id")
    sentinels = ", ".join(f"DATE '{d}'" for d in cfg["construction_sentinels"])
    n_raw = q1(f"SELECT count(*) FROM {raw_c}")[0]
    n_occ_na = q1(f"SELECT count(*) FROM {raw_c} WHERE {OCC_INT} IS NULL")[0]
    # Les dates restent côté DuckDB (pandas ne gère pas les années < 1677 en nanosecondes)
    df = con.execute(f"""
        SELECT id, state, yearOfLoss, strftime(dateOfLoss, '%Y-%m') AS loss_month,
               {OCC_INT} AS occ,
               CAST(amountPaidOnBuildingClaim AS DOUBLE) AS paid,
               CAST(netBuildingPaymentAmount AS DOUBLE) AS net_paid,
               totalBuildingInsuranceCoverage AS cov, buildingDeductibleCode AS ded_code,
               {zc} AS zone_raw, {zone_group_sql(zc)} AS zone_group,
               foundationType AS fnd, elevatedBuildingIndicator AS elev,
               year(originalConstructionDate) AS constr_year,
               coalesce(originalConstructionDate IN ({sentinels}), FALSE) AS constr_sentinel,
               CAST(numberOfFloorsInTheInsuredBuilding AS VARCHAR) AS floors,
               primaryResidenceIndicator AS prim, countyCode, waterDepth, floodWaterDuration,
               floodEvent, buildingPropertyValue, elevationDifference,
               row_number() OVER (PARTITION BY {part_all} ORDER BY id) AS dup_rank
        FROM {raw_c} WHERE {OCC_FILTER}""").df()
    for c in ["waterDepth", "floodWaterDuration", "buildingPropertyValue", "elevationDifference", "cov"]:
        df[c] = df[c].astype("Int64")

    # Anomalies (lignes écartées du dataset principal)
    ded_map = cfg["deductible_map"]
    fnd_ok = set(cfg["foundation_codes"]) | {cfg["foundation_missing_code"]}
    age_ok = (df["constr_year"].notna() & ~df["constr_sentinel"].astype(bool)
              & (df["constr_year"] >= cfg["construction_min_year"]))
    conds = pd.DataFrame({
        "paiement négatif": df["paid"] < 0,
        "âge négatif": age_ok & (df["constr_year"] > df["yearOfLoss"]),
        "doublon exact": df["dup_rank"] > 1,
        "paiement sans couverture": (df["paid"] > 0) & (df["cov"] == 0),
        "code hors table (franchise)": df["ded_code"].notna() & ~df["ded_code"].isin(ded_map),
        "code hors table (fondation)": df["fnd"].notna() & ~df["fnd"].isin(fnd_ok),
        "code hors table (étages)": df["floors"].notna() & ~df["floors"].isin(cfg["floors_codes"]),
    }).fillna(False).astype(bool)
    motif = conds.dot(pd.Index(conds.columns + "; ")).str.rstrip("; ")
    is_anom = conds.any(axis=1)
    m = df.loc[~is_anom].reset_index(drop=True)
    age_ok = age_ok[~is_anom].reset_index(drop=True)

    # Cible binaire
    paid = m["paid"]
    paid_flag = pd.Series(pd.NA, index=m.index, dtype="boolean")
    paid_flag[paid > 0] = True
    paid_flag[paid == 0] = False
    recode = paid.isna() & (m["net_paid"] == 0) & cfg["paid_na_net_zero_is_unpaid"]
    paid_flag[recode] = False
    return SimpleNamespace(df=df, conds=conds, motif=motif, is_anom=is_anom, m=m, age_ok=age_ok,
                           paid_flag=paid_flag, recode=recode, n_raw=n_raw, n_occ_na=n_occ_na)


# =============================================================================
# DIAGNOSTIC DES VALEURS SENTINELLES (lecture seule)
# =============================================================================
SENTINEL_CANDIDATES = [-999, 999, 9999, 99999, 999999, 2147483647]
SWEEP_CANDIDATES = [-999, -99, -1, 999, 9999, 99999, 999999, 2147483647]


def sentinel_tables(m: pd.DataFrame, paid_flag: pd.Series, final_name: dict, sweep_cols: dict):
    """Construit le rapport de diagnostic des sentinelles. Renvoie la liste de lignes markdown
    et la liste des autres sentinelles détectées au balayage générique."""
    out = []
    w = out.append
    N = len(m)
    qs = [0.001, 0.01, 0.05, 0.5, 0.95, 0.99, 0.999]
    for raw, name in final_name.items():
        s = m[raw]
        v = s.dropna()
        w(f"## `{name}` (`{raw}`)\n")
        w(f"- Lignes : {n(N)} ; NA : {n(s.isna().sum())} ({pct(s.isna().sum(), N)}) ; "
          f"min {v.min()} ; max {v.max()} ; moyenne {v.astype(float).mean():,.1f} ; médiane {v.median()}"
          .replace(",", " "))
        qv = v.astype(float).quantile(qs)
        w("- Quantiles : " + " ; ".join(f"{100 * q:g} % = {x:,.0f}".replace(",", " ") for q, x in qv.items()))
        tab = pd.DataFrame({"valeur": SENTINEL_CANDIDATES,
                            "lignes": [int((s == x).sum()) for x in SENTINEL_CANDIDATES]})
        tab["part"] = [pct(k, N) for k in tab["lignes"]]
        w("\nValeurs sentinelles suspectes :\n"); w(md_table(tab))
        neg = v[(v < 0) & (v != -999)]
        w(f"\n- Valeurs négatives autres que −999 : {n(len(neg))}"
          + (f" ({', '.join(f'{k} : {n(c)}' for k, c in neg.value_counts().sort_index().items())})"
             if len(neg) else ""))
        w(f"- Zéros : {n((v == 0).sum())} ({pct((v == 0).sum(), N)} des lignes, "
          f"{pct((v == 0).sum(), len(v))} des valeurs renseignées)")
        if raw == "waterDepth":
            w("- " + " ; ".join(f"> {t} : {n((v > t).sum())}" for t in [300, 500, 900]) + " (hors 999 : "
              f"> 900 et ≠ 999 : {n(((v > 900) & (v != 999)).sum())})")
            big = v[v > 300].value_counts().sort_index()
            w(f"- Valeurs > 300 : {', '.join(f'{k} ({c})' for k, c in big.items())}")
        if raw == "floodWaterDuration":
            w("- " + " ; ".join(f"> {t} h : {n((v > t).sum())}" for t in [168, 720]) +
              f" ; = 999 : {n((v == 999).sum())} ; > 999 : {n((v > 999).sum())}")
            big = v[v > 168].value_counts().sort_index()
            w(f"- Valeurs > 168 : {', '.join(f'{k} ({c})' for k, c in big.items())}")
        if raw == "buildingPropertyValue":
            w(f"- Exactement 2 147 483 647 : {n((v == 2147483647).sum())}")
            vv = v[v != 2147483647]
            for t in [1_000_000, 5_000_000, 10_000_000]:
                k = int((vv > t).sum())
                w(f"- > {t / 1e6:g} M$ (hors 2 147 483 647) : {n(k)} ({pct(k, N)} des lignes)")
            top = vv.sort_values(ascending=False).head(15)
            w(f"- 15 plus grandes valeurs (hors 2 147 483 647) : {', '.join(n(x) for x in top)}")
            w(f"- Moyenne / médiane avec la sentinelle : {v.astype(float).mean():,.0f} / {v.median():,.0f} ; "
              f"sans : {vv.astype(float).mean():,.0f} / {vv.median():,.0f}".replace(",", " "))
            # Structure des valeurs élevées : tranches, rapport à la couverture, années
            ratio = vv.astype(float) / m.loc[vv.index, "cov"].astype(float).replace(0, float("nan"))
            edges = [1e6, 1e7, 1e8, 1e9, 3e9]
            rows = []
            for lo, hi in zip(edges[:-1], edges[1:]):
                sel = (vv >= lo) & (vv < hi)
                idx = vv.index[sel.to_numpy()]
                rows.append([f"[{lo / 1e6:g} M$ ; {hi / 1e6:g} M$)", int(sel.sum()), pct(int(sel.sum()), N),
                             round(float(ratio[idx].median()), 1),
                             int(m.loc[idx, "cov"].median()),
                             f"{int(m.loc[idx, 'yearOfLoss'].quantile(.1))}–{int(m.loc[idx, 'yearOfLoss'].quantile(.9))}",
                             pct(int((vv[idx] % 100 == 0).sum()), len(idx))])
            w("\nStructure des valeurs élevées :\n")
            w(md_table(pd.DataFrame(rows, columns=["tranche", "lignes", "part", "médiane valeur / couverture",
                                                   "médiane couverture", "années (P10–P90)",
                                                   "multiples de 100"])))
            k10 = int((vv > 10_000_000).sum())
            k100 = int((vv >= 100_000_000).sum())
            keep = vv[vv <= 10_000_000].astype(float)
            status = ("appliqué dans `claims_clean.parquet` (CONFIG `property_value_max`)"
                      if CONFIG["property_value_max"] else "non appliqué")
            w(f"\n**Seuil proposé ({status}) : 10 M$.** Entre 1 et 10 M$, la valeur vaut en médiane "
              "≈ 6 fois la couverture, plafonnée à 250 000 $ pour une maison : c'est plausible pour des "
              "maisons côtières chères. Au-delà, le rapport valeur / couverture explose (≈ 90 entre 10 et "
              "100 M$, ≈ 6 000 au-delà de 100 M$). Les valeurs ≥ 100 M$ sont concentrées sur 1998–2001 et "
              "presque toutes multiples de 100 : cela évoque une erreur d'unité (cents ?) plutôt qu'une "
              f"sentinelle. Mettre en NA les valeurs > 10 M$ toucherait {n(k10)} lignes ({pct(k10, N)}) ; "
              f"moyenne / médiane après : {n(round(keep.mean()))} / {n(round(keep.median()))}. "
              f"Variante plus prudente : ≥ 100 M$ seulement ({n(k100)} lignes).")
        # Croisements avec paid_flag et loss_year pour chaque sentinelle présente
        for x in [c for c in SENTINEL_CANDIDATES if (s == c).any()]:
            hit = (s == x).fillna(False)
            pf = pd.DataFrame({"paid_flag": paid_flag.astype("object").fillna("NA").astype(str), "hit": hit})
            ct = pf.groupby("paid_flag")["hit"].agg(lignes="sum", total="size").reset_index()
            ct["part"] = [pct(a, b) for a, b in zip(ct["lignes"], ct["total"])]
            ct["lignes"] = ct["lignes"].astype(int)
            w(f"\n**{x} × paid_flag** (part des sinistres de chaque statut) :\n"); w(md_table(ct))
            yr = (pd.DataFrame({"loss_year": m["yearOfLoss"], "hit": hit}).groupby("loss_year")["hit"]
                  .agg(lignes="sum", total="size").reset_index())
            yr = yr[yr["lignes"] > 0]
            yr["part de l'année"] = [pct(a, b) for a, b in zip(yr["lignes"], yr["total"])]
            yr["lignes"] = yr["lignes"].astype(int)
            w(f"\n**{x} × loss_year** (années où la valeur apparaît) :\n")
            w(md_table(yr.drop(columns="total")))
        w("")

    # Balayage générique : valeurs « rondes » répétées anormalement souvent
    w("## Balayage générique\n")
    w(f"Valeurs examinées : {SWEEP_CANDIDATES}. Une valeur est signalée **anormale** si elle apparaît au "
      "moins 5 fois et plus de 5 fois plus souvent que la moyenne de ses deux voisines (v − 1 et v + 1). "
      "Les versions réelles (déflatées, non entières) ne sont pas balayées : leurs sources nominales le sont.\n")
    rows, others = [], []
    for name, s in sweep_cols.items():
        v = s.dropna().astype(float)
        vc = v.value_counts()
        for x in SWEEP_CANDIDATES:
            k = int(vc.get(float(x), 0))
            if not k:
                continue
            nb = (vc.get(float(x - 1), 0) + vc.get(float(x + 1), 0)) / 2
            flag = k >= 5 and k > 5 * max(nb, 1)
            rows.append([name, x, k, f"{nb:g}", "**oui**" if flag else "non"])
            if flag:
                others.append((name, x, k))
    w(md_table(pd.DataFrame(rows, columns=["colonne", "valeur", "lignes", "moyenne des voisines", "anormale"]))
      if rows else "Aucune des valeurs examinées n'apparaît.")
    w("")
    return out, others


def sentinels():
    check_inputs(["claims_file"])
    cfg = CONFIG
    con = connect()
    L = load_claims(con)
    m = L.m
    ded = m["ded_code"].map(cfg["deductible_map"]).astype("Int64")
    age = (m["yearOfLoss"] - m["constr_year"]).where(L.age_ok).astype("Int64")
    final_name = {"waterDepth": "water_depth", "floodWaterDuration": "flood_duration",
                  "buildingPropertyValue": "buildingPropertyValue"}
    sweep = {"amountPaidOnBuildingClaim (paiement nominal)": m["paid"],
             "totalBuildingInsuranceCoverage (building_coverage)": m["cov"],
             "deductible_amount": ded, "building_age": age, "loss_year": m["yearOfLoss"],
             "water_depth": m["waterDepth"], "flood_duration": m["floodWaterDuration"],
             "buildingPropertyValue": m["buildingPropertyValue"],
             "elevationDifference (non retenue)": m["elevationDifference"]}
    body, others = sentinel_tables(m, L.paid_flag, final_name, sweep)
    head = ["# Diagnostic des valeurs sentinelles\n",
            "> Lecture seule. Généré par `clean_data.py sentinels`. Population : les lignes de "
            f"`claims_clean.parquet` (maisons individuelles hors anomalies), soit {n(len(m))} sinistres, "
            "avec les valeurs **brutes** (avant toute correction de sentinelle).\n"]
    concl = ["## Autres sentinelles détectées au balayage\n"]
    targeted = {("water_depth", -999), ("flood_duration", 999), ("buildingPropertyValue", 2147483647)}
    rest = [(c, x, k) for c, x, k in others if (c, x) not in targeted]
    concl += [f"- `{c}` = {x} : {n(k)} lignes (non corrigé, à décider)" for c, x, k in rest] or \
             ["- Aucune en dehors des trois sentinelles visées."]
    (cfg["out_dir"] / "sentinel_report.md").write_text("\n".join(head + body + concl) + "\n", encoding="utf-8")
    print(f"Rapport écrit : {cfg['out_dir'] / 'sentinel_report.md'}")
    for c, x, k in others:
        print(f" - sentinelle détectée : {c} = {x} ({k} lignes)")


def clean():
    check_inputs(["claims_file", "policies_file", "cpi_file"])
    cfg = CONFIG
    con = connect()
    out = cfg["out_dir"]
    q1 = lambda s: con.execute(s).fetchone()
    raw_c = f"read_parquet('{cfg['claims_file']}')"
    raw_p = f"read_parquet('{cfg['policies_file']}')"
    zc, zp = cfg["flood_zone_column_claims"], cfg["flood_zone_column_policies"]
    check_columns(con, cfg["claims_file"], CLAIMS_REQUIRED, [zc, "netBuildingPaymentAmount"])
    check_columns(con, cfg["policies_file"], POLICIES_REQUIRED, [zp, "asOfDate"])
    # Nombre de lignes du claims_clean.parquet précédent (contrôle : aucune ligne supprimée)
    prev_path = out / "claims_clean.parquet"
    prev_rows = pq.ParquetFile(prev_path).metadata.num_rows if prev_path.exists() else None

    # ------------------------------------------------------------ lecture, anomalies, cibles
    L = load_claims(con)
    n_raw, n_occ_na, n_occ = L.n_raw, L.n_occ_na, len(L.df)
    conds, motif, is_anom = L.conds, L.motif, L.is_anom
    con.register("motifs", pd.DataFrame({"id": L.df.loc[is_anom, "id"], "motif": motif[is_anom]}))
    con.execute(f"COPY (SELECT r.*, m.motif FROM {raw_c} r JOIN motifs m USING (id) ORDER BY id) "
                f"TO '{out / 'claims_anomalies.parquet'}' (FORMAT parquet)")
    anom_by_motif = conds[is_anom].sum()
    anom_combo = motif[is_anom].value_counts()
    m, age_ok, paid_flag, recode = L.m, L.age_ok, L.paid_flag, L.recode
    ded_map = cfg["deductible_map"]
    fnd_ok = set(cfg["foundation_codes"]) | {cfg["foundation_missing_code"]}
    paid = m["paid"]
    n_paid_na_left = int(paid_flag.isna().sum())

    # ------------------------------------------------------------ valeurs sentinelles -> NA
    # Hypothèses non documentées par FEMA (CONFIG["sentinel_to_na"]) ; aucune ligne supprimée.
    sent_stats = {}
    rules = dict(cfg["sentinel_to_na"])
    cond_rules = {}   # règles conditionnelles : col -> (codes, lignes trouvées, appliquée ?)
    for col, r_ in cfg["sentinel_to_na_if_frequent"].items():
        k = int(m[col].isin(r_["codes"]).sum())
        cond_rules[col] = (r_["codes"], k, k >= r_["min_rows"])
        if k >= r_["min_rows"]:
            rules[col] = r_["codes"]
    # Colonnes des règles non appliquées : statistiques calculées quand même (avant = après)
    for col in list(rules) + [c for c in cond_rules if c not in rules]:
        codes = rules.get(col, [])
        before = m[col].copy()
        hit = before.isin(codes)
        m[col] = before.mask(hit)
        sent_stats[col] = dict(codes=codes, n=int(hit.sum()), na_before=int(before.isna().sum()),
                               na_after=int(m[col].isna().sum()),
                               min_b=before.min(), max_b=before.max(), mean_b=before.mean(), med_b=before.median(),
                               min_a=m[col].min(), max_a=m[col].max(), mean_a=m[col].mean(), med_a=m[col].median())

    # Seuil des valeurs extrêmes de buildingPropertyValue (hypothèse non documentée, CONFIG)
    pv_max = cfg["property_value_max"]
    if pv_max is not None:
        before = m["buildingPropertyValue"].copy()
        hit = (before > pv_max).fillna(False)
        m["buildingPropertyValue"] = before.mask(hit)
        a = m["buildingPropertyValue"]
        sent_stats["buildingPropertyValue>max"] = dict(
            codes=[f"> {n(pv_max)}"], n=int(hit.sum()), na_before=int(before.isna().sum()),
            na_after=int(a.isna().sum()), min_b=before.min(), max_b=before.max(), mean_b=before.mean(),
            med_b=before.median(), min_a=a.min(), max_a=a.max(), mean_a=a.mean(), med_a=a.median())

    # ------------------------------------------------------------ CPI
    cpi, meta, *_ = load_cpi(cfg["cpi_file"])
    cpi_av = cpi.dropna(subset=["cpi"])
    base_month = pd.Period(cfg["cpi_base"], freq="M") if cfg["cpi_base"] else cpi_av["mois"].max()
    cpi_base = float(cpi_av.set_index("mois").loc[base_month, "cpi"])
    m["loss_month_period"] = pd.to_datetime(m["loss_month"], format="%Y-%m").dt.to_period("M")
    m = m.merge(cpi[["mois", "cpi"]], left_on="loss_month_period", right_on="mois",
                how="left", validate="m:1").drop(columns="mois")
    no_cpi = m["loss_month_period"].notna() & m["cpi"].isna()
    allowed = {pd.Period(x, freq="M") for x in cfg["cpi_months_missing_ok"]}
    bad_months = set(m.loc[no_cpi, "loss_month_period"]) - allowed
    assert not bad_months, f"Mois de sinistre sans CPI non autorisés : {sorted(map(str, bad_months))}"
    factor = cpi_base / m["cpi"]

    # ------------------------------------------------------------ dataset final
    ded_amount = m["ded_code"].map(ded_map).astype("Int64")
    assert ded_amount.isna().sum() <= m["ded_code"].isna().sum(), "La table des franchises a créé des NA"
    zone_cats = list(cfg["flood_zone_groups"]) + [cfg["flood_zone_other"]]
    fnd_labels = m["fnd"].replace({cfg["foundation_missing_code"]: cfg["missing_label"]})
    final = pd.DataFrame({
        "paid_flag": paid_flag,
        "paid_building_real": (paid * factor).where(paid_flag.fillna(False).astype(bool)).astype("Float64"),
        "building_coverage": m["cov"].astype("Int64"),
        "deductible_amount": ded_amount,
        "flood_zone_group": pd.Categorical(m["zone_group"], categories=zone_cats),
        "foundation_type": pd.Categorical(fnd_labels, categories=sorted(cfg["foundation_codes"])
                                          + [cfg["missing_label"]]),
        "elevated_building": m["elev"].astype("boolean"),
        "building_age": (m["yearOfLoss"] - m["constr_year"]).where(age_ok).astype("Int64"),
        "n_floors": pd.Categorical(m["floors"], categories=sorted(cfg["floors_codes"])),
        "primary_residence": m["prim"].astype("boolean"),
        "county_fips": pd.Categorical(m["countyCode"]),
        "loss_year": m["yearOfLoss"].astype("Int64"),
        "rating_system": pd.Categorical(m["occ"].map(cfg["rating_system_map"]),
                                        categories=list(cfg["rating_system_map"].values())),
        "water_depth": m["waterDepth"].astype("Int64"),
        "flood_duration": m["floodWaterDuration"].astype("Int64"),
        "floodEvent": pd.Categorical(m["floodEvent"]),
        "building_coverage_real": (m["cov"] * factor).astype("Float64"),
        "deductible_amount_real": (ded_amount.astype("Float64") * factor).astype("Float64"),
        "buildingPropertyValue": m["buildingPropertyValue"].astype("Int64"),
        "state": pd.Categorical(m["state"]),
        "loss_month_period": m["loss_month_period"],
        "id": m["id"].astype("Int64"),
        "paid_na_to_zero": recode.astype("boolean"),
    })[FINAL_COLUMNS]
    final.to_parquet(out / "claims_clean.parquet", index=False)

    # ------------------------------------------------------------ polices : zone × comté × année
    pol_view = f"""SELECT {zone_group_sql(zp)} AS flood_zone_group, left(censusGeoid, 5) AS county_fips,
                          policyEffectiveDate AS eff, policyTerminationDate AS term, policyCount AS pc,
                          totalBuildingInsuranceCoverage AS cov, totalInsurancePremiumOfThePolicy AS prem
                   FROM {raw_p} WHERE {OCC_FILTER}"""
    con.execute(f"CREATE TEMP VIEW pol AS {pol_view}")
    p = q1("""SELECT count(*), count(*) FILTER (WHERE term <= eff), min(eff), max(eff), max(term),
                     sum(pc * date_diff('day', eff, term) / 365.25) FILTER (WHERE term > eff),
                     sum(prem) FILTER (WHERE term > eff),
                     count(*) FILTER (WHERE pc <> 1), count(*) FILTER (WHERE prem < 0),
                     sum(prem) FILTER (WHERE prem < 0),
                     count(*) FILTER (WHERE flood_zone_group IS NULL), count(*) FILTER (WHERE county_fips IS NULL),
                     count(*) FILTER (WHERE term > eff AND date_diff('day', eff, term) <= 366)
              FROM pol""")
    (n_pol, n_pol_bad, min_eff, max_eff, max_term, py_expected, prem_expected,
     n_pc_not1, n_prem_neg, sum_prem_neg, n_pol_zone_na, n_pol_county_na, n_pol_1y) = p
    extraction = pd.Timestamp(q1(f"SELECT CAST(timezone('UTC', max(asOfDate)) AS VARCHAR) FROM {raw_p}")[0]).normalize()
    zy = con.execute("""
        WITH v AS (SELECT *, date_diff('day', eff, term) AS term_days FROM pol WHERE term > eff),
             y AS (SELECT *, unnest(range(year(eff), year(term - 1) + 1)) AS yr FROM v),
             o AS (SELECT *, date_diff('day', greatest(eff, make_date(yr::INT, 1, 1)),
                                       least(term, make_date(yr::INT + 1, 1, 1))) AS ov FROM y)
        SELECT flood_zone_group, county_fips, yr::INT AS year,
               sum(pc * ov / 365.25) AS policy_years,
               sum(cov * ov / 365.25) AS building_coverage_years,
               sum(prem * ov / term_days) AS premium_earned,
               count(*) AS n_policy_rows
        FROM o WHERE ov > 0 GROUP BY ALL ORDER BY 1, 2, 3""").df()
    first_year = pd.Timestamp(min_eff).year
    reason = pd.Series(pd.NA, index=zy.index, dtype="string")
    reason[zy["year"] == first_year] = (f"troncature à gauche : contrats ayant pris effet avant le "
                                        f"{pd.Timestamp(min_eff).date()} absents du fichier")
    reason[zy["year"] >= extraction.year] = f"postérieure à l'extraction du {extraction.date()}"
    zy["partial_year"] = reason.notna().astype("boolean")
    zy["partial_reason"] = pd.Categorical(reason)
    zy["flood_zone_group"] = pd.Categorical(zy["flood_zone_group"], categories=zone_cats)
    zy["county_fips"] = pd.Categorical(zy["county_fips"])
    zy["year"] = zy["year"].astype("Int64")
    for c in ["policy_years", "building_coverage_years", "premium_earned"]:
        zy[c] = zy[c].astype("Float64")
    zy["n_policy_rows"] = zy["n_policy_rows"].astype("Int64")
    zy.to_parquet(out / "zone_year.parquet", index=False)

    # Contrôles de double comptage (indicatifs : pas d'identifiant de police)
    dup_key = ("censusGeoid, latitude, longitude, originalNBDate, originalConstructionDate, ratedFloodZone, "
               "totalBuildingInsuranceCoverage, totalContentsInsuranceCoverage, totalInsurancePremiumOfThePolicy, "
               "buildingReplacementCost, numberOfFloorsInInsuredBuilding, elevatedBuildingIndicator")
    pol_dup = q1(f"""SELECT coalesce(sum(k - 1), 0), coalesce(sum((k - 1) * yrs), 0) FROM (
                       SELECT count(*) k, any_value(date_diff('day', policyEffectiveDate, policyTerminationDate)
                                                    / 365.25) yrs
                       FROM {raw_p} WHERE {OCC_FILTER}
                       GROUP BY {dup_key}, policyEffectiveDate, policyTerminationDate HAVING k > 1)""")
    pol_ids = q1(f"SELECT count(*) - count(DISTINCT id) FROM {raw_p} WHERE {OCC_FILTER}")[0]

    # ------------------------------------------------------------ contrôles automatiques
    chk = pd.read_parquet(out / "claims_clean.parquet")
    checks = []

    def check(cond, label):
        assert cond, f"Contrôle échoué : {label}"
        checks.append(label)

    check(list(chk.columns) == FINAL_COLUMNS, "aucune colonne hors liste dans claims_clean.parquet")
    check(chk.loc[chk["paid_flag"].fillna(True) == False, "paid_building_real"].isna().all(),
          "pas de paid_building_real quand paid_flag = 0")
    check(chk.loc[chk["paid_flag"].isna(), "paid_building_real"].isna().all(),
          "pas de paid_building_real quand paid_flag est NA")
    for c in ["paid_building_real", "building_coverage", "deductible_amount",
              "building_coverage_real", "deductible_amount_real"]:
        check(not (chk[c].dropna() < 0).any(), f"aucun montant négatif dans {c}")
    check(not (chk["building_age"].dropna() < 0).any(), "building_age >= 0")
    month_no_cpi = set(m.loc[no_cpi, "loss_month_period"])
    check(month_no_cpi <= allowed,
          "tous les mois de sinistre ont un CPI (hors mois déclarés manquants dans CONFIG)")
    check(m["ded_code"].dropna().isin(ded_map).all(), "codes de franchise tous dans la table")
    check(m["fnd"].dropna().isin(fnd_ok).all(), "codes de fondation tous dans la table (+ code 0)")
    check(m["floors"].dropna().isin(cfg["floors_codes"]).all(), "codes d'étages tous dans la table")
    check(chk["rating_system"].notna().all(), "rating_system défini pour toutes les lignes")
    check(chk["county_fips"].dropna().astype(str).str.fullmatch(r"\d{5}").all(), "county_fips sur 5 chiffres")
    check(chk["id"].is_unique, "id unique")
    check(set(chk["state"].dropna()) <= set(cfg["region_iv"]), "États tous dans la Région IV")
    check(n_occ == len(chk) + int(is_anom.sum()), "lignes filtrées = dataset final + anomalies")
    check(pd.read_parquet(out / "claims_anomalies.parquet", columns=["id"]).shape[0] == int(is_anom.sum()),
          "claims_anomalies.parquet contient toutes les lignes écartées")
    check(abs(zy["policy_years"].sum() - py_expected) < 1e-6 * py_expected,
          "polices-années conservées par la répartition en années civiles")
    check(abs(zy["premium_earned"].sum() - prem_expected) < 1e-6 * abs(prem_expected),
          "prime totale conservée par la répartition en années civiles")
    check(pol_ids == 0, "id de police unique (pas de ligne répétée)")
    # Sentinelles
    check(not (chk["water_depth"] == -999).any(), "plus de -999 dans water_depth")
    check(not (chk["flood_duration"] == 999).any(), "plus de 999 dans flood_duration")
    if cond_rules["buildingPropertyValue"][2]:
        check(not (chk["buildingPropertyValue"] == 2147483647).any(),
              "plus de 2147483647 dans buildingPropertyValue")
    if pv_max is not None:
        check(not (chk["buildingPropertyValue"] > pv_max).any(),
              f"plus de buildingPropertyValue > {n(pv_max)} $")
    check(len(chk) == len(L.m), "la correction des sentinelles ne supprime aucune ligne")
    if prev_rows is not None:
        check(len(chk) == prev_rows,
              f"nombre de lignes de claims_clean.parquet identique à la version précédente ({n(prev_rows)})")

    # ------------------------------------------------------------ dictionnaire de données
    dd = pd.DataFrame(
        [("claims_clean.parquet", s[0], str(chk[s[0]].dtype), *s[1:]) for s in FINAL_SPEC]
        + [("zone_year.parquet", s[0], str(zy[s[0]].dtype), *s[1:]) for s in ZONE_YEAR_SPEC],
        columns=["fichier", "nom", "type", "colonne_brute", "transformation", "famille", "role"])
    # Transformation de buildingPropertyValue : dépend de l'application effective de la règle
    codes_b, k_b, applied_b = cond_rules["buildingPropertyValue"]
    dd.loc[(dd["fichier"] == "claims_clean.parquet") & (dd["nom"] == "buildingPropertyValue"), "transformation"] = (
        (f"{codes_b[0]} → NA (valeur sentinelle supposée, non documentée)" if applied_b else
         f"règle {codes_b[0]} → NA (valeur sentinelle supposée, non documentée) non appliquée : "
         f"valeur présente {k_b} fois")
        + (f" ; valeurs > {pv_max} → NA (seuil supposé, non documenté : erreur d'unité probable)"
           if pv_max is not None else " ; valeurs > 10 M$ suspectes, seuil proposé non appliqué")
        + " ; candidat ensemble A en attente d'un test")
    dd.to_csv(out / "data_dictionary.csv", index=False)

    # ------------------------------------------------------------ rapport
    r = []
    w = r.append
    nf = len(chk)
    w("# Rapport de nettoyage (phase 2) : sinistres NFIP, Région IV\n")
    w("> Généré par `clean_data.py clean`. Fichiers bruts lus en lecture seule. "
      "Audit préalable : `audit_report.md`.\n")
    w("## 1. Paramètres retenus (CONFIG)\n")
    w(f"- Sinistres : `{cfg['claims_file'].name}` ; polices : `{cfg['policies_file'].name}` ; "
      f"CPI : `{cfg['cpi_file'].name}`.")
    w(f"- Filtre bâtiment : `occupancyType ∈ {cfg['occupancy_keep']}` (maisons individuelles).")
    w(f"- Système de tarification (`rating_system`) : {cfg['rating_system_map']} : les codes à 2 chiffres "
      "sont ceux de Risk Rating 2.0 (dictionnaire OpenFEMA v3).")
    w(f"- Zones : colonne `{zc}` (sinistres) et `{zp}` (polices). Regroupement :")
    for g, zones in cfg["flood_zone_groups"].items():
        w(f"  - {g} : {', '.join(zones)}")
    w(f"  - {cfg['flood_zone_other']} : tout autre code non manquant ; NA reste NA.")
    w(f"- Franchises : {cfg['deductible_map']}.")
    w(f"- CPI : série **{meta.get('Series Id')}** ({meta.get('Series Title')}), base {meta.get('Base Period')}. "
      f"**CPI_base = {base_month} ({cpi_base})**. Mois tolérés sans CPI : {cfg['cpi_months_missing_ok']}.")
    w(f"- Dates de construction inutilisables (→ `building_age` NA) : sentinelles {cfg['construction_sentinels']} "
      f"et années < {cfg['construction_min_year']}.")
    w("- `elevationDifference` abandonnée (58 % de NA, décision 10) : pas de `elevation_band`.")
    w("- `paid_flag` : paiement NA avec paiement net nul → faux (dossier clos sans paiement), "
      "signalé par `paid_na_to_zero`.\n")

    w("## 2. Effectifs à chaque étape\n")
    steps = pd.DataFrame([
        ["Fichier brut", n_raw],
        [f"occupancyType ∈ {cfg['occupancy_keep']}", n_occ],
        ["Lignes écartées (anomalies)", int(is_anom.sum())],
        ["**claims_clean.parquet**", nf],
    ], columns=["étape", "lignes"])
    w(md_table(steps))
    w(f"\n`occupancyType` NA ou non entier dans le fichier brut : {n(n_occ_na)} (exclues par le filtre).\n")

    w("## 3. Anomalies écartées → `claims_anomalies.parquet`\n")
    w("Une ligne peut cumuler plusieurs motifs. Le fichier contient toutes les colonnes brutes + `motif`.\n")
    w(md_table(anom_by_motif.rename_axis("motif").reset_index(name="lignes")))
    w("\nCombinaisons de motifs :\n")
    w(md_table(anom_combo.rename_axis("motif").reset_index(name="lignes")))
    w("\n*Montants négatifs : selon le dictionnaire v3, ils correspondent à des chèques non encaissés puis "
      "réémis. Doublons exacts : la ligne au plus petit `id` est conservée.*\n")

    w("## 4. Recodages et valeurs manquantes signalés\n")
    w(f"- `paid_flag` : vrai {n((chk['paid_flag'] == True).sum())}, faux {n((chk['paid_flag'] == False).sum())} "
      f"(dont {n(recode.sum())} issus d'un paiement NA avec net nul), NA {n(n_paid_na_left)}.")
    w(f"- `foundation_type` = « {cfg['missing_label']} » (code 0) : {n((fnd_labels == cfg['missing_label']).sum())} "
      f"lignes ; toutes en `rating_system` = ancien : "
      f"{n(((fnd_labels == cfg['missing_label']) & (m['occ'] == 1)).sum())}.")
    w(f"- `building_age` NA : {n(chk['building_age'].isna().sum())}, dont date manquante "
      f"{n(m['constr_year'].isna().sum())}, sentinelle 1492-10-12 {n(m['constr_sentinel'].astype(bool).sum())}, "
      f"année < {cfg['construction_min_year']} (hors sentinelle) "
      f"{n(((m['constr_year'] < cfg['construction_min_year']) & ~m['constr_sentinel'].astype(bool)).sum())}.")
    w(f"- Sinistres sans CPI (mois {', '.join(sorted(map(str, month_no_cpi))) or 'aucun'}) : {n(no_cpi.sum())} → "
      "`paid_building_real`, `building_coverage_real`, `deductible_amount_real` NA.")
    zv = m.groupby("zone_raw", dropna=False).size()
    other_codes = m.loc[m["zone_group"] == cfg["flood_zone_other"], "zone_raw"].value_counts()
    w(f"- Codes de zone classés « {cfg['flood_zone_other']} » : "
      f"{', '.join(f'{k} ({n(v)})' for k, v in other_codes.items()) or 'aucun'} "
      "(absents du dictionnaire v3).")
    w(f"- `flood_zone_group` NA (`{zc}` manquant) : {n(chk['flood_zone_group'].isna().sum())}.")
    zt = chk["flood_zone_group"].value_counts(dropna=False).rename_axis("flood_zone_group").reset_index(name="lignes")
    w(""); w(md_table(zt)); w("")
    w(f"- `rating_system` : " + ", ".join(f"{k} {n(v)}" for k, v in chk["rating_system"].value_counts().items()) + ".")
    w("- `loss_month_period` est stocké en `period[M]` pandas : pandas le relit tel quel, mais DuckDB ou R "
      "n'y voient qu'un entier (mois depuis 1970).\n")

    w("## 4 bis. Valeurs sentinelles → NA (hypothèses non documentées par FEMA)\n")
    w("Diagnostic détaillé : `sentinel_report.md`. Aucune ligne supprimée.\n")
    names = {"waterDepth": "water_depth", "floodWaterDuration": "flood_duration",
             "buildingPropertyValue": "buildingPropertyValue",
             "buildingPropertyValue>max": "buildingPropertyValue (seuil)"}
    srows = []
    for col, st in sent_stats.items():
        applied = col in rules or col == "buildingPropertyValue>max"
        srows.append([names[col], ", ".join(map(str, cond_rules[col][0] if col in cond_rules else st["codes"])),
                      "oui" if applied else "**non**", st["n"], st["na_before"], st["na_after"],
                      pct(st["na_after"], nf), st["min_b"], st["max_b"], st["min_a"], st["max_a"],
                      round(float(st["mean_b"]), 1), round(float(st["mean_a"]), 1),
                      float(st["med_b"]), float(st["med_a"])])
    w(md_table(pd.DataFrame(srows, columns=[
        "colonne", "code", "appliquée", "remplacés par NA", "NA avant", "NA après", "% NA après",
        "min avant", "max avant", "min après", "max après", "moyenne avant", "moyenne après",
        "médiane avant", "médiane après"])))
    wd = chk["water_depth"].dropna()
    negs = wd[wd < 0].value_counts().sort_index()
    w(f"\n- `water_depth` : {n(negs.sum())} valeurs négatives conservées (non modifiées) : "
      + ", ".join(f"{k} ({n(c)})" for k, c in negs.items()) + ". Aucune conversion pouces / pieds, aucun "
      "plafonnement : le dictionnaire v3 indique une unité mixte possible.")
    fd = chk["flood_duration"].dropna()
    w(f"- `flood_duration` : zéros conservés : {n((fd == 0).sum())} ({pct((fd == 0).sum(), len(fd))} des valeurs "
      f"renseignées, {pct((fd == 0).sum(), nf)} des lignes). Un zéro peut signifier « non renseigné », "
      "mais ce n'est pas démontré.")
    codes_b, k_b, applied_b = cond_rules["buildingPropertyValue"]
    if not applied_b:
        w(f"- `buildingPropertyValue` : règle {codes_b} → NA **non appliquée** : la valeur apparaît "
          f"{n(k_b)} fois (seuil {cfg['sentinel_to_na_if_frequent']['buildingPropertyValue']['min_rows']}). "
          "Les valeurs extrêmes (jusqu'à ≈ 2,14 milliards) ne sont pas ce code.")
    bpv = chk["buildingPropertyValue"].dropna().astype(float)
    if pv_max is not None:
        st = sent_stats["buildingPropertyValue>max"]
        w(f"- `buildingPropertyValue` : **seuil appliqué : valeurs > {n(pv_max)} $ → NA** (hypothèse non "
          f"documentée par FEMA, CONFIG `property_value_max`) : {n(st['n'])} valeurs remplacées "
          f"({pct(st['n'], nf)} des lignes). Moyenne {n(round(st['mean_b']))} → {n(round(st['mean_a']))} ; "
          f"médiane {n(round(st['med_b']))} → {n(round(st['med_a']))} ; max {n(st['max_b'])} → {n(st['max_a'])}. "
          "Motif : au-delà de 10 M$ le rapport valeur / couverture explose (≈ 90 à ≈ 7 000) et les valeurs "
          "≥ 100 M$ (1998–2001, multiples de 100) évoquent une erreur d'unité ; détail dans `sentinel_report.md`.")
    w(f"- `buildingPropertyValue` après correction : valeurs > 1 M$ : {n((bpv > 1e6).sum())} ; "
      f"> 5 M$ : {n((bpv > 5e6).sum())} ; > 10 M$ : {n((bpv > 1e7).sum())}. La valeur 99 999 "
      f"({n((bpv == 99999).sum())} lignes) reste suspecte mais n'est pas modifiée.\n")

    w("## 5. Valeurs manquantes par colonne finale\n")
    na = pd.DataFrame({"colonne": FINAL_COLUMNS, "type": [str(chk[c].dtype) for c in FINAL_COLUMNS],
                       "NA": [int(chk[c].isna().sum()) for c in FINAL_COLUMNS]})
    na["% NA"] = (100 * na["NA"] / nf).round(2)
    w(md_table(na)); w("")

    w("## 6. Rappel des contrôles de la phase 1\n")
    w("- Région IV : exactement AL, FL, GA, KY, MS, NC, SC, TN dans les deux fichiers ; préfixes FIPS cohérents.")
    w("- Aucune `dateOfLoss` manquante ; `yearOfLoss` = année de `dateOfLoss` partout.")
    w("- Pas d'espaces parasites ; booléens déjà typés BOOLEAN ; `countyCode` sur 5 caractères.")
    w("- Détail complet : `audit_report.md`.\n")

    w("## 7. Polices → `zone_year.parquet`\n")
    w(f"- Lignes de police après filtre bâtiment : {n(n_pol)} ; écartées de l'exposition car fin ≤ début : "
      f"{n(n_pol_bad)} ; `id` répétés : {n(pol_ids)} ; `policyCount` ≠ 1 : {n(n_pc_not1)}.")
    w(f"- Zone NA : {n(n_pol_zone_na)} lignes ; comté NA (`censusGeoid` manquant) : {n(n_pol_county_na)} lignes. "
      "Ces lignes sont gardées avec une clé NA.")
    w(f"- Résultat : {n(len(zy))} cellules zone × comté × année ; {n(round(zy['policy_years'].sum()))} polices-années.")
    w("- **Exposition** : chaque ligne est répartie sur les années civiles couvertes au prorata des jours "
      "(`policy_years` = policyCount × jours / 365,25 ; prime acquise = prime × jours / durée du contrat). "
      "Les totaux sont conservés (contrôles ci-dessous).")
    w(f"- **Transactions et double comptage** : un `id` par ligne, {n(pol_ids)} répété ; `policyCount` ≠ 1 : "
      f"{n(n_pc_not1)} ligne(s) ; {pct(n_pol_1y, n_pol)} des contrats durent au plus un an. "
      "Selon le dictionnaire, `policyTerminationDate` intègre déjà "
      "les résiliations (« cancelled or lapsed »), donc l'exposition n'a pas besoin d'être tronquée. "
      f"Contrôle indicatif sans identifiant de police : {n(pol_dup[0])} lignes identiques sur 12 attributs du "
      f"bien et du contrat et sur les mêmes dates ({n(round(pol_dup[1]))} polices-années, "
      f"{100 * pol_dup[1] / py_expected:.2f} % du total). C'est un majorant du double comptage, car des "
      "maisons voisines identiques sont possibles. Rien n'a été retiré.")
    w(f"- **Prime** : `totalInsurancePremiumOfThePolicy`. Lecture du dictionnaire v3 : `policyCost` = « calculated "
      "premium + reserve fund assessment + federal policy fee + HFIAA surcharge », donc la prime ne comprend "
      "*a priori* ni frais ni surcharges ; et « negative values indicate a refund ». À confirmer par le groupe. "
      f"Primes négatives : {n(n_prem_neg)} lignes ({n(round(sum_prem_neg))} $), conservées.")
    claim_years = sorted(chk["loss_year"].dropna().unique().tolist())
    expo_years = sorted(zy["year"].dropna().unique().tolist())
    w(f"- Années de sinistre : {claim_years[0]}–{claim_years[-1]} ; années d'exposition : "
      f"{expo_years[0]}–{expo_years[-1]} (prises d'effet {pd.Timestamp(min_eff).date()} → "
      f"{pd.Timestamp(max_eff).date()}, fins jusqu'au {pd.Timestamp(max_term).date()}).")
    no_expo = [y for y in claim_years if y not in expo_years]
    w(f"- Années de sinistre sans exposition : {no_expo[0]}–{no_expo[-1]} ({len(no_expo)} années, "
      f"{n(chk['loss_year'].isin(no_expo).sum())} sinistres)." if no_expo else "- Aucune année sans exposition.")
    part = zy[zy["partial_year"]].groupby("year")["partial_reason"].first()
    w("- Années marquées partielles : " + "; ".join(f"{y} ({rs})" for y, rs in part.items()) + ".\n")

    w("## 8. Contrôles automatiques (tous réussis)\n")
    for c in checks:
        w(f"- ✅ {c}")
    w("")
    (out / "cleaning_report.md").write_text("\n".join(r), encoding="utf-8")

    # ------------------------------------------------------------ résumé terminal
    print(f"Sinistres : {n(n_raw)} bruts → {n(n_occ)} maisons individuelles → {n(nf)} propres "
          f"+ {n(is_anom.sum())} anomalies")
    print("Anomalies par motif :", {k: int(v) for k, v in anom_by_motif.items() if v})
    print(f"paid_flag : vrai {n((chk['paid_flag'] == True).sum())}, faux {n((chk['paid_flag'] == False).sum())}, "
          f"NA {n(n_paid_na_left)}")
    print(f"CPI_base {base_month} = {cpi_base} ({meta.get('Series Id')})")
    print(f"zone_year : {n(len(zy))} cellules, {n(round(zy['policy_years'].sum()))} polices-années")
    print(f"{len(checks)} contrôles automatiques réussis")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["audit", "sentinels", "clean"])
    {"audit": audit, "sentinels": sentinels, "clean": clean}[ap.parse_args().phase]()
