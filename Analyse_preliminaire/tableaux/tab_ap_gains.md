<!-- tab_ap_gains | Gain in test Poisson deviance relative to M0 (%) | sources : Modeles/resultats/deviance_par_modele.csv, Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv | statut : [Provisoire, exploratoire] | v0.1, 15/11/2026 ; résultats provisoires et exploratoires, voir STATUT_RESULTATS.md -->
**Gain in test Poisson deviance relative to M0 (%)** [Provisoire, exploratoire]

Sources : `Modeles/resultats/deviance_par_modele.csv`, `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv`

| Model | Paid: test | Paid: test excl. 2024 | Paid: rescaled | All: test | All: test excl. 2024 | All: rescaled |
|---|---|---|---|---|---|---|
| M1 GLM, zone | 7.09 | 7.29 | 10.61 | 6.9 | 7.01 | 10.02 |
| M2 Poisson GLM | -3.4 | -2.65 | -0.46 | -1.9 | -1.32 | 0.62 |
| M3 negative binomial GLM | 13.75 | 7.53 | 3.14 | 13.03 | 6.42 | 3.45 |
| M4 LightGBM | 15.87 | 13.98 | 11.7 | 17.56 | 14.66 | 12.48 |
| M_oracle (not predictive) | 43.12 | 29.11 | 16.87 | 41.04 | 28.31 | 16.06 |
