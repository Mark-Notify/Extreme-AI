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
from typing import Optional

from .config import settings


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are an expert quantitative trader specializing in XAUUSD (Gold) scalping. "
    "Analyze the provided market data and give a concise trading recommendation. "
    "Respond ONLY with a JSON object containing these exact keys: "
    '{"recommendation": "BUY" | "SELL" | "HOLD", "confidence": <0.0-1.0>, "reasoning": "<1-2 sentences>"}. '
    "Do not include any other text."
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

    return (
        f"Symbol: {symbol}\n"
        f"Current Price: {price:.2f}\n"
        f"RSI: {rsi:.2f} ({rsi_zone})\n"
        f"MACD Histogram: {macd_hist:.4f}\n"
        f"ATR: {atr:.4f}\n"
        f"ADX: {adx:.2f}\n"
        f"Market Regime: {regime}\n"
        f"Technical AI Probability UP: {ai_prob_up:.2%}\n"
        f"Technical AI Probability DOWN: {ai_prob_down:.2%}\n"
        f"Technical AI Confidence: {ai_confidence:.2%}\n"
        f"Technical AI Direction: {ai_direction}\n"
        f"Proposed Trade Side: {confirm_side}\n\n"
        "Based on this data, should we execute the proposed trade?"
    )


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_llm_response(text: str) -> dict:
    """Extract JSON from model response, tolerating extra wrapping text."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try extracting first JSON object
    match = re.search(r"\{.*?\}", text, re.DOTALL)
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
            temperature=0.1,
            max_tokens=200,
        )
        content = response.choices[0].message.content or ""
        parsed = _parse_llm_response(content)
        return {
            "recommendation": parsed.get("recommendation", "HOLD"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reasoning": parsed.get("reasoning", content[:200]),
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
            generation_config={"temperature": 0.1, "max_output_tokens": 200},
        )
        content = response.text or ""
        parsed = _parse_llm_response(content)
        return {
            "recommendation": parsed.get("recommendation", "HOLD"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reasoning": parsed.get("reasoning", content[:200]),
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
            market_data: dict with price, rsi, macd_hist, atr, adx, regime, etc.
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
        Derive a consensus from available model outputs.

        Rules:
        - If only one model available: use its recommendation
        - If both available and agree: use their average confidence
        - If both available but disagree: return HOLD (skip trade)
        - If neither available: return confirm_side (pass-through)
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
            return votes[0][0], votes[0][1]

        # Both voted
        rec_a, conf_a = votes[0]
        rec_b, conf_b = votes[1]
        if rec_a == rec_b:
            return rec_a, (conf_a + conf_b) / 2.0
        # Disagreement → HOLD
        return "HOLD", 0.0
