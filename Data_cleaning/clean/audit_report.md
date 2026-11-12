# Rapport d'audit (phase 1) : sinistres et polices NFIP, Région IV

> Lecture seule. Généré par `clean_data.py audit`. Aucune ligne n'a été modifiée ni supprimée.

- Sinistres : `NfipClaimsV3_SE.parquet` : 787 274 lignes
- Polices : `NfipPoliciesV3_SE.parquet` : 31 463 858 lignes
- Date d'extraction (`asOfDate`) : sinistres 2026-09-08 00:00:00 UTC ; polices 2026-09-08 00:00:00 UTC
- Sauf mention contraire, les contrôles 4 à 8 et 10 portent sur la population filtrée `occupancyType ∈ [1, 11]` (624 268 sinistres).

## 1. Colonnes requises, types, valeurs manquantes, dates

Toutes les colonnes requises sont présentes dans les deux fichiers. Les colonnes marquées *(audit)* sont lues uniquement pour les contrôles.

### Sinistres (fichier complet)

| colonne | type | NA | % NA |
|---|---|---|---|
| id | BIGINT | 0 | 0.00 |
| state | VARCHAR | 0 | 0.00 |
| dateOfLoss | DATE | 0 | 0.00 |
| yearOfLoss | SMALLINT | 0 | 0.00 |
| occupancyType | SMALLINT | 119 | 0.02 |
| amountPaidOnBuildingClaim | DECIMAL(12,2) | 187 431 | 23.81 |
| totalBuildingInsuranceCoverage | INTEGER | 4 | 0.00 |
| buildingDeductibleCode | VARCHAR | 44 919 | 5.71 |
| floodZoneCurrent | VARCHAR | 508 990 | 64.65 |
| elevationDifference | INTEGER | 466 237 | 59.22 |
| foundationType | VARCHAR | 0 | 0.00 |
| elevatedBuildingIndicator | BOOLEAN | 0 | 0.00 |
| originalConstructionDate | DATE | 1665 | 0.21 |
| numberOfFloorsInTheInsuredBuilding | SMALLINT | 3313 | 0.42 |
| primaryResidenceIndicator | BOOLEAN | 0 | 0.00 |
| countyCode | VARCHAR | 5681 | 0.72 |
| waterDepth | SMALLINT | 73 030 | 9.28 |
| floodWaterDuration | SMALLINT | 173 569 | 22.05 |
| floodEvent | VARCHAR | 180 634 | 22.94 |
| buildingPropertyValue | INTEGER | 186 599 | 23.70 |
| latitude *(audit)* | DECIMAL(9,1) | 6754 | 0.86 |
| longitude *(audit)* | DECIMAL(9,1) | 6754 | 0.86 |
| asOfDate *(audit)* | TIMESTAMP WITH TIME ZONE | 0 | 0.00 |
| ratedFloodZone *(audit)* | VARCHAR | 16 506 | 2.10 |
| netBuildingPaymentAmount *(audit)* | DECIMAL(12,2) | 0 | 0.00 |
| nonPaymentReasonBuilding *(audit)* | VARCHAR | 579 192 | 73.57 |
| mostRecentPaymentDate *(audit)* | DATE | 187 431 | 23.81 |

### Polices (fichier complet)

