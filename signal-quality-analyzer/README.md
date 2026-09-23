# AI-Powered Signal Quality Analyzer

**Problem Statement No. 25** — AI-Powered Signal Quality Analyzer  
Built with: **Python · Flask · Pandas · IBM Granite (watsonx.ai) · HTML · CSS · JavaScript · Chart.js**

---

## 📌 Project Overview

A simple, student-friendly web application that:

1. **Processes Signal Data** — Reads CSV containing SNR, BER, and Latency and computes statistics.
2. **Detects Signal Issues** — Applies configurable thresholds to flag Low SNR, High BER, High Latency, Signal Degradation, and Possible Interference with GOOD / WARNING / CRITICAL severity.
3. **Generates Intelligent Insights** — Sends analyzed data to **IBM Granite** via **IBM watsonx.ai** and returns structured Cause · Explanation · Recommendation. Falls back to rule-based analysis when credentials are absent.
4. **Predicts Potential Failures** — Uses linear trend analysis on historical data to output Failure Risk (LOW / MEDIUM / HIGH), Signal Trend (IMPROVING / STABLE / DEGRADING), and a plain-English reason.

---

## 🗂 Project Structure

```
signal-quality-analyzer/
├── frontend/
│   ├── index.html       ← Dashboard UI
│   ├── style.css        ← Dark navy theme
│   └── script.js        ← API calls + Chart.js + report
├── backend/
│   ├── app.py           ← Flask API (4 endpoints)
│   ├── analyzer.py      ← analyze_signal, detect_issues, calculate_quality
│   ├── prediction.py    ← predict_failure
│   ├── ai_insight.py    ← generate_insight (IBM Granite + fallback)
│   └── requirements.txt
├── data/
│   └── signal_data.csv  ← 50-row sample dataset
├── .env.example         ← Template for IBM credentials
└── README.md
```

---

## 🚀 Quick Start

### 1 — Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2 — Configure IBM watsonx.ai (optional)

```bash
# In the root folder
copy .env.example .env       # Windows
cp  .env.example .env        # macOS / Linux
```

Edit `.env` and fill in your IBM Cloud API key, project ID, and URL.  
**If you skip this step the app still works using the rule-based fallback.**

### 3 — Start Flask backend

```bash
cd backend
python app.py
```

The API runs at **http://127.0.0.1:5000**

### 4 — Open the frontend

Open `frontend/index.html` directly in your browser — no extra server needed.

> Windows shortcut:
> ```
> start frontend\index.html
> ```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/sample`  | Load & analyze built-in sample data |
| POST | `/api/upload`  | Validate uploaded CSV |
| POST | `/api/analyze` | Full analysis pipeline (file upload) |
| POST | `/api/insight` | AI insight only (JSON payload) |
| POST | `/api/predict` | Failure prediction only (JSON payload) |

---

## 📊 Required CSV Format

```
timestamp,snr,ber,latency
2024-01-01 00:00:00,28.5,0.0012,45
2024-01-01 00:05:00,27.8,0.0015,48
...
```

| Column | Unit | Description |
|--------|------|-------------|
| `timestamp` | datetime | Measurement timestamp |
| `snr`       | dB       | Signal-to-Noise Ratio |
| `ber`       | ratio    | Bit Error Rate |
| `latency`   | ms       | Network latency |

---

## ⚙️ Detection Thresholds

| Metric  | Good        | Warning     | Critical    |
|---------|-------------|-------------|-------------|
| SNR     | ≥ 25 dB     | 15–25 dB    | < 10 dB     |
| BER     | < 0.001     | 0.001–0.01  | > 0.05      |
| Latency | < 80 ms     | 80–150 ms   | > 250 ms    |

---

## 🤖 LangFlow / LangChain Workflow

```
Signal Data (CSV)
      ↓
Signal Analysis     [analyzer.py → analyze_signal()]
      ↓
Issue Detection     [analyzer.py → detect_issues()]
      ↓
Quality Score       [analyzer.py → calculate_quality()]
      ↓
Historical Trends   [prediction.py → predict_failure()]
      ↓
IBM Granite Prompt  [ai_insight.py → _call_watsonx()]
      ↓
AI Insight          {Cause, Explanation, Recommendation}
      ↓
Recommendations     [app.py → _build_recommendations()]
      ↓
Frontend Display    Charts + Report
```

No complex multi-agent setup — a single sequential chain from raw data to insight.

---

## 🏗 Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend UI | HTML5, CSS3, JavaScript (ES6) |
| Charting | Chart.js 4.x |
| Backend | Python 3.10+, Flask 3.x |
| Data Processing | Pandas, NumPy |
| AI / LLM | IBM Granite via IBM watsonx.ai |
| Environment | python-dotenv |
| CORS | flask-cors |

---

## 📋 Viva / Demo Checklist

- ✅ Upload CSV or load sample data
- ✅ View SNR / BER / Latency statistics and charts
- ✅ See detected issues with severity badges
- ✅ Read AI-generated Cause · Explanation · Recommendation
- ✅ View Failure Risk + Signal Trend
- ✅ Review Recommended Actions
- ✅ Generate and download text report
- ✅ Works entirely without IBM credentials (fallback mode)

---

## 📄 License

MIT — free to use for educational purposes.
