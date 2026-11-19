"""Analysis of the evaluation of the agent: INFO.VIEW vs. Fabric API.

Reads the CSV with one row per run (question, repetition and method) and produces
the accuracy tables, the statistical tests and Figures 6, 7 and 8.

Tests:
- Accuracy: Fisher's exact test on the proportion of correct answers.
- Time, tool calls and tokens: Wilcoxon signed-rank test, paired by question,
  using the median of the three repetitions of each question and method.

Usage:
    python analysis_transfermarkt.py results.csv output_folder
"""

import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy.stats import wilcoxon, fisher_exact

CSV = sys.argv[1]
OUT = sys.argv[2]

df = pd.read_csv(CSV)
df["method"] = df["via"].map({"infoview": "INFO.VIEW", "api": "Fabric API"})
ORDER = ["INFO.VIEW", "Fabric API"]
COLORS = {"INFO.VIEW": "#2a78d6", "Fabric API": "#eb6834"}

TYPES = {
    1: "Discovery", 2: "Discovery", 14: "Discovery", 16: "Discovery",
    3: "Simple value", 4: "Simple value",
    5: "Filtered value", 6: "Filtered value", 12: "Filtered value",
    7: "Comparison", 8: "Comparison",
    9: "Ranking", 10: "Ranking",
    11: "Evolution over time",
    13: "Cross-table",
    15: "Ambiguous", 17: "Ambiguous",
    18: "Out of scope", 19: "Out of scope",
}
TYPE_ORDER = ["Discovery", "Simple value", "Filtered value", "Comparison", "Ranking",
              "Evolution over time", "Cross-table", "Ambiguous", "Out of scope"]
df["type"] = df["pregunta_id"].map(TYPES)

serif = [f for f in ["Times New Roman", "Liberation Serif", "DejaVu Serif"]
         if any(f == x.name for x in font_manager.fontManager.ttflist)]
plt.rcParams.update({
    "font.family": "serif", "font.serif": serif, "font.size": 10,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": "#444444", "ytick.color": "#444444",
    "axes.labelcolor": "#222222", "savefig.dpi": 300,
})
print("font:", serif[:1])

lines = []
def out(s=""):
    lines.append(s)

# ---------- Table: accuracy by method ----------
acc = df.groupby("method").agg(correct=("correcta", "sum"), runs=("correcta", "count"),
                               errors=("error", lambda s: s.notna().sum())).loc[ORDER]
acc["accuracy"] = acc.correct / acc.runs * 100
tab = [[acc.loc["INFO.VIEW", "correct"], acc.loc["INFO.VIEW", "runs"] - acc.loc["INFO.VIEW", "correct"]],
       [acc.loc["Fabric API", "correct"], acc.loc["Fabric API", "runs"] - acc.loc["Fabric API", "correct"]]]
_, p_fisher = fisher_exact(tab)
out("ACCURACY BY METHOD")
out(acc.to_string())
out(f"Fisher exact p = {p_fisher:.3f}")

# ---------- Table: accuracy by type ----------
bt = (df.groupby(["type", "method"]).correcta.agg(["sum", "count"]).unstack("method"))
qcount = df.groupby("type").pregunta_id.nunique()
out("\nACCURACY BY TYPE")
rows = []
for t in TYPE_ORDER:
    r = {"type": t, "questions": int(qcount[t])}
    for m in ORDER:
        s, c = bt.loc[t, ("sum", m)], bt.loc[t, ("count", m)]
        r[m] = f"{s}/{c} ({s / c * 100:.0f}%)"
        r[m + "_pct"] = s / c * 100
    rows.append(r)
bytype = pd.DataFrame(rows)
out(bytype.to_string())

# ---------- Time and tokens ----------
# Failed runs (errors) are excluded from time, calls and tokens.
df["n_desc"] = df["ruta"].fillna("").str.count("describe_table_schema")
ok = df[df.error.isna()].copy()
d = ok[ok.n_desc > 0].copy()
d["describe_per_call"] = d.segundos_describe / d.n_desc

def summ(series):
    q1, med, q3 = np.percentile(series.dropna(), [25, 50, 75])
    return f"{med:.2f} [{q1:.2f}-{q3:.2f}]"

out("\nTIME AND TOKENS (median [IQR]); successful runs except where noted")
metrics = [
    ("Total time per question (s)", ok, "segundos_total"),
    ("Tool time per question (s)", ok, "segundos_herramientas"),
    ("Time per describe_table_schema call (s)", d, "describe_per_call"),
    ("Tool calls per question", ok, "n_llamadas"),
    ("Total tokens per question", ok, "tokens_totales"),
    ("Characters returned by tools", ok, "caracteres_herramientas"),
]
for name, data, col in metrics:
    a = data[data.method == "INFO.VIEW"][col].dropna()
    b = data[data.method == "Fabric API"][col].dropna()
    # Paired comparison: median of the repetitions of each question and method
    paired = data.groupby(["pregunta_id", "method"])[col].median().unstack().dropna()
    p = wilcoxon(paired["Fabric API"], paired["INFO.VIEW"]).pvalue
    higher = int((paired["Fabric API"] > paired["INFO.VIEW"]).sum())
    out(f"{name}: INFO.VIEW {summ(a)} | Fabric API {summ(b)} | "
        f"Fabric API higher in {higher} of {len(paired)} questions | Wilcoxon p = {p:.2g}")

