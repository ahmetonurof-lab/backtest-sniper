"""
replay_trailing_v2.py — A/B/C trailing replay karsilastirmasi.

Ayni entry uretim kurali uzerinde 3 trailing modu kosar (entry'ler trailing'den
bagimsiz uretilir; modlar yalnizca entry sonrasi SL/TP davranisini degistirir):

  A (retrace)      : yalnizca FVG gap'i icinde kapanis onaylar (eski davranis)
  B (continuation) : gap ici kapanis VEYA pozisyon lehine far-side kapanis
                     (short: close < bottom, long: close > top) — varsayilan
  C (atr_chase)    : B + FVG aday kullanilamazsa SL = close -+ K*ATR fallback
                     (K = ATR_TRAIL_MULT) ve is_placeable sartiyla.

Kullanim:
  python replay_trailing_v2.py                 # tum 30 coin
  python replay_trailing_v2.py ADAUSDT SOLUSDT  # secili coinler
  python replay_trailing_v2.py --workers 6     # paralel worker sayisi

Cikti: reports/trailing_replay_ab_c.md (per-trade + ozet tablo).
"""

import builtins
import concurrent.futures
import os
import sys
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
_SNIPER_SRC = os.path.join(_HERE, "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import analyzer_v5  # noqa: E402
import config as cfg  # noqa: E402

MODES = [("A", "retrace"), ("B", "continuation"), ("C", "atr_chase")]


class _CaptureLogger:
    """Engine'in log_trade cagrilarini toplar (trailing_count dahil)."""

    def __init__(self):
        self.trades = []

    def log_trade(self, d):
        self.trades.append(dict(d))

    def save_and_clear(self):
        pass


def _worker(sym, mode):
    """Tek coin + tek mod (paralel worker). Sessiz calisir."""
    real_print = builtins.print
    builtins.print = lambda *a, **k: None
    try:
        analyzer_v5.TRAIL_MODE = mode
        lg = _CaptureLogger()
        analyzer_v5._LOGGER = lg
        try:
            res = analyzer_v5.collect_fvg_profile(sym)
            ok = not (res is None or res[0] is None)
        except Exception:
            ok = False
        analyzer_v5._LOGGER = None
        return sym, ok, lg.trades
    finally:
        builtins.print = real_print


def run_mode(mode, symbols, workers):
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        fut_map = {ex.submit(_worker, sym, mode): sym for sym in symbols}
        trades = []
        errors = []
        for fut in concurrent.futures.as_completed(fut_map):
            sym, ok, ts = fut.result()
            if not ok:
                errors.append(sym)
            trades.extend(ts)
    return trades, errors


def _key(t):
    return (t["symbol"], t["entry_time"], t["side"], t["entry_price"])


def _summarize(trades):
    n = len(trades)
    if n == 0:
        return {
            "n": 0,
            "tp": 0,
            "ptrail": 0,
            "loss": 0,
            "win_pct": 0.0,
            "pnl": 0.0,
            "hops": 0,
            "hops_per_trade": 0.0,
        }
    tp = sum(1 for t in trades if t["result"] == "TP")
    ptrail = sum(1 for t in trades if t["result"] == "PROFIT_TRAIL")
    loss = n - tp - ptrail
    pnl = sum(t["final_pnl_usd"] for t in trades)
    hops = sum(t["trailing_count"] for t in trades)
    return {
        "n": n,
        "tp": tp,
        "ptrail": ptrail,
        "loss": loss,
        "win_pct": (tp + ptrail) / n * 100 if n else 0.0,
        "pnl": pnl,
        "hops": hops,
        "hops_per_trade": hops / n if n else 0.0,
    }


def _diff_rows(base, variant):
    """base -> variant gecisinde farkli sonuclanan trade'ler."""
    rows = []
    for k, v in variant.items():
        b = base.get(k)
        if b is None:
            continue
        if (b["trailing_count"], b["result"], b["final_pnl_usd"]) != (
            v["trailing_count"],
            v["result"],
            v["final_pnl_usd"],
        ):
            rows.append((k, b, v))
    return rows


def main():
    args = sys.argv[1:]
    workers = 4
    if "--workers" in args:
        i = args.index("--workers")
        try:
            workers = max(1, int(args[i + 1]))
            del args[i : i + 2]
        except (ValueError, IndexError):
            pass
    feather_dir = os.path.join(_HERE, "data", "daily")
    all_syms = sorted(
        f[: -len("_1m_raw.feather")]
        for f in os.listdir(feather_dir)
        if f.endswith("_1m_raw.feather")
    )
    symbols = [s.upper() for s in args if s.upper() in set(all_syms)]
    if not symbols:
        symbols = all_syms

    t0 = datetime.now()
    results = {}
    errors = {}
    for tag, mode in MODES:
        trades, errs = run_mode(mode, symbols, workers)
        results[tag] = {_key(t): t for t in trades}
        errors[tag] = errs
        dt = (datetime.now() - t0).total_seconds()
        print(f"[{tag}:{mode}] {len(trades)} trade, {len(errs)} hatali coin, {dt:.0f}s")

    base_a = results["A"]
    base_b = results["B"]
    base_c = results["C"]

    sum_a = _summarize(base_a.values())
    sum_b = _summarize(base_b.values())
    sum_c = _summarize(base_c.values())
    ab_rows = _diff_rows(base_a, base_b)
    bc_rows = _diff_rows(base_b, base_c)
    ab_pnl_delta = sum(v["final_pnl_usd"] - b["final_pnl_usd"] for _, b, v in ab_rows)
    bc_pnl_delta = sum(v["final_pnl_usd"] - b["final_pnl_usd"] for _, b, v in bc_rows)
    ab_hop_delta = sum(v["trailing_count"] - b["trailing_count"] for _, b, v in ab_rows)
    bc_hop_delta = sum(v["trailing_count"] - b["trailing_count"] for _, b, v in bc_rows)

    atm = getattr(cfg, "ATR_TRAIL_MULT", None)
    tmm = getattr(cfg, "TRAIL_MIN_MOVE_MULT", None)

    lines = []
    w = lines.append
    w(
        f"# Trailing Replay — A/B/C Karsilastirma ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    )
    w("")
    w("Ayni entry uretim kurali, 3 trailing modu:")
    w(
        "- **A retrace-only**: yalnizca FVG gap'i icinde kapanis onaylar (eski davranis)."
    )
    w(
        "- **B +continuation**: gap ici VEYA pozisyon lehine far-side kapanis (short `close < bottom`, long `close > top`); aksi yon invalidation."
    )
    w(
        "- **C +ATR-chase**: B + FVG aday yoksa `SL = close -+ ATR_TRAIL_MULT*ATR` fallback."
    )
    w("")
    w(
        f"Parametreler: `ATR_TRAIL_MULT={atm}`, `TRAIL_MIN_MOVE_MULT={tmm}`; entry/komisyon ve TP-RR mantigi moddan etkilenmez (TP degisimi yalnizca trail kaymasi kadar)."
    )
    w(f"Coinler ({len(symbols)}): {', '.join(symbols)}")
    w(
        f"Hatali coin: A={','.join(errors['A']) or '-'} | B={','.join(errors['B']) or '-'} | C={','.join(errors['C']) or '-'}"
    )
    w("")
    w(
        "> Not: Modlar farkli SL/TP uzerinden exit zamanini degistirdigi icin trade sayilari modlar arasinda farklidir"
    )
    w(
        "> (bir trade'in exit'i, bir sonraki entry'nin zamanlamasini kaydirir). Ozet satirlari mod-ic toplamlardir;"
    )
    w(
        "> per-trade tablosu yalnizca ayni (coin, entry) ile eslesen trade'leri karsilastirir."
    )
    w("")
    w("## Ozet")
    w("")
    hdr = "| Mod | Trade | TP | PTrail | LOSS | PE% | NetPnL | ToplamHOP | HOP/trade |"
    w(hdr)
    w("|" + "---|" * (hdr.count("|") - 1))
    for tag, s in (("A", sum_a), ("B", sum_b), ("C", sum_c)):
        w(
            f"| {tag} | {s['n']} | {s['tp']} | {s['ptrail']} | {s['loss']} | "
            f"{s['win_pct']:.1f}% | {s['pnl']:+,.0f} | {s['hops']} | {s['hops_per_trade']:.2f} |"
        )
    w("")
    w("## A → B (continuation eklenince)")
    w(f"- Farkli sonuclanan (eslesen) trade: **{len(ab_rows)}**")
    w(f"- Toplam HOP degisimi: **{ab_hop_delta:+d}**")
    w(f"- Toplam PnL degisimi: **{ab_pnl_delta:+,.0f} USD**")
    w(
        f"- HOP artan trade sayisi: {sum(1 for _, b, v in ab_rows if v['trailing_count'] > b['trailing_count'])}"
    )
    w(
        f"- HOP azalan trade sayisi: {sum(1 for _, b, v in ab_rows if v['trailing_count'] < b['trailing_count'])}"
    )
    w(
        f"- Sonuc degisen trade sayisi: {sum(1 for _, b, v in ab_rows if b['result'] != v['result'])}"
    )
    w("")
    w("## B → C (ATR-chase fallback eklenince)")
    w(f"- Farkli sonuclanan (eslesen) trade: **{len(bc_rows)}**")
    w(f"- Toplam HOP degisimi: **{bc_hop_delta:+d}**")
    w(f"- Toplam PnL degisimi: **{bc_pnl_delta:+,.0f} USD**")
    w(
        f"- HOP artan trade sayisi: {sum(1 for _, b, v in bc_rows if v['trailing_count'] > b['trailing_count'])}"
    )
    w(
        f"- HOP azalan trade sayisi: {sum(1 for _, b, v in bc_rows if v['trailing_count'] < b['trailing_count'])}"
    )
    w(
        f"- Sonuc degisen trade sayisi: {sum(1 for _, b, v in bc_rows if b['result'] != v['result'])}"
    )

    def _fmt_time(ts):
        if isinstance(ts, datetime):
            return ts.strftime("%Y-%m-%d %H:%M")
        return str(ts)

    for title, rows, tag_a, tag_b in (
        ("## A vs B — Per-trade fark (eslesen)", ab_rows, "A", "B"),
        ("## B vs C — Per-trade fark (eslesen)", bc_rows, "B", "C"),
    ):
        if not rows:
            w("")
            w(title)
            w("")
            w("*(Fark yok)*")
            continue
        w("")
        w(title)
        w("")
        hdr2 = (
            f"| Coin | Side | Entry | Sonuc {tag_a} | Sonuc {tag_b} | "
            f"HOP {tag_a} | HOP {tag_b} | PnL {tag_a} | PnL {tag_b} |"
        )
        w(hdr2)
        w("|" + "---|" * (hdr2.count("|") - 1))
        for k, b, v in rows:
            sym, et, side, _ep = k
            w(
                f"| {sym} | {side} | {_fmt_time(et)} | {b['result']} | {v['result']} | "
                f"{b['trailing_count']} | {v['trailing_count']} | "
                f"{b['final_pnl_usd']:+,.0f} | {v['final_pnl_usd']:+,.0f} |"
            )

    w("")
    w("## Yorum")
    w("")
    w(
        "- A->B: continuation yalnizca lehine far-side kapanista ek SL ceker; retrace onceligi korunur (ilk gorulen onay kazanir), aksi yon invalidation."
    )
    w(
        "- B->C: ATR-chase yalnizca FVG aday kullanilamadiginda devreye girer; `TMM*risk` altindaki hareketler atlanir."
    )
    w(
        "- Per-trade eslesen karsilastirma yalnizca ayni entry anina sahip trade'leri kapsar; toplam farklar ayni zamanda trade devir hizi etkisini icerir."
    )

    report_dir = os.path.join(_HERE, "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    rpt_path = os.path.join(report_dir, "trailing_replay_ab_c.md")
    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nRapor: {rpt_path}")
    print(f"Toplam sure: {(datetime.now() - t0).total_seconds():.0f}s")


if __name__ == "__main__":
    main()
