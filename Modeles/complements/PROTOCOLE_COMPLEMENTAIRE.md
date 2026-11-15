# Protocole complémentaire pré-enregistré : vérifications VC1 à VC4 et ablation

**Rédigé le 15/11/2026 à 17:52 (CET), avant toute exécution des vérifications complémentaires et des
ablations.** Branche locale `modeles-premier-jet`. Ce fichier ne sera plus modifié après exécution. Le
protocole du premier jet (`Modeles/PROTOCOLE.md`, avec son avenant n° 1) et ses hypothèses H-a, H-b et
H-c restent inchangés.

## 1. Éléments réutilisés (noms exacts)

- **Table** : `EDA/ds_clean.csv`. Colonnes : `county_id`, `zone` (V*, A*, X), `year`, `n_claims`,
  `n_all`, `exposure_years`, `mean_coverage`, `hist_per_1000`, `county_hist_per_1000`, `period`.
- **Préparation** : `Modeles/scripts/commun.py`. La fonction `prepare` exclut les lignes à exposition
  nulle ou à variable manquante, soit 13 lignes ; il en reste 22 472.
- **Cibles** : « payés » = `n_claims` (principale), « tous » = `n_all` (secondaire).
- **Hyperparamètres de M4** (`Modeles/resultats/ajustement_*.json`) :
  - payés : `learning_rate` 0,02, `num_leaves` 7, `min_data_in_leaf` 100, `lambda_l2` 1,
    122 itérations ;
  - tous : identique, sauf `lambda_l2` 10, 113 itérations.
- **Offset de LightGBM** (avenant n° 1) : `init_score = log(exposure_years) + log(r)`, avec r le taux
  moyen des lignes d'ajustement.
- **α̂ de M3** : 6,126863… (payés) et 4,239792… (tous), valeurs exactes lues dans
  `ajustement_*.json`. Le rapport les arrondit à 6,13 et 4,24.

## 2. Hypothèses pré-enregistrées

Les seuils ci-dessous rendent les hypothèses opérationnelles. « Gain » = gain relatif de déviance de
Poisson par rapport à M0 sur le test 2020–2024, en points de pourcentage. « Recalé » = après recalage
annuel sur les totaux observés (définition du § 5.4 de `RAPPORT_MODELES.md`).

- **H-d** : retirer `mean_coverage` améliore la déviance de test de M2. Comparaison G1 contre M2 :
  confirmée si la déviance de G1 est **inférieure** à celle de M2, **à la fois** en brut et après
  recalage.
- **H-e** : retirer `mean_coverage` modifie peu M4. Comparaison L1 contre M4 : confirmée si l'écart de
  gain est **inférieur à 2 points**, en brut et après recalage.
- **H-f** : retirer `county_hist_per_1000` ne dégrade pas M4 sur le test. Comparaison L2 contre M4 :
  confirmée si la déviance de test de L2 est **inférieure ou égale** à celle de M4, en brut et après
  recalage.
- **H-g** : M4 réduit à la zone seule (L5) est proche de M1. Confirmée si l'écart de gain est **inférieur
  à 2 points**, en brut et après recalage.

Pour chaque hypothèse, si le brut et le recalé vont dans des sens différents : **non tranchée**.

## 3. Vérifications (phase 1)

- **VC1** : offset dans la validation de LightGBM. Lecture du code, puis rejeu 2010–2017 → 2018–2019
  avec les hyperparamètres retenus.
  - Déviance de Poisson calculée à la main à chaque itération, comparée à la métrique renvoyée par
    LightGBM.
  - **DÉFAUT** si la validation n'a pas d'`init_score` ou en a un mauvais. Dans ce cas, un nouveau
    réglage est fait avec la grille élargie : `learning_rate` {0,01 ; 0,02}, `num_leaves`
    {3 ; 5 ; 7 ; 15}, `min_data_in_leaf` {100 ; 200 ; 400}, `lambda_l2` {1 ; 10}.
