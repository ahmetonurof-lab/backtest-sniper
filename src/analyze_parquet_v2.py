"""
analyze_parquet_v2.py — session.py'deki GERCEK detect_phase() sinirlariyla analiz.
Tüm sorulari kodun kendi faz tanimiyla cevaplar.
"""
import os, sys, math, pandas as pd

# session.py'deki detect_phase'i kullan
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src"))
from session import detect_phase, SessionPhase
from datetime import datetime, timezone

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

SESSION_LABELS = {
    "default":   "DEFAULT   [22:00-02:00]",
    "real_cbdr": "REAL_CBDR [19:00-01:00]",
    "asia_range":"ASIA_RANGE [01:00-05:00]",
}


def get_phase(hour: int, session_cfg: dict) -> str:
    """detect_phase() ile gercek faz adini dondur."""
    dt = datetime(2024, 1, 1, hour, 0, tzinfo=timezone.utc)
    p = detect_phase(dt, session_cfg)
    return p.value  # CBDR / LONDON / NEWYORK / CLOSED


def analyze():
    print("=" * 110)
    print("  ANALIZ V2 — Kodun Kendi detect_phase() Sinirlari Kullaniliyor")
    print("=" * 110)

    # Phase sinirlarini goster
    for cfg_name, sess_cfg in [("DEFAULT", {"start": 22, "end": 2}),
                                ("REAL_CBDR", {"start": 19, "end": 1}),
                                ("ASIA_RANGE", {"start": 1, "end": 5})]:
        print(f"\n  {cfg_name} — session_hours={sess_cfg}")
        for h in range(24):
            p = get_phase(h, sess_cfg)
            print(f"    {h:02d}:00 -> {p:10}", end="")
            if h % 4 == 3:
                print()
        print()

    # ─────────────────────────────────────────────────────────
    # SORU 1: Entry saatlerinin faz bazinda dagilimi
    # ─────────────────────────────────────────────────────────
    print("=" * 110)
    print("  SORU 1 (v2): Entry'ler hangi FAZLARDA acilmis? (kodun detect_phase() ile)")
    print("=" * 110)

    for fname in ["trades_default.parquet", "trades_real_cbdr.parquet", "trades_asia_range.parquet"]:
        fp = os.path.join(REPORTS_DIR, fname)
        if not os.path.isfile(fp):
            continue
        df = pd.read_parquet(fp)
        session_key = fname.replace("trades_", "").replace(".parquet", "")
        label = SESSION_LABELS.get(session_key, session_key)

        # Session config
        sess_cfg = {
            "default": {"start": 22, "end": 2},
            "real_cbdr": {"start": 19, "end": 1},
            "asia_range": {"start": 1, "end": 5},
        }[session_key]

        df["hour"] = pd.to_datetime(df["entry_time"]).dt.hour
        df["phase"] = df["hour"].apply(lambda h: get_phase(h, sess_cfg))

        print(f"\n  >>> {label}  (toplam {len(df):,} trade)")
        phase_order = ["CBDR", "LONDON", "NEWYORK", "CLOSED"]
        phase_counts = df["phase"].value_counts()
        for p in phase_order:
            cnt = phase_counts.get(p, 0)
            pct = cnt / len(df) * 100 if len(df) else 0
            bar = "█" * int(cnt / phase_counts.max() * 40) if phase_counts.max() else ""
            print(f"    {p:<10} {cnt:>8,}  (%{pct:5.2f})  {bar}")

        # Per-coin per-phase WR
        print(f"\n    -- Coin bazinda faz WR'leri --")
        grp = df.groupby(["symbol", "phase"]).agg(
            trades=("final_pnl_usd", "count"),
            wins=("final_pnl_usd", lambda x: (x > 0).sum()),
        ).reset_index()
        grp["wr"] = (grp["wins"] / grp["trades"] * 100).round(1)
        for sym in sorted(df["symbol"].unique()):
            parts = []
            for p in phase_order:
                row = grp[(grp["symbol"] == sym) & (grp["phase"] == p)]
                if not row.empty:
                    r = row.iloc[0]
                    parts.append(f"{p}={r['trades']:>4}trade WR={r['wr']:>4.1f}%")
            print(f"    {sym:<10} | {' | '.join(parts)}")

    # ─────────────────────────────────────────────────────────
    # SORU 3 (v2): Kodun kendi fazlariyla Asya/Londra/NY karsilastirmasi
    # ─────────────────────────────────────────────────────────
    print("\n\n" + "=" * 110)
    print("  SORU 3 (v2): Kodun Kendi Faz Tanimiyla Karsilastirma")
    print("=" * 110)
    print(f"""
  Kodun detect_phase() tanimi:
    LONDON  = 02:00-13:00 UTC  (02'de basliyor, textbook 07-08 degil!)
    NEWYORK = 13:00-22:00 UTC
    CLOSED  = 22:00-02:00 UTC (CBDR window)

  NOT: Kodda bagimsiz bir ASIA fazi yoktur.
  Asia range (02-08) sadece RangeTracker icin izlenir,
  detect_phase() hicbir zaman "ASIA" dondurmez.
  Londra 02'de basladigi icin 02-08 arasi = erken Londra'dir.
  """)

    for fname in ["trades_default.parquet", "trades_real_cbdr.parquet", "trades_asia_range.parquet"]:
        fp = os.path.join(REPORTS_DIR, fname)
        if not os.path.isfile(fp):
            continue
        df = pd.read_parquet(fp)
        session_key = fname.replace("trades_", "").replace(".parquet", "")
        label = SESSION_LABELS.get(session_key, session_key)
        sess_cfg = {
            "default": {"start": 22, "end": 2},
            "real_cbdr": {"start": 19, "end": 1},
            "asia_range": {"start": 1, "end": 5},
        }[session_key]

        df["hour"] = pd.to_datetime(df["entry_time"]).dt.hour
        df["phase"] = df["hour"].apply(lambda h: get_phase(h, sess_cfg))

        print(f"\n  --- {label} ---")
        print(f"  {'Phase':<12} {'Trades':>8} {'Wins':>7} {'WR%':>7} {'AvgPnL':>9} {'TotalPnL':>10}")
        print(f"  {'-'*55}")
        for p in ["LONDON", "NEWYORK", "CBDR", "CLOSED"]:
            sd = df[df["phase"] == p]
            n = len(sd)
            if n == 0:
                continue
            w = (sd["final_pnl_usd"] > 0).sum()
            wr = w / n * 100
            ap = sd["final_pnl_usd"].mean()
            tp = sd["final_pnl_usd"].sum()
            print(f"  {p:<12} {n:>8,} {w:>7} {wr:>6.1f}% {ap:>+8.2f} {tp:>+10,.0f}")

    # ─────────────────────────────────────────────────────────
    # SORU 3 BONUS: Gercekten Asya vs Londra karsilastirmasi
    # (kod ASIA donmez ama 02-08 = Asya range tracking penceresi)
    # ─────────────────────────────────────────────────────────
    print(f"\n\n  --- BONUS: Asya Range (02-08) vs Londra (08-13) vs NY (13-22) ---")
    print(f"  (Asia = 02-08 kodun RangeTracker.asia siniri, London icin degil)")
    print(f"  {'Session':<18} {'AsiaWr':>8} {'EarlyLonWr':>12} {'NY_WR':>8} {'Asia-LonFark':>12}")
    print(f"  {'-'*60}")

    for fname in ["trades_default.parquet", "trades_real_cbdr.parquet", "trades_asia_range.parquet"]:
        fp = os.path.join(REPORTS_DIR, fname)
        if not os.path.isfile(fp):
            continue
        df = pd.read_parquet(fp)
        session_key = fname.replace("trades_", "").replace(".parquet", "")
        label = SESSION_LABELS.get(session_key, session_key)
        df["hour"] = pd.to_datetime(df["entry_time"]).dt.hour

        asia = df[df["hour"].between(2, 7)]
        early_lon = df[df["hour"].between(8, 12)]  # Londra 13'e kadar ama Asya'dan sonrasi
        ny = df[df["hour"].between(13, 21)]

        def wr(df):
            return (df["final_pnl_usd"] > 0).mean() * 100 if len(df) else 0

        a_wr, e_wr, n_wr = wr(asia), wr(early_lon), wr(ny)
        print(f"  {label:<18} {a_wr:>7.1f}% {e_wr:>10.1f}% {n_wr:>7.1f}% {a_wr-e_wr:>+10.1f}%")


if __name__ == "__main__":
    analyze()
