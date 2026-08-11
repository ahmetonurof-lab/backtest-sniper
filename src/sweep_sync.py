"""
sweep_sync.py — A6-01: canlı sweep-tüketim mantığının backtest izolesi.

Kaynak: sniper/src/trading/signal_engine.py:78-93 (progress_rsm Blok 8).
Canlıdaki iki dal da birebir korunur:
  1. IDLE + sweep_confirmed → on_sweep(bar_index=current.index) → sweep_confirmed=False
  2. SWEEP_DETECTED → on_sweep_confirmed(...) → IDLE'ye döndüyse sweep_confirmed=False

Amaç: aynı sweep'in her 15m bar'da yeniden onaylanıp aynı "ölü" sinyali
üretmesini önlemek (SEIUSDT direction-fail döngüsü). analyzer_v5.py'den
izole edilir — backtest motoruna başka hiçbir değişiklik yapılmaz.
"""


def process_sweep(rsm, ss, bars_15m, current, atr_val=0.0, symbol=""):
    """Canlı progress_rsm Blok 8 sweep-tüketim mantığı (signal_engine.py:78-93)."""
    if rsm.state_name == "IDLE" and ss.sweep_confirmed:
        rsm.on_sweep(
            direction=ss.sweep_direction or "bullish",
            level=ss.sweep_level or 0.0,
            bar_index=current.index,
        )
        # Sweep tüketildi (SWEEP_DETECTED'e geçildi veya dedup reddetti):
        # bayrağı temizle. Aksi halde aynı sweep her 15m bar'da yeniden
        # onaylanıp aynı "ölü" sinyali üretirdi (SEIUSDT direction-fail
        # döngüsü — giriş reddi sonrası pozisyon açılmadan tekrar denenir).
        ss.sweep_confirmed = False

    if rsm.state_name == "SWEEP_DETECTED":
        rsm.on_sweep_confirmed(bars_15m, current, atr_val, symbol)
        if rsm.state_name == "IDLE":
            ss.sweep_confirmed = False
