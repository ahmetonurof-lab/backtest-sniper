"""analyze_fvg_atr.py - FVG kalitesi, volatilite, Long/Short asimetrisi."""

import pandas as pd
import numpy as np
import os

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
df = pd.read_parquet(os.path.join(REPORTS_DIR, "trades_default.parquet"))
df["atr_clean"] = df["atr"].replace(0, np.nan)
df["rel_fvg"] = df["fvg_size_pips"] / df["atr_clean"]


def pct_bin(series, q=4, prefix="Q"):
    """Adaptive percentile binning - handles duplicate edges automatically."""
    bins = np.unique(series.quantile([i / q for i in range(q + 1)]))
    n = len(bins) - 1
    if n < 1:
        return pd.Series(None, index=series.index)
    labels = [f"{prefix}{i+1}" for i in range(n)]
    return pd.cut(series, bins=bins, labels=labels, include_lowest=True)


fv = df["fvg_size_pips"].clip(lower=0.1)
df["fvg_bin"] = pct_bin(fv, q=4, prefix="Abs")
# Force consistent naming
df["fvg_bin"] = (
    df["fvg_bin"].cat.rename_categories(
        {
            c: ["Abs_XS", "Abs_S", "Abs_M", "Abs_L"][i] if i < 4 else c
            for i, c in enumerate(df["fvg_bin"].cat.categories)
        }
    )
    if hasattr(df["fvg_bin"], "cat") and df["fvg_bin"].cat.categories is not None
    else df["fvg_bin"]
)

rel = df["rel_fvg"].dropna()
df["rel_fvg_bin"] = None
if len(rel) > 0:
    df.loc[rel.index, "rel_fvg_bin"] = pct_bin(rel, q=4, prefix="Rel")

# Analizler
fvg_abs = (
    df.groupby(["symbol", "fvg_bin"], observed=True)
    .agg(
        Trades=("is_cashflow_positive", "count"),
        Cashflow_WR=("is_cashflow_positive", "mean"),
        Avg_R=("r_multiple", "mean"),
        Total_PnL=("final_pnl_usd", "sum"),
    )
    .round(3)
)
fvg_rel = (
    df.groupby(["symbol", "rel_fvg_bin"], observed=True)
    .agg(
        Trades=("is_cashflow_positive", "count"),
        Cashflow_WR=("is_cashflow_positive", "mean"),
        Avg_R=("r_multiple", "mean"),
        Total_PnL=("final_pnl_usd", "sum"),
    )
    .round(3)
)
side_bias = (
    df.groupby(["symbol", "side"])
    .agg(
        Trades=("is_cashflow_positive", "count"),
        Cashflow_WR=("is_cashflow_positive", "mean"),
        Avg_R=("r_multiple", "mean"),
    )
    .round(3)
)
trail_eff = (
    df.groupby(["symbol", "trailing_count"])
    .agg(
        Trades=("is_cashflow_positive", "count"),
        Cashflow_WR=("is_cashflow_positive", "mean"),
        Avg_R=("r_multiple", "mean"),
    )
    .round(3)
)

# CSV
csv_dir = REPORTS_DIR
fvg_abs.to_csv(os.path.join(csv_dir, "out_fvg_absolute.csv"))
fvg_rel.to_csv(os.path.join(csv_dir, "out_fvg_relative.csv"))
side_bias.to_csv(os.path.join(csv_dir, "out_side_bias.csv"))
trail_eff.to_csv(os.path.join(csv_dir, "out_trail_efficiency.csv"))

print("=" * 80)
print("  ANALIZ A: MUTLAK FVG BOYUTU")
print("=" * 80)
print(fvg_abs.to_string())
print("\n" + "=" * 80)
print("  ANALIZ B: GORECELI FVG (FVG/ATR)")
print("=" * 80)
print(fvg_rel.to_string())
print("\n" + "=" * 80)
print("  ANALIZ C: LONG/SHORT ASIMETRISI")
print("=" * 80)
print(side_bias.to_string())
print("\n" + "=" * 80)
print("  ANALIZ D: TRAILING VERIMLILIGI")
print("=" * 80)
print(trail_eff.to_string())

print("\n" + "=" * 80)
print("  OZET BULGULAR")
print("=" * 80)
toxic = fvg_abs[(fvg_abs["Cashflow_WR"] < 0.50) & (fvg_abs["Total_PnL"] < 0)]
print("\n  Zehirli FVG (WR<%50 ve PnL<0):")
if len(toxic):
    for (sym, bin_), row in toxic.iterrows():
        print(
            f"    {sym:<10} {bin_:<10} WR={row['Cashflow_WR']:.1%} PnL={row['Total_PnL']:>+8,.0f}"
        )
else:
    print("    (yok)")

print("\n  Long/Short farki (>%5):")
for sym in sorted(df["symbol"].unique()):
    sd = side_bias.loc[sym]
    if "LONG" in sd.index and "SHORT" in sd.index:
        diff = sd.loc["LONG", "Cashflow_WR"] - sd.loc["SHORT", "Cashflow_WR"]
        if abs(diff) > 0.05:
            print(
                f"    {sym:<10} L={sd.loc['LONG','Cashflow_WR']:.1%} S={sd.loc['SHORT','Cashflow_WR']:.1%} F={diff:+.1%}"
            )

print(
    f"\n  CSV:\n    {os.path.join(csv_dir,'out_fvg_relative.csv')}\n    {os.path.join(csv_dir,'out_side_bias.csv')}"
)
print("  OK")
