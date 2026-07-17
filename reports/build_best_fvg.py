import os

base = os.path.dirname(os.path.abspath(__file__))
sessions = ["REAL_CBDR", "DEFAULT", "ASIA_RANGE"]
coins = {}

for s in sessions:
    fp = os.path.join(base, f"fvg_profile_{s}.md")
    with open(fp, encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 4 and parts[0].endswith("USDT"):
                try:
                    coin = parts[0]
                    fvg = float(parts[1])
                    score = int(parts[2])
                except ValueError:
                    continue
                if coin not in coins or score > coins[coin]["score"]:
                    coins[coin] = {"session": s, "fvg": fvg, "score": score}

lines = [
    "# The Best FVG — Per-Coin Best Session",
    "",
    "| Coin | Best Session | FVG Size | Score |",
    "|------|-------------|----------|-------|",
]
for coin in sorted(coins):
    c = coins[coin]
    lines.append(
        f'| {coin:<8} | {c["session"]:<12} | {c["fvg"]:.3f} | {c["score"]:>5} |'
    )

lines += [
    "",
    "```python",
    "# FVG_SIZE_MAP — Best of All Sessions",
    "FVG_SIZE_MAP: dict[str, float] = {",
]
for coin in sorted(coins):
    c = coins[coin]
    lines.append(
        f'    "{coin}": {c["fvg"]:.3f},  # [{c["session"]}] score={c["score"]}'
    )
lines += ["}", "```"]

out = os.path.join(base, "the_best_fvg.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Yazildi: {out}")
print(f"Coin: {len(coins)}")
