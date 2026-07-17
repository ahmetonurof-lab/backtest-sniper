# Bucket Risk Multiplier Raporu (v2 — composite score + PF gate)
_Üretim zamanı: 2026-07-17 14:54 UTC_

Metodoloji: mutlak sabit çapa noktaları (coin-içi min-max YOK), PF hem ağırlıklı bileşen hem de sert tavan (gate) olarak kullanılıyor, n<100 için ek güvenlik kilidi var.

---

## AAVEUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=1120)
Score=0.4903 | Final Multiplier = **0.8x**

• PF (2.393) -> norm=0.46
✓ Sharpe (0.2492) -> norm=0.62
✗ MaxDD (4.185%) -> norm=0.00
✓ Confidence(n) (1120) -> norm=1.00
✓ PE (bonus) (59.02%) -> norm=0.63

---

### 1.5-2.0  (n=879)
Score=0.5709 | Final Multiplier = **1.0x**

• PF (2.574) -> norm=0.52
✓ Sharpe (0.2578) -> norm=0.64
• MaxDD (2.639%) -> norm=0.39
✓ Confidence(n) (879) -> norm=0.88
✓ PE (bonus) (56.66%) -> norm=0.56
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=998)
Score=0.6274 | Final Multiplier = **1.0x**

✓ PF (2.733) -> norm=0.58
✓ Sharpe (0.2949) -> norm=0.74
• MaxDD (2.703%) -> norm=0.37
✓ Confidence(n) (998) -> norm=1.00
✓ PE (bonus) (57.21%) -> norm=0.57
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=691)
Score=0.8974 | Final Multiplier = **1.5x**

✓ PF (4.54) -> norm=1.00
✓ Sharpe (0.394) -> norm=0.98
✓ MaxDD (1.596%) -> norm=0.69
✓ Confidence(n) (691) -> norm=0.69
✓ PE (bonus) (61.36%) -> norm=0.71
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=256)
Score=0.8766 | Final Multiplier = **1.5x**

✓ PF (7.546) -> norm=1.00
✓ Sharpe (0.4525) -> norm=1.00
✓ MaxDD (1.279%) -> norm=0.78
✗ Confidence(n) (256) -> norm=0.26
✓ PE (bonus) (63.28%) -> norm=0.78
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## ADAUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=1049)
Score=0.3827 | Final Multiplier = **0.8x**

✗ PF (1.851) -> norm=0.28
• Sharpe (0.1868) -> norm=0.47
✗ MaxDD (3.662%) -> norm=0.10
✓ Confidence(n) (1049) -> norm=1.00
• PE (bonus) (54.34%) -> norm=0.48

---

### 1.5-2.0  (n=909)
Score=0.5545 | Final Multiplier = **1.0x**

• PF (2.361) -> norm=0.45
✓ Sharpe (0.2496) -> norm=0.62
• MaxDD (2.393%) -> norm=0.46
✓ Confidence(n) (909) -> norm=0.91
✓ PE (bonus) (58.64%) -> norm=0.62

---

### 2.0-3.0  (n=1037)
Score=0.754 | Final Multiplier = **1.2x**

✓ PF (3.241) -> norm=0.75
✓ Sharpe (0.3116) -> norm=0.78
✓ MaxDD (1.793%) -> norm=0.63
✓ Confidence(n) (1037) -> norm=1.00
✓ PE (bonus) (58.15%) -> norm=0.60
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=577)
Score=0.6245 | Final Multiplier = **1.0x**

✓ PF (2.885) -> norm=0.63
✓ Sharpe (0.2945) -> norm=0.74
• MaxDD (2.312%) -> norm=0.48
✓ Confidence(n) (577) -> norm=0.58
✓ PE (bonus) (57.02%) -> norm=0.57
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=169)
Score=0.8605 | Final Multiplier = **1.5x**

✓ PF (8.07) -> norm=1.00
✓ Sharpe (0.4676) -> norm=1.00
✓ MaxDD (1.513%) -> norm=0.71
✗ Confidence(n) (169) -> norm=0.17
✓ PE (bonus) (65.68%) -> norm=0.86
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## ALGOUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=884)
Score=0.4169 | Final Multiplier = **0.8x**

✗ PF (1.928) -> norm=0.31
• Sharpe (0.1995) -> norm=0.50
✗ MaxDD (3.115%) -> norm=0.25
✓ Confidence(n) (884) -> norm=0.88
• PE (bonus) (54.41%) -> norm=0.48

---

### 1.5-2.0  (n=896)
Score=0.773 | Final Multiplier = **1.2x**

✓ PF (3.229) -> norm=0.74
✓ Sharpe (0.3461) -> norm=0.87
✓ MaxDD (1.772%) -> norm=0.64
✓ Confidence(n) (896) -> norm=0.90
✓ PE (bonus) (62.17%) -> norm=0.74
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1049)
Score=0.7333 | Final Multiplier = **1.2x**

✓ PF (3.305) -> norm=0.77
✓ Sharpe (0.2877) -> norm=0.72
✓ MaxDD (2.065%) -> norm=0.55
✓ Confidence(n) (1049) -> norm=1.00
✓ PE (bonus) (58.06%) -> norm=0.60
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=729)
Score=0.8244 | Final Multiplier = **1.5x**

✓ PF (3.856) -> norm=0.95
✓ Sharpe (0.2998) -> norm=0.75
✓ MaxDD (1.372%) -> norm=0.75
✓ Confidence(n) (729) -> norm=0.73
✓ PE (bonus) (58.71%) -> norm=0.62
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=222)
Score=0.8266 | Final Multiplier = **1.5x**

✓ PF (5.425) -> norm=1.00
✓ Sharpe (0.3797) -> norm=0.95
✓ MaxDD (1.824%) -> norm=0.62
✗ Confidence(n) (222) -> norm=0.22
✓ PE (bonus) (59.46%) -> norm=0.65
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## APTUSDT

### 0.0-1.0  (n=143)
Score=0.5483 | Final Multiplier = **1.0x**

✓ PF (2.97) -> norm=0.66
✓ Sharpe (0.2684) -> norm=0.67
• MaxDD (2.73%) -> norm=0.36
✗ Confidence(n) (143) -> norm=0.14
• PE (bonus) (53.15%) -> norm=0.44
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 1.0-1.5  (n=588)
Score=0.2414 | Final Multiplier = **0.5x**

✗ PF (1.48) -> norm=0.16
✗ Sharpe (0.1399) -> norm=0.35
✗ MaxDD (4.27%) -> norm=0.00
✓ Confidence(n) (588) -> norm=0.59
• PE (bonus) (53.57%) -> norm=0.45

---

### 1.5-2.0  (n=862)
Score=0.4764 | Final Multiplier = **0.8x**

✗ PF (1.901) -> norm=0.30
• Sharpe (0.2164) -> norm=0.54
• MaxDD (2.079%) -> norm=0.55
✓ Confidence(n) (862) -> norm=0.86
✓ PE (bonus) (56.61%) -> norm=0.55

---

### 2.0-3.0  (n=1086)
Score=0.6352 | Final Multiplier = **1.0x**