| colonne | type | NA | % NA |
|---|---|---|---|
| id | BIGINT | 0 | 0.00 |
| propertyState | VARCHAR | 0 | 0.00 |
| censusGeoid | VARCHAR | 99 542 | 0.32 |
| occupancyType | SMALLINT | 20 | 0.00 |
| floodZoneCurrent | VARCHAR | 10 359 270 | 32.92 |
| policyEffectiveDate | DATE | 0 | 0.00 |
| policyTerminationDate | DATE | 0 | 0.00 |
| policyCount | SMALLINT | 0 | 0.00 |
| totalBuildingInsuranceCoverage | INTEGER | 0 | 0.00 |
| totalInsurancePremiumOfThePolicy | INTEGER | 0 | 0.00 |
| latitude *(audit)* | DECIMAL(9,1) | 39 627 | 0.13 |
| longitude *(audit)* | DECIMAL(9,1) | 39 627 | 0.13 |
| asOfDate *(audit)* | TIMESTAMP WITH TIME ZONE | 0 | 0.00 |
| policyTermIndicator *(audit)* | SMALLINT | 0 | 0.00 |
| endorsementEffectiveDate *(audit)* | DATE | 7 301 621 | 23.21 |
| cancellationDateOfFloodPolicy *(audit)* | DATE | 30 013 728 | 95.39 |
| originalNBDate *(audit)* | DATE | 5956 | 0.02 |
| originalConstructionDate *(audit)* | DATE | 31 647 | 0.10 |
| ratedFloodZone *(audit)* | VARCHAR | 6450 | 0.02 |

- Sinistres : `dateOfLoss` de 1978-01-01 à 2026-09-06 ; `originalConstructionDate` de 1069-01-01 à 2026-03-17.
- Polices : `policyEffectiveDate` de 2009-01-01 à 2027-07-17 ; `policyTerminationDate` de 0001-01-01 à 2029-10-02.

## 2. Région IV : États, FIPS, coordonnées

### Sinistres (`state`)

| etat | lignes | part | Région IV |
|---|---|---|---|
| FL | 448 535 | 56.97 % | oui |
| NC | 109 574 | 13.92 % | oui |
| MS | 64 568 | 8.2 % | oui |
| SC | 49 612 | 6.3 % | oui |
| AL | 44 872 | 5.7 % | oui |
| KY | 27 938 | 3.55 % | oui |
| GA | 24 474 | 3.11 % | oui |
| TN | 17 701 | 2.25 % | oui |

- (a) Attendus absents : aucun
- (b) Présents hors Région IV : aucun
- (c) Lignes concernées par (b) : 0 ; État manquant : 0

### Polices (`propertyState`)

| etat | lignes | part | Région IV |
|---|---|---|---|
| FL | 22 377 729 | 71.12 % | oui |
| SC | 2 715 743 | 8.63 % | oui |
| NC | 2 207 590 | 7.02 % | oui |
| GA | 1 461 299 | 4.64 % | oui |
| MS | 1 141 638 | 3.63 % | oui |
| AL | 692 411 | 2.2 % | oui |
| TN | 493 321 | 1.57 % | oui |
| KY | 374 127 | 1.19 % | oui |

- (a) Attendus absents : aucun
- (b) Présents hors Région IV : aucun
- (c) Lignes concernées par (b) : 0 ; État manquant : 0

- Sinistres : `countyCode` manquant : 5 681 ; préfixe FIPS incohérent avec `state` : 0.
- Polices : `censusGeoid` manquant : 99 542 ; préfixe FIPS incohérent avec `propertyState` : 0.

- Sinistres : coordonnées manquantes 6 754 ; hors de la boîte englobante de l'État déclaré (± 0.1°) : 172 (0.02 %).
- Polices : coordonnées manquantes 39 627 ; hors de la boîte englobante de l'État déclaré (± 0.1°) : 718 (0.00 %).

*Contrôle approximatif (boîtes rectangulaires, coordonnées arrondies à 0,1°) : un point dans la boîte n'est pas forcément dans l'État.*

## 3. Types : numériques en texte, espaces parasites, booléens

Colonnes texte (VARCHAR) parmi les colonnes requises, fichiers complets :

| fichier | colonne | non NA | convertibles en nombre | avec espaces en début/fin | vides |
|---|---|---|---|---|---|
| sinistres | state | 787 274 | 0 | 0 | 0 |
| sinistres | buildingDeductibleCode | 742 355 | 572 677 | 0 | 0 |
| sinistres | floodZoneCurrent | 278 284 | 0 | 0 | 0 |
| sinistres | foundationType | 787 274 | 787 274 | 0 | 0 |
| sinistres | countyCode | 781 593 | 781 593 | 0 | 0 |
| sinistres | floodEvent | 606 640 | 0 | 0 | 0 |
| polices | propertyState | 31 463 858 | 0 | 0 | 0 |
| polices | censusGeoid | 31 364 316 | 31 364 316 | 0 | 0 |
| polices | floodZoneCurrent | 21 104 588 | 0 | 0 | 0 |

