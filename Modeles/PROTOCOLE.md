# Protocole pré-enregistré : premier jet des modèles de fréquence

**Rédigé le 15/11/2026 à 17:34 (CET), avant toute vérification de la phase 1 et avant tout ajustement
de modèle.** Branche locale `modeles-premier-jet`, créée depuis `main` au commit `69d0d21`.

Ce fichier ne sera plus modifié après l'exécution des modèles. Si les résultats contredisent les
hypothèses, `RAPPORT_MODELES.md` le dira, et les hypothèses ne seront pas réécrites.

## 1. Question

Sur la table agrégée `EDA/ds_clean.csv` (une ligne par comté × zone d'inondation × année, 2010–2024),
un LightGBM à objectif Poisson prédit-il mieux le nombre de sinistres qu'un GLM de Poisson ou binomial
négatif, avec l'exposition en polices-années comme offset ? Il s'agit d'un **premier jet
exploratoire** : l'unité n'est pas le secteur de recensement prévu par le projet.

## 2. Hypothèses pré-enregistrées

- **H-a** : les modèles font à peine mieux que le modèle nul (M0) en déviance de Poisson sur le test.
- **H-b** : tous les modèles sous-prédisent le niveau de sinistres du test. Le taux d'entraînement est
  d'environ 5,6 pour 1 000 polices-années, contre environ 15,9 en test (chiffres de
  `EDA/figures/eda_key_numbers.json`, à revérifier en V7 et V8).
- **H-c** : avec ce jeu de variables, l'écart entre GLM et LightGBM est faible.

## 3. Données, cibles et décisions fixées à l'avance

- **Découpage** : entraînement 2010–2019, test 2020–2024. Le test n'est utilisé qu'une fois, pour
  l'évaluation finale. Aucun réglage sur le test.
- **Cibles** :
  - `n_claims` : sinistres à montant bâtiment réel > 0, cible obligatoire ;
  - « tous les sinistres » : si V4 confirme qu'une colonne existe (`n_all` d'après
    `ds_clean_roles.json`), elle sert de seconde cible ; sinon, une reconstruction dans un nouveau
    script est tentée.
- **Offset** : `log(exposure_years)`.
- **Lignes exclues** :
  1. **Exposition nulle** (log impossible) : exclue, avec comptage. Blocage si plus de 1 % des lignes
     ou plus de 1 % de l'exposition sont concernés.
  2. **Exposition très faible** : **aucun seuil supplémentaire.** Une ligne de faible exposition reçoit
     une prédiction proportionnellement faible grâce à l'offset. L'exclure retirerait de vrais
     sinistres et rendrait les totaux non comparables. Le nombre de lignes sous 0,5 polices-année, et
     leurs sinistres, est rapporté en V2.
  3. **Variable explicative manquante** : la ligne est exclue de **tous** les modèles, pour que tous
     soient évalués sur les mêmes lignes. Comptage rapporté en V6.
- **Variables** :
  - `zone` (catégorielle) ;
  - `mean_coverage`, exprimée en **milliers de dollars nominaux, sans autre transformation**. C'est un
    choix d'échelle pour un coefficient lisible (effet multiplicatif par tranche de 1 000 $). La
    variable n'est pas déflatée : c'est une limite connue, car elle porte une tendance temporelle ;
  - `hist_per_1000` et `county_hist_per_1000` : **transformées par `log1p` dans les GLM**. Ces
    distributions ont une queue très lourde (d'après `eda_unit_year_summary.csv` : P99 ≈ 1 723 et
    max 9 722 pour `hist_per_1000`). Avec un lien log, une variable linéaire non transformée
    produirait des prédictions explosives aux extrêmes. LightGBM reçoit les variables brutes, puisque
    les arbres sont insensibles aux transformations monotones.
- **Interdits** : l'identifiant du comté, l'année (sauf dans le modèle « oracle », explicitement non
  prédictif), toute variable postérieure au sinistre (`water_depth`, `floodEvent`, etc.), et tout
  réglage sur le test.
- **Graine** : `SEED = 42` partout (bootstrap, permutations, LightGBM).

## 4. Modèles

