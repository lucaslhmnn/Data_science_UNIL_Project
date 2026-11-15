"""
Exploratory analysis for the flood claim FREQUENCY models (NFIP, FEMA Region 4).

Research question (see CLAUDE.md): does LightGBM (Poisson) beat a Poisson / negative
binomial GLM for the number of paid claims per unit x year, with exposure in
policy-years as offset? Training 2010-2019, test 2020-2024.

Data
----
One input: EDA/ds_clean.csv, one row per county x flood zone x year (2010-2024),
with the paid claim count (target), the exposure in policy-years (offset), candidate
features and controls. Definitions and the list of largest events are in
EDA/ds_clean_roles.json. Both files are made by EDA/build_ds_clean.py
from the cleaned claims and policies, and are versioned, so this script runs on its own.
A "unit" below is one county x zone cell.

Story told by the figures (EDA/figures/eda_*.png and .pdf)
------------------------------------------------------
  eda_1_exposure_claims  Exposure is stable; claims and frequency jump in hurricane years.
  eda_2_overdispersion   Counts are mostly small with a long tail: variance far above
                         the mean, even within a year (Poisson too narrow -> NB, LightGBM).
  eda_3_concentration    A small share of unit-years and a few events hold most claims;
                         the test window contains Ian and Helene.
  eda_4_zone             Frequency by flood zone: V > A > X, in both periods.
  eda_5_features         Candidate features against frequency (training years only).
  eda_6_geography        Frequency by state, and persistence of the frequency of each
                         county x zone cell between training and test periods.

Tables (EDA/figures/):
  eda_by_year.csv, eda_by_state.csv, eda_unit_year_summary.csv, eda_key_numbers.json

Conventions: a claim counts if its building paid amount is positive (the target);
all claims are kept as a sensitivity count. Feature relationships use the training
years only, so no test information is used. Year is shown for description, never as
a feature. No em dashes in labels (project rule).

Run from the repository root:  python EDA/eda.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator, NullFormatter

# -------------------------------------------------------------------------
# 0. PATHS, PERIODS, STYLE
# -------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "EDA" / "ds_clean.csv"            # made by EDA/build_ds_clean.py
ROLES = ROOT / "EDA" / "ds_clean_roles.json"
OUT = ROOT / "EDA" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

TRAIN = (2010, 2019)
TEST = (2020, 2024)
Y0, Y1 = TRAIN[0], TEST[1]
STATE_FIPS = {"01": "AL", "12": "FL", "13": "GA", "21": "KY", "28": "MS", "37": "NC",
              "45": "SC", "47": "TN"}

BLUE, ORANGE, GREEN, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
ZONE_COL = {"V*": ORANGE, "A*": BLUE, "X": GREEN}
NEUTRAL, INK, INK2, MUTED = "#c9c8c2", "#0b0b0b", "#52514e", "#8a8984"
GRID, BAND = "#e6e5e1", "#efeeea"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10, "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": INK2,
    "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True,
    "axes.titlesize": 11, "axes.titlelocation": "left", "axes.titlepad": 10,
    "grid.color": GRID, "grid.linewidth": 0.7, "xtick.color": INK2, "ytick.color": INK2,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.frameon": False,
    "legend.fontsize": 8.5, "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "text.parse_math": False,
})
thousands = FuncFormatter(lambda v, _: f"{v / 1e6:,.1f}M" if v >= 1e6
                          else (f"{v / 1000:,.0f}k" if v >= 1000 else f"{v:,.0f}"))
pct = FuncFormatter(lambda v, _: f"{v:.0f}%")
plain = FuncFormatter(lambda v, _: f"{v:g}")


def log_axis(ax, which="y"):
    """Log scale with plain tick labels (no mathtext), minor labels hidden."""
    for w in which:
        axis = ax.xaxis if w == "x" else ax.yaxis
        (ax.set_xscale if w == "x" else ax.set_yscale)("log")
        axis.set_major_formatter(plain)
        axis.set_minor_formatter(NullFormatter())


def export(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}")


def suptitle(fig, text):
    fig.suptitle(text, x=0.01, ha="left", fontsize=12.5, fontweight="bold")


def num(s):
    return pd.to_numeric(s, errors="coerce").astype("float64")


def period(year):
    return np.where(year <= TRAIN[1], "train", "test")


def shade_test(ax):
    ax.axvspan(TEST[0] - 0.5, TEST[1] + 0.5, color=BAND, lw=0, zorder=0)
    ax.text(TEST[0] - 0.3, ax.get_ylim()[1], "test", fontsize=8.5, color=INK2,
            va="top", ha="left", style="italic")


def freq(n, e):
    """Claims per 1,000 policy-years."""
    return 1000 * n / e


# -------------------------------------------------------------------------
# 1. DATA
# -------------------------------------------------------------------------
pd.set_option("future.no_silent_downcasting", True)
print(f"Loading {DATA.relative_to(ROOT)}...")
uy = pd.read_csv(DATA, dtype={"county_id": str, "zone": str, "state": str})
roles = json.loads(ROLES.read_text())
uy = uy[uy["exposure_years"] > 0].copy()
uy["unit"] = uy["county_id"] + " " + uy["zone"]
uy["period"] = period(uy["year"])
tr, te = uy[uy["period"] == "train"], uy[uy["period"] == "test"]
LEVEL, UNIT, UNITS = "county-zone", "county-zone", "county-zone cells"
print(f"  {len(uy):,} {UNIT}-years ({uy['unit'].nunique():,} {UNITS}), "
      f"{int(uy['n_claims'].sum()):,} paid claims, {uy['exposure_years'].sum() / 1e6:,.1f}M "
      "policy-years")

# Claims left out of the table (no county, zone D or unknown) and largest events
no_unit = roles["dropped"]["claims_without_county_share"] \
    + roles["dropped"]["claims_zone_D_or_unknown_share"]
top_ev = pd.DataFrame(roles["major_events"]).set_index("name") \
    .rename(columns={"paid_claims": "n"})

# -------------------------------------------------------------------------
# 2. TABLES
# -------------------------------------------------------------------------
by_year = uy.groupby("year").agg(n_claims=("n_claims", "sum"), n_all=("n_all", "sum"),
                                 n_major=("n_major", "sum"),
                                 exposure=("exposure_years", "sum"),
                                 zero_share=("n_claims", lambda s: (s == 0).mean()))
by_year["freq"] = freq(by_year["n_claims"], by_year["exposure"])
by_year["freq_all"] = freq(by_year["n_all"], by_year["exposure"])
# "Ordinary" floods: paid claims outside the ten largest named events
by_year["freq_ex_major"] = freq(by_year["n_claims"] - by_year["n_major"], by_year["exposure"])
# Mean coverage per policy, nominal and in constant dollars (exposure-weighted)
cov = uy.assign(w_nom=uy["mean_coverage"] * uy["exposure_years"],
                w_real=uy["coverage_real"] * uy["exposure_years"]).groupby("year")[
                    ["w_nom", "w_real"]].sum()
by_year["mean_coverage"] = cov["w_nom"] / by_year["exposure"]
by_year["coverage_real"] = cov["w_real"] / by_year["exposure"]
by_year.round(4).to_csv(OUT / "eda_by_year.csv")

by_state = uy.groupby(["state", "period"], observed=True).agg(n=("n_claims", "sum"),
                                               e=("exposure_years", "sum")).unstack()
by_state_f = pd.DataFrame({p: freq(by_state[("n", p)], by_state[("e", p)])
                           for p in ["train", "test"]})
by_state_f["share_exposure"] = by_state["e"].sum(axis=1) / by_state["e"].sum().sum()
by_state_f = by_state_f.sort_values("share_exposure", ascending=False)
by_state_f.round(4).to_csv(OUT / "eda_by_state.csv")

summary_cols = ["n_claims", "exposure_years", "mean_coverage", "coverage_real", "hist_per_1000",
                "county_hist_per_1000"]
uy[[c for c in summary_cols if c in uy]].describe(
    percentiles=[.1, .25, .5, .75, .9, .99]).T.round(3).to_csv(OUT / "eda_unit_year_summary.csv")

print("\nFigures:")
# -------------------------------------------------------------------------
# FIGURE 1: exposure, claims and frequency by year
# -------------------------------------------------------------------------
year_label = top_ev.head(6).groupby("year").apply(
    lambda g: ", ".join(i.replace("Hurricane ", "") for i in g.index), include_groups=False)

fig, (a, b, c) = plt.subplots(1, 3, figsize=(15.5, 4.5), layout="constrained")
a.bar(by_year.index, by_year["exposure"], 0.8, color=BLUE)
a.yaxis.set_major_formatter(thousands)
a.set_title("(a) Exposure in policy-years")

b.bar(by_year.index, by_year["n_claims"], 0.8, color=BLUE)
b.yaxis.set_major_formatter(thousands)
b.set_ylim(0, by_year["n_claims"].max() * 1.2)
for yr_, lbl in year_label.items():
    b.text(yr_, by_year.loc[int(yr_), "n_claims"] * 1.02, lbl, ha="center", va="bottom",
           fontsize=7.5, color=INK2, style="italic")
b.set_title("(b) Paid claims per year")

c.plot(by_year.index, by_year["freq"], "-o", color=BLUE, lw=2, ms=4, mec="white",
       label="paid claims (target)")
c.plot(by_year.index, by_year["freq_all"], "--", color=INK2, lw=1.2, label="all claims")
c.plot(by_year.index, by_year["freq_ex_major"], "-s", color=ORANGE, lw=1.6, ms=3.5, mec="white",
       label="paid claims outside the ten largest events")
log_axis(c, "y")
c.legend(loc="upper left")
c.set_title("(c) Claims per 1,000 policy-years (log scale)")
for ax in (a, b, c):
    ax.set_xlim(Y0 - 0.6, Y1 + 0.6)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    shade_test(ax)
ratio_years = by_year["freq"].max() / by_year["freq"].min()
suptitle(fig, f"Exposure is stable, claims are not: yearly frequency varies by a factor of "
              f"{ratio_years:.0f}")
export(fig, "eda_1_exposure_claims")

# -------------------------------------------------------------------------
# FIGURE 2: count distribution and overdispersion
# -------------------------------------------------------------------------
y, ex = tr["n_claims"].to_numpy(float), tr["exposure_years"].to_numpy(float)
mu0 = ex * y.sum() / ex.sum()                                   # one rate for all
rate_y = tr.groupby("year")["n_claims"].transform("sum") / \
    tr.groupby("year")["exposure_years"].transform("sum")
mu1 = (tr["exposure_years"] * rate_y).to_numpy(float)          # one rate per year
disp0 = np.sum((y - mu0) ** 2 / mu0) / (len(y) - 1)
disp1 = np.sum((y - mu1) ** 2 / mu1) / (len(y) - tr["year"].nunique())
alpha = np.sum((y - mu1) ** 2 - y) / np.sum(mu1 ** 2)          # NB2, method of moments
g_yz = [tr["year"], tr["zone"]]                                # one rate per year x zone
rate_yz = tr.groupby(g_yz)["n_claims"].transform("sum") / \
    tr.groupby(g_yz)["exposure_years"].transform("sum")
mu2 = (tr["exposure_years"] * rate_yz).to_numpy(float)
ok = mu2 > 0
disp2 = np.sum((y[ok] - mu2[ok]) ** 2 / mu2[ok]) / (ok.sum() - tr.groupby(g_yz).ngroups)
zero_share = (uy["n_claims"] == 0).mean()

fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.8), layout="constrained")
counts = uy["n_claims"]
edges = np.r_[0, 1, np.unique(np.round(np.logspace(0.3, np.log10(counts.max() + 1), 22)))]
h, _ = np.histogram(counts, bins=edges)
a.bar(range(len(h)), 100 * h / len(counts), 0.8,
      color=[ORANGE] + [BLUE] * (len(h) - 1))
lbls = ["0"] + [f"{int(lo)}" if hi - lo <= 1 else f"{int(lo)}-{int(hi) - 1}"
                for lo, hi in zip(edges[1:-1], edges[2:])]
a.set_xticks(range(len(h))[::2], lbls[::2], rotation=45, ha="right", fontsize=8)
a.yaxis.set_major_formatter(pct)
a.set_xlabel(f"Paid claims per {UNIT}-year")
a.set_title(f"(a) {Y0}-{Y1}: {zero_share:.0%} of {UNIT}-years have no claim, the tail reaches "
            f"{int(counts.max()):,}")

bins = pd.qcut(mu1, 25, duplicates="drop")
mv = pd.DataFrame({"y": y, "mu": mu1, "b": bins}).groupby("b", observed=True) \
       .agg(m=("y", "mean"), v=("y", "var"), mu=("mu", "mean"))
mv = mv[(mv["m"] > 0) & (mv["v"] > 0)]
grid = np.logspace(np.log10(mv["mu"].min()), np.log10(mv["mu"].max()), 50)
b.plot(mv["m"], mv["v"], "o", color=BLUE, ms=5, label="observed (25 bins of expected count)")
b.plot(grid, grid, color=MUTED, ls=":", lw=1.2, label="Poisson: variance = mean")
b.plot(grid, grid + alpha * grid ** 2, color=ORANGE, lw=1.6,
         label=f"negative binomial, alpha = {alpha:.2f}")
log_axis(b, "xy")
b.set_xlabel("Mean count in bin")
b.set_ylabel("Variance in bin")
b.grid(True, which="major", axis="both")
b.legend(loc="upper left")
b.set_title(f"(b) Dispersion {disp0:,.0f} overall, {disp1:,.0f} within years, {disp2:,.0f} "
            "within year and zone (Poisson = 1)")
suptitle(fig, f"Counts are overdispersed: a plain Poisson model is too narrow "
              f"({UNIT} level; (b) training years)")
export(fig, "eda_2_overdispersion")

# -------------------------------------------------------------------------
# FIGURE 3: concentration and events
# -------------------------------------------------------------------------
s = uy["n_claims"].sort_values(ascending=False).to_numpy()
cum = np.cumsum(s) / s.sum()
share_units = np.arange(1, len(s) + 1) / len(s)
top1 = cum[int(np.ceil(0.01 * len(s))) - 1]
top5 = cum[int(np.ceil(0.05 * len(s))) - 1]
top10_ev = top_ev.head(10)
ev_share = top10_ev["n"].sum() / uy["n_claims"].sum()
test_share = te["n_claims"].sum() / uy["n_claims"].sum()
test_expo = te["exposure_years"].sum() / uy["exposure_years"].sum()

fig, (a, b) = plt.subplots(1, 2, figsize=(13.5, 4.8), gridspec_kw={"width_ratios": [1, 1.2]},
                           layout="constrained")
a.plot(100 * share_units, 100 * cum, color=BLUE, lw=2)
a.plot([0, 100], [0, 100], color=MUTED, ls=":", lw=1)
for q, v in [(1, top1), (5, top5)]:
    a.plot([q, q], [0, 100 * v], color=MUTED, lw=0.8)
    a.text(q * 0.9, 100 * v + 2, f"top {q}%: {v:.0%} of claims", fontsize=8.5, color=INK,
           ha="right", va="bottom")
a.set_xscale("log")
a.set_xlim(0.01, 100)
a.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
a.yaxis.set_major_formatter(pct)
a.set_ylim(0, 100)
a.set_xlabel(f"Share of {UNIT}-years, ranked by claims (log scale)")
a.set_title(f"(a) Cumulative share of paid claims, {Y0}-{Y1}")

names = [f"{i.replace('Hurricane ', '').replace('Tropical Storm ', 'TS ')} ({int(r.year)})"
         for i, r in top10_ev.iterrows()]
cols = [ORANGE if r.year >= TEST[0] else BLUE for r in top10_ev.itertuples()]
b.barh(names[::-1], top10_ev["n"].to_numpy()[::-1], height=0.62, color=cols[::-1])
for i, n in enumerate(top10_ev["n"].to_numpy()[::-1]):
    b.text(n + top10_ev["n"].max() * 0.01, i, f"{n / 1000:,.1f}k", va="center", fontsize=8.5)
b.grid(axis="y", visible=False)
b.grid(axis="x", visible=True)
b.xaxis.set_major_formatter(thousands)
b.tick_params(axis="y", length=0)
b.set_xlim(0, top10_ev["n"].max() * 1.12)
b.set_title(f"(b) Top 10 events = {ev_share:.0%} of claims (orange: test period)")
suptitle(fig, f"Claims are concentrated: the test years hold {test_share:.0%} of claims "
              f"for {test_expo:.0%} of exposure")
export(fig, "eda_3_concentration")

# -------------------------------------------------------------------------
# FIGURE 4: frequency by flood zone
# -------------------------------------------------------------------------
zones = ["V*", "A*", "X"]
zsum = uy.groupby([uy["zone"].astype(str), "period"])[["n_claims", "exposure_years"]].sum()
zf = freq(zsum["n_claims"], zsum["exposure_years"]).unstack().reindex(zones)[["train", "test"]]
ze = zsum["exposure_years"].groupby(level=0).sum().reindex(zones)
zshare = ze / ze.sum()

fig, ax = plt.subplots(figsize=(8.5, 4.6), layout="constrained")
x = np.arange(len(zones))
for k, (p, col) in enumerate([("train", BLUE), ("test", ORANGE)]):
    xs = x + (k - 0.5) * 0.36
    ax.bar(xs, zf[p], 0.34, color=col, label=f"{p} {TRAIN if p == 'train' else TEST}"
           .replace("(", "").replace(")", "").replace(", ", "-"))
    for xi, v in zip(xs, zf[p]):
        ax.text(xi, v + zf.max().max() * 0.015, f"{v:.1f}", ha="center", va="bottom", fontsize=8.5)
ax.set_xticks(x, [f"{z}\n{s:.0%} of policy-years" for z, s in zip(zones, zshare)])
ax.tick_params(axis="x", length=0)
ax.set_ylim(0, zf.max().max() * 1.15)
ax.set_ylabel("Paid claims per 1,000 policy-years")
ax.legend(loc="upper right")
ax.set_title("V and A zones form the SFHA (Special Flood Hazard Area)")
suptitle(fig, "Frequency by flood zone: V > A > X in both periods")
export(fig, "eda_4_zone")

# -------------------------------------------------------------------------
# FIGURE 5: candidate features against frequency (training years only)
# -------------------------------------------------------------------------
FEATURES = {"coverage_real": ("Mean building coverage per policy (constant 2024 USD)",
                              FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k"), 1),
            "hist_per_1000": ("Paid claims 1990-2008 per 1,000 policies, same cell", plain, 1),
            "county_hist_per_1000": ("Paid claims 1990-2008 per 1,000 policies, county",
                                     plain, 1)}
FEATURES = {k: v for k, v in FEATURES.items() if k in tr and tr[k].notna().any()}
rho = {}
fig, axes = plt.subplots(1, len(FEATURES), figsize=(5 * len(FEATURES), 4.4),
                         layout="constrained", squeeze=False)
# One point per unit over the training years: exposure-weighted feature, pooled frequency
w = tr.assign(**{f"w_{c}": tr[c] * tr["exposure_years"] for c in FEATURES})
unit_tr = w.groupby("unit").agg(n=("n_claims", "sum"), e=("exposure_years", "sum"),
                                **{f"w_{c}": (f"w_{c}", "sum") for c in FEATURES})
for c in FEATURES:
    unit_tr[c] = unit_tr[f"w_{c}"] / unit_tr["e"]
unit_tr = unit_tr[unit_tr["e"] >= 100]
unit_tr["f"] = freq(unit_tr["n"], unit_tr["e"])
for ax, (col, (lbl, fmt, scale)) in zip(axes[0], FEATURES.items()):
    d = unit_tr[[col, "n", "e", "f"]].dropna()
    d = d.assign(bin=pd.qcut(d[col].rank(method="first"), 10, labels=False))
    g = d.groupby("bin").agg(x=(col, "median"), n=("n", "sum"), e=("e", "sum"))
    g["f"] = freq(g["n"], g["e"])
    rho[col] = d[col].corr(d["f"], method="spearman")
    ax.plot(scale * g["x"], g["f"], "-o", color=BLUE, lw=2, ms=5, mec="white")
    log_axis(ax, "y")
    ax.xaxis.set_major_formatter(fmt)
    ax.set_xlabel(f"{lbl} (decile median)")
    ax.set_title(f"Spearman rho = {rho[col]:.2f} ({len(d)} {UNITS})")
axes[0, 0].set_ylabel("Paid claims per 1,000 policy-years (log)")
suptitle(fig, f"Candidate features against frequency, training years {TRAIN[0]}-{TRAIN[1]} "
              f"({UNITS} with 100+ policy-years, grouped in deciles)")
export(fig, "eda_5_features")

# -------------------------------------------------------------------------
# FIGURE 6: geography and persistence
# -------------------------------------------------------------------------
pers = uy.groupby(["unit", "period"]).agg(n=("n_claims", "sum"), e=("exposure_years", "sum")) \
         .unstack()
pers = pers[(pers[("e", "train")] >= 100) & (pers[("e", "test")] >= 100)]
f_tr = freq(pers[("n", "train")], pers[("e", "train")])
f_te = freq(pers[("n", "test")], pers[("e", "test")])
rho_pers = f_tr.corr(f_te, method="spearman")
big = (pers[("e", "train")] >= 5000) & (pers[("e", "test")] >= 2500)
rho_big = f_tr[big].corr(f_te[big], method="spearman")

fig, (a, b) = plt.subplots(1, 2, figsize=(13.5, 4.9), layout="constrained")
st = by_state_f.sort_values("train")
yy = np.arange(len(st))
a.barh(yy - 0.19, st["train"], 0.36, color=BLUE, label=f"train {TRAIN[0]}-{TRAIN[1]}")
a.barh(yy + 0.19, st["test"], 0.36, color=ORANGE, label=f"test {TEST[0]}-{TEST[1]}")
a.set_yticks(yy, [f"{s} ({w:.0%})" for s, w in zip(st.index, st["share_exposure"])])
a.grid(axis="y", visible=False)
a.grid(axis="x", visible=True)
a.tick_params(axis="y", length=0)
a.set_xlabel("Paid claims per 1,000 policy-years")
a.legend(loc="lower right")
a.set_title("(a) Frequency by state (share of exposure)")

eps = 0.05
size = pers[("e", "train")] + pers[("e", "test")]
b.scatter(f_tr + eps, f_te + eps, s=np.clip(size / size.max() * 300, 4, 300), color=BLUE,
          alpha=0.4, lw=0)
lim = [eps, max(f_tr.max(), f_te.max()) * 1.5]
b.plot(lim, lim, color=MUTED, ls=":", lw=1)
log_axis(b, "xy")
b.grid(True, which="major", axis="both")
b.set_xlabel(f"Frequency, train {TRAIN[0]}-{TRAIN[1]}")
b.set_ylabel(f"Frequency, test {TEST[0]}-{TEST[1]}")
b.set_title(f"(b) {len(pers)} {UNITS}: rho = {rho_pers:.2f}; {int(big.sum())} largest: "
            f"rho = {rho_big:.2f} (size = exposure, 0 shown at 0.05)")
suptitle(fig, "The test hurricanes hit other places: past frequency barely predicts the test "
              "period")
export(fig, "eda_6_geography")

# -------------------------------------------------------------------------
# KEY NUMBERS
# -------------------------------------------------------------------------
key = {
    "level": LEVEL, "n_unit_years": len(uy), "n_units": int(uy["unit"].nunique()),
    "n_unit_years_train": len(tr), "n_unit_years_test": len(te),
    "paid_claims": int(uy["n_claims"].sum()), "policy_years": float(uy["exposure_years"].sum()),
    "claims_without_unit_share": float(no_unit),
    "freq_overall": float(freq(uy["n_claims"].sum(), uy["exposure_years"].sum())),
    "freq_train": float(freq(tr["n_claims"].sum(), tr["exposure_years"].sum())),
    "freq_test": float(freq(te["n_claims"].sum(), te["exposure_years"].sum())),
    "freq_by_year": {int(k): v for k, v in by_year["freq"].round(2).items()},
    "freq_ex_major_train": float(freq((tr["n_claims"] - tr["n_major"]).sum(),
                                      tr["exposure_years"].sum())),
    "freq_ex_major_test": float(freq((te["n_claims"] - te["n_major"]).sum(),
                                     te["exposure_years"].sum())),
    "major_share_train": float(tr["n_major"].sum() / tr["n_claims"].sum()),
    "major_share_test": float(te["n_major"].sum() / te["n_claims"].sum()),
    "coverage_nominal_change": float(by_year["mean_coverage"].iloc[-1]
                                     / by_year["mean_coverage"].iloc[0] - 1),
    "coverage_real_change": float(by_year["coverage_real"].iloc[-1]
                                  / by_year["coverage_real"].iloc[0] - 1),
    "freq_max_min_ratio": float(ratio_years),
    "zero_share": float(zero_share),
    "zero_share_train": float((tr["n_claims"] == 0).mean()),
    "max_count": int(counts.max()),
    "dispersion_overall": float(disp0), "dispersion_within_year": float(disp1),
    "dispersion_within_year_zone": float(disp2),
    "nb_alpha_moments": float(alpha),
    "top1pct_unit_years_share": float(top1), "top5pct_unit_years_share": float(top5),
    "top10_events": {k: int(v) for k, v in top10_ev["n"].items()},
    "top10_events_share": float(ev_share),
    "test_share_claims": float(test_share), "test_share_exposure": float(test_expo),
    "zone_freq": zf.round(2).to_dict(), "zone_share_exposure": zshare.round(4).to_dict(),
    "feature_spearman_train": {k: round(v, 3) for k, v in rho.items()},
    "persistence_spearman": float(rho_pers), "persistence_n_units": len(pers),
    "persistence_spearman_largest": float(rho_big), "persistence_n_largest": int(big.sum()),
    "state_freq": by_state_f.round(2).to_dict(),
}
(OUT / "eda_key_numbers.json").write_text(json.dumps(key, indent=1, default=str))

print("\n========== Key numbers ==========")
print(f" Level                 : {LEVEL} ({len(uy):,} unit-years, {uy['unit'].nunique()} units)")
print(f" Frequency /1000 PY    : overall {key['freq_overall']:.1f}, train {key['freq_train']:.1f},"
      f" test {key['freq_test']:.1f}")
print(f" Outside top 10 events : train {key['freq_ex_major_train']:.1f}, "
      f"test {key['freq_ex_major_test']:.1f} per 1,000 PY")
print(f" Mean coverage 2010-24 : nominal {key['coverage_nominal_change']:+.0%}, "
      f"constant dollars {key['coverage_real_change']:+.0%}")
print(f" Zero unit-years       : {zero_share:.1%}")
print(f" Dispersion            : {disp0:,.0f} overall, {disp1:,.0f} within year, "
      f"{disp2:,.0f} within year x zone, "
      f"NB alpha {alpha:.2f}")
print(f" Concentration         : top 1% unit-years {top1:.0%}, top 10 events {ev_share:.0%}")
print(f" Test period           : {test_share:.0%} of claims, {test_expo:.0%} of exposure")
print(" Zone frequency        : " + "; ".join(f"{z} {zf.loc[z, 'train']:.1f} / "
                                              f"{zf.loc[z, 'test']:.1f}" for z in zones))
print(" Feature rho (train)   : " + ", ".join(f"{k} {v:.2f}" for k, v in rho.items()))
print(f" Persistence rho       : {rho_pers:.2f} ({len(pers)} units), largest {rho_big:.2f} "
      f"({int(big.sum())})")
print(f" Claims without unit   : {no_unit:.2%}")
print(f"\n Outputs in {OUT}")
