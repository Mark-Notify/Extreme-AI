from typing import Dict, Optional

import pandas as pd

from .config import settings
from .rule_based import compute_rule_based_prob
from .lstm_model import ExtremeLSTM
from .regime import detect_regime


class ExtremeAIEngine:
    """
    รวม Rule-based + LSTM เป็น AI Engine ตัวเดียว
    """

    def __init__(self):
        self.lstm = ExtremeLSTM()
        self.lstm_enabled = self.lstm.load(settings.LSTM_MODEL_PATH)
        if self.lstm_enabled:
            print(f"[AI] LSTM loaded from {settings.LSTM_MODEL_PATH}")
        else:
            print("[AI] LSTM model not found, using Rule-based only.")

    def compute_ai(self, df: pd.DataFrame) -> Dict:
        regime = detect_regime(df)

        # --- Rule-based ---
        rb = compute_rule_based_prob(df)
        prob_up_rb = rb["prob_up"]
        prob_down_rb = rb["prob_down"]

        # --- LSTM (ถ้ามีโมเดล) ---
        prob_up_lstm: Optional[float] = None
        if self.lstm_enabled:
            prob_up_lstm = self.lstm.predict_prob(df)

        # --- รวมผล: LSTM 70% + Rule-based 30% ถ้ามี LSTM ---
        if prob_up_lstm is not None:
            raw_prob_up = 0.7 * float(prob_up_lstm) + 0.3 * float(prob_up_rb)
        else:
            raw_prob_up = float(prob_up_rb)

        # ========== ขยายความต่างจาก 0.5 ให้ชัดขึ้น ==========
        # เดิม: prob มักจะลอยแถว ๆ 0.5 → ดูแล้วไม่มั่นใจ
        # เราจะทำแบบนี้:
        #   delta = raw_prob_up - 0.5
        #   amplified_delta = delta * 3.0
        #   prob_up = 0.5 + amplified_delta
        # แล้วค่อย clamp ให้อยู่ใน [0.05, 0.95]
        # ผลคือ:
        #   - ถ้า raw_prob_up 0.52 → กลายเป็น ~0.56
        #   - ถ้า raw_prob_up 0.60 → กลายเป็น ~0.80
        #   - ถ้า raw_prob_up 0.40 → กลายเป็น ~0.20
        delta = raw_prob_up - 0.5
        amplified_delta = delta * 3.0  # อยากแรงกว่านี้ก็เพิ่ม factor ได้ เช่น 4.0
        prob_up = 0.5 + amplified_delta

        # กันสุดขอบไม่ให้สุดโต่งเกินไป
        if prob_up < 0.05:
            prob_up = 0.05
        elif prob_up > 0.95:
            prob_up = 0.95

        prob_down = 1.0 - prob_up

        ai_dir = "UP" if prob_up > 0.5 else "DOWN"
        ai_conf = abs(prob_up - 0.5) * 2.0  # map 0.5 → 0, 0/1 → 1

        return {
            "prob_up": float(prob_up),
            "prob_down": float(prob_down),
            "direction": ai_dir,
            "confidence": float(ai_conf),
            "regime": regime,
            "rule_based": rb,
            "use_lstm": self.lstm_enabled and prob_up_lstm is not None,
            "prob_up_lstm": float(prob_up_lstm) if prob_up_lstm is not None else None,
            "raw_prob_up": float(raw_prob_up),  # ไว้ debug ดูค่าก่อนขยาย
        }
