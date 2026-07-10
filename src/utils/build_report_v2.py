"""build_report_v2.py — crash log almali rapor builder"""

import os
import sys
import pickle
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src"))
sys.path.insert(0, os.path.dirname(__file__))
os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(
    os.path.dirname(__file__), "..", "output"
)

from fvg_profile_v5 import build_report

dump = os.path.join(os.path.dirname(__file__), "..", "reports", "_v5_dump.pkl")
md = os.path.join(os.path.dirname(__file__), "..", "reports", "fvg_profile_v5.md")

with open(dump, "rb") as f:
    data = pickle.load(f)
print(
    f"Yuklendi: {len(data['all_coin_data'])} coin, {len(data['results_data'])} result",
    flush=True,
)

try:
    with open(md, "w", encoding="utf-8") as f:
        build_report(data["all_coin_data"], data["results_data"], f)
    sz = os.path.getsize(md)
    print(f"TAMAM: {sz:,} bytes", flush=True)
except Exception:
    with open(
        os.path.join(os.path.dirname(__file__), "..", "reports", "_v5_crash.log"), "w"
    ) as ef:
        traceback.print_exc(file=ef)
    print("CRASH — log reports/_v5_crash.log", flush=True)
