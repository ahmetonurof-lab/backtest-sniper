import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from session_router import get_session_hours

for s in ["BTCUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]:
    h = get_session_hours(s)
    print(f"{s}: session={h}")
