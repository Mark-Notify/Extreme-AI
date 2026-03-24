# core/position_sizing.py

from core.config import settings


def calculate_position_size(
    balance: float,
    atr: float,
    risk_percent: float | None = None,
    win_rate: float | None = None,
    avg_rr: float | None = None,
) -> float:
    """
    คำนวณ volume (lot) แบบ Dynamic Position Sizing

    เมธอด 1 — Fixed Fractional (default):
        risk_amount = balance * risk_percent
        SL distance = ATR_SL_MULTIPLIER * atr
        cost_per_lot = (SL_distance / TICK_SIZE) * TICK_VALUE
        volume = risk_amount / cost_per_lot

    เมธอด 2 — Kelly Criterion (ถ้า win_rate + avg_rr ระบุ และเปิด KELLY_CRITERION_ENABLED):
        kelly_f = win_rate - (1 - win_rate) / avg_rr
        risk_percent = kelly_f * KELLY_FRACTION (half-Kelly default)

    เลือกค่าน้อยกว่าระหว่าง Fixed Fractional vs Kelly เพื่อความปลอดภัย

    Parameters:
        balance     : ยอดเงินในบัญชี
        atr         : ค่า ATR ล่าสุด
        risk_percent: สัดส่วนความเสี่ยง (None = ใช้จาก settings)
        win_rate    : อัตรากำไรโดยประมาณ 0-1 (สำหรับ Kelly)
        avg_rr      : Risk:Reward ratio เฉลี่ย (สำหรับ Kelly)
    """

    if risk_percent is None:
        risk_percent = settings.RISK_PER_TRADE

    if balance <= 0 or atr <= 0 or risk_percent <= 0:
        return settings.MIN_VOLUME

    # ── Kelly Criterion (optional) ────────────────────────────────────
    kelly_enabled = getattr(settings, "KELLY_CRITERION_ENABLED", False)
    if kelly_enabled and win_rate is not None and avg_rr is not None and avg_rr > 0:
        kelly_f = win_rate - (1.0 - win_rate) / avg_rr
        if kelly_f > 0:  # only apply Kelly when it yields a positive bet size
            kelly_fraction = getattr(settings, "KELLY_FRACTION", 0.5)  # Half-Kelly
            kelly_risk = kelly_f * kelly_fraction
            # ใช้ค่าน้อยกว่าระหว่าง Fixed Fractional vs Kelly (conservative)
            risk_percent = min(risk_percent, max(0.001, kelly_risk))

    # ── Fixed Fractional ──────────────────────────────────────────────
    risk_amount = balance * risk_percent

    sl_distance_price = settings.ATR_SL_MULTIPLIER * atr
    if sl_distance_price <= 0:
        return settings.MIN_VOLUME

    # price distance → points
    sl_points = sl_distance_price / settings.TICK_SIZE
    if sl_points <= 0:
        return settings.MIN_VOLUME

    cost_per_lot = sl_points * settings.TICK_VALUE
    if cost_per_lot <= 0:
        return settings.MIN_VOLUME

    volume = risk_amount / cost_per_lot

    # ── Drawdown protection: ลด size เมื่อ balance ลดลงจาก peak ──────
    initial_balance = getattr(settings, "INITIAL_BALANCE", balance)
    if initial_balance > 0 and balance < initial_balance:
        drawdown_pct = (initial_balance - balance) / initial_balance
        if drawdown_pct > 0.10:   # drawdown > 10% → ลด size 50%
            volume *= 0.5
        elif drawdown_pct > 0.05:  # drawdown > 5% → ลด size 25%
            volume *= 0.75

    # clamp volume ตาม min/max
    volume = max(settings.MIN_VOLUME, min(volume, settings.MAX_VOLUME))
    return round(volume, 2)