✓ PF (2.655) -> norm=0.55
✓ Sharpe (0.2791) -> norm=0.70
• MaxDD (2.115%) -> norm=0.54
✓ Confidence(n) (1086) -> norm=1.00
✓ PE (bonus) (57.46%) -> norm=0.58
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=831)
Score=0.9323 | Final Multiplier = **1.5x**

✓ PF (4.312) -> norm=1.00
✓ Sharpe (0.3712) -> norm=0.93
✓ MaxDD (0.867%) -> norm=0.90
✓ Confidence(n) (831) -> norm=0.83
✓ PE (bonus) (61.85%) -> norm=0.73
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=364)
Score=0.8165 | Final Multiplier = **1.5x**

✓ PF (4.031) -> norm=1.00
✓ Sharpe (0.3657) -> norm=0.91
• MaxDD (2.107%) -> norm=0.54
• Confidence(n) (364) -> norm=0.36
✓ PE (bonus) (58.79%) -> norm=0.63
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## ARBUSDT

### 0.0-1.0  (n=373)
Score=0.22 | Final Multiplier = **0.5x**

✗ PF (1.482) -> norm=0.16
• Sharpe (0.1408) -> norm=0.35
✗ MaxDD (4.308%) -> norm=0.00
• Confidence(n) (373) -> norm=0.37
• PE (bonus) (53.08%) -> norm=0.44

---

### 1.0-1.5  (n=1185)
Score=0.5036 | Final Multiplier = **1.0x**

• PF (2.094) -> norm=0.36
✓ Sharpe (0.2382) -> norm=0.60
• MaxDD (2.704%) -> norm=0.37
✓ Confidence(n) (1185) -> norm=1.00
✓ PE (bonus) (58.23%) -> norm=0.61

---

### 1.5-2.0  (n=888)
Score=0.7251 | Final Multiplier = **1.2x**

✓ PF (2.955) -> norm=0.65
✓ Sharpe (0.303) -> norm=0.76
✓ MaxDD (1.36%) -> norm=0.75
✓ Confidence(n) (888) -> norm=0.89
✓ PE (bonus) (61.82%) -> norm=0.73
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1247)
Score=0.7161 | Final Multiplier = **1.2x**

✓ PF (3.135) -> norm=0.71
✓ Sharpe (0.3001) -> norm=0.75
• MaxDD (2.185%) -> norm=0.52
✓ Confidence(n) (1247) -> norm=1.00
✓ PE (bonus) (60.14%) -> norm=0.67
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=735)
Score=0.8541 | Final Multiplier = **1.5x**

✓ PF (3.852) -> norm=0.95
✓ Sharpe (0.3452) -> norm=0.86
✓ MaxDD (1.41%) -> norm=0.74
✓ Confidence(n) (735) -> norm=0.73
✓ PE (bonus) (59.18%) -> norm=0.64
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=241)
Score=0.8342 | Final Multiplier = **1.5x**

✓ PF (11.726) -> norm=1.00
✓ Sharpe (0.3327) -> norm=0.83
✓ MaxDD (1.392%) -> norm=0.75
✗ Confidence(n) (241) -> norm=0.24
✓ PE (bonus) (69.29%) -> norm=0.98
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## ATOMUSDT

### 0.0-1.0  (n=370)
Score=0.1931 | Final Multiplier = **0.0x**

✗ PF (1.384) -> norm=0.13
✗ Sharpe (0.1228) -> norm=0.31
✗ MaxDD (10.02%) -> norm=0.00
• Confidence(n) (370) -> norm=0.37
• PE (bonus) (52.43%) -> norm=0.41

---

### 1.0-1.5  (n=1088)
Score=0.3884 | Final Multiplier = **0.8x**

✗ PF (1.885) -> norm=0.29
• Sharpe (0.2009) -> norm=0.50
✗ MaxDD (3.839%) -> norm=0.05
✓ Confidence(n) (1088) -> norm=1.00
• PE (bonus) (54.41%) -> norm=0.48

---

### 1.5-2.0  (n=893)
Score=0.5535 | Final Multiplier = **1.0x**

• PF (2.356) -> norm=0.45
✓ Sharpe (0.2539) -> norm=0.63
• MaxDD (2.459%) -> norm=0.44
✓ Confidence(n) (893) -> norm=0.89
✓ PE (bonus) (59.57%) -> norm=0.65

---

### 2.0-3.0  (n=1011)
Score=0.7991 | Final Multiplier = **1.2x**

✓ PF (3.458) -> norm=0.82
✓ Sharpe (0.3057) -> norm=0.76
✓ MaxDD (1.429%) -> norm=0.73
✓ Confidence(n) (1011) -> norm=1.00
✓ PE (bonus) (59.15%) -> norm=0.64
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=715)
Score=0.9142 | Final Multiplier = **1.5x**

✓ PF (5.769) -> norm=1.00
✓ Sharpe (0.4157) -> norm=1.00
✓ MaxDD (1.576%) -> norm=0.69
✓ Confidence(n) (715) -> norm=0.71
✓ PE (bonus) (66.99%) -> norm=0.90
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=166)
Score=0.5627 | Final Multiplier = **1.0x**

✓ PF (2.848) -> norm=0.62
✓ Sharpe (0.2979) -> norm=0.74
• MaxDD (2.563%) -> norm=0.41
✗ Confidence(n) (166) -> norm=0.17
• PE (bonus) (53.61%) -> norm=0.45
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## AVAXUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=1147)
Score=0.357 | Final Multiplier = **0.8x**

✗ PF (1.762) -> norm=0.25
• Sharpe (0.1933) -> norm=0.48
✗ MaxDD (6.416%) -> norm=0.00
✓ Confidence(n) (1147) -> norm=1.00
• PE (bonus) (53.44%) -> norm=0.45

---

### 1.5-2.0  (n=870)
Score=0.4829 | Final Multiplier = **0.8x**

• PF (2.17) -> norm=0.39
✓ Sharpe (0.2259) -> norm=0.56
• MaxDD (2.745%) -> norm=0.36
✓ Confidence(n) (870) -> norm=0.87
• PE (bonus) (53.56%) -> norm=0.45

---

### 2.0-3.0  (n=1057)
Score=0.8319 | Final Multiplier = **1.5x**

✓ PF (3.902) -> norm=0.97
✓ Sharpe (0.3296) -> norm=0.82
• MaxDD (2.396%) -> norm=0.46
✓ Confidence(n) (1057) -> norm=1.00
✓ PE (bonus) (60.93%) -> norm=0.70
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=659)
Score=0.8818 | Final Multiplier = **1.5x**

✓ PF (4.137) -> norm=1.00
✓ Sharpe (0.3569) -> norm=0.89
✓ MaxDD (1.371%) -> norm=0.75
✓ Confidence(n) (659) -> norm=0.66
✓ PE (bonus) (62.37%) -> norm=0.75
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=173)
Score=0.8711 | Final Multiplier = **1.5x**

✓ PF (5.806) -> norm=1.00
✓ Sharpe (0.4536) -> norm=1.00
✓ MaxDD (1.291%) -> norm=0.77
✗ Confidence(n) (173) -> norm=0.17
✓ PE (bonus) (65.32%) -> norm=0.84
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## BNBUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=1046)
Score=0.568 | Final Multiplier = **1.0x**

