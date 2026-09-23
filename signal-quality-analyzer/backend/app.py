"""
AI-Powered Signal Quality Analyzer — Flask Backend
Endpoints:
  POST /api/upload   — upload & validate CSV
  POST /api/analyze  — full signal analysis
  POST /api/insight  — AI/rule-based insight
  POST /api/predict  — failure prediction
"""

import os
import io
import json
import logging

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from analyzer   import analyze_signal, detect_issues, calculate_quality
from prediction import predict_failure
from ai_insight import generate_insight

# ------------------------------------------------------------------ #
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)           # allow the frontend (any origin) to call the API

REQUIRED_COLUMNS = {"timestamp", "snr", "ber", "latency"}

# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _load_df(file_storage) -> pd.DataFrame:
    """Read an uploaded CSV FileStorage into a validated DataFrame."""
    content = file_storage.read().decode("utf-8")
    df = pd.read_csv(io.StringIO(content))
    df.columns = [c.strip().lower() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["snr"]       = pd.to_numeric(df["snr"],     errors="coerce")
    df["ber"]       = pd.to_numeric(df["ber"],     errors="coerce")
    df["latency"]   = pd.to_numeric(df["latency"], errors="coerce")
    df = df.dropna(subset=["snr", "ber", "latency"])

    if df.empty:
        raise ValueError("No valid rows found after parsing numeric columns.")

    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def _full_analysis(df: pd.DataFrame) -> dict:
    """Run the complete analysis pipeline and return a combined result dict."""
    stats      = analyze_signal(df)
    issues     = detect_issues(stats)
    quality    = calculate_quality(stats)
    prediction = predict_failure(df)
    insight    = generate_insight(stats, issues, quality, prediction)

    # Recommendations derived from issues
    recommendations = _build_recommendations(issues, prediction)

    return {
        "stats":           stats,
        "issues":          issues,
        "quality":         quality,
        "prediction":      prediction,
        "insight":         insight,
        "recommendations": recommendations,
        "record_count":    len(df),
    }


def _build_recommendations(issues: list, prediction: dict) -> list:
    """Generate a tailored list of recommended actions."""
    recs = set()
    for issue in issues:
        sev    = issue["severity"]
        metric = issue.get("metric", "")
        if "SNR" in metric:
            recs.add("Check antenna alignment and cable connections to improve SNR.")
        if "BER" in metric:
            recs.add("Investigate RF interference sources near the transmitter.")
        if "Latency" in metric or "latency" in metric.lower():
            recs.add("Review network routing and check for congestion.")
        if "Degradation" in issue["issue"] or "degradation" in issue["issue"].lower():
            recs.add("Monitor SNR degradation trend and schedule preventive maintenance.")
        if "Interference" in issue["issue"]:
            recs.add("Conduct spectrum analysis to identify interference sources.")
        if sev == "CRITICAL":
            recs.add("Escalate to the network engineering team immediately.")

    trend = prediction.get("signal_trend", "STABLE")
    risk  = prediction.get("failure_risk", "LOW")
    if trend == "DEGRADING":
        recs.add("Increase monitoring frequency for all signal metrics.")
    if risk in ("MEDIUM", "HIGH"):
        recs.add("Review communication channel conditions and equipment health.")
    if risk == "HIGH":
        recs.add("Consider proactive component replacement to prevent failure.")

    if not recs:
        recs.add("Continue routine monitoring. Signal is operating within normal parameters.")
        recs.add("Document baseline metrics for future comparison.")

    return sorted(recs)


# ------------------------------------------------------------------ #
#  Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/api/upload", methods=["POST"])
def upload():
    """Validate uploaded CSV and return basic file info."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported."}), 400

    try:
        df = _load_df(file)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    return jsonify({
        "success":      True,
        "filename":     file.filename,
        "record_count": len(df),
        "columns":      list(df.columns),
        "message":      f"File '{file.filename}' uploaded successfully. {len(df)} valid records found.",
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Full analysis pipeline: stats + issues + quality + prediction + insight + recommendations."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]
    try:
        df     = _load_df(file)
        result = _full_analysis(df)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        logger.exception("Unexpected error during analysis")
        return jsonify({"error": f"Internal error: {exc}"}), 500

    return jsonify(result)


@app.route("/api/insight", methods=["POST"])
def insight():
    """Re-run only the AI insight step given JSON payload."""
    data = request.get_json(force=True, silent=True) or {}
    stats      = data.get("stats")
    issues     = data.get("issues", [])
    quality    = data.get("quality", {})
    prediction = data.get("prediction", {})

    if not stats:
        return jsonify({"error": "Missing 'stats' in request body."}), 400

    try:
        result = generate_insight(stats, issues, quality, prediction)
    except Exception as exc:
        logger.exception("Error generating insight")
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


@app.route("/api/predict", methods=["POST"])
def predict():
    """Re-run only the prediction step given a JSON payload with series arrays."""
    data = request.get_json(force=True, silent=True) or {}
    try:
        df = pd.DataFrame({
            "snr":     data.get("snr_series", []),
            "ber":     data.get("ber_series", []),
            "latency": data.get("latency_series", []),
        })
        if df.empty:
            return jsonify({"error": "Empty series data."}), 400
        result = predict_failure(df)
    except Exception as exc:
        logger.exception("Error during prediction")
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


@app.route("/api/sample", methods=["GET"])
def sample():
    """Return the bundled sample dataset as JSON for the 'Load Sample Data' button."""
    sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "signal_data.csv")
    try:
        df     = pd.read_csv(sample_path)
        df.columns = [c.strip().lower() for c in df.columns]
        df["snr"]     = pd.to_numeric(df["snr"],     errors="coerce")
        df["ber"]     = pd.to_numeric(df["ber"],     errors="coerce")
        df["latency"] = pd.to_numeric(df["latency"], errors="coerce")
        df = df.dropna()
        result = _full_analysis(df)
        result["filename"] = "signal_data.csv (sample)"
    except Exception as exc:
        logger.exception("Error loading sample data")
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


# ------------------------------------------------------------------ #

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info("Starting Signal Quality Analyzer backend on port %d", port)
    app.run(debug=True, port=port)