- **VC2** : contrôle croisé de M3. GLM statsmodels de famille `NegativeBinomial(alpha=α̂)` ; Σ(y−μ),
  Σ(y−μ)/(1+αμ) et Σμ/Σy ; binomial négatif avec constante et offset seuls.
- **VC3** : zone × temps.
  - Tableaux par année et par zone depuis `ds_clean` ;
  - codes bruts de `ratedFloodZone` par année. Ils sont absents de `claims_clean.parquet` (qui ne garde
    que `flood_zone_group`) : ils sont lus dans le fichier brut local `NfipClaimsV3_SE.parquet`,
    **agrégés uniquement** et restreints aux `id` de `claims_clean`. Si le fichier est absent, la
    vérification est déclarée non calculable ;
  - part des sinistres par `rating_system` (colonne de `claims_clean`) ;
  - exposition par système de tarification : non disponible dans les fichiers propres, donc non
    reconstruite.
- **VC4** : les 13 lignes exclues. Déviance de M0 et M1 sur le test, avec et sans elles.

## 4. Modèles de l'ablation (phase 2)

Mêmes lignes (22 472), mêmes découpages et mêmes cibles. Les GLM utilisent `log1p` des historiques,
comme M2.

| Code | Type | Variables |
|---|---|---|
| M0 | taux moyen | aucune |
| M1 | GLM Poisson | zone |
| M2 | GLM Poisson | zone + couverture (k$) + log1p(hist) + log1p(county_hist) |
| M4 | LightGBM | zone + couverture + hist + county_hist |
| G1 | GLM Poisson | zone + log1p(hist) + log1p(county_hist) |
| G2 | GLM Poisson | zone + historiques + couverture en 5 tranches (bornes : quintiles des lignes d'entraînement ; valeurs de test hors bornes dans la tranche extrême) |
| G3 | GLM Poisson | zone + couverture (k$) |
| G4 | GLM Poisson | zone + historiques + rang centile de la couverture au sein de l'année (rang des lignes de la même année, entre 0 et 1, sans sinistres) |
| L1 | LightGBM | zone + hist + county_hist |
| L2 | LightGBM | zone + couverture + hist |
| L3 | LightGBM | zone + couverture |
| L4 | LightGBM | zone + hist |
| L5 | LightGBM | zone |
| L6 | LightGBM | zone + rang centile de la couverture dans l'année + hist + county_hist |

- **Modèles LightGBM** : mêmes hyperparamètres que M4, **y compris le nombre d'itérations**, qui n'est
  pas réoptimisé par variante. C'est un choix pré-enregistré : il peut désavantager les variantes à
  moins de variables. Si VC1 révèle un défaut, ce sont les hyperparamètres corrigés qui servent.
- **M0, M1, M2 et M4 sont recalculés** dans `complements/resultats/`. On contrôle qu'ils reproduisent
  les prédictions du premier jet (écart relatif maximal inférieur à 1e-9 pour les GLM ; identité pour
  LightGBM).

## 5. Métriques

Pour chaque modèle et chaque cible :
- déviance de Poisson totale et par ligne, sur l'entraînement, le test, le test sans 2024 et chaque
  année de test ;
- gain par rapport à M0, brut et après recalage annuel (diagnostic qui utilise les totaux observés du
  test) ;
- ratio prédit / observé, par année de test et au total ;
- différence de déviance avec la référence (M2 pour les G, M4 pour les L), année par année ;
- pour les L : importance par gain et par permutation sur le test (20 répétitions, graine 42) ;
- pour les G : coefficients avec erreurs standard HC0 et en grappes par année, à titre indicatif.

Aucun bootstrap. Graine : `SEED = 42`.

## 6. Critères d'arrêt

- `Modeles/.venv` absent ou inutilisable : arrêt.
- GLM non convergent : le modèle est déclaré échoué et les autres sont conservés.
- Si les références recalculées (M0, M1, M2, M4) ne reproduisent pas le premier jet : l'écart est
  signalé, et la table s'appuie sur les valeurs recalculées, pour que tout soit sur la même base.
- Aucun fichier existant n'est modifié. Les sorties vont uniquement dans `Modeles/complements/`. Aucune
  opération Git d'écriture.
