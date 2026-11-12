"""
EDA complète — claims_clean (NFIP, Région IV)
=============================================

Reprend le style des scripts MATLAB (u2.m, variance_decomposition.m) :
palette fixe, panneaux (a)/(b), titres porteurs du message, boîtes à
moustaches annotées, barres par année étiquetées, bandes d'événements,
export PNG 300 dpi + PDF vectoriel.

Adapté à 621k sinistres : aucun chiffre codé en dur, échelle log pour les
montants, médianes/quantiles plutôt que moyenne/écart-type, hexbin au lieu
de nuages de points, échantillon pour le jitter.

Figures produites (EDA/figures/) :
  fig1_missing        (a) % manquant par colonne | (b) % manquant par décennie
  fig2_annual         (a) sinistres par année    | (b) taux de paiement & sévérité médiane
  fig3_monthly        Sinistres mensuels, grands événements ombrés
  fig4_severity       (a) distribution log du montant payé | (b) ratio payé / couverture
  fig5_boxes          Sévérité par zone (a) et par élévation (b) — boîtes annotées
  fig6_frequency      Taux de paiement par variable catégorielle
  fig7_depth          (a) hexbin profondeur × sévérité | (b) médiane par profondeur
  fig8_geography      (a) top états | (b) top comtés
  fig9_correlation    Corrélations de Spearman
  fig10_model_vars    Nouvelles variables (v2 seulement) : taux de paiement et
                      montant médian par fold, split et major_event

Lancer depuis la racine du projet :
  python EDA/EDA.py                                   # v2 (défaut) : claims_model -> figures_v2
  python EDA/EDA.py Data_cleaning/clean/claims_clean.parquet EDA/figures   # v1
Le dataset v2 se crée avec : python EDA/dsEDA.py
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

# -------------------------------------------------------------------------
# 0. CHEMINS & STYLE
# -------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    ROOT / "EDA" / "data" / "claims_model.parquet"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "EDA" / "figures_v2"
if not DATA.exists():
    sys.exit(f"{DATA} introuvable. Lancer d'abord : python EDA/dsEDA.py")
DERIVED = ["date", "paid", "coverage", "ratio_cov", "paid_rate", "year", "elev_lbl",
           "coverage_ratio", "at_cap", "foundation_rr2", "event_group", "major_event",
           "split", "era", "building_age_missing", "deductible_missing",
           "primary_residence_missing", "recent_claim", "paid_gt_cov", "fold"]
OUT.mkdir(parents=True, exist_ok=True)


# --- Palette (validée daltonisme, ordre fixe) et encres -----------------------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
BLUE, ORANGE = SERIES[0], SERIES[1]
NEUTRAL = "#c9c8c2"     # barres non mises en avant
INK = "#0b0b0b"         # texte principal
INK2 = "#52514e"        # texte secondaire, axes
MUTED = "#8a8984"       # lignes de référence
GRID = "#e6e5e1"
BAND = "#efeeea"        # bandes d'événements
SEQ = LinearSegmentedColormap.from_list(
    "seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("div", [ORANGE, "#f0efec", BLUE])

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10,
    "text.color": INK,
    "axes.labelcolor": INK2,
    "axes.edgecolor": INK2,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "axes.titlesize": 11,
    "axes.titlelocation": "left",
    "axes.titlepad": 10,
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.frameon": False,
    "legend.fontsize": 8.5,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "text.parse_math": False,   # les « $ » des montants ne sont pas des formules
})

dollars = FuncFormatter(lambda v, _: f"${v:,.0f}")
kdollars = FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k")
pow10 = FuncFormatter(lambda v, _: {1: "$10", 2: "$100", 3: "$1k", 4: "$10k", 5: "$100k",
                                     6: "$1M"}.get(round(v), ""))
thousands = FuncFormatter(lambda v, _: f"{v / 1000:,.0f}k" if v >= 1000 else f"{v:,.0f}")
pct = FuncFormatter(lambda v, _: f"{v:.0f} %")


def export(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}.png / .pdf")


def suptitle(fig, text):
    fig.suptitle(text, x=0.01, ha="left", fontsize=12.5, fontweight="bold")


def num(s):
    """Colonne nullable pandas -> float numpy (NA -> nan)."""
    return pd.to_numeric(s, errors="coerce").astype("float64")


def bar_labels(ax, x, heights, fmt, offset, inside_n=None):
    """Valeur au-dessus de chaque barre ; effectif discret sous l'axe si fourni."""
    for i, h in zip(x, heights):
        ax.text(i, h + offset, fmt(h), ha="center", va="bottom", fontsize=8.5, color=INK)
    if inside_n is not None:
        for i, n in zip(x, inside_n):
            ax.text(i, 0, f" {n / 1000:,.0f}k" if n >= 1000 else f" {n}",
                    ha="center", va="bottom", fontsize=7.5, color="white")


