"""Phase 1 : vérifications V1 à V8 (PROTOCOLE.md). Écrit Modeles/VERIFICATIONS.md ; en cas d'échec
d'un contrôle BLOQUANT, écrit aussi Modeles/BLOCAGE.md et sort avec le code 2 (aucun modèle)."""
import io
import re
import sys
import time
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from commun import (BUILD, CLAIMS, DS, FEATURES, KEYNUM, MOD, ROLES, SEED, TEST, TRAIN, ZONES,  # noqa: E402
                    glm_design, lgb_matrix, load_ds, load_roles, md_table, prepare, zone_design)

CMD = "Modeles/.venv/bin/python Modeles/scripts/01_verifications.py  (lancé par Modeles/run_all.sh)"
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


# --------------------------------------------------------------------------------------------- V1
def v1_integrite():
    ds, roles = load_ds(), load_roles()
    print(f"Fichier : {DS.name} ; lignes = {len(ds)} ; colonnes = {ds.shape[1]}")
    print("Types :", dict(ds.dtypes.astype(str)))
    na = ds.isna().sum()
    print("Valeurs manquantes par colonne (non nulles) :", na[na > 0].to_dict() or "aucune")
    dup = int(ds.duplicated(["county_id", "zone", "year"]).sum())
    print(f"Doublons de la clé (county_id, zone, year) : {dup}")
    years = sorted(ds["year"].unique().tolist())
    print(f"Années : {years}")
    tr_years = set(ds.loc[ds["period"] == "train", "year"])
    te_years = set(ds.loc[ds["period"] == "test", "year"])
    overlap = tr_years & te_years
    print(f"Années train {min(tr_years)}–{max(tr_years)} ; test {min(te_years)}–{max(te_years)} ; "
          f"chevauchement : {sorted(overlap) or 'aucun'}")
    period_ok = bool(((ds["year"] <= TRAIN[1]) == (ds["period"] == "train")).all())
    print(f"`period` cohérent avec TRAIN={TRAIN} / TEST={TEST} : {period_ok}")
    print(f"Effectifs : train {int((ds['period'] == 'train').sum())}, test {int((ds['period'] == 'test').sum())}")
    # Rôles : seules les listes de noms de colonnes (major_events est une liste de dictionnaires)
    role_of = {}
    for r, cols in roles.items():
        if isinstance(cols, list) and all(isinstance(c, str) for c in cols):
            for c in cols:
                role_of.setdefault(c, r)          # zone : « id » puis « features » (rôle double)
    role_of["mean_coverage"] = "features" if "mean_coverage" in roles["features"] else role_of.get("mean_coverage")
    for c in FEATURES:
        if c in roles["features"]:
            role_of[c] = "features"
    for c in FEATURES:
        print(f"  rôle de {c} dans ds_clean_roles.json : {role_of.get(c)}")
    print(f"  rôle de n_claims : {role_of.get('n_claims')} ; exposure_years : {role_of.get('exposure_years')} ; "
          f"n_all : {role_of.get('n_all')}")
    feat_roles_ok = all(role_of.get(c) == "features" for c in FEATURES)
    ok = dup == 0 and not overlap and period_ok and feat_roles_ok and \
        role_of.get("n_claims") == "target" and role_of.get("exposure_years") == "offset"
    notes = []
    if role_of.get("n_all") != "target":
        notes.append(f"n_all a le rôle « {role_of.get('n_all')} » dans ds_clean_roles.json (compte de sensibilité), "
                     "pas « target » : son usage comme seconde cible suit la consigne (V4), écart signalé.")
    if "zone" in roles["id"] and "zone" in roles["features"]:
        notes.append("zone figure à la fois dans « id » et « features » de ds_clean_roles.json (rôle double, cohérent).")
    return ok, notes


