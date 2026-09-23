/* ============================================================
   AI-Powered Signal Quality Analyzer — Frontend Script
   All communication with Flask backend happens here.
   ============================================================ */

"use strict";

// ---- Config ----
const API_BASE = "http://127.0.0.1:5000";

// ---- State ----
let uploadedFile   = null;    // File object from input
let lastResult     = null;    // Full analysis result from /api/analyze or /api/sample
let charts         = {};      // Chart.js instances keyed by id

// ---- Chart colour palette ----
const CHART_COLORS = {
  snr:     { border: "#38bdf8", bg: "rgba(56,189,248,.15)" },
  ber:     { border: "#f85149", bg: "rgba(248,81,73,.12)" },
  latency: { border: "#d29922", bg: "rgba(210,153,34,.12)" },
  quality: { border: "#22d3ee", bg: "rgba(34,211,238,.12)" },
};

// ================================================================
// NAV — smooth tab switching
// ================================================================
document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    const target = link.dataset.section;
    showSection(target);
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    link.classList.add("active");
  });
});

function showSection(name) {
  document.querySelectorAll(".page-section").forEach(s => s.classList.add("hidden"));
  const el = document.getElementById("section-" + name);
  if (el) el.classList.remove("hidden");
}

// ================================================================
// DRAG & DROP
// ================================================================
const dropZone     = document.getElementById("drop-zone");
const fileInput    = document.getElementById("csv-file-input");

dropZone.addEventListener("dragover",  e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", ()  => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelect(file);
});
dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFileSelect(fileInput.files[0]);
});

function handleFileSelect(file) {
  if (!file.name.toLowerCase().endsWith(".csv")) {
    alert("Please select a .csv file.");
    return;
  }
  uploadedFile = file;
  showUploadStatus(file.name, null);
  document.getElementById("btn-analyze").disabled = false;
}

// ================================================================
// UPLOAD STATUS
// ================================================================
function showUploadStatus(filename, recordCount) {
  const box     = document.getElementById("upload-status");
  const fnEl    = document.getElementById("status-filename");
  const recEl   = document.getElementById("status-records");
  fnEl.textContent  = "📁 " + filename;
  recEl.textContent = recordCount !== null ? `📊 ${recordCount} records` : "";
  box.classList.remove("hidden");
}

// ================================================================
// LOAD SAMPLE DATA
// ================================================================
document.getElementById("btn-load-sample").addEventListener("click", async () => {
  showLoading(true);
  try {
    const res = await fetch(`${API_BASE}/api/sample`);
    if (!res.ok) throw new Error((await res.json()).error || "Server error");
    const data = await res.json();
    lastResult = data;
    showUploadStatus(data.filename || "signal_data.csv (sample)", data.record_count);
    document.getElementById("btn-analyze").disabled    = false;
    document.getElementById("btn-generate-report").disabled = false;
    renderAll(data);
    navigateTo("analysis");
  } catch (err) {
    alert("Error loading sample data:\n" + err.message);
  } finally {
    showLoading(false);
  }
});

// ================================================================
// RUN FULL ANALYSIS
// ================================================================
document.getElementById("btn-analyze").addEventListener("click", async () => {
  if (!uploadedFile) return;
  showLoading(true);
  try {
    const form = new FormData();
    form.append("file", uploadedFile);
    const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).error || "Server error");
    const data = await res.json();
    lastResult = data;
    showUploadStatus(uploadedFile.name, data.record_count);
    document.getElementById("btn-generate-report").disabled = false;
    renderAll(data);
    navigateTo("analysis");
  } catch (err) {
    alert("Analysis failed:\n" + err.message);
  } finally {
    showLoading(false);
  }
});

// ================================================================
// MASTER RENDER
// ================================================================
function renderAll(data) {
  renderKPI(data.stats, data.quality);
  renderStats(data.stats);
  renderCharts(data.stats);
  renderIssues(data.issues);
  renderInsight(data.insight);
  renderActions(data.recommendations);
  renderPrediction(data.prediction);
}

// ================================================================
// KPI ROW
// ================================================================
function renderKPI(stats, quality) {
  document.getElementById("kpi-snr-val").textContent   = stats.snr.current.toFixed(2);
  document.getElementById("kpi-ber-val").textContent   = stats.ber.current.toFixed(4);
  document.getElementById("kpi-lat-val").textContent   = stats.latency.current.toFixed(1);
  document.getElementById("kpi-score-val").textContent = quality.score;
  document.getElementById("kpi-score-label").textContent = quality.label;

  // Colour the score card
  const scoreCard = document.getElementById("kpi-score");
  scoreCard.style.borderColor =
    quality.status === "CRITICAL" ? "var(--critical)" :
    quality.status === "WARNING"  ? "var(--warning)"  : "var(--success)";

  document.getElementById("kpi-row").classList.remove("hidden");
}