def draw_box(ax, xc, y, col, bw=0.30):
    """Boîte à moustaches manuelle (traduction de draw_box de u2.m)."""
    y = y[~np.isnan(y)]
    if y.size == 0:
        return
    q1, q2, q3 = np.quantile(y, [0.25, 0.50, 0.75])
    iqr = q3 - q1
    w_lo = max(y.min(), q1 - 1.5 * iqr)
    w_hi = min(y.max(), q3 + 1.5 * iqr)
    ax.fill([xc - bw, xc + bw, xc + bw, xc - bw], [q1, q1, q3, q3],
            facecolor=col, alpha=0.18, edgecolor=col, lw=1.2, zorder=2)
    ax.plot([xc - bw, xc + bw], [q2, q2], color=col, lw=2.2, zorder=3,
            solid_capstyle="butt")
    for a_, b_ in [(q3, w_hi), (w_lo, q1)]:
        ax.plot([xc, xc], [a_, b_], color=col, lw=1, zorder=2)
    for w in (w_lo, w_hi):
        ax.plot([xc - bw / 2, xc + bw / 2], [w, w], color=col, lw=1, zorder=2)


def box_panel(ax, df, group_col, order, labels, title, rng):
    """Boîtes de log10(sévérité) par groupe + jitter échantillonné + annotations."""
    sev = np.log10(df["paid"])
    top = sev.max() + 0.2
    for i, g in enumerate(order, start=1):
        col = SERIES[i - 1]
        y = sev[df[group_col] == g].to_numpy()
        y = y[~np.isnan(y)]
        if y.size == 0:
            continue
        samp = rng.choice(y, size=min(400, y.size), replace=False)
        ax.scatter(i + (rng.random(samp.size) - 0.5) * 0.24, samp,
                   s=5, color=col, alpha=0.22, lw=0, zorder=1)
        draw_box(ax, i, y, col)
        ax.plot(i, np.log10(np.mean(10 ** y)), "D", ms=7, mfc="white",
                mec=col, mew=1.6, zorder=4)
        ax.text(i, top, f"médiane ${10 ** np.median(y):,.0f}\nn = {y.size:,}",
                ha="center", va="bottom", fontsize=8.5, color=INK2, linespacing=1.4)
    ax.set_xticks(range(1, len(order) + 1), labels)
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(0.4, len(order) + 0.6)
    ax.set_ylim(sev.quantile(0.001) - 0.2, top + 0.75)
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


# -------------------------------------------------------------------------
# 1. CHARGEMENT
# -------------------------------------------------------------------------
pd.set_option("future.no_silent_downcasting", True)
print("Chargement…")
df = pd.read_parquet(DATA)
df["date"] = df["loss_month_period"].dt.to_timestamp()
df["year"] = num(df["loss_year"]).astype(int)
df["paid"] = num(df["paid_building_real"]).where(lambda s: s > 0)
df["coverage"] = num(df["building_coverage_real"])
df["ratio_cov"] = df["paid"] / df["coverage"].where(lambda s: s > 0)
paid_rate = df["paid_flag"].astype(float)
df["paid_rate"] = paid_rate
overall = paid_rate.mean()
rng = np.random.default_rng(42)

N = len(df)
VALUE = "building_value_real" if "building_value_real" in df.columns else "buildingPropertyValue"
print(f"  {N:,} sinistres, {df['year'].min()}–{df['year'].max()}")

# -------------------------------------------------------------------------
# 2. TABLEAUX DESCRIPTIFS (console + CSV)
# -------------------------------------------------------------------------
print("\n=== Statistiques numériques ===")
num_cols = ["paid_building_real", "building_coverage_real", "deductible_amount_real",
            "building_age", "water_depth", "flood_duration", VALUE]
