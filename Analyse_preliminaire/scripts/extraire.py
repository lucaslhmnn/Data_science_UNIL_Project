"""Construit, à partir des fichiers EXISTANTS uniquement (aucun modèle, aucun recalcul de déviance) :
tableaux/chiffres_cles.json, tableaux/*.csv et *.md, figures/*.png, STATUT_RESULTATS.md, TRACABILITE.md.
Usage (racine du dépôt) : Modeles/.venv/bin/python Analyse_preliminaire/scripts/extraire.py"""
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registre as R  # noqa: E402

AP, ROOT = R.AP, R.ROOT
TAB, FIG = AP / "tableaux", AP / "figures"
VERSION, DATE = "v0.1", "15/11/2026"
STAT_EN = {"E": "[Established]", "P": "[Provisional, exploratory]", "N": "[Not demonstrated]"}
COL = {"M0": "#8a8984", "M1": "#c9c8c2", "M_oracle": "#1baf7a", "M2": "#2a78d6", "M3": "#eda100", "M4": "#eb6834"}
MODEL_EN = {"M0": "M0 null", "M1": "M1 GLM, zone", "M_oracle": "M_oracle (not predictive)", "M2": "M2 Poisson GLM",
            "M3": "M3 negative binomial GLM", "M4": "M4 LightGBM"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#e6e5e1", "axes.axisbelow": True, "axes.titlelocation": "left",
                     "figure.facecolor": "white"})


def rd(p):
    return pd.read_csv(ROOT / p)


def save_table(name, df, sources, statut, titre):
    df.to_csv(TAB / f"{name}.csv", index=False)
    head = [f"<!-- {name} | {titre} | sources : {', '.join(sources)} | statut : {R.STATUTS[statut][0]} | "
            f"{VERSION}, {DATE} ; résultats provisoires et exploratoires, voir STATUT_RESULTATS.md -->",
            f"**{titre}** {R.STATUTS[statut][0]}", "", f"Sources : {', '.join(f'`{s}`' for s in sources)}", ""]
    (TAB / f"{name}.md").write_text("\n".join(head) + "\n" + R_md(df) + "\n", encoding="utf-8")
    return name


