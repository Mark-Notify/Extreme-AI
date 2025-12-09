import os
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def generate_signal_chart(
    df: pd.DataFrame,
    pre_idx: Optional[int],
    confirm_idx: Optional[int],
    save_dir: str = "charts",
    filename_prefix: str = "signal",
) -> Optional[str]:
    """
    วาดกราฟ Close + RSI + MACD (hist) และจุด pre/confirm
    คืน path ของไฟล์ png
    """
    if df.empty:
        return None
    os.makedirs(save_dir, exist_ok=True)

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    # price
    axes[0].plot(df["time"], df["Close"])
    axes[0].set_title("XAUUSD Price")

    if pre_idx is not None and 0 <= pre_idx < len(df):
        axes[0].scatter(df["time"].iloc[pre_idx], df["Close"].iloc[pre_idx], marker="^")
    if confirm_idx is not None and 0 <= confirm_idx < len(df):
        axes[0].scatter(df["time"].iloc[confirm_idx], df["Close"].iloc[confirm_idx], marker="s")

    # RSI
    axes[1].plot(df["time"], df["RSI"])
    axes[1].axhline(30, linestyle="--")
    axes[1].axhline(70, linestyle="--")
    axes[1].set_title("RSI")

    # MACD hist
    axes[2].bar(df["time"], df["MACD_HIST"])
    axes[2].set_title("MACD Histogram")

    plt.tight_layout()
    filename = f"{filename_prefix}_{pd.Timestamp.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(save_dir, filename)
    plt.savefig(path)
    plt.close(fig)
    return path
