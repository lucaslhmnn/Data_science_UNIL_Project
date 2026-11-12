# Rapport de nettoyage (phase 2) : sinistres NFIP, Région IV

> Généré par `clean_data.py clean`. Fichiers bruts lus en lecture seule. Audit préalable : `audit_report.md`.

## 1. Paramètres retenus (CONFIG)

- Sinistres : `NfipClaimsV3_SE.parquet` ; polices : `NfipPoliciesV3_SE.parquet` ; CPI : `CPI_1978_2026.xlsx`.
- Filtre bâtiment : `occupancyType ∈ [1, 11]` (maisons individuelles).
- Système de tarification (`rating_system`) : {1: 'ancien (1)', 11: 'Risk Rating 2.0 (11)'} : les codes à 2 chiffres sont ceux de Risk Rating 2.0 (dictionnaire OpenFEMA v3).
- Zones : colonne `ratedFloodZone` (sinistres) et `ratedFloodZone` (polices). Regroupement :
  - A* : A, AE, A99, AH, AHB, AO, AOB, AR, ARE, ARH, ARO, ARA, A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11, A12, A13, A14, A15, A16, A17, A18, A19, A20, A21, A22, A23, A24, A25, A26, A27, A28, A29, A30, A01, A02, A03, A04, A05, A06, A07, A08, A09
  - V* : V, VE, V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12, V13, V14, V15, V16, V17, V18, V19, V20, V21, V22, V23, V24, V25, V26, V27, V28, V29, V30, V01, V02, V03, V04, V05, V06, V07, V08, V09
  - X : X, B, C
  - D : D
  - autre : tout autre code non manquant ; NA reste NA.
- Franchises : {'0': 500, '1': 1000, '2': 2000, '3': 3000, '4': 4000, '5': 5000, '9': 750, 'A': 10000, 'B': 15000, 'C': 20000, 'D': 25000, 'E': 50000, 'F': 1250, 'G': 1500, 'H': 200}.
- CPI : série **CUUR0000SA0** (All items in U.S. city average, all urban consumers, not seasonally adjusted), base 1982-84=100. **CPI_base = 2026-10 (337.511)**. Mois tolérés sans CPI : ['2025-10'].
- Dates de construction inutilisables (→ `building_age` NA) : sentinelles ['1492-10-12'] et années < 1700.
- `elevationDifference` abandonnée (58 % de NA, décision 10) : pas de `elevation_band`.
- `paid_flag` : paiement NA avec paiement net nul → faux (dossier clos sans paiement), signalé par `paid_na_to_zero`.

## 2. Effectifs à chaque étape

| étape | lignes |
|---|---|
| Fichier brut | 787 274 |
| occupancyType ∈ [1, 11] | 624 268 |
| Lignes écartées (anomalies) | 2575 |
| **claims_clean.parquet** | 621 693 |

`occupancyType` NA ou non entier dans le fichier brut : 119 (exclues par le filtre).

## 3. Anomalies écartées → `claims_anomalies.parquet`

Une ligne peut cumuler plusieurs motifs. Le fichier contient toutes les colonnes brutes + `motif`.

| motif | lignes |
|---|---|
| paiement négatif | 34 |
| âge négatif | 1378 |
| doublon exact | 888 |
| paiement sans couverture | 277 |
| code hors table (franchise) | 0 |
| code hors table (fondation) | 0 |
| code hors table (étages) | 0 |

Combinaisons de motifs :

| motif | lignes |
|---|---|
| âge négatif | 1376 |
| doublon exact | 888 |
| paiement sans couverture | 275 |
| paiement négatif | 34 |
| âge négatif; paiement sans couverture | 2 |

*Montants négatifs : selon le dictionnaire v3, ils correspondent à des chèques non encaissés puis réémis. Doublons exacts : la ligne au plus petit `id` est conservée.*

## 4. Recodages et valeurs manquantes signalés