allt = df.groupby("method").segundos_total.median()
out(f"\nTotal time median incl. failed runs: {allt.to_dict()}")
out(f"Describe per-call n: {d.groupby('method').size().to_dict()}")
out(f"Mean tokens (ok runs): {ok.groupby('method').tokens_totales.mean().round(0).to_dict()}")

open(f"{OUT}/summary.txt", "w").write("\n".join(lines))
print("\n".join(lines))

# ---------- Figure: accuracy by type ----------
fig, ax = plt.subplots(figsize=(6.3, 3.8))
y = np.arange(len(TYPE_ORDER))
h = 0.36
for i, m in enumerate(ORDER):
    vals = bytype[m + "_pct"].values
    ax.barh(y + (i - 0.5) * (h + 0.04), vals, height=h, color=COLORS[m], label=m,
            edgecolor="white", linewidth=0.8)
    for yy, v in zip(y + (i - 0.5) * (h + 0.04), vals):
        ax.text(v + 1.2, yy, f"{v:.0f}%", va="center", fontsize=8, color="#444444")
ax.set_yticks(y, [f"{t} ({int(qcount[t])})" for t in TYPE_ORDER])
ax.invert_yaxis()
ax.set_xlim(0, 112)
ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("Correct answers")
ax.xaxis.grid(True, color="#e1e0d9", linewidth=0.6)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=9)
fig.tight_layout()
fig.savefig(f"{OUT}/Figure6_accuracy_by_type.png")
plt.close(fig)

# ---------- Figure: time boxplots ----------
fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.2))
panels = [
    (axes[0], ok, "segundos_total", "Total time per question (s)", "(a) Complete answer"),
    (axes[1], d, "describe_per_call", "Time per call (s)", "(b) describe_table_schema"),
]
for ax, data, col, ylabel, title in panels:
    vals = [data[data.method == m][col].dropna() for m in ORDER]
    bp = ax.boxplot(vals, tick_labels=ORDER, widths=0.5, patch_artist=True,
                    medianprops=dict(color="#222222", linewidth=1.4),
                    flierprops=dict(marker="o", markersize=4, markerfacecolor="white",
                                    markeredgecolor="#666666"),
                    whiskerprops=dict(color="#666666"), capprops=dict(color="#666666"))
    for patch, m in zip(bp["boxes"], ORDER):
        patch.set_facecolor(COLORS[m]); patch.set_alpha(0.85); patch.set_edgecolor("#444444")
    for i, v in enumerate(vals, start=1):
        med = np.median(v)
        ax.text(i + 0.3, med, f"{med:.2f} s", va="center", fontsize=8, color="#222222")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    ax.set_ylim(bottom=0)
    ax.yaxis.grid(True, color="#e1e0d9", linewidth=0.6)
    ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(f"{OUT}/Figure7_time_by_method.png")
plt.close(fig)

# ---------- Figure: tokens boxplot ----------
fig, ax = plt.subplots(figsize=(4.2, 3.2))
vals = [ok[ok.method == m]["tokens_totales"].dropna() for m in ORDER]
bp = ax.boxplot(vals, tick_labels=ORDER, widths=0.5, patch_artist=True,
                medianprops=dict(color="#222222", linewidth=1.4),
                flierprops=dict(marker="o", markersize=4, markerfacecolor="white",
                                markeredgecolor="#666666"),
                whiskerprops=dict(color="#666666"), capprops=dict(color="#666666"))
for patch, m in zip(bp["boxes"], ORDER):
    patch.set_facecolor(COLORS[m]); patch.set_alpha(0.85); patch.set_edgecolor("#444444")
for i, v in enumerate(vals, start=1):
    med = np.median(v)
    ax.text(i + 0.3, med, f"{med:,.0f}", va="center", fontsize=8, color="#222222")
ax.set_ylabel("Total tokens per question (log scale)")
ax.set_yscale("log")
ax.set_yticks([1000, 3000, 10000, 30000, 100000, 300000], ["1,000", "3,000", "10,000", "30,000", "100,000", "300,000"])
ax.minorticks_off()
ax.yaxis.grid(True, color="#e1e0d9", linewidth=0.6)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(f"{OUT}/Figure8_tokens_by_method.png")
plt.close(fig)