- Booléens : `elevatedBuildingIndicator` et `primaryResidenceIndicator` sont de type BOOLEAN / BOOLEAN dans le Parquet (pas de texte "true"/"1" à convertir).
- `occupancyType` : type SMALLINT (sinistres), SMALLINT (polices). Le filtre utilise `TRY_CAST(trim(CAST(occupancyType AS VARCHAR)) AS INTEGER)`, valable en texte comme en entier.

## 4. Valeurs distinctes des colonnes codées

### `occupancyType` (sinistres, fichier complet)

| occupancyType | lignes |
|---|---|
| 1 | 442 273 |
| 11 | 181 995 |
| 4 | 37 782 |
| 3 | 32 990 |
| 2 | 26 707 |
| 15 | 18 307 |
| 18 | 16 068 |
| 16 | 8187 |
| 12 | 6873 |
| 14 | 6793 |
| 6 | 6142 |
| 13 | 2851 |
| 19 | 143 |
| NA | 119 |
| 17 | 44 |

### `buildingDeductibleCode`

| valeur | lignes | dans la table |
|---|---|---|
| 0 | 166 734 | oui |
| 1 | 121 719 | oui |
| 2 | 92 615 | oui |
| 3 | 3743 | oui |
| 4 | 742 | oui |
| 5 | 55 212 | oui |
| 9 | 19 863 | oui |
| A | 14 974 | oui |
| D | 3 | oui |
| F | 113 994 | oui |
| G | 5017 | oui |
| H | 9 | oui |
| NA | 29 643 | NA |

### `foundationType`

| valeur | lignes | dans la table |
|---|---|---|
| 0 | 442 273 | **non** |
| 1 | 111 206 | oui |
| 2 | 3075 | oui |
| 3 | 19 771 | oui |
| 4 | 14 213 | oui |
| 5 | 19 600 | oui |
| 6 | 14 130 | oui |

### `numberOfFloorsInTheInsuredBuilding`

| valeur | lignes | dans la table |
|---|---|---|
| 1 | 394 371 | oui |
| 2 | 171 282 | oui |
| 3 | 38 952 | oui |
| 4 | 4236 | oui |
| 5 | 11 945 | oui |
| 6 | 200 | oui |
| NA | 3282 | NA |

### `elevatedBuildingIndicator`

| valeur | lignes |
|---|---|
| false | 446 491 |
| true | 177 777 |

### `primaryResidenceIndicator`

| valeur | lignes |
|---|---|
| false | 251 019 |
| true | 373 249 |

Codes hors table (population filtrée) : `buildingDeductibleCode` : 0 lignes; `foundationType` : 442 273 lignes; `numberOfFloorsInTheInsuredBuilding` : 0 lignes

`foundationType` × `occupancyType` :

| occupancyType | foundationType | lignes | premier_sinistre | dernier_sinistre |
|---|---|---|---|---|
| 1 | 0 | 442 273 | 1978-01-01 00:00:00 | 2023-06-15 00:00:00 |
| 11 | 1 | 111 206 | 1985-08-31 00:00:00 | 2026-09-06 00:00:00 |
| 11 | 2 | 3075 | 1989-02-15 00:00:00 | 2026-08-13 00:00:00 |
| 11 | 3 | 19 771 | 1989-09-21 00:00:00 | 2026-09-03 00:00:00 |
| 11 | 4 | 14 213 | 1986-12-31 00:00:00 | 2026-09-01 00:00:00 |
| 11 | 5 | 19 600 | 1986-12-03 00:00:00 | 2026-08-28 00:00:00 |
| 11 | 6 | 14 130 | 1985-09-02 00:00:00 | 2026-09-02 00:00:00 |

