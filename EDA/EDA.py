"""
EDA — sinistres NFIP, Région IV de FEMA (maisons individuelles, 1978-2026)
=========================================================================

Les figures suivent le fil du rapport. Chaque étape répond à une question
et prépare le modèle en deux parties (probabilité de paiement, puis montant
payé) :

  Données
    fig1_missing          Quelles variables sont fiables ? Le manque dépend de l'époque.
  Histoire
    fig2_events           Les sinistres arrivent par catastrophes : quelques ouragans
                          concentrent l'essentiel des sinistres et des montants.
    fig3_zone_risk        Rapportés aux polices en vigueur, les zones se classent
                          V > A > X : fréquence et coût par police (2010-2024).
    fig4_payment          Cible 1 : qu'est-ce qui fait varier la probabilité de paiement ?
    fig5_severity         Cible 2 : montant très asymétrique, tronqué par le plafond.
    fig6_severity_drivers Le montant dépend de l'événement et de l'époque, peu de la zone.
    fig7_correlation      Synthèse : corrélations de rang entre cibles et variables.
  Annexes
    fig8_depth            La profondeur d'eau explique le montant mais n'est connue qu'après coup.
    fig9_geography        Répartition par État (la Floride domine).
    fig10_validation      Plis et découpage temporel : la cible change entre périodes.

Tableaux (EDA/figures/) :
  summary_numeric.csv      statistiques descriptives des variables numériques
  summary_categorical.csv  effectif, taux de paiement et montant médian par modalité
  tests.csv                tests d'association avec taille d'effet (khi², Kruskal-Wallis)
  key_numbers.json         chiffres cités dans le rapport

Conventions :
  - montants en USD réels (revalorisés par le CPI) ;
  - « montant » = paid_building_real parmi les sinistres payés (> 0) ;
  - les sinistres de 2025 et après (recent_claim, dossiers peut-être encore
    ouverts) sont exclus des analyses de paiement et de montant, gardés
    pour les comptages ;
  - avec 600 000 lignes, toutes les p-valeurs sont minuscules : on lit la
    taille d'effet (V de Cramér, epsilon²), pas la p-valeur.

Lancer depuis la racine du projet (après python EDA/dsEDA.py) :
  python EDA/EDA.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from scipy import stats

# -------------------------------------------------------------------------
# 0. CHEMINS & STYLE
# -------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "EDA" / "data" / "data_clean.parquet"
EXPO = ROOT / "Data_cleaning" / "clean" / "zone_year.parquet"
OUT = ROOT / "EDA" / "figures"
for p, hint in [(DATA, "python EDA/dsEDA.py"), (EXPO, "Data_cleaning/clean/clean_data.py")]:
    if not p.exists():
        raise SystemExit(f"{p} introuvable. Le créer avec : {hint}")
OUT.mkdir(parents=True, exist_ok=True)

# Palette (validée daltonisme, ordre fixe) et encres
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
BLUE, ORANGE, GREEN = SERIES[0], SERIES[1], SERIES[2]
ZONE_COL = {"V*": ORANGE, "A*": BLUE, "X": GREEN, "D": SERIES[3]}
NEUTRAL = "#c9c8c2"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID, BAND = "#e6e5e1", "#efeeea"
SEQ = LinearSegmentedColormap.from_list(
    "seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("div", [ORANGE, "#f0efec", BLUE])

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10, "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": INK2,
    "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True,
    "axes.titlesize": 11, "axes.titlelocation": "left", "axes.titlepad": 10,
    "grid.color": GRID, "grid.linewidth": 0.7, "xtick.color": INK2, "ytick.color": INK2,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.frameon": False,
    "legend.fontsize": 8.5, "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "text.parse_math": False,   # les « $ » des montants ne sont pas des formules
})

kdollars = FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k")
pow10 = FuncFormatter(lambda v, _: {1: "$10", 2: "$100", 3: "$1k", 4: "$10k", 5: "$100k",
                                     6: "$1M"}.get(round(v), ""))
thousands = FuncFormatter(lambda v, _: f"{v / 1000:,.0f}k" if v >= 1000 else f"{v:,.0f}")
pct = FuncFormatter(lambda v, _: f"{v:.0f} %")
RENAME = {"True": "oui", "False": "non", "NA": "n. r.", "inconnu": "inconnu"}


def export(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}")


def suptitle(fig, text):
    fig.suptitle(text, x=0.01, ha="left", fontsize=12.5, fontweight="bold")


def num(s):
    """Colonne nullable pandas -> float numpy (NA -> nan)."""
    return pd.to_numeric(s, errors="coerce").astype("float64")


def as_level(s):
    """Catégorie / booléen nullable -> chaîne, NA explicite."""
    return s.astype("object").where(s.notna(), "NA").astype(str)


def bar_labels(ax, x, heights, fmt, offset, inside_n=None):
    """Valeur au-dessus de chaque barre ; effectif discret dans la barre si fourni."""
    for i, h in zip(x, heights):
        ax.text(i, h + offset, fmt(h), ha="center", va="bottom", fontsize=8.5, color=INK)
    if inside_n is not None:
        for i, n in zip(x, inside_n):
            ax.text(i, 0, f" {n / 1000:,.0f}k" if n >= 1000 else f" {n}",
                    ha="center", va="bottom", fontsize=7.5, color="white")


def draw_box(ax, xc, y, col, bw=0.30):
    """Boîte à moustaches manuelle (quartiles, moustaches à 1,5 × IQR)."""
    q1, q2, q3 = np.quantile(y, [0.25, 0.50, 0.75])
    iqr = q3 - q1
    w_lo, w_hi = max(y.min(), q1 - 1.5 * iqr), min(y.max(), q3 + 1.5 * iqr)
    ax.fill([xc - bw, xc + bw, xc + bw, xc - bw], [q1, q1, q3, q3],
            facecolor=col, alpha=0.18, edgecolor=col, lw=1.2, zorder=2)
    ax.plot([xc - bw, xc + bw], [q2, q2], color=col, lw=2.2, zorder=3, solid_capstyle="butt")
    for a_, b_ in [(q3, w_hi), (w_lo, q1)]:
        ax.plot([xc, xc], [a_, b_], color=col, lw=1, zorder=2)
    for w in (w_lo, w_hi):
        ax.plot([xc - bw / 2, xc + bw / 2], [w, w], color=col, lw=1, zorder=2)


def box_panel(ax, d, group_col, order, labels, title, colors, rng):
    """Boîtes de log10(montant) par groupe + jitter échantillonné + médiane et n."""
    lsev = np.log10(d["paid"])
    top = lsev.max() + 0.2
    for i, (g, col) in enumerate(zip(order, colors), start=1):
        y = lsev[d[group_col] == g].dropna().to_numpy()
        if y.size == 0:
            continue
        samp = rng.choice(y, size=min(400, y.size), replace=False)
        ax.scatter(i + (rng.random(samp.size) - 0.5) * 0.24, samp,
                   s=5, color=col, alpha=0.22, lw=0, zorder=1)
        draw_box(ax, i, y, col)
        ax.plot(i, np.log10(np.mean(10 ** y)), "D", ms=7, mfc="white", mec=col, mew=1.6, zorder=4)
        ax.text(i, top, f"médiane ${10 ** np.median(y):,.0f}\nn = {y.size:,}",
                ha="center", va="bottom", fontsize=8.5, color=INK2, linespacing=1.4)
    ax.set_xticks(range(1, len(order) + 1), labels)
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(0.4, len(order) + 0.6)
    ax.set_ylim(lsev.quantile(0.001) - 0.2, top + 0.75)
    ax.set_yticks([2, 3, 4, 5, 6])
    ax.yaxis.set_major_formatter(pow10)
    ax.set_title(title)


def box_legend(fig):
    handles = [Line2D([], [], color=INK2, lw=2.2, label="médiane"),
               Patch(facecolor=INK2, alpha=0.18, edgecolor=INK2, label="intervalle interquartile"),
               Line2D([], [], color=INK2, lw=1, label="moustaches (1,5 × IQR)"),
               Line2D([], [], marker="D", ls="none", mfc="white", mec=INK2, mew=1.6, ms=7,
                      label="moyenne")]
    fig.legend(handles=handles, loc="upper right", ncol=4, bbox_to_anchor=(1.0, 1.0))


# --- Tests d'association : on rapporte la taille d'effet --------------------
def cramers_v(x, y):
    """Khi² d'indépendance et V de Cramér entre deux variables catégorielles."""
    ct = pd.crosstab(x, y)
    chi2, p, dof, _ = stats.chi2_contingency(ct, correction=False)
    v = np.sqrt(chi2 / (ct.to_numpy().sum() * (min(ct.shape) - 1)))
    return chi2, p, v


