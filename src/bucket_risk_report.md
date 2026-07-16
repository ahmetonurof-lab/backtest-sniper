# Bucket Risk Multiplier Raporu (v2 — composite score + PF gate)
_Üretim zamanı: 2026-07-16 03:02 UTC_

Metodoloji: mutlak sabit çapa noktaları (coin-içi min-max YOK), PF hem ağırlıklı bileşen hem de sert tavan (gate) olarak kullanılıyor, n<100 için ek güvenlik kilidi var.

---

## AAVEUSDT

### 0.0-1.0  (n=481)
Score=0.1375 | Final Multiplier = **0.0x**

✗ PF (1.164) -> norm=0.05
✗ Sharpe (0.0722) -> norm=0.18
✗ MaxDD (16.297%) -> norm=0.00
• Confidence(n) (481) -> norm=0.48
• PE (bonus) (50.94%) -> norm=0.36

---

### 1.0-1.5  (n=1127)
Score=0.4915 | Final Multiplier = **0.8x**

• PF (2.409) -> norm=0.47
✓ Sharpe (0.2485) -> norm=0.62
✗ MaxDD (4.605%) -> norm=0.00
✓ Confidence(n) (1127) -> norm=1.00
✓ PE (bonus) (58.74%) -> norm=0.62

---

### 1.5-2.0  (n=928)
Score=0.5548 | Final Multiplier = **1.0x**

• PF (2.503) -> norm=0.50
✓ Sharpe (0.2553) -> norm=0.64
✗ MaxDD (2.812%) -> norm=0.34
✓ Confidence(n) (928) -> norm=0.93
• PE (bonus) (55.93%) -> norm=0.53
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1057)
Score=0.7276 | Final Multiplier = **1.2x**

✓ PF (2.899) -> norm=0.63
✓ Sharpe (0.3195) -> norm=0.80
✓ MaxDD (1.496%) -> norm=0.72
✓ Confidence(n) (1057) -> norm=1.00
✓ PE (bonus) (58.47%) -> norm=0.62
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=698)
Score=0.8579 | Final Multiplier = **1.5x**

✓ PF (4.217) -> norm=1.00
✓ Sharpe (0.3756) -> norm=0.94
• MaxDD (2.132%) -> norm=0.53
✓ Confidence(n) (698) -> norm=0.70
✓ PE (bonus) (60.32%) -> norm=0.68
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=243)
Score=0.8771 | Final Multiplier = **1.5x**

✓ PF (8.371) -> norm=1.00
✓ Sharpe (0.4324) -> norm=1.00
✓ MaxDD (1.244%) -> norm=0.79
✗ Confidence(n) (243) -> norm=0.24
✓ PE (bonus) (63.37%) -> norm=0.78
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

### 0.0-1.0  (n=451)
Score=0.1113 | Final Multiplier = **0.0x**

✗ PF (1.187) -> norm=0.06
✗ Sharpe (0.0385) -> norm=0.10
✗ MaxDD (22.056%) -> norm=0.00
• Confidence(n) (451) -> norm=0.45
✗ PE (bonus) (48.78%) -> norm=0.29

---

### 1.0-1.5  (n=872)
Score=0.4568 | Final Multiplier = **0.8x**

• PF (2.061) -> norm=0.35
• Sharpe (0.2186) -> norm=0.55
✗ MaxDD (2.93%) -> norm=0.31
✓ Confidence(n) (872) -> norm=0.87
• PE (bonus) (55.05%) -> norm=0.50

---

### 1.5-2.0  (n=886)
Score=0.7644 | Final Multiplier = **1.2x**

✓ PF (3.187) -> norm=0.73
✓ Sharpe (0.3467) -> norm=0.87
✓ MaxDD (1.824%) -> norm=0.62
✓ Confidence(n) (886) -> norm=0.89
✓ PE (bonus) (62.3%) -> norm=0.74
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1038)
Score=0.7388 | Final Multiplier = **1.2x**

✓ PF (3.308) -> norm=0.77
✓ Sharpe (0.2874) -> norm=0.72
✓ MaxDD (1.964%) -> norm=0.58
✓ Confidence(n) (1038) -> norm=1.00
✓ PE (bonus) (58.29%) -> norm=0.61
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=715)
Score=0.7899 | Final Multiplier = **1.2x**

✓ PF (3.734) -> norm=0.91
✓ Sharpe (0.2986) -> norm=0.75
✓ MaxDD (1.686%) -> norm=0.66
✓ Confidence(n) (715) -> norm=0.71
✓ PE (bonus) (58.46%) -> norm=0.62
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=214)
Score=0.826 | Final Multiplier = **1.5x**

✓ PF (4.618) -> norm=1.00
✓ Sharpe (0.4248) -> norm=1.00
✓ MaxDD (2.067%) -> norm=0.55
✗ Confidence(n) (214) -> norm=0.21
✓ PE (bonus) (58.41%) -> norm=0.61
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## APTUSDT

### 0.0-1.0  (n=140)
Score=0.5786 | Final Multiplier = **1.0x**

✓ PF (3.119) -> norm=0.71
✓ Sharpe (0.2798) -> norm=0.70
• MaxDD (2.716%) -> norm=0.37
✗ Confidence(n) (140) -> norm=0.14
• PE (bonus) (54.29%) -> norm=0.48
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 1.0-1.5  (n=577)
Score=0.2643 | Final Multiplier = **0.5x**

✗ PF (1.504) -> norm=0.17
• Sharpe (0.1444) -> norm=0.36
✗ MaxDD (3.624%) -> norm=0.11
✓ Confidence(n) (577) -> norm=0.58
• PE (bonus) (53.21%) -> norm=0.44

---

### 1.5-2.0  (n=859)
Score=0.4362 | Final Multiplier = **0.8x**