desc = df[num_cols].apply(num).describe(percentiles=[.01, .25, .5, .75, .95, .99]).T
desc["missing_%"] = df[num_cols].isna().mean().mul(100).round(1)
print(desc.round(1).to_string())
desc.to_csv(OUT / "summary_numeric.csv")

print("\n=== Variables catégorielles ===")
cat_cols = [c for c in ["flood_zone_group", "foundation_type", "n_floors", "rating_system",
                        "elevated_building", "primary_residence", "state", "era", "split"]
            if c in df.columns]
cat_rows = []
for c in cat_cols:
    t = (df.groupby(df[c].astype("object").fillna("NA"), observed=True)
           .agg(n=("id", "size"), paid_rate=("paid_rate", "mean"),
                median_paid=("paid", "median")))
    t["share_%"] = 100 * t["n"] / N
    t.insert(0, "variable", c)
    cat_rows.append(t.reset_index(names="level"))
    print(f"\n{c}\n{t.round(3).to_string()}")
pd.concat(cat_rows).to_csv(OUT / "summary_categorical.csv", index=False)

LABELS = {"paid_building_real": "Montant payé", "buildingPropertyValue": "Valeur du bâtiment",
          "building_value_real": "Valeur du bâtiment", "primary_residence": "Résidence principale",
          "floodEvent": "Événement nommé", "flood_duration": "Durée de submersion",
          "water_depth": "Profondeur d'eau", "building_age": "Âge du bâtiment",
          "deductible_amount_real": "Franchise (réelle)", "deductible_amount": "Franchise",
          "flood_zone_group": "Zone d'inondation", "county_fips": "Comté", "n_floors": "Étages"}

# -------------------------------------------------------------------------
# FIGURE 1 — Valeurs manquantes
# -------------------------------------------------------------------------
print("\nFigures :")
miss = df.drop(columns=DERIVED + ["building_coverage", "deductible_amount"], errors="ignore") \
         .isna().mean().mul(100).sort_values()
miss = miss[miss >= 0.05]   # doublons nominaux retirés ; < 0,05 % non affiché

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
suptitle(fig, "Valeurs manquantes")
export(fig, "fig1_missing")

# -------------------------------------------------------------------------
# FIGURE 2 — Évolution annuelle : trois mesures, trois panneaux (pas de double axe)
# -------------------------------------------------------------------------
yr = df.groupby("year").agg(n=("id", "size"), rate=("paid_rate", "mean"),
                            med=("paid", "median"),
                            recoded=("paid_na_to_zero", lambda s: s.astype(float).sum()))
# taux de paiement parmi les dossiers non recodés (paiement NA -> non payé exclu)
yr["rate_nr"] = yr["rate"] * yr["n"] / (yr["n"] - yr["recoded"])
recent_from = df.loc[df["recent_claim"], "year"].min() if "recent_claim" in df.columns else None
done = yr.index < recent_from if recent_from is not None else np.ones(len(yr), bool)
thr = yr["n"].quantile(0.90)
hot = yr["n"] >= thr
share_top = yr.loc[hot, "n"].sum() / N

fig, (a, b, c) = plt.subplots(1, 3, figsize=(15, 4.4), layout="constrained")
a.bar(yr.index, yr["n"], 0.8, color=np.where(hot, ORANGE, NEUTRAL))
for y_, v in yr.loc[hot, "n"].items():
    a.text(y_, v + yr["n"].max() * 0.015, f"{y_}", ha="center", va="bottom",
           fontsize=7.5, color=INK2, rotation=90)
a.yaxis.set_major_formatter(thousands)
a.set_ylim(0, yr["n"].max() * 1.18)
a.set_title(f"(a) Sinistres par année — {hot.sum()} années = {share_top:.0%} du total")

yd = yr[done]
b.plot(yd.index, 100 * yd["rate"], color=BLUE, lw=2, label="tous les sinistres")
b.plot(yd.index, 100 * yd["rate_nr"], color=INK2, lw=1.2, ls="--",
       label="hors paiements NA recodés en « non payé »")
