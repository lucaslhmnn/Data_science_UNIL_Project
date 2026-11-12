# Diagnostic des valeurs sentinelles

> Lecture seule. Généré par `clean_data.py sentinels`. Population : les lignes de `claims_clean.parquet` (maisons individuelles hors anomalies), soit 621 693 sinistres, avec les valeurs **brutes** (avant toute correction de sentinelle).

## `water_depth` (`waterDepth`)

- Lignes : 621 693 ; NA : 55 208 (8.88 %) ; min -999 ; max 993 ; moyenne 4.4 ; médiane 1.0
- Quantiles : 0.1 % = -18 ; 1 % = -6 ; 5 % = 0 ; 50 % = 1 ; 95 % = 18 ; 99 % = 99 ; 99.9 % = 280

Valeurs sentinelles suspectes :

| valeur | lignes | part |
|---|---|---|
| -999 | 1 | 0.00 % |
| 999 | 0 | 0.00 % |
| 9999 | 0 | 0.00 % |
| 99 999 | 0 | 0.00 % |
| 999 999 | 0 | 0.00 % |
| 2 147 483 647 | 0 | 0.00 % |

- Valeurs négatives autres que −999 : 19 632 (-240 : 1, -207 : 1, -204 : 1, -188 : 1, -186 : 1, -180 : 3, -176 : 1, -171 : 1, -156 : 2, -144 : 1, -138 : 1, -132 : 2, -127 : 1, -125 : 1, -120 : 2, -116 : 3, -112 : 1, -107 : 2, -106 : 1, -104 : 1, -103 : 2, -102 : 1, -100 : 1, -99 : 1, -98 : 92, -96 : 7, -95 : 1, -94 : 1, -93 : 3, -92 : 3, -91 : 1, -90 : 4, -89 : 5, -88 : 4, -87 : 5, -86 : 2, -85 : 2, -84 : 9, -82 : 4, -81 : 4, -80 : 6, -79 : 5, -78 : 4, -77 : 5, -76 : 5, -75 : 6, -74 : 3, -73 : 3, -72 : 9, -71 : 2, -69 : 2, -68 : 3, -67 : 4, -66 : 3, -65 : 2, -64 : 1, -63 : 5, -62 : 1, -61 : 1, -60 : 9, -59 : 1, -58 : 4, -57 : 4, -56 : 2, -55 : 5, -54 : 2, -53 : 2, -52 : 4, -51 : 5, -50 : 3, -49 : 1, -48 : 16, -47 : 3, -46 : 3, -45 : 5, -44 : 5, -43 : 6, -42 : 8, -41 : 3, -40 : 9, -39 : 2, -38 : 6, -37 : 1, -36 : 17, -35 : 3, -34 : 8, -33 : 8, -32 : 9, -30 : 15, -29 : 3, -28 : 13, -27 : 3, -26 : 11, -25 : 4, -24 : 40, -23 : 6, -22 : 13, -21 : 6, -20 : 23, -19 : 6, -18 : 33, -17 : 7, -16 : 25, -15 : 18, -14 : 34, -13 : 27, -12 : 85, -11 : 59, -10 : 284, -9 : 397, -8 : 1 143, -7 : 1 759, -6 : 1 553, -5 : 1 124, -4 : 1 285, -3 : 1 297, -2 : 2 059, -1 : 7 896)
- Zéros : 252 104 (40.55 % des lignes, 44.50 % des valeurs renseignées)
- > 300 : 437 ; > 500 : 21 ; > 900 : 8 (hors 999 : > 900 et ≠ 999 : 8)
- Valeurs > 300 : 301 (1), 310 (1), 312 (6), 320 (2), 324 (6), 325 (1), 336 (23), 339 (1), 340 (6), 341 (2), 348 (3), 360 (258), 366 (1), 372 (2), 375 (7), 376 (2), 377 (3), 378 (1), 380 (1), 396 (2), 399 (1), 400 (6), 402 (1), 416 (1), 420 (65), 432 (1), 436 (1), 444 (2), 450 (1), 480 (7), 500 (1), 528 (1), 574 (1), 576 (1), 620 (1), 700 (4), 721 (1), 800 (4), 918 (1), 926 (1), 928 (1), 949 (1), 970 (1), 993 (3)