def kruskal_eps2(values, groups):
    """Kruskal-Wallis et epsilon² (part de variance des rangs expliquée par le groupe)."""
    samples = [v.to_numpy() for _, v in values.groupby(groups, observed=True) if len(v) >= 30]
    h, p = stats.kruskal(*samples)
    n, k = sum(len(s) for s in samples), len(samples)
    return h, p, (h - k + 1) / (n - k)


# -------------------------------------------------------------------------
# 1. CHARGEMENT
# -------------------------------------------------------------------------
pd.set_option("future.no_silent_downcasting", True)
print("Chargement…")
df = pd.read_parquet(DATA)
expo = pd.read_parquet(EXPO)
rng = np.random.default_rng(42)
N = len(df)

# Valeurs manquantes mesurées sur les colonnes d'origine, avant les dérivées
NOT_MISSING = ["building_coverage", "deductible_amount",          # doublons nominaux
               "coverage_ratio", "at_cap", "paid_gt_cov"]          # définies si payé seulement
miss = df.drop(columns=NOT_MISSING, errors="ignore").isna().mean().mul(100).sort_values()
miss = miss[miss >= 0.05]

df["date"] = df["loss_month_period"].dt.to_timestamp()
df["year"] = num(df["loss_year"]).astype(int)
df["paid"] = num(df["paid_building_real"]).where(lambda s: s > 0)
df["coverage"] = num(df["building_coverage_real"])
df["ratio_cov"] = df["paid"] / df["coverage"].where(lambda s: s > 0)
df["paid_rate"] = df["paid_flag"].astype(float)
df["elev_lbl"] = df["elevated_building"].map({True: "Surélevé", False: "Non surélevé"})

