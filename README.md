# Data_science_UNIL_Project
This is a public repo containing the project for data science and management

## Objectif

Prédire la **fréquence des sinistres** d'assurance inondation du NFIP (programme fédéral américain) dans
la Région IV de FEMA : le nombre de sinistres payés rapporté au nombre de polices en vigueur. La question
de recherche est de savoir si LightGBM (objectif de Poisson) prédit mieux cette fréquence qu'un GLM de
Poisson et qu'un GLM binomial négatif, avec l'exposition en polices-années comme offset. Entraînement sur
2010-2019, test sur 2020-2024.

État au 15/11/2026 : données nettoyées, table d'analyse par comté × zone d'inondation × année
(`EDA/ds_clean.csv`), analyse exploratoire, premiers modèles sur cette table (`Modeles/`, résultats
préliminaires) et rapport d'update. La table par secteur de recensement reste à faire. Les règles de travail du groupe sont dans [`CLAUDE.md`](CLAUDE.md).

## Structure du dépôt

```
.
├── README.md                  ce fichier
├── requirements.txt           dépendances Python (versions figées)
├── CLAUDE.md                  règles du projet (question, périodes, conventions)
├── download_nfip.py           test de téléchargement OpenFEMA (Delaware uniquement)
├── EDA/
│   ├── README.md              construction de ds_clean, conclusions de l'EDA, contenu du rapport
│   ├── build_ds_clean.py      construit ds_clean à partir des données nettoyées
│   ├── ds_clean.csv           table d'analyse : comté × zone × année, 2010-2024
│   ├── ds_clean_roles.json    rôle et définition de chaque colonne
│   ├── eda.py                 analyse exploratoire (lit ds_clean.csv)
│   └── figures/               figures eda_1 à eda_6, tableaux et chiffres clés
├── quarto_report/
│   ├── README.md              comment compiler le rapport
│   ├── report.qmd, sections/  rapport d'update (version à rendre)
│   └── archive_v1_technical/  version précédente du rapport, plus technique
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

## Utiliser les données

Tout ce qu'il faut est versionné : un `git pull` suffit, pas besoin des fichiers bruts.

```python
import pandas as pd

# Table d'analyse de la fréquence : une ligne par comté × zone d'inondation × année
ds = pd.read_csv("EDA/ds_clean.csv", dtype={"county_id": str})

# Données nettoyées d'origine : une ligne par sinistre, et l'exposition des polices
claims = pd.read_parquet("Data_cleaning/clean/claims_clean.parquet")
zone_year = pd.read_parquet("Data_cleaning/clean/zone_year.parquet")
```

- [`EDA/README.md`](EDA/README.md) : construction et colonnes de `ds_clean`, conclusions de l'EDA.
- [`Data_cleaning/clean/README.md`](Data_cleaning/clean/README.md) : colonnes, transformations et limites
  des données nettoyées.

## Ordre d'exécution (pour régénérer)

1. Placer les deux fichiers bruts `*_SE.parquet` dans `Data_cleaning/` (voir [`Data_cleaning/README.md`](Data_cleaning/README.md)).
2. Lancer, depuis la racine du dépôt :

   ```bash
   .venv/bin/python Data_cleaning/clean/clean_data.py audit
   .venv/bin/python Data_cleaning/clean/clean_data.py sentinels
   .venv/bin/python Data_cleaning/clean/clean_data.py clean
   ```

3. Vérifier les sommes de contrôle : `grep -v '^#' Data_cleaning/clean/CHECKSUMS.txt | shasum -a 256 -c -`

Les étapes suivantes ne demandent pas les fichiers bruts :

4. Table d'analyse et EDA :

   ```bash
   .venv/bin/python EDA/build_ds_clean.py   # seulement si les données nettoyées ont changé
   .venv/bin/python EDA/eda.py
   ```

5. Rapport (demande [Quarto](https://quarto.org/docs/get-started/)) :

   ```bash
   cd quarto_report && quarto render report.qmd
   ```
