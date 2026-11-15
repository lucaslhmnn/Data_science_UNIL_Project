# Modeles/ : premier jet des modèles de fréquence

**Statut : modèles exécutés (aucun blocage).** Branche locale `modeles-premier-jet`, créée depuis `main`
(`69d0d21`). **Rien n'est commité ni poussé.**

## Objectif

Comparer, sur la table agrégée `EDA/ds_clean.csv` (comté × zone d'inondation × année, 2010–2024), un
GLM de Poisson, un GLM binomial négatif et un LightGBM Poisson, avec l'exposition en offset.
Entraînement 2010–2019, test 2020–2024. C'est un premier jet exploratoire, pas le modèle final du projet
(qui vise le secteur × année).

## Reproduire

Depuis la racine du dépôt :

```bash
bash Modeles/run_all.sh
```

Le script :
1. crée `Modeles/.venv` depuis `environnement.txt` s'il n'existe pas ;
2. calcule les sommes de contrôle des entrées (`ENTREES.txt`) ;
3. lance les vérifications, puis les modèles, puis l'évaluation, et s'arrête avec le code 2 si un
   contrôle bloquant échoue.

**Durée mesurée** (Apple M3, environnement déjà créé) : environ 8 s au total. Le détail par étape est
dans `logs/durees.log`. Deux exécutions successives donnent des résultats identiques octet pour octet,
à l'exception du champ `duree_s` des fichiers `ajustement_*.json`.

**Environnement** : Python 3.13.0, pandas 3.1.1, numpy 2.5.4, scipy 1.18.1, statsmodels 0.15.0,
lightgbm 4.7.0, matplotlib 3.11.2, pyarrow 26.0.1 et scikit-learn 1.9.1 (liste complète dans
`environnement.txt`). Sur macOS sans Homebrew, LightGBM utilise la copie de `libomp` fournie par
scikit-learn : `run_all.sh` positionne `DYLD_FALLBACK_LIBRARY_PATH` (voir `VERIFICATIONS.md`, V5).
Solution standard : `brew install libomp`.

Graine : `SEED = 42` partout. `requirements.txt` à la racine n'est ni utilisé ni modifié : il n'est pas
installable tel quel.

## Contenu

| Élément | Rôle |
|---|---|
| `PROTOCOLE.md` | Hypothèses et plan pré-enregistrés (15/11/2026, 17:34), et avenant n° 1 (17:39) |
| `VERIFICATIONS.md` | Contrôles V1 à V8 : commande, sortie, statut (régénéré à chaque exécution) |
| `RAPPORT_MODELES.md` | Résultats, lecture par rapport aux hypothèses, limites, suites proposées |
| `ENTREES.txt` | SHA-256 des fichiers d'entrée lus |
| `environnement.txt` | `pip freeze` de `Modeles/.venv` |
| `run_all.sh` | Exécution complète |
| `scripts/commun.py` | Chemins, graine, déviance, préparation des lignes, matrices des modèles |
| `scripts/01_verifications.py` | Phase 1 ; écrit `VERIFICATIONS.md`, et `BLOCAGE.md` en cas de blocage |
| `scripts/02_modeles.py` | Phase 2 : M0, M1, M_oracle, M2, M3, M4, pour les cibles « payés » et « tous » |
| `scripts/03_evaluation.py` | Phase 3 : déviances, calibration, bootstrap, importances, figures |
| `resultats/` | Prédictions par ligne, déviances, calibration, bootstrap, coefficients, grille et modèles LightGBM (`m4_*.txt`), diagnostic recalé |
| `figures/` | Prédit contre observé par année, calibration par zone, gain de déviance par année (pour chaque cible) |
| `logs/` | Sortie de chaque script, environnement, durées |

`construire_cible_tous.py` n'existe pas : la colonne `n_all` (tous les sinistres) était déjà présente
dans `ds_clean` (V4).

## Principaux résultats

Détail et réserves dans `RAPPORT_MODELES.md`.

- **Déviance de test, gain par rapport au modèle nul (payés)** : M1 (zone) +7,1 %, M2 (Poisson complet)
  −3,4 %, M3 (binomial négatif) +13,7 %, M4 (LightGBM) +15,9 %.
- **Sous-prédiction** : tous les modèles sous-prédisent le niveau du test. Ratio prédit / observé de
  0,32 (M2) à 0,63 (M3).
- **Le gain brut de M3 est en grande partie un artefact de niveau** : M3 prédit 1,94 fois le total
  d'entraînement.
- **Une fois le niveau retiré** (diagnostic non pré-enregistré), M4 (+11,7 %) dépasse à peine le GLM
  « zone seule » (+10,6 %).
