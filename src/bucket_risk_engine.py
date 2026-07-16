"""
bucket_risk_engine.py
======================
CBDR_RISK_MATRIX bucket'ları için mutlak (coin-içi normalizasyon YAPMAYAN)
composite-score tabanlı risk multiplier motoru.

GİRDİ FORMATI (bucket_data.json):
---------------------------------
Her bucket için backtest çıktından şu alanları içeren bir liste bekliyor:

[
  {
    "symbol": "GMXUSDT",
    "session": "REAL_CBDR",
    "bucket_low": 0.0,
    "bucket_high": 1.0,
    "n": 612,
    "pf": 3.8,
    "sharpe": 0.34,
    "max_dd_pct": 0.6,
    "pe_pct": 62.0
  },
  ...
]

Bu dosyayı kendi backtest raporlama script'inden (calc.py / analyzer_v5.py
çıktısından) üretip bu script ile aynı klasöre koy.

Bu script SADECE hesaplama/rapor/config üretimini yapar; backtest'i
KENDİSİ ÇALIŞTIRMAZ.

ÇIKTI:
------
1. config_backup_pre_v2.py   -> mevcut config.py'nin yedeği (varsa)
2. cbdr_risk_matrix_v2.py    -> yeni CBDR_RISK_MATRIX bloğu (config.py'ye
                                  yapıştırılmaya hazır, geçerli Python sözdizimi)
3. bucket_risk_report.md     -> her bucket için gerekçeli, açıklanabilir rapor
4. bucket_score_comparison.csv -> eski vs yeni multiplier karşılaştırma tablosu
   (eski multiplier verilmişse)

Kullanım:
    python3 bucket_risk_engine.py bucket_data.json [eski_config.py]
"""

from __future__ import annotations

import json
import sys
import re
import csv
from pathlib import Path
from datetime import datetime, timezone

# ──────────────────────────────────────────────────────────────────────────
# 1. SABİT ÇAPA NOKTALARI (mutlak referanslar — coin-içi normalizasyon YOK)
# ──────────────────────────────────────────────────────────────────────────

ANCHORS = {
    "pf_floor": 1.0,      # PF<=1.0  -> norm 0 (breakeven veya kayıp)
    "pf_ceil": 4.0,       # PF>=4.0  -> norm 1 (doygunluk)
    "sharpe_ceil": 0.40,  # Sharpe>=0.40 -> norm 1
    "dd_floor_pct": 0.5,  # MaxDD<=%0.5 -> norm 1 (en iyi)
    "dd_ceil_pct": 4.0,   # MaxDD>=%4.0 -> norm 0 (en kötü)
    "conf_ceil_n": 1000,  # n>=1000 -> norm 1 (tam güven)
    "pe_floor_pct": 40.0, # PE<=%40 -> norm 0
    "pe_ceil_pct": 70.0,  # PE>=%70 -> norm 1
}

