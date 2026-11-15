# Traçabilité des chiffres

> 15/11/2026 · branche `modeles-premier-jet` · version `v0.1` · **Résultats provisoires et exploratoires, voir `STATUT_RESULTATS.md`** · aucun commit à ce stade.

Chaque chiffre de `section_modelisation.qmd` est inséré par du code (`ck("clé")`) qui lit `tableaux/chiffres_cles.json`, lui-même extrait des fichiers ci-dessous par `scripts/extraire.py`. Aucun chiffre n'est écrit à la main dans la section (règle de `CLAUDE.md`). `scripts/verifier_chiffres.py` relit chaque source et compare (tolérance relative 1e-9 sur la valeur, égalité exacte de l'affichage arrondi).

Les chiffres des tableaux de la section sont lus directement dans `tableaux/*.csv` (sources indiquées en tête de chaque `tableaux/*.md`).

| Clé | Affichage | Valeur exacte | Fichier source | Cellule | Résultat | Cité dans la section |
|---|---|---|---|---|---|---|
| `raw_claims` | 787,274 | 787274 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « Fichier brut » | R1 | oui |
| `single_family` | 624,268 | 624268 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « occupancyType ∈ [1, 11] » | R1 | oui |
| `anomalies` | 2,575 | 2575 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « Lignes écartées (anomalies) » | R1 | oui |
| `clean_claims` | 621,693 | 621693 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « **claims_clean.parquet** » | R1 | oui |
| `anom_neg_age` | 1,378 | 1378 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « âge négatif » (après « | motif | lignes | ») | R2 | non (registre seulement) |
| `anom_duplicate` | 888 | 888 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « doublon exact » (après « | motif | lignes | ») | R2 | non (registre seulement) |
| `anom_paid_nocov` | 277 | 277 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « paiement sans couverture » (après « | motif | lignes | ») | R2 | non (registre seulement) |
| `anom_neg_paid` | 34 | 34 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « paiement négatif » (après « | motif | lignes | ») | R2 | non (registre seulement) |
| `anom_two_reasons` | 2 | 2 | `Data_cleaning/clean/cleaning_report.md` | ligne de tableau « âge négatif; paiement sans couverture » (après « Combinaisons de motifs ») | R2 | oui |
| `ds_rows` | 22,485 | 22485 | `EDA/ds_clean_roles.json` | clé `rows` | R3 | oui |
| `ds_counties` | 734 | 734 | `EDA/ds_clean_roles.json` | clé `counties` | R3 | oui |
| `policy_years` | 22.7 million | 22701122.37 | `EDA/figures/eda_key_numbers.json` | clé `policy_years` | R3 | oui |
| `rows_used` | 22,472 | 22472 | `Modeles/resultats/preparation.json` | clé `lignes_gardees` | R3 | non (registre seulement) |
| `rows_excluded` | 13 | 13 | `Modeles/resultats/preparation.json` | clé `variable_manquante` | R3 | oui |
| `rows_train` | 14,999 | 14999 | `Modeles/resultats/ajustement_payes.json` | clé `lignes_train` | R4 | oui |
| `rows_test` | 7,473 | 7473 | `Modeles/resultats/ajustement_payes.json` | clé `lignes_test` | R4 | oui |
| `claims_train_paid` | 88,898 | 88898 | `Modeles/resultats/ajustement_payes.json` | clé `sinistres_train` | R4 | oui |
| `claims_test_paid` | 108,584 | 108584 | `Modeles/resultats/ajustement_payes.json` | clé `sinistres_test` | R4 | oui |
| `claims_train_all` | 123,082 | 123082 | `Modeles/resultats/ajustement_tous.json` | clé `sinistres_train` | R4 | oui |
| `claims_test_all` | 130,316 | 130316 | `Modeles/resultats/ajustement_tous.json` | clé `sinistres_test` | R4 | oui |
| `freq_train` | 5.60 | 5.59683042 | `EDA/figures/eda_key_numbers.json` | clé `freq_train` | R5 | oui |
| `freq_test` | 15.93 | 15.92727075 | `EDA/figures/eda_key_numbers.json` | clé `freq_test` | R5 | oui |
| `share_2024_test` | 50.8% | 0.5077727842 | agrégation | observé 2024 / somme des observés 2020-2024 (payés, modèle M0) dans par_annee_calibration_deviance.csv | R5 | oui |
| `excl13_dev_effect` | 3.8e-07 | 3.791424881e-07 | agrégation | maximum de |ecart_relatif| dans vc4_lignes_exclues.csv | R3 | oui |
| `m2_pearson_disp` | 109.2 | 109.2362626 | `Modeles/resultats/ajustement_payes.json` | clé `M2_dispersion_pearson` | R8 | oui |
| `m2_aic` | 388,487 | 388487.4439 | `Modeles/resultats/ajustement_payes.json` | clé `M2_AIC_train` | R8 | non (registre seulement) |
| `m3_aic` | 36,690 | 36689.84682 | `Modeles/resultats/ajustement_payes.json` | clé `M3_AIC_train` | R8 | non (registre seulement) |
| `m3_alpha` | 6.13 | 6.126863402 | `Modeles/resultats/ajustement_payes.json` | clé `M3_alpha` | R8 | non (registre seulement) |
| `m3_train_ratio` | 1.94 | 1.943603777 | `Modeles/resultats/calibration_totale_par_periode.csv` | ligne (cible = payes, period = train, modele = M3), colonne `ratio_predit_observe` | R9 | oui |
| `nb_const_ratio` | 2.64 | 2.636632387 | `Modeles/complements/resultats/vc2_binomial_negatif.csv` | ligne (cible = payes), colonne `ratio_somme_mu_somme_y_constante_seule` | R9 | oui |
| `vc2_coef_diff` | 1.4e-06 | 1.446498598e-06 | `Modeles/complements/resultats/vc2_binomial_negatif.csv` | ligne (cible = payes), colonne `ecart_max_coef_GLM_vs_M3` | R6 | oui |
| `vc1_metric_diff` | 5.9e-14 | 5.86197757e-14 | `Modeles/complements/resultats/vc1_synthese.csv` | ligne (cible = payes), colonne `ecart_max_metrique_lgb_vs_main` | R6 | oui |
| `m4_iters` | 122 | 122 | `Modeles/resultats/ajustement_payes.json` | clé `M4_iterations` | R7 | non (registre seulement) |
| `m4_nonreg` | 1.0013 | 1.001300799 | `Modeles/resultats/ajustement_payes.json` | clé `M4_nonregression_ratio_train` | R6, R7 | oui |
| `se_ratio_vzone` | 13 | 12.62392171 | agrégation | es_robuste_HC0 / es_modele de zone_V* (M2, payés) dans coefficients_payes.csv | R8 | oui |
| `boot_distinct` | 118 | 118 | `Modeles/resultats/bootstrap_annees_test.csv` | ligne (cible = payes, difference = M4 - M2), colonne `nb_tirages_distincts` | R23 | oui |
| `gain_test_M1_payes` | +7.1% | 0.07094932873 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = payes, modele = M1, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | oui |
| `gain_test_M1_tous` | +6.9% | 0.06903849625 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = tous, modele = M1, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | non (registre seulement) |
| `gain_test_M2_payes` | -3.4% | -0.03397678017 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = payes, modele = M2, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | oui |
| `gain_test_M2_tous` | -1.9% | -0.01904116498 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = tous, modele = M2, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | non (registre seulement) |
| `gain_test_M3_payes` | +13.7% | 0.1374645466 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = payes, modele = M3, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | oui |
| `gain_test_M3_tous` | +13.0% | 0.1303178179 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = tous, modele = M3, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | non (registre seulement) |
| `gain_test_M4_payes` | +15.9% | 0.1586846503 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = payes, modele = M4, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | oui |
| `gain_test_M4_tous` | +17.6% | 0.1755906938 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = tous, modele = M4, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | non (registre seulement) |
| `gain_test_M_oracle_payes` | +43.1% | 0.4312185851 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = payes, modele = M_oracle, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | oui |
| `gain_test_M_oracle_tous` | +41.0% | 0.4103916801 | `Modeles/resultats/deviance_par_modele.csv` | ligne (cible = tous, modele = M_oracle, ensemble = test 2020-2024), colonne `gain_relatif_vs_M0` | R10 | non (registre seulement) |
| `gain_recal_M1_payes` | +10.6% | 0.1060559204 | `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | ligne (cible = payes, modele = M1), colonne `gain_vs_M0_recalee` | R11 | oui |
| `gain_recal_M1_tous` | +10.0% | 0.1002135615 | `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | ligne (cible = tous, modele = M1), colonne `gain_vs_M0_recalee` | R11 | non (registre seulement) |
| `gain_recal_M2_payes` | -0.5% | -0.004609890229 | `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | ligne (cible = payes, modele = M2), colonne `gain_vs_M0_recalee` | R11 | oui |
| `gain_recal_M2_tous` | +0.6% | 0.006210851504 | `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | ligne (cible = tous, modele = M2), colonne `gain_vs_M0_recalee` | R11 | non (registre seulement) |
| `gain_recal_M3_payes` | +3.1% | 0.03135469213 | `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | ligne (cible = payes, modele = M3), colonne `gain_vs_M0_recalee` | R11 | oui |
| `gain_recal_M3_tous` | +3.5% | 0.03452272784 | `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | ligne (cible = tous, modele = M3), colonne `gain_vs_M0_recalee` | R11 | non (registre seulement) |
| `gain_recal_M4_payes` | +11.7% | 0.1169540545 | `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | ligne (cible = payes, modele = M4), colonne `gain_vs_M0_recalee` | R11 | oui |
| `gain_recal_M4_tous` | +12.5% | 0.1247703457 | `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | ligne (cible = tous, modele = M4), colonne `gain_vs_M0_recalee` | R11 | non (registre seulement) |
| `zone_share_m4` | 91% | 0.9068169619 | agrégation | gain recalé de M1 / gain recalé de M4 (payés), diagnostic_deviance_recalee_par_annee.csv | R11 | oui |
| `zone_share_l2` | 64% | 0.6449414694 | agrégation | gain recalé de M1 / gain recalé de L2 (payés), ablation_deviance.csv (test_recale) | R11 | non (registre seulement) |
| `ratio_test_M0` | 0.35 | 0.3513986504 | `Modeles/resultats/calibration_totale_par_periode.csv` | ligne (cible = payes, period = test, modele = M0), colonne `ratio_predit_observe` | R12 | non (registre seulement) |
| `ratio_test_M2` | 0.32 | 0.3189907156 | `Modeles/resultats/calibration_totale_par_periode.csv` | ligne (cible = payes, period = test, modele = M2), colonne `ratio_predit_observe` | R12 | oui |
| `ratio_test_M3` | 0.63 | 0.6289943707 | `Modeles/resultats/calibration_totale_par_periode.csv` | ligne (cible = payes, period = test, modele = M3), colonne `ratio_predit_observe` | R12 | oui |
| `ratio_test_M4` | 0.44 | 0.4412246056 | `Modeles/resultats/calibration_totale_par_periode.csv` | ligne (cible = payes, period = test, modele = M4), colonne `ratio_predit_observe` | R12 | non (registre seulement) |
| `ratio_2021_M4` | 2.71 | 2.710402166 | `Modeles/resultats/par_annee_calibration_deviance.csv` | ligne (cible = payes, modele = M4, annee = 2021), colonne `ratio_predit_observe` | R12 | oui |
| `ratio_2022_M4` | 0.30 | 0.300935259 | `Modeles/resultats/par_annee_calibration_deviance.csv` | ligne (cible = payes, modele = M4, annee = 2022), colonne `ratio_predit_observe` | R12 | oui |
| `ratio_2024_M4` | 0.19 | 0.1928542544 | `Modeles/resultats/par_annee_calibration_deviance.csv` | ligne (cible = payes, modele = M4, annee = 2024), colonne `ratio_predit_observe` | R12 | oui |
| `abl_G1_raw` | +0.2% | 0.001539113477 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = G1, ensemble = test), colonne `gain_vs_M0` | R14 | non (registre seulement) |
| `abl_G1_rec` | -1.0% | -0.009817028892 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = G1, ensemble = test_recale), colonne `gain_vs_M0` | R14 | oui |
| `abl_G3_raw` | -3.2% | -0.03191357503 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = G3, ensemble = test), colonne `gain_vs_M0` | R14 | non (registre seulement) |
| `abl_G3_rec` | +7.9% | 0.07894252885 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = G3, ensemble = test_recale), colonne `gain_vs_M0` | R14 | non (registre seulement) |
| `abl_G5_hp_raw` | +0.1% | 0.0007615243613 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = G5_hp, ensemble = test), colonne `gain_vs_M0` | R13 | oui |
| `abl_G5_hp_rec` | +6.9% | 0.06890274798 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = G5_hp, ensemble = test_recale), colonne `gain_vs_M0` | R13 | oui |
| `abl_L1_raw` | -5.4% | -0.05399942545 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L1, ensemble = test), colonne `gain_vs_M0` | R13 | oui |
| `abl_L1_rec` | -9.0% | -0.0895399317 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L1, ensemble = test_recale), colonne `gain_vs_M0` | R13 | oui |
| `abl_L2_raw` | +21.8% | 0.2179875379 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L2, ensemble = test), colonne `gain_vs_M0` | R13 | oui |
| `abl_L2_rec` | +16.4% | 0.1644427059 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L2, ensemble = test_recale), colonne `gain_vs_M0` | R13 | oui |
| `abl_L3_raw` | +15.6% | 0.1563184969 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L3, ensemble = test), colonne `gain_vs_M0` | R13 | oui |
| `abl_L3_rec` | +13.7% | 0.1372560248 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L3, ensemble = test_recale), colonne `gain_vs_M0` | R13 | oui |
| `abl_L5_raw` | +5.3% | 0.05331907053 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L5, ensemble = test), colonne `gain_vs_M0` | R13 | oui |
| `abl_L5_rec` | +8.0% | 0.07952243314 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L5, ensemble = test_recale), colonne `gain_vs_M0` | R13 | oui |
| `abl_L6_raw` | -8.7% | -0.08696655602 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L6, ensemble = test), colonne `gain_vs_M0` | R13 | oui |
| `abl_L6_rec` | -12.8% | -0.1283734081 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L6, ensemble = test_recale), colonne `gain_vs_M0` | R13 | non (registre seulement) |
| `abl_L5_train` | +2.2% | 0.02221449954 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = L5, ensemble = train), colonne `gain_vs_M0` | R13 | oui |
| `abl_M1_train` | +2.4% | 0.02446967907 | `Modeles/complements/resultats/ablation_deviance.csv` | ligne (cible = payes, modele = M1, ensemble = train), colonne `gain_vs_M0` | R13 | oui |
| `mult_A` | x3.72 | 3.723410457 | `Modeles/complements/resultats/vc3_multiplicateur_zone.csv` | ligne (zone = A*), colonne `multiplicateur_payes` | R16 | oui |
| `mult_V` | x2.92 | 2.921527355 | `Modeles/complements/resultats/vc3_multiplicateur_zone.csv` | ligne (zone = V*), colonne `multiplicateur_payes` | R16 | oui |
| `mult_X` | x0.87 | 0.8685525105 | `Modeles/complements/resultats/vc3_multiplicateur_zone.csv` | ligne (zone = X), colonne `multiplicateur_payes` | R16 | oui |
| `x_claims_share_2021` | 34.9% | 0.3488862131 | `Modeles/complements/resultats/vc3_zone_annee.csv` | ligne (year = 2021, zone = X), colonne `part_payes` | R16 | oui |
| `x_claims_share_2022` | 6.9% | 0.06854164618 | `Modeles/complements/resultats/vc3_zone_annee.csv` | ligne (year = 2022, zone = X), colonne `part_payes` | R16 | oui |
| `x_expo_share_min` | 40.2% | 0.4015611265 | agrégation | minimum de part_exposition de la zone X sur 2018-2024 dans vc3_zone_annee.csv | R16 | oui |
| `x_expo_share_max` | 46.4% | 0.4644664089 | agrégation | maximum de part_exposition de la zone X sur 2018-2024 dans vc3_zone_annee.csv | R16 | oui |
| `t5_expo_train` | 81.0% | 0.8101731358 | `Modeles/complements/resultats/hp_taux_par_tranche_couverture.csv` | ligne (cible = payes, period = train, tranche = T5), colonne `part_exposition_periode` | R17 | oui |
| `t5_expo_test` | 92.9% | 0.9294110483 | `Modeles/complements/resultats/hp_taux_par_tranche_couverture.csv` | ligne (cible = payes, period = test, tranche = T5), colonne `part_exposition_periode` | R17 | oui |
| `t5_rate_train` | 4.33 | 4.334617992 | `Modeles/complements/resultats/hp_taux_par_tranche_couverture.csv` | ligne (cible = payes, period = train, tranche = T5), colonne `taux_observe_1000` | R17 | oui |
| `t5_rate_test` | 16.29 | 16.28836701 | `Modeles/complements/resultats/hp_taux_par_tranche_couverture.csv` | ligne (cible = payes, period = test, tranche = T5), colonne `taux_observe_1000` | R17 | oui |
| `t5_rows_test` | 43.7% | 0.437 | `Modeles/complements/resultats/ablation_variables_construites.json` | clé `repartition_tranches` → `test` → `T5` | R17 | non (registre seulement) |
| `perm_zone` | +78,523 | 78522.81402 | `Modeles/resultats/importance_permutation_test_m4.csv` | ligne (cible = payes, variable = zone), colonne `hausse_deviance_test_moyenne` | R15 | oui |
| `perm_cov` | +65,558 | 65557.99642 | `Modeles/resultats/importance_permutation_test_m4.csv` | ligne (cible = payes, variable = mean_coverage), colonne `hausse_deviance_test_moyenne` | R15 | oui |
| `perm_chist` | -13,784 | -13783.51887 | `Modeles/resultats/importance_permutation_test_m4.csv` | ligne (cible = payes, variable = county_hist_per_1000), colonne `hausse_deviance_test_moyenne` | R14 | oui |
| `gain_share_chist` | 49% | 0.4882611051 | `Modeles/resultats/importance_gain_payes.csv` | ligne (variable = county_hist_per_1000), colonne `part_gain` | R14 | oui |

## Chiffres retirés faute de source

- Couverture moyenne pondérée de 203,6 k$ (entraînement) et 222,0 k$ (test), et facteur 0,904 sur les prédictions de M2, cités au § 7.3 de `Modeles/RAPPORT_MODELES.md` : calculés en exploration, absents de tout CSV ou JSON. Remplacés par les parts d'exposition de la tranche de couverture la plus haute (`hp_taux_par_tranche_couverture.csv`).

