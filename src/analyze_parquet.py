"""
analyze_parquet.py — Parquet dosyalarindan 3 soruyu cevapla:
  1) Entry saati histogrami (0-23 UTC) — hangi saatlerde trade acilmis
  2) fail: %0.00 kod mantigi + Wilson hesaplama
  3) Asya saatlerinde trade simülasyonu
"""
import os
import math
import pandas as pd

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

SESSION_LABELS = {
    "default":   "DEFAULT   [22:00-02:00]",
    "real_cbdr": "REAL_CBDR [19:00-01:00]",
    "asia_range":"ASIA_RANGE [01:00-05:00]",
}

# ─── wilson_upper (birebir cbdr_default.py'deki kod) ──────
def wilson_upper(wins: int, trades: int, z: float = 1.96) -> float:
    if trades == 0:
        return 1.0
    z2 = z * z
    p_hat = wins / trades
    denominator = 1 + z2 / trades
    centre = p_hat + z2 / (2 * trades)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * trades)) / trades)
    return min(1.0, (centre + margin) / denominator)


# ─────────────────────────────────────────────────────────────
#  SORU 1: Entry saati histogrami
# ─────────────────────────────────────────────────────────────
def question1():
    print("=" * 100)
    print("  SORU 1: Entry Saati Dagitimi (UTC) — Hangi saatlerde gercekten trade acilmis?")
    print("=" * 100)

    for fname in ["trades_default.parquet", "trades_real_cbdr.parquet", "trades_asia_range.parquet"]:
        fp = os.path.join(REPORTS_DIR, fname)
        if not os.path.isfile(fp):
            continue
        df = pd.read_parquet(fp)
        session_key = fname.replace("trades_", "").replace(".parquet", "")
        label = SESSION_LABELS.get(session_key, session_key)
        df["hour"] = pd.to_datetime(df["entry_time"]).dt.hour

        print(f"\n  >>> {label}  (toplam {len(df):,} trade)")
        hist = df["hour"].value_counts().sort_index()
        bar_max = hist.max() if len(hist) else 1
        for h in range(24):
            cnt = hist.get(h, 0)
            bar_len = int(cnt / bar_max * 40)
            bar = "█" * bar_len if bar_len else ""
            print(f"    {h:02d}:00  {cnt:>7,}  (%{cnt/len(df)*100:5.2f})  {bar}")

        # Per-symbol per-hour
        print(f"\n    -- Coin bazinda en yogun 3 saat --")
        sym_hours = df.groupby(["symbol", "hour"]).size().reset_index(name="cnt")
        for sym in sorted(df["symbol"].unique()):
            top3 = sym_hours[sym_hours["symbol"] == sym].nlargest(3, "cnt")
            hours_str = ", ".join(f"{r['hour']:02d}:00({r['cnt']})" for _, r in top3.iterrows())
            print(f"    {sym:<10} => {hours_str}")


# ─────────────────────────────────────────────────────────────
#  SORU 2: fail: %0.00 kodu ve anlami
# ─────────────────────────────────────────────────────────────
def question2():
    print("\n\n" + "=" * 100)
    print("  SORU 2: fail: %0.00 — Kaynak Kod + Gercek Zamanli Hesaplama")
    print("=" * 100)

    # Kod blokunu goster
    print(r'''
  Kaynak: cbdr_default.py / analyze_thresholds() — satir ~480-495

  ------------------------------------------------------------------------
  CBDR_BUCKETS = [
      (0, 1.0, "0-1%"),      # bucket 0: lo_pct=0
      (1.0, 1.5, "1-1.5%"),  # bucket 1: lo_pct=1.0
      (1.5, 2.0, "1.5-2%"),  # bucket 2: lo_pct=1.5
      (2.0, 3.0, "2-3%"),    # bucket 3: lo_pct=2.0
      (3.0, 5.0, "3-5%"),    # bucket 4: lo_pct=3.0
      (5.0, 999, ">5%"),     # bucket 5: lo_pct=5.0
  ]

  fail_limit = None
  for b in buckets:                     # SIRALI: 0-1%, 1-1.5%, 1.5-2%, ...
      if b["trades"] < min_bucket_trades:   # <100 trade varsa atla
          continue
      if b["wr"] > 0 and \
         wilson_upper(b["wins"], b["trades"]) < overall_wr:
          fail_limit = b["lo_pct"]           # ALT SINIR = threshold
          break                               # ILK kırılımda dur

  mantik:
    1. Bucketlar KUCUKTEN BUYUGE (0-1% ... >5%) taranir.
    2. wilson_upper(bucket) = bucket'in WR'sinin istatistiksel
       olarak ulasabilecegi EN IYIMSER (%95 GA ust sinir).
    3. Bu ust sinir bile genel WR'nin ALTINDAysa -> bucket
       "guvenilir sekilde kotu" sayilir.
    4. fail_limit = o bucket'in alt siniri (lo_pct).
    5. ILK kotu bucket'ta durur, gerisine bakmaz.
  ''')

    # Simdi gercek veriyle adim adim goster
    print("  --- GERCEK VERI ILE ORNEK (DEFAULT) ---\n")
    df = pd.read_parquet(os.path.join(REPORTS_DIR, "trades_default.parquet"))
    # CBDR bucket verisi yok (parquet'e kaydedilmiyor), ama WR'yi gosterebiliriz
    for sym in ["ADAUSDT", "APTUSDT", "ETHUSDT", "XRPUSDT"]:
        sd = df[df["symbol"] == sym]
        tot = len(sd)
        wins = (sd["final_pnl_usd"] > 0).sum()
        be = (sd["final_pnl_usd"] == 0).sum()
        losses = tot - wins - be
        wr = wins / tot * 100 if tot else 0
        # Wilson hesapla (tum veri tek bucket gibi)
        wu = wilson_upper(wins, tot) * 100
        print(f"  {sym:<10} {tot:>6} trade | WIN:{wins:>5} BE:{be:>5} LOSS:{losses:>5} | "
              f"WR={wr:>5.1f}% | WilsonUpper={wu:>5.2f}%")

    print(r'''
  ------------------------------------------------------------------------
  fail: %0.00  =  fail_limit = 0.0  =  ilk bucket (0-1%) kotu cikti

  Bu demek: CBDR genisligi 0-1% araligindaki gunlerin WR'si,
  wilson_upper() testine gore genel ortalamadan istatistiksel
  olarak anlamli sekilde DUSUK. Bucket'in alt siniri 0.0 oldugu
  icin %0.00 yaziliyor.

  ANLAMI: "En dar CBDR araligi bile zaten kotu" -> bu coin'de
  CBDR bazli filtreleme ise yaramaz, tum seviyeler benzer veya
  daha genis CBDR'ler DAHA iyi olabiliyor.

  fail: BULUNAMADI = hicbir bucket wilson testini gecmedi.
  Yani bucket'lar arasinda istatistiksel olarak anlamli fark
  yok (veya tum bucket'lar ortalamaya yakin).
  ------------------------------------------------------------------------
  ''')


