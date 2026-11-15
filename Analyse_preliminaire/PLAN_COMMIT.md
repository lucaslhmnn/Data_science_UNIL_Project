# Plan de commit (proposé, NON exécuté)

> 15/11/2026 · branche `modeles-premier-jet` · version `v0.1` · **Résultats provisoires et exploratoires, voir
> `STATUT_RESULTATS.md`** · aucun commit à ce stade. **Aucune de ces commandes n'a été lancée : elles
> attendent l'accord explicite de l'équipe.**

## Principes

- **Branche** : `modeles-premier-jet`. Pas de push, pas de merge vers `main` dans ce plan.
- **Deux commits** :
  1. `Modeles/` : le premier jet et les compléments, qui sont les **sources** des chiffres ;
  2. `Analyse_preliminaire/`.

  Le dossier `Analyse_preliminaire/` lit les résultats de `Modeles/`. Le commiter seul casserait sa
  traçabilité.
- **Ajout par liste explicite** (`--pathspec-from-file`), jamais `git add .`.
- **Exclus** :
  - par le `.gitignore` existant : `.venv/`, `__pycache__/`, `.DS_Store` ;
  - explicitement : les rendus générés (`Analyse_preliminaire/rendu_test.html`, `rendu_test_files/`,
    `rendu_verification*`) ;
  - aucune donnée brute ; aucun fichier de plus de 10 Mo (le plus gros fait 6,9 Mio).
