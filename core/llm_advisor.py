# core/llm_advisor.py
"""
LLM Advisor - Uses OpenAI GPT and Google Gemini to analyze trading signals
and provide an additional confirmation layer before executing trades.

Both models are queried independently, then a consensus is derived.
When LLM_REQUIRE_CONSENSUS=true in .env, only trades where both models agree
with the technical AI will be executed, adding a high-quality filter.
"""

import json
import re
import time
from typing import Optional

from .config import settings


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are an elite quantitative trader and risk manager specializing in XAUUSD (Gold) scalping on M1/M5 timeframes. "
    "You combine technical analysis, market microstructure knowledge, and risk management to make precise trading decisions. "
    "Analyze all provided market data holistically, paying special attention to: "
    "1) Trend alignment across EMA9/EMA21/EMA50, "
    "2) Momentum via RSI, MACD histogram, and Stochastic, "
    "3) Volatility via ATR and Bollinger Bands, "
    "4) Volume confirmation, "
    "5) Market regime (trending/sideways/reversal/volatile). "
    "Respond ONLY with a JSON object containing these exact keys: "
    '{"recommendation": "BUY" | "SELL" | "HOLD", "confidence": <0.0-1.0>, "reasoning": "<1-2 sentences>", "risk_note": "<brief risk warning if any>"}. '
    "Do not include any other text outside the JSON."
)