WEIGHTS = {
    "pf": 0.41,
    "sharpe": 0.27,
    "dd": 0.17,
    "conf": 0.10,
    "pe": 0.05,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Ağırlıklar toplamı 1.0 olmalı"

# Composite score -> ham multiplier
SCORE_TO_MULT = [
    (0.80, 1.5),
    (0.65, 1.2),
    (0.50, 1.0),
    (0.35, 0.8),
    (0.20, 0.5),
    (0.00, 0.0),
]

# PF gate: sert tavan (composite skordan bağımsız, PF tek başına belirler)
PF_GATE = [
    (2.5, None),   # PF>=2.5 -> tavan yok
    (1.8, 1.2),    # 1.8<=PF<2.5 -> tavan 1.2x
    (1.3, 0.8),    # 1.3<=PF<1.8 -> tavan 0.8x
    (0.0, 0.0),    # PF<1.3 -> tavan 0.0x
]

SAFETY_MIN_N = 100      # n<100 ise mult her koşulda <=1.0x
SAFETY_CAP = 1.0

VALID_MULTS = [0.0, 0.5, 0.8, 1.0, 1.2, 1.5]


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def snap_to_valid(mult: float) -> float:
    """En yakın geçerli multiplier basamağına yuvarla (aşağı yönlü, muhafazakâr)."""
    candidates = [m for m in VALID_MULTS if m <= mult + 1e-9]
    return max(candidates) if candidates else 0.0


# ──────────────────────────────────────────────────────────────────────────
# 2. NORMALİZASYON FONKSİYONLARI
# ──────────────────────────────────────────────────────────────────────────

def normalize(bucket: dict) -> dict:
    pf = bucket["pf"]
    sharpe = bucket["sharpe"]
    dd = bucket["max_dd_pct"]
    n = bucket["n"]
    pe = bucket.get("pe_pct", 50.0)

    pf_norm = clip((pf - ANCHORS["pf_floor"]) / (ANCHORS["pf_ceil"] - ANCHORS["pf_floor"]))
    sharpe_norm = clip(sharpe / ANCHORS["sharpe_ceil"])
    dd_norm = clip(1 - (dd - ANCHORS["dd_floor_pct"]) / (ANCHORS["dd_ceil_pct"] - ANCHORS["dd_floor_pct"]))
    conf_norm = clip(n / ANCHORS["conf_ceil_n"])
    pe_norm = clip((pe - ANCHORS["pe_floor_pct"]) / (ANCHORS["pe_ceil_pct"] - ANCHORS["pe_floor_pct"]))

    return {
        "pf_norm": pf_norm,
        "sharpe_norm": sharpe_norm,
        "dd_norm": dd_norm,
        "conf_norm": conf_norm,
        "pe_norm": pe_norm,
    }


def composite_score(norms: dict) -> float:
    return (
        WEIGHTS["pf"] * norms["pf_norm"]
        + WEIGHTS["sharpe"] * norms["sharpe_norm"]
        + WEIGHTS["dd"] * norms["dd_norm"]
        + WEIGHTS["conf"] * norms["conf_norm"]
        + WEIGHTS["pe"] * norms["pe_norm"]
    )


def score_to_mult(score: float) -> float:
    for threshold, mult in SCORE_TO_MULT:
        if score >= threshold:
            return mult
    return 0.0


def pf_gate_cap(pf: float):
    for threshold, cap in PF_GATE:
        if pf >= threshold:
            return cap  # None = tavan yok
    return 0.0


def _zero_bucket_result():
    return {
        "norms": {k: 0.0 for k in ["pf_norm", "sharpe_norm", "dd_norm", "conf_norm", "pe_norm"]},
        "score": 0.0,
        "composite_mult": 0.0,
        "gate_cap": 0.0,
        "gated_mult": 0.0,
        "safety_applied": False,
        "final_mult": 0.0,
    }


def compute_final_mult(bucket: dict):
    if bucket["n"] == 0:
        return _zero_bucket_result()
    norms = normalize(bucket)
    score = composite_score(norms)
    composite_mult = score_to_mult(score)

    gate_cap = pf_gate_cap(bucket["pf"])
    gated_mult = composite_mult if gate_cap is None else min(composite_mult, gate_cap)

    safety_applied = bucket["n"] < SAFETY_MIN_N
    final_mult = min(gated_mult, SAFETY_CAP) if safety_applied else gated_mult
    final_mult = snap_to_valid(final_mult)

    return {
        "norms": norms,
        "score": round(score, 4),
        "composite_mult": composite_mult,
        "gate_cap": gate_cap,
        "gated_mult": gated_mult,
        "safety_applied": safety_applied,
        "final_mult": final_mult,
    }


# ──────────────────────────────────────────────────────────────────────────
# 3. GEREKÇE ÜRETİMİ (explainability)
# ──────────────────────────────────────────────────────────────────────────

def reason_lines(bucket: dict, result: dict) -> list:
    if bucket["n"] == 0:
        return ["Bucket'ta hic trade yok (n=0) -> multiplier 0.0x (guvenli varsayilan)"]
    norms = result["norms"]
    lines = []

    def tick_or_cross(label, norm_val, raw_val, unit=""):
        mark = "✓" if norm_val >= 0.55 else ("✗" if norm_val < 0.35 else "•")
        lines.append(f"{mark} {label} ({raw_val}{unit}) -> norm={norm_val:.2f}")

    tick_or_cross("PF", norms["pf_norm"], bucket["pf"])
    tick_or_cross("Sharpe", norms["sharpe_norm"], bucket["sharpe"])
    tick_or_cross("MaxDD", norms["dd_norm"], bucket["max_dd_pct"], "%")
    tick_or_cross("Confidence(n)", norms["conf_norm"], bucket["n"])
    tick_or_cross("PE (bonus)", norms["pe_norm"], bucket.get("pe_pct", 50.0), "%")

    if result["gate_cap"] is not None and result["gated_mult"] < result["composite_mult"]:
        lines.append(
            f"→ PF Gate devrede: PF={bucket['pf']} tavanı {result['gate_cap']}x'e çekti "
            f"(composite skor {result['composite_mult']}x öneriyordu, gate kazandı)."
        )
    elif result["gate_cap"] is None:
        lines.append("→ PF Gate açık (PF>=2.5), tavan sınırlaması yok.")

    if result["safety_applied"]:
        lines.append(
            f"→ Güvenlik kilidi devrede: n={bucket['n']} < {SAFETY_MIN_N}, "
            f"multiplier {SAFETY_CAP}x ile sınırlandı."
        )

    return lines


# ──────────────────────────────────────────────────────────────────────────
# 4. RAPOR ÜRETİMİ
# ──────────────────────────────────────────────────────────────────────────

def build_report(buckets_with_results: list) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [
        "# Bucket Risk Multiplier Raporu (v2 — composite score + PF gate)",
        f"_Üretim zamanı: {ts}_",
        "",
        "Metodoloji: mutlak sabit çapa noktaları (coin-içi min-max YOK), "
        "PF hem ağırlıklı bileşen hem de sert tavan (gate) olarak kullanılıyor, "
        "n<100 için ek güvenlik kilidi var.",
        "",
        "---",
        "",
    ]

    current_symbol = None
    for bucket, result in buckets_with_results:
        if bucket["symbol"] != current_symbol:
            current_symbol = bucket["symbol"]
            out.append(f"## {current_symbol}")
            out.append("")

        out.append(f"### {bucket['bucket_low']}-{bucket['bucket_high']}  (n={bucket['n']})")
        out.append(f"Score={result['score']} | Final Multiplier = **{result['final_mult']}x**")
        out.append("")
        for line in reason_lines(bucket, result):
            out.append(line)
        out.append("")
        out.append("---")
        out.append("")

    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────
# 5. CONFIG.PY BLOĞU ÜRETİMİ
# ──────────────────────────────────────────────────────────────────────────

def build_config_block(buckets_with_results: list[tuple[dict, dict]]) -> str:
    by_symbol: dict[str, list[tuple[dict, dict]]] = {}
    for bucket, result in buckets_with_results:
        by_symbol.setdefault(bucket["symbol"], []).append((bucket, result))

    lines = [
        "# ── CBDR Risk Matrisi v2 (composite score + PF gate ile üretildi) ──",
        f"# Üretim zamanı: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "# Metodoloji: mutlak sabit çapa (coin-içi normalizasyon yok),",
        "# PF hem ağırlık hem sert gate, n<100 güvenlik kilidi.",
        "# Gerekçeler için bkz: bucket_risk_report.md",
        "",
        "CBDR_RISK_MATRIX: dict[str, dict] = {",
    ]

    for symbol, items in by_symbol.items():
        session = items[0][0].get("session", "DEFAULT")
        lines.append(f'    "{symbol}": {{')
        lines.append(f'        "session": "{session}",')
        lines.append('        "weekend_bonus": False,')
        lines.append('        "weekend_mult": 1.0,')
        lines.append('        "buckets": [')
        for bucket, result in items:
            lines.append(
                f"            ({bucket['bucket_low']}, {bucket['bucket_high']}, "
                f"{result['final_mult']}),  "
                f"# n={bucket['n']} PF={bucket['pf']} Sharpe={bucket['sharpe']} "
                f"MaxDD={bucket['max_dd_pct']}% Score={result['score']}"
            )
        lines.append("        ],")
        lines.append("    },")

    lines.append("}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# 6. ESKİ vs YENİ KARŞILAŞTIRMA (opsiyonel — eski config.py verilirse)
# ──────────────────────────────────────────────────────────────────────────

def parse_old_multipliers(old_config_path: str) -> dict:
    """
    Eski config.py içindeki CBDR_RISK_MATRIX'ten (symbol, low, high) -> eski_mult
    çıkarır. Basit regex tabanlı bir parser; config.py'nin format değiştirmediği
    varsayılır.
    """
    text = Path(old_config_path).read_text(encoding="utf-8")
    result = {}
    current_symbol = None
    for line in text.splitlines():
        sym_match = re.match(r'\s*"([A-Z0-9]+USDT)":\s*\{', line)
        if sym_match:
            current_symbol = sym_match.group(1)
            continue
        bucket_match = re.match(
            r"\s*\(([\d.]+),\s*([\d.]+),\s*([\d.]+)\)", line
        )
        if bucket_match and current_symbol:
            low, high, mult = bucket_match.groups()
            result[(current_symbol, float(low), float(high))] = float(mult)
    return result


def build_comparison_csv(buckets_with_results: list[tuple[dict, dict]], old_mults: dict, out_path: str):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "symbol", "bucket_low", "bucket_high", "n", "pf", "sharpe",
            "max_dd_pct", "old_mult", "new_mult", "delta"
        ])
        rows = []
        for bucket, result in buckets_with_results:
            key = (bucket["symbol"], bucket["bucket_low"], bucket["bucket_high"])
            old = old_mults.get(key)
            new = result["final_mult"]
            delta = (new - old) if old is not None else None
            rows.append((bucket, result, old, new, delta))

        # en çok değişenler üstte
        rows.sort(key=lambda r: abs(r[4]) if r[4] is not None else -1, reverse=True)

        for bucket, result, old, new, delta in rows:
            writer.writerow([
                bucket["symbol"], bucket["bucket_low"], bucket["bucket_high"],
                bucket["n"], bucket["pf"], bucket["sharpe"], bucket["max_dd_pct"],
                old if old is not None else "N/A", new,
                round(delta, 2) if delta is not None else "N/A",
            ])