# --------------------------------------------------------------------------------------------- V2
def v2_exposition():
    ds = load_ds()
    e = ds["exposure_years"]
    finite = bool(np.isfinite(e).all())
    neg = int((e < 0).sum())
    zero = int((e == 0).sum())
    low = e < 0.5
    print(f"Exposition finie partout : {finite} ; négative : {neg} ; nulle : {zero}")
    q = e.quantile([0, .01, .05, .5, .95, .99, 1]).round(4)
    print("Distribution (min, P1, P5, P50, P95, P99, max) :", q.tolist())
    print(f"Lignes < 0,5 police-année : {int(low.sum())} ({low.mean():.2%} des lignes), "
          f"exposition {e[low].sum():.2f} ({e[low].sum() / e.sum():.5%}), "
          f"sinistres payés {int(ds.loc[low, 'n_claims'].sum())}, tous {int(ds.loc[low, 'n_all'].sum())}")
    z = e <= 0
    share_rows, share_expo = z.mean(), e[z].sum() / e.sum()
    print(f"Exclusion pour le log (exposition ≤ 0) : {int(z.sum())} lignes ({share_rows:.2%}), "
          f"exposition {share_expo:.2%}")
    print("Seuil d'exclusion des expositions très faibles : aucun (décision pré-enregistrée, PROTOCOLE § 3).")
    ok = finite and neg == 0 and share_rows <= 0.01 and share_expo <= 0.01
    notes = [f"{int(low.sum())} lignes ont moins de 0,5 police-année ; elles sont gardées (aucun seuil), "
             f"avec {int(ds.loc[low, 'n_claims'].sum())} sinistres payés."]
    return ok, notes


# --------------------------------------------------------------------------------------------- V3
def v3_fuite_historiques():
    src = BUILD.read_text()
    hist = re.search(r"HIST\s*=\s*\((\d{4}),\s*(\d{4})\)", src)
    h0, h1 = int(hist.group(1)), int(hist.group(2))
    print(f"build_ds_clean.py : HIST = ({h0}, {h1})")
    for pat in [r'h = claims\[claims\["year"\]\.between\(\*HIST\).*', r"avg_cz = .*", r"avg_c = .*",
                r'd\["hist_per_1000"\] = .*', r'd\["county_hist_per_1000"\] = .*', r'claims\["year"\] = .*',
                r'claims\["paid"\] = .*']:
        m = re.search(pat, src)
        print("  ligne :", m.group(0).strip() if m else f"(motif introuvable : {pat})")

    # Recalcul indépendant depuis claims_clean.parquet
    c = pd.read_parquet(CLAIMS, columns=["loss_year", "paid_building_real", "county_fips", "flood_zone_group"])
    print("Colonnes de claims_clean utilisées : loss_year (année de survenue), paid_building_real, "
          "county_fips, flood_zone_group")
    c["year"] = pd.to_numeric(c["loss_year"]).astype(int)
    c["paid"] = pd.to_numeric(c["paid_building_real"], errors="coerce") > 0
    c["county"] = c["county_fips"].astype("object")
    c["zone"] = c["flood_zone_group"].astype("object")
    ds = load_ds()
    d = ds[ds["exposure_years"] > 0]
    tr = d[d["year"] <= TRAIN[1]]
    avg_cz = tr.groupby(["county_id", "zone"])["exposure_years"].mean()
    avg_c = tr.groupby(["county_id", "year"])["exposure_years"].sum().groupby("county_id").mean()
    nyears = tr.groupby(["county_id", "zone"])["year"].nunique()
    print(f"Dénominateur : moyenne de exposure_years (polices-années) des lignes d'entraînement "
          f"{TRAIN[0]}–{TRAIN[1]} présentes pour la cellule ; cellules avec moins de 10 années présentes : "
          f"{int((nyears < 10).sum())} sur {len(nyears)}")

    def recompute(lo, hi):
        h = c[c["year"].between(lo, hi) & c["paid"] & c["county"].notna()]
        hcz = h[h["zone"].isin(ZONES)].groupby(["county", "zone"]).size()
        hc = h.groupby("county").size()
        idx = pd.MultiIndex.from_frame(ds[["county_id", "zone"]])
        n = hcz.reindex(idx).fillna(0).to_numpy()
        per = 1000 * n / avg_cz.reindex(idx).to_numpy()
        cper = 1000 * ds["county_id"].map(hc).fillna(0).to_numpy() / ds["county_id"].map(avg_c).to_numpy()
        return n, per, cper

    def compare(name, a, b):
        a, b = np.asarray(a, float), np.asarray(b, float)
        both = ~np.isnan(a) & ~np.isnan(b)
        rel = np.abs(a[both] - b[both]) / np.maximum(np.abs(b[both]), 1e-9)
        nan_mismatch = int((np.isnan(a) != np.isnan(b)).sum())
        ndiff = int((rel > 1e-5).sum()) + nan_mismatch
        print(f"  {name} : lignes différentes (écart relatif > 1e-5 ou NA différent) = {ndiff} ; "
              f"écart absolu max = {np.max(np.abs(a[both] - b[both])):.6g}")
        return ndiff

    print(f"Recalcul avec les sinistres {h0}–{h1} (définition du script) :")
    n, per, cper = recompute(h0, h1)
    d1 = compare("hist_claims_1990_2008", n, ds["hist_claims_1990_2008"])
    d2 = compare("hist_per_1000", per, ds["hist_per_1000"])
    d3 = compare("county_hist_per_1000", cper, ds["county_hist_per_1000"])
    print("Recalcul avec tous les sinistres de survenue < 2010 (1978–2009), comme demandé :")
    n2, per2, cper2 = recompute(c["year"].min(), 2009)
    e1 = compare("hist_per_1000 (<2010)", per2, ds["hist_per_1000"])
    e2 = compare("county_hist_per_1000 (<2010)", cper2, ds["county_hist_per_1000"])
    print("  (les écarts de ce second recalcul viennent de la fenêtre 1990–2008 du script, plus étroite que "
          "« < 2010 », pas d'une fuite)")
    ok = h1 < 2010 and d1 == 0 and d2 == 0 and d3 == 0
    notes = [f"Les sinistres qui alimentent les historiques sont ceux de {h0}–{h1} (aucune année ≥ 2010) : "
             "pas de fuite par le numérateur.",
             "Le dénominateur est l'exposition moyenne 2010–2019 de la cellule (ou du comté). Pour une ligne "
             "d'entraînement, il utilise donc l'exposition d'années postérieures à la ligne, et pour la "
             "validation interne de LightGBM (2018–2019) l'exposition des années de validation. Ce n'est pas "
             "une information de sinistres, mais c'est une légère information future : signalé, non bloquant "
             "selon la règle V3 (qui porte sur les années de sinistres).",
             "La moyenne porte sur les années présentes de la cellule, pas sur 10 ans fixes."]
    return ok, notes