✗ PF (1.797) -> norm=0.27
• Sharpe (0.2074) -> norm=0.52
• MaxDD (2.47%) -> norm=0.44
✓ Confidence(n) (859) -> norm=0.86
• PE (bonus) (56.23%) -> norm=0.54

---

### 2.0-3.0  (n=1087)
Score=0.6394 | Final Multiplier = **1.0x**

✓ PF (2.669) -> norm=0.56
✓ Sharpe (0.2802) -> norm=0.70
• MaxDD (2.089%) -> norm=0.55
✓ Confidence(n) (1087) -> norm=1.00
✓ PE (bonus) (57.59%) -> norm=0.59
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=812)
Score=0.9321 | Final Multiplier = **1.5x**

✓ PF (4.203) -> norm=1.00
✓ Sharpe (0.3714) -> norm=0.93
✓ MaxDD (0.824%) -> norm=0.91
✓ Confidence(n) (812) -> norm=0.81
✓ PE (bonus) (61.58%) -> norm=0.72
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=360)
Score=0.8193 | Final Multiplier = **1.5x**

✓ PF (4.119) -> norm=1.00
✓ Sharpe (0.375) -> norm=0.94
• MaxDD (2.154%) -> norm=0.53
• Confidence(n) (360) -> norm=0.36
✓ PE (bonus) (58.33%) -> norm=0.61
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

### 0.0-1.0  (n=997)
Score=0.3654 | Final Multiplier = **0.8x**

✗ PF (1.879) -> norm=0.29
• Sharpe (0.1572) -> norm=0.39
✗ MaxDD (3.721%) -> norm=0.08
✓ Confidence(n) (997) -> norm=1.00
• PE (bonus) (55.57%) -> norm=0.52

---

### 1.0-1.5  (n=1177)
Score=0.3008 | Final Multiplier = **0.5x**

✗ PF (1.566) -> norm=0.19
• Sharpe (0.1497) -> norm=0.37
✗ MaxDD (5.059%) -> norm=0.00
✓ Confidence(n) (1177) -> norm=1.00
• PE (bonus) (53.44%) -> norm=0.45

---

### 1.5-2.0  (n=1053)
Score=0.6817 | Final Multiplier = **1.2x**

✓ PF (2.791) -> norm=0.60
✓ Sharpe (0.2842) -> norm=0.71
✓ MaxDD (1.641%) -> norm=0.67
✓ Confidence(n) (1053) -> norm=1.00
✓ PE (bonus) (58.31%) -> norm=0.61
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=872)
Score=0.7049 | Final Multiplier = **1.2x**

✓ PF (3.114) -> norm=0.70
✓ Sharpe (0.2869) -> norm=0.72
✓ MaxDD (1.824%) -> norm=0.62
✓ Confidence(n) (872) -> norm=0.87
✓ PE (bonus) (57.68%) -> norm=0.59
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=416)
Score=0.8334 | Final Multiplier = **1.5x**

✓ PF (4.343) -> norm=1.00
✓ Sharpe (0.3553) -> norm=0.89
✓ MaxDD (1.85%) -> norm=0.61
• Confidence(n) (416) -> norm=0.42
✓ PE (bonus) (62.5%) -> norm=0.75
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=95)
Score=0.8142 | Final Multiplier = **1.0x**

✓ PF (4.888) -> norm=1.00
✓ Sharpe (0.3795) -> norm=0.95
• MaxDD (2.087%) -> norm=0.55
✗ Confidence(n) (95) -> norm=0.10
✓ PE (bonus) (67.37%) -> norm=0.91
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.
→ Güvenlik kilidi devrede: n=95 < 100, multiplier 1.0x ile sınırlandı.

---

## AVAXUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=749)
Score=0.5223 | Final Multiplier = **1.0x**

• PF (2.345) -> norm=0.45
✓ Sharpe (0.2755) -> norm=0.69
✗ MaxDD (3.031%) -> norm=0.28
✓ Confidence(n) (749) -> norm=0.75
✓ PE (bonus) (58.34%) -> norm=0.61

---

### 1.5-2.0  (n=898)
Score=0.3531 | Final Multiplier = **0.8x**

✗ PF (1.643) -> norm=0.21
• Sharpe (0.1659) -> norm=0.41
✗ MaxDD (3.235%) -> norm=0.22
✓ Confidence(n) (898) -> norm=0.90
• PE (bonus) (55.79%) -> norm=0.53

---

### 2.0-3.0  (n=1000)
Score=0.648 | Final Multiplier = **1.0x**

✓ PF (3.004) -> norm=0.67
✓ Sharpe (0.281) -> norm=0.70
✗ MaxDD (2.814%) -> norm=0.34
✓ Confidence(n) (1000) -> norm=1.00
• PE (bonus) (56.1%) -> norm=0.54
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=717)
Score=0.6424 | Final Multiplier = **1.0x**

✓ PF (2.74) -> norm=0.58
✓ Sharpe (0.2969) -> norm=0.74
✓ MaxDD (1.933%) -> norm=0.59
✓ Confidence(n) (717) -> norm=0.72
✓ PE (bonus) (59.27%) -> norm=0.64
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=358)
Score=0.7055 | Final Multiplier = **1.2x**

✓ PF (4.345) -> norm=1.00
✓ Sharpe (0.2832) -> norm=0.71
✗ MaxDD (3.172%) -> norm=0.24
• Confidence(n) (358) -> norm=0.36
✓ PE (bonus) (56.98%) -> norm=0.57
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## BNBUSDT

### 0.0-1.0  (n=1216)
Score=0.1246 | Final Multiplier = **0.0x**

✗ PF (0.913) -> norm=0.00
✗ Sharpe (-0.034) -> norm=0.00
✗ MaxDD (42.501%) -> norm=0.00
✓ Confidence(n) (1216) -> norm=1.00
• PE (bonus) (54.77%) -> norm=0.49

