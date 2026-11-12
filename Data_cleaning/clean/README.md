# Données nettoyées : sinistres NFIP, Région IV de FEMA

Guide pour le groupe : ce que contiennent les fichiers de ce dossier, comment ils ont été produits et ce
qu'il faut savoir avant de modéliser. Tous les chiffres viennent de `audit_report.md`,
`sentinel_report.md` et `cleaning_report.md`. Rôle et transformation de chaque colonne :
`data_dictionary.csv`.

> Source : OpenFEMA. *This product uses the Federal Emergency Management Agency's OpenFEMA API, but is
> not endorsed by FEMA.* Les données de ce dossier sont **modifiées par le groupe et non approuvées par
> FEMA**.

## 1. Fichiers

| Fichier | Contenu | Lignes |
|---|---|---:|
| `claims_clean.parquet` | **Une ligne par sinistre** (maison individuelle, hors anomalies), 23 colonnes | 621 693 |
| `zone_year.parquet` | Exposition des polices par zone d'inondation × comté × année civile, 9 colonnes | 30 253 |
| `claims_anomalies.parquet` | Sinistres écartés du dataset principal : les 84 colonnes brutes + `motif` | 2 575 |
| `data_dictionary.csv` | Une ligne par colonne finale des deux premiers fichiers : type, colonne brute, transformation, famille, rôle | – |
| `CHECKSUMS.txt` | SHA-256, taille et nombre de lignes des fichiers de données | – |
| `clean_data.py` | Le script qui produit tout ce qui précède | – |
| `audit_report.md` | Audit des fichiers bruts (phase 1, lecture seule) | – |
| `sentinel_report.md` | Diagnostic des valeurs sentinelles | – |
| `cleaning_report.md` | Effectifs, recodages, valeurs manquantes et contrôles du nettoyage | – |
| `push_feasibility.md` | Diagnostic de faisabilité du partage par GitHub (état du 12/11/2026) | – |

### `zone_year.parquet`

Une ligne = une zone (`flood_zone_group`, même regroupement que les sinistres, à partir de
`ratedFloodZone`) × un comté (`county_fips` = 5 premiers caractères de `censusGeoid`) × une année civile
(`year`), pour les maisons individuelles (`occupancyType` ∈ {1, 11}).

- `policy_years` : Σ policyCount × (jours du contrat tombant dans l'année) / 365,25. Chaque contrat est
  réparti au prorata des jours sur les années qu'il couvre.
- `building_coverage_years` : Σ couverture bâtiment × jours dans l'année / 365,25 (dollars-années,
  nominaux).
- `premium_earned` : Σ `totalInsurancePremiumOfThePolicy` × jours dans l'année / durée du contrat (prime
  acquise, nominale). D'après le dictionnaire v3, cette prime n'inclurait pas les frais et surcharges
  (`policyCost` = prime + fonds de réserve + frais fédéral + surcharge HFIAA). Cette lecture est **à
  confirmer**. 115 primes négatives (remboursements, −121 500 $ au total) sont conservées.
- `n_policy_rows` : nombre de lignes de police qui touchent l'année.
- `partial_year` / `partial_reason` : année à exposition incomplète :
  - **2009** : troncature à gauche. Le fichier ne contient que des contrats ayant pris effet à partir du
    01/01/2009, donc ceux en cours depuis 2008 manquent.
  - **2026, 2027, 2028** : postérieures à l'extraction du 08/09/2026.
- Totaux : 26 478 054 polices-années. Les clés NA sont gardées : zone NA pour 6 313 lignes de police,
  comté NA pour 52 668. 135 lignes dont la date de fin précède le début sont exclues de l'exposition.

### `claims_anomalies.parquet` : motifs