# --------------------------------------------------------------------------------------------- V4
def v4_cible():
    ds = load_ds()
    roles = load_roles()
    count_cols = [c for c in ds.columns if c.startswith("n_") and c != "n_policy_rows"]
    print(f"Colonnes de comptage : {count_cols} (n_policy_rows exclue : nombre de lignes de police)")
    for c in count_cols:
        print(f"  {c} : {roles['description'].get(c)}")
    has_all = "n_all" in ds.columns
    print(f"Colonne « tous les sinistres » présente : {has_all} -> pas de reconstruction "
          "(Modeles/scripts/construire_cible_tous.py non nécessaire)")
    by_year = ds.groupby("year")[["n_claims", "n_all"]].sum()
    by_year["tous_>=_payes"] = by_year["n_all"] >= by_year["n_claims"]
    print(by_year.to_string())
    ok_rows = bool((ds["n_all"] >= ds["n_claims"]).all())
    print(f"n_all >= n_claims sur toutes les lignes : {ok_rows}")
    ok = has_all and bool(by_year["tous_>=_payes"].all()) and ok_rows
    notes = ["Cible « tous » = n_all : tous les sinistres de la cellule, payés ou non, issus de claims_clean "
             "(maisons individuelles, hors anomalies du nettoyage, avec comté et zone V*/A*/X). Avant 2018 "
             "environ, la plupart des non-payés viennent d'un paiement NA recodé en 0 au nettoyage."]
    return ok, notes


