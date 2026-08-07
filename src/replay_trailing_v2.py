"""
replay_trailing_v2.py — A/B/C trailing replay karsilastirmasi + parametre taramasi.

Ayni entry uretim kurali uzerinde trailing modlari kosar (entry'ler trailing'den
bagimsiz uretilir; modlar yalnizca entry sonrasi SL/TP davranisini degistirir):

  A (retrace)      : yalnizca FVG gap'i icinde kapanis onaylar (eski davranis)
  B (continuation) : gap ici kapanis VEYA pozisyon lehine far-side kapanis
                     (short: close < bottom, long: close > top)
  C (atr_chase)    : B + FVG aday kullanilamazsa SL = close -+ K*ATR fallback

Parametre taramasi (bas mühendis direktifi):
  --cont-k K...    continuation/atr_chase SL tamponu K*ATR (varsayilan: 0.1).
                   Daha genis K (0.3/0.5/1.0) retrace'in dogal mesafesine
                   yakinlasir -> trend-ici noise'a dayaniklilik.
  --cont-bars N... continuation onay penceresi: far-side kapanisin ard arda
                   N bar korunmasi gerekir (varsayilan: 1 = ilk kapanista
                   tetikle; sahte kirilim filtreleri N > 1).

Kullanim:
  python replay_trailing_v2.py                          # baseline A/B/C
  python replay_trailing_v2.py ADAUSDT SOLUSDT          # secili coinler
  python replay_trailing_v2.py --workers 6              # paralel worker sayisi
  python replay_trailing_v2.py --cont-k 0.3 0.5 1.0     # K taramasi
  python replay_trailing_v2.py --cont-bars 2 3          # onay penceresi taramasi
  python replay_trailing_v2.py --cont-k 0.3 0.5 --cont-bars 1 2

Cikti: reports/trailing_replay_ab_c.md (ozet + varyasyon + per-trade tablolari).
"""

import builtins
import concurrent.futures
import itertools
import os
import pickle
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

BARS_PER_HOUR = 4  # 15dk bar


class _CaptureLogger:
    """Engine'in log_trade cagrilarini toplar (trailing_count + hold_bars dahil)."""

    def __init__(self):
        self.trades = []

    def log_trade(self, d):
        self.trades.append(dict(d))

    def save_and_clear(self):
        pass


def _worker(sym, mode, k, bars):
    """Tek coin + tek mod + tek (K, bars) (paralel worker). Sessiz calisir."""
    real_print = builtins.print
    builtins.print = lambda *a, **k: None
    try:
        analyzer_v5.TRAIL_MODE = mode
        analyzer_v5.CONT_BUFFER_MULT = k
        analyzer_v5.CONT_CONFIRM_BARS = bars
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


def run_mode(mode, symbols, workers, k, bars):
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        fut_map = {ex.submit(_worker, sym, mode, k, bars): sym for sym in symbols}
        trades = []
        errors = []
        for fut in concurrent.futures.as_completed(fut_map):
            sym, ok, ts = fut.result()
            if not ok:
                errors.append(sym)
            trades.extend(ts)
    return trades, errors


def _checkpoint_path():
    return os.path.join(_HERE, "..", "reports", "_replay_checkpoint.pkl")


def _load_checkpoint(runs):
    """Onceki yarim kalmis taramayi yukler (runs listesi birebir eslesmeli)."""
    path = _checkpoint_path()
    if not os.path.exists(path):
        return {}, {}
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        if data.get("runs") != runs:
            print("Checkpoint config uyusmuyor — temiz basliyorum.")
            return {}, {}
        return data.get("results", {}), data.get("errors", {})
    except Exception as e:  # noqa: BLE001
        print(f"Checkpoint okunamadi ({e}) — temiz basliyorum.")
        return {}, {}


def _save_checkpoint(runs, results, errors):
    path = _checkpoint_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump({"runs": runs, "results": results, "errors": errors}, f)


def _key(t):
    return (t["symbol"], t["entry_time"], t["side"], t["entry_price"])


def _avg_hold(trades, results_set):
    sel = [t.get("hold_bars", 0) for t in trades if t["result"] in results_set]
    return sum(sel) / len(sel) if sel else 0.0


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
            "avg_hold_bars": 0.0,
            "avg_hold_tp": 0.0,
            "avg_hold_ptrail": 0.0,
            "avg_hold_loss": 0.0,
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
        "avg_hold_bars": _avg_hold(trades, {"TP", "PROFIT_TRAIL", "LOSS", "OPEN"}),
        "avg_hold_tp": _avg_hold(trades, {"TP"}),
        "avg_hold_ptrail": _avg_hold(trades, {"PROFIT_TRAIL"}),
        "avg_hold_loss": _avg_hold(trades, {"LOSS"}),
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


def _avg_hold_delta(rows):
    ds = [v.get("hold_bars", 0) - b.get("hold_bars", 0) for _, b, v in rows]
    return sum(ds) / len(ds) if ds else 0.0