recent_from = int(df.loc[df["recent_claim"], "year"].min())
closed = df[~df["recent_claim"]].copy()            # analyses de paiement et de montant
payd = closed[closed["paid"].notna()]              # sinistres payés, dossiers clos
overall = closed["paid_rate"].mean()
print(f"  {N:,} sinistres, {df['year'].min()}–{df['year'].max()} "
      f"({(~df['recent_claim']).sum():,} hors {recent_from}+)")

LABELS = {"paid_building_real": "Montant payé", "building_value_real": "Valeur du bâtiment",
          "primary_residence": "Résidence principale", "floodEvent": "Événement nommé",
          "flood_duration": "Durée de submersion", "water_depth": "Profondeur d'eau",
          "building_age": "Âge du bâtiment", "deductible_amount_real": "Franchise",
          "flood_zone_group": "Zone d'inondation", "county_fips": "Comté", "n_floors": "Étages"}

# -------------------------------------------------------------------------
# 2. TABLEAUX DESCRIPTIFS
# -------------------------------------------------------------------------
num_cols = ["paid_building_real", "building_coverage_real", "deductible_amount_real",
            "building_age", "water_depth", "flood_duration", "building_value_real"]
desc = df[num_cols].apply(num).describe(percentiles=[.01, .25, .5, .75, .95, .99]).T
desc["missing_%"] = df[num_cols].isna().mean().mul(100).round(1)
desc.round(1).to_csv(OUT / "summary_numeric.csv")

CAT = {"flood_zone_group": "Zone d'inondation", "elevated_building": "Bâtiment surélevé",
       "primary_residence": "Résidence principale", "n_floors": "Étages",
       "era": "Époque", "state": "État"}
cat_rows = []
for c in CAT:
    t = closed.groupby(as_level(closed[c])).agg(n=("id", "size"), paid_rate=("paid_rate", "mean"),
                                                median_paid=("paid", "median"))
    t["share_%"] = 100 * t["n"] / len(closed)
    t.insert(0, "variable", c)
    cat_rows.append(t.reset_index(names="level"))
pd.concat(cat_rows).round(4).to_csv(OUT / "summary_categorical.csv", index=False)

# Tests : paiement (khi²) et montant (Kruskal-Wallis sur les payés)
tests = []
for c, lbl in CAT.items():
    chi2, p, v = cramers_v(as_level(closed[c]), closed["paid_flag"].astype(bool))
    tests.append({"cible": "paiement", "variable": c, "test": "khi²", "stat": chi2, "p": p,
                  "effet": "V de Cramér", "valeur": v})
    h, p, e2 = kruskal_eps2(np.log(payd["paid"]), as_level(payd[c]))
    tests.append({"cible": "montant", "variable": c, "test": "Kruskal-Wallis", "stat": h, "p": p,
                  "effet": "epsilon²", "valeur": e2})
tests = pd.DataFrame(tests)
tests.to_csv(OUT / "tests.csv", index=False)
effect = {(r.cible, r.variable): r.valeur for r in tests.itertuples()}

print("\nFigures :")
# -------------------------------------------------------------------------
# FIGURE 1 — Données : valeurs manquantes
# -------------------------------------------------------------------------
fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1, 1.15]},
                           layout="constrained")
a.barh([LABELS.get(c, c) for c in miss.index], miss.values, height=0.65, color=BLUE)
for i, v in enumerate(miss.values):
    a.text(v + 0.6, i, f"{v:.1f} %", va="center", fontsize=8.5, color=INK)
a.set_xlim(0, miss.max() * 1.2)
a.xaxis.set_major_formatter(pct)
a.grid(axis="y", visible=False)
a.grid(axis="x", visible=True)
a.tick_params(axis="y", length=0)
a.set_title(f"(a) Part de valeurs manquantes — {len(miss)} colonnes")

decade = (df["year"] // 10) * 10
key = miss.sort_values(ascending=False).index[:6]
miss_dec = df[key].isna().groupby(decade).mean().mul(100)
for i, c in enumerate(key):
    b.plot(miss_dec.index, miss_dec[c], "-o", color=SERIES[i], lw=2, ms=4.5,
           mec="white", mew=0.8, label=LABELS.get(c, c))
b.set_xticks(miss_dec.index, [f"{d}s" for d in miss_dec.index])
b.yaxis.set_major_formatter(pct)
b.set_ylim(0, 100)
b.set_title("(b) Le manque dépend de l'époque (par décennie)")
b.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
suptitle(fig, "Valeurs manquantes : aucune n'est aléatoire, d'où les indicatrices de manque")
export(fig, "fig1_missing")

# -------------------------------------------------------------------------
# FIGURE 2 — Les sinistres arrivent par catastrophes
# -------------------------------------------------------------------------
monthly = df.groupby("date").size()
monthly = monthly.reindex(pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS"),
                          fill_value=0)
eg = df["event_group"].astype(str)
named = ~eg.str.startswith("mois ")          # « mois AAAA-MM » = sinistres sans événement nommé
top_ev = eg[named].value_counts().head(8).index
peaks = sorted((df.loc[eg == e, "date"].mode().iloc[0], e) for e in top_ev)

by_ev = df.assign(eg=eg).groupby("eg").agg(n=("id", "size"), amount=("paid", "sum")) \
          .sort_values("amount", ascending=False)
cum_amt = by_ev["amount"].cumsum() / by_ev["amount"].sum()
cum_n = by_ev["n"].cumsum() / N
rank = np.arange(1, len(by_ev) + 1)
top3 = by_ev.index[:3]
top3_amt, top3_n = cum_amt.iloc[2], cum_n.iloc[2]
top10_amt = cum_amt.iloc[9]
top8_claims = eg.isin(top_ev).mean()

fig, (a, b) = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [2.3, 1]},
                           layout="constrained")