# ──────────────────────────────────────────────────────────────────────────
# 7. MAIN
# ──────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python3 bucket_risk_engine.py bucket_data.json [eski_config.py]")
        sys.exit(1)

    data_path = sys.argv[1]
    old_config_path = sys.argv[2] if len(sys.argv) > 2 else None

    buckets = json.loads(Path(data_path).read_text(encoding="utf-8"))

    buckets_with_results = []
    for bucket in buckets:
        result = compute_final_mult(bucket)
        buckets_with_results.append((bucket, result))

    out_dir = Path(".")

    # 1) Rapor
    report_text = build_report(buckets_with_results)
    (out_dir / "bucket_risk_report.md").write_text(report_text, encoding="utf-8")

    # 2) Config bloğu
    config_block = build_config_block(buckets_with_results)
    (out_dir / "cbdr_risk_matrix_v2.py").write_text(config_block, encoding="utf-8")

    # 3) Eski config yedeği + karşılaştırma
    if old_config_path:
        backup_path = out_dir / "config_backup_pre_v2.py"
        backup_path.write_text(Path(old_config_path).read_text(encoding="utf-8"), encoding="utf-8")

        old_mults = parse_old_multipliers(old_config_path)
        build_comparison_csv(buckets_with_results, old_mults, str(out_dir / "bucket_score_comparison.csv"))
        print(f"Yedek alındı: {backup_path}")
        print(f"Karşılaştırma: bucket_score_comparison.csv")

    print(f"Rapor: bucket_risk_report.md ({len(buckets)} bucket)")
    print(f"Config bloğu: cbdr_risk_matrix_v2.py")
    print("NOT: Bu blok mevcut config.py'deki CBDR_RISK_MATRIX'in YERİNE elle "
          "yapıştırılmalı — script config.py'yi otomatik overwrite ETMEZ, "
          "kontrolsüz değişikliği önlemek için.")


if __name__ == "__main__":
    main()
