# Rapport des compléments : vérifications VC1 à VC4 et ablation des variables

*Branche locale `modeles-premier-jet`. Exécution du 15/11/2026. Rien n'est commité.*

Tous les chiffres viennent de `Modeles/complements/resultats/` et de
`Modeles/complements/VERIFICATIONS_COMPLEMENTAIRES.md`, produits par `Modeles/complements/run_all.sh`.
Conventions :
- **constat** : un chiffre calculé ;
- **[interprétation]** : une lecture des chiffres ;
- **non démontré** : une hypothèse que les calculs ne tranchent pas.

Les hypothèses H-d à H-g et leurs seuils ont été fixés avant toute exécution
(`PROTOCOLE_COMPLEMENTAIRE.md`, 17:52). Deux éléments ont été ajoutés après lecture des résultats et sont
marqués **hors protocole** : le modèle `G5_hp` et le tableau `hp_taux_par_tranche_couverture.csv`.

## 1. Objectif et lien avec le premier jet

Le premier jet (`Modeles/RAPPORT_MODELES.md`) concluait sur trois points :
- le gain de LightGBM (M4) par rapport au modèle nul était réel en brut, mais dépassait à peine celui du
  GLM « zone seule » (M1) après recalage annuel ;
- le binomial négatif (M3) devait son score à un niveau trop haut ;
- la couverture nominale pénalisait le GLM Poisson complet (M2).

Ce complément vérifie quatre points techniques (VC1 à VC4), puis retire les variables une à une pour
localiser la source des écarts. Les références M0, M1, M2 et M4 sont recalculées : elles reproduisent
exactement le premier jet (écart relatif de 0, `ablation_reproduction_premier_jet.csv`).

## 2. Vérifications

| | Statut | Constat | Conséquence |
|---|---|---|---|
| VC1 Offset dans la validation de LightGBM | **CONFORME** | La validation reçoit `init_score = log(e) + log(r_fit)`, avec r_fit calculé sur 2010–2017. La métrique d'arrêt précoce de LightGBM est identique à la log-vraisemblance négative recalculée à la main (écart maximal 5,9e-14 pour payés, 7,5e-14 pour tous). La déviance recalculée à la main est minimale à l'itération 122 (payés) et 113 (tous), soit celles retenues. Sans offset en validation, la déviance de validation passerait de 100 796 à 163 014 (illustration). | Pas de nouveau réglage : les ablations réutilisent les hyperparamètres du premier jet. |
| VC2 Contrôle croisé de M3 | **CONFORME** | Un GLM `NegativeBinomial(α̂)` reproduit M3 : écart maximal de 1,5e-6 sur les coefficients, de 1,3e-10 sur la log-vraisemblance. Sur l'entraînement, Σ(y−μ)/(1+αμ) = 0 (score de la constante en NB2), mais Σ(y−μ) = −83 884 (payés) et −104 822 (tous). Σμ/Σy = 1,944 et 1,852. Avec seulement la constante et l'offset, Σμ/Σy vaut déjà 2,637 (α = 6,55) et 2,411 (α = 4,49). | Étaye la première partie du § 7.2 du premier jet : l'estimateur NB2 n'impose pas l'égalité des totaux, et l'écart existe sans aucune variable. Le rôle propre de la valeur de α n'est pas isolé : **non démontré**. |
| VC3 Zone × temps | **ÉCART** (règle : un code brut d'au moins 1 % d'une année apparaît ou disparaît autour de 2021) | Le code déclencheur est `NA` (zone brute manquante) : jusqu'à 2,6 % des sinistres en 2018, puis 0 à partir de 2021. Voir le détail ci-dessous. | Hypothèses à vérifier, aucune cause établie. |
| VC4 Les 13 lignes exclues | **CONFORME** | Les 13 lignes (comtés 13197, 13239, 13307, 37081) sont toutes en test et sans sinistre. Elles pèsent 1,6e-6 de l'exposition du test, et modifient la déviance de test de M0 et M1 d'au plus 3,8e-7 en relatif. | Exclusion négligeable. |

**Détail de VC3 (constats) :**

