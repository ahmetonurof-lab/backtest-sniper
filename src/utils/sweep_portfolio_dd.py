"""
sweep_portfolio_dd.py — Gercek portfoy MaxDD hesaplamali risk carpani taramasi.
Trade'leri gun bazinda toplayip, portfoy equity egrisi uzerinden peak-to-trough hesaplar.
"""

import pandas as pd
import os

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
df = pd.read_parquet(os.path.join(REPORTS_DIR, "trades_default.parquet"))

df["hour"] = pd.to_datetime(df["entry_time"]).dt.hour
df["is_el"] = df["hour"].between(2, 7)
df["date"] = pd.to_datetime(df["entry_time"]).dt.date


def portfolio_maxdd_full(daily_series):
    """Returns (max_dd_val, max_dd_pct, start_date, recovery_date, days_to_recover)"""
    cum = daily_series.cumsum()
    peak = cum.cummax()
    dd = peak - cum
    max_dd_val = dd.max()
    max_dd_pct = max_dd_val / 10000 * 100

    # En kotu cukur anini bul
    trough_idx = dd.idxmax()
    trough_val = cum[trough_idx]

    # Bu cukurdan onceki en son peak
    mask_before = cum.index <= trough_idx
    peak_before_mask = cum[mask_before]
    peak_before = peak_before_mask.max()
    peak_idx = peak_before_mask.idxmax()

    # Recovery: trough sonrasi, peak_before'u tekrar gectigi ilk gun
    mask_after = cum.index > trough_idx
    after = cum[mask_after]
    rec_idx = after[after >= peak_before]
    if not rec_idx.empty:
        recovery_date = rec_idx.index[0]
        days_to_recover = (pd.Timestamp(recovery_date) - pd.Timestamp(trough_idx)).days
    else:
        recovery_date = None
        days_to_recover = None

    return max_dd_val, max_dd_pct, peak_idx, trough_idx, recovery_date, days_to_recover


def calmar_ratio(daily_series):
    """Calmar = yilliklandirilmis getiri / MaxDD%"""
    total_days = (
        (daily_series.index[-1] - daily_series.index[0]).days
        if hasattr(daily_series.index, "__getitem__")
        else len(daily_series)
    )
    total_days = max(total_days, 1)
    ann_return = (daily_series.sum() / 10000) / (total_days / 365)
    _, dd_pct = portfolio_maxdd_full(daily_series)
    return ann_return / (dd_pct / 100) if dd_pct > 0 else 0


# ─── ANA TARAMA: 1.0 - 2.0 (0.2) ───────────────────────────
SWEEP = [round(1.0 + i * 0.2, 1) for i in range(6)]
print("=" * 120)
print("  GERCEK PORTFOY MAxDD — Erken London Risk Carpani Taramasi")
print("  (13 coin gunluk birlestirilmis, gercek peak-to-trough + Calmar + Recovery)")
print("=" * 120)
print()
h = f"  {'Mult':<6} {'ToplamPnL':>10} {'Calmar':>8} {'MaxDD%':>8} {'RecGun':>7} {'RecTarih':>12} {'PnL/DD':>7} {'EL_PnL':>10}"
print(h)
print(f"  {'-'*70}")

for mult in SWEEP + [round(1.0 + i * 0.5, 1) for i in [0, 1, 2, 3, 4, 6, 8]]:
    if mult in SWEEP:
        pass
    elif mult in [round(1.0 + i * 0.5, 1) for i in [0, 1, 2, 3, 4, 6, 8]]:
        pass
    else:
        continue

    df_s = df.copy()
    df_s.loc[df_s["is_el"], "final_pnl_usd"] *= mult
    daily = df_s.groupby("date")["final_pnl_usd"].sum().sort_index()
    tp = daily.sum()
    dd_val, dd_pct, peak_d, trough_d, rec_d, rec_days = portfolio_maxdd_full(daily)
    ratio = tp / dd_val if dd_val else 0
    el_pnl = df_s[df_s["is_el"]]["final_pnl_usd"].sum()
    calmar = calmar_ratio(daily)
    rec_str = f"{rec_days}g" if rec_days is not None else "∞"
    rec_date = rec_d.strftime("%Y-%m-%d") if rec_d is not None else "-"
    print(
        f"  {mult:<6.1f} {tp:>+10,.0f} {calmar:>7.2f}  {dd_pct:>6.2f}% {rec_str:>7} {rec_date:>12} {ratio:>6.1f} {el_pnl:>+10,.0f}"
    )

# ─── YENI: Calmar + Recovery + EL_PF detayi ──────────────────
print()
print("=" * 120)
print("  DETAYLI ANALIZ: Calmar, Recovery Time, Early London PF")
print("=" * 120)

# Portfolio PF (tum trade'ler, baseline)
gross_p = df[df["final_pnl_usd"] > 0]["final_pnl_usd"].sum()
gross_l = abs(df[df["final_pnl_usd"] < 0]["final_pnl_usd"].sum())
pf_port = gross_p / gross_l if gross_l else 0
print(f"\n  Portfolio PF (tumu, 1.0x): {pf_port:.2f}")

