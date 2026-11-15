<!-- tab_ap_calibration | Predicted / observed paid claims by test year | sources : Modeles/resultats/par_annee_calibration_deviance.csv, Modeles/resultats/calibration_totale_par_periode.csv | statut : [Provisoire, exploratoire] | v0.1, 15/11/2026 ; résultats provisoires et exploratoires, voir STATUT_RESULTATS.md -->
**Predicted / observed paid claims by test year** [Provisoire, exploratoire]

Sources : `Modeles/resultats/par_annee_calibration_deviance.csv`, `Modeles/resultats/calibration_totale_par_periode.csv`

| Model | 2020 | 2021 | 2022 | 2023 | 2024 | 2020-2024 |
|---|---|---|---|---|---|---|
| M0 null | 0.68 | 2.42 | 0.25 | 0.94 | 0.13 | 0.35 |
| M1 GLM, zone | 0.66 | 2.34 | 0.24 | 0.93 | 0.13 | 0.34 |
| M2 Poisson GLM | 0.64 | 2.22 | 0.23 | 0.83 | 0.11 | 0.32 |
| M3 negative binomial GLM | 1.25 | 4.39 | 0.45 | 1.64 | 0.23 | 0.63 |
| M4 LightGBM | 0.72 | 2.71 | 0.3 | 1.37 | 0.19 | 0.44 |