ymax = monthly.max() * 1.22
last, level = None, 0
for peak, name in peaks:
    a.axvspan(peak - pd.DateOffset(months=2), peak + pd.DateOffset(months=2),
              color=BAND, lw=0, zorder=0)
    level = level + 1 if last is not None and (peak - last).days < 540 else 0
    a.text(peak, ymax * (0.985 - 0.07 * level), name.replace("Hurricane ", ""),
           ha="center", va="top", fontsize=8.5, color=INK2, style="italic")
    last = peak
a.plot(monthly.index, monthly.values, color=INK, lw=0.9, zorder=2)
a.set_ylim(0, ymax)
a.set_xlim(monthly.index[0], monthly.index[-1])
a.yaxis.set_major_formatter(thousands)
a.set_ylabel("Sinistres par mois")
a.set_title(f"(a) Sinistres mensuels — les 8 plus grands événements = {top8_claims:.0%} "
            "des sinistres")

b.plot(rank, 100 * cum_amt.values, color=BLUE, lw=2, label="montants payés")
b.plot(rank, 100 * cum_n.values, color=ORANGE, lw=2, label="nombre de sinistres")
b.axvline(3, ls=":", color=MUTED, lw=1)
b.text(3.3, 100 * top3_amt, f"{top3_amt:.0%}", color=BLUE, fontsize=9, va="bottom")
b.text(3.3, 100 * top3_n, f"{top3_n:.0%}", color=ORANGE, fontsize=9, va="top")
b.set_xscale("log")
b.set_xlim(1, len(by_ev))
b.set_ylim(0, 100)
b.yaxis.set_major_formatter(pct)
b.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
b.set_xlabel("Événements classés par montant payé (échelle log)")
b.legend(loc="lower right")
b.set_title(f"(b) Part cumulée — {', '.join(e.replace('Hurricane ', '') for e in top3)}")
suptitle(fig, f"Les sinistres arrivent par catastrophes : 3 ouragans = {top3_amt:.0%} "
              "des montants payés")
export(fig, "fig2_events")

# -------------------------------------------------------------------------
# FIGURE 3 — Risque par zone, rapporté aux polices en vigueur (2010-2024)
# -------------------------------------------------------------------------
Y0, Y1 = 2010, 2024        # années d'exposition complètes, dossiers clos
zones = ["V*", "A*", "X"]
ex = expo[expo["year"].between(Y0, Y1) & expo["flood_zone_group"].isin(zones)]
ex = ex.groupby([ex["flood_zone_group"].astype(str), "year"])["policy_years"].sum().astype(float)
cl = df[df["year"].between(Y0, Y1) & df["flood_zone_group"].isin(zones)]
cl = cl.groupby([cl["flood_zone_group"].astype(str), "year"]) \
       .agg(n=("id", "size"), amount=("paid", "sum"))
zy = cl.join(ex.rename("py"), how="inner")
zy["freq"] = 1000 * zy["n"] / zy["py"]
pool = zy.groupby(level=0)[["n", "amount", "py"]].sum().reindex(zones)
pool["freq"] = 1000 * pool["n"] / pool["py"]          # sinistres pour 1 000 polices-années
pool["cost"] = pool["amount"] / pool["py"]            # USD payés par police-année
pool["share_py"] = pool["py"] / pool["py"].sum()

fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), gridspec_kw={"width_ratios": [1, 1, 1.8]},
                         layout="constrained")
x = np.arange(len(zones))
cols = [ZONE_COL[z] for z in zones]
for ax, col_, fmt, title in [
        (axes[0], "freq", lambda h: f"{h:.1f}", "(a) Sinistres pour 1 000 polices-années"),
        (axes[1], "cost", lambda h: f"${h:,.0f}", "(b) Montant payé par police-année")]:
    ax.bar(x, pool[col_], 0.62, color=cols)
    bar_labels(ax, x, pool[col_], fmt, pool[col_].max() * 0.015)
    ax.set_xticks(x, [f"{z}\n{s:.0%} des polices" for z, s in zip(zones, pool["share_py"])])
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, pool[col_].max() * 1.15)
    ax.set_title(title)
axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
c = axes[2]
for z in zones:
    s = zy.loc[z, "freq"]
    c.plot(s.index, s.values, "-o", color=ZONE_COL[z], lw=2, ms=4, mec="white", mew=0.8, label=z)
c.set_yscale("log")
c.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
c.set_xticks(range(Y0, Y1 + 1, 2))
c.legend(loc="upper left", ncol=3)
c.set_title("(c) Fréquence annuelle (échelle log) : les pics sont les années d'ouragan")
suptitle(fig, f"Risque par zone d'inondation, {Y0}–{Y1} : la zone V cumule fréquence et coût")
export(fig, "fig3_zone_risk")

# -------------------------------------------------------------------------
# FIGURE 4 — Cible 1 : probabilité de paiement
# -------------------------------------------------------------------------
yr = df.groupby("year").agg(n=("id", "size"), rate=("paid_rate", "mean"),
                            recoded=("paid_na_to_zero", lambda s: s.astype(float).sum()))
yr["rate_nr"] = yr["rate"] * yr["n"] / (yr["n"] - yr["recoded"])
yr = yr[yr.index < recent_from]

panels = ["flood_zone_group", "elevated_building", "primary_residence", "n_floors", "era"]
fig, axes = plt.subplots(2, 3, figsize=(14.5, 7.8), layout="constrained")
for ax, c in zip(axes.flat, panels):
    g = closed.groupby(as_level(closed[c])).agg(rate=("paid_rate", "mean"), n=("id", "size"))
    g = g[g["n"] >= 100]
    if c == "flood_zone_group":
        g = g.reindex([z for z in ["V*", "A*", "X", "D", "inconnu"] if z in g.index])
    x = np.arange(len(g))
    hi = np.abs(g["rate"] - overall) == np.abs(g["rate"] - overall).max()
    ax.bar(x, 100 * g["rate"], 0.62, color=np.where(hi, ORANGE, BLUE))
    ax.axhline(100 * overall, ls=":", color=MUTED, lw=1)
    bar_labels(ax, x, 100 * g["rate"], lambda h: f"{h:.0f} %", 1.2, inside_n=g["n"])
    ax.set_xticks(x, [RENAME.get(i, i) for i in g.index], fontsize=8.5 if len(g) > 5 else 9)
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(pct)
    ax.set_title(f"{CAT[c]} — V = {effect[('paiement', c)]:.2f}")
f = axes.flat[5]
f.plot(yr.index, 100 * yr["rate"], color=BLUE, lw=2, label="tous les sinistres")
f.plot(yr.index, 100 * yr["rate_nr"], color=INK2, lw=1.2, ls="--",
       label="hors paiements NA recodés « non payé »")
f.axhline(100 * overall, ls=":", color=MUTED, lw=1)
f.yaxis.set_major_formatter(pct)
f.set_ylim(40, 100)
f.legend(loc="lower right", fontsize=7.5)
f.set_title("Par année : avant 2018, le « non payé » vient surtout du recodage")
suptitle(fig, f"Cible 1 — taux de paiement {overall:.0%} (pointillés) ; effets faibles "
              "(V de Cramér), l'écart entre époques reflète surtout le recodage")
export(fig, "fig4_payment")

# -------------------------------------------------------------------------
# FIGURE 5 — Cible 2 : distribution du montant payé
# -------------------------------------------------------------------------
sev = payd["paid"]
ratio = payd["ratio_cov"].dropna().clip(upper=1.2)
at_cap = (payd["ratio_cov"] >= 0.99).mean()
skew_log = stats.skew(np.log(sev))

