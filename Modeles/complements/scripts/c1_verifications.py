"""Phase 1 des compléments : VC1 à VC4 (PROTOCOLE_COMPLEMENTAIRE.md § 3). Écrit
Modeles/complements/VERIFICATIONS_COMPLEMENTAIRES.md et des tableaux dans complements/resultats/.
Statut de chaque vérification : CONFORME, ÉCART ou DÉFAUT, selon des règles explicites dans le code."""
import io
import re
import sys
import time
import warnings
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ccommun import (CFIG, CLAIMS, COMP, CRES, FIT, JET_RES, MOD, ROOT, SEED, TARGETS, TEST, TRAIN,  # noqa: E402
                     VALID, ZONES, glm_design, jet_info, lgb_X, load_ds, m4_params, poisson_deviance, prepare,
                     zone_design)

CMD = "Modeles/.venv/bin/python Modeles/complements/scripts/c1_verifications.py  (lancé par Modeles/complements/run_all.sh)"
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)


# ------------------------------------------------------------------------------------------- VC1
def vc1_offset_validation():
    import lightgbm as lgb
    src = (MOD / "scripts" / "02_modeles.py").read_text()
    lines = [r"r_fit = .*", r"dva = lgb\.Dataset\(.*", r"b = fit_lgb\(lgb_matrix\(fit_part\).*",
             r"lgb_matrix\(val_part\), val_part\[col\].*", r"callbacks=\[lgb\.early_stopping.*", r'"metric": "poisson"']
    print("Lecture de Modeles/scripts/02_modeles.py :")
    found = {}
    for pat in lines:
        m = re.search(pat, src)
        found[pat] = bool(m)
        print("  ", m.group(0).strip() if m else f"(introuvable : {pat})")
    code_ok = all(found.values()) and "init_score=initv" in src and \
        'val_part["log_e"] + np.log(r_fit)' in src and 'r_fit = fit_part[col].sum() / fit_part["exposure_years"].sum()' in src
    print(f"-> Le Dataset de validation reçoit init_score = log(e) + log(r_fit), r_fit calculé sur les lignes "
          f"d'ajustement {FIT} : {code_ok}")

    d, _ = prepare(load_ds())
    tr = d[d["period"] == "train"]
    fit_part, val_part = tr[tr["year"].between(*FIT)], tr[tr["year"].between(*VALID)]
    feats = ["zone", "mean_coverage", "hist_per_1000", "county_hist_per_1000"]
    status_ok = code_ok
    rows = []
    for code, col in TARGETS.items():
        params, n_iter = m4_params(code)
        r_fit = fit_part[col].sum() / fit_part["exposure_years"].sum()
        init_f = fit_part["log_e"] + np.log(r_fit)
        init_v = val_part["log_e"].to_numpy() + np.log(r_fit)
        dtr = lgb.Dataset(lgb_X(fit_part, feats), fit_part[col].to_numpy(float), init_score=init_f,
                          categorical_feature=["zone"], free_raw_data=False)
        dva = lgb.Dataset(lgb_X(val_part, feats), val_part[col].to_numpy(float), init_score=init_v,
                          categorical_feature=["zone"], reference=dtr)
        rec = {}
        n_total = 400
        b = lgb.train(params, dtr, n_total, valid_sets=[dva], valid_names=["validation"],
                      callbacks=[lgb.record_evaluation(rec)])
        lgb_metric = np.array(rec["validation"]["poisson"])
        y = val_part[col].to_numpy(float)
        Xv = lgb_X(val_part, feats)
        hand_nll, hand_dev = [], []
        for k in range(1, n_total + 1):
            mu = np.exp(b.predict(Xv, raw_score=True, num_iteration=k) + init_v)
            hand_nll.append(np.mean(mu - y * np.log(mu)))
            hand_dev.append(poisson_deviance(y, mu).sum())
        hand_nll, hand_dev = np.array(hand_nll), np.array(hand_dev)
        max_diff = float(np.max(np.abs(hand_nll - lgb_metric)))
        window = n_iter + 100                                   # itérations réellement entraînées (patience 100)
        k_window = int(np.argmin(hand_dev[:window]) + 1)
        k_all = int(np.argmin(hand_dev) + 1)
        # Variante sans offset en validation, pour mesurer l'effet d'un éventuel défaut
        mu_nooff = np.exp(b.predict(Xv, raw_score=True, num_iteration=n_iter))
        print(f"\nCible {code} : hyperparamètres {{{', '.join(f'{k}={params[k]}' for k in ['learning_rate', 'num_leaves', 'min_data_in_leaf', 'lambda_l2'])}}}, "
              f"itération retenue au premier jet = {n_iter}")
        print(f"  r_fit = {r_fit:.6g} (taux des lignes 2010-2017) ; log(r_fit) = {np.log(r_fit):.6f}")
        print(f"  métrique LightGBM « poisson » (validation) = moyenne de (mu - y log mu) calculée à la main : "
              f"écart absolu max sur {n_total} itérations = {max_diff:.3e}")
        print(f"  déviance calculée à la main : minimum sur les {window} itérations entraînées au premier jet "
              f"à l'itération {k_window} (déviance {hand_dev[k_window - 1]:,.1f}) ; minimum sur {n_total} "
              f"itérations : {k_all} (déviance {hand_dev[k_all - 1]:,.1f})".replace(",", " "))
        print(f"  déviance à l'itération retenue {n_iter} : {hand_dev[n_iter - 1]:,.1f} ; "
              f"sans offset en validation (illustration) : {poisson_deviance(y, mu_nooff).sum():,.1f}".replace(",", " "))
        ok = max_diff < 1e-6 and k_window == n_iter
        status_ok &= ok
        rows.append({"cible": code, "iteration_retenue": n_iter, "argmin_deviance_main_fenetre": k_window,
                     "argmin_deviance_main_400": k_all, "ecart_max_metrique_lgb_vs_main": max_diff,
                     "deviance_validation_iteration_retenue": hand_dev[n_iter - 1]})
        pd.DataFrame({"iteration": np.arange(1, n_total + 1), "poisson_lightgbm": lgb_metric,
                      "poisson_nll_main": hand_nll, "deviance_main": hand_dev}).to_csv(
            CRES / f"vc1_courbe_validation_{code}.csv", index=False)
    pd.DataFrame(rows).to_csv(CRES / "vc1_synthese.csv", index=False)
    status = "CONFORME" if status_ok else "DÉFAUT"
    concl = ("La validation reçoit son propre init_score = log(e) + log(r_fit), r_fit étant le taux des lignes "
             "d'ajustement 2010-2017 ; la métrique d'arrêt précoce de LightGBM coïncide avec la log-vraisemblance "
             "négative recalculée à la main avec cet offset, et l'itération qui minimise la déviance calculée à la "
             "main (dans la fenêtre réellement entraînée) est celle retenue. Aucun nouveau réglage n'est nécessaire : "
             "les ablations réutilisent les hyperparamètres du premier jet.") if status_ok else \
        "Défaut détecté : voir la sortie ; un nouveau réglage est requis (PROTOCOLE_COMPLEMENTAIRE § 3)."
    return status, concl