**-999 × paid_flag** (part des sinistres de chaque statut) :

| paid_flag | lignes | total | part |
|---|---|---|---|
| False | 1 | 171746 | 0.00 % |
| True | 0 | 449947 | 0.00 % |

**-999 × loss_year** (années où la valeur apparaît) :

| loss_year | lignes | part de l'année |
|---|---|---|
| 1992 | 1 | 0.01 % |

## `flood_duration` (`floodWaterDuration`)

- Lignes : 621 693 ; NA : 128 674 (20.70 %) ; min 0 ; max 999 ; moyenne 0.6 ; médiane 0.0
- Quantiles : 0.1 % = 0 ; 1 % = 0 ; 5 % = 0 ; 50 % = 0 ; 95 % = 0 ; 99 % = 10 ; 99.9 % = 96

Valeurs sentinelles suspectes :

| valeur | lignes | part |
|---|---|---|
| -999 | 0 | 0.00 % |
| 999 | 9 | 0.00 % |
| 9999 | 0 | 0.00 % |
| 99 999 | 0 | 0.00 % |
| 999 999 | 0 | 0.00 % |
| 2 147 483 647 | 0 | 0.00 % |

- Valeurs négatives autres que −999 : 0
- Zéros : 485 401 (78.08 % des lignes, 98.45 % des valeurs renseignées)
- > 168 h : 228 ; > 720 h : 14 ; = 999 : 9 ; > 999 : 0
- Valeurs > 168 : 180 (1), 182 (1), 192 (27), 195 (1), 196 (1), 216 (16), 218 (1), 228 (1), 240 (38), 264 (20), 288 (9), 291 (1), 294 (1), 312 (2), 336 (28), 360 (6), 380 (1), 384 (2), 400 (1), 408 (4), 480 (1), 502 (1), 504 (22), 528 (4), 552 (1), 576 (2), 624 (2), 648 (2), 672 (7), 695 (1), 696 (3), 720 (6), 742 (1), 816 (1), 840 (1), 960 (1), 984 (1), 999 (9)

**999 × paid_flag** (part des sinistres de chaque statut) :

| paid_flag | lignes | total | part |
|---|---|---|---|
| False | 3 | 171746 | 0.00 % |
| True | 6 | 449947 | 0.00 % |

**999 × loss_year** (années où la valeur apparaît) :

| loss_year | lignes | part de l'année |
|---|---|---|
| 1997 | 6 | 0.07 % |
| 1998 | 1 | 0.00 % |
| 1999 | 1 | 0.00 % |
| 2002 | 1 | 0.02 % |

## `buildingPropertyValue` (`buildingPropertyValue`)

- Lignes : 621 693 ; NA : 133 759 (21.52 %) ; min 0 ; max 2142924000 ; moyenne 1 906 556.5 ; médiane 119560.0
- Quantiles : 0.1 % = 0 ; 1 % = 0 ; 5 % = 15 840 ; 50 % = 119 560 ; 95 % = 450 211 ; 99 % = 1 207 774 ; 99.9 % = 989 532 864

Valeurs sentinelles suspectes :

| valeur | lignes | part |
|---|---|---|
| -999 | 0 | 0.00 % |
| 999 | 0 | 0.00 % |
| 9999 | 0 | 0.00 % |
| 99 999 | 42 | 0.01 % |
| 999 999 | 0 | 0.00 % |
| 2 147 483 647 | 0 | 0.00 % |

