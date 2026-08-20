"""fallback_sweep_compare.py — retrace_fallback (E) sweep sonucu vs A baseline.

Bas muhendis karar kurali: N, en yuksek NetPnL'ye gore DEGIL, A baseline'a gore
en az yeni outlier (SUIUSDT tarzi negatif aykiri) ureten degerle secilir.

Kullanim:
  python tools/fallback_sweep_compare.py              # checkpoint dosyasindan okur
  python tools/fallback_sweep_compare.py --ck PATH    # ozel checkpoint yolu
"""

import argparse
import os
import pickle

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CK = os.path.join(_HERE, "..", "reports", "_replay_checkpoint.pkl")


def _fmt(v):
    return f"{v:+,.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ck", default=_DEFAULT_CK)
    args = ap.parse_args()

    with open(args.ck, "rb") as f:
        data = pickle.load(f)

    results = data["results"]
    runs = data["runs"]

    base = results[("A", 0.1, 1)]
    base_by_sym = {}
    for t in base.values():
        base_by_sym.setdefault(t["symbol"], []).append(t["final_pnl_usd"])

    def pnl_by_sym(trades):
        out = {}
        for t in trades:
            out.setdefault(t["symbol"], []).append(t["final_pnl_usd"])
        return out

    def summary(trades):
        n = len(trades)
        return {
            "n": n,
            "pnl": sum(t["final_pnl_usd"] for t in trades),
            "tp": sum(1 for t in trades if t["result"] == "PROFIT_TAKE_PROFIT"),
            "ptrail": sum(1 for t in trades if t["result"] == "PROFIT_TRAIL"),
            "loss": sum(1 for t in trades if t["result"] == "LOSS"),
            "hops": sum(t["trailing_count"] for t in trades),
        }

    lines = []
    w = lines.append

    a = summary(base.values())
    w("## A (retrace baseline)")
    w(
        f"- n={a['n']} pnl={_fmt(a['pnl'])} TP={a['tp']} PTrail={a['ptrail']} LOSS={a['loss']} HOP={a['hops']}"
    )
    w("")
    w("## E (retrace_fallback) — N gridi vs A")
    hdr = "| N | n | NetPnL | ΔPnL vs A | TP | PTrail | LOSS | HOP |"
    w(hdr)
    w("|" + "---|" * (hdr.count("|") - 1))
    for tag, mode, k, bars in runs:
        if tag == "A":
            continue
        if (tag, k, bars) not in results:
            w(f"| {tag} K={k} N={bars} | (yok) |")
            continue
        s = summary(results[(tag, k, bars)].values())
        w(
            f"| {bars} | {s['n']} | {_fmt(s['pnl'])} | {_fmt(s['pnl'] - a['pnl'])} "
            f"| {s['tp']} | {s['ptrail']} | {s['loss']} | {s['hops']} |"
        )
    w("")

    w("## Coin-bazli deltalar (E - A) — outlier taramasi")
    w("")
    w("En kotu 10 delta (yeni outlier riski):")
    for tag, mode, k, bars in runs:
        if tag == "A":
            continue
        key = (tag, k, bars)
        if key not in results:
            continue
        ev = pnl_by_sym(results[key].values())
        deltas = {}
        for sym, base_pnls in base_by_sym.items():
            e_pnl = sum(ev.get(sym, [0]))
            deltas[sym] = e_pnl - sum(base_pnls)
        worst = sorted(deltas.items(), key=lambda kv: kv[1])[:10]
        w(f"### N={bars}")
        for sym, d in worst:
            w(f"- {sym}: {_fmt(d)}")
        w("")

    out_path = os.path.join(_HERE, "..", "reports", "fallback_sweep_compare.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Rapor: {out_path}")


if __name__ == "__main__":
    main()
