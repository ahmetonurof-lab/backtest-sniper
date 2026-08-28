"""
parity_report_crypto.py — Canli vs backtest (Binance 15d) side-by-side raporu.

KULLANIM:
    python tools/parity_report_crypto.py

Bu script:
  1. Canli events_2026-08-2*.jsonl dosyalarini SSH ile production'dan
     download eder (events) ve parse eder — symbol bazli:
        trades, wins (TP+PTrail), losses, win%, gross_wins, gross_losses,
        net_pnl_usdt, avg_pnl_usdt, pf.
  2. reports/analyzer_v5_summary.md dosyasindan son koşunun per-symbol
    tablosunu parse eder — R cinsinden metrikleri USDT-bazli metric
    formatina cevirmez (analyzer R/ATR kullaniyor, ama per-symbol PnL,
    trade count ve win% direkt kullanilabilir).
  3. Tek TABLO'da yanyana basar: BTC'deki live-trade'lerin backtestte
    olup olmadigina bakmaksizin, her iki evrende de olan coinleri
    gosterir; birinde olup digerinde olmayan coinler ayri sutunlarda.

URETIM: Sonuc stdout'a basilir + reports/parity_crypto_report.md'ye
  yazilir (ileride commitlenebilir).

Bu script analyzer_v5.py'ye DOKUNMAZ. Sadece onun ciktisini okur
ve canli veriyle birebir ayni formatta raporlar.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
_PROJ_ROOT = Path(__file__).resolve().parent.parent
REPORTS = _PROJ_ROOT / "reports"
SUMMARY_MD = REPORTS / "analyzer_v5_summary.md"
PARITY_MD = REPORTS / "parity_crypto_report.md"
LOG_PATH = _PROJ_ROOT / "logs" / "binance_15d_download.log"

# Canli: production server'daki events dosyalari
LIVE_HOST = "ContaboBot"
LIVE_EVENTS_GLOB = "/root/sniper/output/events_2026-08-2*.jsonl"


# ── Canli parse ───────────────────────────────────────────────────────
def fetch_live_events() -> list[dict]:
    """SSH ile production'dan events dosyalarini oku."""
    # Bash escaping — heredoc yerine grep+cat ile tek parca indir
    cmd = (
        f"ssh -o BatchMode=yes {LIVE_HOST} "
        f"'cat /root/sniper/output/events_2026-08-2*.jsonl'"
    )
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"ssh failed: {out.stderr}")
    rows = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("event_type") == "exit":
            rows.append(ev)
    return rows


def summarize_live(events: list[dict]) -> dict[str, dict]:
    """Per-symbol canli istatistik (USDT-bazli)."""
    by_sym: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        by_sym[ev["symbol"]].append(ev)
    out: dict[str, dict] = {}
    for sym, lst in by_sym.items():
        wins = [e for e in lst if e.get("result") in ("TP", "PROFIT_TRAIL")]
        losses = [e for e in lst if e.get("result") not in ("TP", "PROFIT_TRAIL")]
        gross_w = sum(e.get("pnl", 0.0) for e in wins)
        gross_l = abs(sum(e.get("pnl", 0.0) for e in losses))
        net = sum(e.get("pnl", 0.0) for e in lst)
        out[sym] = {
            "trades": len(lst),
            "wins": len(wins),
            "losses": len(losses),
            "win_pct": round(100 * len(wins) / len(lst), 1) if lst else 0.0,
            "net_pnl_usdt": round(net, 2),
            "avg_pnl_usdt": round(net / len(lst), 2) if lst else 0.0,
            "gross_wins": round(gross_w, 2),
            "gross_losses": round(gross_l, 2),
            "pf": round(gross_w / gross_l, 2) if gross_l > 0 else float("inf"),
        }
    return out


# ── Trade dump parse (analyzer_v5'in yazdigi trades_dump.json) ──────
def parse_trades_dump(path: Path) -> tuple[float, float, int, int] | None:
    """Trade dump'tan gercek (gross_wins, gross_losses, trades, wins) hesapla.

    PF = gross_wins / gross_losses (gross_loss=0 ise math.inf).
    Returns: (gross_wins_R, gross_losses_R, n_trades, n_wins)
    """
    if not path.exists():
        return None
    import json as _json
    try:
        trades = _json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    gross_w = 0.0
    gross_l = 0.0
    wins = 0
    for t in trades:
        pnl = t.get("pnl", 0.0) or 0.0
        result = t.get("result", "")
        if pnl > 0:
            gross_w += pnl
            if result in ("TP", "PROFIT_TRAIL"):
                wins += 1
        elif pnl < 0:
            gross_l += abs(pnl)
    return gross_w, gross_l, len(trades), wins