---

### 1.0-1.5  (n=1017)
Score=0.433 | Final Multiplier = **0.8x**

• PF (2.079) -> norm=0.36
• Sharpe (0.2199) -> norm=0.55
✗ MaxDD (4.275%) -> norm=0.00
✓ Confidence(n) (1017) -> norm=1.00
✓ PE (bonus) (62.24%) -> norm=0.74

---

### 1.5-2.0  (n=484)
Score=0.467 | Final Multiplier = **0.8x**

• PF (2.528) -> norm=0.51
✓ Sharpe (0.258) -> norm=0.65
✗ MaxDD (4.112%) -> norm=0.00
• Confidence(n) (484) -> norm=0.48
✓ PE (bonus) (61.36%) -> norm=0.71
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=571)
Score=0.6965 | Final Multiplier = **1.2x**

✓ PF (3.483) -> norm=0.83
✓ Sharpe (0.3259) -> norm=0.81
✗ MaxDD (3.082%) -> norm=0.26
✓ Confidence(n) (571) -> norm=0.57
✓ PE (bonus) (61.3%) -> norm=0.71
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=292)
Score=0.8707 | Final Multiplier = **1.5x**

✓ PF (5.934) -> norm=1.00
✓ Sharpe (0.4831) -> norm=1.00
✓ MaxDD (1.605%) -> norm=0.68
✗ Confidence(n) (292) -> norm=0.29
✓ PE (bonus) (67.12%) -> norm=0.90
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=51)
Score=0.8626 | Final Multiplier = **1.0x**

✓ PF (7.157) -> norm=1.00
✓ Sharpe (0.6395) -> norm=1.00
✓ MaxDD (1.376%) -> norm=0.75
✗ Confidence(n) (51) -> norm=0.05
✓ PE (bonus) (72.55%) -> norm=1.00
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.
→ Güvenlik kilidi devrede: n=51 < 100, multiplier 1.0x ile sınırlandı.

---

## DOGEUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=712)
Score=0.387 | Final Multiplier = **0.8x**

✗ PF (1.948) -> norm=0.32
• Sharpe (0.1942) -> norm=0.49
✗ MaxDD (3.435%) -> norm=0.16
✓ Confidence(n) (712) -> norm=0.71
✓ PE (bonus) (56.6%) -> norm=0.55

---

### 1.5-2.0  (n=699)
Score=0.3282 | Final Multiplier = **0.5x**

✗ PF (1.551) -> norm=0.18
• Sharpe (0.1589) -> norm=0.40
✗ MaxDD (2.894%) -> norm=0.32
✓ Confidence(n) (699) -> norm=0.70
• PE (bonus) (53.22%) -> norm=0.44

---

### 2.0-3.0  (n=824)
Score=0.5232 | Final Multiplier = **1.0x**

• PF (2.298) -> norm=0.43
✓ Sharpe (0.2556) -> norm=0.64
• MaxDD (2.677%) -> norm=0.38
✓ Confidence(n) (824) -> norm=0.82
• PE (bonus) (55.95%) -> norm=0.53

---

### 3.0-5.0  (n=696)
Score=0.9141 | Final Multiplier = **1.5x**

✓ PF (5.227) -> norm=1.00
✓ Sharpe (0.416) -> norm=1.00
✓ MaxDD (1.405%) -> norm=0.74
✓ Confidence(n) (696) -> norm=0.70
✓ PE (bonus) (63.07%) -> norm=0.77
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=355)
Score=0.8971 | Final Multiplier = **1.5x**

✓ PF (9.562) -> norm=1.00
✓ Sharpe (0.4433) -> norm=1.00
✓ MaxDD (1.291%) -> norm=0.77
• Confidence(n) (355) -> norm=0.35
✓ PE (bonus) (70.14%) -> norm=1.00
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## DOTUSDT

### 0.0-1.0  (n=820)
Score=0.295 | Final Multiplier = **0.5x**

✗ PF (1.621) -> norm=0.21
• Sharpe (0.1513) -> norm=0.38
✗ MaxDD (4.97%) -> norm=0.00
✓ Confidence(n) (820) -> norm=0.82
• PE (bonus) (55.61%) -> norm=0.52

---

### 1.0-1.5  (n=1123)
Score=0.5048 | Final Multiplier = **1.0x**

• PF (2.296) -> norm=0.43
✓ Sharpe (0.2424) -> norm=0.61
✗ MaxDD (3.246%) -> norm=0.22
✓ Confidence(n) (1123) -> norm=1.00
• PE (bonus) (56.46%) -> norm=0.55

---

### 1.5-2.0  (n=984)
Score=0.4253 | Final Multiplier = **0.8x**

• PF (2.166) -> norm=0.39
• Sharpe (0.2094) -> norm=0.52
✗ MaxDD (3.971%) -> norm=0.01
✓ Confidence(n) (984) -> norm=0.98
• PE (bonus) (54.88%) -> norm=0.50

---

### 2.0-3.0  (n=1093)
Score=0.7244 | Final Multiplier = **1.2x**

✓ PF (2.997) -> norm=0.67
✓ Sharpe (0.3118) -> norm=0.78
✓ MaxDD (1.743%) -> norm=0.64
✓ Confidence(n) (1093) -> norm=1.00
✓ PE (bonus) (58.83%) -> norm=0.63
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=475)
Score=0.7181 | Final Multiplier = **1.2x**

✓ PF (3.548) -> norm=0.85
✓ Sharpe (0.2879) -> norm=0.72
✓ MaxDD (1.855%) -> norm=0.61
• Confidence(n) (475) -> norm=0.47
• PE (bonus) (54.32%) -> norm=0.48
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=188)
Score=0.7288 | Final Multiplier = **1.2x**

