# Parquet Analiz Raporu V2 — 3 Soru (Kodun Gerçek Faz Sınırlarıyla)

**Oluşturma:** 2026-07-04  
**Kaynak:** `trades_default.parquet`, `trades_real_cbdr.parquet`, `trades_asia_range.parquet`  
**Araç:** `src/analyze_parquet_v2.py` (kullanır: `sniper/src/session.py::detect_phase()`)

---

## Ön Bilgi: Kodun `detect_phase()` Gerçek Sınırları

```python
# session.py ~satir 305-325
def detect_phase(dt, session_hours=None):
    h = dt.hour
    # CBDR window (session_hours'a gore)
    in_cbdr = (h >= sh or h < eh) if spans else (sh <= h < eh)
    if in_cbdr:
        return SessionPhase.CBDR
    # Aktif seanslar (HARDCODED, piyasa saatleri degismez)
    if 2 <= h < 13:
        return SessionPhase.LONDON      # ← 02:00'de basliyor!
    elif 13 <= h < 22:
        return SessionPhase.NEWYORK
    return SessionPhase.CLOSED
```

### Her Session İçin Saat-Faz Tablosu

```
DEFAULT [22-2]:
  00-01 CBDR | 02-12 LONDON | 13-21 NEWYORK | 22-23 CBDR

REAL_CBDR [19-1]:
  00 CBDR | 01 CLOSED | 02-12 LONDON | 13-18 NEWYORK | 19-23 CBDR

ASIA_RANGE [1-5]:
  00 CLOSED | 01-04 CBDR | 05-12 LONDON | 13-21 NEWYORK | 22-23 CLOSED
```

**Kritik:** Kodda bağımsız bir `ASIA` fazı yoktur. `RangeTracker.asia` (02-08) sadece range genişliği izleme amaçlıdır, entry engellemez. **LONDON 02:00 UTC'de başlar** — textbook "Londra 07-08 açılır"ın aksine.

---

## Soru 1 — Entry'ler hangi FAZLARDA açılmış?

### DEFAULT [22-2] — 79.633 trade

| Faz | Trade | % | WR |
|-----|-------|---|----|
| **LONDON** (02-13) | 35.741 | **%44.9** | **%44.1** |
| **NEWYORK** (13-22) | 42.340 | **%53.2** | **%38.0** |
| CBDR (22-02) | 1.552 | %1.9 | %30.6 |

### REAL_CBDR [19-1] — 67.518 trade

| Faz | Trade | % | WR |
|-----|-------|---|----|
| **LONDON** (02-13) | 36.716 | **%54.4** | **%42.7** |
| **NEWYORK** (13-22) | 28.266 | **%41.9** | **%36.1** |
| CBDR (19-01) | 1.608 | %2.4 | %34.1 |
| CLOSED (01-02) | 928 | %1.4 | %57.2 |

### ASIA_RANGE [1-5] — 78.377 trade

| Faz | Trade | % | WR |
|-----|-------|---|----|
| **LONDON** (05-13) | 22.174 | **%28.3** | **%47.1** |
| **NEWYORK** (13-22) | 40.921 | **%52.2** | **%36.0** |
| CLOSED (22-01) | 13.842 | %17.7 | %44.0 |
| CBDR (01-05) | 1.440 | %1.8 | %27.8 |

### ➡ V2 Sonuç

**Önceki rapordaki çelişki çözüldü.** 02:00-07:00 arasındaki 15.373 trade "Asya trade'i" değil, **erken Londra trade'i** — çünkü kodun `detect_phase()` fonksiyonu LONDON'u 02:00'de başlatıyor.

Her üç session'da da:
- **LONDON WR > NEWYORK WR** (~5-8 puan farkla)
- LONDON'da hem daha yüksek WR hem de daha yüksek ortalama PnL
- NEWYORK daha fazla trade üretiyor ama WR düşük

---

## Soru 2 — `fail: %0.00` Nedir?

(Kod aynı, değişiklik yok. Bkz. V1 raporu.)

---

## Soru 3 — Kodun Kendi Fazlarıyla Performans Karşılaştırması

### LONDON vs NEWYORK (Her Session)

| Session | London WR | NY WR | Fark | London AvgPnL | NY AvgPnL |
|---------|-----------|-------|------|---------------|-----------|
| DEFAULT | %44.1 | %38.0 | **+6.1p** | +$20.88 | +$14.01 |
| REAL_CBDR | %42.7 | %36.1 | **+6.6p** | +$19.96 | +$12.90 |
| ASIA_RANGE | %47.1 | %36.0 | **+11.1p** | +$26.98 | +$10.71 |

### Peki "Erken Londra (02-08) vs Geç Londra (08-13)" Farkı?

| Session | 02-08 WR | 08-13 WR | 13-22 WR | 02-08 vs 08-13 |
|---------|----------|----------|----------|----------------|
| DEFAULT | %49.1 | %40.4 | %38.0 | **+8.7p** |
| REAL_CBDR | %47.0 | %39.1 | %35.8 | **+7.9p** |
| ASIA_RANGE | %53.1 | %45.0 | %36.0 | **+8.1p** |

### ➡ V2 Sonuç

1. **Kod LONDON'u 02:00 UTC'de başlatıyor.** 02-08 arası "Asya" değil, erken Londra.
2. **Erken Londra (02-08) en yüksek WR'ye sahip** (~%48-53). Bu gerçek bir bulgu.
3. **Geç Londra (08-13) orta WR** (~%39-45).
4. **NEWYORK (13-22) en düşük WR** (~%36-38).
5. ASIA_RANGE'de CLOSED fazı (22-01) WR=%44 ile iyi — çünkü bu saatlerde az trade var ama kaliteli.

**Öneri:** Strateji optimizasyonu için "erken Londra saatlerinde (02-08) daha agresif, NY'de daha seçici" bir yaklaşım düşünülebilir. Bu hipotez ayrı bir backtest gerektirir.

---

*Rapor `src/analyze_parquet_v2.py` ile oluşturulmuştur. `detect_phase()` fonksiyonu `sniper/src/session.py`'den alınmıştır.*
