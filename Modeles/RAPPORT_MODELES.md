# Rapport : premier jet des modèles de fréquence (comté × zone × année)

*Branche locale `modeles-premier-jet` (depuis `main`, commit `69d0d21`). Exécution du 15/11/2026.
Rien n'est commité.*

Tous les chiffres viennent des fichiers de `Modeles/resultats/`, produits par `Modeles/run_all.sh`. Les
passages marqués **[interprétation]** sont des lectures, pas des constats. Aucune conclusion causale.

## 1. Objectif et question

Premier jet exploratoire de la question du projet : un LightGBM à objectif Poisson prédit-il mieux le
nombre de sinistres qu'un GLM de Poisson ou binomial négatif, avec l'exposition en offset ?

L'unité est **comté × zone d'inondation × année** (`EDA/ds_clean.csv`), et non le secteur de
recensement prévu par le projet. Entraînement 2010–2019, test 2020–2024. Les hypothèses H-a, H-b et H-c,
et le plan d'évaluation, ont été fixés avant tout ajustement (`PROTOCOLE.md`, 15/11/2026 à 17:34). Un
avenant (17:39) a modifié la procédure d'offset de LightGBM, toujours avant tout ajustement (§ 4).

## 2. Données et décisions

- **Lignes** : 22 485 dans `ds_clean`. 13 sont exclues de tous les modèles (`hist_per_1000` manquant ;
  ce sont des cellules présentes uniquement en test, sans sinistre). Restent 22 472 lignes : 14 999 en
  entraînement et 7 473 en test.
- **Exposition** : aucune ligne nulle ou négative. Aucun seuil d'exclusion des faibles expositions
  (décision pré-enregistrée) : 108 lignes ont moins de 0,5 police-année, avec 1 sinistre payé.
- **Cibles** :
  - « payés », `n_claims` : 88 898 sinistres en entraînement, 108 584 en test ;
  - « tous », `n_all` : 123 082 en entraînement, 130 316 en test. `n_all` existait déjà ; aucune
    reconstruction n'a été nécessaire.
- **Variables** :
  - `zone` (V*, A*, X ; X est la référence des GLM) ;
  - `mean_coverage`, en milliers de dollars nominaux ;
  - `hist_per_1000` et `county_hist_per_1000`, transformées par `log1p` dans les GLM et brutes dans
    LightGBM.