- Le code `0` (hors table) concerne 442 273 lignes, dont 442 273 avec `occupancyType` = 1 (qui compte 442 273 lignes au total). Lecture : `occupancyType` 1 est l'ancien code « maison individuelle », 11 celui de Risk Rating 2.0, et la fondation n'est renseignée que dans le nouveau système. Le code 0 signifie donc vraisemblablement « non renseigné », pas une erreur de saisie.

### `countyCode` : longueur et zéros initiaux

| longueur | commence_par_0 | non_numerique | lignes |
|---|---|---|---|
| 5 | 35 516 | 0 | 619 737 |
| NA | 0 | 0 | 4531 |

*Les comtés d'Alabama (FIPS 01) doivent commencer par 0 : un countyCode de 4 caractères signalerait un zéro initial perdu.*

## 5. `amountPaidOnBuildingClaim`

- NA : 146 423 (23.46 %) ; zéros : 26 165 (4.19 %) ; négatifs : 34 ; > 0 : 451 646 (72.35 %)
- Min -2250000.00 ; max 500000.00 ; médiane des paiements > 0 : 11655.34

Que sont les paiements NA ? Colonnes lues pour l'audit seulement (`netBuildingPaymentAmount`, `nonPaymentReasonBuilding`, `mostRecentPaymentDate`) :

| net_nul | motif_non_paiement | sans_date_paiement | lignes |
|---|---|---|---|
| True | True | True | 139 166 |
| True | False | True | 7257 |

- 139 166 des 146 423 NA ont un motif de non-paiement, 146 423 un paiement net nul, et 0 ont une date de paiement : ce sont très vraisemblablement des dossiers clos sans paiement.

Tableau croisé paiement × `totalBuildingInsuranceCoverage` :

| paiement | couverture > 0 | couverture = 0 | couverture < 0 | couverture NA |
|---|---|---|---|---|
| <= 0 | 23 193 | 3006 | 0 | 0 |
| > 0 | 451 369 | 277 | 0 | 0 |
| NA | 145 109 | 1312 | 0 | 2 |

- Parmi les paiements NA, `buildingPropertyValue` est aussi NA pour 118 116 lignes (80.67 %).

## 6. `elevationDifference`

- Code 9999 : 0 (0.00 %) ; NA : 364 234 (58.35 %) ; autres valeurs |x| ≥ 999 : 1
- Valeurs extrêmes (implausibles pour une maison) : < −50 pieds : 21 ; > 50 pieds : 217. Elles tombent dans les classes extrêmes sans être corrigées.
- Le code 9999 n'apparaît pas dans ce fichier : les valeurs manquantes sont déjà des NA.
- Hors 9999 (260 034 valeurs) : min -1978 ; P1/P5/P10/P25/P50/P75/P90/P95/P99 = -8 / -5 / -3 / 0 / 1 / 3 / 6 / 8 / 11 ; max 987

Effectifs par valeur entre −10 et 20 (pieds, au-dessus (+) ou au-dessous (−) de la BFE) :

| valeur | lignes |
|---|---|
| -10 | 345 |
| -9 | 696 |
| -8 | 1420 |
| -7 | 2482 |
| -6 | 3742 |
| -5 | 4916 |
| -4 | 5533 |
| -3 | 6380 |
| -2 | 6841 |
| -1 | 8120 |
| 0 | 42 086 |
| 1 | 53 288 |
| 2 | 40 207 |
| 3 | 24 682 |
| 4 | 17 234 |
| 5 | 12 590 |
| 6 | 8991 |
| 7 | 6386 |
| 8 | 4745 |
| 9 | 3103 |
| 10 | 2145 |
| 11 | 1190 |
| 12 | 687 |
| 13 | 443 |
| 14 | 245 |
| 15 | 191 |
| 16 | 106 |
| 17 | 100 |
| 18 | 71 |
| 19 | 26 |
| 20 | 40 |