• PF (2.32) -> norm=0.44
✓ Sharpe (0.2627) -> norm=0.66
• MaxDD (2.562%) -> norm=0.41
✓ Confidence(n) (1046) -> norm=1.00
✓ PE (bonus) (64.24%) -> norm=0.81

---

### 1.5-2.0  (n=492)
Score=0.4455 | Final Multiplier = **0.8x**

• PF (2.364) -> norm=0.45
✓ Sharpe (0.2577) -> norm=0.64
✗ MaxDD (4.198%) -> norm=0.00
• Confidence(n) (492) -> norm=0.49
✓ PE (bonus) (61.59%) -> norm=0.72

---

### 2.0-3.0  (n=603)
Score=0.8345 | Final Multiplier = **1.5x**

✓ PF (4.141) -> norm=1.00
✓ Sharpe (0.3487) -> norm=0.87
• MaxDD (2.189%) -> norm=0.52
✓ Confidence(n) (603) -> norm=0.60
✓ PE (bonus) (64.51%) -> norm=0.82
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=285)
Score=0.8616 | Final Multiplier = **1.5x**

✓ PF (5.177) -> norm=1.00
✓ Sharpe (0.434) -> norm=1.00
✓ MaxDD (1.726%) -> norm=0.65
✗ Confidence(n) (285) -> norm=0.28
✓ PE (bonus) (65.61%) -> norm=0.85
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=50)
Score=0.8668 | Final Multiplier = **1.0x**

✓ PF (7.427) -> norm=1.00
✓ Sharpe (0.6049) -> norm=1.00
✓ MaxDD (1.287%) -> norm=0.78
✗ Confidence(n) (50) -> norm=0.05
✓ PE (bonus) (70.0%) -> norm=1.00
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.
→ Güvenlik kilidi devrede: n=50 < 100, multiplier 1.0x ile sınırlandı.

---

## DOGEUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=711)
Score=0.3881 | Final Multiplier = **0.8x**

✗ PF (2.047) -> norm=0.35
• Sharpe (0.2058) -> norm=0.51
✗ MaxDD (3.852%) -> norm=0.04
✓ Confidence(n) (711) -> norm=0.71
✓ PE (bonus) (56.68%) -> norm=0.56

---

### 1.5-2.0  (n=716)
Score=0.3792 | Final Multiplier = **0.8x**

✗ PF (1.628) -> norm=0.21
• Sharpe (0.1675) -> norm=0.42
• MaxDD (2.248%) -> norm=0.50
✓ Confidence(n) (716) -> norm=0.72
• PE (bonus) (54.19%) -> norm=0.47

---

### 2.0-3.0  (n=828)
Score=0.5767 | Final Multiplier = **1.0x**

• PF (2.478) -> norm=0.49
✓ Sharpe (0.2827) -> norm=0.71
• MaxDD (2.493%) -> norm=0.43
✓ Confidence(n) (828) -> norm=0.83
✓ PE (bonus) (56.76%) -> norm=0.56

---

### 3.0-5.0  (n=706)
Score=0.9242 | Final Multiplier = **1.5x**

✓ PF (5.2) -> norm=1.00
✓ Sharpe (0.4128) -> norm=1.00
✓ MaxDD (1.211%) -> norm=0.80
✓ Confidence(n) (706) -> norm=0.71
✓ PE (bonus) (62.89%) -> norm=0.76
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=354)
Score=0.8956 | Final Multiplier = **1.5x**

✓ PF (9.273) -> norm=1.00
✓ Sharpe (0.4396) -> norm=1.00
✓ MaxDD (1.302%) -> norm=0.77
• Confidence(n) (354) -> norm=0.35
✓ PE (bonus) (69.49%) -> norm=0.98
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## DOTUSDT

### 0.0-1.0  (n=304)
Score=0.0755 | Final Multiplier = **0.0x**

✗ PF (1.046) -> norm=0.02
✗ Sharpe (0.0263) -> norm=0.07
✗ MaxDD (5.574%) -> norm=0.00
✗ Confidence(n) (304) -> norm=0.30
• PE (bonus) (52.63%) -> norm=0.42

---

### 1.0-1.5  (n=822)
Score=0.3061 | Final Multiplier = **0.5x**

✗ PF (1.635) -> norm=0.21
• Sharpe (0.1676) -> norm=0.42
✗ MaxDD (6.172%) -> norm=0.00
✓ Confidence(n) (822) -> norm=0.82
• PE (bonus) (54.38%) -> norm=0.48

---

### 1.5-2.0  (n=834)
Score=0.5331 | Final Multiplier = **1.0x**

• PF (2.298) -> norm=0.43
✓ Sharpe (0.256) -> norm=0.64
• MaxDD (2.516%) -> norm=0.42
✓ Confidence(n) (834) -> norm=0.83
• PE (bonus) (56.47%) -> norm=0.55

---

### 2.0-3.0  (n=1093)
Score=0.8402 | Final Multiplier = **1.5x**

✓ PF (3.485) -> norm=0.83
✓ Sharpe (0.3299) -> norm=0.82
✓ MaxDD (1.025%) -> norm=0.85
✓ Confidence(n) (1093) -> norm=1.00
✓ PE (bonus) (60.02%) -> norm=0.67
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=710)
Score=0.6244 | Final Multiplier = **1.0x**

✓ PF (3.269) -> norm=0.76
✓ Sharpe (0.266) -> norm=0.67
✗ MaxDD (3.151%) -> norm=0.24
✓ Confidence(n) (710) -> norm=0.71
• PE (bonus) (53.52%) -> norm=0.45
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=251)
Score=0.8514 | Final Multiplier = **1.5x**

✓ PF (7.627) -> norm=1.00
✓ Sharpe (0.497) -> norm=1.00
✓ MaxDD (1.939%) -> norm=0.59
✗ Confidence(n) (251) -> norm=0.25
✓ PE (bonus) (67.73%) -> norm=0.92
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## DYDXUSDT

### 0.0-1.0  (n=360)
Score=0.5082 | Final Multiplier = **1.0x**

✓ PF (2.846) -> norm=0.62
✓ Sharpe (0.2655) -> norm=0.66
✗ MaxDD (5.842%) -> norm=0.00
• Confidence(n) (360) -> norm=0.36
✓ PE (bonus) (64.44%) -> norm=0.81
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 1.0-1.5  (n=806)
Score=0.5188 | Final Multiplier = **1.0x**

• PF (2.222) -> norm=0.41
✓ Sharpe (0.2737) -> norm=0.68
✗ MaxDD (2.784%) -> norm=0.35
✓ Confidence(n) (806) -> norm=0.81
• PE (bonus) (56.45%) -> norm=0.55

---

### 1.5-2.0  (n=973)
Score=0.5906 | Final Multiplier = **1.0x**

• PF (2.425) -> norm=0.47
✓ Sharpe (0.2511) -> norm=0.63
✓ MaxDD (1.897%) -> norm=0.60
✓ Confidence(n) (973) -> norm=0.97
• PE (bonus) (56.12%) -> norm=0.54

---