// ================================================================
// STATS TABLE
// ================================================================
function renderStats(stats) {
  const pairs = [
    ["snr",     "snr"],
    ["ber",     "ber"],
    ["latency", "lat"],
  ];
  pairs.forEach(([key, prefix]) => {
    const s = stats[key];
    document.getElementById(`${prefix}-current`).textContent = formatMetric(key, s.current);
    document.getElementById(`${prefix}-average`).textContent = formatMetric(key, s.average);
    document.getElementById(`${prefix}-minimum`).textContent = formatMetric(key, s.minimum);
    document.getElementById(`${prefix}-maximum`).textContent = formatMetric(key, s.maximum);
  });
  document.getElementById("stats-grid").classList.remove("hidden");
  document.getElementById("charts-grid").classList.remove("hidden");
}

function formatMetric(key, val) {
  if (key === "ber")     return val.toFixed(4);
  if (key === "snr")     return val.toFixed(2) + " dB";
  if (key === "latency") return val.toFixed(1) + " ms";
  return val;
}

// ================================================================
// CHARTS
// ================================================================
function renderCharts(stats) {
  const labels = stats.timestamps.map(ts => {
    const d = new Date(ts);
    return isNaN(d) ? ts : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  });

  buildLineChart("chart-snr",     labels, stats.snr_series,     "SNR (dB)",         CHART_COLORS.snr);
  buildLineChart("chart-ber",     labels, stats.ber_series,     "BER",              CHART_COLORS.ber);
  buildLineChart("chart-latency", labels, stats.latency_series, "Latency (ms)",     CHART_COLORS.latency);

  // Quality trend derived from SNR (proxy for combined quality)
  const qualityProxy = stats.snr_series.map(v => Math.round(Math.min(100, (v / 35) * 100)));
  buildLineChart("chart-quality", labels, qualityProxy, "Quality Proxy (%)", CHART_COLORS.quality);
}

function buildLineChart(canvasId, labels, data, label, colors) {
  const ctx = document.getElementById(canvasId).getContext("2d");
  if (charts[canvasId]) charts[canvasId].destroy();
  charts[canvasId] = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderColor:     colors.border,
        backgroundColor: colors.bg,
        borderWidth:     2,
        pointRadius:     2,
        pointHoverRadius: 5,
        fill:            true,
        tension:         0.35,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { labels: { color: "#8b949e", font: { size: 12 } } },
        tooltip: { mode: "index", intersect: false }
      },
      scales: {
        x: { ticks: { color: "#8b949e", maxTicksLimit: 8, font: { size: 11 } }, grid: { color: "#21262d" } },
        y: { ticks: { color: "#8b949e", font: { size: 11 } }, grid: { color: "#21262d" } }
      }
    }
  });
}

// ================================================================
// ISSUES
// ================================================================
function renderIssues(issues) {
  const container = document.getElementById("issues-container");
  container.innerHTML = "";
  if (!issues || !issues.length) {
    container.innerHTML = '<p class="placeholder-text">No issues data available.</p>';
    return;
  }
  issues.forEach(issue => {
    const card = document.createElement("div");
    card.className = `issue-card sev-${issue.severity}`;
    card.innerHTML = `
      <div>
        <span class="issue-sev-badge">${issue.severity}</span>
      </div>
      <div class="issue-main">
        <h4>${issue.issue}</h4>
        <p class="issue-meta">Metric: <strong>${issue.metric}</strong> &nbsp;|&nbsp; Value: <strong>${issue.value}</strong></p>
        <p class="issue-explain">${issue.explanation}</p>
      </div>`;
    container.appendChild(card);
  });
}

// ================================================================
// AI INSIGHT
// ================================================================
function renderInsight(insight) {
  if (!insight) return;
  document.getElementById("insight-cause").textContent          = insight.cause          || "—";
  document.getElementById("insight-explanation").textContent    = insight.explanation    || "—";
  document.getElementById("insight-recommendation").textContent = insight.recommendation || "—";
  document.getElementById("insight-source").textContent         = insight.source         || "AI Analysis";
  document.getElementById("insight-card").classList.remove("hidden");
}

// ================================================================
// RECOMMENDED ACTIONS
// ================================================================
function renderActions(recs) {
  const container = document.getElementById("actions-container");
  container.innerHTML = "";
  if (!recs || !recs.length) {
    container.innerHTML = '<p class="placeholder-text">No recommendations available.</p>';
    return;
  }
  const icons = ["🔧", "📡", "🔍", "⚡", "📊", "🛡️", "🔄", "📋"];
  recs.forEach((rec, i) => {
    const item = document.createElement("div");
    item.className = "action-item";
    item.innerHTML = `<span class="action-icon">${icons[i % icons.length]}</span><span>${rec}</span>`;
    container.appendChild(item);
  });
}

