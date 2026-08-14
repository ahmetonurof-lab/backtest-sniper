Sniper Backtest Karar Kaydı ve Yerel Ajan Direktifi
Tarih: 2026-08-14 22:42 Europe/Istanbul
Kapsam: ahmetonurof-lab/backtest-sniper
Amaç: Canlıya trailing veya başka iyileştirme deploy etmeden önce güvenilir backtest baseline oluşturmak.

Karar
Seçenek A uygulanmayacak. b16d751 öncesindeki inline sweep davranışını geri getirmek yasak.

Eski davranışta sweep_confirmed temizlenmiyor ve bar_index=None kullanıldığı için aynı sweep her 15m barda tekrar tetiklenebiliyordu. Bu bilinen state bug'ı aynı sinyali tekrar tekrar işleme sokuyor ve yaklaşık 22650 trade / +4M PnL sonucu üretiyordu. Bu rakam strateji performansı değil, bug kaynaklı şişmiş sonuçtur.

Seçenek B de doğrudan uygulanmayacak. Sadece sweep_sync.py içine BIAS_LOCKED eklemek yeterli değil; backtest'in canlıyla doğru parity için sweep tetikleme, BIAS latch, FVG-only arama ve restart/state davranışları birlikte ele alınmalı.

Uygulanacak doğru yol: C
Backtest şu süreci uygulamalı:

text
CBDR range
  -> ilk geçerli CBDR sweep
  -> günlük BIAS kilitlenir
  -> aynı CBDR döngüsünde yeni sweep beklenmez
  -> yalnızca BIAS yönlü FVG aranır
  -> FVG wick rejection + filtreler
  -> entry
Aynı zamanda bilinen sweep_confirmed tekrar tetikleme bug'ı kapalı kalmalı.

Yerel ajanın uygulama direktifi
1. Sweep tetikleme fix'ini koru
src/sweep_sync.py ve src/analyzer_v5.py içinde:

IDLE + ss.sweep_confirmed dalında rsm.on_sweep(..., bar_index=current.index, symbol=symbol) kullanılmalı.

Sweep tetiklendikten sonra ss.sweep_confirmed = False kalmalı.

SWEEP_DETECTED dalında on_sweep_confirmed(...) çağrılmalı.

RSM IDLE'ye dönerse ss.sweep_confirmed = False kalmalı.

bar_index=None ve sweep flag'ini temizlemeyen eski inline kod geri getirilmeyecek.

2. BIAS_LOCKED parity dalını ekle
src/sweep_sync.py yalnızca sweep tetiklemeyi değil, canlı signal_engine.py akışındaki BIAS_LOCKED davranışını da kapsamalı:

python
if rsm.state_name == "BIAS_LOCKED":
    db = ss.daily_bias
    locked_dir = rsm.direction
    bias_conflict = (
        (locked_dir == "bullish" and db == DailyBias.BEARISH)
        or (locked_dir == "bearish" and db == DailyBias.BULLISH)
        or db == DailyBias.NEUTRAL
    )
    if bias_conflict:
        rsm.reset()
    else:
        rsm.on_bias_fvg(bars_15m, current, atr_val, symbol)
Kod birebir kopyalanacaksa mevcut canlı signal_engine.py ile AST veya davranışsal fixture karşılaştırması yapılmalı. BIAS_LOCKED dalında yeni sweep çağrısı olmayacak.

3. State ve persistence parity'sini açıkça belirle
Backtest her koşudan önce temiz state ile başlamalı. Önceki koşunun trade_state.json veya sweep persistence kayıtları yeni koşuyu kirletmemeli.

Ajan şunlardan birini uygulamalı:

Her backtest run için geçici ve benzersiz SNIPER_OUTPUT_DIR kullanmak.

Ya da run başında yalnızca backtest'e ait state dosyasını temizlemek ve bunu loglamak.

Aynı veriyle ikinci koşuda trade sayısının state kalıntısı yüzünden değişmesi kabul edilmeyecek.

4. Entry ve trailing iyileştirmelerini baseline'dan ayır
Önce güvenilir strateji baseline'ı oluşturulacak. Baseline'da:

Canlıyla uyumlu CBDR/Bias/Sweep/FVG state akışı.

Mevcut retrace-only trailing davranışı.

Bilinen A6-01 sweep reset fix'i.

Canlı BIAS_LOCKED / sweep'siz BIAS yönlü FVG araması.

Sonra trailing iyileştirmeleri ayrı feature flag veya ayrı commit ile test edilecek:

R-kâr kapısı: +0.8R, +1.0R.

Profit protection / breakeven buffer.

Swing/ATR chandelier trail.

FVG retrace trail.

Bu iyileştirmeler baseline commit'ine karıştırılmayacak; her koşu aynı entry seti üzerinde ve ayrı mod etiketiyle raporlanacak.

Test planı
Zorunlu unit/integration testleri
Aynı sweep ikinci kez tetiklenmez.

İki farklı symbol aynı bar_index ile birbirini engellemez.

İlk sweep sonrası BIAS_LOCKED dalı yeni sweep beklemeden aynı yönlü FVG arar.

BIAS tersine dönerse veya yeni CBDR döngüsü başlarsa RSM resetlenir.

Son 10 ters FVG, daha eski uyumlu FVG'yi gizlemez.

Touched/invalidated FVG tekrar trigger olmaz.

Aynı temiz state ve aynı veriyle iki baseline koşusu aynı trade sayısı ve PnL üretir.

BIAS_LOCKED flow, canlı SignalEngine.progress_rsm() fixture'ı ile backtest sonucu olarak eşleşir.

Karşılaştırma koşulları
En az şu koşular ayrı raporlanmalı:

BASELINE_RETRACE_LIVE_PARITY

PROFIT_GATE_0_8R

PROFIT_GATE_1_0R

ATR_TRAIL_0_5

ATR_TRAIL_0_75

HYBRID_FVG_PLUS_PROFIT_GATE

Her raporda trade sayısı, win rate, profit factor, NetPnL, MaxDD, expectancy, average hold ve exit reason dağılımı bulunmalı.

Reddedilen sonuçlar
Aşağıdaki sonuçlar başarı kanıtı olarak kabul edilmeyecek:

22650 trade / +4M PnL üreten eski sweep flag bug'lı koşu.

State dosyası temizlenmeden yapılan ikinci koşu.

BIAS_LOCKED dalı olmadan canlı parity iddiası.

Sadece toplam PnL gösterip MaxDD, fee ve trade count göstermeyen rapor.

Trailing değişikliği ile entry/state değişikliğini aynı committe karıştıran koşu.

Kabul kriterleri
Eski sweep tekrar tetikleme döngüsü yok.

Canlı modeldeki ilk sweep sonrası günlük BIAS kilidi backtestte mevcut.

BIAS kilitliyken yeni sweep beklenmiyor.

Yalnızca BIAS yönlü FVG aranıyor.

Baseline koşusu temiz state ile tekrarlanabilir.

Yeni trailing stratejisi baseline'dan ayrı ve geri alınabilir.

Her değişiklik için test sonucu ve commit hash kaydediliyor.

Canlıya deploy kararı yalnızca baseline ve iyileştirme koşulları yan yana değerlendirildikten sonra verilecek.

Son karar cümlesi
Eski bug'lı backtesti geri getirme. Önce canlıyla gerçek parity sağlayan, A6-01 sweep tetikleme fix'ini koruyan ve BIAS_LOCKED ile doğrudan BIAS yönlü FVG arayan temiz baseline'ı kur. Trailing/profit-protection iyileştirmelerini bunun üzerine ayrı deney olarak test et.
[dosya içeriği sonu]
