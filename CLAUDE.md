# NFIP flood frequency project (update due 16 Nov)
Goal: does LightGBM (Poisson) beat Poisson/NB GLM for flood claim FREQUENCY at census tract x year?
Train 2010-2019, test 2020-2024 (2009 and 2025+ dropped: incomplete exposure or open claims).
Offset = exposure in policy-years. Target = claims with a positive BUILDING paid amount.
Status (15 Nov): tract table not built yet. The update uses EDA/ds_clean.csv, the same kind of table
at county x flood zone x year (built by EDA/build_ds_clean.py, columns in EDA/ds_clean_roles.json).

## Rules
- Course template (in repo) defines report structure. Never change its section order.
- Every number in the report comes from code output. Never write metrics by hand.
- Fixed seeds. No use of future information. `year` is NOT a model feature.
- Check OpenFEMA data dictionary for real field names. Never guess.
- No em dashes in any prose. English only.
- Raw data never committed.

## Data contract: data/processed/tract_year.parquet
tract_id (str, 11 digits), year (int), state (str), n_claims (int), exposure_years (float),
n_policies (float), plus aggregated policy features (e.g. mean building coverage, mean deductible,
share in SFHA, share pre-FIRM, share single-family) and hist_claims_1990_2008 (int).
A 50k-row sample with the same schema: data/sample/tract_year_sample.parquet.

## File ownership (avoid merge conflicts)
A: src/data.py, src/features.py, data/*   B: EDA/* (eda.py, build_ds_clean.py, ds_clean.csv, figures/eda_*)
C: src/models.py, src/evaluate.py, results/*
D/E: the .qmd only