# --------------------------------------------------------------------------------------------- V5
def v5_dependances():
    import importlib
    import os
    vers = {}
    for m in ["pandas", "numpy", "scipy", "statsmodels", "lightgbm", "matplotlib", "pyarrow", "sklearn"]:
        vers[m] = importlib.import_module(m).__version__
    print("Versions :", vers)
    # Chemin affiché relativement à la racine du dépôt (pas de chemin personnel dans les fichiers publiés)
    dyld = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "(non défini)").replace(str(MOD.parent) + "/", "")
    print("DYLD_FALLBACK_LIBRARY_PATH =", dyld, "(relatif à la racine du dépôt)")
    import lightgbm as lgb
    import statsmodels.api as sm
    d, _ = prepare(load_ds())
    s = d[d["period"] == "train"].sample(100, random_state=SEED)
    y, off = s["n_claims"].to_numpy(float), s["log_e"].to_numpy()
    g = sm.GLM(y, zone_design(s), family=sm.families.Poisson(), offset=off).fit()
    print(f"GLM Poisson (statsmodels, offset) sur 100 lignes : converge = {g.converged}, "
          f"somme prédite {g.fittedvalues.sum():.3f} / observée {y.sum():.0f}")
    p = {"objective": "poisson", "verbose": -1, "seed": SEED, "deterministic": True, "num_threads": 1,
         "force_row_wise": True, "min_data_in_leaf": 20, "learning_rate": 0.1}
    Xc = pd.DataFrame({"constante": np.ones(len(s))})
    m0 = s["exposure_years"].to_numpy() * y.sum() / s["exposure_years"].sum()
    # (a) Procédure initiale du protocole : init_score = log(exposition) seul
    b0 = lgb.train(p, lgb.Dataset(lgb_matrix(s), y, init_score=off, categorical_feature=["zone"]), 50)
    pred0 = np.exp(b0.predict(lgb_matrix(s), raw_score=True) + off)
    bc0 = lgb.train(p, lgb.Dataset(Xc, y, init_score=off), 50)
    print(f"(a) init_score = log(e) : somme prédite {pred0.sum():.3f} / observée {y.sum():.0f} ; "
          f"variable constante -> {bc0.num_trees()} arbre(s), score brut {np.unique(bc0.predict(Xc, raw_score=True))}")
    # (b) Procédure de l'avenant n° 1 : init_score = log(e) + log(taux moyen des lignes d'ajustement)
    base = np.log(y.sum() / s["exposure_years"].sum())
    b = lgb.train(p, lgb.Dataset(lgb_matrix(s), y, init_score=off + base, categorical_feature=["zone"]), 50)
    pred = np.exp(b.predict(lgb_matrix(s), raw_score=True) + off + base)
    bc = lgb.train(p, lgb.Dataset(Xc, y, init_score=off + base), 50)
    pc = np.exp(bc.predict(Xc, raw_score=True) + off + base)
    rel = np.max(np.abs(pc - m0) / m0)
    print(f"(b) init_score = log(e) + log(r) : somme prédite {pred.sum():.3f} / observée {y.sum():.0f} "
          f"(ratio {pred.sum() / y.sum():.4f})")
    print(f"    contrôle variable constante : écart relatif max avec M0 = {rel:.2e}")
    ok = g.converged and rel < 0.01 and abs(pred.sum() / y.sum() - 1) < 0.01
    notes = ["LightGBM 4.7.0 ne se charge pas sans la bibliothèque système libomp (absente : Homebrew n'est "
             "pas installé). Contournement local, sans installation globale : la copie de libomp fournie dans "
             "le paquet scikit-learn de Modeles/.venv est désignée par DYLD_FALLBACK_LIBRARY_PATH (positionné "
             "par run_all.sh). Solution standard : `brew install libomp`.",
             "(a) montre pourquoi la procédure initiale ne convient pas : avec un init_score, LightGBM désactive "
             "boost_from_average, et une variable constante ne produit qu'un arbre trivial sans coupure "
             "(score brut 0). Le modèle "
             "part de 1 sinistre par police-année et ne rattrape pas l'intercept en 50 itérations (pas plafonné "
             "par poisson_max_delta_step). (b) est la procédure de l'avenant n° 1 de PROTOCOLE.md : elle "
             "reproduit M0 exactement avec une variable constante, et la somme observée à moins de 1 % près."]
    return ok, notes