- **Taux de sinistres payés pour 1 000 polices-années, entraînement → test** :
  - A* : 6,85 → 25,50, soit ×3,72 ;
  - V* : 14,11 → 41,22, soit ×2,92 ;
  - X : 3,48 → 3,02, soit ×0,87.

  Pour « tous » : ×3,22, ×2,43 et ×0,88.
- **Zone X dans le temps** :
  - sa part de l'exposition reste entre 40,2 % et 46,4 % de 2018 à 2024 ;
  - sa part des sinistres payés passe de 34,9 % (2021) à 6,9 %, 5,5 % et 5,4 % (2022–2024) ;
  - son taux annuel en 2022–2024 (3,53 ; 0,79 ; 5,81) reste dans la plage observée à l'entraînement
    (par exemple 6,28 en 2018).
- **Codes bruts de `ratedFloodZone`** (lus dans le fichier brut local, agrégés, restreints aux sinistres
  de `claims_clean`) :
  - les anciens codes B et C (rangés en X) pèsent de 0,9 % à 8,7 % des sinistres avant 2022, puis moins
    de 0,1 % ensuite ;
  - aucun code n'apparaît après 2021 ;
  - 19 codes rares disparaissent après 2021 ; un seul dépasse 1 % une année : `NA`.
- **Système de tarification** : la part des sinistres codés Risk Rating 2.0 atteint 93 % à 97 % en 2022
  selon la zone, puis 100 % en 2023–2024. Elle n'est pas nulle avant 2021 (10,7 % en A* dès 2010). Cela
  concorde avec un code d'occupation qui refléterait le dernier enregistrement de la police plutôt que
  le système en vigueur au sinistre, mais c'est **non démontré**.
- **Exposition par système de tarification** : non disponible dans les fichiers propres ; rien n'a été
  reconstruit.
- **Regroupement des zones** (`clean_data.py`, CONFIG) :
  - A* = A, AE, A1–A30, A01–A09, A99, AH, AHB, AO, AOB, AR et variantes ;
  - V* = V, VE, V1–V30, V01–V09 ;
  - X = X, B, C ;
  - D à part ;
  - tout autre code non manquant → « autre » ; la zone manquante reste NA.

  `build_ds_clean.py` ne garde que V*, A* et X. D, « autre » et NA sont exclus, côté sinistres comme
  côté exposition.
- **[interprétation]** La chute de la part de X dans les sinistres accompagne la hausse en A*. Le taux
  de X lui-même ne montre pas de rupture. Un changement de codage des zones lié à Risk Rating 2.0 reste
  une hypothèse **non démontrée** ; vérifier les codes bruts côté polices serait nécessaire et n'a pas été
  fait.

## 3. Table d'ablation

Gain de déviance de Poisson par rapport à M0 sur le test 2020–2024, en pourcentage. Le **recalage**
utilise les totaux observés de chaque année de test : c'est un diagnostic, pas une prédiction. Ratio =
somme prédite / somme observée sur le test.

### Sinistres payés (cible principale)

| Modèle | Variables | Entraînement | Test brut | Test sans 2024 | Test recalé | Sans 2024, recalé | Ratio test |
|---|---|---:|---:|---:|---:|---:|---:|
| M1 | zone (GLM) | 2,45 | 7,09 | 7,29 | 10,61 | 9,37 | 0,344 |
| M2 | zone + couverture + historiques (GLM) | 10,61 | −3,40 | −2,65 | −0,46 | −1,13 | 0,319 |
| G1 | zone + historiques | 10,10 | 0,15 | −0,99 | −0,98 | −1,68 | 0,358 |
| G2 | zone + historiques + couverture en tranches | 11,31 | −2,13 | −1,81 | −0,11 | −0,55 | 0,327 |
| G3 | zone + couverture | 5,65 | −3,19 | 0,67 | 7,89 | 7,08 | 0,273 |
| G4 | zone + historiques + rang de couverture | 11,37 | 0,69 | −0,83 | −1,42 | −2,06 | 0,367 |
| G5_hp *(hors protocole)* | zone + couverture en tranches | 6,91 | 0,08 | 2,23 | 6,89 | 6,60 | 0,301 |
| M4 | 4 variables (LightGBM) | 23,87 | 15,87 | 13,98 | 11,70 | 13,68 | 0,441 |
| L1 | sans couverture | 20,77 | −5,40 | −5,07 | −8,95 | −6,85 | 0,362 |
| L2 | sans historique du comté | 21,70 | **21,80** | 18,95 | **16,44** | 18,36 | 0,488 |
| L3 | zone + couverture | 12,40 | 15,63 | 12,63 | 13,73 | 13,24 | 0,421 |
| L4 | zone + historique de la cellule | 18,72 | −2,74 | −2,59 | −4,92 | −3,70 | 0,359 |
| L5 | zone seule | 2,22 | 5,33 | 5,53 | 7,95 | 7,08 | 0,346 |
| L6 | rang de couverture à la place de la couverture | 24,53 | −8,70 | −5,82 | −12,84 | −7,45 | 0,354 |