**Bornes proposées** `[-inf, -2, 0, 2, 4, 8, inf]` (pieds ; 0 = plancher au niveau de la BFE) :

| classe | lignes | part |
|---|---|---|
| 1. < -2 | 26 128 | 4.19 % |
| 2. [-2, 0) | 14 961 | 2.4 % |
| 3. [0, 2) | 95 374 | 15.28 % |
| 4. [2, 4) | 64 889 | 10.39 % |
| 5. [4, 8) | 45 201 | 7.24 % |
| 6. >= 8 | 13 481 | 2.16 % |
| non renseigné | 364 234 | 58.35 % |

## 7. `floodZoneCurrent`

| zone | lignes | groupe proposé |
|---|---|---|
| NA | 404 870 | autre |
| AE | 156 430 | A* |
| X | 33 123 | X |
| VE | 12 862 | V* |
| A | 5441 | A* |
| AHB | 4779 | A* |
| AH | 2842 | A* |
| A07 | 707 | A* |
| A10 | 469 | A* |
| A08 | 376 | A* |
| AOB | 339 | A* |
| C | 273 | X |
| A09 | 237 | A* |
| B | 233 | X |
| A11 | 210 | A* |
| A05 | 184 | A* |
| AO | 158 | A* |
| A06 | 131 | A* |
| A13 | 104 | A* |
| A12 | 100 | A* |
| A04 | 65 | A* |
| A14 | 46 | A* |
| A15 | 46 | A* |
| A17 | 37 | A* |
| V09 | 31 | V* |
| V12 | 31 | V* |
| A03 | 25 | A* |
| A02 | 21 | A* |
| V20 | 11 | V* |
| V13 | 10 | V* |
| V15 | 8 | V* |
| V10 | 8 | V* |
| A01 | 8 | A* |
| A16 | 8 | A* |
| A18 | 6 | A* |
| V16 | 5 | V* |
| V14 | 5 | V* |
| V05 | 4 | V* |
| V08 | 4 | V* |
| A20 | 3 | A* |
| V17 | 3 | V* |
| V18 | 3 | V* |
| V | 3 | V* |
| V21 | 3 | V* |
| AR | 2 | A* |
| A19 | 2 | A* |
| V11 | 1 | V* |
| A21 | 1 | A* |

**Regroupement proposé** : A* = zones commençant par A (A, AE, A01–A30, AH, AO, A99, AR…) ; V* = V, VE, V01–V30 ; X = X, B, C (B et C sont les anciennes appellations des zones à risque modéré ou minimal, devenues X) ; D ; autre = tout le reste.

| groupe | lignes | part |
|---|---|---|
| NA | 404 870 | 64.86 % |
| A* | 172 777 | 27.68 % |
| X | 33 629 | 5.39 % |
| V* | 12 992 | 2.08 % |

- `floodZoneCurrent` NA : 404 870 (64.86 %). Pour comparaison, `ratedFloodZone` (zone de tarification au moment de la police, *non retenue dans la liste*) : NA 13 705 (2.20 %).

Taux de NA par décennie de sinistre :

| decennie | % NA floodZoneCurrent | % NA ratedFloodZone | lignes |
|---|---|---|---|
| 1970 | 100.00 | 31.20 | 14 473 |
| 1980 | 99.20 | 9.20 | 59 366 |
| 1990 | 96.20 | 0.90 | 149 338 |
| 2000 | 89.20 | 1.00 | 142 149 |
| 2010 | 24.40 | 0.70 | 124 594 |
| 2020 | 22.80 | 0.00 | 134 348 |

- Polices filtrées : `floodZoneCurrent` NA 8 578 107 (32.41 %).

## 8. Dates, âge du bâtiment, doublons, effectifs