| Motif | Lignes |
|---|---:|
| âge négatif (construction postérieure à l'année du sinistre) | 1 378 |
| doublon exact (toutes colonnes identiques sauf `id` ; on garde le plus petit `id`) | 888 |
| paiement > 0 avec couverture bâtiment nulle | 277 |
| paiement négatif (chèque non encaissé puis réémis, selon le dictionnaire v3) | 34 |

Deux lignes cumulent « âge négatif » et « paiement sans couverture », d'où 2 575 lignes au total. Ce
fichier contient les colonnes géographiques fines publiées par FEMA (`reportedZipCode`, `censusGeoid`,
`latitude`, `longitude`), absentes de `claims_clean.parquet`.

## 2. Périmètre

- **États** : AL, FL, GA, KY, MS, NC, SC, TN, soit exactement la Région IV de FEMA, dans les deux fichiers
  bruts. Aucun État absent, aucun État en trop, préfixes FIPS cohérents avec l'État
  (`audit_report.md`, § 2).
- **Bâtiments** : maisons individuelles uniquement, `occupancyType` ∈ {1, 11}. 1 est l'ancien code, 11
  celui de Risk Rating 2.0. Cela fait 624 268 sinistres sur 787 274.
- **Garantie** : **bâtiment seulement**. Le contenu n'est pas modélisé.
- **Période des sinistres** : `dateOfLoss` du 01/01/1978 au 06/09/2026 (extraction du 08/09/2026).
- **Période des polices** : prises d'effet du 01/01/2009 au 17/07/2027, fins jusqu'au 17/07/2028, soit
  une exposition calculée sur 2009–2028, dont 2009 et 2026–2028 partielles.
- **Sinistres sans exposition correspondante** : 1978–2008, soit 354 707 sinistres.

## 3. Colonnes de `claims_clean.parquet`

Rôles (colonne `role` de `data_dictionary.csv`) :

- **cible** : ce qu'on modélise ;
- **ensemble A** : connu à la souscription, utilisable pour une tarification a priori ;
- **ensemble B** : intensité de l'événement, mesurée après le sinistre. **À ne pas utiliser pour une
  tarification a priori** : cette information n'existe pas au moment où l'on fixe la prime, et l'utiliser
  surestimerait le pouvoir prédictif du modèle (fuite d'information). Elle sert seulement à expliquer la
  sévérité *ex post* ;
- **groupe** : `floodEvent`, pour la validation croisée par événement, pas comme prédicteur ;
- **contrôle** : traçabilité, hors modèle.

| Colonne | Rôle | Définition | Unité / valeurs |
|---|---|---|---|
| `paid_flag` | cible | Sinistre bâtiment payé (montant > 0). Un paiement NA avec paiement net nul compte comme non payé (dossier clos sans paiement) | booléen |
| `paid_building_real` | cible | Montant payé sur le bâtiment, revalorisé ; NA si non payé | $ d'octobre 2026 |
| `building_coverage` | ensemble A | Plafond de garantie bâtiment (`totalBuildingInsuranceCoverage`) | $ nominaux |
| `deductible_amount` | ensemble A | Franchise bâtiment convertie depuis son code (table § 4) | $ nominaux |
| `flood_zone_group` | ensemble A | Zone de tarification FIRM regroupée : A*, V*, X (X, B, C), D, autre | catégorie |
| `foundation_type` | ensemble A | Type de fondation : 1 dalle, 2 sous-sol, 3 vide sanitaire, 4 à 6 surélevé (avec ou sans enclos) ; « non renseigné » = code 0 | catégorie |
| `elevated_building` | ensemble A | Bâtiment surélevé | booléen |
| `building_age` | ensemble A | Année du sinistre − année de construction | années |
| `n_floors` | ensemble A | Code d'étages : 1, 2, 3 ou plus, 4 split-level, 5 mobil-home sur fondation, 6 maison en rangée de 3 étages ou plus. **C'est un code, pas un nombre** | catégorie |
| `primary_residence` | ensemble A | Résidence principale | booléen |
| `county_fips` | ensemble A | Code FIPS du comté, 5 caractères avec les zéros initiaux | catégorie |
| `loss_year` | ensemble A | Année du sinistre | année |
| `rating_system` | ensemble A | Système de codage de la police : « ancien (1) » ou « Risk Rating 2.0 (11) » | catégorie |
| `water_depth` | ensemble B | Hauteur d'eau dans le bâtiment (`waterDepth`) | pouces, **unité mixte possible** (§ 5) |
| `flood_duration` | ensemble B | Durée de submersion (`floodWaterDuration`) | heures |
| `floodEvent` | groupe | Nom de l'événement (ouragan, tempête…) ; NA si non nommé | catégorie |
| `building_coverage_real` | ensemble A | `building_coverage` revalorisé | $ d'octobre 2026 |
| `deductible_amount_real` | ensemble A | `deductible_amount` revalorisé | $ d'octobre 2026 |
| `buildingPropertyValue` | contrôle | Valeur du bâtiment estimée par l'expert (candidat ensemble A, à tester : voir § 5) | $ nominaux |
| `state` | contrôle | État | catégorie |
| `loss_month_period` | contrôle | Mois du sinistre, clé du CPI | `period[M]` pandas |
| `id` | contrôle | Identifiant OpenFEMA de la ligne | entier |
| `paid_na_to_zero` | contrôle | Vrai si `paid_flag` a été mis à faux à partir d'un paiement NA | booléen |

Effectifs de la cible : `paid_flag` vrai pour 449 947 sinistres, faux pour 171 746 (dont 145 628 recodés
depuis un paiement NA), NA pour 0.

## 4. Transformations

- **Revalorisation (CPI)** : CPI-U du BLS, série **CUUR0000SA0** (« All items in U.S. city average, all
  urban consumers, not seasonally adjusted », base 1982-84 = 100), identifiant lu dans l'Excel. Mois de
  base **octobre 2026 (337,511)**. Montant réel = montant nominal × CPI_base / CPI(mois de `dateOfLoss`).
  **Octobre 2025 est vide dans l'Excel** : les 271 sinistres de ce mois ont des montants réels NA. Il n'y a
  pas d'interpolation.
- **Franchises** (`buildingDeductibleCode` → $) : 0 = 500, 1 = 1 000, 2 = 2 000, 3 = 3 000, 4 = 4 000,
  5 = 5 000, 9 = 750, A = 10 000, B = 15 000, C = 20 000, D = 25 000, E = 50 000, F = 1 250, G = 1 500,
  H = 200 (polices de groupe uniquement).
- **Zones** : `ratedFloodZone` (zone de tarification) plutôt que `floodZoneCurrent`, qui manquait pour
  65 % des sinistres. Le code `AA` (3 sinistres), absent du dictionnaire v3, est classé « autre ».
- **`elevationDifference`** : la règle 9999 → NA était prévue, mais le code 9999 n'apparaît pas dans les
  données (0 occurrence). La variable a été **abandonnée** (58,35 % de NA parmi les maisons
  individuelles) : il n'y a **pas de `elevation_band`** dans le dataset.
- **Âge** : `building_age` est NA si la date de construction manque (56), vaut la sentinelle 1492-10-12
  (37 754) ou précède 1700 (4).
- **Valeurs sentinelles → NA**. Ce sont **des hypothèses non documentées par FEMA**, et aucune ligne n'est
  supprimée :

  | Colonne | Règle | Appliquée | Valeurs mises en NA |
  |---|---|---|---:|
  | `water_depth` | −999 → NA | oui | 1 |
  | `flood_duration` | 999 → NA | oui | 9 |
  | `buildingPropertyValue` | 2 147 483 647 → NA | **non**, valeur absente (0 occurrence) | 0 |
  | `buildingPropertyValue` | > 10 000 000 $ → NA (erreur d'unité probable) | oui | 942 |

  Les valeurs négatives de `water_depth` (19 632, de −240 à −1) et les zéros de `flood_duration` (98,46 %
  des valeurs renseignées) sont **conservés**. Détails : `sentinel_report.md`.

## 5. Limites à lire avant de modéliser

1. **Population assurée uniquement** : seuls les biens couverts par le NFIP figurent dans les données. Ce
   n'est pas le parc immobilier.
2. **Aucune clé entre sinistres et polices** (identifiants caviardés) : on ne peut relier les deux qu'en
   agrégé (zone × comté × année), via `zone_year.parquet`.
3. **Exposition seulement à partir de 2009** : 354 707 sinistres de 1978 à 2008 n'ont pas d'exposition
   correspondante. 2009 et 2026–2028 sont partielles.
4. **Valeurs manquantes non aléatoires** :
   - `buildingPropertyValue` est NA pour **21,67 %** des sinistres. Le manque est très lié au paiement
     : 54 % de NA chez les paiements nuls, 81 % chez les paiements NA (recodés en non payés) et 0,5 %
     chez les payés, d'après `audit_report.md`, § 10.
   - `elevationDifference` manquait pour **58,35 %** des sinistres, d'où son abandon et l'absence de
     `elevation_band`.
   - Autres NA : `flood_duration` 20,70 %, `floodEvent` 22,87 %, `water_depth` 8,88 %, `building_age`
     6,08 %.
5. **`water_depth` à unité mixte** : pouces ou pieds selon le dossier, d'après le dictionnaire v3. Les
   lignes en pieds ne sont pas identifiables : rien n'a été converti. Certaines valeurs sont suspectes
   mais non corrigées : −98 (92 lignes), 360 (258) et 420 (65).
6. **Valeurs fixées par l'expert après le sinistre** : `buildingPropertyValue` et `water_depth`.
   `buildingPropertyValue` est en contrôle tant qu'un test n'a pas montré qu'on peut l'utiliser sans fuite.
   La valeur 99 999 (42 lignes) reste suspecte.
7. **Plafond et franchise** : le montant payé est borné par `building_coverage` (censure à droite) et
   n'existe qu'au-delà de la franchise (troncature à gauche). Un GLM Gamma naïf ne le prend pas en compte.
8. **Dépendance entre sinistres d'un même événement** : un même ouragan touche des milliers de biens. Il
   faut valider par `floodEvent` (validation croisée groupée) et non par tirage aléatoire des lignes.
   `floodEvent` est NA pour 22,87 % des sinistres (événements non nommés).
9. **Codage différent selon le système** : `foundation_type` est « non renseigné » pour les 440 133
   sinistres codés dans l'ancien système. Il n'est donc informatif que pour Risk Rating 2.0.

## 6. Origine du dictionnaire v3

Les tables de codes (fondations, étages, zones, occupations, signification des montants négatifs, unités)
proviennent du fichier des champs OpenFEMA, versionné dans `Data_cleaning/dictionary/OpenFemaDataSetFields.csv`.
Il a été téléchargé le 12/11/2026 depuis
[https://www.fema.gov/api/open/v1/OpenFemaDataSetFields.csv](https://www.fema.gov/api/open/v1/OpenFemaDataSetFields.csv).
**Le groupe n'a pas confirmé l'origine officielle de ce fichier**, et toutes les tables de codes en
dépendent.

## 7. Charger les données

```python
import pandas as pd

claims    = pd.read_parquet("Data_cleaning/clean/claims_clean.parquet")      # 621 693 × 23
zone_year = pd.read_parquet("Data_cleaning/clean/zone_year.parquet")         # 30 253 × 9
anomalies = pd.read_parquet("Data_cleaning/clean/claims_anomalies.parquet")  # 2 575 × 85
```

Les types sont conservés (catégories, booléens et entiers nullables). `loss_month_period` est un
`period[M]` pandas ; dans R ou DuckDB, il apparaît comme un entier (mois depuis 1970).

## 8. Régénérer

1. Placer les deux fichiers bruts dans `Data_cleaning/` (voir `Data_cleaning/README.md`) :
   `NfipClaimsV3_SE.parquet` et `NfipPoliciesV3_SE.parquet`. L'Excel du CPI est déjà dans le dépôt.
2. Depuis la racine du dépôt :

   ```bash
   .venv/bin/python Data_cleaning/clean/clean_data.py audit      # écrit audit_report.md
   .venv/bin/python Data_cleaning/clean/clean_data.py sentinels  # écrit sentinel_report.md
   .venv/bin/python Data_cleaning/clean/clean_data.py clean      # écrit les parquet, le dictionnaire, cleaning_report.md
   ```

   Si un fichier d'entrée manque, le script s'arrête en indiquant lequel et où le placer.
3. Mesures du 12/11/2026 sur un Apple M3 (8 cœurs, 16 Go), fichiers en cache : `audit` 6,3 s (pic
   mémoire ≈ 2,8 Gio), `sentinels` 1,6 s (≈ 1,2 Gio), `clean` 5,8 s (≈ 3,7 Gio).
4. Vérifier : `grep -v '^#' Data_cleaning/clean/CHECKSUMS.txt | shasum -a 256 -c -`. Les sommes
   SHA-256 vérifient que les fichiers clonés ou téléchargés sont intacts. **Après une régénération,
   celles de `claims_clean.parquet` et `zone_year.parquet` ne correspondent plus**, même avec les mêmes
   fichiers bruts (constaté le 12/11/2026) : le contenu est identique, mais l'ordre des lignes de
   `claims_clean` varie (lecture parallèle de DuckDB), et les sommes de `zone_year` diffèrent d'environ
   1e-15 en relatif. Pour comparer deux versions, trier par `id` (ou par zone × comté × année) et comparer
   les valeurs, pas les octets.

## 9. Version

- Générée le **12/11/2026** par `clean_data.py` au commit **`95976f9`**
  (`95976f9165e36073738b2243aff0b21e3183578d`).
- `claims_clean.parquet` : 621 693 lignes ; `zone_year.parquet` : 30 253 ; `claims_anomalies.parquet` :
  2 575.
- Sommes SHA-256 : `CHECKSUMS.txt`.
- Chaque nouvelle version des parquet ajoute environ 16 Mio à l'historique Git : ne les recommiter que
  pour une version validée par le groupe.