b.axhline(100 * overall, ls=":", color=MUTED, lw=1)
b.text(yd.index.min(), 100 * overall - 1, f"moyenne {overall:.0%}", fontsize=8, color=INK2,
       va="top")
b.yaxis.set_major_formatter(pct)
b.set_ylim(40, 100)
b.legend(loc="lower right")
b.set_title("(b) Taux de paiement : les creux viennent du recodage")

c.plot(yd.index, yd["med"], color=BLUE, lw=2)
c.yaxis.set_major_formatter(kdollars)
c.set_ylim(0, yd["med"].max() * 1.12)
c.set_title("(c) Montant payé médian (USD réels)")
for ax in (a, b, c):
    ax.set_xlim(yr.index.min() - 1, yr.index.max() + 1)
note = (f" ; (b) et (c) s'arrêtent en {recent_from - 1} (dossiers {recent_from}+ "
        "possiblement encore ouverts)") if recent_from is not None else ""
suptitle(fig, "Évolution annuelle des sinistres" + note)
export(fig, "fig2_annual")

# -------------------------------------------------------------------------
# FIGURE 3 — Série mensuelle, grands événements ombrés (cf. Fig 1 de u2.m)
# -------------------------------------------------------------------------
monthly = df.groupby("date").size()
monthly = monthly.reindex(pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS"),
                          fill_value=0)
ev = df.dropna(subset=["floodEvent"])
ev = ev[ev["floodEvent"].astype(str).str.lower() != "flooding"]
top_ev = ev["floodEvent"].value_counts().head(8).index
top8_share = df["floodEvent"].isin(top_ev).mean()
peaks = sorted((ev.loc[ev["floodEvent"] == e, "date"].mode().iloc[0], str(e)) for e in top_ev)

fig, ax = plt.subplots(figsize=(14, 4.8), layout="constrained")
ymax = monthly.max() * 1.22
last, level = None, 0
for peak, name in peaks:
    ax.axvspan(peak - pd.DateOffset(months=2), peak + pd.DateOffset(months=2),
               color=BAND, lw=0, zorder=0)
    level = level + 1 if last is not None and (peak - last).days < 540 else 0
    ax.text(peak, ymax * (0.985 - 0.07 * level), name.replace("Hurricane ", ""),
            ha="center", va="top", fontsize=8.5, color=INK2, style="italic")
    last = peak
ax.plot(monthly.index, monthly.values, color=INK, lw=0.9, zorder=2)
ax.set_ylim(0, ymax)
ax.set_xlim(monthly.index[0], monthly.index[-1])
ax.yaxis.set_major_formatter(thousands)
ax.set_ylabel("Sinistres par mois")
ax.set_title(f"Les 8 plus grands événements nommés (bandes grises) représentent "
             f"{top8_share:.0%} des sinistres")
suptitle(fig, f"Sinistres mensuels, {monthly.index[0].year}–{monthly.index[-1].year}")
export(fig, "fig3_monthly")

# -------------------------------------------------------------------------
# FIGURE 4 — Distribution de la sévérité et plafond
# -------------------------------------------------------------------------
sev = df["paid"].dropna()
ratio = df["ratio_cov"].dropna().clip(upper=1.2)
at_cap = (df["ratio_cov"] >= 0.99).sum() / df["ratio_cov"].notna().sum()
has_era = "era" in df.columns

fig, axes = plt.subplots(1, 3 if has_era else 2, figsize=(15 if has_era else 11, 4.4),
                         layout="constrained")
