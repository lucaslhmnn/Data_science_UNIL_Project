# Data_science_UNIL_Project
This is a public repo containing the project for data science and management

## Objectif

Analyser les sinistres d'assurance inondation du NFIP (programme fédéral américain) dans la Région IV de
FEMA, avec une analyse exploratoire et une analyse par zone d'inondation. Modéliser le sinistre bâtiment
en deux parties, d'abord la probabilité de paiement puis le montant payé, en comparant un GLM (logistique
et Gamma) à du gradient boosting interprété par SHAP.

## Structure du dépôt

```
.
├── README.md                  ce fichier
├── requirements.txt           dépendances Python (versions figées)
├── download_nfip.py           test de téléchargement OpenFEMA (Delaware uniquement)
└── Data_cleaning/
    ├── README.md              fichiers d'entrée : origine, emplacement, sommes de contrôle
    ├── CPI_1978_2026.xlsx     indice des prix BLS (revalorisation)
    ├── dictionary/            dictionnaire des champs OpenFEMA (tables de codes)
    ├── (fichiers bruts *_SE.parquet : non versionnés, à placer ici)
    └── clean/
        ├── README.md          guide des données nettoyées : à lire avant de modéliser
        ├── clean_data.py      script de nettoyage (audit, sentinelles, nettoyage)
        ├── claims_clean.parquet       dataset propre : une ligne par sinistre
        ├── zone_year.parquet          exposition des polices par zone × comté × année
        ├── claims_anomalies.parquet   sinistres écartés, avec leur motif
        ├── data_dictionary.csv        rôle et transformation de chaque colonne
        ├── CHECKSUMS.txt              SHA-256 des fichiers de données
        └── *_report.md, push_feasibility.md   rapports d'audit, de sentinelles et de nettoyage
```

## Sources de données

- **OpenFEMA**, jeux *FIMA NFIP Redacted Claims v3* et *FIMA NFIP Redacted Policies v3* (API v3), filtrés
  sur les États de la Région IV (AL, FL, GA, KY, MS, NC, SC, TN). Date d'extraction (`asOfDate`) :
  08/09/2026. Date d'accès à l'API, procédure d'extraction et lien de téléchargement des fichiers bruts :
  **à compléter par Lucas Lhmnn**, qui a préparé ces fichiers.

  > *This product uses the Federal Emergency Management Agency's OpenFEMA API, but is not endorsed by
  > FEMA.*

  **Les données de ce dépôt sont modifiées par le groupe et non approuvées par FEMA.**
- **BLS**, indice des prix CPI-U, série CUUR0000SA0, pour la revalorisation des montants
  (`Data_cleaning/CPI_1978_2026.xlsx`, versionné).
- **Dictionnaire des champs OpenFEMA** (tables de codes) :
  [https://www.fema.gov/api/open/v1/OpenFemaDataSetFields.csv](https://www.fema.gov/api/open/v1/OpenFemaDataSetFields.csv),
  copie versionnée dans `Data_cleaning/dictionary/`.

Origine précise et sommes de contrôle des fichiers bruts : [`Data_cleaning/README.md`](Data_cleaning/README.md).

## Installation

Python 3.12 ou plus (testé avec 3.13.0). Depuis la racine du dépôt :

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Utiliser le dataset propre

Les données nettoyées sont versionnées dans [`Data_cleaning/clean/`](Data_cleaning/clean/) : un
`git pull` suffit, pas besoin des fichiers bruts.

```python
import pandas as pd
claims = pd.read_parquet("Data_cleaning/clean/claims_clean.parquet")
```

Lire d'abord [`Data_cleaning/clean/README.md`](Data_cleaning/clean/README.md) : définitions des colonnes,
rôles (cibles, ensembles A et B), transformations et limites.

## Ordre d'exécution (pour régénérer)

1. Placer les deux fichiers bruts `*_SE.parquet` dans `Data_cleaning/` (voir [`Data_cleaning/README.md`](Data_cleaning/README.md)).
2. Lancer, depuis la racine du dépôt :

   ```bash
   .venv/bin/python Data_cleaning/clean/clean_data.py audit
   .venv/bin/python Data_cleaning/clean/clean_data.py sentinels
   .venv/bin/python Data_cleaning/clean/clean_data.py clean
   ```

3. Vérifier les sommes de contrôle : `grep -v '^#' Data_cleaning/clean/CHECKSUMS.txt | shasum -a 256 -c -`