# Early London PF (baseline, 1.0x)
el = df[df["is_el"]]
el_gp = el[el["final_pnl_usd"] > 0]["final_pnl_usd"].sum()
el_gl = abs(el[el["final_pnl_usd"] < 0]["final_pnl_usd"].sum())
el_pf = el_gp / el_gl if el_gl else 0
print(f"  Early London PF (1.0x):      {el_pf:.2f}  ({len(el)} trade)")

# Non-EL PF
nel = df[~df["is_el"]]
nel_gp = nel[nel["final_pnl_usd"] > 0]["final_pnl_usd"].sum()
nel_gl = abs(nel[nel["final_pnl_usd"] < 0]["final_pnl_usd"].sum())
nel_pf = nel_gp / nel_gl if nel_gl else 0
print(f"  Non-Early London PF (1.0x):  {nel_pf:.2f}  ({len(nel)} trade)")

print()
print(
    f"  {'Mult':<6} {'Calmar':>8} {'MaxDD%':>8} {'RecGun':>7} {'Peak':>12} {'Trough':>12} {'RecDate':>12} {'PF_Tum':>7} {'PF_EL':>7}"
)
print(f"  {'-'*85}")

for mult in [round(0.5 + i * 0.5, 1) for i in range(10)]:
    df_s = df.copy()
    df_s.loc[df_s["is_el"], "final_pnl_usd"] *= mult
    daily = df_s.groupby("date")["final_pnl_usd"].sum().sort_index()
    dd_val, dd_pct, peak_d, trough_d, rec_d, rec_days = portfolio_maxdd_full(daily)
    calmar = calmar_ratio(daily)

    # Portfolio PF
    gp = df_s[df_s["final_pnl_usd"] > 0]["final_pnl_usd"].sum()
    gl = abs(df_s[df_s["final_pnl_usd"] < 0]["final_pnl_usd"].sum())
    pf_all = gp / gl if gl else 0

    # EL PF
    el_s = df_s[df_s["is_el"]]
    el_gp = el_s[el_s["final_pnl_usd"] > 0]["final_pnl_usd"].sum()
    el_gl = abs(el_s[el_s["final_pnl_usd"] < 0]["final_pnl_usd"].sum())
    pf_el = el_gp / el_gl if el_gl else 0

    rec_str = f"{rec_days}g" if rec_days is not None else "∞"
    peak_s = peak_d.strftime("%Y-%m-%d") if peak_d is not None else "-"
    trough_s = trough_d.strftime("%Y-%m-%d") if trough_d is not None else "-"
    rec_date = rec_d.strftime("%Y-%m-%d") if rec_d is not None else "-"
    print(
        f"  {mult:<6.1f} {calmar:>7.2f}  {dd_pct:>6.2f}% {rec_str:>7} {peak_s:>12} {trough_s:>12} {rec_date:>12} {pf_all:>6.2f} {pf_el:>6.2f}"
    )
    df_s = df.copy()
    df_s.loc[df_s["is_el"], "final_pnl_usd"] *= mult
    daily = df_s.groupby("date")["final_pnl_usd"].sum().sort_index()
    tp = daily.sum()
    dd_val, dd_pct = portfolio_maxdd(daily)
    ratio = tp / dd_val if dd_val else 0
    el_pnl = df_s[df_s["is_el"]]["final_pnl_usd"].sum()
    print(
        f"  {mult:<6.1f} {tp:>+10,.0f} {dd_val:>10,.0f} {dd_pct:>9.2f}% {ratio:>6.1f} {el_pnl:>+10,.0f}"
    )


# ─── COIN BAZINDA GERCEK DD (portfoy ici) ──────────────────
print()
print("=" * 100)
print("  COIN BAZINDA — Günlük PnL dagilimi (baseline 1.0x)")
print("=" * 100)
print()
print(
    f"  {'Coin':<10} {'Trades':>7} {'ToplamPnL':>10} {'WR%':>6} {'MaxDD$':>9} {'MaxDD%':>8} {'StdDev':>8} {'Sharpe':>7}"
)
print(f"  {'-'*65}")

daily_pnl = df.groupby("date")["final_pnl_usd"].sum().sort_index()
port_dd_val, port_dd_pct = portfolio_maxdd(daily_pnl)

for sym in sorted(df["symbol"].unique()):
    sd = df[df["symbol"] == sym]
    dly = sd.groupby("date")["final_pnl_usd"].sum().sort_index()
    tp = dly.sum()
    n = len(sd)
    wr = (sd["final_pnl_usd"] > 0).mean() * 100
    dd_val, dd_pct = portfolio_maxdd(dly)
    std = dly.std()
    sharpe = (dly.mean() / std) * (365**0.5) if std else 0
    print(
        f"  {sym:<10} {n:>7} {tp:>+10,.0f} {wr:>5.1f}% {dd_val:>9,.0f} {dd_pct:>7.2f}% {std:>7.2f} {sharpe:>6.2f}"
    )

print()
print("  PORTFOY TOPLAMI:")
print(
    f"  {'TOPLAM':<10} {len(df):>7} {daily_pnl.sum():>+10,.0f} {'-':>6} {port_dd_val:>9,.0f} {port_dd_pct:>7.2f}% {daily_pnl.std():>7.2f} {daily_pnl.mean()/daily_pnl.std()*(365**0.5) if daily_pnl.std() else 0:>6.2f}"
)
