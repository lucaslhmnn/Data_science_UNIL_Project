"""
Build the COUNTY x FLOOD ZONE x year modelling table for the claim frequency analysis.

Output
------
  EDA/ds_clean.csv          one row per county x zone x year, 2010-2024
  EDA/ds_clean_roles.json   role and definition of each column
The CSV is versioned in git, so the EDA runs without rebuilding it. Rebuild it only if
the cleaned data change.

Why county x zone x year
------------------------
Claims and policies are redacted and share no identifier, so they can only be joined in
aggregate. The finest common level available in the repository is flood zone x county x
year (zone_year.parquet). Keeping the zone as a dimension, instead of averaging it per
county, keeps the strongest known risk factor: frequency differs by zone (V > A > X), and
this difference disappears once zones are mixed within a county.
Same idea as the tract table of CLAUDE.md (data/processed/tract_year.parquet), at a
coarser geographic level.

Inputs (already cleaned and versioned, single-family homes, FEMA Region 4):
  - Data_cleaning/clean/claims_clean.parquet  one row per claim
  - Data_cleaning/clean/zone_year.parquet     policy exposure by zone x county x year

Definitions
-----------
  zone            flood zone group of the policy or claim (ratedFloodZone): V*, A*, X.
                  Zone D and unknown zones are dropped (well below 1% of claims and exposure).
  n_claims        claims with a positive building paid amount (target)
  exposure_years  policy-years in force (offset: log(exposure_years))
  coverage_real   mean building coverage in constant 2024 USD. The nominal coverage rises
                  every year with prices, so a model could use it to guess the year, which
                  is not allowed. It is deflated with the CPI of the previous year, known
                  before the year starts.
  Features are known at the start of the year and contain no year effect. Premiums are
  left out: they reflect the insurer's rating, not the insured risk.
  Controls are for description and checks only, never model inputs.
  Years 2010-2024: policy records start in 2009 (partial year) and claims of 2025 and
  later may still be open.

Run from the repository root:  python EDA/build_ds_clean.py
"""

import json
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "Data_cleaning" / "clean" / "claims_clean.parquet"
EXPO = ROOT / "Data_cleaning" / "clean" / "zone_year.parquet"
CPI = ROOT / "Data_cleaning" / "CPI_1978_2026.xlsx"     # BLS CPI-U, also used by clean_data.py
CPI_BASE = 2024                     # coverage_real is in USD of this year
OUT_DIR = ROOT / "EDA"
CSV = OUT_DIR / "ds_clean.csv"
ROLES = OUT_DIR / "ds_clean_roles.json"

TRAIN = (2010, 2019)
TEST = (2020, 2024)
Y0, Y1 = TRAIN[0], TEST[1]
HIST = (1990, 2008)                 # history window, entirely before the modelling period
ZONES = ["V*", "A*", "X"]
LOW_EXPOSURE = 100                  # policy-years: frequency too noisy below this
MAJOR_EVENTS = 10                   # largest named events of 2010-2024, by paid claims
STATE_FIPS = {"01": "AL", "12": "FL", "13": "GA", "21": "KY", "28": "MS", "37": "NC",
              "45": "SC", "47": "TN"}
KEY = ["county", "zone", "year"]


def num(s):
    return pd.to_numeric(s, errors="coerce").astype("float64")


def cpi_annual(path):
    """Annual average of the monthly CPI-U (years with 12 months only)."""
    rows = list(openpyxl.load_workbook(path, read_only=True, data_only=True)
                .worksheets[0].iter_rows(values_only=True))
    h = next(i for i, r in enumerate(rows) if r[0] == "Year")
    hdr = list(rows[h])
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    out = {}
    for r in rows[h + 1:]:
        if r[0] is None:
            continue
        v = [r[hdr.index(m)] for m in months]
        if all(isinstance(x, (int, float)) for x in v):
            out[int(r[0])] = float(np.mean(v))
    return out


pd.set_option("future.no_silent_downcasting", True)

# -------------------------------------------------------------------------
# 1. Inputs
# -------------------------------------------------------------------------
claims = pd.read_parquet(CLAIMS)
claims["year"] = num(claims["loss_year"]).astype(int)
claims["paid"] = num(claims["paid_building_real"]) > 0
claims["county"] = claims["county_fips"].astype("object")
claims["zone"] = claims["flood_zone_group"].astype("object")
claims["event"] = claims["floodEvent"].astype("object")

