# NFIP flood frequency project (update due 16 Nov)
Goal: does LightGBM (Poisson) beat Poisson/NB GLM for flood claim FREQUENCY at census tract x year?
Train 2009-2019, test 2020-2024 (drop incomplete last year). Offset = exposure in policy-years.

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
A: src/data.py, src/features.py, data/*   B: src/eda.py, figures/eda_*   C: src/models.py, src/evaluate.py, results/*
D/E: the .qmd only