# ------------------------------------------------------------------------------------------- VC2
def vc2_binomial_negatif():
    import statsmodels.api as sm
    from statsmodels.discrete.discrete_model import NegativeBinomial
    d, _ = prepare(load_ds())
    tr = d[d["period"] == "train"]
    worst = 0.0
    score_ok = True
    rows = []
    for code, col in TARGETS.items():
        info = jet_info(code)
        alpha = info["M3_alpha"]
        y = tr[col].to_numpy(float)
        X = glm_design(tr)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g = sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=tr["log_e"]).fit()
        c3 = pd.read_csv(JET_RES / f"coefficients_{code}.csv")
        c3 = c3[(c3.modele == "M3") & (c3.variable != "alpha")].set_index("variable")["coefficient"]
        diff = (g.params - c3.reindex(g.params.index)).abs()
        llf_diff = abs(g.llf - info["M3_loglik_train"])
        print(f"\nCible {code} : alpha (M3, exact) = {alpha:.6f}")
        print("  coefficients GLM NegativeBinomial(alpha fixé) vs M3 :")
        print(pd.DataFrame({"GLM_NB_alpha_fixe": g.params, "M3_NegativeBinomial": c3.reindex(g.params.index),
                            "ecart_absolu": diff}).round(8).to_string())
        print(f"  log-vraisemblance : GLM {g.llf:.4f} ; M3 {info['M3_loglik_train']:.4f} ; écart {llf_diff:.3e}")
        worst = max(worst, float(diff.max()))
        p = pd.read_csv(JET_RES / f"predictions_{code}.csv", dtype={"county_id": str})
        pt = p[p["period"] == "train"]
        mu = pt["M3"].to_numpy()
        yy = pt["observe"].to_numpy()
        s1 = float(np.sum(yy - mu))
        s2 = float(np.sum((yy - mu) / (1 + alpha * mu)))
        ratio = mu.sum() / yy.sum()
        print(f"  M3 sur l'entraînement : Σ(y-μ) = {s1:,.2f} ; Σ(y-μ)/(1+αμ) = {s2:.6f} ; Σμ/Σy = {ratio:.4f}".replace(",", " "))
        score_ok &= abs(s2) < 1e-3 * yy.sum() ** 0.5
        nb0 = NegativeBinomial(y, np.ones((len(y), 1)), loglike_method="nb2", exposure=tr["exposure_years"].to_numpy())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r0 = nb0.fit(start_params=np.array([np.log(y.sum() / tr["exposure_years"].sum()), 1.0]),
                         method="newton", maxiter=5000, disp=0)
        mu0 = r0.predict(np.ones((len(y), 1)), exposure=tr["exposure_years"].to_numpy())
        print(f"  NB constante + offset seuls : converge = {r0.mle_retvals.get('converged')}, alpha = {r0.params[-1]:.4f}, "
              f"Σμ/Σy = {mu0.sum() / y.sum():.4f}")
        rows.append({"cible": code, "alpha": alpha, "ecart_max_coef_GLM_vs_M3": float(diff.max()),
                     "ecart_loglik": llf_diff, "somme_y_moins_mu": s1, "somme_score_nb2": s2,
                     "ratio_somme_mu_somme_y_M3": ratio, "alpha_constante_seule": float(r0.params[-1]),
                     "ratio_somme_mu_somme_y_constante_seule": float(mu0.sum() / y.sum())})
    pd.DataFrame(rows).to_csv(CRES / "vc2_binomial_negatif.csv", index=False)
    status = "CONFORME" if worst < 1e-3 and score_ok else "ÉCART"
    r = pd.DataFrame(rows).set_index("cible")
    concl = (f"Le GLM NegativeBinomial à α fixé reproduit M3 (écart maximal sur les coefficients "
             f"{worst:.1e}). Sur l'entraînement, Σ(y-μ)/(1+αμ) est nul (équation du score de la constante en NB2, "
             f"lien log) tandis que Σ(y-μ) ne l'est pas : Σμ/Σy = {r.loc['payes', 'ratio_somme_mu_somme_y_M3']:.3f} "
             f"(payés), {r.loc['tous', 'ratio_somme_mu_somme_y_M3']:.3f} (tous). Cela étaye la première partie du "
             f"§ 7.2 (l'estimateur NB2 n'impose pas l'égalité des totaux). Avec la constante et l'offset seuls, "
             f"Σμ/Σy vaut déjà {r.loc['payes', 'ratio_somme_mu_somme_y_constante_seule']:.3f} (payés) : l'écart de "
             f"niveau existe sans aucune variable. Le rôle précis de la valeur de α n'est pas isolé par ce calcul "
             f"(non démontré).")
    return status, concl


