# Sources des figures

> v0.1, 15/11/2026. Branche `modeles-premier-jet`. Aucun commit à ce stade. Figures régénérées par `Analyse_preliminaire/scripts/extraire.py` à partir des CSV existants, jamais à partir des modèles. Titres en anglais, conformément à `CLAUDE.md` (English only). Résultats provisoires et exploratoires, voir `STATUT_RESULTATS.md`.

| Figure | CSV d'origine | Script |
|---|---|---|
| `figures/fig_ap_zone_rates.png` | `Modeles/complements/resultats/vc3_zone_annee.csv` | `scripts/extraire.py` (fonction `build_figures`) |
| `figures/fig_ap_gains.png` | `Modeles/resultats/deviance_par_modele.csv`, `Modeles/resultats/diagnostic_deviance_recalee_par_annee.csv` | `scripts/extraire.py` (fonction `build_figures`) |
| `figures/fig_ap_calibration.png` | `Modeles/resultats/par_annee_calibration_deviance.csv` | `scripts/extraire.py` (fonction `build_figures`) |
| `figures/fig_ap_ablation.png` | `Modeles/complements/resultats/ablation_deviance.csv` | `scripts/extraire.py` (fonction `build_figures`) |