✓ PF (4.992) -> norm=1.00
✓ Sharpe (0.4262) -> norm=1.00
✗ MaxDD (4.311%) -> norm=0.00
✗ Confidence(n) (188) -> norm=0.19
✓ PE (bonus) (57.98%) -> norm=0.60
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
Score=0.5322 | Final Multiplier = **1.0x**

• PF (2.222) -> norm=0.41
✓ Sharpe (0.2737) -> norm=0.68
• MaxDD (2.509%) -> norm=0.43
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
Score=0.3926 | Final Multiplier = **0.8x**

✗ PF (2.009) -> norm=0.34
• Sharpe (0.1962) -> norm=0.49
• MaxDD (2.665%) -> norm=0.38
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

### 0.0-1.0  (n=620)
Score=0.3892 | Final Multiplier = **0.8x**

• PF (2.088) -> norm=0.36
• Sharpe (0.2007) -> norm=0.50
✗ MaxDD (3.784%) -> norm=0.06
✓ Confidence(n) (620) -> norm=0.62
✓ PE (bonus) (59.52%) -> norm=0.65

---

### 1.0-1.5  (n=1218)
Score=0.7008 | Final Multiplier = **1.2x**

✓ PF (2.963) -> norm=0.65
✓ Sharpe (0.2874) -> norm=0.72
✓ MaxDD (1.872%) -> norm=0.61
✓ Confidence(n) (1218) -> norm=1.00
✓ PE (bonus) (61.08%) -> norm=0.70
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 1.5-2.0  (n=919)
Score=0.9005 | Final Multiplier = **1.5x**

✓ PF (3.974) -> norm=0.99
✓ Sharpe (0.3216) -> norm=0.80
✓ MaxDD (0.986%) -> norm=0.86
✓ Confidence(n) (919) -> norm=0.92
✓ PE (bonus) (63.22%) -> norm=0.77
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1287)
Score=0.9093 | Final Multiplier = **1.5x**

✓ PF (4.298) -> norm=1.00
✓ Sharpe (0.3084) -> norm=0.77
✓ MaxDD (0.837%) -> norm=0.90
✓ Confidence(n) (1287) -> norm=1.00
✓ PE (bonus) (62.47%) -> norm=0.75
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=566)
Score=0.7945 | Final Multiplier = **1.2x**

✓ PF (4.158) -> norm=1.00
✓ Sharpe (0.2814) -> norm=0.70
✓ MaxDD (1.897%) -> norm=0.60
✓ Confidence(n) (566) -> norm=0.57
✓ PE (bonus) (61.48%) -> norm=0.72
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=173)
Score=0.8945 | Final Multiplier = **1.5x**

✓ PF (8.911) -> norm=1.00
✓ Sharpe (0.4218) -> norm=1.00
✓ MaxDD (0.927%) -> norm=0.88
✗ Confidence(n) (173) -> norm=0.17
✓ PE (bonus) (68.79%) -> norm=0.96
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## INJUSDT

### 0.0-1.0  (n=244)
Score=0.0724 | Final Multiplier = **0.0x**

✗ PF (1.045) -> norm=0.01
✗ Sharpe (0.0341) -> norm=0.09
✗ MaxDD (3.885%) -> norm=0.03
✗ Confidence(n) (244) -> norm=0.24
✗ PE (bonus) (47.95%) -> norm=0.27

---

### 1.0-1.5  (n=852)
Score=0.3547 | Final Multiplier = **0.8x**

✗ PF (1.804) -> norm=0.27
• Sharpe (0.188) -> norm=0.47
✗ MaxDD (3.713%) -> norm=0.08
✓ Confidence(n) (852) -> norm=0.85
• PE (bonus) (51.29%) -> norm=0.38

---

### 1.5-2.0  (n=825)
Score=0.5525 | Final Multiplier = **1.0x**

• PF (2.445) -> norm=0.48
✓ Sharpe (0.2691) -> norm=0.67
• MaxDD (2.699%) -> norm=0.37
✓ Confidence(n) (825) -> norm=0.82
✓ PE (bonus) (56.61%) -> norm=0.55

---

### 2.0-3.0  (n=1218)
Score=0.5301 | Final Multiplier = **1.0x**

✗ PF (1.998) -> norm=0.33
✓ Sharpe (0.2264) -> norm=0.57
✓ MaxDD (1.564%) -> norm=0.70
✓ Confidence(n) (1218) -> norm=1.00
• PE (bonus) (53.53%) -> norm=0.45

---

### 3.0-5.0  (n=947)
Score=0.9428 | Final Multiplier = **1.5x**

✓ PF (3.951) -> norm=0.98
✓ Sharpe (0.397) -> norm=0.99
✓ MaxDD (1.049%) -> norm=0.84
✓ Confidence(n) (947) -> norm=0.95
✓ PE (bonus) (60.08%) -> norm=0.67
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=272)
Score=0.8366 | Final Multiplier = **1.5x**

✓ PF (4.367) -> norm=1.00
✓ Sharpe (0.4036) -> norm=1.00
✓ MaxDD (1.931%) -> norm=0.59
✗ Confidence(n) (272) -> norm=0.27
✓ PE (bonus) (57.35%) -> norm=0.58
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## LDOUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=414)
Score=0.4192 | Final Multiplier = **0.8x**

✗ PF (1.935) -> norm=0.31
• Sharpe (0.2017) -> norm=0.50
• MaxDD (2.124%) -> norm=0.54
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

### 0.0-1.0  (n=424)
Score=0.2889 | Final Multiplier = **0.5x**

✗ PF (1.672) -> norm=0.22
• Sharpe (0.1817) -> norm=0.45
✗ MaxDD (4.054%) -> norm=0.00
• Confidence(n) (424) -> norm=0.42
✓ PE (bonus) (59.2%) -> norm=0.64

---