- `dateOfLoss` : type DATE ; NA 0 ; `yearOfLoss` NA 0 ; `yearOfLoss` ≠ année de `dateOfLoss` : 0.
- `originalConstructionDate` : NA 56 ; année > `yearOfLoss` (âge négatif) : 1 378 ; année < 1800 (implausible) : 37 815 ; âge = 0 : 3 721.

Âges négatifs les plus fréquents :

| age | lignes |
|---|---|
| -1 | 555 |
| -2 | 263 |
| -3 | 121 |
| -4 | 65 |
| -5 | 49 |
| -6 | 37 |
| -7 | 54 |
| -8 | 51 |
| -9 | 52 |
| -10 | 34 |

Dates de construction < 1800 :

| originalConstructionDate | lignes |
|---|---|
| 1069-01-01 00:00:00 | 1 |
| 1070-01-01 00:00:00 | 3 |
| 1492-10-12 00:00:00 | 37 802 |
| 1753-01-02 00:00:00 | 1 |
| 1769-01-01 00:00:00 | 1 |
| 1778-01-01 00:00:00 | 2 |
| 1791-01-01 00:00:00 | 3 |
| 1797-06-01 00:00:00 | 2 |

- 12/10/1492 (37 802 lignes, dont 37 802 en `occupancyType` = 1) est une valeur sentinelle (« date inconnue »), pas une vraie date.

- Doublons d'`id` : 0 ; `id` NA : 0.
- Lignes identiques sur les 83 autres colonnes du fichier brut : 888 lignes en trop (333 groupes).
- Indicatif : lignes payées partageant date, comté, montant payé, couverture, date de construction et valeur du bien : 723 en trop (doublons possibles, non certains).

**Effectifs** : 787 274 sinistres dans le fichier → 624 268 après `occupancyType ∈ [1, 11]` (79.29 %). `occupancyType` NA ou non entier : 119.

## 9. Polices : nature des lignes, exposition

- Après filtre bâtiment : 26 463 999 lignes sur 31 463 858 (84.11 %) ; `id` distincts : 26 463 999.
- `policyCount` > 1 : 0 lignes ; somme de `policyCount` : 26 463 999 ; `policyCount` NA ou ≤ 0 : 0.
- `endorsementEffectiveDate` renseignée : 20 341 962 (76.87 %) ; `cancellationDateOfFloodPolicy` renseignée : 1 216 940 (4.60 %).

Durée `policyTerminationDate − policyEffectiveDate` :

| duree | lignes |
|---|---|
| <= 1 an | 26 454 748 |
| 1 à 3 ans | 9116 |
| fin <= début | 135 |

`policyTermIndicator` :

| policyTermIndicator | lignes |
|---|---|
| 1 | 26 454 822 |
| 3 | 9100 |
| 2 | 27 |
| 9 | 25 |
| 0 | 12 |
| 5 | 5 |
| 4 | 4 |
| 6 | 4 |

- Double comptage potentiel (clé approchée : bloc de recensement, coordonnées, date de 1re souscription, date de construction, zone tarifée, couverture) : lignes avec mêmes dates de début et de fin : 297 481 en trop ; périodes qui chevauchent la ligne précédente du même bien : 316 894 (1.20 %).
  *Sans identifiant de police (caviardé), ce contrôle ne peut être qu'indicatif : deux maisons voisines peuvent partager la clé.*

Lignes par année de prise d'effet :

| annee_effet | lignes | fin_apres_extraction |
|---|---|---|
| 2009 | 1 702 314 | 0 |
| 2010 | 1 675 128 | 0 |
| 2011 | 1 660 149 | 0 |
| 2012 | 1 664 720 | 0 |
| 2013 | 1 695 030 | 0 |
| 2014 | 1 680 928 | 0 |
| 2015 | 1 494 316 | 0 |
| 2016 | 1 481 585 | 0 |
| 2017 | 1 500 740 | 0 |
| 2018 | 1 492 137 | 0 |
| 2019 | 1 459 113 | 0 |
| 2020 | 1 457 607 | 0 |
| 2021 | 1 412 972 | 0 |
| 2022 | 1 298 847 | 0 |
| 2023 | 1 282 507 | 1 |
| 2024 | 1 306 424 | 0 |
| 2025 | 1 279 766 | 386 111 |
| 2026 | 919 715 | 919 715 |
| 2027 | 1 | 1 |