- Valeurs négatives autres que −999 : 0
- Zéros : 14 685 (2.36 % des lignes, 3.01 % des valeurs renseignées)
- Exactement 2 147 483 647 : 0
- > 1 M$ (hors 2 147 483 647) : 6 273 (1.01 % des lignes)
- > 5 M$ (hors 2 147 483 647) : 1 527 (0.25 % des lignes)
- > 10 M$ (hors 2 147 483 647) : 942 (0.15 % des lignes)
- 15 plus grandes valeurs (hors 2 147 483 647) : 2 142 924 000, 2 134 394 800, 2 125 000 000, 2 101 088 000, 2 100 826 000, 2 098 200 000, 2 097 187 200, 2 072 862 000, 2 063 468 400, 2 052 325 000, 2 047 500 000, 2 040 030 000, 2 025 000 000, 2 018 221 800, 2 000 068 000
- Moyenne / médiane avec la sentinelle : 1 906 556 / 119 560 ; sans : 1 906 556 / 119 560

Structure des valeurs élevées :

| tranche | lignes | part | médiane valeur / couverture | médiane couverture | années (P10–P90) | multiples de 100 |
|---|---|---|---|---|---|---|
| [1 M$ ; 10 M$) | 5377 | 0.86 % | 6.50 | 250 000 | 1989–2024 | 23.19 % |
| [10 M$ ; 100 M$) | 185 | 0.03 % | 87.50 | 185 000 | 1989–2005 | 70.81 % |
| [100 M$ ; 1000 M$) | 289 | 0.05 % | 5 568.10 | 143 000 | 1998–2001 | 93.43 % |
| [1000 M$ ; 3000 M$) | 473 | 0.08 % | 7 085.10 | 197 000 | 1998–2000 | 99.79 % |

**Seuil proposé (appliqué dans `claims_clean.parquet` (CONFIG `property_value_max`)) : 10 M$.** Entre 1 et 10 M$, la valeur vaut en médiane ≈ 6 fois la couverture, plafonnée à 250 000 $ pour une maison : c'est plausible pour des maisons côtières chères. Au-delà, le rapport valeur / couverture explose (≈ 90 entre 10 et 100 M$, ≈ 6 000 au-delà de 100 M$). Les valeurs ≥ 100 M$ sont concentrées sur 1998–2001 et presque toutes multiples de 100 : cela évoque une erreur d'unité (cents ?) plutôt qu'une sentinelle. Mettre en NA les valeurs > 10 M$ toucherait 942 lignes (0.15 %) ; moyenne / médiane après : 176 935 / 119 296. Variante plus prudente : ≥ 100 M$ seulement (762 lignes).

**99999 × paid_flag** (part des sinistres de chaque statut) :

| paid_flag | lignes | total | part |
|---|---|---|---|
| False | 2 | 171746 | 0.00 % |
| True | 40 | 449947 | 0.01 % |

**99999 × loss_year** (années où la valeur apparaît) :

| loss_year | lignes | part de l'année |
|---|---|---|
| 1995 | 1 | 0.01 % |
| 1996 | 14 | 0.07 % |
| 1997 | 6 | 0.07 % |
| 1998 | 9 | 0.03 % |
| 1999 | 7 | 0.02 % |
| 2000 | 1 | 0.01 % |
| 2001 | 1 | 0.02 % |
| 2004 | 2 | 0.01 % |
| 2009 | 1 | 0.01 % |

## Balayage générique

Valeurs examinées : [-999, -99, -1, 999, 9999, 99999, 999999, 2147483647]. Une valeur est signalée **anormale** si elle apparaît au moins 5 fois et plus de 5 fois plus souvent que la moyenne de ses deux voisines (v − 1 et v + 1). Les versions réelles (déflatées, non entières) ne sont pas balayées : leurs sources nominales le sont.

| colonne | valeur | lignes | moyenne des voisines | anormale |
|---|---|---|---|---|
| water_depth | -999 | 1 | 0 | non |
| water_depth | -99 | 1 | 46.5 | non |
| water_depth | -1 | 7896 | 127082 | non |
| flood_duration | 999 | 9 | 0 | **oui** |
| buildingPropertyValue | 99 999 | 42 | 1276.5 | non |
| elevationDifference (non retenue) | -1 | 8100 | 24390 | non |

## Autres sentinelles détectées au balayage

- Aucune en dehors des trois sentinelles visées.