- `paid_flag` : vrai 449 947, faux 171 746 (dont 145 628 issus d'un paiement NA avec net nul), NA 0.
- `foundation_type` = « non renseigné » (code 0) : 440 133 lignes ; toutes en `rating_system` = ancien : 440 133.
- `building_age` NA : 37 814, dont date manquante 56, sentinelle 1492-10-12 37 754, année < 1700 (hors sentinelle) 4.
- Sinistres sans CPI (mois 2025-10) : 271 → `paid_building_real`, `building_coverage_real`, `deductible_amount_real` NA.
- Codes de zone classés « autre » : AA (3) (absents du dictionnaire v3).
- `flood_zone_group` NA (`ratedFloodZone` manquant) : 13 673.

| flood_zone_group | lignes |
|---|---|
| A* | 463 535 |
| X | 109 112 |
| V* | 34 601 |
| NA | 13 673 |
| D | 769 |
| autre | 3 |

- `rating_system` : ancien (1) 440 133, Risk Rating 2.0 (11) 181 560.
- `loss_month_period` est stocké en `period[M]` pandas : pandas le relit tel quel, mais DuckDB ou R n'y voient qu'un entier (mois depuis 1970).

## 4 bis. Valeurs sentinelles → NA (hypothèses non documentées par FEMA)

Diagnostic détaillé : `sentinel_report.md`. Aucune ligne supprimée.

| colonne | code | appliquée | remplacés par NA | NA avant | NA après | % NA après | min avant | max avant | min après | max après | moyenne avant | moyenne après | médiane avant | médiane après |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| water_depth | -999 | oui | 1 | 55 208 | 55 209 | 8.88 % | -999 | 993 | -240 | 993 | 4.40 | 4.40 | 1.00 | 1.00 |
| flood_duration | 999 | oui | 9 | 128 674 | 128 683 | 20.70 % | 0 | 999 | 0 | 984 | 0.60 | 0.60 | 0.00 | 0.00 |
| buildingPropertyValue | 2147483647 | **non** | 0 | 133 759 | 133 759 | 21.52 % | 0 | 2 142 924 000 | 0 | 2 142 924 000 | 1 906 556.50 | 1 906 556.50 | 119 560.00 | 119 560.00 |
| buildingPropertyValue (seuil) | > 10 000 000 | oui | 942 | 133 759 | 134 701 | 21.67 % | 0 | 2 142 924 000 | 0 | 10 000 000 | 1 906 556.50 | 176 935.00 | 119 560.00 | 119 296.00 |

- `water_depth` : 19 632 valeurs négatives conservées (non modifiées) : -240 (1), -207 (1), -204 (1), -188 (1), -186 (1), -180 (3), -176 (1), -171 (1), -156 (2), -144 (1), -138 (1), -132 (2), -127 (1), -125 (1), -120 (2), -116 (3), -112 (1), -107 (2), -106 (1), -104 (1), -103 (2), -102 (1), -100 (1), -99 (1), -98 (92), -96 (7), -95 (1), -94 (1), -93 (3), -92 (3), -91 (1), -90 (4), -89 (5), -88 (4), -87 (5), -86 (2), -85 (2), -84 (9), -82 (4), -81 (4), -80 (6), -79 (5), -78 (4), -77 (5), -76 (5), -75 (6), -74 (3), -73 (3), -72 (9), -71 (2), -69 (2), -68 (3), -67 (4), -66 (3), -65 (2), -64 (1), -63 (5), -62 (1), -61 (1), -60 (9), -59 (1), -58 (4), -57 (4), -56 (2), -55 (5), -54 (2), -53 (2), -52 (4), -51 (5), -50 (3), -49 (1), -48 (16), -47 (3), -46 (3), -45 (5), -44 (5), -43 (6), -42 (8), -41 (3), -40 (9), -39 (2), -38 (6), -37 (1), -36 (17), -35 (3), -34 (8), -33 (8), -32 (9), -30 (15), -29 (3), -28 (13), -27 (3), -26 (11), -25 (4), -24 (40), -23 (6), -22 (13), -21 (6), -20 (23), -19 (6), -18 (33), -17 (7), -16 (25), -15 (18), -14 (34), -13 (27), -12 (85), -11 (59), -10 (284), -9 (397), -8 (1 143), -7 (1 759), -6 (1 553), -5 (1 124), -4 (1 285), -3 (1 297), -2 (2 059), -1 (7 896). Aucune conversion pouces / pieds, aucun plafonnement : le dictionnaire v3 indique une unité mixte possible.
- `flood_duration` : zéros conservés : 485 401 (98.46 % des valeurs renseignées, 78.08 % des lignes). Un zéro peut signifier « non renseigné », mais ce n'est pas démontré.
- `buildingPropertyValue` : règle [2147483647] → NA **non appliquée** : la valeur apparaît 0 fois (seuil 10). Les valeurs extrêmes (jusqu'à ≈ 2,14 milliards) ne sont pas ce code.
- `buildingPropertyValue` : **seuil appliqué : valeurs > 10 000 000 $ → NA** (hypothèse non documentée par FEMA, CONFIG `property_value_max`) : 942 valeurs remplacées (0.15 % des lignes). Moyenne 1 906 556 → 176 935 ; médiane 119 560 → 119 296 ; max 2 142 924 000 → 10 000 000. Motif : au-delà de 10 M$ le rapport valeur / couverture explose (≈ 90 à ≈ 7 000) et les valeurs ≥ 100 M$ (1998–2001, multiples de 100) évoquent une erreur d'unité ; détail dans `sentinel_report.md`.
- `buildingPropertyValue` après correction : valeurs > 1 M$ : 5 331 ; > 5 M$ : 585 ; > 10 M$ : 0. La valeur 99 999 (42 lignes) reste suspecte mais n'est pas modifiée.

## 5. Valeurs manquantes par colonne finale

| colonne | type | NA | % NA |
|---|---|---|---|
| paid_flag | boolean | 0 | 0.00 |
| paid_building_real | Float64 | 171 957 | 27.66 |
| building_coverage | Int64 | 2 | 0.00 |
| deductible_amount | Int64 | 29 533 | 4.75 |
| flood_zone_group | category | 13 673 | 2.20 |
| foundation_type | category | 0 | 0.00 |
| elevated_building | boolean | 0 | 0.00 |
| building_age | Int64 | 37 814 | 6.08 |
| n_floors | category | 3267 | 0.53 |
| primary_residence | boolean | 0 | 0.00 |
| county_fips | category | 4513 | 0.73 |
| loss_year | Int64 | 0 | 0.00 |
| rating_system | category | 0 | 0.00 |
| water_depth | Int64 | 55 209 | 8.88 |
| flood_duration | Int64 | 128 683 | 20.70 |
| floodEvent | category | 142 184 | 22.87 |
| building_coverage_real | Float64 | 273 | 0.04 |
| deductible_amount_real | Float64 | 29 804 | 4.79 |
| buildingPropertyValue | Int64 | 134 701 | 21.67 |
| state | category | 0 | 0.00 |
| loss_month_period | period[M] | 0 | 0.00 |
| id | Int64 | 0 | 0.00 |
| paid_na_to_zero | boolean | 0 | 0.00 |

## 6. Rappel des contrôles de la phase 1

- Région IV : exactement AL, FL, GA, KY, MS, NC, SC, TN dans les deux fichiers ; préfixes FIPS cohérents.
- Aucune `dateOfLoss` manquante ; `yearOfLoss` = année de `dateOfLoss` partout.
- Pas d'espaces parasites ; booléens déjà typés BOOLEAN ; `countyCode` sur 5 caractères.
- Détail complet : `audit_report.md`.

## 7. Polices → `zone_year.parquet`

- Lignes de police après filtre bâtiment : 26 463 999 ; écartées de l'exposition car fin ≤ début : 135 ; `id` répétés : 0 ; `policyCount` ≠ 1 : 0.
- Zone NA : 6 313 lignes ; comté NA (`censusGeoid` manquant) : 52 668 lignes. Ces lignes sont gardées avec une clé NA.
- Résultat : 30 253 cellules zone × comté × année ; 26 478 054 polices-années.
- **Exposition** : chaque ligne est répartie sur les années civiles couvertes au prorata des jours (`policy_years` = policyCount × jours / 365,25 ; prime acquise = prime × jours / durée du contrat). Les totaux sont conservés (contrôles ci-dessous).
- **Transactions et double comptage** : un `id` par ligne, 0 répété ; `policyCount` ≠ 1 : 0 ligne(s) ; 99.97 % des contrats durent au plus un an. Selon le dictionnaire, `policyTerminationDate` intègre déjà les résiliations (« cancelled or lapsed »), donc l'exposition n'a pas besoin d'être tronquée. Contrôle indicatif sans identifiant de police : 187 305 lignes identiques sur 12 attributs du bien et du contrat et sur les mêmes dates (192 395 polices-années, 0.73 % du total). C'est un majorant du double comptage, car des maisons voisines identiques sont possibles. Rien n'a été retiré.
- **Prime** : `totalInsurancePremiumOfThePolicy`. Lecture du dictionnaire v3 : `policyCost` = « calculated premium + reserve fund assessment + federal policy fee + HFIAA surcharge », donc la prime ne comprend *a priori* ni frais ni surcharges ; et « negative values indicate a refund ». À confirmer par le groupe. Primes négatives : 115 lignes (-121 500 $), conservées.
- Années de sinistre : 1978–2026 ; années d'exposition : 2009–2028 (prises d'effet 2009-01-01 → 2027-07-17, fins jusqu'au 2028-07-17).
- Années de sinistre sans exposition : 1978–2008 (31 années, 354 707 sinistres).
- Années marquées partielles : 2009 (troncature à gauche : contrats ayant pris effet avant le 2009-01-01 absents du fichier); 2026 (postérieure à l'extraction du 2026-09-08); 2027 (postérieure à l'extraction du 2026-09-08); 2028 (postérieure à l'extraction du 2026-09-08).

## 8. Contrôles automatiques (tous réussis)

- ✅ aucune colonne hors liste dans claims_clean.parquet
- ✅ pas de paid_building_real quand paid_flag = 0
- ✅ pas de paid_building_real quand paid_flag est NA
- ✅ aucun montant négatif dans paid_building_real
- ✅ aucun montant négatif dans building_coverage
- ✅ aucun montant négatif dans deductible_amount
- ✅ aucun montant négatif dans building_coverage_real
- ✅ aucun montant négatif dans deductible_amount_real
- ✅ building_age >= 0
- ✅ tous les mois de sinistre ont un CPI (hors mois déclarés manquants dans CONFIG)
- ✅ codes de franchise tous dans la table
- ✅ codes de fondation tous dans la table (+ code 0)
- ✅ codes d'étages tous dans la table
- ✅ rating_system défini pour toutes les lignes
- ✅ county_fips sur 5 chiffres
- ✅ id unique
- ✅ États tous dans la Région IV
- ✅ lignes filtrées = dataset final + anomalies
- ✅ claims_anomalies.parquet contient toutes les lignes écartées
- ✅ polices-années conservées par la répartition en années civiles
- ✅ prime totale conservée par la répartition en années civiles
- ✅ id de police unique (pas de ligne répétée)
- ✅ plus de -999 dans water_depth
- ✅ plus de 999 dans flood_duration
- ✅ plus de buildingPropertyValue > 10 000 000 $
- ✅ la correction des sentinelles ne supprime aucune ligne
- ✅ nombre de lignes de claims_clean.parquet identique à la version précédente (621 693)