// ================================================================
// PREDICTION
// ================================================================
function renderPrediction(pred) {
  if (!pred) return;

  const riskEl   = document.getElementById("pred-risk");
  const trendEl  = document.getElementById("pred-trend");
  const statusEl = document.getElementById("pred-status");

  riskEl.textContent   = pred.failure_risk;
  trendEl.textContent  = pred.signal_trend;
  statusEl.textContent = pred.prediction;

  riskEl.className   = "pred-value risk-"  + pred.failure_risk;
  trendEl.className  = "pred-value trend-" + pred.signal_trend;
  statusEl.className = "pred-value";
  if (pred.prediction === "HIGH RISK") statusEl.style.color = "var(--critical)";
  else if (pred.prediction === "AT RISK") statusEl.style.color = "var(--warning)";
  else statusEl.style.color = "var(--success)";

  document.getElementById("pred-reason").textContent = pred.reason || "—";

  // Metric trend chips
  const chipContainer = document.getElementById("metric-trends");
  chipContainer.innerHTML = "";
  if (pred.metric_trends) {
    const icons = { IMPROVING: "⬆️", STABLE: "➡️", DEGRADING: "⬇️" };
    Object.entries(pred.metric_trends).forEach(([metric, dir]) => {
      const chip = document.createElement("div");
      chip.className = "trend-chip";
      chip.innerHTML = `${icons[dir] || "—"} <strong>${metric.toUpperCase()}</strong>: <span class="trend-${dir}">${dir}</span>`;
      chipContainer.appendChild(chip);
    });
  }

  document.getElementById("prediction-card").classList.remove("hidden");
}

// ================================================================
// REPORT
// ================================================================
document.getElementById("btn-generate-report").addEventListener("click", () => {
  if (!lastResult) return;
  const report = buildReport(lastResult);
  const preview = document.getElementById("report-preview");
  preview.textContent = report;
  preview.classList.remove("hidden");

  // Download
  const blob = new Blob([report], { type: "text/plain" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = "signal_quality_report.txt";
  a.click();
  URL.revokeObjectURL(url);

  navigateTo("report");
});

function buildReport(d) {
  const now = new Date().toLocaleString();
  const sep = "=".repeat(60);
  const sub = "-".repeat(60);

  let lines = [
    sep,
    "  AI-POWERED SIGNAL QUALITY ANALYZER — ANALYSIS REPORT",
    sep,
    `  Generated : ${now}`,
    `  Dataset   : ${d.filename || "Uploaded CSV"}`,
    `  Records   : ${d.record_count}`,
    sep,
    "",
    "1. SIGNAL STATISTICS",
    sub,
    `  SNR     — Current: ${d.stats.snr.current.toFixed(2)} dB  | Avg: ${d.stats.snr.average.toFixed(2)} dB  | Min: ${d.stats.snr.minimum.toFixed(2)} dB  | Max: ${d.stats.snr.maximum.toFixed(2)} dB`,
    `  BER     — Current: ${d.stats.ber.current.toFixed(4)}    | Avg: ${d.stats.ber.average.toFixed(4)}    | Min: ${d.stats.ber.minimum.toFixed(4)}    | Max: ${d.stats.ber.maximum.toFixed(4)}`,
    `  Latency — Current: ${d.stats.latency.current.toFixed(1)} ms | Avg: ${d.stats.latency.average.toFixed(1)} ms | Min: ${d.stats.latency.minimum.toFixed(1)} ms | Max: ${d.stats.latency.maximum.toFixed(1)} ms`,
    "",
    "2. SIGNAL QUALITY SCORE",
    sub,
    `  Score  : ${d.quality.score} / 100`,
    `  Rating : ${d.quality.label}`,
    `  Status : ${d.quality.status}`,
    "",
    "3. DETECTED ISSUES",
    sub,
  ];

  (d.issues || []).forEach((issue, i) => {
    lines.push(`  ${i + 1}. [${issue.severity}] ${issue.issue}`);
    lines.push(`     Metric: ${issue.metric}  |  Value: ${issue.value}`);
    lines.push(`     ${issue.explanation}`);
    lines.push("");
  });

  lines.push("4. AI INTELLIGENT INSIGHTS");
  lines.push(sub);
  if (d.insight) {
    lines.push(`  Source         : ${d.insight.source}`);
    lines.push(`  Cause          : ${d.insight.cause}`);
    lines.push(`  Explanation    : ${d.insight.explanation}`);
    lines.push(`  Recommendation : ${d.insight.recommendation}`);
  }
  lines.push("");

  lines.push("5. FAILURE PREDICTION");
  lines.push(sub);
  if (d.prediction) {
    lines.push(`  Failure Risk  : ${d.prediction.failure_risk}`);
    lines.push(`  Signal Trend  : ${d.prediction.signal_trend}`);
    lines.push(`  Prediction    : ${d.prediction.prediction}`);
    lines.push(`  Reason        : ${d.prediction.reason}`);
  }
  lines.push("");

  lines.push("6. RECOMMENDED ACTIONS");
  lines.push(sub);
  (d.recommendations || []).forEach((rec, i) => {
    lines.push(`  ${i + 1}. ${rec}`);
  });
  lines.push("");
  lines.push(sep);
  lines.push("  END OF REPORT — AI-Powered Signal Quality Analyzer");
  lines.push(sep);

  return lines.join("\n");
}

// ================================================================
// HELPERS
// ================================================================
function showLoading(visible) {
  document.getElementById("loading-overlay").classList.toggle("hidden", !visible);
}

function navigateTo(sectionName) {
  showSection(sectionName);
  document.querySelectorAll(".nav-link").forEach(l => {
    l.classList.toggle("active", l.dataset.section === sectionName);
  });
}
