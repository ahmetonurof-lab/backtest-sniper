"""
quant_logger.py — Parquet tabanli trade logger.
Buffer (bellek) mantigiyla calisir: her islemde diske yazmaz,
test bitince tek seferde yuksek sikistirmayla .parquet dosyasina gomer.

Kullanim:
  logger = QuantLogger("reports/trades.parquet")
  logger.log_trade({...})   # her trade kapanisinda
  logger.save_and_clear()    # test sonunda
"""
import os
import pandas as pd
from datetime import datetime


class QuantLogger:
    """Buffer'li Parquet logger — backtest trade'lerini toplu kaydeder."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.buffer = []

    def log_trade(self, trade_data: dict):
        """Backtest motoru her trade kapandiginda cagirir."""
        self.buffer.append(trade_data)

    def save_and_clear(self):
        """Buffer'daki veriyi Parquet'e yazar ve bellegi temizler."""
        if not self.buffer:
            print("  [QuantLogger] Kaydedilecek islem yok.")
            return

        df = pd.DataFrame(self.buffer)

        # Zorunlu alanlari kontrol et
        required_cols = ["symbol", "session", "side", "entry_time",
                         "entry_price", "exit_price", "result",
                         "final_pnl_usd", "risk_usd"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = None

        # --- OTOMATIK METRIK HESAPLARI ---

        # 1. Reel Nakit Akisi (senin "gizli karli stop" metrigin)
        if "final_pnl_usd" in df.columns:
            df["is_cashflow_positive"] = df["final_pnl_usd"] > 0.0

        # 2. R-Multiple (motor hesaplamadiysa)
        if "r_multiple" not in df.columns and "final_pnl_usd" in df.columns and "risk_usd" in df.columns:
            df["r_multiple"] = df.apply(
                lambda row: row["final_pnl_usd"] / row["risk_usd"]
                if row["risk_usd"] not in (0, None) and pd.notna(row["risk_usd"])
                else 0.0,
                axis=1,
            )

        # 3. Trailing etiketi
        if "trailing_count" in df.columns:
            df["trail_category"] = df["trailing_count"].apply(
                lambda tc: "SL-" if tc == 0 else ("SL1" if tc == 1 else "SL2+")
            )

        # --- DOSYAYA YAZ ---
        if os.path.exists(self.filepath):
            existing_df = pd.read_parquet(self.filepath)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_parquet(self.filepath, engine="pyarrow", compression="snappy", index=False)
        n = len(self.buffer)
        print(f"  [QuantLogger] {n} islem -> '{self.filepath}' (toplam {len(df)} satir)")
        self.buffer.clear()
