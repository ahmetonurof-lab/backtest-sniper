import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src"))

import analyzer_v5 as an

from trading.trailing_manager import TrailingManager
from models import Bar, FVG


def bar(i, o, h, low, c):
    return Bar(
        index=i,
        open=o,
        high=h,
        low=low,
        close=c,
        volume=0.0,
        is_closed=True,
        timestamp=i,
    )


def fvg(dirn, top, bottom, ri):
    return FVG(direction=dirn, top=top, bottom=bottom, real_index=ri, timeframe="15m")


cases = [
    # bullish, far-side tek bar -> continuation (N=1)
    (
        fvg("bullish", 105, 104, 2),
        [
            bar(0, 100, 103, 99, 102),
            bar(1, 101, 104, 100, 102),
            bar(2, 103, 106, 102, 105),
            bar(3, 103, 105, 101, 103),
            bar(4, 106, 109, 105, 107),
        ],
        1,
        "continuation",
    ),
    # bullish, far-side 1 bar sonra gap ici -> retrace (N=2'de)
    (
        fvg("bullish", 105, 104, 2),
        [
            bar(0, 100, 103, 99, 102),
            bar(1, 101, 104, 100, 102),
            bar(2, 103, 106, 102, 105),
            bar(3, 103, 105, 101, 103),
            bar(4, 106, 109, 105, 107),
            bar(5, 104, 106, 103.5, 104.5),
        ],
        2,
        "retrace",
    ),
    # bullish, ard arda 2 far-side -> continuation (N=2)
    (
        fvg("bullish", 105, 104, 2),
        [
            bar(0, 100, 103, 99, 102),
            bar(1, 101, 104, 100, 102),
            bar(2, 103, 106, 102, 105),
            bar(3, 103, 105, 101, 103),
            bar(4, 106, 109, 105, 107),
            bar(5, 107, 110, 106, 108),
        ],
        2,
        "continuation",
    ),
    # bullish invalidation -> None
    (
        fvg("bullish", 105, 104, 2),
        [
            bar(0, 100, 103, 99, 102),
            bar(1, 101, 104, 100, 102),
            bar(2, 103, 106, 102, 105),
            bar(3, 103, 105, 101, 103),
        ],
        1,
        None,
    ),
    # bearish, far-side tek bar -> continuation (N=1)
    (
        fvg("bearish", 99, 98, 1),
        [
            bar(0, 100, 103, 99, 102),
            bar(1, 99, 101, 97, 98),
            bar(2, 96, 98, 93, 95),
            bar(3, 95, 97, 93, 94),
        ],
        1,
        "continuation",
    ),
    # bearish, far-side 2 bar + araya gap ici -> retrace (N=2)
    (
        fvg("bearish", 99, 98, 1),
        [
            bar(0, 100, 103, 99, 102),
            bar(1, 99, 101, 97, 98),
            bar(2, 96, 98, 93, 95),
            bar(3, 95, 97, 93, 94),
            bar(4, 97.5, 99, 96.5, 98.2),
        ],
        2,
        "retrace",
    ),
    # bearish invalidation -> None
    (
        fvg("bearish", 99, 98, 1),
        [bar(0, 100, 103, 99, 102), bar(1, 99, 101, 97, 98), bar(2, 100, 102, 99, 101)],
        1,
        None,
    ),
]

fails = 0
for i, (fvg_obj, bars, n, expected) in enumerate(cases):
    bt = an.fvg_confirm_mode(fvg_obj, bars, n)
    lv = TrailingManager._fvg_confirm_mode(fvg_obj, bars, n)
    ok = bt == expected and lv == expected
    if not ok:
        fails += 1
        print(f"case {i}: backtest={bt} live={lv} expected={expected}")
    else:
        print(f"case {i}: OK ({bt})")

print(
    f"\n{len(cases) - fails}/{len(cases)} parity OK, config K={an.CONT_BUFFER_MULT} N={an.CONT_CONFIRM_BARS}"
)
sys.exit(1 if fails else 0)