### 2.0-3.0  (n=1397)
Score=0.7362 | Final Multiplier = **1.2x**

✓ PF (2.981) -> norm=0.66
✓ Sharpe (0.3118) -> norm=0.78
✓ MaxDD (1.474%) -> norm=0.72
✓ Confidence(n) (1397) -> norm=1.00
✓ PE (bonus) (59.41%) -> norm=0.65
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1023)
Score=0.9391 | Final Multiplier = **1.5x**

✓ PF (4.614) -> norm=1.00
✓ Sharpe (0.363) -> norm=0.91
✓ MaxDD (1.004%) -> norm=0.86
✓ Confidence(n) (1023) -> norm=1.00
✓ PE (bonus) (63.15%) -> norm=0.77
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=294)
Score=0.9043 | Final Multiplier = **1.5x**

✓ PF (8.09) -> norm=1.00
✓ Sharpe (0.4002) -> norm=1.00
✓ MaxDD (0.891%) -> norm=0.89
✗ Confidence(n) (294) -> norm=0.29
✓ PE (bonus) (66.33%) -> norm=0.88
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## ENAUSDT

### 0.0-1.0  (n=135)
Score=0.4225 | Final Multiplier = **0.8x**

✗ PF (1.942) -> norm=0.31
✓ Sharpe (0.2728) -> norm=0.68
• MaxDD (2.503%) -> norm=0.43
✗ Confidence(n) (135) -> norm=0.14
• PE (bonus) (54.07%) -> norm=0.47

---

### 1.0-1.5  (n=390)
Score=0.3398 | Final Multiplier = **0.5x**

✗ PF (2.009) -> norm=0.34
• Sharpe (0.1962) -> norm=0.49
✗ MaxDD (3.752%) -> norm=0.07
• Confidence(n) (390) -> norm=0.39
• PE (bonus) (51.03%) -> norm=0.37

---

### 1.5-2.0  (n=600)
Score=0.4482 | Final Multiplier = **0.8x**

✗ PF (1.982) -> norm=0.33
✓ Sharpe (0.242) -> norm=0.60
• MaxDD (2.603%) -> norm=0.40
✓ Confidence(n) (600) -> norm=0.60
• PE (bonus) (53.67%) -> norm=0.46

---

### 2.0-3.0  (n=1079)
Score=0.909 | Final Multiplier = **1.5x**

✓ PF (3.849) -> norm=0.95
✓ Sharpe (0.3667) -> norm=0.92
✓ MaxDD (1.208%) -> norm=0.80
✓ Confidence(n) (1079) -> norm=1.00
✓ PE (bonus) (61.91%) -> norm=0.73
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1068)
Score=0.9444 | Final Multiplier = **1.5x**

✓ PF (4.377) -> norm=1.00
✓ Sharpe (0.3601) -> norm=0.90
✓ MaxDD (0.792%) -> norm=0.92
✓ Confidence(n) (1068) -> norm=1.00
✓ PE (bonus) (61.33%) -> norm=0.71
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=580)
Score=0.9102 | Final Multiplier = **1.5x**

✓ PF (6.02) -> norm=1.00
✓ Sharpe (0.3634) -> norm=0.91
✓ MaxDD (0.739%) -> norm=0.93
✓ Confidence(n) (580) -> norm=0.58
✓ PE (bonus) (63.1%) -> norm=0.77
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## GMXUSDT

### 0.0-1.0  (n=285)
Score=0.3156 | Final Multiplier = **0.5x**

✗ PF (2.004) -> norm=0.33
• Sharpe (0.1848) -> norm=0.46
✗ MaxDD (4.66%) -> norm=0.00
✗ Confidence(n) (285) -> norm=0.28
• PE (bonus) (55.09%) -> norm=0.50

---

### 1.0-1.5  (n=734)
Score=0.6928 | Final Multiplier = **1.2x**

✓ PF (3.257) -> norm=0.75
✓ Sharpe (0.2995) -> norm=0.75
• MaxDD (2.53%) -> norm=0.42
✓ Confidence(n) (734) -> norm=0.73
✓ PE (bonus) (62.4%) -> norm=0.75
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 1.5-2.0  (n=829)
Score=0.5643 | Final Multiplier = **1.0x**

✓ PF (2.975) -> norm=0.66
✓ Sharpe (0.2631) -> norm=0.66
✗ MaxDD (4.064%) -> norm=0.00
✓ Confidence(n) (829) -> norm=0.83
✓ PE (bonus) (60.31%) -> norm=0.68
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1248)
Score=0.8601 | Final Multiplier = **1.5x**

✓ PF (3.747) -> norm=0.92
✓ Sharpe (0.3088) -> norm=0.77
✓ MaxDD (1.172%) -> norm=0.81
✓ Confidence(n) (1248) -> norm=1.00
✓ PE (bonus) (63.3%) -> norm=0.78
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=775)
Score=0.9542 | Final Multiplier = **1.5x**

✓ PF (5.378) -> norm=1.00
✓ Sharpe (0.4111) -> norm=1.00
✓ MaxDD (0.752%) -> norm=0.93
✓ Confidence(n) (775) -> norm=0.78
✓ PE (bonus) (63.35%) -> norm=0.78
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=295)
Score=0.8924 | Final Multiplier = **1.5x**

✓ PF (11.337) -> norm=1.00
✓ Sharpe (0.5316) -> norm=1.00
✓ MaxDD (1.263%) -> norm=0.78
✗ Confidence(n) (295) -> norm=0.29
✓ PE (bonus) (73.9%) -> norm=1.00
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## INJUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=438)
Score=0.1953 | Final Multiplier = **0.0x**

✗ PF (1.364) -> norm=0.12
✗ Sharpe (0.1227) -> norm=0.31
✗ MaxDD (4.506%) -> norm=0.00
• Confidence(n) (438) -> norm=0.44
• PE (bonus) (51.37%) -> norm=0.38

---

### 1.5-2.0  (n=749)
Score=0.5391 | Final Multiplier = **1.0x**

• PF (2.462) -> norm=0.49
✓ Sharpe (0.254) -> norm=0.64
• MaxDD (2.628%) -> norm=0.39
✓ Confidence(n) (749) -> norm=0.75
• PE (bonus) (55.81%) -> norm=0.53

---

### 2.0-3.0  (n=1066)
Score=0.5758 | Final Multiplier = **1.0x**

• PF (2.34) -> norm=0.45
✓ Sharpe (0.2755) -> norm=0.69
• MaxDD (2.372%) -> norm=0.47
✓ Confidence(n) (1066) -> norm=1.00
✓ PE (bonus) (56.57%) -> norm=0.55

---

### 3.0-5.0  (n=1359)
Score=0.7608 | Final Multiplier = **1.2x**

✓ PF (3.167) -> norm=0.72
✓ Sharpe (0.3115) -> norm=0.78
✓ MaxDD (1.434%) -> norm=0.73
✓ Confidence(n) (1359) -> norm=1.00
✓ PE (bonus) (57.84%) -> norm=0.59
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=466)
Score=0.9083 | Final Multiplier = **1.5x**

