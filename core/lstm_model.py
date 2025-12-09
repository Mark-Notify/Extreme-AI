from typing import Optional, Tuple
import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


class _LSTMNet(nn.Module):
    def __init__(self, input_size: int = 7, hidden_size: int = 64, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        out = self.fc(out)
        return out


class ExtremeLSTM:
    """
    LSTM Model แบบง่าย ๆ
    - input: ลำดับ feature 60 แท่ง (features 7 ตัว)
    - output: ค่า scalar แทนทิศทาง (บวก=ขึ้น / ลบ=ลง)
    """

    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = _LSTMNet().to(self.device)

    def prepare_sequences(
        self,
        df: pd.DataFrame,
        seq_len: int = 60,
    ) -> Tuple[np.ndarray, np.ndarray]:
        feats = df[["Close", "RSI", "MACD", "MACD_HIST", "ATR", "ADX", "RET"]].values
        # label = sign of next return
        y_raw = df["RET"].shift(-1).fillna(0).values
        y_sign = np.sign(y_raw)

        X, y = [], []
        for i in range(len(df) - seq_len - 1):
            X.append(feats[i : i + seq_len])
            y.append(y_sign[i + seq_len])
        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.float32).reshape(-1, 1)
        return X, y

    def fit(self, df: pd.DataFrame, epochs: int = 5, batch_size: int = 32):
        X, y = self.prepare_sequences(df)
        if len(X) == 0:
            print("[LSTM] Not enough data to train.")
            return

        dataset = TensorDataset(torch.tensor(X), torch.tensor(y))
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)

        self.model.train()
        for epoch in range(epochs):
            total_loss = 0.0
            for bx, by in loader:
                bx, by = bx.to(self.device), by.to(self.device)
                optimizer.zero_grad()
                out = self.model(bx)
                loss = criterion(out, by)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            print(f"[LSTM] Epoch {epoch+1}/{epochs}, Loss={total_loss/len(loader):.6f}")

    def predict_prob(self, df: pd.DataFrame, seq_len: int = 60) -> Optional[float]:
        if len(df) < seq_len + 1:
            return None
        feats = df[["Close", "RSI", "MACD", "MACD_HIST", "ATR", "ADX", "RET"]].values
        x = feats[-seq_len:].astype("float32")
        x = torch.tensor(x).unsqueeze(0).to(self.device)
        self.model.eval()
        with torch.no_grad():
            out = self.model(x).item()
        # map scalar -> probability via sigmoid
        prob_up = 1 / (1 + torch.exp(torch.tensor(-out))).item()
        return float(prob_up)

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.model.state_dict(), path)

    def load(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        state = torch.load(path, map_location=self.device)
        self.model.load_state_dict(state)
        return True