fig, (a, b, c) = plt.subplots(1, 3, figsize=(15, 4.4), layout="constrained")
lsev = np.log10(sev)
lo = np.floor(lsev.quantile(0.001) * 2) / 2
a.hist(lsev[lsev >= lo], bins=70, color=BLUE, edgecolor="white", linewidth=0.3)
a.set_ylim(0, a.get_ylim()[1] * 1.15)
ytop = a.get_ylim()[1]
for q, ls, name in [(0.5, "--", "médiane"), (0.95, ":", "q95")]:
    v = np.log10(sev.quantile(q))
    a.axvline(v, ls=ls, color=INK, lw=1.1)
    a.text(v, ytop * 0.985, f"{name}\n${10 ** v:,.0f}", fontsize=8.5, color=INK, ha="center",
           va="top", linespacing=1.3, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
a.set_xlim(lo, lsev.max() + 0.1)
a.set_xticks([t for t in [1, 2, 3, 4, 5, 6] if t >= lo])
a.xaxis.set_major_formatter(pow10)
a.yaxis.set_major_formatter(thousands)
a.set_xlabel("Montant payé (USD réels, échelle log)")
a.set_ylabel("Sinistres payés")
a.set_title(f"(a) Moyenne ${sev.mean():,.0f}, médiane ${sev.median():,.0f}")

b.hist(ratio, bins=60, color=BLUE, edgecolor="white", linewidth=0.3)
b.axvline(1, ls="--", color=INK, lw=1.1)
b.text(0.98, b.get_ylim()[1] * 0.97, "plafond", ha="right", va="top", fontsize=8.5, color=INK)
b.yaxis.set_major_formatter(thousands)
b.set_xlabel("Montant payé / couverture bâtiment")
b.set_title(f"(b) {at_cap:.1%} des sinistres payés atteignent le plafond")

cap = payd.groupby("era", observed=True)["ratio_cov"].agg(lambda s: (s >= 0.99).mean())
x = np.arange(len(cap))
c.bar(x, 100 * cap.values, 0.62, color=np.where(cap.values == cap.max(), ORANGE, NEUTRAL))
bar_labels(c, x, 100 * cap.values, lambda h: f"{h:.1f} %", 0.25)
c.set_xticks(x, cap.index.astype(str))
c.tick_params(axis="x", length=0)
c.yaxis.set_major_formatter(pct)
c.set_ylim(0, 100 * cap.max() * 1.2)
c.set_title("(c) Part au plafond, par époque")
suptitle(fig, "Cible 2 — montant payé : asymétrique (loi log-normale ou Gamma), tronqué par "
              "le plafond")
export(fig, "fig5_severity")

# -------------------------------------------------------------------------
# FIGURE 6 — Ce qui fait varier le montant
# -------------------------------------------------------------------------
zones_box = ["V*", "A*", "X"]
eras = list(payd["era"].cat.categories)
payd["event_lbl"] = np.where(payd["major_event"], "Helene, Ian,\nKatrina", "autres")
eps_event = kruskal_eps2(np.log(payd["paid"]), payd["event_lbl"])[2]
med_event = payd.groupby("major_event")["paid"].median()
rho_num = {c: payd[c].astype(float).corr(payd["paid"], method="spearman")
           for c in ["building_coverage_real", "deductible_amount_real", "building_age",
                     "loss_year", "water_depth"]}

fig, axes = plt.subplots(1, 4, figsize=(18, 5.6), sharey=True,
                         gridspec_kw={"width_ratios": [2, 4.2, 3, 2]}, layout="constrained")
box_panel(axes[0], payd, "event_lbl", ["autres", "Helene, Ian,\nKatrina"],
          ["autres", "Helene, Ian,\nKatrina"], f"(a) Événement — ε² = {eps_event:.3f}",
          [NEUTRAL, ORANGE], rng)
box_panel(axes[1], payd, "era", eras, eras,
          f"(b) Époque — ε² = {effect[('montant', 'era')]:.3f}", [BLUE] * len(eras), rng)
box_panel(axes[2], payd, "flood_zone_group", zones_box, zones_box,
          f"(c) Zone — ε² = {effect[('montant', 'flood_zone_group')]:.3f}",
          [ZONE_COL[z] for z in zones_box], rng)
box_panel(axes[3], payd, "elev_lbl", ["Non surélevé", "Surélevé"], ["Non\nsurélevé", "Surélevé"],
          f"(d) Surélévation — ε² = {effect[('montant', 'elevated_building')]:.3f}",
          [BLUE, ORANGE], rng)
for ax in axes[1:]:
    ax.tick_params(axis="y", labelleft=False)
axes[0].set_ylabel("Montant payé (USD réels, échelle log)")
box_legend(fig)
suptitle(fig, "Le montant dépend surtout de l'événement et de l'époque ; zone et surélévation "
              "pèsent peu")
export(fig, "fig6_severity_drivers")

# -------------------------------------------------------------------------
# FIGURE 7 — Synthèse : corrélations de rang
# -------------------------------------------------------------------------
corr_cols = {"paid_flag": "Payé (0/1)", "paid_building_real": "Montant payé",
             "building_coverage_real": "Couverture", "deductible_amount_real": "Franchise",
             "building_age": "Âge du bâtiment", "loss_year": "Année",
             "elevated_building": "Surélevé", "primary_residence": "Résidence principale",
             "water_depth": "Profondeur d'eau*", "flood_duration": "Durée de submersion*"}
cdf = closed[list(corr_cols)].apply(num)
cdf.loc[cdf["paid_building_real"] <= 0, "paid_building_real"] = np.nan   # montant si payé
C = cdf.rename(columns=corr_cols).corr(method="spearman")
C.iloc[0, 1] = C.iloc[1, 0] = np.nan      # montant défini seulement si payé

fig, ax = plt.subplots(figsize=(8.8, 7.2), layout="constrained")
im = ax.imshow(C.mask(np.triu(np.ones_like(C, dtype=bool))), cmap=DIV, vmin=-1, vmax=1)
ax.set_xticks(range(len(C) - 1), C.columns[:-1], rotation=40, ha="right")
ax.set_yticks(range(1, len(C)), C.columns[1:])
ax.set_xlim(-0.5, len(C) - 1.5)
ax.set_ylim(len(C) - 0.5, 0.5)
ax.grid(False)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)
for i in range(len(C)):
    for j in range(i):
        v = C.iat[i, j]
        if np.isnan(v):
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, color=GRID, lw=0))
            ax.text(j, i, "—", ha="center", va="center", fontsize=8, color=INK2)
            continue
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                color="white" if abs(v) > 0.55 else INK)
cb = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
cb.set_label("ρ de Spearman", color=INK2)
cb.outline.set_visible(False)
ax.set_title("* connu seulement après le sinistre (hors modèle prédictif)")
suptitle(fig, "Corrélations de rang : cibles et variables candidates")
export(fig, "fig7_correlation")