# ------------------------------------------------------------------------------------------- VC3
def vc3_zone_temps():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ds = load_ds()
    t = ds.groupby(["year", "zone"]).agg(exposition=("exposure_years", "sum"), payes=("n_claims", "sum"),
                                         tous=("n_all", "sum")).reset_index()
    t["taux_payes_1000"] = 1000 * t["payes"] / t["exposition"]
    t["taux_tous_1000"] = 1000 * t["tous"] / t["exposition"]
    for c in ["exposition", "payes", "tous"]:
        t[f"part_{c}"] = t[c] / t.groupby("year")[c].transform("sum")
    t.to_csv(CRES / "vc3_zone_annee.csv", index=False)
    print("Par année et par zone (ds_clean, 22 485 lignes) :")
    print(t.round(4).to_string(index=False))
    per = ds.assign(p=np.where(ds["year"] <= TRAIN[1], "train", "test")).groupby(["zone", "p"])[
        ["n_claims", "n_all", "exposure_years"]].sum()
    rate = (1000 * per["n_claims"] / per["exposure_years"]).unstack()
    rate_all = (1000 * per["n_all"] / per["exposure_years"]).unstack()
    mult = pd.DataFrame({"taux_payes_train": rate["train"], "taux_payes_test": rate["test"],
                         "multiplicateur_payes": rate["test"] / rate["train"],
                         "taux_tous_train": rate_all["train"], "taux_tous_test": rate_all["test"],
                         "multiplicateur_tous": rate_all["test"] / rate_all["train"]})
    print("\nTaux pour 1 000 polices-années, entraînement vs test :\n" + mult.round(3).to_string())
    mult.to_csv(CRES / "vc3_multiplicateur_zone.csv")

    fig, ax = plt.subplots(figsize=(11, 4.6), layout="constrained")
    cols = {"V*": "#eb6834", "A*": "#2a78d6", "X": "#1baf7a"}
    for z in ["V*", "A*", "X"]:
        s = t[t["zone"] == z]
        ax.plot(s["year"], s["taux_payes_1000"], "-o", ms=4, color=cols[z], label=f"zone {z}")
    ax.set_yscale("log")
    ax.axvspan(TEST[0] - 0.5, TEST[1] + 0.5, color="#2a78d6", alpha=0.06, lw=0)
    ax.set_xticks(range(2010, 2025))
    ax.set_ylabel("Sinistres payés pour 1 000 polices-années (échelle log)")
    ax.set_title("Taux de sinistres payés par zone d'inondation et par année (ds_clean ; test ombré)")
    ax.legend(frameon=False)
    fig.savefig(CFIG / "vc3_taux_zone_annee.png", dpi=200)
    plt.close(fig)

    # Définition du regroupement
    clean_src = (ROOT / "Data_cleaning" / "clean" / "clean_data.py").read_text()
    build_src = (ROOT / "EDA" / "build_ds_clean.py").read_text()
    m = re.search(r'"flood_zone_groups": \{.*?\n    \},', clean_src, re.S)
    print("\nRegroupement défini dans Data_cleaning/clean/clean_data.py (CONFIG) :\n" + (m.group(0) if m else "(introuvable)"))
    for pat in [r'"flood_zone_other": .*', r'ZONES = .*', r'no_zone = .*', r'c = c\[c\["zone"\]\.isin\(ZONES\)\]',
                r'e = e\[e\["zone"\]\.isin\(ZONES\)\]']:
        mm = re.search(pat, clean_src + "\n" + build_src)
        print("  ", mm.group(0).strip() if mm else f"(introuvable : {pat})")

    # Codes bruts de ratedFloodZone : absents de claims_clean, lus dans le fichier brut (agrégés seulement)
    clean = pd.read_parquet(CLAIMS, columns=["id", "loss_year", "flood_zone_group", "rating_system", "county_fips",
                                             "paid_building_real"])
    clean["year"] = pd.to_numeric(clean["loss_year"]).astype(int)
    print(f"\nColonnes de zone dans claims_clean.parquet : flood_zone_group uniquement (pas de ratedFloodZone brut).")
    raw_path = ROOT / "Data_cleaning" / "NfipClaimsV3_SE.parquet"
    code_change = None
    if raw_path.exists():
        raw = pd.read_parquet(raw_path, columns=["id", "ratedFloodZone"])
        r = clean[["id", "year", "flood_zone_group"]].merge(raw, on="id", how="left", validate="one_to_one")
        r = r[r["year"].between(TRAIN[0], TEST[1])]
        r["code"] = r["ratedFloodZone"].fillna("NA")
        ct = r.groupby(["year", "code"]).size().unstack(fill_value=0)
        share = ct.div(ct.sum(axis=1), axis=0)
        ct.to_csv(CRES / "vc3_codes_bruts_ratedFloodZone_par_annee.csv")
        before = share.loc[:2021]
        after = share.loc[2022:]
        appear = [c for c in share.columns if (before[c] == 0).all() and (after[c] > 0).any()]
        disappear = [c for c in share.columns if (before[c] > 0).any() and (after[c] == 0).all()]
        big = [c for c in appear + disappear if share[c].max() >= 0.01]
        print(f"Fichier brut lu (agrégation seulement) : {raw_path.name}, restreint aux id de claims_clean, années 2010-2024 "
              f"({len(r)} sinistres).")
        main_codes = share.max().sort_values(ascending=False).head(12).index
        print("Part des principaux codes bruts par année :\n" + share[main_codes].round(4).to_string())
        print(f"Codes présents seulement jusqu'en 2021 : {disappear or 'aucun'} ; seulement à partir de 2022 : "
              f"{appear or 'aucun'} ; parmi eux, part annuelle max ≥ 1 % : {big or 'aucun'}")
        grp = r.groupby(["year", r["flood_zone_group"].astype(str)]).size().unstack(fill_value=0)
        print("Groupes de claims_clean par année (y compris D, autre, NA) :\n" + grp.to_string())
        code_change = bool(big)
    else:
        print(f"{raw_path.name} absent : liste des codes bruts non calculable.")

    # Système de tarification (claims_clean)
    c = clean[clean["year"].between(TRAIN[0], TEST[1]) & clean["county_fips"].notna()
              & clean["flood_zone_group"].astype(str).isin(ZONES)].copy()
    c["paid"] = pd.to_numeric(c["paid_building_real"], errors="coerce") > 0
    rs = c.groupby(["year", c["flood_zone_group"].astype(str), c["rating_system"].astype(str)]).agg(
        tous=("id", "size"), payes=("paid", "sum")).reset_index()
    rs["part_tous_dans_annee_zone"] = rs["tous"] / rs.groupby(["year", "flood_zone_group"])["tous"].transform("sum")
    rs.to_csv(CRES / "vc3_systeme_tarification.csv", index=False)
    piv = rs[rs["rating_system"].str.startswith("Risk")].pivot(index="year", columns="flood_zone_group",
                                                                 values="part_tous_dans_annee_zone").fillna(0)
    print("\nPart des sinistres (tous) codés Risk Rating 2.0, par année et par zone :\n" + piv.round(3).to_string())
    print("Exposition par système de tarification : non disponible dans les fichiers propres (zone_year.parquet "
          "n'a pas cette ventilation) ; rien n'est reconstruit.")
    status = "ÉCART" if code_change else ("CONFORME" if code_change is False else "ÉCART")
    m_ = mult
    concl = (f"Taux de sinistres payés, test / entraînement : V* × {m_.loc['V*', 'multiplicateur_payes']:.2f}, "
             f"A* × {m_.loc['A*', 'multiplicateur_payes']:.2f}, X × {m_.loc['X', 'multiplicateur_payes']:.2f}. "
             + ("Des codes bruts représentant au moins 1 % d'une année apparaissent ou disparaissent autour de fin 2021 : "
                "un changement de codage est une hypothèse à vérifier (voir la sortie)." if code_change else
                "Aucun code brut représentant au moins 1 % d'une année n'apparaît ni ne disparaît entre 2010-2021 et "
                "2022-2024." if code_change is False else "Codes bruts non vérifiables (fichier brut absent).")
             + " La part Risk Rating 2.0 est tabulée par année et zone ; aucune cause n'est attribuée.")
    return status, concl


