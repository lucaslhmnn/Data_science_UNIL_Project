"""
Build the COUNTY x year modelling table for the claim frequency analysis.

Output
------
  data/processed/county_year.parquet       one row per county x year, 2010-2024
  data/processed/county_year_roles.json    role of each column (target, offset, ...)

Same layout as the tract table of CLAUDE.md (data/processed/tract_year.parquet), one
geographic level higher, with extra control columns. It is built only from files
already in the repository, so anyone can regenerate it in a few seconds:
  - Data_cleaning/clean/claims_clean.parquet  one row per claim (single-family homes)
  - Data_cleaning/clean/zone_year.parquet     policy exposure by flood zone x county x year

Definitions
-----------
  n_claims        claims with a positive building paid amount (target)
  exposure_years  policy-years in force (offset: log(exposure_years))
  Features are known at the start of the year and contain no year effect:
  share_sfha, share_v, share_x, mean_coverage, hist_claims_1990_2008, hist_per_1000.
  Pricing variables (premiums) are left out: they reflect the insurer's rating, not
  the insured risk (see quarto_report/sections/_data.qmd).
  Controls are for description and checks only, never model inputs.

Run from the repository root:  python src/build_county_year.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "Data_cleaning" / "clean" / "claims_clean.parquet"
EXPO = ROOT / "Data_cleaning" / "clean" / "zone_year.parquet"
OUT_DIR = ROOT / "data" / "processed"
OUT = OUT_DIR / "county_year.parquet"
ROLES = OUT_DIR / "county_year_roles.json"

TRAIN = (2010, 2019)
TEST = (2020, 2024)
Y0, Y1 = TRAIN[0], TEST[1]
HIST = (1990, 2008)                 # history window, entirely before the modelling period
LOW_EXPOSURE = 100                  # policy-years: frequency too noisy below this
MAJOR_EVENTS = 10                   # largest named events of 2010-2024, by paid claims
STATE_FIPS = {"01": "AL", "12": "FL", "13": "GA", "21": "KY", "28": "MS", "37": "NC",
              "45": "SC", "47": "TN"}


def num(s):
    return pd.to_numeric(s, errors="coerce").astype("float64")


pd.set_option("future.no_silent_downcasting", True)

# -------------------------------------------------------------------------
# 1. Inputs
# -------------------------------------------------------------------------
claims = pd.read_parquet(CLAIMS)
claims["year"] = num(claims["loss_year"]).astype(int)
claims["paid"] = num(claims["paid_building_real"]) > 0
claims["county"] = claims["county_fips"].astype("object")
claims["event"] = claims["floodEvent"].astype("object")

expo = pd.read_parquet(EXPO)
expo["county"] = expo["county_fips"].astype("object")
expo["zone"] = expo["flood_zone_group"].astype("object")
expo["py"] = num(expo["policy_years"])
expo["cov_years"] = num(expo["building_coverage_years"])

# -------------------------------------------------------------------------
# 2. Exposure and policy features per county x year
# -------------------------------------------------------------------------
e = expo[expo["year"].between(Y0, Y1) & expo["county"].notna()]
unit = e.groupby(["county", "year"]).agg(exposure_years=("py", "sum"),
                                         cov_years=("cov_years", "sum"),
                                         n_policy_rows=("n_policy_rows", "sum"),
                                         partial_year=("partial_year", "any"))
z = e.assign(py_known=np.where(e["zone"].notna(), e["py"], 0.0),
             py_sfha=np.where(e["zone"].isin(["A*", "V*"]), e["py"], 0.0),
             py_v=np.where(e["zone"] == "V*", e["py"], 0.0),
             py_x=np.where(e["zone"] == "X", e["py"], 0.0)) \
     .groupby(["county", "year"])[["py_known", "py_sfha", "py_v", "py_x"]].sum()
unit = unit.join(z)
unit["share_sfha"] = unit["py_sfha"] / unit["py_known"]
unit["share_v"] = unit["py_v"] / unit["py_known"]
unit["share_x"] = unit["py_x"] / unit["py_known"]
unit["share_zone_unknown"] = 1 - unit["py_known"] / unit["exposure_years"]
unit["mean_coverage"] = unit["cov_years"] / unit["exposure_years"]       # nominal USD

# -------------------------------------------------------------------------
# 3. Claim counts per county x year
# -------------------------------------------------------------------------
c = claims[claims["year"].between(Y0, Y1)]
no_county = c["county"].isna()
c = c[~no_county]
named = c[c["paid"] & c["event"].notna()
          & ~c["event"].astype(str).str.lower().isin(["flooding", "flood"])]
major = named["event"].value_counts().head(MAJOR_EVENTS).index
counts = c.groupby(["county", "year"]).agg(
    n_claims=("paid", "sum"), n_all=("id", "size"),
    n_major=("event", lambda s: (s.isin(major) & c.loc[s.index, "paid"]).sum()))
unit = unit.join(counts, how="left")
for col in ["n_claims", "n_all", "n_major"]:
    unit[col] = unit[col].fillna(0).astype(int)

# -------------------------------------------------------------------------
# 4. History (1990-2008) and controls
# -------------------------------------------------------------------------
hist = claims[claims["year"].between(*HIST) & claims["paid"]].groupby("county").size()
cy = unit.reset_index().rename(columns={"county": "county_id"})
cy = cy[cy["exposure_years"] > 0].copy()
cy["state"] = cy["county_id"].str[:2].map(STATE_FIPS)
cy["hist_claims_1990_2008"] = cy["county_id"].map(hist).fillna(0).astype(int)
# Scaled by the average policy count of the TRAINING years only (no test information)
avg_train = cy[cy["year"] <= TRAIN[1]].groupby("county_id")["exposure_years"].mean()
cy["hist_per_1000"] = 1000 * cy["hist_claims_1990_2008"] / cy["county_id"].map(avg_train)

cy["period"] = np.where(cy["year"] <= TRAIN[1], "train", "test")
cy["freq_per_1000"] = 1000 * cy["n_claims"] / cy["exposure_years"]
cy["major_event_share"] = np.where(cy["n_claims"] > 0, cy["n_major"] / cy["n_claims"], 0.0)
cy["low_exposure"] = cy["exposure_years"] < LOW_EXPOSURE

ROLE = {
    "id": ["county_id", "year", "state"],
    "target": ["n_claims"],
    "offset": ["exposure_years"],
    "features": ["share_sfha", "share_v", "share_x", "mean_coverage",
                 "hist_claims_1990_2008", "hist_per_1000"],
    "controls": ["period", "n_all", "n_major", "major_event_share", "freq_per_1000",
                 "low_exposure", "share_zone_unknown", "partial_year", "n_policy_rows"],
}
cols = [c for group in ROLE.values() for c in group]
cy = cy[cols].sort_values(["county_id", "year"]).reset_index(drop=True)
cy["county_id"] = cy["county_id"].astype("string")
cy["state"] = cy["state"].astype("category")
cy["period"] = pd.Categorical(cy["period"], categories=["train", "test"])

# -------------------------------------------------------------------------
# 5. Checks and output
# -------------------------------------------------------------------------
assert not cy.duplicated(["county_id", "year"]).any()
assert cy["state"].notna().all(), "county outside Region 4"
assert (cy["n_claims"] <= cy["n_all"]).all()
assert cy["year"].between(Y0, Y1).all()

OUT_DIR.mkdir(parents=True, exist_ok=True)
cy.to_parquet(OUT, index=False)
roles = {
    **ROLE,
    "description": {
        "n_claims": "claims with a positive building paid amount (real USD > 0)",
        "exposure_years": "policy-years in force, single-family homes (zone_year.parquet)",
        "share_sfha": "share of known-zone policy-years in zones A* or V*",
        "share_v": "share of known-zone policy-years in zone V*",
        "share_x": "share of known-zone policy-years in zone X",
        "mean_coverage": "building coverage-years / policy-years, nominal USD",
        "hist_claims_1990_2008": "paid claims in the county, loss years 1990-2008",
        "hist_per_1000": "hist_claims_1990_2008 per 1,000 average policy-years of 2010-2019",
        "period": f"train {TRAIN[0]}-{TRAIN[1]}, test {TEST[0]}-{TEST[1]}",
        "n_all": "all claims, paid or not (sensitivity count)",
        "n_major": f"paid claims from the {MAJOR_EVENTS} largest named events of {Y0}-{Y1}",
        "major_event_share": "n_major / n_claims (0 when no claim)",
        "freq_per_1000": "1000 * n_claims / exposure_years",
        "low_exposure": f"exposure_years < {LOW_EXPOSURE}",
        "share_zone_unknown": "share of policy-years without flood zone",
        "partial_year": "exposure year flagged partial in zone_year (none in 2010-2024)",
        "n_policy_rows": "number of policy records (not a policy count)",
    },
    "major_events": list(map(str, major)),
    "claims_without_county_share": float(no_county.mean()),
    "rows": len(cy), "counties": int(cy["county_id"].nunique()),
}
ROLES.write_text(json.dumps(roles, indent=2))

print(f"{OUT.relative_to(ROOT)}: {len(cy):,} county-years, {cy['county_id'].nunique()} counties, "
      f"{cy['n_claims'].sum():,} paid claims, {cy['exposure_years'].sum() / 1e6:,.1f}M "
      "policy-years")
print(f"  train {(cy['period'] == 'train').sum():,} rows, test {(cy['period'] == 'test').sum():,}"
      f" rows; claims without county dropped: {no_county.mean():.2%}")
print(f"{ROLES.relative_to(ROOT)}: roles and definitions")