# ── Backtest parse (analyzer_v5_summary.md'den) ───────────────────────
def parse_bt_summary(path: Path) -> dict[str, dict] | None:
    """En son [BASELINE_RETRACE_LIVE_PARITY] tablosunu parse et.

    Format ornegi (19-kolonlu tablo):
        | SYMBOL | Trades | TP% | PTrail% | Loss% | PF | Sharpe | MaxDD% |
        | Fee | NetPnL | Exp$ | AvgHold | PnL/Fee | FVGCr | FVGEnt |
        | MinRisk | Score | IFVG# | IFVG$ |

    Return: { SYM: {trades, win_pct, loss_pct, tp_pct, ptrail_pct,
                     pf, net_pnl_r (R-bazli)} }
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Son BASELINE_RETRACE_LIVE_PARITY blogunu bul (dosyanin en sonunda).
    sections = text.split("\n---\n")
    last = None
    for s in sections:
        if "[BASELINE_RETRACE_LIVE_PARITY]" in s and "Symbol" in s:
            last = s
    if not last:
        return None

    out: dict[str, dict] = {}
    for line in last.splitlines():
        cols = [c.strip() for c in line.split("|")]
        # Bos / ayrac satirlarini atla
        if len(cols) < 12 or not cols[1]:
            continue
        sym = cols[1]
        if not re.match(r"^[A-Z0-9]+USDT$", sym):
            continue
        try:
            trades = int(cols[2].replace(",", ""))
            tp = float(cols[3].rstrip("%"))
            ptr = float(cols[4].rstrip("%"))
            loss = float(cols[5].rstrip("%"))
            pf_s = cols[6]
            pf = float(pf_s) if pf_s not in ("inf", "") else float("inf")
            # index 10 = NetPnL (R)
            net_pnl_r = float(cols[10].replace(",", ""))
        except (ValueError, IndexError):
            continue
        win_pct = round(tp + ptr, 1)
        out[sym] = {
            "trades": trades,
            "win_pct": win_pct,
            "loss_pct": loss,
            "tp_pct": tp,
            "ptrail_pct": ptr,
            "pf": pf,
            "net_pnl_r": net_pnl_r,
        }
    return out


# ── Combined report ───────────────────────────────────────────────────
def build_combined(
    live: dict[str, dict],
    bt: dict[str, dict],
    bt_pf: float | None = None,
    bt_gross: tuple[float, float] | None = None,
) -> str:
    """Yanyana karsilastirma tablosu uret (per-symbol ustte, genel altta)."""
    all_syms = sorted(set(live) | set(bt))
    lines = []
    lines.append("# PARITY REPORT -- Canli (8.5g) vs Backtest (Binance 15d)")
    lines.append("")

    # ── 1. PER-SYMBOL DETAY (USTTE) ──
    lines.append("## 1. Per-Symbol Detay")
    lines.append("")
    lines.append(
        "| Symbol | Live N | Live W | Live L | Live Win% | "
        "Live NetPnL (USDT) | Live Avg | "
        "BT N | BT Win% | BT TP% | BT PTrail% | BT Loss% | "
        "BT NetPnL (R) | BT AvgR | Eslesme |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for sym in all_syms:
        l = live.get(sym)
        b = bt.get(sym)
        if l and b:
            match = "MATCH"
        elif l and not b:
            match = "live-only"
        else:
            match = "bt-only"
        # Live sutunlari
        l_n = l["trades"] if l else "—"
        l_w = l["wins"] if l else "—"
        l_l = l["losses"] if l else "—"
        l_wp = f"{l['win_pct']:.1f}" if l else "—"
        l_np = f"{l['net_pnl_usdt']:+.2f}" if l else "—"
        l_avg = f"{l['avg_pnl_usdt']:+.2f}" if l else "—"
        # BT sutunlari
        b_n = b["trades"] if b else "—"
        b_wp = f"{b['win_pct']:.1f}" if b else "—"
        b_tp = f"{b['tp_pct']:.1f}" if b else "—"
        b_ptp = f"{b['ptrail_pct']:.1f}" if b else "—"
        b_lp = f"{b['loss_pct']:.1f}" if b else "—"
        b_np = f"{b['net_pnl_r']:+.0f}" if b else "—"
        b_avg = (
            f"{b['net_pnl_r']/b['trades']:+.2f}"
            if b and b['trades'] > 0 else "—"
        )
        lines.append(
            f"| {sym} | {l_n} | {l_w} | {l_l} | {l_wp} | "
            f"{l_np} | {l_avg} | "
            f"{b_n} | {b_wp} | {b_tp} | {b_ptp} | {b_lp} | "
            f"{b_np} | {b_avg} | {match} |"
        )
    lines.append("")

    # ── 2. GENEL OZET (ALTTA) ──
    lines.append("## 2. Genel Ozet (Toplam)")
    lines.append("")

    # Ortak istatistik tablosu
    lines.append("### 2.1 Ortak Istatistik")
    lines.append("")
    lines.append(
        "| Kaynak | Trade | Wins | Losses | Win% | "
        "Net PnL | Ort/trade | Gross Win | Gross Loss | PF |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    if live:
        l_t = sum(s["trades"] for s in live.values())
        l_w = sum(s["wins"] for s in live.values())
        l_l = sum(s["losses"] for s in live.values())
        l_n = sum(s["net_pnl_usdt"] for s in live.values())
        l_a = l_n / l_t if l_t else 0
        l_gw = sum(s["gross_wins"] for s in live.values())
        l_gl = sum(s["gross_losses"] for s in live.values())
        l_pf = l_gw / l_gl if l_gl > 0 else float("inf")
        lines.append(
            f"| **CANLI** (USDT) | {l_t} | {l_w} | {l_l} | "
            f"{100*l_w/l_t:.1f} | {l_n:+.2f} | {l_a:+.2f} | "
            f"{l_gw:+.2f} | {l_gl:+.2f} | {l_pf:.2f} |"
        )
    if bt:
        b_t = sum(s["trades"] for s in bt.values())
        b_w = sum(s["trades"] * s["win_pct"] / 100 for s in bt.values())
        b_n = sum(s["net_pnl_r"] for s in bt.values())
        b_a = b_n / b_t if b_t else 0
        b_gw = bt_gross[0] if bt_gross else 0
        b_gl = bt_gross[1] if bt_gross else 0
        if bt_pf is None:
            b_pf_str = "n/a"
        elif bt_pf == float("inf"):
            b_pf_str = "inf (0 loss)"
        else:
            b_pf_str = f"{bt_pf:.2f}"
        lines.append(
            f"| **BACKTEST** (R) | {b_t} | {int(b_w)} | {b_t-int(b_w)} | "
            f"{b_w/b_t*100:.1f} | {b_n:+.0f} | {b_a:+.2f} | "
            f"{b_gw:+.0f} | {b_gl:+.0f} | {b_pf_str} |"
        )
    lines.append("")

    # Sembol kapsama
    lines.append("### 2.2 Sembol Kapsama")
    lines.append("")
    n_live = len(live)
    n_bt = len(bt)
    n_match = len([s for s in (set(live) & set(bt))])
    n_live_only = len(set(live) - set(bt))
    n_bt_only = len(set(bt) - set(live))
    lines.append(
        f"- CANLI sembol sayisi: **{n_live}**\n"
        f"- BACKTEST sembol sayisi: **{n_bt}**\n"
        f"- Eslesen (MATCH): **{n_match}**\n"
        f"- Canli-only: **{n_live_only}** (canli trade acmis, BT'de yok)\n"
        f"- BT-only: **{n_bt_only}** (BT'de var, canli hic trade acmamis)"
    )
    lines.append("")

    # Eslesme / TERS yon analizi
    lines.append("### 2.3 Eslesme Analizi")
    lines.append("")
    lines.append("**TERS yon (canli negatif, BT pozitif):**")
    lines.append("")
    lines.append("| Symbol | Live NetPnL | BT NetPnL | Fark |")
    lines.append("|---|---|---|---|")
    for sym in sorted(set(live) & set(bt)):
        l = live[sym]
        b = bt[sym]
        if l["net_pnl_usdt"] < 0 and b["net_pnl_r"] > 0:
            lines.append(
                f"| {sym} | {l['net_pnl_usdt']:+.2f} | "
                f"{b['net_pnl_r']:+.0f}R | "
                f"{l['net_pnl_usdt'] - b['net_pnl_r']:+.2f} |"
            )
    lines.append("")
    lines.append("**TERS yon (canli pozitif, BT negatif):**")
    lines.append("")
    lines.append("| Symbol | Live NetPnL | BT NetPnL | Fark |")
    lines.append("|---|---|---|---|")
    for sym in sorted(set(live) & set(bt)):
        l = live[sym]
        b = bt[sym]
        if l["net_pnl_usdt"] > 0 and b["net_pnl_r"] < 0:
            lines.append(
                f"| {sym} | {l['net_pnl_usdt']:+.2f} | "
                f"{b['net_pnl_r']:+.0f}R | "
                f"{l['net_pnl_usdt'] - b['net_pnl_r']:+.2f} |"
            )
    lines.append("")
    lines.append("**AYNI yon (ikisi de pozitif):**")
    lines.append("")
    lines.append("| Symbol | Live NetPnL | BT NetPnL | Fark |")
    lines.append("|---|---|---|---|")
    for sym in sorted(set(live) & set(bt)):
        l = live[sym]
        b = bt[sym]
        if l["net_pnl_usdt"] > 0 and b["net_pnl_r"] > 0:
            lines.append(
                f"| {sym} | {l['net_pnl_usdt']:+.2f} | "
                f"{b['net_pnl_r']:+.0f}R | "
                f"{l['net_pnl_usdt'] - b['net_pnl_r']:+.2f} |"
            )
    lines.append("")
    lines.append("**AYNI yon (ikisi de negatif):**")
    lines.append("")
    lines.append("| Symbol | Live NetPnL | BT NetPnL | Fark |")
    lines.append("|---|---|---|---|")
    for sym in sorted(set(live) & set(bt)):
        l = live[sym]
        b = bt[sym]
        if l["net_pnl_usdt"] < 0 and b["net_pnl_r"] < 0:
            lines.append(
                f"| {sym} | {l['net_pnl_usdt']:+.2f} | "
                f"{b['net_pnl_r']:+.0f}R | "
                f"{l['net_pnl_usdt'] - b['net_pnl_r']:+.2f} |"
            )
    lines.append("")
    lines.append("")
    lines.append("Notlar:")
    lines.append(
        "- **CANLI**: production bot, events_2026-08-2*.jsonl, USDT. "
        "Sadece kapanan (exit) trade'ler. Trailing_count dahil degil, "
        "qty birebir Binance tarafindan raporlanan (testnet) miktardir."
    )
    lines.append(
        "- **BACKTEST**: analyzer_v5.py + Binance 1m CSV (15 gun). "
        "Metrikler **R cinsinden** (1R = ATR risk, forex mantigi). "
        "USDT karsiligi icin trade-level qty + entry/exit fiyati gerekir; "
        "bu raporda sadece R tablosu kullanildi. Tam USDT karsiligi "
        "icin analyzer_v5.py'ye trade dump (qty + prices) eklemek gerekir."
    )
    lines.append("")
    return "\n".join(lines)


def main():
    print("=== PARITY REPORT — CANLI vs BACKTEST (Binance 15d) ===")
    print()
    print("[1/3] Canli events cekiliyor (SSH)...")
    events = fetch_live_events()
    print(f"      {len(events)} exit event")
    live = summarize_live(events)
    print(f"      {len(live)} sembol")
    print()
    print("[2/3] Backtest summary parse ediliyor...")
    bt = parse_bt_summary(SUMMARY_MD)
    if bt is None:
        print("      HATA: summary.md bulunamadi veya parse edilemedi")
        print(f"      Beklenen: {SUMMARY_MD}")
        return 1
    print(f"      {len(bt)} sembol (analyzer_v5)")
    # Trade dump'tan gercek gross_wins/gross_losses (PF hesap icin)
    bt_dump = parse_trades_dump(REPORTS / "trades_dump.json")
    if bt_dump:
        b_gw_r, b_gl_r, b_n_dump, b_w_dump = bt_dump
        b_pf_real = (b_gw_r / b_gl_r) if b_gl_r > 0 else float("inf")
        print(
            f"      Trade dump: {b_n_dump} trade, gross_win={b_gw_r:.0f}R, "
            f"gross_loss={b_gl_r:.0f}R, PF={b_pf_real:.2f}"
        )
    else:
        b_gw_r = b_gl_r = b_pf_real = None
        print("      Trade dump YOK — PF hesaplanamadi")
    print()
    print("[3/3] Rapor uretiliyor...")
    report = build_combined(
        live, bt, bt_pf=b_pf_real,
        bt_gross=(b_gw_r, b_gl_r) if bt_dump else None,
    )
    print()
    print(report)
    PARITY_MD.parent.mkdir(parents=True, exist_ok=True)
    PARITY_MD.write_text(report, encoding="utf-8")
    print()
    print(f"Rapor yazildi: {PARITY_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