# ------------------------------------------------------------------------------------------- VC4
def vc4_lignes_exclues():
    import statsmodels.api as sm
    ds = load_ds()
    excl = ds[ds[["zone", "mean_coverage", "hist_per_1000", "county_hist_per_1000"]].isna().any(axis=1)]
    print(excl[["county_id", "zone", "year", "period", "exposure_years", "n_claims", "n_all",
                "hist_per_1000", "county_hist_per_1000"]].to_string(index=False))
    all_test = bool((excl["period"] == "test").all())
    no_claim = bool((excl["n_claims"] == 0).all() and (excl["n_all"] == 0).all())
    te_all = ds[ds["period"] == "test"]
    share = excl["exposure_years"].sum() / te_all["exposure_years"].sum()
    print(f"\nToutes en test : {all_test} ; aucun sinistre (payés et tous) : {no_claim} ; "
          f"part de l'exposition du test : {share:.3e}")
    d, _ = prepare(ds)
    rows = []
    worst = 0.0
    for code, col in TARGETS.items():
        tr = d[d["period"] == "train"]
        rate = tr[col].sum() / tr["exposure_years"].sum()
        m1 = sm.GLM(tr[col].to_numpy(float), zone_design(tr), family=sm.families.Poisson(), offset=tr["log_e"]).fit()
        full = te_all.copy()
        full["log_e"] = np.log(full["exposure_years"])
        mu0 = rate * full["exposure_years"]
        mu1 = m1.predict(zone_design(full), offset=full["log_e"])
        keep = full.index.isin(d.index[d["period"] == "test"]) if False else ~full.index.isin(excl.index)
        for name, mu in [("M0", mu0), ("M1", mu1)]:
            dev_with = poisson_deviance(full[col], mu).sum()
            dev_without = poisson_deviance(full.loc[keep, col], mu[keep]).sum()
            rel = (dev_with - dev_without) / dev_without
            worst = max(worst, abs(rel))
            rows.append({"cible": code, "modele": name, "deviance_test_avec_13": dev_with,
                         "deviance_test_sans_13": dev_without, "ecart_relatif": rel})
    t = pd.DataFrame(rows)
    t.to_csv(CRES / "vc4_lignes_exclues.csv", index=False)
    excl.to_csv(CRES / "vc4_liste_13_lignes.csv", index=False)
    print(t.to_string(index=False))
    ok = all_test and no_claim and worst < 1e-3
    status = "CONFORME" if ok else "ÉCART"
    concl = (f"Les 13 lignes sont toutes en test, sans aucun sinistre, et pèsent {share:.1e} de l'exposition du test. "
             f"Les inclure change la déviance de test de M0 et M1 d'au plus {worst:.1e} en relatif : exclusion "
             f"négligeable.") if ok else "Voir la sortie : l'exclusion n'est pas négligeable selon le critère retenu."
    return status, concl