# --------------------------------------------------------------------------------------------- V6
def v6_variables():
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    ds = load_ds()
    d, info = prepare(ds)
    print("Lignes exclues par la préparation (PROTOCOLE § 3) :", info)
    miss = ds[FEATURES].isna()
    print("Manquants par variable (table complète) :", miss.sum().to_dict())
    print("Années et période des lignes à variable manquante :",
          ds.loc[miss.any(axis=1), ["year", "period"]].value_counts().to_dict())
    tr = d[d["period"] == "train"]
    num = ["mean_coverage", "hist_per_1000", "county_hist_per_1000"]
    print("Distribution (entraînement) :")
    print(tr[num].describe(percentiles=[.01, .05, .5, .95, .99]).T.round(3).to_string())
    print("Corrélation de Pearson (entraînement) :\n" + tr[num].corr().round(3).to_string())
    print("Corrélation de Spearman (entraînement) :\n" + tr[num].corr(method="spearman").round(3).to_string())
    print(f"Part de hist_per_1000 = 0 (entraînement) : {(tr['hist_per_1000'] == 0).mean():.3f} ; "
          f"county_hist_per_1000 = 0 : {(tr['county_hist_per_1000'] == 0).mean():.3f}")
    zt = d.groupby(["zone", "period"]).agg(lignes=("year", "size"), exposition=("exposure_years", "sum")).unstack()
    print("Zones (lignes, exposition) par période :\n" + zt.round(0).to_string())
    tr_share = tr.groupby("zone")["exposure_years"].sum() / tr["exposure_years"].sum()
    rare = tr_share[tr_share < 0.02]
    print(f"Modalités rares en entraînement (< 2 % de l'exposition) : {rare.round(4).to_dict()}")
    absent = set(d.loc[d['period'] == 'test', 'zone']) - set(tr['zone'])
    print(f"Modalités du test absentes de l'entraînement : {sorted(absent) or 'aucune'}")
    X = glm_design(tr)
    vif = {c: round(variance_inflation_factor(X.to_numpy(), i), 3) for i, c in enumerate(X.columns) if c != "const"}
    print("VIF (matrice GLM, entraînement) :", vif)
    notes = [f"{info['variable_manquante']} lignes ont une variable explicative manquante et sont exclues de "
             f"tous les modèles ({info['sinistres_payes_exclus']} sinistres payés, "
             f"{info['sinistres_tous_exclus']} sinistres au total)."]
    if len(rare):
        notes.append(f"Zone rare en entraînement : {', '.join(f'{k} ({v:.1%} de l’exposition)' for k, v in rare.items())}.")
    return True, notes


# --------------------------------------------------------------------------------------------- V7
def v7_derive():
    d, _ = prepare(load_ds())
    y = d.groupby("year").agg(payes=("n_claims", "sum"), tous=("n_all", "sum"), expo=("exposure_years", "sum"))
    y["taux_payes_1000"] = 1000 * y["payes"] / y["expo"]
    y["taux_tous_1000"] = 1000 * y["tous"] / y["expo"]
    print(y.round(3).to_string())
    for p, (a, b) in [("train", TRAIN), ("test", TEST)]:
        s = y.loc[a:b]
        print(f"Taux {p} : payés {1000 * s['payes'].sum() / s['expo'].sum():.3f}, "
              f"tous {1000 * s['tous'].sum() / s['expo'].sum():.3f} pour 1 000 polices-années")
    te = y.loc[TEST[0]:TEST[1]]
    print(f"Part de 2024 dans les sinistres du test : payés {te.loc[2024, 'payes'] / te['payes'].sum():.3f}, "
          f"tous {te.loc[2024, 'tous'] / te['tous'].sum():.3f}")
    comp = d.groupby(["period", "zone"])["exposure_years"].sum()
    comp = (comp / comp.groupby(level=0).transform("sum")).unstack().round(4)
    print("Part de l'exposition par zone et par période :\n" + comp.to_string())
    return True, []