# ─────────────────────────────────────────────────────────────
#  SORU 3: Asya saatlerinde trade simulasyonu
# ─────────────────────────────────────────────────────────────
def question3():
    print("\n\n" + "=" * 100)
    print("  SORU 3: Asya Saatlerinde Entry Simulasyonu (2:00-8:00 UTC)")
    print("=" * 100)
    print(r'''
  Onemli Uyari: Mevcut parquet verisi ZATEN saat filtresiyle
  toplanmis trade'leri iceriyor. "Entry filtresini tamamen
  kaldir" simule etmek icin AYRI BIR backtest gerekir.

  ANCAK: Uc farkli session'u karsilastirarak Asya saatlerinin
  etkisini dolayli olarak gorebiliriz:
    - DEFAULT    [22:00-02:00] -> fiilen 2:00-22:00 trade acar
    - REAL_CBDR  [19:00-01:00] -> fiilen 1:00-19:00 trade acar
    - ASIA_RANGE [01:00-05:00] -> fiilen 5:00-1:00 trade acar  (gece+Asya)

  (Not: SessionState entry filter'inin ters calistigini varsayarsak)
  ''')

    data = {}
    for fname in ["trades_default.parquet", "trades_real_cbdr.parquet", "trades_asia_range.parquet"]:
        fp = os.path.join(REPORTS_DIR, fname)
        if not os.path.isfile(fp):
            continue
        df = pd.read_parquet(fp)
        session_key = fname.replace("trades_", "").replace(".parquet", "")
        df["hour"] = pd.to_datetime(df["entry_time"]).dt.hour

        # Asya: 2-8 UTC
        df["is_asia"] = df["hour"].between(2, 7)
        london_ny = df[~df["is_asia"]]

        data[session_key] = {
            "all": df,
            "asia": df[df["is_asia"]],
            "ln": london_ny
        }

    # Karsilastirma tablosu
    print(f"  {'Session':<15} {'Segment':<12} {'Trades':>8} {'Wins':>7} {'WR%':>7} {'AvgPnL':>8}")
    print(f"  {'-'*55}")
    for sk, d in data.items():
        label = SESSION_LABELS.get(sk, sk)
        for seg_name, seg_df in [("Tumu", d["all"]), ("Asya(2-8)", d["asia"]), ("Londra/NY", d["ln"])]:
            n = len(seg_df)
            w = (seg_df["final_pnl_usd"] > 0).sum()
            wr = w / n * 100 if n else 0
            ap = seg_df["final_pnl_usd"].mean() if n else 0
            print(f"  {label:<15} {seg_name:<12} {n:>8,} {w:>7} {wr:>6.1f}% {ap:>+8.2f}")

    # Coin bazinda Asya vs Londra/NY karsilastirmasi
    print(f"\n  --- Coin Bazinda: Asya vs Londra/NY WR karsilastirmasi (DEFAULT) ---")
    print(f"  {'Coin':<10} {'AsiaTr':>8} {'AsiaWR':>8} {'LN_Tr':>8} {'LN_WR':>8} {'FarkWR':>8}")
    print(f"  {'-'*55}")
    dft = data["default"]["all"]
    for sym in sorted(dft["symbol"].unique()):
        sd = dft[dft["symbol"] == sym]
        asia = sd[sd["is_asia"]]
        ln = sd[~sd["is_asia"]]
        n_a, w_a = len(asia), (asia["final_pnl_usd"] > 0).sum()
        n_l, w_l = len(ln), (ln["final_pnl_usd"] > 0).sum()
        wr_a = w_a / n_a * 100 if n_a else 0
        wr_l = w_l / n_l * 100 if n_l else 0
        print(f"  {sym:<10} {n_a:>8,} {wr_a:>7.1f}% {n_l:>8,} {wr_l:>7.1f}% {wr_a-wr_l:>+7.1f}%")


if __name__ == "__main__":
    question1()
    question2()
    question3()