CHECKS = [("VC1", "Offset dans la validation de LightGBM", vc1_offset_validation),
          ("VC2", "Contrôle croisé de M3 (binomial négatif)", vc2_binomial_negatif),
          ("VC3", "Zone × temps et système de tarification", vc3_zone_temps),
          ("VC4", "Les 13 lignes exclues", vc4_lignes_exclues)]


def main():
    t0 = time.time()
    out = ["# Vérifications complémentaires VC1 à VC4\n",
           f"> Générées par `{CMD}` le {time.strftime('%d/%m/%Y à %H:%M:%S %Z')}. Graine : 42. Chaque section : "
           "commande, sortie brute, statut (CONFORME / ÉCART / DÉFAUT) et conclusion calculée selon les règles du "
           "script.\n"]
    summary = []
    for code, title, fn in CHECKS:
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                status, concl = fn()
        except Exception as exc:
            status, concl = "DÉFAUT", f"Exception : {type(exc).__name__}: {exc}"
        summary.append((code, title, status))
        out += [f"## {code} {title} : **{status}**\n", f"Commande : `{CMD}`, fonction `{fn.__name__}`.\n",
                "```text", buf.getvalue().rstrip(), "```\n", f"**Conclusion** : {concl}\n"]
        print(f"{code} {title} : {status}")
    from ccommun import md_table
    out.insert(2, "## Synthèse\n\n" + md_table(pd.DataFrame(summary, columns=["vérification", "intitulé", "statut"])) + "\n")
    out.append(f"Durée : {time.time() - t0:.1f} s.")
    (COMP / "VERIFICATIONS_COMPLEMENTAIRES.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    if any(s == "DÉFAUT" and c == "VC1" for c, _, s in summary):
        print("VC1 en DÉFAUT : un nouveau réglage de M4 est requis avant les ablations.")
        sys.exit(3)


if __name__ == "__main__":
    main()