a, b = axes[0], axes[1]
lsev = np.log10(sev)
lo = np.floor(lsev.quantile(0.001) * 2) / 2
a.hist(lsev[lsev >= lo], bins=70, color=BLUE, edgecolor="white", linewidth=0.3)
a.set_ylim(0, a.get_ylim()[1] * 1.15)
ytop = a.get_ylim()[1]
for q, ls, name in [(0.5, "--", "médiane"), (0.95, ":", "q95")]:
    v = np.log10(sev.quantile(q))
    a.axvline(v, ls=ls, color=INK, lw=1.1)
    a.text(v, ytop * 0.985, f"{name}\n${10 ** v:,.0f}", fontsize=8.5, color=INK,
           ha="center", va="top", linespacing=1.3,
           bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
a.set_xlim(lo, lsev.max() + 0.1)
a.set_xticks([t for t in [1, 2, 3, 4, 5, 6] if t >= lo])
a.xaxis.set_major_formatter(pow10)
a.yaxis.set_major_formatter(thousands)
a.set_xlabel("Montant payé (USD réels, échelle log)")
a.set_title(f"(a) Montant payé : moyenne ${sev.mean():,.0f}, médiane ${sev.median():,.0f}")

b.hist(ratio, bins=60, color=BLUE, edgecolor="white", linewidth=0.3)
b.axvline(1, ls="--", color=INK, lw=1.1)
b.text(0.98, b.get_ylim()[1] * 0.97, "plafond", ha="right", va="top", fontsize=8.5, color=INK)
b.yaxis.set_major_formatter(thousands)
b.set_xlabel("Montant payé / couverture bâtiment")
b.set_title(f"(b) {at_cap:.1%} des sinistres payés atteignent le plafond")

if has_era:
    c = axes[2]
    cap = df.dropna(subset=["at_cap"]).groupby("era", observed=True)["at_cap"] \
            .agg(lambda s: s.astype(float).mean())
    x = np.arange(len(cap))
    c.bar(x, 100 * cap.values, 0.62, color=np.where(cap.values == cap.max(), ORANGE, NEUTRAL))
    bar_labels(c, x, 100 * cap.values, lambda h: f"{h:.1f} %", 0.25)
    c.set_xticks(x, cap.index.astype(str))
    c.tick_params(axis="x", length=0)
    c.yaxis.set_major_formatter(pct)
    c.set_ylim(0, 100 * cap.max() * 1.2)
    c.set_title("(c) Part au plafond, par époque")
for ax in axes[:2]:
    ax.set_ylabel("Sinistres payés")
suptitle(fig, "Sévérité des sinistres payés")
export(fig, "fig4_severity")

# -------------------------------------------------------------------------
# FIGURE 5 — Sévérité par groupe (boîtes annotées, cf. Fig 2b de u2.m)
# -------------------------------------------------------------------------
zones = [z for z in ["A*", "V*", "X", "D"] if (df["flood_zone_group"] == z).any()]
fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5.4), gridspec_kw={"width_ratios": [1.6, 1]},
                           sharey=True, layout="constrained")
box_panel(a, df, "flood_zone_group", zones, zones, "(a) Par zone d'inondation", rng)
df["elev_lbl"] = df["elevated_building"].map({True: "Surélevé", False: "Non surélevé"})
box_panel(b, df, "elev_lbl", ["Non surélevé", "Surélevé"], ["Non surélevé", "Surélevé"],
          "(b) Selon la surélévation", rng)
a.set_ylabel("Montant payé (USD réels, échelle log)")
box_legend(fig)
suptitle(fig, "Montant payé par groupe")
export(fig, "fig5_boxes")

# -------------------------------------------------------------------------
# FIGURE 6 — Taux de paiement par variable catégorielle
# -------------------------------------------------------------------------
second = ("foundation_type", "Fondation") if "foundation_type" in df.columns \
    else ("era", "Époque")
cats = [("flood_zone_group", "Zone d'inondation"), second,
        ("n_floors", "Code d'étages"), ("primary_residence", "Résidence principale"),
        ("elevated_building", "Bâtiment surélevé"), ("rating_system", "Système de codage")]
RENAME = {"True": "oui", "False": "non", "non renseigné": "n. r.",
          "Risk Rating 2.0 (11)": "Risk Rating 2.0", "ancien (1)": "ancien"}
fig, axes = plt.subplots(2, 3, figsize=(14, 7.6), sharey=True, layout="constrained")
for ax, (c, lbl) in zip(axes.flat, cats):
    g = df.groupby(df[c].astype("object").fillna("NA")).agg(rate=("paid_rate", "mean"),
                                                           n=("id", "size"))
    g = g[g["n"] >= 100]
    x = np.arange(len(g))
    ax.bar(x, 100 * g["rate"], 0.62, color=BLUE)
    ax.axhline(100 * overall, ls=":", color=MUTED, lw=1)
    bar_labels(ax, x, 100 * g["rate"], lambda h: f"{h:.0f} %", 1.2, inside_n=g["n"])
    ax.set_xticks(x, [RENAME.get(str(i), str(i)) for i in g.index],
                  fontsize=8.5 if len(g) > 5 else 9)
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(pct)
    ax.set_title(lbl)