Déviance totale de test de M0 : 547 575.

### Tous les sinistres (cible secondaire)

| Modèle | Entraînement | Test brut | Test sans 2024 | Test recalé | Sans 2024, recalé | Ratio test |
|---|---:|---:|---:|---:|---:|---:|
| M1 | 2,59 | 6,90 | 7,01 | 10,02 | 8,95 | 0,398 |
| M2 | 9,67 | −1,90 | −1,32 | 0,62 | −0,08 | 0,376 |
| G1 | 9,33 | 0,85 | −0,14 | 0,21 | −0,52 | 0,411 |
| G2 | 10,31 | −0,97 | −0,67 | 0,87 | 0,43 | 0,383 |
| G3 | 5,15 | −1,87 | 1,61 | 7,94 | 7,15 | 0,326 |
| G4 | 10,37 | 1,39 | 0,01 | −0,08 | −0,82 | 0,420 |
| G5_hp *(hors protocole)* | 6,29 | 1,13 | 3,03 | 7,07 | 6,78 | 0,356 |
| M4 | 21,64 | 17,56 | 14,66 | 12,48 | 14,62 | 0,524 |
| L1 | 18,52 | −4,03 | −3,90 | −6,64 | −5,28 | 0,415 |
| L2 | 19,64 | 19,71 | 15,74 | 14,72 | 15,45 | 0,540 |
| L3 | 11,51 | 14,61 | 11,38 | 13,08 | 12,15 | 0,478 |
| L4 | 16,51 | −1,81 | −1,50 | −3,34 | −2,25 | 0,413 |
| L5 | 2,32 | 5,05 | 5,19 | 7,31 | 6,59 | 0,400 |
| L6 | 22,05 | −6,97 | −4,24 | −10,03 | −5,44 | 0,407 |

Déviance totale de test de M0 : 592 664. Les ratios par année sont dans
`ablation_calibration_annee.csv`. Le profil est le même pour tous les modèles : surprédiction en 2021,
forte sous-prédiction en 2022 et 2024.

### Différence de déviance avec la référence, par année (payés ; négatif = mieux que la référence)

| Modèle (référence) | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|---:|
| G1 (M2) | −1 911 | +1 750 | −3 915 | −25 | −15 347 |
| G3 (M2) | +10 824 | −850 | −17 571 | −589 | +7 056 |
| L1 (M4) | +833 | −1 766 | +43 965 | +4 013 | +69 414 |
| L2 (M4) | −70 | +1 097 | −13 271 | −29 | −20 199 |
| L3 (M4) | +6 577 | +1 746 | −5 959 | +984 | −2 053 |
| L5 (M4) | +6 714 | +138 | +13 821 | +201 | +36 823 |

Le reste est dans `ablation_diff_par_annee.csv`. Les écarts se jouent surtout en 2022 et 2024.

## 4. Hypothèses H-d à H-g