✓ PF (6.215) -> norm=1.00
✓ Sharpe (0.4073) -> norm=1.00
✓ MaxDD (1.029%) -> norm=0.85
• Confidence(n) (466) -> norm=0.47
✓ PE (bonus) (62.45%) -> norm=0.75
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## LDOUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=414)
Score=0.3776 | Final Multiplier = **0.8x**

✗ PF (1.935) -> norm=0.31
• Sharpe (0.2017) -> norm=0.50
✗ MaxDD (2.98%) -> norm=0.29
• Confidence(n) (414) -> norm=0.41
• PE (bonus) (53.62%) -> norm=0.45

---

### 1.5-2.0  (n=763)
Score=0.3507 | Final Multiplier = **0.8x**

✗ PF (1.909) -> norm=0.30
• Sharpe (0.187) -> norm=0.47
✗ MaxDD (4.783%) -> norm=0.00
✓ Confidence(n) (763) -> norm=0.76
• PE (bonus) (54.39%) -> norm=0.48

---

### 2.0-3.0  (n=1019)
Score=0.931 | Final Multiplier = **1.5x**

✓ PF (4.023) -> norm=1.00
✓ Sharpe (0.3694) -> norm=0.92
✓ MaxDD (1.216%) -> norm=0.80
✓ Confidence(n) (1019) -> norm=1.00
✓ PE (bonus) (61.83%) -> norm=0.73
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=953)
Score=0.8981 | Final Multiplier = **1.5x**

✓ PF (4.177) -> norm=1.00
✓ Sharpe (0.3518) -> norm=0.88
✓ MaxDD (1.535%) -> norm=0.70
✓ Confidence(n) (953) -> norm=0.95
✓ PE (bonus) (61.39%) -> norm=0.71
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=629)
Score=0.9204 | Final Multiplier = **1.5x**

✓ PF (8.788) -> norm=1.00
✓ Sharpe (0.371) -> norm=0.93
✓ MaxDD (0.768%) -> norm=0.92
✓ Confidence(n) (629) -> norm=0.63
✓ PE (bonus) (64.07%) -> norm=0.80
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## LINKUSDT

### 0.0-1.0  (n=789)
Score=0.1129 | Final Multiplier = **0.0x**

✗ PF (1.069) -> norm=0.02
✗ Sharpe (0.0162) -> norm=0.04
✗ MaxDD (9.318%) -> norm=0.00
✓ Confidence(n) (789) -> norm=0.79
✗ PE (bonus) (48.16%) -> norm=0.27

---

### 1.0-1.5  (n=1072)
Score=0.5064 | Final Multiplier = **1.0x**

• PF (2.067) -> norm=0.36
✓ Sharpe (0.2382) -> norm=0.60
• MaxDD (2.568%) -> norm=0.41
✓ Confidence(n) (1072) -> norm=1.00
✓ PE (bonus) (58.12%) -> norm=0.60

---

### 1.5-2.0  (n=974)
Score=0.6778 | Final Multiplier = **1.2x**

✓ PF (2.871) -> norm=0.62
✓ Sharpe (0.2908) -> norm=0.73
✓ MaxDD (2.017%) -> norm=0.57
✓ Confidence(n) (974) -> norm=0.97
✓ PE (bonus) (59.24%) -> norm=0.64
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1014)
Score=0.7639 | Final Multiplier = **1.2x**

✓ PF (3.199) -> norm=0.73
✓ Sharpe (0.3158) -> norm=0.79
✓ MaxDD (1.528%) -> norm=0.71
✓ Confidence(n) (1014) -> norm=1.00
✓ PE (bonus) (58.09%) -> norm=0.60
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=440)
Score=0.8001 | Final Multiplier = **1.5x**

✓ PF (3.883) -> norm=0.96
✓ Sharpe (0.3525) -> norm=0.88
• MaxDD (2.153%) -> norm=0.53
• Confidence(n) (440) -> norm=0.44
✓ PE (bonus) (60.68%) -> norm=0.69
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=167)
Score=0.8855 | Final Multiplier = **1.5x**

✓ PF (6.172) -> norm=1.00
✓ Sharpe (0.3967) -> norm=0.99
✓ MaxDD (1.097%) -> norm=0.83
✗ Confidence(n) (167) -> norm=0.17
✓ PE (bonus) (70.66%) -> norm=1.00
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## NEARUSDT

### 0.0-1.0  (n=107)
Score=0.2789 | Final Multiplier = **0.5x**

✗ PF (1.74) -> norm=0.25
• Sharpe (0.2078) -> norm=0.52
✗ MaxDD (5.849%) -> norm=0.00
✗ Confidence(n) (107) -> norm=0.11
• PE (bonus) (56.07%) -> norm=0.54

---

### 1.0-1.5  (n=464)
Score=0.1845 | Final Multiplier = **0.0x**

✗ PF (1.219) -> norm=0.07
✗ Sharpe (0.0841) -> norm=0.21
✗ MaxDD (3.321%) -> norm=0.19
• Confidence(n) (464) -> norm=0.46
• PE (bonus) (51.08%) -> norm=0.37

---

### 1.5-2.0  (n=701)
Score=0.5153 | Final Multiplier = **1.0x**

• PF (2.344) -> norm=0.45
✓ Sharpe (0.2458) -> norm=0.61
• MaxDD (2.529%) -> norm=0.42
✓ Confidence(n) (701) -> norm=0.70
• PE (bonus) (54.49%) -> norm=0.48

---

### 2.0-3.0  (n=1093)
Score=0.6301 | Final Multiplier = **1.0x**

✓ PF (2.679) -> norm=0.56
✓ Sharpe (0.2299) -> norm=0.57
✓ MaxDD (1.525%) -> norm=0.71
✓ Confidence(n) (1093) -> norm=1.00
• PE (bonus) (55.17%) -> norm=0.51
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1107)
Score=0.9129 | Final Multiplier = **1.5x**

✓ PF (3.879) -> norm=0.96
✓ Sharpe (0.3599) -> norm=0.90
✓ MaxDD (1.074%) -> norm=0.84
✓ Confidence(n) (1107) -> norm=1.00
✓ PE (bonus) (60.61%) -> norm=0.69
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=508)
Score=0.8698 | Final Multiplier = **1.5x**

✓ PF (5.273) -> norm=1.00
✓ Sharpe (0.3584) -> norm=0.90
✓ MaxDD (1.154%) -> norm=0.81
• Confidence(n) (508) -> norm=0.51
✓ PE (bonus) (57.28%) -> norm=0.58
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## ONDOUSDT

### 0.0-1.0  (n=351)
Score=0.3526 | Final Multiplier = **0.8x**

• PF (2.107) -> norm=0.37
• Sharpe (0.1847) -> norm=0.46
✗ MaxDD (3.492%) -> norm=0.15
• Confidence(n) (351) -> norm=0.35
✗ PE (bonus) (50.14%) -> norm=0.34

---

### 1.0-1.5  (n=574)
Score=0.6134 | Final Multiplier = **1.0x**

✓ PF (2.955) -> norm=0.65
✓ Sharpe (0.2966) -> norm=0.74
✗ MaxDD (2.86%) -> norm=0.33
✓ Confidence(n) (574) -> norm=0.57
✓ PE (bonus) (59.93%) -> norm=0.66
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 1.5-2.0  (n=359)
Score=0.4957 | Final Multiplier = **0.8x**