expo = pd.read_parquet(EXPO)
expo["county"] = expo["county_fips"].astype("object")
expo["zone"] = expo["flood_zone_group"].astype("object")
expo["py"] = num(expo["policy_years"])
expo["cov_years"] = num(expo["building_coverage_years"])

# -------------------------------------------------------------------------
# 2. Exposure per county x zone x year
# -------------------------------------------------------------------------
e = expo[expo["year"].between(Y0, Y1) & expo["county"].notna()]
expo_dropped = e.loc[~e["zone"].isin(ZONES), "py"].sum() / e["py"].sum()
e = e[e["zone"].isin(ZONES)]
unit = e.groupby(KEY).agg(exposure_years=("py", "sum"), cov_years=("cov_years", "sum"),
                          n_policy_rows=("n_policy_rows", "sum"),
                          partial_year=("partial_year", "any"))
unit["mean_coverage"] = unit["cov_years"] / unit["exposure_years"]       # nominal USD

# -------------------------------------------------------------------------
# 3. Claim counts per county x zone x year
# -------------------------------------------------------------------------
c = claims[claims["year"].between(Y0, Y1)]
no_county = c["county"].isna().mean()
c = c[c["county"].notna()]
no_zone = (~c["zone"].isin(ZONES)).mean()
c = c[c["zone"].isin(ZONES)]

named = c[c["paid"] & c["event"].notna()
          & ~c["event"].astype(str).str.lower().isin(["flooding", "flood"])]
ev_counts = named.groupby(named["event"].astype(str)).agg(n=("id", "size"),
                                                         year=("year", "median"))
ev_counts = ev_counts.sort_values("n", ascending=False).head(MAJOR_EVENTS)
c = c.assign(major=c["paid"] & c["event"].astype(str).isin(ev_counts.index))
counts = c.groupby(KEY).agg(n_claims=("paid", "sum"), n_all=("id", "size"),
                            n_major=("major", "sum"))
unit = unit.join(counts, how="left")
for col in ["n_claims", "n_all", "n_major"]:
    unit[col] = unit[col].fillna(0).astype(int)
claims_lost = 1 - unit["n_claims"].sum() / c["paid"].sum()     # claims without exposure row

# -------------------------------------------------------------------------
# 4. History 1990-2008 (before the modelling period) and controls
# -------------------------------------------------------------------------
h = claims[claims["year"].between(*HIST) & claims["paid"] & claims["county"].notna()]
hist_cz = h[h["zone"].isin(ZONES)].groupby(["county", "zone"]).size()
hist_c = h.groupby("county").size()

d = unit.reset_index()
d = d[d["exposure_years"] > 0].copy()
d["state"] = d["county"].str[:2].map(STATE_FIPS)
train = d["year"] <= TRAIN[1]
# Scaled by the average exposure of the TRAINING years only (no test information)
avg_cz = d[train].groupby(["county", "zone"])["exposure_years"].mean()
avg_c = d[train].groupby(["county", "year"])["exposure_years"].sum().groupby("county").mean()
cz = pd.MultiIndex.from_frame(d[["county", "zone"]])
d["hist_claims_1990_2008"] = hist_cz.reindex(cz).fillna(0).astype(int).to_numpy()
d["hist_per_1000"] = 1000 * d["hist_claims_1990_2008"] / avg_cz.reindex(cz).to_numpy()
d["county_hist_per_1000"] = 1000 * d["county"].map(hist_c).fillna(0) / d["county"].map(avg_c)

# Coverage in constant dollars: deflated by the CPI of the previous year (known in advance)
cpi = cpi_annual(CPI)
d["coverage_real"] = d["mean_coverage"] * cpi[CPI_BASE] / d["year"].map(lambda y: cpi[y - 1])

d["period"] = np.where(train, "train", "test")
d["freq_per_1000"] = 1000 * d["n_claims"] / d["exposure_years"]
d["major_event_share"] = np.where(d["n_claims"] > 0, d["n_major"] / d["n_claims"], 0.0)
d["low_exposure"] = d["exposure_years"] < LOW_EXPOSURE