| Hypothèse | Critère pré-enregistré | Payés | Tous | Verdict |
|---|---|---|---|---|
| **H-d** : retirer la couverture améliore M2 | déviance de G1 < M2, en brut **et** après recalage | brut : 546 732 < 566 180 ✓ ; recalé : −0,98 % contre −0,46 % ✗ | brut ✓ (587 648 < 603 949) ; recalé : 0,21 % contre 0,62 % ✗ | **Non tranchée** (le brut et le recalé divergent) |
| **H-e** : retirer la couverture modifie peu M4 | écart de gain entre L1 et M4 < 2 points, brut et recalé | 21,3 et 20,6 points | 21,6 et 19,1 points | **Contredite** |
| **H-f** : retirer l'historique du comté ne dégrade pas M4 | déviance de L2 ≤ M4, brut et recalé | 428 210 ≤ 460 683 ✓ ; recalé 16,44 % ≥ 11,70 % ✓ | ✓ ; ✓ | **Confirmée** (L2 est même meilleur) |
| **H-g** : L5 proche de M1 | écart de gain < 2 points, brut et recalé | brut : 1,76 ✓ ; recalé : 2,66 ✗ | brut : 1,85 ✓ ; recalé : 2,71 ✗ | **Non tranchée** |

**Sur H-g (constat)** : L5 reste sous M1 jusque sur l'entraînement (2,22 % contre 2,45 %). Or M1 est
l'estimateur du maximum de vraisemblance du modèle « zone seule » sur l'entraînement : aucun modèle à
zone seule ne peut faire mieux que lui sur ces lignes. L5 est donc sous-ajusté, ce qui concorde avec le
nombre d'itérations non réoptimisé (122, avec un taux d'apprentissage de 0,02), un choix pré-enregistré.

## 5. Réponses aux trois questions

**(a) La différence entre LightGBM et le GLM tient-elle à la non-linéarité ou à l'extrapolation de la
couverture nominale ?**

Constats :
- **Sans couverture, LightGBM fait moins bien que le GLM équivalent** : L1 −5,40 % brut / −8,95 % recalé,
  contre G1 +0,15 % / −0,98 %.
- **Avec zone et couverture seulement, LightGBM l'emporte nettement** : L3 +15,63 % / +13,73 %, contre
  G3 (linéaire) −3,19 % / +7,89 % et `G5_hp` (en tranches, hors protocole) +0,08 % / +6,89 %.
- **Le rang de la couverture dans l'année ne reproduit pas l'effet** : L6 −8,70 % / −12,84 %.
- **Aucune valeur de test ne sort de la plage d'entraînement** (0 hors bornes). En revanche, 43,7 % des
  lignes de test tombent dans la tranche haute T5, contre 20 % à l'entraînement par construction.
- **Tableau descriptif hors protocole** (`hp_taux_par_tranche_couverture.csv`) :
  - T5 porte 81 % de l'exposition d'entraînement et 92,9 % de celle du test ;
  - son taux observé passe de 4,34 à 16,29 ;
  - L3 prédit 4,78 pour T5 en entraînement et 6,42 en test ;
  - `G5_hp` prédit 4,18.

[interprétation] L'avantage de LightGBM sur les GLM dépend de la couverture **nominale**. Ce n'est pas
une non-linéarité générale de la couverture, puisque les tranches de `G5_hp` ne la reproduisent pas, ni
une extrapolation hors de la plage observée, puisqu'il n'y a aucune valeur hors bornes. Le fait que le
rang dans l'année (sans composante temporelle) supprime l'effet concorde avec l'hypothèse que LightGBM
exploite une composante temporelle de la couverture nominale. Cette hypothèse reste **non démontrée** :
des seuils fins au sein de T5 ou des interactions avec la zone pourraient aussi jouer.

**(b) Quelle part du gain après recalage vient de la zone seule ?**

- **Payés** : M1 obtient 10,61 %, soit **91 %** du gain recalé de M4 (11,70 %) et **64 %** de celui de
  L2 (16,44 %), une variante choisie en regardant le test. *Corrigé le 15/11/2026 : 64 % et non 65 %, à
  partir des valeurs exactes.*
- **Tous** : 10,02 %, soit 80 % de M4 (12,48 %) et 68 % de L2 (14,72 %).
- LightGBM avec la zone seule (L5, 7,95 %) est sous-ajusté (§ 4).

**(c) Les historiques apportent-ils quelque chose hors période ?**

Constats :
- **Dans les GLM** : ajouter les deux historiques à la zone fait passer le gain recalé de 10,61 % (M1) à
  −0,98 % (G1). Les retirer de M2 le fait passer de −0,46 % à 7,89 % (G3).