- Date d'extraction : 2026-09-08. Prises d'effet postérieures : 79 422 ; fins postérieures : 1 305 828. Les années 2025 et 2026 (et au-delà) sont donc partielles en exposition, sous réserve du délai de saisie.

## 10. `buildingPropertyValue` (information)

- NA global : 134 450 (21.54 %).

| statut | lignes | % NA valeur | valeur médiane |
|---|---|---|---|
| non payé (0) | 26 199 | 54.09 | 125 310.00 |
| paiement NA | 146 423 | 80.67 | 101 346.00 |
| payé | 451 646 | 0.48 | 120 251.00 |

*Si les NA de la valeur du bien coïncident avec les dossiers non payés, la variable est renseignée par l'expert lors du sinistre (risque de fuite), ce que le test prévu devra trancher.*

## 11. Fichier CPI (`CPI_1978_2026.xlsx`)

- Feuilles : ['BLS Data Series']
- En-têtes de métadonnées : Consumer Price Index for All Urban Consumers (CPI-U); Original Data Value; Series Id = CUUR0000SA0; Not Seasonally Adjusted; Series Title = All items in U.S. city average, all urban consumers, not seasonally adjusted; Area = U.S. city average; Item = All items; Base Period = 1982-84=100; Years = 1978 to 2026
- Ligne d'en-tête du tableau (ligne 12) : ['Year', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'HALF1', 'HALF2']
- Format **large** : une ligne par année, une colonne par mois (+ moyennes semestrielles HALF1/HALF2, à ignorer).
- Unité : indice, base 1982-84 = 100 (pas un taux d'inflation).
- Premier mois : 1978-01 ; dernier mois : 2026-10 (CPI = 337.511).
- Mois manquants entre le premier et le dernier : 2025-10 (valeur brute '').
- Sinistres filtrés dont le mois de `dateOfLoss` n'a pas de CPI : 271 (mois manquants) + 0 (avant 1978-01) + 0 (après 2026-10).

## Conclusion

**Les données correspondent à la Région IV** : les deux fichiers contiennent exactement AL, FL, GA, KY, MS, NC, SC, TN, sans État hors Région IV ni État manquant.

### Points nécessitant une décision avant la phase 2

1. `foundationType` = 0 (hors table) pour 442 273 lignes (70.85 %), soit exactement tous les sinistres `occupancyType` = 1 (ancien système). Les écarter par défaut supprimerait 71 % du jeu : traiter 0 comme « non renseigné » ?
2. 34 montants payés négatifs.
3. 146 423 `amountPaidOnBuildingClaim` NA (23.46 %). Selon la consigne, paid_flag = NA, ce qui retire du modèle logistique la quasi-totalité des sinistres non payés (146 423 NA contre 26 165 zéros). Or 139 166 de ces NA portent un motif de non-paiement : les traiter comme paid_flag = 0 ?
4. 277 sinistres payés avec une couverture bâtiment nulle.
5. `elevationDifference` non renseignée (9999 ou NA) pour 58.35 % des sinistres.
6. `floodZoneCurrent` est NA pour 64.86 % des sinistres filtrés (contre 2.20 % pour `ratedFloodZone`) : flood_zone_group serait majoritairement manquant.
7. 1 378 âges négatifs (construction postérieure au sinistre).
8. 37 815 dates de construction antérieures à 1800, dont la sentinelle 1492-10-12 : building_age serait d'environ 500 ans. À mettre en NA (et compter) ou écarter ?
9. 888 sinistres en double exact (hors `id`).
10. CPI manquant pour 2025-10 : 271 sinistres concernés ; l'assert « tous les mois trouvés » échouerait.