- **Variables exclues** : l'identifiant du comté, l'année (sauf dans l'oracle) et toute variable
  postérieure au sinistre.

## 3. Vérifications (détail dans `VERIFICATIONS.md`)

Les huit contrôles sont réussis, sans blocage. Écarts et remarques :

- **V1** : `n_all` a le rôle « controls » dans `ds_clean_roles.json` (compte de sensibilité). Son usage
  comme seconde cible suit la consigne.
- **V3** :
  - les historiques n'utilisent que les sinistres de **1990–2008**. Le recalcul indépendant depuis
    `claims_clean.parquet` donne 0 ligne différente ;
  - le **dénominateur** est l'exposition moyenne 2010–2019 de la cellule, calculée sur les années
    présentes. Pour une ligne d'entraînement, il utilise donc l'exposition d'années postérieures, et,
    pour la validation interne de LightGBM, celle de 2018–2019. C'est une légère information future, qui
    ne porte pas sur les sinistres. Signalée, non bloquante.
- **V5** :
  - **LightGBM 4.7.0 ne se charge pas sans `libomp`**, et Homebrew n'est pas installé. Contournement
    local : `DYLD_FALLBACK_LIBRARY_PATH` désigne la copie de `libomp` fournie par scikit-learn dans le
    venv. Solution standard : `brew install libomp` ;
  - **la procédure d'offset initiale était incorrecte** : avec `init_score = log(exposition)`, la somme
    prédite valait 6 853 pour 176 sinistres observés sur 100 lignes (§ 4).
- **V6** : la zone V* ne représente que 1,35 % de l'exposition d'entraînement. Les VIF valent au plus
  3,0. La corrélation de Spearman entre les deux historiques est de 0,81.
- **V7** :
  - taux d'entraînement : 5,597 (payés) et 7,749 (tous) pour 1 000 polices-années ;
  - taux de test : 15,927 et 19,115 ;
  - 2024 porte 50,8 % des sinistres payés du test (48,5 % pour « tous ») ;
  - la composition par zone est stable : la zone A passe de 58,7 % de l'exposition en entraînement à
    55,1 % en test.
- **V8** : tous les chiffres recoupés sont identiques (22 485, 14 999 / 7 486, dispersions
  167,39 / 141,24 / 125,88, part de 2024 de 0,508, fréquences 5,597 / 15,927).

## 4. Spécification des modèles

| Code | Spécification |
|---|---|
| M0 | Taux moyen de l'entraînement × exposition |
| M1 | GLM Poisson, `zone`, offset log(exposition) |
| M_oracle | GLM Poisson, `zone` + facteur année, ajusté **sur chaque période elle-même**. Oracle, non prédictif |
| M2 | GLM Poisson, `zone` + couverture (k$) + log1p(historique de la cellule) + log1p(historique du comté), offset |
| M3 | Binomial négatif NB2 (statsmodels `NegativeBinomial`, α par maximum de vraisemblance), mêmes variables et même offset |
| M4 | LightGBM `poisson`, mêmes variables brutes, zone catégorielle |

**Points techniques constatés pendant l'exécution :**

- **M3** : avec les valeurs de départ par défaut, statsmodels renvoie des paramètres NaN tout en
  signalant « converged ». Le départ est donc fixé aux coefficients de M2 et à α = 1. Newton et BFGS
  donnent alors la même log-vraisemblance (écart de 7e-9).
- **M4** (avenant n° 1) : `init_score = log(exposition) + log(r)`, avec r le taux moyen des lignes
  d'ajustement. En effet, LightGBM ignore `boost_from_average` quand un `init_score` est fourni.
  - Réglage : ajustement sur 2010–2017, validation sur 2018–2019, grille de 16 combinaisons.
  - Retenu (payés) : `learning_rate` 0,02, `num_leaves` 7, `min_data_in_leaf` 100, `lambda_l2` 1,
    122 itérations.
  - Retenu (tous) : identique, sauf `lambda_l2` = 10, 113 itérations.
  - Non-régression : la somme prédite sur l'entraînement vaut 1,0013 fois (payés) et 1,0009 fois (tous)
    la somme observée, dans la tolérance de 1 %.
- **Ajustement sur l'entraînement** :
  - M2 : dispersion de Pearson / ddl = 109,2 (payés) et 111,3 (tous) ;
  - M3 : α = 6,13 (payés) et 4,24 (tous) ;
  - AIC sur l'entraînement, M2 contre M3 : 388 487 contre 36 690 (payés), 461 879 contre 44 163 (tous).

## 5. Résultats

### 5.1 Déviance de Poisson sur le test (gain relatif par rapport à M0)

| Modèle | Payés, test 2020–2024 | Payés, sans 2024 | Tous, test 2020–2024 | Tous, sans 2024 |
|---|---:|---:|---:|---:|
| M0 | 547 575 (0 %) | 246 986 (0 %) | 592 664 (0 %) | 277 812 (0 %) |
| M1 | 508 725 (+7,1 %) | 228 982 (+7,3 %) | 551 747 (+6,9 %) | 258 345 (+7,0 %) |
| M2 | 566 180 (**−3,4 %**) | 253 522 (−2,6 %) | 603 949 (−1,9 %) | 281 483 (−1,3 %) |
| M3 | 472 303 (+13,7 %) | 228 395 (+7,5 %) | 515 429 (+13,0 %) | 259 981 (+6,4 %) |
| M4 | 460 683 (**+15,9 %**) | 212 452 (+14,0 %) | 488 597 (+17,6 %) | 237 094 (+14,7 %) |
| M_oracle (non prédictif) | 311 450 (+43,1 %) | 175 096 (+29,1 %) | 349 439 (+41,0 %) | 199 154 (+28,3 %) |

Déviance moyenne par ligne sur le test (payés) : M0 73,27 ; M1 68,08 ; M2 75,76 ; M3 63,20 ;
M4 61,65.

Gain par rapport à M0 **sur l'entraînement** (payés) : M1 +2,5 %, M2 +10,6 %, **M3 −3,7 %**, M4 +23,9 %.

### 5.2 Calibration : ratio prédit / observé

| Payés | M0 | M1 | M2 | M3 | M4 |
|---|---:|---:|---:|---:|---:|
| Entraînement 2010–2019 | 1,000 | 1,000 | 1,000 | **1,944** | 1,001 |
| Test 2020–2024 | 0,351 | 0,344 | 0,319 | 0,629 | 0,441 |
| 2020 | 0,684 | 0,658 | 0,637 | 1,254 | 0,720 |
| 2021 | 2,418 | 2,336 | 2,223 | 4,386 | 2,710 |
| 2022 | 0,249 | 0,243 | 0,227 | 0,447 | 0,301 |
| 2023 | 0,935 | 0,927 | 0,834 | 1,645 | 1,368 |
| 2024 | 0,130 | 0,131 | 0,114 | 0,227 | 0,193 |

Le tableau pour « tous » est dans `resultats/par_annee_calibration_deviance.csv`, avec le même profil :
au total du test, 0,376 (M2), 0,698 (M3) et 0,524 (M4).

**Calibration par zone sur le test (payés)** :

| Zone | M2 | M3 | M4 |
|---|---:|---:|---:|
| X | 0,986 | 2,610 | 1,407 |
| A* | 0,256 | 0,452 | 0,355 |
| V* | 0,326 | 0,419 | 0,343 |

### 5.3 Incertitude : bootstrap des 5 années de test (1 000 tirages, graine 42)

| Différence de déviance (test) | Valeur | Intervalle à 95 % (percentiles) | Part des tirages < 0 | Valeur en retirant chaque année tour à tour (min ; max) |
|---|---:|---|---:|---|
| Payés, M4 − M2 | −105 497 | [−221 928 ; +10 783] | 92,6 % | [−108 604 ; −41 070] |
| Payés, M2 − M0 | +18 605 | [−33 400 ; +72 326] | 27,3 % | [−5 246 ; +31 265] |
| Payés, M4 − M0 | −86 892 | [−169 038 ; −17 213] | 100 % | [−86 418 ; −34 534] |
| Tous, M4 − M2 | −115 351 | [−245 972 ; +15 269] | 92,1 % | [−119 690 ; −44 389] |
| Tous, M4 − M0 | −104 066 | [−202 969 ; −14 111] | 99,2 % | [−104 977 ; −40 718] |

Avec 5 blocs, les 1 000 tirages ne produisent que **118 combinaisons distinctes**. Ces intervalles sont
**indicatifs** : ils ne valent pas une incertitude d'échantillonnage. M4 − M2 n'est négatif qu'en 2022,
2023 et 2024 (payés).

### 5.4 Diagnostic complémentaire, non pré-enregistré : déviance après recalage annuel

Chaque modèle est multiplié, année par année, par le rapport du total observé au total prédit. Cela
retire l'erreur de niveau et ne laisse que la **répartition entre cellules**. Ce calcul utilise les
totaux observés du test : ce n'est pas une prédiction.

| Gain par rapport à M0 recalé (payés) | M1 | M2 | M3 | M4 | M_oracle |
|---|---:|---:|---:|---:|---:|
| Test 2020–2024 | +10,6 % | −0,5 % | +3,1 % | +11,7 % | +16,9 % |
| Test sans 2024 | +9,4 % | −1,1 % | +2,7 % | +13,7 % | +13,7 % |

Pour « tous » : M1 +10,0 %, M2 +0,6 %, M3 +3,5 %, M4 +12,5 %.

### 5.5 Variables

**Importance dans M4 (payés)** :

| Variable | Part du gain (entraînement) | Hausse de la déviance de test par permutation (20 répétitions) |
|---|---:|---:|
| `zone` | 11,2 % | +78 523 (±23 647) |
| `mean_coverage` | 22,2 % | +65 558 (±27 114) |
| `hist_per_1000` | 17,8 % | +15 627 (±13 287) |
| `county_hist_per_1000` | 48,8 % | **−13 784** (±12 549) |

**Coefficients (payés, entraînement)**, avec des erreurs standard à lire **à titre indicatif seulement** :

| Variable | M2 coef. (exp) | E.S. modèle | E.S. HC0 | E.S. grappes par année | M3 coef. (exp) |
|---|---|---:|---:|---:|---|
| zone V* (réf. X) | 0,753 (×2,12) | 0,024 | 0,300 | 0,283 | 0,471 (×1,60) |
| zone A* (réf. X) | 0,425 (×1,53) | 0,011 | 0,222 | 0,253 | 0,219 (×1,24) |
| couverture (par k$ nominal) | −0,0055 (×0,9945) | 0,0001 | 0,0029 | 0,0047 | −0,0043 |
| log1p(historique de la cellule) | 0,178 | 0,008 | 0,127 | 0,089 | 0,063 |
| log1p(historique du comté) | 0,286 | 0,009 | 0,179 | 0,264 | 0,157 |

Pour M3, α = 6,13 (E.S. 0,13).

## 6. Lecture par rapport aux hypothèses pré-enregistrées

- **H-a** (les modèles font à peine mieux que M0 sur le test) :
  - **confirmée pour M2**, qui fait même moins bien que M0 (−3,4 %) ;
  - **contredite pour M4 et, en apparence, pour M3** : gains de +15,9 % et +13,7 %. Pour M4, toutes les
    variantes du bootstrap et du retrait d'une année restent négatives par rapport à M0, avec la réserve
    des 118 combinaisons ;
  - **[interprétation]** le gain de M3 tient surtout au niveau (§ 7.2) : il tombe à +3,1 % après
    recalage. Celui de M4 résiste (+11,7 %), mais il dépasse à peine celui de M1 (+10,6 %).
    *Correction du 15/11/2026 (`complements/RAPPORT_COMPLEMENTS.md`, § 8, point 3) : ce gain dépend presque
    entièrement de la couverture nominale. Sans elle, LightGBM tombe à −5,4 % en brut.*
- **H-b** (tous les modèles sous-prédisent le niveau du test) :
  - **confirmée au total** : le ratio prédit / observé va de 0,319 (M2) à 0,629 (M3) pour les payés ;
  - **pas chaque année** : 2021 est surprédite par tous les modèles (2,2 à 4,4 fois), et 2023 l'est par
    M3 et M4.
- **H-c** (écart faible entre GLM et LightGBM) :
  - **contredite face à M2** : M4 − M2 = −105 497, soit 19 % de la déviance de M0. Mais l'intervalle
    bootstrap contient 0 ;
  - **plutôt confirmée face à M3** (−11 620) et face au GLM « zone seule » M1 une fois le niveau retiré
    (11,7 % contre 10,6 %) ;
  - **[interprétation]** l'écart dépend donc surtout du GLM choisi. *Correction du 15/11/2026
    (`complements/RAPPORT_COMPLEMENTS.md`, § 8, point 1) : le retard du GLM Poisson complet sur M1 vient
    surtout des historiques, comme le montre l'ablation ; la couverture nominale y contribue par un effet de
    niveau.*

## 7. Constats suspects et limites

1. **Procédure d'offset de LightGBM.** La procédure initialement prévue sous-estimait l'intercept : la
   somme prédite valait 39 fois la somme observée sur le mini-modèle. Elle a été corrigée par l'avenant
   n° 1 avant tout ajustement. Il faudra la reprendre dans le vrai projet.
2. **Niveau de M3.** Le binomial négatif prédit **1,94 fois** le total observé sur l'entraînement.
   L'estimateur du maximum de vraisemblance NB2 n'impose pas l'égalité des totaux, contrairement au GLM
   Poisson avec constante. *Correction du 15/11/2026 (VC2) : l'écart existe déjà avec la constante seule
   (Σμ/Σy = 2,64) ; le rôle propre de α n'est pas démontré.* Son bon score brut sur le test vient en partie de ce
   niveau trop haut, qui compense par hasard la hausse des sinistres en test. Il surprédit la zone X
   d'un facteur 2,6.
3. **Couverture nominale.** *Corrigé le 15/11/2026 : les moyennes de 203,6 k$ et 222,0 k$ et le facteur
   0,904 cités ici ne figuraient dans aucun fichier de résultats ; ils sont retirés.* Constat sourcé : la
   tranche de couverture la plus haute (quintiles de l'entraînement) passe de 81,0 % de l'exposition
   d'entraînement à 92,9 % de celle du test (`complements/resultats/hp_taux_par_tranche_couverture.csv`).
   Avec un coefficient de couverture négatif (−0,0055 par k$ pour M2), cela abaisse les prédictions de M2
   sur le test. C'est l'effet de temps déguisé déjà signalé dans le rapport de projet. M2 fait moins bien
   que M1 (zone seule) sur le test, mais surtout à cause des historiques (voir l'ablation des compléments).
4. **L'historique du comté nuit sur le test** pour M4 : sa permutation *réduit* la déviance (−13 784).
   Il porte pourtant 49 % du gain à l'entraînement. **[interprétation]** Cela concorde avec la faible
   persistance géographique entre périodes (ρ = 0,11 dans l'EDA).
5. **L'oracle n'est pas un plafond.** Il ne contient que la zone et l'année. En 2020 et 2021, M2 le bat
   (+30,9 % contre +11,9 % en 2020).
6. **Erreurs standard.** Celles du modèle Poisson sont environ 10 fois trop petites par rapport à HC0
   (surdispersion d'environ 109). Aucune inférence n'est à tirer des coefficients.
7. **Grille de LightGBM.** Les hyperparamètres retenus sont tous aux bornes basses de la grille
   (`learning_rate` 0,02, `num_leaves` 7, `min_data_in_leaf` 100). La grille est peut-être trop étroite.
8. **Limites générales** :
   - dépendance entre cellules d'un même événement : les déviances ne sont pas des sommes
     d'observations indépendantes ;
   - surdispersion forte ;
   - **5 années de test**, dont **2024 (50,8 %)** domine ;
   - `mean_coverage` en dollars nominaux ;
   - jeu de variables mince (4 variables) ;
   - exposition construite à partir de transactions de police sans clé ;
   - cible « payés » dépendante de la politique de règlement, et cible « tous » sensible au recodage des
     paiements NA avant 2018 ;
   - unité comté × zone et non secteur ;
   - le dénominateur des historiques utilise l'exposition 2010–2019 (V3) ;
   - LightGBM tourne grâce à un contournement local de `libomp`.

## 8. Ce qui est établi, choisi ou heuristique

- **Établi (calculé, reproductible à l'octet près sur deux exécutions)** : les déviances, ratios,
  intervalles bootstrap et importances ci-dessus, sur ces données et avec ces spécifications.
- **Choix de modélisation** :
  - l'exclusion des 13 lignes à variable manquante ;
  - l'absence de seuil d'exposition ;
  - `log1p` pour les historiques des GLM, la couverture en k$ ;
  - la zone X comme référence ;
  - l'offset de LightGBM (avenant n° 1) ;
  - la grille et la fenêtre de validation 2018–2019 ;
  - les valeurs de départ de M3.
- **Heuristique** : le bootstrap par année (5 blocs), le recalage annuel (diagnostic), et l'importance
  par permutation (variables corrélées, Spearman 0,81 entre historiques).

## 9. Étapes suivantes proposées (non exécutées)

1. Revaloriser la couverture (CPI), ou la remplacer par un rang au sein de l'année, puis réévaluer M2 et
   M4.
2. Pour M3 : évaluer après recalage du niveau sur l'entraînement, ou comparer avec un NB à moyenne
   contrainte. Rapporter systématiquement la calibration totale.
3. Évaluation glissante sur plus d'années (prédire chaque année de 2016 à 2024 à partir des années
   antérieures), pour dépasser 5 blocs.
4. Élargir la grille de LightGBM (taux d'apprentissage plus bas, `min_data_in_leaf` plus élevé) et
   tester sans l'historique du comté.
5. Calculer le dénominateur des historiques avec les seules années d'ajustement de chaque pli.
6. Ajouter le Gini et la calibration par décile prévus par le projet, puis reproduire le tout au niveau
   secteur × année.
