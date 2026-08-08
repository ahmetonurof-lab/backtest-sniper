# Baş Mühendis Raporu — Trailing Yol Haritası (2026-08-08)

Soru: "continuation-confirm K=1.0 sonucu geldi mi, yoksa doğrudan ATR-chase replay'ine mi geçiyoruz?"

## 1. Continuation (B) — K=1.0 sonucu GELDİ: ölü

Kaynak: `backtest-sniper/reports/trailing_replay_ab_c.md` (2026-08-07 21:21, FINAL, 30 coin).

| Varyasyon | NetPnL | PE% | A'dan sapma |
|---|---|---|---|
| A retrace (baseline) | **+4,100,540** | 60.9% | — |
| B K=1.0 N=1 | -1,207,682 | 33.5% | -5,308,222 |
| B K=1.0 N=2 | -1,194,755 | 33.6% | -5,295,295 |
| B K=1.0 N=3 | -1,181,140 | 33.8% | -5,281,680 |

- **9/9 B varyasyonu derin negatif** (K=0.1/0.3/1.0 × N=1/2/3): -1.18M ila -1.53M.
- N-bar teyit marjinal iyileştiriyor ama PE% 32.7-33.8 yapısal bozuk (A: 60.9); geniş K tamponu da telafi etmiyor (HOP -15.5K, PnL Delta -2.5M).
- **Karar:** continuation canlıya deploy edilmez. **A/retrace sabit kalır.**

## 2. ATR-chase (D / aktivasyonlu) — tarama tamam, K=2.0/R=1.5 seçildi

Kaynak: `backtest-sniper/reports/trailing_activation_scan.md` (2026-08-07 22:54, PYTH+SEI 13 koşu grid).

- Hiçbir D(K,R) toplam NetPnL'de A'yı geçmiyor; en iyi D K=2.0/R=1.5 → +437,071 (A: +438,205, -0.26%).
- **K=2.0 tek tutarlı iyileşme:** MaxDD 1,088→1,035 (-4.9%) ve A'ya ~1K NetPnL mesafe. K=1.0 tüm R'lerde negatif (-5.3K ila -7.2K).
- Kullanıcı kararı: **D modu (TRAIL_MODE=activation, K=2.0, R=1.5) canlıya birebir uygulandı.**

## 3. Canlı durum (bugün, 2026-08-08)

- D modu deploy: commit `42de7d5` (config kalıcı, env override destekli).
- **Recovery tick_size fix deploy:** commit `daaeeb0` — root cause `recover_positions`'ın ActiveTrade'i tick_size'sız kurması (default 0.10) → tüm trailing iyileşmeleri normalize'de yutuluyordu. 5 adımlık plan tamamlandı, testleri geçti.
- Canlı doğrulama: ALGO (tick=1e-05) trail#1 sl=0.089010/tp=0.082170 **updated**; RENDER (tick=0.001) trail#1 sl=1.318/tp=1.217 **updated**. 0 ERROR/CRITICAL, run `paper-20260808-000537`.

## 4. Sıradaki adım

- Continuation kapatıldı; ATR-chase replay'i (K=0.5/1.0/1.5) planlanmıştı — canlıda D modu K=2.0 ile çalıştığı için bu replay parametre setinin revize edilip edilmeyeceği kararı bekliyor.
- Açık izler: `runtime.status` senkronizasyonu (integration_lifecycle), ENA pre-entry SL guard kalibrasyonu, DYDX reconciliation.
