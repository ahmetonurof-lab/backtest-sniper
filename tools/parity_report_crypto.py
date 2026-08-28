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
def build_combined(live: dict[str, dict], bt: dict[str, dict]) -> str:
    """Yanyana karsilastirma tablosu uret."""
    all_syms = sorted(set(live) | set(bt))
    lines = []
    lines.append("# PARITY REPORT -- Canli (8.5g) vs Backtest (Binance 15d)")
    lines.append("")
    lines.append("## Ortak istatistik")
    lines.append("")
    lines.append("| Kaynak | Trade | Win% | Net PnL | Ort/trade | PF |")
    lines.append("|---|---|---|---|---|---|")

    if live:
        l_t = sum(s["trades"] for s in live.values())
        l_w = sum(s["wins"] for s in live.values())
        l_n = sum(s["net_pnl_usdt"] for s in live.values())
        l_a = l_n / l_t if l_t else 0
        l_pf_w = sum(s["gross_wins"] for s in live.values())
        l_pf_l = sum(s["gross_losses"] for s in live.values())
        l_pf = l_pf_w / l_pf_l if l_pf_l else float("inf")
        lines.append(
            f"| **CANLI** (USDT) | {l_t} | {100*l_w/l_t:.1f} | "
            f"{l_n:+.2f} | {l_a:+.2f} | {l_pf:.2f} |"
        )
    if bt:
        b_t = sum(s["trades"] for s in bt.values())
        b_w = sum(s["trades"] * s["win_pct"] / 100 for s in bt.values())
        b_n = sum(s["net_pnl_r"] for s in bt.values())
        b_a = b_n / b_t if b_t else 0
        b_pf_vals = [s["pf"] for s in bt.values() if s["pf"] not in (float("inf"), 0)]
        b_pf_avg = sum(b_pf_vals) / len(b_pf_vals) if b_pf_vals else 0
        lines.append(
            f"| **BACKTEST** (R) | {b_t} | {b_w/b_t*100:.1f} | "
            f"{b_n:+.2f} | {b_a:+.2f} | {b_pf_avg:.2f} |"
        )
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

    # Per-symbol
    lines.append("## Per-symbol")
    lines.append("")
    lines.append(
        "| Symbol | Live N | Live Win% | Live NetPnL (USDT) | "
        "BT N | BT Win% | BT NetPnL (R) | Eslesme |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for sym in all_syms:
        l = live.get(sym)
        b = bt.get(sym)
        if l and b:
            match = "MATCH"
        elif l and not b:
            match = "live-only"
        else:
            match = "bt-only"
        l_n = l["trades"] if l else "—"
        l_w = f"{l['win_pct']}" if l else "—"
        l_p = f"{l['net_pnl_usdt']:+.2f}" if l else "—"
        b_n = b["trades"] if b else "—"
        b_w = f"{b['win_pct']}" if b else "—"
        b_p = f"{b['net_pnl_r']:+.0f}" if b else "—"
        lines.append(
            f"| {sym} | {l_n} | {l_w} | {l_p} | {b_n} | {b_w} | {b_p} | {match} |"
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
    print()
    print("[3/3] Rapor uretiliyor...")
    report = build_combined(live, bt)
    print()
    print(report)
    PARITY_MD.parent.mkdir(parents=True, exist_ok=True)
    PARITY_MD.write_text(report, encoding="utf-8")
    print()
    print(f"Rapor yazildi: {PARITY_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
