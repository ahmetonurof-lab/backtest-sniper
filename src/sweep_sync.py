"""
sweep_sync.py — A6-01 + Plan C: canlı sweep-tüketim + BIAS_LOCKED backtest izolesi.

Kaynak: sniper/src/trading/signal_engine.py:78-114 (progress_rsm Blok 8).
Canlıdaki üç dal da birebir korunur:
  1. IDLE + sweep_confirmed → on_sweep(bar_index=current.index, symbol) → sweep_confirmed=False
  2. SWEEP_DETECTED → on_sweep_confirmed(...) → IDLE'ye döndüyse sweep_confirmed=False
  3. BIAS_LOCKED → bias_conflict ise reset, değilse on_bias_fvg(...) (yeni sweep GEREKMEZ)

Amaç: aynı sweep'in her 15m bar'da yeniden onaylanıp aynı "ölü" sinyali
üretmesini önlemek (SEIUSDT direction-fail döngüsü) + kilitli bias yönünde
sweep'siz BIAS yönlü FVG re-entry'i sağlamak (LUNA direktifi Plan C madde 2).
analyzer_v5.py'den izole edilir — canlı akışa başka hiçbir değişiklik yapılmaz.
"""

from session import DailyBias


def process_sweep(rsm, ss, bars_15m, current, atr_val=0.0, symbol=""):
    """Canlı progress_rsm Blok 8 mantığı (signal_engine.py:78-114)."""
    if rsm.state_name == "IDLE" and ss.sweep_confirmed:
        rsm.on_sweep(
            direction=ss.sweep_direction or "bullish",
            level=ss.sweep_level or 0.0,
            bar_index=current.index,
            symbol=symbol,
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

    if rsm.state_name == "BIAS_LOCKED":
        db = ss.daily_bias
        locked_dir = rsm.direction
        bias_conflict = (
            (locked_dir == "bullish" and db == DailyBias.BEARISH)
            or (locked_dir == "bearish" and db == DailyBias.BULLISH)
            or db == DailyBias.NEUTRAL
        )
        if bias_conflict:
            # Bias tersine dondu veya nötr (yeni CBDR gunu) -> kiliti kaldir,
            # yeni sweep bekle. Kilit yonune ters duşen FVG'lerle
            # surdurulebilir kayip zincirini onler.
            rsm.reset()
        else:
            # Bias hala kilit yonunu destekliyor -> taze FVG wick rejection'i
            # ile yeniden TRIGGER_READY olmaya calis (yeni sweep gerekmez).
            rsm.on_bias_fvg(bars_15m, current, atr_val, symbol)

    ss.fvg_ready = rsm.state_name == "TRIGGER_READY"