def _build_market_prompt(market_data: dict) -> str:
    symbol = market_data.get("symbol", "XAUUSD")
    price = market_data.get("price", 0)
    rsi = market_data.get("rsi", 50)
    rsi_zone = market_data.get("rsi_zone", "Neutral")
    macd_hist = market_data.get("macd_hist", 0)
    atr = market_data.get("atr", 0)
    adx = market_data.get("adx", 0)
    regime = market_data.get("regime", "unknown")
    ai_prob_up = market_data.get("ai_prob_up", 0.5)
    ai_prob_down = market_data.get("ai_prob_down", 0.5)
    ai_confidence = market_data.get("ai_confidence", 0.0)
    ai_direction = market_data.get("ai_direction", "")
    confirm_side = market_data.get("confirm_side", "")

    # Enhanced context fields
    ema_trend = market_data.get("ema_trend", 0)
    bb_pct_b = market_data.get("bb_pct_b", 0.5)
    bb_width = market_data.get("bb_width", 0)
    stoch_k = market_data.get("stoch_k", 50)
    vol_ratio = market_data.get("vol_ratio", 1.0)
    rule_reasons = market_data.get("rule_reasons", [])

    ema_desc = {2: "Fully Bullish (9>21>50)", 1: "Partially Bullish", 0: "Neutral",
                -1: "Partially Bearish", -2: "Fully Bearish (9<21<50)"}.get(int(ema_trend), "Neutral")

    bb_pos = "Near Lower Band" if bb_pct_b < 0.2 else ("Near Upper Band" if bb_pct_b > 0.8 else "Middle")
    vol_desc = f"{'High' if vol_ratio > 1.5 else 'Normal'} (x{vol_ratio:.1f} avg)"

    reasons_str = ", ".join(rule_reasons[:5]) if rule_reasons else "None"

    return (
        f"=== MARKET SNAPSHOT: {symbol} ===\n"
        f"Current Price: {price:.2f}\n\n"
        f"--- MOMENTUM INDICATORS ---\n"
        f"RSI(14): {rsi:.1f} [{rsi_zone}]\n"
        f"MACD Histogram: {macd_hist:.4f}\n"
        f"Stochastic %K: {stoch_k:.1f}\n\n"
        f"--- TREND INDICATORS ---\n"
        f"EMA Alignment: {ema_desc} (score={int(ema_trend)})\n"
        f"ADX(14): {adx:.1f} ({'Strong' if adx > 25 else 'Weak'} trend)\n"
        f"Market Regime: {regime}\n\n"
        f"--- VOLATILITY ---\n"
        f"ATR(14): {atr:.4f}\n"
        f"Bollinger Band Position: {bb_pos} (%B={bb_pct_b:.2f})\n"
        f"BB Width: {bb_width:.4f}\n\n"
        f"--- VOLUME ---\n"
        f"Volume vs Average: {vol_desc}\n\n"
        f"--- AI ANALYSIS ---\n"
        f"Technical AI Probability UP: {ai_prob_up:.1%}\n"
        f"Technical AI Probability DOWN: {ai_prob_down:.1%}\n"
        f"Technical AI Confidence: {ai_confidence:.1%}\n"
        f"Technical AI Direction: {ai_direction}\n"
        f"Key Signals: {reasons_str}\n\n"
        f"=== PROPOSED TRADE: {confirm_side} ===\n"
        "Should we execute this trade? Consider risk/reward carefully.\n"
        "Recommend BUY/SELL only if high confidence. Recommend HOLD to skip if risk is elevated."
    )


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_llm_response(text: str) -> dict:
    """Extract JSON from model response, tolerating extra wrapping text."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try extracting a JSON object (greedy, handles nested braces)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}


# ---------------------------------------------------------------------------
# OpenAI GPT
# ---------------------------------------------------------------------------

def _query_gpt(prompt: str) -> dict:
    """Call OpenAI Chat Completion and return parsed recommendation dict."""
    try:
        import openai  # type: ignore
    except ImportError:
        return {"error": "openai package not installed"}

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,   # ต่ำมากเพื่อให้ consistent
            max_tokens=300,
            response_format={"type": "json_object"},  # force JSON output
        )
        content = response.choices[0].message.content or ""
        parsed = _parse_llm_response(content)
        return {
            "recommendation": parsed.get("recommendation", "HOLD"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reasoning": parsed.get("reasoning", content[:200]),
            "risk_note": parsed.get("risk_note", ""),
        }
    except Exception as e:
        return {"error": str(e), "recommendation": "HOLD", "confidence": 0.0, "reasoning": ""}


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------

def _query_gemini(prompt: str) -> dict:
    """Call Google Gemini and return parsed recommendation dict."""
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError:
        return {"error": "google-generativeai package not installed"}

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=_SYSTEM_PROMPT,
        )
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.05,
                "max_output_tokens": 300,
                "response_mime_type": "application/json",
            },
        )
        content = response.text or ""
        parsed = _parse_llm_response(content)
        return {
            "recommendation": parsed.get("recommendation", "HOLD"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reasoning": parsed.get("reasoning", content[:200]),
            "risk_note": parsed.get("risk_note", ""),
        }
    except Exception as e:
        return {"error": str(e), "recommendation": "HOLD", "confidence": 0.0, "reasoning": ""}


# ---------------------------------------------------------------------------
# LLMAdvisor class
# ---------------------------------------------------------------------------

class LLMAdvisor:
    """
    Queries OpenAI GPT and/or Google Gemini to validate a trading signal.

    Usage:
        advisor = LLMAdvisor()
        result = advisor.analyze_signal(market_data, confirm_side="BUY")
        if result["consensus"] == "BUY":
            # proceed with trade

    The result dict contains:
        gpt_recommendation, gpt_confidence, gpt_reasoning (if enabled)
        gemini_recommendation, gemini_confidence, gemini_reasoning (if enabled)
        consensus: "BUY" | "SELL" | "HOLD"
        consensus_confidence: float
        llm_agrees: bool  (True if consensus matches proposed trade side)
    """

    def __init__(self):
        self.gpt_enabled = bool(settings.OPENAI_API_KEY) and settings.LLM_ADVISOR_ENABLED
        self.gemini_enabled = bool(settings.GEMINI_API_KEY) and settings.LLM_ADVISOR_ENABLED
        if self.gpt_enabled:
            print(f"[LLM] GPT advisor enabled (model={settings.OPENAI_MODEL})")
        if self.gemini_enabled:
            print(f"[LLM] Gemini advisor enabled (model={settings.GEMINI_MODEL})")
        if not self.gpt_enabled and not self.gemini_enabled:
            print("[LLM] LLM advisor disabled (set LLM_ADVISOR_ENABLED=true and provide API keys)")

    def analyze_signal(self, market_data: dict, confirm_side: str) -> dict:
        """
        Analyze market data with available LLMs and derive consensus.

        Args:
            market_data: dict with price, rsi, macd_hist, atr, adx, regime,
                         ema_trend, bb_pct_b, bb_width, stoch_k, vol_ratio,
                         rule_reasons, etc.
            confirm_side: "BUY" or "SELL" — the trade the technical AI wants to execute

        Returns:
            dict with gpt/gemini results and consensus fields.
        """
        data = {**market_data, "confirm_side": confirm_side}
        prompt = _build_market_prompt(data)

        result: dict = {}

        # --- GPT ---
        gpt_rec: Optional[str] = None
        gpt_conf = 0.0
        if self.gpt_enabled:
            gpt_out = _query_gpt(prompt)
            gpt_rec = gpt_out.get("recommendation", "HOLD")
            gpt_conf = float(gpt_out.get("confidence", 0.0))
            result["gpt_recommendation"] = gpt_rec
            result["gpt_confidence"] = gpt_conf
            result["gpt_reasoning"] = gpt_out.get("reasoning", "")
            result["gpt_risk_note"] = gpt_out.get("risk_note", "")
            if "error" in gpt_out:
                result["gpt_error"] = gpt_out["error"]
                print(f"[LLM][GPT] error: {gpt_out['error']}")
            else:
                print(f"[LLM][GPT] {gpt_rec} (conf={gpt_conf:.2f}) — {result.get('gpt_reasoning','')[:80]}")

        # --- Gemini ---
        gemini_rec: Optional[str] = None
        gemini_conf = 0.0
        if self.gemini_enabled:
            gemini_out = _query_gemini(prompt)
            gemini_rec = gemini_out.get("recommendation", "HOLD")
            gemini_conf = float(gemini_out.get("confidence", 0.0))
            result["gemini_recommendation"] = gemini_rec
            result["gemini_confidence"] = gemini_conf
            result["gemini_reasoning"] = gemini_out.get("reasoning", "")
            result["gemini_risk_note"] = gemini_out.get("risk_note", "")
            if "error" in gemini_out:
                result["gemini_error"] = gemini_out["error"]
                print(f"[LLM][Gemini] error: {gemini_out['error']}")
            else:
                print(f"[LLM][Gemini] {gemini_rec} (conf={gemini_conf:.2f}) — {result.get('gemini_reasoning','')[:80]}")

        # --- Consensus ---
        consensus, consensus_confidence = self._derive_consensus(
            confirm_side, gpt_rec, gpt_conf, gemini_rec, gemini_conf
        )
        result["consensus"] = consensus
        result["consensus_confidence"] = consensus_confidence
        result["llm_agrees"] = (consensus == confirm_side.upper())
        return result

    def _derive_consensus(
        self,
        confirm_side: str,
        gpt_rec: Optional[str],
        gpt_conf: float,
        gemini_rec: Optional[str],
        gemini_conf: float,
    ) -> tuple:
        """
        Derive a consensus from available model outputs using confidence-weighted voting.

        Rules:
        - If neither model is available: pass-through (return confirm_side)
        - If only one model available: use its recommendation (must have conf > 0.5 to agree)
        - If both available and agree: use their confidence-weighted average
        - If both available but disagree: pick higher-confidence model if gap > 0.15, else HOLD
        """
        side = confirm_side.upper()

        if not self.gpt_enabled and not self.gemini_enabled:
            return side, 1.0  # pass-through when advisor is off

        votes = []
        if self.gpt_enabled and gpt_rec:
            votes.append((gpt_rec.upper(), gpt_conf))
        if self.gemini_enabled and gemini_rec:
            votes.append((gemini_rec.upper(), gemini_conf))

        if not votes:
            return side, 0.5

        if len(votes) == 1:
            rec, conf = votes[0]
            # If single model says HOLD or has low confidence, don't override
            if rec == "HOLD" or conf < 0.45:
                return "HOLD", conf
            return rec, conf

        # Both voted
        rec_a, conf_a = votes[0]
        rec_b, conf_b = votes[1]

        if rec_a == rec_b:
            # Unanimous: simple average confidence
            return rec_a, (conf_a + conf_b) / 2.0

        # Disagreement: pick higher-confidence if gap is significant
        if abs(conf_a - conf_b) > 0.20:
            if conf_a > conf_b:
                return rec_a, conf_a * 0.8  # small penalty for disagreement
            else:
                return rec_b, conf_b * 0.8

        # Close disagreement → HOLD (too uncertain)
        return "HOLD", 0.0
