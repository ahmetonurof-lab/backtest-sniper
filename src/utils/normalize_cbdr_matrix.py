"""
normalize_cbdr_matrix.py — n<100 trade'li CBDR bucket'larını 1.0x'e çeker.

1. reports/cbdr_{session}_report.md dosyalarını parse eder
2. Her coin/session/bucket için trade sayısını (n) çıkarır
3. config.py'deki CBDR_RISK_MATRIX'te n<100 olan bucket'ların
   multiplier'ını 1.0 yapar
4. config.py'yi günceller ve değişiklik özetini basar
"""

import re
import os
import shutil

BACKTEST_DIR = os.path.dirname(os.path.abspath(__file__))
SNIPER_CONFIG = os.path.join(BACKTEST_DIR, "..", "..", "sniper", "src", "config.py")

REPORTS = {
    "DEFAULT": os.path.join(BACKTEST_DIR, "..", "reports", "cbdr_default_report.md"),
    "ASIA_RANGE": os.path.join(
        BACKTEST_DIR, "..", "reports", "cbdr_asia_range_report.md"
    ),
    "REAL_CBDR": os.path.join(
        BACKTEST_DIR, "..", "reports", "cbdr_real_cbdr_report.md"
    ),
}

BUCKET_LABEL_MAP = {
    "0-1%": (0.0, 1.0),
    "1-1.5%": (1.0, 1.5),
    "1.5-2%": (1.5, 2.0),
    "2-3%": (2.0, 3.0),
    "3-5%": (3.0, 5.0),
    ">5%": (5.0, 999.0),
}

SESSION_MAP = {
    "DEFAULT": "cbdr_default_report.md",
    "ASIA_RANGE": "cbdr_asia_range_report.md",
    "REAL_CBDR": "cbdr_real_cbdr_report.md",
}


def parse_report(filepath):
    """Parse CBDR markdown raporu, döndür: {coin: {bucket_label: n}}"""
    if not os.path.isfile(filepath):
        print(f"  Rapor bulunamadi: {filepath}")
        return {}
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
    result = {}
    # Her coin bir ### header ile baslar
    coin_blocks = re.split(r"\n### ", text)
    for block in coin_blocks:
        if not block.strip():
            continue
        lines = block.strip().split("\n")
        coin = lines[0].strip()
        # Sadece USDT ile biten coinleri al
        if not coin.endswith("USDT"):
            continue
        # Tabloyu bul (| ile baslayan satirlar)
        table_start = None
        table_rows = []
        for i, line in enumerate(lines):
            if line.startswith("| CBDR% Araligi") or line.startswith("| CBDR% Aralığı"):
                table_start = i
                break
        if table_start is not None:
            for line in lines[table_start + 2 :]:
                if not line.startswith("|"):
                    break
                table_rows.append(line)
        coin_data = {}
        for row in table_rows:
            cols = [c.strip() for c in row.split("|")[1:-1]]
            if len(cols) >= 7:
                bucket_label = cols[0]
                n_str = cols[2].replace(",", "").replace(" ", "")
                try:
                    n = int(n_str)
                except ValueError:
                    continue
                coin_data[bucket_label] = n
        if coin_data:
            result[coin] = coin_data
    return result


def buckets_near(a, b, eps=0.001):
    """Compare two (lo, hi) tuples allowing slight float differences."""
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def find_config_coin_bounds(text, coin_key, session):
    """Find the start and end line indices for a coin's entry in config text."""
    pattern = re.compile(r'^\s*"' + re.escape(coin_key) + r'":\s*\{')
    start = None
    depth = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if start is None:
            if pattern.search(line):
                # Verify session matches
                for j in range(i, min(i + 10, len(lines))):
                    if '"session"' in lines[j] and session in lines[j]:
                        start = i
                        break
            if start is not None:
                depth = 1
                continue
        if start is not None:
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                return start, i + 1
    return None, None


