"""
Failure Prediction Module
Analyses historical trends in SNR, BER, and Latency to estimate
failure risk without predicting an exact failure time.
"""

import pandas as pd
import numpy as np


def _linear_slope(series: pd.Series) -> float:
    """Return the linear regression slope of a numeric series."""
    if len(series) < 3:
        return 0.0
    x = np.arange(len(series), dtype=float)
    y = series.values.astype(float)
    # Simple least-squares slope
    x_mean, y_mean = x.mean(), y.mean()
    denom = ((x - x_mean) ** 2).sum()
    if denom == 0:
        return 0.0
    return float(((x - x_mean) * (y - y_mean)).sum() / denom)


def predict_failure(df: pd.DataFrame) -> dict:
    """
    Evaluate trend direction and magnitude to produce:
      - failure_risk:    LOW / MEDIUM / HIGH
      - signal_trend:   IMPROVING / STABLE / DEGRADING
      - prediction:     STABLE / AT RISK / HIGH RISK
      - reason:         short human-readable explanation
      - metric_trends:  per-metric slope direction
    """
    snr_slope     = _linear_slope(df["snr"])
    ber_slope     = _linear_slope(df["ber"])
    latency_slope = _linear_slope(df["latency"])

    # Classify per-metric direction
    def direction(slope, invert=False):
        threshold = 0.01
        if abs(slope) < threshold:
            return "STABLE"
        improving = slope > 0 if not invert else slope < 0
        return "IMPROVING" if improving else "DEGRADING"

    snr_dir     = direction(snr_slope, invert=False)   # higher SNR is better
    ber_dir     = direction(ber_slope, invert=True)    # lower BER is better
    latency_dir = direction(latency_slope, invert=True)  # lower latency is better

    degrading_count = sum(1 for d in [snr_dir, ber_dir, latency_dir] if d == "DEGRADING")
    improving_count = sum(1 for d in [snr_dir, ber_dir, latency_dir] if d == "IMPROVING")

    # Overall trend
    if improving_count >= 2:
        signal_trend = "IMPROVING"
    elif degrading_count >= 2:
        signal_trend = "DEGRADING"
    else:
        signal_trend = "STABLE"

    # Failure risk based on how many metrics are degrading and magnitude
    snr_latest     = float(df["snr"].tail(10).mean())
    ber_latest     = float(df["ber"].tail(10).mean())
    latency_latest = float(df["latency"].tail(10).mean())

    risk_score = 0
    if snr_latest < 15:
        risk_score += 2
    elif snr_latest < 20:
        risk_score += 1

    if ber_latest > 0.03:
        risk_score += 2
    elif ber_latest > 0.01:
        risk_score += 1

    if latency_latest > 200:
        risk_score += 2
    elif latency_latest > 120:
        risk_score += 1

    if degrading_count >= 2:
        risk_score += 2
    elif degrading_count == 1:
        risk_score += 1

    if risk_score >= 6:
        failure_risk = "HIGH"
        prediction   = "HIGH RISK"
    elif risk_score >= 3:
        failure_risk = "MEDIUM"
        prediction   = "AT RISK"
    else:
        failure_risk = "LOW"
        prediction   = "STABLE"

    # Build reason string
    reasons = []
    if snr_dir == "DEGRADING":
        reasons.append("SNR is decreasing")
    if ber_dir == "DEGRADING":
        reasons.append("BER is increasing")
    if latency_dir == "DEGRADING":
        reasons.append("latency is increasing")
    if snr_dir == "IMPROVING":
        reasons.append("SNR is recovering")
    if ber_dir == "IMPROVING":
        reasons.append("BER is improving")
    if latency_dir == "IMPROVING":
        reasons.append("latency is decreasing")

    if reasons:
        reason = "Signal quality is " + signal_trend.lower() + " because " + ", ".join(reasons) + "."
    else:
        reason = "All metrics are stable. No significant trend detected."

    return {
        "failure_risk":  failure_risk,
        "signal_trend":  signal_trend,
        "prediction":    prediction,
        "reason":        reason,
        "metric_trends": {
            "snr":     snr_dir,
            "ber":     ber_dir,
            "latency": latency_dir,
        },
        "slopes": {
            "snr":     round(snr_slope, 6),
            "ber":     round(ber_slope, 8),
            "latency": round(latency_slope, 4),
        }
    }
