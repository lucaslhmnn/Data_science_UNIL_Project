<!-- tab_ap_ablation_all | Ablation, all claims: gain relative to M0 (%) and predicted / observed | sources : Modeles/complements/resultats/ablation_deviance.csv, Modeles/complements/resultats/ablation_calibration_annee.csv | statut : [Provisoire, exploratoire] | v0.1, 15/11/2026 ; résultats provisoires et exploratoires, voir STATUT_RESULTATS.md -->
**Ablation, all claims: gain relative to M0 (%) and predicted / observed** [Provisoire, exploratoire]

Sources : `Modeles/complements/resultats/ablation_deviance.csv`, `Modeles/complements/resultats/ablation_calibration_annee.csv`

| Model | Features | Test | Test excl. 2024 | Rescaled | Pred./obs. |
|---|---|---|---|---|---|
| M1 | GLM: zone | 6.9 | 7.01 | 10.02 | 0.4 |
| M2 | GLM: zone + coverage + histories | -1.9 | -1.32 | 0.62 | 0.38 |
| G1 | GLM: zone + histories | 0.85 | -0.14 | 0.21 | 0.41 |
| G3 | GLM: zone + coverage | -1.87 | 1.61 | 7.94 | 0.33 |
| G5_hp | GLM: zone + coverage bands (outside protocol) | 1.13 | 3.03 | 7.07 | 0.36 |
| M4 | LightGBM: zone + coverage + histories | 17.56 | 14.66 | 12.48 | 0.52 |
| L1 | LightGBM: zone + histories | -4.03 | -3.9 | -6.64 | 0.42 |
| L2 | LightGBM: zone + coverage + cell history | 19.71 | 15.74 | 14.72 | 0.54 |
| L3 | LightGBM: zone + coverage | 14.61 | 11.38 | 13.08 | 0.48 |
| L5 | LightGBM: zone | 5.05 | 5.19 | 7.31 | 0.4 |
| L6 | LightGBM: zone + coverage rank in year + histories | -6.97 | -4.24 | -10.03 | 0.41 |
