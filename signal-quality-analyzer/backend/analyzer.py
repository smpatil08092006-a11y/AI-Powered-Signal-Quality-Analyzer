"""
Signal Analysis Module
Processes SNR, BER, and Latency data to compute statistics,
detect issues, and calculate a signal quality score.
"""

import pandas as pd

# ---------- Thresholds ----------
SNR_GOOD       = 25.0   # dB  — above this is good
SNR_WARNING    = 15.0   # dB  — below this triggers warning
SNR_CRITICAL   = 10.0   # dB  — below this is critical

BER_GOOD       = 0.001  # below this is good
BER_WARNING    = 0.010  # above this triggers warning
BER_CRITICAL   = 0.050  # above this is critical

LAT_GOOD       = 80     # ms  — below this is good
LAT_WARNING    = 150    # ms  — above this triggers warning
LAT_CRITICAL   = 250    # ms  — above this is critical


def analyze_signal(df: pd.DataFrame) -> dict:
    """Return per-metric statistics from a validated DataFrame."""
    result = {}
    for col in ["snr", "ber", "latency"]:
        series = df[col]
        result[col] = {
            "current": round(float(series.iloc[-1]), 6),
            "average": round(float(series.mean()), 6),
            "minimum": round(float(series.min()), 6),
            "maximum": round(float(series.max()), 6),
        }
    # Time-series arrays for charts (last 50 points max)
    tail = df.tail(50)
    result["timestamps"] = tail["timestamp"].astype(str).tolist()
    result["snr_series"]     = [round(v, 4) for v in tail["snr"].tolist()]
    result["ber_series"]     = [round(v, 6) for v in tail["ber"].tolist()]
    result["latency_series"] = [round(v, 2) for v in tail["latency"].tolist()]
    return result


def detect_issues(stats: dict) -> list:
    """
    Evaluate current metric values against thresholds.
    Returns a list of issue dicts with severity info.
    """
    issues = []
    snr     = stats["snr"]["current"]
    ber     = stats["ber"]["current"]
    latency = stats["latency"]["current"]

    # SNR issues
    if snr < SNR_CRITICAL:
        issues.append({
            "issue":       "Critical Low SNR Detected",
            "severity":    "CRITICAL",
            "metric":      "SNR",
            "value":       f"{snr:.2f} dB",
            "explanation": f"SNR is extremely low ({snr:.2f} dB). Signal is nearly unusable. Possible hardware failure or severe interference."
        })
    elif snr < SNR_WARNING:
        issues.append({
            "issue":       "Low SNR Detected",
            "severity":    "WARNING",
            "metric":      "SNR",
            "value":       f"{snr:.2f} dB",
            "explanation": f"SNR has dropped to {snr:.2f} dB. Signal quality is degrading. Monitor for further decline."
        })

    # BER issues
    if ber > BER_CRITICAL:
        issues.append({
            "issue":       "Critical High BER Detected",
            "severity":    "CRITICAL",
            "metric":      "BER",
            "value":       f"{ber:.4f}",
            "explanation": f"BER is critically high ({ber:.4f}). Significant data corruption is occurring. Immediate action required."
        })
    elif ber > BER_WARNING:
        issues.append({
            "issue":       "High BER Detected",
            "severity":    "WARNING",
            "metric":      "BER",
            "value":       f"{ber:.4f}",
            "explanation": f"BER has risen to {ber:.4f}. Elevated error rate may affect data integrity."
        })

    # Latency issues
    if latency > LAT_CRITICAL:
        issues.append({
            "issue":       "Critical High Latency Detected",
            "severity":    "CRITICAL",
            "metric":      "Latency",
            "value":       f"{latency:.1f} ms",
            "explanation": f"Latency is critically high ({latency:.1f} ms). Real-time communication will be severely impacted."
        })
    elif latency > LAT_WARNING:
        issues.append({
            "issue":       "High Latency Detected",
            "severity":    "WARNING",
            "metric":      "Latency",
            "value":       f"{latency:.1f} ms",
            "explanation": f"Latency is elevated at {latency:.1f} ms. Performance may be noticeably degraded."
        })

    # Signal degradation pattern: SNR low AND BER high
    if snr < SNR_WARNING and ber > BER_WARNING:
        issues.append({
            "issue":       "Possible Signal Degradation Detected",
            "severity":    "WARNING",
            "metric":      "SNR + BER",
            "value":       f"SNR={snr:.2f} dB, BER={ber:.4f}",
            "explanation": "Simultaneous low SNR and high BER indicates signal degradation, possibly caused by interference or path loss."
        })

    # All three metrics abnormal — likely interference
    if snr < SNR_WARNING and ber > BER_WARNING and latency > LAT_WARNING:
        issues.append({
            "issue":       "Possible Interference Detected",
            "severity":    "CRITICAL",
            "metric":      "All Metrics",
            "value":       f"SNR={snr:.2f}, BER={ber:.4f}, Lat={latency:.1f} ms",
            "explanation": "All three metrics are outside acceptable ranges simultaneously. Possible RF interference or equipment fault."
        })

    if not issues:
        issues.append({
            "issue":       "Signal Operating Normally",
            "severity":    "GOOD",
            "metric":      "All Metrics",
            "value":       "Within thresholds",
            "explanation": "SNR, BER, and latency are all within acceptable operating ranges."
        })

    return issues


def calculate_quality(stats: dict) -> dict:
    """
    Compute a 0–100 signal quality score from current SNR, BER, latency.
    Returns score, label, and overall status.
    """
    snr     = stats["snr"]["current"]
    ber     = stats["ber"]["current"]
    latency = stats["latency"]["current"]

    # Normalise each metric to a 0–100 sub-score
    # SNR: 0 dB → 0, 35 dB → 100
    snr_score = max(0.0, min(100.0, (snr / 35.0) * 100))

    # BER: 0 → 100, 0.1 → 0 (log-style clamping)
    ber_score = max(0.0, min(100.0, (1 - ber / 0.1) * 100))

    # Latency: 0 ms → 100, 400 ms → 0
    lat_score = max(0.0, min(100.0, (1 - latency / 400.0) * 100))

    # Weighted average: SNR 40 %, BER 35 %, Latency 25 %
    score = round(snr_score * 0.40 + ber_score * 0.35 + lat_score * 0.25, 1)

    if score >= 80:
        label, status = "Excellent", "GOOD"
    elif score >= 60:
        label, status = "Good", "GOOD"
    elif score >= 40:
        label, status = "Warning", "WARNING"
    else:
        label, status = "Critical", "CRITICAL"

    return {"score": score, "label": label, "status": status}