### 1.0-1.5  (n=801)
Score=0.2993 | Final Multiplier = **0.5x**

✗ PF (1.488) -> norm=0.16
✗ Sharpe (0.1332) -> norm=0.33
✗ MaxDD (3.203%) -> norm=0.23
✓ Confidence(n) (801) -> norm=0.80
• PE (bonus) (54.31%) -> norm=0.48

---

### 1.5-2.0  (n=943)
Score=0.4794 | Final Multiplier = **0.8x**

• PF (2.234) -> norm=0.41
✓ Sharpe (0.2759) -> norm=0.69
✗ MaxDD (4.644%) -> norm=0.00
✓ Confidence(n) (943) -> norm=0.94
✓ PE (bonus) (58.11%) -> norm=0.60

---

### 2.0-3.0  (n=1014)
Score=0.5532 | Final Multiplier = **1.0x**

• PF (2.525) -> norm=0.51
✓ Sharpe (0.2898) -> norm=0.72
✗ MaxDD (3.622%) -> norm=0.11
✓ Confidence(n) (1014) -> norm=1.00
✓ PE (bonus) (58.48%) -> norm=0.62
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=686)
Score=0.669 | Final Multiplier = **1.2x**

✓ PF (3.108) -> norm=0.70
✓ Sharpe (0.3438) -> norm=0.86
✗ MaxDD (2.952%) -> norm=0.30
✓ Confidence(n) (686) -> norm=0.69
✓ PE (bonus) (57.58%) -> norm=0.59
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=226)
Score=0.8283 | Final Multiplier = **1.5x**

✓ PF (4.631) -> norm=1.00
✓ Sharpe (0.4543) -> norm=1.00
• MaxDD (2.242%) -> norm=0.50
✗ Confidence(n) (226) -> norm=0.23
✓ PE (bonus) (64.16%) -> norm=0.81
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## NEARUSDT

### 0.0-1.0  (n=307)
Score=0.4337 | Final Multiplier = **0.8x**

• PF (2.491) -> norm=0.50
✓ Sharpe (0.23) -> norm=0.57
✗ MaxDD (3.712%) -> norm=0.08
✗ Confidence(n) (307) -> norm=0.31
✓ PE (bonus) (57.98%) -> norm=0.60

---

### 1.0-1.5  (n=942)
Score=0.2463 | Final Multiplier = **0.5x**

✗ PF (1.381) -> norm=0.13
✗ Sharpe (0.1211) -> norm=0.30
✗ MaxDD (5.095%) -> norm=0.00
✓ Confidence(n) (942) -> norm=0.94
• PE (bonus) (50.96%) -> norm=0.37

---

### 1.5-2.0  (n=900)
Score=0.5059 | Final Multiplier = **1.0x**

• PF (2.458) -> norm=0.49
✓ Sharpe (0.2453) -> norm=0.61
✗ MaxDD (3.417%) -> norm=0.17
✓ Confidence(n) (900) -> norm=0.90
• PE (bonus) (53.67%) -> norm=0.46

---

### 2.0-3.0  (n=1293)
Score=0.5921 | Final Multiplier = **1.0x**

• PF (2.437) -> norm=0.48
✓ Sharpe (0.2592) -> norm=0.65
✓ MaxDD (2.055%) -> norm=0.56
✓ Confidence(n) (1293) -> norm=1.00
• PE (bonus) (55.76%) -> norm=0.53

---

### 3.0-5.0  (n=894)
Score=0.7386 | Final Multiplier = **1.2x**

✓ PF (3.189) -> norm=0.73
✓ Sharpe (0.2948) -> norm=0.74
✓ MaxDD (1.46%) -> norm=0.73
✓ Confidence(n) (894) -> norm=0.89
✓ PE (bonus) (56.6%) -> norm=0.55
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=316)
Score=0.8629 | Final Multiplier = **1.5x**

✓ PF (5.869) -> norm=1.00
✓ Sharpe (0.3835) -> norm=0.96
✓ MaxDD (1.465%) -> norm=0.72
✗ Confidence(n) (316) -> norm=0.32
✓ PE (bonus) (63.61%) -> norm=0.79
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## ONDOUSDT

### 0.0-1.0  (n=351)
Score=0.3998 | Final Multiplier = **0.8x**

• PF (2.107) -> norm=0.37
• Sharpe (0.1847) -> norm=0.46
• MaxDD (2.52%) -> norm=0.42
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

### 0.0-1.0  (n=309)
Score=0.4004 | Final Multiplier = **0.8x**

✗ PF (2.026) -> norm=0.34
✓ Sharpe (0.2342) -> norm=0.59
✗ MaxDD (3.117%) -> norm=0.25
✗ Confidence(n) (309) -> norm=0.31
✓ PE (bonus) (56.96%) -> norm=0.57

---

### 1.0-1.5  (n=962)
Score=0.4357 | Final Multiplier = **0.8x**

✗ PF (1.972) -> norm=0.32
• Sharpe (0.2088) -> norm=0.52
✗ MaxDD (3.155%) -> norm=0.24
✓ Confidence(n) (962) -> norm=0.96
• PE (bonus) (54.78%) -> norm=0.49

---

### 1.5-2.0  (n=964)
Score=0.7905 | Final Multiplier = **1.2x**

✓ PF (3.237) -> norm=0.75
✓ Sharpe (0.3292) -> norm=0.82
✓ MaxDD (1.349%) -> norm=0.76
✓ Confidence(n) (964) -> norm=0.96
✓ PE (bonus) (62.45%) -> norm=0.75
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1073)
Score=0.7889 | Final Multiplier = **1.2x**

✓ PF (3.27) -> norm=0.76
✓ Sharpe (0.3295) -> norm=0.82
✓ MaxDD (1.428%) -> norm=0.73
✓ Confidence(n) (1073) -> norm=1.00
✓ PE (bonus) (58.81%) -> norm=0.63
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=989)
Score=0.6751 | Final Multiplier = **1.2x**

