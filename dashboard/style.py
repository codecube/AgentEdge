"""Dashboard styling — Edge Operations Center aesthetic."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Outfit:wght@300;400;600;700;800&display=swap');

:root {
    --bg-primary: #0a0e17;
    --bg-secondary: #111827;
    --bg-card: #151d2e;
    --bg-card-hover: #1a2438;
    --border: #1e293b;
    --border-active: #334155;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --cyan: #00f0ff;
    --cyan-dim: #00f0ff33;
    --amber: #ffaa00;
    --amber-dim: #ffaa0033;
    --crimson: #ff3366;
    --crimson-dim: #ff336633;
    --green: #22c55e;
    --green-dim: #22c55e33;
}

/* Global overrides */
.stApp {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Outfit', sans-serif !important;
}

.stApp header { background-color: transparent !important; }

/* Main title styling */
h1 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    color: var(--text-primary) !important;
}

h2, h3 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
    color: var(--text-secondary) !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
}

/* Card containers */
div[data-testid="stExpander"],
div[data-testid="column"] > div {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    padding: 12px 16px !important;
}

div[data-testid="stMetric"] label {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.08em !important;
    color: var(--text-muted) !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 500 !important;
    color: var(--cyan) !important;
}

/* Code/monospace blocks */
code, pre, .stCode {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* Status indicator animation */
@keyframes pulse-green {
    0%, 100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4); }
    50% { box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
}

@keyframes pulse-amber {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255, 170, 0, 0.4); }
    50% { box-shadow: 0 0 0 6px rgba(255, 170, 0, 0); }
}

@keyframes scan-line {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100vh); }
}

.status-online {
    display: inline-block;
    width: 8px; height: 8px;
    background: var(--green);
    border-radius: 50%;
    animation: pulse-green 2s ease-in-out infinite;
    margin-right: 8px;
}

.status-offline {
    display: inline-block;
    width: 8px; height: 8px;
    background: var(--crimson);
    border-radius: 50%;
    margin-right: 8px;
}

/* Message feed styling */
.msg-feed {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    line-height: 1.6;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 12px 16px;
    max-height: 300px;
    overflow-y: auto;
}

.msg-jetson { color: var(--cyan); }
.msg-macmini { color: var(--amber); }
.msg-system { color: var(--text-muted); }
.msg-anomaly { color: var(--crimson); font-weight: 500; }

/* LFM reasoning stream */
.lfm-stream {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    line-height: 1.8;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-left: 3px solid var(--cyan);
    border-radius: 0 4px 4px 0;
    padding: 16px 20px;
    color: var(--text-secondary);
    min-height: 80px;
}

.lfm-cursor {
    display: inline-block;
    width: 2px;
    height: 1em;
    background: var(--cyan);
    animation: blink 1s step-end infinite;
    margin-left: 2px;
    vertical-align: text-bottom;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}

/* AQI gauge */
.aqi-bar {
    display: flex;
    gap: 3px;
    margin-top: 4px;
}
.aqi-segment {
    height: 6px;
    flex: 1;
    border-radius: 2px;
    background: var(--border);
    transition: background 0.3s ease;
}
.aqi-1 .aqi-segment:nth-child(-n+1) { background: var(--green); }
.aqi-2 .aqi-segment:nth-child(-n+2) { background: #84cc16; }
.aqi-3 .aqi-segment:nth-child(-n+3) { background: var(--amber); }
.aqi-4 .aqi-segment:nth-child(-n+4) { background: #f97316; }
.aqi-5 .aqi-segment:nth-child(-n+5) { background: var(--crimson); }

/* Section dividers */
.section-header {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    margin-bottom: 16px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}

section[data-testid="stSidebar"] .stChatInput {
    background-color: var(--bg-card) !important;
    border-color: var(--border) !important;
}

section[data-testid="stSidebar"] .stChatInput input {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
    color: var(--text-primary) !important;
}

/* Plotly chart background override */
.js-plotly-plot .plotly .main-svg { background: transparent !important; }
</style>
"""

AQI_LABELS = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Unhealthy"}
AQI_COLORS = {1: "#22c55e", 2: "#84cc16", 3: "#ffaa00", 4: "#f97316", 5: "#ff3366"}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(21,29,46,0.6)",
    font=dict(family="JetBrains Mono, monospace", color="#94a3b8", size=11),
    margin=dict(l=40, r=16, t=32, b=32),
    xaxis=dict(gridcolor="#1e293b", zerolinecolor="#1e293b"),
    yaxis=dict(gridcolor="#1e293b", zerolinecolor="#1e293b"),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=10),
        orientation="h",
        y=1.12,
    ),
)