ROLE = {
    "id": ["county_id", "zone", "year", "state"],
    "target": ["n_claims"],
    "offset": ["exposure_years"],
    "features": ["zone", "mean_coverage", "coverage_real", "hist_claims_1990_2008", "hist_per_1000",
                 "county_hist_per_1000"],
    "controls": ["period", "n_all", "n_major", "major_event_share", "freq_per_1000",
                 "low_exposure", "partial_year", "n_policy_rows"],
}
d = d.rename(columns={"county": "county_id"})
cols = list(dict.fromkeys(c for group in ROLE.values() for c in group))
d = d[cols].sort_values(["county_id", "zone", "year"]).reset_index(drop=True)
d["county_id"] = d["county_id"].astype("string")
d["zone"] = pd.Categorical(d["zone"], categories=ZONES)
d["state"] = d["state"].astype("category")
d["period"] = pd.Categorical(d["period"], categories=["train", "test"])

# -------------------------------------------------------------------------
# 5. Checks and output
# -------------------------------------------------------------------------
assert not d.duplicated(["county_id", "zone", "year"]).any()
assert d["state"].notna().all(), "county outside Region 4"
assert (d["n_claims"] <= d["n_all"]).all()
assert d["year"].between(Y0, Y1).all()

# CSV: county_id keeps its leading zero ("01001"); read it as text:
#   pd.read_csv(CSV, dtype={"county_id": str})
d.to_csv(CSV, index=False, float_format="%.6g")
roles = {
    **ROLE,
    "description": {
        "county_id": "county FIPS code, 5 characters (claims: countyCode; policies: "
                     "first 5 characters of censusGeoid)",
        "zone": "flood zone group from ratedFloodZone: V* (coastal, waves), A* (100-year "
                "floodplain), X (moderate or low risk). V* and A* form the SFHA",
        "year": "calendar year (claims: yearOfLoss; policies: days covered in the year)",
        "n_claims": "claims with a positive building paid amount (real USD > 0)",
        "exposure_years": "policy-years in force: sum of policyCount x days covered / 365.25",
        "mean_coverage": "building coverage-years / policy-years, nominal USD (rises with "
                         "prices, so it carries a time trend: prefer coverage_real in models)",
        "coverage_real": f"mean_coverage in constant {CPI_BASE} USD, deflated by the annual "
                         "average CPI-U of the previous year",
        "hist_claims_1990_2008": "paid claims of this county and zone, loss years 1990-2008",
        "hist_per_1000": "hist_claims_1990_2008 per 1,000 average policy-years of the county "
                         "and zone over 2010-2019",
        "county_hist_per_1000": "paid claims of the county (all zones), 1990-2008, per 1,000 "
                                "average yearly policy-years of the county over 2010-2019",
        "period": f"train {TRAIN[0]}-{TRAIN[1]}, test {TEST[0]}-{TEST[1]}",
        "n_all": "all claims, paid or not (sensitivity count)",
        "n_major": f"paid claims from the {MAJOR_EVENTS} largest named events of {Y0}-{Y1}",
        "major_event_share": "n_major / n_claims (0 when no claim)",
        "freq_per_1000": "1000 * n_claims / exposure_years",
        "low_exposure": f"exposure_years < {LOW_EXPOSURE}",
        "partial_year": "exposure year flagged partial in zone_year (none in 2010-2024)",
        "n_policy_rows": "number of policy records (not a policy count)",
    },
    "major_events": [{"name": k, "year": int(r.year), "paid_claims": int(r.n)}
                     for k, r in ev_counts.iterrows()],
    "dropped": {"claims_without_county_share": float(no_county),
                "claims_zone_D_or_unknown_share": float(no_zone),
                "paid_claims_without_exposure_row_share": float(claims_lost),
                "exposure_zone_D_or_unknown_share": float(expo_dropped)},
    "rows": len(d), "counties": int(d["county_id"].nunique()),
}
ROLES.write_text(json.dumps(roles, indent=2))

print(f"{CSV.relative_to(ROOT)}: {len(d):,} county-zone-years, {d['county_id'].nunique()} "
      f"counties, {d['n_claims'].sum():,} paid claims, {d['exposure_years'].sum() / 1e6:,.1f}M "
      "policy-years")
print(f"  train {(d['period'] == 'train').sum():,} rows, test {(d['period'] == 'test').sum():,} rows")
print(f"  dropped: claims without county {no_county:.2%}, zone D or unknown {no_zone:.2%}, "
      f"paid claims without exposure row {claims_lost:.2%}; exposure zone D or unknown "
      f"{expo_dropped:.2%}")
print(f"{ROLES.relative_to(ROOT)}: roles and definitions")