| Code | Modèle | Rôle |
|---|---|---|
| M0 | Taux moyen de l'entraînement × exposition | Modèle nul |
| M1 | GLM Poisson, `zone` seule, offset | Référence |
| M_oracle | GLM Poisson, `zone` + facteur année, offset, **ajusté sur le test lui-même** | Plafond indicatif, « oracle, non prédictif » |
| M2 | GLM Poisson, `zone` + `mean_coverage` (k$) + `log1p(hist_per_1000)` + `log1p(county_hist_per_1000)`, offset | Principal |
| M3 | Binomial négatif NB2 (statsmodels `NegativeBinomial`, α estimé par maximum de vraisemblance), mêmes variables et même offset | Principal |
| M4 | LightGBM `objective="poisson"`, mêmes variables brutes, `zone` catégorielle, `init_score = log(exposure_years)` | Principal |

**Réglage de M4** :
- validation temporelle interne : ajustement sur 2010–2017, validation sur 2018–2019 ;
- arrêt précoce sur la métrique `poisson` de LightGBM (la log-vraisemblance négative, qui a le même
  minimum que la déviance) ;
- petite grille : `learning_rate` ∈ {0,02 ; 0,05}, `num_leaves` ∈ {7 ; 15},
  `min_data_in_leaf` ∈ {100 ; 300}, `lambda_l2` ∈ {1 ; 10} ;
- jusqu'à 3 000 itérations, arrêt après 100 sans amélioration ;
- puis réajustement sur 2010–2019 avec le nombre d'itérations retenu.

À la prédiction : `exp(raw_score + log(exposure_years))`. Contrôle de non-régression : la somme des
prédictions sur l'entraînement doit égaler la somme observée à 1 % près.

## 5. Plan d'évaluation (test 2020–2024)

1. Déviance de Poisson, totale et moyenne par ligne, sur l'entraînement et le test.
2. Déviance par année de test, puis sur le test complet, avec et sans 2024.
3. Calibration : sinistres prédits et observés, et leur ratio, par année ; par zone sur le test.
4. Gain relatif de déviance par rapport à M0.
5. Bootstrap par année de test (rééchantillonnage des 5 années avec remise, 1 000 réplications,
   graine 42) des différences de déviance M4 − M2 et M2 − M0. Avec 5 blocs seulement, l'intervalle est
   **indicatif** : s'il n'est pas informatif, on le dira.
6. Importance des variables de M4 (gain, et permutation sur le test, graine 42). Coefficients de M2 et
   M3 avec des erreurs standard robustes (HC0 et grappes par année), données à titre indicatif
   seulement.
7. Figures : prédit contre observé par année, calibration par zone, déviance par année.

## 6. Critères d'arrêt

- Un contrôle **BLOQUANT** de la phase 1 (V1 à V5) échoue : aucun modèle n'est ajusté. On écrit
  `BLOCAGE.md` et la documentation, puis on s'arrête.
- Un échec technique d'ajustement (non-convergence d'un GLM, non-régression LightGBM hors tolérance) :
  le modèle concerné est rapporté comme **échoué**, avec la sortie d'erreur. Les autres sont
  conservés. Aucun contournement par modification des données ou des scripts existants.
- Aucun fichier existant du dépôt n'est modifié. Tout est écrit dans `Modeles/`. Aucune opération
  Git d'écriture (commit, push, add, stash…).

## Avenant n° 1 (15/11/2026, 17:39 CET), écrit avant tout ajustement de M0 à M4

Le texte ci-dessus est conservé tel quel. Pendant le contrôle V5, sur un mini-modèle de 100 lignes, on a
constaté que lorsqu'un `init_score` est fourni, LightGBM désactive `boost_from_average`. En partant de
`init_score = log(exposure_years)`, le modèle démarre donc à 1 sinistre par police-année, alors que le
taux est d'environ 0,002. Les arbres doivent rattraper l'intercept, mais leur pas est plafonné
(`poisson_max_delta_step`) : au bout de 50 itérations, la somme prédite valait 6 853 pour 176 sinistres
observés.

**Modification de la procédure M4** :
- `init_score = log(exposure_years) + log(r)`, où r = sinistres / exposition sur les **lignes
  d'ajustement** (2010–2017 pendant le réglage, 2010–2019 pour le modèle final) ;
- prédiction : `exp(raw_score + log(exposure_years) + log(r))`.

C'est l'équivalent d'un offset accompagné d'un intercept initial, sans aucune information du test. Le
contrôle de non-régression (somme prédite = somme observée à 1 % près sur l'entraînement) est inchangé.
Le reste du protocole ne change pas.