✓ PF (2.822) -> norm=0.61
✓ Sharpe (0.2753) -> norm=0.69
✓ MaxDD (1.694%) -> norm=0.66
✓ Confidence(n) (989) -> norm=0.99
✓ PE (bonus) (57.63%) -> norm=0.59
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=215)
Score=0.8659 | Final Multiplier = **1.5x**

✓ PF (5.421) -> norm=1.00
✓ Sharpe (0.439) -> norm=1.00
✓ MaxDD (1.365%) -> norm=0.75
✗ Confidence(n) (215) -> norm=0.21
✓ PE (bonus) (61.86%) -> norm=0.73
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## PYTHUSDT

### 0.0-1.0  (n=140)
Score=0.3486 | Final Multiplier = **0.5x**

✗ PF (1.899) -> norm=0.30
✓ Sharpe (0.2281) -> norm=0.57
✗ MaxDD (3.325%) -> norm=0.19
✗ Confidence(n) (140) -> norm=0.14
• PE (bonus) (55.0%) -> norm=0.50

---

### 1.0-1.5  (n=600)
Score=0.7741 | Final Multiplier = **1.2x**

✓ PF (3.677) -> norm=0.89
✓ Sharpe (0.3175) -> norm=0.79
✓ MaxDD (2.031%) -> norm=0.56
✓ Confidence(n) (600) -> norm=0.60
✓ PE (bonus) (63.0%) -> norm=0.77
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 1.5-2.0  (n=670)
Score=0.8233 | Final Multiplier = **1.5x**

✓ PF (3.819) -> norm=0.94
✓ Sharpe (0.3459) -> norm=0.86
✓ MaxDD (2.055%) -> norm=0.56
✓ Confidence(n) (670) -> norm=0.67
✓ PE (bonus) (65.82%) -> norm=0.86
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1409)
Score=0.7941 | Final Multiplier = **1.2x**

✓ PF (3.373) -> norm=0.79
✓ Sharpe (0.3149) -> norm=0.79
✓ MaxDD (1.451%) -> norm=0.73
✓ Confidence(n) (1409) -> norm=1.00
✓ PE (bonus) (60.04%) -> norm=0.67
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=863)
Score=0.9186 | Final Multiplier = **1.5x**

✓ PF (4.289) -> norm=1.00
✓ Sharpe (0.3789) -> norm=0.95
✓ MaxDD (1.318%) -> norm=0.77
✓ Confidence(n) (863) -> norm=0.86
✓ PE (bonus) (61.76%) -> norm=0.73
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=388)
Score=0.9087 | Final Multiplier = **1.5x**

✓ PF (7.041) -> norm=1.00
✓ Sharpe (0.3974) -> norm=0.99
✓ MaxDD (0.955%) -> norm=0.87
• Confidence(n) (388) -> norm=0.39
✓ PE (bonus) (66.24%) -> norm=0.87
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
Score=0.4391 | Final Multiplier = **0.8x**

• PF (2.33) -> norm=0.44
✓ Sharpe (0.2662) -> norm=0.67
✗ MaxDD (3.393%) -> norm=0.17
✗ Confidence(n) (120) -> norm=0.12
✓ PE (bonus) (61.67%) -> norm=0.72

---

### 1.0-1.5  (n=500)
Score=0.3359 | Final Multiplier = **0.5x**

✗ PF (1.833) -> norm=0.28
• Sharpe (0.2063) -> norm=0.52
✗ MaxDD (3.902%) -> norm=0.03
• Confidence(n) (500) -> norm=0.50
✓ PE (bonus) (56.8%) -> norm=0.56

---

### 1.5-2.0  (n=545)
Score=0.4774 | Final Multiplier = **0.8x**

• PF (2.271) -> norm=0.42
✓ Sharpe (0.233) -> norm=0.58
• MaxDD (2.686%) -> norm=0.38
• Confidence(n) (545) -> norm=0.55
✓ PE (bonus) (56.88%) -> norm=0.56

---

### 2.0-3.0  (n=1050)
Score=0.922 | Final Multiplier = **1.5x**

✓ PF (4.057) -> norm=1.00
✓ Sharpe (0.3403) -> norm=0.85
✓ MaxDD (1.022%) -> norm=0.85
✓ Confidence(n) (1050) -> norm=1.00
✓ PE (bonus) (62.57%) -> norm=0.75
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1038)
Score=0.9405 | Final Multiplier = **1.5x**

✓ PF (4.022) -> norm=1.00
✓ Sharpe (0.3822) -> norm=0.96
✓ MaxDD (1.211%) -> norm=0.80
✓ Confidence(n) (1038) -> norm=1.00
✓ PE (bonus) (62.24%) -> norm=0.74
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=493)
Score=0.9114 | Final Multiplier = **1.5x**

✓ PF (6.835) -> norm=1.00
✓ Sharpe (0.4146) -> norm=1.00
✓ MaxDD (1.064%) -> norm=0.84
• Confidence(n) (493) -> norm=0.49
✓ PE (bonus) (63.69%) -> norm=0.79
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## SOLUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=561)
Score=0.2218 | Final Multiplier = **0.5x**

✗ PF (1.409) -> norm=0.14
✗ Sharpe (0.132) -> norm=0.33
✗ MaxDD (4.969%) -> norm=0.00
✓ Confidence(n) (561) -> norm=0.56
• PE (bonus) (52.41%) -> norm=0.41

---

### 1.5-2.0  (n=767)
Score=0.3808 | Final Multiplier = **0.8x**

✗ PF (1.797) -> norm=0.27
• Sharpe (0.1846) -> norm=0.46
✗ MaxDD (3.032%) -> norm=0.28
✓ Confidence(n) (767) -> norm=0.77
• PE (bonus) (54.11%) -> norm=0.47