- **Volume** : environ 24 Mo, dont 21 Mo pour les 4 CSV de prédictions (voir l'option B).

**Aucun fichier existant du dépôt n'est concerné.** Les corrections des fichiers suivis ont été annulées
(`INCOHERENCES_DOCUMENTAIRES.md`, statut). `git status` ne doit montrer que `Modeles/` et
`Analyse_preliminaire/`, comme non suivis.

## Option A (recommandée pour la traçabilité complète) : tout, prédictions comprises

```bash
# Commit 1 : Modeles/
git add --pathspec-from-file=Analyse_preliminaire/plan_commit_modeles.txt
git status --short           # contrôler : uniquement Modeles/, rien d'autre
git commit -m "Modèles de fréquence, premier jet et compléments (exploratoires, local)

- Modeles/ : protocole pré-enregistré, vérifications V1 à V8, M0 à M4, évaluation.
- Modeles/complements/ : vérifications VC1 à VC4, table d'ablation.
Résultats provisoires et exploratoires ; aucun push.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

# Commit 2 : Analyse_preliminaire/
git add --pathspec-from-file=Analyse_preliminaire/plan_commit_analyse_preliminaire.txt
git status --short
git commit -m "Analyse préliminaire : section du rapport, registre des résultats, traçabilité

- section_modelisation.qmd (anglais), chiffres insérés par code depuis tableaux/chiffres_cles.json.
- STATUT_RESULTATS.md (23 résultats), TRACABILITE.md, incohérences documentaires proposées.
Résultats provisoires et exploratoires ; aucun push.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Option B (historique plus léger) : sans les 4 CSV de prédictions

Retirer ces 4 lignes de `plan_commit_modeles.txt` avant le commit 1 (−21 Mo). Ils se régénèrent en quelques
secondes avec `Modeles/run_all.sh` et `Modeles/complements/run_all.sh`, mais `Modeles/complements` en a
besoin (VC2 et le contrôle de reproduction) :

```
Modeles/resultats/predictions_payes.csv
Modeles/resultats/predictions_tous.csv
Modeles/complements/resultats/ablation_predictions_payes.csv
Modeles/complements/resultats/ablation_predictions_tous.csv
```

## Listes exactes

Les deux listes sont jointes : `plan_commit_modeles.txt` et `plan_commit_analyse_preliminaire.txt`, une
ligne par fichier, générées depuis `git status --porcelain --untracked-files=all` le 15/11/2026.

### plan_commit_modeles.txt (98 fichiers)
```
Modeles/ENTREES.txt
Modeles/PROTOCOLE.md
Modeles/RAPPORT_MODELES.md
Modeles/README.md
Modeles/VERIFICATIONS.md
Modeles/complements/ENTREES.txt
Modeles/complements/PROTOCOLE_COMPLEMENTAIRE.md
Modeles/complements/RAPPORT_COMPLEMENTS.md
Modeles/complements/README.md
Modeles/complements/VERIFICATIONS_COMPLEMENTAIRES.md
Modeles/complements/figures/ablation_gain_brut.png
Modeles/complements/figures/ablation_gain_recale.png
Modeles/complements/figures/vc3_taux_zone_annee.png
Modeles/complements/logs/00_environnement.log
Modeles/complements/logs/c1_verifications.log
Modeles/complements/logs/c2_ablation_modeles.log
Modeles/complements/logs/c3_ablation_evaluation.log
Modeles/complements/logs/c4_descriptif_couverture_hp.log
Modeles/complements/logs/durees.log
Modeles/complements/resultats/ablation_calibration_annee.csv
Modeles/complements/resultats/ablation_coefficients_glm.csv
Modeles/complements/resultats/ablation_deviance.csv
Modeles/complements/resultats/ablation_diff_par_annee.csv
Modeles/complements/resultats/ablation_importance_lgb.csv
Modeles/complements/resultats/ablation_predictions_payes.csv
Modeles/complements/resultats/ablation_predictions_tous.csv
Modeles/complements/resultats/ablation_reproduction_premier_jet.csv
Modeles/complements/resultats/ablation_variables_construites.json
Modeles/complements/resultats/hp_taux_par_tranche_couverture.csv
Modeles/complements/resultats/lgb_L1_payes.txt
Modeles/complements/resultats/lgb_L1_tous.txt
Modeles/complements/resultats/lgb_L2_payes.txt
Modeles/complements/resultats/lgb_L2_tous.txt
Modeles/complements/resultats/lgb_L3_payes.txt
Modeles/complements/resultats/lgb_L3_tous.txt
Modeles/complements/resultats/lgb_L4_payes.txt
Modeles/complements/resultats/lgb_L4_tous.txt
Modeles/complements/resultats/lgb_L5_payes.txt
Modeles/complements/resultats/lgb_L5_tous.txt
Modeles/complements/resultats/lgb_L6_payes.txt
Modeles/complements/resultats/lgb_L6_tous.txt
Modeles/complements/resultats/lgb_M4_payes.txt
Modeles/complements/resultats/lgb_M4_tous.txt
Modeles/complements/resultats/vc1_courbe_validation_payes.csv
Modeles/complements/resultats/vc1_courbe_validation_tous.csv
Modeles/complements/resultats/vc1_synthese.csv
Modeles/complements/resultats/vc2_binomial_negatif.csv
Modeles/complements/resultats/vc3_codes_bruts_ratedFloodZone_par_annee.csv
Modeles/complements/resultats/vc3_multiplicateur_zone.csv
Modeles/complements/resultats/vc3_systeme_tarification.csv
Modeles/complements/resultats/vc3_zone_annee.csv
Modeles/complements/resultats/vc4_lignes_exclues.csv
Modeles/complements/resultats/vc4_liste_13_lignes.csv
Modeles/complements/run_all.sh
Modeles/complements/scripts/c1_verifications.py
Modeles/complements/scripts/c2_ablation_modeles.py
Modeles/complements/scripts/c3_ablation_evaluation.py
Modeles/complements/scripts/c4_descriptif_couverture_hp.py
Modeles/complements/scripts/ccommun.py
Modeles/environnement.txt
Modeles/figures/calibration_zone_test_payes.png
Modeles/figures/calibration_zone_test_tous.png
Modeles/figures/gain_deviance_par_annee_payes.png
Modeles/figures/gain_deviance_par_annee_tous.png
Modeles/figures/predit_observe_par_annee_payes.png
Modeles/figures/predit_observe_par_annee_tous.png
Modeles/logs/00_environnement.log
Modeles/logs/01_verifications.log
Modeles/logs/02_modeles.log
Modeles/logs/03_evaluation.log
Modeles/logs/durees.log
Modeles/resultats/ajustement_payes.json
Modeles/resultats/ajustement_tous.json
Modeles/resultats/bootstrap_annees_test.csv
Modeles/resultats/calibration_par_zone_test.csv
Modeles/resultats/calibration_totale_par_periode.csv
Modeles/resultats/coefficients_payes.csv
Modeles/resultats/coefficients_tous.csv
Modeles/resultats/deviance_par_annee_test_matrice_payes.csv
Modeles/resultats/deviance_par_annee_test_matrice_tous.csv
Modeles/resultats/deviance_par_modele.csv
Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv
Modeles/resultats/importance_gain_payes.csv
Modeles/resultats/importance_gain_tous.csv
Modeles/resultats/importance_permutation_test_m4.csv
Modeles/resultats/lgb_grille_payes.csv
Modeles/resultats/lgb_grille_tous.csv
Modeles/resultats/m4_payes.txt
Modeles/resultats/m4_tous.txt
Modeles/resultats/par_annee_calibration_deviance.csv
Modeles/resultats/predictions_payes.csv
Modeles/resultats/predictions_tous.csv
Modeles/resultats/preparation.json
Modeles/run_all.sh
Modeles/scripts/01_verifications.py
Modeles/scripts/02_modeles.py
Modeles/scripts/03_evaluation.py
Modeles/scripts/commun.py
```

### plan_commit_analyse_preliminaire.txt (51 fichiers, listes comprises)
```
Analyse_preliminaire/INCOHERENCES_DOCUMENTAIRES.md
Analyse_preliminaire/NOTE_ENSEIGNANT.md
Analyse_preliminaire/PASSAGES_A_COMPLETER.md
Analyse_preliminaire/PLAN_COMMIT.md
Analyse_preliminaire/README.md
Analyse_preliminaire/STATUT_RESULTATS.md
Analyse_preliminaire/TRACABILITE.md
Analyse_preliminaire/figures/SOURCES.md
Analyse_preliminaire/figures/fig_ap_ablation.png
Analyse_preliminaire/figures/fig_ap_calibration.png
Analyse_preliminaire/figures/fig_ap_gains.png
Analyse_preliminaire/figures/fig_ap_zone_rates.png
Analyse_preliminaire/logs/extraire.log
Analyse_preliminaire/logs/verification_chiffres.log
Analyse_preliminaire/plan_commit_analyse_preliminaire.txt
Analyse_preliminaire/plan_commit_modeles.txt
Analyse_preliminaire/rendu_test.qmd
Analyse_preliminaire/run_all.sh
Analyse_preliminaire/scripts/extraire.py
Analyse_preliminaire/scripts/registre.py
Analyse_preliminaire/scripts/verifier_chiffres.py
Analyse_preliminaire/section_modelisation.qmd
Analyse_preliminaire/tableaux/chiffres_cles.json
Analyse_preliminaire/tableaux/tab_ap_ablation_all.csv
Analyse_preliminaire/tableaux/tab_ap_ablation_all.md
Analyse_preliminaire/tableaux/tab_ap_ablation_paid.csv
Analyse_preliminaire/tableaux/tab_ap_ablation_paid.md
Analyse_preliminaire/tableaux/tab_ap_annexe_ablation_complete.csv
Analyse_preliminaire/tableaux/tab_ap_annexe_ablation_complete.md
Analyse_preliminaire/tableaux/tab_ap_annexe_calibration.csv
Analyse_preliminaire/tableaux/tab_ap_annexe_calibration.md
Analyse_preliminaire/tableaux/tab_ap_annexe_coefficients_glm.csv
Analyse_preliminaire/tableaux/tab_ap_annexe_coefficients_glm.md
Analyse_preliminaire/tableaux/tab_ap_annexe_diff_annee.csv
Analyse_preliminaire/tableaux/tab_ap_annexe_diff_annee.md
Analyse_preliminaire/tableaux/tab_ap_annexe_verifications.csv
Analyse_preliminaire/tableaux/tab_ap_annexe_verifications.md
Analyse_preliminaire/tableaux/tab_ap_anomalies.csv
Analyse_preliminaire/tableaux/tab_ap_anomalies.md
Analyse_preliminaire/tableaux/tab_ap_calibration.csv
Analyse_preliminaire/tableaux/tab_ap_calibration.md
Analyse_preliminaire/tableaux/tab_ap_coefficients.csv
Analyse_preliminaire/tableaux/tab_ap_coefficients.md
Analyse_preliminaire/tableaux/tab_ap_gains.csv
Analyse_preliminaire/tableaux/tab_ap_gains.md
Analyse_preliminaire/tableaux/tab_ap_importance.csv
Analyse_preliminaire/tableaux/tab_ap_importance.md
Analyse_preliminaire/tableaux/tab_ap_volumes.csv
Analyse_preliminaire/tableaux/tab_ap_volumes.md
Analyse_preliminaire/tableaux/tab_ap_zone_shift.csv
Analyse_preliminaire/tableaux/tab_ap_zone_shift.md
```
