# Modeles/complements/ : vérifications VC1 à VC4 et ablation des variables

**Statut : exécuté, sans arrêt.**
- VC1 (offset dans la validation de LightGBM) : CONFORME.
- VC2 (contrôle croisé du binomial négatif) : CONFORME.
- VC3 (zone × temps) : ÉCART, voir le rapport.
- VC4 (13 lignes exclues) : CONFORME.
- Table d'ablation : produite.

Branche locale `modeles-premier-jet`. **Rien n'est commité ni poussé.** Aucun fichier existant n'est
modifié : tout est écrit ici.

## Reproduire

Depuis la racine du dépôt, après `Modeles/run_all.sh`, qui crée `Modeles/.venv` :

```bash
bash Modeles/complements/run_all.sh
```

- Le script réutilise `Modeles/.venv` et le contournement `libomp` du premier jet. Il s'arrête si le venv
  est absent.
- Il ne réécrit jamais `Modeles/resultats/`.
- **Durée mesurée** (Apple M3) : environ 15 s. Le détail par étape est dans `logs/durees.log`.
- Graine : 42 ; versions : `logs/00_environnement.log`.
- VC3 lit le fichier brut local `Data_cleaning/NfipClaimsV3_SE.parquet`, pour des agrégats seulement.
  S'il est absent, cette partie est déclarée non calculable.

## Contenu

| Élément | Rôle |
|---|---|
| `PROTOCOLE_COMPLEMENTAIRE.md` | Hypothèses H-d à H-g, seuils, modèles et métriques, pré-enregistrés (15/11/2026, 17:52) |
| `VERIFICATIONS_COMPLEMENTAIRES.md` | VC1 à VC4 : commande, sortie, statut, conclusion |
| `RAPPORT_COMPLEMENTS.md` | Résultats, verdicts sur les hypothèses, réponses (a) à (c), écarts avec `RAPPORT_MODELES.md` |
| `ENTREES.txt` | SHA-256 des fichiers lus |
| `run_all.sh` | Exécution complète |
| `scripts/ccommun.py` | Outils partagés (importe `Modeles/scripts/commun.py` sans le modifier) |
| `scripts/c1_verifications.py` | VC1 à VC4 |
| `scripts/c2_ablation_modeles.py` | Ajustement de M0, M1, M2, M4, G1 à G4, `G5_hp` (hors protocole) et L1 à L6, pour les deux cibles |
| `scripts/c3_ablation_evaluation.py` | Déviances, recalage, calibration, différences annuelles, importances, figures |
| `scripts/c4_descriptif_couverture_hp.py` | Hors protocole : taux observés et prédits par tranche de couverture |
| `resultats/` | `ablation_deviance.csv`, `ablation_calibration_annee.csv`, `ablation_diff_par_annee.csv`, `ablation_importance_lgb.csv`, `ablation_coefficients_glm.csv`, prédictions, modèles LightGBM, fichiers `vc*` et `hp_*` |
| `figures/` | `ablation_gain_brut.png`, `ablation_gain_recale.png`, `vc3_taux_zone_annee.png` |
| `logs/` | Sorties des scripts, environnement, durées |

## En bref (sinistres payés, gain de déviance de test par rapport au modèle nul)

| | Brut | Après recalage annuel* |
|---|---:|---:|
| M1, GLM zone | +7,1 % | +10,6 % |
| M2, GLM complet | −3,4 % | −0,5 % |
| M4, LightGBM complet | +15,9 % | +11,7 % |
| L1, LightGBM sans couverture | −5,4 % | −9,0 % |
| L2, LightGBM sans historique du comté | **+21,8 %** | **+16,4 %** |
| L3, LightGBM zone + couverture | +15,6 % | +13,7 % |

\* Diagnostic qui utilise les totaux observés de chaque année de test.