• PF (2.5) -> norm=0.50
✓ Sharpe (0.2688) -> norm=0.67
✗ MaxDD (3.019%) -> norm=0.28
• Confidence(n) (359) -> norm=0.36
• PE (bonus) (55.43%) -> norm=0.51
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=508)
Score=0.6423 | Final Multiplier = **1.0x**

✓ PF (3.121) -> norm=0.71
✓ Sharpe (0.2968) -> norm=0.74
• MaxDD (2.589%) -> norm=0.40
• Confidence(n) (508) -> norm=0.51
✓ PE (bonus) (59.65%) -> norm=0.65
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=229)
Score=0.4932 | Final Multiplier = **0.8x**

• PF (2.535) -> norm=0.51
✓ Sharpe (0.2669) -> norm=0.67
✗ MaxDD (2.876%) -> norm=0.32
✗ Confidence(n) (229) -> norm=0.23
• PE (bonus) (55.46%) -> norm=0.52
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=105)
Score=0.7429 | Final Multiplier = **1.2x**

✓ PF (3.418) -> norm=0.81
✓ Sharpe (0.4015) -> norm=1.00
✓ MaxDD (1.938%) -> norm=0.59
✗ Confidence(n) (105) -> norm=0.10
✓ PE (bonus) (59.05%) -> norm=0.63
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## OPUSDT

### 0.0-1.0  (n=139)
Score=0.4227 | Final Multiplier = **0.8x**

✗ PF (1.937) -> norm=0.31
✓ Sharpe (0.2378) -> norm=0.59
• MaxDD (2.077%) -> norm=0.55
✗ Confidence(n) (139) -> norm=0.14
• PE (bonus) (56.12%) -> norm=0.54

---

### 1.0-1.5  (n=494)
Score=0.4392 | Final Multiplier = **0.8x**

• PF (2.184) -> norm=0.39
✓ Sharpe (0.2434) -> norm=0.61
✗ MaxDD (3.289%) -> norm=0.20
• Confidence(n) (494) -> norm=0.49
✓ PE (bonus) (57.49%) -> norm=0.58

---

### 1.5-2.0  (n=753)
Score=0.4313 | Final Multiplier = **0.8x**

• PF (2.085) -> norm=0.36
✓ Sharpe (0.2339) -> norm=0.58
✗ MaxDD (3.511%) -> norm=0.14
✓ Confidence(n) (753) -> norm=0.75
• PE (bonus) (55.64%) -> norm=0.52

---

### 2.0-3.0  (n=1231)
Score=0.7801 | Final Multiplier = **1.2x**

✓ PF (3.139) -> norm=0.71
✓ Sharpe (0.3229) -> norm=0.81
✓ MaxDD (1.219%) -> norm=0.79
✓ Confidence(n) (1231) -> norm=1.00
✓ PE (bonus) (60.84%) -> norm=0.69
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=924)
Score=0.8715 | Final Multiplier = **1.5x**

✓ PF (3.858) -> norm=0.95
✓ Sharpe (0.3562) -> norm=0.89
✓ MaxDD (1.598%) -> norm=0.69
✓ Confidence(n) (924) -> norm=0.92
✓ PE (bonus) (58.87%) -> norm=0.63
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=453)
Score=0.8209 | Final Multiplier = **1.5x**

✓ PF (4.641) -> norm=1.00
✓ Sharpe (0.3184) -> norm=0.80
✓ MaxDD (1.51%) -> norm=0.71
• Confidence(n) (453) -> norm=0.45
✓ PE (bonus) (57.84%) -> norm=0.59
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## PYTHUSDT

### 0.0-1.0  (n=24)
Score=0.4046 | Final Multiplier = **0.8x**

✗ PF (1.776) -> norm=0.26
• Sharpe (0.1754) -> norm=0.44
✓ MaxDD (0.826%) -> norm=0.91
✗ Confidence(n) (24) -> norm=0.02
• PE (bonus) (54.17%) -> norm=0.47
→ Güvenlik kilidi devrede: n=24 < 100, multiplier 1.0x ile sınırlandı.

---

### 1.0-1.5  (n=388)
Score=0.4588 | Final Multiplier = **0.8x**

• PF (2.563) -> norm=0.52
✓ Sharpe (0.2525) -> norm=0.63
✗ MaxDD (4.276%) -> norm=0.00
• Confidence(n) (388) -> norm=0.39
✓ PE (bonus) (61.6%) -> norm=0.72
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 1.5-2.0  (n=573)
Score=0.5507 | Final Multiplier = **1.0x**

• PF (2.616) -> norm=0.54
✓ Sharpe (0.2632) -> norm=0.66
• MaxDD (2.638%) -> norm=0.39
✓ Confidence(n) (573) -> norm=0.57
✓ PE (bonus) (57.24%) -> norm=0.57
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1108)
Score=0.8411 | Final Multiplier = **1.5x**

✓ PF (3.569) -> norm=0.86
✓ Sharpe (0.3185) -> norm=0.80
✓ MaxDD (1.102%) -> norm=0.83
✓ Confidence(n) (1108) -> norm=1.00
✓ PE (bonus) (60.56%) -> norm=0.69
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1072)
Score=0.9672 | Final Multiplier = **1.5x**

✓ PF (5.314) -> norm=1.00
✓ Sharpe (0.4048) -> norm=1.00
✓ MaxDD (1.045%) -> norm=0.84
✓ Confidence(n) (1072) -> norm=1.00
✓ PE (bonus) (66.23%) -> norm=0.87
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=595)
Score=0.9263 | Final Multiplier = **1.5x**

✓ PF (9.723) -> norm=1.00
✓ Sharpe (0.3807) -> norm=0.95
✓ MaxDD (0.832%) -> norm=0.91
✓ Confidence(n) (595) -> norm=0.59
✓ PE (bonus) (67.56%) -> norm=0.92
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## RENDERUSDT

### 0.0-1.0  (n=243)
Score=0.3737 | Final Multiplier = **0.8x**

• PF (2.152) -> norm=0.38
✓ Sharpe (0.2369) -> norm=0.59
✗ MaxDD (4.505%) -> norm=0.00
✗ Confidence(n) (243) -> norm=0.24
✓ PE (bonus) (59.26%) -> norm=0.64

---

### 1.0-1.5  (n=500)
Score=0.3207 | Final Multiplier = **0.5x**

✗ PF (1.849) -> norm=0.28
• Sharpe (0.1838) -> norm=0.46
✗ MaxDD (3.796%) -> norm=0.06
• Confidence(n) (500) -> norm=0.50
• PE (bonus) (52.4%) -> norm=0.41

---

### 1.5-2.0  (n=752)
Score=0.5599 | Final Multiplier = **1.0x**

• PF (2.601) -> norm=0.53
✓ Sharpe (0.2625) -> norm=0.66
✗ MaxDD (2.845%) -> norm=0.33
✓ Confidence(n) (752) -> norm=0.75
✓ PE (bonus) (59.57%) -> norm=0.65
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=998)
Score=0.7965 | Final Multiplier = **1.2x**