def R_md(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |")
    return "\n".join(out)


def pct(v):
    return None if pd.isna(v) else round(100 * v, 2)


# ------------------------------------------------------------------------------------------------ chiffres
def build_chiffres():
    ck = {}
    for k, (src, kind) in R.CHIFFRES.items():
        v = R.value(k)
        f, cell = R.source_text(k)
        rid = [r[0] for r in R.RESULTATS if k in r[2]]
        ck[k] = {"valeur": v, "affichage": R.fmt(v, kind), "format": kind, "source": f, "cellule": cell, "resultat": rid}
    (TAB / "chiffres_cles.json").write_text(json.dumps(ck, indent=1, ensure_ascii=False), encoding="utf-8")
    return ck


# ------------------------------------------------------------------------------------------------ tableaux
def build_tables(ck):
    made = []
    M, C = R.M, R.C
    t = pd.DataFrame([
        ["Raw claims, FEMA Region 4", ck["raw_claims"]["affichage"]],
        ["Single-family homes (occupancyType 1 or 11)", ck["single_family"]["affichage"]],
        ["Set aside as anomalies", ck["anomalies"]["affichage"]],
        ["Cleaned claims (claims_clean)", ck["clean_claims"]["affichage"]],
        ["Analysis table ds_clean: county x zone x year rows", ck["ds_rows"]["affichage"]],
        ["Rows used by the models (missing feature excluded)", ck["rows_used"]["affichage"]],
        ["Training rows 2010-2019", ck["rows_train"]["affichage"]],
        ["Test rows 2020-2024", ck["rows_test"]["affichage"]]], columns=["Step", "Count"])
    made.append(save_table("tab_ap_volumes", t, [R.CLEAN_REPORT, "EDA/ds_clean_roles.json", f"{M}/preparation.json",
                                                 f"{M}/ajustement_payes.json"], "E", "Data volumes"))
    t = pd.DataFrame([["Negative building age", ck["anom_neg_age"]["affichage"]],
                      ["Exact duplicate (lowest id kept)", ck["anom_duplicate"]["affichage"]],
                      ["Payment without building coverage", ck["anom_paid_nocov"]["affichage"]],
                      ["Negative payment", ck["anom_neg_paid"]["affichage"]],
                      ["Of which with two reasons", ck["anom_two_reasons"]["affichage"]]], columns=["Reason", "Claims"])
    made.append(save_table("tab_ap_anomalies", t, [R.CLEAN_REPORT], "E", "Claims set aside as anomalies"))

    dv, rc = rd(f"{M}/deviance_par_modele.csv"), rd(f"{M}/diagnostic_deviance_recalee_par_annee.csv")
    rows = []
    for m in ["M1", "M2", "M3", "M4", "M_oracle"]:
        r = [MODEL_EN[m]]
        for c in ["payes", "tous"]:
            g = dv[(dv.cible == c) & (dv.modele == m)].set_index("ensemble")["gain_relatif_vs_M0"]
            rr = rc[(rc.cible == c) & (rc.modele == m)].iloc[0]
            r += [pct(g["test 2020-2024"]), pct(g["test sans 2024"]), pct(rr["gain_vs_M0_recalee"])]
        rows.append(r)
    t = pd.DataFrame(rows, columns=["Model", "Paid: test", "Paid: test excl. 2024", "Paid: rescaled",
                                    "All: test", "All: test excl. 2024", "All: rescaled"])
    made.append(save_table("tab_ap_gains", t, [f"{M}/deviance_par_modele.csv", f"{M}/diagnostic_deviance_recalee_par_annee.csv"],
                           "P", "Gain in test Poisson deviance relative to M0 (%)"))

    py = rd(f"{M}/par_annee_calibration_deviance.csv")
    py = py[(py.cible == "payes") & (py.periode == "test") & py.modele.isin(["M0", "M1", "M2", "M3", "M4"])]
    t = py.pivot(index="modele", columns="annee", values="ratio_predit_observe").round(2)
    tot = rd(f"{M}/calibration_totale_par_periode.csv")
    tot = tot[(tot.cible == "payes") & (tot.period == "test")].set_index("modele")["ratio_predit_observe"]
    t["2020-2024"] = tot.reindex(t.index).round(2)
    t.columns = [str(c) for c in t.columns]
    t = t.reset_index().rename(columns={"modele": "Model"})
    t["Model"] = t["Model"].map(MODEL_EN)
    made.append(save_table("tab_ap_calibration", t, [f"{M}/par_annee_calibration_deviance.csv", f"{M}/calibration_totale_par_periode.csv"],
                           "P", "Predicted / observed paid claims by test year"))

    ab = rd(f"{C}/ablation_deviance.csv")
    cal = rd(f"{C}/ablation_calibration_annee.csv")
    desc = {"M1": "GLM: zone", "M2": "GLM: zone + coverage + histories", "G1": "GLM: zone + histories",
            "G3": "GLM: zone + coverage", "G5_hp": "GLM: zone + coverage bands (outside protocol)",
            "M4": "LightGBM: zone + coverage + histories", "L1": "LightGBM: zone + histories",
            "L2": "LightGBM: zone + coverage + cell history", "L3": "LightGBM: zone + coverage",
            "L5": "LightGBM: zone", "L6": "LightGBM: zone + coverage rank in year + histories"}
    for c, lab in [("payes", "paid"), ("tous", "all")]:
        rows = []
        for m, dsc in desc.items():
            g = ab[(ab.cible == c) & (ab.modele == m)].set_index("ensemble")["gain_vs_M0"]
            ratio = cal[(cal.cible == c) & (cal.modele == m) & (cal.annee == "total")]["ratio_predit_observe"].iloc[0]
            rows.append([m, dsc, pct(g["test"]), pct(g["test_sans_2024"]), pct(g["test_recale"]), round(ratio, 2)])
        t = pd.DataFrame(rows, columns=["Model", "Features", "Test", "Test excl. 2024", "Rescaled", "Pred./obs."])
        made.append(save_table(f"tab_ap_ablation_{lab}", t, [f"{C}/ablation_deviance.csv", f"{C}/ablation_calibration_annee.csv"],
                               "P", f"Ablation, {lab} claims: gain relative to M0 (%) and predicted / observed"))

    z = rd(f"{C}/vc3_multiplicateur_zone.csv")
    t = pd.DataFrame({"Zone": z.zone, "Paid, train": z.taux_payes_train.round(2), "Paid, test": z.taux_payes_test.round(2),
                      "Paid, ratio": z.multiplicateur_payes.round(2), "All, train": z.taux_tous_train.round(2),
                      "All, test": z.taux_tous_test.round(2), "All, ratio": z.multiplicateur_tous.round(2)})
    made.append(save_table("tab_ap_zone_shift", t, [f"{C}/vc3_multiplicateur_zone.csv"], "E",
                           "Observed claims per 1,000 policy-years by zone, training vs test"))

    perm = rd(f"{M}/importance_permutation_test_m4.csv")
    gain = rd(f"{M}/importance_gain_payes.csv").set_index("variable")["part_gain"]
    perm = perm[perm.cible == "payes"]
    t = pd.DataFrame({"Feature": perm.variable, "Share of training gain (%)": perm.variable.map(gain).mul(100).round(1).values,
                      "Test deviance increase when permuted": perm.hausse_deviance_test_moyenne.round(0).astype(int).values,
                      "Std. dev. (20 permutations)": perm.hausse_deviance_test_ecart_type.round(0).astype(int).values})
    made.append(save_table("tab_ap_importance", t, [f"{M}/importance_permutation_test_m4.csv", f"{M}/importance_gain_payes.csv"],
                           "P", "M4 feature importance (paid claims)"))

    co = rd(f"{M}/coefficients_payes.csv")
    t = co[["modele", "variable", "coefficient", "es_modele", "es_robuste_HC0", "es_grappes_annee"]].copy()
    t.columns = ["Model", "Term", "Coefficient", "SE (model)", "SE (HC0)", "SE (clustered by year)"]
    t = t.round(4)
    made.append(save_table("tab_ap_coefficients", t, [f"{M}/coefficients_payes.csv"], "P",
                           "M2 and M3 coefficients, paid claims (standard errors indicative only)"))

    # Annexes
    piv = ab.pivot_table(index=["cible", "modele"], columns="ensemble", values="gain_vs_M0").mul(100).round(2).reset_index()
    piv = piv[["cible", "modele", "train", "test", "test_sans_2024", "test_recale", "test_sans_2024_recale"]]
    piv.columns = ["Target", "Model", "Train", "Test", "Test excl. 2024", "Rescaled", "Rescaled excl. 2024"]
    made.append(save_table("tab_ap_annexe_ablation_complete", piv, [f"{C}/ablation_deviance.csv"], "P",
                           "Appendix: full ablation, gain relative to M0 (%)"))
    ca = cal[(cal.cible == "payes")].pivot(index="modele", columns="annee", values="ratio_predit_observe").round(2).reset_index()
    ca.columns = ["Model"] + [str(c) for c in ca.columns[1:]]
    made.append(save_table("tab_ap_annexe_calibration", ca, [f"{C}/ablation_calibration_annee.csv"], "P",
                           "Appendix: predicted / observed by test year, all ablation models (paid)"))
    df = rd(f"{C}/ablation_diff_par_annee.csv")
    df = df.pivot_table(index=["cible", "modele", "reference"], columns="annee",
                        values="difference_modele_moins_reference").round(0).reset_index()
    df.columns = ["Target", "Model", "Reference"] + [str(c) for c in df.columns[3:]]
    made.append(save_table("tab_ap_annexe_diff_annee", df, [f"{C}/ablation_diff_par_annee.csv"], "P",
                           "Appendix: deviance difference with the reference model, by test year (negative = better)"))
    gc = rd(f"{C}/ablation_coefficients_glm.csv")
    gc = gc[gc.cible == "payes"][["modele", "variable", "coefficient", "es_robuste_HC0", "es_grappes_annee"]].round(4)
    gc.columns = ["Model", "Term", "Coefficient", "SE (HC0)", "SE (clustered by year)"]
    made.append(save_table("tab_ap_annexe_coefficients_glm", gc, [f"{C}/ablation_coefficients_glm.csv"], "P",
                           "Appendix: coefficients of the ablation GLMs (paid; indicative standard errors)"))
    rows = []
    for path, pat in [("Modeles/VERIFICATIONS.md", r"^\| (V\d) \| (.+?) \| (.+?) \| (.+?) \|"),
                      ("Modeles/complements/VERIFICATIONS_COMPLEMENTAIRES.md", r"^\| (VC\d) \| (.+?) \| (.+?) \|")]:
        for ln in (ROOT / path).read_text().splitlines():
            mm = re.match(pat, ln)
            if mm:
                g = mm.groups()
                rows.append([g[0], g[1], g[2] if g[0].startswith("VC") else g[3], path])
    t = pd.DataFrame(rows, columns=["Check", "Title (French, as in source)", "Status (as in source)", "Source"])
    made.append(save_table("tab_ap_annexe_verifications", t, ["Modeles/VERIFICATIONS.md",
                                                              "Modeles/complements/VERIFICATIONS_COMPLEMENTAIRES.md"],
                           "E", "Appendix: technical checks V1-V8 and VC1-VC4"))
    return made


# ------------------------------------------------------------------------------------------------ figures
def build_figures():
    srcs = {}
    C, M = R.C, R.M
    z = rd(f"{C}/vc3_zone_annee.csv")
    fig, ax = plt.subplots(figsize=(10, 4.4), layout="constrained")
    for zz, col in [("V*", "#eb6834"), ("A*", "#2a78d6"), ("X", "#1baf7a")]:
        s = z[z.zone == zz]
        ax.plot(s.year, s.taux_payes_1000, "-o", ms=4, color=col, label=f"zone {zz}")
    ax.set_yscale("log")
    ax.axvspan(2019.5, 2024.5, color="#2a78d6", alpha=0.06, lw=0)
    ax.set_xticks(range(2010, 2025))
    ax.set_ylabel("Paid claims per 1,000 policy-years (log scale)")
    ax.set_title("Observed paid-claim rate by flood zone and year (descriptive; test years shaded)")
    ax.legend(frameon=False)
    fig.savefig(FIG / "fig_ap_zone_rates.png", dpi=200)
    plt.close(fig)
    srcs["fig_ap_zone_rates.png"] = [f"{C}/vc3_zone_annee.csv"]

    dv, rc = rd(f"{M}/deviance_par_modele.csv"), rd(f"{M}/diagnostic_deviance_recalee_par_annee.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True, layout="constrained")
    models = ["M1", "M2", "M3", "M4"]
    for ax, c, lab in zip(axes, ["payes", "tous"], ["paid claims", "all claims"]):
        raw = [100 * dv[(dv.cible == c) & (dv.modele == m) & (dv.ensemble == "test 2020-2024")].gain_relatif_vs_M0.iloc[0] for m in models]
        rec = [100 * rc[(rc.cible == c) & (rc.modele == m)].gain_vs_M0_recalee.iloc[0] for m in models]
        x = range(len(models))
        ax.bar([i - 0.2 for i in x], raw, 0.38, color=[COL[m] for m in models], label="raw")
        ax.bar([i + 0.2 for i in x], rec, 0.38, color=[COL[m] for m in models], alpha=0.45, hatch="//", label="rescaled by year")
        for i, (a, b) in enumerate(zip(raw, rec)):
            ax.text(i - 0.2, a + (0.4 if a >= 0 else -1.2), f"{a:+.1f}", ha="center", fontsize=8.5)
            ax.text(i + 0.2, b + (0.4 if b >= 0 else -1.2), f"{b:+.1f}", ha="center", fontsize=8.5)
        ax.axhline(0, color="#0b0b0b", lw=1)
        ax.set_xticks(list(x), [MODEL_EN[m] for m in models], fontsize=8.5)
        ax.set_title(lab)
    axes[0].set_ylabel("Gain in test Poisson deviance vs M0 (%)")
    axes[0].legend(frameon=False, fontsize=8.5)
    fig.suptitle("Exploratory: test deviance gain relative to the null model, raw and rescaled by year "
                 "(rescaling uses observed yearly totals)", x=0.01, ha="left", fontsize=11)
    fig.savefig(FIG / "fig_ap_gains.png", dpi=200)
    plt.close(fig)
    srcs["fig_ap_gains.png"] = [f"{M}/deviance_par_modele.csv", f"{M}/diagnostic_deviance_recalee_par_annee.csv"]

    py = rd(f"{M}/par_annee_calibration_deviance.csv")
    py = py[(py.cible == "payes") & (py.periode == "test")]
    fig, ax = plt.subplots(figsize=(10, 4.4), layout="constrained")
    for m in ["M0", "M2", "M3", "M4"]:
        s = py[py.modele == m]
        ax.plot(s.annee, s.ratio_predit_observe, "-o", ms=5, color=COL[m], label=MODEL_EN[m])
    ax.axhline(1, color="#0b0b0b", lw=1, ls=":")
    ax.set_yscale("log")
    ax.set_xticks(range(2020, 2025))
    ax.set_ylabel("Predicted / observed paid claims (log scale)")
    ax.set_title("Exploratory: calibration by test year (1 = calibrated); models fitted on 2010-2019")
    ax.legend(frameon=False, fontsize=8.5)
    fig.savefig(FIG / "fig_ap_calibration.png", dpi=200)
    plt.close(fig)
    srcs["fig_ap_calibration.png"] = [f"{M}/par_annee_calibration_deviance.csv"]

    ab = rd(f"{C}/ablation_deviance.csv")
    ab = ab[ab.cible == "payes"]
    order = ["M1", "M2", "G1", "G3", "G5_hp", "M4", "L1", "L2", "L3", "L5", "L6"]
    lab = {"M1": "M1 GLM zone", "M2": "M2 GLM full", "G1": "G1 GLM no coverage", "G3": "G3 GLM zone + coverage",
           "G5_hp": "G5_hp GLM zone + coverage bands*", "M4": "M4 LightGBM full", "L1": "L1 LightGBM no coverage",
           "L2": "L2 LightGBM no county history", "L3": "L3 LightGBM zone + coverage", "L5": "L5 LightGBM zone only",
           "L6": "L6 LightGBM coverage rank in year"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True, layout="constrained")
    for ax, ens, ttl in zip(axes, ["test", "test_recale"], ["raw", "rescaled by year (uses observed totals)"]):
        v = [100 * ab[(ab.modele == m) & (ab.ensemble == ens)].gain_vs_M0.iloc[0] for m in order]
        y = list(range(len(order)))[::-1]
        cols = ["#8a8984" if m in ("M1", "M2", "M4") else ("#c9c8c2" if m.endswith("_hp") else
                ("#2a78d6" if m.startswith("G") else "#eb6834")) for m in order]
        ax.barh(y, v, color=cols, height=0.65)
        for yi, val in zip(y, v):
            ax.text(val + (0.4 if val >= 0 else -0.4), yi, f"{val:+.1f}", va="center",
                    ha="left" if val >= 0 else "right", fontsize=8.5)
        ax.set_xlim(min(0, min(v)) - 5, max(0, max(v)) + 4)
        ax.axvline(0, color="#0b0b0b", lw=1)
        ax.set_yticks(y, [lab[m] for m in order], fontsize=9)
        ax.set_xlabel("Gain in test Poisson deviance vs M0 (%)")
        ax.set_title(ttl)
    fig.suptitle("Exploratory ablation, paid claims (* added outside the pre-registered protocol)", x=0.01,
                 ha="left", fontsize=11)
    fig.savefig(FIG / "fig_ap_ablation.png", dpi=200)
    plt.close(fig)
    srcs["fig_ap_ablation.png"] = [f"{C}/ablation_deviance.csv"]

    lines = ["# Sources des figures", "", f"> {VERSION}, {DATE}. Branche `modeles-premier-jet`. Aucun commit à ce stade. "
             "Figures régénérées par `Analyse_preliminaire/scripts/extraire.py` à partir des CSV existants, jamais à "
             "partir des modèles. Titres en anglais, conformément à `CLAUDE.md` (English only). Résultats "
             "provisoires et exploratoires, voir `STATUT_RESULTATS.md`.", "",
             "| Figure | CSV d'origine | Script |", "|---|---|---|"]
    for f, s in srcs.items():
        lines.append(f"| `figures/{f}` | {', '.join(f'`{x}`' for x in s)} | `scripts/extraire.py` (fonction `build_figures`) |")
    (FIG / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return list(srcs)


# ------------------------------------------------------------------------------------------------ registres
def header(titre):
    return [f"# {titre}", "", f"> {DATE} · branche `modeles-premier-jet` · version `{VERSION}` · "
            "**Résultats provisoires et exploratoires, voir `STATUT_RESULTATS.md`** · aucun commit à ce stade.", ""]


def build_statut(ck):
    out = header("Registre des résultats (STATUT_RESULTATS)")
    out += ["Ce registre est la base du travail futur. Chaque résultat cité dans `section_modelisation.qmd` y figure, "
            "avec un identifiant repris dans le texte sous la forme d'un commentaire `<!-- Rk -->`. Quand un résultat "
            "change de statut, on modifie sa ligne et on ajoute une entrée au journal ; le texte n'a pas besoin d'être "
            "réécrit tant que ses formulations restent conditionnelles.", "",
            "## Étiquettes", "",
            "| Étiquette (dossier) | Équivalent dans la section (anglais) | Définition |", "|---|---|---|",
            "| **[Établi]** | [Established] | Calcul vérifié, reproductible, indépendant des choix de modélisation "
            "évalués sur le test : chaîne de données, vérifications techniques, reproduction exacte des références, "
            "constats descriptifs sur les données. |",
            "| **[Provisoire, exploratoire]** | [Provisional, exploratory] | Calcul correct dont la portée est limitée "
            "par le dispositif : 5 années de test, dépendance entre cellules, variantes comparées sur le même test, "
            "jeu de 4 variables, exposition non validée pour les petites cellules, recalage utilisant les totaux "
            "observés. Statut par défaut des gains de déviance, de l'ablation et de la lecture des variables. |",
            "| **[Non démontré]** | [Not demonstrated] | Hypothèse formulée mais non testée. |", "",
            "## Registre", "",
            "| Id | Énoncé | Valeur(s) | Fichier(s) source | Statut | Condition pour changer de statut | Version |",
            "|---|---|---|---|---|---|---|"]
    counts = {"E": 0, "P": 0, "N": 0}
    for rid, txt, keys, st, cond in R.RESULTATS:
        counts[st] += 1
        vals = "; ".join(f"`{k}` = {ck[k]['affichage']}" for k in keys) or "aucune valeur (hypothèse)"
        srcs = ", ".join(sorted({ck[k]["source"] for k in keys})) or "—"
        out.append(f"| {rid} | {txt} | {vals} | {srcs} | {R.STATUTS[st][0]} | {cond} | {VERSION} |")
    out += ["", f"Décompte : {counts['E']} [Établi], {counts['P']} [Provisoire, exploratoire], {counts['N']} [Non démontré].",
            "", "## Journal des versions", "", "| Version | Date | Contenu |", "|---|---|---|",
            f"| {VERSION} | {DATE} | Création : registre de {len(R.RESULTATS)} résultats issus du premier jet "
            "(`Modeles/`) et des compléments (`Modeles/complements/`). Aucun nouveau modèle. |"]
    (AP / "STATUT_RESULTATS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    return counts


def build_tracabilite(ck):
    qmd = (AP / "section_modelisation.qmd").read_text() if (AP / "section_modelisation.qmd").exists() else ""
    used = set(re.findall(r'ck\("([A-Za-z0-9_]+)"\)', qmd))
    out = header("Traçabilité des chiffres")
    out += ["Chaque chiffre de `section_modelisation.qmd` est inséré par du code (`ck(\"clé\")`) qui lit "
            "`tableaux/chiffres_cles.json`, lui-même extrait des fichiers ci-dessous par `scripts/extraire.py`. "
            "Aucun chiffre n'est écrit à la main dans la section (règle de `CLAUDE.md`). "
            "`scripts/verifier_chiffres.py` relit chaque source et compare (tolérance relative 1e-9 sur la valeur, "
            "égalité exacte de l'affichage arrondi).", "",
            "Les chiffres des tableaux de la section sont lus directement dans `tableaux/*.csv` (sources indiquées en "
            "tête de chaque `tableaux/*.md`).", "",
            "| Clé | Affichage | Valeur exacte | Fichier source | Cellule | Résultat | Cité dans la section |",
            "|---|---|---|---|---|---|---|"]
    for k, d in ck.items():
        out.append(f"| `{k}` | {d['affichage']} | {d['valeur']:.10g} | {d['source']} | {d['cellule']} | "
                   f"{', '.join(d['resultat'])} | {'oui' if k in used else 'non (registre seulement)'} |")
    out += ["", "## Chiffres retirés faute de source", "",
            "- Couverture moyenne pondérée de 203,6 k$ (entraînement) et 222,0 k$ (test), et facteur 0,904 sur les "
            "prédictions de M2, cités au § 7.3 de `Modeles/RAPPORT_MODELES.md` : calculés en exploration, absents de "
            "tout CSV ou JSON. Remplacés par les parts d'exposition de la tranche de couverture la plus haute "
            "(`hp_taux_par_tranche_couverture.csv`).", ""]
    (AP / "TRACABILITE.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    ck = build_chiffres()
    tabs = build_tables(ck)
    figs = build_figures()
    counts = build_statut(ck)
    build_tracabilite(ck)
    print(f"{len(ck)} chiffres, {len(tabs)} tableaux, {len(figs)} figures ; statuts : {counts}")


if __name__ == "__main__":
    main()
