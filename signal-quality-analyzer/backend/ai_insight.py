"""
AI Insight Module
Sends signal data to IBM Granite via IBM watsonx.ai.
Falls back to rule-based insights when credentials are missing.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  IBM watsonx.ai helper                                               #
# ------------------------------------------------------------------ #

def _get_watsonx_token(api_key: str) -> str:
    """Exchange an IBM Cloud API key for a short-lived IAM token."""
    import urllib.request
    url  = "https://iam.cloud.ibm.com/identity/token"
    body = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={api_key}"
    req  = urllib.request.Request(
        url,
        data=body.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["access_token"]


def _call_watsonx(prompt: str, api_key: str, project_id: str, url: str) -> str:
    """Call IBM watsonx.ai Granite text generation API."""
    import urllib.request
    token   = _get_watsonx_token(api_key)
    endpoint = f"{url.rstrip('/')}/ml/v1/text/generation?version=2023-05-29"
    payload  = json.dumps({
        "model_id": "ibm/granite-13b-instruct-v2",
        "input":    prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens":  400,
            "temperature":     0.7,
        },
        "project_id": project_id
    }).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data["results"][0]["generated_text"].strip()


# ------------------------------------------------------------------ #
#  Rule-based fallback                                                 #
# ------------------------------------------------------------------ #

def _rule_based_insight(stats: dict, issues: list, quality: dict, prediction: dict) -> dict:
    """
    Generate structured insight without any external API call.
    Used when IBM credentials are not configured.
    """
    snr     = stats["snr"]["current"]
    ber     = stats["ber"]["current"]
    latency = stats["latency"]["current"]
    score   = quality["score"]
    trend   = prediction.get("signal_trend", "STABLE")
    risk    = prediction.get("failure_risk", "LOW")

    # --- Cause ---
    causes = []
    if snr < 15:
        causes.append("critically low Signal-to-Noise Ratio")
    elif snr < 25:
        causes.append("below-average Signal-to-Noise Ratio")

    if ber > 0.01:
        causes.append("elevated Bit Error Rate indicating data corruption")
    if latency > 150:
        causes.append("high network latency affecting communication quality")

    if not causes:
        cause = "All signal metrics are within normal operating parameters."
    else:
        cause = "Detected: " + "; ".join(causes) + "."

    # --- Explanation ---
    if score >= 80:
        explanation = (
            f"The signal is performing well. SNR is {snr:.1f} dB (good), "
            f"BER is {ber:.4f} (acceptable), and latency is {latency:.0f} ms (normal). "
            f"No significant issues detected in the current readings."
        )
    elif score >= 60:
        explanation = (
            f"Signal quality is adequate but showing early signs of stress. "
            f"SNR of {snr:.1f} dB and BER of {ber:.4f} suggest minor degradation. "
            f"Latency at {latency:.0f} ms is slightly elevated. Monitor closely."
        )
    elif score >= 40:
        explanation = (
            f"Signal quality is degraded. SNR has dropped to {snr:.1f} dB, "
            f"BER has risen to {ber:.4f}, and latency is {latency:.0f} ms. "
            f"The trend is {trend.lower()}. Corrective action is recommended."
        )
    else:
        explanation = (
            f"Signal quality is critical. SNR is only {snr:.1f} dB, "
            f"BER is {ber:.4f} indicating heavy data loss, and latency is {latency:.0f} ms. "
            f"Failure risk is {risk}. Immediate investigation required."
        )

    # --- Recommendation ---
    recs = []
    if snr < 25:
        recs.append("Inspect antenna alignment and connections to improve SNR")
    if ber > 0.005:
        recs.append("Check for RF interference sources near the transmitter")
    if latency > 100:
        recs.append("Review routing configuration and network path congestion")
    if trend == "DEGRADING":
        recs.append("Increase monitoring frequency and set alerts for threshold breaches")
    if risk == "HIGH":
        recs.append("Escalate to network engineering team for immediate review")
    if not recs:
        recs.append("Continue routine monitoring. No corrective action needed at this time")

    recommendation = ". ".join(recs) + "."

    return {
        "cause":          cause,
        "explanation":    explanation,
        "recommendation": recommendation,
        "source":         "Rule-Based Fallback (IBM credentials not configured)"
    }


# ------------------------------------------------------------------ #
#  Public entry point                                                  #
# ------------------------------------------------------------------ #

def generate_insight(stats: dict, issues: list, quality: dict, prediction: dict) -> dict:
    """
    Generate AI insight using IBM Granite when credentials are present,
    otherwise use the rule-based fallback.
    """
    api_key    = os.getenv("WATSONX_API_KEY", "").strip()
    project_id = os.getenv("WATSONX_PROJECT_ID", "").strip()
    wx_url     = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").strip()

    if not api_key or not project_id:
        logger.info("IBM credentials not configured — using rule-based fallback.")
        return _rule_based_insight(stats, issues, quality, prediction)

    # Build prompt
    issue_lines = "\n".join(
        f"  - {i['issue']} (Severity: {i['severity']}, Value: {i['value']})"
        for i in issues
    )
    prompt = f"""You are a telecommunications signal quality expert.

Analyze the following signal data and provide a structured response with exactly three sections:
1. Cause
2. Explanation
3. Recommendation

Signal Metrics:
  - SNR (Signal-to-Noise Ratio): {stats['snr']['current']:.2f} dB (avg: {stats['snr']['average']:.2f} dB)
  - BER (Bit Error Rate): {stats['ber']['current']:.4f} (avg: {stats['ber']['average']:.4f})
  - Latency: {stats['latency']['current']:.1f} ms (avg: {stats['latency']['average']:.1f} ms)

Detected Issues:
{issue_lines}

Signal Quality Score: {quality['score']}/100 ({quality['label']})
Signal Trend: {prediction.get('signal_trend', 'UNKNOWN')}
Failure Risk: {prediction.get('failure_risk', 'UNKNOWN')}

Respond in this exact format:
Cause: <one sentence>
Explanation: <two to three sentences>
Recommendation: <one to two sentences>"""

    try:
        raw = _call_watsonx(prompt, api_key, project_id, wx_url)
        # Parse structured response
        result = {"cause": "", "explanation": "", "recommendation": "", "source": "IBM Granite (watsonx.ai)"}
        for line in raw.splitlines():
            if line.lower().startswith("cause:"):
                result["cause"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("explanation:"):
                result["explanation"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("recommendation:"):
                result["recommendation"] = line.split(":", 1)[1].strip()
        # If parsing failed, use raw text
        if not result["cause"] and not result["explanation"]:
            result["explanation"] = raw
        return result
    except Exception as exc:
        logger.warning("IBM watsonx.ai call failed (%s) — falling back to rule-based.", exc)
        fb = _rule_based_insight(stats, issues, quality, prediction)
        fb["source"] = f"Rule-Based Fallback (watsonx.ai error: {type(exc).__name__})"
        return fb