✓ PF (3.209) -> norm=0.74
✓ Sharpe (0.3407) -> norm=0.85
✓ MaxDD (1.324%) -> norm=0.76
✓ Confidence(n) (998) -> norm=1.00
✓ PE (bonus) (60.92%) -> norm=0.70
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=772)
Score=0.9353 | Final Multiplier = **1.5x**

✓ PF (5.019) -> norm=1.00
✓ Sharpe (0.4109) -> norm=1.00
✓ MaxDD (1.143%) -> norm=0.82
✓ Confidence(n) (772) -> norm=0.77
✓ PE (bonus) (63.6%) -> norm=0.79
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=261)
Score=0.8596 | Final Multiplier = **1.5x**

✓ PF (7.198) -> norm=1.00
✓ Sharpe (0.3526) -> norm=0.88
✓ MaxDD (1.096%) -> norm=0.83
✗ Confidence(n) (261) -> norm=0.26
✓ PE (bonus) (66.67%) -> norm=0.89
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## SEIUSDT

### 0.0-1.0  (n=120)
Score=0.3305 | Final Multiplier = **0.5x**

✗ PF (1.815) -> norm=0.27
• Sharpe (0.1892) -> norm=0.47
✗ MaxDD (3.08%) -> norm=0.26
✗ Confidence(n) (120) -> norm=0.12
✓ PE (bonus) (60.83%) -> norm=0.69

---

### 1.0-1.5  (n=496)
Score=0.3233 | Final Multiplier = **0.5x**

✗ PF (1.794) -> norm=0.26
• Sharpe (0.2008) -> norm=0.50
✗ MaxDD (3.948%) -> norm=0.01
• Confidence(n) (496) -> norm=0.50
• PE (bonus) (56.25%) -> norm=0.54

---

### 1.5-2.0  (n=558)
Score=0.4494 | Final Multiplier = **0.8x**

• PF (2.148) -> norm=0.38
✓ Sharpe (0.2212) -> norm=0.55
✗ MaxDD (2.802%) -> norm=0.34
✓ Confidence(n) (558) -> norm=0.56
✓ PE (bonus) (57.53%) -> norm=0.58

---

### 2.0-3.0  (n=1082)
Score=0.9396 | Final Multiplier = **1.5x**

✓ PF (4.403) -> norm=1.00
✓ Sharpe (0.3554) -> norm=0.89
✓ MaxDD (0.907%) -> norm=0.88
✓ Confidence(n) (1082) -> norm=1.00
✓ PE (bonus) (63.68%) -> norm=0.79
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1039)
Score=0.9204 | Final Multiplier = **1.5x**

✓ PF (3.906) -> norm=0.97
✓ Sharpe (0.3755) -> norm=0.94
✓ MaxDD (1.248%) -> norm=0.79
✓ Confidence(n) (1039) -> norm=1.00
✓ PE (bonus) (61.69%) -> norm=0.72
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=512)
Score=0.9225 | Final Multiplier = **1.5x**

✓ PF (7.971) -> norm=1.00
✓ Sharpe (0.4259) -> norm=1.00
✓ MaxDD (0.913%) -> norm=0.88
• Confidence(n) (512) -> norm=0.51
✓ PE (bonus) (64.84%) -> norm=0.83
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## SOLUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=570)
Score=0.2339 | Final Multiplier = **0.5x**

✗ PF (1.451) -> norm=0.15
✗ Sharpe (0.1382) -> norm=0.35
✗ MaxDD (4.582%) -> norm=0.00
✓ Confidence(n) (570) -> norm=0.57
• PE (bonus) (53.16%) -> norm=0.44

---

### 1.5-2.0  (n=775)
Score=0.3809 | Final Multiplier = **0.8x**

✗ PF (1.862) -> norm=0.29
• Sharpe (0.1958) -> norm=0.49
✗ MaxDD (3.419%) -> norm=0.17
✓ Confidence(n) (775) -> norm=0.78
• PE (bonus) (55.1%) -> norm=0.50

---

### 2.0-3.0  (n=1010)
Score=0.5782 | Final Multiplier = **1.0x**

• PF (2.415) -> norm=0.47
✓ Sharpe (0.2709) -> norm=0.68
• MaxDD (2.576%) -> norm=0.41
✓ Confidence(n) (1010) -> norm=1.00
✓ PE (bonus) (59.7%) -> norm=0.66

---

### 3.0-5.0  (n=702)
Score=0.9106 | Final Multiplier = **1.5x**

✓ PF (4.571) -> norm=1.00
✓ Sharpe (0.3756) -> norm=0.94
✓ MaxDD (1.108%) -> norm=0.83
✓ Confidence(n) (702) -> norm=0.70
✓ PE (bonus) (61.82%) -> norm=0.73
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=245)
Score=0.7188 | Final Multiplier = **1.2x**

✓ PF (3.755) -> norm=0.92
✓ Sharpe (0.3268) -> norm=0.82
• MaxDD (2.643%) -> norm=0.39
✗ Confidence(n) (245) -> norm=0.24
✓ PE (bonus) (58.78%) -> norm=0.63
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## STRKUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=253)
Score=0.4704 | Final Multiplier = **0.8x**

• PF (2.379) -> norm=0.46
✓ Sharpe (0.2628) -> norm=0.66
✗ MaxDD (2.936%) -> norm=0.30
✗ Confidence(n) (253) -> norm=0.25
✓ PE (bonus) (56.52%) -> norm=0.55

---

### 1.5-2.0  (n=637)
Score=0.4903 | Final Multiplier = **0.8x**

• PF (2.414) -> norm=0.47
✓ Sharpe (0.2377) -> norm=0.59
✗ MaxDD (3.013%) -> norm=0.28
✓ Confidence(n) (637) -> norm=0.64
• PE (bonus) (54.95%) -> norm=0.50

---

### 2.0-3.0  (n=1131)
Score=0.7807 | Final Multiplier = **1.2x**

✓ PF (3.289) -> norm=0.76
✓ Sharpe (0.3097) -> norm=0.77
✓ MaxDD (1.438%) -> norm=0.73
✓ Confidence(n) (1131) -> norm=1.00
✓ PE (bonus) (60.65%) -> norm=0.69
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1006)
Score=0.8409 | Final Multiplier = **1.5x**

✓ PF (3.508) -> norm=0.84
✓ Sharpe (0.3698) -> norm=0.92
✓ MaxDD (1.622%) -> norm=0.68
✓ Confidence(n) (1006) -> norm=1.00
✓ PE (bonus) (59.84%) -> norm=0.66
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=629)
Score=0.916 | Final Multiplier = **1.5x**

✓ PF (6.866) -> norm=1.00
✓ Sharpe (0.3718) -> norm=0.93
✓ MaxDD (0.908%) -> norm=0.88
✓ Confidence(n) (629) -> norm=0.63
✓ PE (bonus) (65.18%) -> norm=0.84
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## SUIUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=826)
Score=0.4311 | Final Multiplier = **0.8x**

• PF (2.113) -> norm=0.37
• Sharpe (0.1654) -> norm=0.41
• MaxDD (2.707%) -> norm=0.37
✓ Confidence(n) (826) -> norm=0.83
• PE (bonus) (53.15%) -> norm=0.44