# -------------------------------------------------------------------------
# FIGURE 8 (annexe) — Profondeur d'eau et montant
# -------------------------------------------------------------------------
d = payd[["water_depth", "paid"]].apply(num).dropna()
d = d[d["water_depth"].between(0, d["water_depth"].quantile(0.99))]
d["depth_bin"] = (d["water_depth"] // 4) * 4 + 2           # classes de 4 unités
by_depth = d.groupby("depth_bin")["paid"].agg(
    med="median", n="size", q25=lambda s: s.quantile(.25), q75=lambda s: s.quantile(.75))
by_depth = by_depth[by_depth["n"] >= 200]
rho_depth = d["water_depth"].corr(d["paid"], method="spearman")

fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.6), layout="constrained")
dl = d[np.log10(d["paid"]) >= 2]
hb = a.hexbin(dl["water_depth"], np.log10(dl["paid"]), gridsize=(40, 22), bins="log", cmap=SEQ,
              mincnt=1, linewidths=0)
cb = fig.colorbar(hb, ax=a, pad=0.02)
cb.set_label("Sinistres par cellule (log)", color=INK2)
cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
cb.ax.yaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
cb.outline.set_visible(False)
a.grid(False)
a.set_yticks([2, 3, 4, 5, 6])
a.yaxis.set_major_formatter(pow10)
a.set_xlabel("Profondeur d'eau (valeur brute, unité mixte pieds / pouces)")
a.set_ylabel("Montant payé (USD réels, log)")
a.set_title(f"(a) Densité des sinistres — ρ de Spearman = {rho_depth:.2f}")
b.fill_between(by_depth.index, by_depth["q25"], by_depth["q75"], color=BLUE, alpha=0.18,
               lw=0, label="intervalle interquartile")
b.plot(by_depth.index, by_depth["med"], color=BLUE, lw=2, label="médiane")
b.yaxis.set_major_formatter(kdollars)
b.set_ylim(0, by_depth["q75"].max() * 1.08)
b.set_xlabel("Profondeur d'eau (valeur brute, unité mixte pieds / pouces)")
b.set_title("(b) Montant payé selon la profondeur (classes de 4 unités)")
b.legend(loc="upper left")
suptitle(fig, "Profondeur d'eau et montant payé (connue après coup, hors modèle prédictif)")
export(fig, "fig8_depth")

# -------------------------------------------------------------------------
# FIGURE 9 (annexe) — Géographie
# -------------------------------------------------------------------------
geo = df.groupby(df["state"].astype(str)).agg(n=("id", "size"), total=("paid", "sum")) \
        .sort_values("n")
county_n = df.loc[df["county_fips"].astype(str) != "inconnu", "county_fips"].astype(str) \
             .value_counts()
top15_share = county_n.head(15).sum() / N

fig, ax = plt.subplots(figsize=(8.5, 4.8), layout="constrained")
ax.barh(geo.index, geo["n"], height=0.62, color=BLUE)
for i, (n, t) in enumerate(zip(geo["n"], geo["total"])):
    ax.text(n + geo["n"].max() * 0.015, i,
            f"{n / 1000:,.0f}k ({n / N:.0%})  ·  ${t / 1e9:,.1f} Md payés",
            va="center", fontsize=8.5, color=INK)
ax.set_xlim(0, geo["n"].max() * 1.6)
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.xaxis.set_major_formatter(thousands)
ax.tick_params(axis="y", length=0)
ax.set_title(f"{len(county_n)} comtés ; les 15 premiers = {top15_share:.0%} des sinistres")
suptitle(fig, "Sinistres et montants payés par État")
export(fig, "fig9_geography")

# -------------------------------------------------------------------------
# FIGURE 10 (annexe) — Validation : plis par événement et découpage temporel
# -------------------------------------------------------------------------
folds = sorted(df["fold"].unique())
groups = [("fold", folds, [f"pli {f}" for f in folds], "Plis par événement (validation)"),
          ("split", ["train", "valid", "test"],
           ["train\n≤ 2016", "valid\n2017–2020", "test\n≥ 2021"], "Découpage temporel"),
          ("major_event", [False, True], ["autres", "Helene, Ian,\nKatrina"],
           f"Grands ouragans ({df['major_event'].mean():.0%} des sinistres)")]
fig, axes = plt.subplots(2, 3, figsize=(14, 7.8), sharey="row",
                         gridspec_kw={"width_ratios": [5, 3, 2.2]}, layout="constrained")
gstats = [closed.groupby(k, observed=True).agg(rate=("paid_rate", "mean"), med=("paid", "median"),
                                               n=("id", "size")).reindex(o)
          for k, o, _, _ in groups]