suptitle(fig, f"Taux de paiement par caractéristique (pointillés : moyenne {overall:.0%})")
export(fig, "fig6_frequency")

# -------------------------------------------------------------------------
# FIGURE 7 — Profondeur d'eau et sévérité
# -------------------------------------------------------------------------
d = df[["water_depth", "paid"]].apply(num).dropna()
d = d[d["water_depth"].between(0, d["water_depth"].quantile(0.99))]
# classes de 4 unités (centre de classe) pour une courbe lisible
d["depth_bin"] = (d["water_depth"] // 4) * 4 + 2
by_depth = d.groupby("depth_bin")["paid"].agg(["median", "size",
                                               lambda s: s.quantile(.25),
                                               lambda s: s.quantile(.75)])
by_depth.columns = ["med", "n", "q25", "q75"]
by_depth = by_depth[by_depth["n"] >= 200]
rho = d["water_depth"].corr(d["paid"], method="spearman")

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
a.set_title(f"(a) Densité des sinistres — ρ de Spearman = {rho:.2f}")

b.fill_between(by_depth.index, by_depth["q25"], by_depth["q75"], color=BLUE, alpha=0.18,
               lw=0, label="intervalle interquartile")
b.plot(by_depth.index, by_depth["med"], color=BLUE, lw=2, label="médiane")
b.yaxis.set_major_formatter(kdollars)
b.set_ylim(0, by_depth["q75"].max() * 1.08)
b.set_xlabel("Profondeur d'eau (valeur brute, unité mixte pieds / pouces)")
b.set_title("(b) Montant payé selon la profondeur (classes de 4 unités)")
b.legend(loc="upper left")
suptitle(fig, "Profondeur d'eau et montant payé (variable ex post, hors modèle prédictif)")
export(fig, "fig7_depth")

# -------------------------------------------------------------------------
# FIGURE 8 — Géographie
# -------------------------------------------------------------------------
geo_s = df.groupby(df["state"].astype(str)).agg(n=("id", "size"), total=("paid", "sum")) \
          .sort_values("n")
geo_c = df[df["county_fips"].astype(str) != "inconnu"] \
          .groupby(df["county_fips"].astype("object").dropna()) \
          .agg(n=("id", "size"), state=("state", "first")) \
          .nlargest(15, "n").sort_values("n")
top15_share = geo_c["n"].sum() / N

fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5.4), layout="constrained")
a.barh(geo_s.index, geo_s["n"], height=0.62, color=BLUE)
for i, (n, t) in enumerate(zip(geo_s["n"], geo_s["total"])):
    a.text(n + geo_s["n"].max() * 0.015, i, f"{n / 1000:,.0f}k  ·  ${t / 1e9:,.1f} Md payés",
           va="center", fontsize=8.5, color=INK)
a.set_xlim(0, geo_s["n"].max() * 1.5)
a.set_title("(a) Sinistres et montants payés, par État")

b.barh([f"{i}  {s}" for i, s in zip(geo_c.index, geo_c["state"])], geo_c["n"],
       height=0.62, color=BLUE)
for i, n in enumerate(geo_c["n"]):
    b.text(n + geo_c["n"].max() * 0.015, i, f"{n / 1000:,.1f}k", va="center",
           fontsize=8.5, color=INK)
b.set_xlim(0, geo_c["n"].max() * 1.15)
b.set_title(f"(b) Les 15 premiers comtés = {top15_share:.0%} des sinistres")
for ax in (a, b):
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.xaxis.set_major_formatter(thousands)
    ax.tick_params(axis="y", length=0)
suptitle(fig, "Répartition géographique")
export(fig, "fig8_geography")

# -------------------------------------------------------------------------
# FIGURE 9 — Corrélations de Spearman (triangle inférieur)
# -------------------------------------------------------------------------
corr_cols = {"paid_building_real": "Montant payé", "paid_flag": "Payé (0/1)",
             "building_coverage_real": "Couverture", "deductible_amount_real": "Franchise",
             "building_age": "Âge du bâtiment", "water_depth": "Profondeur d'eau",
             "flood_duration": "Durée de submersion", VALUE: "Valeur du bâtiment",
             "elevated_building": "Surélevé", "primary_residence": "Résidence principale",
             "loss_year": "Année"}