- **Dans LightGBM, l'historique du comté nuit** : sans lui (L2), +4,74 points de gain recalé, et sa
  permutation dans M4 améliore le test (−13 784).
- **L'historique de la cellule nuit seul** : L4 −4,92 % contre L5 +7,95 %.
- **Mais il est utile avec la couverture dans L2** : sa permutation y dégrade le test de +34 198
  (± 17 653).

[interprétation] Hors période, les historiques n'apportent rien aux GLM, et leur apport à LightGBM n'existe
qu'en combinaison avec la couverture. L'historique du comté est nuisible dans tous les cas observés.
L'apport de l'historique de la cellule reste **non tranché**, compte tenu de la dispersion des
permutations.

## 6. Ce qui est établi, choisi ou heuristique

- **Établi (calculé, reproductible)** :
  - les statuts de VC1, VC2 et VC4 ;
  - les tableaux de VC3 ;
  - les déviances, gains, ratios et différences annuelles de l'ablation ;
  - la reproduction exacte des références ;
  - l'inégalité d'entraînement entre L5 et M1.
- **Choix de modélisation** :
  - les seuils opérationnels des hypothèses (2 points, sens commun du brut et du recalé) ;
  - le nombre d'itérations de LightGBM non réoptimisé par variante ;
  - les tranches par quintiles de lignes (et non d'exposition, d'où 81 % de l'exposition en T5) ;
  - le rang de couverture calculé au sein de l'année ;
  - `log1p` des historiques dans les GLM ;
  - la lecture des codes de zone dans le fichier brut (agrégats seulement).
- **Heuristique** :
  - le recalage annuel (il utilise les totaux observés) ;
  - l'importance par permutation (variables corrélées) ;
  - la règle de statut de VC3 (seuil de 1 %) ;
  - `G5_hp` et le tableau par tranche, ajoutés hors protocole après lecture des résultats.

## 7. Limites et points non tranchés

- 5 années de test, dont 2024 pèse 50,8 % des sinistres payés. Les écarts entre modèles se concentrent
  en 2022 et 2024.
- Dépendance entre cellules touchées par un même événement : les différences de déviance ne sont pas
  des sommes d'observations indépendantes. Aucune incertitude n'est calculée ici, comme le demandait la
  consigne.
- Le recalage utilise les totaux observés du test.
- Le nombre d'itérations de LightGBM n'est pas réoptimisé par variante. Cela désavantage les variantes
  plus simples, comme le montre L5.
- Couverture en dollars nominaux, unité comté × zone, cible influencée par la politique de règlement.
- **Non tranchés** : le mécanisme exact par lequel la couverture nominale aide LightGBM (a) ; l'apport de
  l'historique de la cellule (c) ; un éventuel changement de codage des zones lié à Risk Rating 2.0
  (VC3, côté polices non vérifié) ; le rôle propre de α dans le niveau de M3 (VC2).

## 8. Écarts avec `RAPPORT_MODELES.md` (non modifié)

1. **§ 6 (H-c) et § 7.3** attribuent le retard de M2 sur M1 à la couverture nominale. L'ablation montre
   que **l'essentiel de ce retard vient des historiques**. Sans couverture (G1), M2 reste loin de M1 :
   +0,15 % contre +7,09 % en brut, −0,98 % contre +10,61 % après recalage. Sans historiques (G3), il
   remonte à +7,89 % après recalage. L'effet de niveau de la couverture (facteur 0,904) est réel, mais il
   ne suffit pas à expliquer l'écart.
2. **§ 7.2** : VC2 étaye la partie « l'estimateur NB2 n'impose pas l'égalité des totaux ». En revanche,
   le rôle attribué à « α ≈ 6 élevé » n'est pas démontré : la constante seule donne déjà Σμ/Σy = 2,64.
3. **§ 6 (H-a)** : le gain de M4 dépend presque entièrement de la couverture nominale (L1 −5,40 % brut).
   La phrase « le gain de M4 résiste après recalage » est exacte, mais doit être lue avec cette réserve.
4. **§ 7.4** (l'historique du comté nuit au test) : **confirmé** par L2.
