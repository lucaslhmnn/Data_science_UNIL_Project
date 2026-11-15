# Modeles/ : premier jet des modèles de fréquence

**Statut : modèles exécutés (aucun blocage).** Premier jet fait sur la branche `modeles-premier-jet`,
fusionnée dans `main` le 15/11/2026, puis complétée par la phase 4 (fin de ce fichier).

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
| `scripts/04_evaluation_glissante.py` | Phase 4 (ajoutée après le premier jet, non pré-enregistrée) : évaluation à origine glissante 2016–2024, voir ci-dessous |
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

## Phase 4 : évaluation à origine glissante (ajout du 15/11/2026, Lucas J.)

Analyse complémentaire, **non pré-enregistrée**, ajoutée après lecture du premier jet. Les scripts 01 à 03
et leurs résultats ne sont pas modifiés. `scripts/04_evaluation_glissante.py` reprend les modèles M0 à M4
à l'identique (formules, grille, offset de l'avenant n° 1) et change quatre choses :

1. **Évaluation** : ajuster sur 2010..t−1 et prédire t, pour t = 2016 à 2024. 2016–2019 sert de
   validation, 2020–2024 reste le test. La grille LightGBM est réglée à chaque origine sur les deux
   dernières années d'entraînement.
2. **Variables** : le jeu principal (A) remplace la couverture nominale par `coverage_real` (nouvelle
   colonne de `ds_clean`, dollars constants de 2024). Jeux de sensibilité : P (premier jet), B (sans
   historique du comté), C (sans couverture), D (avec historique récent de la cellule).
3. **Mesures** : gain de déviance brut et recalé par année, Gini, prédit sur observé, intervalles à 95 %
   par rééchantillonnage des comtés, et détail Floride contre les sept autres États.
4. **Sensibilité** : même évaluation sur les sinistres payés hors des dix plus grands événements, sur
   tous les sinistres, et avec LightGBM aux réglages fixes du premier jet (`M4_fixe`).
5. **Calibration par décile** (`glissant_calibration_deciles.csv`).

Sorties : `resultats/glissant_*.csv`, `figures/glissant_gain.png`, `logs/04_evaluation_glissante.log`.
Le rapport Quarto lit ces fichiers. Durée : environ 4 minutes.

Résultat principal (cible « payés », jeu A, gain recalé par rapport à M0) : sur le test, M1 (zone seule)
+12,6 %, M2 +4,4 %, M3 +3,6 %, M4 −8,6 % ; l'écart M4 − M1 a un intervalle à 95 % qui exclut zéro.
Avec les réglages fixes du premier jet, M4 fait +0,4 % : toujours derrière M1, mais l'écart n'est plus
significatif. Lecture prudente : LightGBM n'est pas meilleur, et probablement moins bon.
Le gain de M4 dans le premier jet (+15,9 %) ne résiste pas : le nombre d'arbres retenu varie de 1 à 272
selon l'origine. Hors grands événements, les totaux prédits sont proches des observés et M2 gagne
+8,9 % sur le test.

Réserve : cette phase a été conçue après avoir vu les résultats du premier jet sur 2020–2024. Le test
n'est donc plus vierge et ces résultats sont exploratoires (le rapport le dit).

Contrôles : le script reproduit d'abord le premier jet (`glissant_reproduction_premier_jet.csv`, mêmes
gains à trois décimales). `ds_clean.csv` a gagné la colonne `coverage_real` ; ses 18 autres colonnes sont
identiques, et une réexécution de 01 à 03 redonne les résultats commités à 1e-12 près (les fichiers
commités du premier jet ont donc été laissés tels quels, `ENTREES.txt` compris).
