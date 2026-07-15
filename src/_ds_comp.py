"""DS vs normal trade kıyaslaması"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "sniper", "src"
    ),
)
import config as cfg
from analyzer_v5 import collect_fvg_profile

syms = sorted(cfg.SYMBOLS)
print(
    f"\n  {'Symbol':<12} {'DS_Trade':>9} {'DS_WR%':>7} {'DS_PF':>7} {'DS_PnL':>9} {'Norm_Trade':>10} {'Norm_WR%':>8} {'Norm_PF':>7} {'Norm_PnL':>10}"
)
print(f"  {'-'*85}")
t_ds_n, t_ds_wr, t_ds_pf, t_ds_pnl = 0, 0, 0, 0
t_nm_n, t_nm_wr, t_nm_pf, t_nm_pnl = 0, 0, 0, 0
for sym in syms:
    r = collect_fvg_profile(sym)
    if r and r[0]:
        _, _, _, _, _, ds_stats = r
        c = ds_stats.get("comp", {})
        ds = c.get("ds", {})
        nm = c.get("normal", {})
        print(
            f"  {sym:<12} {ds.get('n',0):>9} {ds.get('wr',0):>6.1f}% {ds.get('pf',0):>6.2f} {ds.get('pnl',0):>+8.0f} {nm.get('n',0):>10} {nm.get('wr',0):>7.1f}% {nm.get('pf',0):>6.2f} {nm.get('pnl',0):>+9.0f}",
            flush=True,
        )
        t_ds_n += ds.get("n", 0)
        t_ds_wr += ds.get("wr", 0) * ds.get("n", 0)
        t_ds_pf += ds.get("pf", 0)
        t_ds_pnl += ds.get("pnl", 0)
        t_nm_n += nm.get("n", 0)
        t_nm_wr += nm.get("wr", 0) * nm.get("n", 0)
        t_nm_pf += nm.get("pf", 0)
        t_nm_pnl += nm.get("pnl", 0)
avg_ds_wr = t_ds_wr / t_ds_n if t_ds_n else 0
avg_nm_wr = t_nm_wr / t_nm_n if t_nm_n else 0
print(f"  {'-'*85}")
print(
    f"  {'TOPLAM':<12} {t_ds_n:>9} {avg_ds_wr:>6.1f}% {t_ds_pf/t_ds_n:>6.2f} {t_ds_pnl:>+8.0f} {t_nm_n:>10} {avg_nm_wr:>7.1f}% {t_nm_pf/t_nm_n:>6.2f} {t_nm_pnl:>+9.0f}"
)
