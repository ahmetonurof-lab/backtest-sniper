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
from retrace_state import RetraceState


def process_sweep(rsm, ss, bars_15m, current, atr_val=0.0, symbol=""):
    """Canlı progress_rsm Blok 8 mantığı (signal_engine.py:78-114)."""
    # IFVG (ikincil yol): her bar'da kaynak etiketini 'NORMAL' sifirla;
    # asagidaki IFVG blogu tetiklenirse 'IFVG' ile ezer. Flag kapaliyken
    # check_ifvg_retest None doner -> islevsel etki yok.
    rsm._last_trigger_source = "NORMAL"

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

    # ── IFVG ikincil yol: normal yol TRIGGER_READY yapmadiysa dene ──
    # Ana sweep+FVG yolu onceeliklidir; ayni bar'da normal kazandiysa
    # (state zaten TRIGGER_READY) buraya girilmez. IFVG tetiklenirse
    # trigger_fvg ayni tiptedir (HTFFVG) -> SL/TP ayni kaliyla calisir.
    if rsm.state != RetraceState.TRIGGER_READY:
        ifvg_hit = rsm.check_ifvg_retest(current)
        if ifvg_hit is not None:
            # IFVG entry state makinesini kirletmesin: trigger aninda yon
            # IFVG yonune cekilir (entry side hesabi icin gerekli) AMA giris
            # oncesi sweep/bias yonu saklanir. Entry tarafi (analyzer_v5)
            # kapanista bu yone geri donup normal entry gibi BIAS_LOCKED'a
            # gecer — ters yon kilidi bias_conflict -> reset ile gunun sweep
            # penceresini oldurmesin (17K normal trade bastirmasi).
            rsm._pre_ifvg_direction = rsm.direction
            rsm.state = RetraceState.TRIGGER_READY
            rsm.direction = ifvg_hit.direction
            rsm.trigger_fvg = ifvg_hit
            rsm._last_trigger_source = "IFVG"

    ss.fvg_ready = rsm.state_name == "TRIGGER_READY"