---

### 2.0-3.0  (n=1009)
Score=0.5609 | Final Multiplier = **1.0x**

• PF (2.374) -> norm=0.46
✓ Sharpe (0.2666) -> norm=0.67
• MaxDD (2.737%) -> norm=0.36
✓ Confidence(n) (1009) -> norm=1.00
✓ PE (bonus) (59.07%) -> norm=0.64

---

### 3.0-5.0  (n=698)
Score=0.9024 | Final Multiplier = **1.5x**

✓ PF (4.371) -> norm=1.00
✓ Sharpe (0.3674) -> norm=0.92
✓ MaxDD (1.136%) -> norm=0.82
✓ Confidence(n) (698) -> norm=0.70
✓ PE (bonus) (61.32%) -> norm=0.71
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=238)
Score=0.8058 | Final Multiplier = **1.5x**

✓ PF (4.046) -> norm=1.00
✓ Sharpe (0.3423) -> norm=0.86
✓ MaxDD (1.788%) -> norm=0.63
✗ Confidence(n) (238) -> norm=0.24
✓ PE (bonus) (60.08%) -> norm=0.67
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## STRKUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=251)
Score=0.4496 | Final Multiplier = **0.8x**

• PF (2.286) -> norm=0.43
✓ Sharpe (0.2583) -> norm=0.65
✗ MaxDD (2.996%) -> norm=0.29
✗ Confidence(n) (251) -> norm=0.25
• PE (bonus) (55.38%) -> norm=0.51

---

### 1.5-2.0  (n=636)
Score=0.4804 | Final Multiplier = **0.8x**

• PF (2.375) -> norm=0.46
✓ Sharpe (0.2335) -> norm=0.58
✗ MaxDD (3.038%) -> norm=0.27
✓ Confidence(n) (636) -> norm=0.64
• PE (bonus) (54.72%) -> norm=0.49

---

### 2.0-3.0  (n=1122)
Score=0.7765 | Final Multiplier = **1.2x**

✓ PF (3.266) -> norm=0.76
✓ Sharpe (0.309) -> norm=0.77
✓ MaxDD (1.444%) -> norm=0.73
✓ Confidence(n) (1122) -> norm=1.00
✓ PE (bonus) (60.43%) -> norm=0.68
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=994)
Score=0.8205 | Final Multiplier = **1.5x**

✓ PF (3.422) -> norm=0.81
✓ Sharpe (0.3626) -> norm=0.91
✓ MaxDD (1.669%) -> norm=0.67
✓ Confidence(n) (994) -> norm=0.99
✓ PE (bonus) (59.26%) -> norm=0.64
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=619)
Score=0.9064 | Final Multiplier = **1.5x**

✓ PF (6.74) -> norm=1.00
✓ Sharpe (0.3801) -> norm=0.95
✓ MaxDD (1.193%) -> norm=0.80
✓ Confidence(n) (619) -> norm=0.62
✓ PE (bonus) (64.94%) -> norm=0.83
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## SUIUSDT

### 1.0-1.5  (n=809)
Score=0.4183 | Final Multiplier = **0.8x**

✗ PF (2.045) -> norm=0.35
• Sharpe (0.1699) -> norm=0.42
✗ MaxDD (2.794%) -> norm=0.34
✓ Confidence(n) (809) -> norm=0.81
• PE (bonus) (52.78%) -> norm=0.43

---

### 1.5-2.0  (n=720)
Score=0.5358 | Final Multiplier = **1.0x**

• PF (2.215) -> norm=0.40
✓ Sharpe (0.248) -> norm=0.62
✓ MaxDD (1.808%) -> norm=0.63
✓ Confidence(n) (720) -> norm=0.72
• PE (bonus) (54.31%) -> norm=0.48

---

### 2.0-3.0  (n=1117)
Score=0.5082 | Final Multiplier = **1.0x**

• PF (2.126) -> norm=0.38
✓ Sharpe (0.2234) -> norm=0.56
• MaxDD (2.276%) -> norm=0.49
✓ Confidence(n) (1117) -> norm=1.00
• PE (bonus) (51.84%) -> norm=0.39

---

### 3.0-5.0  (n=936)
Score=0.6676 | Final Multiplier = **1.2x**

✓ PF (2.887) -> norm=0.63
✓ Sharpe (0.2993) -> norm=0.75
• MaxDD (2.24%) -> norm=0.50
✓ Confidence(n) (936) -> norm=0.94
✓ PE (bonus) (57.16%) -> norm=0.57
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=409)
Score=0.8983 | Final Multiplier = **1.5x**

✓ PF (6.321) -> norm=1.00
✓ Sharpe (0.3822) -> norm=0.96
✓ MaxDD (1.044%) -> norm=0.84
• Confidence(n) (409) -> norm=0.41
✓ PE (bonus) (67.48%) -> norm=0.92
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## TIAUSDT

### 0.0-1.0  (n=44)
Score=0.5567 | Final Multiplier = **1.0x**

✓ PF (3.054) -> norm=0.68
✓ Sharpe (0.3182) -> norm=0.80
✗ MaxDD (3.251%) -> norm=0.21
✗ Confidence(n) (44) -> norm=0.04
• PE (bonus) (52.27%) -> norm=0.41
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.
→ Güvenlik kilidi devrede: n=44 < 100, multiplier 1.0x ile sınırlandı.

---

### 1.0-1.5  (n=317)
Score=0.4329 | Final Multiplier = **0.8x**

• PF (2.091) -> norm=0.36
✓ Sharpe (0.2453) -> norm=0.61
✗ MaxDD (2.816%) -> norm=0.34
✗ Confidence(n) (317) -> norm=0.32
✓ PE (bonus) (57.41%) -> norm=0.58