---

### 1.5-2.0  (n=730)
Score=0.56 | Final Multiplier = **1.0x**

• PF (2.312) -> norm=0.44
✓ Sharpe (0.2565) -> norm=0.64
✓ MaxDD (1.752%) -> norm=0.64
✓ Confidence(n) (730) -> norm=0.73
• PE (bonus) (55.21%) -> norm=0.51

---

### 2.0-3.0  (n=1121)
Score=0.5129 | Final Multiplier = **1.0x**

• PF (2.135) -> norm=0.38
✓ Sharpe (0.2291) -> norm=0.57
• MaxDD (2.291%) -> norm=0.49
✓ Confidence(n) (1121) -> norm=1.00
• PE (bonus) (52.1%) -> norm=0.40

---

### 3.0-5.0  (n=930)
Score=0.6741 | Final Multiplier = **1.2x**

✓ PF (2.94) -> norm=0.65
✓ Sharpe (0.2975) -> norm=0.74
• MaxDD (2.231%) -> norm=0.51
✓ Confidence(n) (930) -> norm=0.93
✓ PE (bonus) (57.53%) -> norm=0.58
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=419)
Score=0.9071 | Final Multiplier = **1.5x**

✓ PF (6.255) -> norm=1.00
✓ Sharpe (0.3919) -> norm=0.98
✓ MaxDD (1.028%) -> norm=0.85
• Confidence(n) (419) -> norm=0.42
✓ PE (bonus) (67.78%) -> norm=0.93
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## TIAUSDT

### 0.0-1.0  (n=46)
Score=0.4675 | Final Multiplier = **0.8x**

✓ PF (2.692) -> norm=0.56
✓ Sharpe (0.3059) -> norm=0.76
✗ MaxDD (3.824%) -> norm=0.05
✗ Confidence(n) (46) -> norm=0.05
✗ PE (bonus) (50.0%) -> norm=0.33
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.
→ Güvenlik kilidi devrede: n=46 < 100, multiplier 1.0x ile sınırlandı.

---

### 1.0-1.5  (n=310)
Score=0.4045 | Final Multiplier = **0.8x**

✗ PF (2.015) -> norm=0.34
✓ Sharpe (0.226) -> norm=0.56
✗ MaxDD (2.86%) -> norm=0.33
✗ Confidence(n) (310) -> norm=0.31
• PE (bonus) (56.13%) -> norm=0.54

---

### 1.5-2.0  (n=545)
Score=0.7827 | Final Multiplier = **1.2x**

✓ PF (3.383) -> norm=0.79
✓ Sharpe (0.3587) -> norm=0.90
✓ MaxDD (1.421%) -> norm=0.74
• Confidence(n) (545) -> norm=0.55
✓ PE (bonus) (61.1%) -> norm=0.70
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1212)
Score=0.7704 | Final Multiplier = **1.2x**

✓ PF (3.14) -> norm=0.71
✓ Sharpe (0.3192) -> norm=0.80
✓ MaxDD (1.265%) -> norm=0.78
✓ Confidence(n) (1212) -> norm=1.00
✓ PE (bonus) (57.76%) -> norm=0.59
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1101)
Score=0.9379 | Final Multiplier = **1.5x**

✓ PF (4.024) -> norm=1.00
✓ Sharpe (0.3682) -> norm=0.92
✓ MaxDD (1.03%) -> norm=0.85
✓ Confidence(n) (1101) -> norm=1.00
✓ PE (bonus) (61.04%) -> norm=0.70
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=807)
Score=0.9593 | Final Multiplier = **1.5x**

✓ PF (7.088) -> norm=1.00
✓ Sharpe (0.4256) -> norm=1.00
✓ MaxDD (0.806%) -> norm=0.91
✓ Confidence(n) (807) -> norm=0.81
✓ PE (bonus) (66.05%) -> norm=0.87
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## UNIUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=689)
Score=0.3118 | Final Multiplier = **0.5x**

✗ PF (1.753) -> norm=0.25
• Sharpe (0.1725) -> norm=0.43
✗ MaxDD (4.657%) -> norm=0.00
✓ Confidence(n) (689) -> norm=0.69
• PE (bonus) (54.14%) -> norm=0.47

---

### 1.5-2.0  (n=814)
Score=0.6465 | Final Multiplier = **1.0x**

✓ PF (2.714) -> norm=0.57
✓ Sharpe (0.2958) -> norm=0.74
✓ MaxDD (1.949%) -> norm=0.59
✓ Confidence(n) (814) -> norm=0.81
✓ PE (bonus) (58.97%) -> norm=0.63
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1100)
Score=0.6606 | Final Multiplier = **1.2x**

✓ PF (2.837) -> norm=0.61
✓ Sharpe (0.2772) -> norm=0.69
• MaxDD (2.09%) -> norm=0.55
✓ Confidence(n) (1100) -> norm=1.00
✓ PE (bonus) (57.82%) -> norm=0.59
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=719)
Score=0.7551 | Final Multiplier = **1.2x**

✓ PF (3.676) -> norm=0.89
✓ Sharpe (0.3484) -> norm=0.87
✗ MaxDD (3.008%) -> norm=0.28
✓ Confidence(n) (719) -> norm=0.72
✓ PE (bonus) (60.5%) -> norm=0.68
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=385)
Score=0.6755 | Final Multiplier = **1.2x**

✓ PF (3.373) -> norm=0.79
✓ Sharpe (0.3228) -> norm=0.81
• MaxDD (2.582%) -> norm=0.41
• Confidence(n) (385) -> norm=0.39
• PE (bonus) (55.58%) -> norm=0.52
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## XRPUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=1174)
Score=0.3467 | Final Multiplier = **0.5x**

✗ PF (1.629) -> norm=0.21
• Sharpe (0.162) -> norm=0.40
✗ MaxDD (3.457%) -> norm=0.16
✓ Confidence(n) (1174) -> norm=1.00
• PE (bonus) (55.03%) -> norm=0.50

---

### 1.5-2.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 2.0-3.0  (n=694)
Score=0.5837 | Final Multiplier = **1.0x**

✓ PF (2.721) -> norm=0.57
✓ Sharpe (0.261) -> norm=0.65
• MaxDD (2.442%) -> norm=0.45
✓ Confidence(n) (694) -> norm=0.69
• PE (bonus) (56.34%) -> norm=0.54
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=363)
Score=0.8669 | Final Multiplier = **1.5x**

✓ PF (5.489) -> norm=1.00
✓ Sharpe (0.4193) -> norm=1.00
✓ MaxDD (1.702%) -> norm=0.66
• Confidence(n) (363) -> norm=0.36
✓ PE (bonus) (63.36%) -> norm=0.78
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=121)
Score=0.8161 | Final Multiplier = **1.5x**

✓ PF (3.961) -> norm=0.99
✓ Sharpe (0.4226) -> norm=1.00
✓ MaxDD (1.949%) -> norm=0.59
✗ Confidence(n) (121) -> norm=0.12
✓ PE (bonus) (57.85%) -> norm=0.60
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---