# --------------------------------------------------------------------------------------------- V8
def v8_coherence():
    import json
    ds = load_ds()
    kn = json.loads(KEYNUM.read_text())
    uy = ds[ds["exposure_years"] > 0]
    tr = uy[uy["period"] == "train"]
    y, ex = tr["n_claims"].to_numpy(float), tr["exposure_years"].to_numpy(float)
    mu0 = ex * y.sum() / ex.sum()
    rate_y = tr.groupby("year")["n_claims"].transform("sum") / tr.groupby("year")["exposure_years"].transform("sum")
    mu1 = (tr["exposure_years"] * rate_y).to_numpy(float)
    g = [tr["year"], tr["zone"]]
    mu2 = (tr["exposure_years"] * tr.groupby(g)["n_claims"].transform("sum")
           / tr.groupby(g)["exposure_years"].transform("sum")).to_numpy(float)
    ok2 = mu2 > 0
    disp = {"dispersion_overall": np.sum((y - mu0) ** 2 / mu0) / (len(y) - 1),
            "dispersion_within_year": np.sum((y - mu1) ** 2 / mu1) / (len(y) - tr["year"].nunique()),
            "dispersion_within_year_zone": np.sum((y[ok2] - mu2[ok2]) ** 2 / mu2[ok2]) / (ok2.sum() - tr.groupby(g).ngroups)}
    te = uy[uy["period"] == "test"]
    rows = [("lignes de ds_clean", 22485, len(ds)), ("lignes train", 14999, int((ds.period == "train").sum())),
            ("lignes test", 7486, int((ds.period == "test").sum()))]
    for k, v in disp.items():
        rows.append((f"{k} (eda_key_numbers.json)", round(kn[k], 2), round(float(v), 2)))
    rows += [("part de 2024 dans les sinistres payés du test (rapport externe : 0,508)", 0.508,
              round(float(te.loc[te.year == 2024, "n_claims"].sum() / te["n_claims"].sum()), 3)),
             ("fréquence train (eda_key_numbers.json)", round(kn["freq_train"], 3),
              round(1000 * tr["n_claims"].sum() / tr["exposure_years"].sum(), 3)),
             ("fréquence test (eda_key_numbers.json)", round(kn["freq_test"], 3),
              round(1000 * te["n_claims"].sum() / te["exposure_years"].sum(), 3))]
    t = pd.DataFrame(rows, columns=["élément", "valeur citée", "valeur observée"])
    t["écart"] = [("non" if abs(float(a) - float(b)) <= 1e-3 * max(1, abs(float(a))) else "OUI") for a, b in
                  zip(t["valeur citée"], t["valeur observée"])]
    print(t.to_string(index=False))
    notes = [f"Écart : {r['élément']} (cité {r['valeur citée']}, observé {r['valeur observée']})"
             for _, r in t.iterrows() if r["écart"] == "OUI"]
    return True, notes


CHECKS = [("V1", "Intégrité de la table", True, v1_integrite),
          ("V2", "Exposition", True, v2_exposition),
          ("V3", "Fuite temporelle des historiques", True, v3_fuite_historiques),
          ("V4", "Cible", True, v4_cible),
          ("V5", "Dépendances", True, v5_dependances),
          ("V6", "Variables", False, v6_variables),
          ("V7", "Dérive entre entraînement et test", False, v7_derive),
          ("V8", "Cohérence avec le rapport", False, v8_coherence)]


def main():
    t0 = time.time()
    out = ["# Vérifications (phase 1)\n",
           f"> Générées par `{CMD}` le {time.strftime('%d/%m/%Y à %H:%M:%S %Z')}. Chaque section donne la "
           "fonction exécutée (dans le script), sa sortie brute et le statut. Graine : 42.\n"]
    failed = []
    summary = []
    for code, title, blocking, fn in CHECKS:
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                ok, notes = fn()
        except Exception as exc:  # un contrôle qui plante est un échec
            ok, notes = False, [f"Exception : {type(exc).__name__}: {exc}"]
        status = "RÉUSSI" if ok else ("ÉCHEC" if blocking else "À SIGNALER")
        if not ok and blocking:
            failed.append((code, title, buf.getvalue(), notes))
        summary.append((code, title, "BLOQUANT" if blocking else "NON BLOQUANT", status, len(notes)))
        out += [f"## {code} [{'BLOQUANT' if blocking else 'NON BLOQUANT'}] {title} : **{status}**\n",
                f"Commande : `{CMD}`, fonction `{fn.__name__}`.\n", "```text", buf.getvalue().rstrip(), "```\n"]
        if notes:
            out += ["Remarques :\n"] + [f"- {n}" for n in notes] + [""]
        print(f"{code} {title} : {status}")
    out.insert(2, "## Synthèse\n\n" + md_table(pd.DataFrame(
        summary, columns=["contrôle", "intitulé", "type", "statut", "remarques"])) + "\n")
    out.append(f"Durée : {time.time() - t0:.1f} s.")
    (MOD / "VERIFICATIONS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    if failed:
        b = ["# Blocage : aucun modèle n'a été ajusté\n"]
        for code, title, txt, notes in failed:
            b += [f"## {code} {title}\n", "Preuve (sortie du contrôle) :\n", "```text", txt.rstrip(), "```",
                  *[f"- {n}" for n in notes], ""]
        b.append("Cause probable, correction proposée et responsable : à compléter dans la documentation.")
        (MOD / "BLOCAGE.md").write_text("\n".join(b) + "\n", encoding="utf-8")
        print("BLOCAGE : voir Modeles/BLOCAGE.md")
        sys.exit(2)


if __name__ == "__main__":
    main()