---

### 1.5-2.0  (n=538)
Score=0.7257 | Final Multiplier = **1.2x**

✓ PF (3.178) -> norm=0.73
✓ Sharpe (0.3502) -> norm=0.88
✓ MaxDD (1.868%) -> norm=0.61
• Confidence(n) (538) -> norm=0.54
✓ PE (bonus) (60.59%) -> norm=0.69
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 2.0-3.0  (n=1208)
Score=0.7562 | Final Multiplier = **1.2x**

✓ PF (3.099) -> norm=0.70
✓ Sharpe (0.3201) -> norm=0.80
✓ MaxDD (1.464%) -> norm=0.72
✓ Confidence(n) (1208) -> norm=1.00
✓ PE (bonus) (58.03%) -> norm=0.60
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=1075)
Score=0.9293 | Final Multiplier = **1.5x**

✓ PF (3.996) -> norm=1.00
✓ Sharpe (0.3774) -> norm=0.94
✓ MaxDD (1.328%) -> norm=0.76
✓ Confidence(n) (1075) -> norm=1.00
✓ PE (bonus) (61.21%) -> norm=0.71
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=800)
Score=0.9554 | Final Multiplier = **1.5x**

✓ PF (6.544) -> norm=1.00
✓ Sharpe (0.436) -> norm=1.00
✓ MaxDD (0.847%) -> norm=0.90
✓ Confidence(n) (800) -> norm=0.80
✓ PE (bonus) (65.38%) -> norm=0.85
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## UNIUSDT

### 0.0-1.0  (n=0)
Score=0.0 | Final Multiplier = **0.0x**

Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)

---

### 1.0-1.5  (n=1033)
Score=0.3168 | Final Multiplier = **0.5x**

✗ PF (1.653) -> norm=0.22
• Sharpe (0.1542) -> norm=0.39
✗ MaxDD (4.891%) -> norm=0.00
✓ Confidence(n) (1033) -> norm=1.00
• PE (bonus) (54.11%) -> norm=0.47

---

### 1.5-2.0  (n=921)
Score=0.6017 | Final Multiplier = **1.0x**

• PF (2.463) -> norm=0.49
✓ Sharpe (0.2575) -> norm=0.64
✓ MaxDD (1.746%) -> norm=0.64
✓ Confidence(n) (921) -> norm=0.92
• PE (bonus) (55.81%) -> norm=0.53

---

### 2.0-3.0  (n=1196)
Score=0.7977 | Final Multiplier = **1.2x**

✓ PF (3.422) -> norm=0.81
✓ Sharpe (0.3386) -> norm=0.85
✓ MaxDD (1.849%) -> norm=0.61
✓ Confidence(n) (1196) -> norm=1.00
✓ PE (bonus) (60.2%) -> norm=0.67
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=612)
Score=0.6725 | Final Multiplier = **1.2x**

✓ PF (2.823) -> norm=0.61
✓ Sharpe (0.3415) -> norm=0.85
✓ MaxDD (1.914%) -> norm=0.60
✓ Confidence(n) (612) -> norm=0.61
✓ PE (bonus) (58.17%) -> norm=0.61
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=299)
Score=0.6675 | Final Multiplier = **1.2x**

✓ PF (3.509) -> norm=0.84
✓ Sharpe (0.3188) -> norm=0.80
✗ MaxDD (2.988%) -> norm=0.29
✗ Confidence(n) (299) -> norm=0.30
✓ PE (bonus) (58.19%) -> norm=0.61
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

## XRPUSDT

### 0.0-1.0  (n=1061)
Score=0.1221 | Final Multiplier = **0.0x**

✗ PF (0.972) -> norm=0.00
✗ Sharpe (-0.0134) -> norm=0.00
✗ MaxDD (27.159%) -> norm=0.00
✓ Confidence(n) (1061) -> norm=1.00
• PE (bonus) (53.25%) -> norm=0.44

---

### 1.0-1.5  (n=945)
Score=0.3053 | Final Multiplier = **0.5x**

✗ PF (1.593) -> norm=0.20
• Sharpe (0.1528) -> norm=0.38
✗ MaxDD (5.166%) -> norm=0.00
✓ Confidence(n) (945) -> norm=0.94
• PE (bonus) (55.98%) -> norm=0.53

---

### 1.5-2.0  (n=569)
Score=0.168 | Final Multiplier = **0.0x**

✗ PF (1.289) -> norm=0.10
✗ Sharpe (0.0825) -> norm=0.21
✗ MaxDD (9.536%) -> norm=0.00
✓ Confidence(n) (569) -> norm=0.57
✗ PE (bonus) (49.56%) -> norm=0.32

---

### 2.0-3.0  (n=712)
Score=0.5749 | Final Multiplier = **1.0x**

✓ PF (3.016) -> norm=0.67
✓ Sharpe (0.2687) -> norm=0.67
✗ MaxDD (3.611%) -> norm=0.11
✓ Confidence(n) (712) -> norm=0.71
✓ PE (bonus) (56.74%) -> norm=0.56
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 3.0-5.0  (n=429)
Score=0.7829 | Final Multiplier = **1.2x**

✓ PF (3.806) -> norm=0.94
✓ Sharpe (0.347) -> norm=0.87
• MaxDD (2.182%) -> norm=0.52
• Confidence(n) (429) -> norm=0.43
✓ PE (bonus) (60.37%) -> norm=0.68
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---

### 5.0-999.0  (n=159)
Score=0.7565 | Final Multiplier = **1.2x**

✓ PF (3.716) -> norm=0.91
✓ Sharpe (0.4021) -> norm=1.00
• MaxDD (2.696%) -> norm=0.37
✗ Confidence(n) (159) -> norm=0.16
✓ PE (bonus) (61.64%) -> norm=0.72
→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.

---