C = df[list(corr_cols)].apply(num).rename(columns=corr_cols).corr(method="spearman")
mask = np.triu(np.ones_like(C, dtype=bool))
Cm = C.mask(mask)

fig, ax = plt.subplots(figsize=(8.8, 7.2), layout="constrained")
im = ax.imshow(Cm, cmap=DIV, vmin=-1, vmax=1)
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
        if np.isnan(v):   # ex. montant payé × payé (0/1) : montant défini seulement si payé
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, color=GRID, lw=0))
            ax.text(j, i, "—", ha="center", va="center", fontsize=8, color=INK2)
            continue
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                color="white" if abs(v) > 0.55 else INK)
cb = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
cb.set_label("ρ de Spearman", color=INK2)
cb.outline.set_visible(False)
ax.set_title("Paires disponibles ; bleu = corrélation positive, orange = négative")
suptitle(fig, "Corrélations de rang")
export(fig, "fig9_correlation")

# -------------------------------------------------------------------------
# FIGURE 10 — Nouvelles variables du dataset v2 (une mesure par ligne)
# -------------------------------------------------------------------------
NEW = ["fold", "split", "major_event"]
if all(c in df.columns for c in NEW):
    folds = sorted(df["fold"].unique())
    groups = [("fold", folds, [f"pli {f}" for f in folds], "Plis par événement (validation)"),
              ("split", ["train", "valid", "test"],
               ["train\n≤ 2016", "valid\n2017–2020", "test\n≥ 2021"], "Découpage temporel"),
              ("major_event", [False, True], ["autres", "Helene, Ian,\nKatrina"],
               f"Grands ouragans ({df['major_event'].mean():.0%} des sinistres)")]
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.8), sharey="row",
                             gridspec_kw={"width_ratios": [5, 3, 2.2]}, layout="constrained")
    med_max = 0
    stats = []
    for key, order, _, _ in groups:
        g = df.groupby(key, observed=True).agg(rate=("paid_rate", "mean"), med=("paid", "median"),
                                               n=("id", "size")).reindex(order)
        stats.append(g)
        med_max = max(med_max, g["med"].max())
    for j, ((key, order, labels, title), g) in enumerate(zip(groups, stats)):
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
    suptitle(fig, "Variables ajoutées au dataset de modélisation "
                  f"(pointillés : taux moyen {overall:.0%})")
    export(fig, "fig10_model_vars")


# -------------------------------------------------------------------------
# RÉSUMÉ CONSOLE
# -------------------------------------------------------------------------
print("\n========== Résumé ==========")
print(f" Sinistres                 : {N:,}")
print(f" Taux de paiement          : {overall:.1%}")
print(f" Sévérité médiane / moyenne: ${sev.median():,.0f} / ${sev.mean():,.0f}")
print(f" Atteinte du plafond       : {at_cap:.1%}")
print(f" Top 8 événements          : {top8_share:.1%} des sinistres")
print(f" Spearman profondeur/payé  : {rho:.2f}")
print(f" Figures et CSV dans       : {OUT}")

# Métriques pour la comparaison v1 / v2 (compare_eda.py)
metrics = {
    "dataset": DATA.name, "n_rows": N, "n_cols": int(df.shape[1] - len(
        [c for c in ["date", "year", "paid", "coverage", "ratio_cov", "paid_rate", "elev_lbl"]
         if c in df.columns])),
    "paid_rate": overall, "sev_median": float(sev.median()), "sev_mean": float(sev.mean()),
    "at_cap": float(at_cap), "top8_events_share": float(top8_share), "spearman_depth": float(rho),
    "missing_pct": miss.round(2).to_dict(),
    "paid_rate_by": {c: df.groupby(df[c].astype("object").fillna("NA"))["paid_rate"].mean()
                        .round(4).to_dict() for c in cat_cols if c != "state"},
    "spearman": C.round(3).to_dict(),
}
(OUT / "metrics.json").write_text(json.dumps(metrics, indent=1, ensure_ascii=False, default=str))
