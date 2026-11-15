<!-- tab_ap_importance | M4 feature importance (paid claims) | sources : Modeles/resultats/importance_permutation_test_m4.csv, Modeles/resultats/importance_gain_payes.csv | statut : [Provisoire, exploratoire] | v0.1, 15/11/2026 ; résultats provisoires et exploratoires, voir STATUT_RESULTATS.md -->
**M4 feature importance (paid claims)** [Provisoire, exploratoire]

Sources : `Modeles/resultats/importance_permutation_test_m4.csv`, `Modeles/resultats/importance_gain_payes.csv`

| Feature | Share of training gain (%) | Test deviance increase when permuted | Std. dev. (20 permutations) |
|---|---|---|---|
| zone | 11.2 | 78523 | 23647 |
| mean_coverage | 22.2 | 65558 | 27114 |
| hist_per_1000 | 17.8 | 15627 | 13287 |
| county_hist_per_1000 | 48.8 | -13784 | 12549 |
