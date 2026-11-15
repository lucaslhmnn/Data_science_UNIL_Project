# Passages « TO FILL BY TEAM » du rapport Quarto

> 15/11/2026 · branche `modeles-premier-jet` · version `v0.1` · **Résultats provisoires et exploratoires, voir
> `STATUT_RESULTATS.md`** · aucun commit à ce stade.

**Il y a 4 passages, et non 5.** Recherche de « TO FILL BY TEAM » dans `quarto_report/report.qmd` et
`quarto_report/sections/*.qmd` le 15/11/2026 : 1 passage dans `report.qmd` et 3 dans `_data.qmd`. Le
passage sur l'IA apparaît deux fois dans le HTML rendu, ce qui explique le décompte « 5 » d'un rapport
antérieur. Aucun passage n'est modifié ici.

## 1. `quarto_report/sections/_data.qmd`, ligne 17

> **[TO FILL BY TEAM: number of tract-years in the modelling table, in total and per split, once
> `tract_year.parquet` is built]**

**Information à fournir par l'équipe.** La table secteur × année n'existe pas dans le dépôt, donc aucun
chiffre ne peut être donné.

Si l'équipe décide de rendre la mise à jour avec la table comté × zone, voici une **proposition, à
valider**, dont les chiffres doivent être insérés par code, conformément à `CLAUDE.md` :

> « Until the tract table is built, the exploratory models use `ds_clean`: `{python} ck("ds_rows")` county by
> zone by year rows, of which `{python} ck("rows_train")` training rows and `{python} ck("rows_test")` test
> rows after excluding `{python} ck("rows_excluded")` rows with a missing feature (@sec-ap). »

## 2. `quarto_report/sections/_data.qmd`, ligne 161

> **[TO FILL BY TEAM: result of the tract vintage check on Region 4, once the tract-year table is built]**

**Information à fournir par l'équipe.** Aucun contrôle des millésimes de secteurs sur la Région IV n'existe
dans les fichiers du dépôt. Rien n'est proposé.

## 3. `quarto_report/sections/_data.qmd`, ligne 168

> **[TO FILL BY TEAM: share of tract-years with zero claims, once the tract-year table is built]**

**Information à fournir par l'équipe.** La part de zéros n'est connue qu'au niveau comté × zone
(`EDA/figures/eda_key_numbers.json`, `zero_share`, déjà cité juste avant dans le même paragraphe). Rien
n'est proposé au niveau secteur.

## 4. `quarto_report/report.qmd`, ligne 150

> **[TO FILL BY TEAM: any other use of AI tools during the project (for example for the cleaning and EDA
> scripts), and confirmation that this statement follows the course policy]**

**Faits établis dans le dépôt** :
- les 6 commits de nettoyage du 12/11/2026 portent la mention « Co-Authored-By: Claude Opus 5.5 »
  (`git log`, commits `95976f9` à `c125486`) ;
- les dossiers `Modeles/`, `Modeles/complements/` et `Analyse_preliminaire/` ont été produits avec Claude
  Code (voir leurs README).

**Proposition, à valider** (première partie seulement) :

> « Claude Code (Anthropic) was also used to write the data cleaning scripts and their reports
> (`Data_cleaning/clean/`), and the exploratory models and their documentation (`Modeles/`,
> `Analyse_preliminaire/`). The team defined the decisions recorded in these files and checked the
> results. »

**Décisions et informations à fournir par l'équipe** :
- un éventuel usage de l'IA pour l'EDA (`EDA/`) : aucune trace dans le dépôt ;
- la confirmation que la déclaration respecte la politique du cours.
