# GÖREV 2 — 119K NORMAL Suppression Kök Neden Teşhisi

**Tarih:** 2026-08-18 · **Kapsam:** IFVG paper-deploy direktifi Görev 2 (sadece teşhis — KOD DEĞİŞİKLİĞİ YOK)
**Araç:** `tools/diag_ifvg_normal_suppression.py` (monkeypatch ile per-bar RSM state izi, üretim koduna dokunmaz)

---

## 1. Bulgu özeti

Guard-fix sonrası 28-coin koşusunda NORMAL trade kaybının (~5,797 trade / ~-119,307 PnL)
kök nedeni **teşhis edildi**: IFVG ikincil yolu, RSM state makinesini **IDLE yerine
BIAS_LOCKED'de tutarak** yeni günün/pencerenin NORMAL sweep→FVG zincirini geciktiriyor.
Bu bir "state machine kilitlenmesi" değil, **bilinçli IFVG tasarımının yan etkisi** — ve
3 örnek coinde ölçülen net etki **açıkça pozitif** (aşağıda).

### 2. Mekanizma (bar-bazlı kanıt)

Örnek coinlerde IFVG KAPALI (baseline) vs AÇIK per-bar RSM izi karşılaştırması:

| Coin | STATE_DIVERGE (bar) | BLOCKED BIAS_LOCKED (bar) | SUPPRESSED (NORMAL trigger kaybı) | USURPED |
|---|---|---|---|---|
| ARBUSDT | 3,803 | 948 | 197 | 1 |
| SEIUSDT | 3,062 | 454 | 204 | 1 |
| XRPUSDT | 2,015 | 451 | 106 | 1 |

**Kök neden zinciri:**

1. Bir NORMAL FVG adayı **body-broken** olursa (`on_bias_fvg` / `on_sweep_confirmed`
   içinde `body_broke_down=True`), IFVG_ENABLED=True iken FVG **`_register_inverted()` ile
   kaydedilir** ve `continue` edilir. RSM **BIAS_LOCKED'de kalır** (baseline'da da kalır —
   bu kısım aynı).
2. Fark burada: baseline'da body-broken FVG **atılır** ve RSM bir sonraki fırsatta
   (yeni sweep / taze FVG) NORMAL tetiklemeye devam eder. IFVG'de ise flipped aday
   retest beklerken RSM **yüzlerce bar boyunca BIAS_LOCKED'de meşgul tutulur**.
   - Örnek (XRPUSDT bar 1416-1426+): `IDLE->IDLE` (off) vs `BIAS_LOCKED->BIAS_LOCKED`
     **6 bekleyen inverted adayla** (on) — RSM, retest'i asla gelmeyen adaylarla dolu.
   - Örnek (SEIUSDT bar 1176-1178): `BIAS_LOCKED (bullish)` (off) vs `IDLE` (on) —
     IFVG yönü ters olduğu için bias_conflict reset'i, baseline'ın kilitli kalıp
     NORMAL retest beklemesinin yerini alıyor.
3. RSM IDLE değilken `process_sweep`'in **IDLE+on_sweep dalı çalışamaz** → yeni
   günün/pencerenin sweep'i NORMAL FVG aramasına başlatılamaz → ~200/coin NORMAL
   trigger doğrudan kaybolur (`SUPPRESSED`).

**Yani iki ayrı yan etki var:**
- **(A) Retest bekleyen inverted adaylar RSM'i BIAS_LOCKED'de tutar** (en büyük
  blokaj: 948/454/451 bar) → NORMAL sweep penceresi kaybolur.
- **(B) IFVG trigger'ı (girdi reddi dahil) RSM'i yön flipli BIAS_LOCKED'e sokar** →
  bias_conflict reset'i ile kilit düşer, NORMAL retest fırsatı erken sonlanır
  (STATE_DIVERGE'nin `IDLE vs BIAS_LOCKED` deseni).

### 3. Kayıp trade'lerin sınıflandırması (3 coin örneklem)

| Coin | NORMAL trade (off) | NORMAL trade (on) | Δ NORMAL | IFVG trade (on) | Δ net trade | Δ net PnL |
|---|---|---|---|---|---|---|
| ARBUSDT | 2,125 | 1,912 | **-213** | +353 | **+140** | **+7,530** |
| SEIUSDT | 1,848 | 1,626 | **-222** | +396 | **+174** | **+19,786** |
| XRPUSDT | 1,011 | 904 | **-107** | +233 | **+126** | **+3,937** |

- Kaybolan NORMAL trade'lerin tamamı **yukarıdaki (A)+(B) mekanizması** ile açıklanıyor
  (RACE/başka bir filtre bulunamadı; `USURPED` yani aynı barda IFVG'nin NORMAL'i
  ezmesi neredeyse hiç yok — 1'er kez).
- Kaybolan her NORMAL trade'in yerine bir IFVG trade'i **gelmiyor** (Δ NORMAL ≈
  SUPPRESSED sayısı), ama IFVG kendi başına **2-3 kat daha fazla yeni trade** üretiyor
  (NEW_IFVG_ONLY: 481/505/323) ve net PnL her üç coinde de **pozitif**.

### 4. Kök neden netliği → karar önerisi

**Bu kabul edilebilir bir trade-off'tur — şu anki haliyle dokunmaya değmez:**

- IFVG'nin kendi katkısı (+406,592 → 28-coin koşusunda) NORMAL kaybının (~-119,307)
  **3.4 katı**; örneklemde de her 3 coin net pozitif.
- Blokaj pencereleri **tekrar eden, kısa ömürlü fırsatlar** — RSM bir sonraki CBDR
  günü / bias dönüşünde IDLE'ye döner, kalıcı kilit yok.

**Olası gelecek iyileştirme (öncelik düşük — kod değişikliği bu direktifte YASAK, karar ayrı):**
IFVG izlemesini ana RSM'den **ayırıp paralel/bağımsız** yürütmek (örn. inverted aday
listesi için ayrı mini-state machine ya da `_inverted_candidates` varken ana RSM'in
IDLE'ye dönmesine izin veren bir dal): teorik kazanç = bastırılan NORMAL trade'lerin
bir kısmı geri kazanılabilir (tahmini +100-200 trade/coin ölçeğinde), ama IFVG tetik
semantiği (BIAS_LOCKED'de flipped retest bekleme) değişeceği için 28-coin yeniden
doğrulama gerekir. Bu, ayrı bir iş olarak planlanmalı — paper açılışını **bloklamaz**.

**Kırmızı çizgi:** Bu teşhis hiçbir üretim dosyasını değiştirmedi (`tools/` altındaki
teşhis scripti hariç). IFVG_ENABLED canlı config'de hâlâ `False`.

---

### Ek: teşhis aracı

`backtest-sniper/tools/diag_ifvg_normal_suppression.py` — aynı coin'i IFVG off/on
koşar, per-bar RSM state izini karşılaştırıp SUPPRESSED/USURPED/STATE_DIVERGE
sınıflandırması + BLOCKED bar sayılarını basar. Tekrar çalıştırmak için:

```bash
cd backtest-sniper && python tools/diag_ifvg_normal_suppression.py
```
