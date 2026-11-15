<!-- tab_ap_volumes | Data volumes | sources : Data_cleaning/clean/cleaning_report.md, EDA/ds_clean_roles.json, Modeles/resultats/preparation.json, Modeles/resultats/ajustement_payes.json | statut : [Établi] | v0.1, 15/11/2026 ; résultats provisoires et exploratoires, voir STATUT_RESULTATS.md -->
**Data volumes** [Établi]

Sources : `Data_cleaning/clean/cleaning_report.md`, `EDA/ds_clean_roles.json`, `Modeles/resultats/preparation.json`, `Modeles/resultats/ajustement_payes.json`

| Step | Count |
|---|---|
| Raw claims, FEMA Region 4 | 787,274 |
| Single-family homes (occupancyType 1 or 11) | 624,268 |
| Set aside as anomalies | 2,575 |
| Cleaned claims (claims_clean) | 621,693 |
| Analysis table ds_clean: county x zone x year rows | 22,485 |
| Rows used by the models (missing feature excluded) | 22,472 |
| Training rows 2010-2019 | 14,999 |
| Test rows 2020-2024 | 7,473 |
