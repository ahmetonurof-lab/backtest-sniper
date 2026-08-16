"""run_sf_two_stage.py — STRUCTURAL FALLBACK iki asamali tarama.

Asama 1 (tarama): secili coinlerde varyantlar SERI kosulur; kazanan belirlenir.
Asama 2 (dogrulama): secilen varyantlar tam evrende BASELINE ile karsilastirilir.

ISINMA KURALI (2026-08-16): varyantlar ASLA hep birlikte kosulmaz — varyant
bazinda SIRALI; her varyant kendi icinde istenirse --workers ile paralel calisir.
Ilk denemede 4 varyant workers 6 ile tek seferde kosulmus, makine kendini
korumaya almis; ayrı ayrı kosta problem yok. Her (sym, tag) sonucu disk'e
cache'lenir — makine kapanirsa kaldigi yerden devam eder.
Rapor: reports/analyzer_v5_sf_two_stage.md
"""

# ruff: noqa: E402
import concurrent.futures
import contextlib
import io
import json
import os
import sys
import threading
import time
from datetime import datetime

_ROOT = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_ROOT, "src")
sys.path.insert(0, _SRC)
_SNIPER_SRC = os.path.join(_ROOT, "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import analyzer_v5 as _eng  # noqa: E402
import config as cfg  # noqa: E402

_CACHE_DIR = os.path.join(_ROOT, "reports", "sf_two_stage_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

# (tag, structural_fallback_mode, profit_gate, swing_min_r)
_TAGS = [
    ("BASELINE", None, 0.0, None),
    ("OLD_PROFIT_GATE_1R", None, 1.0, None),
    ("A_LADDER_ONLY", "LADDER", 0.0, None),
    ("B_SWING_ONLY", "SWING", 0.0, None),
    ("B_SWING_ONLY_1_5R", "SWING", 0.0, 1.5),
    ("C_HYBRID", "HYBRID", 0.0, None),
]

# Tarama seti (dev-test sembolleri: 4 session tipine yayilir)
SCREEN_SYMS = [
    "BNBUSDT",
    "SOLUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "XRPUSDT",
    "ATOMUSDT",
]


def _cache_path(sym, tag):
    return os.path.join(_CACHE_DIR, f"{sym}_{tag}.json")


def _load_result(sym, tag):
    p = _cache_path(sym, tag)
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _save_result(sym, tag, res):
    with open(_cache_path(sym, tag), "w", encoding="utf-8") as f:
        json.dump(res, f, default=str)


def _run_task(sym, tag, mode, gate, swing_min_r, force=False):
    if not force:
        res = _load_result(sym, tag)
        if res is not None:
            print(
                f"  [{datetime.now().strftime('%H:%M:%S')}] {sym} {tag:<16} CACHE",
                flush=True,
            )
            return res
    t0 = time.time()
    try:
        # Motor gurultusunu (progress/load log'lari) sustur: cikti buyuklugunu
        # sinirli tutar, task basina tek satir yeter. Hatalar worker icinde
        # yakalanip dict olarak doner (stderr kaybi yok).
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            res = _eng._sf_compare_worker(sym, mode, gate, swing_min_r)
    except Exception as e:
        res = {"sym": sym, "error": str(e)}
    _save_result(sym, tag, res)
    dt = time.time() - t0
    if "stats" in res:
        s = res["stats"]
        print(
            f"  [{datetime.now().strftime('%H:%M:%S')}] {sym} {tag:<16} OK "
            f"{s['total_trades']} islem PnL={s['total_pnl']:+,.0f} {dt:.0f}s",
            flush=True,
        )
    else:
        print(
            f"  [{datetime.now().strftime('%H:%M:%S')}] {sym} {tag:<16} "
            f"ERR:{res.get('error', '?')} {dt:.0f}s",
            flush=True,
        )
    return res


def _aggregate(results, syms, tag_names):
    agg = {
        t: {
            "n": 0,
            "tp": 0,
            "pt": 0,
            "loss": 0,
            "pe": 0.0,
            "pf": 0.0,
            "dd": 0.0,
            "pnl": 0.0,
            "fvg": 0,
            "lad": 0,
            "swg": 0,
            "fb_tr": 0,
            "fb_pnl": 0.0,
        }
        for t in tag_names
    }
    for sym in syms:
        for tag in tag_names:
            res = results.get((sym, tag), {})
            if "error" in res or "stats" not in res:
                continue
            s = res["stats"]
            a = agg[tag]
            n = s["total_trades"]
            a["n"] += n
            a["tp"] += int(s["tp_pct"] * n / 100)
            a["pt"] += int(s["profit_trail_pct"] * n / 100)
            a["loss"] += int(s["loss_pct"] * n / 100)
            a["dd"] = max(a["dd"], s["max_dd_pct"])
            a["pnl"] += s["total_pnl"]
            a["fvg"] += s.get("sf_trail_fvg_count", 0)
            a["lad"] += s.get("sf_trail_ladder_count", 0)
            a["swg"] += s.get("sf_trail_swing_count", 0)
            a["fb_tr"] += s.get("sf_fallback_only_trades", 0)
            a["fb_pnl"] += s.get("sf_fallback_only_pnl", 0)
    for t in tag_names:
        a = agg[t]
        a["pe"] = (a["tp"] + a["pt"]) / a["n"] * 100 if a["n"] else 0.0
        gp = sum(
            results[(s, t)]["stats"]["total_pnl"]
            for s in syms
            if "stats" in results.get((s, t), {})
            and results[(s, t)]["stats"]["total_pnl"] > 0
        )
        gl = abs(
            sum(
                results[(s, t)]["stats"]["total_pnl"]
                for s in syms
                if "stats" in results.get((s, t), {})
                and results[(s, t)]["stats"]["total_pnl"] < 0
            )
        )
        a["pf"] = 999.0 if gl == 0 else gp / gl
    return agg


def _print_table(title, agg, tag_names):
    print(f"\n  --- {title} ---")
    print(
        f"  {'Mod':<18} {'Trade':>6} {'TP%':>6} {'PTrail%':>8} {'PE%':>6} "
        f"{'PF':>6} {'MaxDD%':>7} {'NetPnL':>12} {'Exp/t':>8}"
    )
    for t in tag_names:
        a = agg[t]
        exp = a["pnl"] / a["n"] if a["n"] else 0.0
        print(
            f"  {t:<18} {a['n']:>6} {a['tp'] / a['n'] * 100 if a['n'] else 0:>6.1f} "
            f"{a['pt'] / a['n'] * 100 if a['n'] else 0:>8.1f} {a['pe']:>6.1f} "
            f"{a['pf']:>6.2f} {a['dd']:>7.1f} {a['pnl']:>+12,.0f} {exp:>+8.2f}"
        )


def _run_stage(syms, tags, workers=1):
    """Bir kume tag'i kosar. Varyantlar arasi SIRALI (isinma korumasi);
    workers>1 ise yalnizca o varyantin coinleri paralel kosulur."""
    results = {}
    for tag, mode, gate, swing_min_r in tags:
        tasks = [(sym, tag, mode, gate, swing_min_r) for sym in sorted(syms)]
        if workers <= 1:
            for sym, _, m, g, smr in tasks:
                results[(sym, tag)] = _run_task(sym, tag, m, g, smr)
        else:
            print(
                f"  [{datetime.now().strftime('%H:%M:%S')}] {tag} — "
                f"{len(tasks)} coin / {workers} worker (varyant SIRALI)",
                flush=True,
            )
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
                fut_map = {
                    ex.submit(_run_task, sym, tag, m, g, smr): (sym, tag)
                    for sym, _, m, g, smr in tasks
                }
                for fut in concurrent.futures.as_completed(fut_map):
                    key = fut_map[fut]
                    try:
                        results[key] = fut.result()
                    except Exception as e:
                        results[key] = {"sym": key[0], "error": str(e)}
    return results


def _start_heartbeat():
    """Cikti sessizken islemci host tarafindan oldurulmesin diye 10 sn'de bir
    nokta basar (uzun sessiz task'larda tool'u 'cikti yok' sanmasin)."""

    def _beat():
        while True:
            time.sleep(10)
            sys.stdout.write(".")
            sys.stdout.flush()

    t = threading.Thread(target=_beat, daemon=True)
    t.start()
    return t


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SF iki asama tarama")
    parser.add_argument(
        "--screen-syms",
        nargs="+",
        default=SCREEN_SYMS,
        help="Asama 1 tarama coinleri",
    )
    parser.add_argument(
        "--stage2-only", action="store_true", help="Asama 2'yi dogrudan baslat"
    )
    parser.add_argument(
        "--force", action="store_true", help="Cache'i yok say, yeniden kos"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Varyant ICINDE coin paralelligi. Varyantlar arasi daima SIRALI "
        "(isinma korumasi); yalnizca tek varyantin coinleri bu kadar worker ile "
        "paralel kosulur.",
    )
    parser.add_argument(
        "--validate-tags",
        nargs="+",
        default=None,
        help="Asama 2 dogrulama tag'leri (BASELINE disinda). Varsayilan: kazanan. "
        "Ornek: --validate-tags A_LADDER_ONLY B_SWING_ONLY B_SWING_ONLY_1_5R C_HYBRID",
    )
    args = parser.parse_args()

    t_all = time.time()
    tag_names = [t for t, *_ in _TAGS]
    _start_heartbeat()

    # ── Asama 1: tarama ──
    if not args.stage2_only:
        syms1 = sorted(args.screen_syms)
        print("=" * 100)
        print(f"  ASAMA 1 — TARAMA ({len(syms1)} coin, seri)")
        print(f"  Coinler: {', '.join(syms1)}")
        print("=" * 100)
        r1 = _run_stage(syms1, _TAGS)
        a1 = _aggregate(r1, syms1, tag_names)
        _print_table("ASAMA 1 — TOPLAM", a1, tag_names)
        b = a1["BASELINE"]
        print("\n  Varyant vs BASELINE (NetPnL farki):")
        for t in ("A_LADDER_ONLY", "B_SWING_ONLY", "B_SWING_ONLY_1_5R", "C_HYBRID"):
            d = a1[t]["pnl"] - b["pnl"]
            print(f"    {t:<18} Δ={d:+,.0f}  {'> BASELINE' if d > 0 else '< BASELINE'}")
        best = max(
            ("A_LADDER_ONLY", "B_SWING_ONLY", "B_SWING_ONLY_1_5R", "C_HYBRID"),
            key=lambda t: a1[t]["pnl"],
        )
        print(f"\n  KAZANAN VARYANT: {best} (NetPnL={a1[best]['pnl']:+,.0f})")
    else:
        # stage2-only: cache'ten kazanan tag'i oku
        best_path = os.path.join(_CACHE_DIR, "_winner.txt")
        if not os.path.isfile(best_path):
            print("HATA: stage2-only icin once asama 1 kosulmali.")
            sys.exit(1)
        with open(best_path, "r", encoding="utf-8") as f:
            best = f.read().strip()
        print(f"  Cache'ten kazanan: {best}")
        syms1 = []
        r1 = {}
        # Asama 1 sonuclarini cache'ten geri yukle (rapor tablosu icin)
        for sym in sorted(SCREEN_SYMS):
            for tag, *_ in _TAGS:
                r = _load_result(sym, tag)
                if r is not None:
                    r1[(sym, tag)] = r
        if r1:
            syms1 = sorted({s for (s, _) in r1})
        a1 = _aggregate(r1, syms1, tag_names)

    # ── Asama 2: tam evren dogrulama ──
    syms2 = sorted(cfg.SYMBOLS)
    if args.validate_tags:
        validate = list(dict.fromkeys(args.validate_tags))
        for t in validate:
            if t not in tag_names:
                print(f"HATA: bilinmeyen tag '{t}'. Secenekler: {tag_names}")
                sys.exit(1)
    else:
        validate = [best]
    tags2 = [t for t in _TAGS if t[0] in (["BASELINE"] + validate)]
    mode_txt = f"{args.workers} worker/varyant" if args.workers > 1 else "seri"
    print("=" * 100)
    print(
        f"  ASAMA 2 — DOGRULAMA ({len(syms2)} coin, {mode_txt}): "
        f"BASELINE vs {', '.join(validate)}"
    )
    print("=" * 100)
    r2 = _run_stage(syms2, tags2, workers=args.workers)
    tags2_names = [t[0] for t in tags2]
    a2 = _aggregate(r2, syms2, tags2_names)
    _print_table("ASAMA 2 — TOPLAM", a2, tags2_names)

    # ── Rapor ──
    lines = []
    w = lines.append
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    w(f"# SF IKI ASAMA TARAMA — {ts}")
    w("")
    w("## Asama 1 (tarama)")
    w("")
    w(f"**Coinler:** {', '.join(syms1) if syms1 else '(stage2-only)'}")
    w("")
    w(
        "| Mod | Trade | TP% | PTrail% | Loss% | PE% | PF | MaxDD% | NetPnL | Exp$/trade |"
    )
    w("|" + "---|" * 9)
    for t in tag_names:
        a = a1[t]
        exp = a["pnl"] / a["n"] if a["n"] else 0.0
        w(
            f"| {t} | {a['n']} | {a['tp'] / a['n'] * 100 if a['n'] else 0:.1f}% | "
            f"{a['pt'] / a['n'] * 100 if a['n'] else 0:.1f}% | "
            f"{a['loss'] / a['n'] * 100 if a['n'] else 0:.1f}% | {a['pe']:.1f}% | "
            f"{a['pf']:.2f} | {a['dd']:.1f}% | {a['pnl']:+,.0f} | {exp:+.2f} |"
        )
    if syms1:
        w("")
        w(f"**Kazanan varyant:** `{best}` (NetPnL bazinda)")
    w("")
    w("## Asama 2 (tam evren dogrulama)")
    w("")
    w(f"**Coinler:** {len(syms2)} ({', '.join(syms2[:7])} ...)")
    w("")
    w(
        "| Mod | Trade | TP% | PTrail% | Loss% | PE% | PF | MaxDD% | NetPnL | Exp$/trade |"
    )
    w("|" + "---|" * 9)
    for t in tags2_names:
        a = a2[t]
        exp = a["pnl"] / a["n"] if a["n"] else 0.0
        w(
            f"| {t} | {a['n']} | {a['tp'] / a['n'] * 100 if a['n'] else 0:.1f}% | "
            f"{a['pt'] / a['n'] * 100 if a['n'] else 0:.1f}% | "
            f"{a['loss'] / a['n'] * 100 if a['n'] else 0:.1f}% | {a['pe']:.1f}% | "
            f"{a['pf']:.2f} | {a['dd']:.1f}% | {a['pnl']:+,.0f} | {exp:+.2f} |"
        )
    for vt in validate:
        w("")
        w(f"## Coin bazli: {vt} vs BASELINE")
        w("")
        w("| Symbol | Tr(B) | PE%(B) | PnL(B) | Tr(W) | PE%(W) | PnL(W) | ΔPnL(W-B) |")
        w("|" + "---|" * 7)
        w_win = 0
        for sym in syms2:
            rb = r2.get((sym, "BASELINE"), {})
            rw = r2.get((sym, vt), {})
            if "stats" not in rb or "stats" not in rw:
                w(f"| {sym} | — | — | — | — | — | — | HATA |")
                continue
            sb, sw = rb["stats"], rw["stats"]
            d = sw["total_pnl"] - sb["total_pnl"]
            if d > 0:
                w_win += 1
            w(
                f"| {sym} | {sb['total_trades']} | {sb['positive_exit_pct']:.1f}% | "
                f"{sb['total_pnl']:+,.0f} | {sw['total_trades']} | "
                f"{sw['positive_exit_pct']:.1f}% | {sw['total_pnl']:+,.0f} | {d:+,.0f} |"
            )
        w("")
    ab = a2["BASELINE"]
    w("## Sonuc")
    w("")
    for vt in validate:
        av = a2[vt]
        w_win = sum(
            1
            for sym in syms2
            if "stats" in r2.get((sym, "BASELINE"), {})
            and "stats" in r2.get((sym, vt), {})
            and r2[(sym, vt)]["stats"]["total_pnl"]
            > r2[(sym, "BASELINE")]["stats"]["total_pnl"]
        )
        d = av["pnl"] - ab["pnl"]
        mark = "> BASELINE" if d > 0 else ("< BASELINE" if d < 0 else "= BASELINE")
        w(
            f"- **{vt}**: NetPnL {av['pnl']:+,.0f} (Δ {d:+,.0f}, {mark}), "
            f"{w_win}/{len(syms2)} coinde gecuyor. MaxDD {av['dd']:.1f}%. "
            f"Fallback: FVG={av['fvg']} Ladder={av['lad']} Swing={av['swg']} | "
            f"fallback-only {av['fb_tr']} trade / {av['fb_pnl']:+,.0f} PnL."
        )
    best_v = max(validate, key=lambda t: a2[t]["pnl"])
    if a2[best_v]["pnl"] > ab["pnl"]:
        w("")
        w(f"- **Kazanan: {best_v}** (toplam NetPnL'de baseline'i geciyor).")
    else:
        w("")
        w("- **Baseline**, dogrulanan tum varyantlarin onde; fallback eklemez.")

    rpt_dir = os.path.join(_ROOT, "reports")
    os.makedirs(rpt_dir, exist_ok=True)
    rpt_path = os.path.join(rpt_dir, "analyzer_v5_sf_two_stage.md")
    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    with open(os.path.join(_CACHE_DIR, "_winner.txt"), "w", encoding="utf-8") as f:
        f.write(best)

    print(f"\n  Rapor: {rpt_path}")
    print(f"  Toplam sure: {time.time() - t_all:.0f}s")


if __name__ == "__main__":
    main()