def modify_config():
    """config.py'de n<100 olan bucket'ları 1.0x yap."""
    with open(SNIPER_CONFIG, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    modified_lines = list(lines)

    changes = []

    # Her session'daki her coin için
    for session, fpath in SESSION_MAP.items():
        report = parse_report(
            os.path.join(os.path.dirname(BACKTEST_DIR), "reports", fpath)
        )
        if not report:
            report = parse_report(os.path.join(BACKTEST_DIR, "..", "reports", fpath))
        if not report:
            print(f"  [!] {session} raporu okunamadi, atlaniyor.")
            continue

        # Config'de bu session'daki coinleri bul
        for coin_key in list(report.keys()):
            start, end = None, None
            for i, line in enumerate(lines):
                if f'"{coin_key}"' in line and "{" in line:
                    # Check if this is inside CBDR_RISK_MATRIX and session matches
                    for j in range(i, min(i + 10, len(lines))):
                        if '"session"' in lines[j] and session in lines[j]:
                            start = i
                            break
                    if start is not None:
                        depth = 0
                        for k in range(start, len(lines)):
                            depth += lines[k].count("{") - lines[k].count("}")
                            if depth <= 0:
                                end = k + 1
                                break
                        break

            if start is None:
                # Coin config'te yok veya farkli session'da, atla
                continue

            coin_report = report.get(coin_key, {})
            # Her bucket satirini kontrol et
            for line_idx in range(start, end):
                line = lines[line_idx]
                # (lo, hi, mult) pattern
                m = re.match(
                    r"^\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\).*",
                    line,
                )
                if not m:
                    continue
                lo = float(m.group(1))
                hi = float(m.group(2))
                cur_mult = float(m.group(3))

                # Hangi bucket label'a karsilik geldigini bul
                bucket_label = None
                for label, (blo, bhi) in BUCKET_LABEL_MAP.items():
                    if buckets_near((lo, hi), (blo, bhi)):
                        bucket_label = label
                        break
                if bucket_label is None:
                    # Normalize (int vs float edge case)
                    for label, (blo, bhi) in BUCKET_LABEL_MAP.items():
                        if abs(lo - blo) < 0.01 and abs(hi - bhi) < 0.01:
                            bucket_label = label
                            break

                if bucket_label is None:
                    continue

                n = coin_report.get(bucket_label, 0)

                if n < 100 and cur_mult != 1.0:
                    # degistir
                    old_line = lines[line_idx]
                    # Replace the mult value
                    new_line = re.sub(
                        r"(\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*)[\d.]+(\s*\))",
                        r"\g<1>1.0\g<2>",
                        old_line,
                    )
                    # Add comment about the change
                    if "#" in new_line:
                        new_line = re.sub(r"(#.*)", r"\1 (n<100 -> 1.0x)", new_line)
                    else:
                        new_line = new_line.rstrip() + "  # n<100 -> 1.0x"
                    modified_lines[line_idx] = new_line
                    changes.append(
                        f"  {coin_key:>10s} [{session:>12s}] {bucket_label:>8s}: "
                        f"{cur_mult:.1f}x -> 1.0x  (n={n})"
                    )

    if not changes:
        print("\n  Degisiklik yok. Tüm n<100 bucket'lar zaten 1.0x.")
        return

    # Yedek al
    backup = SNIPER_CONFIG + ".bak"
    shutil.copy2(SNIPER_CONFIG, backup)
    print(f"  Yedek: {backup}")

    # Yaz
    with open(SNIPER_CONFIG, "w", encoding="utf-8") as f:
        f.write("\n".join(modified_lines))

    print(f"\n  === DEGISIKLIK ÖZETI ({len(changes)} hücre) ===\n")
    for c in changes:
        print(c)
    print("\n  config.py güncellendi.")


if __name__ == "__main__":
    # Raporlari parse et
    print("n<100 CBDR bucket'larini 1.0x'e normalize ediyorum...\n")
    for session, fpath in SESSION_MAP.items():
        report_path = os.path.join(BACKTEST_DIR, "..", "reports", fpath)
        data = parse_report(report_path)
        total_buckets = sum(len(v) for v in data.values())
        print(f"  {session:>12s}: {len(data)} coin, {total_buckets} bucket okundu")
    print()
    modify_config()
