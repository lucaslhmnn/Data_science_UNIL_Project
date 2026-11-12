# EDA et dataset de modélisation

## Lancer

```bash
python EDA/dsEDA.py   # crée data/claims_model.parquet à partir de claims_clean
python EDA/EDA.py     # EDA sur claims_model -> figures_v2/
```

## L'EDA

`EDA.py` produit des tableaux de statistiques et 10 figures : valeurs manquantes, évolution dans le temps,
distribution des montants, taux de paiement par catégorie, géographie, corrélations et nouvelles
variables.

Principaux constats :

- 72 % des sinistres sont payés.
- Montant payé médian : 20 000 $ ; moyenne : 51 000 $. Quelques très gros sinistres tirent la moyenne.
- 5,5 % des sinistres payés atteignent le plafond de couverture (14 % en 2005-2012, l'époque de Katrina).
- Helene, Katrina et Ian font à eux seuls 44 % des montants payés.

## Le nouveau dataset

`dsEDA.py` crée `data/claims_model.parquet` à partir de `claims_clean`. L'original n'est pas modifié, et
toutes les lignes sont gardées.

**Supprimé** : `foundation_type`, qui disait exactement la même chose que `rating_system`.

**Modifié** :

- les valeurs impossibles deviennent NA (valeur de bâtiment à 0, âge au-delà de 150 ans) ;
- `water_depth` = 99 devient NA (code de remplissage) ;
- `primary_residence` devient NA avant 2000, car l'information n'était pas saisie avant ;
- la valeur du bâtiment est revalorisée (`building_value_real`), comme les autres montants ;
- les NA des catégories (zone, comté, étages) deviennent « inconnu ».

**Signalé, sans retirer de lignes** :

- `recent_claim` : sinistres de 2025 et après, dont les dossiers peuvent être encore ouverts ;
- `paid_gt_cov` : 1 334 sinistres avec un montant payé supérieur à la couverture.

**Ajouté** :

- `coverage_ratio`, `at_cap` : part du plafond payée, et sinistre au plafond ;
- `event_group`, `major_event` : événement du sinistre, et grand ouragan ;
- `fold` : 5 groupes pour valider les modèles, sans jamais couper un même événement en deux ;
- `split` : découpage dans le temps (avant 2017 / 2017-2020 / après 2020) ;
- `building_age_missing`, `deductible_missing`, `primary_residence_missing` : valeur manquante ;
- `era`, `foundation_rr2` : variables de contrôle.

**Retiré du modèle** : `rating_system`. Il mesure surtout l'époque du sinistre et non le risque. L'effet du
temps passe par `loss_year`.

**Variables du modèle** : couverture, franchise, zone, surélévation, âge, étages, résidence principale,
comté, État et année, plus les indicatrices de valeur manquante. `water_depth` et `flood_duration` ne
servent qu'à l'analyse, car on ne les connaît qu'après le sinistre. La liste exacte est dans
`data/claims_model_roles.json`.

## Résultat

Les statistiques sont les mêmes qu'avant. La différence est qu'un GLM peut maintenant être estimé : il n'y
a plus de variables redondantes. On ne sait pas encore si les prédictions sont meilleures.

Les corrélations trompeuses ont disparu : valeur du bâtiment × année passe de 0,63 à 0,27 (c'était
l'inflation), résidence principale × année de 0,44 à 0,06 (c'était un changement de saisie).

Pour valider les modèles, utiliser `fold` en priorité, et `split` comme vérification.

## Points à surveiller

1. **Recodage des paiements manquants.** Avant 2018 environ, la plupart des sinistres non payés viennent
   de paiements NA recodés en « non payé » dans `claims_clean` (`paid_na_to_zero`). Les creux du taux de
   paiement en 1992 et 2007 viennent entièrement de ce recodage. La règle est probablement juste (dossier
   clos sans paiement), mais elle est à vérifier sur le fichier brut.
2. **Unité de `water_depth`.** Elle mélange pieds et pouces, et rien dans les données ne permet de les
   distinguer. À signaler dans le rapport si on commente la figure 7.
3. **Résidence principale.** Manquante pour 36 % des lignes (avant 2000) : le modèle doit l'utiliser avec
   son indicatrice `primary_residence_missing`.
4. **Sinistres de 2025 et après.** Dossiers possiblement encore ouverts : taux de paiement et montants
   sous-estimés. Les exclure des analyses d'évolution, ou en tenir compte.
5. **Payé supérieur à la couverture.** 1 334 sinistres (`paid_gt_cov`), et 211 marqués « payés » sans
   montant. Probables erreurs de saisie : décider s'il faut les exclure du modèle du montant.
6. **Validation.** Les plis (`fold`) ont la même taille mais pas le même contenu : chaque grand ouragan
   domine un pli. Présenter les scores comme une moyenne et un écart-type sur les 5 plis. Le découpage
   temporel (`split`) a un ensemble de test très différent (surtout Helene et Ian), donc il sert seulement
   de vérification.
7. **Plafond de couverture.** Le montant des sinistres au plafond est tronqué. Pour le modèle du montant,
   garder la couverture en variable ou modéliser le ratio payé / couverture.
8. **Variables pas encore ajoutées.** `elevationDifference`, `postFIRMConstructionIndicator`,
   `crsClassCode`, latitude et longitude sont de bons candidats pour le modèle. `dsEDA.py` les ajoute
   automatiquement si le fichier brut `Data_cleaning/NfipClaimsV3_SE.parquet` est présent.
9. **Valeur du bâtiment.** Fixée par l'expert après le sinistre : risque de fuite d'information. Elle reste
   hors du modèle tant que ce n'est pas testé.