med_max = max(g["med"].max() for g in gstats)
for j, ((key_, order, labels, title), g) in enumerate(zip(groups, gstats)):
    x = np.arange(len(g))
    top, bot = axes[0, j], axes[1, j]
    top.bar(x, 100 * g["rate"], 0.62, color=BLUE)
    top.axhline(100 * overall, ls=":", color=MUTED, lw=1)
    bar_labels(top, x, 100 * g["rate"], lambda h: f"{h:.0f} %", 1.2, inside_n=g["n"])
    top.set_ylim(0, 100)
    top.yaxis.set_major_formatter(pct)
    top.set_title(f"({'abc'[j]}) {title}")
    bot.bar(x, g["med"], 0.62, color=BLUE)
    bar_labels(bot, x, g["med"], lambda h: f"${h / 1000:,.0f}k", med_max * 0.015)
    bot.set_ylim(0, med_max * 1.15)
    bot.yaxis.set_major_formatter(kdollars)
    for ax in (top, bot):
        ax.set_xticks(x, labels)
        ax.tick_params(axis="x", length=0)
axes[0, 0].set_ylabel("Taux de paiement")
axes[1, 0].set_ylabel("Montant payé médian (USD réels)")
suptitle(fig, f"Validation : la cible change d'un pli et d'une période à l'autre "
              f"(pointillés : taux moyen {overall:.0%}, dossiers clos)")
export(fig, "fig10_validation")

# -------------------------------------------------------------------------
# CHIFFRES CLÉS (cités dans le rapport)
# -------------------------------------------------------------------------
split_rate = gstats[1]["rate"]
unpaid = closed[~closed["paid_flag"].astype(bool)]
recoded_share = unpaid.groupby(unpaid["year"] >= 2018)["paid_na_to_zero"] \
                      .agg(lambda s: s.astype(float).mean())
key_numbers = {
    "n_claims": N, "years": [int(df["year"].min()), int(df["year"].max())],
    "n_closed": len(closed), "recent_from": recent_from,
    "n_counties": len(county_n), "top15_counties_share": top15_share,
    "paid_rate": overall,
    "paid_rate_train_test": {k: float(v) for k, v in split_rate.items()},
    "severity_median": float(sev.median()), "severity_mean": float(sev.mean()),
    "severity_q95": float(sev.quantile(.95)), "skew_log_severity": float(skew_log),
    "at_cap": float(at_cap), "at_cap_by_era": cap.round(4).to_dict(),
    "top3_events": list(top3), "top3_share_amount": top3_amt, "top3_share_claims": top3_n,
    "top10_share_amount": top10_amt, "top8_share_claims": top8_claims,
    "zone_freq_per_1000": pool["freq"].round(2).to_dict(),
    "zone_cost_per_policy_year": pool["cost"].round(1).to_dict(),
    "zone_share_policies": pool["share_py"].round(4).to_dict(),
    "zone_share_claims": (df["flood_zone_group"].astype(str).value_counts(normalize=True)
                          .round(4).to_dict()),
    "unpaid_from_recoding": {"avant 2018": float(recoded_share[False]),
                             "2018+": float(recoded_share[True])},
    "severity_median_major_event": {"autres": float(med_event[False]),
                                    "Helene/Ian/Katrina": float(med_event[True])},
    "severity_median_by_era": payd.groupby("era", observed=True)["paid"].median()
                                  .round(0).to_dict(),
    "epsilon2_major_event": eps_event,
    "spearman_paid": {k: round(v, 3) for k, v in rho_num.items()},
    "spearman_depth_paid_0_q99": rho_depth,
    "missing_pct": miss.round(2).to_dict(),
    "effect_sizes": {f"{r.cible}:{r.variable}": round(r.valeur, 4) for r in tests.itertuples()},
}
(OUT / "key_numbers.json").write_text(json.dumps(key_numbers, indent=1, ensure_ascii=False,
                                                 default=str))

print("\n========== Chiffres clés ==========")
print(f" Sinistres                 : {N:,} ({len(closed):,} clos)")
print(f" Taux de paiement          : {overall:.1%}  (train {split_rate['train']:.0%}, "
      f"test {split_rate['test']:.0%})")
print(f" Montant médian / moyen    : ${sev.median():,.0f} / ${sev.mean():,.0f}")
print(f" Au plafond                : {at_cap:.1%}")
print(f" 3 plus grands événements  : {top3_amt:.0%} des montants, {top3_n:.0%} des sinistres")
print(" Fréquence /1000 pol.-ans  : " + ", ".join(f"{z} {v:.1f}" for z, v in pool["freq"].items()))
print(" Coût / police-année       : " + ", ".join(f"{z} ${v:,.0f}" for z, v in pool["cost"].items()))
print(f" Non payés issus du recodage: avant 2018 {recoded_share[False]:.0%}, "
      f"2018+ {recoded_share[True]:.0%}")
print(f" Montant médian grands ouragans / autres: ${med_event[True]:,.0f} / "
      f"${med_event[False]:,.0f} (ε² = {eps_event:.3f})")
print(" Spearman avec le montant : " + ", ".join(f"{k} {v:.2f}" for k, v in rho_num.items()))
print("\n Tailles d'effet :")
print(tests.pivot(index="variable", columns="cible", values="valeur").round(3).to_string())
print(f"\n Sorties dans : {OUT}")