def _fmt_time(ts):
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M")
    return str(ts)


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

    def _vals(flag, default, cast):
        if flag not in args:
            return list(default)
        i = args.index(flag)
        out = []
        j = i + 1
        while j < len(args) and not args[j].startswith("-"):
            try:
                out.append(cast(args[j]))
            except ValueError:
                break
            j += 1
        del args[i:j]
        return out or list(default)

    cont_ks = _vals("--cont-k", [0.1], float)
    cont_bars = _vals("--cont-bars", [1], int)

    cont_only = "--cont-only" in args
    if cont_only:
        args.remove("--cont-only")

    feather_dir = os.path.join(_HERE, "data", "daily")
    all_syms = sorted(
        f[: -len("_1m_raw.feather")]
        for f in os.listdir(feather_dir)
        if f.endswith("_1m_raw.feather")
    )
    symbols = [s.upper() for s in args if s.upper() in set(all_syms)]
    if not symbols:
        symbols = all_syms

    combos = list(itertools.product(cont_ks, cont_bars))
    runs = [("A", "retrace", 0.1, 1)]
    for k, bars in combos:
        runs.append(("B", "continuation", k, bars))
        if not cont_only:
            runs.append(("C", "atr_chase", k, bars))

    print(
        f"{len(runs)} kosis: A baseline + B/C x {len(combos)} kombinasyon "
        f"(K={cont_ks}, bars={cont_bars}), {len(symbols)} coin, {workers} worker"
    )
    t0 = datetime.now()
    results, errors = _load_checkpoint(runs)
    done = set(results)
    pending = [r for r in runs if (r[0], r[2], r[3]) not in done]
    if results:
        print(
            f"Checkpoint'ten {len(results)}/{len(runs)} kosis yuklendi, "
            f"{len(pending)} kalan: {[f'{t}:{k}/{b}' for t, _m, k, b in pending]}"
        )
    for tag, mode, k, bars in pending:
        key = (tag, k, bars)
        trades, errs = run_mode(mode, symbols, workers, k, bars)
        results[key] = {_key(t): t for t in trades}
        errors[key] = errs
        _save_checkpoint(runs, results, errors)
        dt = (datetime.now() - t0).total_seconds()
        print(
            f"[{tag}:{mode} K={k} bars={bars}] {len(trades)} trade, "
            f"{len(errs)} hatali coin, {dt:.0f}s (checkpoint kaydedildi)"
        )

    base_key = ("A", 0.1, 1)
    base_a = results[base_key]

    atm = getattr(cfg, "ATR_TRAIL_MULT", None)
    tmm = getattr(cfg, "TRAIL_MIN_MOVE_MULT", None)

    lines = []
    w = lines.append
    w(
        f"# Trailing Replay — {'A/B' if cont_only else 'A/B/C'} + Parametre Taramasi ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    )
    w("")
    w("Ayni entry uretim kurali, trailing modlari + (K, bars) taramasi:")
    w(
        "- **A retrace-only**: yalnizca FVG gap'i icinde kapanis onaylar (eski davranis)."
    )
    w(
        "- **B +continuation**: gap ici VEYA pozisyon lehine far-side kapanis (short `close < bottom`, long `close > top`); aksi yon invalidation."
    )
    w(
        "- **C +ATR-chase**: B + FVG aday yoksa `SL = close -+ K*ATR` fallback (`K = CONT_BUFFER_MULT`)."
    )
    w(
        "- `CONT_BUFFER_MULT` (K): continuation/atr-chase SL tamponu; `CONT_CONFIRM_BARS` (bars): far-side kapanisin ard arda N bar korunmasi (N=1 ilk kapanista tetikler)."
    )
    w("")
    w(
        "Not (etiket sabit): A/B/C semasi onceki taramalarla AYNIDIR — B, daha once K=0.3/N=1'de negatif "
        "cikan 'continuation' modunun kendisidir; bu tarama ayni B modunu (K, N) gridi ile parametrize eder "
        "(`--cont-only` = C/ATR-chase atlanir, A baseline + B varyasyonlari kosulur)."
    )
    w("")
    w(
        f"Sabitler: `ATR_TRAIL_MULT={atm}`, `TRAIL_MIN_MOVE_MULT={tmm}`; entry/komisyon ve TP-RR mantigi moddan etkilenmez."
    )
    w(f"Coinler ({len(symbols)}): {', '.join(symbols)}")
    w("")
    w("## Ozet")
    w("")
    hdr = (
        "| Mod | K | Bars | Trade | TP | PTrail | LOSS | PE% | NetPnL | "
        "HOP | HOP/t | AvgHold(b) | AvgHold(h) |"
    )
    w(hdr)
    w("|" + "---|" * (hdr.count("|") - 1))
    for tag, _mode, k, bars in runs:
        s = _summarize(results[(tag, k, bars)].values())
        w(
            f"| {tag} | {k} | {bars} | {s['n']} | {s['tp']} | {s['ptrail']} | {s['loss']} | "
            f"{s['win_pct']:.1f}% | {s['pnl']:+,.0f} | {s['hops']} | "
            f"{s['hops_per_trade']:.2f} | {s['avg_hold_bars']:.1f} | "
            f"{s['avg_hold_bars'] / BARS_PER_HOUR:.1f} |"
        )
    w("")
    w(
        "> AvgHold: ortalama bar basi holding (15dk bar); (h) = saat. Modlar SL/TP uzerinden exit zamanini degistirdigi icin trade sayilari da degisir."
    )
    w("")

    # ── Varyasyon analizi: her B/C run vs A baseline (eslesen trade'ler) ──
    w("## A (retrace baseline) vs varyasyon — eslesen trade'ler")
    w("")
    vhdr = (
        "| Varyasyon | Matched | Farkli | HOP + | HOP - | HOP Delta | "
        "PnL Delta | Sonuc Degisen | AvgHold Delta(b) | AvgHold Delta(h) |"
    )
    w(vhdr)
    w("|" + "---|" * (vhdr.count("|") - 1))
    for tag, _mode, k, bars in runs:
        if tag == "A":
            continue
        key = (tag, k, bars)
        variant = results[key]
        rows = _diff_rows(base_a, variant)
        ho_d = sum(v["trailing_count"] - b["trailing_count"] for _, b, v in rows)
        pnl_d = sum(v["final_pnl_usd"] - b["final_pnl_usd"] for _, b, v in rows)
        n_up = sum(1 for _, b, v in rows if v["trailing_count"] > b["trailing_count"])
        n_dn = sum(1 for _, b, v in rows if v["trailing_count"] < b["trailing_count"])
        n_rc = sum(1 for _, b, v in rows if b["result"] != v["result"])
        hd = _avg_hold_delta(rows)
        w(
            f"| {tag} K={k} B={bars} | {len(variant)} | {len(rows)} | {n_up} | {n_dn} | "
            f"{ho_d:+d} | {pnl_d:+,.0f} | {n_rc} | {hd:+.1f} | {hd / BARS_PER_HOUR:+.1f} |"
        )
    w("")
    w(
        "> Hipotez kontrolu: AvgHold Delta > 0, genis K / teyit penceresi SL'yi gec kaydirdigi icin holding'i uzatir (erken kesmeyi onler)."
    )

    # ── A/B/C per-trade detay yalnizca tek kombinasyon varsa (eski davranis) ──
    if len(runs) == 3:
        base_b = results[("B", combos[0][0], combos[0][1])]
        base_c = results[("C", combos[0][0], combos[0][1])]
        ab_rows = _diff_rows(base_a, base_b)
        bc_rows = _diff_rows(base_b, base_c)
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
                f"HOP {tag_a} | HOP {tag_b} | PnL {tag_a} | PnL {tag_b} | "
                f"Hold {tag_a}(b) | Hold {tag_b}(b) |"
            )
            w(hdr2)
            w("|" + "---|" * (hdr2.count("|") - 1))
            for k2, b, v in rows:
                sym, et, side, _ep = k2
                w(
                    f"| {sym} | {side} | {_fmt_time(et)} | {b['result']} | {v['result']} | "
                    f"{b['trailing_count']} | {v['trailing_count']} | "
                    f"{b['final_pnl_usd']:+,.0f} | {v['final_pnl_usd']:+,.0f} | "
                    f"{b.get('hold_bars', 0)} | {v.get('hold_bars', 0)} |"
                )

    w("")
    w("## Yorum")
    w("")
    w(
        "- A->B/C: continuation yalnizca lehine far-side kapanista ek SL ceker; retrace onceligi korunur (ilk gorulen onay kazanir), aksi yon invalidation."
    )
    w(
        "- B->C: ATR-chase yalnizca FVG aday kullanilamadiginda devreye girer; `TMM*risk` altindaki hareketler atlanir."
    )
    w(
        "- Hipotez: dar K (0.1) SL'yi fiyatin az once gectigi sinirin hemen yanina koyar -> trend-ici pullback'te erken cikis; genis K bunu retrace'in dogal mesafesine yakinlastirir (AvgHold ve PnL satirlarindan takip edin)."
    )
    w(
        "- N-bar teyit (bars > 1): ilk far-side kapanista degil, ard arda N kapanis sonrasi tetiklenir — sahte kirilimlari filtreler; trade sayisini azaltmasi beklenir."
    )

    report_dir = os.path.join(_HERE, "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    rpt_path = os.path.join(report_dir, "trailing_replay_ab_c.md")
    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    ck = _checkpoint_path()
    if os.path.exists(ck):
        os.remove(ck)
    print(f"\nRapor: {rpt_path}")
    print(f"Toplam sure: {(datetime.now() - t0).total_seconds():.0f}s")


if __name__ == "__main__":
    main()
